"""
Biotech Intelligence Platform - Main Entry Point

This is the orchestration layer that ties together:
- 13F ownership scraping
- KOL extraction from PubMed
- Excel workbook generation
- Web API (FastAPI)

Usage (CLI):
    python main.py --company ABVX
    python main.py --scrape-13f
    python main.py --find-kols "obefazimod ulcerative colitis"

Usage (Web Server):
    python main.py --serve
    # or: uvicorn main:app --reload
"""

import argparse
from pathlib import Path
from datetime import date
import json

# FastAPI imports
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Local imports for CLI
from src.scrapers.sec_13f_scraper import (
    SECEdgarScraper,
    BIOTECH_SPECIALIST_FUNDS,
    scrape_all_specialist_funds
)
from src.scrapers.holdings_analyzer import (
    generate_summary_report,
    export_to_csv,
    load_filings_from_json
)
from src.scrapers.pubmed_kol_extractor import PubMedKOLExtractor
from src.excel_generator import ExcelWorkbookGenerator, CompanyData

# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Helix API",
    description="Biotech Competitive Intelligence Platform",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Note: Frontend is served from root index.html (SatyaBio SPA)

# Templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    from app.database import init_db
    init_db()

# Include API routers
from app.routers import auth_router, documents_router, admin_router, sources_router, citations_router
from app.routers.company import router as company_router

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(sources_router, prefix="/api/sources", tags=["Sources"])
app.include_router(citations_router, prefix="/api/citations", tags=["Citations"])
app.include_router(company_router, prefix="/api/company", tags=["Company"])

# =============================================================================
# Frontend Routes
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the main landing page."""
    return FileResponse(BASE_DIR / "index.html")

@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    """Serve the login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    """Serve the user dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def serve_admin(request: Request):
    """Serve the admin panel."""
    return templates.TemplateResponse("admin.html", {"request": request})


# Import page generators
from app.pages import (
    generate_companies_page,
    generate_targets_page,
    generate_kols_page,
    generate_about_page,
    generate_company_detail,
    generate_glp1_report,
    generate_tl1a_report,
    generate_b7h3_report,
)

@app.get("/companies", response_class=HTMLResponse)
@app.get("/companies/{path:path}", response_class=HTMLResponse)
async def serve_companies():
    """Serve companies page with 145 biotech companies."""
    return HTMLResponse(generate_companies_page())

@app.get("/targets/glp1-obesity", response_class=HTMLResponse)
async def serve_glp1_report():
    """Serve GLP-1 / Obesity competitive landscape report."""
    return HTMLResponse(generate_glp1_report())

@app.get("/targets/tl1a-ibd", response_class=HTMLResponse)
async def serve_tl1a_report():
    """Serve TL1A / IBD competitive landscape report."""
    return HTMLResponse(generate_tl1a_report())

@app.get("/targets/b7h3-adc", response_class=HTMLResponse)
async def serve_b7h3_report():
    """Serve B7-H3 / ADC competitive landscape report."""
    return HTMLResponse(generate_b7h3_report())

@app.get("/targets", response_class=HTMLResponse)
@app.get("/targets/{path:path}", response_class=HTMLResponse)
async def serve_targets():
    """Serve targets/competitive landscapes page."""
    return HTMLResponse(generate_targets_page())

@app.get("/kols", response_class=HTMLResponse)
async def serve_kols():
    """Serve KOL Finder page."""
    return HTMLResponse(generate_kols_page())

@app.get("/research", response_class=HTMLResponse)
async def serve_research():
    """Redirect to companies for now."""
    return HTMLResponse(generate_companies_page())

@app.get("/about", response_class=HTMLResponse)
async def serve_about():
    """Serve about page."""
    return HTMLResponse(generate_about_page())

@app.get("/report/{path:path}", response_class=HTMLResponse)
async def serve_report():
    """Redirect to homepage."""
    return FileResponse(BASE_DIR / "index.html")

@app.get("/api/company/{ticker}/html", response_class=HTMLResponse)
async def serve_company_detail(ticker: str):
    """Serve individual company detail page."""
    return HTMLResponse(generate_company_detail(ticker))

# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}

# =============================================================================
# CLI Functions
# =============================================================================

def scrape_13f_filings(num_quarters: int = 1):
    """Scrape 13F filings from biotech specialist funds"""
    print("=" * 60)
    print("SCRAPING 13F FILINGS")
    print("=" * 60)

    filings = scrape_all_specialist_funds(num_quarters)

    print(f"\nScraped {len(filings)} filings")
    return filings


def analyze_13f_holdings():
    """Analyze scraped 13F holdings and generate report"""
    print("=" * 60)
    print("ANALYZING 13F HOLDINGS")
    print("=" * 60)

    report = generate_summary_report()

    if "error" in report:
        print(f"Error: {report['error']}")
        return None

    # Print summary
    print(f"\nFunds analyzed: {len(report['funds_analyzed'])}")
    print(f"Total holdings analyzed: {report['total_holdings_analyzed']}")

    print("\n" + "-" * 40)
    print("TOP CONSENSUS POSITIONS")
    print("-" * 40)

    for ticker, data in list(report["consensus_positions"].items())[:10]:
        if data["specialist_fund_count"] >= 2:
            direction_emoji = "📈" if data["consensus_direction"] == "ACCUMULATING" else "📉" if data["consensus_direction"] == "DISTRIBUTING" else "➡️"
            print(f"\n{ticker} - {data['company_name'][:30]}")
            print(f"  {direction_emoji} {data['specialist_fund_count']} funds | ${data['total_value_mm']}M | {data['consensus_direction']}")

    # Export
    export_to_csv(report)

    # Save full report as JSON
    report_path = Path("data/reports/full_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nFull report saved to {report_path}")

    return report


def find_kols(query: str, max_results: int = 100):
    """Find KOLs for a given search query"""
    print("=" * 60)
    print(f"FINDING KOLs: {query}")
    print("=" * 60)

    extractor = PubMedKOLExtractor()
    kols = extractor.find_kols(query, max_publications=max_results)

    print(f"\nFound {len(kols)} KOLs")
    print("\nTOP 10:")
    print("-" * 40)

    for i, kol in enumerate(kols[:10], 1):
        email_status = "✅" if kol.email else "❌"
        print(f"{i}. {kol.name}")
        print(f"   {kol.institution or 'Unknown institution'}")
        print(f"   {email_status} {kol.email or 'No email found'}")
        print(f"   {kol.publication_count} pubs | Score: {kol.relevance_score:.1f}")

    # Export
    output_dir = Path("data/kols")
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = query.replace(" ", "_").lower()[:50]
    extractor.export_kols_to_csv(kols, output_dir / f"{safe_name}_kols.csv", query)
    extractor.export_kols_to_json(kols, output_dir / f"{safe_name}_kols.json", query)

    return kols


def generate_company_workbook(ticker: str, include_kols: bool = True):
    """Generate an Excel workbook for a company"""
    print("=" * 60)
    print(f"GENERATING WORKBOOK: {ticker}")
    print("=" * 60)

    # For now, use sample data structure
    # In production, this would pull from database

    company = CompanyData(
        ticker=ticker,
        name=f"{ticker} Inc.",  # Would be looked up
        description="Company description would be populated from database.",
    )

    # Try to load ownership data if available
    report_path = Path("data/reports/full_report.json")
    if report_path.exists():
        with open(report_path) as f:
            report = json.load(f)

        if ticker in report.get("consensus_positions", {}):
            consensus = report["consensus_positions"][ticker]
            company.name = consensus["company_name"]
            company.ownership = consensus.get("funds", [])

    generator = ExcelWorkbookGenerator()
    filepath = generator.generate(company)

    print(f"\nWorkbook generated: {filepath}")
    return filepath


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the FastAPI server."""
    import uvicorn
    print("=" * 60)
    print(f"STARTING HELIX SERVER")
    print(f"Running on http://{host}:{port}")
    print("=" * 60)
    uvicorn.run("main:app", host=host, port=port, reload=reload)


def main():
    parser = argparse.ArgumentParser(description="Biotech Intelligence Platform")

    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the web server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for web server (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--scrape-13f",
        action="store_true",
        help="Scrape 13F filings from biotech specialist funds"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze scraped 13F holdings"
    )
    parser.add_argument(
        "--find-kols",
        type=str,
        metavar="QUERY",
        help="Find KOLs for a search query (e.g., 'obefazimod ulcerative colitis')"
    )
    parser.add_argument(
        "--company",
        type=str,
        metavar="TICKER",
        help="Generate workbook for a company ticker"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo with sample data"
    )

    args = parser.parse_args()

    if args.serve:
        run_server(port=args.port, reload=args.reload)

    elif args.scrape_13f:
        scrape_13f_filings()
        analyze_13f_holdings()

    elif args.analyze:
        analyze_13f_holdings()

    elif args.find_kols:
        find_kols(args.find_kols)

    elif args.company:
        generate_company_workbook(args.company)

    elif args.demo:
        print("=" * 60)
        print("RUNNING DEMO")
        print("=" * 60)

        # 1. Generate sample workbook
        from src.excel_generator import generate_sample_workbook
        print("\n1. Generating sample Excel workbook...")
        filepath = generate_sample_workbook()
        print(f"   Created: {filepath}")

        # 2. Demo KOL search (limited)
        print("\n2. Demo KOL search (obefazimod)...")
        kols = find_kols("obefazimod ulcerative colitis", max_results=20)

        print("\n" + "=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)
        print(f"\nGenerated files in:")
        print(f"  - data/workbooks/")
        print(f"  - data/kols/")
        print(f"\nNext steps:")
        print(f"  1. Run --scrape-13f to pull real 13F data")
        print(f"  2. Run --find-kols 'drug indication' for any drug")
        print(f"  3. Run --company TICKER to generate full analysis")
        print(f"  4. Run --serve to start the web server")

    else:
        parser.print_help()
        print("\n" + "=" * 60)
        print("QUICK START:")
        print("  python main.py --demo          # Run demo with sample data")
        print("  python main.py --serve         # Start web server")
        print("  python main.py --scrape-13f    # Scrape real 13F filings")
        print("  python main.py --find-kols 'GLP-1 obesity'  # Find KOLs")
        print("=" * 60)


if __name__ == "__main__":
    main()
