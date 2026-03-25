"""
SatyaBio — Live API Connectors

Connects to external biotech data sources in real-time to supplement
the internal Neon RAG database. Each connector returns standardized
results that can be merged with RAG search results.

APIs:
  1. ClinicalTrials.gov v2 API — active trials by condition, sponsor, intervention
  2. OpenFDA — approved drugs, labels, adverse events
  3. PubMed (NCBI E-utilities) — peer-reviewed publications

Usage:
    from api_connectors import search_clinical_trials, search_fda_drugs, search_pubmed

    # Find all UC trials
    trials = search_clinical_trials(condition="ulcerative colitis", status="RECRUITING")

    # Find approved drugs for narcolepsy
    drugs = search_fda_drugs(condition="narcolepsy")

    # Find recent papers on KRAS inhibitors
    papers = search_pubmed(query="KRAS G12C inhibitor clinical trial", max_results=10)

NOTE: This version uses the `requests` library instead of urllib.
      Install with: pip3 install requests
      The `requests` library handles SSL certificates, URL encoding, and
      connection issues much more reliably on macOS than urllib.
"""

import os
import time
import requests
from typing import Optional


# =============================================================================
# 1. ClinicalTrials.gov v2 API
# =============================================================================

CTGOV_BASE = "https://clinicaltrials.gov/api/v2/studies"

def search_clinical_trials(
    condition: str = "",
    intervention: str = "",
    sponsor: str = "",
    status: str = "",          # RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED, etc.
    phase: str = "",           # PHASE1, PHASE2, PHASE3, PHASE4
    max_results: int = 20,
) -> list[dict]:
    """
    Search ClinicalTrials.gov v2 API.

    Returns a list of dicts with: nct_id, title, status, phase, conditions,
    interventions, sponsor, start_date, enrollment, study_type, brief_summary.
    """
    params = {
        "format": "json",
        "pageSize": min(max_results, 100),
    }

    # v2 API uses query.cond, query.intr, query.spons
    if condition:
        params["query.cond"] = condition
    if intervention:
        params["query.intr"] = intervention
    if sponsor:
        params["query.spons"] = sponsor
    if status:
        params["filter.overallStatus"] = status
    if phase:
        params["filter.phase"] = phase

    try:
        resp = requests.get(
            CTGOV_BASE,
            params=params,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) SatyaBio/1.0"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.SSLError:
        # Retry without SSL verification as fallback (macOS cert issue)
        try:
            resp = requests.get(
                CTGOV_BASE,
                params=params,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) SatyaBio/1.0"},
                timeout=20,
                verify=False,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ClinicalTrials.gov API error (SSL fallback): {e}")
            return []
    except Exception as e:
        print(f"  ClinicalTrials.gov API error: {e}")
        return []

    results = []
    for study in data.get("studies", []):
        protocol = study.get("protocolSection", {})
        id_module = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        design_module = protocol.get("designModule", {})
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
        conditions_module = protocol.get("conditionsModule", {})
        interventions_module = protocol.get("armsInterventionsModule", {})
        desc_module = protocol.get("descriptionModule", {})
        outcomes_module = protocol.get("outcomesModule", {})

        # Extract interventions
        interventions = []
        for arm in interventions_module.get("interventions", []):
            interventions.append({
                "name": arm.get("name", ""),
                "type": arm.get("type", ""),
            })

        # Extract conditions
        conditions = conditions_module.get("conditions", [])

        # Extract primary outcomes
        primary_outcomes = []
        for outcome in outcomes_module.get("primaryOutcomes", []):
            primary_outcomes.append(outcome.get("measure", ""))

        results.append({
            "source": "ClinicalTrials.gov",
            "nct_id": id_module.get("nctId", ""),
            "title": id_module.get("briefTitle", ""),
            "official_title": id_module.get("officialTitle", ""),
            "status": status_module.get("overallStatus", ""),
            "phase": ",".join(design_module.get("phases", [])),
            "conditions": conditions,
            "interventions": interventions,
            "sponsor": sponsor_module.get("leadSponsor", {}).get("name", ""),
            "start_date": status_module.get("startDateStruct", {}).get("date", ""),
            "enrollment": design_module.get("enrollmentInfo", {}).get("count", 0),
            "study_type": design_module.get("studyType", ""),
            "summary": desc_module.get("briefSummary", ""),
            "primary_outcomes": primary_outcomes,
            "url": f"https://clinicaltrials.gov/study/{id_module.get('nctId', '')}",
        })

    return results


# =============================================================================
# 2. OpenFDA API — Drug Labels and Approvals
# =============================================================================

OPENFDA_BASE = "https://api.fda.gov"

def search_fda_drugs(
    condition: str = "",
    drug_name: str = "",
    max_results: int = 10,
) -> list[dict]:
    """
    Search OpenFDA for approved drug labels by condition or drug name.

    Returns a list of dicts with: brand_name, generic_name, manufacturer,
    indications, route, dosage_form, substance_name, warnings.
    """
    # Build the search query
    # OpenFDA is picky about exact phrases — use broader matching for conditions
    search_parts = []
    if condition:
        # Use unquoted terms for broader matching (quoted exact phrases often 404)
        # Also simplify complex terms: "KRAS-mutant cancer" → "KRAS"
        clean_cond = condition.replace("-mutant", "").replace("-positive", "").replace("-negative", "")
        search_parts.append(f'indications_and_usage:({clean_cond})')
    if drug_name:
        # Try both brand_name and generic_name for better recall
        search_parts.append(f'(openfda.brand_name:"{drug_name}"+OR+openfda.generic_name:"{drug_name}")')

    if not search_parts:
        return []

    search_query = "+AND+".join(search_parts)
    url = f"{OPENFDA_BASE}/drug/label.json?search={search_query}&limit={max_results}"

    try:
        resp = requests.get(url, headers={"User-Agent": "SatyaBio/1.0"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.SSLError:
        try:
            resp = requests.get(url, headers={"User-Agent": "SatyaBio/1.0"}, timeout=15, verify=False)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  OpenFDA API error (SSL fallback): {e}")
            return []
    except Exception as e:
        print(f"  OpenFDA API error: {e}")
        return []

    results = []
    for item in data.get("results", []):
        openfda = item.get("openfda", {})

        results.append({
            "source": "FDA",
            "brand_name": (openfda.get("brand_name", [""])[0] if openfda.get("brand_name") else ""),
            "generic_name": (openfda.get("generic_name", [""])[0] if openfda.get("generic_name") else ""),
            "manufacturer": (openfda.get("manufacturer_name", [""])[0] if openfda.get("manufacturer_name") else ""),
            "indications": (item.get("indications_and_usage", [""])[0][:500] if item.get("indications_and_usage") else ""),
            "route": openfda.get("route", []),
            "dosage_form": (openfda.get("dosage_form", [""])[0] if openfda.get("dosage_form") else ""),
            "substance_name": openfda.get("substance_name", []),
            "warnings": (item.get("boxed_warning", [""])[0][:300] if item.get("boxed_warning") else ""),
        })

    return results


# =============================================================================
# 3. PubMed (NCBI E-utilities)
# =============================================================================

PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

def search_pubmed(
    query: str,
    max_results: int = 10,
    sort: str = "relevance",  # relevance, pub_date
) -> list[dict]:
    """
    Search PubMed for publications.

    Returns a list of dicts with: pmid, title, authors, journal, pub_date,
    doi, url.
    """
    # NCBI rate limit: 3 requests/sec without API key, 10/sec with key
    # Add a small delay to avoid 429 errors when multiple searches run in parallel
    api_key = os.environ.get("NCBI_API_KEY", "")
    base_params = {}
    if api_key:
        base_params["api_key"] = api_key

    # Step 1: Search for PMIDs
    search_params = {
        **base_params,
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": sort,
        "retmode": "json",
    }

    try:
        resp = requests.get(PUBMED_SEARCH, params=search_params, headers={"User-Agent": "SatyaBio/1.0"}, timeout=15)
        if resp.status_code == 429:
            # Rate limited — wait and retry once
            time.sleep(1.5)
            resp = requests.get(PUBMED_SEARCH, params=search_params, headers={"User-Agent": "SatyaBio/1.0"}, timeout=15)
        resp.raise_for_status()
        search_data = resp.json()
    except requests.exceptions.SSLError:
        try:
            resp = requests.get(PUBMED_SEARCH, params=search_params, headers={"User-Agent": "SatyaBio/1.0"}, timeout=15, verify=False)
            resp.raise_for_status()
            search_data = resp.json()
        except Exception as e:
            print(f"  PubMed search error (SSL fallback): {e}")
            return []
    except Exception as e:
        print(f"  PubMed search error: {e}")
        return []

    pmids = search_data.get("esearchresult", {}).get("idlist", [])
    if not pmids:
        return []

    # Step 2: Fetch summaries for those PMIDs
    time.sleep(0.5)  # NCBI rate limit: 3 requests/second without API key
    summary_params = {
        **base_params,
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }

    try:
        resp = requests.get(PUBMED_SUMMARY, params=summary_params, headers={"User-Agent": "SatyaBio/1.0"}, timeout=15)
        if resp.status_code == 429:
            time.sleep(1.5)
            resp = requests.get(PUBMED_SUMMARY, params=summary_params, headers={"User-Agent": "SatyaBio/1.0"}, timeout=15)
        resp.raise_for_status()
        summary_data = resp.json()
    except requests.exceptions.SSLError:
        try:
            resp = requests.get(PUBMED_SUMMARY, params=summary_params, headers={"User-Agent": "SatyaBio/1.0"}, timeout=15, verify=False)
            resp.raise_for_status()
            summary_data = resp.json()
        except Exception as e:
            print(f"  PubMed summary error (SSL fallback): {e}")
            return []
    except Exception as e:
        print(f"  PubMed summary error: {e}")
        return []

    results = []
    summaries = summary_data.get("result", {})

    for pmid in pmids:
        article = summaries.get(pmid, {})
        if not article or pmid == "uids":
            continue

        # Extract authors
        authors = []
        for author in article.get("authors", []):
            authors.append(author.get("name", ""))

        # Extract DOI from articleids
        doi = ""
        for aid in article.get("articleids", []):
            if aid.get("idtype") == "doi":
                doi = aid.get("value", "")
                break

        results.append({
            "source": "PubMed",
            "pmid": pmid,
            "title": article.get("title", ""),
            "authors": authors[:5],  # First 5 authors
            "journal": article.get("fulljournalname", article.get("source", "")),
            "pub_date": article.get("pubdate", ""),
            "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })

    return results


# =============================================================================
# Utility: Format API results for Claude context
# =============================================================================

def format_api_results_for_claude(
    trials: list[dict] = None,
    fda_drugs: list[dict] = None,
    papers: list[dict] = None,
) -> str:
    """
    Format API results into a context block for Claude's system prompt.
    This gets appended alongside the RAG context.
    """
    parts = []

    if trials:
        parts.append("=== LIVE DATA: ClinicalTrials.gov ===")
        parts.append(f"Total trials returned: {len(trials)}")
        parts.append("IMPORTANT: Present EVERY trial individually in a markdown table. Do NOT summarize as 'X trials'.\n")
        for t in trials:
            interventions_str = ", ".join(f"{i['name']} ({i['type']})" for i in t.get("interventions", []))
            parts.append(f"  [{t['nct_id']}] {t['title']}")
            parts.append(f"    Status: {t['status']} | Phase: {t['phase']} | Sponsor: {t['sponsor']}")
            parts.append(f"    Conditions: {', '.join(t.get('conditions', []))}")
            parts.append(f"    Interventions: {interventions_str}")
            parts.append(f"    Enrollment: {t.get('enrollment', 'N/A')} | Start: {t.get('start_date', 'N/A')}")
            if t.get("primary_outcomes"):
                parts.append(f"    Primary endpoints: {'; '.join(t['primary_outcomes'][:3])}")
            if t.get("summary"):
                # Truncate long summaries but include enough for context
                summary = t["summary"][:300].strip()
                parts.append(f"    Summary: {summary}")
            parts.append(f"    URL: {t['url']}")
            parts.append("")
        parts.append("")

    if fda_drugs:
        parts.append("=== LIVE DATA: FDA Approved Drugs ===")
        for d in fda_drugs:
            parts.append(f"  {d['brand_name']} ({d['generic_name']})")
            parts.append(f"    Manufacturer: {d['manufacturer']}")
            parts.append(f"    Indications: {d['indications'][:200]}...")
            if d.get("warnings"):
                parts.append(f"    Boxed Warning: {d['warnings'][:150]}...")
            parts.append("")
        parts.append("")

    if papers:
        parts.append("=== LIVE DATA: PubMed Publications ===")
        for p in papers:
            authors_str = ", ".join(p.get("authors", [])[:3])
            if len(p.get("authors", [])) > 3:
                authors_str += " et al."
            parts.append(f"  [{p['pmid']}] {p['title']}")
            parts.append(f"    {authors_str} — {p['journal']} ({p['pub_date']})")
            parts.append(f"    URL: {p['url']}")
            parts.append("")
        parts.append("")

    if not parts:
        return ""

    header = "--- LIVE API DATA (fetched in real-time) ---\n"
    header += "The following data was retrieved from external APIs and is current as of today.\n"
    header += "Cite the source (ClinicalTrials.gov, FDA, PubMed) when referencing this data.\n\n"
    return header + "\n".join(parts) + "\n--- END LIVE DATA ---"


# =============================================================================
# Quick test
# =============================================================================

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print("Testing ClinicalTrials.gov API...")
    trials = search_clinical_trials(condition="ulcerative colitis", status="RECRUITING", max_results=3)
    if trials:
        for t in trials:
            print(f"  {t['nct_id']}: {t['title']} ({t['status']}, {t['phase']})")
    else:
        print("  No results (check internet connection)")

    print("\nTesting OpenFDA API...")
    drugs = search_fda_drugs(condition="narcolepsy", max_results=3)
    if drugs:
        for d in drugs:
            print(f"  {d['brand_name']} ({d['generic_name']}) — {d['manufacturer']}")
    else:
        print("  No results (check internet connection)")

    print("\nTesting PubMed API...")
    papers = search_pubmed("KRAS G12C inhibitor clinical trial 2025", max_results=3)
    if papers:
        for p in papers:
            print(f"  [{p['pmid']}] {p['title']} — {p['journal']}")
    else:
        print("  No results (check internet connection)")
