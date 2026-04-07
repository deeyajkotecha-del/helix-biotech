"""
Pre-compute Company Asset Maps → Neon Cache

Fetches ALL clinical trials for every company in the universe from
ClinicalTrials.gov, extracts drug assets, and stores the results in
Neon for instant loading on the frontend.

This replaces the live 10-20 second API call with a <100ms DB read.

Usage:
    python3 precompute_assets.py                    # All companies
    python3 precompute_assets.py --ticker LLY       # Single company
    python3 precompute_assets.py --ticker LLY,MRK   # Multiple
    python3 precompute_assets.py --priority 1        # High-priority only
    python3 precompute_assets.py --dry-run           # Preview without saving

Designed to run on a schedule (weekly) or on-demand.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# ── Path setup ──
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SEARCH_DIR = os.path.join(os.path.dirname(_THIS_DIR), "search")
if _SEARCH_DIR not in sys.path:
    sys.path.insert(0, _SEARCH_DIR)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_DIR)))
_APP_DIR = os.path.join(_PROJECT_ROOT, "app")
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import psycopg2
from api_connectors import search_clinical_trials_paginated, extract_drug_assets

# ── Ticker → Sponsor mapping ──
# This maps our internal tickers to the exact sponsor name used on ClinicalTrials.gov
TICKER_TO_SPONSOR = {
    "ABBV": "AbbVie",
    "AGTSY": "Astellas Pharma",
    "ALKS": "Alkermes",
    "ALNY": "Alnylam Pharmaceuticals",
    "AMGN": "Amgen",
    "ARGX": "argenx",
    "ASND": "Ascendis Pharma",
    "AXSM": "Axsome Therapeutics",
    "AZN": "AstraZeneca",
    "BCYC": "Bicycle Therapeutics",
    "BIIB": "Biogen",
    "BILH": "Boehringer Ingelheim",
    "BMY": "Bristol-Myers Squibb",
    "BPMC": "Blueprint Medicines",
    "CELC": "Celcuity",
    "CGON": "CG Oncology",
    "CNTA": "Centessa Pharmaceuticals",
    "CRNX": "Crinetics Pharmaceuticals",
    "DAWN": "Day One Biopharmaceuticals",
    "DFTX": "Definium Therapeutics",
    "DSNKY": "Daiichi Sankyo",
    "ERAS": "Erasca",
    "ESALY": "Eisai",
    "EXAS": "Exact Sciences",
    "GILD": "Gilead Sciences",
    "GPCR": "Structure Therapeutics",
    "GSK": "GSK",
    "HRMY": "Harmony Biosciences",
    "IBRX": "ImmunityBio",
    "INCY": "Incyte",
    "INSM": "Insmed",
    "IONS": "Ionis Pharmaceuticals",
    "IOVA": "Iovance Biotherapeutics",
    "JAZZ": "Jazz Pharmaceuticals",
    "JNJ": "Johnson & Johnson",
    "KRTX": "Karuna Therapeutics",
    "LLY": "Eli Lilly",
    "LXEO": "Lexeo Therapeutics",
    "MRK": "Merck",
    "MRNA": "Moderna",
    "NBIX": "Neurocrine Biosciences",
    "NUVL": "Nuvalent",
    "NVO": "Novo Nordisk",
    "NVS": "Novartis",
    "PFE": "Pfizer",
    "PTCT": "PTC Therapeutics",
    "QURE": "uniQure",
    "RCKT": "Rocket Pharmaceuticals",
    "REGN": "Regeneron",
    "RVMD": "Revolution Medicines",
    "SNY": "Sanofi",
    "SRPT": "Sarepta Therapeutics",
    "UTHR": "United Therapeutics",
    "VKTX": "Viking Therapeutics",
    "VRDN": "Viridian Therapeutics",
    "VRTX": "Vertex Pharmaceuticals",
    # Japanese / Asian companies — use common English sponsor names
    "RHHBY": "Roche",
    "ROG": "Roche",
    "TAK": "Takeda",
}

# Priority tiers (1 = highest)
PRIORITY = {
    # Tier 1: Big pharma + key biotechs
    "LLY": 1, "MRK": 1, "PFE": 1, "BMY": 1, "ABBV": 1, "AMGN": 1,
    "GILD": 1, "REGN": 1, "AZN": 1, "NVS": 1, "JNJ": 1, "NVO": 1,
    "VRTX": 1, "BIIB": 1, "GSK": 1, "SNY": 1, "MRNA": 1,
    # Tier 2: Mid-cap movers
    "RVMD": 2, "NUVL": 2, "IOVA": 2, "BPMC": 2, "INCY": 2,
    "JAZZ": 2, "HRMY": 2, "IONS": 2, "SRPT": 2, "ALNY": 2,
    "DSNKY": 2, "ESALY": 2, "INSM": 2, "ARGX": 2,
    # Tier 3: Smaller / specialty
}


def precompute_company(ticker: str, company_name: str, conn, dry_run: bool = False):
    """Fetch all trials for a company from ClinicalTrials.gov and cache in Neon."""
    sponsor = TICKER_TO_SPONSOR.get(ticker, company_name)
    print(f"\n  {ticker} — {company_name}")
    print(f"    Sponsor search: \"{sponsor}\"")

    start = time.time()

    # Paginate through all trials (up to 1000)
    try:
        all_trials = search_clinical_trials_paginated(
            sponsor=sponsor,
            max_pages=10,
            page_size=100,
        )
    except Exception as e:
        print(f"    ERROR fetching trials: {e}")
        return {"trials": 0, "assets": 0}

    elapsed = time.time() - start
    print(f"    Found {len(all_trials)} trials in {elapsed:.1f}s")

    if not all_trials:
        return {"trials": 0, "assets": 0}

    # Extract drug assets
    assets = extract_drug_assets(all_trials)
    active_assets = sum(1 for a in assets.values() if
        sum(a["statuses"].get(s, 0) for s in
            ["RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"]) > 0
    )
    print(f"    Extracted {len(assets)} drug assets ({active_assets} with active trials)")

    if dry_run:
        # Show top 10
        PHASE_RANK = {"PHASE4": 5, "PHASE3": 4, "PHASE2,PHASE3": 3.5,
                      "PHASE2": 3, "PHASE1,PHASE2": 2.5, "PHASE1": 2,
                      "EARLY_PHASE1": 1, "NA": 0, "": 0}
        sorted_a = sorted(assets.items(),
                          key=lambda x: (PHASE_RANK.get(x[1]["highest_phase"], 0), x[1]["trial_count"]),
                          reverse=True)
        for name, info in sorted_a[:10]:
            ac = sum(info["statuses"].get(s, 0) for s in
                     ["RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"])
            print(f"      {name:<35} {info['highest_phase']:<15} {info['trial_count']:>3} trials  ({ac} active)")
        return {"trials": len(all_trials), "assets": len(assets)}

    # ── Store in Neon ──
    cur = conn.cursor()

    # Clear old data for this ticker
    cur.execute("DELETE FROM company_assets WHERE ticker = %s", (ticker,))

    # Insert each asset
    PHASE_RANK = {"PHASE4": 5, "PHASE3": 4, "PHASE2,PHASE3": 3.5,
                  "PHASE2": 3, "PHASE1,PHASE2": 2.5, "PHASE1": 2,
                  "EARLY_PHASE1": 1, "NA": 0, "": 0}
    sorted_assets = sorted(
        assets.items(),
        key=lambda x: (PHASE_RANK.get(x[1]["highest_phase"], 0), x[1]["trial_count"]),
        reverse=True,
    )

    for name, info in sorted_assets:
        active_count = sum(info["statuses"].get(s, 0) for s in
                           ["RECRUITING", "ACTIVE_NOT_RECRUITING",
                            "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"])
        cur.execute("""
            INSERT INTO company_assets
                (ticker, company_name, sponsor_name, drug_name, drug_type,
                 highest_phase, trial_count, active_count, phases, statuses,
                 conditions, trials, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (ticker, drug_name) DO UPDATE SET
                drug_type = EXCLUDED.drug_type,
                highest_phase = EXCLUDED.highest_phase,
                trial_count = EXCLUDED.trial_count,
                active_count = EXCLUDED.active_count,
                phases = EXCLUDED.phases,
                statuses = EXCLUDED.statuses,
                conditions = EXCLUDED.conditions,
                trials = EXCLUDED.trials,
                updated_at = NOW()
        """, (
            ticker, company_name, sponsor,
            name, info["type"], info["highest_phase"],
            info["trial_count"], active_count,
            json.dumps(info["phases"]),
            json.dumps(info["statuses"]),
            json.dumps(info["conditions"][:15]),  # Top 15 conditions
            json.dumps(info["trials"][:50]),       # Keep top 50 trials per drug
        ))

    # Update summary table
    phase_breakdown = {}
    for _, info in sorted_assets:
        ph = info["highest_phase"] or "Unknown"
        phase_breakdown[ph] = phase_breakdown.get(ph, 0) + 1

    top_assets_json = []
    for name, info in sorted_assets[:30]:  # Top 30 for the summary
        ac = sum(info["statuses"].get(s, 0) for s in
                 ["RECRUITING", "ACTIVE_NOT_RECRUITING",
                  "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"])
        top_assets_json.append({
            "drug_name": name,
            "type": info["type"],
            "highest_phase": info["highest_phase"],
            "trial_count": info["trial_count"],
            "active_count": ac,
            "conditions": info["conditions"][:5],
        })

    cur.execute("""
        INSERT INTO company_asset_summary
            (ticker, company_name, sponsor_name, total_trials, total_assets,
             total_active, phase_breakdown, top_assets, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (ticker) DO UPDATE SET
            company_name = EXCLUDED.company_name,
            sponsor_name = EXCLUDED.sponsor_name,
            total_trials = EXCLUDED.total_trials,
            total_assets = EXCLUDED.total_assets,
            total_active = EXCLUDED.total_active,
            phase_breakdown = EXCLUDED.phase_breakdown,
            top_assets = EXCLUDED.top_assets,
            updated_at = NOW()
    """, (
        ticker, company_name, sponsor,
        len(all_trials), len(assets), active_assets,
        json.dumps(phase_breakdown),
        json.dumps(top_assets_json),
    ))

    conn.commit()
    print(f"    Cached {len(assets)} assets + summary in Neon")

    return {"trials": len(all_trials), "assets": len(assets)}


def main():
    parser = argparse.ArgumentParser(description="Pre-compute company asset maps")
    parser.add_argument("--ticker", type=str, help="Comma-separated tickers (e.g. LLY,MRK)")
    parser.add_argument("--priority", type=int, help="Only companies with this priority or higher (1=top)")
    parser.add_argument("--all", action="store_true", help="All companies")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()

    # Load company universe
    configs_dir = os.path.join(_APP_DIR, "configs")
    if configs_dir not in sys.path:
        sys.path.insert(0, configs_dir)
    from companies import COMPANY_UNIVERSE

    if args.ticker:
        tickers = [t.strip().upper() for t in args.ticker.split(",")]
        companies = {t: COMPANY_UNIVERSE[t] for t in tickers if t in COMPANY_UNIVERSE}
        # Also allow tickers not in COMPANY_UNIVERSE if they're in TICKER_TO_SPONSOR
        for t in tickers:
            if t not in companies and t in TICKER_TO_SPONSOR:
                companies[t] = {"name": TICKER_TO_SPONSOR[t], "category": "unknown"}
    elif args.priority:
        companies = {t: COMPANY_UNIVERSE[t] for t in COMPANY_UNIVERSE
                     if PRIORITY.get(t, 99) <= args.priority}
    elif args.all:
        companies = dict(COMPANY_UNIVERSE)
    else:
        # Default: priority 1 + 2
        companies = {t: COMPANY_UNIVERSE[t] for t in COMPANY_UNIVERSE
                     if PRIORITY.get(t, 99) <= 2}

    print(f"\n{'=' * 60}")
    print(f"  Asset Pre-Compute Pipeline")
    print(f"  Companies: {len(companies)} | Dry run: {args.dry_run}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    conn = None
    if not args.dry_run:
        conn = psycopg2.connect(os.environ["NEON_DATABASE_URL"])

    totals = {"trials": 0, "assets": 0, "companies": 0}
    start = time.time()

    # Sort by priority
    sorted_companies = sorted(companies.items(),
                              key=lambda x: (PRIORITY.get(x[0], 99), x[0]))

    for ticker, info in sorted_companies:
        try:
            stats = precompute_company(ticker, info["name"], conn, dry_run=args.dry_run)
            totals["trials"] += stats["trials"]
            totals["assets"] += stats["assets"]
            if stats["trials"] > 0:
                totals["companies"] += 1
        except Exception as e:
            print(f"    ERROR: {e}")

        # Rate limit — 1 second between companies
        time.sleep(1.0)

    if conn:
        conn.close()

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"  Pre-Compute Complete — {int(elapsed // 60)}m {int(elapsed % 60)}s")
    print(f"  Companies processed: {totals['companies']}")
    print(f"  Total trials cached: {totals['trials']}")
    print(f"  Total drug assets:   {totals['assets']}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
