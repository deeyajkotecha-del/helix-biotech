"""
Document Image Audit — Full visibility into every document in the system.

Shows exactly what each document is, whether it has images cached,
whether a PDF exists on disk, and flags documents that SHOULD have
images but don't.

Usage:
    python audit_documents.py                  # Full audit
    python audit_documents.py --ticker LXEO    # Audit one company
    python audit_documents.py --problems-only  # Only show documents with issues

Requires: NEON_DATABASE_URL in .env
"""

import os
import sys
import argparse
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import psycopg2

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
LIBRARY_PATH = os.environ.get("LIBRARY_PATH", "")


def check_file_exists(file_path: str, filename: str, ticker: str) -> tuple[bool, str]:
    """Check if a document's file exists on disk. Returns (exists, resolved_path)."""
    if not file_path and not filename:
        return False, ""

    # Direct path
    if file_path and os.path.isfile(file_path):
        return True, file_path

    # If file_path is a directory, try with filename
    if file_path and os.path.isdir(file_path) and filename:
        combined = os.path.join(file_path, filename)
        if os.path.isfile(combined):
            return True, combined

    # Try library paths
    basename = os.path.basename(file_path) if file_path else filename
    if not basename:
        return False, ""

    search_dirs = [
        LIBRARY_PATH,
        os.path.join(LIBRARY_PATH, "companies", ticker, "sources") if ticker else "",
    ]
    for d in search_dirs:
        if not d:
            continue
        candidate = os.path.join(d, basename)
        if os.path.isfile(candidate):
            return True, candidate

    return False, file_path or ""


def get_file_extension(filename: str, file_path: str) -> str:
    """Get the file extension from filename or file_path."""
    for name in [filename, file_path]:
        if name:
            ext = os.path.splitext(name)[1].lower()
            if ext:
                return ext
    return "(none)"


def classify_document(filename: str, file_path: str, doc_type: str) -> tuple[str, bool]:
    """
    Classify a document and whether it SHOULD have slide images.
    Returns (category, should_have_images).
    """
    ext = get_file_extension(filename, file_path)
    dt = (doc_type or "").lower()
    fn = (filename or "").lower()

    # PDF documents — these SHOULD have images
    if ext == ".pdf":
        return "PDF document", True

    # PubMed XML articles
    if ext == ".xml" or "pmid" in fn:
        return "PubMed XML article", False

    # Plain text / clinical trials text dumps
    if ext == ".txt":
        return "Text file", False

    # JSON data files
    if ext == ".json":
        return "JSON data file", False

    # CSV data
    if ext == ".csv" or ext == ".tsv":
        return "Spreadsheet data", False

    # HTML content
    if ext in (".html", ".htm"):
        return "HTML page", False

    # SEC filings (often text-based, no PDF)
    if "sec" in dt or "10-k" in dt or "10-q" in dt or "8-k" in dt:
        return "SEC filing (text)", False

    # Clinical trials text
    if "trial" in dt or "clinical" in dt:
        return "Clinical trial data", False

    # No extension — check doc_type for clues
    if ext == "(none)":
        if "deck" in dt or "presentation" in dt or "poster" in dt:
            return "Presentation (missing file)", True
        if "publication" in dt or "pubmed" in dt:
            return "Publication (text)", False
        return f"Unknown (doc_type: {doc_type or 'none'})", False

    return f"Other ({ext})", False


def main():
    parser = argparse.ArgumentParser(description="Audit all documents for image status")
    parser.add_argument("--ticker", type=str, help="Audit only this ticker")
    parser.add_argument("--problems-only", action="store_true", help="Only show docs that should have images but don't")
    args = parser.parse_args()

    if not DATABASE_URL:
        print("ERROR: NEON_DATABASE_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    query = """
        SELECT
            d.id, d.ticker, d.filename, d.file_path, d.doc_type, d.title,
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
    cur.close()
    conn.close()

    # ── Analyze every document ──
    # Stats collectors
    by_ticker = defaultdict(lambda: {"total": 0, "has_images": 0, "needs_images": 0, "ok_no_images": 0})
    by_category = defaultdict(lambda: {"count": 0, "has_images": 0, "missing_images": 0})
    problems = []  # Documents that SHOULD have images but don't

    print(f"\n{'='*80}")
    print(f"  DOCUMENT IMAGE AUDIT")
    print(f"  Total documents: {len(documents)}")
    print(f"{'='*80}\n")

    if not args.problems_only:
        print(f"{'ID':>6}  {'Ticker':<8} {'Type':<28} {'Images':>6}  {'On Disk':>7}  {'Title'}")
        print(f"{'─'*6}  {'─'*8} {'─'*28} {'─'*6}  {'─'*7}  {'─'*40}")

    for doc_id, ticker, filename, file_path, doc_type, title, page_count, word_count, cached_images in documents:
        category, should_have_images = classify_document(filename, file_path, doc_type)
        file_exists, resolved_path = check_file_exists(file_path, filename, ticker)
        ext = get_file_extension(filename, file_path)

        # Track stats
        by_ticker[ticker]["total"] += 1
        by_category[category]["count"] += 1

        if cached_images > 0:
            by_ticker[ticker]["has_images"] += 1
            by_category[category]["has_images"] += 1
            status = "OK"
        elif should_have_images:
            by_ticker[ticker]["needs_images"] += 1
            by_category[category]["missing_images"] += 1
            if file_exists:
                status = "FIXABLE"  # PDF is on disk, can render images
                reason = "PDF on disk but no cached images"
            else:
                status = "MISSING"  # PDF not on disk
                reason = "PDF not found on disk"
            problems.append({
                "doc_id": doc_id, "ticker": ticker, "filename": filename,
                "title": title, "category": category, "status": status,
                "reason": reason, "file_path": resolved_path,
                "page_count": page_count,
            })
        else:
            by_ticker[ticker]["ok_no_images"] += 1
            status = "N/A"  # Not expected to have images

        if not args.problems_only:
            img_str = f"{cached_images}" if cached_images > 0 else ("NEED" if should_have_images else "—")
            disk_str = "yes" if file_exists else "no"
            display_title = (title or filename or "(no title)")[:50]
            print(f"{doc_id:>6}  {ticker:<8} {category:<28} {img_str:>6}  {disk_str:>7}  {display_title}")

    # ── Summary by document category ──
    print(f"\n\n{'='*80}")
    print(f"  BREAKDOWN BY DOCUMENT TYPE")
    print(f"{'='*80}\n")
    print(f"  {'Category':<32} {'Total':>6}  {'Has Img':>7}  {'Missing':>7}  {'Need Images?'}")
    print(f"  {'─'*32} {'─'*6}  {'─'*7}  {'─'*7}  {'─'*12}")
    for cat in sorted(by_category.keys(), key=lambda c: by_category[c]["count"], reverse=True):
        s = by_category[cat]
        need = "YES" if s["missing_images"] > 0 else "no"
        print(f"  {cat:<32} {s['count']:>6}  {s['has_images']:>7}  {s['missing_images']:>7}  {need}")

    # ── Summary by ticker ──
    print(f"\n\n{'='*80}")
    print(f"  BREAKDOWN BY COMPANY")
    print(f"{'='*80}\n")
    print(f"  {'Ticker':<10} {'Total':>6}  {'Has Img':>7}  {'Needs Img':>9}  {'No Img OK':>9}  {'Coverage'}")
    print(f"  {'─'*10} {'─'*6}  {'─'*7}  {'─'*9}  {'─'*9}  {'─'*10}")
    for ticker in sorted(by_ticker.keys()):
        s = by_ticker[ticker]
        imageable = s["has_images"] + s["needs_images"]
        coverage = f"{s['has_images']}/{imageable}" if imageable > 0 else "N/A"
        print(f"  {ticker:<10} {s['total']:>6}  {s['has_images']:>7}  {s['needs_images']:>9}  {s['ok_no_images']:>9}  {coverage}")

    # ── Problem documents ──
    if problems:
        print(f"\n\n{'='*80}")
        print(f"  DOCUMENTS THAT NEED IMAGES ({len(problems)} total)")
        print(f"{'='*80}\n")

        fixable = [p for p in problems if p["status"] == "FIXABLE"]
        missing = [p for p in problems if p["status"] == "MISSING"]

        if fixable:
            print(f"  FIXABLE — PDF on disk, just need to run backfill ({len(fixable)}):")
            for p in fixable:
                print(f"    [{p['ticker']}] {p['title'] or p['filename']}  (doc {p['doc_id']})")

        if missing:
            print(f"\n  MISSING — PDF not found, need to re-download ({len(missing)}):")
            for p in missing:
                path_hint = os.path.basename(p['file_path']) if p['file_path'] else '(no path)'
                print(f"    [{p['ticker']}] {p['title'] or p['filename']}  →  {path_hint}")
    else:
        print(f"\n  All documents that should have images already do!")

    print()


if __name__ == "__main__":
    main()
