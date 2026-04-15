"""
SatyaBio Therapeutic Area Configuration System

This module defines the clinical analytical framework for each therapeutic area.
Adding a new TA means creating a new config — no code changes required.

Each TA config defines:
- What clinical endpoints matter (and what units they use)
- What response criteria are used (RECIST, EASI, PANSS, etc.)
- What figure types are relevant and how to extract them
- What "response depth" means in this context
- How to assess quality and durability
- What the competitive comparison dimensions are

Usage:
    from config.therapeutic_areas import get_ta_config, list_therapeutic_areas

    config = get_ta_config("oncology_solid")
    config = get_ta_config("autoimmune_derm")
    config = get_ta_config("neuropsych")

    # Or look up by indication
    config = get_ta_config_for_indication("atopic dermatitis")
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EndpointDefinition:
    """Defines a clinical endpoint and how to interpret it."""
    name: str                       # 'OS', 'PFS', 'EASI', 'PANSS_total', 'HbA1c'
    display_name: str               # 'Overall survival', 'EASI score', 'PANSS total score'
    unit: str                       # 'months', 'score', 'percent', 'percent_change', 'absolute_change'
    direction: str                  # 'lower_is_better', 'higher_is_better', 'time_to_event'
    primary_in: list[str] = field(default_factory=list)  # ['1L NSCLC', '2L+ CRC'] — where this is a primary endpoint
    clinically_meaningful_delta: Optional[float] = None   # MCID if known


@dataclass
class ResponseCriteria:
    """Defines response assessment criteria for a therapeutic area."""
    name: str                       # 'RECIST_1.1', 'EASI', 'PANSS', 'ACR', 'PASI'
    categories: list[str]           # ordered from worst to best response
    is_continuous: bool             # True for EASI/PANSS (scores), False for RECIST (CR/PR/SD/PD)
    threshold_type: str             # 'pct_change_from_baseline', 'absolute_change', 'categorical', 'responder_rate'
    responder_thresholds: dict = field(default_factory=dict)  # {'EASI-50': 50, 'EASI-75': 75, 'EASI-90': 90}
    pr_threshold: Optional[float] = None   # -30 for RECIST
    pd_threshold: Optional[float] = None   # +20 for RECIST


@dataclass
class FigureTypeConfig:
    """Defines what figure types are relevant for a therapeutic area."""
    figure_type: str                # 'kaplan_meier', 'waterfall', 'responder_bar_chart', 'score_over_time', 'dose_response'
    relevance: str                  # 'primary', 'secondary', 'rare'
    extraction_prompt_key: str      # key to look up the extraction prompt
    output_table: str               # which Postgres table to write to


@dataclass
class ThresholdConfig:
    """Response quality thresholds, calibrated per TA."""
    meaningful: float               # floor for "this drug does something"
    deep: float                     # top quartile
    exceptional: float              # top decile
    threshold_unit: str             # 'pct_change', 'response_category', 'score_change'
    is_categorical: bool = False    # True for heme (CR > VGPR > PR), False for continuous


@dataclass
class TherapeuticAreaConfig:
    """Complete configuration for a therapeutic area."""
    ta_id: str                              # 'oncology_solid', 'heme', 'autoimmune_derm', 'neuropsych'
    display_name: str
    description: str

    # Clinical framework
    primary_endpoints: list[EndpointDefinition]
    secondary_endpoints: list[EndpointDefinition]
    response_criteria: list[ResponseCriteria]

    # Figure extraction
    figure_types: list[FigureTypeConfig]

    # Response quality thresholds (fallback when landscape data is sparse)
    default_thresholds: dict[str, ThresholdConfig]  # keyed by modality_class

    # Competitive comparison dimensions — what matters for cross-trial comparison
    comparison_dimensions: list[str]

    # Cross-trial caveat factors — what makes naive comparison dangerous
    caveat_factors: list[str]

    # Analyst prompt context — injected into LLM narrative generation
    analyst_context: str


# ============================================================================
# THERAPEUTIC AREA CONFIGURATIONS
# ============================================================================

ONCOLOGY_SOLID = TherapeuticAreaConfig(
    ta_id="oncology_solid",
    display_name="Oncology — solid tumors",
    description="Solid tumor malignancies assessed by imaging-based response criteria",

    primary_endpoints=[
        EndpointDefinition("OS", "Overall survival", "months", "time_to_event", ["most solid tumors"]),
        EndpointDefinition("PFS", "Progression-free survival", "months", "time_to_event", ["most solid tumors"]),
        EndpointDefinition("ORR", "Objective response rate", "percent", "higher_is_better"),
        EndpointDefinition("DOR", "Duration of response", "months", "time_to_event"),
    ],
    secondary_endpoints=[
        EndpointDefinition("DCR", "Disease control rate", "percent", "higher_is_better"),
        EndpointDefinition("CBR", "Clinical benefit rate", "percent", "higher_is_better"),
        EndpointDefinition("TTP", "Time to progression", "months", "time_to_event"),
        EndpointDefinition("DFS", "Disease-free survival", "months", "time_to_event", ["adjuvant settings"]),
        EndpointDefinition("EFS", "Event-free survival", "months", "time_to_event", ["neoadjuvant/perioperative"]),
    ],
    response_criteria=[
        ResponseCriteria("RECIST_1.1", ["CR", "PR", "SD", "PD", "NE"], is_continuous=False,
                        threshold_type="pct_change_from_baseline", pr_threshold=-30, pd_threshold=20),
        ResponseCriteria("iRECIST", ["iCR", "iPR", "iSD", "iUPD", "iCPD", "NE"], is_continuous=False,
                        threshold_type="pct_change_from_baseline", pr_threshold=-30, pd_threshold=20),
        ResponseCriteria("mRECIST", ["CR", "PR", "SD", "PD", "NE"], is_continuous=False,
                        threshold_type="pct_change_from_baseline", pr_threshold=-30, pd_threshold=20),
        ResponseCriteria("RANO", ["CR", "PR", "SD", "PD", "NE"], is_continuous=False,
                        threshold_type="pct_change_from_baseline"),
    ],
    figure_types=[
        FigureTypeConfig("kaplan_meier", "primary", "km_extraction", "km_results"),
        FigureTypeConfig("waterfall", "primary", "waterfall_extraction", "waterfall_results"),
        FigureTypeConfig("swimmer", "primary", "swimmer_extraction", "swimmer_results"),
        FigureTypeConfig("spider", "secondary", "spider_extraction", "spider_results"),
        FigureTypeConfig("forest", "primary", "forest_extraction", "forest_results"),
    ],
    default_thresholds={
        "IO":           ThresholdConfig(-30, -50, -80, "pct_change"),
        "TKI":          ThresholdConfig(-30, -60, -90, "pct_change"),
        "chemo":        ThresholdConfig(-30, -40, -60, "pct_change"),
        "ADC":          ThresholdConfig(-30, -50, -75, "pct_change"),
        "bispecific":   ThresholdConfig(-30, -50, -75, "pct_change"),
        "degrader":     ThresholdConfig(-30, -50, -75, "pct_change"),
        "radioligand":  ThresholdConfig(-30, -50, -75, "pct_change"),
        "default":      ThresholdConfig(-30, -50, -75, "pct_change"),
    },
    comparison_dimensions=[
        "ORR", "CR rate", "median PFS", "median OS", "median DOR",
        "durable response rate", "depth-durability correlation",
        "biomarker-selected ORR", "safety (Grade 3+ AE rate)",
    ],
    caveat_factors=[
        "trial design (single-arm vs randomized)",
        "control arm choice",
        "line of therapy",
        "biomarker selection criteria",
        "patient population differences (ECOG, prior therapies, CNS metastases)",
        "crossover allowed/rate",
        "data maturity and follow-up duration",
        "response criteria version",
    ],
    analyst_context="""You are a PhD oncologist and biotech investment analyst.
    Focus on: response depth vs durability correlation, censoring patterns,
    curve shape interpretation, cross-trial comparability caveats,
    and resistance mechanism implications from spider plot kinetics."""
)


HEME_MALIGNANCY = TherapeuticAreaConfig(
    ta_id="heme",
    display_name="Hematologic malignancies",
    description="Blood cancers assessed by categorical response criteria (IWG, IMWG, iwCLL, Lugano)",

    primary_endpoints=[
        EndpointDefinition("CR_rate", "Complete remission rate", "percent", "higher_is_better"),
        EndpointDefinition("ORR", "Overall response rate", "percent", "higher_is_better"),
        EndpointDefinition("MRD_neg_rate", "MRD negativity rate", "percent", "higher_is_better"),
        EndpointDefinition("PFS", "Progression-free survival", "months", "time_to_event"),
        EndpointDefinition("OS", "Overall survival", "months", "time_to_event"),
        EndpointDefinition("EFS", "Event-free survival", "months", "time_to_event"),
        EndpointDefinition("DOR", "Duration of response", "months", "time_to_event"),
    ],
    secondary_endpoints=[
        EndpointDefinition("transfusion_independence", "Transfusion independence rate", "percent", "higher_is_better"),
        EndpointDefinition("TTNT", "Time to next treatment", "months", "time_to_event"),
        EndpointDefinition("relapse_free_survival", "Relapse-free survival", "months", "time_to_event"),
    ],
    response_criteria=[
        ResponseCriteria("IWG_AML", ["CR", "CRp", "CRh", "CRi", "MLFS", "HI", "SD", "PD", "NE"],
                        is_continuous=False, threshold_type="categorical"),
        ResponseCriteria("iwCLL", ["CR", "CRi", "nPR", "PR", "SD", "PD", "NE"],
                        is_continuous=False, threshold_type="categorical"),
        ResponseCriteria("IMWG", ["sCR", "CR", "VGPR", "PR", "MR", "SD", "PD", "NE"],
                        is_continuous=False, threshold_type="categorical"),
        ResponseCriteria("Lugano", ["CR", "PR", "SD", "PD", "NE"],
                        is_continuous=False, threshold_type="categorical"),
    ],
    figure_types=[
        FigureTypeConfig("kaplan_meier", "primary", "km_extraction", "km_results"),
        FigureTypeConfig("response_bar_chart", "primary", "response_bar_extraction", "waterfall_results"),
        FigureTypeConfig("swimmer", "primary", "swimmer_extraction", "swimmer_results"),
        FigureTypeConfig("forest", "primary", "forest_extraction", "forest_results"),
        FigureTypeConfig("mrd_kinetics", "secondary", "mrd_kinetics_extraction", "spider_results"),
    ],
    default_thresholds={
        # Categorical — "deep" = CR, "exceptional" = CR + MRD-neg
        "default": ThresholdConfig(meaningful=3, deep=1, exceptional=0,
                                   threshold_unit="response_category", is_categorical=True),
    },
    comparison_dimensions=[
        "CR rate", "MRD negativity rate", "ORR", "median PFS", "median DOR",
        "fixed-duration vs continuous therapy", "time to CR",
        "CR durability", "safety (CRS rate for bispecifics/CAR-T)",
    ],
    caveat_factors=[
        "response criteria version (IWG 2003 vs 2022, iwCLL 2008 vs 2018)",
        "MRD sensitivity threshold (10^-4 vs 10^-5 vs 10^-6)",
        "MRD assay method (flow cytometry vs NGS vs PCR)",
        "patient population (de novo vs relapsed, cytogenetic risk)",
        "prior lines and prior drug classes",
        "fixed-duration vs treat-to-progression",
    ],
    analyst_context="""You are a PhD hematologist and biotech investment analyst.
    Focus on: depth of remission (CR vs CRi vs VGPR), MRD negativity rates and
    sustainability, fixed-duration treatment potential, and how response depth
    correlates with PFS/OS. In heme, categorical response depth matters more
    than continuous tumor shrinkage."""
)


AUTOIMMUNE_DERM = TherapeuticAreaConfig(
    ta_id="autoimmune_derm",
    display_name="Autoimmune — dermatology",
    description="Inflammatory skin diseases assessed by continuous scoring systems (EASI, PASI, IGA)",

    primary_endpoints=[
        EndpointDefinition("EASI", "Eczema Area and Severity Index", "score", "lower_is_better",
                          clinically_meaningful_delta=6.6),
        EndpointDefinition("EASI_pct_change", "EASI % change from baseline", "percent_change", "lower_is_better"),
        EndpointDefinition("IGA_0_1", "IGA 0/1 (clear/almost clear) rate", "percent", "higher_is_better"),
        EndpointDefinition("PASI", "Psoriasis Area and Severity Index", "score", "lower_is_better"),
        EndpointDefinition("PASI_pct_change", "PASI % change from baseline", "percent_change", "lower_is_better"),
    ],
    secondary_endpoints=[
        EndpointDefinition("DLQI", "Dermatology Life Quality Index", "score", "lower_is_better",
                          clinically_meaningful_delta=4.0),
        EndpointDefinition("pruritus_NRS", "Pruritus NRS (itch)", "score", "lower_is_better",
                          clinically_meaningful_delta=4.0),
        EndpointDefinition("SCORAD", "SCORAD index", "score", "lower_is_better"),
        EndpointDefinition("BSA", "Body surface area affected", "percent", "lower_is_better"),
    ],
    response_criteria=[
        ResponseCriteria("EASI", ["EASI-50", "EASI-75", "EASI-90", "EASI-100"],
                        is_continuous=True, threshold_type="responder_rate",
                        responder_thresholds={"EASI-50": 50, "EASI-75": 75, "EASI-90": 90, "EASI-100": 100}),
        ResponseCriteria("PASI", ["PASI-50", "PASI-75", "PASI-90", "PASI-100"],
                        is_continuous=True, threshold_type="responder_rate",
                        responder_thresholds={"PASI-50": 50, "PASI-75": 75, "PASI-90": 90, "PASI-100": 100}),
        ResponseCriteria("IGA", ["0", "1", "2", "3", "4"],
                        is_continuous=False, threshold_type="categorical"),
    ],
    figure_types=[
        FigureTypeConfig("score_over_time", "primary", "score_timecourse_extraction", "endpoint_timecourse_results"),
        FigureTypeConfig("responder_bar_chart", "primary", "responder_bar_extraction", "responder_results"),
        FigureTypeConfig("dose_response", "secondary", "dose_response_extraction", "dose_response_results"),
        FigureTypeConfig("kaplan_meier", "secondary", "km_extraction", "km_results"),  # time to relapse
        FigureTypeConfig("forest", "secondary", "forest_extraction", "forest_results"),
    ],
    default_thresholds={
        "biologic":     ThresholdConfig(meaningful=50, deep=75, exceptional=90,
                                        threshold_unit="easi_responder_pct"),
        "JAK_inhibitor": ThresholdConfig(meaningful=50, deep=75, exceptional=90,
                                         threshold_unit="easi_responder_pct"),
        "degrader":     ThresholdConfig(meaningful=50, deep=75, exceptional=90,
                                        threshold_unit="easi_responder_pct"),
        "default":      ThresholdConfig(meaningful=50, deep=75, exceptional=90,
                                        threshold_unit="easi_responder_pct"),
    },
    comparison_dimensions=[
        "EASI-75 rate at week 16", "EASI-90 rate", "IGA 0/1 rate",
        "speed of onset (week 4 EASI change)", "durability after withdrawal",
        "pruritus NRS improvement", "safety (infection rate, malignancy signal)",
        "route and dosing convenience",
    ],
    caveat_factors=[
        "baseline disease severity (moderate vs severe)",
        "prior biologic exposure",
        "concomitant TCS use allowed/required",
        "primary endpoint timepoint (week 12 vs 16 vs 24)",
        "placebo response rate differences",
        "rescue medication rules",
    ],
    analyst_context="""You are a dermatology clinical expert and biotech investment analyst.
    Focus on: EASI-75/90 responder rates and onset speed, IGA 0/1 achievement,
    durability after treatment withdrawal (relapse kinetics), and head-to-head
    positioning vs dupilumab. Differentiation in this space is about speed,
    depth (EASI-90 vs EASI-75), and maintenance of response off-treatment."""
)


AUTOIMMUNE_RHEUM = TherapeuticAreaConfig(
    ta_id="autoimmune_rheum",
    display_name="Autoimmune — rheumatology / GI",
    description="Systemic autoimmune and inflammatory GI diseases (RA, SLE, UC, Crohn's, IBD)",

    primary_endpoints=[
        EndpointDefinition("ACR20", "ACR20 response rate", "percent", "higher_is_better"),
        EndpointDefinition("ACR50", "ACR50 response rate", "percent", "higher_is_better"),
        EndpointDefinition("ACR70", "ACR70 response rate", "percent", "higher_is_better"),
        EndpointDefinition("SRI4", "SRI-4 response rate (SLE)", "percent", "higher_is_better"),
        EndpointDefinition("CDAI_remission", "CDAI clinical remission rate", "percent", "higher_is_better"),
        EndpointDefinition("Mayo_endoscopic", "Mayo endoscopic subscore improvement", "percent", "higher_is_better"),
        EndpointDefinition("endoscopic_remission", "Endoscopic remission rate (UC/Crohn's)", "percent", "higher_is_better"),
    ],
    secondary_endpoints=[
        EndpointDefinition("DAS28_CRP", "DAS28-CRP score", "score", "lower_is_better"),
        EndpointDefinition("HAQ_DI", "HAQ-DI improvement", "score", "lower_is_better"),
        EndpointDefinition("SLEDAI", "SLEDAI-2K score", "score", "lower_is_better"),
        EndpointDefinition("steroid_sparing", "Steroid-free remission rate", "percent", "higher_is_better"),
        EndpointDefinition("histologic_remission", "Histologic remission rate", "percent", "higher_is_better"),
    ],
    response_criteria=[
        ResponseCriteria("ACR", ["ACR20", "ACR50", "ACR70"],
                        is_continuous=True, threshold_type="responder_rate",
                        responder_thresholds={"ACR20": 20, "ACR50": 50, "ACR70": 70}),
        ResponseCriteria("SRI", ["SRI-4", "SRI-5", "SRI-6", "SRI-7", "SRI-8"],
                        is_continuous=True, threshold_type="responder_rate"),
        ResponseCriteria("Mayo", ["remission", "response", "no_response"],
                        is_continuous=False, threshold_type="categorical"),
    ],
    figure_types=[
        FigureTypeConfig("responder_bar_chart", "primary", "responder_bar_extraction", "responder_results"),
        FigureTypeConfig("score_over_time", "primary", "score_timecourse_extraction", "endpoint_timecourse_results"),
        FigureTypeConfig("kaplan_meier", "secondary", "km_extraction", "km_results"),
        FigureTypeConfig("forest", "primary", "forest_extraction", "forest_results"),
        FigureTypeConfig("endoscopy_images", "secondary", "endoscopy_extraction", "qualitative_results"),
    ],
    default_thresholds={
        "biologic":     ThresholdConfig(meaningful=20, deep=50, exceptional=70,
                                        threshold_unit="acr_responder_level"),
        "JAK_inhibitor": ThresholdConfig(meaningful=20, deep=50, exceptional=70,
                                         threshold_unit="acr_responder_level"),
        "default":      ThresholdConfig(meaningful=20, deep=50, exceptional=70,
                                        threshold_unit="acr_responder_level"),
    },
    comparison_dimensions=[
        "ACR50 rate at primary timepoint", "ACR70 rate", "DAS28 remission rate",
        "radiographic progression inhibition", "speed of onset",
        "steroid-sparing ability", "safety (infection, cardiovascular, malignancy)",
    ],
    caveat_factors=[
        "inadequate responder to what (csDMARD-IR vs bDMARD-IR vs JAK-IR)",
        "concomitant methotrexate allowed/required",
        "baseline disease activity and duration",
        "prior biologic exposure and number of prior failures",
        "primary endpoint timepoint",
        "rescue medication rules",
    ],
    analyst_context="""You are a rheumatology/GI clinical expert and biotech investment analyst.
    Focus on: ACR50/70 rates (not just ACR20), speed of onset, head-to-head data
    vs TNF inhibitors and JAK inhibitors, steroid-sparing, and for GI — endoscopic
    vs clinical remission rates and histologic endpoints."""
)


NEUROPSYCH = TherapeuticAreaConfig(
    ta_id="neuropsych",
    display_name="Neuropsychiatry",
    description="CNS, psychiatric, and neurological diseases assessed by clinical rating scales",

    primary_endpoints=[
        EndpointDefinition("PANSS_total", "PANSS total score change", "score_change", "lower_is_better",
                          clinically_meaningful_delta=15),
        EndpointDefinition("MADRS", "MADRS total score change", "score_change", "lower_is_better",
                          clinically_meaningful_delta=2),
        EndpointDefinition("CGI_S", "CGI-S improvement", "score", "lower_is_better"),
        EndpointDefinition("ADAS_Cog", "ADAS-Cog score change (AD)", "score_change", "lower_is_better"),
        EndpointDefinition("MDS_UPDRS", "MDS-UPDRS Part II+III (PD)", "score_change", "lower_is_better"),
        EndpointDefinition("seizure_frequency", "Seizure frequency reduction", "percent_change", "lower_is_better"),
        EndpointDefinition("annualized_relapse_rate", "Annualized relapse rate (MS)", "rate", "lower_is_better"),
    ],
    secondary_endpoints=[
        EndpointDefinition("PANSS_positive", "PANSS positive subscale", "score_change", "lower_is_better"),
        EndpointDefinition("PANSS_negative", "PANSS negative subscale", "score_change", "lower_is_better"),
        EndpointDefinition("HAM_D", "HAM-D score change", "score_change", "lower_is_better"),
        EndpointDefinition("PHQ_9", "PHQ-9 score change", "score_change", "lower_is_better"),
        EndpointDefinition("CDR_SB", "CDR-SB score change (AD)", "score_change", "lower_is_better"),
        EndpointDefinition("MWT", "Maintenance of Wakefulness Test (narcolepsy)", "minutes", "higher_is_better"),
        EndpointDefinition("ESS", "Epworth Sleepiness Scale", "score", "lower_is_better"),
    ],
    response_criteria=[
        ResponseCriteria("PANSS_response", [">=30% reduction", ">=50% reduction", "remission"],
                        is_continuous=True, threshold_type="responder_rate",
                        responder_thresholds={"response": 30, "robust_response": 50}),
        ResponseCriteria("MADRS_response", [">=50% reduction", "remission (<=10)"],
                        is_continuous=True, threshold_type="responder_rate",
                        responder_thresholds={"response": 50}),
        ResponseCriteria("CGI_response", ["much improved", "very much improved"],
                        is_continuous=False, threshold_type="categorical"),
    ],
    figure_types=[
        FigureTypeConfig("score_over_time", "primary", "score_timecourse_extraction", "endpoint_timecourse_results"),
        FigureTypeConfig("responder_bar_chart", "primary", "responder_bar_extraction", "responder_results"),
        FigureTypeConfig("kaplan_meier", "secondary", "km_extraction", "km_results"),  # time to relapse
        FigureTypeConfig("forest", "secondary", "forest_extraction", "forest_results"),
        FigureTypeConfig("dose_response", "secondary", "dose_response_extraction", "dose_response_results"),
    ],
    default_thresholds={
        "default": ThresholdConfig(meaningful=15, deep=25, exceptional=35,
                                   threshold_unit="panss_total_change"),
    },
    comparison_dimensions=[
        "primary endpoint effect size vs placebo", "PANSS positive vs negative subscale",
        "speed of onset", "NNT (number needed to treat)",
        "weight and metabolic effects", "EPS/akathisia rates",
        "discontinuation rate due to AEs", "effect on negative symptoms",
    ],
    caveat_factors=[
        "baseline severity (PANSS total, MADRS)",
        "placebo response rate (varies enormously in psych trials)",
        "trial duration (4 vs 6 vs 8 weeks for acute, relapse prevention design)",
        "concomitant medications allowed",
        "enrichment design (placebo washout, single-blind lead-in)",
        "geographic site distribution (affects placebo rate)",
    ],
    analyst_context="""You are a neuropsychiatry clinical expert and biotech investment analyst.
    Focus on: effect size vs placebo (and the placebo rate itself), PANSS positive vs negative
    subscale separation, onset speed, metabolic and neurological safety, and the design enrichment
    question (did they use a placebo lead-in to suppress placebo response). In psychiatry,
    the placebo response rate IS the story — a drug that beats 40% placebo response by 10 points
    is very different from one that beats 25% placebo response by 10 points."""
)


METABOLIC = TherapeuticAreaConfig(
    ta_id="metabolic",
    display_name="Metabolic / endocrine",
    description="Diabetes, obesity, NASH/MASH, and metabolic disorders",

    primary_endpoints=[
        EndpointDefinition("HbA1c_change", "HbA1c change from baseline", "percent_change", "lower_is_better",
                          clinically_meaningful_delta=0.3),
        EndpointDefinition("body_weight_pct_change", "Body weight % change", "percent_change", "lower_is_better"),
        EndpointDefinition("NASH_resolution", "NASH resolution without fibrosis worsening", "percent", "higher_is_better"),
        EndpointDefinition("fibrosis_improvement", "Fibrosis improvement >= 1 stage", "percent", "higher_is_better"),
    ],
    secondary_endpoints=[
        EndpointDefinition("FPG", "Fasting plasma glucose change", "mg_dL", "lower_is_better"),
        EndpointDefinition("body_weight_5pct", "% achieving >=5% weight loss", "percent", "higher_is_better"),
        EndpointDefinition("body_weight_10pct", "% achieving >=10% weight loss", "percent", "higher_is_better"),
        EndpointDefinition("body_weight_15pct", "% achieving >=15% weight loss", "percent", "higher_is_better"),
        EndpointDefinition("NAS_score_change", "NAS score change", "score_change", "lower_is_better"),
        EndpointDefinition("ALT_normalization", "ALT normalization rate", "percent", "higher_is_better"),
    ],
    response_criteria=[
        ResponseCriteria("HbA1c_target", ["<7%", "<6.5%"],
                        is_continuous=True, threshold_type="responder_rate",
                        responder_thresholds={"target_7": 7.0, "target_6.5": 6.5}),
        ResponseCriteria("weight_loss", [">=5%", ">=10%", ">=15%", ">=20%"],
                        is_continuous=True, threshold_type="responder_rate",
                        responder_thresholds={"5pct": 5, "10pct": 10, "15pct": 15, "20pct": 20}),
    ],
    figure_types=[
        FigureTypeConfig("score_over_time", "primary", "score_timecourse_extraction", "endpoint_timecourse_results"),
        FigureTypeConfig("responder_bar_chart", "primary", "responder_bar_extraction", "responder_results"),
        FigureTypeConfig("waterfall", "secondary", "waterfall_extraction", "waterfall_results"),  # weight loss per patient
        FigureTypeConfig("dose_response", "primary", "dose_response_extraction", "dose_response_results"),
        FigureTypeConfig("forest", "secondary", "forest_extraction", "forest_results"),
    ],
    default_thresholds={
        "GLP1_RA":  ThresholdConfig(meaningful=5, deep=10, exceptional=15,
                                     threshold_unit="body_weight_pct_loss"),
        "default":  ThresholdConfig(meaningful=0.5, deep=1.0, exceptional=1.5,
                                     threshold_unit="hba1c_pct_reduction"),
    },
    comparison_dimensions=[
        "HbA1c reduction from baseline", "body weight % change",
        "% achieving >=10% and >=15% weight loss", "GI tolerability",
        "cardiovascular outcomes", "dosing frequency and route",
        "titration schedule", "manufacturing scalability",
    ],
    caveat_factors=[
        "baseline HbA1c and body weight",
        "background therapy (metformin, insulin, etc.)",
        "trial duration (short-term efficacy vs long-term outcomes)",
        "dose titration schedule differences",
        "GI AE-related discontinuation rate",
        "estimand (treatment policy vs on-treatment)",
    ],
    analyst_context="""You are a metabolic disease clinical expert and biotech investment analyst.
    Focus on: magnitude of weight loss (the bar keeps rising — 15%+ is now expected from
    next-gen GLP-1s), GI tolerability vs efficacy trade-off, oral vs injectable route,
    cardiovascular outcomes data, and muscle mass preservation. For NASH/MASH, focus on
    histologic endpoints and the gap between Phase 2 biomarker data and Phase 3 biopsy outcomes."""
)


RARE_DISEASE = TherapeuticAreaConfig(
    ta_id="rare_disease",
    display_name="Rare / genetic diseases",
    description="Rare genetic, enzymatic, and ultra-orphan diseases assessed by disease-specific functional and biomarker endpoints",

    primary_endpoints=[
        EndpointDefinition("enzyme_activity", "Enzyme activity level", "percent_normal", "higher_is_better"),
        EndpointDefinition("biomarker_reduction", "Disease biomarker reduction", "percent_change", "lower_is_better"),
        EndpointDefinition("functional_score", "Disease-specific functional score", "score", "lower_is_better"),
        EndpointDefinition("event_rate", "Annualized event/crisis rate", "rate", "lower_is_better"),
        EndpointDefinition("6MWT", "6-minute walk test distance", "meters", "higher_is_better",
                          clinically_meaningful_delta=30),
        EndpointDefinition("FVC", "Forced vital capacity", "percent_predicted", "higher_is_better"),
    ],
    secondary_endpoints=[
        EndpointDefinition("organ_volume", "Organ volume change (spleen/liver)", "percent_change", "lower_is_better"),
        EndpointDefinition("transfusion_burden", "Transfusion burden reduction", "percent_change", "lower_is_better"),
        EndpointDefinition("PRO", "Patient-reported outcome score", "score", "higher_is_better"),
        EndpointDefinition("growth_velocity", "Growth velocity (pediatric)", "cm_per_year", "higher_is_better"),
    ],
    response_criteria=[
        ResponseCriteria("biomarker_normalization", ["normalized", "improved", "stable", "worsened"],
                        is_continuous=False, threshold_type="categorical"),
        ResponseCriteria("functional_response", ["clinically meaningful improvement", "stable", "declined"],
                        is_continuous=False, threshold_type="categorical"),
    ],
    figure_types=[
        FigureTypeConfig("score_over_time", "primary", "score_timecourse_extraction", "endpoint_timecourse_results"),
        FigureTypeConfig("waterfall", "secondary", "waterfall_extraction", "waterfall_results"),
        FigureTypeConfig("responder_bar_chart", "primary", "responder_bar_extraction", "responder_results"),
        FigureTypeConfig("kaplan_meier", "secondary", "km_extraction", "km_results"),
        FigureTypeConfig("dose_response", "secondary", "dose_response_extraction", "dose_response_results"),
    ],
    default_thresholds={
        "gene_therapy":     ThresholdConfig(meaningful=10, deep=50, exceptional=80,
                                            threshold_unit="pct_normal_enzyme"),
        "ERT":              ThresholdConfig(meaningful=10, deep=50, exceptional=80,
                                            threshold_unit="pct_normal_enzyme"),
        "SRT":              ThresholdConfig(meaningful=20, deep=40, exceptional=60,
                                            threshold_unit="biomarker_pct_reduction"),
        "antisense":        ThresholdConfig(meaningful=20, deep=50, exceptional=70,
                                            threshold_unit="biomarker_pct_reduction"),
        "default":          ThresholdConfig(meaningful=20, deep=50, exceptional=70,
                                            threshold_unit="pct_improvement"),
    },
    comparison_dimensions=[
        "biomarker normalization rate", "functional endpoint improvement",
        "durability of effect", "route and dosing frequency",
        "immunogenicity (ADA rates)", "organ-specific response",
        "pediatric vs adult efficacy", "natural history comparison",
    ],
    caveat_factors=[
        "natural history comparator vs placebo-controlled",
        "disease severity and genotype distribution",
        "extremely small N (many trials <30 patients)",
        "endpoint heterogeneity across disease subtypes",
        "treatment-naive vs switch patients",
        "age and disease duration at treatment start",
        "single-center vs multi-center",
    ],
    analyst_context="""You are a rare disease clinical expert and biotech investment analyst.
    Focus on: biomarker normalization vs functional improvement disconnect,
    durability of gene therapy vs chronic ERT/SRT, immunogenicity risk (especially for
    gene therapy and ERT), small N trial interpretation challenges, natural history
    comparison validity, and regulatory path (accelerated approval on biomarker vs
    full approval on functional endpoints). In rare disease, the competitive landscape
    is often empty — differentiation is about access, convenience, and durability."""
)


# ============================================================================
# REGISTRY AND LOOKUP
# ============================================================================

_TA_REGISTRY: dict[str, TherapeuticAreaConfig] = {
    "oncology_solid": ONCOLOGY_SOLID,
    "oncology": ONCOLOGY_SOLID,       # alias
    "heme": HEME_MALIGNANCY,
    "hematology": HEME_MALIGNANCY,    # alias
    "autoimmune_derm": AUTOIMMUNE_DERM,
    "dermatology": AUTOIMMUNE_DERM,   # alias
    "autoimmune_rheum": AUTOIMMUNE_RHEUM,
    "rheumatology": AUTOIMMUNE_RHEUM, # alias
    "GI": AUTOIMMUNE_RHEUM,           # alias (UC/Crohn's share the config)
    "neuropsych": NEUROPSYCH,
    "neurology": NEUROPSYCH,          # alias
    "psychiatry": NEUROPSYCH,         # alias
    "metabolic": METABOLIC,
    "endocrine": METABOLIC,           # alias
    "rare_disease": RARE_DISEASE,
    "rare": RARE_DISEASE,             # alias
    "orphan": RARE_DISEASE,           # alias
}

# Indication → TA mapping (extensible, not hardcoded per-target)
_INDICATION_TA_MAP: dict[str, str] = {
    # Oncology solid
    "NSCLC": "oncology_solid", "CRC": "oncology_solid", "breast cancer": "oncology_solid",
    "melanoma": "oncology_solid", "RCC": "oncology_solid", "HCC": "oncology_solid",
    "pancreatic": "oncology_solid", "gastric": "oncology_solid", "SCLC": "oncology_solid",
    "ovarian": "oncology_solid", "prostate": "oncology_solid", "bladder": "oncology_solid",
    "head and neck": "oncology_solid", "glioblastoma": "oncology_solid",
    "cholangiocarcinoma": "oncology_solid", "mesothelioma": "oncology_solid",
    # Heme
    "AML": "heme", "CLL": "heme", "DLBCL": "heme", "follicular lymphoma": "heme",
    "multiple myeloma": "heme", "MDS": "heme", "ALL": "heme", "CML": "heme",
    "mantle cell lymphoma": "heme", "Waldenstrom": "heme", "marginal zone lymphoma": "heme",
    # Autoimmune derm
    "atopic dermatitis": "autoimmune_derm", "psoriasis": "autoimmune_derm",
    "vitiligo": "autoimmune_derm", "alopecia areata": "autoimmune_derm",
    "hidradenitis suppurativa": "autoimmune_derm", "prurigo nodularis": "autoimmune_derm",
    # Autoimmune rheum / GI
    "rheumatoid arthritis": "autoimmune_rheum", "SLE": "autoimmune_rheum",
    "lupus nephritis": "autoimmune_rheum", "ulcerative colitis": "autoimmune_rheum",
    "Crohn's disease": "autoimmune_rheum", "psoriatic arthritis": "autoimmune_rheum",
    "ankylosing spondylitis": "autoimmune_rheum", "IBD": "autoimmune_rheum",
    # Neuropsych
    "schizophrenia": "neuropsych", "MDD": "neuropsych", "bipolar": "neuropsych",
    "Alzheimer": "neuropsych", "Parkinson": "neuropsych", "epilepsy": "neuropsych",
    "narcolepsy": "neuropsych", "ADHD": "neuropsych", "ALS": "neuropsych",
    "multiple sclerosis": "neuropsych", "migraine": "neuropsych",
    # Metabolic
    "T2D": "metabolic", "obesity": "metabolic", "NASH": "metabolic", "MASH": "metabolic",
    "type 2 diabetes": "metabolic",
    # Rare disease
    "Gaucher": "rare_disease", "Fabry": "rare_disease", "Pompe": "rare_disease",
    "Hunter syndrome": "rare_disease", "MPS": "rare_disease", "SMA": "rare_disease",
    "Duchenne": "rare_disease", "DMD": "rare_disease", "hemophilia": "rare_disease",
    "sickle cell": "rare_disease", "PKU": "rare_disease", "cystic fibrosis": "rare_disease",
    "Huntington": "rare_disease", "Friedreich ataxia": "rare_disease",
    "hereditary angioedema": "rare_disease", "HAE": "rare_disease",
    "PNH": "rare_disease", "aHUS": "rare_disease", "TTP": "rare_disease",
}


def get_ta_config(ta_id: str) -> TherapeuticAreaConfig:
    """Get therapeutic area configuration by ID or alias."""
    config = _TA_REGISTRY.get(ta_id.lower())
    if config is None:
        raise ValueError(
            f"Unknown therapeutic area: '{ta_id}'. "
            f"Available: {list_therapeutic_areas()}"
        )
    return config


def get_ta_config_for_indication(indication: str) -> Optional[TherapeuticAreaConfig]:
    """Look up the therapeutic area for a given indication name."""
    indication_lower = indication.lower()
    for key, ta_id in _INDICATION_TA_MAP.items():
        if key.lower() in indication_lower:
            return _TA_REGISTRY[ta_id]
    return None


def list_therapeutic_areas() -> list[str]:
    """List all unique therapeutic area IDs (no aliases)."""
    seen = set()
    result = []
    for ta_id, config in _TA_REGISTRY.items():
        if config.ta_id not in seen:
            seen.add(config.ta_id)
            result.append(config.ta_id)
    return result


def register_therapeutic_area(config: TherapeuticAreaConfig, aliases: list[str] = None):
    """Register a new therapeutic area configuration at runtime."""
    _TA_REGISTRY[config.ta_id] = config
    if aliases:
        for alias in aliases:
            _TA_REGISTRY[alias.lower()] = config


def register_indication_mapping(indication: str, ta_id: str):
    """Map an indication name to a therapeutic area."""
    _INDICATION_TA_MAP[indication] = ta_id
