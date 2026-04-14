"""
Ownership & 13F Intelligence Router

Endpoints for institutional ownership tracking:
- Biotech specialist fund listings
- XBI ETF holdings
- SEC 13F filing lookups
- KOL (Key Opinion Leader) search via PubMed
- Database statistics
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import json

router = APIRouter()

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
BACKEND_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "backend" / "data"


def _load_json(path: Path) -> dict | list | None:
    """Safely load a JSON file, returning None if missing or invalid."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _get_xbi_holdings_path() -> Path | None:
    """Find XBI holdings JSON — check root data/ first, then backend/data/."""
    for base in [DATA_DIR, BACKEND_DATA_DIR]:
        path = base / "xbi_holdings.json"
        if path.exists():
            return path
    return None


# ---------------------------------------------------------------------------
# /api/ownership/funds — Specialist fund list
# ---------------------------------------------------------------------------

@router.get("/funds")
async def get_specialist_funds():
    """Get list of tracked biotech specialist hedge funds that file 13F."""
    from src.scrapers.sec_13f_scraper import BIOTECH_SPECIALIST_FUNDS

    return {
        "funds": [
            {"name": f.name, "cik": f.cik, "is_specialist": f.is_biotech_specialist}
            for f in BIOTECH_SPECIALIST_FUNDS
        ],
        "count": len(BIOTECH_SPECIALIST_FUNDS),
    }


# ---------------------------------------------------------------------------
# /api/ownership/xbi — XBI ETF holdings
# ---------------------------------------------------------------------------

@router.get("/xbi")
async def get_xbi_holdings():
    """
    Get SPDR S&P Biotech ETF (XBI) holdings.
    Returns the full holdings list with weights.
    """
    path = _get_xbi_holdings_path()
    if path:
        data = _load_json(path)
        if data:
            return data

    # Fallback — return a stub so the frontend doesn't break
    return {
        "etf": "XBI",
        "name": "SPDR S&P Biotech ETF",
        "holdings_count": 0,
        "holdings": [],
        "note": "XBI holdings not yet scraped. Run the fetch_xbi_holdings script.",
    }


# ---------------------------------------------------------------------------
# /api/ownership/13f/{fund_name} — Individual fund 13F holdings
# ---------------------------------------------------------------------------

@router.get("/13f/{fund_name}")
async def get_fund_holdings(fund_name: str):
    """
    Get the most recent 13F holdings for a specific biotech specialist fund.
    Searches by partial fund name match.
    """
    from src.scrapers.sec_13f_scraper import SECEdgarScraper, BIOTECH_SPECIALIST_FUNDS

    # Find fund by partial name match
    fund = None
    for f in BIOTECH_SPECIALIST_FUNDS:
        if fund_name.lower() in f.name.lower():
            fund = f
            break

    if not fund:
        raise HTTPException(status_code=404, detail=f"Fund '{fund_name}' not found")

    try:
        scraper = SECEdgarScraper()
        filings = scraper.get_13f_filings(fund.cik, num_quarters=1)
        return {
            "fund": fund.name,
            "cik": fund.cik,
            "filings": filings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching 13F data: {e}")


# ---------------------------------------------------------------------------
# /api/ownership/13f/consensus — Cross-fund consensus positions
# ---------------------------------------------------------------------------

@router.get("/13f/consensus")
async def get_consensus_positions():
    """
    Analyze 13F holdings across all specialist funds to find consensus positions.
    Returns the full report if available, or triggers a fresh analysis.
    """
    report_path = DATA_DIR / "reports" / "full_report.json"
    if report_path.exists():
        data = _load_json(report_path)
        if data:
            return data

    # No cached report — try to generate one
    try:
        from src.scrapers.holdings_analyzer import generate_summary_report
        report = generate_summary_report()
        if "error" in report:
            raise HTTPException(status_code=500, detail=report["error"])
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {e}")


# ---------------------------------------------------------------------------
# /api/ownership/kols/search — Key Opinion Leader lookup
# ---------------------------------------------------------------------------

class KOLSearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10


@router.post("/kols/search")
async def search_kols(request: KOLSearchRequest):
    """
    Search PubMed for Key Opinion Leaders (KOLs) on a drug or indication.
    Returns top authors by publication count with affiliations.
    """
    try:
        from src.scrapers.pubmed_kol_extractor import PubMedKOLExtractor

        extractor = PubMedKOLExtractor()
        kols = extractor.find_kols(request.query, max_results=request.max_results)
        return {
            "query": request.query,
            "kols": kols,
            "count": len(kols),
        }
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="KOL search not available — pubmed_kol_extractor not found.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# /api/ownership/stats — Database statistics
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_stats():
    """Get high-level database statistics (companies, trials, filings)."""
    import sqlite3

    db_path = DATA_DIR / "helix.db" if (DATA_DIR / "helix.db").exists() else BACKEND_DATA_DIR / "helix.db"
    if not db_path.exists():
        return {
            "companies": 0,
            "clinical_trials": 0,
            "sec_filings": 0,
            "database": "not found",
        }

    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM companies")
        companies = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM clinical_trials")
        trials = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sec_filings")
        filings = cur.fetchone()[0]

        conn.close()

        return {
            "companies": companies,
            "clinical_trials": trials,
            "sec_filings": filings,
            "database": str(db_path.name),
        }
    except Exception as e:
        return {"error": str(e), "database": "error"}
