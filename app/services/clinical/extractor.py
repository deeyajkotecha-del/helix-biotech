"""
Clinical Data Extractor - Data-driven clinical trial analysis.

Reads clinical data from JSON files in data/companies/{ticker}/
Supports 145+ companies by adding JSON files, not editing code.

Directory structure:
    data/
    ├── companies/
    │   └── {TICKER}/
    │       ├── company.json      # Company info, partnerships, targets
    │       ├── {asset}.json      # Asset clinical data (e.g., kt621.json)
    │       └── ...
    └── definitions/
        ├── endpoints.json        # Endpoint definitions (EASI, FEV1, etc.)
        └── biomarkers.json       # Biomarker definitions (STAT6, IRF5, etc.)
"""

import json
from pathlib import Path
from typing import Optional
from functools import lru_cache


# =============================================================================
# PATH CONFIGURATION
# =============================================================================

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
COMPANIES_DIR = DATA_DIR / "companies"
DEFINITIONS_DIR = DATA_DIR / "definitions"
CONFIG_DIR = DATA_DIR / "config"


# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

@lru_cache(maxsize=128)
def load_json_file(file_path: str) -> dict:
    """Load and cache a JSON file."""
    path = Path(file_path)
    if not path.exists():
        return {}
    with open(path, 'r') as f:
        return json.load(f)


def clear_cache():
    """Clear the JSON file cache (useful after updates)."""
    load_json_file.cache_clear()


def load_company_data(ticker: str) -> Optional[dict]:
    """
    Load company data from data/companies/{ticker}/company.json

    Returns company info including:
    - name, ticker, headquarters, website
    - modalities, therapeutic_focus
    - partnerships
    - targets (STAT6, IRF5, etc.)
    """
    ticker = ticker.upper()
    company_file = COMPANIES_DIR / ticker / "company.json"

    if not company_file.exists():
        return None

    return load_json_file(str(company_file))


def load_asset_data(ticker: str, asset_name: str) -> Optional[dict]:
    """
    Load asset clinical data from data/companies/{ticker}/{asset}.json

    Asset name is normalized: KT-621 -> kt621.json

    Returns full asset data including:
    - asset info (name, target, mechanism)
    - clinical_development (stage, indications)
    - trials (with endpoints, safety)
    - investment_thesis, key_risks, upcoming_catalysts
    """
    ticker = ticker.upper()
    # Normalize asset name: KT-621 -> kt621, KT-579 -> kt579
    asset_normalized = asset_name.lower().replace("-", "")
    asset_file = COMPANIES_DIR / ticker / f"{asset_normalized}.json"

    if not asset_file.exists():
        return None

    return load_json_file(str(asset_file))


def load_endpoint_definitions() -> dict:
    """Load endpoint definitions from data/definitions/endpoints.json"""
    return load_json_file(str(DEFINITIONS_DIR / "endpoints.json"))


def load_biomarker_definitions() -> dict:
    """Load biomarker definitions from data/definitions/biomarkers.json"""
    return load_json_file(str(DEFINITIONS_DIR / "biomarkers.json"))


def load_taxonomy() -> dict:
    """Load taxonomy configuration from data/config/taxonomy.json"""
    return load_json_file(str(CONFIG_DIR / "taxonomy.json"))


def load_company_index() -> dict:
    """Load company index from data/companies/index.json"""
    return load_json_file(str(COMPANIES_DIR / "index.json"))


# =============================================================================
# TAXONOMY FUNCTIONS
# =============================================================================

def get_taxonomy() -> dict:
    """Return the full taxonomy structure."""
    return load_taxonomy()


def get_taxonomy_tier(tier_name: str) -> dict:
    """Get a specific taxonomy tier (development_stage, modality, etc.)"""
    taxonomy = load_taxonomy()
    return taxonomy.get(tier_name, {})


# =============================================================================
# COMPANY INDEX FUNCTIONS
# =============================================================================

def get_all_companies(
    development_stage: str = None,
    modality: str = None,
    therapeutic_area: str = None,
    thesis_type: str = None,
    priority: str = None,
    has_data: bool = None
) -> list[dict]:
    """
    Get all companies from index with optional filters.

    Filters:
    - development_stage: Filter by stage (e.g., "mid_clinical")
    - modality: Filter by modality (e.g., "small_molecule")
    - therapeutic_area: Filter by area (e.g., "oncology_precision")
    - thesis_type: Filter by thesis (e.g., "binary_event")
    - priority: Filter by priority (e.g., "high")
    - has_data: Filter by whether company has data files
    """
    index = load_company_index()
    companies = index.get("companies", [])

    # Apply filters
    if development_stage:
        companies = [c for c in companies if c.get("development_stage") == development_stage]
    if modality:
        companies = [c for c in companies if c.get("modality") == modality]
    if therapeutic_area:
        companies = [c for c in companies if c.get("therapeutic_area") == therapeutic_area]
    if thesis_type:
        companies = [c for c in companies if c.get("thesis_type") == thesis_type]
    if priority:
        companies = [c for c in companies if c.get("priority") == priority]
    if has_data is not None:
        companies = [c for c in companies if c.get("has_data") == has_data]

    return companies


def get_company_from_index(ticker: str) -> Optional[dict]:
    """Get a company's metadata from the index."""
    ticker = ticker.upper()
    index = load_company_index()
    for company in index.get("companies", []):
        if company.get("ticker", "").upper() == ticker:
            return company
    return None


def get_company_full(ticker: str) -> Optional[dict]:
    """
    Get full company data including:
    - Index metadata (classification, thesis type, etc.)
    - Company data (if exists)
    - Pipeline summary
    """
    ticker = ticker.upper()

    # Get index metadata
    index_data = get_company_from_index(ticker)

    # Get company data if it exists
    company_data = load_company_data(ticker)

    # Get asset list
    assets = list_company_assets(ticker)

    # Build full response
    result = {
        "ticker": ticker,
        "has_data": company_data is not None,
        "assets_count": len(assets),
        "assets": assets
    }

    # Merge index metadata
    if index_data:
        result["classification"] = {
            "development_stage": index_data.get("development_stage"),
            "modality": index_data.get("modality"),
            "modality_subtype": index_data.get("modality_subtype"),
            "therapeutic_area": index_data.get("therapeutic_area"),
            "therapeutic_subtype": index_data.get("therapeutic_subtype"),
            "thesis_type": index_data.get("thesis_type"),
            "priority": index_data.get("priority")
        }
        result["name"] = index_data.get("name")
        result["market_cap_mm"] = index_data.get("market_cap_mm")
        result["fund_ownership_pct"] = index_data.get("fund_ownership_pct")
        result["notes"] = index_data.get("notes")

    # Merge company data
    if company_data:
        result["company_details"] = {
            "name": company_data.get("name"),
            "headquarters": company_data.get("headquarters"),
            "website": company_data.get("website"),
            "description": company_data.get("description"),
            "cash_runway": company_data.get("cash_runway"),
        }
        result["investment_thesis"] = company_data.get("investment_thesis", [])
        result["key_risks"] = company_data.get("key_risks", [])
        result["partnerships"] = company_data.get("partnerships", [])
        result["targets"] = company_data.get("targets", {})

    return result if (index_data or company_data) else None


# =============================================================================
# DISCOVERY FUNCTIONS
# =============================================================================

def list_companies() -> list[str]:
    """List all company tickers with data directories (excludes TEMPLATE)."""
    if not COMPANIES_DIR.exists():
        return []
    return sorted([
        d.name for d in COMPANIES_DIR.iterdir()
        if d.is_dir() and d.name != "TEMPLATE" and not d.name.startswith(".")
    ])


def list_company_assets(ticker: str) -> list[str]:
    """List all assets for a company."""
    ticker = ticker.upper()
    company_dir = COMPANIES_DIR / ticker

    if not company_dir.exists():
        return []

    assets = []
    for f in company_dir.glob("*.json"):
        if f.name != "company.json":
            # Convert kt621.json -> KT-621
            name = f.stem.upper()
            if name.startswith("KT"):
                name = f"KT-{name[2:]}"
            assets.append(name)

    return sorted(assets)


# =============================================================================
# MAIN API FUNCTIONS
# =============================================================================

def generate_clinical_summary_for_asset(asset_name: str, ticker: str = "KYMR") -> dict:
    """
    Generate complete clinical data package for an asset with contextual definitions.

    Reads from:
    - data/companies/{ticker}/{asset}.json
    - data/definitions/endpoints.json
    - data/definitions/biomarkers.json
    """
    asset_data = load_asset_data(ticker, asset_name)
    if not asset_data:
        raise ValueError(f"Asset {asset_name} not found for {ticker}")

    endpoint_defs = load_endpoint_definitions()
    biomarker_defs = load_biomarker_definitions()

    # Enrich trials with endpoint definitions
    enriched_trials = []
    for trial in asset_data.get("trials", []):
        enriched_trial = trial.copy()
        enriched_endpoints = []

        for endpoint in trial.get("endpoints", []):
            endpoint_name = endpoint.get("name", "").split(" ")[0]
            definition = endpoint_defs.get(endpoint_name) or biomarker_defs.get(endpoint_name)

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

    # Get relevant definitions based on asset's target
    target = asset_data.get("asset", {}).get("target", "")
    relevant_biomarkers = {target: biomarker_defs.get(target, {})} if target in biomarker_defs else {}

    # Add commonly used biomarkers for the indication
    common_biomarkers = ["TARC", "Eotaxin-3", "IgE", "IL-31"]
    for bm in common_biomarkers:
        if bm in biomarker_defs:
            relevant_biomarkers[bm] = biomarker_defs[bm]

    return {
        **asset_data,
        "trials": enriched_trials,
        "definitions": {
            "endpoints": endpoint_defs,
            "biomarkers": relevant_biomarkers
        },
        "source": f"Data loaded from data/companies/{ticker.upper()}/"
    }


def get_company_pipeline(ticker: str) -> dict:
    """
    Get full pipeline for a company.

    Reads company.json and all asset JSON files.
    """
    company_data = load_company_data(ticker)
    if not company_data:
        raise ValueError(f"Company {ticker} not found")

    assets = []
    for asset_name in list_company_assets(ticker):
        asset_data = load_asset_data(ticker, asset_name)
        if asset_data:
            asset_info = asset_data.get("asset", {})
            clinical_dev = asset_data.get("clinical_development", {})
            assets.append({
                "name": asset_info.get("name", asset_name),
                "target": asset_info.get("target"),
                "stage": clinical_dev.get("current_stage"),
                "mechanism": asset_info.get("mechanism"),
                "lead_indication": clinical_dev.get("indications_in_development", [""])[0],
                "partner": asset_info.get("partner")
            })

    return {
        "company": {
            "name": company_data.get("name"),
            "ticker": company_data.get("ticker"),
            "headquarters": company_data.get("headquarters"),
            "description": company_data.get("description"),
            "cash_runway": company_data.get("cash_runway"),
        },
        "assets": assets,
        "partnerships": company_data.get("partnerships", []),
        "targets": company_data.get("targets", {})
    }


def get_target_landscape(target_name: str, ticker: str = None) -> Optional[dict]:
    """
    Get target landscape with biomarker definitions.

    If ticker is provided, loads from that company's company.json.
    Otherwise searches all companies for target data.
    """
    target_upper = target_name.upper()
    biomarker_defs = load_biomarker_definitions()

    # If ticker provided, load from that company
    if ticker:
        company_data = load_company_data(ticker)
        if company_data:
            targets = company_data.get("targets", {})
            if target_upper in targets:
                return {
                    **targets[target_upper],
                    "biomarker_definition": biomarker_defs.get(target_upper, {}),
                    "measurement_methods": biomarker_defs.get(target_upper, {}).get("measurement_methods", {})
                }

    # Search all companies
    for company_ticker in list_companies():
        company_data = load_company_data(company_ticker)
        if company_data:
            targets = company_data.get("targets", {})
            if target_upper in targets:
                return {
                    **targets[target_upper],
                    "biomarker_definition": biomarker_defs.get(target_upper, {}),
                    "measurement_methods": biomarker_defs.get(target_upper, {}).get("measurement_methods", {})
                }

    # Return just biomarker definition if no company target data found
    if target_upper in biomarker_defs:
        return {
            "name": target_upper,
            "biomarker_definition": biomarker_defs[target_upper],
            "measurement_methods": biomarker_defs[target_upper].get("measurement_methods", {})
        }

    return None


# =============================================================================
# DEFINITIONS ACCESS
# =============================================================================

def get_endpoint_definitions() -> dict:
    """Return all endpoint definitions."""
    return load_endpoint_definitions()


def get_biomarker_definitions() -> dict:
    """Return all biomarker definitions."""
    return load_biomarker_definitions()


def get_definition_for_endpoint(endpoint_name: str) -> dict:
    """Get definition for a specific endpoint."""
    return load_endpoint_definitions().get(endpoint_name, {})


def get_definition_for_biomarker(biomarker_name: str) -> dict:
    """Get definition for a specific biomarker."""
    return load_biomarker_definitions().get(biomarker_name, {})


# =============================================================================
# CONTEXT ENRICHMENT HELPERS
# =============================================================================

def enrich_endpoint_result(endpoint_name: str, result: str,
                           timepoint: str = None, dose_group: str = None) -> dict:
    """Enrich an endpoint result with its full definition."""
    definition = get_definition_for_endpoint(endpoint_name)

    return {
        "endpoint": endpoint_name,
        "full_name": definition.get("full_name", endpoint_name),
        "result": result,
        "timepoint": timepoint,
        "dose_group": dose_group,
        "category": definition.get("category"),
        "description": definition.get("description"),
        "scoring": definition.get("scoring"),
        "interpretation": definition.get("interpretation"),
        "comparator_benchmarks": definition.get("comparator_benchmarks"),
        "clinical_relevance": definition.get("clinical_relevance")
    }


def enrich_biomarker_result(biomarker_name: str, result: str,
                            method: str = None, tissue: str = None,
                            timepoint: str = None) -> dict:
    """Enrich a biomarker result with its full definition."""
    definition = get_definition_for_biomarker(biomarker_name)
    method_info = definition.get("measurement_methods", {}).get(method, {}) if method else {}

    return {
        "biomarker": biomarker_name,
        "full_name": definition.get("full_name", biomarker_name),
        "result": result,
        "timepoint": timepoint,
        "tissue": tissue,
        "type": definition.get("type"),
        "pathway": definition.get("pathway"),
        "biology": definition.get("biology"),
        "measurement_method": {
            "name": method,
            "description": method_info.get("description"),
            "sample": method_info.get("sample"),
            "readout": method_info.get("readout")
        } if method else None,
        "clinical_significance": definition.get("clinical_significance")
    }


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

# For existing code that imports these
KYMERA_ASSETS = set(list_company_assets("KYMR"))
SUPPORTED_TARGETS = {"STAT6", "IRF5", "IRAK4"}


def get_supported_assets(ticker: str = "KYMR") -> list:
    """Return list of supported assets for a company."""
    return list_company_assets(ticker)


def get_supported_targets() -> list:
    """Return list of supported targets."""
    return list(SUPPORTED_TARGETS)
