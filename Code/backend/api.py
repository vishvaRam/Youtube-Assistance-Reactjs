import os
import re
import time
import shutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any
import google.generativeai as genai

# Local imports
from yt_transcript import get_clean_transcript
from yt_chat import (
    load_transcript_files,
    create_vector_store,
    setup_chatbot,
    TRANSCRIPT_DIR,
    VECTOR_DB_DIR
)
from yt_chat import store as chat_history_store

# Store chatbot instances by session ID
chatbots: Dict[str, Any] = {}

app = FastAPI(
    title="YouTube Chat Assistant API",
    description="API for chatting with YouTube video transcripts.",
    version="1.0.0",
)

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://172.20.0.3:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- End CORS Configuration ---

class VideoProcessRequest(BaseModel):
    youtube_url: HttpUrl
    api_key: str

class ChatRequest(BaseModel):
    question: str
    session_id: str

class ClearSessionRequest(BaseModel):
    session_id: str


def clear_directory_robust(path, retries=10, delay=0.2):
    """
    Clears only the contents of a directory without removing the directory itself.
    Useful for avoiding locking issues on the directory itself.
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        return True

    for i in range(retries):
        try:
            print(f"Attempt {i+1}: Trying to clear contents of '{path}'...")
            current_items = os.listdir(path)
            for item in current_items:
                item_path = os.path.join(path, item)
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)  # Use rmtree for subdirectories
            print(f"Successfully cleared contents of '{path}'.")
            return True
        except Exception as e:
            print(f"Error clearing '{path}': {e}. Retrying in {delay}s...")
            time.sleep(delay)
    raise OSError(f"Failed to clear contents of '{path}' after {retries} retries.")


@app.post("/process_video/", summary="Process a YouTube video and initialize chatbot")
async def process_video(request: VideoProcessRequest):
    """
    Fetches the transcript for a given YouTube URL and initializes a chatbot session.
    """
    video_url = str(request.youtube_url)
    api_key = request.api_key

    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required.")

    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error configuring Gemini API: {e}. Please check your API key.")

    try:
        video_id = get_video_id(video_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Could not extract video ID from URL.")
        
        session_id = video_id  # Session ID is tied to the video ID

        # 1. Clear existing chatbot instance if re-processing the same video
        if session_id in chatbots:
            del chatbots[session_id]
            print(f"Existing chatbot instance for session {session_id} removed.")

        # 2. Clear chat history for this session from yt_chat's store
        if session_id in chat_history_store:
            del chat_history_store[session_id]
            print(f"Existing chat history for session {session_id} removed.")

        # 3. Clear transcripts directory contents only (don't delete the dir itself)
        try:
            clear_directory_robust(TRANSCRIPT_DIR)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to clear transcripts directory: {e}")

        # 4. Clear vectorstore directory contents only
        try:
            clear_directory_robust(VECTOR_DB_DIR)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to clear vectorstore directory: {e}")

        # 5. Regenerate transcript
        transcript_result_message = get_clean_transcript(video_url)
        if "Error:" in transcript_result_message:
            raise HTTPException(status_code=500, detail=transcript_result_message)

        documents = load_transcript_files(directory=TRANSCRIPT_DIR)
        if not documents:
            raise HTTPException(status_code=500, detail=f"No transcript files found in '{TRANSCRIPT_DIR}' after processing.")

        vector_store = create_vector_store(documents, api_key)
        chatbot = setup_chatbot(vector_store, api_key)
        chatbots[session_id] = chatbot

        return {
            "message": "Video processed and chatbot initialized.",
            "session_id": session_id,
            "transcript_status": transcript_result_message
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process video and initialize chatbot: {e}")


@app.post("/chat/", summary="Send a message to the chatbot")
async def chat_with_video(request: ChatRequest):
    """
    Sends a question to the chatbot for a specific session and gets a response.
    """
    session_id = request.session_id
    question = request.question

    if session_id not in chatbots:
        raise HTTPException(status_code=404, detail="Session not found. Please process a video first.")

    chatbot = chatbots[session_id]

    try:
        result = chatbot.invoke(
            {"question": question},
            config={"configurable": {"session_id": session_id}}
        )
        answer = result.get("answer", "I couldn't generate an answer. Please try rephrasing your question or processing the video again.")
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get response from chatbot: {e}")


@app.post("/clear_session/", summary="Clear a specific chatbot session")
async def clear_backend_session(request: ClearSessionRequest):
    """
    Deletes the chatbot instance and its associated chat history for a given session ID.
    Note: This does NOT clear transcript or vector store files from disk.
    Those are handled by /process_video for a fresh start per video.
    """
    session_id = request.session_id

    if session_id in chatbots:
        del chatbots[session_id]
        print(f"Backend chatbot instance for session {session_id} cleared.")

    if session_id in chat_history_store:
        del chat_history_store[session_id]
        print(f"Backend chat history for session {session_id} cleared.")

    return {"message": f"Session '{session_id}' cleared successfully."}


def get_video_id(url):
    """Extract video ID from YouTube URL"""
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None


@app.get("/health", summary="Health check endpoint")
async def health_check():
    """Simple health check endpoint to verify API is running."""
    return {"status": "ok"}