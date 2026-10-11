# ✅ Auto-Delete Feature Implemented

## What Changed

### 📁 Files are now stored in TEMPORARY directory
- **Before:** `data/uploads/` (permanent storage)
- **After:** System temp folder (e.g., `/tmp/rag_temp_xxxxx/`)
- **Auto-deleted:** When app closes OR user closes browser

### 🧹 Cleanup Triggers

1. **User closes browser tab/window** → Files deleted immediately
2. **User clicks "Clear" button** → Files deleted immediately  
3. **Server shuts down** (Ctrl+C) → All temp files deleted
4. **Page refresh** → Old session files deleted, new ones created

### 🔧 Technical Implementation

**Backend (`app.py`):**
```python
import tempfile
import atexit
import shutil

# Create temp directory
TEMP_DIR = tempfile.mkdtemp(prefix="rag_temp_")

# Auto-cleanup on shutdown
def cleanup_all():
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

atexit.register(cleanup_all)

# Per-session cleanup
@app.route("/cleanup", methods=["POST"])
def cleanup():
    cleanup_session(sid)
```

**Frontend (`index.html`):**
```javascript
window.addEventListener("beforeunload", () => {
  navigator.sendBeacon("/cleanup");
});
```

## 📊 File Lifecycle

```
User uploads PDF
    ↓
Stored in: /tmp/rag_temp_abc123/{session_id}/file.pdf
    ↓
User chats with document
    ↓
User closes browser OR clicks "Clear"
    ↓
🧹 Files automatically deleted!
```

## ✅ Benefits

- ✅ **No storage clutter** - Files never accumulate
- ✅ **Privacy** - Documents deleted after use
- ✅ **No manual cleanup needed** - Fully automatic
- ✅ **Server restart safe** - Temp files always cleaned

## 🔒 Security Notes

- Files stored in system temp directory (usually `/tmp/` on Mac/Linux)
- Each user session gets unique folder
- Files deleted within seconds of browser close
- No permanent storage anywhere

## 🧪 Test It Yourself

1. Start app: `python app.py`
2. Upload a PDF
3. Check temp folder location (shown in terminal)
4. Close browser tab
5. See terminal message: "🧹 Cleaning up temporary directory..."
6. Files are gone! ✅

---

**Your RAG app is now fully ephemeral - no traces left behind!** 🎉
