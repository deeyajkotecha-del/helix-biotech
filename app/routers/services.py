"""
Services API Router

Endpoints for KOL finding, IR scraping, and other research services.
"""

import sys
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# Add src to path for imports
SRC_DIR = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class KOLSearchRequest(BaseModel):
    query: str
    max_results: int = 50
    us_only: bool = True


class IRScrapeRequest(BaseModel):
    ticker: str


# ============================================
# KOL Finder Endpoints
# ============================================

@router.get("/kols/search")
async def search_kols(
    query: str = Query(..., description="Search query (e.g., 'GLP-1 obesity')"),
    max_results: int = Query(50, ge=1, le=100, description="Maximum number of KOLs to return"),
    us_only: bool = Query(True, description="Filter to US-based researchers only")
):
    """
    Search for Key Opinion Leaders (KOLs) based on publications and clinical trials.

    Combines data from:
    - PubMed (publication authors)
    - ClinicalTrials.gov (trial investigators)

    Returns researchers ranked by combined publication and trial activity.
    """
    try:
        from services.kol_finder import find_kols

        result = find_kols(
            query=query,
            max_results=max_results,
            us_only=us_only
        )

        # Convert dataclasses to dicts for JSON response
        return {
            "query": result.query,
            "total_kols": result.total_kols,
            "us_only": result.us_only,
            "searched_at": result.searched_at,
            "kols": [
                {
                    "name": kol.name,
                    "first_name": kol.first_name,
                    "last_name": kol.last_name,
                    "institution": kol.institution,
                    "country": kol.country,
                    "email": kol.email,
                    "publication_count": kol.publication_count,
                    "trial_count": kol.trial_count,
                    "combined_score": kol.combined_score,
                    "recent_publications": [
                        {
                            "pmid": pub.pmid,
                            "title": pub.title,
                            "journal": pub.journal,
                            "year": pub.year,
                            "citation_count": pub.citation_count,
                        }
                        for pub in kol.publications[:5]  # Limit to 5 recent pubs
                    ],
                    "trials": [
                        {
                            "nct_id": trial.nct_id,
                            "title": trial.title,
                            "phase": trial.phase,
                            "status": trial.status,
                            "sponsor": trial.sponsor,
                            "role": trial.role,
                        }
                        for trial in kol.trials[:5]  # Limit to 5 trials
                    ],
                }
                for kol in result.kols
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kols/search")
async def search_kols_post(request: KOLSearchRequest):
    """
    Search for KOLs (POST version for complex queries).
    """
    return await search_kols(
        query=request.query,
        max_results=request.max_results,
        us_only=request.us_only
    )


@router.get("/kols/email")
async def find_kol_email(
    name: str = Query(..., description="Researcher name (e.g., 'John Smith')"),
    institution: str = Query("", description="Institution name (e.g., 'Johns Hopkins')")
):
    """
    Find institutional email for a researcher using PubMed data.
    """
    try:
        from services.email_finder import find_email

        email = find_email(name, institution)

        return {
            "name": name,
            "institution": institution,
            "email": email,
            "found": email is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kols/trial-investigators")
async def search_trial_investigators(
    query: str = Query(..., description="Search query for clinical trials"),
    max_trials: int = Query(100, ge=1, le=500, description="Maximum trials to search")
):
    """
    Search ClinicalTrials.gov for investigators working on a specific topic.

    Returns investigators ranked by number of trials they're involved in.
    """
    try:
        from services.trial_investigators import search_trial_investigators as search_investigators

        investigators = search_investigators(query, max_trials=max_trials)

        return {
            "query": query,
            "total_investigators": len(investigators),
            "investigators": [
                {
                    "name": inv.name,
                    "first_name": inv.first_name,
                    "last_name": inv.last_name,
                    "affiliation": inv.affiliation,
                    "country": inv.country,
                    "role": inv.role,
                    "trial_count": inv.trial_count,
                    "trials": [
                        {
                            "nct_id": trial.nct_id,
                            "title": trial.title,
                            "phase": trial.phase,
                            "status": trial.status,
                            "sponsor": trial.sponsor,
                            "role": trial.role,
                        }
                        for trial in inv.trials[:5]
                    ]
                }
                for inv in investigators
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# IR Scraper Endpoints
# ============================================

@router.get("/ir/supported-tickers")
async def get_supported_tickers():
    """
    Get list of tickers with IR scraping configurations.
    """
    try:
        from services.ir_scraper import get_supported_tickers

        tickers = get_supported_tickers()
        return {
            "tickers": tickers,
            "count": len(tickers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ir/scrape/{ticker}")
async def scrape_ir_documents(ticker: str):
    """
    Scrape IR documents (presentations, SEC filings, etc.) for a company.

    Currently supported: ARWR
    """
    try:
        from services.ir_scraper import scrape_ir_documents as scrape_docs, is_ticker_supported

        if not is_ticker_supported(ticker):
            raise HTTPException(
                status_code=400,
                detail=f"Ticker {ticker} is not supported. Use GET /api/services/ir/supported-tickers to see available tickers."
            )

        result = scrape_docs(ticker)

        return {
            "ticker": result.ticker,
            "company_name": result.company_name,
            "ir_base_url": result.ir_base_url,
            "scraped_at": result.scraped_at,
            "total_documents": result.total_documents,
            "documents_by_year": result.documents_by_year,
            "documents": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "url": doc.url,
                    "date": doc.date,
                    "type": doc.doc_type,
                    "event": doc.event,
                    "file_size": doc.file_size,
                    "category": doc.category,
                }
                for doc in result.documents
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ir/presentations/{ticker}")
async def get_presentations(ticker: str):
    """
    Get all presentations (investor decks, posters) for a company.
    """
    try:
        from services.ir_scraper import scrape_all_presentations, is_ticker_supported

        if not is_ticker_supported(ticker):
            raise HTTPException(
                status_code=400,
                detail=f"Ticker {ticker} is not supported."
            )

        result = scrape_all_presentations(ticker)

        return {
            "ticker": result["ticker"],
            "total_presentations": result["total_presentations"],
            "by_year": result["by_year"],
            "by_type": result["by_type"],
            "presentations": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "url": doc.url,
                    "date": doc.date,
                    "type": doc.doc_type,
                    "event": doc.event,
                }
                for doc in result["presentations"]
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
