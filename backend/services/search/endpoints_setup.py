"""
SatyaBio Clinical Endpoints Database — Structured extraction of trial results.

This is the foundation for landscape charts (like the Wedbush EASI-75 chart).
Instead of just text chunks, this stores NUMERIC clinical data points that can
be queried, compared across drugs, and charted.

Schema:
    clinical_endpoints — One row per data point (e.g., "dupilumab SOLO 2 EASI-75 = 48%")

    Links to the existing drugs table via drug_id for mechanism/target enrichment.
    Links to ClinicalTrials.gov via nct_id for trial metadata.

Usage:
    python3 endpoints_setup.py              # Create tables
    python3 endpoints_setup.py --drop       # Drop and recreate (careful!)
    python3 endpoints_setup.py --stats      # Show current data counts

Requires:
    NEON_DATABASE_URL in .env
"""

import os
import sys
import argparse

from dotenv import load_dotenv
load_dotenv()

import psycopg2

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")

SCHEMA_SQL = """
-- ============================================================================
-- Clinical Endpoints: Structured trial results for landscape charting
-- ============================================================================

CREATE TABLE IF NOT EXISTS clinical_endpoints (
    id              SERIAL PRIMARY KEY,

    -- Drug identification
    drug_name       TEXT NOT NULL,               -- canonical drug name (e.g., "dupilumab")
    brand_name      TEXT,                        -- brand if approved (e.g., "DUPIXENT")
    drug_id         INTEGER REFERENCES drugs(drug_id) ON DELETE SET NULL,
    company_ticker  TEXT,                        -- e.g., "REGN"
    company_name    TEXT,                        -- e.g., "Regeneron"

    -- Target / mechanism
    target          TEXT,                        -- e.g., "IL-4Ra/IL-13"
    mechanism       TEXT,                        -- e.g., "anti-IL-4Ra mAb"
    modality        TEXT,                        -- e.g., "mAb", "small_molecule", "ADC"

    -- Trial identification
    trial_name      TEXT,                        -- e.g., "SOLO 2", "DESTINY-Breast03"
    nct_id          TEXT,                        -- e.g., "NCT02277743"
    phase           TEXT,                        -- "Phase 1", "Phase 2", "Phase 3", "Approved"

    -- Indication / disease
    indication      TEXT NOT NULL,               -- e.g., "Atopic Dermatitis", "HER2+ mBC"
    indication_detail TEXT,                      -- e.g., "moderate-to-severe, adult"
    line_of_therapy TEXT,                        -- e.g., "1L", "2L+", "3L+"

    -- The actual endpoint data
    endpoint_name   TEXT NOT NULL,               -- e.g., "EASI-75", "ORR", "mPFS", "mOS"
    endpoint_category TEXT,                      -- "efficacy", "safety", "pk", "biomarker"
    value           REAL,                        -- the numeric value (e.g., 48.0 for 48%)
    value_unit      TEXT DEFAULT '%',            -- "%", "months", "mg/L", "HR"
    value_type      TEXT DEFAULT 'absolute',     -- "absolute", "pbo_adjusted", "vs_comparator"

    -- Comparator data (for pbo-adjusted or head-to-head)
    comparator_name TEXT,                        -- e.g., "placebo", "docetaxel", "T-DM1"
    comparator_value REAL,                       -- comparator arm value
    hazard_ratio    REAL,                        -- HR if applicable
    confidence_interval TEXT,                    -- e.g., "0.28-0.45"
    p_value         TEXT,                        -- e.g., "<0.001", "0.023"

    -- Population
    enrollment      INTEGER,                     -- N enrolled
    evaluable_n     INTEGER,                     -- N evaluable (if different)
    population_note TEXT,                        -- e.g., "ITT", "PD-L1 >= 50%", "HER2-low"

    -- Dosing
    dose            TEXT,                        -- e.g., "300mg Q2W", "5.4mg/kg"
    schedule        TEXT,                        -- e.g., "Q2W", "Q3W", "continuous"

    -- Timepoint
    timepoint       TEXT,                        -- e.g., "Week 16", "12 months", "data cutoff"
    median_followup TEXT,                        -- e.g., "28.4 months"
    data_cutoff     TEXT,                        -- e.g., "2024-06-15"

    -- Source / provenance
    source_type     TEXT,                        -- "publication", "conference", "sec_filing", "fda_label", "ir_deck"
    source_detail   TEXT,                        -- e.g., "ASCO 2024 oral", "NEJM 2023", "10-K FY2024"
    source_url      TEXT,                        -- link to source
    source_ticker   TEXT,                        -- ticker of the document source (may differ from company_ticker)

    -- Metadata
    extracted_from  TEXT,                        -- document filename this was extracted from
    extraction_confidence REAL DEFAULT 1.0,      -- 0-1, how confident the extraction is
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    -- Dedup: same drug + trial + endpoint + value type should be unique
    UNIQUE(drug_name, trial_name, endpoint_name, value_type, dose, timepoint)
);

-- Indexes for fast landscape queries
CREATE INDEX IF NOT EXISTS idx_endpoints_indication ON clinical_endpoints (LOWER(indication));
CREATE INDEX IF NOT EXISTS idx_endpoints_endpoint ON clinical_endpoints (LOWER(endpoint_name));
CREATE INDEX IF NOT EXISTS idx_endpoints_drug ON clinical_endpoints (LOWER(drug_name));
CREATE INDEX IF NOT EXISTS idx_endpoints_target ON clinical_endpoints (LOWER(target));
CREATE INDEX IF NOT EXISTS idx_endpoints_phase ON clinical_endpoints (phase);
CREATE INDEX IF NOT EXISTS idx_endpoints_ticker ON clinical_endpoints (company_ticker);
CREATE INDEX IF NOT EXISTS idx_endpoints_nct ON clinical_endpoints (nct_id);
CREATE INDEX IF NOT EXISTS idx_endpoints_drug_id ON clinical_endpoints (drug_id);

-- Composite indexes for common landscape queries
CREATE INDEX IF NOT EXISTS idx_endpoints_landscape
    ON clinical_endpoints (LOWER(indication), LOWER(endpoint_name), phase);
CREATE INDEX IF NOT EXISTS idx_endpoints_drug_endpoint
    ON clinical_endpoints (LOWER(drug_name), LOWER(endpoint_name));
"""

DROP_SQL = "DROP TABLE IF EXISTS clinical_endpoints CASCADE;"


def setup_tables(conn):
    """Create the clinical_endpoints table."""
    cur = conn.cursor()
    cur.execute(SCHEMA_SQL)
    conn.commit()
    cur.close()
    print("  clinical_endpoints table created (or already exists)")


def drop_tables(conn):
    """Drop the clinical_endpoints table."""
    cur = conn.cursor()
    cur.execute(DROP_SQL)
    conn.commit()
    cur.close()
    print("  clinical_endpoints table dropped")


def show_stats(conn):
    """Show current data counts."""
    cur = conn.cursor()

    try:
        cur.execute("SELECT COUNT(*) FROM clinical_endpoints")
        total = cur.fetchone()[0]
    except Exception:
        print("  Table doesn't exist yet — run without --stats first")
        return

    if total == 0:
        print("  clinical_endpoints: 0 rows (empty)")
        print("  Run endpoint_extractor.py to populate from your document library")
        return

    print(f"  Total endpoints: {total}")

    cur.execute("""
        SELECT indication, COUNT(*), COUNT(DISTINCT drug_name)
        FROM clinical_endpoints
        GROUP BY indication
        ORDER BY COUNT(*) DESC
        LIMIT 15
    """)
    print(f"\n  {'Indication':<35s} {'Endpoints':>10s} {'Drugs':>8s}")
    print(f"  {'-'*35} {'-'*10} {'-'*8}")
    for row in cur.fetchall():
        print(f"  {row[0]:<35s} {row[1]:>10d} {row[2]:>8d}")

    cur.execute("""
        SELECT endpoint_name, COUNT(*), COUNT(DISTINCT drug_name)
        FROM clinical_endpoints
        GROUP BY endpoint_name
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    print(f"\n  {'Endpoint':<25s} {'Data Points':>12s} {'Drugs':>8s}")
    print(f"  {'-'*25} {'-'*12} {'-'*8}")
    for row in cur.fetchall():
        print(f"  {row[0]:<25s} {row[1]:>12d} {row[2]:>8d}")

    cur.execute("SELECT COUNT(DISTINCT company_ticker) FROM clinical_endpoints WHERE company_ticker IS NOT NULL")
    companies = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT drug_name) FROM clinical_endpoints")
    drugs = cur.fetchone()[0]
    print(f"\n  Companies: {companies} | Drugs: {drugs}")

    cur.close()


def main():
    parser = argparse.ArgumentParser(description="SatyaBio Clinical Endpoints DB Setup")
    parser.add_argument("--drop", action="store_true", help="Drop and recreate table")
    parser.add_argument("--stats", action="store_true", help="Show current data counts")
    args = parser.parse_args()

    if not DATABASE_URL:
        print("ERROR: Set NEON_DATABASE_URL in .env")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)

    if args.stats:
        show_stats(conn)
    elif args.drop:
        print("  Dropping and recreating clinical_endpoints...")
        drop_tables(conn)
        setup_tables(conn)
    else:
        setup_tables(conn)

    conn.close()


if __name__ == "__main__":
    main()
