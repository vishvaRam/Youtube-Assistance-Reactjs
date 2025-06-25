import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css'; // Make sure this path is correct

const API_BASE_URL = 'http://localhost:8000'; // FastAPI backend URL

function App() {
    const [youtubeUrl, setYoutubeUrl] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [question, setQuestion] = useState('');
    const [chatHistory, setChatHistory] = useState([]);
    const [sessionId, setSessionId] = useState(null);
    const [videoUrlDisplay, setVideoUrlDisplay] = useState(null);

    useEffect(() => {
        // Load chat history from local storage on component mount
        const savedChatHistory = localStorage.getItem('chatHistory');
        const savedSessionId = localStorage.getItem('sessionId');
        const savedVideoUrl = localStorage.getItem('videoUrlDisplay');

        if (savedChatHistory) {
            setChatHistory(JSON.parse(savedChatHistory));
        }
        if (savedSessionId) {
            setSessionId(savedSessionId);
        }
        if (savedVideoUrl) {
            setVideoUrlDisplay(savedVideoUrl);
        }
    }, []);

    useEffect(() => {
        // Save chat history and session data to local storage whenever it changes
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
        if (sessionId) {
            localStorage.setItem('sessionId', sessionId);
        } else {
            localStorage.removeItem('sessionId');
        }
        if (videoUrlDisplay) {
            localStorage.setItem('videoUrlDisplay', videoUrlDisplay);
        } else {
            localStorage.removeItem('videoUrlDisplay');
        }
    }, [chatHistory, sessionId, videoUrlDisplay]);

    const processVideo = async () => {
        if (!youtubeUrl) {
            alert('Please enter a YouTube URL.');
            return;
        }
        if (!apiKey) {
            alert('Please enter your Gemini API key.');
            return;
        }

        try {
            setChatHistory(prev => [...prev, { role: 'info', content: 'Processing video and initializing chatbot...' }]);

            const response = await axios.post(`${API_BASE_URL}/process_video/`, {
                youtube_url: youtubeUrl,
                api_key: apiKey,
            });
            setSessionId(response.data.session_id);
            setVideoUrlDisplay(youtubeUrl);
            setChatHistory([]); // Clear chat history on new video
            localStorage.removeItem('chatHistory'); // Clear local storage for new video
            alert('Video processed and chatbot initialized successfully! You can now ask questions.');
            setChatHistory(prev => [...prev, { role: 'bot', content: 'Hello! I have processed the video. Ask me anything about it!' }]);

        } catch (error) {
            console.error('Error processing video:', error);
            const errorMessage = error.response?.data?.detail || error.message;
            alert(`Error: ${errorMessage}`);
            setChatHistory(prev => prev.filter(msg => msg.content !== 'Processing video and initializing chatbot...')); // Remove info message
            setChatHistory(prev => [...prev, { role: 'error', content: `Error processing video: ${errorMessage}` }]);
        }
    };

    const sendMessage = async () => {
        if (!question.trim()) return; // Don't send empty messages
        if (!sessionId) {
            alert('Please process a video first to start chatting.');
            return;
        }

        const userMessage = question;
        setChatHistory(prevChatHistory => [...prevChatHistory, { role: 'user', content: userMessage }]);
        setQuestion(''); // Clear input immediately

        try {
            setChatHistory(prev => [...prev, { role: 'info', content: 'Bot is thinking...' }]);

            const response = await axios.post(`${API_BASE_URL}/chat/`, {
                question: userMessage,
                session_id: sessionId,
            });
            const botResponse = response.data.answer;
            // Remove the 'Bot is thinking...' message before adding the actual response
            setChatHistory(prevChatHistory => prevChatHistory.filter(msg => msg.content !== 'Bot is thinking...'));
            setChatHistory(prevChatHistory => [...prevChatHistory, { role: 'bot', content: botResponse }]);
        } catch (error) {
            console.error('Error sending message:', error);
            const errorMessage = error.response?.data?.detail || error.message;
            // Remove the 'Bot is thinking...' message if there was an error
            setChatHistory(prevChatHistory => prevChatHistory.filter(msg => msg.content !== 'Bot is thinking...'));
            alert(`Error during chat: ${errorMessage}`);
            setChatHistory(prev => [...prev, { role: 'error', content: `Error during chat: ${errorMessage}` }]);
        }
    };

    const clearChat = () => {
        const confirmClear = window.confirm("Are you sure you want to clear the entire chat history and session?");
        if (confirmClear) {
            setChatHistory([]);
            setSessionId(null);
            setVideoUrlDisplay(null);
            localStorage.clear(); // Clear all relevant local storage
            alert('Chat history and session cleared!');
        }
    };

    // Helper to extract video ID for iframe
    const getYouTubeVideoId = (url) => {
        try {
            const urlObj = new URL(url);
            if (urlObj.hostname === 'www.youtube.com' || urlObj.hostname === 'youtube.com') {
                if (urlObj.pathname.includes('/watch')) {
                    return urlObj.searchParams.get('v');
                }
                if (urlObj.pathname.includes('/shorts/')) {
                    return urlObj.pathname.split('/shorts/')[1];
                }
            }
        } catch (e) {
            console.error("Invalid URL for video ID extraction:", url, e);
        }
        return null;
    };

    const displayVideoId = videoUrlDisplay ? getYouTubeVideoId(videoUrlDisplay) : null;

    return (
        <div className="app-container">
            <div className="sidebar">
                <h2>🎥 YouTube Video Chat</h2>
                <div className="input-group">
                    <label htmlFor="api-key">Gemini API Key:</label>
                    <input
                        id="api-key"
                        type="password"
                        placeholder="Enter your Gemini API Key"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        className="input-field"
                    />
                </div>
                <div className="input-group">
                    <label htmlFor="youtube-url">YouTube URL:</label>
                    <textarea
                        id="youtube-url"
                        placeholder="Paste your YouTube URL here..."
                        value={youtubeUrl}
                        onChange={(e) => setYoutubeUrl(e.target.value)}
                        className="input-field url-input"
                        rows={3}
                    />
                </div>
                <button onClick={processVideo} className="button primary-button">Process Video</button>
                <button onClick={clearChat} className="button secondary-button">Clear Chat History & Session</button>
                
                {displayVideoId && (
                    <>
                        <h3>Current Video</h3>
                        <div className="video-embed-container">
                            <iframe
                                width="100%"
                                height="200"
                                src={`https://www.youtube.com/embed/${displayVideoId}`}
                                title="YouTube video player"
                                frameBorder="0"
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowFullScreen
                            ></iframe>
                        </div>
                    </>
                )}

                <div className="how-to-use">
                    <h3>How to use:</h3>
                    <ol>
                        <li>Enter your Gemini API key.</li>
                        <li>Paste a YouTube video URL (full URL, including `https://`).</li>
                        <li>Click "Process Video".</li>
                        <li>Wait for transcript processing and chatbot initialization.</li>
                        <li>Start chatting about the video!</li>
                    </ol>
                </div>
            </div>
            <div className="chat-area">
                <div className="chat-messages">
                    {chatHistory.map((message, index) => (
                        <div key={index} className={`message ${message.role}`}>
                            <div className="message-content">
                                {message.role === 'user' && <strong>You:</strong>}
                                {message.role === 'bot' && <strong>Bot:</strong>}
                                {message.role === 'info' && <strong className="info-message-indicator">Info:</strong>}
                                {message.role === 'error' && <strong className="error-message-indicator">Error:</strong>}
                                <p>{message.content}</p>
                            </div>
                        </div>
                    ))}
                </div>
                {sessionId ? (
                    <div className="chat-input">
                        <input
                            type="text"
                            placeholder="Ask a question about the video..."
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                            disabled={!sessionId} // Disable if no session
                        />
                        <button onClick={sendMessage} className="button send-button" disabled={!sessionId}>Send</button>
                    </div>
                ) : (
                    <p className="initial-message">👈 Please process a YouTube video and enter your API key first to start chatting!</p>
                )}
            </div>
        </div>
    );
}

export default App;