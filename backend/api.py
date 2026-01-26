"""
Helix Intelligence API

FastAPI server exposing biotech intelligence endpoints.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from src.scrapers.sec_13f_scraper import SECEdgarScraper, BIOTECH_SPECIALIST_FUNDS
from src.scrapers.pubmed_kol_extractor import PubMedKOLExtractor
from pathlib import Path
import json

app = FastAPI(
    title="Helix Intelligence API",
    description="Biotech investment research platform",
    version="1.0.0"
)

# Tracked biotech companies
TRACKED_COMPANIES = {
    "ABVX": {
        "ticker": "ABVX",
        "name": "Abivax SA",
        "description": "Clinical-stage biotech focused on inflammatory diseases",
        "sector": "Biotechnology",
        "lead_asset": "Obefazimod (ABX464)",
        "indication": "Ulcerative Colitis",
        "stage": "NDA Filed",
        "website": "https://www.abivax.com"
    },
    "INSM": {
        "ticker": "INSM",
        "name": "Insmed Incorporated",
        "description": "Global biopharma focused on serious and rare diseases",
        "sector": "Biotechnology",
        "lead_asset": "Brensocatib",
        "indication": "Bronchiectasis",
        "stage": "Phase 3",
        "website": "https://www.insmed.com"
    },
    "CGON": {
        "ticker": "CGON",
        "name": "CG Oncology Inc",
        "description": "Clinical-stage biotech developing oncolytic immunotherapies for bladder cancer",
        "sector": "Biotechnology",
        "lead_asset": "Cretostimogene (CG0070)",
        "indication": "NMIBC",
        "stage": "Phase 3",
        "website": "https://www.cgoncology.com"
    },
    "GPCR": {
        "ticker": "GPCR",
        "name": "Structure Therapeutics",
        "description": "Clinical-stage biopharma pioneering GPCR-targeted small molecules",
        "sector": "Biotechnology",
        "lead_asset": "GSBR-1290",
        "indication": "Obesity/T2D",
        "stage": "Phase 2",
        "website": "https://www.structuretx.com"
    },
    "VRNA": {
        "ticker": "VRNA",
        "name": "Verona Pharma",
        "description": "Biopharma focused on respiratory diseases",
        "sector": "Biotechnology",
        "lead_asset": "Ensifentrine",
        "indication": "COPD",
        "stage": "Approved",
        "website": "https://www.vfrona.com"
    }
}

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-production-0a3c.up.railway.app",
        "https://helix-production-f9fa.up.railway.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class KOLSearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10


class CompanyRequest(BaseModel):
    ticker: str
    name: str


@app.get("/")
async def root():
    return {
        "service": "Helix Intelligence API",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/companies")
async def get_companies():
    """Get list of tracked biotech companies (includes XBI holdings if available)"""
    # Try to load XBI holdings for expanded company list
    holdings_path = Path(__file__).parent / "data" / "xbi_holdings.json"

    if holdings_path.exists():
        try:
            with open(holdings_path) as f:
                xbi_data = json.load(f)
                holdings = xbi_data.get("holdings", [])
                # Convert XBI holdings format to company format
                companies = []
                for h in holdings:
                    companies.append({
                        "ticker": h["ticker"],
                        "name": h["name"],
                        "description": h.get("description", f"Biotech company in XBI ETF"),
                        "sector": h.get("sector", "Biotechnology"),
                        "lead_asset": None,
                        "indication": None,
                        "stage": None,
                        "weight": h.get("weight"),
                        "website": None
                    })
                return companies
        except Exception:
            pass

    return list(TRACKED_COMPANIES.values())


@app.get("/api/companies/{ticker}")
async def get_company(ticker: str):
    """Get details for a specific company"""
    ticker = ticker.upper()
    if ticker not in TRACKED_COMPANIES:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")
    return TRACKED_COMPANIES[ticker]


@app.get("/api/reports/{ticker}")
async def get_report(ticker: str):
    """Get intelligence report for a company"""
    ticker = ticker.upper()
    if ticker not in TRACKED_COMPANIES:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    company = TRACKED_COMPANIES[ticker]

    # Build report with available intelligence (matching app's expected format)
    report = {
        "ticker": ticker,
        "company_name": company["name"],
        "generated_at": datetime.utcnow().isoformat(),
        "sections": {
            "bluf": {
                "summary": f"{company['name']} is developing {company['lead_asset']} for {company['indication']}. Currently in {company['stage']}.",
                "investment_thesis": f"Promising {company['stage']} asset in {company['indication']} with specialist fund interest.",
                "key_catalysts": [
                    f"{company['stage']} data readout expected",
                    "Potential FDA approval pathway",
                    "Conference presentations"
                ],
                "key_risks": [
                    "Clinical trial execution risk",
                    "Competitive landscape",
                    "Regulatory uncertainty"
                ],
                "recommendation": "Monitor for catalyst updates"
            },
            "pipeline": {
                "lead_asset": company["lead_asset"],
                "lead_asset_stage": company["stage"],
                "lead_asset_indication": company["indication"],
                "programs": [
                    {
                        "name": company["lead_asset"],
                        "indication": company["indication"],
                        "stage": company["stage"],
                        "description": f"Lead program for {company['name']}"
                    }
                ],
                "total_programs": 1
            },
            "clinical_trials": {
                "active_trials": [],
                "completed_trials": [],
                "upcoming_readouts": [
                    {
                        "trial_id": "TBD",
                        "title": f"{company['lead_asset']} {company['stage']} Trial",
                        "expected_date": "2025",
                        "phase": company["stage"]
                    }
                ],
                "total_trials": 1,
                "phases_summary": {company["stage"]: 1}
            },
            "preclinical": {
                "pubmed_articles": [],
                "conference_posters": [],
                "key_findings": [f"Mechanism targeting {company['indication']}"],
                "mechanism_of_action": f"Novel therapeutic approach for {company['indication']}"
            },
            "patent_legal": {
                "key_patents": [],
                "nearest_expiry": "TBD",
                "litigation": [],
                "regulatory_notes": [f"{company['stage']} development ongoing"]
            },
            "management": {
                "ceo": None,
                "key_executives": [],
                "recent_changes": [],
                "board_highlights": []
            }
        },
        "data_sources": [
            "SEC 13F Filings",
            "PubMed",
            "ClinicalTrials.gov",
            "Company Filings"
        ]
    }

    return report


@app.get("/api/funds")
async def get_specialist_funds():
    """Get list of tracked biotech specialist funds"""
    return {
        "funds": [{"name": f.name, "cik": f.cik, "is_specialist": f.is_biotech_specialist} for f in BIOTECH_SPECIALIST_FUNDS],
        "count": len(BIOTECH_SPECIALIST_FUNDS)
    }


@app.get("/api/xbi")
async def get_xbi_holdings():
    """Get XBI ETF holdings"""
    holdings_path = Path(__file__).parent / "data" / "xbi_holdings.json"

    if holdings_path.exists():
        with open(holdings_path) as f:
            return json.load(f)

    # Return tracked companies as fallback
    return {
        "etf": "XBI",
        "name": "SPDR S&P Biotech ETF",
        "holdings_count": len(TRACKED_COMPANIES),
        "holdings": list(TRACKED_COMPANIES.values())
    }


@app.post("/api/kols/search")
async def search_kols(request: KOLSearchRequest):
    """Search for Key Opinion Leaders on a topic"""
    try:
        extractor = PubMedKOLExtractor()
        kols = extractor.find_kols(request.query, max_results=request.max_results)
        return {
            "query": request.query,
            "kols": kols,
            "count": len(kols)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/13f/{fund_name}")
async def get_fund_holdings(fund_name: str):
    """Get 13F holdings for a specific fund"""
    # Find fund by name (partial match)
    fund = None
    for f in BIOTECH_SPECIALIST_FUNDS:
        if fund_name.lower() in f.name.lower():
            fund = f
            break

    if not fund:
        raise HTTPException(status_code=404, detail=f"Fund {fund_name} not found")

    try:
        scraper = SECEdgarScraper()
        filings = scraper.get_13f_filings(fund.cik, num_quarters=1)
        return {
            "fund": fund.name,
            "cik": fund.cik,
            "filings": filings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
