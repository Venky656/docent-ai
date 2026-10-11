# Docent — AI Document Q&A Assistant

Upload any PDF and chat with it. Answers stream live with page-level citations.

## Quick start

```bash
cp .env.example .env   # add your API key (see below)
pip install -r requirements.txt
python app.py          # open http://localhost:8080
```

Get a free key: [Groq](https://console.groq.com) (`gsk_...`, recommended) or [Gemini](https://aistudio.google.com/app/apikey) (`AIza...`).

## How it works

PDF → extract text (pypdf → PyMuPDF → OCR) → chunk → embed (MiniLM) → FAISS → top-k retrieval → grounded, streamed answer with sources.

## Configure

`LLM_PROVIDER`: `groq` · `gemini` · `grok`. Key knobs in `.env`: `RETRIEVAL_K` (5), `MAX_CHUNK_CHARS` (600), `MAX_HISTORY_TURNS` (4), `MAX_OUTPUT_TOKENS` (1200). See `.env.example` for all options.

## Project layout

```
app.py                 Flask app + RAG pipeline
templates/             landing.html (/) · app.html (/app)
static/css/            stylesheet
samples/               test PDFs
tests/                 smoke test (python tests/smoke_test.py)
data/sessions/         per-session index (git-ignored, 24h expiry)
```

## Built by

**Venkaiah Swamy Kalikaya** — [LinkedIn](https://www.linkedin.com/in/venkaiah-swamy-kalikaya/) · [GitHub](https://github.com/Venky656) · [Portfolio](https://venky-portfolio-v1.vercel.app/)
