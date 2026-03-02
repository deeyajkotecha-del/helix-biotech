#!/usr/bin/env python3
"""
Scrape oncology company IR pages for presentations and press releases.

Usage:
    python scripts/scrape_oncology.py                         # scrape all companies
    python scripts/scrape_oncology.py --ticker NUVL            # single company
    python scripts/scrape_oncology.py --ticker NUVL --dry-run  # find links only
    python scripts/scrape_oncology.py --list                   # list configured companies
    python scripts/scrape_oncology.py --stats                  # show download stats
    python scripts/scrape_oncology.py --monitor                # staleness check only
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.scrapers.oncology_config import ONCOLOGY_COMPANIES, get_all_oncology_tickers
from app.services.scrapers.oncology_scraper import OncologyScraper

METADATA_FILE = PROJECT_ROOT / "data" / "downloads" / "oncology_metadata.json"
MONITOR_FILE = PROJECT_ROOT / "data" / "downloads" / "monitor_history.json"
STALE_DAYS = 90
CONSECUTIVE_ZERO_THRESHOLD = 3


# ── Monitor: history persistence ─────────────────────────────────────


def _load_history() -> dict:
    if MONITOR_FILE.exists():
        try:
            return json.loads(MONITOR_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"runs": []}


def _save_history(history: dict) -> None:
    MONITOR_FILE.parent.mkdir(parents=True, exist_ok=True)
    MONITOR_FILE.write_text(json.dumps(history, indent=2))


def _load_metadata() -> dict:
    if METADATA_FILE.exists():
        try:
            data = json.loads(METADATA_FILE.read_text())
            data.pop("_errors", None)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def record_run(scrape_results: dict[str, list]) -> None:
    """Append a scrape run to monitor_history.json."""
    history = _load_history()
    history["runs"].append({
        "date": date.today().isoformat(),
        "timestamp": datetime.now().isoformat(),
        "results": {
            ticker: {"new_docs": len(docs)}
            for ticker, docs in scrape_results.items()
        },
    })
    _save_history(history)


# ── Monitor: analysis ────────────────────────────────────────────────


def _newest_doc_date(metadata: dict, ticker: str) -> str | None:
    """Find the most recent document date for a ticker."""
    dates = [
        meta["date"]
        for meta in metadata.values()
        if isinstance(meta, dict)
        and meta.get("ticker") == ticker
        and not meta.get("duplicate_of")
        and meta.get("date")
    ]
    return max(dates) if dates else None


def _doc_count(metadata: dict, ticker: str) -> int:
    """Count non-duplicate documents for a ticker."""
    return sum(
        1 for meta in metadata.values()
        if isinstance(meta, dict)
        and meta.get("ticker") == ticker
        and not meta.get("duplicate_of")
    )


def _consecutive_zero_runs(history: dict, ticker: str) -> int:
    """Count consecutive runs (most recent first) with 0 new docs."""
    count = 0
    for run in reversed(history.get("runs", [])):
        results = run.get("results", {})
        if ticker not in results:
            continue
        if results[ticker]["new_docs"] == 0:
            count += 1
        else:
            break
    return count


# ── Monitor: report ──────────────────────────────────────────────────


def cmd_monitor():
    """Print staleness report for all configured companies."""
    metadata = _load_metadata()
    history = _load_history()
    today = date.today()
    tickers = get_all_oncology_tickers()

    print(f"\n--- Staleness Monitor ({today.isoformat()}) ---\n")

    stale = 0
    watch = 0
    ok = 0

    for ticker in tickers:
        config = ONCOLOGY_COMPANIES.get(ticker, {})
        newest = _newest_doc_date(metadata, ticker)
        total = _doc_count(metadata, ticker)
        zero_runs = _consecutive_zero_runs(history, ticker)

        if total == 0:
            # No documents at all
            has_direct = bool(config.get("direct_links"))
            hint = "(needs direct_links)" if not has_direct else "(check direct_links)"
            print(f"  [STALE] {ticker} — no documents at all {hint}")
            stale += 1
        elif not newest:
            # Has docs but all dates are null
            if zero_runs >= CONSECUTIVE_ZERO_THRESHOLD:
                print(f"  [WATCH] {ticker} — 0 new docs for {zero_runs} consecutive runs ({total} total, no dates)")
                watch += 1
            else:
                print(f"  [OK]    {ticker} — {total} docs (no dates available)")
                ok += 1
        else:
            days_ago = (today - date.fromisoformat(newest)).days
            if days_ago < 0:
                # Future date (from upcoming conference mapping) — not stale
                if zero_runs >= CONSECUTIVE_ZERO_THRESHOLD:
                    print(f"  [WATCH] {ticker} — 0 new docs for {zero_runs} consecutive runs (newest: {newest})")
                    watch += 1
                else:
                    print(f"  [OK]    {ticker} — newest doc is {newest} (upcoming)")
                    ok += 1
            elif days_ago > STALE_DAYS:
                print(f"  [STALE] {ticker} — newest doc is {newest} ({days_ago} days ago)")
                stale += 1
            elif zero_runs >= CONSECUTIVE_ZERO_THRESHOLD:
                print(f"  [WATCH] {ticker} — 0 new docs for {zero_runs} consecutive runs (newest: {newest})")
                watch += 1
            else:
                print(f"  [OK]    {ticker} — newest doc is {newest} ({days_ago} days ago)")
                ok += 1

    print(f"\n  {ok} OK, {stale} STALE, {watch} WATCH")

    run_count = len(history.get("runs", []))
    if run_count > 0:
        last = history["runs"][-1]
        print(f"  Run history: {run_count} run(s), last on {last['date']}")
    else:
        print("  Run history: no runs recorded yet")


# ── Existing commands ────────────────────────────────────────────────


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

        # Record single-company run and show monitor
        record_run({ticker: results})
        cmd_monitor()
    else:
        all_results = scraper.scrape_all()
        total = 0
        for t, results in all_results.items():
            count = len(results)
            total += count
            if count > 0:
                print(f"  {t}: {count} new document(s) downloaded")
        print(f"\nTotal: {total} new document(s) downloaded across {len(all_results)} companies")

        # Record full run and show monitor
        record_run(all_results)
        cmd_monitor()


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
  %(prog)s --monitor                Show staleness report
        """,
    )
    parser.add_argument("--ticker", help="Scrape a single company (e.g., NUVL)")
    parser.add_argument("--dry-run", action="store_true", help="Find document links without downloading")
    parser.add_argument("--list", action="store_true", help="List all configured oncology companies")
    parser.add_argument("--stats", action="store_true", help="Show download metadata statistics")
    parser.add_argument("--monitor", action="store_true", help="Show staleness report (no scraping)")
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

    if args.monitor:
        cmd_monitor()
        return

    with OncologyScraper() as scraper:
        if args.stats:
            cmd_stats(scraper)
            return

        cmd_scrape(scraper, args.ticker, args.dry_run)


if __name__ == "__main__":
    main()
