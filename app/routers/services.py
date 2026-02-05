"""
Services API Router

Endpoints for IR scraping and research services.
"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# Add src to path for imports
SRC_DIR = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class IRScrapeRequest(BaseModel):
    ticker: str


# ============================================
# Trial Investigators Endpoints
# ============================================

@router.get("/trial-investigators")
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
