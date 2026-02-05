"""Clinical data API router - data-driven from JSON files."""
import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

# =============================================================================
# GLOBAL MEDICAL ACRONYM CAPITALIZATION
# =============================================================================

MEDICAL_ACRONYMS = [
    # Disease/Condition acronyms
    "HCM", "oHCM", "nHCM", "NSCLC", "SCLC", "CML", "AML", "ALL", "NHL", "CLL",
    "DLBCL", "MDS", "MPD", "MPN", "GIST", "RCC", "HCC", "CRC", "TNBC", "HR+",
    "HER2", "EGFR", "ALK", "ROS1", "BRAF", "KRAS", "NRAS", "MET", "RET", "NTRK",
    "IDH1", "IDH2", "FLT3", "BCR-ABL", "JAK2", "MPL", "CALR", "TP53", "BRCA",
    "MSI", "TMB", "PD-L1", "FGFR", "PIK3CA", "PTEN", "mCRPC", "CRPC", "AD", "UC",
    "IBS", "IBD", "RA", "SLE", "MS", "ALS", "PD", "HD", "DMD", "SMA", "CF",
    "COPD", "IPF", "PAH", "CHF", "AF", "VTE", "DVT", "PE", "CAD", "MI", "HF",
    "T2D", "T1D", "CKD", "ESRD", "NASH", "NAFLD", "HBV", "HCV", "HIV", "RSV",
    "CMV", "EBV", "HPV", "HSV", "COVID", "SARS", "MERS", "TB", "UTI", "MRSA",
    "MG", "gMG", "CIDP", "MMN", "ITP", "TTP", "HUS", "PNH", "IgAN",
    # Cardiac/HCM specific
    "LVEF", "LVOT", "NYHA", "NT-proBNP", "BNP", "LAVI", "LV", "LA", "RV", "RA",
    "EF", "SRT", "ICD", "CRT", "ECMO", "LVAD", "PCI", "CABG", "TAVR", "TAVI",
    # Clinical/Regulatory
    "FDA", "EMA", "PMDA", "NMPA", "NDA", "BLA", "sNDA", "sBLA", "MAA", "IND",
    "REMS", "BTD", "PRIME", "ODD", "PRV", "SPA", "PDUFA", "AdCom", "CRL",
    "ORR", "CR", "PR", "SD", "PD", "PFS", "OS", "DFS", "EFS", "TTP", "TTR",
    "DOR", "DoR", "DCR", "CBR", "MRD", "pCR", "ORR", "BOR",
    "AE", "SAE", "TEAE", "DLT", "MTD", "RP2D", "QoL", "PRO", "HRQoL",
    "MCID", "MMRM", "ITT", "mITT", "PP", "LOCF", "NRI",
    # Drug classes/mechanisms
    "CMI", "TKI", "mAb", "ADC", "CAR-T", "BiTE", "TCE", "PROTAC", "SMDC",
    "PPI", "SSRI", "SNRI", "NSAID", "ACE", "ARB", "DPP4", "SGLT2", "GLP-1",
    "PD-1", "PD-L1", "CTLA-4", "LAG-3", "TIM-3", "TIGIT", "CD19", "CD20",
    "CD22", "CD33", "CD38", "BCMA", "FcRn", "C5", "C2", "IL-6", "IL-17",
    "IL-23", "TNF", "JAK", "BTK", "SYK", "PI3K", "mTOR", "CDK", "PARP",
    "HDAC", "BET", "BCL-2", "MCL-1", "MDM2", "KRAS", "SHP2", "SOS1",
    # Biomarkers/Endpoints
    "KCCQ", "CSS", "OSS", "EASI", "IGA", "SCORAD", "DLQI", "SF-36", "EQ-5D",
    "MG-ADL", "QMG", "MGC", "MGII", "INCAT", "ONLS", "mRS", "EDSS",
    "HAQ", "DAS28", "ACR", "PASI", "BSA", "PGA", "VAS",
    "pVO2", "VO2", "6MWD", "6MWT", "FVC", "FEV1", "DLCO", "SpO2",
    "eGFR", "GFR", "CrCl", "BUN", "ALT", "AST", "ALP", "GGT", "INR", "PT",
    "PTT", "aPTT", "WBC", "RBC", "Hgb", "Hct", "PLT", "ANC", "ALC",
    "CRP", "ESR", "PCT", "LDH", "CPK", "CK", "PSA", "AFP", "CEA", "CA-125",
    "HbA1c", "A1c", "FPG", "OGTT", "TG", "TC", "LDL", "HDL", "VLDL",
    # Study/Statistics
    "RCT", "OLE", "EAP", "CUP", "IIT", "IST", "NIS", "RWE", "RWD",
    "HR", "OR", "RR", "ARR", "NNT", "CI", "SD", "SEM", "IQR", "p-value",
    "NS", "vs", "N/A", "TBD", "TBA", "EOT", "EOS", "SOC", "BSC",
    # Other
    "US", "EU", "UK", "JP", "CN", "ROW", "WW", "IP", "NCE", "API", "DP",
    "PK", "PD", "ADME", "DMPK", "IV", "SC", "IM", "PO", "QD", "BID", "TID",
    "QW", "Q2W", "Q4W", "PRN", "BMI", "BSA", "AUC", "Cmax", "Cmin", "Tmax",
]

def capitalize_medical_terms(text: str) -> str:
    """Capitalize medical acronyms in text while preserving case of non-acronyms."""
    if not text:
        return text

    # Sort by length (longest first) to avoid partial replacements
    sorted_acronyms = sorted(MEDICAL_ACRONYMS, key=len, reverse=True)

    for acronym in sorted_acronyms:
        # Create case-insensitive pattern with word boundaries
        pattern = r'\b' + re.escape(acronym.lower()) + r'\b'
        text = re.sub(pattern, acronym, text, flags=re.IGNORECASE)

    return text


def generate_citation_badge(source: dict, ticker: str) -> str:
    """
    Generate a citation badge HTML from a source object.

    Source format: {"id": "kymr_corporate_2026", "slide": 14, "verified": false}
    Output: <a href="..." class="citation-badge" ...>[Corp '26 S14]</a>
    """
    if not source or not isinstance(source, dict):
        return ""

    source_id = source.get("id", "")
    slide = source.get("slide", "")
    verified = source.get("verified", False)

    if not source_id or not slide:
        return ""

    # Generate short label from source_id
    # kymr_corporate_2026 → "Corp '26"
    # kymr_jpm_2026 → "JPM '26"
    # kymr_broaden_poster_aad_2026 → "AAD '26"
    event_keywords = {
        "corporate": "Corp",
        "jpm": "JPM",
        "aad": "AAD",
        "asco": "ASCO",
        "ash": "ASH",
        "esmo": "ESMO",
        "easl": "EASL",
        "poster": "Poster",
        "presentation": "Pres",
    }

    source_lower = source_id.lower()
    event_label = "Src"  # default
    for keyword, label in event_keywords.items():
        if keyword in source_lower:
            event_label = label
            break

    # Extract year (4 digits)
    import re
    year_match = re.search(r'(\d{4})', source_id)
    year_short = year_match.group(1)[-2:] if year_match else "??"

    # Build label: "Corp '26 S14"
    label = f"{event_label} '{year_short} S{slide}"

    # Build URL
    url = f"/api/clinical/companies/{ticker}/sources/{source_id}/slide/{slide}"

    # Build title
    title = f"{event_label} {year_match.group(1) if year_match else ''}, Slide {slide}"

    # Generate badge HTML
    verified_mark = '<span class="verified-check">✓</span>' if verified else ""

    return f'''<a href="{url}" class="citation-badge" target="_blank" title="{title}">[{label}]</a>{verified_mark}'''


def get_stage_priority(stage: str) -> int:
    """Get numeric priority for development stage (lower = more advanced)."""
    if not stage:
        return 99
    stage_lower = stage.lower().strip()
    stage_order = {
        'approved': 1,
        'launched': 1,
        'marketed': 1,
        'bla filed': 2,
        'nda filed': 2,
        'maa filed': 2,
        'submitted': 2,
        'under review': 2,
        'phase 3': 3,
        'pivotal': 3,
        'registrational': 3,
        'phase 2/3': 3,
        'phase 2b': 4,
        'phase 2': 4,
        'phase 1/2': 5,
        'phase 1b': 5,
        'phase 1': 6,
        'ind filed': 7,
        'ind-enabling': 7,
        'ind enabling': 7,
        'preclinical': 8,
        'pre-clinical': 8,
        'discovery': 9,
    }
    # Check for partial matches
    for key, priority in stage_order.items():
        if key in stage_lower:
            return priority
    return 99

def get_drug_class(modality: str) -> str:
    """Extract drug class from modality string."""
    modality_lower = modality.lower() if modality else ""
    if "degrader" in modality_lower or "protac" in modality_lower:
        return "Degrader"
    elif "modulator" in modality_lower:
        return "Modulator"
    elif "inhibitor" in modality_lower:
        return "Inhibitor"
    elif "agonist" in modality_lower:
        return "Agonist"
    elif "antagonist" in modality_lower:
        return "Antagonist"
    elif "antibody" in modality_lower or "mab" in modality_lower:
        return "Antibody"
    elif "adc" in modality_lower:
        return "ADC"
    elif "car-t" in modality_lower or "car t" in modality_lower:
        return "CAR-T"
    elif "small molecule" in modality_lower:
        return "Small Molecule"
    else:
        return ""

from app.services.clinical.extractor import (
    generate_clinical_summary_for_asset,
    get_company_pipeline,
    get_target_landscape,
    get_endpoint_definitions,
    get_biomarker_definitions,
    list_companies,
    list_company_assets,
    clear_cache,
    get_taxonomy,
    get_all_companies,
    get_company_full,
    get_all_targets,
    get_target_full,
    list_all_targets,
)

router = APIRouter()


# =============================================================================
# TAXONOMY ENDPOINT
# =============================================================================

@router.get("/taxonomy")
async def get_taxonomy_endpoint():
    """
    Get the full taxonomy structure for company classification.

    Returns tiers for:
    - development_stage: Large Cap Diversified, Commercial Stage, Late Clinical, etc.
    - modality: Small Molecule, Antibody/Biologics, RNA Therapeutics, etc.
    - therapeutic_area: Oncology-Precision, Rare-Genetic, I&I/Autoimmune, etc.
    - thesis_type: Platform/Royalty, Binary Event, Commercial Compounder, etc.
    """
    return get_taxonomy()


# =============================================================================
# COMPANY INDEX ENDPOINTS
# =============================================================================

@router.get("/companies")
async def list_all_companies(
    development_stage: Optional[str] = Query(None, description="Filter by stage (e.g., mid_clinical)"),
    modality: Optional[str] = Query(None, description="Filter by modality (e.g., small_molecule)"),
    therapeutic_area: Optional[str] = Query(None, description="Filter by area (e.g., oncology_precision)"),
    thesis_type: Optional[str] = Query(None, description="Filter by thesis (e.g., binary_event)"),
    priority: Optional[str] = Query(None, description="Filter by priority (high, medium, low)"),
    has_data: Optional[bool] = Query(None, description="Filter by whether company has data files")
):
    """
    List all companies with optional filters.

    Examples:
    - GET /api/clinical/companies - All companies
    - GET /api/clinical/companies?priority=high - High priority only
    - GET /api/clinical/companies?modality=small_molecule&therapeutic_area=oncology_precision
    - GET /api/clinical/companies?has_data=true - Only companies with data
    """
    companies = get_all_companies(
        development_stage=development_stage,
        modality=modality,
        therapeutic_area=therapeutic_area,
        thesis_type=thesis_type,
        priority=priority,
        has_data=has_data
    )

    return {
        "companies": companies,
        "count": len(companies),
        "filters_applied": {
            k: v for k, v in {
                "development_stage": development_stage,
                "modality": modality,
                "therapeutic_area": therapeutic_area,
                "thesis_type": thesis_type,
                "priority": priority,
                "has_data": has_data
            }.items() if v is not None
        }
    }


@router.get("/companies/html", response_class=HTMLResponse)
async def get_companies_list_html(
    development_stage: Optional[str] = Query(None),
    modality: Optional[str] = Query(None),
    therapeutic_area: Optional[str] = Query(None),
    thesis_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    has_data: Optional[bool] = Query(None)
):
    """
    Companies list page with filters.
    Shows all companies from index.json with clickable navigation.
    """
    companies = get_all_companies(
        development_stage=development_stage,
        modality=modality,
        therapeutic_area=therapeutic_area,
        thesis_type=thesis_type,
        priority=priority,
        has_data=has_data
    )
    taxonomy = get_taxonomy()

    html = _generate_companies_list_html(companies, taxonomy, {
        "development_stage": development_stage,
        "modality": modality,
        "therapeutic_area": therapeutic_area,
        "thesis_type": thesis_type,
        "priority": priority,
        "has_data": has_data
    })
    return HTMLResponse(content=html)


@router.get("/companies/{ticker}")
async def get_company(ticker: str):
    """
    Get full company data including classification, thesis, and pipeline.

    Example: GET /api/clinical/companies/KYMR

    Returns:
    - Classification metadata (stage, modality, area, thesis type)
    - Company details (if data exists)
    - Investment thesis and risks
    - Asset list
    """
    result = get_company_full(ticker)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Company {ticker} not found in index or data files"
        )
    return result


@router.get("/companies/{ticker}/assets")
async def get_company_assets(ticker: str):
    """
    List all assets for a company.

    Example: GET /api/clinical/companies/KYMR/assets
    """
    assets = list_company_assets(ticker)
    if not assets:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found or has no assets")

    return {
        "ticker": ticker.upper(),
        "assets": assets,
        "count": len(assets)
    }


# =============================================================================
# SOURCE ENDPOINTS
# =============================================================================

@router.get("/companies/{ticker}/sources/")
async def get_company_sources(ticker: str):
    """
    List all source documents for a company.

    Example: GET /api/clinical/companies/KYMR/sources/
    Returns the index.json from data/companies/{ticker}/sources/
    """
    from pathlib import Path
    import json

    ticker = ticker.upper()
    sources_index = Path(f"data/companies/{ticker}/sources/index.json")

    if not sources_index.exists():
        return {"sources": []}

    with open(sources_index) as f:
        return json.load(f)


@router.get("/companies/{ticker}/sources/{source_id}/slide/{slide_num}")
async def get_source_slide(ticker: str, source_id: str, slide_num: int):
    """
    Serve a slide image from a source document.

    Example: GET /api/clinical/companies/KYMR/sources/kymr_corporate_2026/slide/14
    Returns the PNG image for slide 14.
    """
    from pathlib import Path
    from fastapi.responses import FileResponse

    ticker = ticker.upper()
    slide_path = Path(f"data/companies/{ticker}/sources/{source_id}/slide_{slide_num:02d}.png")

    if not slide_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Slide {slide_num} not found in source {source_id}"
        )

    return FileResponse(slide_path, media_type="image/png")


# =============================================================================
# ASSET ENDPOINTS
# =============================================================================

@router.get("/assets/{ticker}/{asset_name}/clinical")
async def get_asset_clinical_data(ticker: str, asset_name: str):
    """
    Get full clinical data package for an asset with contextual definitions.

    Example: GET /api/clinical/assets/KYMR/KT-621/clinical

    Data is loaded from data/companies/{ticker}/{asset}.json
    """
    try:
        return generate_clinical_summary_for_asset(asset_name, ticker)
    except ValueError as e:
        available = list_company_assets(ticker)
        raise HTTPException(
            status_code=404,
            detail=f"{str(e)}. Available assets: {', '.join(available) if available else 'none'}"
        )


@router.get("/assets/{ticker}/{asset_name}/clinical/html", response_class=HTMLResponse)
async def get_asset_clinical_html(ticker: str, asset_name: str):
    """Get clinical data as formatted HTML with collapsible sections and tooltips."""
    try:
        data = generate_clinical_summary_for_asset(asset_name, ticker)
        html = _generate_clinical_html(data)
        return HTMLResponse(content=html)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# COMPANY/PIPELINE ENDPOINTS
# =============================================================================

@router.get("/companies/{ticker}/pipeline")
async def get_pipeline(ticker: str):
    """
    Get full pipeline for a company.

    Example: GET /api/clinical/companies/KYMR/pipeline

    Reads from data/companies/{ticker}/company.json and all asset files.
    """
    try:
        return get_company_pipeline(ticker)
    except ValueError as e:
        available = list_companies()
        raise HTTPException(
            status_code=404,
            detail=f"{str(e)}. Available companies: {', '.join(available) if available else 'none'}"
        )


# =============================================================================
# TARGET HTML PAGES
# =============================================================================

@router.get("/targets/html", response_class=HTMLResponse)
async def get_targets_list_html():
    """
    Targets list page showing all targets with linked assets.
    """
    targets = get_all_targets()
    html = _generate_targets_list_html(targets)
    return HTMLResponse(content=html)


@router.get("/targets/{target_name}/html", response_class=HTMLResponse)
async def get_target_page_html(target_name: str):
    """
    Individual target page with:
    - Target biology and validation
    - Competitive landscape (all assets targeting this target)
    - Links to company/asset pages
    """
    target = get_target_full(target_name)
    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"Target {target_name} not found. Available targets: {', '.join(list_all_targets())}"
        )

    html = _generate_target_page_html(target)
    return HTMLResponse(content=html)


# =============================================================================
# TARGET LANDSCAPE ENDPOINTS
# =============================================================================

@router.get("/targets/{target_name}/landscape")
async def get_target_landscape_endpoint(target_name: str):
    """
    Get target landscape with biomarker definitions and measurement methods.

    Example: GET /api/clinical/targets/STAT6/landscape

    Searches all companies for target data.
    """
    result = get_target_landscape(target_name)
    if result:
        return result

    raise HTTPException(
        status_code=404,
        detail=f"Target {target_name} not found in any company data or definitions"
    )


@router.get("/targets/{target_name}/clinical-landscape")
async def get_target_clinical_landscape_legacy(target_name: str):
    """Legacy endpoint - redirects to /targets/{target}/landscape."""
    return await get_target_landscape_endpoint(target_name)


# =============================================================================
# DEFINITION ENDPOINTS
# =============================================================================

@router.get("/definitions/endpoints")
async def get_all_endpoint_definitions():
    """
    Get all endpoint definitions for UI tooltips.

    Loads from data/definitions/endpoints.json
    """
    return get_endpoint_definitions()


@router.get("/definitions/biomarkers")
async def get_all_biomarker_definitions():
    """
    Get all biomarker definitions for UI tooltips.

    Loads from data/definitions/biomarkers.json
    """
    return get_biomarker_definitions()


@router.get("/definitions/endpoints/{endpoint_name}")
async def get_endpoint_definition(endpoint_name: str):
    """Get definition for a specific endpoint."""
    definitions = get_endpoint_definitions()
    if endpoint_name in definitions:
        return definitions[endpoint_name]
    raise HTTPException(status_code=404, detail=f"Endpoint {endpoint_name} not found")


@router.get("/definitions/biomarkers/{biomarker_name}")
async def get_biomarker_definition(biomarker_name: str):
    """Get definition for a specific biomarker."""
    definitions = get_biomarker_definitions()
    if biomarker_name in definitions:
        return definitions[biomarker_name]
    raise HTTPException(status_code=404, detail=f"Biomarker {biomarker_name} not found")


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.post("/cache/clear")
async def clear_data_cache():
    """Clear the JSON file cache (useful after adding new data files)."""
    clear_cache()
    return {"status": "ok", "message": "Cache cleared"}


# =============================================================================
# HTML PAGES
# =============================================================================

@router.get("/companies/{ticker}/html", response_class=HTMLResponse)
async def get_company_html(ticker: str):
    """
    Company overview page with:
    - Snapshot (market cap, cash, stage)
    - Investment thesis (bull/bear)
    - Pipeline summary table
    - Partnerships
    """
    result = get_company_full(ticker)
    if not result:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    html = _generate_company_overview_html(result)
    return HTMLResponse(content=html)


@router.get("/companies/{ticker}/assets/{asset_name}/html", response_class=HTMLResponse)
async def get_asset_page_html(ticker: str, asset_name: str):
    """
    Individual asset page with:
    - Sticky breadcrumb header
    - Sidebar navigation
    - Full asset details in sections
    """
    from app.services.clinical.extractor import load_asset_data

    result = get_company_full(ticker)
    if not result:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    # Find the asset
    assets = result.get("assets", [])
    asset_names = [a.get("name", "") for a in assets]

    # Normalize asset name for matching
    asset_name_normalized = asset_name.lower().replace("-", "").replace("_", "")
    matched_asset = None
    matched_index = -1

    for i, a in enumerate(assets):
        a_name = a.get("name", "")
        a_normalized = a_name.lower().replace("-", "").replace("_", "")
        if a_normalized == asset_name_normalized or asset_name_normalized in a_normalized:
            matched_asset = a
            matched_index = i
            break

    if not matched_asset:
        raise HTTPException(
            status_code=404,
            detail=f"Asset {asset_name} not found. Available: {', '.join(asset_names)}"
        )

    # Get prev/next assets
    prev_asset = assets[matched_index - 1] if matched_index > 0 else None
    next_asset = assets[matched_index + 1] if matched_index < len(assets) - 1 else None

    html = _generate_asset_page_html(result, matched_asset, prev_asset, next_asset)
    return HTMLResponse(content=html)


# =============================================================================
# HTML GENERATION
# =============================================================================

def _generate_clinical_html(data: dict) -> str:
    """Generate HTML page with collapsible sections, tooltips, and method info."""
    asset = data.get("asset", {})
    trials = data.get("trials", [])
    definitions = data.get("definitions", {})

    # Build trials HTML with collapsible sections
    trials_html = ""
    for trial in trials:
        endpoints_rows = ""
        for e in trial.get("endpoints", []):
            definition = e.get("definition", {})
            tooltip_content = _build_tooltip_content(e.get("name", ""), definition)
            method_info = _get_method_info(definition)
            benchmark_info = _get_benchmark_info(definition)

            endpoints_rows += f"""
            <tr>
                <td>
                    <span class="endpoint-name" data-tooltip="{tooltip_content}">{e.get('name', '')}</span>
                    {f'<span class="method-badge">{method_info}</span>' if method_info else ''}
                </td>
                <td>{e.get('category', '')}</td>
                <td>{e.get('dose_group', e.get('timepoint', ''))}</td>
                <td class="result-cell">
                    <strong>{e.get('result', '')}</strong>
                    {f'<div class="benchmark">{benchmark_info}</div>' if benchmark_info else ''}
                </td>
            </tr>
            """

        safety_info = trial.get("safety", "")
        safety_html = f'<div class="safety-note"><strong>Safety:</strong> {safety_info}</div>' if safety_info else ""

        vs_dupilumab = trial.get("vs_dupilumab", "")
        comparison_html = f'<div class="comparison-note"><strong>vs Dupilumab:</strong> {vs_dupilumab}</div>' if vs_dupilumab else ""

        trials_html += f"""
        <div class="card">
            <button class="collapsible">
                <span class="trial-name">{trial.get('name', 'Trial')}</span>
                <span class="trial-phase badge">{trial.get('phase', '')}</span>
                <span class="trial-status badge {'badge-active' if trial.get('status') == 'Ongoing' else ''}">{trial.get('status', '')}</span>
            </button>
            <div class="content">
                <div class="trial-meta">
                    <p><strong>Design:</strong> {trial.get('design', 'N/A')}</p>
                    <p><strong>Population:</strong> {trial.get('population', trial.get('indication', 'N/A'))}</p>
                    <p><strong>Primary Endpoint:</strong> {trial.get('primary_endpoint', 'N/A')}</p>
                </div>
                {safety_html}
                {comparison_html}
                <table class="endpoints-table">
                    <thead><tr><th>Endpoint</th><th>Category</th><th>Arm/Timepoint</th><th>Result</th></tr></thead>
                    <tbody>{endpoints_rows}</tbody>
                </table>
            </div>
        </div>
        """

    # Build thesis and risks
    thesis_html = "".join(f'<div class="thesis-item">{p}</div>' for p in data.get("investment_thesis", []))
    risks_html = "".join(f'<div class="risk-item">{r}</div>' for r in data.get("key_risks", []))

    # Build catalysts
    catalysts = data.get("upcoming_catalysts", [])
    catalysts_html = ""
    for c in catalysts:
        if isinstance(c, dict):
            catalysts_html += f'<div class="catalyst-item"><strong>{c.get("timing", "")}</strong>: {c.get("event", "")}</div>'
        else:
            catalysts_html += f'<div class="catalyst-item">{c}</div>'

    # Build biomarker definitions section
    biomarker_defs = definitions.get("biomarkers", {})
    biomarkers_section = ""
    if biomarker_defs:
        biomarker_cards = ""
        for name, defn in biomarker_defs.items():
            if not defn:
                continue
            methods = defn.get("measurement_methods", {})
            methods_html = ""
            for method_name, method_info in methods.items():
                if isinstance(method_info, dict):
                    methods_html += f"""
                    <div class="method-item">
                        <strong>{method_name.replace('_', ' ').title()}</strong>: {method_info.get('description', '')}
                        <span class="method-detail">Sample: {method_info.get('sample', 'N/A')}</span>
                    </div>
                    """

            biomarker_cards += f"""
            <div class="definition-card">
                <h4>{name} <span class="type-badge">{defn.get('type', '')}</span></h4>
                <p class="full-name">{defn.get('full_name', '')}</p>
                <p class="pathway"><strong>Pathway:</strong> {defn.get('pathway', '')}</p>
                <p class="significance"><strong>Clinical Significance:</strong> {defn.get('clinical_significance', '')}</p>
                {f'<div class="methods"><strong>Measurement Methods:</strong>{methods_html}</div>' if methods_html else ''}
            </div>
            """

        biomarkers_section = f"""
        <div class="card">
            <button class="collapsible">Biomarker Definitions</button>
            <div class="content">
                <div class="definitions-grid">{biomarker_cards}</div>
            </div>
        </div>
        """

    # Clinical development info
    clinical_dev = data.get("clinical_development", {})
    indications = clinical_dev.get("indications_in_development", [])
    indications_html = "".join(f'<span class="indication-badge">{ind}</span>' for ind in indications[:6])

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{asset.get('name', 'Asset')} Clinical Data | Satya Bio</title>
    <style>
        :root {{
            --primary: #1a365d;
            --primary-light: #2c5282;
            --accent: #3182ce;
            --success: #38a169;
            --warning: #d69e2e;
            --danger: #e53e3e;
            --bg: #f7fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text: #2d3748;
            --text-muted: #718096;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            padding: 20px;
            line-height: 1.6;
            color: var(--text);
            margin: 0;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}

        .header {{
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 2rem; }}
        .header-meta {{ opacity: 0.9; margin-bottom: 12px; }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            background: rgba(255,255,255,0.2);
            margin-right: 8px;
            margin-bottom: 4px;
        }}
        .badge-active {{ background: var(--success); }}

        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 16px;
            overflow: hidden;
        }}
        .collapsible {{
            width: 100%;
            background: var(--card-bg);
            border: none;
            padding: 16px 20px;
            text-align: left;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: background 0.2s;
        }}
        .collapsible:hover {{ background: var(--bg); }}
        .collapsible::after {{
            content: '+';
            margin-left: auto;
            font-size: 1.2rem;
            color: var(--text-muted);
        }}
        .collapsible.active::after {{ content: '-'; }}
        .content {{
            padding: 0 20px 20px;
            display: none;
            border-top: 1px solid var(--border);
        }}
        .content.show {{ display: block; }}

        .trial-meta {{ background: var(--bg); padding: 12px; border-radius: 8px; margin-bottom: 12px; }}
        .trial-meta p {{ margin: 4px 0; }}
        .safety-note {{ background: #f0fff4; border-left: 3px solid var(--success); padding: 10px 12px; margin: 12px 0; border-radius: 0 8px 8px 0; }}
        .comparison-note {{ background: #ebf8ff; border-left: 3px solid var(--accent); padding: 10px 12px; margin: 12px 0; border-radius: 0 8px 8px 0; }}

        .endpoints-table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        .endpoints-table th, .endpoints-table td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
        .endpoints-table th {{ background: var(--bg); font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); }}
        .endpoints-table tr:hover {{ background: #fafafa; }}
        .result-cell strong {{ color: var(--primary); }}
        .benchmark {{ font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }}

        .endpoint-name {{ border-bottom: 1px dotted var(--text-muted); cursor: help; }}
        .method-badge {{
            display: inline-block;
            font-size: 0.7rem;
            background: var(--bg);
            color: var(--text-muted);
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 6px;
        }}

        .thesis-item {{ background: #ebf8ff; border-left: 4px solid var(--accent); padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; }}
        .risk-item {{ background: #fff5f5; border-left: 4px solid var(--danger); padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; }}
        .catalyst-item {{ background: #fffff0; border-left: 4px solid var(--warning); padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; }}

        .definitions-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
        .definition-card {{ background: var(--bg); padding: 16px; border-radius: 8px; border: 1px solid var(--border); }}
        .definition-card h4 {{ margin: 0 0 8px 0; color: var(--primary); }}
        .definition-card .full-name {{ font-style: italic; color: var(--text-muted); margin: 0 0 8px 0; }}
        .definition-card .pathway {{ font-size: 0.9rem; margin: 4px 0; }}
        .definition-card .significance {{ font-size: 0.9rem; margin: 8px 0; }}
        .type-badge {{ font-size: 0.75rem; background: var(--accent); color: white; padding: 2px 8px; border-radius: 4px; }}
        .methods {{ margin-top: 12px; }}
        .method-item {{ background: white; padding: 8px; margin: 4px 0; border-radius: 4px; font-size: 0.9rem; }}
        .method-detail {{ display: block; color: var(--text-muted); font-size: 0.8rem; }}

        .indication-badge {{
            display: inline-block;
            background: var(--bg);
            border: 1px solid var(--border);
            padding: 4px 10px;
            border-radius: 16px;
            font-size: 0.8rem;
            margin: 4px 4px 4px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{asset.get('name', 'Unknown')}</h1>
            <div class="header-meta">
                {asset.get('company', '')} ({asset.get('ticker', '')})
                {f" | Partner: {asset.get('partner', '')}" if asset.get('partner') else ""}
            </div>
            <span class="badge">{clinical_dev.get('current_stage', '')}</span>
            <span class="badge">Target: {asset.get('target', '')}</span>
            <span class="badge">{asset.get('modality', '')}</span>
            <div style="margin-top: 12px;">
                <strong>Indications:</strong><br>
                {indications_html}
            </div>
        </div>

        <div class="card">
            <button class="collapsible active">Investment Thesis</button>
            <div class="content show">{thesis_html}</div>
        </div>

        <div class="card">
            <button class="collapsible">Key Risks</button>
            <div class="content">{risks_html}</div>
        </div>

        <div class="card">
            <button class="collapsible">Upcoming Catalysts</button>
            <div class="content">{catalysts_html}</div>
        </div>

        <h2 style="margin-top: 30px; color: var(--primary);">Clinical Trials</h2>
        {trials_html}

        <h2 style="margin-top: 30px; color: var(--primary);">Reference Definitions</h2>
        {biomarkers_section}
    </div>

    <script>
        document.querySelectorAll('.collapsible').forEach(btn => {{
            btn.addEventListener('click', function() {{
                this.classList.toggle('active');
                const content = this.nextElementSibling;
                content.classList.toggle('show');
            }});
        }});
    </script>
</body>
</html>
"""


def _build_tooltip_content(endpoint_name: str, definition: dict) -> str:
    """Build tooltip content for an endpoint."""
    if not definition:
        return ""
    parts = []
    if definition.get("full_name"):
        parts.append(definition["full_name"])
    if definition.get("description"):
        desc = definition["description"]
        parts.append(desc[:100] + "..." if len(desc) > 100 else desc)
    return " | ".join(parts).replace('"', "'")


def _get_method_info(definition: dict) -> str:
    """Extract measurement method info from definition."""
    method = definition.get("measurement_method")
    if isinstance(method, dict):
        for name, info in method.items():
            if isinstance(info, dict) and info.get("description"):
                return info.get("sample", name.replace("_", " ").title())
    return ""


def _get_benchmark_info(definition: dict) -> str:
    """Extract comparator benchmark info from definition."""
    benchmarks = definition.get("comparator_benchmarks", {})
    if benchmarks:
        parts = [f"{drug}: {val}" for drug, val in benchmarks.items()]
        return " | ".join(parts[:2])
    return ""


def _generate_companies_list_html(companies: list, taxonomy: dict, filters: dict) -> str:
    """Generate companies list page HTML with filters."""
    active_filters = {k: v for k, v in filters.items() if v is not None}

    # Build filter options
    stages = taxonomy.get("development_stage", {})
    modalities = taxonomy.get("modality", {})
    areas = taxonomy.get("therapeutic_area", {})
    thesis_types = taxonomy.get("thesis_type", {})

    def make_filter_options(options: dict, param: str, current: str) -> str:
        html = f'<option value="">All</option>'
        for key, label in options.items():
            selected = 'selected' if current == key else ''
            html += f'<option value="{key}" {selected}>{label}</option>'
        return html

    stage_options = make_filter_options(stages, "development_stage", filters.get("development_stage", ""))
    modality_options = make_filter_options(modalities, "modality", filters.get("modality", ""))
    area_options = make_filter_options(areas, "therapeutic_area", filters.get("therapeutic_area", ""))
    thesis_options = make_filter_options(thesis_types, "thesis_type", filters.get("thesis_type", ""))

    # Build company cards
    company_cards = ""
    for c in companies:
        ticker = c.get("ticker", "")
        name = c.get("name", ticker)
        has_data = c.get("has_data", False)
        priority = c.get("priority", "medium")
        notes = c.get("notes", "")

        data_badge = '<span class="badge has-data">Has Data</span>' if has_data else '<span class="badge no-data">No Data</span>'
        priority_class = f"priority-{priority}"

        company_cards += f'''
        <a href="/api/clinical/companies/{ticker}/html" class="company-card {priority_class}">
            <div class="company-header">
                <div class="ticker">{ticker}</div>
                <div class="badges">
                    <span class="badge stage">{c.get('development_stage', '').replace('_', ' ').title()}</span>
                    {data_badge}
                </div>
            </div>
            <div class="company-name">{name}</div>
            <div class="company-meta">
                <span class="modality">{c.get('modality', '').replace('_', ' ').title()}</span>
                <span class="separator">·</span>
                <span class="area">{c.get('therapeutic_area', '').replace('_', ' ').title()}</span>
            </div>
            <div class="company-notes">{notes}</div>
            <div class="company-footer">
                <span class="market-cap">${c.get('market_cap_mm', 'N/A')}M</span>
                <span class="priority badge {priority}">{priority.title()}</span>
            </div>
        </a>'''

    # Stats
    total = len(companies)
    with_data = sum(1 for c in companies if c.get("has_data"))
    high_priority = sum(1 for c in companies if c.get("priority") == "high")

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Companies | Clinical Data Platform</title>
    <style>
        :root {{
            --primary: #1a365d;
            --primary-light: #2c5282;
            --accent: #3182ce;
            --bull: #38a169;
            --bear: #e53e3e;
            --warning: #d69e2e;
            --bg: #f7fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text: #2d3748;
            --text-muted: #718096;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}

        .header {{
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            color: white;
            padding: 32px 24px;
        }}
        .header-content {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 8px;
        }}
        .header p {{
            opacity: 0.9;
        }}

        .stats {{
            display: flex;
            gap: 24px;
            margin-top: 20px;
        }}
        .stat-item {{
            background: rgba(255,255,255,0.15);
            padding: 12px 20px;
            border-radius: 8px;
        }}
        .stat-item .value {{
            font-size: 1.5rem;
            font-weight: 600;
        }}
        .stat-item .label {{
            font-size: 0.8rem;
            opacity: 0.8;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }}

        .filters {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 24px;
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            align-items: flex-end;
        }}
        .filter-group {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .filter-group label {{
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
        .filter-group select {{
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 0.9rem;
            min-width: 160px;
            background: white;
        }}
        .filter-group select:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        .filter-btn {{
            padding: 8px 20px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
        }}
        .filter-btn:hover {{
            background: var(--primary-light);
        }}
        .clear-btn {{
            background: transparent;
            color: var(--text-muted);
            border: 1px solid var(--border);
        }}
        .clear-btn:hover {{
            background: var(--bg);
            color: var(--text);
        }}

        .active-filters {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }}
        .active-filter {{
            background: var(--accent);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .active-filter .remove {{
            cursor: pointer;
            opacity: 0.8;
        }}
        .active-filter .remove:hover {{
            opacity: 1;
        }}

        .companies-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }}

        .company-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            text-decoration: none;
            color: var(--text);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: all 0.2s;
            display: block;
            border: 2px solid transparent;
        }}
        .company-card:hover {{
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
            border-color: var(--accent);
            transform: translateY(-2px);
        }}
        .company-card.priority-high {{
            border-left: 4px solid var(--bull);
        }}
        .company-card.priority-medium {{
            border-left: 4px solid var(--warning);
        }}
        .company-card.priority-low {{
            border-left: 4px solid var(--border);
        }}

        .company-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }}
        .ticker {{
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--primary);
        }}
        .badges {{
            display: flex;
            gap: 6px;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.7rem;
            text-transform: uppercase;
        }}
        .badge.stage {{
            background: var(--bg);
            color: var(--text-muted);
        }}
        .badge.has-data {{
            background: #c6f6d5;
            color: var(--bull);
        }}
        .badge.no-data {{
            background: var(--bg);
            color: var(--text-muted);
        }}
        .badge.high {{
            background: #c6f6d5;
            color: var(--bull);
        }}
        .badge.medium {{
            background: #fefcbf;
            color: #975a16;
        }}
        .badge.low {{
            background: var(--bg);
            color: var(--text-muted);
        }}

        .company-name {{
            font-size: 1rem;
            font-weight: 500;
            margin-bottom: 4px;
        }}
        .company-meta {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 12px;
        }}
        .separator {{
            margin: 0 4px;
        }}
        .company-notes {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 12px;
            line-height: 1.4;
        }}
        .company-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 12px;
            border-top: 1px solid var(--border);
        }}
        .market-cap {{
            font-weight: 600;
            color: var(--primary);
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>Companies</h1>
            <p>Biotech and pharma companies with clinical data analysis</p>
            <div class="stats">
                <div class="stat-item">
                    <div class="value">{total}</div>
                    <div class="label">Companies</div>
                </div>
                <div class="stat-item">
                    <div class="value">{with_data}</div>
                    <div class="label">With Data</div>
                </div>
                <div class="stat-item">
                    <div class="value">{high_priority}</div>
                    <div class="label">High Priority</div>
                </div>
            </div>
        </div>
    </div>

    <div class="container">
        <form class="filters" method="GET" action="/api/clinical/companies/html">
            <div class="filter-group">
                <label>Stage</label>
                <select name="development_stage">
                    {stage_options}
                </select>
            </div>
            <div class="filter-group">
                <label>Modality</label>
                <select name="modality">
                    {modality_options}
                </select>
            </div>
            <div class="filter-group">
                <label>Therapeutic Area</label>
                <select name="therapeutic_area">
                    {area_options}
                </select>
            </div>
            <div class="filter-group">
                <label>Thesis Type</label>
                <select name="thesis_type">
                    {thesis_options}
                </select>
            </div>
            <div class="filter-group">
                <label>Priority</label>
                <select name="priority">
                    <option value="">All</option>
                    <option value="high" {'selected' if filters.get('priority') == 'high' else ''}>High</option>
                    <option value="medium" {'selected' if filters.get('priority') == 'medium' else ''}>Medium</option>
                    <option value="low" {'selected' if filters.get('priority') == 'low' else ''}>Low</option>
                </select>
            </div>
            <div class="filter-group">
                <label>Data Status</label>
                <select name="has_data">
                    <option value="">All</option>
                    <option value="true" {'selected' if filters.get('has_data') == True else ''}>Has Data</option>
                    <option value="false" {'selected' if filters.get('has_data') == False else ''}>No Data</option>
                </select>
            </div>
            <button type="submit" class="filter-btn">Apply Filters</button>
            <a href="/api/clinical/companies/html" class="filter-btn clear-btn">Clear</a>
        </form>

        <div class="companies-grid">
            {company_cards if company_cards else '<p>No companies match the selected filters.</p>'}
        </div>
    </div>
</body>
</html>'''


def _format_tag_label(tag: str) -> str:
    """Format tag from snake_case to Title Case. e.g. 'mid_clinical' -> 'Mid Clinical'"""
    if not tag:
        return ""
    return tag.replace("_", " ").title()


def _format_market_cap(value) -> str:
    """Format market cap - handle both numeric and pre-formatted string values."""
    if not value or value == 0:
        return "N/A"
    # If it's already a string with $ or B, return as-is
    if isinstance(value, str):
        # Remove any existing $ prefix for consistency, then add it back
        clean = value.strip()
        if clean.startswith("$"):
            return clean  # Already formatted like "$3.5B"
        return f"${clean}"
    # If numeric, format it
    if isinstance(value, (int, float)):
        if value >= 1000:
            return f"${value/1000:.1f}B"
        return f"${value:.0f}M"
    return str(value)


def _simplify_stage(stage: str) -> str:
    """Simplify long stage descriptions to short pills.
    e.g. 'IND-enabling complete; Phase 1 expected 2026' -> 'IND-enabling'
    """
    if not stage:
        return ""
    stage_lower = stage.lower()

    # Check for known stage keywords and return short version
    if "approved" in stage_lower:
        return "Approved"
    if "phase 3" in stage_lower or "phase3" in stage_lower or "ph3" in stage_lower:
        return "Phase 3"
    if "phase 2b" in stage_lower:
        return "Phase 2b"
    if "phase 2a" in stage_lower:
        return "Phase 2a"
    if "phase 2" in stage_lower or "phase2" in stage_lower or "ph2" in stage_lower:
        return "Phase 2"
    if "phase 1b" in stage_lower:
        return "Phase 1b"
    if "phase 1" in stage_lower or "phase1" in stage_lower or "ph1" in stage_lower:
        return "Phase 1"
    if "ind-enabling" in stage_lower or "ind enabling" in stage_lower:
        return "IND-enabling"
    if "ind" in stage_lower and "filed" in stage_lower:
        return "IND Filed"
    if "preclinical" in stage_lower:
        return "Preclinical"
    if "discovery" in stage_lower:
        return "Discovery"

    # If stage is long (has semicolon or >20 chars), take first part
    if ";" in stage:
        return stage.split(";")[0].strip()
    if len(stage) > 25:
        return stage[:20].strip() + "..."

    return stage


def _generate_company_overview_html(data: dict) -> str:
    """Generate company overview page HTML."""
    ticker = data.get("ticker", "")
    name = data.get("name", data.get("company_details", {}).get("name", ticker))
    company = data.get("company_details", {})
    classification = data.get("classification", {})
    thesis = data.get("investment_thesis", {})
    assets = data.get("assets", [])
    catalysts = data.get("catalysts", [])
    partnerships = data.get("partnerships", [])
    thesis_url = data.get("thesis_url", "")
    core_thesis = data.get("core_thesis", "")

    # Build pipeline table rows
    pipeline_rows = ""
    for asset in assets:
        asset_name = asset.get("name", "Unknown")
        asset_slug = asset_name.lower().replace("-", "").replace(" ", "_")
        target = asset.get("target", {})
        target_name = target.get("name", target) if isinstance(target, dict) else target
        stage = asset.get("stage", "")
        # Handle indications - can be dict (v2.0) or list (v1.0)
        indications = asset.get("indications")
        if asset.get("lead_indication"):
            lead_ind = asset.get("lead_indication")
        elif isinstance(indications, dict):
            lead = indications.get("lead", {})
            lead_ind = lead.get("name", "") if isinstance(lead, dict) else lead if lead else ""
        elif isinstance(indications, list) and indications:
            lead_ind = indications[0] if isinstance(indications[0], str) else indications[0].get("name", "")
        else:
            lead_ind = ""

        # Find next catalyst for this asset
        next_catalyst = ""
        for c in catalysts:
            if c.get("asset", "").lower() == asset_name.lower():
                next_catalyst = f"{c.get('event', '')} ({c.get('timing', '')})"
                break

        target_key = str(target_name).upper().replace(" ", "_") if target_name else ""
        # Simplify stage for clean badge display
        simple_stage = _simplify_stage(stage)
        pipeline_rows += f'''
        <tr>
            <td><a href="/api/clinical/companies/{ticker}/assets/{asset_slug}/html" class="asset-link">{asset_name}</a></td>
            <td><a href="/api/clinical/targets/{target_key}/html" class="target-link">{target_name}</a></td>
            <td><span class="badge stage">{simple_stage}</span></td>
            <td>{lead_ind}</td>
            <td class="catalyst-cell">{next_catalyst or '<span class="no-data">—</span>'}</td>
        </tr>'''

    # Build bull/bear HTML
    bull_case_raw = thesis.get("bull_case", []) if isinstance(thesis, dict) else thesis
    bear_case_raw = thesis.get("bear_case", []) if isinstance(thesis, dict) else []

    # Handle v2.0 schema where bull_case/bear_case are dicts with key_points
    if isinstance(bull_case_raw, dict):
        bull_case = bull_case_raw.get("key_points", [])
    else:
        bull_case = bull_case_raw if isinstance(bull_case_raw, list) else []

    if isinstance(bear_case_raw, dict):
        bear_case = bear_case_raw.get("key_points", [])
    else:
        bear_case = bear_case_raw if isinstance(bear_case_raw, list) else []

    bull_items = ""
    for item in bull_case[:3]:
        if isinstance(item, dict):
            bull_items += f'<li><strong>{item.get("point", "")}</strong><span class="evidence">{item.get("evidence", "")}</span></li>'
        else:
            bull_items += f'<li>{item}</li>'

    bear_items = ""
    for item in bear_case[:3]:
        if isinstance(item, dict):
            bear_items += f'<li><strong>{item.get("point", "")}</strong><span class="evidence">{item.get("evidence", "")}</span></li>'
        else:
            bear_items += f'<li>{item}</li>'

    # Build partnerships HTML
    partnerships_html = ""
    for p in partnerships:
        if isinstance(p, dict):
            partnerships_html += f'''
            <div class="partnership-row">
                <div class="partner">{p.get('partner', '')}</div>
                <div class="asset">{p.get('asset', '')}</div>
                <div class="terms">{p.get('upfront', '')} {f"/ {p.get('milestones', '')}" if p.get('milestones') else ''}</div>
                <div class="status">{p.get('status', '')}</div>
            </div>'''

    # Build unique, formatted tags - avoid duplicates
    raw_tags = [
        classification.get('development_stage', ''),
        classification.get('modality', ''),
        classification.get('therapeutic_area', ''),
    ]
    seen_tags = set()
    tags_html = ""
    for tag in raw_tags:
        if tag and tag not in seen_tags:
            seen_tags.add(tag)
            tags_html += f'<span class="badge">{_format_tag_label(tag)}</span>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} - {name} | Company Overview</title>
    <style>
        /* Satya Bio color palette - matches asset pages */
        :root {{
            --navy: #1a2b3c;
            --coral: #e07a5f;
            --white: #ffffff;
            --gray-light: #f8f9fa;
            --gray-border: #e2e5e9;
            --gray-text: #6b7280;
            --text-primary: #374151;
            /* Legacy aliases */
            --primary: var(--navy);
            --primary-light: #2d4a5e;
            --accent: var(--coral);
            --bg: var(--gray-light);
            --card-bg: var(--white);
            --border: var(--gray-border);
            --text: var(--text-primary);
            --text-muted: var(--gray-text);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}

        /* Breadcrumb */
        .breadcrumb {{
            background: white;
            padding: 12px 24px;
            border-bottom: 1px solid var(--border);
            font-size: 0.9rem;
        }}
        .breadcrumb a {{
            color: var(--accent);
            text-decoration: none;
        }}
        .breadcrumb a:hover {{
            text-decoration: underline;
        }}
        .breadcrumb span {{
            color: var(--text-muted);
            margin: 0 8px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
        }}

        /* Header - clean navy, no gradients */
        .header {{
            background: var(--navy);
            color: var(--white);
            padding: 32px;
            border-radius: 0;
            margin-bottom: 24px;
        }}
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }}
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 4px;
        }}
        .header .ticker {{
            font-size: 1rem;
            opacity: 0.8;
        }}
        .header .description {{
            opacity: 0.9;
            max-width: 700px;
            line-height: 1.5;
        }}
        .snapshot {{
            display: flex;
            gap: 24px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        .snapshot-item {{
            background: rgba(255,255,255,0.15);
            padding: 12px 20px;
            border-radius: 8px;
        }}
        .snapshot-item .label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            opacity: 0.7;
        }}
        .snapshot-item .value {{
            font-size: 1.25rem;
            font-weight: 600;
        }}

        /* Tags - subtle pills */
        .tags {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 0.75rem;
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.25);
            color: rgba(255,255,255,0.9);
        }}

        /* Cards */
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 24px;
            overflow: hidden;
        }}
        .card-header {{
            padding: 16px 24px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            font-size: 1.1rem;
            color: var(--primary);
        }}
        .card-content {{
            padding: 24px;
        }}

        /* Thesis */
        .thesis-btn {{
            float: right;
            background: var(--accent, #e07a5f);
            color: white;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 500;
            text-decoration: none;
        }}
        .thesis-btn:hover {{
            opacity: 0.9;
        }}
        .core-thesis {{
            background: var(--white);
            border: 1px solid var(--gray-border);
            border-left: 3px solid var(--coral);
            border-radius: 0;
            padding: 16px 20px;
            margin-bottom: 20px;
            font-size: 0.95rem;
            line-height: 1.6;
            color: var(--text-primary);
        }}
        .thesis-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }}
        @media (max-width: 768px) {{
            .thesis-grid {{ grid-template-columns: 1fr; }}
        }}
        .thesis-column {{
            padding: 20px;
            border-radius: 0;
            background: var(--white);
            border: 1px solid var(--gray-border);
        }}
        .thesis-column.bull {{
            border-left: 2px solid var(--coral);
        }}
        .thesis-column.bear {{
            border-left: 2px solid var(--navy);
        }}
        .thesis-column h3 {{
            font-size: 1rem;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .thesis-column.bull h3 {{ color: var(--coral); }}
        .thesis-column.bear h3 {{ color: var(--navy); }}
        .thesis-column ul {{
            list-style: none;
        }}
        .thesis-column li {{
            margin-bottom: 12px;
            padding-left: 16px;
            position: relative;
        }}
        .thesis-column li::before {{
            content: '•';
            position: absolute;
            left: 0;
        }}
        .thesis-column.bull li::before {{ color: var(--coral); }}
        .thesis-column.bear li::before {{ color: var(--navy); }}
        .thesis-column li strong {{
            display: block;
            margin-bottom: 4px;
        }}
        .thesis-column .evidence {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}

        /* Pipeline Table - Bloomberg style */
        .pipeline-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .pipeline-table th, .pipeline-table td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--gray-border);
        }}
        .pipeline-table th {{
            background: var(--navy);
            color: var(--white);
            font-size: 0.75rem;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
        .pipeline-table tbody tr:nth-child(even) {{
            background: var(--gray-light);
        }}
        .pipeline-table tr:hover {{
            background: #f0f4f8;
        }}
        .pipeline-table .badge.stage {{
            background: var(--gray-light);
            color: var(--navy);
            border: 1px solid var(--gray-border);
            font-size: 0.75rem;
            padding: 3px 10px;
            border-radius: 3px;
        }}
        .asset-link {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 600;
        }}
        .asset-link:hover {{
            text-decoration: underline;
        }}
        .target-link {{
            color: #805ad5;
            text-decoration: none;
        }}
        .target-link:hover {{
            text-decoration: underline;
        }}
        .catalyst-cell {{
            font-size: 0.9rem;
        }}
        .no-data {{
            color: var(--text-muted);
        }}

        /* Partnerships */
        .partnership-row {{
            display: grid;
            grid-template-columns: 1fr 1fr 2fr auto;
            gap: 16px;
            padding: 16px 0;
            border-bottom: 1px solid var(--border);
            align-items: center;
        }}
        .partnership-row:last-child {{
            border-bottom: none;
        }}
        .partner {{
            font-weight: 600;
        }}
        .terms {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        .status {{
            font-size: 0.85rem;
            padding: 4px 12px;
            background: var(--bg);
            border-radius: 20px;
        }}

        h2 {{
            color: var(--primary);
            margin-bottom: 16px;
        }}
    </style>
</head>
<body>
    <div class="breadcrumb">
        <a href="/companies">Companies</a>
        <span>›</span>
        <strong>{ticker}</strong>
    </div>

    <div class="container">
        <div class="header">
            <div class="header-top">
                <div>
                    <h1>{name}</h1>
                    <div class="ticker">{ticker} · {classification.get('exchange', 'NASDAQ')}</div>
                </div>
                <div class="tags">
                    {tags_html}
                </div>
            </div>
            <p class="description">{company.get('description', '')}</p>
            <div class="snapshot">
                <div class="snapshot-item">
                    <div class="label">Market Cap</div>
                    <div class="value">{_format_market_cap(data.get('market_cap_mm'))}</div>
                </div>
                <div class="snapshot-item">
                    <div class="label">Cash Runway</div>
                    <div class="value">{company.get('cash_runway', 'N/A')}</div>
                </div>
                <div class="snapshot-item">
                    <div class="label">Pipeline</div>
                    <div class="value">{len(assets)} Assets</div>
                </div>
                <div class="snapshot-item">
                    <div class="label">Priority</div>
                    <div class="value">{classification.get('priority', '').title()}</div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">Investment Thesis{f' <a href="{thesis_url}" class="thesis-btn">View Full Thesis →</a>' if thesis_url else ''}</div>
            <div class="card-content">
                {f'<p class="core-thesis">{core_thesis}</p>' if core_thesis else ''}
                <div class="thesis-grid">
                    <div class="thesis-column bull">
                        <h3>🐂 Bull Case</h3>
                        <ul>{bull_items if bull_items else '<li>No bull case data</li>'}</ul>
                    </div>
                    <div class="thesis-column bear">
                        <h3>🐻 Bear Case</h3>
                        <ul>{bear_items if bear_items else '<li>No bear case data</li>'}</ul>
                    </div>
                </div>
            </div>
        </div>

        <h2>Pipeline</h2>
        <div class="card">
            <table class="pipeline-table">
                <thead>
                    <tr>
                        <th>Asset</th>
                        <th>Target</th>
                        <th>Stage</th>
                        <th>Lead Indication</th>
                        <th>Next Catalyst</th>
                    </tr>
                </thead>
                <tbody>
                    {pipeline_rows if pipeline_rows else '<tr><td colspan="5" class="no-data">No pipeline data</td></tr>'}
                </tbody>
            </table>
        </div>

        {f"""<h2>Partnerships</h2>
        <div class="card">
            <div class="card-content">
                {partnerships_html}
            </div>
        </div>""" if partnerships_html else ""}
    </div>
</body>
</html>'''


def _generate_asset_page_html(company_data: dict, asset: dict, prev_asset: dict, next_asset: dict) -> str:
    """Generate individual asset page HTML with sidebar navigation - supports v2.0 schema."""
    ticker = company_data.get("ticker", "")
    company_name = capitalize_medical_terms(company_data.get("name", ""))
    asset_name = capitalize_medical_terms(asset.get("name", "Unknown"))
    target_data = asset.get("target", {})
    mechanism_data = asset.get("mechanism", {})
    stage = capitalize_medical_terms(asset.get("stage", ""))
    modality = asset.get("modality", "")
    drug_class = get_drug_class(modality)
    # Create short modality for header (remove redundant "small molecule" prefix if present)
    short_modality = modality
    if short_modality.lower().startswith("small molecule "):
        short_modality = short_modality[15:].strip()  # Remove "small molecule "
    short_modality = capitalize_medical_terms(short_modality)
    indications_data = asset.get("indications", {})
    market = asset.get("market_opportunity", {})
    clinical_data = asset.get("clinical_data", {})
    investment_analysis = asset.get("investment_analysis", {})

    # New v2.0 fields for disease context
    disease_background = asset.get("disease_background", {})
    current_treatment = asset.get("current_treatment_landscape", {})
    asset_differentiation = asset.get("edg7500_differentiation", {}) or asset.get("differentiation", {})
    competitive_landscape = asset.get("competitive_landscape", {})
    regulatory_path = asset.get("regulatory_path", {})
    abbreviations = asset.get("abbreviations", {})

    # Extract citation badges from source objects
    def get_badge(data_obj, key="source"):
        """Extract source object and generate badge."""
        if isinstance(data_obj, dict):
            source = data_obj.get(key)
            if source:
                return generate_citation_badge(source, ticker)
        return ""

    # Section-level citation badges
    target_source_badge = get_badge(target_data.get("why_good_target", {}) if isinstance(target_data, dict) else {})
    mechanism_badge = get_badge(mechanism_data) if isinstance(mechanism_data, dict) else ""
    indications_badge = get_badge(indications_data) if isinstance(indications_data, dict) else ""
    market_badge = get_badge(market) if isinstance(market, dict) else ""

    # Executive summary data
    one_liner = asset.get("one_liner", "")
    why_good_target = target_data.get("why_good_target", {}) if isinstance(target_data, dict) else {}
    unmet_need = why_good_target.get("unmet_need", []) if isinstance(why_good_target, dict) else []
    if isinstance(unmet_need, str):
        unmet_need = [unmet_need]

    # Get catalysts from both company and asset level
    company_catalysts = company_data.get("catalysts", [])
    asset_catalysts_list = asset.get("catalysts", [])
    asset_catalysts = asset_catalysts_list + [c for c in company_catalysts if c.get("asset", "").lower() == asset_name.lower()]

    # Build FDA designation badges
    fda_designation_badges = ""
    fda_designations = regulatory_path.get("fda_designations", [])
    if isinstance(fda_designations, list):
        for des in fda_designations:
            if isinstance(des, dict):
                des_name = des.get("designation", "")
                des_date = des.get("date", "")
                des_badge = generate_citation_badge(des.get("source"), ticker) if des.get("source") else ""
                fda_designation_badges += f'<span class="badge fda-designation" title="{des.get("indication", "")} ({des_date})">{des_name}{des_badge}</span>'
    elif isinstance(fda_designations, str) and fda_designations.lower() not in ["none", "none yet"]:
        fda_designation_badges = f'<span class="badge fda-designation">{fda_designations}</span>'

    # Parse indications - handle both list and v2.0 nested format
    if isinstance(indications_data, dict):
        lead = indications_data.get("lead", {})
        lead_name = lead.get("name", "") if isinstance(lead, dict) else ""
        expansion = indications_data.get("expansion", [])
        indications = [lead_name] + [e.get("name", "") if isinstance(e, dict) else e for e in expansion]
    elif isinstance(indications_data, list):
        indications = indications_data
    else:
        indications = []

    # Parse target - handle both v1.0 (flat) and v2.0 (nested) schemas
    if isinstance(target_data, dict):
        # Handle both KYMR-style (name) and NUVL-style (primary_target) schemas
        target_name = capitalize_medical_terms(target_data.get("name", "") or target_data.get("primary_target", ""))
        target_full = capitalize_medical_terms(target_data.get("full_name", "") or target_data.get("target_class", ""))
        target_pathway = capitalize_medical_terms(target_data.get("pathway", ""))

        # v2.0 has nested biology object
        biology_data = target_data.get("biology", "")
        if isinstance(biology_data, dict):
            # Handle KYMR-style (simple_explanation) and NUVL-style (function) schemas
            target_biology = biology_data.get("simple_explanation", "") or biology_data.get("pathway_detail", "") or biology_data.get("function", "")
            downstream = biology_data.get("downstream_effects", [])
        else:
            target_biology = biology_data
            downstream = []

        # v2.0 has nested why_good_target object
        why_good = target_data.get("why_good_target", {})
        clinical_validation = why_good.get("clinical_validation", "") if isinstance(why_good, dict) else ""

        # v2.0 has nested genetic_validation object (inside why_good_target or at target level)
        genetic_data = why_good.get("genetic_validation", {}) if isinstance(why_good, dict) else target_data.get("genetic_validation", "")
        if isinstance(genetic_data, dict):
            gof = genetic_data.get("gain_of_function", "")
            lof = genetic_data.get("loss_of_function", "")
            target_genetic = f"<strong>GoF:</strong> {gof}<br><strong>LoF:</strong> {lof}" if gof and lof else (gof or lof)
        else:
            target_genetic = genetic_data

        # v2.0 has nested why_undruggable_before object
        why_data = target_data.get("why_undruggable_before", "") or target_data.get("degrader_advantage", "")
        if isinstance(why_data, dict):
            target_why = why_data.get("degrader_solution", "") or why_data.get("challenge", "")
        else:
            target_why = why_data

        # v2.0 dupilumab_comparison
        dupilumab_comp = target_data.get("dupilumab_comparison", {})
    else:
        target_name = capitalize_medical_terms(target_data) if target_data else ""
        target_full = target_pathway = target_biology = target_genetic = target_why = clinical_validation = ""
        downstream = []
        dupilumab_comp = {}

    # Parse mechanism - handle both v1.0 and v2.0 schemas
    if isinstance(mechanism_data, dict):
        mech_type = mechanism_data.get("type", "")
        mech_desc = mechanism_data.get("how_it_works", "") or mechanism_data.get("description", "")
        mech_diff = mechanism_data.get("differentiation", "") or mechanism_data.get("catalytic_advantage", "")
        mech_selectivity = mechanism_data.get("selectivity", "")
        potency = mechanism_data.get("potency", {})
        if isinstance(potency, dict):
            dc90 = potency.get("dc90", "")
            potency_str = f"{dc90} - {potency.get('interpretation', '')}" if dc90 else ""
        else:
            potency_str = ""
    else:
        mech_type = ""
        mech_desc = mechanism_data
        mech_diff = mech_selectivity = potency_str = ""

    # =======================================================================
    # BUILD CLINICAL DATA HTML - Handle v2.0 schema with phase-specific data
    # =======================================================================
    trials_html = ""
    head_to_head_html = ""

    # Check for v2.0 schema: phase1_healthy_volunteer, phase1b_ad, ongoing_trials
    phase1_hv = clinical_data.get("phase1_healthy_volunteer", {})
    phase1b_ad = clinical_data.get("phase1b_ad", {})
    ongoing_trials = clinical_data.get("ongoing_trials", [])

    # Also check for v1.0 schema: trials array
    trials_v1 = clinical_data.get("trials", [])

    def build_efficacy_table_from_dict(efficacy_endpoints: dict, trial_name: str) -> str:
        """Build efficacy table from v2.0 dict format (EASI, PPNRS, etc.)"""
        if not efficacy_endpoints:
            return ""
        rows = ""
        for endpoint_key, endpoint_data in efficacy_endpoints.items():
            if not isinstance(endpoint_data, dict):
                continue
            name = endpoint_data.get("full_name", endpoint_key.upper())
            what_measures = endpoint_data.get("what_it_measures", "")
            results = endpoint_data.get("results", {})
            # Support both old source_slide and new source object format
            source_obj = endpoint_data.get("source")
            source_badge = generate_citation_badge(source_obj, ticker) if source_obj else ""

            # Get main result
            main_result = results.get("mean_change_overall_day29", "") or results.get("mean_change_overall", "") or results.get("responders_overall", "")
            vs_dup = results.get("vs_dupilumab", "") or results.get("vs_dupilumab_day28_ph3", "") or results.get("vs_dupilumab_week16", "")

            rows += f'''
            <tr>
                <td>
                    <div class="endpoint-name">{name}{source_badge}</div>
                    <div class="endpoint-def">{what_measures}</div>
                </td>
                <td class="result"><strong>{main_result}</strong></td>
                <td class="comparator">{"vs Dupilumab: " + vs_dup if vs_dup else ""}</td>
            </tr>'''

        if rows:
            return f'''
            <div class="endpoints-section">
                <h5>Efficacy Endpoints</h5>
                <table class="data-table">
                    <thead><tr><th>Endpoint</th><th>Result</th><th>vs Comparator</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>'''
        return ""

    def build_biomarker_table(biomarker_results: dict) -> str:
        """Build biomarker table from v2.0 format"""
        if not biomarker_results:
            return ""

        summary_table = biomarker_results.get("summary_table", {})
        data = summary_table.get("data", [])
        if not data:
            return ""

        # Get source badge for biomarker section
        source_obj = summary_table.get("source")
        section_badge = generate_citation_badge(source_obj, ticker) if source_obj else ""

        # Also check for skin_transcriptomics source
        skin_trans = biomarker_results.get("skin_transcriptomics", {})
        skin_trans_badge = generate_citation_badge(skin_trans.get("source"), ticker) if skin_trans.get("source") else ""

        rows = ""
        for item in data:
            name = item.get("biomarker", "")
            what_measures = item.get("what_it_measures", "")
            kt621_result = item.get("kt621_result", "")
            dup_result = item.get("dupilumab_result", "")
            interpretation = item.get("interpretation", "")

            rows += f'''
            <tr>
                <td>
                    <div class="biomarker-name">{name}</div>
                    <div class="method">{what_measures}</div>
                </td>
                <td class="result"><strong>{kt621_result}</strong></td>
                <td class="comparator">Dupilumab: {dup_result}</td>
                <td>{interpretation}</td>
            </tr>'''

        skin_trans_html = ""
        if skin_trans:
            skin_trans_html = f'''
            <div class="skin-transcriptomics" style="margin-top: 12px; padding: 10px;">
                <strong>Skin Transcriptomics{skin_trans_badge}</strong>: {skin_trans.get("result", "")}
                <span style="color: var(--text-muted);">({skin_trans.get("interpretation", "")})</span>
            </div>'''

        return f'''
        <div class="biomarkers-section">
            <h5>Biomarker Results{section_badge}</h5>
            <table class="data-table">
                <thead><tr><th>Biomarker</th><th>Result</th><th>vs Dupilumab</th><th>Interpretation</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
            {skin_trans_html}
        </div>'''

    def build_safety_html(safety: dict) -> str:
        """Build safety section from v2.0 format"""
        if not isinstance(safety, dict):
            return ""
        summary = safety.get("summary", "")
        key_findings = safety.get("key_findings", [])
        conj_comp = safety.get("conjunctivitis_comparison", {})
        source_obj = safety.get("source")
        safety_badge = generate_citation_badge(source_obj, ticker) if source_obj else ""

        findings_html = ""
        if key_findings:
            findings_html = '<ul class="findings-list">' + "".join(f'<li>{f}</li>' for f in key_findings) + '</ul>'

        conj_html = ""
        if conj_comp and isinstance(conj_comp, dict):
            kt621_rate = conj_comp.get("kt621", "")
            dup_rate = conj_comp.get("dupilumab", "")
            interp = conj_comp.get("interpretation", "")
            conj_html = f'''
            <div class="safety-diff">
                <strong>Conjunctivitis:</strong> KT-621 {kt621_rate} vs Dupilumab {dup_rate}<br>
                <em>{interp}</em>
            </div>'''

        if summary or findings_html:
            return f'''
            <div class="safety-box">
                <h5>Safety Profile{safety_badge}</h5>
                <p>{summary}</p>
                {findings_html}
                {conj_html}
            </div>'''
        return ""

    # Build Phase 1 Healthy Volunteer section
    if phase1_hv:
        trial_name = phase1_hv.get("trial_name", "Phase 1 SAD/MAD")
        design = phase1_hv.get("design", {})
        design_type = design.get("type", "") if isinstance(design, dict) else design
        population = design.get("population", "") if isinstance(design, dict) else ""
        sad_n = design.get("sad_n", 0) if isinstance(design, dict) else 0
        mad_n = design.get("mad_n", 0) if isinstance(design, dict) else 0
        # Format patient count cleanly: "n=118 (48 SAD, 70 MAD)"
        try:
            total_n = int(sad_n) + int(mad_n)
            patient_count_str = f"n={total_n} ({sad_n} SAD, {mad_n} MAD)"
        except (ValueError, TypeError):
            patient_count_str = f"n={sad_n} SAD, {mad_n} MAD" if sad_n or mad_n else ""

        # STAT6 degradation data
        stat6_deg = phase1_hv.get("stat6_degradation", {})
        deg_results = stat6_deg.get("results_by_dose", [])
        key_findings = stat6_deg.get("key_findings", [])
        stat6_badge = generate_citation_badge(stat6_deg.get("source"), ticker) if stat6_deg.get("source") else ""

        deg_rows = ""
        for r in deg_results:
            deg_rows += f'''
            <tr>
                <td>{r.get('dose', '')}</td>
                <td class="result"><strong>{r.get('blood_change', '')}</strong></td>
                <td class="result"><strong>{r.get('skin_change', '')}</strong></td>
                <td>{r.get('n_blood', '')}</td>
            </tr>'''

        findings_html = ""
        if key_findings:
            findings_html = '<div class="key-findings"><strong>Key Findings:</strong><ul>' + "".join(f'<li>{f}</li>' for f in key_findings) + '</ul></div>'

        safety_html = build_safety_html(phase1_hv.get("safety", {}))

        trials_html += f'''
        <div class="trial-card">
            <div class="trial-header">
                <h4>{trial_name}</h4>
                <span class="badge completed">Phase 1</span>
                <span class="badge completed">Completed</span>
                <span class="n-enrolled">{patient_count_str}</span>
            </div>
            <div class="trial-meta">
                <p><strong>Design:</strong> {design_type}</p>
                <p><strong>Population:</strong> {population}</p>
            </div>
            <div class="endpoints-section">
                <h5>STAT6 Degradation by Dose{stat6_badge}</h5>
                <table class="data-table">
                    <thead><tr><th>Dose</th><th>Blood Change</th><th>Skin Change</th><th>N</th></tr></thead>
                    <tbody>{deg_rows}</tbody>
                </table>
                <p class="data-approximation-note"><em>Values approximated from presentation visuals. Official: >90% mean STAT6 degradation at doses ≥25mg; complete degradation at ≥50mg MAD.</em></p>
            </div>
            {findings_html}
            {safety_html}
        </div>'''

    # Build Phase 1b AD section
    if phase1b_ad:
        trial_name = phase1b_ad.get("trial_name", "Phase 1b AD")
        design = phase1b_ad.get("design", {})
        design_type = design.get("type", "") if isinstance(design, dict) else design
        population = design.get("population", "") if isinstance(design, dict) else ""
        n_enrolled = design.get("n_enrolled", "") if isinstance(design, dict) else ""
        cohorts = design.get("cohorts", []) if isinstance(design, dict) else []

        limitations = phase1b_ad.get("design_limitations", [])
        lims_html = ""
        if limitations:
            lims_items = "".join(f'<li>{l}</li>' for l in limitations)
            lims_html = f'<div class="limitations-box"><strong>Study Limitations:</strong><ul>{lims_items}</ul></div>'

        # Efficacy endpoints (v2.0 dict format)
        efficacy_endpoints = phase1b_ad.get("efficacy_endpoints", {})
        efficacy_html = build_efficacy_table_from_dict(efficacy_endpoints, trial_name)

        # Biomarker results
        biomarker_results = phase1b_ad.get("biomarker_results", {})
        biomarkers_html = build_biomarker_table(biomarker_results)

        # Safety
        safety_html = build_safety_html(phase1b_ad.get("safety", {}))

        # Baseline characteristics with badge
        baseline_chars_ad = phase1b_ad.get("baseline_characteristics", {})
        baseline_html = ""
        if baseline_chars_ad and isinstance(baseline_chars_ad, dict):
            baseline_badge = generate_citation_badge(baseline_chars_ad.get("source"), ticker) if baseline_chars_ad.get("source") else ""
            baseline_rows = ""
            for key, value in baseline_chars_ad.items():
                if key in ("source", "analyst_note"):
                    continue
                label = key.replace("_", " ").replace("pct", "%").title()
                label = label.replace("Easi", "EASI").replace("Ppnrs", "PPNRS").replace("Scorad", "SCORAD")
                label = label.replace("Bsa", "BSA").replace("Bmi", "BMI").replace("Viga", "vIGA")
                baseline_rows += f'<tr><td>{label}</td><td class="result"><strong>{value}</strong></td></tr>'
            if baseline_rows:
                analyst_note = baseline_chars_ad.get("analyst_note", "")
                note_html = f'<div class="analyst-note"><strong>Note:</strong> {analyst_note}</div>' if analyst_note else ""
                baseline_html = f'''
                <div class="baseline-section" style="margin-top: 16px;">
                    <h5>Baseline Characteristics{baseline_badge}</h5>
                    <table class="data-table" style="font-size: 0.9em;">
                        <tbody>{baseline_rows}</tbody>
                    </table>
                    {note_html}
                </div>'''

        # Comorbid asthma data with badge
        comorbid_asthma = phase1b_ad.get("comorbid_asthma_data", {})
        comorbid_asthma_html = ""
        if comorbid_asthma and isinstance(comorbid_asthma, dict):
            asthma_badge = generate_citation_badge(comorbid_asthma.get("source"), ticker) if comorbid_asthma.get("source") else ""
            asthma_n = comorbid_asthma.get("n", "?")
            caveat = comorbid_asthma.get("caveat", "")

            asthma_rows = ""
            for key, data in comorbid_asthma.items():
                if key in ("source", "n", "caveat") or not isinstance(data, dict):
                    continue
                name = data.get("full_name", key.upper())
                result = data.get("result", "") or data.get("mean_change", "")
                vs_dup = data.get("vs_dupilumab_asthma", "")
                interp = data.get("interpretation", "")
                asthma_rows += f'<tr><td><strong>{name}</strong></td><td class="result">{result}</td><td>{vs_dup}</td><td><em>{interp}</em></td></tr>'

            if asthma_rows:
                comorbid_asthma_html = f'''
                <div class="comorbid-section">
                    <h5 style="margin-bottom: 8px;">Comorbid Asthma Subgroup (n={asthma_n}){asthma_badge}</h5>
                    <table class="data-table" style="font-size: 0.9em;">
                        <thead><tr><th>Measure</th><th>Result</th><th>vs Dupilumab</th><th>Interpretation</th></tr></thead>
                        <tbody>{asthma_rows}</tbody>
                    </table>
                    {f'<p class="caveat" style="margin-top: 8px; font-style: italic; color: #6b7280;">{caveat}</p>' if caveat else ''}
                </div>'''

        # Comorbid allergic rhinitis data with badge
        comorbid_rhinitis = phase1b_ad.get("comorbid_allergic_rhinitis_data", {})
        comorbid_rhinitis_html = ""
        if comorbid_rhinitis and isinstance(comorbid_rhinitis, dict):
            rhinitis_badge = generate_citation_badge(comorbid_rhinitis.get("source"), ticker) if comorbid_rhinitis.get("source") else ""

            rhinitis_rows = ""
            for key, data in comorbid_rhinitis.items():
                if key == "source" or not isinstance(data, dict):
                    continue
                name = data.get("full_name", key.upper())
                n = data.get("n", "")
                result = data.get("mean_change", "")
                responders = data.get("responders", "")
                mcid = data.get("mcid", "")
                rhinitis_rows += f'<tr><td><strong>{name}</strong><br><span style="font-size: 0.85em; color: #6b7280;">MCID: {mcid}</span></td><td>n={n}</td><td class="result">{result}</td><td>{responders} responders</td></tr>'

            if rhinitis_rows:
                comorbid_rhinitis_html = f'''
                <div class="comorbid-section">
                    <h5 style="margin-bottom: 8px;">Comorbid Allergic Rhinitis Subgroup{rhinitis_badge}</h5>
                    <table class="data-table" style="font-size: 0.9em;">
                        <thead><tr><th>Measure</th><th>N</th><th>Change</th><th>Response</th></tr></thead>
                        <tbody>{rhinitis_rows}</tbody>
                    </table>
                </div>'''

        # Head-to-head comparison table
        h2h_data = phase1b_ad.get("head_to_head_comparison_table", {})
        h2h_rows = ""
        h2h_badge = ""
        if isinstance(h2h_data, dict):
            h2h_list = h2h_data.get("data", [])
            caveat = h2h_data.get("caveat", "")
            h2h_badge = generate_citation_badge(h2h_data.get("source"), ticker) if h2h_data.get("source") else ""
            for row in h2h_list:
                endpoint = row.get("endpoint", "")
                kt621 = row.get("kt621_day29", "")
                dup = row.get("dupilumab_day28", "")
                winner = row.get("winner", "")
                winner_class = "winner-kt621" if winner == "KT-621" else "winner-tie" if winner == "Tie" else ""
                # Only highlight KT-621 value with coral when it's the winner
                result_class = "result key-result" if winner == "KT-621" else "result"
                h2h_rows += f'''
                <tr class="{winner_class}">
                    <td>{endpoint}</td>
                    <td class="{result_class}"><strong>{kt621}</strong></td>
                    <td>{dup}</td>
                    <td class="winner">{winner}</td>
                </tr>'''

            if h2h_rows:
                head_to_head_html = f'''
                <div class="h2h-section">
                    <h5>Head-to-Head Comparison: KT-621 vs Dupilumab{h2h_badge}</h5>
                    <p class="caveat">{caveat}</p>
                    <table class="data-table h2h-table">
                        <thead><tr><th>Endpoint</th><th>KT-621 Day 29</th><th>Dupilumab Day 28</th><th>Winner</th></tr></thead>
                        <tbody>{h2h_rows}</tbody>
                    </table>
                    <p class="cross-trial-disclaimer"><em>Note: Cross-trial comparisons may not be reliable. No head-to-head trials have been conducted. Data may not be directly comparable due to differences in trial protocols, dosing regimens, and patient populations.</em></p>
                </div>'''

        trials_html += f'''
        <div class="trial-card featured">
            <div class="trial-header">
                <h4>{trial_name}</h4>
                <span class="badge completed">Phase 1b</span>
                <span class="badge completed">Completed</span>
                <span class="n-enrolled">n={n_enrolled}</span>
            </div>
            <div class="trial-meta">
                <p><strong>Design:</strong> {design_type}</p>
                <p><strong>Population:</strong> {population}</p>
            </div>
            {lims_html}
            {baseline_html}
            {efficacy_html}
            {head_to_head_html}
            {biomarkers_html}
            {comorbid_asthma_html}
            {comorbid_rhinitis_html}
            {safety_html}
        </div>'''

    # Build ongoing trials section
    for trial in ongoing_trials:
        trial_name = trial.get("trial_name", "Trial")
        phase = trial.get("phase", "")
        indication = trial.get("indication", "")
        status = trial.get("status", "Ongoing")
        data_expected = trial.get("data_expected", "")
        trial_badge = generate_citation_badge(trial.get("source"), ticker) if trial.get("source") else ""

        design = trial.get("design", {})
        design_type = design.get("type", "") if isinstance(design, dict) else design
        n_target = design.get("n_target", "") if isinstance(design, dict) else ""
        population = design.get("population", "") if isinstance(design, dict) else ""

        endpoints = trial.get("endpoints", {})
        primary = endpoints.get("primary", "") if isinstance(endpoints, dict) else ""
        secondary = endpoints.get("secondary", []) if isinstance(endpoints, dict) else []

        success = trial.get("what_success_looks_like", {})
        failure = trial.get("what_failure_looks_like", {})

        success_html = ""
        if success:
            items = "".join(f'<li>{k}: {v}</li>' for k, v in success.items() if k != "source_slide")
            success_html = f'<div class="success-criteria"><strong>Success Criteria:</strong><ul>{items}</ul></div>'

        failure_html = ""
        if failure:
            items = "".join(f'<li>{k}: {v}</li>' for k, v in failure.items() if k != "source_slide")
            failure_html = f'<div class="failure-criteria"><strong>Failure Criteria:</strong><ul>{items}</ul></div>'

        trials_html += f'''
        <div class="trial-card ongoing">
            <div class="trial-header">
                <h4>{trial_name}{trial_badge}</h4>
                <span class="badge ongoing">{phase}</span>
                <span class="badge ongoing">{status}</span>
                <span class="n-enrolled">Target n={n_target}</span>
            </div>
            <div class="trial-meta">
                <p><strong>Indication:</strong> {indication}</p>
                <p><strong>Design:</strong> {design_type}</p>
                <p><strong>Population:</strong> {population}</p>
                <p><strong>Primary Endpoint:</strong> {primary}</p>
                <p><strong>Data Expected:</strong> {data_expected}</p>
            </div>
            {success_html}
            {failure_html}
        </div>'''

    # Fallback to v1.0 trials format - handle both list and dict formats
    trials_list = trials_v1.values() if isinstance(trials_v1, dict) else trials_v1
    for trial in trials_list:
        if not isinstance(trial, dict):
            continue
        trial_name = trial.get("trial_name", "Trial")
        phase = trial.get("phase", "")
        status = trial.get("status", "")
        n = trial.get("n_enrolled", "?")

        design = trial.get("design", {})
        design_str = design.get("description", design) if isinstance(design, dict) else design
        limitations = design.get("limitations", "") if isinstance(design, dict) else ""

        pop = trial.get("population", {})
        pop_str = pop.get("description", pop) if isinstance(pop, dict) else pop

        efficacy_rows = ""
        for e in trial.get("efficacy_endpoints", []):
            defn = e.get("definition", {})
            vs = e.get("vs_comparator", {})
            vs_str = f"vs {vs.get('comparator', '')}: {vs.get('comparator_result', '')}" if isinstance(vs, dict) and vs.get("comparator") else ""
            efficacy_rows += f'''
            <tr>
                <td><div class="endpoint-name">{e.get('name', '')}</div></td>
                <td class="result"><strong>{e.get('result', 'Pending')}</strong></td>
                <td>{e.get('timepoint', '')}</td>
                <td class="comparator">{vs_str}</td>
            </tr>'''

        safety = trial.get("safety", {})
        safety_html = ""
        if isinstance(safety, dict) and safety.get("summary"):
            safety_html = f'<div class="safety-box"><h5>Safety</h5><p>{safety.get("summary", "")}</p></div>'

        status_class = "ongoing" if status == "Ongoing" else "completed" if status == "Completed" else ""
        trials_html += f'''
        <div class="trial-card">
            <div class="trial-header">
                <h4>{trial_name}</h4>
                <span class="badge {status_class}">{phase}</span>
                <span class="badge {status_class}">{status}</span>
                <span class="n-enrolled">n={n}</span>
            </div>
            <div class="trial-meta">
                <p><strong>Design:</strong> {design_str}</p>
                <p><strong>Population:</strong> {pop_str}</p>
            </div>
            {f'<div class="endpoints-section"><h5>Efficacy</h5><table class="data-table"><thead><tr><th>Endpoint</th><th>Result</th><th>Timepoint</th><th>vs Comparator</th></tr></thead><tbody>{efficacy_rows}</tbody></table></div>' if efficacy_rows else ''}
            {safety_html}
        </div>'''

    # =======================================================================
    # COMPREHENSIVE CLINICAL DATA (EWTX/HCM-style with tabs and sections)
    # =======================================================================
    if not trials_html and clinical_data.get("trial_name"):
        trial_name = clinical_data.get("trial_name", "")
        trial_design = clinical_data.get("trial_design", {})
        populations = clinical_data.get("populations", {})

        design_phase = trial_design.get("phase", "") if isinstance(trial_design, dict) else ""
        design_desc = trial_design.get("design", "") if isinstance(trial_design, dict) else ""
        doses_tested = trial_design.get("doses_tested", "") if isinstance(trial_design, dict) else ""
        data_cutoff = trial_design.get("data_cutoff", "") if isinstance(trial_design, dict) else ""

        # ===== 1. TRIAL OVERVIEW =====
        trial_overview_html = f'''
        <div class="clinical-subsection trial-overview">
            <div class="trial-overview-header">
                <h3>{trial_name}</h3>
                <span class="badge ongoing">{design_phase}</span>
            </div>
            <div class="trial-overview-grid">
                <div class="overview-item"><strong>Design:</strong> {design_desc}</div>
                {f'<div class="overview-item"><strong>Doses:</strong> {doses_tested}</div>' if doses_tested else ''}
                {f'<div class="overview-item"><strong>Data Cutoff:</strong> {data_cutoff}</div>' if data_cutoff else ''}
            </div>
        </div>'''

        # ===== 2. POPULATIONS TABLE =====
        pop_rows = ""
        if isinstance(populations, dict):
            for pop_key, pop_data in populations.items():
                if isinstance(pop_data, dict):
                    pop_name = pop_key.upper() if pop_key in ['ohcm', 'nhcm'] else pop_key.replace("_", " ").title()
                    n_val = pop_data.get("n", "?")
                    desc = pop_data.get("description", "")
                    pop_rows += f'<tr><td><strong>{pop_name}</strong></td><td class="n-value">{n_val}</td><td>{desc}</td></tr>'

        populations_html = ""
        if pop_rows:
            populations_html = f'''
        <div class="clinical-subsection populations-section">
            <h4>Study Populations</h4>
            <table class="data-table populations-table">
                <thead><tr><th>Cohort</th><th>N</th><th>Description</th></tr></thead>
                <tbody>{pop_rows}</tbody>
            </table>
        </div>'''

        # ===== 3. BASELINE CHARACTERISTICS WITH TABS =====
        # Handle both old (baseline_ohcm/baseline_nhcm) and new (baseline_characteristics.ohcm/nhcm) formats
        baseline_chars = clinical_data.get("baseline_characteristics", {})
        baseline_ohcm = clinical_data.get("baseline_ohcm", {}) or baseline_chars.get("ohcm", {})
        baseline_nhcm = clinical_data.get("baseline_nhcm", {}) or baseline_chars.get("nhcm", {})
        baseline_explained = clinical_data.get("baseline_characteristics_explained", {})

        # Build enhanced tooltips from baseline_characteristics_explained
        variable_defs = baseline_explained.get("variable_definitions", {})

        def get_enhanced_tooltip(key):
            """Build rich tooltip from baseline_characteristics_explained data."""
            key_lower = key.lower()

            # Search through variable_definitions for matching key
            for category, category_data in variable_defs.items():
                if not isinstance(category_data, dict):
                    continue
                for var_key, var_data in category_data.items():
                    if isinstance(var_data, dict) and var_key.lower() in key_lower:
                        defn = var_data.get("definition", "")
                        normal = var_data.get("normal_range", var_data.get("normal", ""))
                        study = var_data.get("study_values", var_data.get("study_finding", ""))
                        relevance = var_data.get("key_relevance", var_data.get("relevance", ""))

                        # Build multi-line tooltip
                        parts = []
                        if defn:
                            parts.append(defn)
                        if normal:
                            parts.append(f"Normal: {normal}")
                        if study:
                            parts.append(f"Study: {study}")
                        if relevance:
                            parts.append(f"Key: {relevance}")

                        if parts:
                            return " | ".join(parts)
                    elif var_key.lower() in key_lower and isinstance(var_data, str):
                        return var_data

            # Fallback to basic tooltips
            basic_tooltips = {
                "nyha": "New York Heart Association functional classification (I-IV)",
                "lvef": "Left Ventricular Ejection Fraction - heart pumping efficiency (normal: 55-70%)",
                "lvot": "Left Ventricular Outflow Tract Gradient - pressure difference showing obstruction",
                "e_prime": "Early diastolic velocity - measures heart relaxation (normal: >8 cm/s)",
                "nt_probnp": "NT-proBNP - cardiac stress biomarker (normal: <125 pg/mL)",
                "kccq": "Kansas City Cardiomyopathy Questionnaire - quality of life (0-100, higher=better)",
                "icd": "Implantable Cardioverter-Defibrillator",
                "sarcomere": "Genetic mutation in sarcomere proteins causing HCM",
                "female": "Percentage of female patients in cohort",
                "age": "Mean (SD) age of patients in years"
            }
            for abbr, tip in basic_tooltips.items():
                if abbr in key_lower:
                    return tip
            return ""

        def build_baseline_rows(baseline_data):
            rows = ""
            for key, value in baseline_data.items():
                # Format label - convert to proper medical abbreviations
                label = key.replace("_", " ").title()
                # Fix common medical acronyms to uppercase
                label = label.replace("Nyha", "NYHA").replace("Lvef", "LVEF").replace("Lvot", "LVOT")
                label = label.replace("Nt Probnp", "NT-proBNP").replace("Kccq", "KCCQ")
                label = label.replace("E Prime", "e'").replace("Icd", "ICD")
                label = label.replace("Ohcm", "oHCM").replace("Nhcm", "nHCM")
                label = label.replace("Hcm", "HCM").replace("Bmi", "BMI")

                # Get enhanced tooltip
                tooltip_text = get_enhanced_tooltip(key)
                tooltip = f' <span class="enhanced-tooltip" data-tooltip="{tooltip_text}">ⓘ</span>' if tooltip_text else ''

                rows += f'<tr><td class="var-cell">{label}{tooltip}</td><td class="baseline-value"><strong>{value}</strong></td></tr>'
            return rows

        baseline_ohcm_rows = build_baseline_rows(baseline_ohcm)
        baseline_nhcm_rows = build_baseline_rows(baseline_nhcm)

        baseline_html = ""
        if baseline_ohcm_rows or baseline_nhcm_rows:
            baseline_html = f'''
        <div class="clinical-subsection baseline-section">
            <h4>Baseline Characteristics</h4>
            <div class="tabs-container">
                <div class="tab-buttons">
                    {'<button class="tab-btn active" data-tab="baseline-ohcm">oHCM (n=' + str(baseline_ohcm.get("n", populations.get("ohcm", {}).get("n", "?"))) + ')</button>' if baseline_ohcm_rows else ''}
                    {'<button class="tab-btn" data-tab="baseline-nhcm">nHCM (n=' + str(baseline_nhcm.get("n", populations.get("nhcm", {}).get("n", "?"))) + ')</button>' if baseline_nhcm_rows else ''}
                </div>
                <div class="tab-content">
                    {f'<div id="baseline-ohcm" class="tab-pane active"><table class="data-table baseline-table"><thead><tr><th>Variable</th><th>Value</th></tr></thead><tbody>{baseline_ohcm_rows}</tbody></table></div>' if baseline_ohcm_rows else ''}
                    {f'<div id="baseline-nhcm" class="tab-pane"><table class="data-table baseline-table"><thead><tr><th>Variable</th><th>Value</th></tr></thead><tbody>{baseline_nhcm_rows}</tbody></table></div>' if baseline_nhcm_rows else ''}
                </div>
            </div>
        </div>'''

        # ===== 4. EFFICACY RESULTS WITH TABS =====
        efficacy_results = clinical_data.get("efficacy_results", {})

        # Separate oHCM and nHCM results
        ohcm_efficacy = {k: v for k, v in efficacy_results.items() if k.startswith("ohcm_")}
        nhcm_efficacy = {k: v for k, v in efficacy_results.items() if k.startswith("nhcm_")}

        def build_efficacy_cards(efficacy_data, prefix):
            cards = ""
            # Group by category (lvot, ntprobnp, e_prime, nyha, etc.)
            categories = {}
            for key, value in efficacy_data.items():
                clean_key = key.replace(f"{prefix}_", "")
                # Determine category
                if "lvot" in clean_key:
                    cat = "LVOT-G Response"
                elif "ntprobnp" in clean_key or "nt_probnp" in clean_key:
                    cat = "NT-proBNP"
                elif "e_prime" in clean_key:
                    cat = "Diastolic Function (e')"
                elif "nyha" in clean_key:
                    cat = "NYHA Improvement"
                elif "kccq" in clean_key:
                    cat = "Quality of Life (KCCQ)"
                elif "clinical" in clean_key:
                    cat = "Overall Clinical Improvement"
                else:
                    cat = "Other Endpoints"
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append((clean_key, value))

            for cat_name, items in categories.items():
                items_html = ""
                for item_key, item_val in items:
                    label = item_key.replace("_", " ").title()
                    items_html += f'<div class="efficacy-item"><span class="efficacy-label">{label}:</span> <strong>{item_val}</strong></div>'
                cards += f'''
                <div class="efficacy-card">
                    <h5>{cat_name}</h5>
                    {items_html}
                </div>'''
            return cards

        ohcm_efficacy_cards = build_efficacy_cards(ohcm_efficacy, "ohcm")
        nhcm_efficacy_cards = build_efficacy_cards(nhcm_efficacy, "nhcm")

        efficacy_html = ""
        if ohcm_efficacy_cards or nhcm_efficacy_cards:
            efficacy_html = f'''
        <div class="clinical-subsection efficacy-section">
            <h4>Efficacy Results</h4>
            <div class="tabs-container">
                <div class="tab-buttons">
                    {'<button class="tab-btn active" data-tab="efficacy-ohcm">oHCM</button>' if ohcm_efficacy_cards else ''}
                    {'<button class="tab-btn" data-tab="efficacy-nhcm">nHCM</button>' if nhcm_efficacy_cards else ''}
                </div>
                <div class="tab-content">
                    {f'<div id="efficacy-ohcm" class="tab-pane active"><div class="efficacy-grid">{ohcm_efficacy_cards}</div></div>' if ohcm_efficacy_cards else ''}
                    {f'<div id="efficacy-nhcm" class="tab-pane"><div class="efficacy-grid">{nhcm_efficacy_cards}</div></div>' if nhcm_efficacy_cards else ''}
                </div>
            </div>
        </div>'''

        # ===== 5. SAFETY SECTION =====
        safety_data = clinical_data.get("safety", {})
        safety_html = ""
        if isinstance(safety_data, dict) and safety_data:
            # Key finding (highlighted)
            key_finding = safety_data.get("lvef_key_finding", "")
            key_finding_html = ""
            if key_finding:
                key_finding_html = f'''
                <div class="safety-key-finding">
                    <span class="check-icon">✓</span>
                    <strong>KEY FINDING:</strong> {key_finding}
                </div>'''

            # Adverse events table
            ae_rows = ""
            ae_keys = ["dizziness", "upper_respiratory", "atrial_fibrillation", "palpitations", "headache", "nausea"]
            for ae_key in ae_keys:
                ae_val = safety_data.get(ae_key, "")
                if ae_val:
                    ae_label = ae_key.replace("_", " ").title()
                    ae_rows += f'<tr><td>{ae_label}</td><td><strong>{ae_val}</strong></td></tr>'

            ae_table = ""
            if ae_rows:
                ae_table = f'''
                <div class="ae-section">
                    <h5>Adverse Events</h5>
                    <table class="data-table ae-table">
                        <thead><tr><th>Event</th><th>Incidence</th></tr></thead>
                        <tbody>{ae_rows}</tbody>
                    </table>
                </div>'''

            # Discontinuation
            discontinuation = safety_data.get("discontinuation", "")
            disc_html = f'<div class="discontinuation"><strong>Discontinuation:</strong> {discontinuation}</div>' if discontinuation else ""

            # Additional findings
            other_findings = []
            for skey, sval in safety_data.items():
                if skey not in ["lvef_key_finding", "discontinuation"] + ae_keys and isinstance(sval, str):
                    other_findings.append(f"<li>{skey.replace('_', ' ').title()}: {sval}</li>")
            other_html = f'<ul class="other-safety">{"".join(other_findings)}</ul>' if other_findings else ""

            safety_html = f'''
        <div class="clinical-subsection safety-section">
            <h4>Safety</h4>
            {key_finding_html}
            {ae_table}
            {disc_html}
            {other_html}
        </div>'''

        # ===== COMBINE ALL CLINICAL DATA SECTIONS =====
        trials_html = f'''
        <div class="comprehensive-clinical">
            {trial_overview_html}
            {populations_html}
            {baseline_html}
            {efficacy_html}
            {safety_html}
        </div>'''

    # =======================================================================
    # BUILD PRECLINICAL DATA HTML
    # =======================================================================
    preclinical_data = asset.get("preclinical_data", {})
    preclinical_html = ""
    if preclinical_data and isinstance(preclinical_data, dict):
        preclinical_badge = generate_citation_badge(preclinical_data.get("source"), ticker) if preclinical_data.get("source") else ""

        # Potency
        potency = preclinical_data.get("potency", {})
        potency_html = ""
        if potency:
            dc90 = potency.get("dc90", "")
            interp = potency.get("interpretation", "")
            potency_html = f'<div class="preclin-item"><strong>Potency:</strong> {dc90} <span style="color: #6b7280;">({interp})</span></div>' if dc90 else ""

        # Selectivity
        selectivity = preclinical_data.get("selectivity", {})
        selectivity_html = ""
        if selectivity:
            desc = selectivity.get("description", "")
            selectivity_html = f'<div class="preclin-item"><strong>Selectivity:</strong> {desc}</div>' if desc else ""

        # Comparison to Dupilumab
        comparison = preclinical_data.get("comparison_to_dupilumab", {})
        comparison_html = ""
        if comparison:
            items = []
            for key, value in comparison.items():
                label = key.replace("_", " ").title()
                items.append(f'<li><strong>{label}:</strong> {value}</li>')
            if items:
                comparison_html = f'<div class="preclin-item"><strong>vs Dupilumab:</strong><ul style="margin: 4px 0 0 16px;">{"".join(items)}</ul></div>'

        # Safety pharmacology
        safety_pharm = preclinical_data.get("safety_pharmacology", {})
        safety_pharm_html = ""
        if safety_pharm:
            rows = []
            for key, value in safety_pharm.items():
                label = key.replace("_", " ").title()
                rows.append(f'<tr><td>{label}</td><td>{value}</td></tr>')
            if rows:
                safety_pharm_html = f'''
                <div class="preclin-item">
                    <strong>Safety Pharmacology:</strong>
                    <table class="data-table" style="font-size: 0.85em; margin-top: 8px;">
                        <tbody>{"".join(rows)}</tbody>
                    </table>
                </div>'''

        if potency_html or selectivity_html or comparison_html or safety_pharm_html:
            preclinical_html = f'''
            <section id="preclinical" class="section">
                <h2 class="section-header">Preclinical Data{preclinical_badge}</h2>
                <div class="card">
                    <div class="card-content" style="display: flex; flex-direction: column; gap: 12px;">
                        {potency_html}
                        {selectivity_html}
                        {comparison_html}
                        {safety_pharm_html}
                    </div>
                </div>
            </section>'''

    # =======================================================================
    # BUILD INVESTMENT ANALYSIS HTML (Wall Street Research Style)
    # =======================================================================
    investment_html = ""
    if investment_analysis:
        bull_case = investment_analysis.get("bull_case", [])
        # Fallback: use key_risks as bear_case if bear_case doesn't exist
        bear_case = investment_analysis.get("bear_case", [])
        key_risks = investment_analysis.get("key_risks", [])
        if not bear_case and key_risks:
            # Convert key_risks strings to bear_case format
            bear_case = [{"point": risk, "evidence": "", "counter_argument": ""} for risk in key_risks]
        key_debates = investment_analysis.get("key_debates", [])
        pos = investment_analysis.get("probability_of_success", {})
        peak_sales = investment_analysis.get("peak_sales_estimate", "")

        # Bull Case Table Rows
        bull_rows = ""
        for item in bull_case:
            if isinstance(item, dict):
                point = item.get('point', '')
                evidence = item.get('evidence', '')
                conf = item.get('confidence', 'Medium').title()
                item_badge = generate_citation_badge(item.get('source'), ticker) if item.get('source') else ""
                bull_rows += f'<tr><td class="point-cell">{point}{item_badge}</td><td>{evidence}</td><td class="conf-cell">{conf}</td></tr>'
            else:
                bull_rows += f'<tr><td class="point-cell">{item}</td><td>—</td><td class="conf-cell">—</td></tr>'

        # Bear Case Table Rows
        bear_rows = ""
        for item in bear_case:
            if isinstance(item, dict):
                point = item.get('point', '')
                evidence = item.get('evidence', '')
                counter = item.get('counter_argument', '')
                prob = item.get('probability', '')
                item_badge = generate_citation_badge(item.get('source'), ticker) if item.get('source') else ""
                # Combine counter and probability into mitigant column
                mitigant = counter if counter else ''
                if prob:
                    mitigant += f' (Probability: {prob})' if mitigant else f'Probability: {prob}'
                bear_rows += f'<tr><td class="point-cell">{point}{item_badge}</td><td>{evidence}</td><td>{mitigant if mitigant else "—"}</td></tr>'
            else:
                bear_rows += f'<tr><td class="point-cell">{item}</td><td>—</td><td>—</td></tr>'

        # Key Debates Table Rows
        debates_rows = ""
        for debate in key_debates:
            if isinstance(debate, dict):
                question = debate.get('question', '')
                bull_view = debate.get('bull_view', '')
                bear_view = debate.get('bear_view', '')
                resolves = debate.get('what_resolves_it', '')
                debates_rows += f'<tr><td class="debate-q">{question}</td><td>{bull_view}</td><td>{bear_view}</td><td>{resolves}</td></tr>'

        # Probability of Success Table
        pos_html = ""
        if pos:
            if isinstance(pos, str):
                # Simple string value
                pos_html = f'''
            <div class="pos-section">
                <h4>Probability of Success</h4>
                <p class="pos-simple">{pos}</p>
            </div>'''
            elif isinstance(pos, dict):
                # Detailed dict with phase breakdowns
                pos_html = f'''
            <div class="pos-section">
                <h4>Probability of Success</h4>
                <table class="research-table pos-table">
                    <tbody>
                        <tr><td class="label-cell">Phase 2b → Phase 3</td><td class="value-cell">{pos.get('phase2b_to_phase3', '—')}</td></tr>
                        <tr><td class="label-cell">Phase 3 → Approval</td><td class="value-cell">{pos.get('phase3_to_approval', '—')}</td></tr>
                        <tr class="total-row"><td class="label-cell">Cumulative PoS</td><td class="value-cell">{pos.get('cumulative_pos', '—')}</td></tr>
                    </tbody>
                </table>
                {f'<p class="pos-methodology">{pos.get("methodology", "")}</p>' if pos.get("methodology") else ''}
            </div>'''

        # Build conditional sections
        bull_section = ""
        if bull_rows:
            bull_section = f'''
            <div class="research-subsection">
                <h4>Bull Case</h4>
                <table class="research-table">
                    <thead>
                        <tr><th>Thesis Point</th><th>Supporting Evidence</th><th>Confidence</th></tr>
                    </thead>
                    <tbody>{bull_rows}</tbody>
                </table>
            </div>'''

        bear_section = ""
        if bear_rows:
            bear_section = f'''
            <div class="research-subsection">
                <h4>{"Key Risks" if key_risks and not investment_analysis.get("bear_case") else "Bear Case"}</h4>
                <table class="research-table">
                    <thead>
                        <tr><th>Risk</th><th>Evidence</th><th>Mitigating Factors</th></tr>
                    </thead>
                    <tbody>{bear_rows}</tbody>
                </table>
            </div>'''

        debates_section = ""
        if debates_rows:
            debates_section = f'''
            <div class="research-subsection">
                <h4>Key Debates</h4>
                <table class="research-table debates-table">
                    <thead>
                        <tr><th>Question</th><th>Bull View</th><th>Bear View</th><th>Resolution Catalyst</th></tr>
                    </thead>
                    <tbody>{debates_rows}</tbody>
                </table>
            </div>'''

        peak_sales_html = ""
        if peak_sales:
            peak_sales_html = f'''
            <div class="peak-sales-highlight" style="margin-top: 12px; padding: 12px;">
                <strong style="color: var(--navy);">Peak Sales Estimate:</strong>
                <span style="font-size: 1em; color: var(--coral); font-weight: 600;">{peak_sales}</span>
            </div>'''

        investment_html = f'''
        <section id="investment" class="section research-section">
            <h2 class="section-header">Investment Analysis</h2>
            <div class="editorial-disclaimer">
                <strong>Satya Bio Analysis</strong> — estimates based on public data and analyst judgment, not sourced from company materials
            </div>
            {bull_section}
            {bear_section}
            {debates_section}
            {pos_html}
            {peak_sales_html}
        </section>'''

    # =======================================================================
    # BUILD DISEASE BACKGROUND HTML
    # =======================================================================
    disease_bg_html = ""
    if disease_background:
        sections_html = ""
        for section_key, section_data in disease_background.items():
            if isinstance(section_data, dict):
                section_title = capitalize_medical_terms(section_key.replace("_", " ").title())
                items_html = ""
                for key, value in section_data.items():
                    label = capitalize_medical_terms(key.replace("_", " ").title())
                    value_str = capitalize_medical_terms(str(value)) if isinstance(value, str) else str(value)
                    items_html += f'<div class="detail-row"><strong>{label}:</strong> {value_str}</div>'
                sections_html += f'''
                <div class="disease-section">
                    <h4>{section_title}</h4>
                    {items_html}
                </div>'''
        if sections_html:
            disease_bg_html = f'''
            <div class="disease-background-section" style="margin-top: 24px; padding: 20px; background: #f8fafc; border-radius: 8px; border-left: 4px solid #3182ce;">
                <h4 style="color: #2c5282; margin-bottom: 16px;">Disease Background</h4>
                <div class="disease-sections" style="display: grid; gap: 20px;">
                    {sections_html}
                </div>
            </div>'''

    # =======================================================================
    # BUILD TREATMENT LANDSCAPE HTML
    # =======================================================================
    treatment_html = ""
    if current_treatment:
        treatment_sections = ""
        for therapy_key, therapy_data in current_treatment.items():
            if isinstance(therapy_data, dict):
                therapy_title = capitalize_medical_terms(therapy_key.replace("_", " ").title())

                # Build therapy details
                details_html = ""
                for key, value in therapy_data.items():
                    if isinstance(value, dict):
                        # Nested drug info (like mavacamten, aficamten)
                        drug_name = capitalize_medical_terms(key.replace("_", " ").title())
                        drug_details = ""
                        for dk, dv in value.items():
                            label = capitalize_medical_terms(dk.replace("_", " ").title())
                            dv_str = capitalize_medical_terms(str(dv)) if isinstance(dv, str) else str(dv)
                            drug_details += f'<div class="drug-detail"><strong>{label}:</strong> {dv_str}</div>'
                        details_html += f'''
                        <div class="nested-drug" style="margin: 12px 0; padding: 12px; background: white; border-radius: 6px;">
                            <h5 style="color: #4a5568; margin-bottom: 8px;">{drug_name}</h5>
                            {drug_details}
                        </div>'''
                    elif isinstance(value, list):
                        label = capitalize_medical_terms(key.replace("_", " ").title())
                        list_items = "".join(f'<li>{capitalize_medical_terms(str(item))}</li>' for item in value)
                        details_html += f'<div class="detail-row"><strong>{label}:</strong><ul style="margin: 4px 0 0 20px;">{list_items}</ul></div>'
                    else:
                        label = capitalize_medical_terms(key.replace("_", " ").title())
                        value_str = capitalize_medical_terms(str(value)) if isinstance(value, str) else str(value)
                        details_html += f'<div class="detail-row"><strong>{label}:</strong> {value_str}</div>'

                treatment_sections += f'''
                <div class="therapy-section" style="margin-bottom: 20px; padding: 16px; background: #fff; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <h4 style="color: #2d3748; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">{therapy_title}</h4>
                    {details_html}
                </div>'''

        if treatment_sections:
            treatment_html = f'''
        <section id="treatment" class="section">
            <h2 class="section-header">Treatment Landscape</h2>
            <div style="display: grid; gap: 16px;">
                {treatment_sections}
            </div>
        </section>'''

    # =======================================================================
    # BUILD DIFFERENTIATION HTML
    # =======================================================================
    differentiation_html = ""
    if asset_differentiation:
        diff_items = ""
        for key, value in asset_differentiation.items():
            label = capitalize_medical_terms(key.replace("_", " ").replace("vs ", "vs. ").title())
            value_str = capitalize_medical_terms(str(value)) if isinstance(value, str) else str(value)
            diff_items += f'''
            <div class="diff-item" style="padding: 10px; background: var(--gray-light); border-left: 2px solid var(--coral);">
                <strong style="color: var(--navy);">{label}</strong>
                <p style="margin: 4px 0 0 0; font-size: 0.85rem;">{value_str}</p>
            </div>'''
        if diff_items:
            differentiation_html = f'''
            <div class="differentiation-section" style="margin-top: 20px;">
                <h4 style="color: var(--navy); margin-bottom: 12px; font-size: 0.95rem; font-weight: 600;">Key Differentiation</h4>
                <div style="display: grid; gap: 10px;">
                    {diff_items}
                </div>
            </div>'''

    # =======================================================================
    # BUILD CATALYSTS HTML (Wall Street Research Style)
    # =======================================================================
    catalysts_rows = ""
    for c in asset_catalysts:
        event = c.get('event', '')
        timing = c.get('timing', '')
        importance = c.get('importance', '')
        what_to_watch = c.get("what_to_watch", [])
        if isinstance(what_to_watch, list):
            watch_text = "; ".join(what_to_watch) if what_to_watch else "—"
        else:
            watch_text = what_to_watch if what_to_watch else "—"
        consensus = c.get("consensus_expectation", "")

        catalysts_rows += f'<tr><td class="event-cell">{event}</td><td>{timing}</td><td>{importance}</td><td>{watch_text}</td><td>{consensus if consensus else "—"}</td></tr>'

    catalysts_html = ""
    if catalysts_rows:
        catalysts_html = f'''
        <table class="research-table catalysts-table">
            <thead>
                <tr><th>Event</th><th>Timing</th><th>Importance</th><th>Key Metrics to Watch</th><th>Consensus</th></tr>
            </thead>
            <tbody>
                {catalysts_rows}
            </tbody>
        </table>'''

    # Indications badges
    ind_badges = "".join(f'<span class="indication-badge">{ind}</span>' for ind in indications if ind)

    # Prev/Next navigation
    prev_slug = prev_asset.get("name", "").lower().replace("-", "").replace(" ", "_") if prev_asset else ""
    next_slug = next_asset.get("name", "").lower().replace("-", "").replace(" ", "_") if next_asset else ""
    prev_name = prev_asset.get("name", "") if prev_asset else ""
    next_name = next_asset.get("name", "") if next_asset else ""

    # Build sidebar "Other Assets" list - all assets for this company sorted by stage
    all_company_assets = company_data.get("assets", [])
    # Sort by stage priority (most advanced first)
    sorted_assets = sorted(all_company_assets, key=lambda a: get_stage_priority(a.get("stage", "")))
    # Build HTML list, excluding current asset
    other_assets_html = ""
    for a in sorted_assets:
        a_name = a.get("name", "")
        if a_name.lower() == asset_name.lower():
            continue  # Skip current asset
        a_slug = a_name.lower().replace("-", "").replace(" ", "_")
        a_stage = a.get("stage", "")
        # Format stage for display (e.g., "Phase 2" -> "Ph2")
        stage_short = a_stage.replace("Phase ", "Ph").replace("Approved", "✓")
        other_assets_html += f'<li><a href="/api/clinical/companies/{ticker}/assets/{a_slug}/html">{a_name} <span style="color: var(--text-muted); font-size: 0.85em;">({stage_short})</span></a></li>'

    # Extract peak sales estimates (can't use {} in f-strings)
    peak_sales = market.get("peak_sales_estimate", {}) if isinstance(market.get("peak_sales_estimate"), dict) else {}
    peak_bull = peak_sales.get("bull_case", "") if peak_sales else ""
    peak_base = peak_sales.get("base_case", "") if peak_sales else ""

    # =======================================================================
    # BUILD EXECUTIVE SUMMARY HTML
    # =======================================================================
    executive_summary_html = ""
    if one_liner or unmet_need:
        # Build key differentiators from unmet_need or asset_differentiation
        differentiators = []
        if unmet_need:
            differentiators = unmet_need[:4]  # Max 4 bullets
        elif asset_differentiation:
            differentiators = list(asset_differentiation.values())[:4]

        diff_bullets = ""
        if differentiators:
            diff_items = "".join(f'<li>{d}</li>' for d in differentiators if d)
            diff_bullets = f'<ul class="exec-bullets">{diff_items}</ul>'

        executive_summary_html = f'''
        <section id="executive-summary" class="section">
            <div class="exec-summary-box">
                <div class="exec-header">
                    <span class="exec-icon">📊</span>
                    <h3>Executive Summary</h3>
                </div>
                <p class="exec-one-liner">{one_liner}</p>
                {f'<div class="exec-differentiators"><h4>Key Differentiators</h4>{diff_bullets}</div>' if diff_bullets else ''}
            </div>
        </section>'''

    # =======================================================================
    # BUILD COMPETITIVE LANDSCAPE HTML
    # =======================================================================
    competitive_html = ""
    if competitive_landscape:
        # Handle both formats: list directly or dict with "competitors" key
        if isinstance(competitive_landscape, list):
            competitors = competitive_landscape
            our_advantages = []
        else:
            competitors = competitive_landscape.get("competitors", [])
            our_advantages = competitive_landscape.get("our_advantages", []) or competitive_landscape.get("vyvgart_advantages", []) or competitive_landscape.get("empasiprubart_advantages", [])

        comp_rows = ""
        for comp in competitors:
            if isinstance(comp, dict):
                drug = comp.get("drug", "") or comp.get("competitor", "")
                company = comp.get("company", "")
                limitation = comp.get("limitation", "") or comp.get("status", "")
                comp_rows += f'<tr><td><strong>{drug}</strong></td><td>{company}</td><td>{limitation}</td></tr>'

        adv_items = ""
        if our_advantages:
            adv_items = "".join(f'<li>{a}</li>' for a in our_advantages)

        if comp_rows or adv_items:
            competitive_html = f'''
        <section id="competitive" class="section">
            <h2 class="section-header">Competitive Landscape</h2>
            <div class="competitive-grid">
                {f"""<div class="comp-card competitors">
                    <h4>Competitors</h4>
                    <table class="data-table">
                        <thead><tr><th>Drug</th><th>Company</th><th>Limitation</th></tr></thead>
                        <tbody>{comp_rows}</tbody>
                    </table>
                </div>""" if comp_rows else ""}
                {f"""<div class="comp-card advantages">
                    <h4>Our Advantages</h4>
                    <ul class="advantages-list">{adv_items}</ul>
                </div>""" if adv_items else ""}
            </div>
        </section>'''

    # Generate abbreviations JSON for JavaScript
    import json as json_module
    abbr_json = json_module.dumps(abbreviations) if abbreviations else "{}"

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{asset_name} - {ticker} | Asset Analysis</title>
    <style>
        /* Bloomberg Terminal Style - Clean, Data-Dense, Professional */
        :root {{
            --navy: #1a2b3c;
            --coral: #e07a5f;
            --white: #ffffff;
            --gray-light: #f8f9fa;
            --gray-border: #e2e5e9;
            --gray-text: #6b7280;
            --text-primary: #374151;
            --green: #4ade80;
            --red: #ef4444;
            --sidebar-width: 200px;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--white);
            color: var(--text-primary);
            line-height: 1.5;
            font-size: 0.875rem;
        }}

        /* Sticky Header */
        .sticky-header {{
            position: sticky;
            top: 0;
            background: var(--white);
            border-bottom: 1px solid var(--gray-border);
            z-index: 100;
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .breadcrumb {{
            font-size: 0.85rem;
        }}
        .breadcrumb a {{
            color: var(--coral);
            text-decoration: none;
        }}
        .breadcrumb a:hover {{
            text-decoration: underline;
        }}
        .breadcrumb span {{
            color: var(--gray-text);
            margin: 0 6px;
        }}
        .breadcrumb strong {{
            color: var(--navy);
        }}
        .header-badges {{
            display: flex;
            gap: 6px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 0.75rem;
            background: var(--gray-light);
            border: 1px solid var(--gray-border);
            color: var(--navy);
        }}
        .badge.ongoing {{ background: var(--gray-light); color: var(--navy); border-color: var(--gray-border); }}
        .badge.completed {{ background: var(--gray-light); color: var(--navy); border-color: var(--gray-border); }}
        .badge.timing {{ background: var(--gray-light); color: var(--gray-text); }}
        .badge.importance.critical {{ background: var(--gray-light); color: var(--red); border-color: var(--red); }}
        .badge.importance.high {{ background: var(--gray-light); color: var(--navy); }}
        .badge-link {{
            text-decoration: none;
        }}
        .badge-link:hover .badge {{
            border-color: var(--coral);
            color: var(--coral);
        }}

        /* Citation Badges */
        .citation-badge {{
            font-size: 0.7em;
            color: var(--gray-text);
            text-decoration: none;
            margin-left: 6px;
            font-family: 'SF Mono', 'Consolas', monospace;
            vertical-align: super;
        }}
        .citation-badge:hover {{
            color: var(--coral);
            text-decoration: underline;
        }}
        .verified-check {{
            color: var(--green);
            font-size: 0.7em;
            margin-left: 2px;
        }}

        /* Layout */
        .layout {{
            display: flex;
            max-width: 1200px;
            margin: 0 auto;
        }}

        /* Sidebar */
        .sidebar {{
            width: var(--sidebar-width);
            padding: 20px 12px;
            position: sticky;
            top: 50px;
            height: calc(100vh - 50px);
            overflow-y: auto;
            border-right: 1px solid var(--gray-border);
            background: var(--white);
        }}
        .sidebar h3 {{
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--gray-text);
            margin-bottom: 10px;
            padding-left: 10px;
            letter-spacing: 0.5px;
        }}
        .sidebar-nav {{
            list-style: none;
        }}
        .sidebar-nav a {{
            display: block;
            padding: 6px 10px;
            color: var(--text-primary);
            text-decoration: none;
            border-radius: 3px;
            font-size: 0.8rem;
            margin-bottom: 1px;
        }}
        .sidebar-nav a:hover {{
            background: var(--gray-light);
        }}
        .sidebar-nav a.active {{
            background: var(--navy);
            color: var(--white);
        }}

        /* Main Content */
        .main {{
            flex: 1;
            padding: 20px 28px;
            max-width: calc(100% - var(--sidebar-width));
        }}

        /* Sections */
        .section {{
            margin-bottom: 36px;
            scroll-margin-top: 70px;
        }}
        .section-header {{
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--navy);
            margin-bottom: 16px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--gray-border);
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }}
        .section-header .citation-badge {{
            margin-left: auto;
            font-size: 0.7rem;
        }}

        /* Asset Header */
        .asset-header {{
            background: var(--navy);
            color: var(--white);
            padding: 24px;
            border-radius: 0;
            margin-bottom: 24px;
        }}
        .asset-header h1 {{
            font-size: 1.5rem;
            margin-bottom: 6px;
            font-weight: 600;
        }}
        .asset-header .subtitle {{
            opacity: 0.85;
            font-size: 0.95rem;
        }}
        .asset-header .tags {{
            margin-top: 12px;
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }}
        .asset-header .badge {{
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            color: var(--white);
            border-radius: 3px;
        }}
        .asset-header .badge.fda-designation {{
            background: rgba(78, 205, 196, 0.25);
            border: 1px solid rgba(78, 205, 196, 0.5);
            color: #4ecdc4;
        }}

        /* Executive Summary */
        .exec-summary-box {{
            background: var(--white);
            border: 1px solid var(--gray-border);
            border-left: 3px solid var(--coral);
            border-radius: 0;
            padding: 16px 20px;
            margin-bottom: 24px;
        }}
        .exec-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }}
        .exec-icon {{
            font-size: 1.1rem;
            color: var(--coral);
        }}
        .exec-header h3 {{
            color: var(--navy);
            font-size: 1rem;
            font-weight: 600;
            margin: 0;
        }}
        .exec-one-liner {{
            font-size: 0.95rem;
            line-height: 1.5;
            color: var(--text-primary);
            margin-bottom: 12px;
        }}
        .exec-differentiators h4 {{
            font-size: 0.75rem;
            color: var(--gray-text);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .exec-bullets {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .exec-bullets li {{
            position: relative;
            padding-left: 18px;
            margin-bottom: 5px;
            line-height: 1.4;
            font-size: 0.85rem;
        }}
        .exec-bullets li::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: var(--coral);
            font-weight: bold;
        }}

        /* Competitive Landscape */
        .competitive-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }}
        @media (max-width: 900px) {{
            .competitive-grid {{ grid-template-columns: 1fr; }}
        }}
        .comp-card {{
            background: var(--white);
            border-radius: 0;
            padding: 16px;
            border: 1px solid var(--gray-border);
        }}
        .comp-card h4 {{
            color: var(--navy);
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 12px;
            padding-bottom: 6px;
            border-bottom: 1px solid var(--gray-border);
        }}
        .comp-card.advantages {{
            background: var(--white);
            border-left: 2px solid var(--coral);
        }}
        .advantages-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .advantages-list li {{
            position: relative;
            padding-left: 16px;
            margin-bottom: 6px;
            line-height: 1.4;
            font-size: 0.85rem;
        }}
        .advantages-list li::before {{
            content: "→";
            position: absolute;
            left: 0;
            color: var(--coral);
        }}

        /* Comprehensive Clinical Data */
        .comprehensive-clinical {{
            background: var(--white);
            border-radius: 0;
            border: 1px solid var(--gray-border);
            overflow: hidden;
        }}
        .clinical-subsection {{
            padding: 16px;
            border-bottom: 1px solid var(--gray-border);
        }}
        .clinical-subsection:last-child {{
            border-bottom: none;
        }}
        .clinical-subsection h4 {{
            color: var(--navy);
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        /* Trial Overview */
        .trial-overview-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }}
        .trial-overview-header h3 {{
            margin: 0;
            color: var(--navy);
            font-size: 1.1rem;
            font-weight: 600;
        }}
        .trial-overview-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 8px;
        }}
        .overview-item {{
            padding: 6px 10px;
            background: var(--gray-light);
            border-radius: 0;
            font-size: 0.85rem;
        }}

        /* Populations Table */
        .populations-table {{
            width: 100%;
        }}
        .populations-table .n-value {{
            font-weight: 600;
            color: var(--coral);
            text-align: center;
        }}

        /* Tabs */
        .tabs-container {{
            margin-top: 10px;
        }}
        .tab-buttons {{
            display: flex;
            gap: 4px;
            margin-bottom: 12px;
            border-bottom: 1px solid var(--gray-border);
            padding-bottom: 0;
        }}
        .tab-btn {{
            padding: 8px 16px;
            border: none;
            background: transparent;
            color: var(--gray-text);
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
            border-bottom: 2px solid transparent;
            margin-bottom: -1px;
            transition: all 0.2s;
        }}
        .tab-btn:hover {{
            color: var(--navy);
        }}
        .tab-btn.active {{
            color: var(--navy);
            border-bottom-color: var(--coral);
        }}
        .tab-pane {{
            display: none;
        }}
        .tab-pane.active {{
            display: block;
        }}

        /* Baseline Characteristics */
        .baseline-table {{
            width: 100%;
        }}
        .baseline-table .baseline-value {{
            text-align: right;
            font-family: 'SF Mono', 'Consolas', monospace;
            font-size: 0.8rem;
        }}
        .tooltip-icon {{
            color: var(--coral);
            cursor: help;
            font-size: 0.8rem;
            margin-left: 3px;
        }}

        /* Enhanced Tooltips */
        .enhanced-tooltip {{
            color: var(--gray-text);
            cursor: help;
            font-size: 0.75rem;
            margin-left: 4px;
            position: relative;
            display: inline-block;
            background: var(--gray-light);
            border-radius: 50%;
            width: 14px;
            height: 14px;
            text-align: center;
            line-height: 14px;
            border: 1px solid var(--gray-border);
        }}
        .enhanced-tooltip:hover {{
            background: var(--navy);
            color: var(--white);
            border-color: var(--navy);
        }}
        .enhanced-tooltip:hover::after {{
            content: attr(data-tooltip);
            position: absolute;
            bottom: calc(100% + 8px);
            left: 50%;
            transform: translateX(-50%);
            background: var(--navy);
            color: var(--white);
            padding: 10px 14px;
            border-radius: 3px;
            font-size: 0.8rem;
            line-height: 1.4;
            white-space: normal;
            width: 280px;
            max-width: 350px;
            z-index: 1000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            font-weight: normal;
            text-align: left;
        }}
        .enhanced-tooltip:hover::before {{
            content: '';
            position: absolute;
            bottom: calc(100% + 2px);
            left: 50%;
            transform: translateX(-50%);
            border: 5px solid transparent;
            border-top-color: var(--navy);
            z-index: 1001;
        }}
        .var-cell {{
            position: relative;
        }}

        /* Global Abbreviation Tooltips */
        .abbr-tooltip {{
            border-bottom: 1px dotted var(--gray-text);
            cursor: help;
            position: relative;
        }}
        .abbr-tooltip:hover {{
            border-bottom-color: var(--coral);
            color: var(--coral);
        }}
        .abbr-tooltip:hover::after {{
            content: attr(data-abbr);
            position: absolute;
            bottom: calc(100% + 6px);
            left: 50%;
            transform: translateX(-50%);
            background: var(--navy);
            color: var(--white);
            padding: 5px 8px;
            border-radius: 2px;
            font-size: 0.75rem;
            white-space: nowrap;
            z-index: 1000;
            font-weight: normal;
        }}
        .abbr-tooltip:hover::before {{
            content: '';
            position: absolute;
            bottom: calc(100% + 2px);
            left: 50%;
            transform: translateX(-50%);
            border: 4px solid transparent;
            border-top-color: var(--navy);
            z-index: 1001;
        }}

        /* Efficacy Grid */
        .efficacy-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 12px;
        }}
        .efficacy-card {{
            background: var(--gray-light);
            border-radius: 0;
            padding: 12px;
            border-left: 2px solid var(--coral);
        }}
        .efficacy-card h5 {{
            color: var(--navy);
            margin: 0 0 8px 0;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        .efficacy-item {{
            margin-bottom: 6px;
            line-height: 1.4;
            font-size: 0.8rem;
        }}
        .efficacy-label {{
            color: var(--gray-text);
            font-size: 0.8rem;
        }}

        /* Safety Section */
        .safety-key-finding {{
            background: var(--white);
            border: 1px solid var(--gray-border);
            border-left: 2px solid var(--green);
            border-radius: 0;
            padding: 12px 16px;
            margin-bottom: 16px;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }}
        .safety-key-finding .check-icon {{
            color: var(--green);
            font-size: 1rem;
            font-weight: bold;
        }}
        .ae-table {{
            width: 100%;
            max-width: 450px;
        }}
        .ae-section {{
            margin-bottom: 12px;
        }}
        .ae-section h5 {{
            color: var(--navy);
            margin-bottom: 8px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        .discontinuation {{
            margin-top: 12px;
            padding: 10px;
            background: var(--gray-light);
            border-radius: 0;
        }}
        .other-safety {{
            margin-top: 10px;
            padding-left: 18px;
            color: var(--gray-text);
            font-size: 0.8rem;
        }}
        .other-safety li {{
            margin-bottom: 4px;
        }}

        /* Cards */
        .card {{
            background: var(--white);
            border-radius: 0;
            border: 1px solid var(--gray-border);
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .card-content {{
            padding: 16px;
        }}

        /* Target/Mechanism Grid */
        .overview-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 20px;
        }}
        @media (max-width: 900px) {{
            .overview-grid {{ grid-template-columns: 1fr; }}
        }}
        .overview-card {{
            background: var(--white);
            border-radius: 0;
            padding: 16px;
            border: 1px solid var(--gray-border);
        }}
        .overview-card.target {{
            background: var(--white);
            border-left: 2px solid var(--navy);
        }}
        .overview-card.mechanism {{
            background: var(--white);
            border-left: 2px solid var(--coral);
        }}
        .overview-card h3 {{
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--gray-border);
            font-size: 0.95rem;
            font-weight: 600;
        }}
        .overview-card.target h3 {{ color: var(--navy); }}
        .overview-card.mechanism h3 {{ color: var(--navy); }}
        .detail-row {{
            margin-bottom: 10px;
            font-size: 0.85rem;
        }}
        .detail-row strong {{
            display: block;
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--gray-text);
            margin-bottom: 3px;
            letter-spacing: 0.3px;
        }}
        .genetic-highlight {{
            background: var(--gray-light);
            border-left: 2px solid var(--green);
            padding: 10px;
            border-radius: 0;
            margin-top: 12px;
            font-size: 0.85rem;
        }}

        /* Market */
        .market-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }}
        .market-item {{
            background: var(--gray-light);
            padding: 12px;
            border-radius: 0;
        }}
        .market-item.full {{ grid-column: 1 / -1; }}
        .market-item.highlight {{
            background: var(--white);
            border-left: 2px solid var(--coral);
        }}
        .market-item .label {{
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--gray-text);
            margin-bottom: 3px;
            letter-spacing: 0.3px;
        }}
        .market-item .value {{
            font-weight: 500;
            font-size: 0.85rem;
        }}

        /* Indications */
        .indications {{
            margin-bottom: 20px;
        }}
        .indication-badge {{
            display: inline-block;
            background: var(--gray-light);
            border: 1px solid var(--gray-border);
            padding: 4px 10px;
            border-radius: 3px;
            font-size: 0.8rem;
            margin: 3px 3px 3px 0;
        }}

        /* Trials */
        .trial-card {{
            background: var(--white);
            border: 1px solid var(--gray-border);
            border-radius: 0;
            padding: 16px;
            margin-bottom: 16px;
        }}
        .trial-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}
        .trial-header h4 {{
            margin: 0;
            color: var(--navy);
            font-size: 1rem;
            font-weight: 600;
        }}
        .n-enrolled {{
            color: var(--gray-text);
            font-size: 0.8rem;
        }}
        .trial-meta {{
            background: var(--gray-light);
            padding: 12px;
            border-radius: 0;
            margin-bottom: 16px;
            font-size: 0.85rem;
        }}
        .trial-meta p {{
            margin-bottom: 6px;
        }}
        .trial-meta p:last-child {{
            margin-bottom: 0;
        }}
        .limitation-text {{
            color: var(--gray-text);
            font-style: italic;
        }}

        /* Data Tables - Compact Bloomberg Style */
        .data-table {{
            width: auto;
            max-width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
            font-size: 0.8rem;
        }}
        .data-table th, .data-table td {{
            padding: 6px 10px;
            text-align: left;
            border: 1px solid var(--gray-border);
        }}
        .data-table th {{
            background: var(--navy);
            color: var(--white);
            font-size: 0.7rem;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
        .data-table td {{
            color: var(--text-primary);
            font-weight: 400;
        }}
        .data-table td:first-child {{
            font-weight: 500;
        }}
        .data-table tbody tr:nth-child(even) {{
            background: var(--gray-light);
        }}
        .endpoint-name, .biomarker-name {{
            font-weight: 600;
            color: var(--navy);
        }}
        .endpoint-def, .method {{
            font-size: 0.75rem;
            color: var(--gray-text);
        }}
        /* Table data: regular weight, dark gray by default */
        .result {{
            color: var(--text-primary);
        }}
        .result strong {{
            color: var(--text-primary);
            font-size: 0.95rem;
            font-weight: 500;
        }}
        /* Use .key-result or .highlight for winning/headline numbers only */
        .result.key-result strong,
        .result.highlight strong,
        td.key-result,
        td.highlight {{
            color: var(--coral);
            font-weight: 600;
        }}
        .comparator {{
            font-size: 0.75rem;
            color: var(--gray-text);
        }}
        .source {{
            font-size: 0.75rem;
            color: var(--gray-text);
        }}

        /* Safety */
        .safety-box {{
            background: var(--white);
            border: 1px solid var(--gray-border);
            border-left: 2px solid var(--green);
            padding: 12px;
            border-radius: 0;
            margin: 12px 0;
        }}
        .safety-box h5 {{
            color: var(--navy);
            margin-bottom: 6px;
            font-size: 0.9rem;
            font-weight: 600;
        }}
        .ae-badges {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-top: 10px;
        }}
        .ae-badge {{
            background: var(--gray-light);
            padding: 3px 8px;
            border-radius: 0;
            font-size: 0.75rem;
        }}
        .safety-diff {{
            margin-top: 10px;
            font-style: italic;
            color: var(--gray-text);
            font-size: 0.85rem;
        }}

        /* Limitations / Warnings - no red, subtle styling */
        .limitations-box {{
            background: var(--white);
            border: 1px solid var(--gray-border);
            border-left: 2px solid var(--coral);
            padding: 10px 14px;
            border-radius: 0;
            font-size: 0.85rem;
            color: var(--text-primary);
            margin-bottom: 12px;
        }}
        .limitations-box strong {{
            color: var(--navy);
        }}
        .limitations-box ul {{
            margin-top: 6px;
            padding-left: 18px;
        }}
        .limitations-box li {{
            margin-bottom: 4px;
            line-height: 1.4;
        }}

        /* Catalysts - now using research-table styling */

        /* Navigation */
        .asset-nav {{
            display: flex;
            justify-content: space-between;
            margin-top: 36px;
            padding-top: 20px;
            border-top: 1px solid var(--gray-border);
        }}
        .nav-link {{
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 10px 16px;
            background: var(--white);
            border: 1px solid var(--gray-border);
            border-radius: 0;
            text-decoration: none;
            color: var(--text-primary);
            font-size: 0.85rem;
        }}
        .nav-link:hover {{
            border-color: var(--coral);
            color: var(--coral);
        }}
        .nav-link.disabled {{
            opacity: 0.5;
            pointer-events: none;
        }}

        h5 {{
            color: var(--navy);
            margin-bottom: 10px;
            font-size: 0.9rem;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }}
        h5 .citation-badge {{
            margin-left: auto;
            font-size: 0.7rem;
        }}

        /* v2.0 Schema: Head-to-Head Comparison Table */
        .h2h-section {{
            margin: 16px 0;
            padding: 16px;
            background: var(--white);
            border-radius: 0;
            border: 1px solid var(--gray-border);
            border-left: 2px solid var(--coral);
        }}
        .h2h-section h5 {{
            color: var(--navy);
            margin-bottom: 6px;
        }}
        .h2h-section .caveat {{
            font-size: 0.75rem;
            color: var(--gray-text);
            font-style: italic;
            margin-bottom: 12px;
        }}
        .h2h-table .winner-kt621 {{
            background: var(--gray-light);
        }}
        .h2h-table .winner {{
            font-weight: 600;
            color: var(--coral);
        }}
        .h2h-table .winner-tie .winner {{
            color: var(--gray-text);
        }}
        .cross-trial-disclaimer {{
            font-size: 0.75rem;
            color: var(--gray-text);
            font-style: italic;
            margin-top: 12px;
            padding: 8px 12px;
            background: var(--gray-light);
            border-radius: 4px;
            line-height: 1.4;
        }}
        .data-approximation-note {{
            font-size: 0.75rem;
            color: var(--gray-text);
            font-style: italic;
            margin-top: 8px;
        }}
        .editorial-disclaimer {{
            font-size: 0.8rem;
            color: var(--gray-text);
            background: var(--gray-light);
            padding: 10px 14px;
            border-radius: 4px;
            margin-bottom: 16px;
            border-left: 3px solid var(--coral);
        }}
        .editorial-disclaimer strong {{
            color: var(--coral);
        }}

        /* Wall Street Research Style: Investment Analysis */
        .research-section {{
            background: var(--white);
        }}
        .research-subsection {{
            margin-bottom: 24px;
        }}
        .research-subsection h4 {{
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--navy);
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            border-bottom: 1px solid var(--gray-border);
            padding-bottom: 6px;
        }}
        .research-table {{
            width: auto;
            max-width: 100%;
            border-collapse: collapse;
            font-size: 0.8rem;
            background: var(--white);
        }}
        .research-table th {{
            background: var(--navy);
            color: var(--white);
            font-weight: 500;
            text-align: left;
            padding: 6px 10px;
            border: 1px solid var(--gray-border);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        .research-table td {{
            padding: 6px 10px;
            border: 1px solid var(--gray-border);
            vertical-align: top;
            color: var(--text-primary);
            line-height: 1.4;
        }}
        .research-table tbody tr:nth-child(even) {{
            background: var(--gray-light);
        }}
        .research-table .point-cell,
        .research-table .event-cell {{
            font-weight: 600;
            width: 25%;
            color: var(--navy);
        }}
        .research-table .conf-cell {{
            width: 90px;
            text-align: center;
            font-weight: 500;
        }}
        .research-table .debate-q {{
            font-weight: 600;
            width: 20%;
        }}
        .debates-table th:nth-child(2),
        .debates-table th:nth-child(3) {{
            width: 25%;
        }}
        .catalysts-table .event-cell {{
            width: 22%;
        }}
        .catalysts-table td:nth-child(2) {{
            width: 12%;
            white-space: nowrap;
        }}
        .catalysts-table td:nth-child(3) {{
            width: 10%;
            font-weight: 500;
        }}

        /* Probability of Success */
        .pos-section {{
            margin-top: 24px;
        }}
        .pos-section h4 {{
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--navy);
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            border-bottom: 1px solid var(--gray-border);
            padding-bottom: 6px;
        }}
        .pos-table {{
            max-width: 350px;
        }}
        .pos-table .label-cell {{
            font-weight: 500;
            width: 160px;
        }}
        .pos-table .value-cell {{
            font-weight: 600;
            text-align: right;
            color: var(--coral);
        }}
        .pos-table .total-row {{
            background: var(--gray-light);
        }}
        .pos-table .total-row td {{
            border-top: 1px solid var(--navy);
        }}
        .pos-methodology {{
            font-size: 0.75rem;
            color: var(--gray-text);
            font-style: italic;
            margin-top: 6px;
        }}

        /* v2.0 Schema: Trial Cards */
        .trial-card.featured {{
            border: 1px solid var(--coral);
            border-left: 3px solid var(--coral);
        }}
        .trial-card.ongoing {{
            border-left: 3px solid var(--gray-text);
        }}
        .key-findings {{
            background: var(--gray-light);
            padding: 12px;
            border-radius: 0;
            margin: 12px 0;
            border-left: 2px solid var(--coral);
        }}
        .key-findings ul {{
            margin: 6px 0 0 18px;
            font-size: 0.85rem;
        }}
        .findings-list {{
            margin: 10px 0 0 18px;
            font-size: 0.85rem;
        }}
        .success-criteria, .failure-criteria {{
            padding: 12px;
            border-radius: 0;
            margin: 10px 0;
            font-size: 0.85rem;
        }}
        .success-criteria {{
            background: var(--white);
            border: 1px solid var(--gray-border);
            border-left: 2px solid var(--green);
        }}
        .failure-criteria {{
            background: var(--white);
            border: 1px solid var(--gray-border);
            border-left: 2px solid var(--red);
        }}
        .success-criteria ul, .failure-criteria ul {{
            margin: 8px 0 0 20px;
        }}

        /* Catalyst enhancements */
        .consensus {{
            margin-top: 12px;
            padding: 10px;
            background: var(--gray-light);
            border-radius: 0;
            font-size: 0.8rem;
        }}
        .impact {{
            display: block;
            font-size: 0.8rem;
            font-weight: 600;
            margin-top: 3px;
        }}
        .scenario.bull .impact {{ color: var(--green); }}
        .scenario.bear .impact {{ color: var(--red); }}

        /* Additional compact styles */
        .analyst-note {{
            background: var(--gray-light);
            border-left: 2px solid var(--coral);
            padding: 8px 12px;
            font-size: 0.8rem;
            margin-top: 10px;
        }}
        .comorbid-section {{
            background: var(--gray-light);
            border-left: 2px solid var(--navy);
            padding: 12px;
            margin-top: 12px;
        }}
        .comorbid-section h5 {{
            margin-bottom: 8px;
        }}
        .baseline-section {{
            margin-top: 12px;
        }}
        .baseline-section h5 {{
            margin-bottom: 8px;
        }}
        .preclin-item {{
            margin-bottom: 10px;
            font-size: 0.85rem;
        }}
        .preclin-item ul {{
            margin: 4px 0 0 16px;
        }}
        .skin-transcriptomics {{
            background: var(--gray-light);
            border-left: 2px solid var(--green);
        }}
        .unmet-need-callout {{
            background: var(--gray-light) !important;
            border-left: 2px solid var(--coral) !important;
            border-radius: 0 !important;
            padding: 12px !important;
        }}
        .peak-sales-highlight {{
            background: var(--gray-light) !important;
            border-left: 2px solid var(--coral) !important;
            border-radius: 0 !important;
        }}
    </style>
</head>
<body>
    <div class="sticky-header">
        <div class="breadcrumb">
            <a href="/companies">Companies</a>
            <span>›</span>
            <a href="/api/clinical/companies/{ticker}/html">{ticker}</a>
            <span>›</span>
            <strong>{asset_name}</strong>
        </div>
        <div class="header-badges">
            <span class="badge">{stage}</span>
            <a href="/api/clinical/targets/{target_name.upper().replace(' ', '_')}/html" class="badge-link"><span class="badge">{target_name}</span></a>
            <span class="badge modality">{short_modality}</span>
        </div>
    </div>

    <div class="layout">
        <nav class="sidebar">
            <h3>Navigation</h3>
            <ul class="sidebar-nav">
                {'<li><a href="#executive-summary">Executive Summary</a></li>' if one_liner else ''}
                <li><a href="#overview">Overview</a></li>
                <li><a href="#target">Target Biology</a></li>
                {'<li><a href="#treatment">Treatment Landscape</a></li>' if current_treatment else ''}
                <li><a href="#clinical">Clinical Data</a></li>
                {'<li><a href="#competitive">Competitive Landscape</a></li>' if competitive_landscape else ''}
                {'<li><a href="#preclinical">Preclinical Data</a></li>' if preclinical_data else ''}
                <li><a href="#investment">Investment Analysis</a></li>
                <li><a href="#market">Market Opportunity</a></li>
                <li><a href="#catalysts">Catalysts</a></li>
            </ul>
            {f'<h3 style="margin-top: 24px;">{ticker} Assets</h3><ul class="sidebar-nav">{other_assets_html}</ul>' if other_assets_html else ''}
        </nav>

        <main class="main">
            {executive_summary_html}

            <section id="overview" class="section">
                <div class="asset-header">
                    <h1>{asset_name}</h1>
                    <div class="subtitle"><a href="/api/clinical/targets/{target_name.upper().replace(' ', '_')}/html" style="color: white; text-decoration: underline;">{target_name}</a> · {short_modality}</div>
                    <div class="tags">
                        <span class="badge">{stage}</span>
                        {f'<span class="badge">{asset.get("ownership", "")}</span>' if asset.get("ownership") else ''}
                        {fda_designation_badges}
                    </div>
                </div>

                <div class="overview-grid">
                    <div class="overview-card target">
                        <h3>Target: <a href="/api/clinical/targets/{target_name.upper().replace(' ', '_')}/html" style="color: var(--coral);">{target_name}</a></h3>
                        {f'<div class="detail-row"><strong>Full Name</strong>{target_full}</div>' if target_full else ''}
                        {f'<div class="detail-row"><strong>Pathway</strong>{target_pathway}</div>' if target_pathway else ''}
                        {f'<div class="detail-row"><a href="#target" style="color: var(--coral);">See Target Biology →</a></div>' if target_biology else ''}
                    </div>
                    <div class="overview-card mechanism">
                        <h3>Mechanism of Action{mechanism_badge}</h3>
                        {f'<div class="detail-row"><strong>Type</strong>{mech_type}</div>' if mech_type else ''}
                        {f'<div class="detail-row"><strong>Description</strong>{mech_desc}</div>' if mech_desc else ''}
                        {f'<div class="detail-row"><strong>Why This Approach</strong>{target_why}</div>' if target_why else ''}
                        {f'<div class="detail-row"><strong>Differentiation</strong>{mech_diff}</div>' if mech_diff else ''}
                    </div>
                </div>

                {f'<div class="indications"><strong>Indications:{indications_badge}</strong> {ind_badges}</div>' if ind_badges else ''}
            </section>

            <section id="target" class="section">
                <h2 class="section-header">Target Biology{target_source_badge}</h2>
                <div class="card">
                    <div class="card-content">
                        {f'<p style="margin-bottom: 16px;">{target_biology}</p>' if target_biology else '<p>No target biology data available.</p>'}
                        {f'<div class="genetic-highlight"><strong>Human Genetic Evidence:</strong> {target_genetic}</div>' if target_genetic else ''}
                        {f'<div class="detail-row" style="margin-top: 16px;"><strong>Why Previous Approaches Failed</strong>{target_why}</div>' if target_why else ''}
                        {disease_bg_html}
                        {differentiation_html}
                    </div>
                </div>
            </section>

            {treatment_html}

            <section id="clinical" class="section">
                <h2 class="section-header">Clinical Data</h2>
                {trials_html if trials_html else '<p class="no-data">No clinical trial data available.</p>'}
            </section>

            {competitive_html}

            {preclinical_html}

            {investment_html}

            <section id="market" class="section">
                <h2 class="section-header">Market Opportunity{market_badge}</h2>
                <div class="card">
                    <div class="card-content">
                        <div class="market-grid">
                            {f'<div class="market-item"><div class="label">Total Addressable Market</div><div class="value">{market.get("total_addressable_market", "") or market.get("tam", "N/A")}</div></div>' if market.get("total_addressable_market") or market.get("tam") else ''}
                            {f'<div class="market-item"><div class="label">Patient Population</div><div class="value">{market.get("patient_population", "")}</div></div>' if market.get("patient_population") else ''}
                            {f'<div class="market-item"><div class="label">Current Penetration</div><div class="value">{market.get("current_penetration", "")}</div></div>' if market.get("current_penetration") else ''}
                            {f'<div class="market-item"><div class="label">Oral Preference</div><div class="value">{market.get("oral_preference", "")}</div></div>' if market.get("oral_preference") else ''}
                            {f'<div class="market-item full highlight"><div class="label">Competitive Advantage</div><div class="value">{market.get("competitive_advantage", "")}</div></div>' if market.get("competitive_advantage") else ''}
                            {f'<div class="market-item"><div class="label">Peak Sales (Bull)</div><div class="value">{peak_bull}</div></div>' if peak_bull else ''}
                            {f'<div class="market-item"><div class="label">Peak Sales (Base)</div><div class="value">{peak_base}</div></div>' if peak_base else ''}
                        </div>
                        {f'<div class="unmet-need-callout" style="margin-top: 12px; padding: 12px;"><strong style="color: var(--navy);">Unmet Need:</strong> <span style="color: var(--text-primary);">{market.get("unmet_need", "")}</span></div>' if market.get("unmet_need") else ''}
                    </div>
                </div>
            </section>

            <section id="catalysts" class="section research-section">
                <h2 class="section-header">Catalysts & Upcoming Events</h2>
                {catalysts_html if catalysts_html else '<p class="no-data">No catalyst data available.</p>'}
            </section>

            <nav class="asset-nav">
                <a href="/api/clinical/companies/{ticker}/assets/{prev_slug}/html" class="nav-link {'disabled' if not prev_asset else ''}">
                    ← {prev_name if prev_asset else 'Previous'}
                </a>
                <a href="/api/clinical/companies/{ticker}/html" class="nav-link">
                    Back to {ticker} Overview
                </a>
                <a href="/api/clinical/companies/{ticker}/assets/{next_slug}/html" class="nav-link {'disabled' if not next_asset else ''}">
                    {next_name if next_asset else 'Next'} →
                </a>
            </nav>
        </main>
    </div>

    <script>
        // Highlight active section in sidebar
        const sections = document.querySelectorAll('.section');
        const navLinks = document.querySelectorAll('.sidebar-nav a');

        window.addEventListener('scroll', () => {{
            let current = '';
            sections.forEach(section => {{
                const sectionTop = section.offsetTop;
                if (scrollY >= sectionTop - 100) {{
                    current = section.getAttribute('id');
                }}
            }});

            navLinks.forEach(link => {{
                link.classList.remove('active');
                if (link.getAttribute('href') === '#' + current) {{
                    link.classList.add('active');
                }}
            }});
        }});

        // Tab switching functionality
        document.querySelectorAll('.tab-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const tabContainer = btn.closest('.tab-container, .baseline-section, .efficacy-section');
                if (!tabContainer) return;

                const tabId = btn.dataset.tab;

                // Update button states within this container
                tabContainer.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Update content visibility within this container
                tabContainer.querySelectorAll('.tab-content').forEach(content => {{
                    content.classList.remove('active');
                    if (content.id === tabId) {{
                        content.classList.add('active');
                    }}
                }});
            }});
        }});

        // Global abbreviation tooltips
        const abbreviations = {abbr_json};
        if (Object.keys(abbreviations).length > 0) {{
            // Build regex pattern from abbreviation keys (sorted by length descending to match longer first)
            const abbrKeys = Object.keys(abbreviations).sort((a, b) => b.length - a.length);
            const pattern = new RegExp('\\\\b(' + abbrKeys.map(k => k.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&')).join('|') + ')\\\\b', 'g');

            // Find text nodes and wrap abbreviations
            const walker = document.createTreeWalker(
                document.querySelector('.content') || document.body,
                NodeFilter.SHOW_TEXT,
                {{
                    acceptNode: function(node) {{
                        // Skip script, style, and already-processed elements
                        const parent = node.parentElement;
                        if (!parent) return NodeFilter.FILTER_REJECT;
                        if (parent.closest('script, style, .abbr-tooltip, .enhanced-tooltip, button, input, textarea, .baseline-table')) {{
                            return NodeFilter.FILTER_REJECT;
                        }}
                        return pattern.test(node.textContent) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
                    }}
                }}
            );

            const nodesToProcess = [];
            while (walker.nextNode()) nodesToProcess.push(walker.currentNode);

            nodesToProcess.forEach(textNode => {{
                const text = textNode.textContent;
                const fragment = document.createDocumentFragment();
                let lastIndex = 0;
                let match;

                // Reset pattern for each node
                pattern.lastIndex = 0;

                while ((match = pattern.exec(text)) !== null) {{
                    // Add text before match
                    if (match.index > lastIndex) {{
                        fragment.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
                    }}

                    // Create tooltip span
                    const span = document.createElement('span');
                    span.className = 'abbr-tooltip';
                    span.setAttribute('data-abbr', abbreviations[match[1]] || abbreviations[match[1].replace('_', ' ')] || match[1]);
                    span.textContent = match[1];
                    fragment.appendChild(span);

                    lastIndex = pattern.lastIndex;
                }}

                // Add remaining text
                if (lastIndex < text.length) {{
                    fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
                }}

                // Replace original node
                if (fragment.childNodes.length > 0) {{
                    textNode.parentNode.replaceChild(fragment, textNode);
                }}
            }});
        }}
    </script>
</body>
</html>'''


def _generate_company_html_v2(data: dict) -> str:
    """Generate PhD-level company analysis HTML with v2 schema."""
    ticker = data.get("ticker", "")
    name = data.get("name", data.get("company_details", {}).get("name", ticker))
    company = data.get("company_details", {})
    classification = data.get("classification", {})
    thesis = data.get("investment_thesis", {})
    assets = data.get("assets", [])
    catalysts = data.get("catalysts", [])
    partnerships = data.get("partnerships", [])

    # Build bull/bear case HTML (Wall Street Research Style)
    bull_case = thesis.get("bull_case", []) if isinstance(thesis, dict) else thesis
    bear_case = thesis.get("bear_case", []) if isinstance(thesis, dict) else []
    key_debates = thesis.get("key_debates", []) if isinstance(thesis, dict) else []

    # Bull Case Table Rows
    bull_rows = ""
    for item in bull_case:
        if isinstance(item, dict):
            point = item.get('point', '')
            evidence = item.get('evidence', '')
            conf = item.get('confidence', 'Medium').title()
            bull_rows += f'<tr><td class="point-cell">{point}</td><td>{evidence}</td><td class="conf-cell">{conf}</td></tr>'
        else:
            bull_rows += f'<tr><td class="point-cell">{item}</td><td>—</td><td class="conf-cell">—</td></tr>'

    # Bear Case Table Rows
    bear_rows = ""
    for item in bear_case:
        if isinstance(item, dict):
            point = item.get('point', '')
            evidence = item.get('evidence', '')
            counter = item.get('counter', '') or item.get('counter_argument', '')
            bear_rows += f'<tr><td class="point-cell">{point}</td><td>{evidence}</td><td>{counter if counter else "—"}</td></tr>'
        else:
            bear_rows += f'<tr><td class="point-cell">{item}</td><td>—</td><td>—</td></tr>'

    # Key Debates Table Rows
    debates_rows = ""
    for debate in key_debates:
        question = debate.get('question', '')
        bull_view = debate.get('bull_view', '')
        bear_view = debate.get('bear_view', '')
        data_watch = debate.get('data_to_watch', '') or debate.get('what_resolves_it', '')
        debates_rows += f'<tr><td class="debate-q">{question}</td><td>{bull_view}</td><td>{bear_view}</td><td>{data_watch}</td></tr>'

    # Build thesis HTML using tables
    bull_html = ""
    if bull_rows:
        bull_html = f'''
        <table class="research-table">
            <thead><tr><th>Thesis Point</th><th>Supporting Evidence</th><th>Confidence</th></tr></thead>
            <tbody>{bull_rows}</tbody>
        </table>'''

    bear_html = ""
    if bear_rows:
        bear_html = f'''
        <table class="research-table">
            <thead><tr><th>Risk</th><th>Evidence</th><th>Mitigating Factors</th></tr></thead>
            <tbody>{bear_rows}</tbody>
        </table>'''

    debates_html = ""
    if debates_rows:
        debates_html = f'''
        <table class="research-table debates-table">
            <thead><tr><th>Question</th><th>Bull View</th><th>Bear View</th><th>Resolution Catalyst</th></tr></thead>
            <tbody>{debates_rows}</tbody>
        </table>'''

    # Build assets HTML with full clinical data
    assets_html = ""
    for asset in assets:
        asset_name = asset.get("name", "Unknown")
        target_data = asset.get("target", {})
        mechanism_data = asset.get("mechanism", {})
        stage = asset.get("stage", "")
        modality = asset.get("modality", "")
        # Handle indications - can be dict (v2.0) or list (v1.0)
        indications_raw = asset.get("indications", [])
        if isinstance(indications_raw, dict):
            lead = indications_raw.get("lead", {})
            lead_name = lead.get("name", "") if isinstance(lead, dict) else lead if lead else ""
            expansion = indications_raw.get("expansion", [])
            indications = [lead_name] + [e.get("name", "") if isinstance(e, dict) else e for e in expansion]
        elif isinstance(indications_raw, list):
            indications = [i.get("name", "") if isinstance(i, dict) else i for i in indications_raw]
        else:
            indications = []
        clinical_data = asset.get("clinical_data", {})
        trials = clinical_data.get("trials", [])

        # Parse target - could be string or dict
        if isinstance(target_data, dict):
            target_name = target_data.get("name", "")
            target_full_name = target_data.get("full_name", "")
            target_pathway = target_data.get("pathway", "")
            target_biology = target_data.get("biology", "")
            target_genetic = target_data.get("genetic_validation", "")
            target_why_degrader = target_data.get("why_undruggable_before", "") or target_data.get("degrader_advantage", "")
        else:
            target_name = target_data
            target_full_name = ""
            target_pathway = ""
            target_biology = ""
            target_genetic = ""
            target_why_degrader = ""

        # Parse mechanism - could be string or dict
        if isinstance(mechanism_data, dict):
            mechanism_type = mechanism_data.get("type", "")
            mechanism_desc = mechanism_data.get("description", "")
            mechanism_diff = mechanism_data.get("differentiation", "")
        else:
            mechanism_type = ""
            mechanism_desc = mechanism_data
            mechanism_diff = ""

        # Build target detail card
        target_detail_html = ""
        if target_name:
            target_detail_html = f'''
            <div class="target-card">
                <div class="target-header">
                    <span class="target-name">{target_name}</span>
                    {f'<span class="target-full-name">({target_full_name})</span>' if target_full_name else ''}
                </div>
                {f'<div class="target-row"><strong>Pathway:</strong> {target_pathway}</div>' if target_pathway else ''}
                {f'<div class="target-row"><strong>Biology:</strong> {target_biology}</div>' if target_biology else ''}
                {f'<div class="target-row genetic"><strong>Genetic Validation:</strong> {target_genetic}</div>' if target_genetic else ''}
                {f'<div class="target-row degrader"><strong>Why Degrader:</strong> {target_why_degrader}</div>' if target_why_degrader else ''}
            </div>'''

        # Build mechanism detail
        mechanism_html = ""
        if mechanism_desc or mechanism_type:
            mechanism_html = f'''
            <div class="mechanism-card">
                <div class="mechanism-header">Mechanism of Action</div>
                {f'<div class="mechanism-type"><strong>Type:</strong> {mechanism_type}</div>' if mechanism_type else ''}
                {f'<div class="mechanism-desc">{mechanism_desc}</div>' if mechanism_desc else ''}
                {f'<div class="mechanism-diff"><strong>Differentiation:</strong> {mechanism_diff}</div>' if mechanism_diff else ''}
            </div>'''

        # Build indications list
        indications_html = ""
        if indications:
            ind_badges = "".join(f'<span class="indication-badge">{ind}</span>' for ind in indications if ind)
            indications_html = f'<div class="indications"><strong>Indications:</strong> {ind_badges}</div>'

        # Build market opportunity section
        market = asset.get("market_opportunity", {})
        market_html = ""
        if market:
            market_html = f'''
            <div class="market-section">
                <h4>Market Opportunity</h4>
                <div class="market-grid">
                    {f'<div class="market-item"><span class="label">TAM</span><span class="value">{market.get("tam")}</span></div>' if market.get("tam") else ''}
                    {f'<div class="market-item"><span class="label">Patient Population</span><span class="value">{market.get("patient_population")}</span></div>' if market.get("patient_population") else ''}
                    {f'<div class="market-item full-width"><span class="label">Current Treatment</span><span class="value">{market.get("current_treatment")}</span></div>' if market.get("current_treatment") else ''}
                    {f'<div class="market-item full-width unmet-need"><span class="label">Unmet Need</span><span class="value">{market.get("unmet_need")}</span></div>' if market.get("unmet_need") else ''}
                </div>
            </div>'''

        # Build clinical significance section (derived from target biology + market)
        clinical_sig_html = ""
        if target_biology or target_genetic or (market and market.get("unmet_need")):
            success_criteria = ""
            if stage and "Phase 2" in stage:
                success_criteria = "<li>EASI-75 response rate ≥35% vs placebo at Week 16</li><li>vIGA-AD 0/1 clear/almost clear skin</li><li>Statistically significant itch improvement (PP-NRS ≥4-point reduction)</li>"
            clinical_sig_html = f'''
            <div class="analysis-section clinical-sig">
                <h4>Clinical Significance</h4>
                <div class="analysis-content">
                    <div class="sig-item">
                        <strong>Why This Target Matters:</strong>
                        <p>{target_biology}</p>
                    </div>
                    {f'<div class="sig-item genetic-box"><strong>Human Genetic Evidence:</strong><p>{target_genetic}</p></div>' if target_genetic else ''}
                    {f'<div class="sig-item"><strong>What Clinical Success Looks Like:</strong><ul>{success_criteria}</ul></div>' if success_criteria else ''}
                    {f'<div class="sig-item"><strong>Why Now:</strong><p>{target_why_degrader}</p></div>' if target_why_degrader else ''}
                </div>
            </div>'''

        # Build key questions section
        key_questions_html = f'''
        <div class="analysis-section key-questions">
            <h4>Key Questions to Monitor</h4>
            <div class="questions-grid">
                <div class="question-item">
                    <div class="question">Can an oral degrader match injectable biologic efficacy in controlled trials?</div>
                    <div class="data-needed"><strong>Data needed:</strong> BROADEN2 Phase 2b EASI-75 results vs placebo</div>
                </div>
                <div class="question-item">
                    <div class="question">Will the safety profile differentiate from Dupixent?</div>
                    <div class="data-needed"><strong>Watch for:</strong> Conjunctivitis incidence, long-term tolerability</div>
                </div>
                <div class="question-item">
                    <div class="question">What is the dose-response relationship?</div>
                    <div class="data-needed"><strong>Key metric:</strong> Efficacy plateau vs dose, Phase 3 dose selection</div>
                </div>
            </div>
        </div>'''

        # Build trials HTML
        trials_html = ""
        for trial in trials:
            trial_name = trial.get("trial_name", "Trial")
            phase = trial.get("phase", "")
            status = trial.get("status", "")

            # Design info
            design = trial.get("design", {})
            design_str = design.get("description", design) if isinstance(design, dict) else design
            limitations = design.get("limitations", "") if isinstance(design, dict) else ""

            # Population info
            pop = trial.get("population", {})
            pop_str = pop.get("description", pop) if isinstance(pop, dict) else pop

            # Efficacy endpoints
            efficacy_html = ""
            for e in trial.get("efficacy_endpoints", []):
                defn = e.get("definition", {})
                vs_comp = e.get("vs_comparator", {})
                comp_str = ""
                if isinstance(vs_comp, dict) and vs_comp.get("comparator"):
                    comp_str = f'<div class="comparator">vs {vs_comp.get("comparator")}: {vs_comp.get("comparator_result", "")} <span class="interp">({vs_comp.get("interpretation", "")})</span></div>'

                caveats = f'<div class="caveats">{e.get("caveats", "")}</div>' if e.get("caveats") else ""

                efficacy_html += f'''
                <tr>
                    <td>
                        <span class="endpoint-name" title="{defn.get('what_it_measures', '')}">{e.get('name', '')}</span>
                        <div class="endpoint-def">{defn.get('full_name', '')}</div>
                    </td>
                    <td class="category">{e.get('category', '')}</td>
                    <td>{e.get('timepoint', '')} / {e.get('dose_group', '')}</td>
                    <td class="result">
                        <strong>{e.get('result', 'Pending')}</strong>
                        {comp_str}
                        {caveats}
                    </td>
                    <td class="source">p.{e.get('source_page', 'N/A')}</td>
                </tr>'''

            # Biomarker endpoints
            biomarker_html = ""
            for b in trial.get("biomarker_endpoints", []):
                vs_comp = f'<div class="comparator">{b.get("vs_comparator", "")}</div>' if b.get("vs_comparator") else ""
                biomarker_html += f'''
                <tr>
                    <td>
                        <span class="biomarker-name">{b.get('name', '')}</span>
                        <div class="method">{b.get('method', '')} ({b.get('tissue', '')})</div>
                    </td>
                    <td class="result"><strong>{b.get('result', '')}</strong></td>
                    <td class="interpretation">{b.get('interpretation', '')}</td>
                    <td class="significance">{b.get('clinical_significance', '')}{vs_comp}</td>
                    <td class="source">p.{b.get('source_page', 'N/A')}</td>
                </tr>'''

            # Safety
            safety = trial.get("safety", {})
            safety_html = ""
            if isinstance(safety, dict):
                aes = safety.get("aes_of_interest", {})
                ae_items = "".join(f'<span class="ae-item">{k}: {v}</span>' for k, v in aes.items()) if aes else ""
                safety_html = f'''
                <div class="safety-section">
                    <div class="safety-summary">{safety.get('summary', '')}</div>
                    <div class="safety-stats">SAEs: {safety.get('saes', 'N/A')} | Discontinuations: {safety.get('discontinuations', 'N/A')}</div>
                    <div class="aes-of-interest">{ae_items}</div>
                    <div class="safety-diff">{safety.get('differentiation', '')}</div>
                </div>'''
            elif safety:
                safety_html = f'<div class="safety-section">{safety}</div>'

            # Limitations
            limitations_list = trial.get("limitations", [])
            limitations_html = ""
            if limitations_list:
                lim_items = "".join(f'<li>{l}</li>' for l in limitations_list)
                limitations_html = f'<div class="limitations"><strong>Limitations:</strong><ul>{lim_items}</ul></div>'

            status_class = "ongoing" if status == "Ongoing" else "completed" if status == "Completed" else ""

            trials_html += f'''
            <div class="trial-card">
                <button class="collapsible trial-header">
                    <span class="trial-name">{trial_name}</span>
                    <span class="badge phase">{phase}</span>
                    <span class="badge status {status_class}">{status}</span>
                    <span class="n-enrolled">n={trial.get('n_enrolled', '?')}</span>
                </button>
                <div class="trial-content">
                    <div class="trial-meta">
                        <p><strong>Design:</strong> {design_str}</p>
                        {f'<p class="design-limitation"><strong>Limitation:</strong> {limitations}</p>' if limitations else ''}
                        <p><strong>Population:</strong> {pop_str}</p>
                    </div>

                    {f'<h4>Efficacy Endpoints</h4><table class="endpoints-table"><thead><tr><th>Endpoint</th><th>Category</th><th>Timepoint</th><th>Result</th><th>Source</th></tr></thead><tbody>{efficacy_html}</tbody></table>' if efficacy_html else ''}

                    {f'<h4>Biomarker Endpoints</h4><table class="biomarkers-table"><thead><tr><th>Biomarker</th><th>Result</th><th>Interpretation</th><th>Clinical Significance</th><th>Source</th></tr></thead><tbody>{biomarker_html}</tbody></table>' if biomarker_html else ''}

                    {safety_html}
                    {limitations_html}
                </div>
            </div>'''

        # Asset catalysts
        asset_catalysts = [c for c in catalysts if c.get("asset", "").lower() == asset_name.lower()]
        catalyst_html = ""
        for c in asset_catalysts:
            what_to_watch = "".join(f'<li>{w}</li>' for w in c.get("what_to_watch", []))
            bull_scenario = c.get("bull_scenario", {})
            bear_scenario = c.get("bear_scenario", {})

            catalyst_html += f'''
            <div class="catalyst-card">
                <div class="catalyst-header">
                    <span class="catalyst-event">{c.get('event', '')}</span>
                    <span class="catalyst-timing badge">{c.get('timing', '')}</span>
                    <span class="catalyst-importance badge {c.get('importance', '').lower()}">{c.get('importance', '')}</span>
                </div>
                {f'<div class="what-to-watch"><strong>What to watch:</strong><ul>{what_to_watch}</ul></div>' if what_to_watch else ''}
                <div class="scenarios">
                    <div class="bull-scenario">
                        <strong>Bull:</strong> {bull_scenario.get('outcome', '')}
                        <div class="rationale">{bull_scenario.get('rationale', '')}</div>
                    </div>
                    <div class="bear-scenario">
                        <strong>Bear:</strong> {bear_scenario.get('outcome', '')}
                        <div class="rationale">{bear_scenario.get('rationale', '')}</div>
                    </div>
                </div>
            </div>'''

        assets_html += f'''
        <div class="asset-section">
            <button class="collapsible asset-header">
                <span class="asset-name">{asset_name}</span>
                <span class="badge target">{target_name}</span>
                <span class="badge stage">{stage}</span>
                {f'<span class="badge modality">{short_modality}</span>' if short_modality else ''}
            </button>
            <div class="asset-content">
                <div class="asset-overview">
                    {target_detail_html}
                    {mechanism_html}
                </div>
                {indications_html}
                {market_html}
                {clinical_sig_html}
                {f'<h4>Clinical Trials</h4>{trials_html}' if trials_html else '<p class="no-data">No clinical trial data available</p>'}
                {f'<h4>Upcoming Catalysts</h4>{catalyst_html}' if catalyst_html else ''}
                {key_questions_html}
            </div>
        </div>'''

    # Build partnerships HTML
    partnerships_html = ""
    for p in partnerships:
        if isinstance(p, dict):
            partnerships_html += f'''
            <div class="partnership-card">
                <div class="partner-name">{p.get('partner', '')} - {p.get('asset', '')}</div>
                <div class="deal-terms">
                    {f'<span>Upfront: {p.get("upfront")}</span>' if p.get("upfront") else ''}
                    {f'<span>Milestones: {p.get("milestones")}</span>' if p.get("milestones") else ''}
                </div>
                <div class="strategic-value">{p.get('strategic_value', '')}</div>
            </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} - {name} | PhD Analysis</title>
    <style>
        :root {{
            --primary: #1a365d;
            --primary-light: #2c5282;
            --accent: #3182ce;
            --bull: #38a169;
            --bear: #e53e3e;
            --warning: #d69e2e;
            --bg: #f7fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text: #2d3748;
            --text-muted: #718096;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        .header h1 {{ font-size: 2rem; margin-bottom: 8px; }}
        .header .one-liner {{ opacity: 0.9; font-size: 1.1rem; margin-bottom: 16px; }}
        .header .tags {{ display: flex; gap: 8px; flex-wrap: wrap; }}

        /* Badges */
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            background: rgba(255,255,255,0.2);
        }}
        .badge.stage {{ background: var(--accent); color: white; }}
        .badge.target {{ background: var(--primary); color: white; }}
        .badge.phase {{ background: #4a5568; color: white; }}
        .badge.status {{ background: #718096; }}
        .badge.status.ongoing {{ background: var(--bull); color: white; }}
        .badge.status.completed {{ background: var(--accent); color: white; }}
        .badge.Critical, .badge.critical {{ background: var(--bear); color: white; }}
        .badge.High, .badge.high {{ background: var(--warning); color: black; }}

        /* Cards */
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .card-header {{
            padding: 16px 20px;
            font-weight: 600;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        /* Tabs */
        .tabs {{
            display: flex;
            border-bottom: 2px solid var(--border);
        }}
        .tab {{
            padding: 12px 24px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1rem;
            font-weight: 500;
            color: var(--text-muted);
            border-bottom: 2px solid transparent;
            margin-bottom: -2px;
        }}
        .tab:hover {{ color: var(--text); }}
        .tab.active {{ color: var(--primary); border-bottom-color: var(--primary); }}
        .tab.bull.active {{ color: var(--bull); border-bottom-color: var(--bull); }}
        .tab.bear.active {{ color: var(--bear); border-bottom-color: var(--bear); }}
        .tab-content {{ display: none; padding: 20px; }}
        .tab-content.active {{ display: block; }}

        /* Wall Street Research Style Tables */
        .research-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            background: white;
        }}
        .research-table th {{
            background: #f8f9fa;
            font-weight: 700;
            text-align: left;
            padding: 10px 12px;
            border: 1px solid #dee2e6;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            color: #1a1a1a;
        }}
        .research-table td {{
            padding: 10px 12px;
            border: 1px solid #dee2e6;
            vertical-align: top;
            color: #1a1a1a;
            line-height: 1.5;
        }}
        .research-table tbody tr:nth-child(even) {{
            background: #fafafa;
        }}
        .research-table .point-cell {{
            font-weight: 600;
            width: 25%;
        }}
        .research-table .conf-cell {{
            width: 100px;
            text-align: center;
            font-weight: 500;
        }}
        .research-table .debate-q {{
            font-weight: 600;
            width: 20%;
        }}
        .debates-table th:nth-child(2),
        .debates-table th:nth-child(3) {{
            width: 25%;
        }}

        /* Collapsible */
        .collapsible {{
            width: 100%;
            background: var(--card-bg);
            border: none;
            padding: 16px 20px;
            text-align: left;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: background 0.2s;
        }}
        .collapsible:hover {{ background: var(--bg); }}
        .collapsible::after {{
            content: '+';
            margin-left: auto;
            font-size: 1.2rem;
            color: var(--text-muted);
        }}
        .collapsible.active::after {{ content: '−'; }}
        .asset-content, .trial-content {{
            display: none;
            padding: 20px;
            border-top: 1px solid var(--border);
        }}
        .asset-content.show, .trial-content.show {{ display: block; }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 0.9rem;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background: var(--bg);
            font-size: 0.8rem;
            text-transform: uppercase;
            color: var(--text-muted);
        }}
        .endpoint-name {{ font-weight: 600; cursor: help; border-bottom: 1px dotted var(--text-muted); }}
        .endpoint-def {{ font-size: 0.8rem; color: var(--text-muted); }}
        .category {{ text-transform: capitalize; }}
        .result strong {{ color: var(--primary); font-size: 1.1rem; }}
        .comparator {{ font-size: 0.85rem; color: var(--text-muted); margin-top: 4px; }}
        .interp {{ font-style: italic; }}
        .caveats {{ font-size: 0.8rem; color: var(--bear); margin-top: 4px; font-style: italic; }}

        /* Safety */
        .safety-section {{
            background: #f0fff4;
            padding: 16px;
            border-radius: 8px;
            margin: 16px 0;
        }}
        .safety-summary {{ margin-bottom: 8px; }}
        .safety-stats {{ font-size: 0.9rem; color: var(--text-muted); }}
        .aes-of-interest {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 8px 0; }}
        .ae-item {{ background: white; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; }}
        .safety-diff {{ color: var(--bull); font-style: italic; }}

        /* Limitations */
        .limitations {{
            background: #fff5f5;
            padding: 12px 16px;
            border-radius: 8px;
            margin: 16px 0;
        }}
        .limitations ul {{ margin-left: 20px; }}
        .design-limitation {{ color: var(--bear); font-style: italic; }}

        /* Catalysts */
        .catalyst-card {{
            background: #fffff0;
            border-left: 4px solid var(--warning);
            padding: 16px;
            margin-bottom: 12px;
            border-radius: 0 8px 8px 0;
        }}
        .catalyst-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }}
        .catalyst-event {{ font-weight: 600; }}
        .what-to-watch ul {{ margin-left: 20px; }}
        .scenarios {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }}
        .bull-scenario {{ background: #f0fff4; padding: 12px; border-radius: 8px; }}
        .bear-scenario {{ background: #fff5f5; padding: 12px; border-radius: 8px; }}
        .rationale {{ font-size: 0.9rem; color: var(--text-muted); margin-top: 4px; }}

        /* Partnerships */
        .partnership-card {{
            padding: 16px;
            border-bottom: 1px solid var(--border);
        }}
        .partner-name {{ font-weight: 600; margin-bottom: 8px; }}
        .deal-terms {{ display: flex; gap: 16px; margin-bottom: 8px; font-size: 0.9rem; }}
        .strategic-value {{ color: var(--text-muted); font-style: italic; }}

        /* Asset sections */
        .asset-section {{
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 16px;
            overflow: hidden;
        }}
        .asset-header {{ border-radius: 12px 12px 0 0; }}
        .asset-overview {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 24px;
        }}
        @media (max-width: 768px) {{
            .asset-overview {{ grid-template-columns: 1fr; }}
        }}
        .no-data {{ color: var(--text-muted); font-style: italic; padding: 16px; }}

        /* Target card */
        .target-card {{
            background: linear-gradient(135deg, #ebf8ff, #e6fffa);
            border: 1px solid #bee3f8;
            border-radius: 12px;
            padding: 20px;
        }}
        .target-header {{
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #bee3f8;
        }}
        .target-name {{
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--primary);
        }}
        .target-full-name {{
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-left: 8px;
        }}
        .target-row {{
            margin-bottom: 12px;
            line-height: 1.5;
        }}
        .target-row strong {{
            color: var(--primary);
            display: block;
            font-size: 0.85rem;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .target-row.genetic {{
            background: #f0fff4;
            padding: 12px;
            border-radius: 8px;
            border-left: 3px solid var(--bull);
        }}
        .target-row.degrader {{
            background: #fef3c7;
            padding: 12px;
            border-radius: 8px;
            border-left: 3px solid var(--warning);
        }}

        /* Mechanism card */
        .mechanism-card {{
            background: linear-gradient(135deg, #faf5ff, #f3e8ff);
            border: 1px solid #e9d8fd;
            border-radius: 12px;
            padding: 20px;
        }}
        .mechanism-header {{
            font-size: 1rem;
            font-weight: 700;
            color: #6b46c1;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #e9d8fd;
        }}
        .mechanism-type {{
            font-size: 0.9rem;
            margin-bottom: 12px;
        }}
        .mechanism-desc {{
            line-height: 1.6;
            margin-bottom: 12px;
        }}
        .mechanism-diff {{
            background: white;
            padding: 12px;
            border-radius: 8px;
            font-size: 0.9rem;
        }}

        /* Indications */
        .indications {{
            padding: 12px 0;
            margin-bottom: 16px;
        }}
        .indication-badge {{
            display: inline-block;
            background: var(--bg);
            border: 1px solid var(--border);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            margin: 4px 4px 4px 0;
        }}

        /* Market Section */
        .market-section {{
            background: linear-gradient(135deg, #f0fff4, #e6fffa);
            border: 1px solid #9ae6b4;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
        }}
        .market-section h4 {{
            color: var(--bull);
            margin: 0 0 16px 0;
        }}
        .market-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}
        .market-item {{
            background: white;
            padding: 12px;
            border-radius: 8px;
        }}
        .market-item.full-width {{
            grid-column: 1 / -1;
        }}
        .market-item .label {{
            display: block;
            font-size: 0.8rem;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}
        .market-item .value {{
            font-weight: 500;
        }}
        .market-item.unmet-need {{
            border-left: 3px solid var(--bull);
        }}

        /* Analysis Sections */
        .analysis-section {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
        }}
        .analysis-section h4 {{
            color: var(--primary);
            margin: 0 0 16px 0;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
        }}
        .analysis-content {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .sig-item {{
            padding: 12px;
            background: var(--bg);
            border-radius: 8px;
        }}
        .sig-item strong {{
            color: var(--primary);
            display: block;
            margin-bottom: 8px;
        }}
        .sig-item p {{
            margin: 0;
            line-height: 1.6;
        }}
        .sig-item ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .sig-item li {{
            margin-bottom: 4px;
        }}
        .genetic-box {{
            background: #f0fff4;
            border-left: 4px solid var(--bull);
        }}

        /* Key Questions */
        .key-questions {{
            background: #fffbeb;
            border-color: var(--warning);
        }}
        .key-questions h4 {{
            color: #b7791f;
        }}
        .questions-grid {{
            display: grid;
            gap: 16px;
        }}
        .question-item {{
            background: white;
            padding: 16px;
            border-radius: 8px;
            border-left: 3px solid var(--warning);
        }}
        .question {{
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--text);
        }}
        .data-needed {{
            font-size: 0.9rem;
            color: var(--text-muted);
        }}

        .trial-card {{
            background: var(--bg);
            border-radius: 8px;
            margin-bottom: 12px;
            overflow: hidden;
        }}
        .trial-header {{ border-radius: 8px 8px 0 0; }}
        .trial-meta {{
            background: white;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 16px;
        }}
        .trial-meta p {{ margin-bottom: 8px; }}
        .n-enrolled {{ color: var(--text-muted); font-size: 0.9rem; }}

        h2 {{ color: var(--primary); margin: 24px 0 16px; }}
        h4 {{ color: var(--primary); margin: 16px 0 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{ticker} - {name}</h1>
            <p class="one-liner">{company.get('description', '')}</p>
            <div class="tags">
                <span class="badge">{classification.get('development_stage', '')}</span>
                <span class="badge">{classification.get('modality', '')}</span>
                <span class="badge">{classification.get('therapeutic_area', '')}</span>
                <span class="badge">{classification.get('thesis_type', '')}</span>
            </div>
        </div>

        <div class="card">
            <div class="tabs">
                <button class="tab bull active" onclick="showTab('bull')">Bull Case</button>
                <button class="tab bear" onclick="showTab('bear')">Bear Case</button>
                <button class="tab" onclick="showTab('debates')">Key Debates</button>
            </div>
            <div id="bull" class="tab-content active">{bull_html if bull_html else '<p>No bull case data</p>'}</div>
            <div id="bear" class="tab-content">{bear_html if bear_html else '<p>No bear case data</p>'}</div>
            <div id="debates" class="tab-content">{debates_html if debates_html else '<p>No debates data</p>'}</div>
        </div>

        <h2>Pipeline Assets</h2>
        {assets_html if assets_html else '<p>No asset data available</p>'}

        <h2>Partnerships</h2>
        <div class="card">
            {partnerships_html if partnerships_html else '<p>No partnership data</p>'}
        </div>
    </div>

    <script>
        // Tab switching
        function showTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            document.querySelector(`.tab[onclick="showTab('${{tabId}}')"]`).classList.add('active');
        }}

        // Collapsible sections
        document.querySelectorAll('.collapsible').forEach(btn => {{
            btn.addEventListener('click', function() {{
                this.classList.toggle('active');
                const content = this.nextElementSibling;
                content.classList.toggle('show');
            }});
        }});

        // Auto-expand first asset
        const firstAsset = document.querySelector('.asset-header');
        if (firstAsset) {{
            firstAsset.click();
            const firstTrial = document.querySelector('.trial-header');
            if (firstTrial) firstTrial.click();
        }}
    </script>
</body>
</html>'''


def _generate_targets_list_html(targets: dict) -> str:
    """Generate targets list page HTML."""
    # Sort targets by number of assets (most competitive first)
    sorted_targets = sorted(targets.items(), key=lambda x: len(x[1]["assets"]), reverse=True)

    # Stats
    total_targets = len(targets)
    multi_asset_targets = sum(1 for _, t in targets.items() if len(t["assets"]) > 1)
    total_assets = sum(len(t["assets"]) for t in targets.values())

    # Build target cards
    target_cards = ""
    for target_key, target in sorted_targets:
        target_name = target["name"]
        full_name = target.get("full_name", "")
        pathway = target.get("pathway", "")
        num_assets = len(target["assets"])
        assets = target["assets"]

        # Get unique companies
        companies = list(set(a["ticker"] for a in assets))
        companies_str = ", ".join(companies)

        # Build asset list preview
        asset_items = ""
        for a in assets[:3]:  # Show first 3
            asset_items += f'''
            <div class="asset-preview">
                <a href="/api/clinical/companies/{a['ticker']}/assets/{a['asset_slug']}/html" class="asset-link">{a['asset_name']}</a>
                <span class="asset-meta">{a['ticker']} · {a['stage']}</span>
            </div>'''
        if num_assets > 3:
            asset_items += f'<div class="more-assets">+{num_assets - 3} more</div>'

        # Determine competitive level
        if num_assets > 2:
            competitive_class = "high"
            competitive_label = "Competitive"
        elif num_assets > 1:
            competitive_class = "medium"
            competitive_label = "Emerging"
        else:
            competitive_class = "low"
            competitive_label = "Single Asset"

        target_cards += f'''
        <a href="/api/clinical/targets/{target_key}/html" class="target-card">
            <div class="target-header">
                <div class="target-name">{target_name}</div>
                <span class="badge competitive-{competitive_class}">{competitive_label}</span>
            </div>
            {f'<div class="full-name">{full_name}</div>' if full_name else ''}
            {f'<div class="pathway">{pathway}</div>' if pathway else ''}
            <div class="companies">{companies_str}</div>
            <div class="assets-preview">
                {asset_items}
            </div>
            <div class="target-footer">
                <span class="asset-count">{num_assets} asset(s)</span>
            </div>
        </a>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Targets | Clinical Data Platform</title>
    <style>
        :root {{
            --primary: #1a365d;
            --primary-light: #2c5282;
            --accent: #3182ce;
            --bull: #38a169;
            --bear: #e53e3e;
            --warning: #d69e2e;
            --bg: #f7fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text: #2d3748;
            --text-muted: #718096;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}

        .header {{
            background: linear-gradient(135deg, #553c9a, #805ad5);
            color: white;
            padding: 32px 24px;
        }}
        .header-content {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 8px;
        }}
        .header p {{
            opacity: 0.9;
        }}

        .stats {{
            display: flex;
            gap: 24px;
            margin-top: 20px;
        }}
        .stat-item {{
            background: rgba(255,255,255,0.15);
            padding: 12px 20px;
            border-radius: 8px;
        }}
        .stat-item .value {{
            font-size: 1.5rem;
            font-weight: 600;
        }}
        .stat-item .label {{
            font-size: 0.8rem;
            opacity: 0.8;
        }}

        .breadcrumb {{
            background: white;
            padding: 12px 24px;
            border-bottom: 1px solid var(--border);
            font-size: 0.9rem;
        }}
        .breadcrumb a {{
            color: var(--accent);
            text-decoration: none;
        }}
        .breadcrumb a:hover {{
            text-decoration: underline;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }}

        .targets-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }}

        .target-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            text-decoration: none;
            color: var(--text);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: all 0.2s;
            display: block;
            border: 2px solid transparent;
        }}
        .target-card:hover {{
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
            border-color: #805ad5;
            transform: translateY(-2px);
        }}

        .target-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }}
        .target-name {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #553c9a;
        }}

        .full-name {{
            font-size: 0.85rem;
            color: var(--text-muted);
            font-style: italic;
            margin-bottom: 8px;
        }}
        .pathway {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 12px;
        }}
        .companies {{
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 12px;
            color: var(--primary);
        }}

        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            text-transform: uppercase;
        }}
        .competitive-high {{
            background: #fed7d7;
            color: var(--bear);
        }}
        .competitive-medium {{
            background: #fefcbf;
            color: #975a16;
        }}
        .competitive-low {{
            background: #c6f6d5;
            color: var(--bull);
        }}

        .assets-preview {{
            margin: 12px 0;
            padding: 12px;
            background: var(--bg);
            border-radius: 8px;
        }}
        .asset-preview {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 0;
            border-bottom: 1px solid var(--border);
        }}
        .asset-preview:last-child {{
            border-bottom: none;
        }}
        .asset-link {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 500;
        }}
        .asset-link:hover {{
            text-decoration: underline;
        }}
        .asset-meta {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        .more-assets {{
            font-size: 0.85rem;
            color: var(--text-muted);
            padding-top: 8px;
        }}

        .target-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 12px;
            border-top: 1px solid var(--border);
            margin-top: 12px;
        }}
        .asset-count {{
            font-weight: 600;
            color: #553c9a;
        }}
    </style>
</head>
<body>
    <div class="breadcrumb">
        <a href="/companies">Companies</a> · <strong>Targets</strong>
    </div>

    <div class="header">
        <div class="header-content">
            <h1>Targets</h1>
            <p>Drug targets across the portfolio with competitive landscape</p>
            <div class="stats">
                <div class="stat-item">
                    <div class="value">{total_targets}</div>
                    <div class="label">Targets</div>
                </div>
                <div class="stat-item">
                    <div class="value">{multi_asset_targets}</div>
                    <div class="label">Multi-Asset</div>
                </div>
                <div class="stat-item">
                    <div class="value">{total_assets}</div>
                    <div class="label">Total Assets</div>
                </div>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="targets-grid">
            {target_cards}
        </div>
    </div>
</body>
</html>'''


def _generate_target_page_html(target: dict) -> str:
    """Generate individual target page HTML with competitive landscape."""
    target_name = target["name"]
    full_name = target.get("full_name", "")
    pathway = target.get("pathway", "")
    biology = target.get("biology", "")
    genetic = target.get("genetic_validation", "")
    why_undruggable = target.get("why_undruggable", "")
    assets = target.get("assets", [])

    # Group assets by company
    by_company = {}
    for asset in assets:
        ticker = asset["ticker"]
        if ticker not in by_company:
            by_company[ticker] = []
        by_company[ticker].append(asset)

    # Build competitive landscape table
    landscape_rows = ""
    for asset in sorted(assets, key=lambda x: x.get("stage", "")):
        mechanism = asset.get("mechanism_type", "")
        diff = asset.get("mechanism_differentiation", "")
        stage = asset.get("stage", "")
        indication = asset.get("lead_indication", "")
        ownership = asset.get("ownership", "")

        stage_class = ""
        if "Approved" in stage:
            stage_class = "approved"
        elif "Phase 3" in stage or "NDA" in stage:
            stage_class = "late"
        elif "Phase 2" in stage:
            stage_class = "mid"
        elif "Phase 1" in stage:
            stage_class = "early"

        landscape_rows += f'''
        <tr>
            <td>
                <a href="/api/clinical/companies/{asset['ticker']}/assets/{asset['asset_slug']}/html" class="asset-link">{asset['asset_name']}</a>
            </td>
            <td>
                <a href="/api/clinical/companies/{asset['ticker']}/html" class="company-link">{asset['ticker']}</a>
            </td>
            <td><span class="badge stage-{stage_class}">{stage}</span></td>
            <td>{mechanism}</td>
            <td>{indication}</td>
            <td>{ownership}</td>
        </tr>'''

    # Build company summary cards
    company_cards = ""
    for ticker, company_assets in by_company.items():
        asset_links = " · ".join(
            f'<a href="/api/clinical/companies/{ticker}/assets/{a["asset_slug"]}/html">{a["asset_name"]}</a>'
            for a in company_assets
        )
        stages = ", ".join(set(a.get("stage", "") for a in company_assets if a.get("stage")))

        company_cards += f'''
        <div class="company-card">
            <div class="company-header">
                <a href="/api/clinical/companies/{ticker}/html" class="ticker">{ticker}</a>
                <span class="asset-count">{len(company_assets)} asset(s)</span>
            </div>
            <div class="company-assets">{asset_links}</div>
            <div class="company-stages">{stages}</div>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{target_name} | Target Analysis</title>
    <style>
        :root {{
            --primary: #553c9a;
            --primary-light: #805ad5;
            --accent: #3182ce;
            --bull: #38a169;
            --bear: #e53e3e;
            --warning: #d69e2e;
            --bg: #f7fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text: #2d3748;
            --text-muted: #718096;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}

        .sticky-header {{
            position: sticky;
            top: 0;
            background: white;
            border-bottom: 1px solid var(--border);
            z-index: 100;
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .breadcrumb {{
            font-size: 0.9rem;
        }}
        .breadcrumb a {{
            color: var(--accent);
            text-decoration: none;
        }}
        .breadcrumb a:hover {{
            text-decoration: underline;
        }}
        .breadcrumb span {{
            color: var(--text-muted);
            margin: 0 8px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
        }}

        .target-header {{
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            color: white;
            padding: 32px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        .target-header h1 {{
            font-size: 2rem;
            margin-bottom: 8px;
        }}
        .target-header .full-name {{
            font-size: 1.1rem;
            opacity: 0.9;
            font-style: italic;
            margin-bottom: 12px;
        }}
        .target-header .pathway {{
            opacity: 0.85;
            font-size: 0.95rem;
        }}
        .target-header .stats {{
            display: flex;
            gap: 24px;
            margin-top: 20px;
        }}
        .target-header .stat {{
            background: rgba(255,255,255,0.15);
            padding: 12px 20px;
            border-radius: 8px;
        }}
        .target-header .stat .value {{
            font-size: 1.5rem;
            font-weight: 600;
        }}
        .target-header .stat .label {{
            font-size: 0.8rem;
            opacity: 0.8;
        }}

        .section {{
            margin-bottom: 32px;
        }}
        .section-header {{
            font-size: 1.25rem;
            color: var(--primary);
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--border);
        }}

        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            padding: 24px;
            margin-bottom: 20px;
        }}

        .biology-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }}
        @media (max-width: 768px) {{
            .biology-section {{ grid-template-columns: 1fr; }}
        }}

        .biology-card {{
            background: linear-gradient(135deg, #ebf8ff, #e6fffa);
            border: 1px solid #bee3f8;
            padding: 20px;
            border-radius: 12px;
        }}
        .biology-card h3 {{
            color: var(--accent);
            margin-bottom: 12px;
            font-size: 1rem;
        }}
        .biology-card p {{
            font-size: 0.95rem;
            line-height: 1.6;
        }}

        .genetic-card {{
            background: linear-gradient(135deg, #f0fff4, #c6f6d5);
            border: 1px solid #9ae6b4;
            padding: 20px;
            border-radius: 12px;
        }}
        .genetic-card h3 {{
            color: var(--bull);
            margin-bottom: 12px;
            font-size: 1rem;
        }}

        .undruggable-card {{
            background: linear-gradient(135deg, #faf5ff, #e9d8fd);
            border: 1px solid #d6bcfa;
            padding: 20px;
            border-radius: 12px;
            grid-column: 1 / -1;
        }}
        .undruggable-card h3 {{
            color: #6b46c1;
            margin-bottom: 12px;
            font-size: 1rem;
        }}

        .landscape-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .landscape-table th, .landscape-table td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        .landscape-table th {{
            background: var(--bg);
            font-size: 0.8rem;
            text-transform: uppercase;
            color: var(--text-muted);
        }}
        .landscape-table tr:hover {{
            background: #fafafa;
        }}
        .asset-link {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 600;
        }}
        .asset-link:hover {{
            text-decoration: underline;
        }}
        .company-link {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
        }}
        .company-link:hover {{
            text-decoration: underline;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
        }}
        .stage-approved {{
            background: #c6f6d5;
            color: var(--bull);
        }}
        .stage-late {{
            background: #bee3f8;
            color: var(--accent);
        }}
        .stage-mid {{
            background: #fefcbf;
            color: #975a16;
        }}
        .stage-early {{
            background: #e2e8f0;
            color: var(--text-muted);
        }}

        .companies-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }}
        .company-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
        }}
        .company-card .company-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .company-card .ticker {{
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--primary);
            text-decoration: none;
        }}
        .company-card .ticker:hover {{
            text-decoration: underline;
        }}
        .company-card .asset-count {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        .company-card .company-assets {{
            font-size: 0.9rem;
            margin-bottom: 8px;
        }}
        .company-card .company-assets a {{
            color: var(--accent);
            text-decoration: none;
        }}
        .company-card .company-assets a:hover {{
            text-decoration: underline;
        }}
        .company-card .company-stages {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}

        .back-link {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: var(--accent);
            text-decoration: none;
            font-size: 0.9rem;
            margin-bottom: 16px;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="sticky-header">
        <div class="breadcrumb">
            <a href="/companies">Companies</a>
            <span>·</span>
            <a href="/api/clinical/targets/html">Targets</a>
            <span>›</span>
            <strong>{target_name}</strong>
        </div>
    </div>

    <div class="container">
        <div class="target-header">
            <h1>{target_name}</h1>
            {f'<div class="full-name">{full_name}</div>' if full_name else ''}
            {f'<div class="pathway">{pathway}</div>' if pathway else ''}
            <div class="stats">
                <div class="stat">
                    <div class="value">{len(assets)}</div>
                    <div class="label">Assets</div>
                </div>
                <div class="stat">
                    <div class="value">{len(by_company)}</div>
                    <div class="label">Companies</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-header">Target Biology</h2>
            <div class="biology-section">
                {f'<div class="biology-card"><h3>Biology</h3><p>{biology}</p></div>' if biology else ''}
                {f'<div class="genetic-card"><h3>Human Genetic Validation</h3><p>{genetic}</p></div>' if genetic else ''}
                {f'<div class="undruggable-card"><h3>Why Previously Undruggable</h3><p>{why_undruggable}</p></div>' if why_undruggable else ''}
            </div>
        </div>

        <div class="section">
            <h2 class="section-header">Competitive Landscape</h2>
            <div class="card">
                <table class="landscape-table">
                    <thead>
                        <tr>
                            <th>Asset</th>
                            <th>Company</th>
                            <th>Stage</th>
                            <th>Mechanism</th>
                            <th>Lead Indication</th>
                            <th>Ownership</th>
                        </tr>
                    </thead>
                    <tbody>
                        {landscape_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <h2 class="section-header">Companies</h2>
            <div class="companies-grid">
                {company_cards}
            </div>
        </div>

        <a href="/api/clinical/targets/html" class="back-link">← Back to All Targets</a>
    </div>
</body>
</html>'''
