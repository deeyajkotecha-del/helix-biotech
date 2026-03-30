"""
SatyaBio — Dynamic Drug Discovery Engine
=========================================
Replaces all hardcoded drug lists, regex patterns, and disease-target maps
with live, API-driven discovery that stays current automatically.

Architecture:
  1. TARGET MAP — OpenTargets API + Claude fallback for disease→target associations
  2. DRUG EXTRACTION — INN/code-name pattern recognition + Claude classification
  3. LANDSCAPE BUILDER — Orchestrates CT.gov → extract → classify → cache
  4. CACHING — Neon DB with TTL (24h landscapes, 7d target maps)

Data Sources:
  - ClinicalTrials.gov v2 API (trials, interventions, phases, sponsors)
  - OpenTargets Platform API (disease-target associations, drug-target links)
  - OpenFDA (approval status)
  - Claude API (MoA classification, target map generation, entity resolution)

Usage:
    from dynamic_discovery import discover_landscape, get_target_map

    # Full landscape for any indication/target — no hardcoding needed
    landscape = discover_landscape("KRAS")
    landscape = discover_landscape("Atopic Dermatitis")
    landscape = discover_landscape("GLP-1")

    # Dynamic target map for any disease
    targets = get_target_map("Alzheimer's Disease")
"""

import os
import re
import sys
import json
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

import requests

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.extras
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CTGOV_BASE = "https://clinicaltrials.gov/api/v2/studies"
OPENTARGETS_API = "https://api.platform.opentargets.org/api/v4/graphql"

# Cache TTLs
LANDSCAPE_TTL_HOURS = 24
TARGET_MAP_TTL_DAYS = 7
DRUG_CLASSIFICATION_TTL_DAYS = 30

# Claude client (lazy init)
_client = None

def _get_client():
    global _client
    if _client is None and CLAUDE_AVAILABLE:
        _client = anthropic.Anthropic()
    return _client


def _call_claude(max_retries=3, **kwargs):
    """Call Claude API with retry on overloaded errors."""
    client = _get_client()
    if not client:
        return None
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  [Claude] Overloaded, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def _get_conn():
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL)


# =============================================================================
# SCHEMA — Cache tables for dynamic discovery
# =============================================================================

CACHE_SCHEMA = """
-- Dynamic discovery cache tables
CREATE TABLE IF NOT EXISTS discovery_cache (
    cache_key       TEXT PRIMARY KEY,
    cache_type      TEXT NOT NULL,           -- 'landscape', 'target_map', 'drug_class'
    query           TEXT NOT NULL,
    result_json     JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    hit_count       INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_discovery_cache_type ON discovery_cache(cache_type);
CREATE INDEX IF NOT EXISTS idx_discovery_cache_expires ON discovery_cache(expires_at);

-- Dynamic drug classifications (persisted beyond cache TTL)
CREATE TABLE IF NOT EXISTS drug_classifications (
    drug_name       TEXT PRIMARY KEY,
    aliases         TEXT[] DEFAULT '{}',
    company         TEXT,
    mechanism       TEXT,
    target          TEXT,
    modality        TEXT,                    -- small_molecule, mab, adc, bispecific, etc.
    drug_class      TEXT,                    -- e.g. "KRAS G12C inhibitor"
    source          TEXT NOT NULL,           -- 'claude', 'opentargets', 'ctgov', 'fda'
    confidence      REAL DEFAULT 0.8,
    raw_context     TEXT,                    -- trial title/intervention text used for classification
    classified_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_drug_class_target ON drug_classifications(target);
CREATE INDEX IF NOT EXISTS idx_drug_class_mechanism ON drug_classifications(mechanism);

-- Dynamic target-disease associations (replaces DISEASE_TARGET_MAP)
CREATE TABLE IF NOT EXISTS dynamic_target_map (
    id              SERIAL PRIMARY KEY,
    disease         TEXT NOT NULL,
    target_name     TEXT NOT NULL,
    target_class    TEXT,                    -- 'established', 'emerging', 'exploratory'
    evidence_score  REAL DEFAULT 0.0,
    description     TEXT,
    source          TEXT NOT NULL,           -- 'opentargets', 'claude', 'hybrid'
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(disease, target_name)
);
CREATE INDEX IF NOT EXISTS idx_target_map_disease ON dynamic_target_map(disease);
"""


def setup_cache_tables():
    """Create cache tables if they don't exist."""
    conn = _get_conn()
    if not conn:
        print("  [Cache] No DB connection — running without cache")
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(CACHE_SCHEMA)
        conn.commit()
        print("  [Cache] Tables ready")
        return True
    except Exception as e:
        print(f"  [Cache] Setup error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# =============================================================================
# CACHE — Read/write with TTL
# =============================================================================

def _cache_key(cache_type: str, query: str) -> str:
    """Generate a deterministic cache key."""
    normalized = query.strip().lower()
    return hashlib.sha256(f"{cache_type}:{normalized}".encode()).hexdigest()[:32]


def _cache_get(cache_type: str, query: str) -> Optional[dict]:
    """Get a cached result if it exists and hasn't expired."""
    conn = _get_conn()
    if not conn:
        return None
    try:
        key = _cache_key(cache_type, query)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT result_json FROM discovery_cache
                WHERE cache_key = %s AND expires_at > NOW()
            """, (key,))
            row = cur.fetchone()
            if row:
                # Bump hit count
                cur.execute("""
                    UPDATE discovery_cache SET hit_count = hit_count + 1
                    WHERE cache_key = %s
                """, (key,))
                conn.commit()
                return row["result_json"]
        return None
    except Exception as e:
        print(f"  [Cache] Read error: {e}")
        return None
    finally:
        conn.close()


def _cache_set(cache_type: str, query: str, result: dict, ttl_hours: int = 24):
    """Store a result in cache with TTL."""
    conn = _get_conn()
    if not conn:
        return
    try:
        key = _cache_key(cache_type, query)
        expires = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO discovery_cache (cache_key, cache_type, query, result_json, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (cache_key) DO UPDATE SET
                    result_json = EXCLUDED.result_json,
                    expires_at = EXCLUDED.expires_at,
                    created_at = NOW(),
                    hit_count = 0
            """, (key, cache_type, query.strip().lower(), json.dumps(result), expires))
        conn.commit()
    except Exception as e:
        print(f"  [Cache] Write error: {e}")
        conn.rollback()
    finally:
        conn.close()


# =============================================================================
# 1. OPENTARGETS API — Dynamic target-disease associations
# =============================================================================

def _search_opentargets_disease(disease_name: str) -> Optional[str]:
    """Search OpenTargets for a disease ID (EFO code)."""
    query = """
    query SearchDisease($q: String!) {
      search(queryString: $q, entityNames: ["disease"], page: {size: 5, index: 0}) {
        hits {
          id
          name
          entity
          score
        }
      }
    }
    """
    try:
        resp = requests.post(OPENTARGETS_API, json={
            "query": query,
            "variables": {"q": disease_name}
        }, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("data", {}).get("search", {}).get("hits", [])
        for hit in hits:
            if hit.get("entity") == "disease":
                return hit["id"]
        return None
    except Exception as e:
        print(f"  [OpenTargets] Disease search error: {e}")
        return None


def _get_opentargets_targets(disease_id: str, max_targets: int = 30) -> list[dict]:
    """Get top associated targets for a disease from OpenTargets."""
    query = """
    query DiseaseTargets($diseaseId: String!, $size: Int!) {
      disease(efoId: $diseaseId) {
        id
        name
        associatedTargets(page: {size: $size, index: 0}) {
          rows {
            target {
              id
              approvedSymbol
              approvedName
            }
            score
            datatypeScores {
              id
              score
            }
          }
        }
      }
    }
    """
    try:
        resp = requests.post(OPENTARGETS_API, json={
            "query": query,
            "variables": {"diseaseId": disease_id, "size": max_targets}
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", {}).get("disease", {})
        rows = data.get("associatedTargets", {}).get("rows", [])

        targets = []
        for row in rows:
            target = row.get("target", {})
            score = row.get("score", 0)

            # Determine relevance class based on evidence score
            if score >= 0.5:
                relevance = "established"
            elif score >= 0.2:
                relevance = "emerging"
            else:
                relevance = "exploratory"

            # Get the most relevant datatype
            datatype_scores = row.get("datatypeScores", [])
            top_evidence = max(datatype_scores, key=lambda d: d.get("score", 0), default={})

            targets.append({
                "target_name": target.get("approvedSymbol", ""),
                "full_name": target.get("approvedName", ""),
                "target_id": target.get("id", ""),
                "evidence_score": round(score, 3),
                "relevance": relevance,
                "top_evidence_type": top_evidence.get("id", ""),
                "source": "opentargets",
            })

        return targets
    except Exception as e:
        print(f"  [OpenTargets] Target fetch error: {e}")
        return []


def _get_opentargets_drugs(disease_id: str, max_drugs: int = 50) -> list[dict]:
    """Get known drugs for a disease from OpenTargets."""
    query = """
    query DiseaseDrugs($diseaseId: String!) {
      disease(efoId: $diseaseId) {
        drugAndClinicalCandidates {
          count
          rows {
            id
            drug {
              id
              name
              drugType
              mechanismsOfAction {
                rows {
                  mechanismOfAction
                  targets {
                    approvedSymbol
                  }
                }
              }
            }
            maxClinicalStage
          }
        }
      }
    }
    """
    try:
        resp = requests.post(OPENTARGETS_API, json={
            "query": query,
            "variables": {"diseaseId": disease_id}
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", {}).get("disease", {})
        rows = data.get("drugAndClinicalCandidates", {}).get("rows", [])

        drugs = []
        seen = set()
        for row in rows[:max_drugs]:
            drug = row.get("drug", {})
            name = drug.get("name", "")
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())

            moa_rows = drug.get("mechanismsOfAction", {}).get("rows", [])
            mechanisms = []
            targets = []
            for moa in moa_rows:
                if moa.get("mechanismOfAction"):
                    mechanisms.append(moa["mechanismOfAction"])
                for t in moa.get("targets", []):
                    if t.get("approvedSymbol"):
                        targets.append(t["approvedSymbol"])

            # Convert OpenTargets phase format to numeric
            phase_str = row.get("maxClinicalStage", "")
            phase_map = {"PHASE_4": 4, "PHASE_3": 3, "PHASE_2_3": 3,
                         "PHASE_2": 2, "PHASE_1_2": 2, "PHASE_1": 1}
            phase_num = phase_map.get(phase_str, 0)

            drugs.append({
                "drug_name": name,
                "drug_type": drug.get("drugType", ""),
                "phase": phase_num,
                "status": phase_str,
                "mechanism": "; ".join(mechanisms) if mechanisms else "",
                "targets": list(set(targets)),
                "source": "opentargets",
            })

        return drugs
    except Exception as e:
        print(f"  [OpenTargets] Drug fetch error: {e}")
        return []


# =============================================================================
# 2. CLAUDE — Dynamic target map + drug classification
# =============================================================================

TARGET_MAP_PROMPT = """You are a biotech/pharma expert. Given a disease or therapeutic area,
identify ALL the key biological targets and therapeutic approaches currently being pursued
in drug development.

For each target/approach, provide:
- target_name: The gene symbol, protein, or approach name (e.g., "KRAS G12C", "PD-1", "Amyloid-beta")
- target_class: "established" (approved drugs or Phase 3+), "emerging" (Phase 1-2 with promising data), or "exploratory" (preclinical or early Phase 1)
- description: One sentence explaining why this target matters for this disease
- drug_examples: 2-3 example drugs in development for this target (if known)

Be COMPREHENSIVE — include both well-known targets and newer/emerging approaches.
Group related targets logically (e.g., for KRAS: G12C-selective, G12D-selective, pan-KRAS, indirect pathway).

Return ONLY a JSON array, no other text:
[
  {
    "target_name": "...",
    "target_class": "established|emerging|exploratory",
    "description": "...",
    "drug_examples": ["drug1", "drug2"]
  }
]"""


def _generate_target_map_claude(disease: str) -> list[dict]:
    """Use Claude to generate a target map for any disease."""
    if not CLAUDE_AVAILABLE:
        return []
    try:
        response = _call_claude(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            system=TARGET_MAP_PROMPT,
            messages=[{"role": "user", "content": f"Disease/therapeutic area: {disease}"}],
        )
        text = response.content[0].text.strip()
        # Extract JSON from response
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        targets = json.loads(text)
        for t in targets:
            t["source"] = "claude"
            t["evidence_score"] = {"established": 0.8, "emerging": 0.5, "exploratory": 0.2}.get(
                t.get("target_class", ""), 0.3
            )
        return targets
    except Exception as e:
        print(f"  [Claude] Target map generation error: {e}")
        return []


DRUG_CLASSIFIER_PROMPT = """You are a pharmaceutical drug classifier. Given a list of drug names
extracted from clinical trial data, classify each one.

For EACH drug, provide:
- drug_name: The canonical/most common name
- aliases: Other names this drug goes by (company codes, brand names, INN)
- company: The developing company (if identifiable from name/context)
- mechanism: Brief mechanism of action (e.g., "selective KRAS G12C inhibitor")
- target: The primary molecular target (e.g., "KRAS G12C", "PD-1", "GLP-1R")
- modality: One of: small_molecule, monoclonal_antibody, adc, bispecific, cell_therapy,
  gene_therapy, peptide, oligonucleotide, vaccine, protein_degrader, radiopharmaceutical, other
- drug_class: The therapeutic class grouping (e.g., "KRAS G12C inhibitor", "PD-1 checkpoint inhibitor", "GLP-1 receptor agonist")
- confidence: 0.0-1.0 how confident you are in this classification

If you don't recognize a drug name, still classify it based on naming patterns:
- Names ending in -mab are monoclonal antibodies
- Names ending in -nib or -tinib are kinase inhibitors
- Names ending in -tide or -glutide are peptides/GLP-1 agonists
- Code names like ABC-1234 may be identifiable by the company prefix

Return ONLY a JSON array, no other text:
[
  {
    "drug_name": "...",
    "aliases": ["..."],
    "company": "...",
    "mechanism": "...",
    "target": "...",
    "modality": "...",
    "drug_class": "...",
    "confidence": 0.9
  }
]"""


def classify_drugs_batch(drug_entries: list[dict], query_context: str = "") -> list[dict]:
    """
    Use Claude to classify a batch of drugs in one API call.

    Args:
        drug_entries: List of dicts with at least 'drug_name' and optionally
                     'trial_title', 'sponsor', 'conditions', 'interventions'
        query_context: The original landscape query for context (e.g., "KRAS")

    Returns:
        List of classification dicts
    """
    if not CLAUDE_AVAILABLE or not drug_entries:
        return []

    # Build context string for Claude
    lines = [f"Landscape context: {query_context}\n"] if query_context else []
    for entry in drug_entries[:50]:  # Cap at 50 per batch to stay within token limits
        name = entry.get("drug_name", "")
        sponsor = entry.get("sponsor", "")
        conditions = entry.get("conditions", "")
        trial_title = entry.get("trial_title", "")
        line = f"- {name}"
        if sponsor:
            line += f" (sponsor: {sponsor})"
        if conditions:
            line += f" [conditions: {conditions}]"
        if trial_title:
            line += f" — trial: {trial_title}"
        lines.append(line)

    try:
        response = _call_claude(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            system=DRUG_CLASSIFIER_PROMPT,
            messages=[{"role": "user", "content": "\n".join(lines)}],
        )
        text = response.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        classifications = json.loads(text)

        # Store classifications in DB for future use
        _store_classifications(classifications)

        return classifications
    except Exception as e:
        print(f"  [Claude] Drug classification error: {e}")
        return []


def _store_classifications(classifications: list[dict]):
    """Persist drug classifications to the database."""
    conn = _get_conn()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            for c in classifications:
                cur.execute("""
                    INSERT INTO drug_classifications
                        (drug_name, aliases, company, mechanism, target, modality, drug_class, source, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'claude', %s)
                    ON CONFLICT (drug_name) DO UPDATE SET
                        aliases = EXCLUDED.aliases,
                        company = COALESCE(NULLIF(EXCLUDED.company, ''), drug_classifications.company),
                        mechanism = COALESCE(NULLIF(EXCLUDED.mechanism, ''), drug_classifications.mechanism),
                        target = COALESCE(NULLIF(EXCLUDED.target, ''), drug_classifications.target),
                        modality = COALESCE(NULLIF(EXCLUDED.modality, ''), drug_classifications.modality),
                        drug_class = COALESCE(NULLIF(EXCLUDED.drug_class, ''), drug_classifications.drug_class),
                        confidence = GREATEST(EXCLUDED.confidence, drug_classifications.confidence),
                        updated_at = NOW()
                """, (
                    c.get("drug_name", ""),
                    c.get("aliases", []),
                    c.get("company", ""),
                    c.get("mechanism", ""),
                    c.get("target", ""),
                    c.get("modality", ""),
                    c.get("drug_class", ""),
                    c.get("confidence", 0.8),
                ))
        conn.commit()
    except Exception as e:
        print(f"  [DB] Classification store error: {e}")
        conn.rollback()
    finally:
        conn.close()


def _get_cached_classifications(drug_names: list[str]) -> dict:
    """Look up previously classified drugs from the database."""
    conn = _get_conn()
    if not conn or not drug_names:
        return {}
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM drug_classifications
                WHERE drug_name = ANY(%s)
            """, (drug_names,))
            rows = cur.fetchall()
            return {row["drug_name"]: dict(row) for row in rows}
    except Exception as e:
        # Table might not exist yet
        return {}
    finally:
        conn.close()


# =============================================================================
# 3. DRUG EXTRACTION — INN patterns + code names (no hardcoded drug lists)
# =============================================================================

# WHO International Nonproprietary Name (INN) suffix patterns
# These are standardized naming stems assigned by WHO — if a word ends with one,
# it's almost certainly a pharmaceutical compound
INN_SUFFIXES = re.compile(
    r'^[a-z].*(?:'
    # Monoclonal antibodies
    r'mab|zumab|ximab|mumab|tumab|lumab|numab|rumab|'
    # Kinase inhibitors
    r'tinib|nib|ciclib|sertib|metinib|ratinib|citinib|letinib|lisib|'
    # Peptides & receptor agonists
    r'tide|glutide|reotide|relbin|'
    # Cardiovascular / metabolic
    r'pril|sartan|olol|statin|vastatin|prazole|gliptin|gliflozin|'
    # Anti-infectives
    r'cillin|floxacin|mycin|cycline|bactam|fungin|vudine|virin|'
    # Other stems
    r'lukast|parin|platin|rubicin|'
    # ADC / fusion / bispecific suffixes
    r'vedotin|mertansine|tansine|ozogamicin|ravtansine|'
    r'fusp|cept'
    r')$',
    re.IGNORECASE
)

# Pharma company code name patterns (e.g., RMC-6236, PF-06939926, BGB-53038)
CODE_NAME_PATTERN = re.compile(
    r'^[A-Z]{1,5}[\-]?\d{2,7}[A-Z]?$|'
    r'^[A-Z]{2,6}[\-]\d{2,}(?:[\-]\d+)?$|'
    r'^[A-Z]\d{4,}$',
    re.IGNORECASE
)

# Known non-drug terms to skip
SKIP_TERMS = {
    "placebo", "sham", "saline", "vehicle", "no treatment", "no intervention",
    "standard of care", "standard care", "best supportive care", "bsc",
    "soc", "usual care", "active comparator", "comparator", "control group",
    "surgery", "radiation", "radiotherapy", "phototherapy", "cryotherapy",
    "biopsy", "transplant", "dialysis", "device", "laser", "ultrasound",
    "blood draw", "blood test", "clinical examination", "phone call",
    "telemedicine", "telehealth", "questionnaire", "survey", "interview",
    "observation", "monitoring", "follow-up", "assessment", "evaluation",
    "dietary supplement", "vitamin", "mineral", "probiotic", "prebiotic",
    "exercise", "physical therapy", "cognitive therapy", "counseling",
    "behavioral", "psychotherapy", "meditation", "yoga", "acupuncture",
    "placebo oral tablet", "matching placebo", "dummy", "open label",
    "dose escalation", "dose expansion", "arm 1", "arm 2", "arm 3",
    "cohort a", "cohort b", "group 1", "group 2", "part a", "part b",
    "treatment", "intervention", "experimental", "investigational",
    "chemotherapy", "immunotherapy", "targeted therapy", "combination therapy",
    "monotherapy", "maintenance", "adjuvant", "neoadjuvant", "palliative",
    "aspirin", "acetaminophen", "ibuprofen", "naproxen", "metformin",
    "insulin", "dexamethasone", "prednisone", "prednisolone", "hydrocortisone",
}


def extract_drugs_from_trials(trials: list[dict]) -> list[dict]:
    """
    Extract drug candidates from ClinicalTrials.gov results WITHOUT hardcoded patterns.

    Uses INN suffix recognition + pharma code name detection to identify drugs
    from intervention fields. Returns structured entries ready for Claude classification.
    """
    drug_candidates = {}  # drug_name_lower → entry dict

    for trial in trials:
        # Get all intervention names
        interventions = trial.get("interventions", [])
        if isinstance(interventions, str):
            intervention_names = [interventions]
        elif isinstance(interventions, list):
            intervention_names = []
            for inv in interventions:
                if isinstance(inv, dict):
                    name = inv.get("name", "")
                    inv_type = inv.get("type", "")
                    # Skip non-drug intervention types
                    if inv_type.upper() in ("PROCEDURE", "BEHAVIORAL", "DEVICE", "DIAGNOSTIC_TEST",
                                            "RADIATION", "DIETARY_SUPPLEMENT", "OTHER"):
                        continue
                    intervention_names.append(name)
                elif isinstance(inv, str):
                    intervention_names.append(inv)
        else:
            intervention_names = []

        # Also check the trial title
        title = trial.get("title", "") or trial.get("official_title", "")

        for raw_name in intervention_names:
            if not raw_name:
                continue

            # Split on common delimiters (trials list "Drug A + Drug B" or "Drug A, Drug B")
            parts = re.split(r'[+/,;]|\band\b|\bwith\b|\bversus\b|\bvs\.?\b', raw_name)

            for part in parts:
                name = part.strip().strip('"').strip("'").strip()

                # Skip empty, too short, too long, or known non-drugs
                if not name or len(name) < 3 or len(name) > 60:
                    continue
                if name.lower() in SKIP_TERMS:
                    continue
                # Skip if it's just a number or dose
                if re.match(r'^[\d\s.]+\s*(mg|ml|mcg|ug|g|kg|%|iu|units?)?\s*$', name, re.IGNORECASE):
                    continue
                # Skip generic descriptors
                if re.match(r'^(low|high|standard|reduced|full)\s+dose', name, re.IGNORECASE):
                    continue

                # Check if this looks like a drug
                is_drug = False
                name_clean = name

                # Test 1: INN suffix match
                # Extract the last word and check against INN patterns
                words = name.split()
                last_word = words[-1].lower() if words else ""
                if INN_SUFFIXES.match(last_word):
                    is_drug = True
                    name_clean = name

                # Test 2: Pharma code name (e.g., RMC-6236, BGB-53038)
                if not is_drug:
                    for word in words:
                        if CODE_NAME_PATTERN.match(word) and len(word) >= 4:
                            is_drug = True
                            name_clean = word
                            break

                # Test 3: Known drug name patterns not caught by INN
                # (brand names like Keytruda, Enhertu, Opdivo are not INN-patterned)
                if not is_drug and len(words) <= 3:
                    # Single/double word names that are proper nouns (capitalized)
                    if words[0][0].isupper() and not name.lower() in SKIP_TERMS:
                        # Additional heuristic: if the trial is a DRUG type intervention
                        # and the name is capitalized, it's likely a drug
                        if len(words) == 1 and len(name) >= 4:
                            is_drug = True
                            name_clean = name

                if is_drug:
                    key = name_clean.lower().strip()
                    if key not in drug_candidates:
                        drug_candidates[key] = {
                            "drug_name": name_clean,
                            "sponsor": trial.get("sponsor", ""),
                            "conditions": ", ".join(trial.get("conditions", []))
                                          if isinstance(trial.get("conditions"), list)
                                          else str(trial.get("conditions", "")),
                            "trial_title": title,
                            "trial_ids": [],
                            "phases": [],
                            "statuses": [],
                            "countries": [],
                            "total_trials": 0,
                            "active_trials": 0,
                        }

                    entry = drug_candidates[key]
                    nct = trial.get("nct_id", "")
                    if nct and nct not in entry["trial_ids"]:
                        entry["trial_ids"].append(nct)
                    entry["total_trials"] += 1

                    phase = trial.get("phase", "")
                    if phase and phase not in entry["phases"]:
                        entry["phases"].append(phase)

                    status = trial.get("status", "")
                    if status and status not in entry["statuses"]:
                        entry["statuses"].append(status)
                    if status in ("RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING"):
                        entry["active_trials"] += 1

    return list(drug_candidates.values())


# =============================================================================
# 4. GET TARGET MAP — OpenTargets + Claude hybrid
# =============================================================================

def get_target_map(disease: str) -> list[dict]:
    """
    Get biological targets/approaches for a disease.
    Uses OpenTargets first, falls back to Claude for coverage gaps.
    Results are cached in DB with 7-day TTL.
    """
    # Check cache first
    cached = _cache_get("target_map", disease)
    if cached:
        print(f"  [TargetMap] Cache hit for '{disease}'")
        return cached.get("targets", [])

    print(f"  [TargetMap] Building target map for '{disease}'...")
    all_targets = []

    # Step 1: Try OpenTargets
    disease_id = _search_opentargets_disease(disease)
    ot_targets = []
    if disease_id:
        print(f"  [OpenTargets] Found disease ID: {disease_id}")
        ot_targets = _get_opentargets_targets(disease_id, max_targets=25)
        if ot_targets:
            print(f"  [OpenTargets] Found {len(ot_targets)} targets")
            all_targets.extend(ot_targets)

    # Step 2: Always use Claude to get therapeutic-approach-level groupings
    # OpenTargets gives gene-level targets but Claude gives the strategic landscape view
    # (e.g., "KRAS G12C-selective" vs "pan-KRAS" vs "indirect KRAS pathway")
    claude_targets = _generate_target_map_claude(disease)
    if claude_targets:
        print(f"  [Claude] Generated {len(claude_targets)} target groupings")
        # Merge: Claude provides the strategic groupings, OpenTargets provides evidence scores
        existing_names = {t["target_name"].lower() for t in all_targets}
        for ct in claude_targets:
            if ct["target_name"].lower() not in existing_names:
                all_targets.append(ct)
                existing_names.add(ct["target_name"].lower())

    # Store in DB for persistence
    _store_target_map(disease, all_targets)

    # Cache the result
    result = {"disease": disease, "targets": all_targets, "timestamp": datetime.now(timezone.utc).isoformat()}
    _cache_set("target_map", disease, result, ttl_hours=TARGET_MAP_TTL_DAYS * 24)

    print(f"  [TargetMap] Total: {len(all_targets)} targets for '{disease}'")
    return all_targets


def _store_target_map(disease: str, targets: list[dict]):
    """Persist target map to the database."""
    conn = _get_conn()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            for t in targets:
                cur.execute("""
                    INSERT INTO dynamic_target_map
                        (disease, target_name, target_class, evidence_score, description, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (disease, target_name) DO UPDATE SET
                        target_class = EXCLUDED.target_class,
                        evidence_score = GREATEST(EXCLUDED.evidence_score, dynamic_target_map.evidence_score),
                        description = COALESCE(NULLIF(EXCLUDED.description, ''), dynamic_target_map.description),
                        updated_at = NOW()
                """, (
                    disease,
                    t.get("target_name", ""),
                    t.get("target_class", t.get("relevance", "emerging")),
                    t.get("evidence_score", 0.5),
                    t.get("description", ""),
                    t.get("source", "hybrid"),
                ))
        conn.commit()
    except Exception as e:
        print(f"  [DB] Target map store error: {e}")
        conn.rollback()
    finally:
        conn.close()


# =============================================================================
# 5. DISCOVER LANDSCAPE — The main orchestrator
# =============================================================================

PHASE_RANK = {
    "PHASE4": 5, "PHASE3": 4, "PHASE2,PHASE3": 3.5, "PHASE2, PHASE3": 3.5,
    "PHASE2": 3, "PHASE1,PHASE2": 2.5, "PHASE1, PHASE2": 2.5,
    "PHASE1": 2, "EARLY_PHASE1": 1.5, "NA": 1, "": 0,
}


def discover_landscape(query: str, region: str = "all", max_trials: int = 200,
                        force_refresh: bool = False) -> dict:
    """
    Build a complete drug landscape for any indication, target, or drug class.
    Fully dynamic — no hardcoded drug lists or regex patterns.

    Pipeline:
      1. Check cache (24h TTL)
      2. Fetch trials from ClinicalTrials.gov
      3. Extract drug names using INN/code-name patterns
      4. Look up existing classifications from DB
      5. Classify unknown drugs with Claude (batch)
      6. Fetch OpenTargets data for additional context
      7. Group by drug class / mechanism
      8. Cache and return

    Args:
        query: Target, indication, or drug class (e.g., "KRAS", "Atopic Dermatitis", "GLP-1")
        region: "all", "china", "korea", "japan", "india", "europe"
        max_trials: Maximum trials to fetch
        force_refresh: Skip cache and rebuild

    Returns:
        Dict with landscape data:
        {
            "query": str,
            "assets": [{"drug_name", "company", "mechanism", "target", "drug_class",
                        "modality", "highest_phase", "trial_count", "active_trials",
                        "trial_ids", "conditions", "countries"}],
            "drug_classes": {"class_name": [drug_names]},
            "target_map": [{"target_name", "relevance", "description"}],
            "total_trials": int,
            "total_assets": int,
            "timestamp": str
        }
    """
    cache_key_query = f"{query}|{region}"

    # Step 0: Check cache
    if not force_refresh:
        cached = _cache_get("landscape", cache_key_query)
        if cached:
            print(f"  [Landscape] Cache hit for '{query}' (region={region})")
            return cached

    print(f"\n{'='*80}")
    print(f"  DYNAMIC LANDSCAPE DISCOVERY: {query}")
    print(f"  Region: {region} | Max trials: {max_trials}")
    print(f"{'='*80}\n")

    # Step 1: Fetch trials from ClinicalTrials.gov
    print("  Step 1: Fetching trials from ClinicalTrials.gov...")
    all_trials = _fetch_trials_comprehensive(query, region, max_trials)
    print(f"  Total trials fetched: {len(all_trials)}")

    if not all_trials:
        empty_result = {
            "query": query, "region": region, "assets": [], "drug_classes": {},
            "target_map": [], "total_trials": 0, "total_assets": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return empty_result

    # Step 2: Extract drug candidates from trials
    print("\n  Step 2: Extracting drug candidates...")
    drug_candidates = extract_drugs_from_trials(all_trials)
    print(f"  Found {len(drug_candidates)} unique drug candidates")

    # Step 3: Check DB for existing classifications
    print("\n  Step 3: Looking up existing drug classifications...")
    drug_names = [d["drug_name"] for d in drug_candidates]
    known = _get_cached_classifications(drug_names)
    print(f"  Found {len(known)} previously classified drugs")

    # Step 4: Classify unknown drugs with Claude
    unknown = [d for d in drug_candidates if d["drug_name"] not in known]
    classifications = {}
    if unknown:
        print(f"\n  Step 4: Classifying {len(unknown)} new drugs with Claude...")
        # Batch into groups of 40 for API efficiency
        for i in range(0, len(unknown), 40):
            batch = unknown[i:i+40]
            batch_results = classify_drugs_batch(batch, query_context=query)
            for c in batch_results:
                classifications[c["drug_name"].lower()] = c
        print(f"  Classified {len(classifications)} drugs")
    else:
        print("  Step 4: All drugs already classified — skipping Claude")

    # Step 5: Try OpenTargets for additional drug/target data
    print("\n  Step 5: Checking OpenTargets for additional context...")
    ot_drugs = []
    disease_id = _search_opentargets_disease(query)
    if disease_id:
        ot_drugs = _get_opentargets_drugs(disease_id, max_drugs=50)
        print(f"  [OpenTargets] Found {len(ot_drugs)} known drugs")

    # Step 6: Merge everything into final asset list
    print("\n  Step 6: Building final landscape...")
    assets = _merge_landscape(drug_candidates, known, classifications, ot_drugs)

    # Step 7: Group by drug class
    drug_classes = defaultdict(list)
    for asset in assets:
        cls = asset.get("drug_class", "Unclassified")
        if cls:
            drug_classes[cls].append(asset["drug_name"])

    # Step 8: Get target map (uses its own cache)
    target_map = get_target_map(query)

    # Build final result
    result = {
        "query": query,
        "region": region,
        "assets": assets,
        "drug_classes": dict(drug_classes),
        "target_map": target_map,
        "total_trials": len(all_trials),
        "total_assets": len(assets),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Cache the result
    _cache_set("landscape", cache_key_query, result, ttl_hours=LANDSCAPE_TTL_HOURS)

    print(f"\n  {'='*60}")
    print(f"  LANDSCAPE COMPLETE: {len(assets)} drug assets across {len(drug_classes)} classes")
    print(f"  From {len(all_trials)} clinical trials")
    print(f"  {'='*60}\n")

    return result


def _fetch_trials_comprehensive(query: str, region: str, max_trials: int) -> list[dict]:
    """
    Fetch trials using multiple search strategies to maximize coverage.
    Uses Claude to expand the query into sub-searches for comprehensive discovery.
    """
    all_trials = {}  # nct_id → trial dict

    def _add(trials_list):
        for t in trials_list:
            nct = t.get("nct_id", "")
            if nct and nct not in all_trials:
                all_trials[nct] = t

    # Strategy 1: Search by condition
    _add(_fetch_ctgov(condition=query, max_results=max_trials))

    # Strategy 2: Search by intervention
    _add(_fetch_ctgov(intervention=query, max_results=min(100, max_trials)))

    # Strategy 3: General term search (titles, keywords, etc.)
    _add(_fetch_ctgov(term=query, max_results=min(100, max_trials)))

    # Strategy 4: Expand the query into related sub-searches
    # For molecular targets (KRAS, EGFR, PD-1, etc.), also search for:
    #   - The target + "inhibitor" as intervention
    #   - Known allele variants (KRAS → G12C, G12D, G12V, etc.)
    #   - The target + common cancer types
    expanded_terms = _expand_search_query(query)
    for term in expanded_terms:
        if len(all_trials) >= max_trials * 2:  # Allow 2x for comprehensive discovery
            break
        _add(_fetch_ctgov(intervention=term, max_results=50))

    # Strategy 5: Region-specific searches
    region_country_map = {
        "china": "China", "korea": "Korea, Republic of",
        "japan": "Japan", "india": "India",
    }
    if region in region_country_map:
        _add(_fetch_ctgov(condition=query, country=region_country_map[region], max_results=50))
        _add(_fetch_ctgov(term=query, country=region_country_map[region], max_results=50))
    elif region == "all":
        for country in ["China", "Japan", "Korea, Republic of"]:
            _add(_fetch_ctgov(condition=query, country=country, max_results=30))

    return list(all_trials.values())


def _expand_search_query(query: str) -> list[str]:
    """
    Use Claude to expand a target/indication into sub-search terms
    for comprehensive trial discovery. Cached to avoid repeated API calls.
    """
    # Check cache
    cached = _cache_get("query_expansion", query)
    if cached:
        return cached.get("terms", [])

    if not CLAUDE_AVAILABLE:
        return []

    try:
        response = _call_claude(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system="""Given a drug target or disease, generate 5-10 ClinicalTrials.gov search terms
that would find ALL relevant clinical trials. Include:
- Allele/mutation variants (e.g., KRAS → "KRAS G12C", "KRAS G12D", "KRAS G12V")
- Drug class terms (e.g., KRAS → "KRAS inhibitor", "RAS inhibitor", "SHP2 inhibitor")
- Related pathway terms (e.g., KRAS → "MAPK pathway", "MEK inhibitor")
- Combination partner terms common in this space

Return ONLY a JSON array of search strings, no other text.""",
            messages=[{"role": "user", "content": f"Target/disease: {query}"}],
        )
        text = response.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        terms = json.loads(text)
        # Cache for 7 days
        _cache_set("query_expansion", query, {"terms": terms}, ttl_hours=7*24)
        return terms
    except Exception as e:
        print(f"  [Claude] Query expansion error: {e}")
        return []


def _fetch_ctgov(condition: str = "", intervention: str = "", term: str = "",
                  country: str = "", max_results: int = 100) -> list[dict]:
    """Low-level ClinicalTrials.gov v2 API call."""
    params = {
        "format": "json",
        "pageSize": min(max_results, 100),
    }
    if condition:
        params["query.cond"] = condition
    if intervention:
        params["query.intr"] = intervention
    if term:
        params["query.term"] = term
    if country:
        params["query.locn"] = country

    try:
        resp = requests.get(
            CTGOV_BASE, params=params,
            headers={"User-Agent": "SatyaBio/2.0 Dynamic Discovery"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [CT.gov] API error: {e}")
        return []

    results = []
    for study in data.get("studies", []):
        protocol = study.get("protocolSection", {})
        id_mod = protocol.get("identificationModule", {})
        status_mod = protocol.get("statusModule", {})
        design_mod = protocol.get("designModule", {})
        sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})
        cond_mod = protocol.get("conditionsModule", {})
        interv_mod = protocol.get("armsInterventionsModule", {})
        desc_mod = protocol.get("descriptionModule", {})
        contact_mod = protocol.get("contactsLocationsModule", {})

        interventions = []
        for arm in interv_mod.get("interventions", []):
            interventions.append({
                "name": arm.get("name", ""),
                "type": arm.get("type", ""),
            })

        conditions = cond_mod.get("conditions", [])

        # Extract countries from locations
        countries = set()
        for loc in contact_mod.get("locations", []):
            c = loc.get("country", "")
            if c:
                countries.add(c)

        results.append({
            "nct_id": id_mod.get("nctId", ""),
            "title": id_mod.get("briefTitle", ""),
            "official_title": id_mod.get("officialTitle", ""),
            "status": status_mod.get("overallStatus", ""),
            "phase": ",".join(design_mod.get("phases", [])),
            "conditions": conditions,
            "interventions": interventions,
            "sponsor": sponsor_mod.get("leadSponsor", {}).get("name", ""),
            "start_date": status_mod.get("startDateStruct", {}).get("date", ""),
            "enrollment": design_mod.get("enrollmentInfo", {}).get("count", 0),
            "countries": list(countries),
            "summary": desc_mod.get("briefSummary", ""),
        })

    return results


def _merge_landscape(candidates: list[dict], known: dict, new_classifications: dict,
                      ot_drugs: list[dict]) -> list[dict]:
    """Merge all data sources into a unified asset list."""
    assets = {}  # drug_name_lower → asset dict

    # Start with extracted candidates + their classifications
    for cand in candidates:
        name = cand["drug_name"]
        key = name.lower()

        # Look up classification (DB first, then new Claude results)
        cls = known.get(name, {})
        if not cls:
            cls = new_classifications.get(key, {})

        # Determine highest phase
        phases = cand.get("phases", [])
        highest_phase = ""
        highest_rank = 0
        for p in phases:
            rank = PHASE_RANK.get(p, 0)
            if rank > highest_rank:
                highest_rank = rank
                highest_phase = p

        assets[key] = {
            "drug_name": cls.get("drug_name", name),
            "aliases": cls.get("aliases", []),
            "company": cls.get("company", cand.get("sponsor", "")),
            "mechanism": cls.get("mechanism", ""),
            "target": cls.get("target", ""),
            "modality": cls.get("modality", ""),
            "drug_class": cls.get("drug_class", ""),
            "highest_phase": highest_phase,
            "highest_phase_rank": highest_rank,
            "total_trials": cand.get("total_trials", 0),
            "active_trials": cand.get("active_trials", 0),
            "trial_ids": cand.get("trial_ids", []),
            "conditions": cand.get("conditions", ""),
            "source": "clinicaltrials.gov",
        }

    # Merge OpenTargets drugs (adds drugs not found in CT.gov)
    for ot in ot_drugs:
        key = ot["drug_name"].lower()
        if key not in assets:
            phase_num = ot.get("phase", 0)
            phase_str = {4: "Approved", 3: "PHASE3", 2: "PHASE2", 1: "PHASE1"}.get(phase_num, "")
            assets[key] = {
                "drug_name": ot["drug_name"],
                "aliases": [],
                "company": "",
                "mechanism": ot.get("mechanism", ""),
                "target": ", ".join(ot.get("targets", [])),
                "modality": ot.get("drug_type", ""),
                "drug_class": "",
                "highest_phase": phase_str,
                "highest_phase_rank": phase_num,
                "total_trials": 0,
                "active_trials": 0,
                "trial_ids": [],
                "conditions": "",
                "source": "opentargets",
            }
        else:
            # Enrich existing entry with OpenTargets data
            existing = assets[key]
            if not existing["mechanism"] and ot.get("mechanism"):
                existing["mechanism"] = ot["mechanism"]
            if not existing["target"] and ot.get("targets"):
                existing["target"] = ", ".join(ot["targets"])

    # Sort by phase (highest first), then by trial count
    asset_list = sorted(
        assets.values(),
        key=lambda a: (a["highest_phase_rank"], a["total_trials"]),
        reverse=True,
    )

    return asset_list


# =============================================================================
# 6. FORMAT FOR CLAUDE SYNTHESIS — replaces format_global_landscape_for_claude
# =============================================================================

def format_landscape_for_claude(landscape: dict) -> str:
    """
    Format a dynamic landscape result for inclusion in Claude synthesis prompts.
    Groups assets by drug class with full trial-level detail so Claude can
    produce Open Evidence-quality narrative responses with inline citations.
    """
    if not landscape or not landscape.get("assets"):
        return ""

    lines = []
    query = landscape.get("query", "")
    total_assets = landscape.get("total_assets", len(landscape["assets"]))
    total_trials = landscape.get("total_trials", 0)

    lines.append(f"=== DRUG LANDSCAPE: {query} ===")
    lines.append(f"Total: {total_assets} drug assets from {total_trials} clinical trials")
    lines.append("")
    lines.append("IMPORTANT INSTRUCTIONS FOR SYNTHESIS:")
    lines.append("- Organize your answer by THERAPEUTIC STRATEGY / DRUG CLASS, not just a flat list")
    lines.append("- For each drug, cite specific NCT IDs inline: {{trial:NCTXXXXXXXX}}")
    lines.append("- Include mechanism of action detail (selectivity, target, modality)")
    lines.append("- Note regional context: which drugs are approved/in-trial in China/Asia vs US/EU")
    lines.append("- Group related drugs together (e.g., all PARP1-selective agents, all degraders)")
    lines.append("- Lead with the most clinically advanced / differentiated agents")
    lines.append("")

    # Group by drug_class
    assets_by_class = defaultdict(list)
    for asset in landscape["assets"]:
        cls = asset.get("drug_class", "") or asset.get("target", "") or "Unclassified"
        assets_by_class[cls].append(asset)

    # Sort classes: put classes with highest-phase drugs first
    def _class_rank(cls_name):
        assets = assets_by_class[cls_name]
        max_rank = max((a.get("highest_phase_rank", 0) for a in assets), default=0)
        total = sum(a.get("total_trials", 0) for a in assets)
        return (max_rank, total)

    sorted_classes = sorted(assets_by_class.keys(), key=_class_rank, reverse=True)

    for cls_name in sorted_classes:
        cls_assets = assets_by_class[cls_name]
        lines.append(f"\n╔══ {cls_name.upper()} ({len(cls_assets)} agents) ══╗")

        # Sort within class by phase rank then trial count
        cls_assets.sort(key=lambda a: (a.get("highest_phase_rank", 0), a.get("total_trials", 0)), reverse=True)

        for a in cls_assets:
            phase = a.get("highest_phase", "Unknown").replace("PHASE", "Phase ")
            company = a.get("company", "")
            mechanism = a.get("mechanism", "")
            modality = a.get("modality", "")
            target = a.get("target", "")
            trials = a.get("total_trials", 0)
            active = a.get("active_trials", 0)
            trial_ids = a.get("trial_ids", [])
            aliases = a.get("aliases", [])
            conditions = a.get("conditions", "")

            # Drug header
            header = f"  ▸ {a['drug_name']}"
            if aliases:
                header += f" (aliases: {', '.join(aliases[:3])})"
            if company:
                header += f" — {company}"
            lines.append(header)

            # Detail line 1: Phase + mechanism
            detail1 = f"    Phase: {phase} | Trials: {trials} ({active} active)"
            if mechanism:
                detail1 += f" | MoA: {mechanism}"
            elif target:
                detail1 += f" | Target: {target}"
            lines.append(detail1)

            # Detail line 2: Modality + conditions
            if modality or conditions:
                detail2 = "   "
                if modality:
                    detail2 += f" Modality: {modality}"
                if conditions:
                    cond_str = conditions if isinstance(conditions, str) else ", ".join(list(conditions)[:3])
                    detail2 += f" | Indications: {cond_str}"
                lines.append(detail2)

            # Trial IDs (so Claude can cite them)
            if trial_ids:
                nct_str = ", ".join(trial_ids[:8])
                if len(trial_ids) > 8:
                    nct_str += f" +{len(trial_ids)-8} more"
                lines.append(f"    NCT IDs: {nct_str}")

            lines.append("")  # spacer

    # Therapeutic approaches / target map
    target_map = landscape.get("target_map", [])
    if target_map:
        lines.append(f"\n╔══ THERAPEUTIC APPROACHES FOR {query.upper()} ══╗")
        for t in target_map:
            relevance = t.get("target_class", t.get("relevance", ""))
            desc = t.get("description", "")
            examples = t.get("drug_examples", [])
            line = f"  ▸ {t['target_name']} [{relevance}]"
            if desc:
                line += f" — {desc}"
            if examples:
                line += f" (e.g., {', '.join(examples[:3])})"
            lines.append(line)

    # Phase distribution summary
    assets = landscape["assets"]
    approved = sum(1 for a in assets if a.get("highest_phase", "").lower() in ("approved", "phase4", "phase 4"))
    ph3 = sum(1 for a in assets if a.get("highest_phase_rank", 0) >= 3.5 and a.get("highest_phase_rank", 0) < 5)
    ph2 = sum(1 for a in assets if 2.5 <= a.get("highest_phase_rank", 0) < 3.5)
    ph1 = sum(1 for a in assets if 1 <= a.get("highest_phase_rank", 0) < 2.5)

    lines.append(f"\nPhase distribution: {approved} Approved, {ph3} Phase 3, {ph2} Phase 2, {ph1} Phase 1")
    lines.append(f"Data source: ClinicalTrials.gov + OpenTargets (live query, {landscape.get('timestamp', 'today')})")

    return "\n".join(lines)


# =============================================================================
# CLI — for testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SatyaBio Dynamic Discovery")
    parser.add_argument("--landscape", type=str, help="Build landscape for target/indication")
    parser.add_argument("--targets", type=str, help="Get target map for a disease")
    parser.add_argument("--region", type=str, default="all", help="Region filter")
    parser.add_argument("--setup", action="store_true", help="Create cache tables")
    parser.add_argument("--refresh", action="store_true", help="Force cache refresh")
    args = parser.parse_args()

    if args.setup:
        setup_cache_tables()

    if args.targets:
        targets = get_target_map(args.targets)
        print(f"\nTarget map for '{args.targets}':")
        for t in targets:
            print(f"  [{t.get('target_class', '?')}] {t['target_name']} "
                  f"(score: {t.get('evidence_score', '?')}) — {t.get('description', '')}")

    if args.landscape:
        result = discover_landscape(args.landscape, region=args.region, force_refresh=args.refresh)
        print(f"\n{format_landscape_for_claude(result)}")
        print(f"\nDrug classes found:")
        for cls, drugs in result.get("drug_classes", {}).items():
            print(f"  {cls}: {', '.join(drugs)}")
