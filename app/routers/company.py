"""
Company API Router

Endpoints for company data, pipeline info, thesis generation, and automated refresh.
"""

import sys
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json

# Add backend to path for imports
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

router = APIRouter()


class FullRefreshRequest(BaseModel):
    months_back: int = 12
    max_presentations: int = 10
    skip_vision: bool = False


def load_pipeline_data(ticker: str) -> dict | None:
    """Load enriched pipeline data from JSON file if available."""
    pipeline_path = BACKEND_DIR / "data" / "pipeline_data" / f"{ticker.lower()}.json"
    if not pipeline_path.exists():
        return None

    try:
        with open(pipeline_path) as f:
            return json.load(f)
    except Exception:
        return None


@router.get("/{ticker}/thesis/html", response_class=HTMLResponse)
async def get_investment_thesis_html(ticker: str):
    """
    Generate comprehensive investment thesis HTML page.
    Uses verified data from FDA, ClinicalTrials.gov, and company sources.
    """
    try:
        if str(BACKEND_DIR) not in sys.path:
            sys.path.insert(0, str(BACKEND_DIR))
        from services.thesis_generator import generate_thesis
        html_content = generate_thesis(ticker.upper())
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No pipeline data found for {ticker}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticker}/refresh")
async def refresh_company_data(ticker: str):
    """
    Refresh company data from all authoritative sources:
    - FDA approval status (OpenFDA API)
    - Clinical trial status (ClinicalTrials.gov API)
    - IR news (company press releases)
    """
    try:
        if str(BACKEND_DIR) not in sys.path:
            sys.path.insert(0, str(BACKEND_DIR))
        from services.company_refresher import CompanyRefresher
        refresher = CompanyRefresher(verbose=False)
        result = refresher.refresh(ticker.upper())
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No pipeline data found for {ticker}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticker}/full-refresh")
async def full_refresh_company(ticker: str, request: FullRefreshRequest = None):
    """
    Full automated refresh: Discover IR page, scrape presentations, analyze with Vision API,
    normalize data, and verify with FDA/ClinicalTrials.gov.

    This works for ANY biotech company - no manual data entry required.

    Parameters:
    - months_back: How many months of presentations to fetch (default: 12)
    - max_presentations: Maximum presentations to analyze with Vision API (default: 10)
    - skip_vision: Skip Vision API analysis and use cached data (default: false)
    """
    request = request or FullRefreshRequest()

    try:
        if str(BACKEND_DIR) not in sys.path:
            sys.path.insert(0, str(BACKEND_DIR))
        from services.master_refresh import refresh_company
        result = await refresh_company(
            ticker.upper(),
            months_back=request.months_back,
            max_presentations=request.max_presentations,
            skip_vision=request.skip_vision,
            verbose=False
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/data-sources")
async def get_company_data_sources(ticker: str):
    """
    Get information about all data sources used for a company.
    Returns IR page info, presentations found, analysis status, and verification status.
    """
    ticker = ticker.upper()
    company_dir = BACKEND_DIR / "data" / "companies" / ticker.lower()

    result = {
        "ticker": ticker,
        "ir_info": None,
        "presentations": [],
        "normalized_data": None,
        "has_vision_analysis": False,
        "fda_verified": False,
        "trials_verified": False
    }

    # Check IR info
    ir_path = company_dir / "ir_info.json"
    if ir_path.exists():
        with open(ir_path) as f:
            result["ir_info"] = json.load(f)

    # Check presentations list
    pres_path = company_dir / "presentations_list.json"
    if pres_path.exists():
        with open(pres_path) as f:
            result["presentations"] = json.load(f)

    # Check analyzed presentations
    analysis_path = company_dir / "analyzed_presentations.json"
    result["has_vision_analysis"] = analysis_path.exists()

    # Check normalized data
    norm_path = company_dir / "normalized.json"
    if norm_path.exists():
        with open(norm_path) as f:
            norm_data = json.load(f)
            result["normalized_data"] = {
                "normalized_at": norm_data.get("normalized_at"),
                "pipeline_count": len(norm_data.get("pipeline", [])),
                "trials_count": len(norm_data.get("clinical_trials", [])),
                "catalysts_count": len(norm_data.get("catalysts", [])),
                "sources": norm_data.get("sources", {})
            }
            result["fda_verified"] = norm_data.get("sources", {}).get("fda_api", False)
            result["trials_verified"] = norm_data.get("sources", {}).get("clinicaltrials_api", False)

    # Also check legacy pipeline_data location
    if not result["normalized_data"]:
        legacy_path = BACKEND_DIR / "data" / "pipeline_data" / f"{ticker.lower()}.json"
        if legacy_path.exists():
            with open(legacy_path) as f:
                legacy_data = json.load(f)
                result["normalized_data"] = {
                    "normalized_at": legacy_data.get("last_updated"),
                    "pipeline_count": len(legacy_data.get("programs", [])),
                    "sources": legacy_data.get("sources", [])
                }

    return result


@router.get("/{ticker}/normalized")
async def get_normalized_data(ticker: str):
    """
    Get normalized company data from automated IR ingestion.
    This is the merged, deduplicated data from all analyzed presentations.
    """
    ticker = ticker.upper()
    company_dir = BACKEND_DIR / "data" / "companies" / ticker.lower()
    norm_path = company_dir / "normalized.json"

    if not norm_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No normalized data for {ticker}. Run POST /api/company/{ticker}/full-refresh first."
        )

    with open(norm_path) as f:
        return json.load(f)


@router.get("/{ticker}/pipeline")
async def get_pipeline_data(ticker: str):
    """Get enriched pipeline data for a company (if available)"""
    data = load_pipeline_data(ticker.upper())

    if not data:
        raise HTTPException(status_code=404, detail=f"No pipeline data found for {ticker}")

    return data
