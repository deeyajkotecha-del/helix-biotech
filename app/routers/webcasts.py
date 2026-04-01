"""
Webcast Pipeline Endpoints — transcribe, ingest, search, library
Split from evidence.py for maintainability.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
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


@router.get("/capture-js")
async def webcast_capture_js():
    """Return the MediaRecorder JS snippet for browser-side audio capture."""
    if not WEBCAST_READY:
        return JSONResponse({"error": "Webcast module not loaded"}, status_code=503)
    return JSONResponse({
        "media_recorder_js": get_media_recorder_js(),
        "instructions": (
            "Inject this JS into the webcast player tab to start recording audio. "
            "Call window.__helixRecorder.stop() to finish. The browser will download "
            "the recording as webcast_recording.webm."
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
