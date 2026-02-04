"""
CLI for extracting company data from IR presentations.

Usage:
    python -m app.cli.extract --ticker ASND
    python -m app.cli.extract --ticker ASND --pdf /path/to/presentation.pdf
    python -m app.cli.extract --priority HIGH
    python -m app.cli.extract --priority HIGH --dry-run
    python -m app.cli.extract --all
    python -m app.cli.extract --list
"""

import argparse
import json
import logging
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

    # Options
    parser.add_argument(
        "--pdf",
        type=str,
        help="Path to existing PDF (skips scraping for --ticker)"
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

        # Create orchestrator
        orchestrator = ExtractionOrchestrator(
            rate_limit_seconds=args.rate_limit,
            dry_run=args.dry_run
        )

        # Single ticker
        if args.ticker:
            ticker = args.ticker.upper()
            if ticker not in IR_WEBSITE_MAP:
                logger.warning(f"{ticker} not in IR mapping, will attempt anyway")

            pdf_path = Path(args.pdf) if args.pdf else None
            result = orchestrator.process_company(
                ticker=ticker,
                pdf_path=pdf_path,
                keywords=args.keywords
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
        print(f"    Assets: {summary.get('assets_found', 0)}")
        print(f"    Trials: {summary.get('trials_found', 0)}")
        print(f"    Catalysts: {summary.get('catalysts_found', 0)}")

    if result.get("extracted_files"):
        print(f"    Files saved: {len(result['extracted_files'])}")

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


if __name__ == "__main__":
    sys.exit(main())
