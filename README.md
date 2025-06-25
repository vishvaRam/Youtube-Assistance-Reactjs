# 🤖 YouTube Chatbot

A powerful tool for chatting with YouTube videos using Google's Gemini API and Streamlit. This application allows you to have interactive conversations about the content of any YouTube video.

## 📦 GitHub Repository

The source code for this project is available on GitHub: [Youtube-Transcript-Assistant](https://github.com/vishvaRam/Youtube-Transcript-Assistant)

## 🐳 Docker Hub Repository

This project is available as a Docker image on Docker Hub: [vishva123/youtube-chatbot](https://hub.docker.com/r/vishva123/youtube-chatbot)

## 🚀 Quick Start with Docker

### Pull the Image
```bash
docker pull vishva123/youtube-chatbot
```

### Run the Container
```bash
docker run -p 8501:8501 vishva123/youtube-chatbot
```

The application will be available at `http://localhost:8501`

## ✨ Features

- 💬 Chat with any YouTube video using Gemini AI
- 📊 Real-time video content analysis
- 🎯 Interactive Streamlit dashboard
- 🐳 Docker containerization for easy deployment

## 📋 Requirements

- 🐳 Docker installed on your system
- 🌐 Internet connection for YouTube API access
- 🔑 Google Gemini API key

## ⚙️ Environment Variables

The container uses the following environment variables:
- `STREAMLIT_SERVER_PORT`: 8501 (default)
- `STREAMLIT_SERVER_ADDRESS`: 0.0.0.0 (default)

## 📖 How to Use

1. 🔑 Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 🐳 Run the Docker container with your API key
3. 🌐 Open the application in your browser at `http://localhost:8501`
4. 🔑 Enter the Gemini API key. 
5. 📺 Enter a YouTube video URL
6. 💬 Start chatting with the video content!

## 🔌 Port Mapping

The application runs on port 8501 by default. Make sure this port is available on your host machine.

## 🛠️ Building from Source

If you want to build the image locally:

1. 📥 Clone the repository
2. 📂 Navigate to the project directory
3. 🔨 Build the Docker image:
```bash
docker build -t youtube-chatbot ./Code
```

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 