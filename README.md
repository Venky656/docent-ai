# Docent — AI Document Q&A Assistant

Clean, simple document Q&A powered by Gemini AI and FAISS vector search.

## Features

- 📄 **Single PDF Upload** - Upload one document at a time (auto-replaces previous)
- 💬 **Smart Chat** - Ask questions about your document with AI-powered answers
- 🔄 **Persistent Sessions** - Document survives refresh & server restarts (auto-expires after 24h)
- 💰 **Quota Optimized** - Suggestions disabled by default (saves 50% API calls)
- ⚡ **Fast** - Streaming responses with real-time typing effect

## Quick Start

### 1. Get API Key

Get your **FREE** Gemini API key from:
👉 https://aistudio.google.com/app/apikey

> **Important:** Use a key starting with `AIza...` (NOT `AQ.Ab...` OAuth tokens - they expire in 1 hour!)

### 2. Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env and paste your API key
nano .env  # or use any text editor

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

### 3. Use

1. Open http://localhost:8080
2. Upload a PDF document
3. Ask questions in the chat
4. Refresh page to clear everything

