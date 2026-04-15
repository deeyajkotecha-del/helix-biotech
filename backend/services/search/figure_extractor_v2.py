"""
SatyaBio Structured Figure Extraction Pipeline

Replaces the old figure_annotator.py (which used a generic one-size-fits-all prompt)
with rigorous, figure-type-specific extraction that outputs structured JSON matching
the knowledge graph schema.

Usage:
    from extraction.figure_extractor_v2 import FigureExtractor

    extractor = FigureExtractor(api_key="sk-ant-...")
    result = extractor.extract("path/to/km_curve.png", figure_type="kaplan_meier")
    # result is a dict matching the km_results schema
"""

import json
import base64
import httpx
from pathlib import Path
from typing import Optional, Literal


# ---------------------------------------------------------------------------
# Figure type detection prompt
# ---------------------------------------------------------------------------

FIGURE_CLASSIFIER_PROMPT = """You are looking at a page from a biotech clinical trial document.
Classify this image into exactly ONE of these categories:

- kaplan_meier: Survival curve with step function, y-axis = probability, x-axis = time, usually has number-at-risk table below
- waterfall: Vertical bars showing % change from baseline per patient, bars go up (growth) and down (shrinkage)
- swimmer: Horizontal bars/lanes showing duration per patient, with event markers (arrows, symbols)
- spider: Multiple overlapping line traces showing individual patient tumor change over time
- forest: Horizontal lines with diamonds/squares showing effect size + CI for subgroups, vertical line of no effect
- score_over_time: Line graph showing a clinical score (EASI, PASI, PANSS, HbA1c, body weight) at multiple timepoints across arms
- responder_bar_chart: Grouped bar chart showing responder rates (EASI-75, ACR50, PASI-90, weight loss >=10%, etc.) by arm
- dose_response: Efficacy/safety plotted across dose levels, showing dose-response relationship
- response_table: Tabular data showing ORR, CR, PR, SD, PD rates
- safety_table: Adverse events, dose modifications, discontinuation rates
- study_design: Schema/diagram of trial design, CONSORT diagram
- dose_escalation: Dose vs response/toxicity, pharmacokinetics
- other_clinical: Other clinical data figure
- non_clinical: Not a clinical data figure (corporate slide, text, logos)

Respond with ONLY the category name, nothing else."""


# ---------------------------------------------------------------------------
# Extraction prompts (one per figure type)
# ---------------------------------------------------------------------------

KM_EXTRACTION_PROMPT = """You are an expert oncology biostatistician extracting data from a Kaplan-Meier survival curve.

FIGURE CONTEXT:
- Trial: {trial_name}
- Drug: {drug_name}
- Indication: {indication}

EXTRACT WITH PRECISION:

1. ENDPOINT: what survival measure? (OS, PFS, DFS, EFS, RFS, DOR, TTP)
   Look in figure title, y-axis label, or caption.

2. ANALYSIS POPULATION: ITT, mITT, per-protocol, as-treated? Look in title or footnote.

3. NUMBER OF ARMS and their labels (read from legend exactly).

4. FOR EACH ARM:
   - arm_name: exact label from legend
   - arm_type: experimental, control, combo, monotherapy
   - n_patients: from "n=" or "N=" in legend or number-at-risk table row 1
   - median_survival_months: where curve crosses 50% on y-axis. Report null if NR (not reached).
   - median_ci_lower and median_ci_upper: if shown
   - events_count: if reported
   - landmark_rates: read survival probability at visible timepoints
     Format: [{{"month": 6, "rate": 0.72, "ci_lower": 0.65, "ci_upper": 0.79}}]
   - number_at_risk: read EVERY row of the table below the curve
     Format: [{{"month": 0, "n": 218}}, {{"month": 6, "n": 142}}, ...]
   - censoring_pattern: estimate from tick marks on the curve
     {{"total_censored_approx": 76, "early_fraction": 0.12, "late_fraction": 0.31}}

5. COMPARISON STATISTICS (usually in a box or footnote):
   - hazard_ratio, hr_ci_lower, hr_ci_upper
   - p_value and p_value_type (one_sided or two_sided)
   - hr_method: log_rank, cox, stratified_cox

6. CURVE BEHAVIOR ASSESSMENT:
   - curve_shape: "early_sep", "late_sep", "crossing", "converging", "parallel", "tail_benefit"
   - separation_time_months: approximate month when curves first clearly diverge
   - crossing_events: [{{"month": 14, "interpretation": "curves cross suggesting non-PH"}}] or []
   - proportional_hazards_met: true if curves maintain roughly parallel separation on log scale, false if they cross or converge. THIS IS CRITICAL — if false, the HR is misleading.

7. STRATIFICATION FACTORS if listed in footnote.

8. CROSSOVER: was crossover allowed? If mentioned, what was the crossover rate?

Return ONLY valid JSON matching this structure. Use null for values you cannot determine.
Set extraction_confidence between 0 and 1 for the overall extraction quality.

{{"endpoint": "...", "analysis_type": "...", "arms": [...], "hazard_ratio": ..., ...}}"""


WATERFALL_EXTRACTION_PROMPT = """You are an expert oncology biostatistician extracting data from a clinical trial waterfall plot.

FIGURE CONTEXT:
- Trial: {trial_name}
- Drug: {drug_name}
- Indication: {indication}

A waterfall plot shows vertical bars (one per patient) representing best percentage change from baseline in tumor measurements. Bars below 0 = shrinkage. Bars above 0 = growth.

EXTRACT THE FOLLOWING:

1. MEASUREMENT TYPE: what does the y-axis measure? (target_lesion_SLD, PSA_change, ctDNA_change, M_protein)

2. ASSESSMENT CRITERIA: RECIST 1.1, iRECIST, mRECIST, RANO, Lugano, IMWG, IWG_AML? (check title/footnote)

3. REFERENCE LINES: Is there a -30% line (PR threshold)? A +20% line (PD threshold)? Others?

4. COLOR/PATTERN LEGEND: what does each color or pattern represent?
   Common patterns: biomarker status, prior therapy, mutation subtype, dose level.

5. FOR EACH VISIBLE BAR (left to right):
   - patient_index: 1, 2, 3... from left
   - pct_change: approximate value read from y-axis (negative = shrinkage)
   - bar_color_or_pattern: describe what you see
   - best_response: CR, PR, SD, PD if determinable from the -30%/+20% thresholds
   - biomarker_status: if color-coded, map from legend

6. SUMMARY STATISTICS if shown:
   - orr (overall response rate), orr_ci (95% CI)
   - cr_rate, dcr (disease control rate), cbr (clinical benefit rate)
   - Any subgroup ORR callouts

7. CRITICAL ASSESSMENT:
   - Total number of bars (= evaluable patients)
   - What fraction cross -30%? Cross -50%?
   - Are the deepest responses associated with a specific biomarker?
   - How many bars show growth (>0)?
   - median_depth_of_response: approximate median of all bars below 0

Return ONLY valid JSON. Use null for values you cannot determine.
Estimate extraction_confidence between 0 and 1.

{{"measurement_type": "...", "assessment_criteria": "...", "orr": ..., "individual_responses": [...], ...}}"""


SWIMMER_EXTRACTION_PROMPT = """You are an expert oncology biostatistician extracting data from a clinical trial swimmer plot.

FIGURE CONTEXT:
- Trial: {trial_name}
- Drug: {drug_name}
- Indication: {indication}

A swimmer plot shows horizontal bars (lanes), one per patient. Lane length = time on treatment or in response. Markers indicate events.

EXTRACT:

1. X-AXIS: time in months, weeks, or cycles?

2. WHAT LANE LENGTH REPRESENTS: time on treatment? time from first response? time from enrollment?

3. LEGEND: identify ALL symbols and their meanings (filled arrow = ongoing, triangle = PD, star = CR, etc.)

4. FOR EACH LANE (top to bottom):
   - patient_index (for cross-linking to waterfall)
   - total_duration_months
   - still_ongoing: does it end with a filled arrow or ongoing marker?
   - best_response: from color or symbol
   - events: [{{"month": 2.1, "type": "PR"}}, {{"month": 8.4, "type": "CR"}}, {{"month": 14, "type": "PD"}}]
   - reason_off_study: PD, AE, death, withdrawal, protocol_complete, or null if ongoing

5. ORDERING: are lanes sorted by duration? by response category? by something else?

6. AGGREGATE ASSESSMENT:
   - How many lanes are still ongoing (arrows)?
   - Approximate median duration?
   - Do CRs cluster at the top (longest)?
   - Are there early dropoffs and what caused them?

Return ONLY valid JSON. Use null for ambiguous values.

{{"measurement_type": "...", "lanes": [...], "median_dor": ..., ...}}"""


SPIDER_EXTRACTION_PROMPT = """You are an expert oncology biostatistician extracting data from a clinical trial spider plot.

FIGURE CONTEXT:
- Trial: {trial_name}
- Drug: {drug_name}
- Indication: {indication}

A spider plot shows tumor size change over time for individual patients. Each line = one patient. Y-axis = % change from baseline. X-axis = time.

EXTRACT:

1. Y-AXIS MEASURE: SLD_pct_change, target_lesion_pct, PSA_pct, ctDNA_pct?

2. X-AXIS UNIT: weeks, cycles, months?

3. REFERENCE LINES: -30% (PR)? +20% (PD)?

4. COLOR CODING: what do line colors/styles represent? (biomarker, dose level, response category)

5. FOR EACH VISIBLE TRACE (as many as you can distinguish):
   - patient_index: for cross-linking
   - datapoints: [{{"time": 0, "value": 0}}, {{"time": 8, "value": -42}}, ...]
   - nadir_value: deepest point
   - nadir_time: when deepest point occurred
   - final_value: last visible point
   - trajectory_class: "rapid_deep", "gradual_deep", "shallow_sustained", "initial_then_regrowth", "primary_refractory", "mixed"
   - regrowth_onset_time: when the line starts going back up (null if no regrowth)

6. POPULATION ASSESSMENT:
   - What fraction of lines stay below -30%?
   - Is there a common regrowth timepoint?
   - trajectory_distribution: estimate % in each class
   - regrowth_pattern: "uniform_timing", "bimodal", "rare", "no_regrowth_observed"

Return ONLY valid JSON. Use null for ambiguous values.

{{"y_axis_measure": "...", "x_axis_unit": "...", "traces": [...], ...}}"""


FOREST_EXTRACTION_PROMPT = """You are an expert oncology biostatistician extracting data from a clinical trial forest plot.

FIGURE CONTEXT:
- Trial: {trial_name}
- Drug: {drug_name}
- Indication: {indication}

A forest plot shows treatment effect (HR, OR, RR) across subgroups. Each row = one subgroup with a point estimate and confidence interval. A vertical line = no effect (HR=1 or OR=1).

EXTRACT:

1. EFFECT MEASURE: HR, OR, RR, risk_difference?

2. OVERALL EFFECT (if shown): point estimate + CI

3. FOR EACH SUBGROUP ROW:
   - subgroup_name: exact label
   - n: number of patients if shown
   - effect_estimate: point value
   - ci_lower, ci_upper
   - events_experimental and events_control if shown
   - favors: "experimental" or "control" based on which side of 1.0

4. INTERACTION P-VALUES: if shown, for each subgroup

5. CONSISTENCY ASSESSMENT:
   - Do all subgroups favor the same direction?
   - Any subgroup where CI crosses 1.0 while others don't?
   - consistency_flag: "consistent", "heterogeneous", "signal_in_subgroup"

Return ONLY valid JSON.

{{"effect_measure": "...", "subgroups": [...], "interaction_p_values": [...], ...}}"""


SCORE_TIMECOURSE_EXTRACTION_PROMPT = """You are an expert clinical scientist extracting data from a score-over-time figure.

FIGURE CONTEXT:
- Trial: {trial_name}
- Drug: {drug_name}
- Indication: {indication}

This figure shows a clinical score (EASI, PASI, PANSS, MADRS, HbA1c, body weight, etc.) measured at multiple timepoints across treatment arms.

EXTRACT:

1. ENDPOINT: what score or measure is on the y-axis? (EASI, PASI, PANSS total, MADRS, HbA1c, body weight %, etc.)

2. Y-AXIS: units and direction (is decrease = improvement or increase = improvement?)

3. X-AXIS: timepoints in weeks, months, or visits?

4. NUMBER OF ARMS and their labels (from legend).

5. FOR EACH ARM:
   - arm_name: exact label from legend
   - arm_type: experimental, control, placebo
   - n_patients: if shown
   - baseline_value: value at week 0 / baseline
   - datapoints: [{{"week": 0, "value": 28.5, "se": 1.2}}, {{"week": 4, "value": 18.3, "se": 1.5}}, ...]
   - final_value: last timepoint value
   - pct_change_from_baseline: if shown or calculable
   - separation_from_placebo: difference vs placebo at primary timepoint

6. PRIMARY TIMEPOINT: which timepoint is the primary endpoint? (usually noted in title or highlighted)

7. STATISTICAL ANNOTATIONS: p-values, asterisks, significance markers at specific timepoints

8. CONFIDENCE INTERVALS or ERROR BARS: SEM, SD, 95% CI?

9. TREATMENT PERIOD vs FOLLOW-UP: is there a line marking end of treatment / withdrawal period?

Return ONLY valid JSON. Use null for values you cannot determine.

{{"endpoint_name": "...", "direction": "...", "arms": [...], "primary_timepoint_week": ..., ...}}"""


RESPONDER_BAR_EXTRACTION_PROMPT = """You are an expert clinical scientist extracting data from a responder rate bar chart.

FIGURE CONTEXT:
- Trial: {trial_name}
- Drug: {drug_name}
- Indication: {indication}

This figure shows responder rates (percentage of patients achieving a threshold) across treatment arms, often with multiple thresholds grouped together.

EXTRACT:

1. RESPONSE CRITERIA: what system? (EASI-50/75/90, PASI-75/90/100, ACR20/50/70, IGA 0/1, weight loss >=5%/10%/15%, etc.)

2. TIMEPOINT: at what visit/week were these rates measured?

3. FOR EACH BAR GROUP:
   - arm_name: treatment arm label
   - arm_type: experimental, control, placebo
   - n_patients: denominator if shown
   - responder_rates: [{{"threshold": "EASI-75", "rate": 0.62, "ci_lower": 0.54, "ci_upper": 0.70, "p_value": "<0.001"}}]

4. STATISTICAL COMPARISONS: p-values vs placebo or vs active comparator for each threshold

5. DOSE GROUPS: if multiple doses shown, list each separately

6. SUMMARY: which arm/dose had the highest rate at each threshold?

Return ONLY valid JSON.

{{"response_criteria": "...", "timepoint_week": ..., "comparisons": [...], ...}}"""


DOSE_RESPONSE_EXTRACTION_PROMPT = """You are an expert clinical pharmacologist extracting data from a dose-response figure.

FIGURE CONTEXT:
- Trial: {trial_name}
- Drug: {drug_name}
- Indication: {indication}

This figure shows efficacy and/or safety across different dose levels.

EXTRACT:

1. ENDPOINT on y-axis (efficacy measure, AE rate, biomarker, PK parameter)

2. DOSE LEVELS on x-axis (mg, mg/kg, etc.)

3. FOR EACH DOSE LEVEL:
   - dose: value and unit
   - n_patients: if shown
   - efficacy_value: primary endpoint value
   - efficacy_ci: confidence interval if shown
   - response_rate: if applicable
   - ae_rate: adverse event rate if shown on same or companion panel

4. DOSE-RESPONSE RELATIONSHIP:
   - dose_response_trend: "clear_monotonic", "plateau", "bell_shaped", "flat", "inverse_at_high_dose"
   - plateau_dose: dose where additional benefit appears to plateau (if applicable)
   - recommended_phase3_dose: if noted or inferable
   - therapeutic_index_note: any note about the balance between efficacy and toxicity

5. STATISTICAL TESTS: dose-response trend test, pairwise comparisons

Return ONLY valid JSON.

{{"endpoint_name": "...", "doses": [...], "dose_response_trend": "...", ...}}"""


# Map figure types to their extraction prompts
EXTRACTION_PROMPTS = {
    "kaplan_meier": KM_EXTRACTION_PROMPT,
    "waterfall": WATERFALL_EXTRACTION_PROMPT,
    "swimmer": SWIMMER_EXTRACTION_PROMPT,
    "spider": SPIDER_EXTRACTION_PROMPT,
    "forest": FOREST_EXTRACTION_PROMPT,
    "score_over_time": SCORE_TIMECOURSE_EXTRACTION_PROMPT,
    "responder_bar_chart": RESPONDER_BAR_EXTRACTION_PROMPT,
    "dose_response": DOSE_RESPONSE_EXTRACTION_PROMPT,
}

# Figure types that contain extractable clinical data
CLINICAL_FIGURE_TYPES = {
    "kaplan_meier", "waterfall", "swimmer", "spider", "forest",
    "score_over_time", "responder_bar_chart", "dose_response",
}


# ---------------------------------------------------------------------------
# Core extractor class
# ---------------------------------------------------------------------------

class FigureExtractor:
    """
    Extracts structured clinical data from biotech figure images using
    Claude's vision API. Replaces the old generic figure_annotator.py.

    The key differences from the old system:
    1. Figure-type-specific prompts (not one-size-fits-all)
    2. Output matches the Postgres knowledge graph schema exactly
    3. Confidence scoring per extraction
    4. Cross-linkable patient_index fields across figure types
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.client = httpx.Client(timeout=120.0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, image_path: str) -> str:
        """Classify a figure image into one of the known types."""
        b64 = self._encode_image(image_path)
        media_type = self._media_type(image_path)

        response = self._call_vision(
            system="You are a clinical figure classifier.",
            prompt=FIGURE_CLASSIFIER_PROMPT,
            image_b64=b64,
            media_type=media_type,
            max_tokens=50,
        )
        return response.strip().lower()

    def extract(
        self,
        image_path: str,
        figure_type: Optional[str] = None,
        trial_name: str = "Unknown",
        drug_name: str = "Unknown",
        indication: str = "Unknown",
    ) -> dict:
        """
        Extract structured data from a clinical figure.

        Args:
            image_path: Path to the figure image (PNG/JPG)
            figure_type: One of 'kaplan_meier', 'waterfall', 'swimmer', 'spider', 'forest'.
                         If None, will auto-classify first.
            trial_name: Name of the trial (for context in the prompt)
            drug_name: Name of the drug
            indication: Disease indication

        Returns:
            dict matching the corresponding Postgres table schema
        """
        # Auto-classify if needed
        if figure_type is None:
            figure_type = self.classify(image_path)

        if figure_type not in CLINICAL_FIGURE_TYPES:
            return {
                "figure_type": figure_type,
                "extractable": False,
                "reason": f"Figure type '{figure_type}' does not contain structured clinical data",
            }

        # Get the right prompt template
        prompt_template = EXTRACTION_PROMPTS[figure_type]
        prompt = prompt_template.format(
            trial_name=trial_name,
            drug_name=drug_name,
            indication=indication,
        )

        # Call vision API
        b64 = self._encode_image(image_path)
        media_type = self._media_type(image_path)

        raw_response = self._call_vision(
            system="You are an expert oncology biostatistician. Extract structured data from clinical trial figures with precision. Return ONLY valid JSON.",
            prompt=prompt,
            image_b64=b64,
            media_type=media_type,
            max_tokens=self.max_tokens,
        )

        # Parse JSON response
        result = self._parse_json_response(raw_response)
        result["figure_type"] = figure_type
        result["source_image"] = str(image_path)

        return result

    def extract_batch(
        self,
        image_paths: list[str],
        trial_name: str = "Unknown",
        drug_name: str = "Unknown",
        indication: str = "Unknown",
    ) -> list[dict]:
        """Extract from multiple figures, auto-classifying each."""
        results = []
        for path in image_paths:
            try:
                result = self.extract(
                    path,
                    trial_name=trial_name,
                    drug_name=drug_name,
                    indication=indication,
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "source_image": str(path),
                    "error": str(e),
                    "extractable": False,
                })
        return results

    # ------------------------------------------------------------------
    # Cross-linking: match patient_index across figure types
    # ------------------------------------------------------------------

    @staticmethod
    def cross_link_patient_data(
        waterfall: Optional[dict],
        swimmer: Optional[dict],
        spider: Optional[dict],
    ) -> list[dict]:
        """
        Cross-link patient-level data across figure types using patient_index.

        This is the core analytical capability: linking a patient's response
        depth (waterfall bar) to their response duration (swimmer lane) to
        their tumor kinetics (spider trace).

        Returns a list of patient-level records ready for the
        patient_responses table.
        """
        patients = {}

        # Index waterfall responses by patient_index
        if waterfall and "individual_responses" in waterfall:
            for resp in waterfall["individual_responses"]:
                idx = resp.get("patient_index")
                if idx is not None:
                    patients.setdefault(idx, {})
                    patients[idx].update({
                        "patient_index": idx,
                        "best_pct_change": resp.get("pct_change"),
                        "best_overall_response": resp.get("best_response"),
                        "biomarker_status": resp.get("biomarker_status"),
                        "assessment_criteria": waterfall.get("assessment_criteria"),
                    })

        # Add swimmer durability data
        if swimmer and "lanes" in swimmer:
            for lane in swimmer["lanes"]:
                idx = lane.get("patient_index")
                if idx is not None:
                    patients.setdefault(idx, {"patient_index": idx})
                    patients[idx].update({
                        "duration_of_response_months": lane.get("total_duration_months"),
                        "dor_censored": lane.get("still_ongoing"),
                        "reason_off_treatment": lane.get("reason_off_study"),
                        "still_on_treatment": lane.get("still_ongoing"),
                    })
                    # Check for response deepening
                    events = lane.get("events", [])
                    response_types = [e["type"] for e in events if e.get("type") in ("CR", "CRi", "PR", "VGPR")]
                    if len(response_types) >= 2:
                        # Response categories ordered by depth
                        depth_order = ["SD", "MR", "PR", "VGPR", "CRi", "CRh", "nCR", "CR"]
                        first_idx = depth_order.index(response_types[0]) if response_types[0] in depth_order else -1
                        last_idx = depth_order.index(response_types[-1]) if response_types[-1] in depth_order else -1
                        patients[idx]["response_deepened"] = last_idx > first_idx
                        patients[idx]["response_deepening_timeline"] = [
                            {"month": e["month"], "status": e["type"]}
                            for e in events if e.get("type") in depth_order
                        ]

        # Add spider kinetics data
        if spider and "traces" in spider:
            for trace in spider["traces"]:
                idx = trace.get("patient_index")
                if idx is not None:
                    patients.setdefault(idx, {"patient_index": idx})
                    patients[idx].update({
                        "tumor_measurements": trace.get("datapoints"),
                        "nadir_pct_change": trace.get("nadir_value"),
                        "nadir_timepoint_weeks": trace.get("nadir_time"),
                        "post_nadir_trajectory": _classify_post_nadir(trace),
                    })

        return list(patients.values())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _call_vision(
        self,
        system: str,
        prompt: str,
        image_b64: str,
        media_type: str,
        max_tokens: int = 4096,
    ) -> str:
        """Call Claude Vision API with an image."""
        response = self.client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

    @staticmethod
    def _encode_image(path: str) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def _media_type(path: str) -> str:
        ext = Path(path).suffix.lower()
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(ext, "image/png")

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        """Parse JSON from LLM response, handling markdown code fences."""
        text = raw.strip()
        if text.startswith("```"):
            # Remove code fences
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_response": raw, "parse_error": True}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _classify_post_nadir(trace: dict) -> str:
    """Classify post-nadir trajectory from spider plot datapoints."""
    datapoints = trace.get("datapoints", [])
    nadir_time = trace.get("nadir_time")
    if not datapoints or nadir_time is None:
        return "unknown"

    post_nadir = [d for d in datapoints if d.get("time", 0) > nadir_time]
    if not post_nadir:
        return "sustained"  # no data after nadir = still shrinking or stable

    final_value = post_nadir[-1].get("value", 0)
    nadir_value = trace.get("nadir_value", 0)

    if nadir_value is None:
        return "unknown"

    regrowth = final_value - nadir_value
    if regrowth <= 5:
        return "sustained"
    elif regrowth <= 20:
        return "slow_regrowth"
    else:
        return "rapid_regrowth"
