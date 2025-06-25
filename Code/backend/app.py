import streamlit as st
import os
from yt_transcript import get_clean_transcript, get_video_id
# Assuming app.py contains the core helper functions.
# If app.py is meant to be a standalone script, consider creating a 'utils.py'
# or similar file to house these reusable functions (load_transcript_files, etc.)
# and import from there. For now, assuming you meant to import from `app`.
from yt_chat import ( 
    load_transcript_files,
    create_vector_store,
    setup_chatbot,
    TRANSCRIPT_DIR,
    VECTOR_DB_DIR
)
import google.generativeai as genai

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "chatbot" not in st.session_state:
    st.session_state.chatbot = None
if "stored_video_url" not in st.session_state:
    st.session_state.stored_video_url = None
if "api_key" not in st.session_state:
    st.session_state.api_key = "" # Initialize API key in session state


def check_transcript_exists(video_id):
    """Check if transcript exists for the given video ID"""
    if not video_id or not os.path.exists(TRANSCRIPT_DIR):
        return False
    transcript_files = os.listdir(TRANSCRIPT_DIR)
    return any(file.startswith(f"transcript_{video_id}_") for file in transcript_files)

# Page config
st.set_page_config(
    page_title="YouTube Video Chat",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for improved UI
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 0;
    }
    
    /* Sidebar width control */
    [data-testid="stSidebar"] {
        min-width: 40% !important;
        max-width: 40% !important;
    }
    
    /* Ensure text inputs (including password type) are dark */
    .stTextInput>div>div>input {
        background-color: #262730; /* A common dark mode background for inputs */
        color: white; /* Ensure text is readable */
        border: 1px solid #4a4a4a; /* Add a subtle dark border */
    }

    /* Adjust placeholder color for text inputs in dark theme if needed */
    .stTextInput>div>div>input::placeholder {
        color: #aaaaaa; /* Lighter gray for placeholder text */
    }

    /* Style the text area for the YouTube URL similarly */
    .stTextArea>div>div>textarea {
        background-color: #262730; /* A common dark mode background for textareas */
        color: white; /* Ensure text is readable */
        border: 1px solid #4a4a4a; /* Add a subtle dark border */
    }

    /* Adjust placeholder color for text areas in dark theme if needed */
    .stTextArea>div>div>textarea::placeholder {
        color: #aaaaaa; /* Lighter gray for placeholder text */
    }

    /* Eye icon for password field - make it visible on dark background */
    .stTextInput>div>div>div>button { /* This targets the the button containing the eye icon */
        color: #ffffff !important; /* Force the eye icon color to white */
        background-color: transparent !important; /* Ensure no background for the button itself */
        border: none !important; /* Remove any border */
    }
    
    /* Chat message styling */
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    
    .chat-message.user {
        background-color: #e3f2fd; /* Light blue for user messages */
    }
    
    .chat-message.assistant {
        background-color: #f5f5f5; /* Light gray for assistant messages */
    }
    
    /* IMPORTANT: If you want chat messages to be dark in dark mode, you'd need to adjust these */
    /* Example for dark mode chat messages: */
    /*
    @media (prefers-color-scheme: dark) {
        .chat-message.user {
            background-color: #3b3b40;
            color: #e0e0e0;
        }
        .chat-message.assistant {
            background-color: #2d2d30;
            color: #e0e0e0;
        }
    }
    */


    /* Message content styling */
    .chat-message .message-content {
        display: flex;
        margin-top: 0.5rem;
    }
    
    /* Avatar styling */
    .chat-message .avatar {
        width: 40px;
        height: 40px;
        margin-right: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #fff;
        border-radius: 50%;
        font-size: 20px;
    }
    

    /* Chat container styling */
    .stChatMessage {
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 10px;
    }
    
    /* Chat input styling */
    .stChatInputContainer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 1rem 2rem;
        background: white; /* This will be white even in dark mode */
        border-top: 1px solid #ddd;
        z-index: 1000;
        backdrop-filter: blur(10px);
    }
    /* IMPORTANT: If you want the chat input container to be dark in dark mode, you'd need to adjust this */
    /* Example for dark mode chat input container: */
    /*
    @media (prefers-color-scheme: dark) {
        .stChatInputContainer {
            background: #1e1e1e;
            border-top: 1px solid #333;
        }
    }
    */
    
    /* Add padding at bottom for chat input */
    .main {
        padding-bottom: 80px;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        padding: 2rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🎥 YouTube Video Chat")
    st.write("Enter a YouTube video URL and your Gemini API key to start chatting about its content!")
    
    # API Key Input - Use session state for persistence
    st.session_state.api_key = st.text_input("Gemini API Key", type="password", value=st.session_state.api_key)

    # Updated URL input with placeholder and help text
    video_url = st.text_area(
        "YouTube URL",
        placeholder="Paste your YouTube URL here...",
        # Use a real YouTube URL as an example
        help="Example: youtube.com/watch?v=", 
        height=100,
        key="video_url_input"
    )
    
    if st.button("Process Video", type="secondary"):
        # Validate inputs only when the button is clicked
        if not video_url:
            st.toast("⚠️ Please enter a YouTube URL.")
            st.stop() # Stop execution until a URL is provided
        
        if not st.session_state.api_key:
            st.toast("⚠️ Please enter your Gemini API key.")
            st.stop() # Stop execution until API key is provided

        # Configure genai with the user-provided API key
        try:
            genai.configure(api_key=st.session_state.api_key)
        except Exception as e:
            st.error(f"Error configuring Gemini API: {e}. Please check your API key.")
            st.stop()

        # Validate URL by trying to extract video ID
        video_id = get_video_id(video_url)
        if not video_id:
            st.toast("❌ Invalid YouTube URL. Please make sure you've copied a complete and valid YouTube video URL.")
            st.stop() # Stop execution if URL is invalid
        else:
            st.toast("✅ YouTube URL recognized! Attempting to process transcript...") # Positive feedback

        try:
            # Check if transcript already exists
            if check_transcript_exists(video_id):
                st.toast("ℹ️ Transcript already exists! Loading chat interface...")
                try:
                    documents = load_transcript_files()
                    if documents:
                        with st.spinner("Creating chat interface..."):
                            vector_store = create_vector_store(documents, st.session_state.api_key)
                            st.session_state.chatbot = setup_chatbot(vector_store, st.session_state.api_key)
                            st.session_state.video_id = video_id
                            st.session_state.stored_video_url = video_url
                            st.toast("✅ Chat interface ready!")
                    else:
                        st.toast("❌ No transcript files found. Please try processing the video again.")
                except Exception as e:
                    st.toast(f"❌ Error setting up chat interface: {str(e)}")
            else:
                with st.spinner("Processing transcript..."):
                    result = get_clean_transcript(video_url)
                    if result.startswith("Error"):
                        st.toast(result + " ❌")
                    else:
                        st.toast("✅ Transcript processed successfully!")
                        
                        # Initialize chatbot with new transcript
                        try:
                            documents = load_transcript_files()
                            if documents:
                                with st.spinner("Creating chat interface..."):
                                    vector_store = create_vector_store(documents, st.session_state.api_key)
                                    st.session_state.chatbot = setup_chatbot(vector_store, st.session_state.api_key)
                                    st.session_state.video_id = video_id
                                    st.session_state.stored_video_url = video_url
                                    st.toast("✅ Chat interface ready!")
                            else:
                                st.toast("❌ No transcript files found. Please try processing the video again.")
                        except Exception as e:
                            st.toast(f"❌ Error setting up chat interface: {str(e)}")
        except Exception as e:
            st.toast(f"❌ Error processing video: {str(e)}")
    
    # Always display the video if URL exists in session state
    if st.session_state.stored_video_url:
        st.divider()
        st.subheader("Current Video")
        st.video(st.session_state.stored_video_url)
    
    st.divider()
    
    # Clear chat button
    if st.button("🧹 Clear Chat History", type="secondary", use_container_width=False):
        st.session_state.chat_history = []
        st.toast("🧹 Chat history cleared!")
    
    st.markdown("""
    ### How to use:
    1. Enter your Gemini API key.
    2. Paste a YouTube video URL
    3. Click "Process Video"
    4. Wait for transcript processing
    5. Start chatting about the video!
    """)

# Main chat interface
st.title("💬 Chat with Your Video")

# Display chat messages using Streamlit's native chat elements
chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat input using Streamlit's native chat input
if st.session_state.chatbot:
    if prompt := st.chat_input("Ask about the video...", key="chat_input"):
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = st.session_state.chatbot.invoke(
                    {"question": prompt},
                    config={"configurable": {"session_id": st.session_state.video_id}}
                )
                answer = result.get("answer", "I couldn't generate an answer. Please try rephrasing your question.")
                st.markdown(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
else:
    st.info("👈 Please process a YouTube video and enter your API key first to start chatting!")
