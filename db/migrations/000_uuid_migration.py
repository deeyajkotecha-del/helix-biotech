"""
SatyaBio Migration 000: Convert 5 existing tables from integer PKs to UUID PKs.

Migrates: drugs, targets, drug_aliases, drug_targets, indications
Also updates all FK references in: clinical_endpoints, drug_pubmed_terms,
    drug_trials, disease_targets, target_aliases, document_indications

Run: python db/migrations/000_uuid_migration.py

Requires NEON_DATABASE_URL in .env
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

import psycopg2

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: NEON_DATABASE_URL not set")
    sys.exit(1)


def run_migration():
    conn = psycopg2.connect(DATABASE_URL)
    # We'll use autocommit=False and explicit BEGIN/COMMIT for transaction safety
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("=== UUID Migration: Converting 5 tables from integer PKs to UUID PKs ===\n")

        # Ensure uuid-ossp extension
        conn.autocommit = True
        cur.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
        conn.autocommit = False

        # Check if migration already ran (drugs.drug_id is already UUID)
        cur.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'drugs' AND column_name = 'drug_id'
        """)
        row = cur.fetchone()
        if row and row[0] == 'uuid':
            print("Migration already applied (drugs.drug_id is UUID). Skipping.")
            return
        if not row:
            print("ERROR: drugs table not found or drug_id column missing.")
            sys.exit(1)

        print(f"Current drugs.drug_id type: {row[0]} — will convert to UUID\n")

        # ================================================================
        # PHASE 1: Add UUID columns to all primary key tables
        # ================================================================
        print("Phase 1: Adding UUID columns...")

        cur.execute("ALTER TABLE drugs ADD COLUMN drug_id_new UUID DEFAULT uuid_generate_v4()")
        cur.execute("UPDATE drugs SET drug_id_new = uuid_generate_v4()")
        print("  drugs.drug_id_new: populated")

        cur.execute("ALTER TABLE targets ADD COLUMN target_id_new UUID DEFAULT uuid_generate_v4()")
        cur.execute("UPDATE targets SET target_id_new = uuid_generate_v4()")
        print("  targets.target_id_new: populated")

        cur.execute("ALTER TABLE drug_aliases ADD COLUMN alias_id_new UUID DEFAULT uuid_generate_v4()")
        cur.execute("UPDATE drug_aliases SET alias_id_new = uuid_generate_v4()")
        print("  drug_aliases.alias_id_new: populated")

        cur.execute("ALTER TABLE drug_targets ADD COLUMN id_new UUID DEFAULT uuid_generate_v4()")
        cur.execute("UPDATE drug_targets SET id_new = uuid_generate_v4()")
        print("  drug_targets.id_new: populated")

        cur.execute("ALTER TABLE indications ADD COLUMN indication_id UUID DEFAULT uuid_generate_v4()")
        cur.execute("UPDATE indications SET indication_id = uuid_generate_v4()")
        print("  indications.indication_id: populated")

        # ================================================================
        # PHASE 2: Add UUID FK columns to all referencing tables and backfill
        # ================================================================
        print("\nPhase 2: Adding UUID FK columns and backfilling...")

        # --- Tables referencing drugs.drug_id ---
        for ref_table in ['clinical_endpoints', 'drug_aliases', 'drug_pubmed_terms', 'drug_targets', 'drug_trials']:
            cur.execute(f"ALTER TABLE {ref_table} ADD COLUMN drug_id_new UUID")
            cur.execute(f"""
                UPDATE {ref_table} rt SET drug_id_new = d.drug_id_new
                FROM drugs d WHERE rt.drug_id = d.drug_id
            """)
            cur.execute(f"SELECT COUNT(*) FROM {ref_table} WHERE drug_id IS NOT NULL AND drug_id_new IS NULL")
            orphans = cur.fetchone()[0]
            if orphans > 0:
                print(f"  WARNING: {ref_table} has {orphans} rows with drug_id not found in drugs — setting NULL")
            print(f"  {ref_table}.drug_id_new: backfilled")

        # --- Tables referencing targets.target_id ---
        for ref_table in ['disease_targets', 'drug_targets', 'target_aliases']:
            cur.execute(f"ALTER TABLE {ref_table} ADD COLUMN target_id_new UUID")
            cur.execute(f"""
                UPDATE {ref_table} rt SET target_id_new = t.target_id_new
                FROM targets t WHERE rt.target_id = t.target_id
            """)
            print(f"  {ref_table}.target_id_new: backfilled")

        # --- targets.parent_id (self-reference) ---
        cur.execute("ALTER TABLE targets ADD COLUMN parent_id_new UUID")
        cur.execute("""
            UPDATE targets child SET parent_id_new = parent.target_id_new
            FROM targets parent WHERE child.parent_id = parent.target_id
        """)
        print("  targets.parent_id_new: backfilled (self-reference)")

        # --- document_indications.indication_id → indications.id ---
        cur.execute("ALTER TABLE document_indications ADD COLUMN indication_id_new UUID")
        cur.execute("""
            UPDATE document_indications di SET indication_id_new = ind.indication_id
            FROM indications ind WHERE di.indication_id = ind.id
        """)
        print("  document_indications.indication_id_new: backfilled")

        # ================================================================
        # PHASE 3: Drop all FK constraints
        # ================================================================
        print("\nPhase 3: Dropping FK constraints...")

        fk_drops = [
            ("clinical_endpoints", "clinical_endpoints_drug_id_fkey"),
            ("drug_aliases", "drug_aliases_drug_id_fkey"),
            ("drug_pubmed_terms", "drug_pubmed_terms_drug_id_fkey"),
            ("drug_targets", "drug_targets_drug_id_fkey"),
            ("drug_targets", "drug_targets_target_id_fkey"),
            ("drug_trials", "drug_trials_drug_id_fkey"),
            ("disease_targets", "disease_targets_target_id_fkey"),
            ("target_aliases", "target_aliases_target_id_fkey"),
            ("targets", "targets_parent_id_fkey"),
            ("document_indications", "document_indications_indication_id_fkey"),
        ]
        for table, constraint in fk_drops:
            cur.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint}")
            print(f"  Dropped {constraint}")

        # ================================================================
        # PHASE 4: Drop PK constraints and UNIQUE constraints
        # ================================================================
        print("\nPhase 4: Dropping PK and UNIQUE constraints...")

        # PKs
        cur.execute("ALTER TABLE drugs DROP CONSTRAINT drugs_pkey")
        cur.execute("ALTER TABLE targets DROP CONSTRAINT targets_pkey")
        cur.execute("ALTER TABLE drug_aliases DROP CONSTRAINT drug_aliases_pkey")
        cur.execute("ALTER TABLE drug_targets DROP CONSTRAINT drug_targets_pkey")
        cur.execute("ALTER TABLE indications DROP CONSTRAINT indications_pkey")
        print("  Dropped all 5 PKs")

        # UNIQUEs that involve changing columns
        cur.execute("ALTER TABLE drugs DROP CONSTRAINT IF EXISTS drugs_canonical_name_company_ticker_key")
        cur.execute("ALTER TABLE drug_targets DROP CONSTRAINT IF EXISTS drug_targets_drug_id_target_id_key")
        print("  Dropped UNIQUE constraints on changing columns")

        # Indexes on changing columns
        cur.execute("DROP INDEX IF EXISTS idx_drug_aliases_drug_id")
        cur.execute("DROP INDEX IF EXISTS idx_drug_targets_drug")
        cur.execute("DROP INDEX IF EXISTS idx_drug_targets_target")
        print("  Dropped indexes on changing columns")

        # ================================================================
        # PHASE 5: Drop old integer columns, rename UUID columns
        # ================================================================
        print("\nPhase 5: Swapping columns (drop integer, rename UUID)...")

        # --- drugs ---
        cur.execute("ALTER TABLE drugs DROP COLUMN drug_id")
        cur.execute("ALTER TABLE drugs RENAME COLUMN drug_id_new TO drug_id")
        cur.execute("ALTER TABLE drugs ALTER COLUMN drug_id SET NOT NULL")
        cur.execute("ALTER TABLE drugs ALTER COLUMN drug_id SET DEFAULT uuid_generate_v4()")
        print("  drugs.drug_id: now UUID")

        # --- targets ---
        cur.execute("ALTER TABLE targets DROP COLUMN target_id")
        cur.execute("ALTER TABLE targets RENAME COLUMN target_id_new TO target_id")
        cur.execute("ALTER TABLE targets ALTER COLUMN target_id SET NOT NULL")
        cur.execute("ALTER TABLE targets ALTER COLUMN target_id SET DEFAULT uuid_generate_v4()")
        cur.execute("ALTER TABLE targets DROP COLUMN parent_id")
        cur.execute("ALTER TABLE targets RENAME COLUMN parent_id_new TO parent_id")
        print("  targets.target_id + parent_id: now UUID")

        # --- drug_aliases ---
        cur.execute("ALTER TABLE drug_aliases DROP COLUMN alias_id")
        cur.execute("ALTER TABLE drug_aliases RENAME COLUMN alias_id_new TO alias_id")
        cur.execute("ALTER TABLE drug_aliases ALTER COLUMN alias_id SET NOT NULL")
        cur.execute("ALTER TABLE drug_aliases ALTER COLUMN alias_id SET DEFAULT uuid_generate_v4()")
        cur.execute("ALTER TABLE drug_aliases DROP COLUMN drug_id")
        cur.execute("ALTER TABLE drug_aliases RENAME COLUMN drug_id_new TO drug_id")
        cur.execute("ALTER TABLE drug_aliases ALTER COLUMN drug_id SET NOT NULL")
        print("  drug_aliases.alias_id + drug_id: now UUID")

        # --- drug_targets ---
        cur.execute("ALTER TABLE drug_targets DROP COLUMN id")
        cur.execute("ALTER TABLE drug_targets DROP COLUMN drug_id")
        cur.execute("ALTER TABLE drug_targets RENAME COLUMN drug_id_new TO drug_id")
        cur.execute("ALTER TABLE drug_targets ALTER COLUMN drug_id SET NOT NULL")
        cur.execute("ALTER TABLE drug_targets DROP COLUMN target_id")
        cur.execute("ALTER TABLE drug_targets RENAME COLUMN target_id_new TO target_id")
        cur.execute("ALTER TABLE drug_targets ALTER COLUMN target_id SET NOT NULL")
        # Drop the old id_new column too — switching to composite PK
        cur.execute("ALTER TABLE drug_targets DROP COLUMN id_new")
        print("  drug_targets.drug_id + target_id: now UUID (composite PK)")

        # --- indications ---
        # Rename old 'id' to drop it, keep new 'indication_id'
        cur.execute("ALTER TABLE indications DROP COLUMN id")
        cur.execute("ALTER TABLE indications ALTER COLUMN indication_id SET NOT NULL")
        cur.execute("ALTER TABLE indications ALTER COLUMN indication_id SET DEFAULT uuid_generate_v4()")
        print("  indications.indication_id: now UUID (was 'id')")

        # --- referencing tables: swap FK columns ---
        for ref_table in ['clinical_endpoints', 'drug_pubmed_terms', 'drug_trials']:
            cur.execute(f"ALTER TABLE {ref_table} DROP COLUMN drug_id")
            cur.execute(f"ALTER TABLE {ref_table} RENAME COLUMN drug_id_new TO drug_id")
            print(f"  {ref_table}.drug_id: now UUID")

        for ref_table in ['disease_targets', 'target_aliases']:
            cur.execute(f"ALTER TABLE {ref_table} DROP COLUMN target_id")
            cur.execute(f"ALTER TABLE {ref_table} RENAME COLUMN target_id_new TO target_id")
            cur.execute(f"ALTER TABLE {ref_table} ALTER COLUMN target_id SET NOT NULL")
            print(f"  {ref_table}.target_id: now UUID")

        cur.execute("ALTER TABLE document_indications DROP COLUMN indication_id")
        cur.execute("ALTER TABLE document_indications RENAME COLUMN indication_id_new TO indication_id")
        print("  document_indications.indication_id: now UUID")

        # ================================================================
        # PHASE 6: Re-add PK, UNIQUE, FK constraints and indexes
        # ================================================================
        print("\nPhase 6: Re-adding constraints and indexes...")

        # PKs
        cur.execute("ALTER TABLE drugs ADD PRIMARY KEY (drug_id)")
        cur.execute("ALTER TABLE targets ADD PRIMARY KEY (target_id)")
        cur.execute("ALTER TABLE drug_aliases ADD PRIMARY KEY (alias_id)")
        cur.execute("ALTER TABLE drug_targets ADD PRIMARY KEY (drug_id, target_id)")
        cur.execute("ALTER TABLE indications ADD PRIMARY KEY (indication_id)")
        print("  PKs: all 5 restored")

        # UNIQUEs
        cur.execute("ALTER TABLE drugs ADD CONSTRAINT drugs_canonical_name_company_ticker_key UNIQUE (canonical_name, company_ticker)")
        cur.execute("ALTER TABLE drug_targets ADD CONSTRAINT drug_targets_drug_id_target_id_key UNIQUE (drug_id, target_id)")
        # targets_name_key and drug_aliases_alias_key and indications_slug_key were on non-PK columns, should still exist
        print("  UNIQUEs: restored")

        # FKs
        cur.execute("ALTER TABLE clinical_endpoints ADD CONSTRAINT clinical_endpoints_drug_id_fkey FOREIGN KEY (drug_id) REFERENCES drugs(drug_id)")
        cur.execute("ALTER TABLE drug_aliases ADD CONSTRAINT drug_aliases_drug_id_fkey FOREIGN KEY (drug_id) REFERENCES drugs(drug_id) ON DELETE CASCADE")
        cur.execute("ALTER TABLE drug_pubmed_terms ADD CONSTRAINT drug_pubmed_terms_drug_id_fkey FOREIGN KEY (drug_id) REFERENCES drugs(drug_id) ON DELETE CASCADE")
        cur.execute("ALTER TABLE drug_targets ADD CONSTRAINT drug_targets_drug_id_fkey FOREIGN KEY (drug_id) REFERENCES drugs(drug_id) ON DELETE CASCADE")
        cur.execute("ALTER TABLE drug_targets ADD CONSTRAINT drug_targets_target_id_fkey FOREIGN KEY (target_id) REFERENCES targets(target_id) ON DELETE CASCADE")
        cur.execute("ALTER TABLE drug_trials ADD CONSTRAINT drug_trials_drug_id_fkey FOREIGN KEY (drug_id) REFERENCES drugs(drug_id) ON DELETE CASCADE")
        cur.execute("ALTER TABLE disease_targets ADD CONSTRAINT disease_targets_target_id_fkey FOREIGN KEY (target_id) REFERENCES targets(target_id)")
        cur.execute("ALTER TABLE target_aliases ADD CONSTRAINT target_aliases_target_id_fkey FOREIGN KEY (target_id) REFERENCES targets(target_id) ON DELETE CASCADE")
        cur.execute("ALTER TABLE targets ADD CONSTRAINT targets_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES targets(target_id)")
        cur.execute("ALTER TABLE document_indications ADD CONSTRAINT document_indications_indication_id_fkey FOREIGN KEY (indication_id) REFERENCES indications(indication_id)")
        print("  FKs: all 10 restored")

        # Indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_drug_aliases_drug_id ON drug_aliases(drug_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_drug_targets_drug ON drug_targets(drug_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_drug_targets_target ON drug_targets(target_id)")
        print("  Indexes: restored")

        # Drop leftover sequences (no longer needed)
        for seq in ['drugs_drug_id_seq', 'targets_target_id_seq', 'drug_aliases_alias_id_seq',
                     'drug_targets_id_seq', 'indications_id_seq']:
            cur.execute(f"DROP SEQUENCE IF EXISTS {seq}")
        print("  Sequences: cleaned up")

        # ================================================================
        # PHASE 7: Verify
        # ================================================================
        print("\nPhase 7: Verifying...")

        for tbl, pk_col in [('drugs', 'drug_id'), ('targets', 'target_id'),
                             ('drug_aliases', 'alias_id'), ('indications', 'indication_id')]:
            cur.execute(f"""
                SELECT data_type FROM information_schema.columns
                WHERE table_name = '{tbl}' AND column_name = '{pk_col}'
            """)
            dtype = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            count = cur.fetchone()[0]
            status = "✅" if dtype == "uuid" else "❌"
            print(f"  {status} {tbl}.{pk_col}: {dtype} ({count} rows)")

        # drug_targets composite PK check
        cur.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'drug_targets' AND column_name = 'drug_id'
        """)
        dtype = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM drug_targets")
        count = cur.fetchone()[0]
        status = "✅" if dtype == "uuid" else "❌"
        print(f"  {status} drug_targets.drug_id: {dtype} ({count} rows)")

        # Verify FK integrity
        print("\n  FK integrity checks:")
        checks = [
            ("drug_aliases", "drug_id", "drugs", "drug_id"),
            ("drug_targets", "drug_id", "drugs", "drug_id"),
            ("drug_targets", "target_id", "targets", "target_id"),
            ("drug_trials", "drug_id", "drugs", "drug_id"),
            ("disease_targets", "target_id", "targets", "target_id"),
            ("target_aliases", "target_id", "targets", "target_id"),
        ]
        for ref_tbl, ref_col, parent_tbl, parent_col in checks:
            cur.execute(f"""
                SELECT COUNT(*) FROM {ref_tbl} r
                WHERE r.{ref_col} IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM {parent_tbl} p WHERE p.{parent_col} = r.{ref_col})
            """)
            orphans = cur.fetchone()[0]
            status = "✅" if orphans == 0 else f"❌ ({orphans} orphans)"
            print(f"    {status} {ref_tbl}.{ref_col} → {parent_tbl}.{parent_col}")

        # COMMIT
        conn.commit()
        print("\n✅ UUID MIGRATION COMPLETE — all changes committed")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ MIGRATION FAILED — rolled back: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
