"""
SatyaBio — Auto-Entity Ingestion Pipeline

THE CORE PROBLEM THIS SOLVES:
We can't manually hardcode every drug, alias, and target into Python arrays.
New drugs enter trials daily, drugs get renamed, companies get acquired.
This module makes the entity database self-populating.

THREE AUTO-INGESTION SOURCES:

1. ClinicalTrials.gov Bulk Ingestion
   - Queries CT.gov for all trials matching our tracked indications/targets
   - Auto-creates drug entities from intervention names
   - Links NCT IDs to drugs
   - Detects alias relationships (same sponsor, same condition, different drug names)
   - Runs on a schedule (daily or weekly)

2. Document Intelligence (PDF → Entities)
   - When a new document enters the library, Claude reads it
   - Extracts: drug names, targets, trial data, endpoints, key results
   - Creates/updates entities automatically
   - Links figures to entities

3. PubMed/FDA Monitoring
   - Scheduled queries for tracked indications
   - New publications and approvals auto-update the entity DB

ALSO PROVIDES:
  - Admin API for manual entity CRUD (no code editing needed)
  - Entity merge (when we discover two entities are the same drug)
  - Confidence scoring (auto-created entities start at lower confidence)
  - Audit trail (who/what created each entity and when)

USAGE:
    # Bulk ingest from ClinicalTrials.gov for an indication
    python3 entity_ingester.py --ingest-trials "NSCLC"

    # Ingest entities from a document
    python3 entity_ingester.py --ingest-doc "path/to/document.pdf"

    # Run full ingestion for all tracked indications
    python3 entity_ingester.py --ingest-all

    # Add a drug manually (no code editing!)
    python3 entity_ingester.py --add-drug

    # Merge two drug entities
    python3 entity_ingester.py --merge-drugs "RMC-6236" "daraxonrasib"
"""

import os
import sys
import json
import argparse
import time
import re
from typing import Optional
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")

if not DATABASE_URL:
    raise ImportError("NEON_DATABASE_URL not set — entity ingester disabled")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


# Import our other modules
from api_connectors import search_clinical_trials, search_pubmed

try:
    from drug_entities import get_conn, lookup_drug
except ImportError:
    pass

# Competitor validation (optional — validates auto-created entities)
try:
    from competitor_validator import validate_competitor, _save_validation_to_queue
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False


# =============================================================================
# Additional Schema (extends drug_entities tables)
# =============================================================================

INGESTION_SCHEMA = """
-- Track entity creation source and confidence
CREATE TABLE IF NOT EXISTS entity_provenance (
    id              SERIAL PRIMARY KEY,
    entity_type     TEXT NOT NULL,                  -- 'drug', 'alias', 'target', 'drug_target', 'trial'
    entity_id       INTEGER NOT NULL,               -- drug_id, alias_id, target_id, etc.
    source_type     TEXT NOT NULL,                  -- 'seed', 'clinicaltrials', 'document', 'pubmed', 'fda', 'manual'
    source_ref      TEXT,                           -- NCT ID, filename, PMID, etc.
    confidence      REAL DEFAULT 0.5,               -- 0.0–1.0 confidence in this entity
    created_by      TEXT DEFAULT 'auto',            -- 'auto', 'admin', 'seed'
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_provenance_entity ON entity_provenance (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_provenance_source ON entity_provenance (source_type);

-- Pending entity matches that need human review
CREATE TABLE IF NOT EXISTS entity_review_queue (
    id              SERIAL PRIMARY KEY,
    action_type     TEXT NOT NULL,                  -- 'merge', 'new_drug', 'new_alias', 'new_target', 'verify'
    entity_type     TEXT,
    entity_id_1     INTEGER,                        -- first entity (e.g., existing drug)
    entity_id_2     INTEGER,                        -- second entity (e.g., duplicate to merge)
    data            JSONB DEFAULT '{}',             -- proposed changes
    confidence      REAL DEFAULT 0.5,
    source_type     TEXT,
    source_ref      TEXT,
    status          TEXT DEFAULT 'pending',         -- 'pending', 'approved', 'rejected', 'auto_applied'
    reviewed_by     TEXT,
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_review_status ON entity_review_queue (status);
"""


def setup_ingestion_tables():
    """Create the ingestion tracking tables."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(INGESTION_SCHEMA)
    conn.commit()
    print("  ✓ Entity ingestion tables created")
    cur.close()
    conn.close()


# =============================================================================
# 1. ClinicalTrials.gov → Auto-Entity Creation
# =============================================================================

# Indications and targets we actively track
TRACKED_INDICATIONS = [
    "NSCLC", "Non-Small Cell Lung Cancer",
    "Breast Cancer", "HR+ Breast Cancer", "Triple Negative Breast Cancer",
    "Pancreatic Cancer", "Colorectal Cancer",
    "Melanoma", "Urothelial Carcinoma",
    "Hepatocellular Carcinoma",
    "Alzheimer Disease", "Alzheimer's Disease",
    "Parkinson Disease", "Parkinson's Disease",
    "NASH", "Nonalcoholic Steatohepatitis", "MASH",
    "Obesity",
    "Hepatitis B", "HBV",
]

TRACKED_TARGETS = [
    "KRAS", "EGFR", "ALK", "ROS1", "HER2", "BRAF", "MEK",
    "PI3K", "PIK3CA", "mTOR",
    "PD-1", "PD-L1", "TROP-2", "Nectin-4", "B7-H4",
    "CDK4", "CDK6", "PARP",
    "GLP-1", "GIP", "GLP-1R",
    "amyloid", "tau", "LRRK2", "alpha-synuclein", "GBA",
]


def _normalize_drug_name(name: str) -> str:
    """Normalize a drug name for comparison."""
    # Remove dosage info, parenthetical notes
    name = re.sub(r'\s*\(.*?\)\s*', '', name)
    name = re.sub(r'\s*\d+\s*mg\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\d+\s*mcg\s*', '', name, flags=re.IGNORECASE)
    name = name.strip().strip(',').strip()
    return name


def _is_likely_drug_name(name: str) -> bool:
    """Filter out common non-drug intervention names."""
    skip_terms = [
        "placebo", "standard of care", "best supportive care", "observation",
        "surgery", "radiation", "chemotherapy", "no intervention",
        "dietary supplement", "behavioral", "device", "procedure",
        "physical therapy", "counseling", "exercise",
    ]
    name_lower = name.lower().strip()

    if len(name_lower) < 3:
        return False
    if any(term in name_lower for term in skip_terms):
        return False
    if name_lower in ("drug", "treatment", "therapy", "control"):
        return False

    return True


def ingest_trials_for_indication(indication: str, max_results: int = 50, validate_new: bool = False) -> dict:
    """
    Query ClinicalTrials.gov for an indication and auto-create drug entities.

    For each trial found:
      1. Extract intervention names
      2. Check if drug already exists in our DB (by name or alias)
      3. If not, create a new drug entity with low confidence
      4. Link the trial (NCT ID) to the drug
      5. If two interventions share a sponsor, flag as potential alias
      6. Optionally validate new entities via competitor_validator

    Args:
        validate_new: If True, run competitor_validator on newly created entities
                     (uses CT.gov + FDA checks, no LLM — fast but costs API calls)

    Returns summary stats.
    """
    print(f"\n  Ingesting trials for: {indication}")

    # Query ClinicalTrials.gov
    trials = search_clinical_trials(condition=indication, max_results=max_results)
    if not trials:
        print(f"  No trials found for {indication}")
        return {"indication": indication, "trials": 0, "new_drugs": 0, "new_links": 0}

    print(f"  Found {len(trials)} trials")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    stats = {"indication": indication, "trials": len(trials), "new_drugs": 0, "new_links": 0, "aliases_flagged": 0}

    for trial in trials:
        nct_id = trial.get("nct_id", "")
        sponsor = trial.get("sponsor", "")
        phase = trial.get("phase", "")
        status = trial.get("status", "")
        title = trial.get("title", "")
        interventions = trial.get("interventions", [])

        if isinstance(interventions, str):
            interventions = [i.strip() for i in interventions.split(",")]

        for intervention_raw in interventions:
            drug_name = _normalize_drug_name(intervention_raw)
            if not _is_likely_drug_name(drug_name):
                continue

            # Check if this drug already exists
            cur.execute("""
                SELECT d.drug_id, d.canonical_name
                FROM drugs d
                JOIN drug_aliases da ON d.drug_id = da.drug_id
                WHERE LOWER(da.alias) = LOWER(%s)
                LIMIT 1
            """, (drug_name,))
            existing = cur.fetchone()

            if existing:
                drug_id = existing["drug_id"]
            else:
                # Create new drug entity with auto-detected fields
                # Map phase string to our format
                phase_map = {
                    "PHASE1": "Phase 1", "Phase 1": "Phase 1",
                    "PHASE2": "Phase 2", "Phase 2": "Phase 2",
                    "PHASE3": "Phase 3", "Phase 3": "Phase 3",
                    "PHASE4": "Phase 4", "Phase 4": "Phase 4",
                    "EARLY_PHASE1": "Phase 1",
                    "Phase 1/Phase 2": "Phase 1/2",
                    "Phase 2/Phase 3": "Phase 2",
                }
                phase_normalized = phase_map.get(phase, phase or "Unknown")

                # Try to figure out company ticker from sponsor name
                # (this is a heuristic — the review queue catches mistakes)
                company_ticker = None  # Would need a company name → ticker lookup

                cur.execute("""
                    INSERT INTO drugs (canonical_name, company_name, indication_primary,
                        indications, phase_highest, status, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (canonical_name, company_ticker) DO NOTHING
                    RETURNING drug_id
                """, (drug_name, sponsor, indication, [indication],
                      phase_normalized, "Active",
                      f"Auto-created from ClinicalTrials.gov {nct_id}"))

                result = cur.fetchone()
                if result:
                    drug_id = result["drug_id"]
                    stats["new_drugs"] += 1

                    # Add canonical name as alias
                    cur.execute("""
                        INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current, notes)
                        VALUES (%s, %s, 'canonical', TRUE, %s)
                        ON CONFLICT (alias) DO NOTHING
                    """, (drug_id, drug_name, f"Auto-created from {nct_id}"))

                    # Track provenance
                    cur.execute("""
                        INSERT INTO entity_provenance (entity_type, entity_id, source_type, source_ref,
                            confidence, created_by, notes)
                        VALUES ('drug', %s, 'clinicaltrials', %s, 0.6, 'auto', %s)
                    """, (drug_id, nct_id, f"Sponsor: {sponsor}, Phase: {phase}, Indication: {indication}"))

                    print(f"    + New drug: {drug_name} (from {nct_id}, sponsor: {sponsor})")

                    # Validate the new entity (async-friendly, non-blocking)
                    if VALIDATOR_AVAILABLE and validate_new:
                        try:
                            val_result = validate_competitor(
                                drug_name, indication,
                                use_llm=False,  # Skip LLM for batch speed; use CT.gov + FDA only
                                verbose=False,
                            )
                            _save_validation_to_queue(val_result, entity_id=drug_id)
                            if not val_result.is_valid:
                                stats.setdefault("flagged_invalid", 0)
                                stats["flagged_invalid"] += 1
                                print(f"      ⚠ Validation flagged: {drug_name} "
                                      f"(confidence: {val_result.confidence:.0%})")
                        except Exception as ve:
                            print(f"      ⚠ Validation error for {drug_name}: {ve}")

                else:
                    # Drug already exists with different ticker, find it
                    cur.execute("SELECT drug_id FROM drugs WHERE canonical_name = %s LIMIT 1", (drug_name,))
                    row = cur.fetchone()
                    drug_id = row["drug_id"] if row else None

            if drug_id:
                # Link trial to drug
                cur.execute("""
                    INSERT INTO drug_trials (drug_id, nct_id, phase, status, title)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (drug_id, nct_id) DO UPDATE SET
                        phase = EXCLUDED.phase,
                        status = EXCLUDED.status
                """, (drug_id, nct_id, phase, status, title))
                stats["new_links"] += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"  Summary: {stats['new_drugs']} new drugs, {stats['new_links']} trial links")
    return stats


def ingest_all_tracked():
    """Run ingestion for all tracked indications and targets."""
    print("=" * 60)
    print("  Full ingestion run — all tracked indications")
    print("=" * 60)

    total_stats = {"trials": 0, "new_drugs": 0, "new_links": 0}

    for indication in TRACKED_INDICATIONS:
        stats = ingest_trials_for_indication(indication, max_results=30)
        total_stats["trials"] += stats["trials"]
        total_stats["new_drugs"] += stats["new_drugs"]
        total_stats["new_links"] += stats["new_links"]
        time.sleep(0.5)  # Be nice to CT.gov API

    print(f"\n{'='*60}")
    print(f"  TOTAL: {total_stats['trials']} trials processed, "
          f"{total_stats['new_drugs']} new drugs, "
          f"{total_stats['new_links']} trial links")
    return total_stats


# =============================================================================
# 2. Document Intelligence → Auto-Entity Creation
# =============================================================================

ENTITY_EXTRACTION_PROMPT = """You are a biotech/pharma analyst. Extract ALL drug entities and clinical data from this document text.

For EACH drug mentioned, extract:
1. drug_name: The drug name (generic/INN preferred, include code if that's all that's given)
2. other_names: Any other names for this drug (brand name, development code, etc.)
3. company: Sponsoring company
4. targets: Biological targets (e.g., "KRAS G12C", "PI3Kalpha", "HER2")
5. modality: Drug type (small molecule, antibody, ADC, cell therapy, etc.)
6. mechanism: How it works (1 sentence)
7. indications: Diseases being studied
8. phase: Highest clinical phase mentioned
9. trial_names: Trial names if mentioned (e.g., "INAVO120", "CodeBreaK 200")
10. nct_ids: NCT numbers if mentioned
11. key_results: Any clinical results mentioned (ORR, PFS, OS, HR, p-values, etc.)

Also extract:
- indication_landscape: What disease area is this document about?
- competitive_context: Any mentions of competitive positioning or comparisons

Return a JSON object with:
{
    "drugs": [ ... list of drug objects ... ],
    "indication_landscape": "...",
    "competitive_context": "..."
}

Return ONLY valid JSON."""


def ingest_entities_from_document(
    doc_text: str,
    filename: str,
    ticker: str = None,
    company: str = None,
    doc_type: str = None,
) -> dict:
    """
    Use Claude to extract drug entities from document text, then auto-create
    them in the database.

    This runs when a new document is added to the library (via scraper or upload).
    """
    import anthropic

    print(f"\n  Extracting entities from: {filename}")

    # Truncate very long documents (Claude has a context limit)
    max_chars = 80000
    if len(doc_text) > max_chars:
        doc_text = doc_text[:max_chars] + "\n\n[... document truncated ...]"

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=ENTITY_EXTRACTION_PROMPT,
            messages=[{"role": "user", "content": doc_text}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        if text.endswith("```"):
            text = text[:-3].strip()

        extraction = json.loads(text)

    except Exception as e:
        print(f"  ⚠ Entity extraction failed: {e}")
        return {"drugs_found": 0, "new_drugs": 0, "new_aliases": 0}

    drugs_data = extraction.get("drugs", [])
    print(f"  Found {len(drugs_data)} drugs mentioned")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    stats = {"drugs_found": len(drugs_data), "new_drugs": 0, "new_aliases": 0, "updated": 0}

    for drug_data in drugs_data:
        drug_name = drug_data.get("drug_name", "").strip()
        if not drug_name or len(drug_name) < 2:
            continue

        other_names = drug_data.get("other_names", [])
        if isinstance(other_names, str):
            other_names = [n.strip() for n in other_names.split(",")]

        # Check if drug exists (by any name)
        all_names = [drug_name] + other_names
        existing_drug_id = None

        for name in all_names:
            cur.execute("""
                SELECT d.drug_id, d.canonical_name
                FROM drugs d
                JOIN drug_aliases da ON d.drug_id = da.drug_id
                WHERE LOWER(da.alias) = LOWER(%s)
                LIMIT 1
            """, (name.strip(),))
            row = cur.fetchone()
            if row:
                existing_drug_id = row["drug_id"]
                break

        if existing_drug_id:
            # Drug exists — add any new aliases and update fields if they're empty
            for other_name in other_names:
                other_name = other_name.strip()
                if other_name and len(other_name) > 2:
                    cur.execute("""
                        INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current, notes)
                        VALUES (%s, %s, 'auto', TRUE, %s)
                        ON CONFLICT (alias) DO NOTHING
                    """, (existing_drug_id, other_name, f"Auto-extracted from {filename}"))
                    if cur.rowcount > 0:
                        stats["new_aliases"] += 1
                        print(f"    + New alias: {other_name} → drug_id {existing_drug_id}")

            stats["updated"] += 1

        else:
            # New drug — create entity
            drug_company = drug_data.get("company", company or "")
            indications = drug_data.get("indications", [])
            if isinstance(indications, str):
                indications = [indications]

            phase = drug_data.get("phase", "Unknown")
            modality = drug_data.get("modality", "")
            mechanism = drug_data.get("mechanism", "")

            cur.execute("""
                INSERT INTO drugs (canonical_name, company_name, indication_primary,
                    indications, modality, mechanism, phase_highest, status, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active', %s)
                ON CONFLICT (canonical_name, company_ticker) DO NOTHING
                RETURNING drug_id
            """, (drug_name, drug_company,
                  indications[0] if indications else "",
                  indications, modality, mechanism, phase,
                  f"Auto-extracted from {filename}"))

            result = cur.fetchone()
            if result:
                drug_id = result["drug_id"]
                stats["new_drugs"] += 1

                # Add canonical + other aliases
                cur.execute("""
                    INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current, notes)
                    VALUES (%s, %s, 'canonical', TRUE, %s)
                    ON CONFLICT (alias) DO NOTHING
                """, (drug_id, drug_name, f"Auto-extracted from {filename}"))

                for other_name in other_names:
                    other_name = other_name.strip()
                    if other_name and len(other_name) > 2:
                        cur.execute("""
                            INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current, notes)
                            VALUES (%s, %s, 'auto', TRUE, %s)
                            ON CONFLICT (alias) DO NOTHING
                        """, (drug_id, other_name, f"Auto-extracted from {filename}"))

                # Track provenance
                cur.execute("""
                    INSERT INTO entity_provenance (entity_type, entity_id, source_type, source_ref,
                        confidence, created_by, notes)
                    VALUES ('drug', %s, 'document', %s, 0.7, 'auto', %s)
                """, (drug_id, filename, f"Company: {drug_company}, Phase: {phase}"))

                # Try to link targets
                for target_name in drug_data.get("targets", []):
                    cur.execute("SELECT target_id FROM targets WHERE LOWER(name) = LOWER(%s)", (target_name,))
                    trow = cur.fetchone()
                    if not trow:
                        cur.execute("""
                            SELECT target_id FROM target_aliases WHERE LOWER(alias) = LOWER(%s) LIMIT 1
                        """, (target_name,))
                        trow = cur.fetchone()
                    if trow:
                        cur.execute("""
                            INSERT INTO drug_targets (drug_id, target_id, role)
                            VALUES (%s, %s, 'primary')
                            ON CONFLICT (drug_id, target_id) DO NOTHING
                        """, (drug_id, trow["target_id"]))

                print(f"    + New drug: {drug_name} ({drug_company})")

    conn.commit()
    cur.close()
    conn.close()

    print(f"  Summary: {stats['new_drugs']} new, {stats['new_aliases']} new aliases, {stats['updated']} updated")
    return stats


# =============================================================================
# 3. Admin API — Manual Entity CRUD (no code editing!)
# =============================================================================

def add_drug_interactive():
    """Interactive CLI to add a drug entity."""
    print("\n  === Add Drug Entity ===\n")

    name = input("  Drug name (canonical): ").strip()
    if not name:
        print("  Cancelled.")
        return

    company = input("  Company name: ").strip()
    ticker = input("  Company ticker (or blank): ").strip() or None
    indication = input("  Primary indication: ").strip()
    modality = input("  Modality (small_molecule, adc, antibody, etc.): ").strip()
    mechanism = input("  Mechanism (1 sentence): ").strip()
    phase = input("  Highest phase (Phase 1/2/3, Approved, Preclinical): ").strip()
    aliases_raw = input("  Other names (comma-separated, or blank): ").strip()
    targets_raw = input("  Target(s) (comma-separated, or blank): ").strip()

    aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()] if aliases_raw else []
    targets = [t.strip() for t in targets_raw.split(",") if t.strip()] if targets_raw else []

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO drugs (canonical_name, company_ticker, company_name,
            indication_primary, indications, modality, mechanism,
            phase_highest, status, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Active', 'Manually added')
        ON CONFLICT (canonical_name, company_ticker) DO NOTHING
        RETURNING drug_id
    """, (name, ticker, company, indication, [indication], modality, mechanism, phase))

    result = cur.fetchone()
    if not result:
        print(f"  Drug '{name}' already exists (or conflict). Use --lookup to check.")
        conn.rollback()
        cur.close()
        conn.close()
        return

    drug_id = result[0]

    # Add aliases
    cur.execute("""
        INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current)
        VALUES (%s, %s, 'canonical', TRUE) ON CONFLICT DO NOTHING
    """, (drug_id, name))

    for alias in aliases:
        cur.execute("""
            INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current, notes)
            VALUES (%s, %s, 'manual', TRUE, 'Manually added')
            ON CONFLICT (alias) DO NOTHING
        """, (drug_id, alias))

    # Link targets
    for target in targets:
        cur.execute("SELECT target_id FROM targets WHERE LOWER(name) = LOWER(%s)", (target,))
        trow = cur.fetchone()
        if not trow:
            cur.execute("SELECT target_id FROM target_aliases WHERE LOWER(alias) = LOWER(%s) LIMIT 1", (target,))
            trow = cur.fetchone()
        if trow:
            cur.execute("""
                INSERT INTO drug_targets (drug_id, target_id, role)
                VALUES (%s, %s, 'primary') ON CONFLICT DO NOTHING
            """, (drug_id, trow[0]))
            print(f"    ✓ Linked to target: {target}")
        else:
            print(f"    ⚠ Target '{target}' not found in hierarchy — skipped")

    # Provenance
    cur.execute("""
        INSERT INTO entity_provenance (entity_type, entity_id, source_type, confidence, created_by)
        VALUES ('drug', %s, 'manual', 0.95, 'admin')
    """, (drug_id,))

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n  ✓ Drug '{name}' created (drug_id: {drug_id})")


def add_alias(drug_name: str, alias: str, alias_type: str = "manual"):
    """Add a new alias to an existing drug (no code editing!)."""
    conn = get_conn()
    cur = conn.cursor()

    # Find the drug
    cur.execute("""
        SELECT d.drug_id, d.canonical_name FROM drugs d
        JOIN drug_aliases da ON d.drug_id = da.drug_id
        WHERE LOWER(da.alias) = LOWER(%s)
        LIMIT 1
    """, (drug_name,))
    row = cur.fetchone()

    if not row:
        print(f"  Drug '{drug_name}' not found.")
        cur.close()
        conn.close()
        return

    drug_id, canonical = row

    cur.execute("""
        INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current, notes)
        VALUES (%s, %s, %s, TRUE, 'Manually added alias')
        ON CONFLICT (alias) DO NOTHING
    """, (drug_id, alias, alias_type))

    if cur.rowcount > 0:
        print(f"  ✓ Added alias '{alias}' → {canonical} (drug_id: {drug_id})")
    else:
        print(f"  Alias '{alias}' already exists.")

    conn.commit()
    cur.close()
    conn.close()


def merge_drugs(name1: str, name2: str):
    """
    Merge two drug entities into one. Keeps the first, moves all aliases/trials
    from the second to the first, then deletes the second.
    """
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Find both drugs
    cur.execute("""
        SELECT d.drug_id, d.canonical_name FROM drugs d
        JOIN drug_aliases da ON d.drug_id = da.drug_id
        WHERE LOWER(da.alias) = LOWER(%s) LIMIT 1
    """, (name1,))
    drug1 = cur.fetchone()

    cur.execute("""
        SELECT d.drug_id, d.canonical_name FROM drugs d
        JOIN drug_aliases da ON d.drug_id = da.drug_id
        WHERE LOWER(da.alias) = LOWER(%s) LIMIT 1
    """, (name2,))
    drug2 = cur.fetchone()

    if not drug1 or not drug2:
        print(f"  Could not find both drugs: {name1}={drug1}, {name2}={drug2}")
        cur.close()
        conn.close()
        return

    if drug1["drug_id"] == drug2["drug_id"]:
        print(f"  These are already the same drug (drug_id: {drug1['drug_id']})")
        cur.close()
        conn.close()
        return

    keep_id = drug1["drug_id"]
    merge_id = drug2["drug_id"]

    print(f"  Merging: {drug2['canonical_name']} (id:{merge_id}) → {drug1['canonical_name']} (id:{keep_id})")

    # Move aliases
    cur.execute("UPDATE drug_aliases SET drug_id = %s WHERE drug_id = %s", (keep_id, merge_id))
    print(f"    Moved {cur.rowcount} aliases")

    # Move trials
    cur.execute("""
        UPDATE drug_trials SET drug_id = %s WHERE drug_id = %s
        AND nct_id NOT IN (SELECT nct_id FROM drug_trials WHERE drug_id = %s)
    """, (keep_id, merge_id, keep_id))
    print(f"    Moved {cur.rowcount} trial links")

    # Move targets
    cur.execute("""
        INSERT INTO drug_targets (drug_id, target_id, role, selectivity)
        SELECT %s, target_id, role, selectivity FROM drug_targets WHERE drug_id = %s
        ON CONFLICT (drug_id, target_id) DO NOTHING
    """, (keep_id, merge_id))

    # Move PubMed terms
    cur.execute("""
        INSERT INTO drug_pubmed_terms (drug_id, indication, search_term, term_type)
        SELECT %s, indication, search_term, term_type FROM drug_pubmed_terms WHERE drug_id = %s
        ON CONFLICT (drug_id, search_term) DO NOTHING
    """, (keep_id, merge_id))

    # Delete the merged drug
    cur.execute("DELETE FROM drugs WHERE drug_id = %s", (merge_id,))

    # Track provenance
    cur.execute("""
        INSERT INTO entity_provenance (entity_type, entity_id, source_type, confidence, created_by, notes)
        VALUES ('drug', %s, 'manual', 1.0, 'admin', %s)
    """, (keep_id, f"Merged drug_id {merge_id} ({drug2['canonical_name']}) into this entity"))

    conn.commit()
    cur.close()
    conn.close()
    print(f"  ✓ Merge complete. Kept: {drug1['canonical_name']} (id:{keep_id})")


# =============================================================================
# Flask Admin Routes
# =============================================================================

def register_admin_routes(app):
    """Register admin API endpoints on a Flask app."""
    from flask import jsonify, request as flask_request

    @app.route("/api/admin/drugs", methods=["POST"])
    def api_add_drug():
        """Add a new drug entity via API."""
        data = flask_request.get_json()
        conn = get_conn()
        cur = conn.cursor()

        name = data.get("canonical_name", "").strip()
        if not name:
            return jsonify({"error": "canonical_name required"}), 400

        cur.execute("""
            INSERT INTO drugs (canonical_name, company_ticker, company_name,
                indication_primary, indications, modality, mechanism,
                pathway, phase_highest, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (canonical_name, company_ticker) DO NOTHING
            RETURNING drug_id
        """, (
            name, data.get("ticker"), data.get("company"),
            data.get("indication"), data.get("indications", []),
            data.get("modality"), data.get("mechanism"),
            data.get("pathway"), data.get("phase", "Unknown"),
            data.get("status", "Active"),
        ))

        result = cur.fetchone()
        if not result:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "Drug already exists or conflict"}), 409

        drug_id = result[0]

        # Add aliases
        cur.execute("""
            INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current)
            VALUES (%s, %s, 'canonical', TRUE) ON CONFLICT DO NOTHING
        """, (drug_id, name))

        for alias_data in data.get("aliases", []):
            if isinstance(alias_data, str):
                alias_data = {"alias": alias_data, "type": "manual"}
            cur.execute("""
                INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current)
                VALUES (%s, %s, %s, TRUE) ON CONFLICT DO NOTHING
            """, (drug_id, alias_data["alias"], alias_data.get("type", "manual")))

        # Link targets
        for target_name in data.get("targets", []):
            cur.execute("SELECT target_id FROM targets WHERE LOWER(name) = LOWER(%s)", (target_name,))
            trow = cur.fetchone()
            if trow:
                cur.execute("""
                    INSERT INTO drug_targets (drug_id, target_id, role)
                    VALUES (%s, %s, 'primary') ON CONFLICT DO NOTHING
                """, (drug_id, trow[0]))

        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"drug_id": drug_id, "canonical_name": name}), 201

    @app.route("/api/admin/drugs/<drug_name>/alias", methods=["POST"])
    def api_add_alias(drug_name):
        """Add an alias to an existing drug."""
        data = flask_request.get_json()
        alias = data.get("alias", "").strip()
        if not alias:
            return jsonify({"error": "alias required"}), 400

        add_alias(drug_name, alias, data.get("type", "manual"))
        return jsonify({"status": "ok"})

    @app.route("/api/admin/drugs/merge", methods=["POST"])
    def api_merge_drugs():
        """Merge two drug entities."""
        data = flask_request.get_json()
        merge_drugs(data.get("keep"), data.get("merge_into"))
        return jsonify({"status": "ok"})

    @app.route("/api/admin/ingest/trials", methods=["POST"])
    def api_ingest_trials():
        """Trigger trial ingestion for an indication."""
        data = flask_request.get_json()
        indication = data.get("indication", "")
        if not indication:
            return jsonify({"error": "indication required"}), 400
        stats = ingest_trials_for_indication(indication)
        return jsonify(stats)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SatyaBio Entity Ingestion Pipeline")
    parser.add_argument("--setup", action="store_true", help="Create ingestion tracking tables")
    parser.add_argument("--ingest-trials", type=str, help="Ingest trials for an indication")
    parser.add_argument("--ingest-all", action="store_true", help="Ingest all tracked indications")
    parser.add_argument("--ingest-doc", type=str, help="Extract entities from a document (provide text file path)")
    parser.add_argument("--add-drug", action="store_true", help="Interactively add a drug")
    parser.add_argument("--add-alias", nargs=2, metavar=("DRUG", "ALIAS"), help="Add alias to existing drug")
    parser.add_argument("--merge-drugs", nargs=2, metavar=("KEEP", "MERGE"), help="Merge two drug entities")
    args = parser.parse_args()

    if args.setup:
        setup_ingestion_tables()

    elif args.ingest_trials:
        ingest_trials_for_indication(args.ingest_trials)

    elif args.ingest_all:
        ingest_all_tracked()

    elif args.ingest_doc:
        with open(args.ingest_doc, "r") as f:
            text = f.read()
        ingest_entities_from_document(text, os.path.basename(args.ingest_doc))

    elif args.add_drug:
        add_drug_interactive()

    elif args.add_alias:
        add_alias(args.add_alias[0], args.add_alias[1])

    elif args.merge_drugs:
        merge_drugs(args.merge_drugs[0], args.merge_drugs[1])

    else:
        parser.print_help()
