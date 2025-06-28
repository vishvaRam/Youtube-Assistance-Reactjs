import os
import shutil
from typing import List, Optional, Any, Dict
import warnings

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*The function.*was deprecated.*")
warnings.filterwarnings("ignore", category=UserWarning)

from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
import google.generativeai as genai

# -------------------------------
# Configuration
# -------------------------------

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
VECTOR_DB_DIR = "vectorstore"
TRANSCRIPT_DIR = "transcripts"

# In-memory store for session histories
store = {} # This global store is accessed by api.py now

# -------------------------------
# Helper Functions
# -------------------------------

def get_session_history(session_id: str) -> ChatMessageHistory:
    """Retrieve or create message history for a session"""
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


def load_transcript_files(directory: str = TRANSCRIPT_DIR) -> List[Document]:
    """Load all transcript text files into LangChain Documents with metadata"""
    documents = []
    if not os.path.exists(directory):
        # If directory doesn't exist, it means it was just cleared by api.py
        # or no transcripts have been generated yet.
        print(f"Transcript directory '{directory}' does not exist or is empty.")
        return [] # Return empty list if directory is not found

    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                documents.append(
                    Document(page_content=content, metadata={"source": filename})
                )
                print(f"Loaded: {filename}")
            except Exception as e:
                print(f"Error loading {filename}: {str(e)}")
    return documents


def create_vector_store(documents: List[Document], api_key: str, persist_dir: str = VECTOR_DB_DIR):
    """Create a new vector store with Gemini embeddings"""
    if not documents:
        raise ValueError("No documents provided to create vector store")

    # The api.py now ensures that persist_dir is cleared before calling this function.
    # So, we can directly proceed to create a new vector store.
    print("Creating new vector store...")
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", "? ", "! "],
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len
    )

    try:
        chunks = text_splitter.split_documents(documents)
        if not chunks:
            raise ValueError("No text chunks created from documents")

        print(f"Created {len(chunks)} text chunks")

        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)

        vector_store = FAISS.from_documents(chunks, embeddings)

        # Ensure the directory exists (api.py already creates it, but good to be safe)
        os.makedirs(persist_dir, exist_ok=True)
        vector_store.save_local(persist_dir)
        print(f"Vector store saved to {persist_dir}")

        return vector_store

    except Exception as e:
        print(f"Error creating vector store: {str(e)}")
        raise


def setup_chatbot(vector_store, api_key: str, verbose: bool = False):
    """Set up conversational chain with custom prompt and message history"""

    llm = GoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0.6, google_api_key=api_key)

    # Custom Prompt Template with Markdown Formatting Instructions
    prompt_template = """
    You're a friendly AI assistant here to chat about YouTube videos!

    **Your Goal:**
    * Help users understand what's in the video by answering their questions.
    * Keep things clear, accurate, and easy to understand.
    * Chat in a natural, engaging way, like you're talking to a friend.
    * If something isn't mentioned in the video, it's totally fine to say so.

    **How to Respond:**
    * Focus on the **main ideas** and cool details from the video.
    * Be **concise** but still give enough info.
    * Always respond in **English**.
    * If a question goes beyond what the video covers, just let them know politely.

    **Things to Keep in Mind (Avoid these!):**
    * No need to mention "transcripts" or "timestamps."
    * Don't guess or add information that isn't in the video.
    * Keep your answers relevant to the video's content.

    **Formatting Tips (Use Markdown):**
    * Use **bold text** for really important stuff.
    * Use *italics* to emphasize words or ideas.
    * Use `code formatting` for specific terms or product names.
    * Use headings (like ## for main topics) if your answer gets a bit longer.
    * Bullet points or numbered lists are great for multiple items.
    * Use > blockquotes if you're directly quoting something from the video.

    **Video Context:**
    {context}

    **User Question:**
    {question}

    **Let's chat about this video!**
    """

    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vector_store.as_retriever(search_kwargs={"k": 6}),
        combine_docs_chain_kwargs={"prompt": PROMPT},
        verbose=verbose
    )

    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history"
    )

    return chain_with_history


def display_sources(response):
    """Display retrieved source chunks"""
    if "source_documents" in response:
        print("\nSources:")
        for i, doc in enumerate(response["source_documents"], 1):
            source = doc.metadata.get("source", "Unknown")
            content = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            print(f"\n{i}. From: {source}")
            print(f"{content}")


# -------------------------------
# Main Application Loop (for local testing, not used by FastAPI)
# -------------------------------

def main():
    api_key = input("Enter your Gemini API key: ").strip()
    if not api_key:
        print("Error: GOOGLE_API_KEY not provided!")
        return

    genai.configure(api_key=api_key)

    print("Loading transcripts...")
    documents = load_transcript_files()
    if not documents:
        print(f"No transcript files found in '{TRANSCRIPT_DIR}'")
        return

    print("Building vector database...")
    # In main(), we still need to ensure the vector store directory is clean
    if os.path.exists(VECTOR_DB_DIR):
        shutil.rmtree(VECTOR_DB_DIR)
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    vector_store = create_vector_store(documents, api_key)

    print("Setting up chatbot...")
    chatbot = setup_chatbot(vector_store, api_key)

    print("\n🤖 Chatbot ready! Type 'quit' to exit.\n")

    session_id = "abc123"

    while True:
        query = input("You: ").strip()
        if query.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        if not query:
            continue

        try:
            result = chatbot.invoke(
                {"question": query},
                config={"configurable": {"session_id": session_id}}
            )
            answer = result.get("answer", "No answer generated.")
            print(f"\nBot: {answer}")

        except Exception as e:
            print(f"\n⚠️ Error processing request: {str(e)}")


if __name__ == "__main__":
    main()