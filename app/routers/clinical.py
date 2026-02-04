"""Clinical data API router."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.services.clinical.extractor import generate_clinical_summary_for_asset

router = APIRouter()


@router.get("/assets/{ticker}/{asset_name}/clinical")
async def get_asset_clinical_data(ticker: str, asset_name: str):
    """
    Get full clinical data package for an asset.

    Example: GET /api/clinical/assets/KYMR/KT-621/clinical
    """
    if asset_name.upper() == "KT-621" and ticker.upper() == "KYMR":
        return generate_clinical_summary_for_asset("KT-621")

    raise HTTPException(status_code=404, detail=f"Asset {asset_name} not found for {ticker}")


@router.get("/assets/{ticker}/{asset_name}/clinical/html", response_class=HTMLResponse)
async def get_asset_clinical_html(ticker: str, asset_name: str):
    """Get clinical data as formatted HTML with collapsible sections."""
    if asset_name.upper() != "KT-621" or ticker.upper() != "KYMR":
        raise HTTPException(status_code=404, detail=f"Asset {asset_name} not found")

    data = generate_clinical_summary_for_asset("KT-621")
    html = _generate_clinical_html(data)
    return HTMLResponse(content=html)


@router.get("/targets/{target_name}/clinical-landscape")
async def get_target_clinical_landscape(target_name: str):
    """Get clinical data for all assets targeting a specific target."""
    if target_name.upper() == "STAT6":
        return {
            "target": "STAT6",
            "full_name": "Signal Transducer and Activator of Transcription 6",
            "pathway": "IL-4/IL-13 signaling",
            "assets": [
                {
                    "name": "KT-621",
                    "company": "Kymera Therapeutics",
                    "ticker": "KYMR",
                    "mechanism": "STAT6 degrader",
                    "phase": "Phase 2b",
                    "key_data": "63% EASI reduction at Day 29 in AD"
                },
                {
                    "name": "Dupixent (dupilumab)",
                    "company": "Regeneron/Sanofi",
                    "ticker": "REGN",
                    "mechanism": "IL-4Ra antibody (blocks STAT6 activation)",
                    "phase": "Approved",
                    "key_data": "Market leader, $13B+ sales"
                }
            ]
        }

    raise HTTPException(status_code=404, detail=f"Target {target_name} not found")


def _generate_clinical_html(data: dict) -> str:
    """Generate HTML page with collapsible sections."""
    asset = data.get("asset", {})
    trials = data.get("trials", [])

    trials_html = ""
    for trial in trials:
        endpoints_rows = "".join(
            f"<tr><td>{e.get('name', '')}</td><td>{e.get('category', '')}</td>"
            f"<td>{e.get('dose_group', '')}</td><td>{e.get('result', '')}</td></tr>"
            for e in trial.get("endpoints", [])
        )
        trials_html += f"""
        <div class="card">
            <button class="collapsible">{trial.get('name', 'Trial')}</button>
            <div class="content">
                <p><strong>Phase:</strong> {trial.get('phase', 'N/A')}</p>
                <p><strong>Design:</strong> {trial.get('design', 'N/A')}</p>
                <p><strong>Population:</strong> {trial.get('population', 'N/A')}</p>
                <p><strong>Primary Endpoint:</strong> {trial.get('primary_endpoint', 'N/A')}</p>
                <table>
                    <thead><tr><th>Endpoint</th><th>Category</th><th>Arm</th><th>Result</th></tr></thead>
                    <tbody>{endpoints_rows}</tbody>
                </table>
            </div>
        </div>
        """

    thesis_html = "".join(f'<div class="thesis">{p}</div>' for p in data.get("investment_thesis_points", []))
    risks_html = "".join(f'<div class="risk">{r}</div>' for r in data.get("key_risks", []))

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{asset.get('name', 'Asset')} Clinical Data | Satya Bio</title>
    <style>
        :root {{ --primary: #1a365d; --accent: #3182ce; --success: #38a169; --danger: #e53e3e; --bg: #f7fafc; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, var(--primary), #2c5282); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0 0 8px 0; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; background: var(--accent); margin-right: 8px; }}
        .card {{ background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 16px; overflow: hidden; }}
        .collapsible {{ width: 100%; background: white; border: none; padding: 16px 20px; text-align: left; font-size: 1rem; font-weight: 600; cursor: pointer; }}
        .collapsible:hover {{ background: #f7fafc; }}
        .content {{ padding: 0 20px 20px; display: none; }}
        .content.show {{ display: block; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #f7fafc; font-size: 0.85rem; text-transform: uppercase; }}
        .thesis {{ background: #ebf8ff; border-left: 4px solid var(--accent); padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; }}
        .risk {{ background: #fff5f5; border-left: 4px solid var(--danger); padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{asset.get('name', 'Unknown')}</h1>
            <div>{asset.get('company', '')} ({asset.get('ticker', '')})</div>
            <span class="badge">{data.get('clinical_development', {}).get('current_stage', '')}</span>
            <span class="badge">Target: {asset.get('target', '')}</span>
        </div>

        <div class="card">
            <button class="collapsible">Investment Thesis</button>
            <div class="content show">{thesis_html}</div>
        </div>

        <div class="card">
            <button class="collapsible">Key Risks</button>
            <div class="content">{risks_html}</div>
        </div>

        {trials_html}
    </div>
    <script>
        document.querySelectorAll('.collapsible').forEach(btn => {{
            btn.addEventListener('click', function() {{
                this.nextElementSibling.classList.toggle('show');
            }});
        }});
    </script>
</body>
</html>
"""
