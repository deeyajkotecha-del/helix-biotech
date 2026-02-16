#!/usr/bin/env python3
"""
Update market cap data from Yahoo Finance for all companies in index.json.

Usage:
    python scripts/update_market_data.py                    # Update all companies
    python scripts/update_market_data.py --ticker HIMS      # Single ticker
    python scripts/update_market_data.py --dry-run          # Preview changes
    python scripts/update_market_data.py --verbose          # Show all lookups
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
INDEX_PATH = PROJECT_ROOT / "data" / "companies" / "index.json"
COMPANIES_DIR = PROJECT_ROOT / "data" / "companies"


def format_market_cap(value: int | float | None) -> str | None:
    """Convert numeric market cap (in USD) to string format like '$3.7B', '$350M'."""
    if value is None or value <= 0:
        return None
    if value >= 1_000_000_000:
        billions = value / 1_000_000_000
        if billions >= 100:
            return f"${billions:.0f}B"
        elif billions >= 10:
            return f"${billions:.0f}B"
        else:
            return f"${billions:.1f}B"
    elif value >= 1_000_000:
        millions = value / 1_000_000
        if millions >= 100:
            return f"${millions:.0f}M"
        else:
            return f"${millions:.0f}M"
    else:
        return f"${value / 1_000_000:.1f}M"


def fetch_market_cap(ticker: str, verbose: bool = False) -> int | None:
    """Fetch live market cap from Yahoo Finance. Returns value in USD or None."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        market_cap = info.get("marketCap")
        if verbose:
            print(f"  [{ticker}] Raw marketCap = {market_cap}")
        return market_cap
    except Exception as e:
        if verbose:
            print(f"  [{ticker}] Error: {e}")
        return None


def update_company_json(ticker: str, new_cap_str: str, dry_run: bool, verbose: bool) -> bool:
    """Update market_cap in individual company.json if it exists. Returns True if updated."""
    company_json = COMPANIES_DIR / ticker / "company.json"
    if not company_json.exists():
        return False

    with open(company_json) as f:
        data = json.load(f)

    old_cap = data.get("market_cap", "")
    if old_cap == new_cap_str:
        return False

    if verbose:
        print(f"    company.json: {old_cap or '(empty)'} -> {new_cap_str}")

    if not dry_run:
        data["market_cap"] = new_cap_str
        with open(company_json, "w") as f:
            json.dump(data, f, indent=2)

    return True


def main():
    parser = argparse.ArgumentParser(description="Update market caps from Yahoo Finance")
    parser.add_argument("--ticker", type=str, help="Update a single ticker only")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--verbose", action="store_true", help="Show all lookups including unchanged")
    args = parser.parse_args()

    if not INDEX_PATH.exists():
        print(f"Error: {INDEX_PATH} not found")
        sys.exit(1)

    with open(INDEX_PATH) as f:
        index = json.load(f)

    companies = index.get("companies", [])
    if not companies:
        print("No companies found in index.")
        sys.exit(1)

    # Filter to single ticker if specified
    if args.ticker:
        ticker_upper = args.ticker.upper()
        companies = [c for c in companies if c["ticker"] == ticker_upper]
        if not companies:
            print(f"Ticker {ticker_upper} not found in index.json")
            sys.exit(1)

    total = len(companies)
    updated = 0
    failed = 0
    unchanged = 0

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Updating market caps for {total} companies...")
    print()

    for i, company in enumerate(companies):
        ticker = company["ticker"]
        old_cap = company.get("market_cap_mm", "")

        market_cap_raw = fetch_market_cap(ticker, verbose=args.verbose)
        new_cap = format_market_cap(market_cap_raw)

        if new_cap is None:
            failed += 1
            if args.verbose:
                print(f"  [{ticker}] SKIP - no data from Yahoo Finance")
            continue

        if new_cap == old_cap:
            unchanged += 1
            if args.verbose:
                print(f"  [{ticker}] {old_cap} (unchanged)")
            continue

        print(f"  {ticker}: {old_cap or '(empty)'} -> {new_cap}")
        updated += 1

        if not args.dry_run:
            company["market_cap_mm"] = new_cap

        # Also update individual company.json
        update_company_json(ticker, new_cap, args.dry_run, args.verbose)

        # Rate limit to avoid being blocked
        if total > 1:
            time.sleep(0.3)

    # Write back index.json
    if not args.dry_run and updated > 0:
        index["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(INDEX_PATH, "w") as f:
            json.dump(index, f, indent=2)
        print()
        print(f"Wrote {INDEX_PATH}")

    print()
    print(f"Done. Updated: {updated}, Unchanged: {unchanged}, Failed: {failed}, Total: {total}")


if __name__ == "__main__":
    main()
