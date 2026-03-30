"""
SatyaBio — PubMed Deep-Dive Literature Agent

Goes beyond basic PubMed title search to fetch:
  1. Full abstracts (via NCBI efetch)
  2. Full-text articles from PubMed Central (PMC) when open-access
  3. Drug-specific literature for pipeline programs
  4. Clinical data extraction from open-access papers

This is what closes the gap with Open Evidence — they surface granular data
(EEG delta power, dose-response, macaque model data) because they read the
actual papers, not just titles.

NCBI APIs used (all free, no key required but key increases rate limit):
  - esearch: find PMIDs matching a query
  - efetch: get full abstracts as XML
  - elink: find PMC IDs linked to PubMed articles
  - efetch on PMC: get full-text XML from PubMed Central

Usage:
    from pubmed_deepdive import deep_search, format_deep_literature_for_claude

    results = deep_search("GTX-102 Angelman", max_papers=5)
    context = format_deep_literature_for_claude(results)

Rate limits:
  - Without API key: 3 requests/sec
  - With NCBI_API_KEY: 10 requests/sec
  - We batch requests and add small delays to stay safe
"""

import os
import re
import time
import requests
import xml.etree.ElementTree as ET
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
load_dotenv()

# ── NCBI API endpoints ──
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ELINK = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
PMC_OA_API = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"

NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")
HEADERS = {"User-Agent": "SatyaBio/1.0 (biotech-research; contact@satyabio.com)"}

# Rate limiting
_last_request_time = 0.0
_min_interval = 0.35 if NCBI_API_KEY else 0.5  # seconds between requests


def _rate_limit():
    """Ensure we don't exceed NCBI rate limits."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    _last_request_time = time.time()


def _base_params() -> dict:
    """Common params for all NCBI requests."""
    params = {}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    return params


# =============================================================================
# 1. SEARCH + FETCH ABSTRACTS
# =============================================================================

def search_with_abstracts(
    query: str,
    max_results: int = 10,
    sort: str = "relevance",
) -> list[dict]:
    """
    Search PubMed and fetch FULL ABSTRACTS (not just titles).

    Returns list of dicts with: pmid, title, authors, journal, pub_date,
    abstract, doi, pmc_id (if open access).
    """
    # Step 1: Search for PMIDs
    _rate_limit()
    search_params = {
        **_base_params(),
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": sort,
        "retmode": "json",
    }

    try:
        resp = requests.get(ESEARCH, params=search_params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        pmids = resp.json().get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"  PubMed search error: {e}")
        return []

    if not pmids:
        return []

    # Step 2: Fetch full abstracts via efetch XML
    _rate_limit()
    fetch_params = {
        **_base_params(),
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "xml",
        "retmode": "xml",
    }

    try:
        resp = requests.get(EFETCH, params=fetch_params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        articles = _parse_pubmed_xml(resp.text)
    except Exception as e:
        print(f"  PubMed efetch error: {e}")
        return []

    # Step 3: Check which have PMC full text available
    pmc_map = _get_pmc_ids(pmids)
    for article in articles:
        pmid = article.get("pmid", "")
        if pmid in pmc_map:
            article["pmc_id"] = pmc_map[pmid]

    return articles


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    """Parse PubMed efetch XML into structured article dicts with full abstracts."""
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    for article_el in root.findall(".//PubmedArticle"):
        citation = article_el.find(".//MedlineCitation")
        if citation is None:
            continue

        pmid_el = citation.find("PMID")
        pmid = pmid_el.text if pmid_el is not None else ""

        article_data = citation.find("Article")
        if article_data is None:
            continue

        # Title
        title_el = article_data.find("ArticleTitle")
        title = _get_text(title_el)

        # Abstract — concatenate all AbstractText elements
        abstract_parts = []
        abstract_el = article_data.find("Abstract")
        if abstract_el is not None:
            for abs_text in abstract_el.findall("AbstractText"):
                label = abs_text.get("Label", "")
                text = _get_text(abs_text)
                if label and text:
                    abstract_parts.append(f"{label}: {text}")
                elif text:
                    abstract_parts.append(text)
        abstract = " ".join(abstract_parts)

        # Authors
        authors = []
        author_list = article_data.find("AuthorList")
        if author_list is not None:
            for author in author_list.findall("Author"):
                last = author.find("LastName")
                fore = author.find("ForeName")
                if last is not None:
                    name = last.text or ""
                    if fore is not None and fore.text:
                        name = f"{fore.text} {name}"
                    authors.append(name)

        # Journal
        journal_el = article_data.find(".//Journal/Title")
        journal = journal_el.text if journal_el is not None else ""

        # Date
        pub_date = ""
        date_el = article_data.find(".//PubDate")
        if date_el is not None:
            year = date_el.find("Year")
            month = date_el.find("Month")
            if year is not None:
                pub_date = year.text or ""
                if month is not None and month.text:
                    pub_date = f"{month.text} {pub_date}"

        # DOI
        doi = ""
        for id_el in article_el.findall(".//ArticleIdList/ArticleId"):
            if id_el.get("IdType") == "doi":
                doi = id_el.text or ""
                break

        # PMC ID
        pmc_id = ""
        for id_el in article_el.findall(".//ArticleIdList/ArticleId"):
            if id_el.get("IdType") == "pmc":
                pmc_id = id_el.text or ""
                break

        articles.append({
            "pmid": pmid,
            "title": title,
            "authors": authors[:6],
            "journal": journal,
            "pub_date": pub_date,
            "abstract": abstract,
            "doi": doi,
            "pmc_id": pmc_id,
            "full_text": "",  # Filled in later if PMC available
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })

    return articles


def _get_text(el) -> str:
    """Extract text from an XML element, including mixed content (text + children)."""
    if el is None:
        return ""
    # itertext() gets all text including within child elements
    return "".join(el.itertext()).strip()


def _get_pmc_ids(pmids: list[str]) -> dict:
    """Find PMC IDs for a list of PubMed IDs (indicates full-text availability)."""
    if not pmids:
        return {}

    _rate_limit()
    params = {
        **_base_params(),
        "dbfrom": "pubmed",
        "db": "pmc",
        "id": ",".join(pmids),
        "retmode": "json",
    }

    try:
        resp = requests.get(ELINK, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {}

    pmc_map = {}
    for linkset in data.get("linksets", []):
        pmid = str(linkset.get("ids", [None])[0])
        links = linkset.get("linksetdbs", [])
        for link_db in links:
            if link_db.get("dbto") == "pmc":
                pmc_links = link_db.get("links", [])
                if pmc_links:
                    pmc_map[pmid] = f"PMC{pmc_links[0]}"
    return pmc_map


# =============================================================================
# 2. FETCH PMC FULL TEXT (open-access papers)
# =============================================================================

def fetch_pmc_fulltext(pmc_id: str, max_chars: int = 15000) -> str:
    """
    Fetch full text of an open-access article from PubMed Central.

    Returns extracted text (capped at max_chars). Returns empty string
    if not available or not open access.
    """
    # Remove "PMC" prefix if present for the API
    pmc_num = pmc_id.replace("PMC", "")

    _rate_limit()
    params = {
        **_base_params(),
        "db": "pmc",
        "id": pmc_num,
        "rettype": "xml",
        "retmode": "xml",
    }

    try:
        resp = requests.get(EFETCH, params=params, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return ""

        text = _extract_text_from_pmc_xml(resp.text)
        return text[:max_chars] if text else ""
    except Exception as e:
        print(f"  PMC fetch error for {pmc_id}: {e}")
        return ""


def _extract_text_from_pmc_xml(xml_text: str) -> str:
    """Extract readable text from PMC full-text XML."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ""

    sections = []

    # Extract article body sections
    body = root.find(".//body")
    if body is not None:
        for sec in body.findall(".//sec"):
            title_el = sec.find("title")
            section_title = title_el.text if title_el is not None else ""

            # Get all paragraph text in this section
            paragraphs = []
            for p in sec.findall(".//p"):
                p_text = "".join(p.itertext()).strip()
                if p_text:
                    paragraphs.append(p_text)

            if paragraphs:
                if section_title:
                    sections.append(f"\n## {section_title}\n")
                sections.extend(paragraphs)

    # If no body sections, try the abstract
    if not sections:
        abstract = root.find(".//abstract")
        if abstract is not None:
            for p in abstract.findall(".//p"):
                p_text = "".join(p.itertext()).strip()
                if p_text:
                    sections.append(p_text)

    # Extract key tables (just captions + data, not full markup)
    for table_wrap in root.findall(".//table-wrap"):
        caption = table_wrap.find(".//caption")
        if caption is not None:
            cap_text = "".join(caption.itertext()).strip()
            if cap_text:
                sections.append(f"\n[Table: {cap_text}]")

    # Extract figure captions (often contain key data)
    for fig in root.findall(".//fig"):
        caption = fig.find(".//caption")
        if caption is not None:
            cap_text = "".join(caption.itertext()).strip()
            if cap_text:
                sections.append(f"\n[Figure: {cap_text}]")

    return "\n".join(sections)


# =============================================================================
# 3. DRUG-SPECIFIC DEEP SEARCH
# =============================================================================

def deep_search_for_drugs(
    drugs: list[str],
    disease: str,
    max_papers_per_drug: int = 3,
    fetch_fulltext: bool = True,
    max_fulltext: int = 5,
) -> list[dict]:
    """
    For each drug in a pipeline, search PubMed for clinical/preclinical data
    and fetch full text where available.

    This is the key function that closes the gap with Open Evidence — it
    provides the granular clinical data (EEG biomarkers, dose-response,
    safety signals) that basic PubMed title searches miss.

    Args:
        drugs: list of drug names to search for
        disease: the disease context
        max_papers_per_drug: how many papers to fetch per drug
        fetch_fulltext: whether to fetch PMC full text
        max_fulltext: total cap on full-text fetches (API budget)

    Returns:
        list of enriched article dicts with abstracts and (optionally) full text
    """
    all_results = []
    fulltext_count = 0

    for drug in drugs:
        # Search for this drug + disease
        query = f'"{drug}" AND "{disease}"'
        papers = search_with_abstracts(query, max_results=max_papers_per_drug)

        if not papers:
            # Try without quotes (for multi-word drug names)
            query = f'{drug} {disease} clinical trial OR preclinical'
            papers = search_with_abstracts(query, max_results=max_papers_per_drug)

        for paper in papers:
            paper["search_drug"] = drug  # Tag which drug this was found for

            # Fetch full text if PMC available and under budget
            if fetch_fulltext and paper.get("pmc_id") and fulltext_count < max_fulltext:
                full_text = fetch_pmc_fulltext(paper["pmc_id"])
                if full_text:
                    paper["full_text"] = full_text
                    fulltext_count += 1
                    print(f"    Full text fetched: {paper['pmc_id']} ({len(full_text)} chars)")

            all_results.append(paper)

    return all_results


# =============================================================================
# 4. BROAD DEEP SEARCH (single query, with abstracts + full text)
# =============================================================================

def deep_search(
    query: str,
    max_papers: int = 8,
    fetch_fulltext: bool = True,
    max_fulltext: int = 4,
) -> list[dict]:
    """
    Enhanced PubMed search that returns abstracts + full text where available.
    Drop-in improvement over the basic search_pubmed() in api_connectors.py.
    """
    papers = search_with_abstracts(query, max_results=max_papers)

    fulltext_count = 0
    for paper in papers:
        if fetch_fulltext and paper.get("pmc_id") and fulltext_count < max_fulltext:
            full_text = fetch_pmc_fulltext(paper["pmc_id"])
            if full_text:
                paper["full_text"] = full_text
                fulltext_count += 1

    return papers


# =============================================================================
# 5. FORMAT FOR CLAUDE SYNTHESIS
# =============================================================================

def format_deep_literature_for_claude(papers: list[dict]) -> str:
    """
    Format deep literature search results for Claude's synthesis context.

    Key difference from the basic formatter: includes full abstracts and
    excerpted full-text sections, giving Claude the granular clinical data
    it needs to produce Open Evidence-quality output.
    """
    if not papers:
        return ""

    lines = []
    lines.append("=== DEEP LITERATURE (PubMed + PMC Full Text) ===")
    lines.append(f"Papers retrieved: {len(papers)}")
    full_count = sum(1 for p in papers if p.get("full_text"))
    if full_count:
        lines.append(f"Open-access full text available: {full_count} papers")
    lines.append("IMPORTANT: Extract specific clinical data points from these papers — "
                 "efficacy numbers (ORR, PFS, OS), biomarker data (EEG, imaging), "
                 "dose-response relationships, safety signals, and preclinical findings. "
                 "Cite as {{pubmed:PMID|AuthorName}}.")
    lines.append("")

    for paper in papers:
        pmid = paper.get("pmid", "?")
        title = paper.get("title", "Untitled")
        authors = paper.get("authors", [])
        first_author = authors[0].split()[-1] if authors else "Unknown"
        journal = paper.get("journal", "")
        date = paper.get("pub_date", "")
        drug = paper.get("search_drug", "")
        pmc = paper.get("pmc_id", "")

        lines.append(f"── PMID:{pmid} | {first_author} et al. | {journal} ({date}) ──")
        if drug:
            lines.append(f"  Drug context: {drug}")
        lines.append(f"  Title: {title}")

        # Full abstract
        abstract = paper.get("abstract", "")
        if abstract:
            # Truncate very long abstracts but keep the meat
            if len(abstract) > 2000:
                abstract = abstract[:2000] + "..."
            lines.append(f"  Abstract: {abstract}")

        # Full text excerpt (if available)
        full_text = paper.get("full_text", "")
        if full_text:
            lines.append(f"  [PMC Full Text Available: {pmc}]")
            # Include key sections — results and discussion are most valuable
            sections_to_include = _extract_key_sections(full_text)
            if sections_to_include:
                lines.append(f"  Key findings from full text:")
                lines.append(f"  {sections_to_include}")

        lines.append("")

    return "\n".join(lines)


def _extract_key_sections(full_text: str, max_chars: int = 3000) -> str:
    """
    Extract the most valuable sections from PMC full text.
    Prioritizes: Results, Discussion, Conclusions, Efficacy, Safety.
    """
    # Split into sections
    sections = re.split(r'\n## ', full_text)

    priority_keywords = [
        "result", "efficac", "outcome", "response", "safety",
        "adverse", "toxicity", "pharmacokinetic", "biomarker",
        "endpoint", "primary", "secondary", "dose", "conclusion",
        "discussion", "clinical", "patient", "trial", "treatment",
        "eeg", "imaging", "survival", "tolerab",
    ]

    key_parts = []
    chars_used = 0

    for section in sections:
        section_lower = section.lower()
        if any(kw in section_lower for kw in priority_keywords):
            # This section is relevant — include it
            available = max_chars - chars_used
            if available <= 0:
                break
            trimmed = section[:available].strip()
            if trimmed:
                key_parts.append(trimmed)
                chars_used += len(trimmed)

    if not key_parts:
        # No labeled sections found — just take the first chunk
        return full_text[:max_chars]

    return "\n".join(key_parts)


# =============================================================================
# 6. PIPELINE LITERATURE ENRICHMENT
# =============================================================================

def enrich_pipeline_with_literature(
    programs: list[dict],
    disease: str,
    max_papers_per_drug: int = 2,
    max_total_fulltext: int = 6,
) -> list[dict]:
    """
    Given a list of pipeline programs (from disease_space_map or dynamic_discovery),
    search PubMed for each drug and return enriched literature results.

    This is the orchestrator function that the query router should call.
    """
    # Extract unique drug names from programs
    drug_names = []
    seen = set()
    for prog in programs:
        name = prog.get("drug_name", "").strip()
        if name and name.lower() not in seen:
            # Clean up drug names: take first name if multiple aliases
            clean_name = name.split("(")[0].strip().split("/")[0].strip()
            if clean_name and len(clean_name) > 2:
                drug_names.append(clean_name)
                seen.add(name.lower())

    if not drug_names:
        return []

    print(f"  Deep literature search for {len(drug_names)} drugs: {', '.join(drug_names[:8])}")
    results = deep_search_for_drugs(
        drugs=drug_names[:10],  # Cap at 10 drugs to avoid rate limits
        disease=disease,
        max_papers_per_drug=max_papers_per_drug,
        fetch_fulltext=True,
        max_fulltext=max_total_fulltext,
    )

    print(f"  Found {len(results)} papers, {sum(1 for r in results if r.get('full_text'))} with full text")
    return results


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "GTX-102 apazunersen Angelman syndrome"

    print(f"\nDeep PubMed search: {query}\n")
    results = deep_search(query, max_papers=5, fetch_fulltext=True, max_fulltext=3)

    for paper in results:
        print(f"PMID: {paper['pmid']}")
        print(f"  Title: {paper['title']}")
        print(f"  Journal: {paper['journal']} ({paper['pub_date']})")
        print(f"  PMC: {paper.get('pmc_id', 'N/A')}")
        abstract = paper.get("abstract", "")
        print(f"  Abstract: {abstract[:300]}..." if len(abstract) > 300 else f"  Abstract: {abstract}")
        if paper.get("full_text"):
            print(f"  Full text: {len(paper['full_text'])} chars")
        print()

    print(f"\nTotal: {len(results)} papers, {sum(1 for r in results if r.get('full_text'))} with full text")
