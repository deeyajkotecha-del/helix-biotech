"""SatyaBio Analyst — AI-powered clinical data extraction and analysis.

Serves the /extract page with:
- PDF upload → automatic structured brief generation
- Follow-up chat with vision (Claude sees actual page images)
- Clickable page references (p. 7) that show the page image
- Optional RAG cross-document search (requires Neon + Voyage AI)
"""

import os
import re
import uuid
import json
import base64
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.pages import _render_head, get_nav_html

router = APIRouter()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "extraction" / "system_prompt.txt"
try:
    _raw_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    SYSTEM_PROMPT = _raw_prompt.encode("ascii", errors="replace").decode("ascii")
except FileNotFoundError:
    SYSTEM_PROMPT = "You are a biotech investment analyst. Generate a structured brief for the uploaded document."

# In-memory document + history storage keyed by session cookie
_papers: dict = {}   # sid -> {"docs": [...]}
_histories: dict = {}  # sid -> [{"role": ..., "content": ...}]

# Lazy Claude client
_client = None

def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def safe_text(text: str) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    for old, new in {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2014": "--", "\u2013": "-", "\u2026": "...", "\u00b0": " deg",
        "\u00b1": "+/-", "\u2264": "<=", "\u2265": ">=",
        "\u00ae": "(R)", "\u2122": "(TM)", "\u00a9": "(c)",
        "\u00d7": "x", "\u2022": "*", "\u00a0": " ", "\u200b": "", "\ufeff": "",
    }.items():
        text = text.replace(old, new)
    return text.encode("ascii", errors="replace").decode("ascii")


# ---------------------------------------------------------------------------
# PDF processing
# ---------------------------------------------------------------------------

def _extract_text(pdf_path: str) -> str:
    import pdfplumber
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"[Page {i+1}]\n{safe_text(page_text)}\n\n"
    return text.strip() if len(text.strip()) > 100 else "ERROR: Could not extract text from this PDF."


def _extract_page_images(pdf_path: str, max_pages: int = 40) -> list:
    from PIL import Image as PILImage
    import pdfplumber
    images = []
    MAX_DIM = 1500
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                img = page.to_image(resolution=150)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    img.save(tmp.name, format="PNG")
                    pil_img = PILImage.open(tmp.name)
                    w, h = pil_img.size
                    if w > MAX_DIM or h > MAX_DIM:
                        ratio = min(MAX_DIM / w, MAX_DIM / h)
                        pil_img = pil_img.resize((int(w * ratio), int(h * ratio)), PILImage.LANCZOS)
                    jpeg_tmp = tmp.name.replace(".png", ".jpg")
                    pil_img.convert("RGB").save(jpeg_tmp, format="JPEG", quality=85)
                    with open(jpeg_tmp, "rb") as f:
                        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
                    os.unlink(tmp.name)
                    os.unlink(jpeg_tmp)
                images.append({"page": i + 1, "image_base64": image_data, "media_type": "image/jpeg"})
    except Exception as e:
        print(f"  Warning: page image extraction failed: {e}")
    return images


def _get_sid(request: Request) -> str:
    sid = request.cookies.get("analyst_sid")
    if not sid:
        sid = str(uuid.uuid4())
    return sid


def _build_doc_context(sid: str) -> str:
    if sid not in _papers or not _papers[sid]["docs"]:
        return ""
    docs = _papers[sid]["docs"]
    if len(docs) == 1:
        d = docs[0]
        return f"""
--- DOCUMENT TEXT ---
Filename: {d['filename']}
Note: You also have the actual page images above. Use BOTH text AND images.

{safe_text(d['text'])}
--- END ---
"""
    parts = []
    for i, d in enumerate(docs, 1):
        parts.append(f"--- DOCUMENT {i} ---\nFilename: {d['filename']}\n{safe_text(d['text'])}\n--- END {i} ---")
    return "Note: Use BOTH extracted text AND visual page images.\n" + "\n".join(parts)


def _build_messages_with_images(sid: str, user_content: str) -> list:
    history = _histories.get(sid, [])
    if not history:
        return [{"role": "user", "content": user_content}]
    messages, first_user = [], False
    for msg in history:
        if msg["role"] == "user" and not first_user:
            first_user = True
            blocks = []
            if sid in _papers:
                for doc in _papers[sid]["docs"]:
                    for pi in doc.get("page_images", []):
                        blocks.append({"type": "image", "source": {"type": "base64", "media_type": pi["media_type"], "data": pi["image_base64"]}})
            blocks.append({"type": "text", "text": msg["content"]})
            messages.append({"role": "user", "content": blocks})
        else:
            messages.append(msg)
    return messages


def _clean_filename_to_title(fname: str) -> str:
    name = fname.replace(".pdf", "").replace(".PDF", "")
    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', name):
        return ""
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r'\s+', ' ', name).strip()
    if name == name.lower():
        name = name.title()
    return name


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@router.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...), request: Request = None):
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "Please upload a PDF file"})

    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text = _extract_text(tmp_path)
        if text.startswith("ERROR:"):
            return JSONResponse(status_code=400, content={"error": text})
        page_images = _extract_page_images(tmp_path)
        sid = _get_sid(request)
        word_count = len(text.split())
        doc_title = _clean_filename_to_title(file.filename) or file.filename

        _papers[sid] = {"docs": [{"text": text, "filename": file.filename, "title": doc_title, "word_count": word_count, "page_images": page_images}]}
        _histories[sid] = []

        total_pages = len(page_images)
        print(f"  Extracted {word_count} words + {total_pages} page images from {file.filename}")

        resp = JSONResponse(content={
            "success": True, "filename": file.filename, "title": doc_title,
            "word_count": word_count, "total_pages": total_pages,
            "all_titles": [doc_title],
        })
        resp.set_cookie("analyst_sid", sid, max_age=86400, httponly=True, samesite="lax")
        return resp
    finally:
        os.unlink(tmp_path)


@router.post("/api/auto-brief")
async def auto_brief(request: Request):
    sid = _get_sid(request)
    if sid not in _papers or not _papers[sid]["docs"]:
        return JSONResponse(status_code=400, content={"error": "No document loaded."})

    try:
        doc_context = safe_text(_build_doc_context(sid))
        history = _histories.setdefault(sid, [])
        brief_request = "Generate the automatic structured brief for this document as specified in your instructions. Analyze ALL pages including graphs, charts, figures, and visual data."
        history.append({"role": "user", "content": brief_request})
        full_system = safe_text(SYSTEM_PROMPT + "\n" + doc_context)
        messages = _build_messages_with_images(sid, brief_request)

        print(f"  Generating brief ({len(messages)} messages)...")
        response = _get_client().messages.create(model="claude-sonnet-4-20250514", max_tokens=8192, system=full_system, messages=messages)
        assistant_message = safe_text(response.content[0].text)
        history.append({"role": "assistant", "content": assistant_message})
        print(f"  Brief generated ({len(assistant_message)} chars)")

        resp = JSONResponse(content={"brief": assistant_message})
        resp.set_cookie("analyst_sid", sid, max_age=86400, httponly=True, samesite="lax")
        return resp
    except Exception as e:
        print(f"  Brief error: {type(e).__name__}: {e}")
        if history and history[-1].get("role") == "user":
            history.pop()
        return JSONResponse(status_code=500, content={"error": f"Something went wrong: {str(e)}"})


@router.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return JSONResponse(status_code=400, content={"error": "Empty message"})

    sid = _get_sid(request)
    if sid not in _papers or not _papers[sid]["docs"]:
        return JSONResponse(status_code=400, content={"error": "No document uploaded yet."})

    history = _histories.setdefault(sid, [])
    doc_context = safe_text(_build_doc_context(sid))
    full_system = safe_text(f"{SYSTEM_PROMPT}\n{doc_context}")
    history.append({"role": "user", "content": user_message})
    messages = _build_messages_with_images(sid, user_message)

    try:
        response = _get_client().messages.create(model="claude-sonnet-4-20250514", max_tokens=8192, system=full_system, messages=messages)
        assistant_message = safe_text(response.content[0].text)
        history.append({"role": "assistant", "content": assistant_message})
        return JSONResponse(content={"response": assistant_message})
    except Exception as e:
        history.pop()
        return JSONResponse(status_code=500, content={"error": f"Something went wrong: {str(e)}"})


@router.get("/api/page-image/{page_num}")
async def page_image(page_num: int, request: Request):
    sid = _get_sid(request)
    if sid not in _papers:
        return JSONResponse(status_code=400, content={"error": "No document loaded"})
    for doc in _papers[sid]["docs"]:
        for img in doc.get("page_images", []):
            if img["page"] == page_num:
                return JSONResponse(content={"page": page_num, "image_base64": img["image_base64"], "media_type": img["media_type"], "doc_title": doc.get("title", doc["filename"])})
    return JSONResponse(status_code=404, content={"error": f"Page {page_num} not found"})


@router.post("/api/reset")
async def reset(request: Request):
    sid = _get_sid(request)
    _papers.pop(sid, None)
    _histories.pop(sid, None)
    return JSONResponse(content={"success": True})


# ---------------------------------------------------------------------------
# HTML Page
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def serve_extract_page():
    """Serve the SatyaBio Analyst page."""
    return HTMLResponse(content=_generate_extract_page_html())


def _generate_extract_page_html() -> str:
    extra_styles = """
        /* -- Extract page layout -- */
        .extract-body { display: flex; flex: 1; overflow: hidden; height: calc(100vh - 64px); }
        .extract-main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .chat-container {
            flex: 1; overflow-y: auto; padding: 28px 24px;
            display: flex; flex-direction: column; gap: 20px; background: var(--bg);
        }

        /* Upload zone */
        .upload-zone { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 24px; }
        .upload-zone.hidden { display: none; }
        .upload-hero { text-align: center; max-width: 600px; }
        .upload-badge {
            display: inline-block; background: var(--accent-light); color: var(--accent);
            font-size: 12px; font-weight: 600; padding: 6px 18px; border-radius: 20px;
            letter-spacing: 1px; text-transform: uppercase; margin-bottom: 20px;
        }
        .upload-hero h2 { font-family: 'Fraunces', serif; font-size: 36px; font-weight: 700; color: var(--navy); line-height: 1.2; margin-bottom: 14px; }
        .upload-hero p { color: var(--text-secondary); font-size: 16px; line-height: 1.6; }
        .upload-box {
            width: 100%; max-width: 600px; border: 2px dashed var(--border); border-radius: 20px;
            padding: 56px 32px; text-align: center; cursor: pointer; transition: all 0.2s;
            background: #f5f3ef;
        }
        .upload-box:hover, .upload-box.dragover { border-color: var(--accent); background: var(--accent-light); }
        .upload-icon {
            width: 64px; height: 64px; background: var(--accent-light); border-radius: 16px;
            display: inline-flex; align-items: center; justify-content: center; margin-bottom: 16px;
        }
        .upload-box h3 { font-size: 18px; font-weight: 700; color: var(--navy); margin-bottom: 8px; }
        .upload-box p { color: var(--text-secondary); font-size: 14px; }
        .upload-box a { color: var(--accent); font-weight: 600; text-decoration: none; cursor: pointer; }
        .upload-box a:hover { text-decoration: underline; }
        .upload-supported { color: var(--text-muted); font-size: 13px; margin-top: 8px; }

        /* Doc pills (nav bar) */
        .doc-pills { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
        .doc-pill {
            background: var(--accent-light); border: 1px solid #f0d5c8; color: var(--accent);
            padding: 5px 14px; border-radius: 20px; font-size: 12px; font-weight: 500;
            display: flex; align-items: center; gap: 7px;
        }
        .doc-pill .dot { width: 7px; height: 7px; background: #3d8b5e; border-radius: 50%; }
        .doc-pill .remove-doc { cursor: pointer; color: #e0a898; font-size: 15px; line-height: 1; }
        .doc-pill .remove-doc:hover { color: #c0392b; }
        .extract-actions { display: flex; align-items: center; gap: 10px; }
        .extract-actions button {
            background: var(--surface); border: 1px solid var(--border); color: var(--text-muted);
            padding: 6px 14px; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 500;
            font-family: inherit; display: none; transition: all 0.15s;
        }
        .extract-actions button.active { display: inline-flex; align-items: center; gap: 4px; }
        .extract-actions button:hover { border-color: var(--accent); color: var(--accent); }

        /* Messages */
        .message { max-width: 760px; width: 100%; margin: 0 auto; display: flex; gap: 12px; }
        .msg-avatar {
            width: 32px; height: 32px; border-radius: 10px; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
            font-size: 11px; font-weight: 700; letter-spacing: -0.3px;
        }
        .msg-content {
            background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
            padding: 18px 22px; font-size: 14px; line-height: 1.75; flex: 1;
            word-wrap: break-word; color: var(--text-secondary);
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }
        .message.user .msg-content { white-space: pre-wrap; background: #f5f3ef; color: var(--navy); }
        .message.system .msg-content { background: #edf7f0; border-color: #c7e2cf; text-align: center; font-size: 13px; color: #3d8b5e; font-weight: 500; }
        .message.system .msg-avatar { display: none; }
        .message.brief .msg-content { border-left: 4px solid var(--accent); }

        /* Markdown styles */
        .msg-content h1, .msg-content h2, .msg-content h3, .msg-content h4 { margin: 16px 0 8px; line-height: 1.3; color: var(--navy); }
        .msg-content h1 { font-family: 'Fraunces', serif; font-size: 22px; font-weight: 700; border-bottom: 2px solid var(--border); padding-bottom: 8px; }
        .msg-content h2 { font-family: 'Fraunces', serif; font-size: 18px; font-weight: 700; border-bottom: 1px solid #f0ebe4; padding-bottom: 6px; }
        .msg-content h3 { font-size: 15px; font-weight: 600; color: var(--accent); }
        .msg-content h4 { font-size: 14px; font-weight: 600; }
        .msg-content p { margin: 8px 0; }
        .msg-content strong { font-weight: 600; color: var(--navy); }
        .msg-content ul, .msg-content ol { margin: 8px 0; padding-left: 24px; }
        .msg-content li { margin: 4px 0; }
        .msg-content code { background: #f5f3ef; padding: 2px 6px; border-radius: 4px; font-size: 12px; color: var(--accent); }
        .msg-content pre { background: #1a2b3c; color: #e5e5e0; padding: 16px; border-radius: 8px; overflow-x: auto; margin: 12px 0; font-size: 12px; }
        .msg-content pre code { background: none; padding: 0; color: inherit; }
        .msg-content blockquote { border-left: 3px solid var(--accent); padding: 8px 16px; margin: 12px 0; background: var(--bg); color: var(--text-secondary); font-style: italic; }
        .msg-content table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 13px; }
        .msg-content th { background: var(--bg); font-weight: 600; text-align: left; padding: 8px 12px; border: 1px solid var(--border); }
        .msg-content td { padding: 8px 12px; border: 1px solid var(--border); }
        .msg-content hr { border: none; border-top: 1px solid var(--border); margin: 16px 0; }
        .msg-content a { color: var(--accent); text-decoration: none; }
        .msg-content a:hover { text-decoration: underline; }

        /* Page refs */
        .page-ref { color: var(--accent); cursor: pointer; text-decoration: underline dotted; font-weight: 500; }
        .page-ref:hover { text-decoration-style: solid; }

        /* Page modal */
        .page-modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(26,43,60,0.85); z-index: 200; align-items: center; justify-content: center; backdrop-filter: blur(4px); }
        .page-modal.active { display: flex; }
        .page-modal-content { background: var(--surface); border-radius: 16px; max-width: 800px; max-height: 90vh; overflow: auto; padding: 24px; position: relative; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
        .page-modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .page-modal-header h3 { font-size: 16px; font-weight: 600; color: var(--navy); }
        .page-modal-close { background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-muted); padding: 4px 8px; border-radius: 6px; }
        .page-modal-close:hover { background: var(--bg); color: var(--navy); }
        .page-modal-img { width: 100%; border-radius: 8px; border: 1px solid var(--border); }

        /* Typing indicator */
        .typing-indicator { display: none; max-width: 760px; width: 100%; margin: 0 auto; }
        .typing-indicator.active { display: flex; gap: 12px; align-items: flex-start; }
        .typing-card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px 24px; flex: 1; border-left: 4px solid var(--accent); }
        .typing-header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
        .typing-spinner { width: 18px; height: 18px; border: 2.5px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0; }
        .typing-title { font-size: 14px; font-weight: 600; color: var(--navy); }
        .typing-steps { display: flex; flex-direction: column; gap: 8px; }
        .typing-step { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--text-muted); transition: all 0.3s; animation: fadeIn 0.3s ease forwards; }
        .typing-step.active { color: var(--accent); font-weight: 500; }
        .typing-step.done { color: #3d8b5e; }
        .typing-step-icon { width: 20px; height: 20px; border-radius: 50%; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 11px; background: var(--bg); color: var(--text-muted); transition: all 0.3s; }
        .typing-step.active .typing-step-icon { background: var(--accent-light); color: var(--accent); box-shadow: 0 0 0 3px rgba(224,122,95,0.1); }
        .typing-step.done .typing-step-icon { background: #edf7f0; color: #3d8b5e; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

        /* Input bar */
        .input-bar { background: var(--surface); border-top: 1px solid var(--border); padding: 16px 24px; display: none; }
        .input-bar.active { display: block; }
        .input-wrapper { max-width: 760px; margin: 0 auto; display: flex; gap: 10px; }
        .input-wrapper input {
            flex: 1; background: var(--bg); border: 1px solid var(--border); border-radius: 10px;
            padding: 12px 16px; color: var(--navy); font-size: 14px; font-family: inherit; outline: none;
        }
        .input-wrapper input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(224,122,95,0.1); }
        .input-wrapper input::placeholder { color: var(--text-muted); }
        .send-btn {
            background: var(--accent); border: none; border-radius: 10px;
            padding: 12px 22px; color: white; font-size: 14px; font-weight: 600; font-family: inherit;
            cursor: pointer; transition: all 0.15s;
        }
        .send-btn:hover { background: var(--accent-hover); }
        .send-btn:disabled { background: #c0b8ae; cursor: not-allowed; }

        /* Quick actions */
        .quick-actions { max-width: 760px; width: 100%; margin: 0 auto; display: none; gap: 8px; flex-wrap: wrap; }
        .quick-actions.active { display: flex; }
        .quick-action {
            background: var(--surface); border: 1px solid var(--border); color: var(--text-secondary);
            padding: 9px 16px; border-radius: 10px; font-size: 13px; font-weight: 500;
            font-family: inherit; cursor: pointer; transition: all 0.15s;
        }
        .quick-action:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); transform: translateY(-1px); }

        /* Loading */
        .loading-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(253,252,250,0.92); z-index: 100; flex-direction: column; align-items: center; justify-content: center; gap: 16px; backdrop-filter: blur(4px); }
        .loading-overlay.active { display: flex; }
        .load-spinner { width: 36px; height: 36px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
        .loading-overlay p { color: var(--text-secondary); font-size: 14px; font-weight: 500; }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #d0c8be; border-radius: 3px; }

        /* Override footer margin for full-height layout */
        .footer { margin-top: 0 !important; display: none; }
    """

    nav = get_nav_html(active="extract")

    page_html = f"""{_render_head("SatyaBio — Clinical Data Extraction", extra_styles=extra_styles, extra_head='<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.1/marked.min.js"></script>')}

{nav}

<div class="extract-body">
    <div class="extract-main">
        <div class="chat-container" id="chatContainer">
            <div class="upload-zone" id="uploadZone">
                <div class="upload-hero">
                    <span class="upload-badge">AI-Powered Extraction</span>
                    <h2>Clinical Data Extraction</h2>
                    <p>Drop a biotech PDF and watch analyst-grade structured data appear in seconds. Powered by Claude.</p>
                </div>
                <div class="upload-box" id="uploadBox" onclick="document.getElementById('fileInput').click()">
                    <div class="upload-icon">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#e07a5f" stroke-width="1.8">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                        </svg>
                    </div>
                    <h3>Drop a clinical trial PDF here</h3>
                    <p>or <a onclick="event.stopPropagation(); document.getElementById('fileInput').click()">browse files</a> to upload</p>
                    <p class="upload-supported">Posters, publications, corporate decks, FDA labels, press releases</p>
                </div>
            </div>

            <div class="quick-actions" id="quickActions">
                <div class="quick-action" onclick="askQ('What are the key red flags or limitations in this data?')">Red flags?</div>
                <div class="quick-action" onclick="askQ('How does this compare to standard of care?')">vs. Standard of care</div>
                <div class="quick-action" onclick="askQ('Walk me through the trial design and any weaknesses.')">Trial design critique</div>
                <div class="quick-action" onclick="askQ('What are the key upcoming catalysts and investment implications?')">Investment thesis</div>
                <div class="quick-action" onclick="askQ('Summarize the safety and tolerability profile.')">Safety profile</div>
                <div class="quick-action" onclick="askQ('Describe the PK/PD profile and what the graphs show.')">PK/PD analysis</div>
            </div>

            <div class="typing-indicator" id="typingIndicator">
                <div class="msg-avatar" style="background:var(--accent);color:white;font-size:10px">SB</div>
                <div class="typing-card">
                    <div class="typing-header"><div class="typing-spinner"></div><span class="typing-title" id="typingTitle">Analyzing...</span></div>
                    <div class="typing-steps" id="typingSteps"></div>
                </div>
            </div>
        </div>

        <div class="input-bar" id="inputBar">
            <div class="input-wrapper">
                <input type="text" id="messageInput" placeholder="Ask about the document..." onkeydown="if(event.key==='Enter'&&!event.shiftKey)sendMessage()">
                <button class="send-btn" id="sendBtn" onclick="sendMessage()">Send</button>
            </div>
        </div>

        <input type="file" id="fileInput" accept=".pdf" style="display:none" onchange="handleFileUpload(this.files[0])">
    </div>
</div>

<div class="loading-overlay" id="loadingOverlay">
    <div class="load-spinner"></div>
    <p id="loadingText">Extracting text...</p>
</div>

<div class="page-modal" id="pageModal" onclick="if(event.target===this)closePageModal()">
    <div class="page-modal-content">
        <div class="page-modal-header">
            <h3 id="pageModalTitle">Page 1</h3>
            <button class="page-modal-close" onclick="closePageModal()">&times;</button>
        </div>
        <img class="page-modal-img" id="pageModalImg" src="" alt="Page">
    </div>
</div>

<script>
marked.setOptions({{ breaks: true, gfm: true, headerIds: false, mangle: false }});

function renderMd(text) {{
    try {{
        let html = marked.parse(text);
        html = html.replace(/\\(p\\.?\\s*(\\d+)(?:\\s*[-\\u2013]\\s*(\\d+))?\\)/gi, function(m, p1, p2) {{
            return p2 ? '(<span class="page-ref" onclick="showPage('+p1+')">p. '+p1+'-'+p2+'</span>)' : '(<span class="page-ref" onclick="showPage('+p1+')">p. '+p1+'</span>)';
        }});
        return html;
    }} catch(e) {{ return esc(text); }}
}}

async function showPage(n) {{
    try {{
        const r = await fetch('/extract/api/page-image/'+n);
        const d = await r.json();
        if(d.error){{ alert(d.error); return; }}
        document.getElementById('pageModalTitle').textContent='Page '+n+' \\u2014 '+d.doc_title;
        document.getElementById('pageModalImg').src='data:'+d.media_type+';base64,'+d.image_base64;
        document.getElementById('pageModal').classList.add('active');
    }} catch(e){{ alert('Could not load page'); }}
}}
function closePageModal(){{ document.getElementById('pageModal').classList.remove('active'); }}

let loadedDocs = [];
const uploadBox = document.getElementById('uploadBox');
uploadBox.addEventListener('dragover', e => {{ e.preventDefault(); uploadBox.classList.add('dragover'); }});
uploadBox.addEventListener('dragleave', () => uploadBox.classList.remove('dragover'));
uploadBox.addEventListener('drop', e => {{ e.preventDefault(); uploadBox.classList.remove('dragover'); if(e.dataTransfer.files[0]) handleFileUpload(e.dataTransfer.files[0]); }});

async function handleFileUpload(file) {{
    if(!file.name.toLowerCase().endsWith('.pdf')){{ alert('Please upload a PDF file.'); return; }}
    const overlay = document.getElementById('loadingOverlay');
    overlay.classList.add('active');
    document.getElementById('loadingText').textContent='Reading "'+file.name+'"...';
    const fd = new FormData(); fd.append('file', file);
    try {{
        const r = await fetch('/extract/api/upload', {{ method: 'POST', body: fd }});
        const d = await r.json();
        if(d.error){{ alert(d.error); return; }}
        loadedDocs = d.all_titles || [d.title || d.filename];
        document.getElementById('uploadZone').classList.add('hidden');
        document.getElementById('inputBar').classList.add('active');
        const pages = d.total_pages || '?';
        addMsg('system', 'Loaded "'+( d.title||d.filename)+'" \\u2014 '+d.word_count.toLocaleString()+' words, '+pages+' pages extracted.');
        overlay.classList.remove('active');
        await generateBrief();
    }} catch(e){{ alert('Upload failed: '+e.message); }} finally {{ overlay.classList.remove('active'); document.getElementById('fileInput').value=''; }}
}}

const briefSteps = [
    {{ label:'Reading document text and images', delay:0 }},
    {{ label:'Analyzing clinical data and endpoints', delay:2500 }},
    {{ label:'Evaluating graphs, KM curves, and figures', delay:5500 }},
    {{ label:'Assessing competitive landscape', delay:9000 }},
    {{ label:'Generating investment-grade brief', delay:13000 }},
];
const chatSteps = [{{ label:'Reviewing document context', delay:0 }}, {{ label:'Formulating response', delay:2000 }}];
let stepTimers = [];

function showProgress(title, steps) {{
    const typing = document.getElementById('typingIndicator');
    document.getElementById('typingTitle').textContent = title;
    const el = document.getElementById('typingSteps'); el.innerHTML = '';
    stepTimers.forEach(t => clearTimeout(t)); stepTimers = [];
    steps.forEach((s,i) => {{
        const d = document.createElement('div'); d.className='typing-step'; d.id='ps-'+i;
        d.innerHTML='<span class="typing-step-icon">'+(i+1)+'</span><span>'+s.label+'</span>';
        el.appendChild(d);
    }});
    steps.forEach((s,i) => {{
        stepTimers.push(setTimeout(() => {{
            for(let j=0;j<i;j++){{ const p=document.getElementById('ps-'+j); if(p){{ p.className='typing-step done'; p.querySelector('.typing-step-icon').textContent='\\u2713'; }} }}
            const c=document.getElementById('ps-'+i); if(c) c.className='typing-step active';
        }}, s.delay));
    }});
    typing.classList.add('active'); scrollBot();
}}
function hideProgress() {{ stepTimers.forEach(t=>clearTimeout(t)); stepTimers=[]; document.getElementById('typingIndicator').classList.remove('active'); }}

async function generateBrief() {{
    showProgress('Generating structured brief...', briefSteps);
    try {{
        const r = await fetch('/extract/api/auto-brief', {{ method:'POST', headers:{{'Content-Type':'application/json'}} }});
        const d = await r.json(); hideProgress();
        if(d.error){{ addMsg('system','Could not generate brief: '+d.error); }}
        else {{ addMsg('brief',d.brief); document.getElementById('quickActions').classList.add('active'); }}
    }} catch(e){{ hideProgress(); addMsg('system','Brief failed: '+e.message); }}
    document.getElementById('messageInput').focus();
}}

async function sendMessage() {{
    const inp = document.getElementById('messageInput');
    const msg = inp.value.trim(); if(!msg) return;
    document.getElementById('quickActions').classList.remove('active');
    addMsg('user', msg); inp.value=''; inp.disabled=true;
    document.getElementById('sendBtn').disabled=true;
    showProgress('Thinking...', chatSteps);
    try {{
        const r = await fetch('/extract/api/chat', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{message:msg}}) }});
        const d = await r.json(); hideProgress();
        if(d.error){{ addMsg('system',d.error); }} else {{ addMsg('assistant',d.response); }}
    }} catch(e){{ hideProgress(); addMsg('system','Request failed: '+e.message); }}
    finally {{ inp.disabled=false; document.getElementById('sendBtn').disabled=false; inp.focus(); }}
}}

function askQ(q) {{ document.getElementById('messageInput').value=q; sendMessage(); }}

function addMsg(role, content) {{
    const c = document.getElementById('chatContainer');
    const qa = document.getElementById('quickActions');
    const m = document.createElement('div'); m.className='message '+role;
    const rendered = (role==='assistant'||role==='brief') ? renderMd(content) : esc(content);
    if(role==='system'){{ m.innerHTML='<div class="msg-content">'+rendered+'</div>'; }}
    else if(role==='brief'){{ m.className='message assistant brief'; m.innerHTML='<div class="msg-avatar" style="background:var(--accent);color:white;font-size:10px">SB</div><div class="msg-content">'+rendered+'</div>'; }}
    else {{ const av=role==='user'?'You':'SB'; const st=role==='user'?'background:#1a2b3c;color:white;font-size:10px':'background:var(--accent);color:white;font-size:10px'; m.innerHTML='<div class="msg-avatar" style="'+st+'">'+av+'</div><div class="msg-content">'+rendered+'</div>'; }}
    c.insertBefore(m, qa); scrollBot();
}}

function esc(t) {{ const d=document.createElement('div'); d.textContent=t; return d.innerHTML; }}
function scrollBot() {{ const c=document.getElementById('chatContainer'); c.scrollTop=c.scrollHeight; }}

document.addEventListener('keydown', e => {{ if(e.key==='Escape') closePageModal(); }});
</script>
</body></html>"""

    return page_html
