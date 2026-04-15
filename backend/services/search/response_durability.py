"""
SatyaBio Response-Durability Analysis Engine

Computes the cross-linkage analytics between waterfall (depth),
swimmer (durability), and spider (kinetics) data, using disease-calibrated
thresholds. Then generates the structured analytical narrative.

This is the core analytical capability that no existing biotech product offers:
linking response depth to durability to kinetics, with calibrated competitive context.

Usage:
    from analytics.response_durability import ResponseDurabilityAnalyzer

    analyzer = ResponseDurabilityAnalyzer(db_url="postgresql://...")

    # Compute cross-linkage for a single trial
    analysis = analyzer.compute_analysis(trial_id="...", vintage_id="...")

    # Generate competitive narrative
    narrative = analyzer.generate_narrative(trial_id="...", target="KRAS", indication="2L NSCLC")
"""

import json
import math
from dataclasses import dataclass, asdict
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor


# ---------------------------------------------------------------------------
# Clinical convention thresholds (fallback when landscape data is sparse)
# ---------------------------------------------------------------------------

CLINICAL_CONVENTION_THRESHOLDS = {
    # (therapeutic_area, modality_class): (meaningful, deep, exceptional)
    # Solid tumor thresholds (percentage-based)
    ("oncology", "IO"):         (-30, -50, -80),
    ("oncology", "TKI"):        (-30, -60, -90),
    ("oncology", "chemo"):      (-30, -40, -60),
    ("oncology", "ADC"):        (-30, -50, -75),
    ("oncology", "bispecific"):  (-30, -50, -75),
    ("oncology", "degrader"):   (-30, -50, -75),
    ("oncology", "radioligand"):(-30, -50, -75),
    # Default solid
    ("oncology", "default"):    (-30, -50, -75),
}

# Heme uses categorical thresholds (not percentage-based)
HEME_RESPONSE_DEPTH_ORDER = {
    "IWG_AML":  ["NE", "PD", "SD", "HI", "MLFS", "CRi", "CRh", "CRp", "CR", "CR_MRD_neg"],
    "iwCLL":    ["NE", "PD", "SD", "PR", "nPR", "CR", "CRi", "uMRD_PB", "uMRD_PB_BM"],
    "IMWG":     ["NE", "PD", "SD", "MR", "PR", "VGPR", "CR", "sCR", "sCR_MRD_neg"],
    "Lugano":   ["NE", "PD", "SD", "PR", "CR"],
}


@dataclass
class DepthDurabilityResult:
    """Results of the depth-durability correlation analysis."""
    depth_durability_corr: Optional[float]     # Spearman rho
    deep_responder_count: int
    deep_responder_median_dor: Optional[float]
    shallow_responder_median_dor: Optional[float]
    dor_by_response_depth: list                # [{bucket, median_dor, n, censored_pct}]
    cr_durability_median: Optional[float]
    cr_conversion_rate: Optional[float]
    cr_conversion_median_time: Optional[float]
    durable_response_rate: Optional[float]
    durable_response_threshold_months: float
    # Kinetics
    median_time_to_response: Optional[float]
    median_time_to_best_response: Optional[float]
    early_response_rate_8wk: Optional[float]
    rapid_progressors_pct: Optional[float]
    # Resistance
    median_time_to_progression: Optional[float]
    progression_pattern: Optional[str]
    regrowth_onset_weeks: Optional[float]
    # Context
    threshold_context: str
    meaningful_threshold: float
    deep_threshold: float
    exceptional_threshold: float


class ResponseDurabilityAnalyzer:
    """
    Computes response-durability cross-linkage analytics from patient-level data.
    """

    def __init__(self, db_url: str):
        self.db_url = db_url
        self._conn = None

    def connect(self):
        self._conn = psycopg2.connect(self.db_url)

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def compute_analysis(
        self,
        trial_id: str,
        vintage_id: Optional[str] = None,
        durable_threshold_months: float = 6.0,
    ) -> DepthDurabilityResult:
        """
        Compute the full depth-durability cross-analysis for a trial.

        1. Load patient-level records
        2. Determine disease context and thresholds
        3. Compute depth-durability correlation
        4. Compute response quality metrics
        5. Compute kinetics and resistance metrics
        """
        patients = self._load_patients(trial_id, vintage_id)
        if not patients:
            raise ValueError(f"No patient-level data found for trial {trial_id}")

        # Get disease context for threshold calibration
        context = self._get_trial_context(trial_id)
        thresholds = self._get_calibrated_thresholds(context)

        # Filter to responders (those with response data)
        responders = [p for p in patients if p.get("best_overall_response") in
                      ("CR", "CRi", "CRh", "nCR", "sCR", "VGPR", "PR", "MR")]

        # Compute depth-durability correlation
        depth_dor_pairs = [
            (p["best_pct_change"], p["duration_of_response_months"])
            for p in responders
            if p.get("best_pct_change") is not None
            and p.get("duration_of_response_months") is not None
        ]

        spearman_rho = _spearman_correlation(depth_dor_pairs) if len(depth_dor_pairs) >= 5 else None

        # Bucket by depth
        deep_threshold = thresholds["deep"]
        deep_responders = [p for p in responders
                          if p.get("best_pct_change") is not None
                          and p["best_pct_change"] <= deep_threshold]
        shallow_responders = [p for p in responders
                             if p.get("best_pct_change") is not None
                             and p["best_pct_change"] > deep_threshold]

        deep_dors = [p["duration_of_response_months"] for p in deep_responders
                     if p.get("duration_of_response_months") is not None]
        shallow_dors = [p["duration_of_response_months"] for p in shallow_responders
                        if p.get("duration_of_response_months") is not None]

        # DoR by response category
        dor_by_depth = self._compute_dor_by_category(responders)

        # CR-specific metrics
        crs = [p for p in patients if p.get("best_overall_response") in ("CR", "sCR")]
        cr_dors = [p["duration_of_response_months"] for p in crs
                   if p.get("duration_of_response_months") is not None]

        # CR conversion (PR -> CR deepening)
        prs = [p for p in patients if p.get("best_overall_response") == "PR"]
        deepened_to_cr = [p for p in patients if p.get("response_deepened") and
                          p.get("best_overall_response") in ("CR", "sCR")]
        cr_conversion_rate = len(deepened_to_cr) / len(prs) if prs else None
        cr_conversion_times = [
            p["response_deepening_timeline"][-1]["month"] - p["response_deepening_timeline"][0]["month"]
            for p in deepened_to_cr
            if p.get("response_deepening_timeline") and len(p["response_deepening_timeline"]) >= 2
        ]

        # Durable response rate
        durable = [p for p in responders
                   if (p.get("duration_of_response_months") is not None
                       and p["duration_of_response_months"] >= durable_threshold_months)
                   or p.get("dor_censored")]
        durable_rate = len(durable) / len(responders) if responders else None

        # Kinetics
        ttrs = [p["time_to_response_months"] for p in responders
                if p.get("time_to_response_months") is not None]

        # Early response (from spider data)
        patients_with_spider = [p for p in patients if p.get("tumor_measurements")]
        early_responders_8wk = 0
        for p in patients_with_spider:
            measurements = p["tumor_measurements"]
            # Find measurement closest to 8 weeks
            for m in measurements:
                if 6 <= m.get("time", 0) <= 10:  # approximately 8 weeks
                    if m.get("value", 0) <= -30:
                        early_responders_8wk += 1
                    break
        early_rate_8wk = (early_responders_8wk / len(patients_with_spider)
                          if patients_with_spider else None)

        # Rapid progressors
        pd_patients = [p for p in patients if p.get("best_overall_response") == "PD"]
        rapid_prog_pct = len(pd_patients) / len(patients) if patients else None

        # Resistance patterns (from spider data)
        regrowth_onsets = [p.get("nadir_timepoint_weeks") for p in patients
                          if p.get("post_nadir_trajectory") in ("slow_regrowth", "rapid_regrowth")
                          and p.get("nadir_timepoint_weeks") is not None]

        trajectories = [p.get("post_nadir_trajectory") for p in patients
                        if p.get("post_nadir_trajectory") is not None]
        if regrowth_onsets:
            # Check if regrowth timing is uniform or bimodal
            onset_std = _stdev(regrowth_onsets) if len(regrowth_onsets) > 1 else 0
            onset_mean = sum(regrowth_onsets) / len(regrowth_onsets)
            cv = onset_std / onset_mean if onset_mean > 0 else 0
            progression_pattern = "uniform_timing" if cv < 0.3 else "bimodal" if cv > 0.6 else "mixed"
        else:
            progression_pattern = "no_regrowth_observed" if patients_with_spider else None

        return DepthDurabilityResult(
            depth_durability_corr=spearman_rho,
            deep_responder_count=len(deep_responders),
            deep_responder_median_dor=_median(deep_dors),
            shallow_responder_median_dor=_median(shallow_dors),
            dor_by_response_depth=dor_by_depth,
            cr_durability_median=_median(cr_dors),
            cr_conversion_rate=cr_conversion_rate,
            cr_conversion_median_time=_median(cr_conversion_times),
            durable_response_rate=durable_rate,
            durable_response_threshold_months=durable_threshold_months,
            median_time_to_response=_median(ttrs),
            median_time_to_best_response=None,  # needs deeper data
            early_response_rate_8wk=early_rate_8wk,
            rapid_progressors_pct=rapid_prog_pct,
            median_time_to_progression=None,  # computed from KM
            progression_pattern=progression_pattern,
            regrowth_onset_weeks=_median(regrowth_onsets),
            threshold_context=context.get("description", "unknown"),
            meaningful_threshold=thresholds["meaningful"],
            deep_threshold=thresholds["deep"],
            exceptional_threshold=thresholds["exceptional"],
        )

    def save_analysis(self, trial_id: str, vintage_id: str, result: DepthDurabilityResult):
        """Save computed analysis to response_durability_analyses table."""
        with self._conn.cursor() as cur:
            cur.execute("""
                INSERT INTO response_durability_analyses (
                    trial_id, vintage_id,
                    threshold_context, meaningful_threshold, deep_threshold, exceptional_threshold,
                    depth_durability_corr, deep_responder_count,
                    deep_responder_median_dor, shallow_responder_median_dor,
                    dor_by_response_depth,
                    cr_durability_median, cr_conversion_rate, cr_conversion_median_time,
                    durable_response_rate, durable_response_threshold,
                    median_time_to_response, median_time_to_best_response,
                    early_response_rate_8wk, rapid_progressors_pct,
                    median_time_to_progression, progression_pattern, regrowth_onset_weeks
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                trial_id, vintage_id,
                result.threshold_context, result.meaningful_threshold,
                result.deep_threshold, result.exceptional_threshold,
                result.depth_durability_corr, result.deep_responder_count,
                result.deep_responder_median_dor, result.shallow_responder_median_dor,
                json.dumps(result.dor_by_response_depth),
                result.cr_durability_median, result.cr_conversion_rate,
                result.cr_conversion_median_time,
                result.durable_response_rate, result.durable_response_threshold_months,
                result.median_time_to_response, result.median_time_to_best_response,
                result.early_response_rate_8wk, result.rapid_progressors_pct,
                result.median_time_to_progression, result.progression_pattern,
                result.regrowth_onset_weeks,
            ))
        self._conn.commit()

    # ------------------------------------------------------------------
    # Competitive landscape query
    # ------------------------------------------------------------------

    def get_competitive_landscape(
        self,
        target: Optional[str] = None,
        indication: Optional[str] = None,
        line_of_therapy: Optional[str] = None,
    ) -> list[dict]:
        """
        Pull competitive landscape data for comparison.

        This is the structured SQL query that replaces vector search
        for competitive analysis questions.
        """
        conditions = []
        params = []

        if target:
            conditions.append("tgt.name = %s")
            params.append(target)
        if indication:
            conditions.append("ind.disease_name ILIKE %s")
            params.append(f"%{indication}%")
        if line_of_therapy:
            conditions.append("t.line_of_therapy = %s")
            params.append(line_of_therapy)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT
                d.canonical_name AS drug_name,
                d.modality,
                d.company_ticker, d.company_name,
                tgt.name AS target,
                ind.disease_name, ind.disease_subtype,
                t.trial_name, t.phase, t.design, t.control_arm,
                t.line_of_therapy, t.biomarker_selection,
                -- Waterfall data
                w.orr, w.orr_ci, w.cr_rate, w.dcr, w.median_depth_of_response,
                -- Durability data
                rda.depth_durability_corr,
                rda.deep_responder_median_dor, rda.shallow_responder_median_dor,
                rda.durable_response_rate, rda.durable_response_threshold,
                rda.cr_durability_median, rda.cr_conversion_rate,
                rda.early_response_rate_8wk, rda.rapid_progressors_pct,
                rda.progression_pattern, rda.regrowth_onset_weeks,
                -- Swimmer data
                sw.median_dor, sw.dor_censoring_rate, sw.pct_ongoing_12mo,
                -- Spider data
                sp.trajectory_distribution, sp.regrowth_pattern,
                -- KM data
                km.endpoint AS km_endpoint,
                km.hazard_ratio, km.hr_ci_lower, km.hr_ci_upper,
                km.curve_shape, km.proportional_hazards_met,
                km.crossover_rate,
                -- Vintage info
                v.disclosure_venue, v.disclosure_date,
                v.data_maturity, v.median_followup_months
            FROM drugs d
            JOIN drug_targets dt ON d.drug_id = dt.drug_id
            JOIN targets tgt ON dt.target_id = tgt.target_id
            JOIN programs p ON d.drug_id = p.drug_id
            JOIN indications ind ON p.indication_id = ind.indication_id
            JOIN trials t ON t.program_id = p.program_id
            JOIN data_vintages v ON v.trial_id = t.trial_id AND v.is_latest = TRUE
            LEFT JOIN waterfall_results w ON w.trial_id = t.trial_id AND w.vintage_id = v.vintage_id
            LEFT JOIN swimmer_results sw ON sw.trial_id = t.trial_id AND sw.vintage_id = v.vintage_id
            LEFT JOIN spider_results sp ON sp.trial_id = t.trial_id AND sp.vintage_id = v.vintage_id
            LEFT JOIN km_results km ON km.trial_id = t.trial_id AND km.vintage_id = v.vintage_id
            LEFT JOIN response_durability_analyses rda ON rda.trial_id = t.trial_id AND rda.vintage_id = v.vintage_id
            {where_clause}
            ORDER BY t.phase DESC, w.orr DESC NULLS LAST
        """

        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Analytical narrative generation
    # ------------------------------------------------------------------

    def build_narrative_context(
        self,
        trial_id: str,
        target: Optional[str] = None,
        indication: Optional[str] = None,
    ) -> dict:
        """
        Build the structured context payload that gets sent to the LLM
        for narrative generation. This is the JSON shown in the
        'Analytical narrative engine' tab.
        """
        # Get this trial's data
        trial_data = self._load_trial_summary(trial_id)
        if not trial_data:
            return {"error": f"No data found for trial {trial_id}"}

        # Get competitive landscape
        competitors = self.get_competitive_landscape(
            target=target,
            indication=indication,
            line_of_therapy=trial_data.get("line_of_therapy"),
        )

        # Exclude this trial from competitors
        competitors = [c for c in competitors if c.get("trial_name") != trial_data.get("trial_name")]

        # Build context payload
        return {
            "drug": trial_data.get("drug_name"),
            "trial": trial_data.get("trial_name"),
            "indication": f"{trial_data.get('line_of_therapy', '')} {trial_data.get('disease_name', '')}".strip(),
            "comparator": trial_data.get("control_arm"),
            "waterfall": {
                "orr": trial_data.get("orr"),
                "orr_ci": trial_data.get("orr_ci"),
                "cr_rate": trial_data.get("cr_rate"),
                "dcr": trial_data.get("dcr"),
                "median_depth": trial_data.get("median_depth_of_response"),
            },
            "durability": {
                "median_dor_months": trial_data.get("median_dor"),
                "dor_censoring_rate": trial_data.get("dor_censoring_rate"),
                "pct_ongoing_12mo": trial_data.get("pct_ongoing_12mo"),
                "depth_durability_corr": trial_data.get("depth_durability_corr"),
                "deep_responder_median_dor": trial_data.get("deep_responder_median_dor"),
                "shallow_responder_median_dor": trial_data.get("shallow_responder_median_dor"),
                "durable_response_rate": trial_data.get("durable_response_rate"),
                "cr_durability_median": trial_data.get("cr_durability_median"),
            },
            "kinetics": {
                "median_time_to_response_months": trial_data.get("median_time_to_response"),
                "trajectory_distribution": trial_data.get("trajectory_distribution"),
                "regrowth_pattern": trial_data.get("regrowth_pattern"),
                "regrowth_onset_weeks": trial_data.get("regrowth_onset_weeks"),
                "early_response_rate_8wk": trial_data.get("early_response_rate_8wk"),
            },
            "km": {
                "endpoint": trial_data.get("km_endpoint"),
                "hazard_ratio": trial_data.get("hazard_ratio"),
                "hr_ci": [trial_data.get("hr_ci_lower"), trial_data.get("hr_ci_upper")],
                "curve_shape": trial_data.get("curve_shape"),
                "proportional_hazards_met": trial_data.get("proportional_hazards_met"),
                "crossover_rate": trial_data.get("crossover_rate"),
            },
            "competitive_context": {
                c["drug_name"]: {
                    "orr": c.get("orr"),
                    "median_dor": c.get("median_dor"),
                    "durable_response_rate": c.get("durable_response_rate"),
                    "depth_durability_corr": c.get("depth_durability_corr"),
                    "phase": c.get("phase"),
                }
                for c in competitors[:10]  # Top 10 competitors
            },
            "thresholds": {
                "context": trial_data.get("threshold_context", "unknown"),
                "meaningful": trial_data.get("meaningful_threshold"),
                "deep": trial_data.get("deep_threshold"),
                "exceptional": trial_data.get("exceptional_threshold"),
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_patients(self, trial_id: str, vintage_id: Optional[str] = None) -> list[dict]:
        """Load patient-level response records for a trial."""
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            if vintage_id:
                cur.execute(
                    "SELECT * FROM patient_responses WHERE trial_id = %s AND vintage_id = %s ORDER BY patient_index",
                    (trial_id, vintage_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM patient_responses WHERE trial_id = %s ORDER BY patient_index",
                    (trial_id,),
                )
            return [dict(row) for row in cur.fetchall()]

    def _get_trial_context(self, trial_id: str) -> dict:
        """Get disease/modality context for threshold calibration."""
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT ind.therapeutic_area, d.modality, ind.disease_name,
                       t.line_of_therapy, t.biomarker_selection
                FROM trials t
                JOIN programs p ON t.program_id = p.program_id
                JOIN drugs d ON p.drug_id = d.drug_id
                JOIN indications ind ON p.indication_id = ind.indication_id
                WHERE t.trial_id = %s
            """, (trial_id,))
            row = cur.fetchone()
            if row:
                return {
                    "therapeutic_area": row["therapeutic_area"] or "oncology",
                    "modality": row["modality"] or "default",
                    "disease_name": row["disease_name"],
                    "line_of_therapy": row["line_of_therapy"],
                    "description": f"{row.get('line_of_therapy', '')} {row.get('disease_name', '')}".strip(),
                }
            return {"therapeutic_area": "oncology", "modality": "default", "description": "unknown"}

    def _get_calibrated_thresholds(self, context: dict) -> dict:
        """
        Get response depth thresholds, calibrated to disease context.

        Priority:
        1. Landscape-derived (from response_thresholds table)
        2. Clinical convention fallback
        """
        # Try landscape-derived first
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT meaningful_threshold, deep_threshold, exceptional_threshold
                FROM response_thresholds rt
                JOIN indications ind ON rt.indication_id = ind.indication_id
                WHERE ind.disease_name ILIKE %s
                AND rt.modality_class = %s
                LIMIT 1
            """, (f"%{context.get('disease_name', '')}%", context.get("modality", "default")))
            row = cur.fetchone()
            if row:
                return {
                    "meaningful": row["meaningful_threshold"],
                    "deep": row["deep_threshold"],
                    "exceptional": row["exceptional_threshold"],
                }

        # Fall back to clinical convention
        key = (context.get("therapeutic_area", "oncology"), context.get("modality", "default"))
        if key not in CLINICAL_CONVENTION_THRESHOLDS:
            key = (context.get("therapeutic_area", "oncology"), "default")
        if key not in CLINICAL_CONVENTION_THRESHOLDS:
            key = ("oncology", "default")

        meaningful, deep, exceptional = CLINICAL_CONVENTION_THRESHOLDS[key]
        return {"meaningful": meaningful, "deep": deep, "exceptional": exceptional}

    def _compute_dor_by_category(self, responders: list[dict]) -> list[dict]:
        """Compute median DoR stratified by response category."""
        categories = {}
        for p in responders:
            cat = p.get("best_overall_response")
            if cat and p.get("duration_of_response_months") is not None:
                categories.setdefault(cat, []).append({
                    "dor": p["duration_of_response_months"],
                    "censored": p.get("dor_censored", False),
                })

        result = []
        for cat, data in categories.items():
            dors = [d["dor"] for d in data]
            censored = [d["censored"] for d in data]
            censored_pct = sum(1 for c in censored if c) / len(censored) if censored else 0
            result.append({
                "bucket": cat,
                "median_dor": _median(dors),
                "n": len(data),
                "censored_pct": round(censored_pct, 2),
            })

        # Sort by response depth (deepest first)
        depth_order = ["CR", "sCR", "CRi", "CRh", "nCR", "VGPR", "PR", "MR", "SD"]
        result.sort(key=lambda x: depth_order.index(x["bucket"]) if x["bucket"] in depth_order else 99)
        return result

    def _load_trial_summary(self, trial_id: str) -> Optional[dict]:
        """Load combined trial summary for narrative context building."""
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM latest_trial_data ltd
                LEFT JOIN waterfall_results w ON w.trial_id = ltd.trial_id AND w.vintage_id = ltd.vintage_id
                LEFT JOIN swimmer_results sw ON sw.trial_id = ltd.trial_id AND sw.vintage_id = ltd.vintage_id
                LEFT JOIN spider_results sp ON sp.trial_id = ltd.trial_id AND sp.vintage_id = ltd.vintage_id
                LEFT JOIN km_results km ON km.trial_id = ltd.trial_id AND km.vintage_id = ltd.vintage_id
                LEFT JOIN response_durability_analyses rda ON rda.trial_id = ltd.trial_id AND rda.vintage_id = ltd.vintage_id
                WHERE ltd.trial_id = %s
                LIMIT 1
            """, (trial_id,))
            row = cur.fetchone()
            return dict(row) if row else None


# ---------------------------------------------------------------------------
# Statistical helpers (pure Python, no scipy dependency)
# ---------------------------------------------------------------------------

def _median(values: list) -> Optional[float]:
    """Compute median of a list of numbers."""
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 1:
        return sorted_vals[n // 2]
    else:
        return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2


def _stdev(values: list) -> float:
    """Compute standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _spearman_correlation(pairs: list[tuple[float, float]]) -> Optional[float]:
    """
    Compute Spearman rank correlation without scipy.
    pairs: list of (x, y) tuples
    """
    if len(pairs) < 5:
        return None

    n = len(pairs)
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]

    # Rank each variable
    x_ranks = _rank(xs)
    y_ranks = _rank(ys)

    # Compute Pearson correlation on ranks
    mean_xr = sum(x_ranks) / n
    mean_yr = sum(y_ranks) / n

    num = sum((x_ranks[i] - mean_xr) * (y_ranks[i] - mean_yr) for i in range(n))
    den_x = math.sqrt(sum((x_ranks[i] - mean_xr) ** 2 for i in range(n)))
    den_y = math.sqrt(sum((y_ranks[i] - mean_yr) ** 2 for i in range(n)))

    if den_x == 0 or den_y == 0:
        return 0.0

    return round(num / (den_x * den_y), 3)


def _rank(values: list[float]) -> list[float]:
    """Assign ranks to values, handling ties with average rank."""
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)

    i = 0
    while i < len(indexed):
        j = i
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j - 1) / 2 + 1  # 1-based average rank
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_rank
        i = j

    return ranks
