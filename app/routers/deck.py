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
        extract_slide_references,
        resolve_reference_links,
    )
    DECK_ANALYZER_READY = True
except ImportError as e:
    print(f"  [deck] Deck analyzer not available: {e}")
    get_deck_analyzer_status = None
    extract_slides_only = None
    analyze_single_slide = None
    compare_slides_to_document = None
    extract_slide_references = None
    resolve_reference_links = None
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

    # Try multiple library paths
    library_paths = [
        os.environ.get("LIBRARY_PATH", ""),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "services", "data"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "services", "data"),
    ]
    if file_path:
        basename = os.path.basename(file_path)
        for lp in library_paths:
            if not lp:
                continue
            # Direct match
            alt_path = os.path.join(lp, basename)
            if os.path.exists(alt_path):
                return alt_path, ticker, company_name, title
            # Try under companies/<TICKER>/sources/
            if ticker:
                alt_path = os.path.join(lp, "companies", ticker, "sources", basename)
                if os.path.exists(alt_path):
                    return alt_path, ticker, company_name, title

    return file_path, ticker, company_name, title  # return even if not found on disk


# ---------------------------------------------------------------------------
# Slide image caching — persist extracted images so they survive PDF removal
# ---------------------------------------------------------------------------

_slide_images_table_ready = False

def _ensure_slide_images_table():
    """Create the slide_images table if it doesn't exist yet.
    Also adds slide_text column if upgrading from older schema."""
    global _slide_images_table_ready
    if _slide_images_table_ready:
        return
    try:
        conn = _get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS slide_images (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                image_b64 TEXT NOT NULL,
                slide_text TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(document_id, page_number)
            )
        """)
        # Add slide_text column if upgrading from older schema
        cur.execute("""
            ALTER TABLE slide_images ADD COLUMN IF NOT EXISTS slide_text TEXT DEFAULT ''
        """)
        cur.close()
        _slide_images_table_ready = True
    except Exception as e:
        print(f"  [deck] Could not create slide_images table: {e}")


def _cache_slide_images(doc_id: int, slides: list):
    """Store extracted slide images in DB for future use (skips if already cached)."""
    _ensure_slide_images_table()
    conn = _get_db()
    cur = conn.cursor()

    # Check if images are already cached for this document
    cur.execute("SELECT COUNT(*) FROM slide_images WHERE document_id = %s", (doc_id,))
    existing = cur.fetchone()[0]
    if existing > 0:
        cur.close()
        return  # Already cached, nothing to do

    cached = 0
    for slide in slides:
        img = slide.get("image_b64", "")
        page = slide.get("slide_number", 0)
        text = slide.get("text", "")
        if img and page:
            try:
                cur.execute(
                    """INSERT INTO slide_images (document_id, page_number, image_b64, slide_text)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (document_id, page_number)
                       DO UPDATE SET slide_text = EXCLUDED.slide_text
                       WHERE slide_images.slide_text IS NULL OR slide_images.slide_text = ''""",
                    (doc_id, page, img, text),
                )
                cached += 1
            except Exception:
                pass  # Skip individual slide errors

    cur.close()
    if cached:
        print(f"  [deck] Cached {cached} slide images for doc {doc_id}")


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

    # ── CACHE-FIRST STRATEGY ──
    # Check the slide_images DB cache BEFORE re-extracting from PDF.
    # This avoids redundant PDF rendering and saves compute costs.
    # Only fall through to PDF extraction on a cache miss.

    try:
        _ensure_slide_images_table()
        conn = _get_db()
        cur = conn.cursor()

        # 1) Check for cached slide images + per-page text
        cur.execute("""
            SELECT page_number, slide_text FROM slide_images
            WHERE document_id = %s ORDER BY page_number
        """, (doc_id,))
        cached_slides = cur.fetchall()  # [(page_num, slide_text), ...]
        image_pages = [r[0] for r in cached_slides]
        slide_text_by_page = {r[0]: r[1] or "" for r in cached_slides}

        # 2) Load chunks as fallback text source (for slides without per-page text)
        cur.execute("""
            SELECT chunk_index, section_title, content, token_count, page_number
            FROM chunks WHERE document_id = %s ORDER BY chunk_index
        """, (doc_id,))
        chunk_rows = cur.fetchall()

        # ── CACHE HIT: serve from slide_images table (fast, no PDF needed) ──
        if image_pages:
            # Build chunk lookup as fallback only for slides missing per-page text
            chunk_text_by_page: dict[int, tuple[str, str]] = {}
            for chunk_idx, section, content, tokens, page_num in chunk_rows:
                if page_num is not None and page_num not in chunk_text_by_page:
                    chunk_text_by_page[page_num] = (content or "", section or "")

            # Load only the first slide's image to keep initial response small
            first_img_b64 = ""
            cur.execute("""
                SELECT image_b64 FROM slide_images
                WHERE document_id = %s AND page_number = %s
            """, (doc_id, image_pages[0]))
            row = cur.fetchone()
            first_img_b64 = row[0] if row else ""
            cur.close()

            slides = []
            for i, page_num in enumerate(image_pages):
                # Prefer per-page text from slide_images (accurate), fall back to chunks
                page_text = slide_text_by_page.get(page_num, "")
                if page_text:
                    text = page_text
                    section = ""
                else:
                    text, section = chunk_text_by_page.get(page_num, ("", ""))

                slides.append({
                    "slide_number": page_num,
                    "text": text,
                    "image_b64": first_img_b64 if i == 0 else "",  # Only first slide has image
                    "word_count": len(text.split()) if text else 0,
                    "section_title": section,
                    "page_number": page_num,
                    "has_image": True,  # Signal that image can be lazy-loaded
                })

            print(f"  [deck] Cache HIT for doc {doc_id}: serving {len(slides)} slides from DB")
            return JSONResponse({
                "doc_id": doc_id,
                "ticker": ticker or "",
                "company_name": company_name or "",
                "title": title or "",
                "slides": slides,
                "total_slides": len(slides),
                "text_only": False,
                "lazy_images": True,  # Tell frontend to use /slide-image endpoint
            })

        cur.close()
    except Exception as e:
        print(f"  [deck] Cache lookup failed (will try PDF): {e}")

    # ── CACHE MISS: extract from PDF on disk, then cache for next time ──
    if file_path and os.path.exists(file_path):
        print(f"  [deck] Cache MISS for doc {doc_id}: extracting from PDF")
        result = extract_slides_only(file_path, include_images=images)
        result["doc_id"] = doc_id
        result["ticker"] = ticker or ""
        result["company_name"] = company_name or ""
        result["title"] = title or ""

        # Cache slide images in DB so next request is instant (no re-extraction)
        if images and result.get("slides"):
            try:
                _cache_slide_images(doc_id, result["slides"])
            except Exception as e:
                print(f"  [deck] Image caching failed (non-fatal): {e}")

        return JSONResponse(result)

    # ── NO CACHE, NO PDF: text-only fallback from chunks ──
    try:
        conn = _get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT chunk_index, section_title, content, token_count, page_number
            FROM chunks WHERE document_id = %s ORDER BY chunk_index
        """, (doc_id,))
        chunk_rows = cur.fetchall()
        cur.close()

        if not chunk_rows:
            return JSONResponse({
                "error": "No content found for this document.",
                "doc_id": doc_id,
            }, status_code=404)

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


@router.get("/slide-image/{doc_id}/{page_number}")
async def get_slide_image(doc_id: int, page_number: int):
    """Get a single slide image by document ID and page number.
    Used for lazy-loading images one at a time instead of all at once."""
    try:
        conn = _get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT image_b64, slide_text FROM slide_images
            WHERE document_id = %s AND page_number = %s
        """, (doc_id, page_number))
        row = cur.fetchone()
        cur.close()

        if not row:
            return JSONResponse({"error": "Image not found"}, status_code=404)

        result = {"image_b64": row[0]}
        if row[1]:
            result["slide_text"] = row[1]
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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

    # ── CACHE-FIRST: check DB for cached image + per-page text before touching PDF ──
    slide_image = ""
    chunk_text = ""
    try:
        _ensure_slide_images_table()
        conn = _get_db()
        cur = conn.cursor()

        # 1) Try to get the pre-rendered image AND per-page text for this slide
        cur.execute("""
            SELECT image_b64, slide_text FROM slide_images
            WHERE document_id = %s AND page_number = %s
        """, (request.doc_id, request.slide_number))
        img_row = cur.fetchone()
        slide_image = img_row[0] if img_row else ""
        per_page_text = img_row[1] if img_row and img_row[1] else ""

        # 2) Use per-page text if available (accurate), fall back to chunks
        if per_page_text:
            chunk_text = per_page_text
        else:
            cur.execute("""
                SELECT content, section_title FROM chunks
                WHERE document_id = %s AND page_number = %s
                ORDER BY chunk_index LIMIT 1
            """, (request.doc_id, request.slide_number))
            text_row = cur.fetchone()
            if not text_row:
                cur.execute("""
                    SELECT content, section_title FROM chunks
                    WHERE document_id = %s AND chunk_index = %s
                """, (request.doc_id, request.slide_number - 1))
                text_row = cur.fetchone()
            chunk_text = text_row[0] if text_row else ""
        cur.close()

        chunk_text = text_row[0] if text_row else ""
    except Exception as e:
        print(f"  [deck] Cache lookup for analysis failed: {e}")

    # If we have a cached image, send it to Claude for vision analysis — no PDF needed
    if slide_image:
        print(f"  [deck] Analyze slide {request.slide_number}: using cached image for vision analysis (no PDF extraction)")
        result = await analyze_single_slide(
            pdf_path=None,
            slide_number=request.slide_number,
            ticker=request.ticker,
            company_name=request.company_name,
            exclude_doc_id=request.doc_id,
            slide_text_override=chunk_text or "(No text extracted for this slide)",
            slide_image_override=slide_image,  # Claude sees the actual slide image
        )
        # Ensure the image is in the response for frontend display too
        if "image_b64" not in result or not result["image_b64"]:
            result["image_b64"] = slide_image
        return JSONResponse(result)

    # Cache miss — fall back to PDF on disk
    if file_path and os.path.exists(file_path):
        print(f"  [deck] Analyze slide {request.slide_number}: cache miss, extracting from PDF")
        result = await analyze_single_slide(
            pdf_path=file_path,
            slide_number=request.slide_number,
            ticker=request.ticker,
            company_name=request.company_name,
            exclude_doc_id=request.doc_id,
        )
        return JSONResponse(result)

    # No image, no PDF — text-only analysis
    if chunk_text:
        result = await analyze_single_slide(
            pdf_path=None,
            slide_number=request.slide_number,
            ticker=request.ticker,
            company_name=request.company_name,
            exclude_doc_id=request.doc_id,
            slide_text_override=chunk_text,
        )
        return JSONResponse(result)

    return JSONResponse({"error": "Slide/chunk not found"}, status_code=404)


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


# ---------------------------------------------------------------------------
# Reference Extraction
# ---------------------------------------------------------------------------

class DeckRefRequest(BaseModel):
    doc_id: int
    slide_number: int
    slide_text: str = ""
    slide_image_b64: str = ""


@router.post("/extract-references")
async def deck_extract_references(request: DeckRefRequest):
    """Extract references from a slide and resolve to PubMed/DOI links."""
    if not DECK_ANALYZER_READY:
        return JSONResponse({"error": "Deck analyzer not loaded"}, status_code=503)

    slide_text = request.slide_text
    slide_image = request.slide_image_b64

    # If no text/image provided, try to load from DB
    if not slide_text and not slide_image:
        try:
            conn = _get_db()
            cur = conn.cursor()

            # Get slide image
            cur.execute("""
                SELECT image_b64 FROM slide_images
                WHERE document_id = %s AND page_number = %s
            """, (request.doc_id, request.slide_number))
            img_row = cur.fetchone()
            if img_row:
                slide_image = img_row[0] or ""

            # Get text
            cur.execute("""
                SELECT content FROM chunks
                WHERE document_id = %s AND page_number = %s
                ORDER BY chunk_index LIMIT 1
            """, (request.doc_id, request.slide_number))
            text_row = cur.fetchone()
            if text_row:
                slide_text = text_row[0] or ""
            cur.close()
        except Exception as e:
            return JSONResponse({"error": f"Failed to load slide data: {e}"}, status_code=500)

    if not slide_text and not slide_image:
        return JSONResponse({"references": [], "message": "No slide content to extract references from"})

    try:
        # Step 1: Extract references using Claude
        refs = await extract_slide_references(slide_text, slide_image)

        if not refs:
            return JSONResponse({"references": [], "message": "No references found on this slide"})

        # Step 2: Resolve to PubMed/DOI links
        refs = await resolve_reference_links(refs)

        return JSONResponse({
            "references": refs,
            "count": len(refs),
            "slide_number": request.slide_number,
        })
    except Exception as e:
        return JSONResponse({"error": f"Reference extraction failed: {e}"}, status_code=500)
