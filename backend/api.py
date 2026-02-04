"""
Helix Intelligence API

FastAPI server exposing biotech intelligence endpoints.
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import sqlite3

# Add parent directory to path for app imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.sec_13f_scraper import SECEdgarScraper, BIOTECH_SPECIALIST_FUNDS
from src.scrapers.pubmed_kol_extractor import PubMedKOLExtractor
from pathlib import Path
import json

app = FastAPI(
    title="Helix Intelligence API",
    description="Biotech investment research platform",
    version="1.0.0"
)

# Include clinical router from main app
try:
    from app.routers import clinical_router
    app.include_router(clinical_router, prefix="/api/clinical", tags=["Clinical"])
except ImportError as e:
    print(f"Warning: Could not import clinical_router: {e}")

# Tracked biotech companies
TRACKED_COMPANIES = {
    "ARWR": {
        "ticker": "ARWR",
        "name": "Arrowhead Pharmaceuticals",
        "description": "Clinical-stage biopharmaceutical company developing RNAi therapeutics using its proprietary TRiM platform",
        "sector": "Biotechnology",
        "lead_asset": "Plozasiran (ARO-APOC3)",
        "indication": "FCS, Severe Hypertriglyceridemia",
        "stage": "Approved (FCS) / Phase 3 (sHTG)",
        "website": "https://arrowheadpharma.com"
    },
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


def load_pipeline_data(ticker: str) -> dict | None:
    """Load enriched pipeline data from JSON file if available, merging in figures."""
    pipeline_path = Path(__file__).parent / "data" / "pipeline_data" / f"{ticker.lower()}.json"
    if not pipeline_path.exists():
        return None

    try:
        with open(pipeline_path) as f:
            data = json.load(f)

        # Also load figures and merge them into programs
        figures_path = Path(__file__).parent / "data" / "figures" / f"{ticker.lower()}.json"
        if figures_path.exists():
            with open(figures_path) as f:
                figures_data = json.load(f)

            # Build a mapping of asset name -> figures (from all trials)
            asset_figures = {}
            for asset_name, asset_data in figures_data.get("assets", {}).items():
                all_figures = []
                for trial_name, trial_data in asset_data.get("trials", {}).items():
                    for fig in trial_data.get("figures", []):
                        fig["trial"] = trial_name
                        all_figures.append(fig)
                if all_figures:
                    asset_figures[asset_name] = all_figures

            # Attach figures to matching programs
            for program in data.get("programs", []):
                program_name = program.get("name", "")
                # Check direct name match
                if program_name in asset_figures:
                    program["figures"] = asset_figures[program_name]
                    continue
                # Check aliases
                for alias in program.get("aliases", []):
                    if alias in asset_figures:
                        program["figures"] = asset_figures[alias]
                        break
                else:
                    # Check if program name starts with or contains asset name
                    for asset_name, figures in asset_figures.items():
                        if program_name.startswith(asset_name) or asset_name in program_name:
                            program["figures"] = figures
                            break

        return data
    except Exception:
        return None

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

# Mount static files for clinical figures
# Figures are stored in the frontend public folder during development
FIGURES_DIR = Path(__file__).parent.parent / "app" / "public" / "figures"
if FIGURES_DIR.exists():
    app.mount("/figures", StaticFiles(directory=str(FIGURES_DIR)), name="figures")


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
    db_management = []

    if conn:
        cur = conn.cursor()
        # Get company info from database
        cur.execute("SELECT * FROM companies WHERE ticker = ?", (ticker,))
        row = cur.fetchone()
        if row:
            db_company = dict(row)

        # Get clinical trials
        cur.execute("""
            SELECT nct_id, title, status, phase, conditions, interventions,
                   sponsor, start_date, completion_date, enrollment
            FROM clinical_trials WHERE company_ticker = ?
            ORDER BY start_date DESC LIMIT 20
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

        # Get management info
        db_management = []
        try:
            cur.execute("""
                SELECT name, title, bio, is_ceo, is_cfo, is_cmo, is_cso
                FROM management WHERE company_ticker = ?
                ORDER BY is_ceo DESC, is_cfo DESC, is_cmo DESC, is_cso DESC, name
            """, (ticker,))
            db_management = [dict(row) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            # Table may not exist yet
            pass

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

    # Load enriched pipeline data if available
    pipeline_data = load_pipeline_data(ticker)

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

    # Build pipeline section - use enriched data if available
    if pipeline_data:
        pipeline_section = {
            "lead_asset": pipeline_data.get("lead_asset"),
            "lead_asset_stage": pipeline_data.get("lead_asset_stage"),
            "lead_asset_indication": pipeline_data.get("lead_asset_indication"),
            "programs": pipeline_data.get("programs", []),
            "total_programs": len(pipeline_data.get("programs", [])),
            "partnerships": pipeline_data.get("partnerships", [])
        }
        # Use enriched company description if available
        if pipeline_data.get("description"):
            company["description"] = pipeline_data["description"]
    else:
        pipeline_section = {
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
            "total_programs": 1 if company.get("lead_asset") else len(db_trials),
            "partnerships": []
        }

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
            "pipeline": pipeline_section,
            "clinical_trials": {
                "active_trials": [
                    {
                        "nct_id": t["nct_id"],
                        "title": t["title"],
                        "phase": t["phase"],
                        "status": t["status"],
                        "conditions": t["conditions"],
                        "interventions": t.get("interventions", []),
                        "sponsor": t.get("sponsor"),
                        "start_date": t.get("start_date"),
                        "completion_date": t.get("completion_date"),
                        "enrollment": t.get("enrollment")
                    } for t in active_trials
                ],
                "completed_trials": [
                    {
                        "nct_id": t["nct_id"],
                        "title": t["title"],
                        "phase": t["phase"],
                        "status": t.get("status", "COMPLETED"),
                        "conditions": t.get("conditions", []),
                        "interventions": t.get("interventions", [])
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
                "ceo": next(
                    ({"name": m["name"], "title": m["title"], "background": m.get("bio")}
                     for m in db_management if m.get("is_ceo")),
                    None
                ),
                "key_executives": [
                    {"name": m["name"], "title": m["title"], "background": m.get("bio")}
                    for m in db_management if not m.get("is_ceo")
                ][:10],
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


@app.post("/api/pipeline/{ticker}/generate-satya-views")
async def generate_satya_views(ticker: str):
    """
    Generate Satya Views (bull/bear thesis + key question) for all pipeline programs
    using Claude API. Requires ANTHROPIC_API_KEY environment variable.
    """
    import os

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not configured. Set environment variable to enable Satya View generation."
        )

    try:
        from services.satya_generator import generate_satya_views_for_company
        data = generate_satya_views_for_company(ticker.upper())
        return {
            "ticker": ticker.upper(),
            "programs_updated": len(data.get("programs", [])),
            "message": "Satya Views generated successfully"
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No pipeline data found for {ticker}")
    except ImportError:
        raise HTTPException(status_code=503, detail="Satya generator service not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pipeline/{ticker}")
async def get_pipeline_data(ticker: str):
    """Get enriched pipeline data for a company (if available)"""
    data = load_pipeline_data(ticker.upper())

    if not data:
        raise HTTPException(status_code=404, detail=f"No pipeline data found for {ticker}")

    return data


@app.get("/api/pipeline/{ticker}/sources")
async def get_pipeline_sources(ticker: str):
    """Get source citations for a company's pipeline data"""
    data = load_pipeline_data(ticker.upper())

    if not data:
        raise HTTPException(status_code=404, detail=f"No pipeline data found for {ticker}")

    return {
        "ticker": ticker.upper(),
        "sources": data.get("sources", []),
        "count": len(data.get("sources", []))
    }


@app.get("/api/figures/{ticker}")
async def get_figures(ticker: str, asset: Optional[str] = None):
    """Get clinical figures for a company"""
    figures_path = Path(__file__).parent / "data" / "figures" / f"{ticker.lower()}.json"

    if not figures_path.exists():
        return {"ticker": ticker.upper(), "assets": {}, "figures": []}

    with open(figures_path) as f:
        data = json.load(f)

    if asset:
        # Return figures for specific asset
        asset_data = data.get("assets", {}).get(asset, {})
        all_figures = []
        for trial_name, trial_data in asset_data.get("trials", {}).items():
            for fig in trial_data.get("figures", []):
                fig["trial"] = trial_name
                all_figures.append(fig)
        return {"ticker": ticker.upper(), "asset": asset, "figures": all_figures}

    return {"ticker": ticker.upper(), **data}


@app.post("/api/figures/{ticker}/extract")
async def extract_figures(
    ticker: str,
    pdf_url: str,
    presentation_name: str,
    asset_name: Optional[str] = None,
    trial_name: Optional[str] = None,
    indication: Optional[str] = None
):
    """
    Extract and optionally annotate figures from a PDF presentation.
    Requires poppler or PyMuPDF for extraction, ANTHROPIC_API_KEY for annotation.
    """
    try:
        from services.figure_extractor import extract_figures_from_pdf, get_extraction_status

        status = get_extraction_status()
        if not status["ready"]:
            raise HTTPException(
                status_code=503,
                detail="PDF extraction not available. Install pdf2image or PyMuPDF."
            )

        result = extract_figures_from_pdf(
            pdf_url=pdf_url,
            ticker=ticker.upper(),
            presentation_name=presentation_name
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        # Optionally annotate with Claude Vision
        if asset_name and os.getenv("ANTHROPIC_API_KEY"):
            from services.figure_annotator import annotate_presentation_figures, save_annotations

            annotations = annotate_presentation_figures(
                extraction_result=result,
                asset_name=asset_name,
                trial_name=trial_name or presentation_name,
                indication=indication or "Unknown"
            )

            save_annotations(ticker.upper(), annotations)
            result["annotations"] = annotations

        return result

    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Service not available: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/company/{ticker}/thesis/html")
async def get_investment_thesis_html(ticker: str):
    """
    Generate comprehensive investment thesis HTML page.
    Uses verified data from FDA, ClinicalTrials.gov, and company sources.
    """
    from fastapi.responses import HTMLResponse
    try:
        from services.thesis_generator import generate_thesis
        html_content = generate_thesis(ticker.upper())
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/company/{ticker}/refresh")
async def refresh_company_data(ticker: str):
    """
    Refresh company data from all authoritative sources:
    - FDA approval status (OpenFDA API)
    - Clinical trial status (ClinicalTrials.gov API)
    - IR news (company press releases)
    """
    try:
        from services.company_refresher import CompanyRefresher
        refresher = CompanyRefresher(verbose=False)
        result = refresher.refresh(ticker.upper())
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No pipeline data found for {ticker}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FullRefreshRequest(BaseModel):
    months_back: int = 12
    max_presentations: int = 10
    skip_vision: bool = False


@app.post("/api/company/{ticker}/full-refresh")
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


@app.get("/api/company/{ticker}/data-sources")
async def get_company_data_sources(ticker: str):
    """
    Get information about all data sources used for a company.
    Returns IR page info, presentations found, analysis status, and verification status.
    """
    ticker = ticker.upper()
    company_dir = Path(__file__).parent / "data" / "companies" / ticker.lower()

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
        legacy_path = Path(__file__).parent / "data" / "pipeline_data" / f"{ticker.lower()}.json"
        if legacy_path.exists():
            with open(legacy_path) as f:
                legacy_data = json.load(f)
                result["normalized_data"] = {
                    "normalized_at": legacy_data.get("last_updated"),
                    "pipeline_count": len(legacy_data.get("programs", [])),
                    "sources": legacy_data.get("sources", [])
                }

    return result


@app.get("/api/company/{ticker}/normalized")
async def get_normalized_data(ticker: str):
    """
    Get normalized company data from automated IR ingestion.
    This is the merged, deduplicated data from all analyzed presentations.
    """
    ticker = ticker.upper()
    company_dir = Path(__file__).parent / "data" / "companies" / ticker.lower()
    norm_path = company_dir / "normalized.json"

    if not norm_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No normalized data for {ticker}. Run POST /api/company/{ticker}/full-refresh first."
        )

    with open(norm_path) as f:
        return json.load(f)


# ===========================================================================
# HTML Page Routes (from main app)
# ===========================================================================

@app.get("/companies", response_class=HTMLResponse)
@app.get("/companies/{path:path}", response_class=HTMLResponse)
async def serve_companies():
    """Serve companies page with 181 biotech companies."""
    try:
        from app.pages import generate_companies_page
        return HTMLResponse(generate_companies_page())
    except ImportError as e:
        return HTMLResponse(f"<html><body><h1>Error loading companies page</h1><p>{e}</p></body></html>")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
