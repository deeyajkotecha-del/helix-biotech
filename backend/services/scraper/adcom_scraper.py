"""
FDA Advisory Committee (AdCom) Meeting Materials Scraper

Scrapes briefing documents, transcripts, presentations, and meeting summaries
from all major FDA advisory committees (CDER + CBER).

Each committee has a predictable URL structure:
  Materials page: fda.gov/advisory-committees/{slug}/{year}-meeting-materials-{slug}
  Individual docs: fda.gov/media/{id}/download

Architecture:
  1. Discover meetings from yearly materials pages (scrape meeting links)
  2. For each meeting, scrape the announcement page for document links
  3. Download briefing docs, transcripts, and presentations as PDFs
  4. Chunk and embed into Neon for RAG search

Usage:
    python3 adcom_scraper.py --committee ODAC               # One committee
    python3 adcom_scraper.py --committee ODAC,CTGTAC        # Multiple
    python3 adcom_scraper.py --all                           # All committees
    python3 adcom_scraper.py --all --years 2024,2025         # Specific years
    python3 adcom_scraper.py --list                          # List all committees
    python3 adcom_scraper.py --committee ODAC --dry-run      # Preview only

Requires in .env:
    NEON_DATABASE_URL=postgresql://...
    VOYAGE_API_KEY=your-voyage-key
"""

import os
import re
import sys
import json
import time
import argparse
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# ── Make sibling modules importable ──
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
_SEARCH_DIR = os.path.join(os.path.dirname(_THIS_DIR), "search")
if _SEARCH_DIR not in sys.path:
    sys.path.insert(0, _SEARCH_DIR)


# ===========================================================================
# FDA Advisory Committee Registry
# ===========================================================================

# Each entry: abbreviation -> (full name, URL slug, FDA center, therapeutic area)
# The slug is used to construct the meeting materials URL

COMMITTEES = {
    # ── CDER (Drugs) ──
    "ODAC": {
        "name": "Oncologic Drugs Advisory Committee",
        "slug": "oncologic-drugs-advisory-committee",
        "center": "CDER",
        "area": "oncology",
        "priority": 1,
    },
    "PCNSDAC": {
        "name": "Peripheral and Central Nervous System Drugs Advisory Committee",
        "slug": "peripheral-and-central-nervous-system-drugs-advisory-committee",
        "center": "CDER",
        "area": "neurology",
        "priority": 1,
    },
    "PDAC": {
        "name": "Psychopharmacologic Drugs Advisory Committee",
        "slug": "psychopharmacologic-drugs-advisory-committee",
        "center": "CDER",
        "area": "psychiatry",
        "priority": 1,
    },
    "EMDAC": {
        "name": "Endocrinologic and Metabolic Drugs Advisory Committee",
        "slug": "endocrinologic-and-metabolic-drugs-advisory-committee",
        "center": "CDER",
        "area": "metabolic",
        "priority": 1,
    },
    "CRDAC": {
        "name": "Cardiovascular and Renal Drugs Advisory Committee",
        "slug": "cardiovascular-and-renal-drugs-advisory-committee",
        "center": "CDER",
        "area": "cardiovascular",
        "priority": 2,
    },
    "AADPAC": {
        "name": "Anesthetic and Analgesic Drug Products Advisory Committee",
        "slug": "anesthetic-and-analgesic-drug-products-advisory-committee",
        "center": "CDER",
        "area": "pain",
        "priority": 2,
    },
    "AMDAC": {
        "name": "Antimicrobial Drugs Advisory Committee",
        "slug": "antimicrobial-drugs-advisory-committee-formerly-known-anti-infective-drugs-advisory-committee",
        "center": "CDER",
        "area": "infectious_disease",
        "priority": 2,
    },
    "AAC": {
        "name": "Arthritis Advisory Committee",
        "slug": "arthritis-advisory-committee",
        "center": "CDER",
        "area": "immunology",
        "priority": 2,
    },
    "BRUDAC": {
        "name": "Bone, Reproductive and Urologic Drugs Advisory Committee",
        "slug": "bone-reproductive-and-urologic-drugs-advisory-committee",
        "center": "CDER",
        "area": "rare_disease",
        "priority": 3,
    },
    "DODAC": {
        "name": "Dermatologic and Ophthalmic Drugs Advisory Committee",
        "slug": "dermatologic-and-ophthalmic-drugs-advisory-committee",
        "center": "CDER",
        "area": "dermatology",
        "priority": 3,
    },
    "DSaRM": {
        "name": "Drug Safety and Risk Management Advisory Committee",
        "slug": "drug-safety-and-risk-management-advisory-committee",
        "center": "CDER",
        "area": "safety",
        "priority": 2,
    },
    "GIDAC": {
        "name": "Gastrointestinal Drugs Advisory Committee",
        "slug": "gastrointestinal-drugs-advisory-committee",
        "center": "CDER",
        "area": "gastroenterology",
        "priority": 2,
    },
    "PADAC": {
        "name": "Pulmonary-Allergy Drugs Advisory Committee",
        "slug": "pulmonary-allergy-drugs-advisory-committee",
        "center": "CDER",
        "area": "pulmonary",
        "priority": 2,
    },
    "MIDAC": {
        "name": "Medical Imaging Drugs Advisory Committee",
        "slug": "medical-imaging-drugs-advisory-committee",
        "center": "CDER",
        "area": "imaging",
        "priority": 3,
    },
    "NDAC": {
        "name": "Nonprescription Drugs Advisory Committee",
        "slug": "nonprescription-drugs-advisory-committee",
        "center": "CDER",
        "area": "otc",
        "priority": 3,
    },
    "PSCPAC": {
        "name": "Pharmaceutical Science and Clinical Pharmacology Advisory Committee",
        "slug": "pharmaceutical-science-and-clinical-pharmacology-advisory-committee",
        "center": "CDER",
        "area": "pharmacology",
        "priority": 3,
    },
    "PCAC": {
        "name": "Pharmacy Compounding Advisory Committee",
        "slug": "pharmacy-compounding-advisory-committee",
        "center": "CDER",
        "area": "compounding",
        "priority": 3,
    },

    # ── CBER (Biologics) ──
    "VRBPAC": {
        "name": "Vaccines and Related Biological Products Advisory Committee",
        "slug": "vaccines-and-related-biological-products-advisory-committee",
        "center": "CBER",
        "area": "vaccines",
        "priority": 1,
    },
    "CTGTAC": {
        "name": "Cellular, Tissue, and Gene Therapies Advisory Committee",
        "slug": "cellular-tissue-and-gene-therapies-advisory-committee",
        "center": "CBER",
        "area": "gene_therapy",
        "priority": 1,
    },
    "BPAC": {
        "name": "Blood Products Advisory Committee",
        "slug": "blood-products-advisory-committee",
        "center": "CBER",
        "area": "blood_products",
        "priority": 3,
    },
    "APAC": {
        "name": "Allergenic Products Advisory Committee",
        "slug": "allergenic-products-advisory-committee",
        "center": "CBER",
        "area": "allergy",
        "priority": 3,
    },
}


# ===========================================================================
# URL Construction
# ===========================================================================

FDA_BASE = "https://www.fda.gov"

# Headers to mimic a real browser (FDA blocks bare requests)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_DELAY = 1.5  # seconds between requests (be polite to FDA servers)


def get_materials_url(slug: str, year: int) -> str:
    """Construct the meeting materials page URL for a committee + year."""
    # CDER pattern
    return f"{FDA_BASE}/advisory-committees/{slug}/{year}-meeting-materials-{slug}"


def get_committee_base_url(slug: str) -> str:
    """Get the main committee page URL."""
    return f"{FDA_BASE}/advisory-committees/{slug}"


# -- Archive (Wayback Machine) support --

WAYBACK_BASE = "https://web.archive.org"

def discover_archive_urls(committee_key: str) -> dict[int, str]:
    """
    Scrape the committee's main page on fda.gov to find Wayback Machine
    links for older years (pre-2023).  Returns {year: archive_url}.

    FDA redirects older meeting-materials pages to web.archive.org, and
    the links appear on the committee's "human-drug-advisory-committees"
    or "blood-vaccines-and-other-biologics" parent page.
    """
    info = COMMITTEES[committee_key]
    slug = info["slug"]

    # Try two URL patterns for the main committee page
    base_urls = [
        f"{FDA_BASE}/advisory-committees/human-drug-advisory-committees/{slug}",
        f"{FDA_BASE}/advisory-committees/{slug}",
    ]

    archive_map: dict[int, str] = {}

    for base_url in base_urls:
        soup = fetch_page(base_url)
        if not soup:
            continue

        main = soup.find("main") or soup
        for link in main.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True).strip()

            # Look for Wayback Machine links
            if "web.archive.org" in href:
                # Extract year from the link text (e.g. "2022", "2019")
                year_match = re.match(r"^(\d{4})$", text)
                if year_match:
                    year = int(year_match.group(1))
                    archive_map[year] = href
                continue

            # Also look for "materials prior to" links (very old archives)
            if "prior" in text.lower() and "archive.org" in href:
                archive_map[0] = href  # Use 0 as sentinel for pre-2009

        if archive_map:
            break  # Found what we need

    return archive_map


def discover_meetings_from_archive(committee_key: str, archive_url: str, year: int) -> list[dict]:
    """
    Discover meetings from a Wayback Machine archived materials page.
    The page structure mirrors fda.gov but links may be rewritten to
    web.archive.org URLs. Meeting-level pages and PDFs usually still
    resolve on fda.gov directly.
    """
    info = COMMITTEES[committee_key]
    slug = info["slug"]

    print(f"  Fetching archive page for {year}: {archive_url[:100]}...")
    time.sleep(REQUEST_DELAY)
    soup = fetch_page(archive_url)
    if not soup:
        print(f"    Archive page not accessible for {year}")
        return []

    meetings = []
    main_content = soup.find("main") or soup.find("div", class_="field--name-body") or soup

    for link in main_content.find_all("a", href=True):
        href = link["href"]
        text = link.get_text(strip=True)

        if not text or len(text) < 10:
            continue

        # Check if this looks like a meeting link
        is_meeting = bool(re.search(
            r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d",
            text.lower()
        ))

        if not is_meeting:
            continue

        # Resolve the URL: could be relative to archive.org or fda.gov
        if href.startswith("/web/"):
            # Wayback Machine relative link — extract the original FDA URL
            # Format: /web/20201030235938/https://www.fda.gov/...
            wb_match = re.search(r"/web/\d+/(https?://.*)", href)
            if wb_match:
                full_url = wb_match.group(1)
            else:
                full_url = f"{WAYBACK_BASE}{href}"
        elif href.startswith("http"):
            full_url = href
        else:
            full_url = urljoin(archive_url, href)

        # For archive meetings, use the Wayback URL as primary (fda.gov pages are often gone)
        # but extract the fda.gov URL as fallback for newer pages that might still be live
        fda_url = None
        wb_match = re.search(r"web\.archive\.org/web/\d+/(https?://[^\"'\s]+)", full_url)
        if wb_match:
            fda_url = wb_match.group(1)

        # Extract date
        date_match = re.search(
            r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s*(\d{4})",
            text.lower()
        )
        meeting_date = ""
        if date_match:
            try:
                month_str, day_str, year_str = date_match.groups()
                dt = datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y")
                meeting_date = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        meetings.append({
            "committee": committee_key,
            "committee_name": info["name"],
            "title": text,
            "date": meeting_date,
            "url": full_url,  # Wayback URL as primary for archive meetings
            "archive_url": fda_url,  # Original fda.gov URL as fallback
            "year": year,
        })

    # Also check for direct PDF links on archive pages
    for link in main_content.find_all("a", href=True):
        href = link["href"]
        text = link.get_text(strip=True)
        if not text:
            continue

        # Look for PDF download links
        if "/media/" in href and "/download" in href:
            # Resolve to fda.gov URL
            if "web.archive.org" in href:
                wb_match = re.search(r"web\.archive\.org/web/\d+/(https?://[^\"'\s]+)", href)
                if wb_match:
                    full_url = wb_match.group(1)
                else:
                    full_url = href
            elif href.startswith("/"):
                full_url = f"{FDA_BASE}{href}"
            else:
                full_url = href

            meetings.append({
                "committee": committee_key,
                "committee_name": info["name"],
                "title": text,
                "date": "",
                "url": full_url,
                "year": year,
                "is_direct_doc": True,
            })

    print(f"    Found {len(meetings)} meetings/documents from archive")
    return meetings


# ===========================================================================
# Web Scraping Helpers
# ===========================================================================

def fetch_page(url: str, retries: int = 2) -> BeautifulSoup | None:
    """Fetch a page and return parsed HTML. Returns None on failure."""
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
            elif resp.status_code == 404:
                return None
            else:
                print(f"    HTTP {resp.status_code} for {url}")
        except requests.RequestException as e:
            print(f"    Request failed (attempt {attempt + 1}): {e}")
        if attempt < retries:
            time.sleep(REQUEST_DELAY * 2)
    return None


def download_pdf(url: str, dest_path: str) -> bool:
    """Download a PDF file to dest_path. Returns True on success."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        if resp.status_code != 200:
            return False
        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
            # Not a PDF — might be an HTML error page
            return False
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"    Download failed: {e}")
        return False


# ===========================================================================
# Meeting Discovery
# ===========================================================================

def discover_meetings(committee_key: str, year: int) -> list[dict]:
    """
    Discover all meetings for a committee in a given year.
    Returns list of dicts with: date, title, url, documents[]
    """
    info = COMMITTEES[committee_key]
    slug = info["slug"]
    materials_url = get_materials_url(slug, year)

    print(f"  Fetching {year} materials page: {materials_url}")
    time.sleep(REQUEST_DELAY)
    soup = fetch_page(materials_url)
    if not soup:
        # Try alternate URL patterns (some committees use different structures)
        alt_url = f"{FDA_BASE}/advisory-committees/{slug}/meeting-materials-{slug}"
        soup = fetch_page(alt_url)
        if not soup:
            print(f"    No materials page found for {year}")
            return []

    meetings = []

    # Look for meeting links — FDA uses various structures:
    # 1. Links containing "meeting-announcement" in the URL
    # 2. Links containing the committee slug + a date
    # 3. Links in the main content area pointing to meeting-specific pages
    main_content = soup.find("main") or soup.find("div", class_="field--name-body") or soup

    # Find all links that look like meeting pages
    for link in main_content.find_all("a", href=True):
        href = link["href"]
        text = link.get_text(strip=True)

        # Skip non-meeting links
        if not text or len(text) < 10:
            continue

        # Match meeting announcement links
        full_url = urljoin(FDA_BASE, href)
        is_meeting = (
            "meeting-announcement" in href.lower()
            or "meeting-materials" in href.lower()
            or re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b.*\d{4}", text.lower())
        )

        if is_meeting and slug.split("-")[0] in href.lower():
            # Extract date from text or URL
            date_match = re.search(
                r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s*(\d{4})",
                text.lower()
            )
            meeting_date = ""
            if date_match:
                try:
                    month_str, day_str, year_str = date_match.groups()
                    dt = datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y")
                    meeting_date = dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass

            meetings.append({
                "committee": committee_key,
                "committee_name": info["name"],
                "title": text,
                "date": meeting_date,
                "url": full_url,
                "year": year,
            })

    # Also look for direct PDF links on the materials page itself
    # (some committees list documents directly without sub-pages)
    for link in main_content.find_all("a", href=True):
        href = link["href"]
        if "/media/" in href and "/download" in href:
            text = link.get_text(strip=True)
            if text:
                # This is a direct document link
                full_url = urljoin(FDA_BASE, href)
                meetings.append({
                    "committee": committee_key,
                    "committee_name": info["name"],
                    "title": text,
                    "date": "",
                    "url": full_url,
                    "year": year,
                    "is_direct_doc": True,
                })

    print(f"    Found {len(meetings)} meetings/documents")
    return meetings


def scrape_meeting_documents(meeting: dict) -> list[dict]:
    """
    Given a meeting dict (from discover_meetings), fetch the meeting page
    and extract all downloadable document links.
    Returns list of dicts with: title, url, doc_type
    """
    if meeting.get("is_direct_doc"):
        # Already a direct document link
        doc_type = classify_document(meeting["title"], meeting["url"])
        return [{
            "title": meeting["title"],
            "url": meeting["url"],
            "doc_type": doc_type,
        }]

    print(f"    Scraping meeting page: {meeting['title'][:80]}")
    time.sleep(REQUEST_DELAY)
    soup = fetch_page(meeting["url"])
    if not soup and meeting.get("archive_url"):
        # Fallback to Wayback Machine URL
        print(f"      FDA URL failed, trying archive URL...")
        time.sleep(REQUEST_DELAY)
        soup = fetch_page(meeting["archive_url"])
    if not soup:
        return []

    documents = []
    main_content = soup.find("main") or soup

    for link in main_content.find_all("a", href=True):
        href = link["href"]
        text = link.get_text(strip=True)

        # Look for downloadable documents (PDFs hosted on FDA)
        if "/media/" in href and "/download" in href and text:
            # Handle Wayback-rewritten URLs: extract the original fda.gov URL
            wb_match = re.search(r"/web/\d+/(https?://[^\"'\s]+)", href)
            if wb_match:
                full_url = wb_match.group(1)
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = urljoin(FDA_BASE, href)

            doc_type = classify_document(text, full_url)
            documents.append({
                "title": text,
                "url": full_url,
                "doc_type": doc_type,
            })

    print(f"      Found {len(documents)} documents")
    return documents


def classify_document(title: str, url: str) -> str:
    """Classify an AdCom document by its title/URL."""
    t = title.lower()
    if "transcript" in t:
        return "adcom_transcript"
    elif "briefing" in t and "fda" in t:
        return "adcom_fda_briefing"
    elif "briefing" in t:
        return "adcom_sponsor_briefing"
    elif "presentation" in t and "fda" in t:
        return "adcom_fda_presentation"
    elif "presentation" in t or "slide" in t:
        return "adcom_sponsor_presentation"
    elif "roster" in t:
        return "adcom_roster"
    elif "agenda" in t:
        return "adcom_agenda"
    elif "question" in t:
        return "adcom_questions"
    elif "minutes" in t or "summary" in t:
        return "adcom_minutes"
    elif "vote" in t or "voting" in t:
        return "adcom_voting"
    else:
        return "adcom_other"


# ===========================================================================
# Document Processing & Embedding
# ===========================================================================

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")

# Priority document types — these are the most valuable for analysis
PRIORITY_DOC_TYPES = {
    "adcom_transcript",
    "adcom_fda_briefing",
    "adcom_sponsor_briefing",
    "adcom_fda_presentation",
    "adcom_sponsor_presentation",
    "adcom_minutes",
    "adcom_questions",
}


def process_and_embed(meeting: dict, doc: dict, dry_run: bool = False) -> bool:
    """
    Download a document PDF, extract text, chunk, embed, and store in Neon.
    Returns True if document was successfully processed.
    """
    if doc["doc_type"] not in PRIORITY_DOC_TYPES:
        return False  # Skip low-value docs (rosters, agendas)

    if dry_run:
        print(f"      [DRY RUN] Would process: {doc['title'][:60]} ({doc['doc_type']})")
        return True

    if not DATABASE_URL or not VOYAGE_API_KEY:
        print("      ERROR: NEON_DATABASE_URL and VOYAGE_API_KEY required for embedding")
        return False

    # Check if already in DB
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # Use URL hash as dedup key
        url_hash = hashlib.md5(doc["url"].encode()).hexdigest()[:16]
        cur.execute(
            "SELECT id FROM documents WHERE file_path = %s",
            (f"adcom:{url_hash}",)
        )
        if cur.fetchone():
            print(f"      Already exists: {doc['title'][:60]}")
            conn.close()
            return False
        conn.close()
    except Exception as e:
        print(f"      DB check failed: {e}")

    # Download PDF to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    print(f"      Downloading: {doc['title'][:60]}...")
    time.sleep(REQUEST_DELAY)
    if not download_pdf(doc["url"], tmp_path):
        print(f"      Failed to download")
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return False

    file_size = os.path.getsize(tmp_path)
    if file_size < 1000:
        print(f"      File too small ({file_size} bytes) — likely not a PDF")
        os.unlink(tmp_path)
        return False

    print(f"      Downloaded: {file_size / 1024 / 1024:.1f} MB")

    # Extract text
    try:
        # Add embed_documents directory to path
        _SEARCH_DIR = os.path.join(os.path.dirname(_THIS_DIR), "search")
        if _SEARCH_DIR not in sys.path:
            sys.path.insert(0, _SEARCH_DIR)
        from embed_documents import extract_text_with_pages, semantic_chunk_document

        pages = extract_text_with_pages(tmp_path)
        if not pages:
            print(f"      No extractable text in PDF")
            os.unlink(tmp_path)
            return False

        page_count = len(pages)
        all_text = " ".join(p["text"] for p in pages)
        word_count = len(all_text.split())
        if word_count < 50:
            print(f"      Too little text ({word_count} words)")
            os.unlink(tmp_path)
            return False

        print(f"      {word_count} words across {page_count} pages")

        # Chunk using the page-aware chunker
        chunks = semantic_chunk_document(pages)
        print(f"      Split into {len(chunks)} chunks")

        # Embed and store
        import voyageai
        import psycopg2
        vo = voyageai.Client(api_key=VOYAGE_API_KEY)
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        url_hash = hashlib.md5(doc["url"].encode()).hexdigest()[:16]
        committee_key = meeting["committee"]
        committee_name = meeting["committee_name"]

        # Build a descriptive title
        doc_title = f"[{committee_key}] {doc['title']}"
        if meeting.get("date"):
            doc_title = f"[{committee_key} {meeting['date']}] {doc['title']}"

        # Insert document record
        cur.execute("""
            INSERT INTO documents (ticker, company_name, filename, file_path, doc_type, title, date, word_count, page_count, file_size_bytes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            f"FDA_{committee_key}",
            committee_name,
            doc["title"][:200],
            f"adcom:{url_hash}",
            doc["doc_type"],
            doc_title,
            meeting.get("date") or None,
            word_count,
            page_count,
            file_size,
        ))
        doc_id = cur.fetchone()[0]

        # Embed chunks in batches
        batch_size = 20
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c["content"] for c in batch]
            embeddings = vo.embed(texts, model="voyage-3", input_type="document").embeddings

            for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                cur.execute("""
                    INSERT INTO chunks (document_id, chunk_index, page_number, section_title, content, token_count, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    doc_id,
                    i + j,
                    chunk.get("page_number", 0),
                    chunk.get("section_title", ""),
                    chunk["content"],
                    chunk.get("token_count", len(chunk["content"].split())),
                    json.dumps(embedding),
                ))

        conn.commit()
        conn.close()
        print(f"      Stored: doc #{doc_id}, {len(chunks)} chunks")
        os.unlink(tmp_path)
        return True

    except ImportError as e:
        print(f"      Import error (missing dependency): {e}")
        os.unlink(tmp_path)
        return False
    except Exception as e:
        print(f"      Processing error: {e}")
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return False


# ===========================================================================
# Main Pipeline
# ===========================================================================

def scrape_committee(committee_key: str, years: list[int], dry_run: bool = False,
                     include_archive: bool = False) -> dict:
    """
    Full scrape pipeline for one committee across specified years.
    If include_archive=True, also scrapes Wayback Machine archived years.
    Returns stats dict.
    """
    info = COMMITTEES[committee_key]
    print(f"\n{'=' * 60}")
    print(f"  {committee_key} — {info['name']}")
    print(f"  Center: {info['center']} | Area: {info['area']} | Years: {years}")
    if include_archive:
        print(f"  Archive mode: ON (will scrape Wayback Machine for older years)")
    print(f"{'=' * 60}\n")

    stats = {"meetings": 0, "documents": 0, "embedded": 0, "skipped": 0}

    # ── Live years (2023+) ──
    live_years = [y for y in years if y >= 2023]
    archive_years_requested = [y for y in years if y < 2023]

    for year in live_years:
        meetings = discover_meetings(committee_key, year)
        stats["meetings"] += len(meetings)

        for meeting in meetings:
            documents = scrape_meeting_documents(meeting)
            stats["documents"] += len(documents)

            for doc in documents:
                if process_and_embed(meeting, doc, dry_run=dry_run):
                    stats["embedded"] += 1
                else:
                    stats["skipped"] += 1

    # ── Archive years (pre-2023, Wayback Machine) ──
    if include_archive or archive_years_requested:
        archive_map = discover_archive_urls(committee_key)
        if archive_map:
            print(f"\n  Archive years available: {sorted(y for y in archive_map if y > 0)}")

        target_archive_years = archive_years_requested if archive_years_requested else sorted(archive_map.keys())

        for year in target_archive_years:
            if year == 0:
                continue  # Skip pre-2009 deep archive for now
            if year not in archive_map:
                print(f"\n  No archive URL found for {year}, trying live URL...")
                meetings = discover_meetings(committee_key, year)
            else:
                meetings = discover_meetings_from_archive(
                    committee_key, archive_map[year], year
                )

            stats["meetings"] += len(meetings)

            for meeting in meetings:
                documents = scrape_meeting_documents(meeting)
                stats["documents"] += len(documents)

                for doc in documents:
                    if process_and_embed(meeting, doc, dry_run=dry_run):
                        stats["embedded"] += 1
                    else:
                        stats["skipped"] += 1

    print(f"\n  {committee_key} Summary: {stats['meetings']} meetings, "
          f"{stats['documents']} documents found, "
          f"{stats['embedded']} embedded, {stats['skipped']} skipped")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="FDA Advisory Committee Meeting Materials Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 adcom_scraper.py --committee ODAC                    # Oncology drugs
  python3 adcom_scraper.py --committee ODAC,CTGTAC,VRBPAC     # Multiple committees
  python3 adcom_scraper.py --all --priority 1                   # All high-priority committees
  python3 adcom_scraper.py --all --years 2023,2024,2025        # Specific years
  python3 adcom_scraper.py --list                               # List all committees
  python3 adcom_scraper.py --committee ODAC --dry-run           # Preview without downloading
        """,
    )
    parser.add_argument("--committee", type=str, help="Comma-separated committee abbreviations (e.g. ODAC,CTGTAC)")
    parser.add_argument("--all", action="store_true", help="Process all committees")
    parser.add_argument("--priority", type=int, help="Only committees with this priority level (1=highest)")
    parser.add_argument("--years", type=str, help="Comma-separated years (default: 2023-2025)")
    parser.add_argument("--list", action="store_true", help="List all tracked committees and exit")
    parser.add_argument("--dry-run", action="store_true", help="Preview without downloading or embedding")
    parser.add_argument("--archive", action="store_true", help="Include Wayback Machine archive years (pre-2023)")

    args = parser.parse_args()

    if args.list:
        print(f"\n{'Abbrev':<10} {'Center':<6} {'Pri':<4} {'Area':<20} Name")
        print("-" * 90)
        for key, info in sorted(COMMITTEES.items(), key=lambda x: (x[1]["priority"], x[1]["center"], x[0])):
            print(f"{key:<10} {info['center']:<6} {info['priority']:<4} {info['area']:<20} {info['name']}")
        print(f"\nTotal: {len(COMMITTEES)} committees")
        return

    if not args.all and not args.committee:
        parser.print_help()
        sys.exit(1)

    # Determine years
    current_year = datetime.now().year
    if args.years:
        years = [int(y.strip()) for y in args.years.split(",")]
    else:
        years = list(range(current_year - 2, current_year + 1))  # Last 3 years

    # Determine committees
    if args.all:
        committees = list(COMMITTEES.keys())
        if args.priority:
            committees = [k for k in committees if COMMITTEES[k]["priority"] <= args.priority]
    else:
        committees = [c.strip().upper() for c in args.committee.split(",")]
        for c in committees:
            if c not in COMMITTEES:
                print(f"Unknown committee: {c}. Use --list to see all options.")
                sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"  FDA AdCom Scraper")
    print(f"  Committees: {len(committees)} | Years: {years} | Dry run: {args.dry_run}")
    print(f"{'=' * 60}")

    total_stats = {"meetings": 0, "documents": 0, "embedded": 0, "skipped": 0}
    start_time = time.time()

    for committee_key in committees:
        stats = scrape_committee(committee_key, years, dry_run=args.dry_run,
                                include_archive=args.archive)
        for k in total_stats:
            total_stats[k] += stats[k]

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  Scrape Complete — {int(elapsed // 60)}m {int(elapsed % 60)}s")
    print(f"  Meetings discovered: {total_stats['meetings']}")
    print(f"  Documents found:     {total_stats['documents']}")
    print(f"  Documents embedded:  {total_stats['embedded']}")
    print(f"  Documents skipped:   {total_stats['skipped']}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
