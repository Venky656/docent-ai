# 🚀 Quick Start Guide

## 1. Get Your FREE API Key

**IMPORTANT:** You currently have an OAuth token which expires in 1 hour!

### Get a permanent key:
1. Go to: **https://aistudio.google.com/app/apikey**
2. Click **"Create API Key"**
3. Copy the key (starts with `AIza...`)

## 2. Configure

Open `.env` and paste your key:

```bash
GEMINI_API_KEY=AIzaSy...your_key_here...
```

## 3. Run

```bash
python app.py
```

Then open: **http://localhost:5000**

---

## ✅ What's Fixed

- **Single document mode** - Upload replaces previous (no clutter)
- **Memory-only sessions** - Clears on refresh
- **Quota optimized** - Suggestions disabled (50% less API calls)
- **Clean UI** - Simple upload → chat flow
- **No persistence** - True one-time use

---

## 📊 API Quota Tips

- Free tier: ~15 requests/minute
- Each question = **1 API call** (suggestions disabled)
- If you enable suggestions: 2 calls per question
- Wait 60 seconds if you hit quota limit

---

## 🆘 Troubleshooting

| Error | Solution |
|-------|----------|
| `401 Unauthorized` | Your API key is invalid/expired. Get new `AIza...` key. |
| `429 Quota reached` | Wait 60 seconds. Normal for free tier. |
| `404 Model not found` | Set `GEMINI_MODEL=gemini-2.0-flash` in `.env` |
| `No module named...` | Run `pip install -r requirements.txt` |

---

**Enjoy your clean, simple RAG app!** 🎉
