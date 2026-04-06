"""
SatyaBio PubMed Scraper — Pulls published research from PubMed/PMC and embeds into Neon.

Searches PubMed by drug name, target, company name, or disease. Downloads abstracts
(and full text from PubMed Central when freely available). Embeds into the same
Neon database for RAG search.

Usage:
    python3 pubmed_scraper.py                                              # Search for all tracked drugs
    python3 pubmed_scraper.py --ticker CNTA                                # Search by company drugs
    python3 pubmed_scraper.py --query "ORX750 orexin" --ticker-label LXEO  # Custom search with ticker
    python3 pubmed_scraper.py --max-results 50                             # Limit results (default: 20)
    python3 pubmed_scraper.py --list-queries                               # Show what searches it would run

Requires in .env:
    NEON_DATABASE_URL=postgresql://...
    VOYAGE_API_KEY=your-voyage-key

Uses NCBI E-utilities (free, no API key required for <3 requests/sec).
Set NCBI_API_KEY in .env for higher rate limits (10 req/sec).
"""

import os
import sys
import re
import json
import hashlib
import argparse
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Try importing required packages
try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests --quiet")
    import requests

try:
    import psycopg2
except ImportError:
    os.system(f"{sys.executable} -m pip install psycopg2-binary --quiet")
    import psycopg2

try:
    import voyageai
except ImportError:
    os.system(f"{sys.executable} -m pip install voyageai --quiet")
    import voyageai


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")  # Optional — get from ncbi.nlm.nih.gov/account
EMBED_MODEL = "voyage-3"
EMBED_BATCH_SIZE = 32
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PMC_OA_BASE = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"

# Rate limiting: 3/sec without API key, 10/sec with
REQUEST_DELAY = 0.35 if NCBI_API_KEY else 1.0

# Drug/company search queries — ticker to PubMed search terms
SEARCH_QUERIES = {
    # Existing portfolio
    "NUVL": ["nuvalent OR NVL-520 OR NVL-655 OR zidesamtinib"],
    "CELC": ["celcuity OR gedatolisib OR PI3K-alpha"],
    "PYXS": ["pyxis oncology OR MICVO OR PYX-201"],
    "RVMD": ["revolution medicines OR RMC-6236 OR RAS(ON)"],
    "RLAY": ["relay therapeutics OR RLY-2608 OR PI3Kalpha mutant-selective"],
    "IOVA": ["iovance OR lifileucel OR amtagvi OR TIL therapy melanoma"],
    "VIR": ["vir biotechnology OR tobevibart OR VIR-2218"],
    "JANX": ["janux therapeutics OR JANX007 OR JANX008"],
    "CGON": ["CG oncology OR cretostimogene OR CG0070 OR NMIBC oncolytic"],
    "URGN": ["urogen pharma OR UGN-102 OR UGN-101 OR uroretev"],
    "VSTM": ["verastem oncology OR avutometinib OR defactinib OR VS-6766"],
    "IBRX": ["immunitybio OR anktiva OR N-803 OR IL-15 superagonist BCG"],
    "TNGX": ["tango therapeutics OR TNG908 OR TNG462 OR synthetic lethal MTAP"],
    # New additions
    "CNTA": ["centessa pharmaceuticals OR ORX750 OR orexin agonist narcolepsy"],
    # Big pharma (selective searches — focus on pipeline news, not everything)
    "PFE": ["pfizer oncology pipeline 2024 2025 2026"],
    "MRK": ["merck keytruda combination clinical trial 2024 2025"],
    "AZN": ["astrazeneca enhertu OR datopotamab deruxtecan 2024 2025"],
    "GILD": ["gilead oncology OR trodelvy OR magrolimab 2024 2025"],
    "TAK": ["takeda orexin OR TAK-861 OR danavorexton 2024 2025"],
    # Chinese biotechs
    "BGNE": ["beigene OR zanubrutinib OR tislelizumab"],
    "LEGN": ["legend biotech OR ciltacabtagene OR carvykti"],
    "HCM": ["hutchmed OR fruquintinib OR surufatinib"],
    # Bicycle
    "BCYC": ["bicycle therapeutics OR BT8009 OR BT5528"],
    # argenx / Kymera (already in portfolio)
    "ARGX": ["argenx OR efgartigimod OR vyvgart"],
    "KYMR": ["kymera therapeutics OR KT-621 OR STAT6 degrader"],
}


# ---------------------------------------------------------------------------
# NCBI E-utilities
# ---------------------------------------------------------------------------

def _eutils_params():
    """Common params for all E-utilities requests."""
    params = {"retmode": "xml"}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    return params


def search_pubmed(query, max_results=20):
    """Search PubMed and return list of PMIDs."""
    params = {
        **_eutils_params(),
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": "date",
        "datetype": "pdat",
        "mindate": "2023/01/01",  # Last ~3 years
        "maxdate": "2026/12/31",
    }
    try:
        r = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=15)
        root = ET.fromstring(r.text)
        pmids = [id_elem.text for id_elem in root.findall(".//Id")]
        count = root.findtext(".//Count", "0")
        return pmids, int(count)
    except Exception as e:
        print(f"    Search error: {e}")
        return [], 0


def fetch_pubmed_articles(pmids):
    """Fetch full article records for a list of PMIDs."""
    if not pmids:
        return []

    params = {
        **_eutils_params(),
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "xml",
    }
    try:
        r = requests.get(f"{EUTILS_BASE}/efetch.fcgi", params=params, timeout=30)
        root = ET.fromstring(r.text)

        articles = []
        for article_elem in root.findall(".//PubmedArticle"):
            article = _parse_article(article_elem)
            if article:
                articles.append(article)
        return articles
    except Exception as e:
        print(f"    Fetch error: {e}")
        return []


def _parse_article(elem):
    """Parse a PubmedArticle XML element into a dict."""
    try:
        medline = elem.find(".//MedlineCitation")
        article = medline.find(".//Article")

        pmid = medline.findtext(".//PMID", "")
        title = article.findtext(".//ArticleTitle", "")
        journal = article.findtext(".//Journal/Title", "")
        journal_abbrev = article.findtext(".//Journal/ISOAbbreviation", "")

        # Abstract
        abstract_parts = []
        for abs_text in article.findall(".//Abstract/AbstractText"):
            label = abs_text.get("Label", "")
            text = abs_text.text or ""
            # Also get tail text and any nested elements
            full_text = "".join(abs_text.itertext())
            if label:
                abstract_parts.append(f"{label}: {full_text}")
            else:
                abstract_parts.append(full_text)
        abstract = "\n".join(abstract_parts)

        # Authors
        authors = []
        for auth in article.findall(".//AuthorList/Author"):
            last = auth.findtext("LastName", "")
            first = auth.findtext("ForeName", "")
            if last:
                authors.append(f"{last} {first}".strip())

        # Date
        pub_date = None
        date_elem = article.find(".//Journal/JournalIssue/PubDate")
        if date_elem is not None:
            year = date_elem.findtext("Year", "")
            month = date_elem.findtext("Month", "01")
            day = date_elem.findtext("Day", "01")
            # Convert month name to number if needed
            month_map = {"jan": "01", "feb": "02", "mar": "03", "apr": "04",
                         "may": "05", "jun": "06", "jul": "07", "aug": "08",
                         "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
            if month.lower() in month_map:
                month = month_map[month.lower()]
            try:
                pub_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except Exception:
                pub_date = year

        # DOI
        doi = ""
        for id_elem in article.findall(".//ELocationID"):
            if id_elem.get("EIdType") == "doi":
                doi = id_elem.text or ""

        # PMC ID (for free full text)
        pmc_id = ""
        for id_elem in elem.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if id_elem.get("IdType") == "pmc":
                pmc_id = id_elem.text or ""

        # MeSH terms
        mesh_terms = []
        for mesh in medline.findall(".//MeshHeadingList/MeshHeading/DescriptorName"):
            mesh_terms.append(mesh.text or "")

        # Keywords
        keywords = []
        for kw in medline.findall(".//KeywordList/Keyword"):
            keywords.append(kw.text or "")

        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal,
            "journal_abbrev": journal_abbrev,
            "pub_date": pub_date,
            "doi": doi,
            "pmc_id": pmc_id,
            "mesh_terms": mesh_terms,
            "keywords": keywords,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }
    except Exception as e:
        return None


def fetch_pmc_fulltext(pmc_id):
    """Try to fetch full text from PubMed Central (free/open access only)."""
    if not pmc_id:
        return None

    try:
        # Use PMC OA service to check if available
        params = {"id": pmc_id}
        r = requests.get(f"{EUTILS_BASE}/efetch.fcgi",
                         params={"db": "pmc", "id": pmc_id, "rettype": "xml", **_eutils_params()},
                         timeout=20)

        if r.status_code != 200:
            return None

        root = ET.fromstring(r.text)

        # Extract body text from PMC XML
        body = root.find(".//body")
        if body is None:
            return None

        # Get all paragraph text
        paragraphs = []
        for p in body.iter("p"):
            text = "".join(p.itertext()).strip()
            if text:
                paragraphs.append(text)

        full_text = "\n\n".join(paragraphs)
        return full_text if len(full_text) > 200 else None

    except Exception as e:
        return None


# ---------------------------------------------------------------------------
# Database & Embedding
# ---------------------------------------------------------------------------

def get_db():
    if not DATABASE_URL:
        print("ERROR: NEON_DATABASE_URL not set")
        sys.exit(1)
    return psycopg2.connect(DATABASE_URL)


def ensure_publications_table(conn):
    """Create publications table if it doesn't exist."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS publications (
            id SERIAL PRIMARY KEY,
            pmid VARCHAR(20) UNIQUE NOT NULL,
            title TEXT NOT NULL,
            abstract TEXT,
            full_text TEXT,
            authors TEXT[],
            journal VARCHAR(500),
            pub_date VARCHAR(20),
            doi VARCHAR(200),
            pmc_id VARCHAR(20),
            mesh_terms TEXT[],
            keywords TEXT[],
            tickers TEXT[],
            url TEXT,
            has_fulltext BOOLEAN DEFAULT FALSE,
            word_count INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()


def publication_exists(conn, pmid):
    cur = conn.cursor()
    cur.execute("SELECT id FROM publications WHERE pmid = %s", (pmid,))
    exists = cur.fetchone() is not None
    cur.close()
    return exists


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


def embed_chunks(vo_client, texts):
    embeddings = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i:i + EMBED_BATCH_SIZE]
        try:
            result = vo_client.embed(batch, model=EMBED_MODEL, input_type="document")
            embeddings.extend(result.embeddings)
        except Exception as e:
            print(f"    Embedding error: {e}")
            embeddings.extend([None] * len(batch))
    return embeddings


# ---------------------------------------------------------------------------
# Processing pipeline
# ---------------------------------------------------------------------------

def process_article(conn, vo_client, article, tickers):
    """Store and embed a PubMed article."""
    if publication_exists(conn, article["pmid"]):
        return False

    # Try to get full text from PMC
    full_text = None
    if article["pmc_id"]:
        print(f"      Checking PMC for full text ({article['pmc_id']})...")
        full_text = fetch_pmc_fulltext(article["pmc_id"])
        if full_text:
            print(f"      Found open-access full text ({len(full_text.split())} words)")
        time.sleep(REQUEST_DELAY)

    # Build the text for embedding
    has_fulltext = full_text is not None
    embed_text = ""

    # Header with metadata
    author_str = ", ".join(article["authors"][:5])
    if len(article["authors"]) > 5:
        author_str += f" et al. ({len(article['authors'])} authors)"

    embed_text += f"PUBLICATION: {article['title']}\n"
    embed_text += f"Authors: {author_str}\n"
    embed_text += f"Journal: {article['journal']} ({article['pub_date']})\n"
    if article["doi"]:
        embed_text += f"DOI: {article['doi']}\n"
    embed_text += "\n"

    if has_fulltext:
        embed_text += full_text
    elif article["abstract"]:
        embed_text += f"ABSTRACT:\n{article['abstract']}"
    else:
        return False  # Skip articles with no content

    word_count = len(embed_text.split())

    # Store in publications table
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO publications (pmid, title, abstract, full_text, authors, journal,
                                  pub_date, doi, pmc_id, mesh_terms, keywords, tickers,
                                  url, has_fulltext, word_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        article["pmid"], article["title"], article["abstract"],
        full_text, article["authors"], article["journal"],
        article["pub_date"], article["doi"], article["pmc_id"],
        article["mesh_terms"], article["keywords"], tickers,
        article["url"], has_fulltext, word_count
    ))
    pub_id = cur.fetchone()[0]

    # Chunk and embed for RAG
    chunks = chunk_text(embed_text)
    embeddings = embed_chunks(vo_client, chunks)

    for ticker in tickers:
        # Determine company name from ticker
        company_name = ticker  # fallback
        for t, queries in SEARCH_QUERIES.items():
            if t == ticker:
                # Extract first meaningful name from query
                first_q = queries[0].split(" OR ")[0]
                company_name = first_q.title()
                break

        # Create document record
        doc_title = f"[PubMed] {article['title']}"
        cur.execute("""
            INSERT INTO documents (ticker, company_name, filename, file_path, doc_type, title, word_count, page_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            ticker, company_name, f"PMID_{article['pmid']}.xml",
            article["url"], "publication", doc_title, word_count, 1
        ))
        doc_id = cur.fetchone()[0]

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            if embedding is None:
                continue
            cur.execute("""
                INSERT INTO chunks (document_id, chunk_index, page_number, content, token_count, embedding)
                VALUES (%s, %s, %s, %s, %s, %s::vector)
            """, (doc_id, i, 1, chunk, len(chunk.split()), str(embedding)))

    conn.commit()
    cur.close()

    ft_tag = " [FULL TEXT]" if has_fulltext else ""
    print(f"    + PMID:{article['pmid']} | {article['title'][:55]}... [{', '.join(tickers)}]{ft_tag}")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args):
    print("\n=== SatyaBio PubMed Scraper ===\n")

    if not DATABASE_URL or not VOYAGE_API_KEY:
        print("ERROR: Set NEON_DATABASE_URL and VOYAGE_API_KEY in .env")
        sys.exit(1)

    conn = get_db()
    ensure_publications_table(conn)
    vo_client = voyageai.Client(api_key=VOYAGE_API_KEY)

    # Determine which queries to run
    if args.query and args.ticker:
        print("ERROR: Cannot specify both --query and --ticker")
        sys.exit(1)

    if args.query:
        # For custom queries, require --ticker-label to specify what ticker to tag them with
        if not args.ticker_label:
            print("ERROR: When using --query, you must also specify --ticker-label")
            print("Example: python3 pubmed_scraper.py --query 'ORX750 orexin' --ticker-label LXEO")
            sys.exit(1)
        ticker_label = args.ticker_label.upper()
        queries = {ticker_label: [args.query]}
    elif args.ticker:
        ticker = args.ticker.upper()
        if ticker not in SEARCH_QUERIES:
            print(f"Unknown ticker: {ticker}. Available: {', '.join(sorted(SEARCH_QUERIES.keys()))}")
            sys.exit(1)
        queries = {ticker: SEARCH_QUERIES[ticker]}
    else:
        queries = SEARCH_QUERIES

    if args.list_queries:
        print("Configured PubMed search queries:\n")
        for ticker, q_list in sorted(queries.items()):
            for q in q_list:
                print(f"  {ticker:6s} | {q}")
        return

    max_results = args.max_results
    total_new = 0

    for ticker, query_list in queries.items():
        for query in query_list:
            print(f"\n[{ticker}] Searching: {query}")

            pmids, total_count = search_pubmed(query, max_results=max_results)
            print(f"  Found {total_count} total results, fetching top {len(pmids)}")
            time.sleep(REQUEST_DELAY)

            if not pmids:
                continue

            articles = fetch_pubmed_articles(pmids)
            print(f"  Parsed {len(articles)} articles")
            time.sleep(REQUEST_DELAY)

            for article in articles:
                try:
                    was_new = process_article(conn, vo_client, article, [ticker])
                    if was_new:
                        total_new += 1
                    time.sleep(REQUEST_DELAY)
                except Exception as e:
                    print(f"    Error: {e}")
                    conn.rollback()

    conn.close()
    print(f"\nDone! Added {total_new} new publications to the database.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SatyaBio PubMed Scraper")
    parser.add_argument("--query", type=str, help="Custom PubMed search query (requires --ticker-label)")
    parser.add_argument("--ticker", type=str, help="Only search for this ticker's drugs")
    parser.add_argument("--ticker-label", type=str, help="Ticker to assign to custom --query results")
    parser.add_argument("--max-results", type=int, default=20, help="Max results per query (default: 20)")
    parser.add_argument("--list-queries", action="store_true", help="Show configured queries without running")
    args = parser.parse_args()
    run(args)
