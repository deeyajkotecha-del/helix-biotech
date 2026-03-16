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

# RAG search (optional — works without it if Neon/Voyage not configured)
try:
    import sys
    _extraction_dir = str(Path(__file__).resolve().parent.parent.parent / "extraction")
    if _extraction_dir not in sys.path:
        sys.path.insert(0, _extraction_dir)
    import rag_search
    _RAG_AVAILABLE = rag_search.is_rag_available()
except (ImportError, Exception):
    _RAG_AVAILABLE = False

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
# RAG Search Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/rag-status")
async def rag_status():
    if not _RAG_AVAILABLE:
        return JSONResponse(content={"available": False})
    stats = rag_search.get_library_stats()
    return JSONResponse(content={"available": True, **stats})


@router.get("/api/library")
async def library_list():
    """Return all documents grouped by company for the sidebar."""
    if not _RAG_AVAILABLE:
        return JSONResponse(content={"companies": []})
    docs = rag_search.get_document_library()
    companies = {}
    for d in docs:
        ticker = d["ticker"]
        if ticker not in companies:
            companies[ticker] = {"ticker": ticker, "company_name": d["company_name"], "documents": []}
        companies[ticker]["documents"].append(d)
    return JSONResponse(content={"companies": list(companies.values())})


@router.post("/api/load-library-doc")
async def load_library_doc(request: Request):
    """Load a document from the library into the chat session via its chunks."""
    if not _RAG_AVAILABLE:
        return JSONResponse(status_code=400, content={"error": "Library not available"})
    data = await request.json()
    doc_id = data.get("doc_id")
    doc_title = data.get("title", "Document")
    if not doc_id:
        return JSONResponse(status_code=400, content={"error": "No doc_id provided"})
    chunks = rag_search.get_document_chunks(doc_id)
    if not chunks:
        return JSONResponse(status_code=404, content={"error": "No content found for this document"})
    full_text = ""
    for c in chunks:
        full_text += f"[Page {c['page']}]\n{safe_text(c['content'])}\n\n"
    sid = _get_sid(request)
    _papers[sid] = {"docs": [{"text": full_text, "filename": doc_title, "title": doc_title, "word_count": len(full_text.split()), "page_images": []}]}
    _histories[sid] = []
    resp = JSONResponse(content={
        "success": True, "title": doc_title,
        "word_count": len(full_text.split()),
        "total_pages": len(set(c["page"] for c in chunks)),
    })
    resp.set_cookie("analyst_sid", sid, max_age=86400, httponly=True, samesite="lax")
    return resp


@router.post("/api/rag-search")
async def rag_search_route(request: Request):
    if not _RAG_AVAILABLE:
        return JSONResponse(status_code=400, content={"error": "RAG search not configured."})
    data = await request.json()
    query = data.get("query", "").strip()
    ticker = data.get("ticker", None)
    if not query:
        return JSONResponse(status_code=400, content={"error": "Empty query"})

    results = rag_search.search(query, top_k=12, ticker_filter=ticker)
    if not results:
        return JSONResponse(content={"response": "No relevant results found in the document library.", "sources": []})

    rag_context = rag_search.format_context_for_claude(results)
    rag_system = f"""{SYSTEM_PROMPT}

IMPORTANT: You are answering a CROSS-DOCUMENT question using search results from the full document library.
Always cite the source document (ticker, filename, page number) for every claim.

{rag_context}"""

    try:
        response = _get_client().messages.create(model="claude-sonnet-4-20250514", max_tokens=4096, system=rag_system, messages=[{"role": "user", "content": query}])
        answer = response.content[0].text
        seen = set()
        sources = []
        for r in results:
            key = f"{r['ticker']}:{r['filename']}"
            if key not in seen:
                seen.add(key)
                # Build a clean display title — avoid showing UUIDs
                display = r.get("title") or r.get("filename") or ""
                # If title looks like a UUID, try to clean the filename instead
                if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-', display):
                    display = r.get("filename", display)
                # Clean up filename into readable form
                display = display.replace(".pdf", "").replace(".PDF", "")
                display = display.replace("_", " ").replace("-", " ")
                display = re.sub(r'\s+', ' ', display).strip()
                if len(display) > 60:
                    display = display[:57] + "..."
                doc_type = r.get("doc_type", "document")
                sources.append({"ticker": r["ticker"], "company": r["company_name"], "display_title": display, "doc_type": doc_type})
        return JSONResponse(content={"response": answer, "sources": sources})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Search failed: {str(e)}"})


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

        /* Sidebar */
        .doc-sidebar {
            width: 300px; min-width: 300px; background: var(--surface); border-right: 1px solid var(--border);
            display: flex; flex-direction: column; overflow: hidden;
        }
        .sidebar-header {
            padding: 18px 20px 14px; border-bottom: 1px solid var(--border);
        }
        .sidebar-header h3 {
            font-family: 'Fraunces', serif; font-size: 15px; font-weight: 700;
            color: var(--navy); margin-bottom: 10px;
        }
        .sidebar-search {
            width: 100%; background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
            padding: 8px 12px; font-size: 13px; font-family: inherit; color: var(--navy); outline: none;
        }
        .sidebar-search:focus { border-color: var(--accent); }
        .sidebar-search::placeholder { color: var(--text-muted); }
        .sidebar-list { flex: 1; overflow-y: auto; padding: 8px 0; }
        .sidebar-company {
            padding: 0 12px; margin-bottom: 4px;
        }
        .sidebar-company-header {
            display: flex; align-items: center; gap: 8px; padding: 8px 8px;
            cursor: pointer; border-radius: 8px; transition: background 0.15s;
            user-select: none;
        }
        .sidebar-company-header:hover { background: var(--bg); }
        .sidebar-company-ticker {
            background: var(--accent-light); color: var(--accent); font-size: 11px; font-weight: 700;
            padding: 3px 8px; border-radius: 6px; letter-spacing: 0.5px;
        }
        .sidebar-company-name {
            font-size: 13px; font-weight: 600; color: var(--navy); flex: 1;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .sidebar-company-count {
            font-size: 11px; color: var(--text-muted); background: var(--bg);
            padding: 2px 7px; border-radius: 10px;
        }
        .sidebar-company-arrow {
            font-size: 10px; color: var(--text-muted); transition: transform 0.2s;
        }
        .sidebar-company.open .sidebar-company-arrow { transform: rotate(90deg); }
        .sidebar-docs { display: none; padding: 2px 0 6px 16px; }
        .sidebar-company.open .sidebar-docs { display: block; }
        .sidebar-doc {
            display: flex; flex-direction: column; gap: 2px;
            padding: 8px 10px; border-radius: 8px; cursor: pointer;
            transition: all 0.15s; border-left: 2px solid transparent;
        }
        .sidebar-doc:hover { background: var(--bg); border-left-color: var(--accent); }
        .sidebar-doc.active { background: var(--accent-light); border-left-color: var(--accent); }
        .sidebar-doc-title {
            font-size: 12.5px; font-weight: 500; color: var(--navy); line-height: 1.3;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
        }
        .sidebar-doc-meta {
            font-size: 11px; color: var(--text-muted); display: flex; gap: 8px; align-items: center;
        }
        .sidebar-doc-type {
            background: #edf7f0; color: #3d8b5e; font-size: 10px; font-weight: 500;
            padding: 1px 6px; border-radius: 4px;
        }
        .sidebar-loading {
            display: flex; align-items: center; justify-content: center; padding: 40px 20px;
            color: var(--text-muted); font-size: 13px; gap: 10px;
        }
        .sidebar-empty {
            padding: 40px 20px; text-align: center; color: var(--text-muted); font-size: 13px;
        }
        @media (max-width: 768px) {
            .doc-sidebar { display: none; }
        }
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

        /* RAG Search */
        .search-section { width: 100%; max-width: 600px; margin-top: 8px; }
        .search-divider { display: flex; align-items: center; gap: 16px; margin: 8px 0 16px; }
        .search-divider::before, .search-divider::after { content: ''; flex: 1; height: 1px; background: var(--border); }
        .search-divider span { color: var(--text-muted); font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; }
        .search-bar {
            display: flex; gap: 8px; width: 100%;
        }
        .search-bar input {
            flex: 1; background: #f5f3ef; border: 2px solid var(--border); border-radius: 12px;
            padding: 14px 18px; font-size: 14px; font-family: inherit; color: var(--navy); outline: none;
            transition: all 0.2s;
        }
        .search-bar input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(224,122,95,0.1); background: white; }
        .search-bar input::placeholder { color: var(--text-muted); }
        .search-bar button {
            background: var(--accent); border: none; border-radius: 12px; padding: 14px 22px;
            color: white; font-size: 14px; font-weight: 600; font-family: inherit;
            cursor: pointer; transition: all 0.15s; white-space: nowrap;
        }
        .search-bar button:hover { background: var(--accent-hover); }
        .search-bar button:disabled { background: #c0b8ae; cursor: not-allowed; }
        .rag-badge {
            display: inline-flex; align-items: center; gap: 6px;
            font-size: 12px; color: var(--text-muted); margin-top: 8px;
        }
        .rag-badge .rag-dot { width: 6px; height: 6px; border-radius: 50%; background: #3d8b5e; }
        .rag-badge.unavailable .rag-dot { background: #c0b8ae; }
        .suggested-queries { margin-top: 14px; display: flex; flex-direction: column; gap: 8px; }
        .sq-row { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
        .sq-chip {
            background: var(--surface); border: 1px solid var(--border); color: var(--text-secondary);
            padding: 8px 14px; border-radius: 10px; font-size: 12.5px; font-weight: 500;
            font-family: inherit; cursor: pointer; transition: all 0.15s;
        }
        .sq-chip:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); transform: translateY(-1px); }

        /* RAG search results */
        .rag-results { max-width: 760px; width: 100%; margin: 0 auto; }
        .rag-result-card {
            background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
            padding: 18px 22px; margin-bottom: 12px; border-left: 4px solid #5b8a72;
        }
        .rag-result-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
        .rag-result-query { font-family: 'Fraunces', serif; font-size: 16px; font-weight: 600; color: var(--navy); }
        .rag-sources { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
        .rag-source-tag {
            background: #edf7f0; color: #3d8b5e; font-size: 11px; font-weight: 500;
            padding: 4px 10px; border-radius: 12px; border: 1px solid #c7e2cf;
        }
        .rag-source-card {
            background: var(--bg); border: 1px solid var(--border); border-radius: 10px;
            padding: 10px 14px; display: flex; flex-direction: column; gap: 3px;
            min-width: 180px; flex: 1; max-width: 280px;
        }
        .rag-source-ticker {
            font-size: 11px; font-weight: 700; color: var(--accent);
            letter-spacing: 0.5px;
        }
        .rag-source-title {
            font-size: 12.5px; font-weight: 500; color: var(--navy); line-height: 1.3;
        }
        .rag-source-company {
            font-size: 11px; color: var(--text-muted);
        }
        .rag-source-type {
            font-size: 10px; color: #3d8b5e; background: #edf7f0;
            padding: 2px 8px; border-radius: 6px; align-self: flex-start;
            font-weight: 500; margin-top: 2px;
        }

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
    <div class="doc-sidebar" id="docSidebar">
        <div class="sidebar-header">
            <h3>Document Library</h3>
            <input type="text" class="sidebar-search" id="sidebarSearch" placeholder="Filter documents..." oninput="filterSidebar(this.value)">
        </div>
        <div class="sidebar-list" id="sidebarList">
            <div class="sidebar-loading" id="sidebarLoading">
                <div class="typing-spinner"></div> Loading library...
            </div>
        </div>
    </div>
    <div class="extract-main">
        <div class="chat-container" id="chatContainer">
            <div class="upload-zone" id="uploadZone">
                <div class="upload-hero">
                    <span class="upload-badge">AI-Powered Extraction</span>
                    <h2>Clinical Data Extraction</h2>
                    <p>Drop a biotech PDF and watch analyst-grade structured data appear in seconds. Powered by Claude.</p>
                </div>
                <div class="search-section" id="ragSection" style="display:none;">
                    <div class="search-divider"><span>Search document library</span></div>
                    <div class="search-bar">
                        <input type="text" id="ragInput" placeholder="e.g. What ADCs are showing ORR above 40%?" onkeydown="if(event.key==='Enter')runRagSearch()">
                        <button id="ragBtn" onclick="runRagSearch()">Search</button>
                    </div>
                    <div class="rag-badge" id="ragBadge"><span class="rag-dot"></span><span id="ragBadgeText">Loading library...</span></div>
                    <div class="suggested-queries" id="suggestedQueries" style="display:none;">
                        <div class="sq-row">
                            <div class="sq-chip" onclick="suggestedSearch('What are the most promising HER2+ breast cancer drugs in development?')">HER2+ Breast Cancer</div>
                            <div class="sq-chip" onclick="suggestedSearch('Compare ADC clinical data across all companies — ORR, DOR, safety')">ADC Landscape</div>
                            <div class="sq-chip" onclick="suggestedSearch('What are the latest NMIBC clinical trial results and how do they compare?')">NMIBC Trials</div>
                        </div>
                        <div class="sq-row">
                            <div class="sq-chip" onclick="suggestedSearch('Which drugs have the best overall survival data in late-stage trials?')">Best OS Data</div>
                            <div class="sq-chip" onclick="suggestedSearch('What checkpoint inhibitor combinations are being tested?')">IO Combos</div>
                            <div class="sq-chip" onclick="suggestedSearch('Summarize the key upcoming catalysts and FDA decision dates')">Upcoming Catalysts</div>
                        </div>
                        <div class="sq-row">
                            <div class="sq-chip" onclick="suggestedSearch('What bispecific antibodies are in clinical development and what are their targets?')">Bispecifics</div>
                            <div class="sq-chip" onclick="suggestedSearch('Compare PFS and ORR data for triple-negative breast cancer treatments')">TNBC Data</div>
                            <div class="sq-chip" onclick="suggestedSearch('What are the key safety signals and dose-limiting toxicities reported?')">Safety Signals</div>
                        </div>
                    </div>
                    <div class="search-divider" style="margin-top:20px;"><span>Or upload a new document</span></div>
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

// ── RAG Cross-Document Search ──
let ragAvailable = false;
let ragDocCount = 0;

async function checkRagStatus() {{
    try {{
        const r = await fetch('/extract/api/rag-status');
        const d = await r.json();
        const section = document.getElementById('ragSection');
        const badge = document.getElementById('ragBadge');
        const badgeText = document.getElementById('ragBadgeText');
        if (d.available) {{
            ragAvailable = true;
            ragDocCount = d.total_documents || 0;
            section.style.display = 'block';
            badgeText.textContent = ragDocCount + ' documents indexed and searchable';
            document.getElementById('suggestedQueries').style.display = 'flex';
        }} else {{
            // Still show the section but indicate unavailable
            section.style.display = 'block';
            badge.classList.add('unavailable');
            badgeText.textContent = 'Document library not configured';
            document.getElementById('ragInput').placeholder = 'Library search unavailable — upload a PDF instead';
            document.getElementById('ragInput').disabled = true;
            document.getElementById('ragBtn').disabled = true;
        }}
    }} catch(e) {{
        // Silently fail — just hide the search section
        document.getElementById('ragSection').style.display = 'none';
    }}
}}

function suggestedSearch(query) {{
    document.getElementById('ragInput').value = query;
    runRagSearch();
}}

const ragSteps = [
    {{ label: 'Embedding query with Voyage AI', delay: 0 }},
    {{ label: 'Searching across document library', delay: 1500 }},
    {{ label: 'Ranking relevant passages', delay: 3000 }},
    {{ label: 'Synthesizing answer with Claude', delay: 4500 }},
];

async function runRagSearch() {{
    const inp = document.getElementById('ragInput');
    const query = inp.value.trim();
    if (!query || !ragAvailable) return;

    // Switch to chat view
    document.getElementById('uploadZone').classList.add('hidden');
    document.getElementById('inputBar').classList.add('active');

    // Show user's question
    addMsg('user', query);
    inp.value = '';

    // Show progress
    showProgress('Searching ' + ragDocCount + ' documents...', ragSteps);
    document.getElementById('messageInput').disabled = true;
    document.getElementById('sendBtn').disabled = true;

    try {{
        const r = await fetch('/extract/api/rag-search', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ query: query }})
        }});
        const d = await r.json();
        hideProgress();

        if (d.error) {{
            addMsg('system', 'Search error: ' + d.error);
        }} else {{
            // Add the answer as a brief-style message
            addMsg('brief', d.response);

            // Show source documents
            if (d.sources && d.sources.length > 0) {{
                let srcHtml = '<div class="rag-result-card">';
                srcHtml += '<div class="rag-result-header"><span class="rag-result-query">Sources (' + d.sources.length + ' documents)</span></div>';
                srcHtml += '<div class="rag-sources">';
                d.sources.forEach(s => {{
                    const title = s.display_title || s.title || s.filename || 'Document';
                    const docType = s.doc_type || 'document';
                    srcHtml += '<div class="rag-source-card">';
                    srcHtml += '<span class="rag-source-ticker">' + esc(s.ticker || '') + '</span>';
                    srcHtml += '<span class="rag-source-title">' + esc(title) + '</span>';
                    if (s.company) srcHtml += '<span class="rag-source-company">' + esc(s.company) + '</span>';
                    srcHtml += '<span class="rag-source-type">' + esc(docType) + '</span>';
                    srcHtml += '</div>';
                }});
                srcHtml += '</div></div>';
                const c = document.getElementById('chatContainer');
                const qa = document.getElementById('quickActions');
                const div = document.createElement('div');
                div.className = 'rag-results';
                div.innerHTML = srcHtml;
                c.insertBefore(div, qa);
                scrollBot();
            }}
        }}
    }} catch(e) {{
        hideProgress();
        addMsg('system', 'Search failed: ' + e.message);
    }} finally {{
        document.getElementById('messageInput').disabled = false;
        document.getElementById('sendBtn').disabled = false;
        document.getElementById('messageInput').focus();
    }}
}}

// Check RAG on load
checkRagStatus();

// ── Document Library Sidebar ──
let libraryData = [];

async function loadLibrary() {{
    try {{
        const r = await fetch('/extract/api/library');
        const d = await r.json();
        libraryData = d.companies || [];
        renderSidebar(libraryData);
    }} catch(e) {{
        document.getElementById('sidebarLoading').innerHTML = '<div class="sidebar-empty">Could not load library</div>';
    }}
}}

function renderSidebar(companies) {{
    const list = document.getElementById('sidebarList');
    if (!companies.length) {{
        list.innerHTML = '<div class="sidebar-empty">No documents in library</div>';
        return;
    }}
    let html = '';
    companies.forEach((co, ci) => {{
        const docCount = co.documents.length;
        html += '<div class="sidebar-company" id="co-' + ci + '">';
        html += '<div class="sidebar-company-header" onclick="toggleCompany(' + ci + ')">';
        html += '<span class="sidebar-company-arrow">&#9654;</span>';
        html += '<span class="sidebar-company-ticker">' + esc(co.ticker) + '</span>';
        html += '<span class="sidebar-company-name">' + esc(co.company_name) + '</span>';
        html += '<span class="sidebar-company-count">' + docCount + '</span>';
        html += '</div>';
        html += '<div class="sidebar-docs">';
        co.documents.forEach(doc => {{
            const docType = doc.doc_type || 'document';
            html += '<div class="sidebar-doc" data-id="' + doc.id + '" data-title="' + esc(doc.title || doc.filename) + '" onclick="loadLibraryDoc(' + doc.id + ', this)">';
            html += '<span class="sidebar-doc-title">' + esc(doc.title || doc.filename) + '</span>';
            html += '<div class="sidebar-doc-meta"><span class="sidebar-doc-type">' + esc(docType) + '</span></div>';
            html += '</div>';
        }});
        html += '</div></div>';
    }});
    list.innerHTML = html;
}}

function toggleCompany(idx) {{
    const el = document.getElementById('co-' + idx);
    if (el) el.classList.toggle('open');
}}

function filterSidebar(query) {{
    const q = query.toLowerCase();
    if (!q) {{ renderSidebar(libraryData); return; }}
    const filtered = libraryData.map(co => {{
        const matchDocs = co.documents.filter(d =>
            (d.title || d.filename || '').toLowerCase().includes(q) ||
            (d.ticker || '').toLowerCase().includes(q) ||
            (co.company_name || '').toLowerCase().includes(q) ||
            (d.doc_type || '').toLowerCase().includes(q)
        );
        if (!matchDocs.length) return null;
        return {{ ...co, documents: matchDocs }};
    }}).filter(Boolean);
    renderSidebar(filtered);
    // Auto-open all companies when filtering
    filtered.forEach((_, i) => {{
        const el = document.getElementById('co-' + i);
        if (el) el.classList.add('open');
    }});
}}

async function loadLibraryDoc(docId, el) {{
    // Highlight active doc
    document.querySelectorAll('.sidebar-doc').forEach(d => d.classList.remove('active'));
    if (el) el.classList.add('active');
    const title = el ? el.dataset.title : 'Document';

    const overlay = document.getElementById('loadingOverlay');
    overlay.classList.add('active');
    document.getElementById('loadingText').textContent = 'Loading "' + title + '" from library...';

    try {{
        const r = await fetch('/extract/api/load-library-doc', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ doc_id: docId, title: title }})
        }});
        const d = await r.json();
        if (d.error) {{ alert(d.error); overlay.classList.remove('active'); return; }}

        // Clear previous chat
        const container = document.getElementById('chatContainer');
        container.querySelectorAll('.message, .rag-results').forEach(m => m.remove());

        loadedDocs = [title];
        document.getElementById('uploadZone').classList.add('hidden');
        document.getElementById('inputBar').classList.add('active');
        document.getElementById('quickActions').classList.remove('active');

        addMsg('system', 'Loaded "' + title + '" from library \\u2014 ' + d.word_count.toLocaleString() + ' words, ' + d.total_pages + ' pages. Note: page images are not available for library documents.');
        overlay.classList.remove('active');
        await generateBrief();
    }} catch(e) {{
        alert('Failed to load document: ' + e.message);
        overlay.classList.remove('active');
    }}
}}

// Load library on page load
loadLibrary();
</script>
</body></html>"""

    return page_html
