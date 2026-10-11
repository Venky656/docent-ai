# Docent — AI Document Q&A Assistant

**Stop reading. Start asking.** Upload any PDF and chat with it. Docent finds the relevant pages and answers with citations — streaming live, like ChatGPT, but grounded in *your* document.

🌐 Landing page at `/` · 💬 App at `/app` · 🚀 Live at http://localhost:8080

## Features

- 📄 **PDF upload** — reports, papers, resumes, manuals (max 20 MB)
- 📷 **OCR fallback** — scanned/image PDFs are read automatically (Tesseract)
- 💬 **ChatGPT-style answers** — markdown, tables, streaming tokens, follow-ups with conversation memory
- 📑 **Page-level citations** — every answer traces to `[file, page]`, plus a collapsible Sources panel
- 💡 **Suggested questions** — tap-to-ask chips generated on every upload
- ⚡ **Multi-provider LLMs** — Groq (free, default), Gemini, or xAI Grok — switch with one env var
- 🔄 **Persistent sessions** — documents survive refresh & restarts (auto-expire after 24h)
- 🛡️ **Safe** — validated sessions, sanitized uploads, XSS-sanitized rendering, secrets in `.env` (git-ignored)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10, Flask 3, Werkzeug |
| RAG | LangChain, PyPDF + PyMuPDF + Tesseract OCR, RecursiveCharacterTextSplitter (500/50) |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` (384-dim) |
| Vector DB | FAISS (per-session, persisted to disk) |
| LLMs | Groq (`openai/gpt-oss-20b`), Gemini (`gemini-3.8-flash`), Grok (`grok-4.7`) — OpenAI-compatible clients, SSE streaming |
| Frontend | Vanilla HTML/CSS/JS, `marked` + DOMPurify |

## How it works

```
Upload → extract text (pypdf → pymupdf → OCR) → chunk → embed → FAISS index
Ask    → embed query → top-k similarity search → grounded prompt → streamed answer + sources
```

## Quick Start

### 1. Get an API key (pick one)

| Provider | Key | Cost |
|---|---|---|
| **Groq** (recommended) | Free at https://console.groq.com → API Keys (`gsk_...`) | $0 |
| Gemini | https://aistudio.google.com/app/apikey (`AIza...`, not `AQ.Ab...` tokens) | Free, 20 req/day |
| Grok (xAI) | https://console.x.ai (needs prepaid credits) | ~½¢/question |

### 2. Setup

```bash
cp .env.example .env
# Edit .env: set LLM_PROVIDER (groq/gemini/grok) + the matching API key
pip install -r requirements.txt
python app.py
```

Tesseract OCR engine must be installed for scanned PDFs (`brew install tesseract` on macOS).

### 3. Use

1. Open http://localhost:8080
2. Click **Open App** → upload a PDF
3. Tap a suggested question or ask your own

## Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `groq`, `gemini`, or `grok` |
| `GROQ_API_KEY` / `GROQ_MODEL` | `openai/gpt-oss-20b` | Groq settings |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | `gemini-3.8-flash` | Gemini settings |
| `XAI_API_KEY` / `GROK_MODEL` | `grok-4.7` | Grok settings |
| `ENABLE_SUGGESTIONS` | `false` | AI questions on upload (extra API call) |
| `RETRIEVAL_K` | `5` | Chunks retrieved per question |
| `MAX_CHUNK_CHARS` | `600` | Chars sent per chunk |
| `MAX_HISTORY_TURNS` | `4` | Conversation memory |
| `MAX_OUTPUT_TOKENS` | `1200` | Answer length cap |
| `SESSION_TTL_HOURS` | `24` | Session expiry |

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/app` | Chat app |
| `GET` | `/status` | Session restore check |
| `POST` | `/upload` | PDF ingest + suggestions |
| `POST` | `/ask_stream` | SSE streaming answers |
| `DELETE` | `/documents` | Clear session |

Sessions are identified by the `X-Session-ID` header (auto-issued, regex-validated).

## Built by

**Venkaiah Swamy Kalikaya (Venky)** — [LinkedIn](https://www.linkedin.com/in/venkaiah-swamy-kalikaya/) · [GitHub](https://github.com/Venky656) · [Portfolio](https://venky-portfolio-v1.vercel.app/)
