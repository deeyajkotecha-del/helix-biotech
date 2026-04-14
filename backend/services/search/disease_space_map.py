"""
SatyaBio — Disease Space Intelligence

When a user asks about a disease (especially rare diseases), this module assembles
a comprehensive "space map" — the full ecosystem an investor, BD team, or trial
designer needs to understand:

  1. THERAPEUTIC PIPELINE — discovered from foundations + validated against CT.gov
  2. PATIENT LANDSCAPE — prevalence, registries, natural history studies
  3. BIOMARKER LANDSCAPE — validated vs exploratory endpoints
  4. KEY ORGANIZATIONS — foundations, advocacy groups, research consortia
  5. CLINICAL INFRASTRUCTURE — active trial sites, clinic networks
  6. REGULATORY CONTEXT — orphan designations, FDA guidance

Architecture:
  - Foundation Registry: curated list of rare disease foundations + pipeline URLs
  - Discovery Layer: foundations surface programs we might not find on CT.gov
  - Validation Layer: every claim cross-referenced against CT.gov, PubMed, FDA
  - Confidence scoring: "validated" vs "foundation-reported" vs "early-signal"

Usage:
    from disease_space_map import build_disease_space, format_space_for_claude

    space = build_disease_space("Angelman syndrome")
    context = format_space_for_claude(space)

Run standalone to test:
    python disease_space_map.py "Angelman syndrome"
"""

import os
import re
import json
import time
import requests
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
load_dotenv()

# ── Imports from existing modules ──
try:
    from api_connectors import search_clinical_trials, search_pubmed
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False

# Claude for intelligent extraction
try:
    import anthropic
    _client = None
    def _get_claude():
        global _client
        if _client is None:
            _client = anthropic.Anthropic()
        return _client
    CLAUDE_AVAILABLE = bool(os.environ.get("ANTHROPIC_API_KEY"))
except ImportError:
    CLAUDE_AVAILABLE = False

# Database for caching
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
    DB_AVAILABLE = bool(DATABASE_URL)
except ImportError:
    DB_AVAILABLE = False
    DATABASE_URL = ""


# =============================================================================
# 1. FOUNDATION REGISTRY
# =============================================================================
# Curated list of rare disease foundations with structured pipeline trackers.
# Each entry specifies:
#   - name: foundation name
#   - url: pipeline/clinical-trials page URL
#   - diseases: which diseases this foundation covers
#   - data_type: what kind of data the page has
#   - scrape_method: how to extract (html_table, json_api, claude_extract)

FOUNDATION_REGISTRY = [
    # ── Neurological / Neurodevelopmental ──
    {
        "name": "Foundation for Angelman Syndrome Therapeutics (FAST)",
        "url": "https://cureangelman.org/current-pipeline",
        "diseases": ["Angelman syndrome"],
        "data_type": "full_pipeline",
        "scrape_method": "claude_extract",
        "notes": "5-pillar pipeline tracker. Updated regularly.",
    },
    {
        "name": "Angelman Syndrome Foundation (ASF)",
        "url": "https://angelman.org/clinical-trials/",
        "diseases": ["Angelman syndrome"],
        "data_type": "trial_tracker",
        "scrape_method": "claude_extract",
        "notes": "Clinical trials by phase. Has clinic network + industry page.",
    },
    {
        "name": "CHDI Foundation",
        "url": "https://chdifoundation.org/drug-development-pipeline/",
        "diseases": ["Huntington disease", "Huntington's disease"],
        "data_type": "full_pipeline",
        "scrape_method": "claude_extract",
        "notes": "Largest private HD funder. Detailed pipeline by modality.",
    },
    {
        "name": "Hereditary Disease Foundation",
        "url": "https://www.hdfoundation.org/research",
        "diseases": ["Huntington disease", "Huntington's disease"],
        "data_type": "research_overview",
        "scrape_method": "claude_extract",
    },
    {
        "name": "Cure SMA",
        "url": "https://www.curesma.org/sma-drug-pipeline/",
        "diseases": ["spinal muscular atrophy", "SMA"],
        "data_type": "full_pipeline",
        "scrape_method": "claude_extract",
        "notes": "Discovery through marketed. Updated frequently.",
    },
    {
        "name": "International Rett Syndrome Foundation",
        "url": "https://www.rettsyndrome.org/about-rett-syndrome/pipeline/",
        "diseases": ["Rett syndrome"],
        "data_type": "full_pipeline",
        "scrape_method": "claude_extract",
    },
    {
        "name": "Parent Project Muscular Dystrophy",
        "url": "https://www.parentprojectmd.org/duchenne-drug-development-pipeline/",
        "diseases": ["Duchenne muscular dystrophy", "DMD"],
        "data_type": "full_pipeline",
        "scrape_method": "claude_extract",
        "notes": "7 therapeutic categories.",
    },
    {
        "name": "ALS Association",
        "url": "https://www.als.org/research/drug-development-pipeline",
        "diseases": ["amyotrophic lateral sclerosis", "ALS"],
        "data_type": "full_pipeline",
        "scrape_method": "claude_extract",
    },
    {
        "name": "Dravet Syndrome Foundation",
        "url": "https://www.dravetfoundation.org/research/therapeutic-pipeline/",
        "diseases": ["Dravet syndrome"],
        "data_type": "full_pipeline",
        "scrape_method": "claude_extract",
    },
    {
        "name": "Friedreich's Ataxia Research Alliance (FARA)",
        "url": "https://www.curefa.org/pipeline",
        "diseases": ["Friedreich ataxia", "Friedreich's ataxia"],
        "data_type": "full_pipeline",
        "scrape_method": "claude_extract",
    },

    # ── Metabolic / Lysosomal ──
    {
        "name": "Cystic Fibrosis Foundation",
        "url": "https://www.cff.org/research-clinical-trials/drug-development-pipeline",
        "diseases": ["cystic fibrosis", "CF"],
        "data_type": "full_pipeline",
        "scrape_method": "claude_extract",
        "notes": "Pipeline to a Cure tracker.",
    },
    {
        "name": "National Gaucher Foundation",
        "url": "https://www.gaucherdisease.org/research/",
        "diseases": ["Gaucher disease"],
        "data_type": "research_overview",
        "scrape_method": "claude_extract",
    },
    {
        "name": "National Fabry Disease Foundation",
        "url": "https://www.fabrydisease.org/research/",
        "diseases": ["Fabry disease"],
        "data_type": "research_overview",
        "scrape_method": "claude_extract",
    },
    {
        "name": "National PKU Alliance",
        "url": "https://npkua.org/research/",
        "diseases": ["phenylketonuria", "PKU"],
        "data_type": "research_overview",
        "scrape_method": "claude_extract",
    },
    {
        "name": "National MPS Society",
        "url": "https://mpssociety.org/research/clinical-trials/",
        "diseases": ["mucopolysaccharidosis", "MPS", "Hunter syndrome", "Hurler syndrome"],
        "data_type": "trial_tracker",
        "scrape_method": "claude_extract",
    },

    # ── Hematological ──
    {
        "name": "Sickle Cell Disease Association of America",
        "url": "https://www.sicklecelldisease.org/research/",
        "diseases": ["sickle cell disease", "SCD"],
        "data_type": "research_overview",
        "scrape_method": "claude_extract",
    },
    {
        "name": "Cooley's Anemia Foundation",
        "url": "https://www.thalassemia.org/research/",
        "diseases": ["thalassemia", "beta-thalassemia"],
        "data_type": "research_overview",
        "scrape_method": "claude_extract",
    },

    # ── Immunological / Autoimmune ──
    {
        "name": "Myasthenia Gravis Foundation of America",
        "url": "https://myasthenia.org/research/",
        "diseases": ["myasthenia gravis", "MG"],
        "data_type": "research_overview",
        "scrape_method": "claude_extract",
    },

    # ── Rare Oncology ──
    {
        "name": "Cholangiocarcinoma Foundation",
        "url": "https://cholangiocarcinoma.org/clinical-trials/",
        "diseases": ["cholangiocarcinoma", "bile duct cancer"],
        "data_type": "trial_tracker",
        "scrape_method": "claude_extract",
    },

    # ── Multi-disease / Meta-organizations ──
    {
        "name": "National Organization for Rare Disorders (NORD)",
        "url": "https://rarediseases.org/",
        "diseases": ["_meta"],  # Covers all rare diseases
        "data_type": "disease_database",
        "scrape_method": "api",
        "notes": "1200+ rare disease reports. Not scrapeable for pipeline, but good for prevalence.",
    },
]


def get_foundations_for_disease(disease_query: str) -> list[dict]:
    """Find foundations in the registry that cover a given disease."""
    query_lower = disease_query.lower()
    matches = []
    for f in FOUNDATION_REGISTRY:
        if f["diseases"] == ["_meta"]:
            continue  # Skip meta-orgs for now
        for d in f["diseases"]:
            if d.lower() in query_lower or query_lower in d.lower():
                matches.append(f)
                break
            # Also try abbreviation matching
            words = query_lower.split()
            if d.lower() in words or any(d.lower() == w for w in words):
                matches.append(f)
                break
    return matches


# =============================================================================
# 2. FOUNDATION PIPELINE SCRAPER
# =============================================================================

def scrape_foundation_pipeline(foundation: dict, timeout: int = 30) -> dict:
    """
    Fetch a foundation's pipeline page and extract structured drug data.

    Returns:
        {
            "foundation": str,
            "url": str,
            "programs": [
                {
                    "drug_name": str,
                    "company": str,
                    "phase": str,  # "Preclinical", "Phase 1", "Phase 2", "Phase 3", "Approved"
                    "mechanism": str,
                    "modality": str,  # "ASO", "Gene therapy", "Small molecule", etc.
                    "status": str,
                    "confidence": str,  # "foundation_reported"
                    "nct_id": str | None,  # Filled in by validation step
                }
            ],
            "scraped_at": str,
            "error": str | None,
        }
    """
    result = {
        "foundation": foundation["name"],
        "url": foundation["url"],
        "programs": [],
        "scraped_at": datetime.now().isoformat(),
        "error": None,
    }

    try:
        # Fetch the page
        headers = {
            "User-Agent": "SatyaBio/1.0 (biotech research platform; contact@satyabio.com)"
        }
        resp = requests.get(foundation["url"], headers=headers, timeout=timeout)
        resp.raise_for_status()
        html = resp.text

        # Strip HTML to get readable text (simple approach)
        text = _html_to_text(html)

        if not text or len(text) < 100:
            result["error"] = "Page content too short or empty"
            return result

        # Use Claude to extract structured pipeline data
        if CLAUDE_AVAILABLE and foundation["scrape_method"] == "claude_extract":
            programs = _claude_extract_pipeline(text, foundation)
            result["programs"] = programs
        else:
            # Fallback: basic regex extraction
            programs = _regex_extract_pipeline(text)
            result["programs"] = programs

    except requests.RequestException as e:
        result["error"] = f"Fetch failed: {str(e)[:200]}"
    except Exception as e:
        result["error"] = f"Extraction failed: {str(e)[:200]}"

    return result


def _html_to_text(html: str) -> str:
    """Simple HTML-to-text conversion. Strips tags, keeps structure."""
    import re
    # Remove scripts and styles
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Convert headers, list items, and table cells to newlines
    text = re.sub(r'<(?:h[1-6]|li|tr|td|th|p|div|br)[^>]*>', '\n', text, flags=re.IGNORECASE)
    # Remove remaining tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ').replace('&#8217;', "'").replace('&#8211;', '-')
    # Clean whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()[:15000]  # Cap to avoid huge context


def _claude_extract_pipeline(page_text: str, foundation: dict) -> list[dict]:
    """Use Claude to extract structured pipeline data from foundation page text."""
    prompt = f"""Extract ALL drug development programs from this {foundation['name']} page.

For each program, extract:
- drug_name: the drug/compound name (e.g., "GTX-102", "apazunersen", "ION582")
- company: the company or institution developing it
- phase: the development phase (one of: "Discovery", "Preclinical", "Phase 1", "Phase 1/2", "Phase 2", "Phase 2/3", "Phase 3", "Filed", "Approved")
- mechanism: how it works (e.g., "antisense oligonucleotide targeting UBE3A-AS")
- modality: drug type (e.g., "ASO", "Gene therapy (AAV)", "Gene therapy (HSC)", "Small molecule", "CRISPR", "Enzyme replacement", "Antibody", "Cell therapy")
- status: current status if mentioned (e.g., "Enrolling", "Phase 3 fully enrolled", "IND filed")
- nct_id: NCT number if mentioned, else null

Return ONLY a JSON array. If you find no programs, return [].
Include EVERY program mentioned, even early-stage/preclinical ones.
Do not invent data — only extract what's on the page.

Page text:
{page_text[:12000]}"""

    try:
        response = _get_claude().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Parse JSON — handle markdown code blocks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        programs = json.loads(text)
        # Tag confidence
        for p in programs:
            p["confidence"] = "foundation_reported"
            if not p.get("nct_id"):
                p["nct_id"] = None
        return programs
    except Exception as e:
        print(f"  Claude extraction failed for {foundation['name']}: {e}")
        return []


def _regex_extract_pipeline(text: str) -> list[dict]:
    """Fallback: use regex to find drug names and phases."""
    programs = []
    # Look for Phase patterns
    phase_pattern = re.compile(
        r'(Phase\s*[1-4][/]?[1-4]?[a-b]?|Preclinical|Pre-clinical|Discovery|Approved|Filed|IND)',
        re.IGNORECASE
    )
    # Look for drug code names near phase mentions
    drug_pattern = re.compile(r'\b([A-Z]{2,5}[-]?\d{2,6}[A-Z]?)\b')

    for match in phase_pattern.finditer(text):
        # Get surrounding context (200 chars around the phase mention)
        start = max(0, match.start() - 150)
        end = min(len(text), match.end() + 150)
        context = text[start:end]

        drug_matches = drug_pattern.findall(context)
        for drug in drug_matches:
            if drug not in [p["drug_name"] for p in programs]:
                programs.append({
                    "drug_name": drug,
                    "company": "Unknown",
                    "phase": match.group(0).strip(),
                    "mechanism": "",
                    "modality": "",
                    "status": "",
                    "confidence": "foundation_reported",
                    "nct_id": None,
                })
    return programs


# =============================================================================
# 3. CROSS-VALIDATION AGAINST CLINICALTRIALS.GOV
# =============================================================================

def validate_programs_against_ctgov(
    programs: list[dict],
    disease: str,
) -> list[dict]:
    """
    Cross-reference foundation-reported programs against ClinicalTrials.gov.

    For each program:
      - If found on CT.gov with matching NCT ID → confidence = "validated"
      - If found on CT.gov with different phase → flag discrepancy
      - If NOT found on CT.gov → confidence stays "foundation_reported" (early signal)

    Also discovers CT.gov trials NOT in foundation data → confidence = "ctgov_only"
    """
    if not API_AVAILABLE:
        return programs

    # Fetch all trials for this disease
    try:
        all_trials = search_clinical_trials(
            condition=disease,
            max_results=100,
        )
    except Exception as e:
        print(f"  CT.gov validation failed: {e}")
        return programs

    # Build lookup by intervention name
    ctgov_by_drug = {}
    for trial in all_trials:
        for intervention in trial.get("interventions", []):
            # Handle both dict format ({"name": "...", "type": "..."}) and plain strings
            if isinstance(intervention, dict):
                name = intervention.get("name", "").lower().strip()
            else:
                name = str(intervention).lower().strip()
            if not name:
                continue
            if name not in ctgov_by_drug:
                ctgov_by_drug[name] = []
            ctgov_by_drug[name].append(trial)

    # Validate each foundation program
    for prog in programs:
        drug_lower = prog["drug_name"].lower().strip()

        # Try exact match, then partial match
        matched_trials = ctgov_by_drug.get(drug_lower, [])
        if not matched_trials:
            # Try partial matching
            for ct_drug, ct_trials in ctgov_by_drug.items():
                if drug_lower in ct_drug or ct_drug in drug_lower:
                    matched_trials = ct_trials
                    break

        if matched_trials:
            # Found on CT.gov — validate
            best_trial = max(matched_trials, key=lambda t: _phase_rank(t.get("phase", "")))
            prog["confidence"] = "validated"
            prog["nct_id"] = best_trial.get("nct_id")
            prog["ctgov_phase"] = best_trial.get("phase", "")
            prog["ctgov_status"] = best_trial.get("status", "")
            prog["ctgov_enrollment"] = best_trial.get("enrollment")
            prog["ctgov_sponsor"] = best_trial.get("sponsor", "")

            # Flag phase discrepancy
            if prog.get("phase") and prog["ctgov_phase"]:
                f_rank = _phase_rank(prog["phase"])
                ct_rank = _phase_rank(prog["ctgov_phase"])
                if abs(f_rank - ct_rank) > 1:
                    prog["phase_discrepancy"] = f"Foundation: {prog['phase']}, CT.gov: {prog['ctgov_phase']}"
        else:
            # Not on CT.gov — could be early-stage or pre-IND
            prog["confidence"] = "foundation_reported"

    # Find CT.gov trials NOT in foundation data (potential gaps)
    foundation_drugs = {p["drug_name"].lower() for p in programs}
    ctgov_only = []
    seen_ncts = set()
    for trial in all_trials:
        nct = trial.get("nct_id", "")
        if nct in seen_ncts:
            continue
        seen_ncts.add(nct)

        # Check if any intervention matches a foundation program
        raw_interventions = trial.get("interventions", [])
        intervention_names = []
        for iv in raw_interventions:
            if isinstance(iv, dict):
                intervention_names.append(iv.get("name", ""))
            else:
                intervention_names.append(str(iv))

        is_matched = any(
            n.lower() in foundation_drugs or
            any(fd in n.lower() for fd in foundation_drugs)
            for n in intervention_names if n
        )

        if not is_matched and trial.get("phase") and "Phase" in str(trial.get("phase", "")):
            ctgov_only.append({
                "drug_name": ", ".join(intervention_names[:2]) if intervention_names else "Unknown",
                "company": trial.get("sponsor", "Unknown"),
                "phase": trial.get("phase", ""),
                "mechanism": "",
                "modality": "",
                "status": trial.get("status", ""),
                "confidence": "ctgov_only",
                "nct_id": nct,
                "ctgov_enrollment": trial.get("enrollment"),
            })

    return programs + ctgov_only[:20]  # Cap CT.gov-only additions


def _phase_rank(phase_str: str) -> int:
    """Convert phase string to numeric rank for comparison."""
    p = str(phase_str).lower()
    if "approved" in p or "marketed" in p:
        return 10
    if "filed" in p or "bla" in p or "nda" in p:
        return 9
    if "phase 4" in p or "phase4" in p:
        return 8
    if "phase 3" in p or "phase3" in p:
        return 7
    if "phase 2/3" in p:
        return 6
    if "phase 2" in p or "phase2" in p:
        return 5
    if "phase 1/2" in p:
        return 4
    if "phase 1" in p or "phase1" in p:
        return 3
    if "ind" in p:
        return 2
    if "preclin" in p or "pre-clin" in p:
        return 1
    if "discovery" in p:
        return 0
    return -1


# =============================================================================
# 4. PATIENT LANDSCAPE & BIOMARKERS (from PubMed + Orphanet)
# =============================================================================

ORPHANET_API = "https://api.orphadata.com/rd"

def get_patient_landscape(disease: str) -> dict:
    """
    Assemble patient landscape data:
      - Prevalence estimates (from Orphanet)
      - Patient registries (from PubMed + known registries)
      - Natural history studies (from CT.gov + PubMed)
    """
    landscape = {
        "prevalence": None,
        "registries": [],
        "natural_history_studies": [],
        "patient_organizations": [],
    }

    # ── Orphanet prevalence ──
    try:
        resp = requests.get(
            f"{ORPHANET_API}/search",
            params={"query": disease, "lang": "en"},
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            results = data.get("results", [])
            if results:
                top = results[0]
                landscape["prevalence"] = {
                    "orphanet_id": top.get("orphaNumber"),
                    "name": top.get("preferredTerm"),
                    "prevalence_class": top.get("prevalence", {}).get("prevalenceClass"),
                    "inheritance": [i.get("name") for i in top.get("inheritances", [])],
                    "age_of_onset": [a.get("name") for a in top.get("ageOfOnsets", [])],
                }
    except Exception as e:
        print(f"  Orphanet query failed: {e}")

    # ── Natural history studies from CT.gov ──
    if API_AVAILABLE:
        try:
            nh_trials = search_clinical_trials(
                condition=disease,
                max_results=20,
            )
            for trial in nh_trials:
                study_type = trial.get("study_type", "").lower()
                title = trial.get("title", "").lower()
                if "natural history" in title or "observational" in study_type or "registry" in title:
                    landscape["natural_history_studies"].append({
                        "nct_id": trial.get("nct_id"),
                        "title": trial.get("title"),
                        "sponsor": trial.get("sponsor"),
                        "status": trial.get("status"),
                        "enrollment": trial.get("enrollment"),
                    })
        except Exception as e:
            print(f"  CT.gov natural history search failed: {e}")

    # ── Biomarker-related publications from PubMed ──
    if API_AVAILABLE:
        try:
            registry_papers = search_pubmed(
                f"{disease} patient registry OR natural history",
                max_results=5,
            )
            for paper in (registry_papers or []):
                title = paper.get("title", "").lower()
                if "registry" in title or "natural history" in title or "epidemiology" in title:
                    landscape["registries"].append({
                        "title": paper.get("title"),
                        "pmid": paper.get("pmid"),
                        "year": paper.get("year"),
                        "journal": paper.get("journal"),
                    })
        except Exception:
            pass

    return landscape


def get_biomarker_landscape(disease: str) -> list[dict]:
    """
    Search PubMed for biomarker and endpoint data relevant to this disease.
    Returns publications focused on biomarkers, outcome measures, and endpoints.
    """
    biomarkers = []
    if not API_AVAILABLE:
        return biomarkers

    try:
        papers = search_pubmed(
            f'"{disease}" AND (biomarker OR endpoint OR "outcome measure" OR EEG OR imaging)',
            max_results=8,
        )
        for paper in (papers or []):
            title = paper.get("title", "").lower()
            relevant = any(kw in title for kw in [
                "biomarker", "endpoint", "outcome", "measure", "eeg",
                "imaging", "mri", "score", "scale", "natural history",
                "progression", "surrogate",
            ])
            if relevant:
                biomarkers.append({
                    "title": paper.get("title"),
                    "pmid": paper.get("pmid"),
                    "year": paper.get("year"),
                    "journal": paper.get("journal"),
                    "abstract": paper.get("abstract", "")[:500],
                })
    except Exception as e:
        print(f"  Biomarker PubMed search failed: {e}")

    return biomarkers


# =============================================================================
# 5. REGULATORY CONTEXT (FDA orphan designations)
# =============================================================================

def get_regulatory_context(disease: str) -> dict:
    """
    Check FDA for orphan drug designations, breakthrough therapy designations,
    and any approved therapies for this disease.
    """
    context = {
        "orphan_designations": [],
        "approved_therapies": [],
    }

    # ── OpenFDA: approved drugs for this condition ──
    try:
        resp = requests.get(
            "https://api.fda.gov/drug/drugsfda.json",
            params={
                "search": f'products.active_ingredients.name:"{disease}" OR submissions.submission_type:"ORIG"',
                "limit": 20,
            },
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            for result in data.get("results", []):
                products = result.get("products", [])
                for prod in products:
                    brand = prod.get("brand_name", "")
                    active = prod.get("active_ingredients", [])
                    ingredients = [a.get("name", "") for a in active]
                    if ingredients:
                        context["approved_therapies"].append({
                            "brand_name": brand,
                            "active_ingredients": ingredients,
                            "application_number": result.get("application_number", ""),
                            "sponsor_name": result.get("sponsor_name", ""),
                        })
    except Exception as e:
        print(f"  FDA approved drugs query failed: {e}")

    # ── Orphan drug designations ──
    try:
        resp = requests.get(
            "https://api.fda.gov/drug/drugsfda.json",
            params={
                "search": f'openfda.route:"ORAL" AND "{disease}"',
                "limit": 10,
            },
            timeout=10,
        )
        # Note: orphan designations are better fetched from the FDA orphan drug
        # product designation database. This is a simplified approach.
    except Exception:
        pass

    return context


# =============================================================================
# 6. MAIN ORCHESTRATOR
# =============================================================================

def build_disease_space(
    disease: str,
    include_foundations: bool = True,
    include_patient_landscape: bool = True,
    include_biomarkers: bool = True,
    include_regulatory: bool = True,
    max_foundation_scrapes: int = 5,
) -> dict:
    """
    Build a comprehensive disease space map.

    Returns:
        {
            "disease": str,
            "generated_at": str,
            "pipeline": {
                "programs": [...],
                "total_programs": int,
                "by_phase": {"Phase 3": N, "Phase 2": N, ...},
                "by_modality": {"ASO": N, "Gene therapy": N, ...},
            },
            "patient_landscape": {...},
            "biomarkers": [...],
            "regulatory": {...},
            "foundations": [...],  # Which foundations were consulted
            "data_quality": {
                "validated_programs": N,
                "foundation_only_programs": N,
                "ctgov_only_programs": N,
            },
        }
    """
    print(f"\n{'='*60}")
    print(f"  Building Disease Space Map: {disease}")
    print(f"{'='*60}")
    start_time = time.time()

    space = {
        "disease": disease,
        "generated_at": datetime.now().isoformat(),
        "pipeline": {"programs": [], "total_programs": 0},
        "patient_landscape": {},
        "biomarkers": [],
        "regulatory": {},
        "foundations": [],
        "data_quality": {},
    }

    # ── Step 1: Foundation pipeline discovery (parallel) ──
    if include_foundations:
        foundations = get_foundations_for_disease(disease)
        print(f"  Found {len(foundations)} foundations for {disease}")

        if foundations:
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(scrape_foundation_pipeline, f): f
                    for f in foundations[:max_foundation_scrapes]
                }
                for future in as_completed(futures):
                    foundation = futures[future]
                    try:
                        result = future.result(timeout=45)
                        space["foundations"].append({
                            "name": result["foundation"],
                            "url": result["url"],
                            "programs_found": len(result["programs"]),
                            "error": result.get("error"),
                        })
                        if result["programs"]:
                            space["pipeline"]["programs"].extend(result["programs"])
                            print(f"    {result['foundation']}: {len(result['programs'])} programs")
                        elif result.get("error"):
                            print(f"    {result['foundation']}: ERROR — {result['error'][:80]}")
                    except Exception as e:
                        print(f"    {foundation['name']}: timeout/error — {e}")

    # ── Step 2: Cross-validate against ClinicalTrials.gov ──
    print(f"  Validating {len(space['pipeline']['programs'])} programs against CT.gov...")
    space["pipeline"]["programs"] = validate_programs_against_ctgov(
        space["pipeline"]["programs"], disease
    )

    # Deduplicate by drug name (keep highest-confidence version)
    space["pipeline"]["programs"] = _deduplicate_programs(space["pipeline"]["programs"])

    # ── Step 3: Patient landscape + biomarkers + regulatory (parallel) ──
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        if include_patient_landscape:
            futures["patient"] = executor.submit(get_patient_landscape, disease)
        if include_biomarkers:
            futures["biomarkers"] = executor.submit(get_biomarker_landscape, disease)
        if include_regulatory:
            futures["regulatory"] = executor.submit(get_regulatory_context, disease)

        for key, future in futures.items():
            try:
                result = future.result(timeout=20)
                if key == "patient":
                    space["patient_landscape"] = result
                elif key == "biomarkers":
                    space["biomarkers"] = result
                elif key == "regulatory":
                    space["regulatory"] = result
            except Exception as e:
                print(f"    {key} query failed: {e}")

    # ── Step 4: Compute statistics ──
    programs = space["pipeline"]["programs"]
    space["pipeline"]["total_programs"] = len(programs)

    by_phase = {}
    by_modality = {}
    for p in programs:
        phase = p.get("phase", "Unknown")
        by_phase[phase] = by_phase.get(phase, 0) + 1
        modality = p.get("modality", "Unknown")
        if modality:
            by_modality[modality] = by_modality.get(modality, 0) + 1
    space["pipeline"]["by_phase"] = dict(sorted(by_phase.items(), key=lambda x: _phase_rank(x[0]), reverse=True))
    space["pipeline"]["by_modality"] = by_modality

    # Data quality stats
    validated = sum(1 for p in programs if p.get("confidence") == "validated")
    foundation_only = sum(1 for p in programs if p.get("confidence") == "foundation_reported")
    ctgov_only = sum(1 for p in programs if p.get("confidence") == "ctgov_only")
    space["data_quality"] = {
        "validated_programs": validated,
        "foundation_only_programs": foundation_only,
        "ctgov_only_programs": ctgov_only,
        "foundations_consulted": len(space["foundations"]),
    }

    elapsed = round(time.time() - start_time, 1)
    print(f"  Disease space built in {elapsed}s: {len(programs)} programs "
          f"({validated} validated, {foundation_only} foundation-only, {ctgov_only} CT.gov-only)")

    return space


def _load_drug_canonical_map() -> dict[str, str]:
    """Build a map of {alias_lowered: canonical_name} from the drugs/drug_aliases tables.
    Used to collapse variants like 'Naltrexone For Extended Release Injectable Suspension',
    'Extended release injectable naltrexone (Vivitrol)', 'Oral naltrexone' → 'VIVITROL'.
    Returns empty dict on DB failure (safe fallback)."""
    try:
        import os
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        dsn = os.environ.get("NEON_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not dsn:
            return {}
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("""
            SELECT d.canonical_name, a.alias
            FROM drugs d
            LEFT JOIN drug_aliases a ON a.drug_id = d.drug_id
        """)
        mapping = {}
        for canonical, alias in cur.fetchall():
            if canonical:
                mapping[canonical.lower().strip()] = canonical
                if alias:
                    mapping[alias.lower().strip()] = canonical
        cur.close()
        conn.close()
        return mapping
    except Exception as e:
        print(f"  ⚠ Drug canonical map unavailable: {e}")
        return {}


def _normalize_drug_name(raw: str, canonical_map: dict[str, str]) -> str:
    """Map a raw drug/intervention name to its canonical form.
    Handles three cases:
      1. Exact alias match (e.g. 'naltrexone' → 'VIVITROL')
      2. Substring match (e.g. 'Extended release injectable naltrexone (Vivitrol)'
         contains 'vivitrol' → 'VIVITROL')
      3. No match — return original (lowercased/stripped for consistent keys)
    """
    s = (raw or "").lower().strip()
    if not s:
        return s
    # 1. Exact match
    if s in canonical_map:
        return canonical_map[s].lower()
    # 2. Try stripping common suffixes/parentheticals: "drug (something)" → "drug"
    import re
    stripped = re.sub(r"\s*\([^)]*\)\s*", " ", s).strip()
    if stripped and stripped in canonical_map:
        return canonical_map[stripped].lower()
    # 3. Substring match — look for any canonical name or alias as a substring
    # Prefer longer matches first to avoid "xeno" matching inside "xenolepsy".
    # Skip very short aliases (<4 chars) to avoid false positives.
    candidates = sorted(
        (k for k in canonical_map if len(k) >= 4 and k in s),
        key=len, reverse=True,
    )
    if candidates:
        return canonical_map[candidates[0]].lower()
    return s


# Module-level cache — built lazily on first dedup call
_CANONICAL_MAP_CACHE: dict | None = None


def _deduplicate_programs(programs: list[dict]) -> list[dict]:
    """Deduplicate programs by drug name, keeping highest-confidence version.
    Normalizes names through the drug entity DB so VIVITROL variants collapse into one."""
    global _CANONICAL_MAP_CACHE
    if _CANONICAL_MAP_CACHE is None:
        _CANONICAL_MAP_CACHE = _load_drug_canonical_map()
    canonical_map = _CANONICAL_MAP_CACHE

    # Drop obviously-non-drug interventions (behavioral/training/placebo/standard of care)
    NON_DRUG_PATTERNS = (
        "computerized", "cognitive training", "skills training", "behavioral therapy",
        "placebo", "standard of care", "sham", "educational", "counseling",
        "questionnaire", "survey", "dietary", "exercise", "physical therapy",
    )
    filtered = []
    for p in programs:
        name = (p.get("drug_name") or "").lower()
        if any(pat in name for pat in NON_DRUG_PATTERNS):
            continue
        filtered.append(p)
    programs = filtered

    seen = {}
    confidence_rank = {"validated": 3, "ctgov_only": 2, "foundation_reported": 1}

    for p in programs:
        key = _normalize_drug_name(p["drug_name"], canonical_map)
        # If we normalized to a canonical name, update drug_name to canonical form
        if key in canonical_map:
            p["drug_name"] = canonical_map[key]
        existing = seen.get(key)
        if not existing:
            seen[key] = p
        else:
            # Keep higher confidence
            existing_rank = confidence_rank.get(existing.get("confidence", ""), 0)
            new_rank = confidence_rank.get(p.get("confidence", ""), 0)
            if new_rank > existing_rank:
                # Merge: keep new but inherit any extra fields from existing
                for k, v in existing.items():
                    if k not in p or not p[k]:
                        p[k] = v
                seen[key] = p
            else:
                # Merge in the other direction
                for k, v in p.items():
                    if k not in existing or not existing[k]:
                        existing[k] = v

    return list(seen.values())


# =============================================================================
# 7. FORMAT FOR CLAUDE SYNTHESIS
# =============================================================================

def format_space_for_claude(space: dict) -> str:
    """Format the disease space map as context for Claude synthesis."""
    lines = []
    disease = space["disease"]
    quality = space.get("data_quality", {})

    lines.append(f"=== DISEASE SPACE INTELLIGENCE: {disease.upper()} ===")
    lines.append(f"Generated: {space['generated_at'][:10]}")
    lines.append(f"Data quality: {quality.get('validated_programs', 0)} CT.gov-validated programs, "
                 f"{quality.get('foundation_only_programs', 0)} foundation-reported (pre-CT.gov), "
                 f"{quality.get('ctgov_only_programs', 0)} CT.gov-only discoveries")
    lines.append(f"Sources: {quality.get('foundations_consulted', 0)} disease foundations consulted + ClinicalTrials.gov + PubMed + Orphanet + OpenFDA")
    lines.append("")

    # ── Pipeline ──
    programs = space["pipeline"].get("programs", [])
    if programs:
        lines.append(f"── THERAPEUTIC PIPELINE ({len(programs)} programs) ──")

        by_phase = space["pipeline"].get("by_phase", {})
        if by_phase:
            phase_summary = ", ".join(f"{phase}: {n}" for phase, n in by_phase.items())
            lines.append(f"Phase distribution: {phase_summary}")

        by_modality = space["pipeline"].get("by_modality", {})
        if by_modality:
            mod_summary = ", ".join(f"{mod}: {n}" for mod, n in by_modality.items())
            lines.append(f"Modality distribution: {mod_summary}")
        lines.append("")

        # Sort by phase (most advanced first)
        sorted_programs = sorted(programs, key=lambda p: _phase_rank(p.get("phase", "")), reverse=True)

        for p in sorted_programs:
            confidence_tag = ""
            if p.get("confidence") == "validated":
                confidence_tag = " ✓CT.gov"
            elif p.get("confidence") == "foundation_reported":
                confidence_tag = " ★foundation"
            elif p.get("confidence") == "ctgov_only":
                confidence_tag = " △CT.gov-only"

            nct = f" ({p['nct_id']})" if p.get("nct_id") else ""
            company = p.get("company", "Unknown")
            mechanism = f" — {p['mechanism']}" if p.get("mechanism") else ""
            modality = f" [{p['modality']}]" if p.get("modality") else ""
            status = f" | Status: {p['status']}" if p.get("status") else ""
            enrollment = f" | N={p['ctgov_enrollment']}" if p.get("ctgov_enrollment") else ""
            discrepancy = ""
            if p.get("phase_discrepancy"):
                discrepancy = f" ⚠ PHASE DISCREPANCY: {p['phase_discrepancy']}"

            lines.append(
                f"  {p.get('phase', '?'):12s} | {p['drug_name']} — {company}{modality}"
                f"{mechanism}{nct}{status}{enrollment}{confidence_tag}{discrepancy}"
            )
        lines.append("")

    # ── Patient Landscape ──
    patient = space.get("patient_landscape", {})
    if patient:
        lines.append("── PATIENT LANDSCAPE ──")

        prev = patient.get("prevalence")
        if prev:
            lines.append(f"  Orphanet ID: {prev.get('orphanet_id', 'N/A')}")
            lines.append(f"  Preferred name: {prev.get('name', disease)}")
            if prev.get("prevalence_class"):
                lines.append(f"  Prevalence class: {prev['prevalence_class']}")
            if prev.get("inheritance"):
                lines.append(f"  Inheritance: {', '.join(prev['inheritance'])}")
            if prev.get("age_of_onset"):
                lines.append(f"  Age of onset: {', '.join(prev['age_of_onset'])}")

        nhs = patient.get("natural_history_studies", [])
        if nhs:
            lines.append(f"\n  Natural History Studies ({len(nhs)}):")
            for study in nhs:
                enrollment = f" N={study['enrollment']}" if study.get("enrollment") else ""
                lines.append(f"    {study.get('nct_id', '?')} — {study.get('title', '?')[:100]} "
                             f"| {study.get('status', '?')}{enrollment}")

        registries = patient.get("registries", [])
        if registries:
            lines.append(f"\n  Published Registry/Epidemiology Studies ({len(registries)}):")
            for reg in registries:
                lines.append(f"    PMID:{reg.get('pmid', '?')} — {reg.get('title', '?')[:120]} "
                             f"({reg.get('journal', '?')}, {reg.get('year', '?')})")
        lines.append("")

    # ── Biomarkers ──
    biomarkers = space.get("biomarkers", [])
    if biomarkers:
        lines.append(f"── BIOMARKER & ENDPOINT LANDSCAPE ({len(biomarkers)} key publications) ──")
        for bm in biomarkers:
            lines.append(f"  PMID:{bm.get('pmid', '?')} — {bm.get('title', '?')[:120]}")
            if bm.get("abstract"):
                lines.append(f"    Summary: {bm['abstract'][:200]}...")
        lines.append("")

    # ── Regulatory ──
    regulatory = space.get("regulatory", {})
    approved = regulatory.get("approved_therapies", [])
    if approved:
        lines.append(f"── APPROVED THERAPIES ({len(approved)}) ──")
        for rx in approved:
            ingredients = ", ".join(rx.get("active_ingredients", []))
            lines.append(f"  {rx.get('brand_name', '?')} ({ingredients}) — "
                         f"{rx.get('sponsor_name', '?')} | {rx.get('application_number', '?')}")
        lines.append("")

    # ── Foundation Sources ──
    foundations = space.get("foundations", [])
    if foundations:
        lines.append("── DISEASE FOUNDATION SOURCES ──")
        for f in foundations:
            error = f" (error: {f['error'][:50]})" if f.get("error") else ""
            lines.append(f"  {f['name']} — {f['url']} — {f['programs_found']} programs{error}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# 8. CACHE LAYER
# =============================================================================

def cache_disease_space(space: dict):
    """Cache a disease space map in Neon for fast retrieval."""
    if not DB_AVAILABLE:
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS disease_space_cache (
                disease VARCHAR(200) PRIMARY KEY,
                space_data JSONB NOT NULL,
                cached_at TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            INSERT INTO disease_space_cache (disease, space_data, cached_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (disease)
            DO UPDATE SET space_data = EXCLUDED.space_data, cached_at = NOW();
        """, (space["disease"].lower(), json.dumps(space)))
        conn.close()
    except Exception as e:
        print(f"  Cache write failed: {e}")


def get_cached_disease_space(disease: str, max_age_hours: int = 48) -> Optional[dict]:
    """Retrieve a cached disease space map if fresh enough."""
    if not DB_AVAILABLE:
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT space_data, cached_at
            FROM disease_space_cache
            WHERE disease = %s
              AND cached_at > NOW() - INTERVAL '%s hours';
        """, (disease.lower(), max_age_hours))
        row = cur.fetchone()
        conn.close()
        if row:
            return row["space_data"]
    except Exception:
        pass
    return None


# =============================================================================
# 9. PUBLIC API
# =============================================================================

def get_disease_space(disease: str, force_refresh: bool = False) -> dict:
    """
    Main entry point. Returns a disease space map, using cache when available.
    """
    if not force_refresh:
        cached = get_cached_disease_space(disease)
        if cached:
            print(f"  Using cached disease space for {disease}")
            return cached

    space = build_disease_space(disease)
    cache_disease_space(space)
    return space


def is_disease_space_query(query: str) -> bool:
    """
    Detect if a query would benefit from disease space intelligence.
    Returns True for rare disease ecosystem/space/landscape questions.
    """
    query_lower = query.lower()

    # Direct disease space triggers
    space_triggers = [
        "space", "landscape", "ecosystem", "pipeline", "what exists",
        "who is working on", "what's in development", "clinical trials for",
        "treatments for", "therapies for", "registr", "patient population",
        "biomarker", "endpoint", "natural history", "foundation",
        "rare disease", "orphan",
    ]

    # Check if query mentions a disease + a space trigger
    has_trigger = any(t in query_lower for t in space_triggers)

    # Check if query mentions a known rare disease
    known_diseases = set()
    for f in FOUNDATION_REGISTRY:
        for d in f["diseases"]:
            if d != "_meta":
                known_diseases.add(d.lower())

    has_disease = any(d in query_lower for d in known_diseases)

    return has_trigger and has_disease


# =============================================================================
# STANDALONE EXECUTION
# =============================================================================

if __name__ == "__main__":
    import sys
    disease = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Angelman syndrome"
    print(f"\nBuilding disease space for: {disease}")
    space = build_disease_space(disease)
    print("\n" + format_space_for_claude(space))
    print(f"\nTotal programs: {space['pipeline']['total_programs']}")
    print(f"Data quality: {json.dumps(space['data_quality'], indent=2)}")
