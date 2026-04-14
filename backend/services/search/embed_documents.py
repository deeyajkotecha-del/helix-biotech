"""
SatyaBio Document Embedder v2 — Upgraded with better model and semantic chunking.

CHANGES FROM v1:
  - Embedding model: voyage-3-lite (512d) -> voyage-3 (1024d)
  - Chunking: Fixed 500-word -> Semantic chunking at section boundaries (800 words, 150 overlap)
  - Section detection: Identifies headers in biotech docs (Clinical Results, Pipeline, etc.)
  - Larger chunks: 800 words captures full clinical data discussions without splitting

Usage:
    python embed_documents.py              # Process all new documents
    python embed_documents.py --ticker NUVL # Process only one company
    python embed_documents.py --reembed    # Re-process everything (fresh start)

Requires in .env:
    NEON_DATABASE_URL=postgresql://...
    VOYAGE_API_KEY=your-voyage-key
    LIBRARY_PATH=/path/to/backend/services/data  (or let pipeline.py handle this)
"""

import os
import sys
import json
import re
import argparse
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import pdfplumber
import voyageai

# OCR for image-only PDFs (conference posters, KM curves, etc.)
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# PyMuPDF for rendering page images to cache in slide_images table
try:
    import fitz as _fitz_module
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

# --- Config ---
DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
LIBRARY_PATH = os.environ.get("LIBRARY_PATH", "")

# ── UPGRADED SETTINGS ──
CHUNK_SIZE = 800          # words per chunk (was 500)
CHUNK_OVERLAP = 150       # overlapping words (was 75)
EMBED_MODEL = "voyage-3"  # 1024 dims, full model (was voyage-3-lite / 512)
EMBED_BATCH_SIZE = 16     # Smaller batches for larger model (was 32)

# ── Dedup: skip _1 duplicate PDFs created by the IR scraper ──
DUPLICATE_SUFFIX_RE = re.compile(r"_\d+\.pdf$", re.IGNORECASE)

def is_duplicate_pdf(filename: str, all_filenames: list[str]) -> bool:
    """
    Check if a file is a _1, _2, etc. duplicate of another PDF.
    e.g. '3409daae...pdf' and '3409daae..._1.pdf' — skip the _1 version.
    """
    match = DUPLICATE_SUFFIX_RE.search(filename)
    if not match:
        return False
    # The original would be the same name without _1
    base = filename[:match.start()] + ".pdf"
    return base.lower() in [f.lower() for f in all_filenames]

# ── OCR: Keywords that indicate a PDF has valuable biotech/scientific content ──
BIOTECH_OCR_KEYWORDS = [
    # Clinical data
    "kaplan-meier", "kaplan meier", "km curve", "overall survival",
    "progression-free", "progression free", "pfs", "os ",
    "overall response", "orr", "complete response", "partial response",
    "waterfall plot", "swimmer plot", "forest plot", "hazard ratio",
    "confidence interval", "median duration", "dose escalation",
    "dose-response", "dose response",
    # Drug/trial terms
    "phase 1", "phase 2", "phase 3", "phase i", "phase ii", "phase iii",
    "clinical trial", "nct0", "endpoint", "primary endpoint",
    "secondary endpoint", "adverse event", "treatment-related",
    "pharmacokinetic", "pk ", "auc", "cmax", "half-life",
    # Molecular/mechanism
    "ic50", "ic₅₀", "ec50", "mechanism of action", "moa",
    "receptor", "inhibitor", "kinase", "antibody", "conjugate",
    "brain penetr", "cns penetr", "tumor volume",
    # Financial/corporate
    "revenue", "pipeline", "market cap", "cash position",
    "guidance", "milestone",
]

# Ticker -> company name mapping (all 60 companies from xbi_scraper.py)
COMPANY_NAMES = {
    # Core small/mid-cap oncology
    "CNTA": "Centessa Pharmaceuticals",
    "NUVL": "Nuvalent",
    "CELC": "Celcuity",
    "PYXS": "Pyxis Oncology",
    "RVMD": "Revolution Medicines",
    "RLAY": "Relay Therapeutics",
    "IOVA": "Iovance Biotherapeutics",
    "VIR": "Vir Biotechnology",
    "JANX": "Janux Therapeutics",
    "CGON": "CG Oncology",
    "URGN": "UroGen Pharma",
    "VSTM": "Verastem Oncology",
    "IBRX": "ImmunityBio",
    "TNGX": "Tango Therapeutics",
    "BCYC": "Bicycle Therapeutics",
    "ARGX": "argenx",
    "KYMR": "Kymera Therapeutics",
    "ALKS": "Alkermes",
    "VKTX": "Viking Therapeutics",
    "GPCR": "Structure Therapeutics",
    "ORKA": "Oruka Therapeutics",
    # XBI top holdings / notable biotechs
    "MRNA": "Moderna",
    "ROIV": "Roivant Sciences",
    "PCVX": "Vaxcyte",
    "SRPT": "Sarepta Therapeutics",
    "SMMT": "Summit Therapeutics",
    "INSM": "Insmed",
    "EXAS": "Exact Sciences",
    "NBIX": "Neurocrine Biosciences",
    "CRNX": "Crinetics Pharmaceuticals",
    "DAWN": "Day One Biopharmaceuticals",
    "RCUS": "Arcus Biosciences",
    # Big pharma
    "PFE": "Pfizer",
    "MRK": "Merck",
    "AZN": "AstraZeneca",
    "GILD": "Gilead Sciences",
    "LLY": "Eli Lilly",
    "BMY": "Bristol-Myers Squibb",
    "ABBV": "AbbVie",
    "AMGN": "Amgen",
    "REGN": "Regeneron",
    "TAK": "Takeda",
    "JNJ": "Johnson & Johnson",
    "RHHBY": "Roche / Genentech",
    "NVS": "Novartis",
    "SNY": "Sanofi",
    "GSK": "GSK",
    "NVO": "Novo Nordisk",
    "DSNKY": "Daiichi Sankyo",
    "VRTX": "Vertex Pharmaceuticals",
    "BIIB": "Biogen",
    "ALNY": "Alnylam Pharmaceuticals",
    "IONS": "Ionis Pharmaceuticals",
    "MDGL": "Madrigal Pharmaceuticals",
    "MRTI": "Mirati Therapeutics",
    "SAGE": "Sage Therapeutics",
    "AXSM": "Axsome Therapeutics",
    "ESALY": "Eisai",
    "BILH": "Boehringer Ingelheim",
    "AGTSY": "Astellas Pharma",
}

# ── Section header patterns for biotech documents ──
SECTION_PATTERNS = [
    r"^(?:ABSTRACT|INTRODUCTION|BACKGROUND|METHODS|RESULTS|DISCUSSION|CONCLUSIONS?|REFERENCES)\s*$",
    r"^(?:Clinical\s+(?:Results|Data|Endpoints?|Activity|Efficacy|Safety))",
    r"^(?:Preclinical\s+(?:Data|Results|Activity))",
    r"^(?:Pharmacokinetics?|PK(?:/PD)?|Pharmacodynamics?)\b",
    r"^(?:Study\s+Design|Trial\s+Design|Patient\s+(?:Population|Demographics|Characteristics))",
    r"^(?:Safety\s+(?:Profile|Data|Summary)|(?:Adverse|Serious Adverse)\s+Events?)",
    r"^(?:Efficacy|Overall\s+(?:Response|Survival)|Progression.Free\s+Survival)",
    r"^(?:Pipeline|Portfolio|Product\s+Candidates?|Lead\s+Programs?)",
    r"^(?:Financial\s+(?:Summary|Highlights|Results|Overview))",
    r"^(?:Risk\s+Factors?|Forward.Looking\s+Statements?)",
    r"^(?:Management(?:'s)?\s+Discussion|MD&A)",
    r"^(?:Executive\s+Summary|Business\s+Overview|Company\s+Overview)",
    r"^(?:Intellectual\s+Property|Patents?|Regulatory)",
    r"^(?:Manufacturing|CMC|Chemistry,?\s+Manufacturing)",
    r"^(?:Competitive\s+Landscape|Market\s+(?:Opportunity|Overview))",
    r"^\d+(?:\.\d+)*\s+[A-Z]",
    r"^[A-Z][A-Z\s&,/-]{10,}$",
]
SECTION_RE = re.compile("|".join(SECTION_PATTERNS), re.MULTILINE | re.IGNORECASE)


def check_env():
    """Verify all required environment variables are set."""
    missing = []
    if not DATABASE_URL: missing.append("NEON_DATABASE_URL")
    if not VOYAGE_API_KEY: missing.append("VOYAGE_API_KEY")
    if not LIBRARY_PATH: missing.append("LIBRARY_PATH")
    if missing:
        print(f"\nERROR: Missing environment variables: {', '.join(missing)}")
        print("Add them to your .env file in the satyabio-paper-agent folder.\n")
        sys.exit(1)


def extract_text_with_pages(pdf_path: str) -> list[dict]:
    """Extract text from PDF, returning a list of {page: int, text: str}."""
    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    text = text.encode('utf-8', errors='replace').decode('utf-8')
                    pages.append({"page": i + 1, "text": text})
    except Exception as e:
        print(f"    Warning: Could not extract text: {e}")
    return pages


def ocr_extract_text(pdf_path: str) -> list[dict]:
    """
    OCR fallback for image-only PDFs (conference posters, KM curves, etc.).
    Converts each page to an image, runs Tesseract, and returns pages list.
    Only keeps the PDF if OCR text contains biotech-relevant keywords.
    """
    if not OCR_AVAILABLE:
        return []

    try:
        images = convert_from_path(pdf_path, dpi=200)
    except Exception as e:
        print(f"    OCR: Could not convert PDF to images: {e}")
        return []

    pages = []
    for i, img in enumerate(images):
        try:
            text = pytesseract.image_to_string(img)
            if text and text.strip():
                text = text.encode('utf-8', errors='replace').decode('utf-8')
                pages.append({"page": i + 1, "text": text})
        except Exception as e:
            print(f"    OCR: Error on page {i+1}: {e}")

    if not pages:
        return []

    # Check if the OCR'd content contains biotech-relevant keywords
    all_text_lower = " ".join(p["text"] for p in pages).lower()
    matches = [kw for kw in BIOTECH_OCR_KEYWORDS if kw in all_text_lower]

    if matches:
        print(f"    OCR: Found biotech content ({', '.join(matches[:3])}...)")
        return pages
    else:
        print(f"    OCR: No biotech-relevant content found, skipping.")
        return []


def semantic_chunk_document(pages: list[dict], chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    UPGRADED chunking: Splits at natural section boundaries when possible,
    falls back to word-count splitting. Tracks section titles and page ranges.
    """
    if not pages:
        return []

    # Build a stream of (word, page_num, is_section_start, section_title)
    word_stream = []
    for page_data in pages:
        page_num = page_data["page"]
        lines = page_data["text"].split("\n")
        for line in lines:
            stripped = line.strip()
            is_header = bool(SECTION_RE.match(stripped)) if stripped else False
            words = line.split()
            for i, word in enumerate(words):
                word_stream.append({
                    "word": word,
                    "page": page_num,
                    "is_section_start": is_header and i == 0,
                    "section_title": stripped if (is_header and i == 0) else "",
                })

    if not word_stream:
        return []

    chunks = []
    current_words = []
    current_start_page = word_stream[0]["page"]
    current_section = ""

    for idx, w in enumerate(word_stream):
        current_words.append(w["word"])

        if w["is_section_start"] and w["section_title"]:
            if len(current_words) >= int(chunk_size * 0.5):
                chunk_text = " ".join(current_words[:-1])
                if chunk_text.strip():
                    chunks.append({
                        "content": chunk_text,
                        "page_number": current_start_page,
                        "section_title": current_section,
                        "token_count": len(current_words) - 1,
                    })
                overlap_start = max(0, len(current_words) - 1 - overlap)
                current_words = current_words[overlap_start:]
                current_start_page = w["page"]
                current_section = w["section_title"]
                continue
            current_section = w["section_title"]

        if len(current_words) >= chunk_size:
            is_near_boundary = False
            lookahead_limit = min(idx + int(chunk_size * 0.2), len(word_stream) - 1)
            for future_idx in range(idx + 1, lookahead_limit + 1):
                if word_stream[future_idx]["is_section_start"]:
                    is_near_boundary = True
                    break

            if not is_near_boundary or len(current_words) >= int(chunk_size * 1.3):
                chunk_text = " ".join(current_words)
                chunks.append({
                    "content": chunk_text,
                    "page_number": current_start_page,
                    "section_title": current_section,
                    "token_count": len(current_words),
                })
                current_words = current_words[-overlap:]
                current_start_page = w["page"]

    if current_words:
        chunk_text = " ".join(current_words)
        if chunk_text.strip():
            chunks.append({
                "content": chunk_text,
                "page_number": current_start_page,
                "section_title": current_section,
                "token_count": len(current_words),
            })

    return chunks


def embed_chunks(vo_client, chunks: list[dict]) -> list[list[float]]:
    """Generate embeddings for chunks using Voyage AI, in batches."""
    all_embeddings = []
    texts = [c["content"] for c in chunks]

    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i:i + EMBED_BATCH_SIZE]
        try:
            result = vo_client.embed(batch, model=EMBED_MODEL, input_type="document")
            all_embeddings.extend(result.embeddings)
        except Exception as e:
            print(f"    Embedding error on batch {i}: {e}")
            all_embeddings.extend([None] * len(batch))

        if i + EMBED_BATCH_SIZE < len(texts):
            time.sleep(0.3)

    return all_embeddings


def cache_slide_images(conn, doc_id: int, file_path: str):
    """Render PDF pages and cache as base64 JPEG in the slide_images table."""
    if not FITZ_AVAILABLE:
        return  # Silently skip if PyMuPDF isn't installed

    cur = conn.cursor()
    try:
        # Ensure table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS slide_images (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                image_b64 TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(document_id, page_number)
            )
        """)

        # Render each page
        import base64
        doc = _fitz_module.open(file_path)
        cached = 0
        for i in range(len(doc)):
            page = doc[i]
            mat = _fitz_module.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            img_b64 = base64.b64encode(pix.tobytes("jpeg")).decode("utf-8")
            cur.execute(
                """INSERT INTO slide_images (document_id, page_number, image_b64)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (document_id, page_number) DO NOTHING""",
                (doc_id, i + 1, img_b64),
            )
            cached += 1
        doc.close()
        conn.commit()
        print(f"    Cached {cached} slide images for doc {doc_id}")
    except Exception as e:
        print(f"    Slide image caching failed (non-fatal): {e}")
    finally:
        cur.close()


def process_document(conn, vo_client, ticker: str, filename: str, file_path: str, metadata: dict):
    """Process a single PDF: extract, semantic-chunk, embed, and store."""
    cur = conn.cursor()

    cur.execute("SELECT id FROM documents WHERE ticker = %s AND filename = %s", (ticker, filename))
    existing = cur.fetchone()
    if existing:
        print(f"    Skipping {filename} (already embedded)")
        cur.close()
        return False

    print(f"    Extracting text from {filename}...")
    pages = extract_text_with_pages(file_path)
    if not pages:
        # Try OCR for image-only PDFs (posters, KM curves, clinical figures)
        if OCR_AVAILABLE:
            print(f"    No selectable text — trying OCR...")
            pages = ocr_extract_text(file_path)
        if not pages:
            print(f"    No usable text in {filename}, skipping.")
            cur.close()
            return False

    # Strip NUL bytes that some PDFs produce (causes PostgreSQL errors)
    for p in pages:
        p["text"] = p["text"].replace("\x00", "")

    total_words = sum(len(p["text"].split()) for p in pages)
    print(f"    {total_words} words across {len(pages)} pages")

    chunks = semantic_chunk_document(pages)
    sections_found = sum(1 for c in chunks if c.get("section_title"))
    print(f"    Split into {len(chunks)} semantic chunks ({sections_found} with section headers)")

    print(f"    Generating embeddings ({EMBED_MODEL}, 1024-dim)...")
    embeddings = embed_chunks(vo_client, chunks)

    file_size = os.path.getsize(file_path)
    cur.execute("""
        INSERT INTO documents (ticker, company_name, filename, file_path, doc_type, title, date, word_count, page_count, file_size_bytes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        ticker,
        COMPANY_NAMES.get(ticker, ticker),
        filename,
        file_path,
        metadata.get("doc_type", ""),
        metadata.get("title", filename.replace(".pdf", "")),
        metadata.get("date", ""),
        total_words,
        len(pages),
        file_size,
    ))
    doc_id = cur.fetchone()[0]

    stored = 0
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        if embedding is None:
            continue
        cur.execute("""
            INSERT INTO chunks (document_id, chunk_index, page_number, section_title, content, token_count, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
        """, (
            doc_id, i,
            chunk["page_number"],
            chunk.get("section_title", ""),
            chunk["content"],
            chunk["token_count"],
            str(embedding),
        ))
        stored += 1

    conn.commit()
    cur.close()
    print(f"    Stored {stored} chunks for {filename}")

    # Cache slide images so the deck analyzer can show them even without the PDF
    cache_slide_images(conn, doc_id, file_path)

    return True


def main():
    parser = argparse.ArgumentParser(description="Embed biotech documents for RAG search (v2 — upgraded)")
    parser.add_argument("--ticker", type=str, help="Process only this ticker (e.g. NUVL)")
    parser.add_argument("--reembed", action="store_true", help="Delete all existing data and re-embed everything")
    args = parser.parse_args()

    check_env()

    print("\n" + "="*60)
    print("  SatyaBio Document Embedder v2")
    print(f"  Model: {EMBED_MODEL} (1024 dimensions)")
    print(f"  Chunk size: {CHUNK_SIZE} words, {CHUNK_OVERLAP} overlap")
    print(f"  Strategy: Semantic chunking with section detection")
    print("="*60 + "\n")

    conn = psycopg2.connect(DATABASE_URL)
    vo_client = voyageai.Client(api_key=VOYAGE_API_KEY)

    if args.reembed:
        print("Clearing all existing embeddings...")
        cur = conn.cursor()
        cur.execute("DELETE FROM chunks")
        cur.execute("DELETE FROM documents")
        conn.commit()
        cur.close()
        print("Done. Re-embedding all documents.\n")

    metadata_lookup = {}
    metadata_path = os.path.join(LIBRARY_PATH, "downloads", "oncology_metadata.json")
    if os.path.isfile(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                raw = json.load(f)
            for url, meta in raw.items():
                fp = meta.get("file_path", "")
                if fp:
                    metadata_lookup[os.path.basename(fp)] = meta
        except Exception:
            pass

    companies_dir = os.path.join(LIBRARY_PATH, "companies")
    if not os.path.isdir(companies_dir):
        print(f"ERROR: Companies folder not found at {companies_dir}")
        print(f"  LIBRARY_PATH = {LIBRARY_PATH!r}")
        print(f"  Resolved to: {os.path.abspath(companies_dir)}")
        print(f"  Hint: Set LIBRARY_PATH=backend/services/data in your .env")
        sys.exit(1)

    tickers = [args.ticker.upper()] if args.ticker else sorted(os.listdir(companies_dir))
    total_new = 0

    for ticker in tickers:
        sources_dir = os.path.join(companies_dir, ticker, "sources")
        if not os.path.isdir(sources_dir):
            continue

        all_pdfs = [f for f in sorted(os.listdir(sources_dir)) if f.lower().endswith(".pdf")]
        if not all_pdfs:
            continue

        # Filter out _1, _2, etc. duplicates
        pdfs = [f for f in all_pdfs if not is_duplicate_pdf(f, all_pdfs)]
        skipped = len(all_pdfs) - len(pdfs)

        name = COMPANY_NAMES.get(ticker, ticker)
        print(f"\n{'='*50}")
        print(f"  {ticker} -- {name} ({len(pdfs)} PDFs{f', {skipped} duplicates skipped' if skipped else ''})")
        print(f"{'='*50}")

        for pdf_name in pdfs:
            pdf_path = os.path.join(sources_dir, pdf_name)
            meta = metadata_lookup.get(pdf_name, {})
            was_new = process_document(conn, vo_client, ticker, pdf_name, pdf_path, meta)
            if was_new:
                total_new += 1

    conn.close()

    print(f"\n{'='*50}")
    print(f"  Done! Embedded {total_new} new documents.")
    print(f"  Model: {EMBED_MODEL} | Chunks: {CHUNK_SIZE}w | Index: HNSW")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
