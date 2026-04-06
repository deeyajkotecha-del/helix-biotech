"""
Webcast Pipeline Endpoints — transcribe, ingest, search, library
Split from evidence.py for maintainability.

Supports:
  - Audio file upload → Whisper transcription → RAG embedding
  - Direct transcript paste → RAG embedding
  - URL-based audio download (yt-dlp) → Whisper → RAG
  - MediaRecorder JS bookmarklet for browser audio capture
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/webcasts", tags=["webcasts"])

# ---------------------------------------------------------------------------
# Lazy-load the webcast pipeline
# ---------------------------------------------------------------------------

_SEARCH_DIR = str(Path(__file__).resolve().parent.parent.parent / "backend" / "services" / "search")
if _SEARCH_DIR not in sys.path:
    sys.path.insert(0, _SEARCH_DIR)

try:
    from webcast_pipeline import (
        get_webcast_status,
        process_webcast,
        search_webcasts,
        list_webcasts,
        get_webcast_transcript,
        ingest_webcast,
        get_media_recorder_js,
        get_registration_js,
    )
    WEBCAST_READY = True
except ImportError as e:
    print(f"  [webcasts] Webcast pipeline not available: {e}")
    get_webcast_status = None
    process_webcast = None
    search_webcasts = None
    list_webcasts = None
    get_webcast_transcript = None
    ingest_webcast = None
    get_media_recorder_js = None
    get_registration_js = None
    WEBCAST_READY = False


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class WebcastProcessRequest(BaseModel):
    audio_path: Optional[str] = None
    url: Optional[str] = None
    title: str = ""
    ticker: str = ""
    company_name: str = ""
    event_date: str = ""
    event_type: str = "webcast"


class WebcastSearchRequest(BaseModel):
    query: str
    ticker: Optional[str] = None
    top_k: int = 10


class WebcastIngestRequest(BaseModel):
    transcript_text: str
    title: str = ""
    ticker: str = ""
    company_name: str = ""
    event_date: str = ""
    event_type: str = "webcast"
    source_url: str = ""
    duration_seconds: float = 0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def webcast_pipeline_status():
    """Check readiness of the webcast transcription pipeline."""
    if not WEBCAST_READY:
        return JSONResponse({"ready": False, "error": "Webcast module not loaded"})
    return JSONResponse(get_webcast_status())


@router.post("/process")
async def webcast_process(request: WebcastProcessRequest):
    """Full pipeline: capture audio -> transcribe -> store in RAG."""
    if not WEBCAST_READY:
        return JSONResponse({"status": "error", "error": "Webcast module not loaded"}, status_code=503)
    result = await process_webcast(
        audio_path=request.audio_path,
        url=request.url,
        title=request.title,
        ticker=request.ticker,
        company_name=request.company_name,
        event_date=request.event_date,
        event_type=request.event_type,
    )
    return JSONResponse(result)


@router.post("/ingest")
async def webcast_ingest(request: WebcastIngestRequest):
    """Ingest a pre-transcribed webcast into the RAG database."""
    if not WEBCAST_READY:
        return JSONResponse({"status": "error", "error": "Webcast module not loaded"}, status_code=503)
    result = ingest_webcast(
        transcript_text=request.transcript_text,
        title=request.title,
        ticker=request.ticker,
        company_name=request.company_name,
        event_date=request.event_date,
        event_type=request.event_type,
        source_url=request.source_url,
        duration_seconds=request.duration_seconds,
    )
    return JSONResponse(result)


@router.post("/search")
async def webcast_search(request: WebcastSearchRequest):
    """Search across all webcast transcripts (hybrid vector + keyword)."""
    if not WEBCAST_READY:
        return JSONResponse({"query": request.query, "results": [], "error": "Webcast module not loaded"})
    results = search_webcasts(query=request.query, ticker=request.ticker, top_k=request.top_k)
    clean_results = []
    for r in results:
        clean_results.append({
            "chunk_id": r.get("id"),
            "content": r.get("content", ""),
            "section_title": r.get("section_title", ""),
            "ticker": r.get("ticker", ""),
            "company_name": r.get("company_name", ""),
            "title": r.get("title", ""),
            "date": r.get("date", ""),
            "score": round(r.get("hybrid_score", r.get("rerank_score", 0)), 4),
        })
    return JSONResponse({"query": request.query, "results": clean_results, "count": len(clean_results)})


@router.get("/library")
async def webcast_library(ticker: str = None, limit: int = 50, offset: int = 0):
    """List all ingested webcasts in the library."""
    if not WEBCAST_READY:
        return JSONResponse({"webcasts": [], "total": 0, "error": "Webcast module not loaded"})
    result = list_webcasts(ticker=ticker, limit=limit, offset=offset)
    for w in result.get("webcasts", []):
        for key in ("embedded_at",):
            if key in w and w[key] is not None:
                w[key] = str(w[key])
    return JSONResponse(result)


@router.get("/transcript/{document_id}")
async def webcast_transcript(document_id: int):
    """Get the full transcript for a specific webcast."""
    if not WEBCAST_READY:
        return JSONResponse({"error": "Webcast module not loaded"}, status_code=503)
    result = get_webcast_transcript(document_id)
    if "document" in result and result["document"]:
        for key in ("embedded_at", "created_at"):
            if key in result["document"] and result["document"][key] is not None:
                result["document"][key] = str(result["document"][key])
    return JSONResponse(result)


@router.post("/upload-audio")
async def webcast_upload_audio(
    audio_file: UploadFile = File(...),
    title: str = Form(""),
    ticker: str = Form(""),
    company_name: str = Form(""),
    event_date: str = Form(""),
    event_type: str = Form("webcast"),
    source_url: str = Form(""),
    duration_seconds: float = Form(0),
):
    """
    Upload an audio file → transcribe with Whisper → embed in RAG.
    This is the primary sustainable workflow for webcast ingestion.
    Accepts: .mp3, .webm, .wav, .m4a, .ogg, .mp4, .flac
    """
    if not WEBCAST_READY:
        return JSONResponse({"status": "error", "error": "Webcast module not loaded"}, status_code=503)

    # Validate file type
    allowed_extensions = {".mp3", ".webm", ".wav", ".m4a", ".ogg", ".mp4", ".flac", ".opus"}
    ext = os.path.splitext(audio_file.filename or "")[1].lower()
    if ext not in allowed_extensions:
        return JSONResponse({
            "status": "error",
            "error": f"Unsupported file type '{ext}'. Accepted: {', '.join(sorted(allowed_extensions))}"
        }, status_code=400)

    # Save uploaded file to temp directory
    os.makedirs("/tmp/helix-webcasts", exist_ok=True)
    temp_path = os.path.join("/tmp/helix-webcasts", f"upload_{audio_file.filename}")
    try:
        contents = await audio_file.read()
        if len(contents) > 100 * 1024 * 1024:  # 100 MB limit
            return JSONResponse({
                "status": "error",
                "error": "File too large. Maximum 100 MB."
            }, status_code=400)

        with open(temp_path, "wb") as f:
            f.write(contents)

        # Run the full pipeline: transcribe → chunk → embed → store
        result = await process_webcast(
            audio_path=temp_path,
            title=title or audio_file.filename or "Uploaded Webcast",
            ticker=ticker,
            company_name=company_name,
            event_date=event_date,
            event_type=event_type,
        )

        # Add source_url to result if provided
        if source_url and result.get("status") == "ok":
            result["source_url"] = source_url

        return JSONResponse(result)

    except Exception as e:
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
    finally:
        # Clean up temp file
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


@router.get("/capture-js")
async def webcast_capture_js(backend_url: str = ""):
    """Return the MediaRecorder JS snippet for browser-side audio capture."""
    if not WEBCAST_READY:
        return JSONResponse({"error": "Webcast module not loaded"}, status_code=503)

    # Auto-detect backend URL from request if not provided
    js = get_media_recorder_js(backend_url=backend_url)

    return JSONResponse({
        "media_recorder_js": js,
        "bookmarklet": f"javascript:void({js.strip()})",
        "instructions": (
            "Paste this JS into the browser console on a webcast page, or save as a bookmarklet. "
            "It will show a recording badge with a Stop button. When you stop, the audio "
            "is automatically uploaded to SatyaBio for transcription and embedding."
        ),
    })


@router.get("/registration-js")
async def webcast_registration_js(
    first_name: str = None, last_name: str = None,
    email: str = None, company: str = None,
):
    """Return JS to auto-fill a webcast registration gate."""
    if not WEBCAST_READY:
        return JSONResponse({"error": "Webcast module not loaded"}, status_code=503)
    js = get_registration_js(first_name, last_name, email, company)
    return JSONResponse({
        "registration_js": js,
        "instructions": (
            "Inject this JS into the registration page to auto-fill the form fields. "
            "It will fill First Name, Last Name, Email, and Company."
        ),
    })
