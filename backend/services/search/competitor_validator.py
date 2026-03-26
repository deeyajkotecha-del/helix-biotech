"""
SatyaBio — Competitor Validator Agent
======================================
Validates whether a drug candidate is a genuine competitor in a given
indication, using multi-source verification:

  1. ClinicalTrials.gov lookup — Does this drug have active trials in the indication?
  2. FDA check — Is it approved or in US FDA pipeline for this indication?
  2b. Global regulators — PMDA (Japan), NMPA (China), EMA (EU), MFDS (Korea)
  3. Drug entity database — Is it in our curated drug knowledge base?
  4. LLM Judge — Claude cross-references its knowledge to catch false positives

Inspired by the precision/recall grading loop in modern competitor discovery
systems: we mine negatives, train the validator to reject them, and measure
F1 over a test set to refine prompts over time.

Integration points:
  - entity_ingester.py calls validate_competitor() before adding low-confidence entities
  - query_router.py calls validate_landscape() to filter landscape results
  - entity_review_queue gets auto-populated with flagged entities

Usage:
    # Validate a single drug-indication pair
    python3 competitor_validator.py --drug "daraxonrasib" --indication "NSCLC"

    # Validate all pending entities in the review queue
    python3 competitor_validator.py --validate-queue

    # Run eval on test set to measure precision/recall
    python3 competitor_validator.py --eval

    # Show validation stats
    python3 competitor_validator.py --status

Requires in .env:
    ANTHROPIC_API_KEY=sk-ant-...
    NEON_DATABASE_URL=postgresql://...
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import requests

# ─── Optional imports ─────────────────────────────────────────────────────────

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

try:
    from api_connectors import search_clinical_trials, search_fda_drugs
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False

try:
    from drug_entities import get_conn, lookup_drug
    DRUG_DB_AVAILABLE = True
except ImportError:
    DRUG_DB_AVAILABLE = False


# ─── Validation result structure ──────────────────────────────────────────────

class ValidationResult:
    """Result of validating a drug-indication competitor claim."""

    def __init__(self, drug_name: str, indication: str):
        self.drug_name = drug_name
        self.indication = indication
        self.is_valid = False           # Final verdict: is this a real competitor?
        self.confidence = 0.0           # 0.0–1.0
        self.evidence = []              # List of evidence items
        self.ct_trials_found = 0        # Trials on ClinicalTrials.gov
        self.fda_match = False          # Found in FDA database
        self.llm_verdict = None         # Claude's assessment
        self.flags = []                 # Warning flags (e.g., "discontinued", "wrong indication")
        self.sources_checked = []       # Which sources were queried

    def to_dict(self):
        return {
            "drug_name": self.drug_name,
            "indication": self.indication,
            "is_valid": self.is_valid,
            "confidence": round(self.confidence, 2),
            "evidence": self.evidence,
            "ct_trials_found": self.ct_trials_found,
            "fda_match": self.fda_match,
            "llm_verdict": self.llm_verdict,
            "flags": self.flags,
            "sources_checked": self.sources_checked,
        }

    def __repr__(self):
        status = "VALID" if self.is_valid else "INVALID"
        return f"<Validation: {self.drug_name} in {self.indication} → {status} ({self.confidence:.0%})>"


# ─── ClinicalTrials.gov verification ─────────────────────────────────────────

def _verify_via_clinical_trials(drug_name: str, indication: str) -> dict:
    """
    Check ClinicalTrials.gov for active trials of this drug in this indication.
    Returns evidence dict with trial count, phases, and statuses.
    """
    if not API_AVAILABLE:
        return {"source": "ClinicalTrials.gov", "status": "unavailable"}

    try:
        # Search for the drug as an intervention in this condition
        trials = search_clinical_trials(
            condition=indication,
            intervention=drug_name,
            max_results=20,
        )

        if not trials:
            # Try without condition filter (drug might be listed under different condition name)
            trials = search_clinical_trials(
                intervention=drug_name,
                max_results=10,
            )

        active_statuses = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}
        completed_statuses = {"COMPLETED"}
        terminated_statuses = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}

        active_trials = [t for t in trials if t.get("status") in active_statuses]
        completed_trials = [t for t in trials if t.get("status") in completed_statuses]
        terminated_trials = [t for t in trials if t.get("status") in terminated_statuses]

        # Check if any trials match the indication
        indication_lower = indication.lower()
        indication_matched = []
        for t in trials:
            conditions = [c.lower() for c in t.get("conditions", [])]
            if any(indication_lower in c or c in indication_lower for c in conditions):
                indication_matched.append(t)

        # Extract phase info
        phases = set()
        for t in trials:
            phase = t.get("phase", "")
            if phase:
                phases.add(phase)

        return {
            "source": "ClinicalTrials.gov",
            "status": "found" if trials else "not_found",
            "total_trials": len(trials),
            "active_trials": len(active_trials),
            "completed_trials": len(completed_trials),
            "terminated_trials": len(terminated_trials),
            "indication_matched": len(indication_matched),
            "phases": list(phases),
            "trial_ids": [t.get("nct_id") for t in trials[:5]],
            "sponsors": list(set(t.get("sponsor", "") for t in trials if t.get("sponsor")))[:3],
        }

    except Exception as e:
        return {"source": "ClinicalTrials.gov", "status": "error", "error": str(e)}


# ─── FDA verification ────────────────────────────────────────────────────────

def _verify_via_fda(drug_name: str, indication: str) -> dict:
    """
    Check OpenFDA for approved drugs matching this name/indication.
    """
    if not API_AVAILABLE:
        return {"source": "FDA", "status": "unavailable"}

    try:
        results = search_fda_drugs(drug_name=drug_name, max_results=5)

        if not results:
            results = search_fda_drugs(condition=indication, max_results=10)
            # Filter for our drug
            results = [
                r for r in results
                if drug_name.lower() in r.get("generic_name", "").lower()
                or drug_name.lower() in r.get("brand_name", "").lower()
            ]

        return {
            "source": "FDA",
            "status": "found" if results else "not_found",
            "matches": len(results),
            "brand_names": [r.get("brand_name") for r in results[:3]],
            "generic_names": [r.get("generic_name") for r in results[:3]],
        }

    except Exception as e:
        return {"source": "FDA", "status": "error", "error": str(e)}


def _verify_via_global_regulators(drug_name: str, indication: str) -> dict:
    """
    Check non-US regulatory databases to verify drugs from China, Japan, Korea, EU.

    Sources:
    - PMDA (Japan) — Pharmaceuticals and Medical Devices Agency
    - NMPA/CDE (China) — via ClinicalTrials.gov cross-ref + sponsor check
    - EMA (Europe) — European Medicines Agency public database

    This supplements the FDA check so we don't miss Asian/EU-only drugs.
    """
    results = {
        "source": "global_regulators",
        "status": "not_found",
        "matches": [],
    }

    drug_lower = drug_name.lower()

    # ── 1. PMDA (Japan) — search their English drug list ──
    try:
        pmda_url = "https://www.pmda.go.jp/english/search/pageSearch.html"
        # PMDA doesn't have a clean API, but we can check via their search page
        # Use a simpler approach: search ClinicalTrials.gov for Japan-only trials
        resp = requests.get(
            "https://clinicaltrials.gov/api/v2/studies",
            params={
                "format": "json",
                "query.intr": drug_name,
                "filter.advanced": 'AREA[LocationCountry] "Japan"',
                "pageSize": 5,
            },
            headers={"User-Agent": "SatyaBio/1.0"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            jp_trials = data.get("totalCount", 0)
            if jp_trials > 0:
                results["matches"].append({
                    "region": "Japan",
                    "source": "ClinicalTrials.gov (Japan-located)",
                    "trials": jp_trials,
                })
    except Exception:
        pass

    # ── 2. China (NMPA/CDE) — check via ClinicalTrials.gov China trials ──
    try:
        resp = requests.get(
            "https://clinicaltrials.gov/api/v2/studies",
            params={
                "format": "json",
                "query.intr": drug_name,
                "filter.advanced": 'AREA[LocationCountry] "China"',
                "pageSize": 5,
            },
            headers={"User-Agent": "SatyaBio/1.0"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            cn_trials = data.get("totalCount", 0)
            if cn_trials > 0:
                results["matches"].append({
                    "region": "China",
                    "source": "ClinicalTrials.gov (China-located)",
                    "trials": cn_trials,
                })
    except Exception:
        pass

    # ── 3. EMA (Europe) — check via their public product database API ──
    try:
        ema_url = "https://medicines.health.europa.eu/MedSearch/api/v2/search"
        resp = requests.get(
            ema_url,
            params={"searchTerm": drug_name, "page": 1, "pageSize": 5},
            headers={"User-Agent": "SatyaBio/1.0", "Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            ema_count = data.get("totalCount", data.get("total", 0))
            if ema_count > 0:
                results["matches"].append({
                    "region": "EU/EMA",
                    "source": "EMA Product Database",
                    "products": ema_count,
                })
    except Exception:
        pass

    # ── 4. Korea (MFDS) — via ClinicalTrials.gov Korea trials ──
    try:
        resp = requests.get(
            "https://clinicaltrials.gov/api/v2/studies",
            params={
                "format": "json",
                "query.intr": drug_name,
                "filter.advanced": 'AREA[LocationCountry] "Korea, Republic of"',
                "pageSize": 5,
            },
            headers={"User-Agent": "SatyaBio/1.0"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            kr_trials = data.get("totalCount", 0)
            if kr_trials > 0:
                results["matches"].append({
                    "region": "South Korea",
                    "source": "ClinicalTrials.gov (Korea-located)",
                    "trials": kr_trials,
                })
    except Exception:
        pass

    if results["matches"]:
        results["status"] = "found"
        results["regions_found"] = [m["region"] for m in results["matches"]]

    return results


# ─── Drug entity database verification ───────────────────────────────────────

def _verify_via_drug_db(drug_name: str, indication: str) -> dict:
    """
    Check our internal drug entity database for this drug.
    Returns enriched info if found (aliases, targets, phase, etc.)
    """
    if not DRUG_DB_AVAILABLE:
        return {"source": "drug_entities", "status": "unavailable"}

    try:
        info = lookup_drug(drug_name)
        if not info:
            return {"source": "drug_entities", "status": "not_found"}

        # Check if indication matches
        indications = info.get("indications", [])
        indication_lower = indication.lower()
        indication_match = any(
            indication_lower in ind.lower() or ind.lower() in indication_lower
            for ind in indications
        )

        return {
            "source": "drug_entities",
            "status": "found",
            "canonical_name": info.get("canonical_name"),
            "company": info.get("company_name"),
            "ticker": info.get("company_ticker"),
            "phase": info.get("phase_highest"),
            "mechanism": info.get("mechanism"),
            "modality": info.get("modality"),
            "indication_match": indication_match,
            "known_indications": indications[:5],
            "alias_count": len(info.get("aliases", [])),
        }

    except Exception as e:
        return {"source": "drug_entities", "status": "error", "error": str(e)}


# ─── LLM Judge (Claude) ──────────────────────────────────────────────────────

VALIDATOR_PROMPT = """You are a biotech competitive intelligence validator. Your job is to determine whether a drug candidate is a GENUINE active competitor in a specific therapeutic indication.

You will be given:
- A drug name (could be a code name, INN, or brand name)
- A therapeutic indication
- Evidence gathered from ClinicalTrials.gov, FDA, and internal databases

Your task: Determine if this drug is a REAL, ACTIVE competitor in this indication.

VALIDATION CRITERIA (all must be considered):
1. EXISTENCE — Is this a real drug/compound? (not a typo, not a discontinued program, not a device)
2. INDICATION MATCH — Is it actually being developed for this indication? (not just a vaguely related disease)
3. ACTIVE DEVELOPMENT — Is it still in active development? (not terminated, not withdrawn, not acquired-and-shelved)
4. COMPETITIVE RELEVANCE — Would an investor consider this a competitor in this space?
5. MECHANISM FIT — Does the mechanism of action make it a plausible treatment for this indication?

RESPOND IN JSON:
{
  "verdict": "valid" | "invalid" | "uncertain",
  "confidence": 0.0 to 1.0,
  "reasoning": "2-3 sentence explanation",
  "flags": ["list of any concerns, e.g., 'discontinued', 'wrong indication', 'preclinical only'"],
  "corrected_indication": "if the drug is real but for a different indication, note it here",
  "corrected_name": "if the name has a typo or is an alias, provide the canonical name"
}

BE STRICT: It's better to flag a marginal competitor as "uncertain" than to let a false positive through.
Only mark as "valid" if you are confident this is a real, active program in this indication."""


def _verify_via_llm(drug_name: str, indication: str, evidence: list[dict]) -> dict:
    """
    Use Claude as a judge to validate the competitor claim, given evidence from other sources.
    """
    if not CLAUDE_AVAILABLE:
        return {"source": "llm_judge", "status": "unavailable"}

    try:
        client = anthropic.Anthropic()

        # Format evidence for Claude
        evidence_text = ""
        for e in evidence:
            evidence_text += f"\n--- {e.get('source', 'Unknown')} ---\n"
            evidence_text += json.dumps(e, indent=2, default=str)

        user_message = f"""Validate this competitor claim:

DRUG: {drug_name}
INDICATION: {indication}

EVIDENCE GATHERED:
{evidence_text}

Is {drug_name} a genuine active competitor in {indication}?"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=VALIDATOR_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        text = response.content[0].text

        # Parse JSON response
        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text.strip())

        return {
            "source": "llm_judge",
            "status": "completed",
            "verdict": result.get("verdict", "uncertain"),
            "confidence": result.get("confidence", 0.5),
            "reasoning": result.get("reasoning", ""),
            "flags": result.get("flags", []),
            "corrected_indication": result.get("corrected_indication"),
            "corrected_name": result.get("corrected_name"),
        }

    except json.JSONDecodeError:
        return {
            "source": "llm_judge",
            "status": "parse_error",
            "raw_response": text if 'text' in dir() else "",
        }
    except Exception as e:
        return {"source": "llm_judge", "status": "error", "error": str(e)}


# ─── Main validation function ────────────────────────────────────────────────

def validate_competitor(
    drug_name: str,
    indication: str,
    use_llm: bool = True,
    verbose: bool = False,
) -> ValidationResult:
    """
    Full multi-source validation of a drug-indication competitor claim.

    Args:
        drug_name: Drug name (any alias — code name, INN, brand)
        indication: Therapeutic indication to validate against
        use_llm: Whether to use Claude LLM judge (costs API tokens)
        verbose: Print progress

    Returns:
        ValidationResult with verdict, confidence, and evidence
    """
    result = ValidationResult(drug_name, indication)

    if verbose:
        print(f"\n{'='*60}")
        print(f"  Validating: {drug_name} in {indication}")
        print(f"{'='*60}")

    # ── Layer 1: ClinicalTrials.gov ──────────────────────────────────────
    if verbose:
        print("  [1/4] Checking ClinicalTrials.gov...")
    ct_evidence = _verify_via_clinical_trials(drug_name, indication)
    result.evidence.append(ct_evidence)
    result.sources_checked.append("ClinicalTrials.gov")

    if ct_evidence.get("status") == "found":
        result.ct_trials_found = ct_evidence.get("total_trials", 0)
        if ct_evidence.get("active_trials", 0) > 0:
            result.confidence += 0.3  # Active trials = strong signal
        elif ct_evidence.get("completed_trials", 0) > 0:
            result.confidence += 0.15  # Completed trials = moderate signal
        if ct_evidence.get("indication_matched", 0) > 0:
            result.confidence += 0.15  # Indication match
        if ct_evidence.get("terminated_trials", 0) > 0 and ct_evidence.get("active_trials", 0) == 0:
            result.flags.append("all_trials_terminated")
            result.confidence -= 0.2

    if verbose:
        print(f"    → {ct_evidence.get('total_trials', 0)} trials found, "
              f"{ct_evidence.get('active_trials', 0)} active")

    # ── Layer 2: FDA (US) ────────────────────────────────────────────────
    if verbose:
        print("  [2/5] Checking FDA (US)...")
    fda_evidence = _verify_via_fda(drug_name, indication)
    result.evidence.append(fda_evidence)
    result.sources_checked.append("FDA")

    if fda_evidence.get("status") == "found" and fda_evidence.get("matches", 0) > 0:
        result.fda_match = True
        result.confidence += 0.2  # FDA presence = strong signal
        if verbose:
            print(f"    → Found in FDA: {fda_evidence.get('brand_names', [])}")
    elif verbose:
        print(f"    → Not found in FDA")

    # ── Layer 2b: Global regulators (Japan/China/EU/Korea) ───────────────
    if verbose:
        print("  [2b/5] Checking global regulators (PMDA, NMPA, EMA, MFDS)...")
    global_evidence = _verify_via_global_regulators(drug_name, indication)
    result.evidence.append(global_evidence)
    result.sources_checked.append("global_regulators")

    if global_evidence.get("status") == "found":
        regions = global_evidence.get("regions_found", [])
        # Give same weight as FDA — presence in any major regulatory region is a strong signal
        if not result.fda_match:
            result.confidence += 0.2  # Only if not already boosted by FDA
        else:
            result.confidence += 0.05  # Small bonus for multi-region
        if verbose:
            print(f"    → Found in: {', '.join(regions)}")
    elif verbose:
        print(f"    → Not found in global regulators")

    # ── Layer 3: Internal drug database ──────────────────────────────────
    if verbose:
        print("  [3/5] Checking drug entity database...")
    db_evidence = _verify_via_drug_db(drug_name, indication)
    result.evidence.append(db_evidence)
    result.sources_checked.append("drug_entities")

    if db_evidence.get("status") == "found":
        result.confidence += 0.1  # Known drug = some signal
        if db_evidence.get("indication_match"):
            result.confidence += 0.1  # Indication confirmed in our DB
        if verbose:
            print(f"    → Found: {db_evidence.get('canonical_name')} "
                  f"({db_evidence.get('company')}) — Phase {db_evidence.get('phase')}")
    elif verbose:
        print(f"    → Not in drug entity database")

    # ── Layer 4: LLM Judge ───────────────────────────────────────────────
    if use_llm:
        if verbose:
            print("  [4/5] Running LLM judge...")
        llm_evidence = _verify_via_llm(drug_name, indication, result.evidence)
        result.evidence.append(llm_evidence)
        result.sources_checked.append("llm_judge")

        if llm_evidence.get("status") == "completed":
            result.llm_verdict = llm_evidence.get("verdict")
            llm_conf = llm_evidence.get("confidence", 0.5)

            # LLM verdict heavily influences final score
            if result.llm_verdict == "valid":
                result.confidence = max(result.confidence, llm_conf * 0.8)
            elif result.llm_verdict == "invalid":
                result.confidence = min(result.confidence, 1.0 - llm_conf * 0.8)
            # Add LLM flags
            result.flags.extend(llm_evidence.get("flags", []))

            if verbose:
                print(f"    → LLM verdict: {result.llm_verdict} "
                      f"(confidence: {llm_conf:.0%})")
                print(f"    → Reasoning: {llm_evidence.get('reasoning', '')}")

    # ── Final verdict ────────────────────────────────────────────────────
    result.confidence = max(0.0, min(1.0, result.confidence))  # Clamp 0–1

    if result.confidence >= 0.6:
        result.is_valid = True
    elif result.confidence >= 0.3:
        result.is_valid = False  # Uncertain — needs human review
        result.flags.append("needs_review")
    else:
        result.is_valid = False

    if verbose:
        print(f"\n  ── VERDICT: {'VALID' if result.is_valid else 'INVALID'} "
              f"(confidence: {result.confidence:.0%}) ──")
        if result.flags:
            print(f"  Flags: {', '.join(result.flags)}")

    return result


# ─── Batch validation for landscape queries ──────────────────────────────────

def validate_landscape(
    drugs: list[dict],
    indication: str,
    use_llm: bool = True,
    verbose: bool = False,
) -> list[dict]:
    """
    Validate a list of drug candidates for a landscape query.
    Returns the drugs list with validation scores attached.

    Args:
        drugs: List of drug dicts (from entity DB or discovery)
              Each must have at least 'drug_name' or 'canonical_name'
        indication: The therapeutic indication
        use_llm: Whether to use LLM judge
        verbose: Print progress

    Returns:
        Same list with 'validation' key added to each drug dict
    """
    validated = []
    for drug in drugs:
        name = drug.get("canonical_name") or drug.get("drug_name") or drug.get("name", "")
        if not name:
            continue

        result = validate_competitor(name, indication, use_llm=use_llm, verbose=verbose)
        drug["validation"] = result.to_dict()
        drug["validation_score"] = result.confidence
        drug["validation_valid"] = result.is_valid
        validated.append(drug)

    # Sort by validation score (highest first)
    validated.sort(key=lambda x: x.get("validation_score", 0), reverse=True)
    return validated


# ─── Database integration: write validation results to review queue ──────────

def _save_validation_to_queue(result: ValidationResult, entity_id: int = None):
    """
    Save a validation result to the entity_review_queue for human review.
    Only saves if the result is uncertain or invalid.
    """
    if not DB_AVAILABLE or not DRUG_DB_AVAILABLE:
        return

    if result.is_valid and result.confidence >= 0.8:
        return  # High-confidence valid — no review needed

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO entity_review_queue
                (action_type, entity_type, entity_id_1, data, confidence,
                 source_type, source_ref, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "verify",
            "drug",
            entity_id,
            json.dumps(result.to_dict()),
            result.confidence,
            "competitor_validator",
            f"{result.drug_name}|{result.indication}",
            "pending",
        ))
        conn.commit()
    except Exception as e:
        print(f"  ⚠ Could not save validation to review queue: {e}")


# ─── Eval framework: measure precision/recall ────────────────────────────────

def run_eval(test_file: str = None, verbose: bool = False) -> dict:
    """
    Run the validator against a test set and measure precision/recall.

    Test set format (JSON):
    [
      {"drug": "sotorasib", "indication": "NSCLC", "expected": true},
      {"drug": "aspirin", "indication": "NSCLC", "expected": false},
      ...
    ]

    Returns:
        {"precision": float, "recall": float, "f1": float, "details": [...]}
    """
    # Default test set (known ground truth for common landscapes)
    default_tests = [
        # True positives — these ARE real competitors
        {"drug": "sotorasib", "indication": "NSCLC", "expected": True},
        {"drug": "adagrasib", "indication": "NSCLC", "expected": True},
        {"drug": "osimertinib", "indication": "NSCLC", "expected": True},
        {"drug": "pembrolizumab", "indication": "NSCLC", "expected": True},
        {"drug": "nivolumab", "indication": "NSCLC", "expected": True},
        {"drug": "daraxonrasib", "indication": "NSCLC", "expected": True},
        {"drug": "resmetirom", "indication": "NASH", "expected": True},
        {"drug": "semaglutide", "indication": "obesity", "expected": True},
        {"drug": "tirzepatide", "indication": "obesity", "expected": True},
        {"drug": "lecanemab", "indication": "Alzheimer's disease", "expected": True},
        # True negatives — these are NOT competitors in these indications
        {"drug": "sotorasib", "indication": "Alzheimer's disease", "expected": False},
        {"drug": "metformin", "indication": "NSCLC", "expected": False},
        {"drug": "ibuprofen", "indication": "NASH", "expected": False},
        {"drug": "amoxicillin", "indication": "obesity", "expected": False},
        {"drug": "FAKE-DRUG-12345", "indication": "NSCLC", "expected": False},
        {"drug": "lisinopril", "indication": "Alzheimer's disease", "expected": False},
    ]

    if test_file:
        with open(test_file) as f:
            tests = json.loads(f.read())
    else:
        tests = default_tests

    # Run validation on each test case
    true_pos = 0
    false_pos = 0
    true_neg = 0
    false_neg = 0
    details = []

    for i, test in enumerate(tests):
        drug = test["drug"]
        indication = test["indication"]
        expected = test["expected"]

        if verbose:
            print(f"\n[{i+1}/{len(tests)}] Testing: {drug} in {indication} (expected: {expected})")

        result = validate_competitor(drug, indication, use_llm=True, verbose=verbose)
        predicted = result.is_valid

        if predicted and expected:
            true_pos += 1
            outcome = "TP"
        elif predicted and not expected:
            false_pos += 1
            outcome = "FP"
        elif not predicted and not expected:
            true_neg += 1
            outcome = "TN"
        else:
            false_neg += 1
            outcome = "FN"

        details.append({
            "drug": drug,
            "indication": indication,
            "expected": expected,
            "predicted": predicted,
            "confidence": result.confidence,
            "outcome": outcome,
            "flags": result.flags,
        })

        if verbose:
            status = "✓" if outcome in ("TP", "TN") else "✗"
            print(f"  {status} {outcome} — confidence: {result.confidence:.0%}")

    # Calculate metrics
    precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0
    recall = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    metrics = {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "true_positives": true_pos,
        "false_positives": false_pos,
        "true_negatives": true_neg,
        "false_negatives": false_neg,
        "total_tests": len(tests),
        "details": details,
    }

    if verbose:
        print(f"\n{'='*60}")
        print(f"  EVAL RESULTS")
        print(f"{'='*60}")
        print(f"  Precision: {precision:.1%}")
        print(f"  Recall:    {recall:.1%}")
        print(f"  F1 Score:  {f1:.1%}")
        print(f"  TP={true_pos}  FP={false_pos}  TN={true_neg}  FN={false_neg}")

    return metrics


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SatyaBio Competitor Validator")
    parser.add_argument("--drug", type=str, help="Drug name to validate")
    parser.add_argument("--indication", type=str, help="Indication to validate against")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM judge (faster, cheaper)")
    parser.add_argument("--eval", action="store_true", help="Run eval on test set")
    parser.add_argument("--eval-file", type=str, help="Custom test set JSON file")
    parser.add_argument("--validate-queue", action="store_true", help="Validate all pending entities")
    parser.add_argument("--status", action="store_true", help="Show validation stats")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.eval:
        run_eval(test_file=args.eval_file, verbose=True)

    elif args.drug and args.indication:
        result = validate_competitor(
            args.drug,
            args.indication,
            use_llm=not args.no_llm,
            verbose=True,
        )
        print(f"\nResult: {json.dumps(result.to_dict(), indent=2, default=str)}")

    elif args.validate_queue:
        if not DB_AVAILABLE or not DRUG_DB_AVAILABLE:
            print("Database not available — cannot validate queue")
            return

        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, data, source_ref
            FROM entity_review_queue
            WHERE status = 'pending'
              AND action_type IN ('new_drug', 'verify')
            ORDER BY created_at DESC
            LIMIT 50
        """)
        pending = cur.fetchall()
        print(f"Found {len(pending)} pending entities to validate")

        for row in pending:
            ref = row.get("source_ref", "")
            data = row.get("data", {})
            drug_name = data.get("drug_name") or data.get("canonical_name") or ref.split("|")[0]
            indication = data.get("indication") or (ref.split("|")[1] if "|" in ref else "")

            if drug_name and indication:
                result = validate_competitor(
                    drug_name, indication,
                    use_llm=not args.no_llm,
                    verbose=args.verbose,
                )
                # Update the queue entry with validation results
                cur.execute("""
                    UPDATE entity_review_queue
                    SET data = data || %s::jsonb,
                        confidence = %s,
                        status = CASE
                            WHEN %s >= 0.8 THEN 'auto_applied'
                            WHEN %s < 0.3 THEN 'rejected'
                            ELSE 'pending'
                        END
                    WHERE id = %s
                """, (
                    json.dumps({"validation": result.to_dict()}),
                    result.confidence,
                    result.confidence,
                    result.confidence,
                    row["id"],
                ))
                conn.commit()
                print(f"  {result}")

    elif args.status:
        if not DB_AVAILABLE or not DRUG_DB_AVAILABLE:
            print("Database not available")
            return

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT status, COUNT(*) as cnt
            FROM entity_review_queue
            WHERE source_type = 'competitor_validator'
            GROUP BY status
            ORDER BY cnt DESC
        """)
        rows = cur.fetchall()
        print("\nValidation Queue Status:")
        for status, cnt in rows:
            print(f"  {status}: {cnt}")

    else:
        parser.print_help()
        print("\nExamples:")
        print('  python3 competitor_validator.py --drug "sotorasib" --indication "NSCLC" -v')
        print('  python3 competitor_validator.py --eval -v')
        print('  python3 competitor_validator.py --validate-queue')


if __name__ == "__main__":
    main()
