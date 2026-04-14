"""
Recover Missing PDFs — Re-download PDFs using stored source URLs.

For every document in the database that should have a PDF but doesn't have
one on disk, this script:
  1. Looks up the source_url from the per-company document_index.json
  2. Downloads the PDF from the original source
  3. Saves it to data/companies/{TICKER}/sources/
  4. Updates the file_path in the database
  5. Renders page images and caches them in the slide_images table

Usage:
    python recover_missing_pdfs.py                    # Recover all missing PDFs
    python recover_missing_pdfs.py --ticker BCYC      # Recover one company
    python recover_missing_pdfs.py --dry-run           # Preview what would be downloaded
    python recover_missing_pdfs.py --report            # Just show the report, no downloads

Requires: NEON_DATABASE_URL, LIBRARY_PATH (or defaults to ../services/data)
"""

import os
import sys
import json
import base64
import hashlib
import argparse
import ssl
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import requests

# Try PyMuPDF for image rendering
try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
LIBRARY_PATH = os.environ.get("LIBRARY_PATH", "")

# Fallback library path
if not LIBRARY_PATH:
    LIBRARY_PATH = str(Path(__file__).resolve().parent.parent / "services" / "data")


# ── File classification ──

PDF_EXTENSIONS = {".pdf"}
NON_RENDERABLE = {".xml", ".txt", ".csv", ".json", ".html", ".htm", ".md", ".tsv"}


def get_extension(filename: str, file_path: str) -> str:
    for name in [filename, file_path]:
        if name:
            ext = os.path.splitext(name)[1].lower()
            if ext:
                return ext
    return ""


def is_pdf_document(filename: str, file_path: str, doc_type: str) -> bool:
    """Check if this document is expected to be a PDF (i.e. should have images)."""
    ext = get_extension(filename, file_path)
    if ext in PDF_EXTENSIONS:
        return True
    if ext in NON_RENDERABLE:
        return False
    # No extension — check doc_type
    dt = (doc_type or "").lower()
    if any(k in dt for k in ["deck", "presentation", "poster", "sec_10k", "sec_10q", "sec_8k"]):
        return True
    return False


def find_file_on_disk(file_path: str, filename: str, ticker: str) -> str | None:
    """Try to find the file on disk."""
    # Direct path
    if file_path and os.path.isfile(file_path):
        return file_path
    # Directory + filename
    if file_path and os.path.isdir(file_path) and filename:
        combined = os.path.join(file_path, filename)
        if os.path.isfile(combined):
            return combined
    # Library paths
    basename = os.path.basename(file_path) if file_path else filename
    if not basename:
        return None
    search_dirs = [
        LIBRARY_PATH,
        os.path.join(LIBRARY_PATH, "companies", ticker, "sources") if ticker else "",
    ]
    for d in search_dirs:
        if not d:
            continue
        candidate = os.path.join(d, basename)
        if os.path.isfile(candidate):
            return candidate
    return None


def load_document_index(ticker: str) -> dict:
    """Load the per-company document_index.json metadata."""
    index_path = os.path.join(LIBRARY_PATH, "companies", ticker, "metadata", "document_index.json")
    if os.path.isfile(index_path):
        with open(index_path) as f:
            return json.load(f)
    return {}


def download_pdf(url: str, dest_path: str) -> bool:
    """Download a PDF from a URL. Returns True on success."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,*/*",
        }
        resp = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
        resp.raise_for_status()

        if len(resp.content) < 100:
            print(f"    Response too small ({len(resp.content)} bytes), skipping")
            return False

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        print(f"    Download failed: {e}")
        return False


def cache_slide_images(conn, doc_id: int, pdf_path: str) -> int:
    """Render PDF pages and cache in slide_images table. Returns count of images cached."""
    if not FITZ_AVAILABLE:
        return 0
    try:
        cur = conn.cursor()
        # Ensure table
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
        doc = fitz.open(pdf_path)
        cached = 0
        for i in range(len(doc)):
            page = doc[i]
            mat = fitz.Matrix(1.5, 1.5)
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
        cur.close()
        return cached
    except Exception as e:
        print(f"    Image caching failed: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Recover missing PDFs and cache slide images")
    parser.add_argument("--ticker", type=str, help="Process only this ticker")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no downloads")
    parser.add_argument("--report", action="store_true", help="Just show the full report")
    args = parser.parse_args()

    if not DATABASE_URL:
        print("ERROR: NEON_DATABASE_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Ensure slide_images table exists
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

    # Get all documents
    query = """
        SELECT d.id, d.ticker, d.filename, d.file_path, d.doc_type, d.title,
               d.page_count, d.word_count,
               (SELECT COUNT(*) FROM slide_images si WHERE si.document_id = d.id) as cached_images
        FROM documents d
    """
    params = []
    if args.ticker:
        query += " WHERE d.ticker = %s"
        params.append(args.ticker.upper())
    query += " ORDER BY d.ticker, d.id"

    cur.execute(query, params)
    documents = cur.fetchall()

    # Load all document indices by ticker
    doc_indices = {}

    # ── Classify every document ──
    stats = {
        "has_images": 0,
        "not_pdf": 0,
        "pdf_on_disk": 0,
        "has_source_url": 0,
        "no_source_url": 0,
        "downloaded": 0,
        "download_failed": 0,
        "images_cached": 0,
    }
    by_ticker = defaultdict(lambda: defaultdict(int))

    print(f"\n{'='*80}")
    print(f"  DOCUMENT RECOVERY & IMAGE PIPELINE")
    print(f"  Total documents: {len(documents)}")
    print(f"  Library path: {LIBRARY_PATH}")
    print(f"  Image renderer: {'PyMuPDF' if FITZ_AVAILABLE else 'NONE (install PyMuPDF!)'}")
    print(f"{'='*80}\n")

    for doc_id, ticker, filename, file_path, doc_type, title, page_count, word_count, cached_images in documents:
        ext = get_extension(filename, file_path)
        is_pdf = is_pdf_document(filename, file_path, doc_type)
        on_disk = find_file_on_disk(file_path, filename, ticker)
        display = (title or filename or "(untitled)")[:60]

        # Load document index for this ticker (cached)
        if ticker not in doc_indices:
            doc_indices[ticker] = load_document_index(ticker)
        index = doc_indices[ticker]

        # Look up source URL from metadata
        source_url = ""
        if filename and filename in index:
            source_url = index[filename].get("source_url", "")
        elif file_path:
            basename = os.path.basename(file_path)
            if basename in index:
                source_url = index[basename].get("source_url", "")

        # ── Already has images — all good ──
        if cached_images > 0:
            stats["has_images"] += 1
            by_ticker[ticker]["has_images"] += 1
            if args.report:
                print(f"  OK    [{ticker:>6}] {display}  ({cached_images} images)")
            continue

        # ── Not a PDF — report what it is ──
        if not is_pdf:
            stats["not_pdf"] += 1
            by_ticker[ticker]["not_pdf"] += 1
            if args.report:
                kind = ext if ext else doc_type or "unknown"
                print(f"  ──    [{ticker:>6}] {display}  ({kind}, no images needed)")
            continue

        # ── PDF is on disk but no images cached ──
        if on_disk:
            stats["pdf_on_disk"] += 1
            by_ticker[ticker]["fixable"] += 1
            print(f"  FIX   [{ticker:>6}] {display}")
            if not args.dry_run and not args.report:
                cached = cache_slide_images(conn, doc_id, on_disk)
                if cached:
                    stats["images_cached"] += 1
                    print(f"          → Cached {cached} images")
            continue

        # ── PDF not on disk — try to recover ──
        if source_url:
            stats["has_source_url"] += 1
            by_ticker[ticker]["recoverable"] += 1

            dest_dir = os.path.join(LIBRARY_PATH, "companies", ticker, "sources")
            dest_name = filename or os.path.basename(urlparse(source_url).path)
            dest_path = os.path.join(dest_dir, dest_name)

            print(f"  DL    [{ticker:>6}] {display}")
            print(f"          URL: {source_url[:80]}...")

            if args.dry_run or args.report:
                continue

            # Download
            if download_pdf(source_url, dest_path):
                stats["downloaded"] += 1
                print(f"          → Downloaded to {dest_name}")

                # Update file_path in database
                cur.execute("UPDATE documents SET file_path = %s WHERE id = %s", (dest_path, doc_id))

                # Cache images
                cached = cache_slide_images(conn, doc_id, dest_path)
                if cached:
                    stats["images_cached"] += 1
                    print(f"          → Cached {cached} images")
            else:
                stats["download_failed"] += 1
        else:
            stats["no_source_url"] += 1
            by_ticker[ticker]["no_url"] += 1
            if args.report:
                path_hint = os.path.basename(file_path) if file_path else "(no path)"
                print(f"  ??    [{ticker:>6}] {display}  →  {path_hint}  (no source URL)")

    cur.close()
    conn.close()

    # ── Summary ──
    print(f"\n{'='*80}")
    print(f"  RESULTS")
    print(f"{'='*80}")
    print(f"    Already have images:    {stats['has_images']}")
    print(f"    Not PDF (no images):    {stats['not_pdf']}")
    print(f"    PDF on disk → cached:   {stats['pdf_on_disk']}")
    print(f"    Recovered (downloaded): {stats['downloaded']}")
    print(f"    Download failed:        {stats['download_failed']}")
    print(f"    No source URL:          {stats['no_source_url']}")
    print(f"    Total images cached:    {stats['images_cached']}")
    print(f"{'='*80}")

    # Per-ticker summary
    print(f"\n  BY COMPANY:")
    for ticker in sorted(by_ticker.keys()):
        s = by_ticker[ticker]
        parts = []
        if s.get("has_images"): parts.append(f"{s['has_images']} OK")
        if s.get("fixable"): parts.append(f"{s['fixable']} fixable")
        if s.get("recoverable"): parts.append(f"{s['recoverable']} recoverable")
        if s.get("not_pdf"): parts.append(f"{s['not_pdf']} non-PDF")
        if s.get("no_url"): parts.append(f"{s['no_url']} no URL")
        print(f"    {ticker:<10} {', '.join(parts)}")

    print()


if __name__ == "__main__":
    main()
