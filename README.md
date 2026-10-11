# 📄 Docent — AI Document Q&A Assistant

**Chat with any PDF.** Upload a document, ask questions, get cited answers — streaming live.

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Flask](https://img.shields.io/badge/Flask-3-black)
![Groq](https://img.shields.io/badge/LLM-Groq_free-orange)
![FAISS](https://img.shields.io/badge/Vector-FAISS-green)

## ✨ What it does

- Upload PDFs (OCR reads scanned pages too)
- ChatGPT-style answers with markdown + tables
- Every answer cites its source page, with a Sources panel
- Tap-to-ask suggestion chips on every upload
- Sessions survive refresh & restarts

## 🚀 Run it

```bash
cp .env.example .env   # paste a free Groq key from console.groq.com
pip install -r requirements.txt
python app.py
```

Open → http://localhost:8080

## ⚙️ Switch models

One var in `.env`: `LLM_PROVIDER=groq` (free) · `gemini` · `grok`. More knobs in `.env.example`.

## 🏗️ Inside

`app.py` · `templates/` · `static/css/` · `samples/` · `tests/` (`python tests/smoke_test.py`)

## 👤 Author

**Venkaiah Swamy Kalikaya** · [LinkedIn](https://www.linkedin.com/in/venkaiah-swamy-kalikaya/) · [GitHub](https://github.com/Venky656) · [Portfolio](https://venky-portfolio-v1.vercel.app/)
