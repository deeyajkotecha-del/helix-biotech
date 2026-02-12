"""
Schema Validator for v2.1 Company and Asset JSON Files

Validates extraction output against the expected v2.1 schema before saving.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Required top-level fields for company.json
COMPANY_REQUIRED_FIELDS = [
    "_metadata",
    "company",
    "investment_thesis_summary",
    "investment_analysis",
    "pipeline_summary",
    "financials",
    "catalysts",
]

# Required top-level fields for asset JSON
ASSET_REQUIRED_FIELDS = [
    "_metadata",
    "asset",
    "target",
    "mechanism",
    "indications",
    "clinical_data",
]

# Optional but recommended asset sections
ASSET_OPTIONAL_FIELDS = [
    "regulatory",
    "partnership",
    "pharmacology",
    "differentiation_claims",
    "competitive_landscape",
    "ip_landscape",
    "market_opportunity",
    "catalysts",
    "investment_analysis",
    "_extraction_quality",
]


def validate_company_json(data: dict, ticker: str) -> dict:
    """
    Validate company.json against v2.1 schema.

    Returns:
        {
            "valid": bool,
            "errors": list[str],
            "warnings": list[str],
            "completeness_score": float (0.0-1.0)
        }
    """
    errors = []
    warnings = []
    fields_present = 0
    fields_total = len(COMPANY_REQUIRED_FIELDS)

    # Check for parse errors
    if data.get("_error"):
        errors.append(f"Extraction error: {data['_error']}")
        return {"valid": False, "errors": errors, "warnings": warnings, "completeness_score": 0.0}

    # Check required fields
    for field in COMPANY_REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")
        else:
            fields_present += 1

    # Validate _metadata
    metadata = data.get("_metadata", {})
    if metadata:
        if metadata.get("version") != "2.1":
            warnings.append(f"Version is '{metadata.get('version')}', expected '2.1'")
        if metadata.get("ticker") != ticker:
            warnings.append(f"Metadata ticker '{metadata.get('ticker')}' != expected '{ticker}'")

    # Validate company section
    company = data.get("company", {})
    if isinstance(company, dict):
        if not company.get("name"):
            warnings.append("company.name is empty")
        if not company.get("one_liner"):
            warnings.append("company.one_liner is empty")

    # Validate investment_analysis structure
    analysis = data.get("investment_analysis", {})
    if isinstance(analysis, dict):
        bull = analysis.get("bull_case", [])
        if isinstance(bull, list) and bull:
            if isinstance(bull[0], dict):
                warnings.append("Company bull_case contains objects — should be simple strings")

    # Validate pipeline_summary
    pipeline = data.get("pipeline_summary", {})
    if isinstance(pipeline, dict):
        programs = pipeline.get("programs", [])
        if not programs:
            warnings.append("pipeline_summary.programs is empty — no assets found")

    # Validate catalysts
    catalysts = data.get("catalysts", [])
    if not catalysts:
        warnings.append("catalysts list is empty")

    completeness = fields_present / fields_total if fields_total > 0 else 0.0
    valid = len(errors) == 0

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "completeness_score": round(completeness, 2),
    }


def validate_asset_json(data: dict, ticker: str) -> dict:
    """
    Validate asset JSON against v2.1 schema.

    Returns:
        {
            "valid": bool,
            "errors": list[str],
            "warnings": list[str],
            "completeness_score": float (0.0-1.0)
        }
    """
    errors = []
    warnings = []
    total_fields = len(ASSET_REQUIRED_FIELDS) + len(ASSET_OPTIONAL_FIELDS)
    fields_present = 0

    # Check for parse errors
    if data.get("_error"):
        errors.append(f"Extraction error: {data['_error']}")
        return {"valid": False, "errors": errors, "warnings": warnings, "completeness_score": 0.0}

    # Check required fields
    for field in ASSET_REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")
        else:
            fields_present += 1

    # Check optional fields
    for field in ASSET_OPTIONAL_FIELDS:
        if field in data and data[field] is not None:
            fields_present += 1
        else:
            warnings.append(f"Missing optional field: {field}")

    # Validate _metadata
    metadata = data.get("_metadata", {})
    if metadata:
        if metadata.get("version") != "2.1":
            warnings.append(f"Version is '{metadata.get('version')}', expected '2.1'")

    # Validate asset section
    asset = data.get("asset", {})
    if isinstance(asset, dict):
        if not asset.get("name"):
            errors.append("asset.name is empty")
        if not asset.get("one_liner"):
            warnings.append("asset.one_liner is empty")

    # Validate clinical_data
    clinical = data.get("clinical_data", {})
    if isinstance(clinical, dict):
        trials = clinical.get("trials", [])
        if not trials:
            warnings.append("clinical_data.trials is empty — no trials found")

    # Validate investment_analysis structure (asset-level uses objects)
    analysis = data.get("investment_analysis", {})
    if isinstance(analysis, dict):
        bull = analysis.get("bull_case", [])
        if isinstance(bull, list) and bull:
            if isinstance(bull[0], str):
                warnings.append("Asset bull_case contains strings — should be objects with thesis/evidence/confidence")

    completeness = fields_present / total_fields if total_fields > 0 else 0.0
    valid = len(errors) == 0

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "completeness_score": round(completeness, 2),
    }
