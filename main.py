"""
Biotech Intelligence Platform - Main Entry Point

This is the orchestration layer that ties together:
- 13F ownership scraping
- Excel workbook generation
- Web API (FastAPI)

Usage (CLI):
    python main.py --company ABVX
    python main.py --scrape-13f

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
    allow_origins=["https://satyabio.com", "https://www.satyabio.com", "http://localhost:8000", "http://localhost:3000"],
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
from app.routers import auth_router, documents_router, admin_router, sources_router, citations_router, services_router, clinical_router, extract_router
from app.routers.company import router as company_router

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(sources_router, prefix="/api/sources", tags=["Sources"])
app.include_router(citations_router, prefix="/api/citations", tags=["Citations"])
app.include_router(company_router, prefix="/api/company", tags=["Company"])
app.include_router(services_router, prefix="/api/services", tags=["Services"])
app.include_router(clinical_router, prefix="/api/clinical", tags=["Clinical"])
app.include_router(extract_router, prefix="/extract", tags=["Extract"])

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
    generate_target_detail_page,
    generate_about_page,
    generate_company_detail,
    generate_glp1_report,
    generate_tl1a_report,
    generate_b7h3_report,
    generate_kras_report,
)
from fastapi.responses import RedirectResponse

@app.get("/companies/ARWR/thesis", response_class=HTMLResponse)
async def serve_arwr_thesis_clean():
    """Redirect ARWR thesis to new clinical company page."""
    return RedirectResponse(url="/api/clinical/companies/ARWR/html", status_code=301)

@app.get("/companies", response_class=HTMLResponse)
async def serve_companies():
    """Serve companies page with 145 biotech companies."""
    return HTMLResponse(generate_companies_page())

@app.get("/targets", response_class=HTMLResponse)
async def serve_targets():
    """Serve targets/competitive landscapes page."""
    return HTMLResponse(generate_targets_page())

@app.get("/targets/glp1-obesity", response_class=HTMLResponse)
async def serve_glp1_report(admin: bool = False):
    """Serve GLP-1 / Obesity competitive landscape report."""
    return HTMLResponse(generate_glp1_report(admin=admin))

@app.get("/targets/tl1a-ibd", response_class=HTMLResponse)
async def serve_tl1a_report(admin: bool = False):
    """Serve TL1A / IBD competitive landscape report."""
    return HTMLResponse(generate_tl1a_report(admin=admin))

@app.get("/targets/b7h3-adc", response_class=HTMLResponse)
async def serve_b7h3_report(admin: bool = False):
    """Serve B7-H3 / ADC competitive landscape report."""
    return HTMLResponse(generate_b7h3_report(admin=admin))

@app.get("/targets/kras", response_class=HTMLResponse)
async def serve_kras_report():
    """Serve KRAS inhibitor competitive landscape report."""
    return HTMLResponse(generate_kras_report())

@app.get("/targets/{slug}", response_class=HTMLResponse)
async def serve_target_detail(slug: str):
    """Serve individual target detail page from JSON data."""
    html = generate_target_detail_page(slug)
    if html:
        return HTMLResponse(html)
    # Fallback to main targets page if slug not found
    return HTMLResponse(generate_targets_page())

@app.get("/about", response_class=HTMLResponse)
async def serve_about():
    """Serve about page."""
    return HTMLResponse(generate_about_page())

@app.get("/report/{path:path}", response_class=HTMLResponse)
async def serve_report():
    """Redirect to homepage."""
    return FileResponse(BASE_DIR / "index.html")

@app.get("/api/company/ARWR/thesis/html", response_class=HTMLResponse)
async def serve_arwr_thesis():
    """Redirect legacy ARWR thesis URL to new clinical company page."""
    return RedirectResponse(url="/api/clinical/companies/ARWR/html", status_code=301)

@app.get("/api/company/{ticker}/html", response_class=HTMLResponse)
async def serve_company_detail(ticker: str):
    """Serve individual company detail page."""
    return HTMLResponse(generate_company_detail(ticker))

# =============================================================================
# Email Subscription (Gate)
# =============================================================================

import re
import time
from datetime import datetime
from pydantic import BaseModel
from fastapi.responses import JSONResponse

class SubscribeRequest(BaseModel):
    email: str

# Simple in-memory rate limiter: { ip: [timestamp, ...] }
_subscribe_rate: dict[str, list[float]] = {}
_RATE_LIMIT = 5       # max requests
_RATE_WINDOW = 60.0   # per 60 seconds

def _check_rate_limit(ip: str) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    now = time.time()
    timestamps = _subscribe_rate.get(ip, [])
    # Prune old entries
    timestamps = [t for t in timestamps if now - t < _RATE_WINDOW]
    if len(timestamps) >= _RATE_LIMIT:
        _subscribe_rate[ip] = timestamps
        return False
    timestamps.append(now)
    _subscribe_rate[ip] = timestamps
    return True

@app.post("/api/subscribe")
async def subscribe(req: SubscribeRequest, request: Request):
    """Save subscriber email for gated company access."""
    # Rate limit
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again later."})

    email = req.email.strip().lower()

    # Validate: no spaces, has @, has dot after @, under 254 chars
    if (len(email) > 254
        or ' ' in email
        or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email)):
        return JSONResponse(status_code=400, content={"detail": "Invalid email address."})

    subs_path = BASE_DIR / "data" / "subscribers.json"
    subs_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        subs = []
        if subs_path.exists():
            with open(subs_path) as f:
                subs = json.load(f)

        # Deduplicate
        existing_emails = {s["email"] for s in subs}
        if email not in existing_emails:
            print(f"NEW_SUBSCRIBER: {email}")
            subs.append({"email": email, "subscribed_at": datetime.utcnow().isoformat() + "Z"})
            with open(subs_path, "w") as f:
                json.dump(subs, f, indent=2)
    except (IOError, OSError) as e:
        return JSONResponse(status_code=500, content={"detail": "Could not save subscription. Please try again."})

    return {"status": "ok", "message": "Subscribed successfully."}

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


def generate_company_workbook(ticker: str):
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

    elif args.company:
        generate_company_workbook(args.company)

    elif args.demo:
        print("=" * 60)
        print("RUNNING DEMO")
        print("=" * 60)

        # Generate sample workbook
        from src.excel_generator import generate_sample_workbook
        print("\nGenerating sample Excel workbook...")
        filepath = generate_sample_workbook()
        print(f"   Created: {filepath}")

        print("\n" + "=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)
        print(f"\nGenerated files in:")
        print(f"  - data/workbooks/")
        print(f"\nNext steps:")
        print(f"  1. Run --scrape-13f to pull real 13F data")
        print(f"  2. Run --company TICKER to generate full analysis")
        print(f"  3. Run --serve to start the web server")

    else:
        parser.print_help()
        print("\n" + "=" * 60)
        print("QUICK START:")
        print("  python main.py --demo          # Run demo with sample data")
        print("  python main.py --serve         # Start web server")
        print("  python main.py --scrape-13f    # Scrape real 13F filings")
        print("=" * 60)


if __name__ == "__main__":
    main()
