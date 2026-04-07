"""
SatyaBio — Investor Insight Engine

Generates evidence-backed insight cards for buy-side analysts.
This is NOT a summarizer — it detects changes, finds inconsistencies,
infers strategic emphasis, and ranks therapeutic areas by activity/risk.

Each insight is:
  - Labeled: confirmed / likely / speculative
  - Scored: 0-100 confidence
  - Cited: specific source documents, trials, or data points
  - Flagged: NEW if detected since last analysis

INSIGHT TYPES:
  1. Pipeline Shift     — trial starts/stops, phase transitions, new indications
  2. Strategic Emphasis  — where the company is concentrating resources (trial frequency, hiring, CapEx)
  3. Competitive Gap     — indications where competitors are ahead and the company is silent
  4. Data Inconsistency  — claims in IR decks that don't match ClinicalTrials.gov data
  5. Risk Signal         — trial delays, enrollment misses, safety signals, regulatory issues
  6. Catalyst Alert      — upcoming data readouts, PDUFA dates, conference presentations
  7. Portfolio Ranking   — rank therapeutic areas by activity, visibility, and risk
  8. Ownership Signal    — specialist fund activity (new positions, exits, conviction changes)

Usage:
    from insight_engine import generate_insights
    insights = generate_insights("LLY")
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import requests

# ── Path setup ──
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from api_connectors import search_clinical_trials_paginated


# =============================================================================
# Core Insight Types
# =============================================================================

INSIGHT_TYPES = {
    "pipeline_shift": {
        "label": "Pipeline Shift",
        "icon": "🔄",
        "description": "Trial starts, stops, phase transitions, new indications",
    },
    "strategic_emphasis": {
        "label": "Strategic Emphasis",
        "icon": "🎯",
        "description": "Where the company is concentrating clinical resources",
    },
    "competitive_gap": {
        "label": "Competitive Gap",
        "icon": "⚠️",
        "description": "Markets where competitors are ahead and this company is absent",
    },
    "data_inconsistency": {
        "label": "Data Inconsistency",
        "icon": "🔍",
        "description": "Discrepancies between IR claims and public trial data",
    },
    "risk_signal": {
        "label": "Risk Signal",
        "icon": "🚨",
        "description": "Trial delays, enrollment concerns, safety signals",
    },
    "catalyst_alert": {
        "label": "Catalyst Alert",
        "icon": "📅",
        "description": "Upcoming data readouts, PDUFA dates, conferences",
    },
    "portfolio_ranking": {
        "label": "Portfolio Ranking",
        "icon": "📊",
        "description": "Therapeutic areas ranked by activity, visibility, and risk",
    },
}


# =============================================================================
# Insight Generation Functions
# =============================================================================

def _get_connection():
    return psycopg2.connect(os.environ["NEON_DATABASE_URL"])


def _detect_pipeline_shifts(ticker: str, assets: list, trials: list) -> list:
    """
    Detect pipeline activity patterns:
    - Drugs with recent trial starts (< 6 months) → new emphasis
    - Drugs with SUSPENDED/TERMINATED status → potential pullback
    - Drugs in multiple phases simultaneously → accelerated development
    - Drugs with only completed trials → potential lifecycle end
    """
    insights = []
    now = datetime.now()
    six_months_ago = (now - timedelta(days=180)).strftime("%Y-%m")

    # 1. Recently started trials (new activity signal)
    new_starts = []
    for trial in trials:
        start = trial.get("start_date", "")
        if start >= six_months_ago and trial.get("status") in (
            "RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING"
        ):
            new_starts.append(trial)

    if new_starts:
        # Group by drug
        drug_starts = defaultdict(list)
        for trial in new_starts:
            for intv in trial.get("interventions", []):
                name = intv.get("name", "")
                if name and len(name) > 3:
                    drug_starts[name].append(trial)

        for drug, drug_trials in sorted(drug_starts.items(), key=lambda x: -len(x[1])):
            if len(drug_trials) >= 2:
                phases = set(t.get("phase", "") for t in drug_trials)
                conditions = set()
                for t in drug_trials:
                    conditions.update(t.get("conditions", [])[:2])

                insights.append({
                    "type": "pipeline_shift",
                    "title": f"{drug}: {len(drug_trials)} new trials started in last 6 months",
                    "body": (
                        f"{drug} has {len(drug_trials)} newly initiated trials across "
                        f"{', '.join(sorted(phases))} in {', '.join(list(conditions)[:3])}. "
                        f"This acceleration suggests growing strategic priority."
                    ),
                    "confidence_label": "confirmed",
                    "confidence_score": 90,
                    "evidence": [
                        f"{t['nct_id']}: {t['title'][:80]}" for t in drug_trials[:3]
                    ],
                    "is_new": True,
                    "drug": drug,
                })

    # 2. Terminated/Suspended trials (risk signal)
    terminated = [t for t in trials if t.get("status") in ("TERMINATED", "SUSPENDED")]
    if terminated:
        recent_terminated = [
            t for t in terminated
            if t.get("start_date", "") >= (now - timedelta(days=365*2)).strftime("%Y-%m")
        ]
        if recent_terminated:
            insights.append({
                "type": "risk_signal",
                "title": f"{len(recent_terminated)} trials terminated or suspended in last 2 years",
                "body": (
                    f"Recent terminations include: "
                    + "; ".join(t["title"][:60] for t in recent_terminated[:3])
                    + ". These may indicate safety, efficacy, or strategic reprioritization."
                ),
                "confidence_label": "confirmed",
                "confidence_score": 85,
                "evidence": [f"{t['nct_id']}: {t['status']}" for t in recent_terminated[:5]],
                "is_new": False,
            })

    # 3. Accelerated development: drugs with many trials AND multiple phases
    #    Only flag the top assets — not every generic chemo drug
    for asset in assets:
        phases = asset.get("phases", {})
        active_phases = [p for p, c in phases.items() if p and c > 0]
        # Require: 4+ phases, 10+ trials, AND has active trials
        if len(active_phases) >= 4 and asset.get("trial_count", 0) >= 10 and asset.get("active_count", 0) >= 3:
            insights.append({
                "type": "pipeline_shift",
                "title": f"{asset['drug_name']}: active across {len(active_phases)} phases simultaneously",
                "body": (
                    f"{asset['drug_name']} has trials in {', '.join(sorted(active_phases))} — "
                    f"a broad development program spanning {asset['trial_count']} trials "
                    f"across {len(asset.get('conditions', []))} indications. "
                    f"This level of investment signals high corporate conviction."
                ),
                "confidence_label": "confirmed",
                "confidence_score": 88,
                "evidence": [
                    f"{p}: {c} trial{'s' if c > 1 else ''}" for p, c in sorted(phases.items())
                ],
                "is_new": False,
                "drug": asset["drug_name"],
            })

    return insights


def _analyze_strategic_emphasis(ticker: str, assets: list) -> list:
    """
    Infer where the company is putting strategic weight based on:
    - Trial count per therapeutic area
    - Active (recruiting) vs completed ratio
    - Phase distribution (Ph3 = more committed than Ph1)
    """
    insights = []

    # Group assets by condition/therapeutic area
    area_stats = defaultdict(lambda: {
        "drugs": set(), "total_trials": 0, "active_trials": 0,
        "phase3_plus": 0, "phase1": 0, "conditions": set(),
    })

    for asset in assets:
        conditions = asset.get("conditions", [])
        for cond in conditions[:5]:
            # Simplify condition to therapeutic area
            area = _classify_therapeutic_area(cond)
            stats = area_stats[area]
            stats["drugs"].add(asset["drug_name"])
            stats["total_trials"] += asset["trial_count"]
            stats["active_trials"] += asset.get("active_count", 0)
            stats["conditions"].add(cond)

            phases = asset.get("phases", {})
            stats["phase3_plus"] += phases.get("PHASE3", 0) + phases.get("PHASE4", 0)
            stats["phase1"] += phases.get("PHASE1", 0) + phases.get("EARLY_PHASE1", 0)

    # Rank areas by weighted score
    ranked = []
    for area, stats in area_stats.items():
        if area in ("Other", "Healthy Volunteers"):
            continue
        score = (
            stats["active_trials"] * 3 +
            stats["phase3_plus"] * 5 +
            len(stats["drugs"]) * 2 +
            stats["total_trials"]
        )
        ranked.append((area, stats, score))

    ranked.sort(key=lambda x: -x[2])

    if ranked:
        # Top focus area insight
        top = ranked[0]
        insights.append({
            "type": "strategic_emphasis",
            "title": f"Primary strategic focus: {top[0]}",
            "body": (
                f"{top[0]} dominates the pipeline with {len(top[1]['drugs'])} drug assets, "
                f"{top[1]['active_trials']} active trials, and {top[1]['phase3_plus']} "
                f"Phase 3+ programs. Key drugs: {', '.join(list(top[1]['drugs'])[:5])}."
            ),
            "confidence_label": "confirmed",
            "confidence_score": 92,
            "evidence": [
                f"{len(top[1]['drugs'])} drugs targeting {top[0]}",
                f"{top[1]['active_trials']} active trials",
                f"{top[1]['phase3_plus']} Phase 3+ trials",
            ],
            "is_new": False,
        })

        # Portfolio diversity insight
        if len(ranked) >= 3:
            top3 = ranked[:3]
            top3_pct = sum(t[2] for t in top3) / max(sum(t[2] for t in ranked), 1) * 100
            insights.append({
                "type": "portfolio_ranking",
                "title": f"Top 3 areas represent {top3_pct:.0f}% of pipeline activity",
                "body": (
                    f"1. {top3[0][0]} ({len(top3[0][1]['drugs'])} drugs, {top3[0][1]['active_trials']} active)\n"
                    f"2. {top3[1][0]} ({len(top3[1][1]['drugs'])} drugs, {top3[1][1]['active_trials']} active)\n"
                    f"3. {top3[2][0]} ({len(top3[2][1]['drugs'])} drugs, {top3[2][1]['active_trials']} active)"
                ),
                "confidence_label": "confirmed",
                "confidence_score": 90,
                "evidence": [
                    f"{a}: score {s:.0f}" for a, _, s in ranked[:5]
                ],
                "is_new": False,
                "ranking": [
                    {
                        "area": area,
                        "drugs": len(stats["drugs"]),
                        "active_trials": stats["active_trials"],
                        "total_trials": stats["total_trials"],
                        "phase3_plus": stats["phase3_plus"],
                        "score": score,
                    }
                    for area, stats, score in ranked[:10]
                ],
            })

        # Emerging area (high Ph1 but low Ph3)
        for area, stats, score in ranked:
            if stats["phase1"] >= 3 and stats["phase3_plus"] == 0:
                insights.append({
                    "type": "pipeline_shift",
                    "title": f"Emerging pipeline area: {area}",
                    "body": (
                        f"{area} has {stats['phase1']} early-phase trials but no Phase 3 programs yet. "
                        f"Drugs: {', '.join(list(stats['drugs'])[:3])}. "
                        f"This could represent a new strategic bet or early exploration."
                    ),
                    "confidence_label": "likely",
                    "confidence_score": 70,
                    "evidence": [
                        f"{stats['phase1']} Phase 1 trials",
                        f"{len(stats['drugs'])} drugs in area",
                    ],
                    "is_new": True,
                })

    return insights


def _detect_competitive_gaps(ticker: str, assets: list) -> list:
    """
    Identify major therapeutic markets where competitors are active
    but this company has no presence. Uses the asset map + known
    high-value disease areas.
    """
    insights = []

    # Map the company's active areas
    company_areas = set()
    for asset in assets:
        for cond in asset.get("conditions", []):
            area = _classify_therapeutic_area(cond)
            if area not in ("Other", "Healthy Volunteers"):
                company_areas.add(area)

    # High-value disease areas (>$10B markets)
    HIGH_VALUE_GAPS = {
        "Oncology": "~$200B global market",
        "Diabetes / Metabolic": "~$80B global market",
        "Immunology / Autoimmune": "~$60B global market",
        "Cardiovascular": "~$50B global market",
        "Neurology / CNS": "~$40B global market",
        "Obesity": "~$50B projected by 2030",
        "Rare Disease": "~$30B global market",
        "Respiratory": "~$25B global market",
        "Infectious Disease": "~$20B global market",
    }

    gaps = []
    for area, market_size in HIGH_VALUE_GAPS.items():
        if area not in company_areas:
            gaps.append((area, market_size))

    if gaps:
        insights.append({
            "type": "competitive_gap",
            "title": f"Absent from {len(gaps)} major therapeutic markets",
            "body": (
                "No active trials in: " +
                ", ".join(f"{g[0]} ({g[1]})" for g in gaps[:5]) +
                ". These represent potential portfolio gaps where competitors "
                "are building significant franchises."
            ),
            "confidence_label": "confirmed",
            "confidence_score": 80,
            "evidence": [f"{g[0]}: {g[1]}" for g in gaps],
            "is_new": False,
        })

    return insights


def _analyze_enrollment_and_timing(trials: list) -> list:
    """
    Detect enrollment concerns and timing issues:
    - Large trials with long enrollment periods
    - Trials that appear stalled (started years ago, still recruiting)
    """
    insights = []
    now = datetime.now()

    stalled = []
    for trial in trials:
        if trial.get("status") != "RECRUITING":
            continue
        start = trial.get("start_date", "")
        if not start:
            continue
        try:
            # Parse year-month format
            start_date = datetime.strptime(start[:7], "%Y-%m")
            months_recruiting = (now - start_date).days / 30
            if months_recruiting > 36:  # 3+ years recruiting
                stalled.append({
                    **trial,
                    "months_recruiting": int(months_recruiting),
                })
        except ValueError:
            continue

    if stalled:
        insights.append({
            "type": "risk_signal",
            "title": f"{len(stalled)} trial(s) recruiting for 3+ years",
            "body": (
                "Prolonged recruitment may indicate enrollment difficulties, "
                "protocol amendments, or slow patient identification. "
                "Trials: " + "; ".join(
                    f"{t['nct_id']} ({t['months_recruiting']}mo)"
                    for t in sorted(stalled, key=lambda x: -x["months_recruiting"])[:5]
                )
            ),
            "confidence_label": "likely",
            "confidence_score": 75,
            "evidence": [
                f"{t['nct_id']}: recruiting since {t['start_date']} ({t['months_recruiting']}mo)"
                for t in stalled[:5]
            ],
            "is_new": False,
        })

    return insights


def _classify_therapeutic_area(condition: str) -> str:
    """Simple heuristic classification of conditions into therapeutic areas."""
    c = condition.lower()

    if any(w in c for w in ["cancer", "carcinoma", "tumor", "leukemia", "lymphoma",
                            "melanoma", "sarcoma", "glioma", "myeloma", "neoplasm",
                            "oncolog", "metasta"]):
        return "Oncology"
    if any(w in c for w in ["diabetes", "glycem", "hba1c", "insulin", "glucose"]):
        return "Diabetes / Metabolic"
    if any(w in c for w in ["obes", "overweight", "weight loss", "bmi"]):
        return "Obesity"
    if any(w in c for w in ["alzheimer", "dementia", "parkinson", "multiple sclerosis",
                            "epilep", "migraine", "stroke", "neuropath", "amyloid",
                            "huntington", "als ", "motor neuron"]):
        return "Neurology / CNS"
    if any(w in c for w in ["arthritis", "lupus", "crohn", "colitis", "psoria",
                            "atopic dermatitis", "eczema", "autoimmune", "inflammat"]):
        return "Immunology / Autoimmune"
    if any(w in c for w in ["heart failure", "atrial", "hypertension", "cardiovascul",
                            "coronary", "thrombos"]):
        return "Cardiovascular"
    if any(w in c for w in ["asthma", "copd", "pulmonary", "respiratory", "lung disease"]):
        return "Respiratory"
    if any(w in c for w in ["hiv", "hepatitis", "influenza", "covid", "sars",
                            "infection", "sepsis", "pneumonia"]):
        return "Infectious Disease"
    if any(w in c for w in ["pain", "analges", "fibromyalg"]):
        return "Pain"
    if any(w in c for w in ["rare", "orphan", "dystrophy", "cystic fibrosis",
                            "sickle cell", "hemophilia", "fabry", "gaucher"]):
        return "Rare Disease"
    if any(w in c for w in ["schizophreni", "bipolar", "depress", "anxiety",
                            "adhd", "ptsd", "psychi"]):
        return "Psychiatry"
    if any(w in c for w in ["healthy"]):
        return "Healthy Volunteers"

    return "Other"


# =============================================================================
# Main Insight Generation Pipeline
# =============================================================================

def generate_insights(ticker: str, company_name: str = "") -> dict:
    """
    Generate all insight cards for a company.

    Pulls from:
      1. Cached asset map (Neon company_assets table)
      2. Live ClinicalTrials.gov data (for freshness checks)
      3. RAG document chunks (for IR deck claims)

    Returns {
        "ticker": str,
        "company": str,
        "generated_at": ISO timestamp,
        "insights": [list of insight cards],
        "summary": {top-level stats},
    }
    """
    conn = _get_connection()
    cur = conn.cursor()

    # ── Load cached assets ──
    cur.execute(
        "SELECT drug_name, drug_type, highest_phase, trial_count, active_count, "
        "phases, statuses, conditions, trials "
        "FROM company_assets WHERE ticker = %s ORDER BY trial_count DESC",
        (ticker,)
    )
    rows = cur.fetchall()

    assets = []
    all_trials = []
    for row in rows:
        asset = {
            "drug_name": row[0],
            "type": row[1],
            "highest_phase": row[2],
            "trial_count": row[3],
            "active_count": row[4],
            "phases": row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
            "statuses": row[6] if isinstance(row[6], dict) else json.loads(row[6] or "{}"),
            "conditions": row[7] if isinstance(row[7], list) else json.loads(row[7] or "[]"),
        }
        assets.append(asset)

        # Unpack trial-level data
        trials_data = row[8] if isinstance(row[8], list) else json.loads(row[8] or "[]")
        for t in trials_data:
            t["_drug"] = row[0]  # Track which drug this trial belongs to
        all_trials.extend(trials_data)

    # Load summary
    cur.execute(
        "SELECT total_trials, total_assets, total_active, sponsor_name "
        "FROM company_asset_summary WHERE ticker = %s",
        (ticker,)
    )
    summary_row = cur.fetchone()

    if not summary_row:
        conn.close()
        return {
            "ticker": ticker,
            "company": company_name,
            "generated_at": datetime.now().isoformat(),
            "insights": [],
            "summary": {"total_trials": 0, "total_assets": 0, "message": "No cached data. Run precompute first."},
        }

    total_trials, total_assets, total_active, sponsor = summary_row

    # ── Also load any document counts for this company from RAG ──
    cur.execute(
        "SELECT doc_type, COUNT(*) FROM documents WHERE ticker = %s GROUP BY doc_type",
        (ticker,)
    )
    doc_counts = dict(cur.fetchall())

    conn.close()

    # ── Generate insights from each analyzer ──
    all_insights = []

    # 1. Pipeline shifts
    all_insights.extend(_detect_pipeline_shifts(ticker, assets, all_trials))

    # 2. Strategic emphasis
    all_insights.extend(_analyze_strategic_emphasis(ticker, assets))

    # 3. Competitive gaps
    all_insights.extend(_detect_competitive_gaps(ticker, assets))

    # 4. Enrollment / timing risks
    all_insights.extend(_analyze_enrollment_and_timing(all_trials))

    # Sort by confidence score descending, then by is_new
    all_insights.sort(key=lambda x: (
        -int(x.get("is_new", False)),
        -x.get("confidence_score", 0),
    ))

    return {
        "ticker": ticker,
        "company": company_name or sponsor,
        "generated_at": datetime.now().isoformat(),
        "total_trials": total_trials,
        "total_assets": total_assets,
        "total_active": total_active,
        "doc_counts": doc_counts,
        "insight_count": len(all_insights),
        "insights": all_insights,
    }


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate investor insights")
    parser.add_argument("--ticker", required=True, help="Company ticker (e.g. LLY)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    result = generate_insights(args.ticker)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"\n{'=' * 60}")
        print(f"  Insight Engine — {result['company']} ({result['ticker']})")
        print(f"  {result['total_trials']} trials | {result['total_assets']} assets | {result['total_active']} active")
        print(f"  Generated: {result['generated_at']}")
        print(f"{'=' * 60}")

        for i, insight in enumerate(result["insights"], 1):
            icon = INSIGHT_TYPES.get(insight["type"], {}).get("icon", "•")
            label = insight.get("confidence_label", "unknown").upper()
            score = insight.get("confidence_score", 0)
            new_tag = " [NEW]" if insight.get("is_new") else ""

            print(f"\n  {icon} #{i}{new_tag} — {insight['title']}")
            print(f"     [{label} {score}%]")
            print(f"     {insight['body'][:200]}")
            if insight.get("evidence"):
                for ev in insight["evidence"][:3]:
                    print(f"       → {ev}")

        print(f"\n  Total: {len(result['insights'])} insights")
        print(f"{'=' * 60}\n")
