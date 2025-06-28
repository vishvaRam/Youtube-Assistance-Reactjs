import React, { useState, useEffect } from 'react';
import { Video, MessageCircle, Send, Trash2, Play, Eye, EyeOff, Loader2, Bot, User, AlertCircle, Info } from 'lucide-react';
import { SiYoutube } from 'react-icons/si';

const API_BASE_URL = 'http://localhost:8000';

function App() {
    const [youtubeUrl, setYoutubeUrl] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [question, setQuestion] = useState('');
    const [chatHistory, setChatHistory] = useState([]);
    const [sessionId, setSessionId] = useState(null);
    const [videoUrlDisplay, setVideoUrlDisplay] = useState(null);
    const [showApiKey, setShowApiKey] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isSending, setIsSending] = useState(false);

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

        setIsProcessing(true);
        try {
            setChatHistory(prev => [...prev, { role: 'info', content: 'Processing video and initializing chatbot...' }]);

            const response = await fetch(`${API_BASE_URL}/process_video/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    youtube_url: youtubeUrl,
                    api_key: apiKey,
                }),
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'Failed to process video');
            }

            setSessionId(data.session_id);
            setVideoUrlDisplay(youtubeUrl);
            setChatHistory([]);
            localStorage.removeItem('chatHistory');
            setChatHistory(prev => [...prev, { role: 'bot', content: 'Hello! I have processed the video. Ask me anything about it!' }]);

        } catch (error) {
            console.error('Error processing video:', error);
            const errorMessage = error.message;
            setChatHistory(prev => prev.filter(msg => msg.content !== 'Processing video and initializing chatbot...'));
            setChatHistory(prev => [...prev, { role: 'error', content: `Error processing video: ${errorMessage}` }]);
        } finally {
            setIsProcessing(false);
        }
    };

    const formatBotMessage = (content) => {
        // Process block-level elements that depend on newlines first
        content = content
            // Headers (h1, h2, h3) - Order from most specific to least specific
            .replace(/\n# (.*)/g, '<h1 class="text-2xl font-bold mt-4 mb-2">$1</h1>')
            .replace(/\n## (.*)/g, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>')
            .replace(/\n### (.*)/g, '<h3 class="text-lg font-semibold mt-3 mb-2">$1</h3>')
            // Numbered lists - Ensure these are processed before general bullet points if there's a conflict
            .replace(/\n(\d+)\. /g, '<br>$1. ') // Using <br> here to ensure a line break is kept
            // Bullet points (both * and -)
            .replace(/\n\* /g, '<br>• ') // Using <br> here to ensure a line break is kept
            .replace(/\n- /g, '<br>• '); // Using <br> here to ensure a line break is kept

        // Process inline elements and general text formatting
        content = content
            // Bold text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Italic text
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Inline code
            .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">$1</code>')
            // Links [text](url)
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 underline">$1</a>')

        // Finally, handle general line breaks
        content = content
            // Convert double newlines to double HTML breaks for paragraph breaks
            .replace(/\n\n/g, '<br><br>')
            // Convert single newlines to single HTML breaks
            .replace(/\n/g, '<br>');

        return content;
    };

    

    const sendMessage = async () => {
        if (!question.trim()) return;
        if (!sessionId) {
            alert('Please process a video first to start chatting.');
            return;
        }

        const userMessage = question;
        setChatHistory(prevChatHistory => [...prevChatHistory, { role: 'user', content: userMessage }]);
        setQuestion('');
        setIsSending(true);

        try {
            setChatHistory(prev => [...prev, { role: 'info', content: 'Bot is thinking...' }]);

            const response = await fetch(`${API_BASE_URL}/chat/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: userMessage,
                    session_id: sessionId,
                }),
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'Failed to send message');
            }

            const botResponse = data.answer;
            setChatHistory(prevChatHistory => prevChatHistory.filter(msg => msg.content !== 'Bot is thinking...'));
            setChatHistory(prevChatHistory => [...prevChatHistory, { role: 'bot', content: botResponse }]);
        } catch (error) {
            console.error('Error sending message:', error);
            const errorMessage = error.message;
            setChatHistory(prevChatHistory => prevChatHistory.filter(msg => msg.content !== 'Bot is thinking...'));
            setChatHistory(prev => [...prev, { role: 'error', content: `Error during chat: ${errorMessage}` }]);
        } finally {
            setIsSending(false);
        }
    };

    const clearChat = async () => { // Made async to await backend call
        const confirmClear = window.confirm("Are you sure you want to clear the entire chat history and session?");
        if (confirmClear) {
            // First, clear frontend state for immediate UI feedback
            setChatHistory([]);
            setVideoUrlDisplay(null);

            // Attempt to clear session on the backend if a session ID exists
            if (sessionId) {
                try {
                    setChatHistory(prev => [...prev, { role: 'info', content: 'Clearing session on backend...' }]);
                    const response = await fetch(`${API_BASE_URL}/clear_session/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ session_id: sessionId }),
                    });

                    const data = await response.json();

                    if (!response.ok) {
                        // Even if backend fails, proceed to clear frontend state, but log error
                        throw new Error(data.detail || 'Failed to clear session on backend');
                    }
                    // Remove the "Clearing session..." message
                    setChatHistory(prev => prev.filter(msg => msg.content !== 'Clearing session on backend...'));
                    setChatHistory(prev => [...prev, { role: 'info', content: 'Session successfully cleared on backend.' }]);

                } catch (error) {
                    console.error('Error clearing backend session:', error);
                    // Remove the "Clearing session..." message
                    setChatHistory(prev => prev.filter(msg => msg.content !== 'Clearing session on backend...'));
                    setChatHistory(prev => [...prev, { role: 'error', content: `Failed to clear backend session: ${error.message}` }]);
                }
            }

            // Finally, clear local storage and set sessionId to null
            // This ensures a complete reset on the frontend, regardless of backend success
            localStorage.clear();
            setSessionId(null);
        }
    };

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

    const renderMessageIcon = (role) => {
        switch (role) {
            case 'user':
                return <User className="w-5 h-5" />;
            case 'bot':
                return <Bot className="w-5 h-5" />;
            case 'error':
                return <AlertCircle className="w-5 h-5" />;
            case 'info':
                return <Info className="w-5 h-5" />;
            default:
                return null;
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
            <div className="flex h-screen">
                {/* Sidebar */}
                <div className="w-2/5 bg-white/80 backdrop-blur-sm border-r border-gray-200 shadow-xl flex flex-col">
                    {/* Header */}
                    <div className="p-6 border-b border-gray-100">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 bg-gradient-to-r from-red-500 to-pink-500 rounded-lg">
                                <SiYoutube className="w-8 h-8 text-white" />
                            </div>
                            {/* NEW: Added a div to wrap the h1 and p */}
                            <div>
                                <h1 className="text-xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                                    YouTube Video Chat
                                </h1>
                                <p className="text-lg text-gray-600">Chat with any YouTube video using AI</p>
                            </div>
                        </div>
                    </div>

                    {/* Form Section */}
                    <div className="p-6 space-y-6 flex-1 overflow-y-auto">
                        {/* API Key Input */}
                        <div className="space-y-2">
                            <label className="block text-lg font-semibold text-gray-700">
                                Gemini API Key
                            </label>
                            <div className="relative">
                                <input
                                    type={showApiKey ? "text" : "password"}
                                    placeholder="Enter your Gemini API Key"
                                    value={apiKey}
                                    onChange={(e) => setApiKey(e.target.value)}
                                    className="text-lg w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 pr-12"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowApiKey(!showApiKey)}
                                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                >
                                    {showApiKey ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>
                        </div>

                        {/* YouTube URL Input */}
                        <div className="space-y-2">
                            <label className="block text-sm font-semibold text-gray-700">
                                YouTube URL
                            </label>
                            <textarea
                                placeholder="Paste your YouTube URL here..."
                                value={youtubeUrl}
                                onChange={(e) => setYoutubeUrl(e.target.value)}
                                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 resize-none"
                                rows={1}
                            />
                        </div>

                        {/* Process Button */}
                        {/* Process and Clear Buttons Container */}
                        <div className="flex gap-4"> {/* Added flex and gap for spacing */}
                            {/* Process Button */}
                            <button
                                onClick={processVideo}
                                disabled={isProcessing || !youtubeUrl || !apiKey}
                                className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 px-4 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
                            >
                                {isProcessing ? (
                                    <>
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                        Processing...
                                    </>
                                ) : (
                                    <>
                                        <Play className="w-5 h-5" />
                                        Process Video
                                    </>
                                )}
                            </button>

                            {/* Clear Chat Button */}
                            <button
                                onClick={clearChat}
                                className="flex-1 bg-gradient-to-r from-gray-500 to-gray-600 text-white py-3 px-4 rounded-xl font-semibold hover:from-gray-600 hover:to-gray-700 transition-all duration-200 flex items-center justify-center gap-2"
                            >
                                <Trash2 className="w-4 h-4" />
                                Clear Chat & Session
                            </button>
                        </div>

                        {/* Video Preview */}
                        {displayVideoId && (
                            <div className="space-y-3">
                                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                                    <Video className="w-5 h-5" />
                                    Current Video
                                </h3>
                                <div className="bg-gray-100 rounded-xl overflow-hidden shadow-lg">
                                    <iframe
                                        width="100%"
                                        // height="500"
                                        src={`https://www.youtube.com/embed/${displayVideoId}`}
                                        title="YouTube video player"
                                        frameBorder="0"
                                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                        allowFullScreen
                                        className="rounded-xl"
                                        style={{ aspectRatio: '16 / 9' }} 
                                    />
                                </div>
                            </div>
                        )}

                        {/* Instructions */}
                        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                            <h3 className="font-semibold text-blue-800 mb-3 flex items-center gap-2">
                                <Info className="w-5 h-5 text-xl" />
                                How to use
                            </h3>
                            <ol className="text-lg text-blue-700 space-y-1 list-decimal list-inside">
                                <li>Enter your Gemini API key</li>
                                <li>Paste a YouTube video URL</li>
                                <li>Click "Process Video"</li>
                                <li>Wait for processing to complete</li>
                                <li>Start chatting about the video!</li>
                            </ol>
                        </div>
                    </div>
                </div>

                {/* Chat Area */}
                <div className="flex-1 flex flex-col bg-gradient-to-b from-white/50 to-gray-50/50 backdrop-blur-sm">
                    {/* Chat Header */}
                    <div className="p-6 border-b border-gray-200 bg-white/80 backdrop-blur-sm">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg">
                                <MessageCircle className="w-8 h-8 text-white" />
                            </div>
                            <div>
                                <h2 className="text-xl font-bold text-gray-800">Chat Interface</h2>
                                <p className="text-xl text-gray-600">
                                    {sessionId ? 'Ask questions about your video' : 'Process a video to start chatting'}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-4">
                        {chatHistory.length === 0 && !sessionId ? (
                            <div className="text-center py-12">
                                <div className="w-20 h-20 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <MessageCircle className="w-10 h-10 text-blue-500" />
                                </div>
                                <h3 className="text-xl font-semibold text-gray-700 mb-2">Ready to Chat!</h3>
                                <p className="text-lg text-gray-500 max-w-md mx-auto">
                                    Process a YouTube video first to start having conversations about its content.
                                </p>
                            </div>
                        ) : (
                            chatHistory.map((message, index) => (
                                <div key={index} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    {message.role !== 'user' && (
                                        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white ${
                                            message.role === 'bot' ? 'bg-gradient-to-r from-blue-500 to-indigo-500' :
                                            message.role === 'error' ? 'bg-gradient-to-r from-red-500 to-pink-500' :
                                            'bg-gradient-to-r from-yellow-500 to-orange-500'
                                        }`}>
                                            {renderMessageIcon(message.role)}
                                        </div>
                                    )}
                                    <div className={`max-w-2xl px-4 py-3 rounded-2xl shadow-lg ${
                                        message.role === 'user' 
                                            ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-br-md' 
                                            : message.role === 'bot'
                                            ? 'bg-white border border-gray-200 text-gray-800 rounded-bl-md'
                                            : message.role === 'error'
                                            ? 'bg-red-50 border border-red-200 text-red-800'
                                            : 'bg-yellow-50 border border-yellow-200 text-yellow-800'
                                    }`}>
                                        <p className="text-lg leading-relaxed whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: formatBotMessage(message.content) }}/>
                                    </div>
                                    {message.role === 'user' && (
                                        <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full flex items-center justify-center text-white">
                                            <User className="w-5 h-5" />
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>

                    {/* Chat Input */}
                    {sessionId && (
                        <div className="p-6 border-t border-gray-200 bg-white/80 backdrop-blur-sm">
                            <div className="flex gap-3">
                                <input
                                    type="text"
                                    placeholder="Ask a question about the video..."
                                    value={question}
                                    onChange={(e) => setQuestion(e.target.value)}
                                    onKeyPress={(e) => e.key === 'Enter' && !isSending && sendMessage()}
                                    className="text-lg flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                                    disabled={isSending}
                                />
                                <button
                                    onClick={sendMessage}
                                    disabled={!question.trim() || isSending}
                                    className="bg-gradient-to-r from-green-600 to-emerald-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 shadow-lg hover:shadow-xl"
                                >
                                    {isSending ? (
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                    ) : (
                                        <Send className="w-5 h-5" />
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default App;