"""
Portfolio Intelligence Service

Three capabilities:
1. State Tracking — snapshots company data, diffs against prior state, surfaces "what changed"
2. TA Scoring — computes therapeutic area rankings from actual trial data (not prompt-guessing)
3. Tension Narrative — builds causal risk chains for synthesis context injection

These functions produce structured context that gets injected into Claude's synthesis prompt,
so the LLM can reason about changes, scores, and risks with real computed data.
"""

import os
import json
import hashlib
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
DATA_DIR = Path(os.environ.get("DATA_DIR", "data/companies"))
SNAPSHOTS_DIR = Path(os.environ.get("SNAPSHOTS_DIR", "data/snapshots"))


# ==========================================================================
# 1. STATE TRACKING — "What changed since last time?"
# ==========================================================================

def _ensure_snapshots_dir(ticker: str) -> Path:
    """Create snapshots directory for a company if it doesn't exist."""
    snap_dir = SNAPSHOTS_DIR / ticker
    snap_dir.mkdir(parents=True, exist_ok=True)
    return snap_dir


def snapshot_company(ticker: str) -> dict:
    """
    Take a timestamped snapshot of a company's current state.
    Stores a minimal diff-friendly representation: pipeline stages, trial statuses,
    catalysts, financials, and key data points.

    Returns the snapshot dict (also saved to disk).
    """
    company_dir = DATA_DIR / ticker
    if not company_dir.exists():
        return {"error": f"No data for {ticker}"}

    # Load company.json
    company_path = company_dir / "company.json"
    if not company_path.exists():
        return {"error": f"No company.json for {ticker}"}

    with open(company_path) as f:
        company = json.load(f)

    # Load all asset JSONs
    assets = {}
    for asset_file in company_dir.glob("*.json"):
        if asset_file.name in ("company.json",):
            continue
        with open(asset_file) as f:
            assets[asset_file.stem] = json.load(f)

    # Build snapshot — the diff-friendly state representation
    snapshot = {
        "ticker": ticker,
        "snapshot_date": datetime.now().isoformat(),
        "snapshot_id": hashlib.md5(
            f"{ticker}-{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12],

        # Pipeline state: asset → stage mapping
        "pipeline": {},

        # Trial states: NCT → status
        "trials": {},

        # Catalysts
        "catalysts": [],

        # Financials
        "financials": company.get("financials", {}),

        # Strategic emphasis (if extracted)
        "strategic_emphasis": company.get("strategic_emphasis"),

        # Portfolio gaps (if extracted)
        "portfolio_gaps": company.get("portfolio_gaps", []),

        # Investment thesis
        "thesis": company.get("investment_thesis_summary", {}).get("core_thesis", ""),

        # Bull/bear cases
        "bull_case": company.get("investment_analysis", {}).get("bull_case", []),
        "bear_case": company.get("investment_analysis", {}).get("bear_case", []),
    }

    # Extract pipeline from company-level
    for prog in company.get("pipeline_summary", {}).get("programs", []):
        asset_key = prog.get("asset", "unknown").lower().replace(" ", "-")
        snapshot["pipeline"][asset_key] = {
            "stage": prog.get("stage"),
            "target": prog.get("target"),
            "indications": prog.get("indications"),
            "next_catalyst": prog.get("next_catalyst"),
        }

    # Extract catalysts
    for cat in company.get("catalysts", []):
        snapshot["catalysts"].append({
            "asset": cat.get("asset"),
            "event": cat.get("event"),
            "timing": cat.get("timing"),
            "importance": cat.get("importance"),
        })

    # Extract trial data from asset JSONs — handle multiple formats
    for asset_name, asset_data in assets.items():
        clinical = asset_data.get("clinical_data", {})

        # Collect all trial-like objects
        all_trials = []
        if isinstance(clinical.get("trials"), list):
            all_trials.extend(clinical["trials"])
        if isinstance(clinical.get("ongoing_trials"), list):
            all_trials.extend(clinical["ongoing_trials"])
        for key, val in clinical.items():
            if key in ("trials", "ongoing_trials"):
                continue
            if isinstance(val, dict) and ("phase" in val or "design" in val or "trial_name" in val):
                all_trials.append(val)

        for trial in all_trials:
            design = trial.get("design", {})
            if isinstance(design, str):
                design = {}
            nct = trial.get("nct_id") or design.get("nct_id", "")
            if nct:
                snapshot["trials"][nct] = {
                    "asset": asset_name,
                    "phase": trial.get("phase") or design.get("phase", ""),
                    "status": trial.get("status") or design.get("status", ""),
                    "indication": trial.get("indication") or design.get("indication", ""),
                    "enrollment": trial.get("enrollment") or design.get("enrollment"),
                    "primary_endpoint": trial.get("primary_endpoint") or design.get("primary_endpoint", ""),
                }

    # Save snapshot
    snap_dir = _ensure_snapshots_dir(ticker)
    snap_file = snap_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(snap_file, "w") as f:
        json.dump(snapshot, f, indent=2)

    return snapshot


def get_latest_snapshot(ticker: str) -> Optional[dict]:
    """Load the most recent snapshot for a ticker."""
    snap_dir = SNAPSHOTS_DIR / ticker
    if not snap_dir.exists():
        return None

    snapshots = sorted(snap_dir.glob("*.json"), reverse=True)
    if not snapshots:
        return None

    with open(snapshots[0]) as f:
        return json.load(f)


def get_previous_snapshot(ticker: str) -> Optional[dict]:
    """Load the second-most-recent snapshot (the one before the latest)."""
    snap_dir = SNAPSHOTS_DIR / ticker
    if not snap_dir.exists():
        return None

    snapshots = sorted(snap_dir.glob("*.json"), reverse=True)
    if len(snapshots) < 2:
        return None

    with open(snapshots[1]) as f:
        return json.load(f)


def diff_company_state(ticker: str) -> dict:
    """
    Compare current company state against the most recent snapshot.
    Returns a structured diff that can be injected into Claude's synthesis context.

    This is the key function — it tells the user "what changed since you last looked."
    """
    # Take a fresh snapshot
    current = snapshot_company(ticker)
    if "error" in current:
        return current

    # Get previous snapshot
    snap_dir = SNAPSHOTS_DIR / ticker
    snapshots = sorted(snap_dir.glob("*.json"), reverse=True)

    # Need at least 2 snapshots (the one we just took + a previous one)
    if len(snapshots) < 2:
        return {
            "ticker": ticker,
            "has_prior": False,
            "message": f"First analysis of {ticker} — no prior state to compare against. Snapshot saved for future comparisons.",
            "current_snapshot_id": current["snapshot_id"],
        }

    # Load the previous snapshot (not the one we just saved)
    with open(snapshots[1]) as f:
        previous = json.load(f)

    diff = {
        "ticker": ticker,
        "has_prior": True,
        "current_date": current["snapshot_date"],
        "previous_date": previous.get("snapshot_date", "unknown"),
        "days_since_last": _days_between(
            previous.get("snapshot_date"), current["snapshot_date"]
        ),
        "changes": [],
    }

    # --- Pipeline changes ---
    prev_pipeline = previous.get("pipeline", {})
    curr_pipeline = current.get("pipeline", {})

    # New programs
    for asset, data in curr_pipeline.items():
        if asset not in prev_pipeline:
            diff["changes"].append({
                "type": "NEW_PROGRAM",
                "severity": "high",
                "detail": f"New pipeline program: {asset} — {data.get('stage')} in {data.get('indications')}",
            })
        elif data.get("stage") != prev_pipeline[asset].get("stage"):
            diff["changes"].append({
                "type": "STAGE_ADVANCE",
                "severity": "high",
                "detail": f"{asset} advanced from {prev_pipeline[asset].get('stage')} → {data.get('stage')}",
            })

    # Dropped programs
    for asset in prev_pipeline:
        if asset not in curr_pipeline:
            diff["changes"].append({
                "type": "PROGRAM_DROPPED",
                "severity": "critical",
                "detail": f"Program {asset} no longer in pipeline (was {prev_pipeline[asset].get('stage')})",
            })

    # --- Trial status changes ---
    prev_trials = previous.get("trials", {})
    curr_trials = current.get("trials", {})

    for nct, data in curr_trials.items():
        if nct not in prev_trials:
            diff["changes"].append({
                "type": "NEW_TRIAL",
                "severity": "medium",
                "detail": f"New trial {nct}: {data.get('asset')} {data.get('phase')} in {data.get('indication')} (N={data.get('enrollment', '?')})",
            })
        elif data.get("status") != prev_trials.get(nct, {}).get("status"):
            old_status = prev_trials[nct].get("status", "?")
            new_status = data.get("status", "?")
            severity = "critical" if "terminat" in str(new_status).lower() or "suspend" in str(new_status).lower() else "medium"
            diff["changes"].append({
                "type": "TRIAL_STATUS_CHANGE",
                "severity": severity,
                "detail": f"Trial {nct} ({data.get('asset')}): {old_status} → {new_status}",
            })

    # --- Catalyst changes ---
    prev_catalysts = {c.get("event", ""): c for c in previous.get("catalysts", [])}
    curr_catalysts = {c.get("event", ""): c for c in current.get("catalysts", [])}

    for event, cat in curr_catalysts.items():
        if event not in prev_catalysts:
            diff["changes"].append({
                "type": "NEW_CATALYST",
                "severity": "medium",
                "detail": f"New catalyst: {cat.get('asset')} — {event} ({cat.get('timing')})",
            })

    # --- Thesis/bull-bear changes ---
    if current.get("thesis") != previous.get("thesis") and previous.get("thesis"):
        diff["changes"].append({
            "type": "THESIS_CHANGED",
            "severity": "high",
            "detail": f"Investment thesis updated. Was: \"{previous.get('thesis', '')[:100]}...\" Now: \"{current.get('thesis', '')[:100]}...\"",
        })

    # --- Financials ---
    prev_cash = previous.get("financials", {}).get("cash_position", "")
    curr_cash = current.get("financials", {}).get("cash_position", "")
    if prev_cash and curr_cash and prev_cash != curr_cash:
        diff["changes"].append({
            "type": "FINANCIAL_UPDATE",
            "severity": "medium",
            "detail": f"Cash position changed: {prev_cash} → {curr_cash}",
        })

    # Summary
    if not diff["changes"]:
        diff["summary"] = f"No material changes detected since {previous.get('snapshot_date', 'last analysis')}."
    else:
        critical = sum(1 for c in diff["changes"] if c["severity"] == "critical")
        high = sum(1 for c in diff["changes"] if c["severity"] == "high")
        diff["summary"] = (
            f"{len(diff['changes'])} changes detected since last analysis "
            f"({diff['days_since_last']} days ago). "
            f"{critical} critical, {high} high severity."
        )

    return diff


def format_diff_for_claude(diff: dict) -> str:
    """
    Format the state diff as context for Claude's synthesis prompt.
    This gets prepended to the synthesis context so Claude can open with "Since your last analysis..."
    """
    if not diff.get("has_prior"):
        return (
            f"═══ STATE TRACKING ═══\n"
            f"First analysis of {diff['ticker']}. No prior state to compare.\n"
            f"Snapshot saved — next query will show what changed.\n"
        )

    if not diff.get("changes"):
        return (
            f"═══ STATE TRACKING ({diff['ticker']}) ═══\n"
            f"Last analyzed: {diff['previous_date'][:10]} ({diff['days_since_last']} days ago)\n"
            f"No material changes detected since last analysis.\n"
        )

    lines = [
        f"═══ WHAT CHANGED SINCE LAST ANALYSIS ({diff['ticker']}) ═══",
        f"Last analyzed: {diff['previous_date'][:10]} ({diff['days_since_last']} days ago)",
        f"Changes detected: {diff['summary']}",
        "",
    ]

    # Group by severity
    for severity in ("critical", "high", "medium"):
        changes = [c for c in diff["changes"] if c["severity"] == severity]
        if changes:
            lines.append(f"[{severity.upper()}]")
            for c in changes:
                lines.append(f"  • {c['type']}: {c['detail']}")
            lines.append("")

    lines.append(
        "INSTRUCTION: Open your response by noting these changes. "
        "Lead with the most significant change and its investment implications. "
        "Do NOT simply list the changes — interpret them. What do they mean for the thesis?"
    )

    return "\n".join(lines)


def _days_between(date_str1: Optional[str], date_str2: Optional[str]) -> int:
    """Calculate days between two ISO date strings."""
    try:
        d1 = datetime.fromisoformat(date_str1)
        d2 = datetime.fromisoformat(date_str2)
        return abs((d2 - d1).days)
    except (TypeError, ValueError):
        return 0


# ==========================================================================
# 2. THERAPEUTIC AREA SCORING — Computed, not prompt-guessed
# ==========================================================================

# Phase weights for activity scoring
PHASE_WEIGHTS = {
    "phase 3": 3.0,
    "phase 2/3": 2.5,
    "pivotal": 3.0,
    "phase 2": 2.0,
    "phase 1/2": 1.5,
    "phase 1": 1.0,
    "preclinical": 0.3,
    "filed": 3.5,
    "approved": 4.0,
}


def score_therapeutic_areas(ticker: str) -> dict:
    """
    Compute therapeutic area scores for a company from actual trial/pipeline data.

    Returns a scored TA table ready for Claude to interpret (not generate from scratch).

    Scoring:
    - Activity: trial_count × phase_weight + enrollment_volume_normalized
    - Risk: competitive_density (fewer = safer), data_maturity (more Phase 3 = safer)
    - Composite: Activity × 0.5 + Risk × 0.5
    """
    company_dir = DATA_DIR / ticker
    if not company_dir.exists():
        return {"error": f"No data for {ticker}"}

    # Collect all TAs from asset data
    ta_data = {}  # TA name → {trials: [], assets: [], enrollment: 0, ...}

    # From asset JSONs
    for asset_file in company_dir.glob("*.json"):
        if asset_file.name == "company.json":
            continue
        with open(asset_file) as f:
            asset = json.load(f)

        asset_name = asset.get("asset", {}).get("name", asset_file.stem)

        # Get indications
        indications = asset.get("indications", {})
        lead = indications.get("lead", {})
        expansions = indications.get("expansion", [])

        all_indications = []
        if lead:
            all_indications.append(lead)
        if isinstance(expansions, list):
            all_indications.extend(expansions)

        for ind in all_indications:
            ta = ind.get("therapeutic_area") or _infer_ta(ind.get("name", ""))
            if not ta:
                ta = "Other"

            if ta not in ta_data:
                ta_data[ta] = {
                    "therapeutic_area": ta,
                    "assets": set(),
                    "trials": [],
                    "total_enrollment": 0,
                    "phase_3_count": 0,
                    "highest_phase": "",
                    "indications": set(),
                }

            ta_data[ta]["assets"].add(asset_name)
            ta_data[ta]["indications"].add(ind.get("name", "Unknown"))

        # Get trial data — handle multiple clinical_data formats
        # Format 1: clinical_data.trials = [...]
        # Format 2: clinical_data.ongoing_trials = [...]
        # Format 3: clinical_data has named trial dicts (phase1_healthy_volunteer, etc.)
        clinical = asset.get("clinical_data", {})
        all_trials = []

        if isinstance(clinical.get("trials"), list):
            all_trials.extend(clinical["trials"])
        if isinstance(clinical.get("ongoing_trials"), list):
            all_trials.extend(clinical["ongoing_trials"])

        # Also pick up dict values that look like trial objects
        for key, val in clinical.items():
            if key in ("trials", "ongoing_trials"):
                continue
            if isinstance(val, dict) and ("phase" in val or "design" in val or "trial_name" in val):
                all_trials.append(val)

        for trial in all_trials:
            # Handle both nested (trial.design.phase) and flat (trial.phase) formats
            design = trial.get("design", {})
            if isinstance(design, str):
                design = {}

            phase = str(trial.get("phase") or design.get("phase", "")).lower()
            indication = str(trial.get("indication") or design.get("indication", ""))
            ta = _infer_ta(indication)
            if not ta:
                ta = "Other"

            if ta not in ta_data:
                ta_data[ta] = {
                    "therapeutic_area": ta,
                    "assets": set(),
                    "trials": [],
                    "total_enrollment": 0,
                    "phase_3_count": 0,
                    "highest_phase": "",
                    "indications": set(),
                }

            enrollment = trial.get("enrollment") or design.get("enrollment") or 0
            if isinstance(enrollment, str):
                try:
                    enrollment = int(str(enrollment).replace(",", "").replace("~", ""))
                except ValueError:
                    enrollment = 0

            ta_data[ta]["trials"].append({
                "nct": trial.get("nct_id") or design.get("nct_id", ""),
                "phase": phase,
                "enrollment": enrollment,
                "status": trial.get("status") or design.get("status", ""),
                "asset": asset_name,
            })
            ta_data[ta]["total_enrollment"] += enrollment
            ta_data[ta]["assets"].add(asset_name)
            ta_data[ta]["indications"].add(indication)

            if "3" in phase:
                ta_data[ta]["phase_3_count"] += 1

    # Now score each TA
    scored_tas = []
    max_enrollment = max(
        (d["total_enrollment"] for d in ta_data.values()), default=1
    ) or 1

    for ta, data in ta_data.items():
        # Activity score: phase-weighted trial count + enrollment
        activity_raw = 0
        for trial in data["trials"]:
            phase = trial["phase"]
            weight = PHASE_WEIGHTS.get(phase, 1.0)
            activity_raw += weight

        # Normalize enrollment contribution (0-3 points)
        enrollment_score = (data["total_enrollment"] / max_enrollment) * 3.0
        activity_raw += enrollment_score

        # Normalize to 1-10
        activity_score = min(10, max(1, round(activity_raw, 1)))

        # Risk score: more Phase 3 trials = lower risk = higher score
        # More assets = more diversification = higher score
        risk_raw = (
            data["phase_3_count"] * 2.0 +
            len(data["assets"]) * 1.0 +
            (1.0 if data["total_enrollment"] > 500 else 0)
        )
        risk_score = min(10, max(1, round(risk_raw, 1)))

        # Composite
        composite = round(activity_score * 0.5 + risk_score * 0.5, 1)

        # Convert sets to lists for JSON
        scored_tas.append({
            "therapeutic_area": ta,
            "activity_score": activity_score,
            "risk_score": risk_score,
            "composite_score": composite,
            "trial_count": len(data["trials"]),
            "total_enrollment": data["total_enrollment"],
            "phase_3_count": data["phase_3_count"],
            "assets": sorted(data["assets"]),
            "indications": sorted(data["indications"]),
        })

    # Sort by composite score descending
    scored_tas.sort(key=lambda x: x["composite_score"], reverse=True)

    return {
        "ticker": ticker,
        "scored_at": datetime.now().isoformat(),
        "therapeutic_areas": scored_tas,
    }


def format_ta_scores_for_claude(scores: dict) -> str:
    """
    Format TA scores as synthesis context. Claude interprets the scores,
    it doesn't compute them.
    """
    if "error" in scores:
        return ""

    tas = scores.get("therapeutic_areas", [])
    if not tas:
        return ""

    lines = [
        f"═══ THERAPEUTIC AREA SCORECARD ({scores['ticker']}) ═══",
        f"Computed from trial data as of {scores['scored_at'][:10]}",
        "",
        "| Therapeutic Area | Activity | Risk | Composite | Trials | Enrollment | Ph3 | Assets |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for ta in tas:
        lines.append(
            f"| {ta['therapeutic_area']} | {ta['activity_score']} | "
            f"{ta['risk_score']} | **{ta['composite_score']}** | "
            f"{ta['trial_count']} | {ta['total_enrollment']:,} | "
            f"{ta['phase_3_count']} | {', '.join(ta['assets'])} |"
        )

    lines.extend([
        "",
        "INSTRUCTION: Interpret this scorecard — don't recalculate it. "
        "Explain what the ranking reveals about strategic priorities. "
        "Flag any TA where activity is high but risk score is low (high-conviction, high-risk bets). "
        "Flag any TA where the company appears to be underinvesting relative to the opportunity.",
    ])

    return "\n".join(lines)


def _infer_ta(indication: str) -> str:
    """Infer therapeutic area from an indication name."""
    indication_lower = str(indication).lower()

    ta_map = {
        "oncology": [
            "cancer", "tumor", "carcinoma", "lymphoma", "leukemia", "melanoma",
            "sarcoma", "myeloma", "glioblastoma", "mesothelioma", "neuroblastoma",
            "nsclc", "sclc", "hcc", "rcc", "aml", "cll", "dlbcl", "mds",
        ],
        "immunology": [
            "arthritis", "lupus", "psoriasis", "dermatitis", "colitis",
            "crohn", "ibd", "uc", "sle", "pemphigus", "vitiligo", "alopecia",
            "myasthenia", "cidp", "itp", "autoimmune",
        ],
        "metabolic": [
            "diabetes", "obesity", "overweight", "nash", "mash", "nafld",
            "weight", "glycemic", "hba1c", "glp-1", "metabolic", "lipid",
            "cardiovascular", "hypertension", "heart failure",
        ],
        "neurology": [
            "alzheimer", "parkinson", "epilepsy", "migraine", "ms ", "multiple sclerosis",
            "als", "huntington", "neuropathy", "seizure", "pain", "sleep apnea",
        ],
        "rare disease": [
            "orphan", "rare", "gaucher", "fabry", "sma", "duchenne", "cystic fibrosis",
            "hemophilia", "sickle cell", "thalassemia", "angelman", "rett",
        ],
        "infectious disease": [
            "hiv", "hepatitis", "covid", "rsv", "influenza", "antimicrobial",
            "antifungal", "antibiotic", "infection", "viral",
        ],
        "respiratory": [
            "asthma", "copd", "pulmonary", "lung fibrosis", "ipf",
        ],
        "musculoskeletal": [
            "osteoarthritis", "osteoporosis", "bone", "joint", "gout",
            "incontinence", "urinary",
        ],
    }

    for ta, keywords in ta_map.items():
        for kw in keywords:
            if kw in indication_lower:
                return ta

    return "other"


# ==========================================================================
# 3. TENSION NARRATIVE — Causal risk chains, not checkbox risks
# ==========================================================================

def build_tension_context(ticker: str) -> str:
    """
    Analyze a company's data and build causal risk chains — not just "risks exist"
    but "if X happens → Y consequence → Z impact on thesis."

    This gets injected into synthesis context so Claude writes with real tension.
    """
    company_dir = DATA_DIR / ticker
    if not company_dir.exists():
        return ""

    company_path = company_dir / "company.json"
    if not company_path.exists():
        return ""

    with open(company_path) as f:
        company = json.load(f)

    # Load all assets
    assets = {}
    for asset_file in company_dir.glob("*.json"):
        if asset_file.name == "company.json":
            continue
        with open(asset_file) as f:
            assets[asset_file.stem] = json.load(f)

    chains = []

    # --- Chain 1: Single-asset dependency ---
    pipeline = company.get("pipeline_summary", {}).get("programs", [])
    clinical_stage = [p for p in pipeline if "phase" in str(p.get("stage", "")).lower()]
    if len(clinical_stage) == 1:
        asset = clinical_stage[0]
        chains.append({
            "trigger": f"{asset.get('asset')} clinical failure",
            "chain": [
                f"{asset.get('asset')} is the ONLY clinical-stage program",
                "Clinical failure means no near-term revenue catalyst",
                f"Cash runway ({company.get('financials', {}).get('cash_runway', '?')}) becomes existential — company must raise capital at distressed valuation or find a partner",
                "Platform value (if any) gets heavily discounted by the market",
            ],
            "severity": "thesis-breaking",
            "what_prevents_it": f"Positive data from {asset.get('asset')} (next catalyst: {asset.get('next_catalyst', '?')})",
        })

    # --- Chain 2: Competitive timing risk ---
    for asset_name, asset_data in assets.items():
        competitors = asset_data.get("competitive_landscape", {})
        if isinstance(competitors, list):
            competitor_list = competitors
        elif isinstance(competitors, dict):
            competitor_list = competitors.get("competitors", [])
        else:
            competitor_list = []

        ahead_competitors = []
        for comp in competitor_list:
            comp_phase = str(comp.get("stage", comp.get("phase", ""))).lower()
            our_phase = str(asset_data.get("asset", {}).get("stage", "")).lower()
            if "3" in comp_phase and "3" not in our_phase:
                ahead_competitors.append(comp)
            elif "approved" in comp_phase and "approved" not in our_phase:
                ahead_competitors.append(comp)

        if ahead_competitors:
            comp_names = [c.get("drug", c.get("name", "?")) for c in ahead_competitors[:3]]
            chains.append({
                "trigger": f"Competitor approval before {asset_name}",
                "chain": [
                    f"{', '.join(comp_names)} are ahead in development",
                    "First-to-market captures physician habits and formulary positions",
                    f"{asset_name} must show CLEAR superiority (not just non-inferiority) to displace an established therapy",
                    "Trial enrollment may slow as patients access approved alternatives",
                    "Pricing power diminishes in a multi-competitor market",
                ],
                "severity": "high",
                "what_prevents_it": f"Differentiated clinical profile (superior efficacy, better safety, or unique convenience advantage)",
            })

    # --- Chain 3: Cash runway pressure ---
    financials = company.get("financials", {})
    runway = str(financials.get("cash_runway", ""))
    if "2026" in runway or "2025" in runway:
        chains.append({
            "trigger": "Cash runway expires before key data readout",
            "chain": [
                f"Runway into {runway} may not extend past next catalysts",
                "Company forced to raise capital (dilutive equity offering) before data de-risks the asset",
                "Pre-data fundraising means selling equity at maximum uncertainty discount",
                "If data is negative, the raise may not happen at all → restructuring or fire-sale M&A",
            ],
            "severity": "critical",
            "what_prevents_it": "Partnership deal (non-dilutive funding), positive interim data, or asset sale",
        })

    # --- Chain 4: Regulatory risk for pivotal programs ---
    for asset_name, asset_data in assets.items():
        clinical = asset_data.get("clinical_data", {})
        # Collect all trial-like objects
        all_trials = []
        if isinstance(clinical.get("trials"), list):
            all_trials.extend(clinical["trials"])
        if isinstance(clinical.get("ongoing_trials"), list):
            all_trials.extend(clinical["ongoing_trials"])
        for key, val in clinical.items():
            if key in ("trials", "ongoing_trials"):
                continue
            if isinstance(val, dict) and ("phase" in val or "design" in val):
                all_trials.append(val)

        for trial in all_trials:
            design = trial.get("design", {})
            if isinstance(design, str):
                design = {}
            phase = str(trial.get("phase") or design.get("phase", "")).lower()
            if "3" in phase or "pivotal" in phase:
                # Check for regulatory risk factors
                risks = []
                if "open" in str(design.get("blinding", "")).lower():
                    risks.append("open-label design (investigator bias risk)")
                endpoint = str(trial.get("primary_endpoint") or design.get("primary_endpoint", "")).lower()
                if "orr" in endpoint or "response" in endpoint:
                    risks.append("surrogate endpoint (may need confirmatory trial for full approval)")
                enrollment = trial.get("enrollment") or design.get("enrollment") or 0
                if isinstance(enrollment, str):
                    try:
                        enrollment = int(str(enrollment).replace(",", "").replace("~", ""))
                    except ValueError:
                        enrollment = 0
                if enrollment and enrollment < 200:
                    risks.append(f"small sample size (N={enrollment}) — regulatory bar is higher")

                if risks:
                    chains.append({
                        "trigger": f"FDA rejects {asset_name} filing or issues CRL",
                        "chain": [
                            f"Pivotal trial has design vulnerabilities: {'; '.join(risks)}",
                            "FDA may require additional data or a confirmatory trial",
                            "18-24 month delay to next filing opportunity",
                            "Competitors advance during the delay window",
                        ],
                        "severity": "high",
                        "what_prevents_it": "Strong efficacy data that overcomes design limitations; pre-submission FDA feedback (Type A/B meeting)",
                    })
                break  # One chain per asset

    if not chains:
        return ""

    # Format for Claude
    lines = [
        f"═══ TENSION MAP ({ticker}) — Causal Risk Chains ═══",
        "",
        "These are NOT generic risk disclaimers. Each is a causal chain: "
        "trigger → consequence → investment impact. Use these to add analytical "
        "tension to the narrative. For each chain, assess the PROBABILITY of the "
        "trigger occurring and whether the 'what prevents it' factor is strong enough.",
        "",
    ]

    for i, chain in enumerate(chains, 1):
        lines.append(f"CHAIN {i} [{chain['severity'].upper()}]: {chain['trigger']}")
        for j, step in enumerate(chain["chain"]):
            lines.append(f"  → {step}")
        lines.append(f"  MITIGANT: {chain['what_prevents_it']}")
        lines.append("")

    return "\n".join(lines)


# ==========================================================================
# 4. REAL-TIME VERIFICATION — Check if key milestones have occurred
# ==========================================================================

NEWSAPI_TIMEOUT = 10  # seconds


def verify_catalysts_and_milestones(ticker: str, company_name: str = None) -> dict:
    """
    Search for recent press releases and news about a company's key events.
    Uses PubMed/news APIs and GlobeNewsWire/PR Newswire patterns.

    Returns structured updates that can be injected into synthesis context
    so Claude knows what has happened SINCE the source documents were written.
    """
    company_dir = DATA_DIR / ticker
    if not company_dir.exists():
        return {"updates": [], "searched": False}

    # Load company data to get catalyst list and partnership info
    company_path = company_dir / "company.json"
    if not company_path.exists():
        return {"updates": [], "searched": False}

    with open(company_path) as f:
        company = json.load(f)

    if not company_name:
        company_name = company.get("company", {}).get("name", ticker)

    # Build search queries from the company's pipeline and partnerships
    search_queries = []

    # 1. Company + FDA / approval / submission
    search_queries.append(f"{company_name} FDA approval submission 2026")

    # 2. Partnership milestones (option exercises, milestone payments)
    financials = company.get("financials", {})
    partnerships = financials.get("partnerships_value", {})
    for partner_key, partner_data in partnerships.items():
        # Extract partner name from key (e.g., "sanofi_irak4" → "Sanofi")
        partner_name = partner_key.split("_")[0].capitalize()
        search_queries.append(f"{company_name} {partner_name} milestone option exercise 2026")

    # 3. Key pipeline assets — data readouts
    for prog in company.get("pipeline_summary", {}).get("programs", []):
        asset_name = prog.get("asset", "")
        if asset_name:
            search_queries.append(f"{company_name} {asset_name} data results 2026")

    # 4. General company news
    search_queries.append(f"{ticker} press release {datetime.now().strftime('%B %Y')}")

    # Execute searches using GlobeNewsWire / Google News RSS patterns
    updates = []
    seen_titles = set()

    for query in search_queries[:6]:  # Cap at 6 queries to keep it fast
        try:
            results = _search_news(query)
            for result in results:
                title = result.get("title", "")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    updates.append(result)
        except Exception as e:
            logger.warning(f"News search failed for '{query}': {e}")

    return {
        "ticker": ticker,
        "searched": True,
        "search_date": datetime.now().isoformat(),
        "queries_run": len(search_queries[:6]),
        "updates": updates,
    }


def _search_news(query: str, max_results: int = 5) -> list:
    """
    Search for recent news using Google News RSS feed (no API key required).
    Falls back gracefully if unavailable.
    """
    results = []

    # Google News RSS — works without API key
    try:
        import urllib.parse
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        resp = requests.get(url, timeout=NEWSAPI_TIMEOUT, headers={
            "User-Agent": "SatyaBio/1.0"
        })
        if resp.status_code == 200:
            # Simple XML parsing for RSS — extract title + link
            import re
            items = re.findall(
                r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>.*?</item>",
                resp.text, re.DOTALL
            )
            for title, link, pub_date in items[:max_results]:
                # Clean HTML entities
                title = title.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
                results.append({
                    "title": title,
                    "url": link,
                    "date": pub_date,
                    "source": "Google News",
                })
    except Exception as e:
        logger.debug(f"Google News RSS search failed: {e}")

    return results


def format_verification_for_claude(verification: dict) -> str:
    """
    Format real-time verification results as context for synthesis.
    This tells Claude about events that happened AFTER the source documents.
    """
    if not verification.get("searched") or not verification.get("updates"):
        return ""

    updates = verification["updates"]
    if not updates:
        return ""

    lines = [
        f"═══ REAL-TIME VERIFICATION ({verification['ticker']}) ═══",
        f"Searched {verification['queries_run']} queries on {verification['search_date'][:10]}",
        f"Found {len(updates)} recent news items. Cross-reference these against the source documents —",
        "if any milestone, approval, partnership event, or data readout has occurred since the source",
        "documents were written, LEAD WITH IT. Flag stale claims in the source data.",
        "",
    ]

    for i, update in enumerate(updates[:10], 1):
        lines.append(f"[{i}] {update['title']}")
        if update.get("date"):
            lines.append(f"    Date: {update['date']}")
        if update.get("url"):
            lines.append(f"    URL: {update['url']}")
        lines.append("")

    lines.append(
        "INSTRUCTION: If any of these news items reveal events that UPDATE or CONTRADICT "
        "claims in the source documents (e.g., an option was exercised, a trial reported results, "
        "an FDA decision was made), you MUST note this prominently. Use the format: "
        "'[UPDATED] Per [source], [old claim]. However, as of [date], [new reality].'"
    )

    return "\n".join(lines)


# ==========================================================================
# Combined context builder — call this from query_router.py
# ==========================================================================

def build_portfolio_context(ticker: str, company_name: str = None) -> str:
    """
    Build the complete portfolio intelligence context for a company.
    Call this from synthesize_answer() and prepend to the context.

    Returns a string with three sections:
    1. State diff (what changed since last query)
    2. Real-time verification (recent news/press releases)
    3. Tension map (causal risk chains)
    """
    sections = []

    # 1. State tracking
    diff = diff_company_state(ticker)
    diff_text = format_diff_for_claude(diff)
    if diff_text:
        sections.append(diff_text)

    # 2. Real-time verification — search for recent events
    verification = verify_catalysts_and_milestones(ticker, company_name)
    verification_text = format_verification_for_claude(verification)
    if verification_text:
        sections.append(verification_text)

    # 3. Tension
    tension_text = build_tension_context(ticker)
    if tension_text:
        sections.append(tension_text)

    return "\n\n".join(sections)
