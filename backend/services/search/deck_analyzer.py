"""
Deck Analyzer — Slide-by-slide investor presentation analysis
==============================================================
Extracts each slide from an investor deck (PDF), runs RAG search
for context from the document library, and generates biotech investor
commentary per slide using Claude.

Usage:
    result = await analyze_deck(
        pdf_path="/path/to/deck.pdf",
        ticker="MRNA",
        company_name="Moderna",
    )
    # result["slides"] = [{slide_number, text, image_b64, rag_context, commentary}, ...]
"""

import os
import sys
import re
import json
import base64
import asyncio
from io import BytesIO
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# ---------------------------------------------------------------------------
# Lazy imports (heavy libs)
# ---------------------------------------------------------------------------

_pdfplumber = None
_fitz = None
_anthropic_client = None


def _get_pdfplumber():
    global _pdfplumber
    if _pdfplumber is None:
        try:
            import pdfplumber
            _pdfplumber = pdfplumber
        except ImportError:
            print("  [deck] pdfplumber not installed")
    return _pdfplumber


def _get_fitz():
    global _fitz
    if _fitz is None:
        try:
            import fitz  # PyMuPDF
            _fitz = fitz
        except ImportError:
            print("  [deck] PyMuPDF not installed")
    return _fitz


def _get_claude():
    global _anthropic_client
    if _anthropic_client is None:
        if not ANTHROPIC_API_KEY:
            print("  [deck] ANTHROPIC_API_KEY not set")
            return None
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        except ImportError:
            print("  [deck] anthropic library not installed")
    return _anthropic_client


def _get_rag_search():
    """Import RAG search function."""
    try:
        from rag_search import rag_search
        return rag_search
    except ImportError:
        return None


# ===========================================================================
# 1. SLIDE EXTRACTION — text + image per page
# ===========================================================================

def extract_slides(pdf_path: str) -> list[dict]:
    """
    Extract each slide from a PDF as text + thumbnail image.
    Returns list of:
        {"slide_number": int, "text": str, "image_b64": str (JPEG base64)}
    """
    slides = []

    # Extract text with pdfplumber
    plumber = _get_pdfplumber()
    page_texts = []
    if plumber:
        try:
            with plumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    # Also try extracting tables
                    tables = page.extract_tables() or []
                    table_text = ""
                    for table in tables:
                        for row in table:
                            if row:
                                table_text += " | ".join(str(cell or "") for cell in row) + "\n"
                    full_text = text
                    if table_text:
                        full_text += "\n[TABLE DATA]\n" + table_text
                    page_texts.append(full_text.strip())
        except Exception as e:
            print(f"  [deck] pdfplumber extraction failed: {e}")

    # Extract images with PyMuPDF (higher quality rendering)
    fitz = _get_fitz()
    page_images = []
    if fitz:
        try:
            doc = fitz.open(pdf_path)
            for i in range(len(doc)):
                page = doc[i]
                # Render at 1.5x zoom for decent quality without huge size
                mat = fitz.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("jpeg")
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                page_images.append(img_b64)
            doc.close()
        except Exception as e:
            print(f"  [deck] PyMuPDF image extraction failed: {e}")

    # Combine
    num_pages = max(len(page_texts), len(page_images))
    for i in range(num_pages):
        slides.append({
            "slide_number": i + 1,
            "text": page_texts[i] if i < len(page_texts) else "",
            "image_b64": page_images[i] if i < len(page_images) else "",
        })

    print(f"  [deck] Extracted {len(slides)} slides from {pdf_path}")
    return slides


# ===========================================================================
# 2. RAG CONTEXT — pull related content per slide
# ===========================================================================

def get_slide_rag_context(
    slide_text: str,
    ticker: str = "",
    exclude_doc_id: int = None,
    top_k: int = 8,
) -> list[dict]:
    """
    Search the RAG database for content related to this slide.
    Excludes chunks from the deck itself (to find external context).
    Returns up to top_k results with full chunk content for deep analysis.
    """
    rag_search = _get_rag_search()
    if rag_search is None or not slide_text.strip():
        return []

    # Build a focused query from the slide text (first 300 words)
    words = slide_text.split()[:300]
    query = " ".join(words)

    try:
        results = rag_search(
            query=query,
            ticker=ticker or None,
            top_k=top_k + 8,  # Over-fetch to allow filtering
        )

        # Filter out chunks from the same document
        filtered = []
        seen_titles = set()
        for r in results:
            if exclude_doc_id and r.get("document_id") == exclude_doc_id:
                continue
            # Deduplicate by title+page to get breadth across sources
            dedup_key = f"{r.get('title','')}-{r.get('page_number',0)}"
            if dedup_key in seen_titles:
                continue
            seen_titles.add(dedup_key)
            filtered.append({
                "content": r.get("content", "")[:800],  # Longer excerpts for deeper analysis
                "title": r.get("title", ""),
                "ticker": r.get("ticker", ""),
                "doc_type": r.get("doc_type", ""),
                "page_number": r.get("page_number", 0),
                "similarity": round(r.get("similarity", 0), 3),
            })
            if len(filtered) >= top_k:
                break

        return filtered

    except Exception as e:
        print(f"  [deck] RAG search failed for slide: {e}")
        return []


# ===========================================================================
# 3. CLAUDE COMMENTARY — biotech investor analysis per slide
# ===========================================================================

SLIDE_ANALYSIS_SYSTEM = """You are a senior biotech investment analyst (MD/PhD background) writing for portfolio managers who already know the science. Be direct, concise, and opinionated. No filler.

For each slide, provide:

## Key Takeaway
One to two sentences: what matters on this slide and why. Lead with the number or data point, not background.

## Data Assessment
- Pull out the SPECIFIC numbers: endpoints, p-values, HRs, ORR, revenue figures, enrollment counts
- Flag what's strong vs weak vs missing. Be blunt about cherry-picked data, immature readouts, or spin.
- Compare to current standard of care or competitor benchmarks — cite specific numbers if you have them from the cross-reference sources.
- If this is a financial slide: highlight the key trend (growth/decline, margin change, guidance vs consensus).

## Red Flags & Gaps
Only include if there's something genuinely worth flagging. Skip this section entirely if the slide is straightforward. Don't manufacture concerns.

## So What?
One to two sentences on investment implications. Be direct: is this bullish, bearish, or noise?

RULES:
- Target 150-250 words total. Shorter is better.
- Never restate what's already visible on the slide. The user can read it.
- Never start with "This slide presents..." or "This earnings release captures..." — jump straight to the insight.
- Use numbers, not adjectives. "$14.8B (+8.6% YoY)" not "strong revenue performance."
- If the RAG cross-references have relevant data, weave it in naturally. If they don't, skip the section — don't say "Without access to specific RAG context."
- If a slide is mostly boilerplate (forward-looking statements, legal disclaimers, table of contents), just say "Boilerplate — skip" and nothing else."""


async def generate_slide_commentary(
    slide_text: str,
    slide_number: int,
    rag_context: list[dict],
    ticker: str = "",
    company_name: str = "",
    slide_image_b64: str = "",
) -> str:
    """
    Generate biotech investor commentary for a single slide.
    Uses Claude with optional vision (slide image) + RAG context.
    """
    client = _get_claude()
    if client is None:
        return "_Commentary unavailable — Claude API not configured._"

    # Build the RAG context section — full excerpts for deep cross-referencing
    rag_section = ""
    if rag_context:
        rag_section = "\n\n---\n**CROSS-REFERENCE: Related content from document library**\n\n"
        for i, ctx in enumerate(rag_context, 1):
            rag_section += (
                f"**Source {i}** [{ctx['ticker']} — {ctx['doc_type']}] *{ctx['title']}*"
                f" (similarity: {ctx['similarity']})\n"
                f"{ctx['content']}\n\n"
            )

    # Build the message
    user_content = []

    # Add slide image if available (vision) — critical for charts/KM curves
    if slide_image_b64:
        user_content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": slide_image_b64,
            },
        })

    prompt = (
        f"**Slide {slide_number}** — {company_name} ({ticker})\n\n"
        f"**Extracted text from slide:**\n{slide_text[:3000]}\n"
        f"{rag_section}\n\n"
        f"Analyze this slide. Extract the key numbers and give your investment read. "
        f"If there's a chart or figure in the image, read the data from it. "
        f"Be concise — the reader already knows the company."
    )
    user_content.append({"type": "text", "text": prompt})

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1200,
            system=SLIDE_ANALYSIS_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text
    except Exception as e:
        print(f"  [deck] Claude commentary failed for slide {slide_number}: {e}")
        return f"_Commentary generation failed: {e}_"


# ===========================================================================
# 4. FULL PIPELINE — analyze entire deck
# ===========================================================================

async def analyze_deck(
    pdf_path: str,
    ticker: str = "",
    company_name: str = "",
    deck_title: str = "",
    exclude_doc_id: int = None,
    include_images: bool = True,
    max_slides: int = 50,
) -> dict:
    """
    Full deck analysis pipeline:
      1. Extract slides (text + images)
      2. For each slide, get RAG context
      3. For each slide, generate Claude commentary
      4. Return structured result

    Returns: {
        "title": str,
        "ticker": str,
        "total_slides": int,
        "slides": [
            {
                "slide_number": int,
                "text": str,
                "image_b64": str,  (if include_images)
                "rag_context": [...],
                "commentary": str,
            }
        ],
        "summary": str,  (overall deck summary)
    }
    """
    if not os.path.exists(pdf_path):
        return {"error": f"File not found: {pdf_path}", "slides": []}

    # Step 1: Extract slides
    slides = extract_slides(pdf_path)
    if not slides:
        return {"error": "Could not extract slides from PDF", "slides": []}

    slides = slides[:max_slides]

    # Step 2 & 3: Get RAG context + commentary for each slide
    analyzed_slides = []
    for slide in slides:
        # Skip near-empty slides (title pages, blank dividers)
        if len(slide["text"].split()) < 10:
            analyzed_slides.append({
                "slide_number": slide["slide_number"],
                "text": slide["text"],
                "image_b64": slide["image_b64"] if include_images else "",
                "rag_context": [],
                "commentary": "_Title/divider slide — no substantive content to analyze._",
            })
            continue

        # RAG context
        rag_context = get_slide_rag_context(
            slide["text"],
            ticker=ticker,
            exclude_doc_id=exclude_doc_id,
            top_k=3,
        )

        # Claude commentary
        commentary = await generate_slide_commentary(
            slide_text=slide["text"],
            slide_number=slide["slide_number"],
            rag_context=rag_context,
            ticker=ticker,
            company_name=company_name,
            slide_image_b64=slide["image_b64"] if include_images else "",
        )

        analyzed_slides.append({
            "slide_number": slide["slide_number"],
            "text": slide["text"],
            "image_b64": slide["image_b64"] if include_images else "",
            "rag_context": rag_context,
            "commentary": commentary,
        })

    # Step 4: Overall summary
    summary = await _generate_deck_summary(analyzed_slides, ticker, company_name, deck_title)

    return {
        "title": deck_title or f"{ticker} Investor Presentation",
        "ticker": ticker,
        "company_name": company_name,
        "total_slides": len(analyzed_slides),
        "slides": analyzed_slides,
        "summary": summary,
    }


async def analyze_single_slide(
    pdf_path: str = None,
    slide_number: int = 1,
    ticker: str = "",
    company_name: str = "",
    exclude_doc_id: int = None,
    slide_text_override: str = None,
) -> dict:
    """Analyze a single slide — useful for on-demand analysis in the UI.
    If slide_text_override is provided, uses that text instead of extracting from PDF.
    This enables text-only analysis when the PDF isn't available on disk."""

    if slide_text_override is not None:
        # Text-only mode: no PDF needed
        slide_text = slide_text_override
        slide_image = ""
    else:
        slides = extract_slides(pdf_path)
        if slide_number < 1 or slide_number > len(slides):
            return {"error": f"Slide {slide_number} not found (deck has {len(slides)} slides)"}
        slide = slides[slide_number - 1]
        slide_text = slide["text"]
        slide_image = slide["image_b64"]

    rag_context = get_slide_rag_context(
        slide_text, ticker=ticker, exclude_doc_id=exclude_doc_id, top_k=5,
    )

    commentary = await generate_slide_commentary(
        slide_text=slide_text,
        slide_number=slide_number,
        rag_context=rag_context,
        ticker=ticker,
        company_name=company_name,
        slide_image_b64=slide_image or "",
    )

    return {
        "slide_number": slide_number,
        "text": slide_text,
        "image_b64": slide_image,
        "rag_context": rag_context,
        "commentary": commentary,
    }


# ===========================================================================
# 4b. REFERENCE EXTRACTION — parse citations from slides, resolve to links
# ===========================================================================

REFERENCE_EXTRACTION_PROMPT = """You are a biomedical reference parser. Given slide text from a biotech investor presentation, extract ALL academic/clinical references and citations.

For EACH reference found, return a JSON object with these fields:
- "raw": the original reference text as it appears on the slide
- "authors": first author surname + "et al" if applicable (e.g. "Pousset et al.")
- "title": article title if discernible (empty string if not)
- "journal": journal name or abbreviation
- "year": publication year as integer
- "volume": volume/issue if present (e.g. "72(11)")
- "pages": page range if present (e.g. "1334-1341")
- "doi": DOI if present (empty string if not)
- "pmid": PubMed ID if present (empty string if not)
- "data_on_file": true if this is a "Data on file" reference, false otherwise

Return a JSON array of objects. If no references are found, return [].
Only return the JSON array, no other text. Be thorough — look for numbered footnotes, superscript citations, and inline references."""


async def extract_slide_references(
    slide_text: str,
    slide_image_b64: str = "",
) -> list[dict]:
    """Extract academic references from a slide using Claude."""
    client = _get_claude()
    if client is None:
        return []

    user_content = []

    # Include slide image for visual reference detection (footnotes at bottom)
    if slide_image_b64:
        user_content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": slide_image_b64,
            },
        })

    user_content.append({
        "type": "text",
        "text": f"Extract all references from this slide:\n\n{slide_text[:4000]}",
    })

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=REFERENCE_EXTRACTION_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        text = response.content[0].text.strip()
        # Parse JSON — handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        refs = json.loads(text)
        return refs if isinstance(refs, list) else []
    except Exception as e:
        print(f"  [deck] Reference extraction failed: {e}")
        return []


async def resolve_reference_links(references: list[dict]) -> list[dict]:
    """Resolve references to PubMed/DOI links via NCBI eUtils API."""
    import urllib.request
    import urllib.parse

    for ref in references:
        if ref.get("data_on_file"):
            ref["pubmed_url"] = ""
            ref["doi_url"] = ""
            continue

        # If we already have a PMID
        if ref.get("pmid"):
            ref["pubmed_url"] = f"https://pubmed.ncbi.nlm.nih.gov/{ref['pmid']}/"
            if not ref.get("doi_url"):
                ref["doi_url"] = ""
            continue

        # If we have a DOI
        if ref.get("doi"):
            ref["doi_url"] = f"https://doi.org/{ref['doi']}"
            ref["pubmed_url"] = ""
            # Try to get PMID from DOI via eUtils
            try:
                query = urllib.parse.quote(ref["doi"])
                url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}[doi]&retmode=json"
                req = urllib.request.Request(url, headers={"User-Agent": "SatyaBio/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                    ids = data.get("esearchresult", {}).get("idlist", [])
                    if ids:
                        ref["pmid"] = ids[0]
                        ref["pubmed_url"] = f"https://pubmed.ncbi.nlm.nih.gov/{ids[0]}/"
            except Exception:
                pass
            continue

        # Search by author + journal + year
        search_parts = []
        if ref.get("authors"):
            # Extract first author surname
            surname = ref["authors"].split(",")[0].split(" et ")[0].strip()
            if surname:
                search_parts.append(f"{surname}[author]")
        if ref.get("journal"):
            search_parts.append(f"{ref['journal']}[journal]")
        if ref.get("year"):
            search_parts.append(f"{ref['year']}[pdat]")

        if not search_parts:
            ref["pubmed_url"] = ""
            ref["doi_url"] = ""
            continue

        try:
            query = urllib.parse.quote(" AND ".join(search_parts))
            url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmode=json&retmax=3"
            req = urllib.request.Request(url, headers={"User-Agent": "SatyaBio/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                ids = data.get("esearchresult", {}).get("idlist", [])
                if ids:
                    ref["pmid"] = ids[0]
                    ref["pubmed_url"] = f"https://pubmed.ncbi.nlm.nih.gov/{ids[0]}/"
                else:
                    ref["pubmed_url"] = ""
            ref["doi_url"] = ""
        except Exception:
            ref["pubmed_url"] = ""
            ref["doi_url"] = ""

    return references


async def _generate_deck_summary(
    slides: list[dict],
    ticker: str,
    company_name: str,
    deck_title: str,
) -> str:
    """Generate an overall investment summary of the full deck."""
    client = _get_claude()
    if client is None:
        return ""

    # Collect all commentary
    slide_summaries = []
    for s in slides:
        if s["commentary"] and "no substantive content" not in s["commentary"]:
            slide_summaries.append(f"Slide {s['slide_number']}: {s['commentary'][:200]}")

    if not slide_summaries:
        return ""

    prompt = (
        f"You just analyzed the full investor deck for {company_name} ({ticker}): "
        f"'{deck_title}'.\n\n"
        f"Here are your slide-by-slide notes:\n"
        + "\n".join(slide_summaries[:30]) +
        f"\n\nWrite a 3-4 paragraph investment summary of this deck. "
        f"What are the key takeaways? What's bullish vs. concerning? "
        f"What questions remain? Be direct and specific."
    )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            system="You are a senior biotech investment analyst writing a deck review memo.",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        return f"_Summary generation failed: {e}_"


# ===========================================================================
# 5. SLIDE EXTRACTION ONLY (lightweight, no Claude)
# ===========================================================================

def extract_slides_only(pdf_path: str, include_images: bool = True) -> dict:
    """
    Just extract slides without any analysis — fast, for the initial load
    in the UI so the user can see the deck immediately.
    """
    if not os.path.exists(pdf_path):
        return {"error": f"File not found: {pdf_path}", "slides": []}

    slides = extract_slides(pdf_path)
    result_slides = []
    for s in slides:
        result_slides.append({
            "slide_number": s["slide_number"],
            "text": s["text"],
            "image_b64": s["image_b64"] if include_images else "",
            "word_count": len(s["text"].split()),
        })

    return {
        "total_slides": len(result_slides),
        "slides": result_slides,
    }


# ===========================================================================
# 6. COMPARE TWO DECKS / DOCUMENTS
# ===========================================================================

async def compare_slides_to_document(
    slide_text: str,
    compare_doc_id: int,
    ticker: str = "",
) -> dict:
    """
    Compare a specific slide's content against a particular document
    in the RAG database (e.g., compare investor deck slide to 10-K section).
    """
    # Get chunks from the comparison document
    try:
        from rag_search import _get_db
        import psycopg2.extras

        conn = _get_db()
        if conn is None:
            return {"error": "Database not available"}

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT c.content, c.section_title, c.page_number, c.chunk_index,
                   d.title, d.ticker, d.doc_type
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.document_id = %s
            ORDER BY c.chunk_index
        """, (compare_doc_id,))
        doc_chunks = [dict(row) for row in cur.fetchall()]

        if not doc_chunks:
            return {"error": f"No chunks found for document {compare_doc_id}"}

        # Use Voyage to find the most relevant chunks
        try:
            from rag_search import _get_voyage, EMBED_MODEL
            vo = _get_voyage()
            if vo:
                query_emb = vo.embed([slide_text[:1000]], model=EMBED_MODEL, input_type="query")
                chunk_embs = vo.embed(
                    [c["content"][:500] for c in doc_chunks[:30]],
                    model=EMBED_MODEL, input_type="document"
                )
                # Compute similarities
                import numpy as np
                q = np.array(query_emb.embeddings[0])
                for i, c in enumerate(doc_chunks[:30]):
                    d = np.array(chunk_embs.embeddings[i])
                    c["similarity"] = float(np.dot(q, d) / (np.linalg.norm(q) * np.linalg.norm(d)))
                doc_chunks[:30] = sorted(doc_chunks[:30], key=lambda x: x.get("similarity", 0), reverse=True)
        except Exception:
            pass  # Fall back to order-based selection

        # Get top relevant chunks
        top_chunks = doc_chunks[:5]
        compare_context = "\n\n".join(
            f"[{c.get('section_title', 'Section')} p.{c.get('page_number', '?')}]: {c['content'][:400]}"
            for c in top_chunks
        )

        # Generate comparison
        client = _get_claude()
        if client is None:
            return {
                "related_chunks": top_chunks,
                "comparison": "_Comparison unavailable — Claude API not configured._",
            }

        compare_doc_title = doc_chunks[0].get("title", "comparison document") if doc_chunks else "document"

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=600,
            system="You are a biotech investment analyst comparing data across documents.",
            messages=[{"role": "user", "content": (
                f"**Slide content:**\n{slide_text[:1500]}\n\n"
                f"**Relevant sections from {compare_doc_title}:**\n{compare_context}\n\n"
                f"Compare these. What's consistent? What's different? "
                f"Any data discrepancies, updated numbers, or new info? Be specific."
            )}],
        )

        return {
            "compare_doc_title": compare_doc_title,
            "related_chunks": [{
                "content": c["content"][:300],
                "section_title": c.get("section_title", ""),
                "page_number": c.get("page_number", 0),
                "similarity": c.get("similarity", 0),
            } for c in top_chunks],
            "comparison": response.content[0].text,
        }

    except Exception as e:
        return {"error": str(e)}


# ===========================================================================
# 7. STATUS
# ===========================================================================

def get_deck_analyzer_status() -> dict:
    """Check if all components are available."""
    return {
        "pdfplumber_available": _get_pdfplumber() is not None,
        "pymupdf_available": _get_fitz() is not None,
        "claude_available": bool(ANTHROPIC_API_KEY),
        "rag_available": _get_rag_search() is not None,
        "ready": (
            _get_pdfplumber() is not None and
            bool(ANTHROPIC_API_KEY)
        ),
    }
