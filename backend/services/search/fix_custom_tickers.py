#!/usr/bin/env python3
"""
Fix PubMed publications with tickers=['CUSTOM'] → tickers=['LXEO']

This script:
  1. Updates the publications table: replaces 'CUSTOM' with 'LXEO' in tickers array
  2. Updates related documents and chunks that were created for 'CUSTOM' searches
  3. Reports what was fixed

Run:
    python3 fix_custom_tickers.py

Requires:
    NEON_DATABASE_URL in .env
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")

if not DATABASE_URL:
    print("ERROR: NEON_DATABASE_URL not set in .env")
    sys.exit(1)


def fix_custom_tickers():
    """Update publications and documents with CUSTOM ticker to LXEO."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        print("\n" + "="*70)
        print("  FIXING PUBMED PUBLICATIONS: CUSTOM → LXEO")
        print("="*70 + "\n")

        # 1. Get publications with CUSTOM ticker
        cur.execute("""
            SELECT id, pmid, title, tickers FROM publications
            WHERE tickers @> ARRAY['CUSTOM']::text[]
        """)
        pubs = cur.fetchall()

        if not pubs:
            print("No publications with CUSTOM ticker found. Nothing to fix.")
            cur.close()
            conn.close()
            return

        print(f"Found {len(pubs)} publications with CUSTOM ticker:\n")
        for i, (pub_id, pmid, title, tickers) in enumerate(pubs, 1):
            print(f"  {i:2d}. PMID {pmid}: {title[:70]}...")

        # 2. Update publications table: replace CUSTOM with LXEO
        print(f"\n\nUpdating publications table...")
        cur.execute("""
            UPDATE publications
            SET tickers = ARRAY_REPLACE(tickers, 'CUSTOM', 'LXEO')
            WHERE tickers @> ARRAY['CUSTOM']::text[]
        """)
        updated_pubs = cur.rowcount
        print(f"  ✓ Updated {updated_pubs} publication records")

        # 3. Get documents with CUSTOM ticker
        cur.execute("""
            SELECT id, ticker, filename FROM documents
            WHERE ticker = 'CUSTOM' AND filename LIKE 'PMID_%'
        """)
        docs = cur.fetchall()

        if docs:
            print(f"\nFound {len(docs)} documents with CUSTOM ticker:")
            doc_ids = [doc[0] for doc in docs]
            for doc_id, ticker, filename in docs:
                print(f"  - {filename} (doc_id: {doc_id})")

            # Update documents ticker from CUSTOM to LXEO
            print(f"\nUpdating {len(docs)} documents...")
            cur.execute("""
                UPDATE documents
                SET ticker = 'LXEO'
                WHERE id = ANY(%s::int[])
            """, (doc_ids,))
            updated_docs = cur.rowcount
            print(f"  ✓ Updated {updated_docs} document records")
        else:
            print(f"\nNo documents with CUSTOM ticker found (may have been created before table existed)")
            updated_docs = 0

        conn.commit()

        # 4. Verify the fix
        cur.execute("""
            SELECT COUNT(*) FROM publications
            WHERE tickers @> ARRAY['CUSTOM']::text[]
        """)
        remaining_custom = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM publications
            WHERE tickers @> ARRAY['LXEO']::text[]
        """)
        with_lxeo = cur.fetchone()[0]

        print(f"\n\nVerification:")
        print(f"  Publications still with CUSTOM: {remaining_custom}")
        print(f"  Publications now with LXEO: {with_lxeo}")

        print("\n" + "="*70)
        print(f"  FIXED {updated_pubs} publications")
        if updated_docs > 0:
            print(f"  FIXED {updated_docs} documents")
        print("="*70 + "\n")

        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        cur.close()
        conn.close()
        return False


if __name__ == "__main__":
    success = fix_custom_tickers()
    sys.exit(0 if success else 1)
