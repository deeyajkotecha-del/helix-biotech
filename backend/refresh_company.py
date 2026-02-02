#!/usr/bin/env python3
"""
Company Data Refresh CLI

One command to refresh all pipeline data from authoritative sources.

Usage:
    python refresh_company.py ARWR
    python refresh_company.py ARWR --quiet
    python refresh_company.py ARWR --sources fda,trials
"""

import sys
import argparse
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from services.company_refresher import CompanyRefresher, COMPANY_IR_URLS


def main():
    parser = argparse.ArgumentParser(
        description="Refresh pipeline data from authoritative sources (FDA, ClinicalTrials.gov, IR News)"
    )
    parser.add_argument("ticker", help="Stock ticker (e.g., ARWR, IONS, ALNY)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress detailed output")
    parser.add_argument("--sources", "-s", help="Comma-separated sources to check (fda,trials,ir)", default="fda,trials,ir")

    args = parser.parse_args()

    ticker = args.ticker.upper()

    print(f"\n🔄 Refreshing {ticker} from live data sources...\n")

    refresher = CompanyRefresher(verbose=not args.quiet)
    result = refresher.refresh(ticker)

    if result["status"] == "error":
        print(f"\n❌ Error: {result.get('message')}")
        sys.exit(1)

    print(f"\n✅ Refresh complete!")
    print(f"   Changes made: {result['changes_made']}")
    print(f"   File: {result['file_path']}")

    if result.get('changes'):
        print("\n   Changes:")
        for change in result['changes']:
            print(f"     • {change.get('program', '')}: {change.get('type')}")


if __name__ == "__main__":
    main()
