import os
import uuid
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any # Keep Any for chatbot instances
import google.generativeai as genai
from fastapi.middleware.cors import CORSMiddleware # Import CORS middleware


# Correct import for your existing yt_transcript.py
from yt_transcript import get_clean_transcript

# Correct imports for your existing yt_chat.py
from yt_chat import (
    load_transcript_files,
    create_vector_store,
    setup_chatbot,
    TRANSCRIPT_DIR # Assuming TRANSCRIPT_DIR is used for loading files
)

# Store chatbot instances by session ID
chatbots: Dict[str, Any] = {} # Use Any as setup_chatbot returns a RunnableWithMessageHistory

app = FastAPI(
    title="YouTube Chat Assistant API",
    description="API for chatting with YouTube video transcripts.",
    version="1.0.0",
)

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",  # Your frontend's address
    "http://127.0.0.1:3000", 
    "http://172.20.0.3:3000,"# Another common local address
    # Add any other origins your frontend might run on, e.g., for deployment
    # If deploying, replace localhost with your actual frontend domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)
# --- End CORS Configuration ---


class VideoProcessRequest(BaseModel):
    youtube_url: HttpUrl
    api_key: str

class ChatRequest(BaseModel):
    question: str
    session_id: str

@app.post("/process_video/", summary="Process a YouTube video and initialize chatbot")
async def process_video(request: VideoProcessRequest):
    """
    Fetches the transcript for a given YouTube URL and initializes a chatbot session.
    """
    video_url = str(request.youtube_url)
    api_key = request.api_key

    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required.")

    # Configure the Google Generative AI library with the provided API key
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error configuring Gemini API: {e}. Please check your API key.")

    try:
        # Step 1: Get clean transcript
        # Call the existing get_clean_transcript from your yt_transcript.py
        transcript_result_message = get_clean_transcript(video_url)

        if "Error:" in transcript_result_message:
            raise HTTPException(status_code=500, detail=transcript_result_message)

        # Generate a unique session ID for this video (or use video ID as session ID)
        # For simplicity, we can use the video_id itself or a new UUID
        # Using video_id extracted by yt_transcript will link session to that video
        video_id = get_video_id(video_url) # Re-extract video ID for session
        if not video_id:
             raise HTTPException(status_code=400, detail="Could not extract video ID from URL.")
        
        session_id = video_id # Use video ID as session ID for consistency

        # Step 2: Load transcripts, create vector store, and setup chatbot
        # These functions are from your existing yt_chat.py
        documents = load_transcript_files(directory=TRANSCRIPT_DIR)
        if not documents:
            raise HTTPException(status_code=500, detail=f"No transcript files found in '{TRANSCRIPT_DIR}' after processing.")
        
        vector_store = create_vector_store(documents, api_key)
        chatbot = setup_chatbot(vector_store, api_key) # This returns RunnableWithMessageHistory

        chatbots[session_id] = chatbot # Store the chatbot instance

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
        # The setup_chatbot returns a RunnableWithMessageHistory, which has an invoke method
        result = chatbot.invoke(
            {"question": question},
            config={"configurable": {"session_id": session_id}}
        )
        answer = result.get("answer", "I couldn't generate an answer. Please try rephrasing your question or processing the video again.")
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get response from chatbot: {e}")

# Helper from yt_transcript.py to extract video ID, needed for session management
def get_video_id(url):
    """Extract video ID from YouTube URL (re-defined here for local use within api.py)"""
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None

@app.get("/health", summary="Health check endpoint")
async def health_check():
    """
    Simple health check endpoint to verify API is running.
    """
    return {"status": "ok"}

# You might want to add an endpoint to clear a session or list active sessions for debugging.