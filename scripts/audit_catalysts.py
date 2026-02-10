#!/usr/bin/env python3
"""
Audit all catalysts.json files across target pages.

Usage:
    python scripts/audit_catalysts.py

Reports:
    - Target name and last_reviewed date
    - Days since last review
    - Upcoming catalysts in the next 90 days
    - Past catalysts missing an outcome field
"""

import json
from datetime import date, timedelta
from pathlib import Path

TARGETS_DIR = Path(__file__).parent.parent / "data" / "targets"


def parse_date(date_str: str) -> date:
    parts = date_str.split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) >= 2 else 1
        day = int(parts[2]) if len(parts) >= 3 else 1
        return date(year, month, day)
    except (ValueError, IndexError):
        return date(9999, 1, 1)


def main():
    today = date.today()
    ninety_days = today + timedelta(days=90)

    cat_files = sorted(TARGETS_DIR.glob("*/catalysts.json"))

    if not cat_files:
        print("No catalysts.json files found in data/targets/*/")
        return

    print(f"Catalyst Audit Report — {today.isoformat()}")
    print("=" * 70)

    for cat_path in cat_files:
        slug = cat_path.parent.name
        with open(cat_path) as f:
            data = json.load(f)

        target = data.get("target", slug)
        last_reviewed = data.get("last_reviewed", "unknown")
        catalysts = data.get("catalysts", [])

        # Days since review
        if last_reviewed != "unknown":
            try:
                reviewed_date = date.fromisoformat(last_reviewed)
                days_ago = (today - reviewed_date).days
            except ValueError:
                days_ago = -1
        else:
            days_ago = -1

        stale_flag = " ** STALE **" if days_ago > 30 else ""

        print(f"\n{target} ({slug})")
        print(f"  Last reviewed: {last_reviewed} ({days_ago} days ago){stale_flag}")
        print(f"  Total catalysts: {len(catalysts)}")

        # Upcoming in next 90 days
        upcoming_soon = []
        past_no_outcome = []

        for c in catalysts:
            parsed = parse_date(c.get("date", ""))
            if today <= parsed <= ninety_days:
                upcoming_soon.append(c)
            if parsed < today and not c.get("outcome"):
                past_no_outcome.append(c)

        if upcoming_soon:
            print(f"  Upcoming (next 90 days): {len(upcoming_soon)}")
            for c in upcoming_soon:
                print(f"    [{c.get('date_display', c['date'])}] {c['company']}: {c['description']}")
        else:
            print("  Upcoming (next 90 days): none")

        if past_no_outcome:
            print(f"  Past catalysts MISSING outcome: {len(past_no_outcome)}")
            for c in past_no_outcome:
                print(f"    [{c.get('date_display', c['date'])}] {c['company']}: {c['description']}")
        else:
            print("  Past catalysts missing outcome: none")

    print("\n" + "=" * 70)
    print("Done.")


if __name__ == "__main__":
    main()
