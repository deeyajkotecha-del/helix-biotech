"""
Backfill Slide Images — Extract and cache page images for all existing documents.

This script finds all documents that have a PDF on disk but no cached images
in the slide_images table, renders each page as a JPEG, and stores the base64
in the database. After running, the deck analyzer will show slide images even
when PDFs are later removed (e.g., in cloud deployments like Railway).

Usage:
    python backfill_slide_images.py                  # Process all documents
    python backfill_slide_images.py --ticker LXEO    # Process only one company
    python backfill_slide_images.py --dry-run        # Preview what would be processed

Requires in .env:
    NEON_DATABASE_URL=postgresql://...
    LIBRARY_PATH=/path/to/data  (where company PDFs live)
"""

import os
import sys
import base64
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import psycopg2

# Try PyMuPDF first (better quality), fall back to pdfplumber
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    import pdfplumber
    from PIL import Image as PILImage
    import tempfile
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
LIBRARY_PATH = os.environ.get("LIBRARY_PATH", "")


def render_pages_fitz(pdf_path: str, max_pages: int = 60) -> list[dict]:
    """Render PDF pages as JPEG base64 using PyMuPDF (fast, high quality)."""
    images = []
    doc = fitz.open(pdf_path)
    for i in range(min(len(doc), max_pages)):
        page = doc[i]
        mat = fitz.Matrix(1.5, 1.5)  # 1.5x zoom
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("jpeg")
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        images.append({"page_number": i + 1, "image_b64": img_b64})
    doc.close()
    return images


def render_pages_pdfplumber(pdf_path: str, max_pages: int = 60) -> list[dict]:
    """Render PDF pages as JPEG base64 using pdfplumber (fallback)."""
    images = []
    MAX_DIM = 1500
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
                jpeg_path = tmp.name.replace(".png", ".jpg")
                pil_img.convert("RGB").save(jpeg_path, format="JPEG", quality=85)
                with open(jpeg_path, "rb") as f:
                    img_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
                os.unlink(tmp.name)
                os.unlink(jpeg_path)
            images.append({"page_number": i + 1, "image_b64": img_b64})
    return images


def render_pages(pdf_path: str) -> list[dict]:
    """Render pages using the best available library."""
    if FITZ_AVAILABLE:
        return render_pages_fitz(pdf_path)
    elif PDFPLUMBER_AVAILABLE:
        return render_pages_pdfplumber(pdf_path)
    else:
        print("ERROR: Neither PyMuPDF nor pdfplumber is installed. Cannot render pages.")
        sys.exit(1)


PDF_EXTENSIONS = {".pdf"}
SKIP_EXTENSIONS = {".xml", ".txt", ".csv", ".json", ".html", ".htm", ".md"}


def find_pdf_on_disk(file_path: str, filename: str, ticker: str) -> str | None:
    """Try to locate a PDF file on disk. Returns None for non-PDF files."""
    # Check the filename extension first — skip non-PDFs entirely
    check_name = filename or file_path or ""
    ext = os.path.splitext(check_name)[1].lower()
    if ext in SKIP_EXTENSIONS or ext not in PDF_EXTENSIONS:
        return None

    # If file_path is a directory (not a file), try appending the filename
    if file_path and os.path.isdir(file_path) and filename:
        combined = os.path.join(file_path, filename)
        if os.path.isfile(combined):
            return combined

    # Direct path — must be an actual file, not a directory
    if file_path and os.path.isfile(file_path):
        return file_path

    if not file_path and not filename:
        return None

    basename = os.path.basename(file_path) if file_path else filename

    # Try library paths
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


def main():
    parser = argparse.ArgumentParser(description="Backfill slide images for all documents")
    parser.add_argument("--ticker", type=str, help="Process only this ticker")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't write to DB")
    parser.add_argument("--force", action="store_true", help="Re-render even if images already cached")
    args = parser.parse_args()

    if not DATABASE_URL:
        print("ERROR: NEON_DATABASE_URL not set in environment")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Ensure the slide_images table exists
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

    # Find documents that need image extraction
    query = """
        SELECT d.id, d.ticker, d.filename, d.file_path, d.page_count,
               (SELECT COUNT(*) FROM slide_images si WHERE si.document_id = d.id) as cached_images
        FROM documents d
        WHERE d.file_path IS NOT NULL
    """
    params = []
    if args.ticker:
        query += " AND d.ticker = %s"
        params.append(args.ticker.upper())
    query += " ORDER BY d.ticker, d.id"

    cur.execute(query, params)
    documents = cur.fetchall()

    print(f"\n{'='*60}")
    print(f"  Slide Image Backfill")
    print(f"  Renderer: {'PyMuPDF' if FITZ_AVAILABLE else 'pdfplumber'}")
    print(f"  Documents found: {len(documents)}")
    print(f"{'='*60}\n")

    processed = 0
    skipped_cached = 0
    skipped_not_pdf = 0
    skipped_no_pdf = 0
    failed = 0

    for doc_id, ticker, filename, file_path, page_count, cached_images in documents:
        # Skip if already cached (unless --force)
        if cached_images > 0 and not args.force:
            skipped_cached += 1
            continue

        # Find PDF on disk (skips non-PDF files like .xml, .txt, etc.)
        pdf_path = find_pdf_on_disk(file_path, filename, ticker)
        if not pdf_path:
            # Distinguish "not a PDF" from "PDF not found on disk"
            check_name = filename or file_path or ""
            ext = os.path.splitext(check_name)[1].lower()
            if ext not in PDF_EXTENSIONS:
                skipped_not_pdf += 1
            else:
                skipped_no_pdf += 1
            continue

        print(f"  [{ticker}] {filename} ({page_count or '?'} pages)...", end=" ", flush=True)

        if args.dry_run:
            print("(dry run — would process)")
            processed += 1
            continue

        try:
            images = render_pages(pdf_path)
            if not images:
                print("no pages rendered")
                failed += 1
                continue

            # Delete old images if --force
            if args.force and cached_images > 0:
                cur.execute("DELETE FROM slide_images WHERE document_id = %s", (doc_id,))

            # Insert images
            for img in images:
                cur.execute(
                    """INSERT INTO slide_images (document_id, page_number, image_b64)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (document_id, page_number) DO NOTHING""",
                    (doc_id, img["page_number"], img["image_b64"]),
                )

            print(f"cached {len(images)} images")
            processed += 1

        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

    cur.close()
    conn.close()

    print(f"\n{'='*60}")
    print(f"  Results:")
    print(f"    Processed:          {processed}")
    print(f"    Skipped (cached):   {skipped_cached}")
    print(f"    Skipped (not PDF):  {skipped_not_pdf}  (XML, TXT, etc. — no images to render)")
    print(f"    Skipped (no file):  {skipped_no_pdf}  (PDF not found on disk)")
    print(f"    Failed:             {failed}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
