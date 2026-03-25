"""
SatyaBio Data Pipeline — Single entry point for the full scrape + embed workflow.

Orchestrates five steps in the correct order:
  1. IR Scraping       — Download PDFs from company investor relations pages (ir_scraper.py)
  2. SEC + Trials      — Scrape SEC EDGAR filings + ClinicalTrials.gov (sec_trials_scraper.py)
  2b. FDA Regulatory   — Scrape FDA labels, approvals, CDER/CBER review PDFs (fda_scraper.py)
  3. PDF Embedding     — Extract text, chunk, embed, and store in Neon (embed_documents.py)
  4. Endpoint Extract  — Pull structured clinical data from embedded chunks (endpoint_extractor.py)

The order matters:
  - IR scraper downloads PDFs to data/companies/{TICKER}/sources/
  - SEC+trials scraper embeds directly into Neon (no PDF download step)
  - Embedder processes the PDFs from step 1 and stores vectors in Neon
  - Running the embedder BEFORE the IR scraper would miss all the new PDFs
  - Endpoint extraction runs AFTER embedding because it reads from embedded chunks

Usage:
    python3 pipeline.py --all                     # Full pipeline, all 60 companies
    python3 pipeline.py --ticker NUVL,RVMD        # Specific companies only
    python3 pipeline.py --all --skip-ir           # Skip IR scraping (PDFs already downloaded)
    python3 pipeline.py --all --skip-sec          # Skip SEC + trials scraping
    python3 pipeline.py --all --skip-embed        # Skip embedding (just scrape)
    python3 pipeline.py --all --skip-endpoints    # Skip endpoint extraction
    python3 pipeline.py --all --endpoints-only    # Only run endpoint extraction
    python3 pipeline.py --all --dry-run           # Preview everything without executing
    python3 pipeline.py --all --fresh             # Wipe Neon DB and re-embed from scratch
    python3 pipeline.py --list                    # List all tracked companies

Requires in .env:
    NEON_DATABASE_URL=postgresql://...
    VOYAGE_API_KEY=your-voyage-key
    ANTHROPIC_API_KEY=your-anthropic-key  (for endpoint extraction)

Optional in .env:
    LIBRARY_PATH=/path/to/data   (defaults to backend/services/data if not set)
"""

import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# ── Make sure sibling modules are importable ──
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# Also add the search directory so embed_documents is importable
_SEARCH_DIR = os.path.join(os.path.dirname(_THIS_DIR), "search")
if _SEARCH_DIR not in sys.path:
    sys.path.insert(0, _SEARCH_DIR)

from company_config import ONCOLOGY_COMPANIES, get_all_oncology_tickers


# ── Helpers ──

def _banner(title: str, detail: str = ""):
    """Print a visible section banner."""
    width = 60
    print(f"\n{'='*width}")
    print(f"  {title}")
    if detail:
        print(f"  {detail}")
    print(f"{'='*width}\n")


def _timestamp() -> str:
    """Current time as a readable string."""
    return datetime.now().strftime("%H:%M:%S")


def _resolve_tickers(args) -> list[str]:
    """Parse ticker argument into a validated list."""
    if args.all:
        return sorted(ONCOLOGY_COMPANIES.keys())
    elif args.ticker:
        tickers = [t.strip().upper() for t in args.ticker.split(",")]
        for t in tickers:
            if t not in ONCOLOGY_COMPANIES:
                print(f"  WARNING: {t} is not in company_config.py — skipping")
        return [t for t in tickers if t in ONCOLOGY_COMPANIES]
    return []


def _list_companies():
    """Print all tracked companies grouped by category."""
    by_cat = {}
    for ticker, info in sorted(ONCOLOGY_COMPANIES.items()):
        cat = info.get("category", "other")
        by_cat.setdefault(cat, []).append((ticker, info["name"]))

    for cat, companies in sorted(by_cat.items()):
        print(f"\n  {cat.upper()} ({len(companies)} companies)")
        for ticker, name in companies:
            print(f"    {ticker:6s}  {name}")

    print(f"\n  Total: {len(ONCOLOGY_COMPANIES)} companies tracked\n")


# ── Step 1: IR Scraping ──

def run_ir_scraper(tickers: list[str], dry_run: bool = False) -> dict:
    """
    Download PDFs from company IR pages.
    Returns {ticker: [list of downloaded doc dicts]}.
    """
    _banner("STEP 1: IR Page Scraping", f"Companies: {len(tickers)} | Dry run: {dry_run}")

    try:
        from ir_scraper import OncologyScraper
    except ImportError as e:
        print(f"  ERROR: Could not import ir_scraper: {e}")
        print("  Make sure curl-cffi and beautifulsoup4 are installed.")
        print("  Skipping IR scraping.\n")
        return {}

    results = {}
    with OncologyScraper() as scraper:
        for ticker in tickers:
            if ticker not in ONCOLOGY_COMPANIES:
                continue
            print(f"\n  [{_timestamp()}] Scraping IR pages for {ticker}...")
            try:
                docs = scraper.scrape_company(ticker, dry_run=dry_run)
                results[ticker] = docs
                count = len(docs) if docs else 0
                print(f"  [{_timestamp()}] {ticker}: {count} documents found")
            except Exception as e:
                print(f"  [{_timestamp()}] {ticker}: ERROR — {e}")
                results[ticker] = []

    total = sum(len(v) for v in results.values())
    print(f"\n  IR Scraping complete: {total} documents across {len(results)} companies\n")
    return results


# ── Step 2: SEC + Clinical Trials ──

def run_sec_trials(tickers: list[str], dry_run: bool = False,
                   sec_only: bool = False, trials_only: bool = False) -> int:
    """
    Scrape SEC EDGAR and ClinicalTrials.gov, embed directly into Neon.
    Returns total documents added.
    """
    sources = []
    if not trials_only:
        sources.append("SEC EDGAR")
    if not sec_only:
        sources.append("ClinicalTrials.gov")

    _banner("STEP 2: SEC + Clinical Trials", f"Companies: {len(tickers)} | Sources: {', '.join(sources)}")

    DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")

    if not DATABASE_URL or not VOYAGE_API_KEY:
        print("  ERROR: NEON_DATABASE_URL and VOYAGE_API_KEY must be set in .env")
        print("  Skipping SEC + trials scraping.\n")
        return 0

    try:
        from sec_trials_scraper import process_company
        import psycopg2
        import voyageai
    except ImportError as e:
        print(f"  ERROR: Could not import sec_trials_scraper: {e}")
        print("  Skipping SEC + trials scraping.\n")
        return 0

    conn = psycopg2.connect(DATABASE_URL)
    vo_client = voyageai.Client(api_key=VOYAGE_API_KEY)

    total_added = 0
    for ticker in tickers:
        if ticker not in ONCOLOGY_COMPANIES:
            continue
        print(f"\n  [{_timestamp()}] Processing {ticker}...")
        try:
            added = process_company(
                ticker, ONCOLOGY_COMPANIES[ticker], conn, vo_client,
                sec_only=sec_only, trials_only=trials_only, dry_run=dry_run,
            )
            total_added += added if added else 0
        except Exception as e:
            print(f"  [{_timestamp()}] {ticker}: ERROR — {e}")

    conn.close()
    print(f"\n  SEC + Trials complete: {total_added} documents added to Neon\n")
    return total_added


# ── Step 2b: FDA Regulatory Data ──

def run_fda_scraper(tickers: list[str], dry_run: bool = False,
                    labels_only: bool = False, approvals_only: bool = False) -> int:
    """
    Scrape FDA data: drug labels, approval history, review documents.
    Embeds directly into Neon.
    Returns total documents added.
    """
    _banner("STEP 2b: FDA Regulatory Data", f"Companies: {len(tickers)} | Dry run: {dry_run}")

    DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")

    if not DATABASE_URL or not VOYAGE_API_KEY:
        print("  ERROR: NEON_DATABASE_URL and VOYAGE_API_KEY must be set in .env")
        print("  Skipping FDA scraping.\n")
        return 0

    try:
        from fda_scraper import process_company as fda_process_company
        import psycopg2
        import voyageai
    except ImportError as e:
        print(f"  ERROR: Could not import fda_scraper: {e}")
        print("  Skipping FDA scraping.\n")
        return 0

    conn = psycopg2.connect(DATABASE_URL)
    vo_client = voyageai.Client(api_key=VOYAGE_API_KEY)

    total_added = 0
    for ticker in tickers:
        if ticker not in ONCOLOGY_COMPANIES:
            continue
        print(f"\n  [{_timestamp()}] Processing FDA data for {ticker}...")
        try:
            added = fda_process_company(
                ticker, ONCOLOGY_COMPANIES[ticker], conn, vo_client,
                labels_only=labels_only, approvals_only=approvals_only, dry_run=dry_run,
            )
            total_added += added if added else 0
        except Exception as e:
            print(f"  [{_timestamp()}] {ticker}: ERROR — {e}")

    conn.close()
    print(f"\n  FDA scraping complete: {total_added} documents added to Neon\n")
    return total_added


# ── Step 3: PDF Embedding ──

def run_embedder(tickers: list[str], fresh: bool = False) -> int:
    """
    Embed downloaded PDFs into Neon via Voyage AI.
    Returns count of newly embedded documents.
    """
    _banner("STEP 3: PDF Embedding", f"Companies: {len(tickers)} | Fresh re-embed: {fresh}")

    DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")

    if not DATABASE_URL or not VOYAGE_API_KEY:
        print("  ERROR: NEON_DATABASE_URL and VOYAGE_API_KEY must be set in .env")
        print("  Skipping embedding.\n")
        return 0

    # Figure out where PDFs live — use LIBRARY_PATH if set, else default to
    # the data/ folder that ir_scraper.py downloads into
    library_path = os.environ.get("LIBRARY_PATH", "")
    if not library_path:
        # Default: backend/services/data (same as ir_scraper.py's DATA_DIR)
        library_path = str(Path(__file__).parent.parent / "data")
        print(f"  LIBRARY_PATH not set, using default: {library_path}")

    try:
        from embed_documents import (
            process_document, semantic_chunk_document, COMPANY_NAMES,
            EMBED_MODEL, CHUNK_SIZE, is_duplicate_pdf
        )
        import psycopg2
        import voyageai
    except ImportError as e:
        print(f"  ERROR: Could not import embed_documents: {e}")
        print("  Skipping embedding.\n")
        return 0

    conn = psycopg2.connect(DATABASE_URL)
    vo_client = voyageai.Client(api_key=VOYAGE_API_KEY)

    # If --fresh, wipe existing embeddings so everything re-processes
    if fresh:
        print("  Clearing all existing embeddings for a fresh start...")
        cur = conn.cursor()
        cur.execute("DELETE FROM chunks")
        cur.execute("DELETE FROM documents")
        conn.commit()
        cur.close()
        print("  Database wiped. Re-embedding all documents.\n")

    # Load metadata file if it exists (for titles/dates from IR scraper)
    import json
    metadata_lookup = {}
    metadata_path = os.path.join(library_path, "downloads", "oncology_metadata.json")
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

    companies_dir = os.path.join(library_path, "companies")
    if not os.path.isdir(companies_dir):
        print(f"  ERROR: Companies folder not found at {companies_dir}")
        print("  Have you run the IR scraper first? (Step 1)")
        print("  Skipping embedding.\n")
        return 0

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
        print(f"\n  [{_timestamp()}] {ticker} — {name} ({len(pdfs)} PDFs{f', {skipped} dupes skipped' if skipped else ''})")

        for pdf_name in pdfs:
            pdf_path = os.path.join(sources_dir, pdf_name)
            meta = metadata_lookup.get(pdf_name, {})
            try:
                was_new = process_document(conn, vo_client, ticker, pdf_name, pdf_path, meta)
                if was_new:
                    total_new += 1
            except Exception as e:
                print(f"    ERROR embedding {pdf_name}: {e}")

    conn.close()
    print(f"\n  Embedding complete: {total_new} new documents embedded\n")
    return total_new


# ── Step 4: Clinical Endpoint Extraction ──

def run_endpoint_extraction(tickers: list[str], dry_run: bool = False) -> int:
    """
    Extract structured clinical endpoints from embedded chunks using Claude.
    Requires: chunks in Neon (from Step 3) + ANTHROPIC_API_KEY.
    Returns total endpoints stored.
    """
    _banner("STEP 4: Clinical Endpoint Extraction", f"Companies: {len(tickers)} | Dry run: {dry_run}")

    DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

    if not DATABASE_URL:
        print("  ERROR: NEON_DATABASE_URL must be set in .env")
        print("  Skipping endpoint extraction.\n")
        return 0

    if not ANTHROPIC_API_KEY:
        print("  ERROR: ANTHROPIC_API_KEY must be set in .env for endpoint extraction")
        print("  Skipping endpoint extraction.\n")
        return 0

    try:
        from endpoint_extractor import run_extraction
        from endpoints_setup import setup_tables
        import psycopg2
        import anthropic
    except ImportError as e:
        print(f"  ERROR: Could not import endpoint modules: {e}")
        print("  Skipping endpoint extraction.\n")
        return 0

    conn = psycopg2.connect(DATABASE_URL)

    # Ensure the clinical_endpoints table exists
    try:
        setup_tables(conn)
    except Exception as e:
        print(f"  WARNING: Table setup issue (may already exist): {e}")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # run_extraction handles its own batching and progress output
    run_extraction(conn, client, tickers=tickers, dry_run=dry_run)

    conn.close()
    return 0  # run_extraction prints its own stats


# ── Main ──

def main():
    parser = argparse.ArgumentParser(
        description="SatyaBio Data Pipeline — scrape IR + SEC + trials + FDA, then embed PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 pipeline.py --all                  Full pipeline, all companies
  python3 pipeline.py --ticker NUVL,RVMD     Specific companies only
  python3 pipeline.py --all --skip-ir        Skip IR scraping (PDFs already downloaded)
  python3 pipeline.py --all --skip-embed     Just scrape, don't embed yet
  python3 pipeline.py --all --fda-only       Only run the FDA scraper
  python3 pipeline.py --all --dry-run        Preview without executing
  python3 pipeline.py --list                 List all tracked companies
        """,
    )
    parser.add_argument("--ticker", type=str, help="Comma-separated tickers (e.g. NUVL,RVMD)")
    parser.add_argument("--all", action="store_true", help="Process all 60 companies")
    parser.add_argument("--list", action="store_true", help="List all tracked companies and exit")
    parser.add_argument("--skip-ir", action="store_true", help="Skip step 1 (IR page scraping)")
    parser.add_argument("--skip-sec", action="store_true", help="Skip step 2 (SEC + trials)")
    parser.add_argument("--skip-fda", action="store_true", help="Skip step 2b (FDA regulatory data)")
    parser.add_argument("--skip-embed", action="store_true", help="Skip step 3 (PDF embedding)")
    parser.add_argument("--fda-only", action="store_true", help="Only run the FDA scraper (skip all other steps)")
    parser.add_argument("--sec-only", action="store_true", help="In step 2, only scrape SEC filings")
    parser.add_argument("--trials-only", action="store_true", help="In step 2, only scrape ClinicalTrials.gov")
    parser.add_argument("--skip-endpoints", action="store_true", help="Skip step 4 (endpoint extraction)")
    parser.add_argument("--endpoints-only", action="store_true", help="Only run endpoint extraction (skip all other steps)")
    parser.add_argument("--dry-run", action="store_true", help="Preview all steps without executing")
    parser.add_argument("--fresh", action="store_true", help="Wipe Neon DB before embedding (use with caution!)")
    args = parser.parse_args()

    # Just list companies and exit
    if args.list:
        _list_companies()
        return

    # Need --all or --ticker
    if not args.all and not args.ticker:
        parser.print_help()
        sys.exit(1)

    tickers = _resolve_tickers(args)
    if not tickers:
        print("No valid tickers to process.")
        sys.exit(1)

    # Safety check for --fresh
    if args.fresh:
        print("\n  ⚠  WARNING: --fresh will DELETE all existing data in Neon and re-embed everything.")
        print("  This is irreversible. Make sure you really want to do this.\n")
        confirm = input("  Type 'yes' to confirm: ").strip().lower()
        if confirm != "yes":
            print("  Cancelled.")
            return

    start_time = time.time()

    _banner(
        "SatyaBio Data Pipeline",
        f"Started at {_timestamp()} | Companies: {len(tickers)} | Dry run: {args.dry_run}"
    )

    # If --fda-only, skip everything except FDA
    if args.fda_only:
        fda_added = run_fda_scraper(tickers, dry_run=args.dry_run)
        elapsed = time.time() - start_time
        _banner("Pipeline Complete", f"Total time: {int(elapsed//60)}m {int(elapsed%60)}s")
        print(f"  FDA documents added: {fda_added}")
        print()
        return

    # If --endpoints-only, skip everything except endpoint extraction
    if args.endpoints_only:
        run_endpoint_extraction(tickers, dry_run=args.dry_run)
        elapsed = time.time() - start_time
        _banner("Pipeline Complete", f"Total time: {int(elapsed//60)}m {int(elapsed%60)}s")
        return

    # ── Step 1: IR Scraping ──
    ir_results = {}
    if not args.skip_ir:
        ir_results = run_ir_scraper(tickers, dry_run=args.dry_run)
    else:
        print("\n  Skipping Step 1 (IR scraping) — --skip-ir flag set\n")

    # ── Step 2: SEC + Clinical Trials ──
    sec_added = 0
    if not args.skip_sec:
        sec_added = run_sec_trials(
            tickers, dry_run=args.dry_run,
            sec_only=args.sec_only, trials_only=args.trials_only,
        )
    else:
        print("\n  Skipping Step 2 (SEC + trials) — --skip-sec flag set\n")

    # ── Step 2b: FDA Regulatory Data ──
    fda_added = 0
    if not args.skip_fda:
        fda_added = run_fda_scraper(tickers, dry_run=args.dry_run)
    else:
        print("\n  Skipping Step 2b (FDA) — --skip-fda flag set\n")

    # ── Step 3: PDF Embedding ──
    embed_count = 0
    if not args.skip_embed and not args.dry_run:
        embed_count = run_embedder(tickers, fresh=args.fresh)
    elif args.dry_run:
        print("\n  Skipping Step 3 (embedding) — dry run mode\n")
    else:
        print("\n  Skipping Step 3 (embedding) — --skip-embed flag set\n")

    # ── Step 4: Clinical Endpoint Extraction ──
    if not args.skip_endpoints and not args.dry_run:
        run_endpoint_extraction(tickers, dry_run=args.dry_run)
    elif args.dry_run:
        print("\n  Skipping Step 4 (endpoint extraction) — dry run mode\n")
    else:
        print("\n  Skipping Step 4 (endpoint extraction) — --skip-endpoints flag set\n")

    # ── Summary ──
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    ir_total = sum(len(v) for v in ir_results.values())

    _banner("Pipeline Complete", f"Total time: {minutes}m {seconds}s")
    print(f"  Step 1  (IR Scraping):    {ir_total} documents downloaded")
    print(f"  Step 2  (SEC + Trials):   {sec_added} documents added to Neon")
    print(f"  Step 2b (FDA Regulatory): {fda_added} documents added to Neon")
    print(f"  Step 3  (PDF Embedding):  {embed_count} new documents embedded")
    print(f"  Step 4  (Endpoints):      see extraction log above")
    print()


if __name__ == "__main__":
    main()
