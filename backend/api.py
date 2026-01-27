"""
Helix Intelligence API

FastAPI server exposing biotech intelligence endpoints.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import sqlite3

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

    # First check TRACKED_COMPANIES
    if ticker in TRACKED_COMPANIES:
        return TRACKED_COMPANIES[ticker]

    # Check XBI holdings
    xbi_company = get_company_from_xbi(ticker)
    if xbi_company:
        return {
            "ticker": xbi_company["ticker"],
            "name": xbi_company["name"],
            "description": xbi_company.get("description", "Biotech company in XBI ETF"),
            "sector": "Biotechnology",
            "lead_asset": None,
            "indication": None,
            "stage": None,
            "weight": xbi_company.get("weight"),
            "website": None
        }

    # Check database
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM companies WHERE ticker = ?", (ticker,))
        row = cur.fetchone()
        conn.close()
        if row:
            company = dict(row)
            return {
                "ticker": company["ticker"],
                "name": company["name"],
                "description": company.get("description", "Biotech company"),
                "sector": "Biotechnology",
                "lead_asset": None,
                "indication": None,
                "stage": None,
                "website": None
            }

    raise HTTPException(status_code=404, detail=f"Company {ticker} not found")


def get_company_from_xbi(ticker: str) -> Optional[dict]:
    """Look up company in XBI holdings"""
    holdings_path = Path(__file__).parent / "data" / "xbi_holdings.json"
    if holdings_path.exists():
        try:
            with open(holdings_path) as f:
                xbi_data = json.load(f)
                for h in xbi_data.get("holdings", []):
                    if h["ticker"].upper() == ticker.upper():
                        return h
        except Exception:
            pass
    return None


@app.get("/api/reports/{ticker}")
async def get_report(ticker: str):
    """Get intelligence report for a company"""
    ticker = ticker.upper()

    # First check TRACKED_COMPANIES for detailed data
    company = TRACKED_COMPANIES.get(ticker)

    # If not in tracked, check XBI holdings
    if not company:
        xbi_company = get_company_from_xbi(ticker)
        if xbi_company:
            company = {
                "ticker": xbi_company["ticker"],
                "name": xbi_company["name"],
                "description": xbi_company.get("description", "Biotech company"),
                "sector": "Biotechnology",
                "lead_asset": None,
                "indication": None,
                "stage": None,
                "website": None
            }

    # Also check database for enriched info
    conn = get_db_connection()
    db_company = None
    db_trials = []
    db_filings = []

    if conn:
        cur = conn.cursor()
        # Get company info from database
        cur.execute("SELECT * FROM companies WHERE ticker = ?", (ticker,))
        row = cur.fetchone()
        if row:
            db_company = dict(row)

        # Get clinical trials
        cur.execute("""
            SELECT nct_id, title, status, phase, conditions, interventions, sponsor
            FROM clinical_trials WHERE company_ticker = ?
            ORDER BY start_date DESC LIMIT 10
        """, (ticker,))
        for row in cur.fetchall():
            trial = dict(row)
            trial["conditions"] = json.loads(trial["conditions"]) if trial["conditions"] else []
            trial["interventions"] = json.loads(trial["interventions"]) if trial["interventions"] else []
            db_trials.append(trial)

        # Get SEC filings
        cur.execute("""
            SELECT accession_number, form_type, filing_date, description
            FROM sec_filings WHERE company_ticker = ?
            ORDER BY filing_date DESC LIMIT 10
        """, (ticker,))
        db_filings = [dict(row) for row in cur.fetchall()]

        conn.close()

    # If we still don't have company info, return 404
    if not company and not db_company:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    # Use database info if available
    if db_company and not company:
        company = {
            "ticker": ticker,
            "name": db_company.get("name", ticker),
            "description": db_company.get("description", "Biotech company"),
            "sector": "Biotechnology",
            "lead_asset": None,
            "indication": None,
            "stage": None,
            "website": None
        }

    # Build report with available intelligence
    lead_asset = company.get("lead_asset") or "Pipeline programs"
    indication = company.get("indication") or "various indications"
    stage = company.get("stage") or "Development"

    # Build clinical trials section from database
    active_trials = [t for t in db_trials if t.get("status") in ["RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"]]
    completed_trials = [t for t in db_trials if t.get("status") == "COMPLETED"]

    # Count phases
    phases_summary = {}
    for t in db_trials:
        phase = t.get("phase", "Unknown")
        phases_summary[phase] = phases_summary.get(phase, 0) + 1

    report = {
        "ticker": ticker,
        "company_name": company["name"],
        "generated_at": datetime.utcnow().isoformat(),
        "sections": {
            "bluf": {
                "summary": f"{company['name']} is a biotechnology company" + (f" developing {lead_asset} for {indication}." if company.get("lead_asset") else "."),
                "investment_thesis": f"Biotech company in XBI ETF" + (f" with {stage} assets." if company.get("stage") else "."),
                "key_catalysts": [
                    "Clinical trial data readouts",
                    "FDA regulatory milestones",
                    "Conference presentations"
                ] if not company.get("lead_asset") else [
                    f"{stage} data readout expected",
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
                "lead_asset": lead_asset if company.get("lead_asset") else None,
                "lead_asset_stage": stage if company.get("stage") else None,
                "lead_asset_indication": indication if company.get("indication") else None,
                "programs": [
                    {
                        "name": lead_asset,
                        "indication": indication,
                        "stage": stage,
                        "description": f"Lead program for {company['name']}"
                    }
                ] if company.get("lead_asset") else [],
                "total_programs": 1 if company.get("lead_asset") else len(db_trials)
            },
            "clinical_trials": {
                "active_trials": [
                    {
                        "trial_id": t["nct_id"],
                        "title": t["title"],
                        "phase": t["phase"],
                        "status": t["status"],
                        "conditions": t["conditions"]
                    } for t in active_trials
                ],
                "completed_trials": [
                    {
                        "trial_id": t["nct_id"],
                        "title": t["title"],
                        "phase": t["phase"]
                    } for t in completed_trials
                ],
                "upcoming_readouts": [],
                "total_trials": len(db_trials),
                "phases_summary": phases_summary if phases_summary else ({stage: 1} if company.get("stage") else {})
            },
            "preclinical": {
                "pubmed_articles": [],
                "conference_posters": [],
                "key_findings": [f"Mechanism targeting {indication}"] if company.get("indication") else [],
                "mechanism_of_action": f"Novel therapeutic approach for {indication}" if company.get("indication") else None
            },
            "patent_legal": {
                "key_patents": [],
                "nearest_expiry": "TBD",
                "litigation": [],
                "regulatory_notes": [f"{stage} development ongoing"] if company.get("stage") else [],
                "recent_filings": [
                    {
                        "form_type": f["form_type"],
                        "filing_date": f["filing_date"],
                        "description": f["description"]
                    } for f in db_filings[:5]
                ]
            },
            "management": {
                "ceo": None,
                "key_executives": [],
                "recent_changes": [],
                "board_highlights": []
            }
        },
        "data_sources": [
            "XBI ETF Holdings",
            "SEC EDGAR",
            "ClinicalTrials.gov"
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


# Database path for enriched data
DB_PATH = Path(__file__).parent / "data" / "helix.db"


def get_db_connection():
    """Get SQLite database connection"""
    import sqlite3
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/search")
async def search_companies(q: str, limit: int = 20):
    """Search companies by ticker or name"""
    conn = get_db_connection()
    if not conn:
        # Fallback to in-memory data
        results = [c for c in TRACKED_COMPANIES.values()
                   if q.upper() in c["ticker"] or q.lower() in c["name"].lower()]
        return {"query": q, "results": results[:limit]}

    cur = conn.cursor()
    cur.execute("""
        SELECT ticker, name, cik, sic_description, xbi_weight
        FROM companies
        WHERE ticker LIKE ? OR name LIKE ?
        ORDER BY xbi_weight DESC NULLS LAST
        LIMIT ?
    """, (f"%{q}%", f"%{q}%", limit))

    results = [dict(row) for row in cur.fetchall()]
    conn.close()

    return {"query": q, "results": results, "count": len(results)}


@app.get("/api/companies/{ticker}/trials")
async def get_company_trials(ticker: str):
    """Get clinical trials for a company"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=404, detail="Database not available")

    cur = conn.cursor()
    cur.execute("""
        SELECT nct_id, title, status, phase, conditions, interventions,
               sponsor, start_date, completion_date, enrollment, study_type
        FROM clinical_trials
        WHERE company_ticker = ?
        ORDER BY start_date DESC
    """, (ticker.upper(),))

    trials = []
    for row in cur.fetchall():
        trial = dict(row)
        trial["conditions"] = json.loads(trial["conditions"]) if trial["conditions"] else []
        trial["interventions"] = json.loads(trial["interventions"]) if trial["interventions"] else []
        trials.append(trial)

    conn.close()

    return {
        "ticker": ticker.upper(),
        "trials": trials,
        "count": len(trials)
    }


@app.get("/api/companies/{ticker}/filings")
async def get_company_filings(ticker: str, form_type: Optional[str] = None):
    """Get SEC filings for a company"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=404, detail="Database not available")

    cur = conn.cursor()

    if form_type:
        cur.execute("""
            SELECT accession_number, form_type, filing_date, description, filing_url
            FROM sec_filings
            WHERE company_ticker = ? AND form_type = ?
            ORDER BY filing_date DESC
        """, (ticker.upper(), form_type))
    else:
        cur.execute("""
            SELECT accession_number, form_type, filing_date, description, filing_url
            FROM sec_filings
            WHERE company_ticker = ?
            ORDER BY filing_date DESC
        """, (ticker.upper(),))

    filings = [dict(row) for row in cur.fetchall()]
    conn.close()

    return {
        "ticker": ticker.upper(),
        "filings": filings,
        "count": len(filings)
    }


@app.get("/api/trials")
async def list_trials(
    status: Optional[str] = None,
    phase: Optional[str] = None,
    limit: int = 50
):
    """List all clinical trials with optional filters"""
    conn = get_db_connection()
    if not conn:
        return {"trials": [], "count": 0}

    cur = conn.cursor()

    query = "SELECT * FROM clinical_trials WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if phase:
        query += " AND phase = ?"
        params.append(phase)

    query += " ORDER BY start_date DESC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)

    trials = []
    for row in cur.fetchall():
        trial = dict(row)
        trial["conditions"] = json.loads(trial["conditions"]) if trial["conditions"] else []
        trial["interventions"] = json.loads(trial["interventions"]) if trial["interventions"] else []
        trials.append(trial)

    conn.close()

    return {"trials": trials, "count": len(trials)}


@app.get("/api/filings")
async def list_filings(
    form_type: Optional[str] = None,
    days: int = 30,
    limit: int = 50
):
    """List recent SEC filings with optional filters"""
    conn = get_db_connection()
    if not conn:
        return {"filings": [], "count": 0}

    cur = conn.cursor()

    cutoff_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    query = "SELECT * FROM sec_filings WHERE filing_date >= ?"
    params = [cutoff_date]

    if form_type:
        query += " AND form_type = ?"
        params.append(form_type)

    query += " ORDER BY filing_date DESC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    filings = [dict(row) for row in cur.fetchall()]
    conn.close()

    return {"filings": filings, "count": len(filings)}


@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    conn = get_db_connection()
    if not conn:
        return {
            "companies": len(TRACKED_COMPANIES),
            "trials": 0,
            "filings": 0,
            "database": "not initialized"
        }

    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM companies")
    companies = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM clinical_trials")
    trials = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sec_filings")
    filings = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT phase) FROM clinical_trials")
    phases = cur.fetchone()[0]

    conn.close()

    return {
        "companies": companies,
        "clinical_trials": trials,
        "sec_filings": filings,
        "trial_phases": phases,
        "database": "helix.db"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
