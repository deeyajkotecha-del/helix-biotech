#!/usr/bin/env python3
"""
Batch Scraper for New Helix Biotech Tickers

Scrapes IR pages for presentations, events, posters, and publications
for all newly added tickers. Uses the existing IRScraper + PresentationScraper.

Also scrapes:
- SEC EDGAR filings (10-K, 10-Q, 8-K) — free API, no key
- ClinicalTrials.gov — active trials via v2 API
- PubMed — published research abstracts

Outputs cataloged results per company into data/companies/{TICKER}/sources/
"""

import sys
import os
import json
import time
import asyncio
import re
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse, quote

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "companies"
DOWNLOADS_DIR = PROJECT_ROOT / "data" / "downloads"

# Add paths for imports
sys.path.insert(0, str(PROJECT_ROOT / "app" / "services" / "scrapers"))
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "services"))

# Import our scrapers
try:
    from ir_scraper import IRScraper, scrape_presentation_links
    IR_SCRAPER_AVAILABLE = True
except ImportError as e:
    print(f"⚠ IR scraper not available: {e}")
    IR_SCRAPER_AVAILABLE = False

try:
    from presentation_scraper import PresentationScraper
    PRESENTATION_SCRAPER_AVAILABLE = True
except ImportError as e:
    print(f"⚠ Presentation scraper not available: {e}")
    PRESENTATION_SCRAPER_AVAILABLE = False


# ============================================================================
# Browser headers
# ============================================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SEC_HEADERS = {
    "User-Agent": "SatyaBio Research research@satyabio.com",
    "Accept-Encoding": "gzip, deflate",
}


# ============================================================================
# Target tickers — load from company.json files
# ============================================================================
NEW_TICKERS = [
    "AUTL", "ANNX", "PRAX", "CLDX", "AXSM", "DYN", "MBX", "RAPT",
    "AGIO", "IMVT", "ALKS", "FOLD", "HRMY", "KRYS", "MPLT", "SLN"
]


def load_company_info(ticker: str) -> dict:
    """Load company.json for a ticker."""
    company_file = DATA_DIR / ticker / "company.json"
    if not company_file.exists():
        return {}
    with open(company_file) as f:
        return json.load(f)


# ============================================================================
# 1. IR Presentations Scraper (using existing IRScraper)
# ============================================================================
def scrape_ir_presentations(ticker: str, config: dict) -> list:
    """Scrape IR presentations page for PDFs."""
    results = []

    if IR_SCRAPER_AVAILABLE:
        try:
            links = scrape_presentation_links(ticker, max_results=10)
            for link in links:
                results.append({
                    "type": "presentation",
                    "title": link.get("title", ""),
                    "url": link.get("url", ""),
                    "date": link.get("date"),
                    "source": "ir_page",
                    "scraped_at": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"    ⚠ IR scraper error: {e}")

    return results


# ============================================================================
# 2. Events & Presentations Page (async scraper)
# ============================================================================
async def scrape_events_presentations(ticker: str, ir_url: str) -> list:
    """Scrape events and presentations using async scraper."""
    results = []

    if not PRESENTATION_SCRAPER_AVAILABLE or not ir_url:
        return results

    try:
        async with PresentationScraper() as scraper:
            presentations = await scraper.scrape(ir_url, months_back=18)
            for pres in presentations:
                results.append({
                    "type": pres.get("type", "presentation"),
                    "title": pres.get("title", ""),
                    "url": pres.get("url", ""),
                    "date": pres.get("date"),
                    "source": "events_page",
                    "classification": pres.get("type"),
                    "scraped_at": datetime.now().isoformat()
                })
    except Exception as e:
        print(f"    ⚠ Events scraper error: {e}")

    return results


# ============================================================================
# 3. SEC EDGAR Filings (no API key needed)
# ============================================================================
def scrape_sec_filings(ticker: str, filing_types: list = None, max_filings: int = 10) -> list:
    """Scrape recent SEC filings from EDGAR."""
    if filing_types is None:
        filing_types = ["10-K", "10-Q", "8-K", "S-1", "DEF 14A"]

    results = []

    try:
        # EDGAR company search API
        url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2024-01-01&enddt={datetime.now().strftime('%Y-%m-%d')}&forms={','.join(filing_types)}"

        # Simpler approach: use EDGAR full-text search
        search_url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms={','.join(filing_types)}&dateRange=custom&startdt=2025-01-01"

        # Use the CIK-based approach instead
        cik_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=&CIK={ticker}&type=10-K&dateb=&owner=include&count=10&search_text=&action=getcompany"

        # Better: use EDGAR submissions API
        # First, get the CIK from ticker
        ticker_url = f"https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}&CIK={ticker}&type=&dateb=&owner=include&count=10&search_text=&action=getcompany"

        # Try the EDGAR XBRL companyfacts endpoint (most reliable)
        tickers_url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(tickers_url, headers=SEC_HEADERS, timeout=15)
        if resp.status_code == 200:
            tickers_data = resp.json()
            cik = None
            for entry in tickers_data.values():
                if entry.get("ticker", "").upper() == ticker.upper():
                    cik = str(entry["cik_str"]).zfill(10)
                    break

            if cik:
                # Get recent filings via submissions endpoint
                submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
                resp2 = requests.get(submissions_url, headers=SEC_HEADERS, timeout=15)
                if resp2.status_code == 200:
                    sub_data = resp2.json()
                    recent = sub_data.get("filings", {}).get("recent", {})
                    forms = recent.get("form", [])
                    dates = recent.get("filingDate", [])
                    accessions = recent.get("accessionNumber", [])
                    primary_docs = recent.get("primaryDocument", [])

                    count = 0
                    for i in range(min(len(forms), 100)):
                        if forms[i] in filing_types and count < max_filings:
                            acc_clean = accessions[i].replace("-", "")
                            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc_clean}/{primary_docs[i]}"
                            results.append({
                                "type": "sec_filing",
                                "filing_type": forms[i],
                                "title": f"{ticker} {forms[i]} — {dates[i]}",
                                "url": filing_url,
                                "date": dates[i],
                                "accession": accessions[i],
                                "source": "sec_edgar",
                                "scraped_at": datetime.now().isoformat()
                            })
                            count += 1
            else:
                print(f"    ⚠ Could not find CIK for {ticker}")
        time.sleep(0.15)  # SEC rate limit: 10 req/sec

    except Exception as e:
        print(f"    ⚠ SEC scraper error: {e}")

    return results


# ============================================================================
# 4. ClinicalTrials.gov (v2 API, no key needed)
# ============================================================================
def scrape_clinical_trials(company_name: str, ticker: str) -> list:
    """Search ClinicalTrials.gov for active trials by company."""
    results = []

    try:
        # ClinicalTrials.gov v2 API
        params = {
            "query.spons": company_name,
            "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,NOT_YET_RECRUITING",
            "pageSize": 20,
            "format": "json",
            "fields": "NCTId,BriefTitle,OverallStatus,Phase,StartDate,PrimaryCompletionDate,EnrollmentCount,Condition,InterventionName,StudyType",
        }

        url = "https://clinicaltrials.gov/api/v2/studies"
        resp = requests.get(url, params=params, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            studies = data.get("studies", [])

            for study in studies:
                proto = study.get("protocolSection", {})
                ident = proto.get("identificationModule", {})
                status = proto.get("statusModule", {})
                design = proto.get("designModule", {})
                conds = proto.get("conditionsModule", {})
                interventions = proto.get("armsInterventionsModule", {})

                nct_id = ident.get("nctId", "")
                title = ident.get("briefTitle", "")
                phase_list = design.get("phases", [])
                phase = ", ".join(phase_list) if phase_list else "N/A"
                conditions = ", ".join(conds.get("conditions", [])[:3])

                # Get intervention names
                intv_names = []
                for intv in interventions.get("interventions", []):
                    intv_names.append(intv.get("name", ""))

                results.append({
                    "type": "clinical_trial",
                    "nct_id": nct_id,
                    "title": title,
                    "phase": phase,
                    "status": status.get("overallStatus", ""),
                    "conditions": conditions,
                    "interventions": ", ".join(intv_names[:3]),
                    "enrollment": status.get("enrollmentInfo", {}).get("count"),
                    "start_date": status.get("startDateStruct", {}).get("date"),
                    "completion_date": status.get("primaryCompletionDateStruct", {}).get("date"),
                    "url": f"https://clinicaltrials.gov/study/{nct_id}",
                    "source": "clinicaltrials_gov",
                    "scraped_at": datetime.now().isoformat()
                })

        time.sleep(0.5)  # Be polite

    except Exception as e:
        print(f"    ⚠ ClinicalTrials.gov scraper error: {e}")

    return results


# ============================================================================
# 5. PubMed Abstracts (NCBI E-utilities, free)
# ============================================================================
def scrape_pubmed(company_name: str, drug_names: list, max_results: int = 10) -> list:
    """Search PubMed for published research about a company's drugs."""
    results = []
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    # Build search queries from drug names and company name
    queries = [f'"{company_name}"[Affiliation] OR "{company_name}"[Title/Abstract]']
    for drug in drug_names[:3]:  # Cap at 3 drug queries
        if drug and len(drug) > 3:
            queries.append(f'"{drug}"[Title/Abstract]')

    seen_pmids = set()

    for query in queries:
        try:
            # Search
            search_url = f"{base_url}/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "date",
                "mindate": "2024/01/01",
                "maxdate": datetime.now().strftime("%Y/%m/%d"),
                "datetype": "pdat"
            }
            resp = requests.get(search_url, params=params, timeout=10)
            if resp.status_code != 200:
                continue

            search_data = resp.json()
            pmids = search_data.get("esearchresult", {}).get("idlist", [])

            if not pmids:
                continue

            # Filter out already seen
            new_pmids = [p for p in pmids if p not in seen_pmids]
            if not new_pmids:
                continue
            seen_pmids.update(new_pmids)

            # Fetch summaries
            summary_url = f"{base_url}/esummary.fcgi"
            params = {
                "db": "pubmed",
                "id": ",".join(new_pmids),
                "retmode": "json",
            }
            resp2 = requests.get(summary_url, params=params, timeout=10)
            if resp2.status_code != 200:
                continue

            summary_data = resp2.json().get("result", {})

            for pmid in new_pmids:
                article = summary_data.get(pmid, {})
                if not article or pmid == "uids":
                    continue

                title = article.get("title", "")
                journal = article.get("fulljournalname", article.get("source", ""))
                pub_date = article.get("pubdate", "")
                authors = article.get("authors", [])
                author_str = ", ".join([a.get("name", "") for a in authors[:3]])
                if len(authors) > 3:
                    author_str += " et al."

                results.append({
                    "type": "publication",
                    "pmid": pmid,
                    "title": title,
                    "journal": journal,
                    "authors": author_str,
                    "date": pub_date,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "source": "pubmed",
                    "scraped_at": datetime.now().isoformat()
                })

            time.sleep(0.4)  # NCBI rate limit: 3 req/sec without API key

        except Exception as e:
            print(f"    ⚠ PubMed error for query '{query[:50]}': {e}")

    return results


# ============================================================================
# 6. Conference Posters (search for ASCO, AAD, AAN, ACR, etc.)
# ============================================================================
def scrape_conference_posters(company_name: str, drug_names: list) -> list:
    """
    Search for conference posters and abstracts.
    Uses PubMed with conference-specific keywords.
    """
    results = []
    conferences = ["ASCO", "AACR", "AAD", "AAN", "ACR", "ASH", "ESMO", "EHA", "SITC", "SABCS", "AHA", "ADA"]
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    # Build queries combining drug names with conference names
    queries = []
    for drug in drug_names[:3]:
        if drug and len(drug) > 3:
            conf_terms = " OR ".join([f'"{c}"' for c in conferences])
            queries.append(f'("{drug}") AND ({conf_terms}) AND ("2024"[PDAT] : "2026"[PDAT])')

    seen_pmids = set()

    for query in queries[:2]:  # Cap to avoid rate limits
        try:
            search_url = f"{base_url}/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": 10,
                "retmode": "json",
                "sort": "date"
            }
            resp = requests.get(search_url, params=params, timeout=10)
            if resp.status_code != 200:
                continue

            pmids = resp.json().get("esearchresult", {}).get("idlist", [])
            new_pmids = [p for p in pmids if p not in seen_pmids]
            if not new_pmids:
                continue
            seen_pmids.update(new_pmids)

            # Fetch details
            summary_url = f"{base_url}/esummary.fcgi"
            resp2 = requests.get(summary_url, params={"db": "pubmed", "id": ",".join(new_pmids), "retmode": "json"}, timeout=10)
            if resp2.status_code != 200:
                continue

            summary_data = resp2.json().get("result", {})
            for pmid in new_pmids:
                article = summary_data.get(pmid, {})
                if not article or pmid == "uids":
                    continue

                results.append({
                    "type": "conference_poster",
                    "pmid": pmid,
                    "title": article.get("title", ""),
                    "journal": article.get("fulljournalname", article.get("source", "")),
                    "date": article.get("pubdate", ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "source": "pubmed_conference",
                    "scraped_at": datetime.now().isoformat()
                })

            time.sleep(0.4)

        except Exception as e:
            print(f"    ⚠ Conference poster error: {e}")

    return results


# ============================================================================
# Main batch runner
# ============================================================================
def get_drug_names(company_data: dict) -> list:
    """Extract drug/asset names from company data for search queries."""
    names = []
    programs = company_data.get("pipeline_summary", {}).get("programs", [])
    for prog in programs:
        asset = prog.get("asset", "")
        if asset:
            # Extract the clean drug name (handle formats like "Obe-cel (Aucatzyl)")
            names.append(asset)
            # Also extract parenthetical names
            paren_match = re.search(r'\(([^)]+)\)', asset)
            if paren_match:
                names.append(paren_match.group(1))
            # And the name before parentheses
            clean = re.sub(r'\s*\([^)]*\)', '', asset).strip()
            if clean and clean != asset:
                names.append(clean)
    return list(set(names))


async def scrape_ticker(ticker: str, company_data: dict) -> dict:
    """Run all scrapers for a single ticker."""
    company_name = company_data.get("company", {}).get("name", ticker)
    drug_names = get_drug_names(company_data)
    ir_url = company_data.get("company", {}).get("website", "")

    # Get IR presentations URL from mapping
    try:
        from ir_website_mapping import get_ir_config
        ir_config = get_ir_config(ticker)
        presentations_url = ir_config.get("presentations_url", "") if ir_config else ""
    except:
        presentations_url = ""

    all_results = {
        "ticker": ticker,
        "company": company_name,
        "scraped_at": datetime.now().isoformat(),
        "drug_names_searched": drug_names,
        "sources": {
            "presentations": [],
            "sec_filings": [],
            "clinical_trials": [],
            "publications": [],
            "conference_posters": []
        },
        "totals": {}
    }

    print(f"\n{'='*60}")
    print(f"  {ticker} — {company_name}")
    print(f"  Drugs: {', '.join(drug_names[:5])}")
    print(f"{'='*60}")

    # 1. IR Presentations
    print(f"  📊 Scraping IR presentations...")
    pres = scrape_ir_presentations(ticker, ir_config or {})
    all_results["sources"]["presentations"] = pres
    print(f"     Found {len(pres)} presentations")

    # 2. Events page (async)
    if presentations_url:
        print(f"  📅 Scraping events & presentations page...")
        events = await scrape_events_presentations(ticker, presentations_url)
        # Deduplicate against presentations
        existing_urls = {p["url"] for p in pres}
        events = [e for e in events if e.get("url") not in existing_urls]
        all_results["sources"]["presentations"].extend(events)
        print(f"     Found {len(events)} additional events")

    # 3. SEC filings
    print(f"  📋 Scraping SEC EDGAR filings...")
    sec = scrape_sec_filings(ticker)
    all_results["sources"]["sec_filings"] = sec
    print(f"     Found {len(sec)} SEC filings")

    # 4. Clinical trials
    print(f"  🔬 Searching ClinicalTrials.gov...")
    trials = scrape_clinical_trials(company_name, ticker)
    all_results["sources"]["clinical_trials"] = trials
    print(f"     Found {len(trials)} active trials")

    # 5. PubMed publications
    print(f"  📚 Searching PubMed publications...")
    pubs = scrape_pubmed(company_name, drug_names)
    all_results["sources"]["publications"] = pubs
    print(f"     Found {len(pubs)} publications")

    # 6. Conference posters
    print(f"  🎯 Searching conference posters/abstracts...")
    posters = scrape_conference_posters(company_name, drug_names)
    all_results["sources"]["conference_posters"] = posters
    print(f"     Found {len(posters)} conference items")

    # Totals
    all_results["totals"] = {
        "presentations": len(all_results["sources"]["presentations"]),
        "sec_filings": len(sec),
        "clinical_trials": len(trials),
        "publications": len(pubs),
        "conference_posters": len(posters),
        "total": sum([
            len(all_results["sources"]["presentations"]),
            len(sec), len(trials), len(pubs), len(posters)
        ])
    }

    return all_results


async def main():
    """Run all scrapers across all new tickers."""
    tickers = NEW_TICKERS
    if len(sys.argv) > 1 and sys.argv[1] != "--all":
        tickers = [t.upper() for t in sys.argv[1:]]

    print(f"🚀 Batch scraping {len(tickers)} tickers")
    print(f"   Tickers: {', '.join(tickers)}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    grand_totals = {
        "presentations": 0, "sec_filings": 0, "clinical_trials": 0,
        "publications": 0, "conference_posters": 0, "total": 0
    }

    for ticker in tickers:
        company_data = load_company_info(ticker)
        if not company_data:
            print(f"\n⚠ {ticker}: No company.json found, skipping")
            continue

        results = await scrape_ticker(ticker, company_data)

        # Save results to sources directory
        sources_dir = DATA_DIR / ticker / "sources"
        sources_dir.mkdir(parents=True, exist_ok=True)

        # Save full scrape results
        output_file = sources_dir / "scraped_sources.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        # Update sources index
        index_file = sources_dir / "index.json"
        index_data = {
            "ticker": ticker,
            "last_scraped": datetime.now().isoformat(),
            "sources": [],
            "totals": results["totals"]
        }

        # Flatten all sources into the index
        for source_type, items in results["sources"].items():
            for item in items:
                index_data["sources"].append({
                    "type": item.get("type", source_type),
                    "title": item.get("title", "")[:200],
                    "url": item.get("url", ""),
                    "date": item.get("date"),
                })

        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=2)

        # Accumulate totals
        for key in grand_totals:
            grand_totals[key] += results["totals"].get(key, 0)

        print(f"  💾 Saved to {output_file.relative_to(PROJECT_ROOT)}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"  BATCH SCRAPE COMPLETE")
    print(f"{'='*60}")
    print(f"  Tickers scraped: {len(tickers)}")
    print(f"  Presentations:   {grand_totals['presentations']}")
    print(f"  SEC filings:     {grand_totals['sec_filings']}")
    print(f"  Clinical trials: {grand_totals['clinical_trials']}")
    print(f"  Publications:    {grand_totals['publications']}")
    print(f"  Conf. posters:   {grand_totals['conference_posters']}")
    print(f"  ─────────────────────────")
    print(f"  TOTAL SOURCES:   {grand_totals['total']}")


if __name__ == "__main__":
    asyncio.run(main())
