#!/usr/bin/env python3
"""
Scrape oncology company IR pages for presentations and press releases.

Usage:
    python scripts/scrape_oncology.py                         # scrape all companies
    python scripts/scrape_oncology.py --ticker NUVL            # single company
    python scripts/scrape_oncology.py --ticker NUVL --dry-run  # find links only
    python scripts/scrape_oncology.py --list                   # list configured companies
    python scripts/scrape_oncology.py --stats                  # show download stats
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.scrapers.oncology_config import ONCOLOGY_COMPANIES, get_all_oncology_tickers
from app.services.scrapers.oncology_scraper import OncologyScraper


def cmd_list():
    """List all configured oncology companies."""
    print(f"{'Ticker':<8} {'Name':<30} {'Pages':<6} {'Platforms'}")
    print("-" * 70)
    for ticker, config in ONCOLOGY_COMPANIES.items():
        platforms = ", ".join(sorted(set(p.get("platform", "standard") for p in config["pages"])))
        print(f"{ticker:<8} {config['name']:<30} {len(config['pages']):<6} {platforms}")
    print(f"\nTotal: {len(ONCOLOGY_COMPANIES)} companies")


def cmd_stats(scraper: OncologyScraper):
    """Show metadata statistics."""
    stats = scraper.get_stats()
    if stats["total_documents"] == 0:
        print("No documents downloaded yet.")
        return

    print(f"Total documents: {stats['total_documents']}")
    print(f"Total size:      {stats['total_size_mb']} MB")
    print(f"Duplicates:      {stats['duplicates']}")
    print()
    print(f"{'Ticker':<8} {'Documents':<12} {'Size (MB)'}")
    print("-" * 35)
    for ticker, data in sorted(stats["companies"].items()):
        size_mb = round(data["size_bytes"] / (1024 * 1024), 1)
        print(f"{ticker:<8} {data['documents']:<12} {size_mb}")


def cmd_probe(scraper: OncologyScraper, ticker: str | None):
    """Probe each page URL and print a summary table."""
    results = scraper.probe_pages(ticker)

    print(f"\n{'Ticker':<7} {'Page':<16} {'Status':<8} {'Docs':<15} {'OK'}")
    print("-" * 60)

    ok_count = 0
    fail_count = 0
    for r in results:
        status = str(r["status_code"] or "ERR")
        docs = f"{r['doc_count']} PDFs found" if r["status_code"] and r["status_code"] < 400 else "0 PDFs found"
        if r["error"]:
            ok_mark = "x"
            note = r["error"].split("\n")[0][:30]
            docs = f"0 PDFs found  ({note})"
            fail_count += 1
        elif r["doc_count"] == 0 and r["status_code"] and r["status_code"] < 400:
            ok_mark = "?"
            docs = "0 PDFs found  (JS-rendered?)"
            fail_count += 1
        else:
            ok_mark = "v"
            ok_count += 1

        print(f"{r['ticker']:<7} {r['page_type']:<16} {status:<8} {docs:<28} {ok_mark}")

    print(f"\n{ok_count} pages OK, {fail_count} pages need attention")


def cmd_scrape(scraper: OncologyScraper, ticker: str | None, dry_run: bool):
    """Run the scraper for one or all companies."""
    if dry_run:
        cmd_probe(scraper, ticker)
        return

    if ticker:
        ticker = ticker.upper()
        if ticker not in ONCOLOGY_COMPANIES:
            print(f"Error: {ticker} not in oncology config. Use --list to see available companies.")
            sys.exit(2)
        results = scraper.scrape_company(ticker)
        print(f"\n{ticker}: {len(results)} new document(s) downloaded")
    else:
        all_results = scraper.scrape_all()
        total = 0
        for t, results in all_results.items():
            count = len(results)
            total += count
            if count > 0:
                print(f"  {t}: {count} new document(s) downloaded")
        print(f"\nTotal: {total} new document(s) downloaded across {len(all_results)} companies")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape oncology company IR pages for presentations and press releases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                   List all configured companies
  %(prog)s --ticker NUVL --dry-run  Find links without downloading
  %(prog)s --ticker NUVL            Download documents for NUVL
  %(prog)s                          Download documents for all companies
  %(prog)s --stats                  Show download statistics
        """,
    )
    parser.add_argument("--ticker", help="Scrape a single company (e.g., NUVL)")
    parser.add_argument("--dry-run", action="store_true", help="Find document links without downloading")
    parser.add_argument("--list", action="store_true", help="List all configured oncology companies")
    parser.add_argument("--stats", action="store_true", help="Show download metadata statistics")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.list:
        cmd_list()
        return

    with OncologyScraper() as scraper:
        if args.stats:
            cmd_stats(scraper)
            return

        cmd_scrape(scraper, args.ticker, args.dry_run)


if __name__ == "__main__":
    main()
