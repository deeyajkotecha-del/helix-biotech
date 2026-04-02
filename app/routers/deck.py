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
    """Extract slides from a document (fast, no analysis).
    Falls back to text-only chunks from DB if PDF is not on disk."""
    if not DECK_ANALYZER_READY:
        return JSONResponse({"error": "Deck analyzer not loaded"}, status_code=503)

    try:
        lookup = _lookup_doc_path(doc_id)
    except Exception as e:
        return JSONResponse({"error": f"DB error: {e}"}, status_code=500)

    if lookup is None:
        return JSONResponse({"error": f"Document {doc_id} not found"}, status_code=404)

    file_path, ticker, company_name, title = lookup

    # Try PDF extraction first
    if file_path and os.path.exists(file_path):
        result = extract_slides_only(file_path, include_images=images)
        result["doc_id"] = doc_id
        result["ticker"] = ticker or ""
        result["company_name"] = company_name or ""
        result["title"] = title or ""
        return JSONResponse(result)

    # Fallback: check slide_images table for pre-rendered images, then chunks
    try:
        conn = _get_db()
        cur = conn.cursor()

        # 1) Check if we have pre-rendered slide images in the DB
        cur.execute("""
            SELECT page_number, image_b64
            FROM slide_images WHERE document_id = %s ORDER BY page_number
        """, (doc_id,))
        image_rows = cur.fetchall()

        # 2) Always load chunks for text content
        cur.execute("""
            SELECT chunk_index, section_title, content, token_count, page_number
            FROM chunks WHERE document_id = %s ORDER BY chunk_index
        """, (doc_id,))
        chunk_rows = cur.fetchall()
        cur.close()

        if not image_rows and not chunk_rows:
            return JSONResponse({
                "error": "No content found for this document.",
                "doc_id": doc_id,
            }, status_code=404)

        # If we have pre-rendered images, build slides from those (with text overlay from chunks)
        if image_rows:
            # Build a lookup of chunk text by page_number for text overlay
            chunk_text_by_page: dict[int, tuple[str, str]] = {}
            for chunk_idx, section, content, tokens, page_num in chunk_rows:
                if page_num is not None and page_num not in chunk_text_by_page:
                    chunk_text_by_page[page_num] = (content or "", section or "")

            slides = []
            for page_num, img_b64 in image_rows:
                text, section = chunk_text_by_page.get(page_num, ("", ""))
                slides.append({
                    "slide_number": page_num,
                    "text": text,
                    "image_b64": img_b64,
                    "word_count": len(text.split()) if text else 0,
                    "section_title": section,
                    "page_number": page_num,
                })

            return JSONResponse({
                "doc_id": doc_id,
                "ticker": ticker or "",
                "company_name": company_name or "",
                "title": title or "",
                "slides": slides,
                "total_slides": len(slides),
                "text_only": False,  # We have actual images!
            })

        # No images available — text-only fallback from chunks
        slides = []
        for row in chunk_rows:
            chunk_idx, section, content, tokens, page_num = row
            slides.append({
                "slide_number": chunk_idx + 1,
                "text": content,
                "image_b64": "",
                "word_count": len(content.split()) if content else 0,
                "section_title": section or "",
                "page_number": page_num,
            })

        return JSONResponse({
            "doc_id": doc_id,
            "ticker": ticker or "",
            "company_name": company_name or "",
            "title": title or "",
            "slides": slides,
            "total_slides": len(slides),
            "text_only": True,  # No images available
        })
    except Exception as e:
        return JSONResponse({"error": f"Failed to load slides: {e}"}, status_code=500)


@router.post("/analyze-slide")
async def deck_analyze_slide(request: DeckSlideAnalyzeRequest):
    """Analyze a single slide with RAG context + Claude commentary.
    If PDF is not on disk, uses the chunk text from the DB instead."""
    if not DECK_ANALYZER_READY:
        return JSONResponse({"error": "Deck analyzer not loaded"}, status_code=503)

    try:
        lookup = _lookup_doc_path(request.doc_id)
    except Exception as e:
        return JSONResponse({"error": f"DB error: {e}"}, status_code=500)

    if lookup is None:
        return JSONResponse({"error": "Document not found"}, status_code=404)

    file_path = lookup[0]

    # If PDF is on disk, use full slide analysis (with image)
    if file_path and os.path.exists(file_path):
        result = await analyze_single_slide(
            pdf_path=file_path,
            slide_number=request.slide_number,
            ticker=request.ticker,
            company_name=request.company_name,
            exclude_doc_id=request.doc_id,
        )
        return JSONResponse(result)

    # Fallback: use slide_images + chunks from DB
    try:
        conn = _get_db()
        cur = conn.cursor()

        # 1) Try to get the pre-rendered image for this slide
        cur.execute("""
            SELECT image_b64 FROM slide_images
            WHERE document_id = %s AND page_number = %s
        """, (request.doc_id, request.slide_number))
        img_row = cur.fetchone()
        slide_image = img_row[0] if img_row else ""

        # 2) Get text content — try by page_number first, then chunk_index
        cur.execute("""
            SELECT content, section_title FROM chunks
            WHERE document_id = %s AND page_number = %s
            ORDER BY chunk_index LIMIT 1
        """, (request.doc_id, request.slide_number))
        text_row = cur.fetchone()
        if not text_row:
            # Fallback: try chunk_index (slide_number is 1-indexed)
            cur.execute("""
                SELECT content, section_title FROM chunks
                WHERE document_id = %s AND chunk_index = %s
            """, (request.doc_id, request.slide_number - 1))
            text_row = cur.fetchone()
        cur.close()

        chunk_text = text_row[0] if text_row else ""

        if not chunk_text and not slide_image:
            return JSONResponse({"error": "Slide/chunk not found"}, status_code=404)

        # Use analyze_single_slide with text override + image from DB
        result = await analyze_single_slide(
            pdf_path=None,
            slide_number=request.slide_number,
            ticker=request.ticker,
            company_name=request.company_name,
            exclude_doc_id=request.doc_id,
            slide_text_override=chunk_text or "(No text extracted for this slide)",
        )
        # Attach the stored image so the frontend can display it
        if slide_image:
            result["image_b64"] = slide_image
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": f"Analysis failed: {e}"}, status_code=500)


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
