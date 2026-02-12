"""
CLI for extracting company data from IR presentations (v2.1 schema).

Usage:
    python -m app.cli.extract --ticker EWTX --pdf ~/Downloads/ewtx_jpm_2026.pdf
    python -m app.cli.extract --ticker EWTX --pdf ~/Downloads/ewtx_jpm_2026.pdf --dry-run -v
    python -m app.cli.extract --ticker EWTX --pdf ~/Downloads/ewtx_jpm_2026.pdf --force
    python -m app.cli.extract --ticker EWTX --pdf ~/Downloads/ewtx_jpm_2026.pdf --asset Sevasemten
    python -m app.cli.extract --ticker ARGX --url https://businesswire.com/news/...
    python -m app.cli.extract --inbox
    python -m app.cli.extract --priority HIGH
    python -m app.cli.extract --list

Inbox workflow:
    1. Download PDFs to ~/helix/inbox/
    2. Run: python -m app.cli.extract --inbox
    3. PDFs are processed and moved to ~/helix/inbox/processed/
"""

import argparse
import json
import logging
import re
import shutil
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Extract company data from IR presentations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m app.cli.extract --ticker ASND
    python -m app.cli.extract --ticker ASND --pdf ~/Downloads/presentation.pdf
    python -m app.cli.extract --priority HIGH
    python -m app.cli.extract --priority HIGH --dry-run
    python -m app.cli.extract --all --rate-limit 5
    python -m app.cli.extract --list
        """
    )

    # Target selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--ticker", "-t",
        type=str,
        help="Single company ticker to process"
    )
    group.add_argument(
        "--priority", "-p",
        type=str,
        choices=["HIGH", "MED-HIGH", "MEDIUM", "MED-LOW", "LOW"],
        help="Process all companies of this priority"
    )
    group.add_argument(
        "--all", "-a",
        action="store_true",
        help="Process all companies in the IR mapping"
    )
    group.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available companies and exit"
    )
    group.add_argument(
        "--inbox", "-i",
        action="store_true",
        help="Process all PDFs in ~/helix/inbox/"
    )

    # Options
    parser.add_argument(
        "--pdf",
        type=str,
        help="Path to existing PDF (skips scraping for --ticker)"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="URL to fetch text from (press release, SEC filing, etc.)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't save files, just show what would be extracted"
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=2.0,
        help="Seconds between API calls (default: 2.0)"
    )
    parser.add_argument(
        "--keywords",
        type=str,
        nargs="+",
        help="Keywords to filter presentations (e.g., 'Corporate' 'Presentation')"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--output-json",
        type=str,
        help="Save results to JSON file"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing files (skip merge)"
    )
    parser.add_argument(
        "--asset",
        type=str,
        help="Extract a single asset only (Pass 2 only, use with --ticker)"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompts"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Import here to avoid startup delay
    from app.services.extraction.orchestrator import (
        ExtractionOrchestrator,
        process_company,
        process_batch
    )
    from app.services.scrapers.ir_website_mapping import (
        IR_WEBSITE_MAP,
        get_companies_by_priority,
        get_all_tickers,
        print_summary
    )

    results = []

    try:
        # List mode
        if args.list:
            print_summary()
            return 0

        # Inbox mode
        if args.inbox:
            return _process_inbox(args, IR_WEBSITE_MAP)

        # Create orchestrator
        orchestrator = ExtractionOrchestrator(
            rate_limit_seconds=args.rate_limit,
            dry_run=args.dry_run,
            force_overwrite=getattr(args, 'force', False)
        )

        # Single ticker
        if args.ticker:
            ticker = args.ticker.upper()
            if ticker not in IR_WEBSITE_MAP:
                logger.warning(f"{ticker} not in IR mapping, will attempt anyway")

            pdf_path = Path(args.pdf) if args.pdf else None

            # URL mode: fetch text from URL
            source_text = None
            source_name = None
            if getattr(args, 'url', None):
                source_text, source_name = _fetch_url_text(args.url)
                if not source_text:
                    logger.error("Failed to fetch text from URL")
                    return 1

            result = orchestrator.process_company(
                ticker=ticker,
                pdf_path=pdf_path,
                keywords=args.keywords,
                asset_name=getattr(args, 'asset', None),
                source_text=source_text,
                source_name=source_name
            )
            results = [result]
            _print_result(result)

        # Priority batch
        elif args.priority:
            tickers = get_companies_by_priority(args.priority)
            logger.info(f"Processing {len(tickers)} {args.priority} priority companies")
            logger.info(f"Companies: {', '.join(tickers)}")

            results = orchestrator.process_batch(tickers, keywords=args.keywords)
            _print_batch_summary(results)

        # All companies
        elif args.all:
            tickers = get_all_tickers()
            logger.info(f"Processing ALL {len(tickers)} companies")

            if not args.yes:
                confirm = input(f"Process {len(tickers)} companies? [y/N] ")
                if confirm.lower() != "y":
                    logger.info("Cancelled")
                    return 0

            results = orchestrator.process_batch(tickers, keywords=args.keywords)
            _print_batch_summary(results)

        # Save results to JSON if requested
        if args.output_json and results:
            output_path = Path(args.output_json)
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {output_path}")

        # Return code based on results
        if results:
            failed = sum(1 for r in results if r["status"] == "failed")
            if failed > 0:
                return 1

        return 0

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        return 1


def _fetch_url_text(url: str) -> tuple[str | None, str | None]:
    """Fetch a URL and extract clean text from HTML."""
    import httpx
    from bs4 import BeautifulSoup
    from urllib.parse import urlparse

    logger.info(f"Fetching URL: {url}")
    try:
        resp = httpx.get(
            url,
            follow_redirects=True,
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch URL: {e}")
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script, style, nav, footer, header elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
        tag.decompose()

    # Try to find the main content area (site-specific selectors first)
    main = (
        soup.find("div", class_="bw-release-story")       # BusinessWire
        or soup.find("div", class_="article-body")         # GlobeNewsWire
        or soup.find("div", id="main-body-container")      # GlobeNewsWire alt
        or soup.find("article")
        or soup.find("main")
        or soup.find(class_=lambda c: c and "article" in c.lower() if isinstance(c, str) else False)
        or soup.body
    )

    text = main.get_text(separator="\n", strip=True) if main else soup.get_text(separator="\n", strip=True)

    # Collapse blank lines
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)

    # Source name from URL
    parsed = urlparse(url)
    source_name = f"{parsed.netloc}{parsed.path}"
    if len(source_name) > 80:
        source_name = source_name[:80]

    logger.info(f"Extracted {len(text)} chars from {parsed.netloc}")

    # Warn if too little text (likely JS-rendered page)
    if len(text) < 500:
        logger.warning(
            f"Only {len(text)} chars extracted — page may require JavaScript rendering. "
            f"Try the company's direct IR page or save the page as text/PDF instead."
        )

    return text, source_name


def _print_result(result: dict):
    """Print a single extraction result."""
    ticker = result["ticker"]
    status = result["status"]

    status_emoji = {
        "success": "[OK]",
        "partial": "[PARTIAL]",
        "failed": "[FAIL]",
        "pending": "[...]"
    }.get(status, "[?]")

    print(f"\n{status_emoji} {ticker}")

    if result.get("pdf_path"):
        print(f"    PDF: {result['pdf_path']}")

    if result.get("extraction_summary"):
        summary = result["extraction_summary"]
        assets = summary.get("assets_extracted", [])
        print(f"    Files: {summary.get('files_generated', 0)}")
        if assets:
            print(f"    Assets: {', '.join(assets)}")
        print(f"    Mode: {summary.get('merge_mode', 'unknown')}")

    if result.get("extracted_files"):
        print(f"    Files saved: {len(result['extracted_files'])}")

    # Show validation results
    if result.get("validation"):
        valid_count = sum(1 for v in result["validation"] if v["valid"])
        total_count = len(result["validation"])
        print(f"    Validation: {valid_count}/{total_count} files valid")

        for v in result["validation"]:
            score = v.get("completeness_score", 0)
            status_str = "PASS" if v["valid"] else "FAIL"
            print(f"      [{status_str}] {v['file']} (completeness: {score:.0%})")
            for err in v.get("errors", []):
                print(f"        ERROR: {err}")
            # Only show warnings in verbose mode
            if logging.getLogger().level <= logging.DEBUG:
                for warn in v.get("warnings", []):
                    print(f"        WARN: {warn}")

    if result.get("errors"):
        for error in result["errors"]:
            print(f"    ERROR: {error}")


def _print_batch_summary(results: list[dict]):
    """Print summary of batch extraction."""
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    partial = sum(1 for r in results if r["status"] == "partial")
    failed = sum(1 for r in results if r["status"] == "failed")

    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Total:   {total}")
    print(f"Success: {success}")
    print(f"Partial: {partial}")
    print(f"Failed:  {failed}")

    if failed > 0:
        print("\nFailed companies:")
        for r in results:
            if r["status"] == "failed":
                errors = r.get("errors", ["Unknown error"])
                print(f"  {r['ticker']}: {errors[0]}")


def _process_inbox(args, ir_map: dict) -> int:
    """Process all PDFs in the inbox folder."""
    from app.services.extraction.orchestrator import ExtractionOrchestrator
    from app.services.extraction.pdf_extractor import extract_text_with_markers

    inbox_dir = Path.home() / "helix" / "inbox"
    processed_dir = inbox_dir / "processed"

    # Ensure directories exist
    inbox_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Find all PDFs in inbox
    pdfs = list(inbox_dir.glob("*.pdf"))

    if not pdfs:
        print("No PDFs found in inbox/")
        print(f"  Drop PDFs here: {inbox_dir}")
        return 0

    print(f"Found {len(pdfs)} PDF(s) in inbox:\n")

    # Detect tickers for each PDF
    pdf_tickers = []
    for pdf_path in pdfs:
        ticker = _detect_ticker(pdf_path, ir_map)
        pdf_tickers.append((pdf_path, ticker))
        status = ticker if ticker else "??? (unknown)"
        print(f"  {pdf_path.name}")
        print(f"    -> Ticker: {status}")

    # Check for unknowns
    unknowns = [(p, t) for p, t in pdf_tickers if not t]
    if unknowns:
        print("\nCould not detect ticker for some PDFs.")
        print("Please rename them with ticker prefix, e.g., 'ASND_presentation.pdf'")
        print("Or process manually: python -m app.cli.extract --ticker ASND --pdf /path/to.pdf")

        # Filter out unknowns
        pdf_tickers = [(p, t) for p, t in pdf_tickers if t]
        if not pdf_tickers:
            return 1

    # Confirm
    print(f"\nReady to process {len(pdf_tickers)} PDF(s)")
    if not args.yes:
        confirm = input("Continue? [Y/n] ")
        if confirm.lower() == "n":
            print("Cancelled")
            return 0

    # Process each PDF
    orchestrator = ExtractionOrchestrator(
        rate_limit_seconds=args.rate_limit,
        dry_run=args.dry_run
    )

    results = []
    for pdf_path, ticker in pdf_tickers:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_path.name} -> {ticker}")
        print("="*60)

        result = orchestrator.process_company(ticker=ticker, pdf_path=pdf_path)
        results.append(result)
        _print_result(result)

        # Move to processed folder on success
        if result["status"] in ("success", "partial") and not args.dry_run:
            dest = processed_dir / pdf_path.name
            # Handle duplicates
            if dest.exists():
                stem = pdf_path.stem
                suffix = pdf_path.suffix
                counter = 1
                while dest.exists():
                    dest = processed_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            shutil.move(str(pdf_path), str(dest))
            print(f"    Moved to: processed/{dest.name}")

    # Summary
    _print_batch_summary(results)
    return 0 if all(r["status"] != "failed" for r in results) else 1


def _detect_ticker(pdf_path: Path, ir_map: dict) -> str | None:
    """
    Detect company ticker from PDF filename or content.

    Tries in order:
    1. Ticker prefix in filename (e.g., "ASND_presentation.pdf")
    2. Known company name in filename (e.g., "Kymera Therapeutics...")
    3. First page content analysis (fallback)
    """
    filename = pdf_path.stem.upper()

    # Build reverse lookup: company name -> ticker
    name_to_ticker = {}
    for ticker, config in ir_map.items():
        name = config.get("name", "").upper()
        if name:
            name_to_ticker[name] = ticker
            # Also add key words from name
            words = name.split()
            if words:
                name_to_ticker[words[0]] = ticker

    # 1. Check if filename starts with a known ticker
    for ticker in ir_map.keys():
        if filename.startswith(ticker + "_") or filename.startswith(ticker + " "):
            return ticker
        # Exact match
        if filename == ticker:
            return ticker

    # 2. Check if filename contains known company name
    for name, ticker in name_to_ticker.items():
        if name in filename:
            return ticker

    # 3. Try common patterns in filename
    # Pattern: "CompanyName Corporate Presentation" or "CompanyName Investor..."
    patterns = [
        r"^([A-Z]{3,5})[\s_-]",  # ASND_... or ASND ...
        r"^([A-Z]{2,5})\d",  # ASND2024...
    ]
    for pattern in patterns:
        match = re.match(pattern, filename)
        if match:
            potential_ticker = match.group(1)
            if potential_ticker in ir_map:
                return potential_ticker

    # 4. Try to extract from PDF content (first 2 pages)
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        text = ""
        for i in range(min(2, len(doc))):
            text += doc[i].get_text()
        doc.close()
        text_upper = text.upper()

        # Look for tickers in content
        for ticker in ir_map.keys():
            # Look for "TICKER:" or "(TICKER)" or "NASDAQ: TICKER"
            if f"({ticker})" in text_upper or f": {ticker}" in text_upper:
                return ticker
            # Look for company name
            name = ir_map[ticker].get("name", "").upper()
            if name and name in text_upper:
                return ticker
    except Exception:
        pass

    return None


if __name__ == "__main__":
    sys.exit(main())
