"""Clinical data API router - data-driven from JSON files."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

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

    # Build pipeline table rows
    pipeline_rows = ""
    for asset in assets:
        asset_name = asset.get("name", "Unknown")
        asset_slug = asset_name.lower().replace("-", "").replace(" ", "_")
        target = asset.get("target", {})
        target_name = target.get("name", target) if isinstance(target, dict) else target
        stage = asset.get("stage", "")
        lead_ind = asset.get("lead_indication") or (asset.get("indications", [""])[0] if asset.get("indications") else "")

        # Find next catalyst for this asset
        next_catalyst = ""
        for c in catalysts:
            if c.get("asset", "").lower() == asset_name.lower():
                next_catalyst = f"{c.get('event', '')} ({c.get('timing', '')})"
                break

        target_key = str(target_name).upper().replace(" ", "_") if target_name else ""
        pipeline_rows += f'''
        <tr>
            <td><a href="/api/clinical/companies/{ticker}/assets/{asset_slug}/html" class="asset-link">{asset_name}</a></td>
            <td><a href="/api/clinical/targets/{target_key}/html" class="target-link">{target_name}</a></td>
            <td><span class="badge stage">{stage}</span></td>
            <td>{lead_ind}</td>
            <td class="catalyst-cell">{next_catalyst or '<span class="no-data">—</span>'}</td>
        </tr>'''

    # Build bull/bear HTML
    bull_case = thesis.get("bull_case", []) if isinstance(thesis, dict) else thesis
    bear_case = thesis.get("bear_case", []) if isinstance(thesis, dict) else []

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

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} - {name} | Company Overview</title>
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

        /* Header */
        .header {{
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            color: white;
            padding: 32px;
            border-radius: 12px;
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

        /* Tags */
        .tags {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            background: rgba(255,255,255,0.2);
        }}
        .badge.stage {{
            background: var(--accent);
            color: white;
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
            border-radius: 8px;
        }}
        .thesis-column.bull {{
            background: #f0fff4;
            border: 1px solid #9ae6b4;
        }}
        .thesis-column.bear {{
            background: #fff5f5;
            border: 1px solid #feb2b2;
        }}
        .thesis-column h3 {{
            font-size: 1rem;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .thesis-column.bull h3 {{ color: var(--bull); }}
        .thesis-column.bear h3 {{ color: var(--bear); }}
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
        .thesis-column.bull li::before {{ color: var(--bull); }}
        .thesis-column.bear li::before {{ color: var(--bear); }}
        .thesis-column li strong {{
            display: block;
            margin-bottom: 4px;
        }}
        .thesis-column .evidence {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}

        /* Pipeline Table */
        .pipeline-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .pipeline-table th, .pipeline-table td {{
            padding: 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        .pipeline-table th {{
            background: var(--bg);
            font-size: 0.8rem;
            text-transform: uppercase;
            color: var(--text-muted);
            font-weight: 600;
        }}
        .pipeline-table tr:hover {{
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
        <a href="/api/clinical/companies">Companies</a>
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
                    <span class="badge">{classification.get('development_stage', '')}</span>
                    <span class="badge">{classification.get('modality', '')}</span>
                    <span class="badge">{classification.get('therapeutic_area', '')}</span>
                </div>
            </div>
            <p class="description">{company.get('description', '')}</p>
            <div class="snapshot">
                <div class="snapshot-item">
                    <div class="label">Market Cap</div>
                    <div class="value">${data.get('market_cap_mm', 'N/A')}M</div>
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
            <div class="card-header">Investment Thesis</div>
            <div class="card-content">
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
    company_name = company_data.get("name", "")
    asset_name = asset.get("name", "Unknown")
    target_data = asset.get("target", {})
    mechanism_data = asset.get("mechanism", {})
    stage = asset.get("stage", "")
    modality = asset.get("modality", "")
    indications_data = asset.get("indications", {})
    market = asset.get("market_opportunity", {})
    clinical_data = asset.get("clinical_data", {})
    investment_analysis = asset.get("investment_analysis", {})

    # Get catalysts from both company and asset level
    company_catalysts = company_data.get("catalysts", [])
    asset_catalysts_list = asset.get("catalysts", [])
    asset_catalysts = asset_catalysts_list + [c for c in company_catalysts if c.get("asset", "").lower() == asset_name.lower()]

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
        target_name = target_data.get("name", "")
        target_full = target_data.get("full_name", "")
        target_pathway = target_data.get("pathway", "")

        # v2.0 has nested biology object
        biology_data = target_data.get("biology", "")
        if isinstance(biology_data, dict):
            target_biology = biology_data.get("simple_explanation", "") or biology_data.get("pathway_detail", "")
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
        target_name = target_data
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
            source = endpoint_data.get("source_slide", "N/A")

            # Get main result
            main_result = results.get("mean_change_overall_day29", "") or results.get("mean_change_overall", "") or results.get("responders_overall", "")
            vs_dup = results.get("vs_dupilumab", "") or results.get("vs_dupilumab_day28_ph3", "") or results.get("vs_dupilumab_week16", "")

            rows += f'''
            <tr>
                <td>
                    <div class="endpoint-name">{name}</div>
                    <div class="endpoint-def">{what_measures}</div>
                </td>
                <td class="result"><strong>{main_result}</strong></td>
                <td class="comparator">{"vs Dupilumab: " + vs_dup if vs_dup else ""}</td>
                <td class="source">Slide {source}</td>
            </tr>'''

        if rows:
            return f'''
            <div class="endpoints-section">
                <h5>Efficacy Endpoints</h5>
                <table class="data-table">
                    <thead><tr><th>Endpoint</th><th>Result</th><th>vs Comparator</th><th>Source</th></tr></thead>
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

        return f'''
        <div class="biomarkers-section">
            <h5>Biomarker Results</h5>
            <table class="data-table">
                <thead><tr><th>Biomarker</th><th>Result</th><th>vs Dupilumab</th><th>Interpretation</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>'''

    def build_safety_html(safety: dict) -> str:
        """Build safety section from v2.0 format"""
        if not isinstance(safety, dict):
            return ""
        summary = safety.get("summary", "")
        key_findings = safety.get("key_findings", [])
        conj_comp = safety.get("conjunctivitis_comparison", {})

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
                <h5>Safety Profile</h5>
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
        sad_n = design.get("sad_n", "") if isinstance(design, dict) else ""
        mad_n = design.get("mad_n", "") if isinstance(design, dict) else ""

        # STAT6 degradation data
        stat6_deg = phase1_hv.get("stat6_degradation", {})
        deg_results = stat6_deg.get("results_by_dose", [])
        key_findings = stat6_deg.get("key_findings", [])

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
                <span class="n-enrolled">n={sad_n} SAD + {mad_n} MAD</span>
            </div>
            <div class="trial-meta">
                <p><strong>Design:</strong> {design_type}</p>
                <p><strong>Population:</strong> {population}</p>
            </div>
            <div class="endpoints-section">
                <h5>STAT6 Degradation by Dose</h5>
                <table class="data-table">
                    <thead><tr><th>Dose</th><th>Blood Change</th><th>Skin Change</th><th>N</th></tr></thead>
                    <tbody>{deg_rows}</tbody>
                </table>
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

        # Head-to-head comparison table
        h2h_data = phase1b_ad.get("head_to_head_comparison_table", {})
        h2h_rows = ""
        if isinstance(h2h_data, dict):
            h2h_list = h2h_data.get("data", [])
            caveat = h2h_data.get("caveat", "")
            for row in h2h_list:
                endpoint = row.get("endpoint", "")
                kt621 = row.get("kt621_day29", "")
                dup = row.get("dupilumab_day28", "")
                winner = row.get("winner", "")
                winner_class = "winner-kt621" if winner == "KT-621" else "winner-tie" if winner == "Tie" else ""
                h2h_rows += f'''
                <tr class="{winner_class}">
                    <td>{endpoint}</td>
                    <td class="result"><strong>{kt621}</strong></td>
                    <td>{dup}</td>
                    <td class="winner">{winner}</td>
                </tr>'''

            if h2h_rows:
                head_to_head_html = f'''
                <div class="h2h-section">
                    <h5>Head-to-Head Comparison: KT-621 vs Dupilumab</h5>
                    <p class="caveat">{caveat}</p>
                    <table class="data-table h2h-table">
                        <thead><tr><th>Endpoint</th><th>KT-621 Day 29</th><th>Dupilumab Day 28</th><th>Winner</th></tr></thead>
                        <tbody>{h2h_rows}</tbody>
                    </table>
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
            {efficacy_html}
            {head_to_head_html}
            {biomarkers_html}
            {safety_html}
        </div>'''

    # Build ongoing trials section
    for trial in ongoing_trials:
        trial_name = trial.get("trial_name", "Trial")
        phase = trial.get("phase", "")
        indication = trial.get("indication", "")
        status = trial.get("status", "Ongoing")
        data_expected = trial.get("data_expected", "")

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
                <h4>{trial_name}</h4>
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

    # Fallback to v1.0 trials format
    for trial in trials_v1:
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
    # BUILD INVESTMENT ANALYSIS HTML
    # =======================================================================
    investment_html = ""
    if investment_analysis:
        bull_case = investment_analysis.get("bull_case", [])
        bear_case = investment_analysis.get("bear_case", [])
        key_debates = investment_analysis.get("key_debates", [])
        pos = investment_analysis.get("probability_of_success", {})

        bull_html = ""
        for item in bull_case:
            if isinstance(item, dict):
                conf = item.get("confidence", "medium").lower()
                bull_html += f'''
                <div class="thesis-item bull">
                    <div class="thesis-point">{item.get('point', '')}</div>
                    <div class="thesis-evidence"><strong>Evidence:</strong> {item.get('evidence', '')}</div>
                    <div class="thesis-meta">
                        <span class="confidence {conf}">{conf.title()} confidence</span>
                        <span class="source">Slide {item.get('source_slide', 'N/A')}</span>
                    </div>
                </div>'''
            else:
                bull_html += f'<div class="thesis-item bull">{item}</div>'

        bear_html = ""
        for item in bear_case:
            if isinstance(item, dict):
                counter = item.get("counter_argument", "")
                prob = item.get("probability", "")
                bear_html += f'''
                <div class="thesis-item bear">
                    <div class="thesis-point">{item.get('point', '')}</div>
                    <div class="thesis-evidence"><strong>Evidence:</strong> {item.get('evidence', '')}</div>
                    {f'<div class="thesis-counter"><strong>Counter:</strong> {counter}</div>' if counter else ''}
                    {f'<div class="probability">Probability: {prob}</div>' if prob else ''}
                </div>'''
            else:
                bear_html += f'<div class="thesis-item bear">{item}</div>'

        debates_html = ""
        for debate in key_debates:
            if isinstance(debate, dict):
                debates_html += f'''
                <div class="debate-item">
                    <div class="debate-question">{debate.get('question', '')}</div>
                    <div class="debate-views">
                        <div class="bull-view"><strong>Bull:</strong> {debate.get('bull_view', '')}</div>
                        <div class="bear-view"><strong>Bear:</strong> {debate.get('bear_view', '')}</div>
                    </div>
                    <div class="data-to-watch"><strong>What resolves it:</strong> {debate.get('what_resolves_it', '')}</div>
                </div>'''

        pos_html = ""
        if pos:
            pos_html = f'''
            <div class="pos-box">
                <h5>Probability of Success</h5>
                <div class="pos-grid">
                    <div class="pos-item"><span class="label">Phase 2b→3:</span> <strong>{pos.get('phase2b_to_phase3', 'N/A')}</strong></div>
                    <div class="pos-item"><span class="label">Phase 3→Approval:</span> <strong>{pos.get('phase3_to_approval', 'N/A')}</strong></div>
                    <div class="pos-item highlight"><span class="label">Cumulative PoS:</span> <strong>{pos.get('cumulative_pos', 'N/A')}</strong></div>
                </div>
                <p class="methodology">{pos.get('methodology', '')}</p>
            </div>'''

        investment_html = f'''
        <section id="investment" class="section">
            <h2 class="section-header">Investment Analysis</h2>
            <div class="investment-grid">
                <div class="bull-section">
                    <h4 class="bull-header">Bull Case</h4>
                    {bull_html}
                </div>
                <div class="bear-section">
                    <h4 class="bear-header">Bear Case</h4>
                    {bear_html}
                </div>
            </div>
            {f'<div class="debates-section"><h4>Key Debates</h4>{debates_html}</div>' if debates_html else ''}
            {pos_html}
        </section>'''

    # =======================================================================
    # BUILD CATALYSTS HTML
    # =======================================================================
    catalysts_html = ""
    for c in asset_catalysts:
        what_to_watch = c.get("what_to_watch", [])
        if isinstance(what_to_watch, list):
            watch_items = "".join(f'<li>{w}</li>' for w in what_to_watch)
        else:
            watch_items = f'<li>{what_to_watch}</li>'
        bull = c.get("bull_scenario", {})
        bear = c.get("bear_scenario", {})
        consensus = c.get("consensus_expectation", "")

        catalysts_html += f'''
        <div class="catalyst-card">
            <div class="catalyst-header">
                <h4>{c.get('event', '')}</h4>
                <span class="badge timing">{c.get('timing', '')}</span>
                <span class="badge importance {c.get('importance', '').lower()}">{c.get('importance', '')}</span>
            </div>
            {f'<div class="watch-list"><strong>What to watch:</strong><ul>{watch_items}</ul></div>' if watch_items else ''}
            <div class="scenarios-grid">
                <div class="scenario bull">
                    <strong>Bull Scenario</strong>
                    <p>{bull.get('outcome', '') if isinstance(bull, dict) else ''}</p>
                    <span class="impact">Stock impact: {bull.get('stock_impact', '') if isinstance(bull, dict) else ''}</span>
                    <span class="rationale">{bull.get('rationale', '') if isinstance(bull, dict) else ''}</span>
                </div>
                <div class="scenario bear">
                    <strong>Bear Scenario</strong>
                    <p>{bear.get('outcome', '') if isinstance(bear, dict) else ''}</p>
                    <span class="impact">Stock impact: {bear.get('stock_impact', '') if isinstance(bear, dict) else ''}</span>
                    <span class="rationale">{bear.get('rationale', '') if isinstance(bear, dict) else ''}</span>
                </div>
            </div>
            {f'<div class="consensus"><strong>Consensus:</strong> {consensus}</div>' if consensus else ''}
        </div>'''

    # Indications badges
    ind_badges = "".join(f'<span class="indication-badge">{ind}</span>' for ind in indications if ind)

    # Prev/Next navigation
    prev_slug = prev_asset.get("name", "").lower().replace("-", "").replace(" ", "_") if prev_asset else ""
    next_slug = next_asset.get("name", "").lower().replace("-", "").replace(" ", "_") if next_asset else ""
    prev_name = prev_asset.get("name", "") if prev_asset else ""
    next_name = next_asset.get("name", "") if next_asset else ""

    # Extract peak sales estimates (can't use {} in f-strings)
    peak_sales = market.get("peak_sales_estimate", {}) if isinstance(market.get("peak_sales_estimate"), dict) else {}
    peak_bull = peak_sales.get("bull_case", "") if peak_sales else ""
    peak_base = peak_sales.get("base_case", "") if peak_sales else ""

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{asset_name} - {ticker} | Asset Analysis</title>
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
            --sidebar-width: 220px;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}

        /* Sticky Header */
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
        .breadcrumb strong {{
            color: var(--primary);
        }}
        .header-badges {{
            display: flex;
            gap: 8px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            background: var(--bg);
            border: 1px solid var(--border);
        }}
        .badge.ongoing {{ background: #c6f6d5; color: var(--bull); border-color: #9ae6b4; }}
        .badge.completed {{ background: #bee3f8; color: var(--accent); border-color: #90cdf4; }}
        .badge.timing {{ background: #fefcbf; color: #975a16; border-color: #f6e05e; }}
        .badge.importance.critical {{ background: #fed7d7; color: var(--bear); }}
        .badge.importance.high {{ background: #fefcbf; color: #975a16; }}
        .badge-link {{
            text-decoration: none;
        }}
        .badge-link:hover .badge {{
            background: #e9d8fd;
            border-color: #805ad5;
        }}

        /* Layout */
        .layout {{
            display: flex;
            max-width: 1400px;
            margin: 0 auto;
        }}

        /* Sidebar */
        .sidebar {{
            width: var(--sidebar-width);
            padding: 24px 16px;
            position: sticky;
            top: 60px;
            height: calc(100vh - 60px);
            overflow-y: auto;
            border-right: 1px solid var(--border);
            background: white;
        }}
        .sidebar h3 {{
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 12px;
            padding-left: 12px;
        }}
        .sidebar-nav {{
            list-style: none;
        }}
        .sidebar-nav a {{
            display: block;
            padding: 8px 12px;
            color: var(--text);
            text-decoration: none;
            border-radius: 6px;
            font-size: 0.9rem;
            margin-bottom: 2px;
        }}
        .sidebar-nav a:hover {{
            background: var(--bg);
        }}
        .sidebar-nav a.active {{
            background: var(--accent);
            color: white;
        }}

        /* Main Content */
        .main {{
            flex: 1;
            padding: 24px 32px;
            max-width: calc(100% - var(--sidebar-width));
        }}

        /* Sections */
        .section {{
            margin-bottom: 48px;
            scroll-margin-top: 80px;
        }}
        .section-header {{
            font-size: 1.5rem;
            color: var(--primary);
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--border);
        }}

        /* Asset Header */
        .asset-header {{
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            color: white;
            padding: 32px;
            border-radius: 12px;
            margin-bottom: 32px;
        }}
        .asset-header h1 {{
            font-size: 2rem;
            margin-bottom: 8px;
        }}
        .asset-header .subtitle {{
            opacity: 0.9;
            font-size: 1.1rem;
        }}
        .asset-header .tags {{
            margin-top: 16px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .asset-header .badge {{
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
        }}

        /* Cards */
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 24px;
            overflow: hidden;
        }}
        .card-content {{
            padding: 24px;
        }}

        /* Target/Mechanism Grid */
        .overview-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }}
        @media (max-width: 900px) {{
            .overview-grid {{ grid-template-columns: 1fr; }}
        }}
        .overview-card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid var(--border);
        }}
        .overview-card.target {{
            background: linear-gradient(135deg, #ebf8ff, #e6fffa);
            border-color: #bee3f8;
        }}
        .overview-card.mechanism {{
            background: linear-gradient(135deg, #faf5ff, #f3e8ff);
            border-color: #e9d8fd;
        }}
        .overview-card h3 {{
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }}
        .overview-card.target h3 {{ color: var(--accent); }}
        .overview-card.mechanism h3 {{ color: #6b46c1; }}
        .detail-row {{
            margin-bottom: 12px;
        }}
        .detail-row strong {{
            display: block;
            font-size: 0.8rem;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}
        .genetic-highlight {{
            background: #f0fff4;
            border-left: 3px solid var(--bull);
            padding: 12px;
            border-radius: 0 8px 8px 0;
            margin-top: 16px;
        }}

        /* Market */
        .market-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
        }}
        .market-item {{
            background: var(--bg);
            padding: 16px;
            border-radius: 8px;
        }}
        .market-item.full {{ grid-column: 1 / -1; }}
        .market-item.highlight {{
            background: #f0fff4;
            border-left: 3px solid var(--bull);
        }}
        .market-item .label {{
            font-size: 0.8rem;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}
        .market-item .value {{
            font-weight: 500;
        }}

        /* Indications */
        .indications {{
            margin-bottom: 24px;
        }}
        .indication-badge {{
            display: inline-block;
            background: var(--bg);
            border: 1px solid var(--border);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            margin: 4px 4px 4px 0;
        }}

        /* Trials */
        .trial-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }}
        .trial-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}
        .trial-header h4 {{
            margin: 0;
            color: var(--primary);
        }}
        .n-enrolled {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        .trial-meta {{
            background: var(--bg);
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .trial-meta p {{
            margin-bottom: 8px;
        }}
        .trial-meta p:last-child {{
            margin-bottom: 0;
        }}
        .limitation-text {{
            color: var(--bear);
            font-style: italic;
        }}

        /* Data Tables */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 0.9rem;
        }}
        .data-table th, .data-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        .data-table th {{
            background: var(--bg);
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--text-muted);
        }}
        .endpoint-name, .biomarker-name {{
            font-weight: 600;
        }}
        .endpoint-def, .method {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        .result strong {{
            color: var(--primary);
            font-size: 1.1rem;
        }}
        .comparator {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        .source {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}

        /* Safety */
        .safety-box {{
            background: #f0fff4;
            border: 1px solid #9ae6b4;
            padding: 16px;
            border-radius: 8px;
            margin: 16px 0;
        }}
        .safety-box h5 {{
            color: var(--bull);
            margin-bottom: 8px;
        }}
        .ae-badges {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 12px;
        }}
        .ae-badge {{
            background: white;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.85rem;
        }}
        .safety-diff {{
            margin-top: 12px;
            font-style: italic;
            color: var(--bull);
        }}

        /* Limitations */
        .limitations-box {{
            background: #fff5f5;
            border-left: 3px solid var(--bear);
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            font-size: 0.9rem;
            color: var(--bear);
        }}

        /* Catalysts */
        .catalyst-card {{
            background: #fffbeb;
            border: 1px solid #f6e05e;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }}
        .catalyst-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}
        .catalyst-header h4 {{
            margin: 0;
            color: #975a16;
        }}
        .watch-list {{
            margin-bottom: 16px;
        }}
        .watch-list ul {{
            margin: 8px 0 0 20px;
        }}
        .scenarios-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }}
        .scenario {{
            padding: 16px;
            border-radius: 8px;
        }}
        .scenario.bull {{
            background: #f0fff4;
        }}
        .scenario.bear {{
            background: #fff5f5;
        }}
        .scenario strong {{
            display: block;
            margin-bottom: 8px;
        }}
        .scenario.bull strong {{ color: var(--bull); }}
        .scenario.bear strong {{ color: var(--bear); }}
        .scenario .rationale {{
            display: block;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 8px;
        }}

        /* Navigation */
        .asset-nav {{
            display: flex;
            justify-content: space-between;
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid var(--border);
        }}
        .nav-link {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px 20px;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            text-decoration: none;
            color: var(--text);
        }}
        .nav-link:hover {{
            border-color: var(--accent);
            color: var(--accent);
        }}
        .nav-link.disabled {{
            opacity: 0.5;
            pointer-events: none;
        }}

        h5 {{
            color: var(--primary);
            margin-bottom: 12px;
        }}

        /* v2.0 Schema: Head-to-Head Comparison Table */
        .h2h-section {{
            margin: 24px 0;
            padding: 20px;
            background: #f0fff4;
            border-radius: 12px;
            border: 1px solid #9ae6b4;
        }}
        .h2h-section h5 {{
            color: var(--bull);
            margin-bottom: 8px;
        }}
        .h2h-section .caveat {{
            font-size: 0.85rem;
            color: var(--text-muted);
            font-style: italic;
            margin-bottom: 16px;
        }}
        .h2h-table .winner-kt621 {{
            background: #f0fff4;
        }}
        .h2h-table .winner {{
            font-weight: 600;
            color: var(--bull);
        }}
        .h2h-table .winner-tie .winner {{
            color: var(--text-muted);
        }}

        /* v2.0 Schema: Investment Analysis */
        .investment-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }}
        @media (max-width: 900px) {{
            .investment-grid {{ grid-template-columns: 1fr; }}
        }}
        .bull-section, .bear-section {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid var(--border);
        }}
        .bull-section {{
            border-left: 4px solid var(--bull);
        }}
        .bear-section {{
            border-left: 4px solid var(--bear);
        }}
        .bull-header {{ color: var(--bull); margin-bottom: 16px; }}
        .bear-header {{ color: var(--bear); margin-bottom: 16px; }}
        .thesis-item {{
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 12px;
        }}
        .thesis-item.bull {{
            background: #f0fff4;
        }}
        .thesis-item.bear {{
            background: #fff5f5;
        }}
        .thesis-point {{
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .thesis-evidence {{
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}
        .thesis-counter {{
            font-size: 0.9rem;
            padding: 8px;
            background: white;
            border-radius: 4px;
            margin-bottom: 8px;
        }}
        .thesis-meta {{
            display: flex;
            gap: 12px;
            font-size: 0.8rem;
        }}
        .confidence {{
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .confidence.high {{ background: #c6f6d5; color: var(--bull); }}
        .confidence.medium {{ background: #fefcbf; color: #975a16; }}
        .confidence.low {{ background: #fed7d7; color: var(--bear); }}
        .probability {{
            font-size: 0.85rem;
            color: var(--bear);
            font-weight: 600;
        }}
        .debates-section {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
        }}
        .debates-section h4 {{
            color: var(--primary);
            margin-bottom: 16px;
        }}
        .debate-item {{
            background: var(--bg);
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 12px;
        }}
        .debate-question {{
            font-weight: 600;
            font-size: 1.1rem;
            margin-bottom: 12px;
            color: var(--primary);
        }}
        .debate-views {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 12px;
        }}
        .bull-view {{
            background: #f0fff4;
            padding: 12px;
            border-radius: 6px;
            font-size: 0.9rem;
        }}
        .bear-view {{
            background: #fff5f5;
            padding: 12px;
            border-radius: 6px;
            font-size: 0.9rem;
        }}
        .data-to-watch {{
            font-size: 0.9rem;
            color: var(--text-muted);
            padding: 8px;
            background: white;
            border-radius: 4px;
        }}
        .pos-box {{
            background: linear-gradient(135deg, #ebf8ff, #e6fffa);
            border: 1px solid #bee3f8;
            border-radius: 12px;
            padding: 24px;
        }}
        .pos-box h5 {{
            color: var(--accent);
            margin-bottom: 16px;
        }}
        .pos-grid {{
            display: flex;
            gap: 24px;
            margin-bottom: 12px;
        }}
        .pos-item {{
            background: white;
            padding: 12px 16px;
            border-radius: 8px;
        }}
        .pos-item.highlight {{
            background: #c6f6d5;
        }}
        .pos-item .label {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        .methodology {{
            font-size: 0.85rem;
            color: var(--text-muted);
            font-style: italic;
        }}

        /* v2.0 Schema: Trial Cards */
        .trial-card.featured {{
            border: 2px solid var(--accent);
            box-shadow: 0 4px 12px rgba(49, 130, 206, 0.15);
        }}
        .trial-card.ongoing {{
            border-left: 4px solid var(--warning);
        }}
        .key-findings {{
            background: #ebf8ff;
            padding: 16px;
            border-radius: 8px;
            margin: 16px 0;
        }}
        .key-findings ul {{
            margin: 8px 0 0 20px;
        }}
        .findings-list {{
            margin: 12px 0 0 20px;
        }}
        .success-criteria, .failure-criteria {{
            padding: 16px;
            border-radius: 8px;
            margin: 12px 0;
        }}
        .success-criteria {{
            background: #f0fff4;
            border-left: 3px solid var(--bull);
        }}
        .failure-criteria {{
            background: #fff5f5;
            border-left: 3px solid var(--bear);
        }}
        .success-criteria ul, .failure-criteria ul {{
            margin: 8px 0 0 20px;
        }}

        /* Catalyst enhancements */
        .consensus {{
            margin-top: 16px;
            padding: 12px;
            background: rgba(255,255,255,0.5);
            border-radius: 8px;
            font-size: 0.9rem;
        }}
        .impact {{
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 4px;
        }}
        .scenario.bull .impact {{ color: var(--bull); }}
        .scenario.bear .impact {{ color: var(--bear); }}
    </style>
</head>
<body>
    <div class="sticky-header">
        <div class="breadcrumb">
            <a href="/api/clinical/companies">Companies</a>
            <span>›</span>
            <a href="/api/clinical/companies/{ticker}/html">{ticker}</a>
            <span>›</span>
            <strong>{asset_name}</strong>
        </div>
        <div class="header-badges">
            <span class="badge">{stage}</span>
            <a href="/api/clinical/targets/{target_name.upper().replace(' ', '_')}/html" class="badge-link"><span class="badge">{target_name} Degrader</span></a>
        </div>
    </div>

    <div class="layout">
        <nav class="sidebar">
            <h3>Navigation</h3>
            <ul class="sidebar-nav">
                <li><a href="#overview">Overview</a></li>
                <li><a href="#target">Target Biology</a></li>
                <li><a href="#clinical">Clinical Data</a></li>
                <li><a href="#investment">Investment Analysis</a></li>
                <li><a href="#market">Market Opportunity</a></li>
                <li><a href="#catalysts">Catalysts</a></li>
            </ul>
            <h3 style="margin-top: 24px;">Target</h3>
            <ul class="sidebar-nav">
                <li><a href="/api/clinical/targets/{target_name.upper().replace(' ', '_')}/html">{target_name} →</a></li>
            </ul>
            <h3 style="margin-top: 24px;">Other Assets</h3>
            <ul class="sidebar-nav">
                {f'<li><a href="/api/clinical/companies/{ticker}/assets/{prev_slug}/html">← {prev_name}</a></li>' if prev_asset else ''}
                {f'<li><a href="/api/clinical/companies/{ticker}/assets/{next_slug}/html">{next_name} →</a></li>' if next_asset else ''}
            </ul>
        </nav>

        <main class="main">
            <section id="overview" class="section">
                <div class="asset-header">
                    <h1>{asset_name}</h1>
                    <div class="subtitle"><a href="/api/clinical/targets/{target_name.upper().replace(' ', '_')}/html" style="color: white; text-decoration: underline;">{target_name}</a> Degrader · {modality}</div>
                    <div class="tags">
                        <span class="badge">{stage}</span>
                        {f'<span class="badge">{asset.get("ownership", "")}</span>' if asset.get("ownership") else ''}
                    </div>
                </div>

                <div class="overview-grid">
                    <div class="overview-card target">
                        <h3>Target: <a href="/api/clinical/targets/{target_name.upper().replace(' ', '_')}/html" style="color: var(--accent);">{target_name}</a></h3>
                        {f'<div class="detail-row"><strong>Full Name</strong>{target_full}</div>' if target_full else ''}
                        {f'<div class="detail-row"><strong>Pathway</strong>{target_pathway}</div>' if target_pathway else ''}
                        {f'<div class="detail-row"><strong>Biology</strong>{target_biology}</div>' if target_biology else ''}
                        {f'<div class="genetic-highlight"><strong>Genetic Validation</strong><br>{target_genetic}</div>' if target_genetic else ''}
                    </div>
                    <div class="overview-card mechanism">
                        <h3>Mechanism of Action</h3>
                        {f'<div class="detail-row"><strong>Type</strong>{mech_type}</div>' if mech_type else ''}
                        {f'<div class="detail-row"><strong>Description</strong>{mech_desc}</div>' if mech_desc else ''}
                        {f'<div class="detail-row"><strong>Why Degrader</strong>{target_why}</div>' if target_why else ''}
                        {f'<div class="detail-row"><strong>Differentiation</strong>{mech_diff}</div>' if mech_diff else ''}
                    </div>
                </div>

                {f'<div class="indications"><strong>Indications:</strong> {ind_badges}</div>' if ind_badges else ''}
            </section>

            <section id="target" class="section">
                <h2 class="section-header">Target Biology</h2>
                <div class="card">
                    <div class="card-content">
                        {f'<p style="margin-bottom: 16px;">{target_biology}</p>' if target_biology else '<p>No target biology data available.</p>'}
                        {f'<div class="genetic-highlight"><strong>Human Genetic Evidence:</strong> {target_genetic}</div>' if target_genetic else ''}
                        {f'<div class="detail-row" style="margin-top: 16px;"><strong>Why Previous Approaches Failed</strong>{target_why}</div>' if target_why else ''}
                    </div>
                </div>
            </section>

            <section id="clinical" class="section">
                <h2 class="section-header">Clinical Data</h2>
                {trials_html if trials_html else '<p class="no-data">No clinical trial data available.</p>'}
            </section>

            {investment_html}

            <section id="market" class="section">
                <h2 class="section-header">Market Opportunity</h2>
                <div class="card">
                    <div class="card-content">
                        <div class="market-grid">
                            {f'<div class="market-item"><div class="label">Total Addressable Market</div><div class="value">{market.get("total_addressable_market", "") or market.get("tam", "N/A")}</div></div>' if market.get("total_addressable_market") or market.get("tam") else ''}
                            {f'<div class="market-item"><div class="label">Current Penetration</div><div class="value">{market.get("current_penetration", "")}</div></div>' if market.get("current_penetration") else ''}
                            {f'<div class="market-item"><div class="label">Oral Preference</div><div class="value">{market.get("oral_preference", "")}</div></div>' if market.get("oral_preference") else ''}
                            {f'<div class="market-item full highlight"><div class="label">Competitive Advantage</div><div class="value">{market.get("competitive_advantage", "")}</div></div>' if market.get("competitive_advantage") else ''}
                            {f'<div class="market-item"><div class="label">Peak Sales (Bull)</div><div class="value">{peak_bull}</div></div>' if peak_bull else ''}
                            {f'<div class="market-item"><div class="label">Peak Sales (Base)</div><div class="value">{peak_base}</div></div>' if peak_base else ''}
                        </div>
                    </div>
                </div>
            </section>

            <section id="catalysts" class="section">
                <h2 class="section-header">Upcoming Catalysts</h2>
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

    # Build bull/bear case HTML
    bull_case = thesis.get("bull_case", []) if isinstance(thesis, dict) else thesis
    bear_case = thesis.get("bear_case", []) if isinstance(thesis, dict) else []
    key_debates = thesis.get("key_debates", []) if isinstance(thesis, dict) else []

    bull_html = ""
    for item in bull_case:
        if isinstance(item, dict):
            bull_html += f'''
            <div class="thesis-item bull">
                <div class="thesis-point">{item.get('point', '')}</div>
                <div class="thesis-evidence"><strong>Evidence:</strong> {item.get('evidence', '')}</div>
                <div class="thesis-meta">
                    <span class="confidence {item.get('confidence', 'medium')}">{item.get('confidence', 'medium').title()} confidence</span>
                    <span class="source">Page {item.get('source_page', 'N/A')}</span>
                </div>
            </div>'''
        else:
            bull_html += f'<div class="thesis-item bull"><div class="thesis-point">{item}</div></div>'

    bear_html = ""
    for item in bear_case:
        if isinstance(item, dict):
            counter = f'<div class="thesis-counter"><strong>Counter:</strong> {item.get("counter", "")}</div>' if item.get("counter") else ""
            bear_html += f'''
            <div class="thesis-item bear">
                <div class="thesis-point">{item.get('point', '')}</div>
                <div class="thesis-evidence"><strong>Evidence:</strong> {item.get('evidence', '')}</div>
                {counter}
                <div class="thesis-meta">
                    <span class="confidence {item.get('confidence', 'medium')}">{item.get('confidence', 'medium').title()} confidence</span>
                    <span class="source">Page {item.get('source_page', 'N/A')}</span>
                </div>
            </div>'''

    debates_html = ""
    for debate in key_debates:
        debates_html += f'''
        <div class="debate-item">
            <div class="debate-question">{debate.get('question', '')}</div>
            <div class="debate-views">
                <div class="bull-view"><strong>Bull:</strong> {debate.get('bull_view', '')}</div>
                <div class="bear-view"><strong>Bear:</strong> {debate.get('bear_view', '')}</div>
            </div>
            <div class="data-to-watch"><strong>Data to watch:</strong> {debate.get('data_to_watch', '')}</div>
        </div>'''

    # Build assets HTML with full clinical data
    assets_html = ""
    for asset in assets:
        asset_name = asset.get("name", "Unknown")
        target_data = asset.get("target", {})
        mechanism_data = asset.get("mechanism", {})
        stage = asset.get("stage", "")
        modality = asset.get("modality", "")
        indications = asset.get("indications", [])
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
                <span class="badge target">{target_name} Degrader</span>
                <span class="badge stage">{stage}</span>
                {f'<span class="badge modality">{modality}</span>' if modality else ''}
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

        /* Thesis items */
        .thesis-item {{
            padding: 16px;
            margin-bottom: 12px;
            border-radius: 8px;
            border-left: 4px solid;
        }}
        .thesis-item.bull {{ background: #f0fff4; border-color: var(--bull); }}
        .thesis-item.bear {{ background: #fff5f5; border-color: var(--bear); }}
        .thesis-point {{ font-weight: 600; margin-bottom: 8px; }}
        .thesis-evidence {{ color: var(--text-muted); margin-bottom: 8px; }}
        .thesis-counter {{ color: var(--bull); margin-bottom: 8px; font-style: italic; }}
        .thesis-meta {{ display: flex; gap: 16px; font-size: 0.85rem; }}
        .confidence {{ padding: 2px 8px; border-radius: 4px; }}
        .confidence.high {{ background: #c6f6d5; color: var(--bull); }}
        .confidence.medium {{ background: #fefcbf; color: var(--warning); }}
        .confidence.low {{ background: #fed7d7; color: var(--bear); }}
        .source {{ color: var(--text-muted); }}

        /* Debates */
        .debate-item {{
            background: #ebf8ff;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 12px;
        }}
        .debate-question {{ font-weight: 600; margin-bottom: 12px; color: var(--primary); }}
        .debate-views {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 12px; }}
        .bull-view {{ color: var(--bull); }}
        .bear-view {{ color: var(--bear); }}
        .data-to-watch {{ background: white; padding: 8px 12px; border-radius: 4px; }}

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
        <a href="/api/clinical/companies/html">Companies</a> · <strong>Targets</strong>
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
            <a href="/api/clinical/companies/html">Companies</a>
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
