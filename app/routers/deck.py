"""
Deck Analyzer Endpoints — slide extraction, analysis, comparison
Split from evidence.py for maintainability.
"""

import os
import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/deck", tags=["deck"])

# ---------------------------------------------------------------------------
# Lazy-load the deck analyzer
# ---------------------------------------------------------------------------

_SEARCH_DIR = str(Path(__file__).resolve().parent.parent.parent / "backend" / "services" / "search")
if _SEARCH_DIR not in sys.path:
    sys.path.insert(0, _SEARCH_DIR)

try:
    from deck_analyzer import (
        get_deck_analyzer_status,
        extract_slides_only,
        analyze_single_slide,
        compare_slides_to_document,
    )
    DECK_ANALYZER_READY = True
except ImportError as e:
    print(f"  [deck] Deck analyzer not available: {e}")
    get_deck_analyzer_status = None
    extract_slides_only = None
    analyze_single_slide = None
    compare_slides_to_document = None
    DECK_ANALYZER_READY = False


# ---------------------------------------------------------------------------
# Shared DB helper — lazy connection
# ---------------------------------------------------------------------------

_db_conn = None

def _get_db():
    """Get or create a DB connection (lazy-init, reuse across requests)."""
    global _db_conn
    try:
        if _db_conn and not _db_conn.closed:
            # Test the connection is still alive
            _db_conn.cursor().execute("SELECT 1")
            return _db_conn
    except Exception:
        _db_conn = None

    import psycopg2
    db_url = os.environ.get("NEON_DATABASE_URL", "")
    if not db_url:
        raise ValueError("NEON_DATABASE_URL not set")
    _db_conn = psycopg2.connect(db_url)
    _db_conn.autocommit = True
    return _db_conn


def _lookup_doc_path(doc_id: int):
    """Look up a document's file path, ticker, company_name, title from DB."""
    conn = _get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT file_path, ticker, company_name, title FROM documents WHERE id = %s",
        (doc_id,)
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    file_path, ticker, company_name, title = row

    # Resolve file path — try stored path, then library fallback
    if file_path and os.path.exists(file_path):
        return file_path, ticker, company_name, title

    library_path = os.environ.get("LIBRARY_PATH", "")
    if library_path and file_path:
        alt_path = os.path.join(library_path, os.path.basename(file_path))
        if os.path.exists(alt_path):
            return alt_path, ticker, company_name, title

    return file_path, ticker, company_name, title  # return even if not found on disk


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class DeckSlideAnalyzeRequest(BaseModel):
    doc_id: int
    slide_number: int
    ticker: str = ""
    company_name: str = ""

class DeckCompareRequest(BaseModel):
    slide_text: str
    compare_doc_id: int
    ticker: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def deck_analyzer_status():
    """Check deck analyzer readiness."""
    if not DECK_ANALYZER_READY:
        return JSONResponse({"ready": False, "error": "Deck analyzer not loaded"})
    return JSONResponse(get_deck_analyzer_status())


@router.get("/slides/{doc_id}")
async def deck_extract_slides(doc_id: int, images: bool = True):
    """Extract slides from a document (fast, no analysis)."""
    if not DECK_ANALYZER_READY:
        return JSONResponse({"error": "Deck analyzer not loaded"}, status_code=503)

    try:
        lookup = _lookup_doc_path(doc_id)
    except Exception as e:
        return JSONResponse({"error": f"DB error: {e}"}, status_code=500)

    if lookup is None:
        return JSONResponse({"error": f"Document {doc_id} not found"}, status_code=404)

    file_path, ticker, company_name, title = lookup

    if not file_path or not os.path.exists(file_path):
        return JSONResponse({
            "error": "PDF file not found on disk. Document may need re-downloading.",
            "doc_id": doc_id,
            "file_path": file_path,
        }, status_code=404)

    result = extract_slides_only(file_path, include_images=images)
    result["doc_id"] = doc_id
    result["ticker"] = ticker or ""
    result["company_name"] = company_name or ""
    result["title"] = title or ""
    return JSONResponse(result)


@router.post("/analyze-slide")
async def deck_analyze_slide(request: DeckSlideAnalyzeRequest):
    """Analyze a single slide with RAG context + Claude commentary."""
    if not DECK_ANALYZER_READY:
        return JSONResponse({"error": "Deck analyzer not loaded"}, status_code=503)

    try:
        lookup = _lookup_doc_path(request.doc_id)
    except Exception as e:
        return JSONResponse({"error": f"DB error: {e}"}, status_code=500)

    if lookup is None:
        return JSONResponse({"error": "Document not found"}, status_code=404)

    file_path = lookup[0]
    if not file_path or not os.path.exists(file_path):
        return JSONResponse({"error": "PDF file not found on disk"}, status_code=404)

    result = await analyze_single_slide(
        pdf_path=file_path,
        slide_number=request.slide_number,
        ticker=request.ticker,
        company_name=request.company_name,
        exclude_doc_id=request.doc_id,
    )
    return JSONResponse(result)


@router.post("/compare")
async def deck_compare(request: DeckCompareRequest):
    """Compare a slide's content against another document in the library."""
    if not DECK_ANALYZER_READY:
        return JSONResponse({"error": "Deck analyzer not loaded"}, status_code=503)

    result = await compare_slides_to_document(
        slide_text=request.slide_text,
        compare_doc_id=request.compare_doc_id,
        ticker=request.ticker,
    )
    return JSONResponse(result)
