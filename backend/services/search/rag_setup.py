"""
SatyaBio RAG Setup v2 — Upgraded database schema for high-quality retrieval.

CHANGES FROM v1:
  - Vector dimension: 512 -> 1024 (for voyage-3 full model)
  - Index type: IVFFlat -> HNSW (better recall, no training needed)
  - Added: tsvector column for hybrid search (keyword + semantic)
  - Added: GIN index on tsvector for fast full-text search
  - Added: section_title column on chunks (for semantic chunking)

Run once to set up / migrate the database:
    python rag_setup.py

WARNING: This will DROP existing chunks table. Back up first if needed.
         You MUST re-embed all documents after running this.
Requires NEON_DATABASE_URL in your .env file.
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

import psycopg2

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")

if not DATABASE_URL:
    print("\n" + "="*60)
    print("  ERROR: NEON_DATABASE_URL not set!")
    print("  1. Go to https://neon.tech and create a free account")
    print("  2. Create a new project (name it 'satyabio')")
    print("  3. Copy the connection string")
    print("  4. Add to your .env file:")
    print("     NEON_DATABASE_URL=postgresql://user:pass@host/db?sslmode=require")
    print("="*60 + "\n")
    sys.exit(1)


def setup_database():
    """Create all tables needed for upgraded RAG."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # ── Extensions ──
    print("Enabling extensions...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # ── Documents table (unchanged) ──
    print("Creating documents table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id              SERIAL PRIMARY KEY,
            ticker          VARCHAR(10) NOT NULL,
            company_name    VARCHAR(200),
            filename        VARCHAR(500) NOT NULL,
            file_path       TEXT,
            doc_type        VARCHAR(50),
            title           TEXT,
            date            VARCHAR(50),
            word_count      INTEGER,
            page_count      INTEGER,
            file_size_bytes BIGINT,
            embedded_at     TIMESTAMP DEFAULT NOW(),
            UNIQUE(ticker, filename)
        );
    """)

    # ── Chunks table — UPGRADED ──
    print("Creating chunks table (1024-dim vectors, HNSW index, full-text search)...")

    # Drop old table — required because vector dimension is changing from 512 to 1024
    cur.execute("DROP TABLE IF EXISTS chunks CASCADE;")
    cur.execute("DELETE FROM documents;")

    cur.execute("""
        CREATE TABLE chunks (
            id              SERIAL PRIMARY KEY,
            document_id     INTEGER REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index     INTEGER NOT NULL,
            page_number     INTEGER,
            section_title   TEXT,
            content         TEXT NOT NULL,
            token_count     INTEGER,
            embedding       vector(1024),
            content_tsv     tsvector,
            created_at      TIMESTAMP DEFAULT NOW()
        );
    """)

    # ── Indexes ──
    print("Creating HNSW vector index (better recall than IVFFlat)...")
    cur.execute("""
        CREATE INDEX idx_chunks_embedding_hnsw
        ON chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 200);
    """)

    print("Creating GIN index for full-text search (hybrid retrieval)...")
    cur.execute("""
        CREATE INDEX idx_chunks_content_tsv
        ON chunks USING gin (content_tsv);
    """)

    # Auto-update the tsvector column when content is inserted/updated
    cur.execute("""
        CREATE OR REPLACE FUNCTION chunks_tsv_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.content_tsv := to_tsvector('english', COALESCE(NEW.content, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)
    cur.execute("""
        DROP TRIGGER IF EXISTS trg_chunks_tsv ON chunks;
        CREATE TRIGGER trg_chunks_tsv
        BEFORE INSERT OR UPDATE OF content ON chunks
        FOR EACH ROW EXECUTE FUNCTION chunks_tsv_trigger();
    """)

    print("Creating supporting indexes...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_document_id
        ON chunks (document_id);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_ticker
        ON documents (ticker);
    """)

    cur.close()
    conn.close()

    print("\n" + "="*60)
    print("  Database setup complete! (v2 — upgraded)")
    print("  ")
    print("  What's new:")
    print("    - 1024-dim vectors (voyage-3 full model)")
    print("    - HNSW index (better recall than IVFFlat)")
    print("    - Full-text search column (for hybrid retrieval)")
    print("    - Section title tracking (for semantic chunks)")
    print("  ")
    print("  Next step: run embed_documents.py --reembed to re-process all PDFs")
    print("="*60 + "\n")


if __name__ == "__main__":
    setup_database()
