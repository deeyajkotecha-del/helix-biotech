"""
SatyaBio FDA Regulatory Scraper

Scrapes five FDA data sources and embeds into Neon:
  1. openFDA Drugs@FDA — Approval history, application numbers, sponsors
  2. DailyMed — Full prescribing info / drug labels (SPL documents)
  3. openFDA Drug Labeling — Structured label sections (indications, warnings, clinical studies)
  4. FDA Approval Packages — HTML review documents (medical reviews, statistical reviews)
  5. CDER/CBER Review PDFs — Downloads actual review PDFs from accessdata.fda.gov
     (medical reviews, statistical reviews, multi-discipline reviews, clinical pharmacology)
     These PDFs are saved to data/companies/{TICKER}/sources/ for Step 3 embedding

All APIs are free, no key required (openFDA has optional API key for higher rate limits).

Uses company_config.py for the full 60-company universe.
Follows the same pattern as sec_trials_scraper.py — fetch text, chunk, embed directly into Neon.

Usage:
    python3 fda_scraper.py --all                     # All 60 companies
    python3 fda_scraper.py --ticker NUVL,RVMD         # Specific companies
    python3 fda_scraper.py --all --labels-only        # Only drug labels
    python3 fda_scraper.py --all --approvals-only     # Only approval history
    python3 fda_scraper.py --all --reviews-only        # Only download CDER/CBER review PDFs
    python3 fda_scraper.py --all --dry-run            # Preview without scraping
    python3 fda_scraper.py --list                     # List all companies

Requires in .env:
    NEON_DATABASE_URL=postgresql://...
    VOYAGE_API_KEY=your-voyage-key

Optional in .env:
    OPENFDA_API_KEY=your-key   (raises rate limit from 40/min to 240/min)
"""

import os
import sys
import re
import hashlib
import argparse
import time
from datetime import datetime
from pathlib import Path

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

# Data directory — same location where ir_scraper.py saves PDFs
DATA_DIR = str(Path(__file__).parent.parent / "data")

# --- Config ---
DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
OPENFDA_API_KEY = os.environ.get("OPENFDA_API_KEY", "")

EMBED_MODEL = "voyage-3"       # 1024 dims (matches rag_setup.py v2 schema)
EMBED_BATCH_SIZE = 16
CHUNK_SIZE = 800               # words per chunk
CHUNK_OVERLAP = 150            # overlapping words

# openFDA base URL
OPENFDA_BASE = "https://api.fda.gov"
DAILYMED_BASE = "https://dailymed.nlm.nih.gov/dailymed"

# Rate limiting
OPENFDA_DELAY = 0.3   # seconds between openFDA requests (40 RPM free tier)
DAILYMED_DELAY = 0.5   # seconds between DailyMed requests

# HTTP headers
HEADERS = {
    "User-Agent": "SatyaBio Research (research@satyabio.com)",
    "Accept": "application/json",
}


# ── Company → FDA brand/generic name mapping ──
# Maps our tickers to the drug names the FDA knows them by.
# This is how we bridge from "NUVL" to FDA's drug records.
COMPANY_DRUGS = {
    # Small/mid-cap oncology
    "NUVL": {"sponsor": "Nuvalent", "drugs": ["zidesamtinib", "NVL-520", "NVL-655"]},
    "RVMD": {"sponsor": "Revolution Medicines", "drugs": ["RMC-6236", "RMC-6291", "RMC-9805"]},
    "CELC": {"sponsor": "Celcuity", "drugs": ["gedatolisib"]},
    "CNTA": {"sponsor": "Centessa Pharmaceuticals", "drugs": ["lixivaptan", "ORX750"]},
    "IOVA": {"sponsor": "Iovance Biotherapeutics", "drugs": ["AMTAGVI", "lifileucel"]},
    "VIR": {"sponsor": "Vir Biotechnology", "drugs": ["tobevibart", "elebsiran"]},
    "JANX": {"sponsor": "Janux Therapeutics", "drugs": ["JANX007", "JANX008"]},
    "ARGX": {"sponsor": "argenx", "drugs": ["VYVGART", "efgartigimod"]},
    "KYMR": {"sponsor": "Kymera Therapeutics", "drugs": ["KT-474", "KT-621"]},
    "SRPT": {"sponsor": "Sarepta Therapeutics", "drugs": ["ELEVIDYS", "EXONDYS 51", "VYONDYS 53", "AMONDYS 45", "delandistrogene moxeparvovec"]},
    "INSM": {"sponsor": "Insmed", "drugs": ["ARIKAYCE", "brensocatib", "amikacin liposome"]},
    "NBIX": {"sponsor": "Neurocrine Biosciences", "drugs": ["INGREZZA", "valbenazine", "crinecerfont"]},
    "MRNA": {"sponsor": "Moderna", "drugs": ["SPIKEVAX", "mresvia", "mRNA-4157"]},
    "ALNY": {"sponsor": "Alnylam Pharmaceuticals", "drugs": ["ONPATTRO", "AMVUTTRA", "patisiran", "vutrisiran"]},
    "IONS": {"sponsor": "Ionis Pharmaceuticals", "drugs": ["SPINRAZA", "TEGSEDI", "WAYLIVRA", "nusinersen", "eplontersen"]},
    "VRTX": {"sponsor": "Vertex Pharmaceuticals", "drugs": ["TRIKAFTA", "CASGEVY", "exagamglogene autotemcel", "suzetrigine"]},
    "BIIB": {"sponsor": "Biogen", "drugs": ["LEQEMBI", "SKYCLARYS", "SPINRAZA", "ADUHELM", "lecanemab"]},
    "ALKS": {"sponsor": "Alkermes", "drugs": ["ARISTADA", "VIVITROL", "LYBALVI"]},
    "VKTX": {"sponsor": "Viking Therapeutics", "drugs": ["VK2735", "VK2809"]},
    "SAGE": {"sponsor": "Sage Therapeutics", "drugs": ["ZURZUVAE", "zuranolone"]},
    "AXSM": {"sponsor": "Axsome Therapeutics", "drugs": ["AUVELITY", "SUNOSI"]},
    "MDGL": {"sponsor": "Madrigal Pharmaceuticals", "drugs": ["REZDIFFRA", "resmetirom"]},
    "EXAS": {"sponsor": "Exact Sciences", "drugs": ["COLOGUARD"]},
    # Big pharma
    "PFE": {"sponsor": "Pfizer", "drugs": ["IBRANCE", "XTANDI", "PADCEV", "ADCETRIS", "LORBRENA", "BRAFTOVI", "TALZENNA", "palbociclib"]},
    "MRK": {"sponsor": "Merck", "drugs": ["KEYTRUDA", "WELIREG", "LYNPARZA", "pembrolizumab"]},
    "AZN": {"sponsor": "AstraZeneca", "drugs": ["TAGRISSO", "IMFINZI", "ENHERTU", "CALQUENCE", "osimertinib", "durvalumab"]},
    "GILD": {"sponsor": "Gilead Sciences", "drugs": ["TRODELVY", "YESCARTA", "sacituzumab govitecan"]},
    "LLY": {"sponsor": "Eli Lilly", "drugs": ["VERZENIO", "RETEVMO", "JAYPIRCA", "abemaciclib", "selpercatinib"]},
    "BMY": {"sponsor": "Bristol-Myers Squibb", "drugs": ["OPDIVO", "YERVOY", "REBLOZYL", "BREYANZI", "AUGTYRO", "nivolumab"]},
    "ABBV": {"sponsor": "AbbVie", "drugs": ["IMBRUVICA", "VENCLEXTA", "EPKINLY", "ibrutinib", "venetoclax"]},
    "AMGN": {"sponsor": "Amgen", "drugs": ["LUMAKRAS", "BLINCYTO", "IMDELLTRA", "sotorasib", "blinatumomab", "tarlatamab"]},
    "REGN": {"sponsor": "Regeneron", "drugs": ["LIBTAYO", "DUPIXENT", "cemiplimab", "dupilumab"]},
    "JNJ": {"sponsor": "Johnson & Johnson", "drugs": ["DARZALEX", "RYBREVANT", "CARVYKTI", "TECVAYLI", "daratumumab", "amivantamab"]},
    "NVS": {"sponsor": "Novartis", "drugs": ["KISQALI", "PLUVICTO", "SCEMBLIX", "KYMRIAH", "ribociclib", "asciminib"]},
    "RHHBY": {"sponsor": "Roche", "drugs": ["TECENTRIQ", "POLIVY", "COLUMVI", "atezolizumab", "glofitamab"]},
    "GSK": {"sponsor": "GSK", "drugs": ["ZEJULA", "BLENREP", "JEMPERLI", "niraparib", "dostarlimab"]},
    "TAK": {"sponsor": "Takeda", "drugs": ["ADCETRIS", "NINLARO", "EXKIVITY", "brentuximab vedotin"]},
    "DSNKY": {"sponsor": "Daiichi Sankyo", "drugs": ["ENHERTU", "trastuzumab deruxtecan"]},
    "SNY": {"sponsor": "Sanofi", "drugs": ["SARCLISA", "JEVTANA", "isatuximab"]},
    "NVO": {"sponsor": "Novo Nordisk", "drugs": ["OZEMPIC", "WEGOVY", "semaglutide"]},
    # Expansion — neuro/sleep, immunology, rare disease, oncology (2026-03-25)
    "HRMY": {"sponsor": "Harmony Biosciences", "drugs": ["WAKIX", "pitolisant"]},
    "JAZZ": {"sponsor": "Jazz Pharmaceuticals", "drugs": ["XYWAV", "XYREM", "RYLAZE", "ZEPZELCA", "sodium oxybate"]},
    "ACAD": {"sponsor": "Acadia Pharmaceuticals", "drugs": ["NUPLAZID", "DAYBUE", "pimavanserin", "trofinetide"]},
    "ITCI": {"sponsor": "Intra-Cellular Therapies", "drugs": ["CAPLYTA", "lumateperone"]},
    "XENE": {"sponsor": "Xenon Pharmaceuticals", "drugs": ["XEN1101", "azetukalner"]},
    "PRAX": {"sponsor": "Praxis Precision Medicine", "drugs": ["PRAX-562", "ulixacaltamide"]},
    "SUPN": {"sponsor": "Supernus Pharmaceuticals", "drugs": ["QELBREE", "OXTELLAR XR", "TROKENDI XR", "viloxazine"]},
    "INCY": {"sponsor": "Incyte", "drugs": ["JAKAFI", "OPZELURA", "MONJUVI", "ruxolitinib", "tafasitamab"]},
    "ARVN": {"sponsor": "Arvinas", "drugs": ["ARV-471", "vepdegestrant", "ARV-766"]},
    "SNDX": {"sponsor": "Syndax Pharmaceuticals", "drugs": ["REVUMENIB", "axatilimab"]},
    "BPMC": {"sponsor": "Blueprint Medicines", "drugs": ["AYVAKIT", "GAVRETO", "avapritinib", "pralsetinib"]},
    "BMRN": {"sponsor": "BioMarin", "drugs": ["VOXZOGO", "BRINEURA", "PALYNZIQ", "ROCTAVIAN", "vosoritide", "valoctocogene roxaparvovec"]},
    "RARE": {"sponsor": "Ultragenyx", "drugs": ["CRYSVITA", "DOJOLVI", "MEPSEVII", "burosumab"]},
    "AUPH": {"sponsor": "Aurinia Pharmaceuticals", "drugs": ["LUPKYNIS", "voclosporin"]},
    "NMRA": {"sponsor": "Neumora Therapeutics", "drugs": ["navacaprant", "NMRA-140"]},
    "IDIA": {"sponsor": "Idorsia", "drugs": ["QUVIVIQ", "daridorexant", "cenerimod"]},
    # Demo priority — added 2026-04-06
    "UTHR": {"sponsor": "United Therapeutics", "drugs": ["TYVASO", "REMODULIN", "ORENITRAM", "UNITUXIN", "treprostinil", "ralinepag"]},
    "ASND": {"sponsor": "Ascendis Pharma", "drugs": ["SKYTROFA", "YORVIPATH", "YUVIWEL", "lonapegsomatropin", "TransCon PTH", "TransCon CNP"]},
    "DFTX": {"sponsor": "Definium Therapeutics", "drugs": ["DT120", "DT402", "lysergide"]},
    "LXEO": {"sponsor": "Lexeo Therapeutics", "drugs": ["LX2006", "LX2020", "LX1001"]},
    # Expansion — Daisy's watchlist (2026-04-06)
    "ETNB": {"sponsor": "89bio", "drugs": ["pegozafermin", "TERN-501"]},
    "GHRS": {"sponsor": "GH Research", "drugs": ["GH001", "GH002", "mebufotenin"]},
    "QURE": {"sponsor": "uniQure", "drugs": ["HEMGENIX", "etranacogene dezaparvovec", "AMT-130"]},
    "VRDN": {"sponsor": "Viridian Therapeutics", "drugs": ["VRDN-001", "veligrotug", "VRDN-003"]},
    "PTCT": {"sponsor": "PTC Therapeutics", "drugs": ["TRANSLARNA", "UPSTAZA", "WAYLIVRA", "ataluren", "eladocagene exuparvovec", "sepiapterine"]},
    "LBRX": {"sponsor": "LB Pharmaceuticals", "drugs": ["LB-102"]},
    "ERAS": {"sponsor": "Erasca", "drugs": ["naporafenib", "ERAS-007", "ERAS-601"]},
    "RLMD": {"sponsor": "Relmada Therapeutics", "drugs": ["REL-1017", "esmethadone"]},
}


# ============================================================================
# openFDA: Drugs@FDA — Approval History
# ============================================================================

def search_openfda_approvals(sponsor_name: str, drug_names: list[str]) -> list[dict]:
    """
    Search openFDA Drugs@FDA endpoint for approval records.
    Returns list of application records (NDA/BLA numbers, approval dates, etc.)
    """
    results = []

    # Search by sponsor name
    query = f'openfda.manufacturer_name:"{sponsor_name}"'
    params = {
        "search": query,
        "limit": 100,
    }
    if OPENFDA_API_KEY:
        params["api_key"] = OPENFDA_API_KEY

    url = f"{OPENFDA_BASE}/drug/drugsfda.json"

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            for result in data.get("results", []):
                app_number = result.get("application_number", "")
                sponsor = result.get("sponsor_name", "")
                products = result.get("products", [])
                submissions = result.get("submissions", [])

                for product in products:
                    brand = product.get("brand_name", "")
                    generic = product.get("active_ingredients", [])
                    dosage = product.get("dosage_form", "")

                    # Get approval dates from submissions
                    approval_dates = []
                    review_docs = []
                    for sub in submissions:
                        sub_type = sub.get("submission_type", "")
                        sub_status = sub.get("submission_status", "")
                        sub_date = sub.get("submission_status_date", "")
                        if sub_status == "AP":  # Approved
                            approval_dates.append(sub_date)

                        # Collect review document URLs
                        for doc in sub.get("application_docs", []):
                            doc_url = doc.get("url", "")
                            doc_type = doc.get("type", "")
                            doc_title = doc.get("title", "")
                            if doc_url:
                                review_docs.append({
                                    "url": doc_url,
                                    "type": doc_type,
                                    "title": doc_title,
                                })

                    results.append({
                        "app_number": app_number,
                        "sponsor": sponsor,
                        "brand_name": brand,
                        "active_ingredients": generic,
                        "dosage_form": dosage,
                        "approval_dates": approval_dates,
                        "review_docs": review_docs,
                    })

        time.sleep(OPENFDA_DELAY)
    except Exception as e:
        print(f"    openFDA error: {e}")

    # Also search by specific drug names for better coverage
    for drug in drug_names:
        query = f'openfda.brand_name:"{drug}"'
        params = {"search": query, "limit": 10}
        if OPENFDA_API_KEY:
            params["api_key"] = OPENFDA_API_KEY

        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for result in data.get("results", []):
                    app_num = result.get("application_number", "")
                    # Avoid duplicates
                    if not any(r["app_number"] == app_num for r in results):
                        products = result.get("products", [])
                        submissions = result.get("submissions", [])
                        for product in products:
                            review_docs = []
                            approval_dates = []
                            for sub in submissions:
                                if sub.get("submission_status") == "AP":
                                    approval_dates.append(sub.get("submission_status_date", ""))
                                for doc in sub.get("application_docs", []):
                                    if doc.get("url"):
                                        review_docs.append({
                                            "url": doc["url"],
                                            "type": doc.get("type", ""),
                                            "title": doc.get("title", ""),
                                        })

                            results.append({
                                "app_number": app_num,
                                "sponsor": result.get("sponsor_name", ""),
                                "brand_name": product.get("brand_name", ""),
                                "active_ingredients": product.get("active_ingredients", []),
                                "dosage_form": product.get("dosage_form", ""),
                                "approval_dates": approval_dates,
                                "review_docs": review_docs,
                            })
            time.sleep(OPENFDA_DELAY)
        except Exception as e:
            pass

    return results


# ============================================================================
# openFDA: Drug Labeling — Structured Label Sections
# ============================================================================

def fetch_drug_labels(sponsor_name: str, drug_names: list[str]) -> list[dict]:
    """
    Fetch structured drug label sections from openFDA drug labeling endpoint.
    Returns rich clinical text: indications, clinical studies, warnings, dosage.
    """
    labels = []
    url = f"{OPENFDA_BASE}/drug/label.json"

    for drug in drug_names:
        # Try brand name first, then generic
        for field in ["openfda.brand_name", "openfda.generic_name"]:
            query = f'{field}:"{drug}"'
            params = {"search": query, "limit": 3}
            if OPENFDA_API_KEY:
                params["api_key"] = OPENFDA_API_KEY

            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                for result in data.get("results", []):
                    openfda = result.get("openfda", {})
                    brand = openfda.get("brand_name", [""])[0] if openfda.get("brand_name") else drug
                    generic = openfda.get("generic_name", [""])[0] if openfda.get("generic_name") else ""
                    app_number = openfda.get("application_number", [""])[0] if openfda.get("application_number") else ""

                    # Extract the most valuable label sections for biotech diligence
                    sections = {}
                    valuable_fields = [
                        ("indications_and_usage", "INDICATIONS AND USAGE"),
                        ("dosage_and_administration", "DOSAGE AND ADMINISTRATION"),
                        ("warnings_and_cautions", "WARNINGS AND PRECAUTIONS"),
                        ("adverse_reactions", "ADVERSE REACTIONS"),
                        ("clinical_studies", "CLINICAL STUDIES"),
                        ("clinical_pharmacology", "CLINICAL PHARMACOLOGY"),
                        ("mechanism_of_action", "MECHANISM OF ACTION"),
                        ("pharmacodynamics", "PHARMACODYNAMICS"),
                        ("pharmacokinetics", "PHARMACOKINETICS"),
                        ("nonclinical_toxicology", "NONCLINICAL TOXICOLOGY"),
                        ("boxed_warning", "BOXED WARNING"),
                        ("drug_interactions", "DRUG INTERACTIONS"),
                        ("use_in_specific_populations", "USE IN SPECIFIC POPULATIONS"),
                        ("description", "DESCRIPTION"),
                        ("how_supplied", "HOW SUPPLIED"),
                    ]

                    for field_key, section_title in valuable_fields:
                        content = result.get(field_key, [])
                        if content and isinstance(content, list):
                            text = "\n\n".join(content)
                            # Clean HTML tags that sometimes appear
                            text = re.sub(r'<[^>]+>', ' ', text)
                            text = re.sub(r'\s+', ' ', text).strip()
                            if len(text) > 50:  # Skip near-empty sections
                                sections[section_title] = text

                    if sections:
                        # Check for duplicates
                        label_id = f"{brand}_{app_number}"
                        if not any(l.get("label_id") == label_id for l in labels):
                            labels.append({
                                "label_id": label_id,
                                "brand_name": brand,
                                "generic_name": generic,
                                "app_number": app_number,
                                "sections": sections,
                            })

                time.sleep(OPENFDA_DELAY)
            except Exception as e:
                pass

    return labels


# ============================================================================
# DailyMed: Full Prescribing Information (SPL)
# ============================================================================

def fetch_dailymed_labels(drug_names: list[str]) -> list[dict]:
    """
    Search DailyMed for drug labels and download full text.
    DailyMed has the most current version of each drug label.
    """
    results = []
    search_url = f"{DAILYMED_BASE}/services/v2/spls.json"

    for drug in drug_names:
        try:
            params = {"drug_name": drug, "pagesize": 5}
            resp = requests.get(search_url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            data = resp.json()
            spls = data.get("data", [])

            for spl in spls:
                set_id = spl.get("setid", "")
                title = spl.get("title", "")
                published = spl.get("published_date", "")

                if not set_id:
                    continue

                # Check for duplicate
                if any(r.get("set_id") == set_id for r in results):
                    continue

                # Fetch the full SPL text
                spl_url = f"{DAILYMED_BASE}/services/v2/spls/{set_id}.json"
                try:
                    spl_resp = requests.get(spl_url, headers=HEADERS, timeout=20)
                    if spl_resp.status_code == 200:
                        spl_data = spl_resp.json()

                        # The full text is in the XML body — extract sections
                        body = spl_data.get("data", {})
                        spl_version = body.get("spl_version", "")
                        title = body.get("title", title)

                        results.append({
                            "set_id": set_id,
                            "title": title,
                            "published_date": published,
                            "spl_version": spl_version,
                            "drug_name": drug,
                        })
                except Exception:
                    pass

                time.sleep(DAILYMED_DELAY)

            time.sleep(DAILYMED_DELAY)
        except Exception as e:
            print(f"    DailyMed error for {drug}: {e}")

    return results


# ============================================================================
# FDA Approval Package Review Documents
# ============================================================================

def fetch_review_documents(review_docs: list[dict]) -> list[dict]:
    """
    Download and extract text from FDA review documents (medical reviews,
    statistical reviews, clinical reviews — like the BLA review in the screenshot).
    These are typically PDFs or HTML pages on accessdata.fda.gov.
    """
    documents = []

    for doc in review_docs:
        url = doc.get("url", "")
        doc_type = doc.get("type", "")
        doc_title = doc.get("title", "")

        if not url:
            continue

        # Skip non-review documents
        skip_types = ["letter", "rems", "other"]
        if any(s in doc_type.lower() for s in skip_types):
            continue

        try:
            resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            if resp.status_code != 200:
                continue

            content_type = resp.headers.get("Content-Type", "")

            if "html" in content_type or "text" in content_type:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "header", "footer"]):
                    tag.decompose()
                text = soup.get_text(separator="\n")
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                text = "\n".join(lines)

                if len(text) > 500:  # Skip near-empty pages
                    documents.append({
                        "url": url,
                        "type": doc_type,
                        "title": doc_title,
                        "text": text[:200000],  # Cap at 200k chars
                    })

            time.sleep(0.3)

        except Exception as e:
            pass

    return documents


# ============================================================================
# CDER/CBER Review Document PDFs — Download to disk for Step 3 embedding
# ============================================================================

# Review document types we want (the actual reviewer assessments)
VALUABLE_REVIEW_TYPES = [
    "Review",           # Generic review
    "Medical",          # Medical officer review
    "Statistical",      # Statistical review
    "Clinical",         # Clinical review
    "Pharmacology",     # Clinical pharmacology
    "Multi-discipline", # Multi-disciplinary review (like the RYBREVANT BLA screenshot)
    "Summary",          # Summary review / action package
    "Chemistry",        # CMC review
    "Risk",             # Risk assessment
    "REMS",             # Risk evaluation and mitigation
]

# Types we DON'T want to download
SKIP_REVIEW_TYPES = ["Letter", "Labeling", "Other"]


def _classify_review_doc(doc: dict) -> str:
    """
    Determine if a review doc from openFDA is worth downloading.
    Returns a clean type string, or '' if we should skip it.
    """
    doc_type = doc.get("type", "")
    doc_title = doc.get("title", "")
    url = doc.get("url", "")

    # Skip non-review types
    for skip in SKIP_REVIEW_TYPES:
        if skip.lower() in doc_type.lower():
            return ""

    # Check if it's a PDF (the ones we want are .pdf on accessdata.fda.gov)
    if url.lower().endswith(".pdf"):
        return doc_type or "Review"

    # Some URLs point to HTML index pages that LIST the review PDFs
    # We'll handle those separately in _scrape_review_index()
    if "accessdata.fda.gov" in url and not url.lower().endswith(".pdf"):
        return "index_page"

    return ""


def _scrape_review_index(index_url: str) -> list[dict]:
    """
    Some openFDA review doc URLs point to an HTML index page that lists
    multiple PDF links (e.g., the approval package page for an NDA/BLA).
    Scrape that page to find all the individual review PDFs.
    """
    pdf_links = []
    try:
        resp = requests.get(index_url, headers=HEADERS, timeout=20, allow_redirects=True)
        if resp.status_code != 200:
            return pdf_links

        soup = BeautifulSoup(resp.text, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)

            # Only grab PDF links
            if not href.lower().endswith(".pdf"):
                continue

            # Make absolute URL
            if href.startswith("/"):
                href = f"https://www.accessdata.fda.gov{href}"
            elif not href.startswith("http"):
                # Relative URL — resolve against the index page
                base = index_url.rsplit("/", 1)[0]
                href = f"{base}/{href}"

            # Filter: only keep review-type PDFs based on link text or filename
            fname_lower = href.lower().split("/")[-1]
            text_lower = text.lower()

            is_review = any(kw in fname_lower or kw in text_lower for kw in [
                "review", "medical", "clinical", "statistic", "pharmac",
                "multi", "summary", "chemistry", "risk", "approv",
            ])

            if is_review or "review" in text_lower:
                pdf_links.append({
                    "url": href,
                    "title": text or fname_lower,
                    "type": "Review",
                })

        time.sleep(0.3)
    except Exception as e:
        print(f"      Error scraping review index {index_url}: {e}")

    return pdf_links


def download_review_pdfs(ticker: str, app_number: str, brand_name: str,
                         review_docs: list[dict], dry_run: bool = False) -> int:
    """
    Download CDER/CBER review document PDFs to the company's sources folder.
    These get picked up by Step 3 (PDF embedder) automatically.

    Args:
        ticker: Company ticker (e.g. "JNJ")
        app_number: FDA application number (e.g. "BLA761210")
        brand_name: Drug brand name (e.g. "RYBREVANT")
        review_docs: List of {url, type, title} from openFDA
        dry_run: If True, just print what would be downloaded

    Returns:
        Number of PDFs downloaded
    """
    # Create the sources directory for this company
    sources_dir = os.path.join(DATA_DIR, "companies", ticker, "sources")
    os.makedirs(sources_dir, exist_ok=True)

    # Collect all PDF URLs to download — both direct PDFs and those from index pages
    pdfs_to_download = []

    for doc in review_docs:
        doc_class = _classify_review_doc(doc)
        if not doc_class:
            continue

        if doc_class == "index_page":
            # Scrape the index page for PDF links
            if not dry_run:
                index_pdfs = _scrape_review_index(doc["url"])
                pdfs_to_download.extend(index_pdfs)
                if index_pdfs:
                    print(f"      Found {len(index_pdfs)} review PDFs from index page")
        else:
            # Direct PDF link
            pdfs_to_download.append(doc)

    if not pdfs_to_download:
        return 0

    # Deduplicate by URL
    seen_urls = set()
    unique_pdfs = []
    for pdf in pdfs_to_download:
        url = pdf["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            unique_pdfs.append(pdf)

    if dry_run:
        print(f"      Would download {len(unique_pdfs)} review PDFs for {brand_name} ({app_number})")
        for pdf in unique_pdfs[:5]:
            print(f"        - {pdf.get('title', 'Unknown')}: {pdf['url']}")
        if len(unique_pdfs) > 5:
            print(f"        ... and {len(unique_pdfs) - 5} more")
        return 0

    downloaded = 0
    for pdf in unique_pdfs:
        url = pdf["url"]
        title = pdf.get("title", "review")
        doc_type = pdf.get("type", "review")

        # Build a clean filename: FDA_RYBREVANT_BLA761210_medical_review.pdf
        # Sanitize the title for use in filename
        safe_title = re.sub(r'[^\w\s-]', '', title.lower())
        safe_title = re.sub(r'[\s]+', '_', safe_title.strip())[:60]
        safe_brand = re.sub(r'[^\w]', '', brand_name.upper())
        safe_app = re.sub(r'[^\w]', '', app_number)

        if safe_title:
            filename = f"FDA_{safe_brand}_{safe_app}_{safe_title}.pdf"
        else:
            filename = f"FDA_{safe_brand}_{safe_app}_review.pdf"

        # Skip if already downloaded
        filepath = os.path.join(sources_dir, filename)
        if os.path.exists(filepath):
            print(f"      Already exists: {filename}")
            continue

        try:
            resp = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True,
                                stream=True)
            if resp.status_code != 200:
                print(f"      HTTP {resp.status_code} for {url}")
                continue

            content_type = resp.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                print(f"      Not a PDF ({content_type}), skipping: {url}")
                continue

            # Stream download to avoid memory issues with large review PDFs
            total_size = 0
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    total_size += len(chunk)

            # Sanity check — skip tiny files (probably error pages)
            if total_size < 5000:
                os.remove(filepath)
                print(f"      Too small ({total_size} bytes), skipping: {filename}")
                continue

            size_mb = total_size / (1024 * 1024)
            print(f"      Downloaded: {filename} ({size_mb:.1f} MB)")
            downloaded += 1
            time.sleep(0.3)  # Be polite to FDA servers

        except Exception as e:
            print(f"      Error downloading {url}: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)

    return downloaded


# ============================================================================
# CHUNKING + EMBEDDING (shared with sec_trials_scraper.py pattern)
# ============================================================================

def chunk_text(text: str, title: str = "", chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append({
            "content": " ".join(chunk_words),
            "section_title": title,
            "token_count": len(chunk_words),
        })
        start += chunk_size - overlap
        if start >= len(words):
            break

    return chunks


def embed_and_store(conn, vo_client, ticker: str, doc_title: str, doc_type: str,
                    text: str, source_url: str = "", doc_date: str = "") -> int:
    """
    Chunk text, embed with Voyage, store in Neon.
    Returns document ID if new, None if duplicate.
    """
    cur = conn.cursor()

    # Dedup by content hash
    content_hash = hashlib.sha256(text[:5000].encode()).hexdigest()[:32]
    filename = f"fda_{content_hash}.txt"

    cur.execute("SELECT id FROM documents WHERE ticker = %s AND filename = %s", (ticker, filename))
    if cur.fetchone():
        print(f"    Already exists, skipping")
        cur.close()
        return None

    # Chunk the text
    chunks = chunk_text(text, title=doc_title)
    if not chunks:
        cur.close()
        return None

    # Embed
    all_embeddings = []
    texts = [c["content"] for c in chunks]
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i:i + EMBED_BATCH_SIZE]
        try:
            result = vo_client.embed(batch, model=EMBED_MODEL, input_type="document")
            all_embeddings.extend(result.embeddings)
        except Exception as e:
            print(f"    Embedding error: {e}")
            all_embeddings.extend([None] * len(batch))
        if i + EMBED_BATCH_SIZE < len(texts):
            time.sleep(0.3)

    # Store document record
    word_count = len(text.split())
    company_name = ONCOLOGY_COMPANIES.get(ticker, {}).get("name", ticker)

    cur.execute("""
        INSERT INTO documents (ticker, company_name, filename, file_path, doc_type, title, date, word_count, page_count, file_size_bytes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        ticker, company_name, filename, source_url,
        doc_type, doc_title, doc_date,
        word_count, 0, len(text.encode()),
    ))
    doc_id = cur.fetchone()[0]

    # Store chunks
    stored = 0
    for i, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
        if embedding is None:
            continue
        cur.execute("""
            INSERT INTO chunks (document_id, chunk_index, page_number, section_title, content, token_count, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
        """, (
            doc_id, i, 0,
            chunk.get("section_title", ""),
            chunk["content"],
            chunk["token_count"],
            str(embedding),
        ))
        stored += 1

    conn.commit()
    cur.close()
    print(f"    Stored: {stored} chunks, {word_count} words (doc #{doc_id})")
    return doc_id


# ============================================================================
# MAIN: Process one company
# ============================================================================

def process_company(ticker: str, company_info: dict, conn, vo_client,
                    labels_only: bool = False, approvals_only: bool = False,
                    reviews_only: bool = False, dry_run: bool = False) -> int:
    """Process all FDA data for one company. Returns count of documents added."""
    company_name = company_info.get("name", ticker)
    drug_info = COMPANY_DRUGS.get(ticker, {})

    if not drug_info:
        print(f"  {ticker}: No FDA drug mapping configured, skipping")
        return 0

    sponsor = drug_info["sponsor"]
    drugs = drug_info["drugs"]
    docs_added = 0
    pdfs_total = 0

    print(f"\n{'='*60}")
    print(f"  {ticker} -- {company_name}")
    print(f"  Sponsor: {sponsor} | Drugs: {', '.join(drugs)}")
    print(f"{'='*60}")

    # ── 1. openFDA Drugs@FDA: Approval history + review doc URLs ──
    if not labels_only or reviews_only:
        print(f"\n  --- Drugs@FDA Approvals ---")
        approvals = search_openfda_approvals(sponsor, drugs)
        print(f"  Found {len(approvals)} application records")

        for app in approvals:
            brand = app.get("brand_name", "Unknown")
            app_num = app.get("app_number", "")
            ingredients = app.get("active_ingredients", [])
            dates = app.get("approval_dates", [])
            latest_date = dates[0] if dates else ""

            # Build approval summary text
            ingredients_str = ", ".join(
                [i.get("name", "") for i in ingredients] if isinstance(ingredients, list) and ingredients and isinstance(ingredients[0], dict)
                else [str(i) for i in ingredients]
            ) if ingredients else "N/A"

            summary = (
                f"FDA Application: {app_num}\n"
                f"Brand Name: {brand}\n"
                f"Sponsor: {app.get('sponsor', sponsor)}\n"
                f"Active Ingredients: {ingredients_str}\n"
                f"Dosage Form: {app.get('dosage_form', 'N/A')}\n"
                f"Approval Date(s): {', '.join(dates) if dates else 'N/A'}\n"
            )

            if not dry_run and not reviews_only and len(summary.split()) > 20:
                title = f"FDA Approval: {brand} ({app_num})"
                doc_id = embed_and_store(conn, vo_client, ticker, title, "fda_approval",
                                        summary, source_url=f"https://api.fda.gov/drug/drugsfda.json?search=application_number:{app_num}",
                                        doc_date=latest_date)
                if doc_id:
                    docs_added += 1

            # ── Fetch review documents (medical reviews, clinical reviews, etc.) ──
            review_docs = app.get("review_docs", [])
            if review_docs:
                # A) Download actual CDER/CBER review PDFs to disk
                #    These get picked up by Step 3 (PDF embedder) automatically
                print(f"    Downloading CDER/CBER review PDFs for {brand} ({app_num})...")
                pdfs_downloaded = download_review_pdfs(
                    ticker, app_num, brand, review_docs, dry_run=dry_run
                )
                if pdfs_downloaded:
                    print(f"    {pdfs_downloaded} review PDFs saved to sources/")
                    pdfs_total += pdfs_downloaded

                # B) Also fetch HTML review docs and embed directly into Neon
                if not dry_run:
                    fetched_docs = fetch_review_documents(review_docs)
                    for rd in fetched_docs:
                        title = f"FDA Review: {brand} - {rd['title'] or rd['type']}"
                        doc_id = embed_and_store(conn, vo_client, ticker, title, "fda_review",
                                                rd["text"], source_url=rd["url"],
                                                doc_date=latest_date)
                        if doc_id:
                            docs_added += 1

    # ── 2. openFDA Drug Labels: Structured label sections ──
    if not approvals_only and not reviews_only:
        print(f"\n  --- FDA Drug Labels ---")
        labels = fetch_drug_labels(sponsor, drugs)
        print(f"  Found {len(labels)} drug labels")

        for label in labels:
            brand = label.get("brand_name", "Unknown")
            sections = label.get("sections", {})

            if dry_run:
                print(f"    {brand}: {len(sections)} sections")
                continue

            # Combine all sections into one document with clear headers
            full_text = f"FDA DRUG LABEL: {brand}\n"
            full_text += f"Application: {label.get('app_number', 'N/A')}\n"
            full_text += f"Generic Name: {label.get('generic_name', 'N/A')}\n\n"

            for section_title, section_text in sections.items():
                full_text += f"\n{'='*40}\n{section_title}\n{'='*40}\n{section_text}\n"

            if len(full_text.split()) > 50:
                title = f"FDA Label: {brand} (Full Prescribing Information)"
                doc_id = embed_and_store(conn, vo_client, ticker, title, "fda_label",
                                        full_text, doc_date="",
                                        source_url=f"https://api.fda.gov/drug/label.json?search=openfda.brand_name:{brand}")
                if doc_id:
                    docs_added += 1

    print(f"\n  {ticker}: {docs_added} FDA documents added to Neon, {pdfs_total} review PDFs downloaded")
    return docs_added


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="SatyaBio FDA Regulatory Scraper — drug labels, approvals, review docs",
    )
    parser.add_argument("--ticker", type=str, help="Comma-separated tickers (e.g. NUVL,RVMD)")
    parser.add_argument("--all", action="store_true", help="Process all 60 companies")
    parser.add_argument("--list", action="store_true", help="List all companies with FDA drug mappings")
    parser.add_argument("--labels-only", action="store_true", help="Only fetch drug labels")
    parser.add_argument("--approvals-only", action="store_true", help="Only fetch approvals + review docs")
    parser.add_argument("--reviews-only", action="store_true", help="Only download CDER/CBER review PDFs (skip labels + embed)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without scraping")
    args = parser.parse_args()

    if not args.list and not args.ticker and not args.all:
        parser.print_help()
        sys.exit(1)

    if args.list:
        mapped = 0
        unmapped = 0
        for ticker in sorted(ONCOLOGY_COMPANIES.keys()):
            name = ONCOLOGY_COMPANIES[ticker]["name"]
            drug_info = COMPANY_DRUGS.get(ticker, {})
            if drug_info:
                drugs = ", ".join(drug_info["drugs"][:3])
                suffix = "..." if len(drug_info["drugs"]) > 3 else ""
                print(f"  {ticker:6s}  {name:35s}  [{drugs}{suffix}]")
                mapped += 1
            else:
                print(f"  {ticker:6s}  {name:35s}  [no drugs mapped]")
                unmapped += 1
        print(f"\n  {mapped} companies with FDA drug mappings, {unmapped} without")
        return

    if not DATABASE_URL or not VOYAGE_API_KEY:
        print("ERROR: Set NEON_DATABASE_URL and VOYAGE_API_KEY in .env")
        sys.exit(1)

    # Determine tickers
    if args.all:
        tickers = sorted(ONCOLOGY_COMPANIES.keys())
    else:
        tickers = [t.strip().upper() for t in args.ticker.split(",")]

    conn = psycopg2.connect(DATABASE_URL)
    vo_client = voyageai.Client(api_key=VOYAGE_API_KEY)

    print(f"\n{'='*60}")
    print(f"  SatyaBio FDA Regulatory Scraper")
    print(f"  Model: {EMBED_MODEL} (1024 dims)")
    print(f"  Companies: {len(tickers)}")
    print(f"{'='*60}")

    total_added = 0
    for ticker in tickers:
        if ticker not in ONCOLOGY_COMPANIES:
            print(f"  WARNING: {ticker} not in company_config.py")
            continue
        added = process_company(
            ticker, ONCOLOGY_COMPANIES[ticker], conn, vo_client,
            labels_only=args.labels_only,
            approvals_only=args.approvals_only,
            reviews_only=args.reviews_only,
            dry_run=args.dry_run,
        )
        total_added += added

    conn.close()

    print(f"\n{'='*60}")
    print(f"  Done! Processed {len(tickers)} companies")
    print(f"  FDA documents added: {total_added}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
