"""
Clinical Data Extractor - PhD-level analysis of clinical trial data.

Extracts structured data from clinical presentations and generates
analysis for the Satya Bio platform.

Integrates data from:
- kymera_full_extraction.py: Full pipeline data for KT-621, KT-579, KT-485
- endpoint_definitions.py: Contextual definitions for endpoints and biomarkers
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from .kymera_full_extraction import (
    KYMERA_COMPANY,
    KT621_DATA,
    KT579_DATA,
    KT485_DATA,
    STAT6_TARGET,
    IRF5_TARGET,
    IRAK4_TARGET,
    get_kymera_full_pipeline,
    get_asset_clinical_data,
    get_target_landscape,
)
from .endpoint_definitions import (
    ENDPOINT_DEFINITIONS,
    BIOMARKER_DEFINITIONS,
    get_endpoint_with_context,
    get_biomarker_with_context,
    get_all_endpoint_definitions,
    get_all_biomarker_definitions,
    get_kt621_data_with_context,
)


class TrialPhase(Enum):
    PHASE_1 = "Phase 1"
    PHASE_1B = "Phase 1b"
    PHASE_2 = "Phase 2"
    PHASE_2A = "Phase 2a"
    PHASE_2B = "Phase 2b"
    PHASE_3 = "Phase 3"


# =============================================================================
# MAIN EXTRACTION FUNCTIONS
# =============================================================================

def generate_clinical_summary_for_asset(asset_name: str) -> dict:
    """
    Generate complete clinical data package for an asset with contextual definitions.

    Supports: KT-621, KT-579, KT-485
    """
    asset_upper = asset_name.upper()

    if asset_upper == "KT-621":
        return _generate_kt621_summary_with_context()
    elif asset_upper == "KT-579":
        return _generate_kt579_summary_with_context()
    elif asset_upper == "KT-485":
        return _generate_kt485_summary_with_context()
    else:
        raise ValueError(f"Unknown asset: {asset_name}. Supported: KT-621, KT-579, KT-485")


def _generate_kt621_summary_with_context() -> dict:
    """Generate KT-621 summary with embedded contextual definitions."""
    base_data = KT621_DATA.copy()
    context_data = get_kt621_data_with_context()

    # Enrich trials with endpoint definitions
    enriched_trials = []
    for trial in base_data.get("trials", []):
        enriched_trial = trial.copy()
        enriched_endpoints = []

        for endpoint in trial.get("endpoints", []):
            endpoint_name = endpoint.get("name", "").split(" ")[0]  # Get base name
            definition = ENDPOINT_DEFINITIONS.get(endpoint_name) or BIOMARKER_DEFINITIONS.get(endpoint_name)

            enriched_endpoint = endpoint.copy()
            if definition:
                enriched_endpoint["definition"] = {
                    "full_name": definition.get("full_name"),
                    "description": definition.get("description"),
                    "category": definition.get("category"),
                    "measurement_method": definition.get("measurement_methods") or definition.get("measurement"),
                    "clinical_significance": definition.get("clinical_significance") or definition.get("clinical_relevance"),
                    "comparator_benchmarks": definition.get("comparator_benchmarks"),
                    "interpretation": definition.get("interpretation"),
                }
            enriched_endpoints.append(enriched_endpoint)

        enriched_trial["endpoints"] = enriched_endpoints
        enriched_trials.append(enriched_trial)

    return {
        **base_data,
        "trials": enriched_trials,
        "endpoints_with_context": context_data,
        "definitions": {
            "endpoints": {k: v for k, v in ENDPOINT_DEFINITIONS.items()
                        if k in ["EASI", "SCORAD", "vIGA-AD", "PPNRS", "POEM", "DLQI", "FEV1", "ACQ-5", "FeNO"]},
            "biomarkers": {k: v for k, v in BIOMARKER_DEFINITIONS.items()
                         if k in ["STAT6", "TARC", "Eotaxin-3", "IgE", "IL-31"]}
        },
        "source": "Kymera Therapeutics Corporate Presentation, January 2026"
    }


def _generate_kt579_summary_with_context() -> dict:
    """Generate KT-579 summary with embedded contextual definitions."""
    base_data = KT579_DATA.copy()

    # Add IRF5 biomarker definition
    irf5_def = BIOMARKER_DEFINITIONS.get("IRF5", {})

    return {
        **base_data,
        "definitions": {
            "biomarkers": {
                "IRF5": irf5_def
            },
            "endpoints": {
                "anti-dsDNA": ENDPOINT_DEFINITIONS.get("anti-dsDNA", {}),
                "joint_swelling": ENDPOINT_DEFINITIONS.get("joint_swelling", {})
            }
        },
        "source": "Kymera Therapeutics Corporate Presentation, January 2026"
    }


def _generate_kt485_summary_with_context() -> dict:
    """Generate KT-485 summary with embedded contextual definitions."""
    base_data = KT485_DATA.copy()

    # Add IRAK4 biomarker definition
    irak4_def = BIOMARKER_DEFINITIONS.get("IRAK4", {})

    return {
        **base_data,
        "definitions": {
            "biomarkers": {
                "IRAK4": irak4_def
            }
        },
        "source": "Kymera Therapeutics Corporate Presentation, January 2026"
    }


# =============================================================================
# COMPANY & PIPELINE FUNCTIONS
# =============================================================================

def get_kymera_pipeline() -> dict:
    """Get full Kymera pipeline with all assets."""
    return {
        "company": KYMERA_COMPANY,
        "assets": [
            {
                "name": "KT-621",
                "target": "STAT6",
                "stage": KT621_DATA["clinical_development"]["current_stage"],
                "mechanism": "STAT6 degrader",
                "lead_indication": "Atopic Dermatitis",
                "key_data": "Phase 1b: 63% EASI reduction at Day 29"
            },
            {
                "name": "KT-579",
                "target": "IRF5",
                "stage": KT579_DATA["clinical_development"]["current_stage"],
                "mechanism": "IRF5 degrader",
                "lead_indication": "Systemic Lupus Erythematosus",
                "key_data": "Phase 1 starting Q1 2026; preclinical superiority in lupus models"
            },
            {
                "name": "KT-485",
                "target": "IRAK4",
                "stage": KT485_DATA["clinical_development"]["current_stage"],
                "mechanism": "IRAK4 degrader",
                "lead_indication": "Hidradenitis Suppurativa",
                "key_data": "Partnered with Sanofi; Phase 1 expected 2026",
                "partner": "Sanofi"
            }
        ],
        "partnerships": KYMERA_COMPANY.get("partnerships", []),
        "cash_runway": KYMERA_COMPANY.get("cash_runway")
    }


# =============================================================================
# TARGET LANDSCAPE FUNCTIONS
# =============================================================================

def get_target_landscape_with_context(target_name: str) -> dict:
    """Get target landscape with biomarker definitions."""
    target_upper = target_name.upper()

    targets = {
        "STAT6": STAT6_TARGET,
        "IRF5": IRF5_TARGET,
        "IRAK4": IRAK4_TARGET
    }

    target_data = targets.get(target_upper)
    if not target_data:
        return None

    # Add biomarker definition if available
    biomarker_def = BIOMARKER_DEFINITIONS.get(target_upper, {})

    return {
        **target_data,
        "biomarker_definition": biomarker_def,
        "measurement_methods": biomarker_def.get("measurement_methods", {}),
    }


# =============================================================================
# DEFINITIONS ACCESS FUNCTIONS
# =============================================================================

def get_endpoint_definitions() -> dict:
    """Return all endpoint definitions for API/UI."""
    return get_all_endpoint_definitions()


def get_biomarker_definitions() -> dict:
    """Return all biomarker definitions for API/UI."""
    return get_all_biomarker_definitions()


def get_definition_for_endpoint(endpoint_name: str) -> dict:
    """Get definition for a specific endpoint."""
    return ENDPOINT_DEFINITIONS.get(endpoint_name, {})


def get_definition_for_biomarker(biomarker_name: str) -> dict:
    """Get definition for a specific biomarker."""
    return BIOMARKER_DEFINITIONS.get(biomarker_name, {})


# =============================================================================
# HELPER FUNCTIONS FOR CONTEXTUAL DATA
# =============================================================================

def enrich_endpoint_result(endpoint_name: str, result: str,
                           timepoint: str = None, dose_group: str = None) -> dict:
    """
    Enrich an endpoint result with its full definition and context.

    Example:
        enrich_endpoint_result("EASI", "-63%", timepoint="Day 29")
    """
    return get_endpoint_with_context(endpoint_name, result, timepoint=timepoint)


def enrich_biomarker_result(biomarker_name: str, result: str,
                            method: str = None, tissue: str = None,
                            timepoint: str = None) -> dict:
    """
    Enrich a biomarker result with its full definition and context.

    Example:
        enrich_biomarker_result("STAT6", ">90% degradation",
                                method="flow_cytometry", tissue="blood")
    """
    return get_biomarker_with_context(biomarker_name, result, method, tissue, timepoint)


# =============================================================================
# SUPPORTED ASSETS
# =============================================================================

KYMERA_ASSETS = {"KT-621", "KT-579", "KT-485"}
SUPPORTED_TARGETS = {"STAT6", "IRF5", "IRAK4"}


def get_supported_assets() -> list:
    """Return list of supported Kymera assets."""
    return list(KYMERA_ASSETS)


def get_supported_targets() -> list:
    """Return list of supported targets."""
    return list(SUPPORTED_TARGETS)
