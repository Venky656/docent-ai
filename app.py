import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import re
import json
import time
import uuid
import shutil
import traceback
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, g
from werkzeug.utils import secure_filename

from google import genai
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.7").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()

client = None
oai_client = None
OAI_MODEL = ""

if LLM_PROVIDER == "grok":
    XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()
    if not XAI_API_KEY:
        raise RuntimeError("Missing XAI_API_KEY in .env (LLM_PROVIDER=grok).")
    from openai import OpenAI
    oai_client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1", timeout=60.0)
    OAI_MODEL = GROK_MODEL
    print(f"LLM provider: grok ({OAI_MODEL})")
elif LLM_PROVIDER == "groq":
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
    if not GROQ_API_KEY:
        raise RuntimeError("Missing GROQ_API_KEY in .env (LLM_PROVIDER=groq). Get a free key at https://console.groq.com")
    from openai import OpenAI
    oai_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1", timeout=60.0)
    OAI_MODEL = GROQ_MODEL
    print(f"LLM provider: groq ({OAI_MODEL})")
else:
    API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    if not API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY in .env.")
    if API_KEY.startswith("AQ.Ab") or API_KEY.startswith("ya29."):
        print("Warning: OAuth token. Get key from: https://aistudio.google.com/app/apikey")
    client = genai.Client(api_key=API_KEY, http_options={"timeout": 60000})
    print(f"LLM provider: gemini ({MODEL_NAME})")


def llm_generate(prompt, max_tokens=300, temperature=None):
    """Single non-streaming completion. Returns text."""
    if oai_client is not None:
        r = oai_client.chat.completions.create(
            model=OAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=TEMPERATURE if temperature is None else temperature,
        )
        return (r.choices[0].message.content or "")
    res = client.models.generate_content(model=MODEL_NAME, contents=f"{SYSTEM_PROMPT}\n\n{prompt}")
    return res.text or ""


def llm_stream(prompt, max_tokens=500, temperature=None):
    """Yield text deltas from a streaming completion."""
    if oai_client is not None:
        stream = oai_client.chat.completions.create(
            model=OAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=TEMPERATURE if temperature is None else temperature,
            stream=True,
        )
        for chunk in stream:
            d = (chunk.choices[0].delta.content or "") if chunk.choices else ""
            if d:
                yield d
    else:
        stream = client.models.generate_content_stream(model=MODEL_NAME, contents=prompt)
        for chunk in stream:
            t = getattr(chunk, "text", "") or ""
            if t:
                yield t

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET") or os.urandom(24).hex()
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf"}
ENABLE_SUGGESTIONS = os.getenv("ENABLE_SUGGESTIONS", "false").lower() == "true"

# Token-saving caps (tune via .env)
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "4"))
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "5"))
MAX_CHUNK_CHARS = int(os.getenv("MAX_CHUNK_CHARS", "600"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1200"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.6"))
SUGGESTION_CHUNKS = int(os.getenv("SUGGESTION_CHUNKS", "3"))
SUGGESTION_CTX_CHARS = int(os.getenv("SUGGESTION_CTX_CHARS", "1200"))

SYSTEM_PROMPT = (
    "You are a helpful AI document assistant, like ChatGPT. "
    "Answer the user's questions using the provided document context. "
    "Be conversational, clear, and well-structured: use short paragraphs, "
    "bullet points, and markdown headings where helpful. "
    "If the answer is not in the context, say so honestly instead of guessing. "
    "Always cite sources as [file, page]. "
    "Prefer bullet points for lists; use markdown tables only for true comparisons, "
    "keeping them narrow (max 3 columns, short cell text)."
)

print("Loading embeddings...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
print("Ready.")

SESSIONS = {}
SESSIONS_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sessions")
os.makedirs(SESSIONS_ROOT, exist_ok=True)
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_HOURS", "24")) * 3600

def session_paths(sid):
    base = os.path.join(SESSIONS_ROOT, sid)
    return {
        "base": base,
        "upload_dir": os.path.join(base, "uploads"),
        "faiss_dir": os.path.join(base, "faiss"),
        "meta": os.path.join(base, "meta.json"),
    }

def save_session_meta(sid, sess):
    try:
        docs = sess.get("documents", {})
        name = next(iter(docs)) if docs else None
        with open(session_paths(sid)["meta"], "w") as f:
            json.dump({
                "filename": name,
                "count": docs.get(name, {}).get("count", 0) if name else 0,
            }, f)
    except Exception as e:
        print(f"Could not save session meta: {e}", flush=True)

def load_session_from_disk(sid):
    p = session_paths(sid)
    if not (os.path.isdir(p["faiss_dir"]) and os.path.isfile(p["meta"])):
        return None
    try:
        with open(p["meta"]) as f:
            meta = json.load(f)
        db = FAISS.load_local(p["faiss_dir"], embeddings, allow_dangerous_deserialization=True)
        name = meta.get("filename") or "document.pdf"
        return {
            "vector_db": db,
            "documents": {name: {"path": os.path.join(p["upload_dir"], name),
                                 "chunks": [], "count": meta.get("count", 0)}},
            "upload_dir": p["upload_dir"],
            "faiss_dir": p["faiss_dir"],
        }
    except Exception as e:
        print(f"Could not restore session {sid}: {e}", flush=True)
        return None

def prune_old_sessions():
    now = time.time()
    try:
        for sid in os.listdir(SESSIONS_ROOT):
            base = os.path.join(SESSIONS_ROOT, sid)
            if os.path.isdir(base) and now - os.path.getmtime(base) > SESSION_TTL_SECONDS:
                shutil.rmtree(base, ignore_errors=True)
                print(f"Pruned expired session {sid}", flush=True)
    except Exception as e:
        print(f"Session prune failed: {e}", flush=True)

def get_session():
    sid = request.headers.get("X-Session-ID")
    if not sid or not re.fullmatch(r"[A-Za-z0-9\-_]{8,64}", sid):
        sid = uuid.uuid4().hex[:16]
    if sid not in SESSIONS:
        restored = load_session_from_disk(sid)
        if restored is not None:
            SESSIONS[sid] = restored
            print(f"Restored session {sid} from disk", flush=True)
        else:
            p = session_paths(sid)
            SESSIONS[sid] = {
                "vector_db": None,
                "documents": {},
                "upload_dir": p["upload_dir"],
                "faiss_dir": p["faiss_dir"],
            }
    return sid, SESSIONS[sid]

@app.before_request
def attach_session():
    sid, sess = get_session()
    g.sid = sid
    g.sess = sess

@app.after_request
def expose_session(resp):
    resp.headers["X-Session-ID"] = getattr(g, "sid", "")
    return resp

def cleanup_session(sid):
    if sid in SESSIONS:
        sess = SESSIONS[sid]
        for d in [sess.get("upload_dir"), sess.get("faiss_dir")]:
            if d and os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)
        base = session_paths(sid)["base"]
        if os.path.isdir(base):
            shutil.rmtree(base, ignore_errors=True)
        del SESSIONS[sid]

def is_quota_error(e):
    s = f"{type(e).__name__}: {e}".lower()
    return any(k in s for k in ("429", "quota", "resource_exhausted", "rate limit"))

def is_auth_error(e):
    s = f"{type(e).__name__}: {e}".lower()
    return any(k in s for k in ("401", "403", "unauthenticated", "api key not valid"))

OCR_MAX_PAGES = 10

def extract_documents(path, filename):
    """Try pypdf -> pymupdf text -> OCR. Returns (docs, method)."""
    try:
        docs = PyPDFLoader(path).load()
        docs = [d for d in docs if d.page_content and d.page_content.strip()]
        if docs:
            return docs, "pypdf"
    except Exception as e:
        print(f"pypdf extraction failed: {e}", flush=True)

    try:
        import pymupdf
        out = []
        with pymupdf.open(path) as pdf:
            for i, page in enumerate(pdf):
                t = (page.get_text() or "").strip()
                if t:
                    out.append(Document(page_content=t, metadata={"source": filename, "page": i}))
        if out:
            return out, "pymupdf"
    except Exception as e:
        print(f"pymupdf extraction failed: {e}", flush=True)

    try:
        import io
        import pymupdf
        import pytesseract
        from PIL import Image
        out = []
        with pymupdf.open(path) as pdf:
            for i in range(min(len(pdf), OCR_MAX_PAGES)):
                pix = pdf[i].get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                t = (pytesseract.image_to_string(img) or "").strip()
                if t:
                    out.append(Document(page_content=t, metadata={"source": filename, "page": i}))
        return out, "ocr"
    except Exception as e:
        print(f"OCR extraction failed: {e}", flush=True)

    return [], "none"

def is_transient_error(e):
    s = f"{type(e).__name__}: {e}".lower()
    return any(k in s for k in ("503", "unavailable", "overloaded", "500", "internal error",
                                "deadline exceeded", "timeout", "timed out", "connection"))

@app.route("/")
def home():
    return render_template("landing.html")

@app.route("/app")
def app_page():
    return render_template("app.html")

@app.route("/favicon.ico")
def favicon():
    return ("", 204)

@app.route("/status")
def status():
    sess = getattr(g, "sess", None) or {}
    docs = sess.get("documents", {})
    if sess.get("vector_db") is None or not docs:
        return jsonify({"ready": False})
    name = next(iter(docs))
    return jsonify({"ready": True, "filename": name, "chunks": docs[name].get("count", 0)})

@app.route("/upload", methods=["POST"])
def upload():
    sess = getattr(g, "sess")

    for old in list(sess.get("documents", {}).keys()):
        p = sess["documents"][old].get("path")
        if p and os.path.exists(p):
            os.remove(p)
    fd = sess.get("faiss_dir")
    if fd and os.path.exists(fd):
        shutil.rmtree(fd, ignore_errors=True)
    sess["documents"] = {}
    sess["vector_db"] = None

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file selected."}), 400

    filename = secure_filename(file.filename)
    if not filename:
        filename = "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF allowed."}), 400

    path = os.path.join(sess["upload_dir"], filename)
    os.makedirs(sess["upload_dir"], exist_ok=True)
    file.save(path)

    try:
        docs, method = extract_documents(path, filename)
        if not docs:
            return jsonify({"error": "No readable text found (even OCR found nothing). Try a different PDF."}), 400
        print(f"Extracted via {method}: {len(docs)} pages", flush=True)
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(docs)
        chunks = [c for c in chunks if c.page_content and c.page_content.strip()]
        if not chunks:
            return jsonify({"error": "PDF has no extractable text."}), 400
        for c in chunks:
            c.metadata["source"] = filename
        sess["documents"] = {filename: {"path": path, "chunks": chunks, "count": len(chunks)}}
        faiss_dir = sess["faiss_dir"]
        os.makedirs(faiss_dir, exist_ok=True)
        sess["vector_db"] = FAISS.from_documents(chunks, embeddings)
        sess["vector_db"].save_local(faiss_dir)
        save_session_meta(getattr(g, "sid", ""), sess)
    except Exception as e:
        print(f"Upload failed for {filename}:\n{traceback.format_exc()}", flush=True)
        msg = str(e)
        if "list index out of range" in msg:
            return jsonify({"error": "Could not parse this PDF (malformed file). Try re-exporting it, or another PDF."}), 400
        return jsonify({"error": f"Upload failed: {e}"}), 500

    suggestions = []
    if ENABLE_SUGGESTIONS:
        ctx = "\n".join(c.page_content for c in chunks[:SUGGESTION_CHUNKS])[:SUGGESTION_CTX_CHARS]
        for attempt in range(3):
            try:
                text = llm_generate(
                    f"Generate 5 short questions a reader might ask about this text. "
                    f"Return ONLY a JSON array of plain question strings, no objects, no markdown.\n\n{ctx}",
                    max_tokens=200,
                )
                start, end = text.find("["), text.rfind("]")
                parsed = json.loads(text[start:end + 1]) if start != -1 and end > start else None
                if isinstance(parsed, list):
                    norm = []
                    for q in parsed:
                        if isinstance(q, dict):
                            q = q.get("question") or q.get("q") or ""
                        if isinstance(q, str) and q.strip():
                            norm.append(q.strip())
                    if norm:
                        suggestions = norm[:5]
                        break
            except Exception as e:
                print(f"Suggestion attempt {attempt + 1}/3 failed: {type(e).__name__}: {e}", flush=True)
                if is_quota_error(e) or is_auth_error(e):
                    break
            time.sleep(1.5 * (attempt + 1))
        if not suggestions:
            print("Suggestions unavailable (quota/auth or empty response).", flush=True)

    return jsonify({
        "message": f"Uploaded {filename} ({len(chunks)} chunks).",
        "filename": filename,
        "chunks": len(chunks),
        "suggestions": suggestions,
    })

@app.route("/documents", methods=["DELETE"])
def clear_documents():
    cleanup_session(getattr(g, "sid", ""))
    return jsonify({"message": "Cleared."})

@app.route("/ask_stream", methods=["POST"])
def ask_stream():
    sess = getattr(g, "sess")
    if sess.get("vector_db") is None:
        return jsonify({"error": "No document uploaded."}), 400

    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query empty."}), 400

    history = data.get("history", [])[-MAX_HISTORY_TURNS * 2:]
    history = [h for h in history if isinstance(h, dict) and h.get("role") in ("user", "assistant")]

    docs = sess["vector_db"].similarity_search(query, k=RETRIEVAL_K)
    if not docs:
        def empty():
            yield f"event: token\ndata: {json.dumps({'text': 'No relevant information found.'})}\n\n"
            yield "event: done\ndata: {}\n\n"
        return Response(stream_with_context(empty()), mimetype="text/event-stream")

    context_parts = []
    sources = []
    for d in docs:
        page = d.metadata.get("page", "?")
        try:
            page = int(page) + 1
        except Exception:
            pass
        src = d.metadata.get("source", "?")
        snippet = (d.page_content or "")[:MAX_CHUNK_CHARS]
        context_parts.append(f"[{src}, Page {page}]\n{snippet}")
        sources.append({"file": src, "page": page, "preview": d.page_content[:150]})

    context = "\n\n".join(context_parts)

    history_block = ""
    if history:
        lines = [f"{'User' if h['role']=='user' else 'Assistant'}: {str(h.get('content',''))[:300]}" for h in history]
        history_block = "Conversation:\n" + "\n".join(lines) + "\n\n"

    prompt = f"""{history_block}Document context:
{context}

User question: {query}

Give a helpful, complete answer based on the document context above. Use markdown formatting (headings, bullets) where it improves readability. Cite sources as [file, page]."""

    def generate():
        yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"
        for attempt in range(2):
            emitted = False
            try:
                for text in llm_stream(prompt, max_tokens=MAX_OUTPUT_TOKENS):
                    emitted = True
                    yield f"event: token\ndata: {json.dumps({'text': text})}\n\n"
                yield "event: done\ndata: {}\n\n"
                return
            except Exception as e:
                if is_quota_error(e):
                    yield f"event: error\ndata: {json.dumps({'error': 'Quota reached. Wait 60s.'})}\n\n"
                    return
                if is_auth_error(e):
                    yield f"event: error\ndata: {json.dumps({'error': 'Invalid API key.'})}\n\n"
                    return
                if emitted:
                    yield "event: done\ndata: {}\n\n"
                    return
                print(f"Stream attempt {attempt + 1}/2 failed: {type(e).__name__}: {e}", flush=True)
                time.sleep(2 * (attempt + 1))
        # Streaming failed: fall back to a single non-streaming call
        try:
            full = llm_generate(prompt, max_tokens=MAX_OUTPUT_TOKENS)
            if full.strip():
                yield f"event: token\ndata: {json.dumps({'text': full})}\n\n"
                yield "event: done\ndata: {}\n\n"
                return
        except Exception as e2:
            print(f"Fallback generate failed: {type(e2).__name__}: {e2}", flush=True)
            if is_quota_error(e2):
                yield f"event: error\ndata: {json.dumps({'error': 'Quota reached. Wait 60s.'})}\n\n"
                return
            if is_auth_error(e2):
                yield f"event: error\ndata: {json.dumps({'error': 'Invalid API key.'})}\n\n"
                return
        yield f"event: error\ndata: {json.dumps({'error': 'Model timed out. Please retry.'})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

if __name__ == "__main__":
    prune_old_sessions()
    app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
