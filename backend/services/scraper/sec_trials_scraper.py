"""
SatyaBio SEC + ClinicalTrials.gov Scraper

Scrapes two data sources and embeds directly into Neon:
  1. SEC EDGAR — 10-K, 10-Q, 8-K filings (free API, no key needed)
  2. ClinicalTrials.gov — Active trials by company (v2 API, no key needed)

Uses company_config.py for the full 60-company universe.
Does NOT handle IR pages — that's ir_scraper.py (uses curl-cffi + Playwright).

Usage:
    python3 sec_trials_scraper.py --all                    # All 60 companies
    python3 sec_trials_scraper.py --ticker NUVL,RVMD       # Specific companies
    python3 sec_trials_scraper.py --all --sec-only         # SEC filings only
    python3 sec_trials_scraper.py --all --trials-only      # Clinical trials only
    python3 sec_trials_scraper.py --all --dry-run          # Preview without scraping
    python3 sec_trials_scraper.py --list                   # List all companies

Requires in .env:
    NEON_DATABASE_URL=postgresql://...
    VOYAGE_API_KEY=your-voyage-key
"""

import os
import sys
import hashlib
import argparse
import time
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# Add parent dirs to path for imports
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import requests
import psycopg2
import voyageai
from bs4 import BeautifulSoup

from company_config import ONCOLOGY_COMPANIES, get_all_oncology_tickers

# --- Config ---
DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")

EMBED_MODEL = "voyage-3"       # 1024 dims (matches rag_setup.py v2 schema)
EMBED_BATCH_SIZE = 16
CHUNK_SIZE = 800               # words per chunk
CHUNK_OVERLAP = 150            # overlapping words

# SEC EDGAR headers (required — they block requests without a user-agent)
SEC_HEADERS = {
    "User-Agent": "SatyaBio Research research@satyabio.com",
    "Accept-Encoding": "gzip, deflate",
}

# CIK codes for SEC lookups (companies without CIK skip SEC scraping)
COMPANY_CIKS = {
    "CNTA": "0001831097", "NUVL": "0001830188", "CELC": "0001592000",
    "PYXS": "0001819404", "RVMD": "0001688568", "RLAY": "0001812665",
    "IOVA": "0001425205", "VIR": "0001751299", "JANX": "0001835579",
    "CGON": "0001699136", "URGN": "0001575051", "VSTM": "0001411460",
    "IBRX": "0001326110", "TNGX": "0001822250", "BCYC": "0001768446",
    "ARGX": "0001697862", "KYMR": "0001798562", "ALKS": "0001520262",
    "VKTX": "0001599298", "GPCR": "0001887982", "ORKA": "0001992814",
    "MRNA": "0001682852", "ROIV": "0001819876", "PCVX": "0001829953",
    "SRPT": "0000873303", "SMMT": "0001808805", "INSM": "0001104506",
    "EXAS": "0001124140", "NBIX": "0000914475", "CRNX": "0001694665",
    "DAWN": "0001829987", "RCUS": "0001698428",
    "PFE": "0000078003", "MRK": "0000310158", "AZN": "0000901832",
    "GILD": "0000882095", "LLY": "0000059478", "BMY": "0000014272",
    "ABBV": "0001551152", "AMGN": "0000318154", "REGN": "0000872589",
    "TAK": "0001781068", "JNJ": "0000200406", "NVS": "0001114448",
    "SNY": "0001121404", "GSK": "0001131399", "VRTX": "0000875320",
    "BIIB": "0000875045", "ALNY": "0001178670", "IONS": "0000936395",
    "MDGL": "0000049708", "MRTI": "0001576263", "SAGE": "0001597553",
    "AXSM": "0001579428",
    # Expansion — neuro/sleep, immunology, rare disease, oncology (2026-03-25)
    "HRMY": "0001802665", "JAZZ": "0001232524", "ACAD": "0001070494",
    "ITCI": "0001567514", "XENE": "0001582313", "PRAX": "0001689548",
    "SUPN": "0001356576", "INCY": "0000879169", "ARVN": "0001655759",
    "SNDX": "0001395937", "BPMC": "0001597264", "BMRN": "0001048477",
    "RARE": "0001515673", "AUPH": "0001600620", "NMRA": "0001885522",
    # Foreign-listed companies (no CIK — skip SEC scraping)
    # RHHBY, NVO, DSNKY, ESALY, BILH, AGTSY, IDIA
    # Demo priority — added 2026-04-06
    "UTHR": "0001082554", "ASND": "0001612042",
    "DFTX": "0001813814",  # Formerly MindMed (MNMD)
    "LXEO": "0001907108",
    # Expansion — Daisy's watchlist (2026-04-06)
    "ETNB": "0001785173", "QURE": "0001590560", "VRDN": "0001590750",
    "PTCT": "0001070081", "LBRX": "0001691082", "ERAS": "0001761918",
    "RLMD": "0001553643",
    # GHRS — foreign issuer (Irish), no CIK — skip SEC scraping
}


# ============================================================================
# SEC EDGAR SCRAPER
# ============================================================================

    # Foreign private issuers (file 20-F/6-K instead of 10-K/10-Q/8-K)
FOREIGN_ISSUERS = {"ASND", "NVS", "TAK", "AZN", "SNY", "GSK", "NVO", "DSNKY", "RHHBY", "ESALY", "GHRS", "QURE"}

def fetch_sec_filings(ticker, cik, filing_types=None, max_filings=5):
    """Fetch recent SEC filings from EDGAR. Returns list of filing metadata."""
    if not filing_types:
        if ticker in FOREIGN_ISSUERS:
            filing_types = ["20-F", "6-K"]
        else:
            filing_types = ["10-K", "10-Q", "8-K"]

    cik_padded = cik.lstrip("0").zfill(10)
    filings = []

    for ftype in filing_types:
        api_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        print(f"  Fetching {ftype} filings from EDGAR for {ticker} (CIK: {cik})...")

        try:
            resp = requests.get(api_url, headers=SEC_HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"    EDGAR API returned {resp.status_code}")
                continue

            data = resp.json()
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            doc_names = recent.get("primaryDocument", [])

            count = 0
            for i, form in enumerate(forms):
                if form == ftype and count < max_filings:
                    filing_date = dates[i] if i < len(dates) else "unknown"
                    accession = accessions[i] if i < len(accessions) else ""
                    doc_name = doc_names[i] if i < len(doc_names) else ""
                    accession_clean = accession.replace("-", "")
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession_clean}/{doc_name}"

                    filings.append({
                        "type": ftype, "date": filing_date,
                        "accession": accession, "url": doc_url,
                        "doc_name": doc_name,
                        "title": f"{ticker} {ftype} ({filing_date})",
                    })
                    count += 1
                    print(f"    Found: {ftype} filed {filing_date}")

            time.sleep(0.2)  # SEC rate limit
        except Exception as e:
            print(f"    Error fetching {ftype}: {e}")

    return filings


def fetch_filing_text(url, max_chars=100000):
    """Download and extract text from an SEC filing (HTML or plain text)."""
    try:
        resp = requests.get(url, headers=SEC_HEADERS, timeout=30)
        if resp.status_code != 200:
            return None

        content = resp.text
        if "<html" in content.lower()[:500]:
            soup = BeautifulSoup(content, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text(separator="\n")
        else:
            text = content

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        text = "\n".join(lines)

        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[... truncated ...]"
        return text

    except Exception as e:
        print(f"    Error fetching filing text: {e}")
        return None


# ============================================================================
# ClinicalTrials.gov SCRAPER
# ============================================================================

def fetch_trials(company_name, ticker, max_results=20):
    """Search ClinicalTrials.gov for active trials by company name (v2 API)."""
    print(f"  Searching ClinicalTrials.gov for {company_name}...")

    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        "query.spons": company_name,
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,NOT_YET_RECRUITING",
        "pageSize": min(max_results, 50),
        "format": "json",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"    ClinicalTrials.gov returned {resp.status_code}")
            return []

        data = resp.json()
        studies = data.get("studies", [])
        print(f"    Found {len(studies)} active trials")

        results = []
        for study in studies:
            proto = study.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status = proto.get("statusModule", {})
            design = proto.get("designModule", {})
            desc = proto.get("descriptionModule", {})
            conditions = proto.get("conditionsModule", {})
            arms = proto.get("armsInterventionsModule", {})

            nct_id = ident.get("nctId", "")
            title = ident.get("briefTitle", "")
            phase = ",".join(design.get("phases", []))
            overall_status = status.get("overallStatus", "")
            brief_summary = desc.get("briefSummary", "")
            condition_list = conditions.get("conditions", [])
            interventions = arms.get("interventions", [])
            intervention_names = [i.get("name", "") for i in interventions]

            text_block = (
                f"CLINICAL TRIAL: {nct_id}\n"
                f"Title: {title}\n"
                f"Phase: {phase}\n"
                f"Status: {overall_status}\n"
                f"Conditions: {', '.join(condition_list)}\n"
                f"Interventions: {', '.join(intervention_names)}\n"
                f"Summary: {brief_summary}\n"
            )
            results.append({"nct_id": nct_id, "title": title, "phase": phase,
                            "status": overall_status, "text": text_block})
        return results

    except Exception as e:
        print(f"    Error: {e}")
        return []


# ============================================================================
# EMBEDDING PIPELINE
# ============================================================================

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return chunks


def embed_and_store(conn, vo_client, text, ticker, company_name, title,
                    doc_type="sec_filing", source_url=""):
    """Chunk, embed, and store a document in Neon."""
    word_count = len(text.split())
    if word_count < 50:
        print(f"    Skipping (too short: {word_count} words)")
        return None

    chunks = chunk_text(text)

    embeddings = []
    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i:i + EMBED_BATCH_SIZE]
        try:
            result = vo_client.embed(batch, model=EMBED_MODEL, input_type="document")
            embeddings.extend(result.embeddings)
        except Exception as e:
            print(f"    Embed error: {e}")
            embeddings.extend([None] * len(batch))

    cur = conn.cursor()

    # Check for duplicates
    filename_hash = hashlib.sha256(title.encode()).hexdigest()[:20]
    cur.execute("SELECT id FROM documents WHERE ticker = %s AND filename = %s", (ticker, filename_hash))
    existing = cur.fetchone()
    if existing:
        print(f"    Already exists (doc #{existing[0]}), skipping")
        cur.close()
        return existing[0]

    cur.execute("""
        INSERT INTO documents (ticker, company_name, filename, file_path, doc_type, title, word_count, page_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (ticker, company_name, filename_hash, source_url, doc_type, title, word_count, 1))
    doc_id = cur.fetchone()[0]

    inserted = 0
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        if embedding is None:
            continue
        cur.execute("""
            INSERT INTO chunks (document_id, chunk_index, page_number, content, token_count, embedding)
            VALUES (%s, %s, %s, %s, %s, %s::vector)
        """, (doc_id, i, 1, chunk, len(chunk.split()), str(embedding)))
        inserted += 1

    conn.commit()
    cur.close()
    print(f"    Stored: {inserted} chunks, {word_count} words (doc #{doc_id})")
    return doc_id


# ============================================================================
# MAIN
# ============================================================================

def process_company(ticker, info, conn, vo_client,
                    sec_only=False, trials_only=False, dry_run=False):
    """
    Scrape SEC filings and/or ClinicalTrials.gov for one company.
    No IR page scraping — that's handled by ir_scraper.py.
    """
    company_name = info["name"]
    cik = COMPANY_CIKS.get(ticker, "")

    print(f"\n{'='*60}")
    print(f"  {ticker} -- {company_name}")
    print(f"{'='*60}")

    docs_added = 0

    # ---------- 1. SEC Filings ----------
    if not trials_only and cik:
        print(f"\n  --- SEC EDGAR ---")
        if dry_run:
            print(f"  [Dry run] Would scrape 10-K, 10-Q, 8-K from EDGAR")
        else:
            filings = fetch_sec_filings(ticker, cik, max_filings=3)
            for filing in filings:
                print(f"  Fetching text for {filing['type']} ({filing['date']})...")
                text = fetch_filing_text(filing["url"])
                if text and len(text.split()) > 100:
                    doc_id = embed_and_store(
                        conn, vo_client, text, ticker, company_name,
                        title=filing["title"],
                        doc_type=f"sec_{filing['type'].lower().replace('-', '')}",
                        source_url=filing["url"],
                    )
                    if doc_id:
                        docs_added += 1
                time.sleep(0.5)
    elif not trials_only and not cik:
        print(f"\n  --- SEC EDGAR ---")
        print(f"  Skipping (no CIK for {ticker} — foreign-listed)")

    # ---------- 2. ClinicalTrials.gov ----------
    if not sec_only:
        print(f"\n  --- ClinicalTrials.gov ---")
        if dry_run:
            print(f"  [Dry run] Would search ClinicalTrials.gov for {company_name}")
        else:
            trials = fetch_trials(company_name, ticker, max_results=15)
            if trials:
                combined = f"ACTIVE CLINICAL TRIALS FOR {company_name} ({ticker})\n"
                combined += f"As of: {datetime.now().strftime('%Y-%m-%d')}\n"
                combined += f"Total active trials: {len(trials)}\n\n"
                for trial in trials:
                    combined += trial["text"] + "\n---\n\n"

                doc_id = embed_and_store(
                    conn, vo_client, combined, ticker, company_name,
                    title=f"[Trials] {company_name} Active Clinical Trials",
                    doc_type="clinical_trials",
                )
                if doc_id:
                    docs_added += 1

    print(f"\n  {ticker}: {docs_added} documents added to Neon")
    return docs_added


def main():
    parser = argparse.ArgumentParser(
        description="SatyaBio SEC + ClinicalTrials.gov Scraper (no IR — see ir_scraper.py)",
    )
    parser.add_argument("--ticker", type=str, help="Comma-separated tickers (e.g. NUVL,RVMD)")
    parser.add_argument("--all", action="store_true", help="Process all 60 companies")
    parser.add_argument("--list", action="store_true", help="List all tracked companies")
    parser.add_argument("--sec-only", action="store_true", help="Only scrape SEC filings")
    parser.add_argument("--trials-only", action="store_true", help="Only scrape ClinicalTrials.gov")
    parser.add_argument("--dry-run", action="store_true", help="Preview without scraping")
    args = parser.parse_args()

    if not args.list and not args.ticker and not args.all:
        parser.print_help()
        sys.exit(1)

    if args.list:
        by_cat = {}
        for t, info in sorted(ONCOLOGY_COMPANIES.items()):
            by_cat.setdefault(info.get("category", "other"), []).append((t, info["name"]))
        for cat, companies in sorted(by_cat.items()):
            print(f"\n  {cat.upper()} ({len(companies)} companies)")
            for t, name in companies:
                has_cik = "SEC" if t in COMPANY_CIKS else "   "
                print(f"    {t:6s}  {name}  [{has_cik}]")
        print(f"\n  Total: {len(ONCOLOGY_COMPANIES)} companies tracked")
        return

    if not DATABASE_URL or not VOYAGE_API_KEY:
        print("ERROR: Set NEON_DATABASE_URL and VOYAGE_API_KEY in .env")
        sys.exit(1)

    # Determine tickers
    if args.all:
        tickers = list(ONCOLOGY_COMPANIES.keys())
    else:
        tickers = [t.strip().upper() for t in args.ticker.split(",")]

    for t in tickers:
        if t not in ONCOLOGY_COMPANIES:
            print(f"WARNING: {t} not in company_config.py")

    conn = psycopg2.connect(DATABASE_URL)
    vo_client = voyageai.Client(api_key=VOYAGE_API_KEY)

    print(f"\n{'='*60}")
    print(f"  SatyaBio SEC + Trials Scraper")
    print(f"  Model: {EMBED_MODEL} (1024 dims)")
    print(f"  Companies: {len(tickers)}")
    sources = []
    if not args.trials_only: sources.append("SEC EDGAR")
    if not args.sec_only: sources.append("ClinicalTrials.gov")
    print(f"  Sources: {', '.join(sources)}")
    print(f"{'='*60}")

    total_added = 0
    for ticker in tickers:
        if ticker not in ONCOLOGY_COMPANIES:
            continue
        added = process_company(
            ticker, ONCOLOGY_COMPANIES[ticker], conn, vo_client,
            sec_only=args.sec_only,
            trials_only=args.trials_only,
            dry_run=args.dry_run,
        )
        if added:
            total_added += added

    conn.close()

    print(f"\n{'='*60}")
    print(f"  Done! Processed {len(tickers)} companies")
    print(f"  Documents added: {total_added}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
