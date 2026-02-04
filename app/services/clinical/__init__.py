"""Clinical data extraction services - data-driven from JSON files."""
from app.services.clinical.extractor import (
    # Data loading
    load_company_data,
    load_asset_data,
    load_endpoint_definitions,
    load_biomarker_definitions,
    load_taxonomy,
    load_company_index,
    clear_cache,

    # Taxonomy
    get_taxonomy,
    get_taxonomy_tier,

    # Company index
    get_all_companies,
    get_company_from_index,
    get_company_full,

    # Discovery
    list_companies,
    list_company_assets,

    # Main API
    generate_clinical_summary_for_asset,
    get_company_pipeline,
    get_target_landscape,
    get_endpoint_definitions,
    get_biomarker_definitions,

    # Enrichment helpers
    enrich_endpoint_result,
    enrich_biomarker_result,

    # Backward compatibility
    KYMERA_ASSETS,
    SUPPORTED_TARGETS,
    get_supported_assets,
    get_supported_targets,
)

__all__ = [
    "load_company_data",
    "load_asset_data",
    "load_endpoint_definitions",
    "load_biomarker_definitions",
    "load_taxonomy",
    "load_company_index",
    "clear_cache",
    "get_taxonomy",
    "get_taxonomy_tier",
    "get_all_companies",
    "get_company_from_index",
    "get_company_full",
    "list_companies",
    "list_company_assets",
    "generate_clinical_summary_for_asset",
    "get_company_pipeline",
    "get_target_landscape",
    "get_endpoint_definitions",
    "get_biomarker_definitions",
    "enrich_endpoint_result",
    "enrich_biomarker_result",
    "KYMERA_ASSETS",
    "SUPPORTED_TARGETS",
    "get_supported_assets",
    "get_supported_targets",
]
