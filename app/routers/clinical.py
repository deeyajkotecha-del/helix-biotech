"""Clinical data API router."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.services.clinical.extractor import (
    generate_clinical_summary_for_asset,
    get_kymera_pipeline,
    get_target_landscape_with_context,
    get_endpoint_definitions,
    get_biomarker_definitions,
    KYMERA_ASSETS,
    SUPPORTED_TARGETS,
)

router = APIRouter()


# =============================================================================
# ASSET ENDPOINTS
# =============================================================================

@router.get("/assets/{ticker}/{asset_name}/clinical")
async def get_asset_clinical_data(ticker: str, asset_name: str):
    """
    Get full clinical data package for an asset with contextual definitions.

    Example: GET /api/clinical/assets/KYMR/KT-621/clinical

    Supported assets: KT-621, KT-579, KT-485
    """
    if ticker.upper() == "KYMR" and asset_name.upper() in KYMERA_ASSETS:
        return generate_clinical_summary_for_asset(asset_name.upper())

    raise HTTPException(
        status_code=404,
        detail=f"Asset {asset_name} not found for {ticker}. Supported: {', '.join(KYMERA_ASSETS)}"
    )


@router.get("/assets/{ticker}/{asset_name}/clinical/html", response_class=HTMLResponse)
async def get_asset_clinical_html(ticker: str, asset_name: str):
    """Get clinical data as formatted HTML with collapsible sections and tooltips."""
    if ticker.upper() != "KYMR" or asset_name.upper() not in KYMERA_ASSETS:
        raise HTTPException(status_code=404, detail=f"Asset {asset_name} not found")

    data = generate_clinical_summary_for_asset(asset_name.upper())
    html = _generate_clinical_html(data)
    return HTMLResponse(content=html)


# =============================================================================
# COMPANY/PIPELINE ENDPOINTS
# =============================================================================

@router.get("/companies/{ticker}/pipeline")
async def get_company_pipeline(ticker: str):
    """
    Get full pipeline for a company.

    Example: GET /api/clinical/companies/KYMR/pipeline
    """
    if ticker.upper() == "KYMR":
        return get_kymera_pipeline()

    raise HTTPException(status_code=404, detail=f"Company {ticker} not found")


# =============================================================================
# TARGET LANDSCAPE ENDPOINTS
# =============================================================================

@router.get("/targets/{target_name}/landscape")
async def get_target_landscape(target_name: str):
    """
    Get target landscape with biomarker definitions and measurement methods.

    Example: GET /api/clinical/targets/STAT6/landscape

    Supported targets: STAT6, IRF5, IRAK4
    """
    result = get_target_landscape_with_context(target_name)
    if result:
        return result

    raise HTTPException(
        status_code=404,
        detail=f"Target {target_name} not found. Supported: {', '.join(SUPPORTED_TARGETS)}"
    )


@router.get("/targets/{target_name}/clinical-landscape")
async def get_target_clinical_landscape_legacy(target_name: str):
    """Legacy endpoint - redirects to /targets/{target}/landscape."""
    return await get_target_landscape(target_name)


# =============================================================================
# DEFINITION ENDPOINTS
# =============================================================================

@router.get("/definitions/endpoints")
async def get_all_endpoint_definitions():
    """
    Get all endpoint definitions for UI tooltips.

    Returns definitions for: EASI, SCORAD, vIGA-AD, PPNRS, FEV1, ACQ-5, etc.
    """
    return get_endpoint_definitions()


@router.get("/definitions/biomarkers")
async def get_all_biomarker_definitions():
    """
    Get all biomarker definitions for UI tooltips.

    Returns definitions for: STAT6, TARC, Eotaxin-3, IRF5, IRAK4, etc.
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
# HTML GENERATION
# =============================================================================

def _generate_clinical_html(data: dict) -> str:
    """Generate HTML page with collapsible sections, tooltips, and method info."""
    asset = data.get("asset", {})
    trials = data.get("trials", [])
    definitions = data.get("definitions", {})
    endpoints_with_context = data.get("endpoints_with_context", {})

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

    # Build endpoint definitions section
    endpoint_defs = definitions.get("endpoints", {})
    endpoints_section = ""
    if endpoint_defs:
        endpoint_cards = ""
        for name, defn in endpoint_defs.items():
            benchmarks = defn.get("comparator_benchmarks", {})
            benchmarks_html = ""
            if benchmarks:
                for drug, value in benchmarks.items():
                    benchmarks_html += f'<div class="benchmark-item"><strong>{drug}:</strong> {value}</div>'

            endpoint_cards += f"""
            <div class="definition-card">
                <h4>{name}</h4>
                <p class="full-name">{defn.get('full_name', '')}</p>
                <p class="description">{defn.get('description', '')}</p>
                <p class="scoring"><strong>Scoring:</strong> {defn.get('scoring', 'N/A') if isinstance(defn.get('scoring'), str) else 'See details'}</p>
                {f'<div class="benchmarks"><strong>Comparator Benchmarks:</strong>{benchmarks_html}</div>' if benchmarks_html else ''}
            </div>
            """

        endpoints_section = f"""
        <div class="card">
            <button class="collapsible">Endpoint Definitions</button>
            <div class="content">
                <div class="definitions-grid">{endpoint_cards}</div>
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

        /* Header */
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

        /* Cards */
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
            transition: transform 0.2s;
        }}
        .collapsible.active::after {{ content: '-'; }}
        .content {{
            padding: 0 20px 20px;
            display: none;
            border-top: 1px solid var(--border);
        }}
        .content.show {{ display: block; }}

        /* Trial info */
        .trial-meta {{ background: var(--bg); padding: 12px; border-radius: 8px; margin-bottom: 12px; }}
        .trial-meta p {{ margin: 4px 0; }}
        .safety-note {{ background: #f0fff4; border-left: 3px solid var(--success); padding: 10px 12px; margin: 12px 0; border-radius: 0 8px 8px 0; }}
        .comparison-note {{ background: #ebf8ff; border-left: 3px solid var(--accent); padding: 10px 12px; margin: 12px 0; border-radius: 0 8px 8px 0; }}

        /* Tables */
        .endpoints-table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        .endpoints-table th, .endpoints-table td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
        .endpoints-table th {{ background: var(--bg); font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); }}
        .endpoints-table tr:hover {{ background: #fafafa; }}
        .result-cell strong {{ color: var(--primary); }}
        .benchmark {{ font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }}

        /* Tooltips */
        .endpoint-name {{
            border-bottom: 1px dotted var(--text-muted);
            cursor: help;
            position: relative;
        }}
        .method-badge {{
            display: inline-block;
            font-size: 0.7rem;
            background: var(--bg);
            color: var(--text-muted);
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 6px;
        }}

        /* Thesis/Risks */
        .thesis-item {{
            background: #ebf8ff;
            border-left: 4px solid var(--accent);
            padding: 12px 16px;
            margin: 8px 0;
            border-radius: 0 8px 8px 0;
        }}
        .risk-item {{
            background: #fff5f5;
            border-left: 4px solid var(--danger);
            padding: 12px 16px;
            margin: 8px 0;
            border-radius: 0 8px 8px 0;
        }}
        .catalyst-item {{
            background: #fffff0;
            border-left: 4px solid var(--warning);
            padding: 12px 16px;
            margin: 8px 0;
            border-radius: 0 8px 8px 0;
        }}

        /* Definitions */
        .definitions-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
        .definition-card {{
            background: var(--bg);
            padding: 16px;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        .definition-card h4 {{ margin: 0 0 8px 0; color: var(--primary); }}
        .definition-card .full-name {{ font-style: italic; color: var(--text-muted); margin: 0 0 8px 0; }}
        .definition-card .pathway {{ font-size: 0.9rem; margin: 4px 0; }}
        .definition-card .significance {{ font-size: 0.9rem; margin: 8px 0; }}
        .type-badge {{ font-size: 0.75rem; background: var(--accent); color: white; padding: 2px 8px; border-radius: 4px; }}
        .methods {{ margin-top: 12px; }}
        .method-item {{ background: white; padding: 8px; margin: 4px 0; border-radius: 4px; font-size: 0.9rem; }}
        .method-detail {{ display: block; color: var(--text-muted); font-size: 0.8rem; }}
        .benchmarks {{ margin-top: 12px; }}
        .benchmark-item {{ font-size: 0.9rem; margin: 4px 0; }}

        /* Indications */
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
        {endpoints_section}
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
        parts.append(definition["description"][:100] + "..." if len(definition.get("description", "")) > 100 else definition["description"])
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
