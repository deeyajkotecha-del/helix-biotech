#!/usr/bin/env python3
"""
One-command refresh for all new Helix Biotech tickers.

Runs the full IR scraping pipeline on your server/laptop using curl-cffi
(bypasses bot detection) with Playwright fallback for JS-rendered pages.

Usage:
    # From helix-biotech root directory:
    python scripts/refresh_all_new.py                  # All 16 new tickers
    python scripts/refresh_all_new.py CLDX IMVT        # Specific tickers only
    python scripts/refresh_all_new.py --dry-run         # Preview what it would scrape
    python scripts/refresh_all_new.py --scrape-only     # Just scrape, skip analysis
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path
from datetime import datetime

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "services"))
sys.path.insert(0, str(BACKEND_DIR / "services" / "scraper"))

# All 16 new tickers
NEW_TICKERS = [
    "AUTL", "ANNX", "PRAX", "CLDX", "AXSM", "DYN", "MBX", "RAPT",
    "AGIO", "IMVT", "ALKS", "FOLD", "HRMY", "KRYS", "MPLT", "SLN"
]


def check_dependencies():
    """Check that all required packages are installed."""
    missing = []

    try:
        import curl_cffi
        print("  ✅ curl-cffi installed")
    except ImportError:
        missing.append("curl-cffi")
        print("  ❌ curl-cffi NOT installed — required for bot detection bypass")

    try:
        from bs4 import BeautifulSoup
        print("  ✅ beautifulsoup4 installed")
    except ImportError:
        missing.append("beautifulsoup4")
        print("  ❌ beautifulsoup4 NOT installed")

    try:
        from playwright.sync_api import sync_playwright
        print("  ✅ playwright installed")
    except ImportError:
        print("  ⚠ playwright NOT installed (optional — fallback for JS-heavy sites)")
        print("    Install with: pip install playwright && playwright install chromium")

    try:
        import pymupdf
        print("  ✅ pymupdf installed (PDF processing)")
    except ImportError:
        try:
            import fitz
            print("  ✅ pymupdf (fitz) installed (PDF processing)")
        except ImportError:
            print("  ⚠ pymupdf NOT installed (needed for PDF analysis, not scraping)")

    if missing:
        print(f"\n❌ Missing required packages: {', '.join(missing)}")
        print(f"   Install with: pip install {' '.join(missing)}")
        return False

    return True


def scrape_ir_pages(tickers: list, dry_run: bool = False):
    """
    Scrape IR pages for all tickers using the backend curl-cffi scraper.
    This is the scraper that bypasses Akamai/Q4 bot detection.
    """
    try:
        from scraper.ir_scraper import OncologyIRScraper
    except ImportError:
        # Try alternative import paths
        try:
            sys.path.insert(0, str(BACKEND_DIR / "services" / "scraper"))
            from ir_scraper import OncologyIRScraper
        except ImportError as e:
            print(f"❌ Cannot import IR scraper: {e}")
            print("   Make sure you're running from the helix-biotech directory")
            return

    from scraper.company_config import ONCOLOGY_COMPANIES

    scraper = OncologyIRScraper()

    for ticker in tickers:
        config = ONCOLOGY_COMPANIES.get(ticker)
        if not config:
            print(f"\n⚠ {ticker}: Not in company_config.py — skipping IR scrape")
            continue

        print(f"\n{'='*60}")
        print(f"  📥 {ticker} — {config['name']}")
        print(f"     Pages: {len(config['pages'])}")
        for page in config['pages']:
            print(f"       [{page['type']}] {page['url']}")
        print(f"{'='*60}")

        if dry_run:
            print("     (dry run — skipping)")
            continue

        try:
            results = scraper.scrape_company(ticker)
            total_docs = len(results.get("documents", []))
            print(f"     ✅ Found {total_docs} documents")
            for doc in results.get("documents", [])[:5]:
                print(f"        📄 {doc.get('title', '')[:80]}")
        except Exception as e:
            print(f"     ❌ Error: {e}")


async def run_master_refresh(tickers: list, dry_run: bool = False):
    """
    Run the full master refresh pipeline (scrape → analyze → normalize → verify).
    This is the heavyweight pipeline that does everything including Vision API analysis.
    """
    try:
        from services.master_refresh import MasterRefresh
    except ImportError as e:
        print(f"⚠ Master refresh not available: {e}")
        print("  Falling back to scrape-only mode")
        scrape_ir_pages(tickers, dry_run)
        return

    for ticker in tickers:
        print(f"\n{'='*60}")
        print(f"  🔄 Full refresh: {ticker}")
        print(f"{'='*60}")

        if dry_run:
            print("     (dry run — skipping)")
            continue

        try:
            refresher = MasterRefresh(ticker, verbose=True)
            result = await refresher.refresh(
                months_back=18,
                max_presentations=10,
                max_slides_per_pdf=50
            )
            print(f"     Status: {result['status']}")
        except Exception as e:
            print(f"     ❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Refresh IR data for new Helix Biotech tickers"
    )
    parser.add_argument("tickers", nargs="*", help="Specific tickers (default: all 16 new)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without scraping")
    parser.add_argument("--scrape-only", action="store_true", help="Just scrape IR pages, skip Vision analysis")
    parser.add_argument("--check", action="store_true", help="Check dependencies and exit")

    args = parser.parse_args()
    tickers = [t.upper() for t in args.tickers] if args.tickers else NEW_TICKERS

    print(f"🧬 Helix Biotech IR Refresh")
    print(f"   Tickers: {', '.join(tickers)}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Mode: {'dry run' if args.dry_run else 'scrape only' if args.scrape_only else 'full refresh'}")
    print()

    # Check dependencies
    print("📋 Checking dependencies...")
    deps_ok = check_dependencies()
    if args.check:
        return

    if not deps_ok:
        print("\n⚠ Fix missing dependencies before running the scraper.")
        return

    print()

    if args.scrape_only:
        scrape_ir_pages(tickers, args.dry_run)
    else:
        asyncio.run(run_master_refresh(tickers, args.dry_run))

    print(f"\n{'='*60}")
    print(f"  ✅ Done! Check data/companies/{{TICKER}}/sources/ for results")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
