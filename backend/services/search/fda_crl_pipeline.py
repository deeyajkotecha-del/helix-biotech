"""
SatyaBio FDA Complete Response Letter (CRL) Ingestion Pipeline.

This module fetches FDA Complete Response Letters from openFDA, extracts text from PDFs,
chunks and embeds the content, and stores it in Neon pgvector for semantic search.

CHANGES:
  - Fetches CRL metadata from openFDA drugs@fda endpoint
  - Downloads and parses PDFs using PyPDF2 (with text fallback)
  - Chunks at ~800 tokens with 100-token overlap
  - Embeds using voyage-3 (1024-dim vectors)
  - Stores in dedicated fda_crl_documents + fda_crl_chunks tables
  - Hybrid search: semantic (cosine) + keyword (tsvector)
  - Integrates with SatyaBio query router for unified search

Usage:
    from fda_crl_pipeline import ingest_all_crls, search_crl_database, is_crl_available

    # One-time setup
    ingest_all_crls(force_refresh=False)

    # Search
    results = search_crl_database("why was drug X rejected?", top_k=5)
    print(format_crl_for_claude(results))

    # Check availability
    if is_crl_available():
        print("CRL data is ingested and ready")

Requires in .env:
    NEON_DATABASE_URL=postgresql://...
    VOYAGE_API_KEY=your-voyage-key
    OPENFDA_API_KEY=optional-for-higher-rate-limits
"""

import os
import re
import json
import time
import hashlib
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from io import BytesIO
from urllib.parse import urljoin

from dotenv import load_dotenv
load_dotenv()

# External dependencies — graceful degradation if unavailable
try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import sql
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("  WARNING: psycopg2 not available — CRL pipeline disabled")

try:
    import voyageai
    VOYAGEAI_AVAILABLE = True
except ImportError:
    VOYAGEAI_AVAILABLE = False
    print("  WARNING: voyageai not available — embedding disabled")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("  WARNING: requests not available — PDF download disabled")

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    print("  WARNING: PyPDF2 not available — PDF text extraction disabled")

try:
    import nltk
    from nltk.tokenize import sent_tokenize
    NLTK_AVAILABLE = True
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True)
        except Exception:
            NLTK_AVAILABLE = False
except ImportError:
    NLTK_AVAILABLE = False


# ── Config ──
DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
OPENFDA_API_KEY = os.environ.get("OPENFDA_API_KEY", "")

EMBED_MODEL = "voyage-3"
EMBED_BATCH_SIZE = 20  # Voyage AI batch limit
CHUNK_SIZE_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 100

# openFDA endpoints
OPENFDA_DRUGS_ENDPOINT = "https://api.fda.gov/drug/drugsfda.json"
OPENFDA_LABELS_ENDPOINT = "https://api.fda.gov/drug/label.json"

# Global clients (lazy-initialized)
_db_conn = None
_voyage_client = None


# ═══════════════════════════════════════════════════════════════
#  Database Connection Management
# ═══════════════════════════════════════════════════════════════

def _get_db():
    """Get or create a database connection."""
    global _db_conn
    try:
        if _db_conn is not None and not _db_conn.closed:
            _db_conn.cursor().execute("SELECT 1")
            return _db_conn
    except Exception:
        try:
            _db_conn.close()
        except Exception:
            pass
        _db_conn = None

    if not DATABASE_URL or not PSYCOPG2_AVAILABLE:
        return None

    try:
        _db_conn = psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"  ERROR: CRL DB connection failed: {e}")
        _db_conn = None

    return _db_conn


def _get_voyage():
    """Get or create a Voyage AI client."""
    global _voyage_client
    if _voyage_client is None:
        if not VOYAGE_API_KEY or not VOYAGEAI_AVAILABLE:
            return None
        try:
            _voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
        except Exception as e:
            print(f"  ERROR: Voyage AI initialization failed: {e}")
            return None
    return _voyage_client


# ═══════════════════════════════════════════════════════════════
#  Schema Setup
# ═══════════════════════════════════════════════════════════════

def setup_crl_tables():
    """Create FDA CRL tables if they don't exist."""
    conn = _get_db()
    if not conn:
        print("  ERROR: Cannot setup CRL tables — no database connection")
        return False

    try:
        cur = conn.cursor()

        # Create fda_crl_documents table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fda_crl_documents (
                id SERIAL PRIMARY KEY,
                drug_name VARCHAR(300) NOT NULL,
                application_number VARCHAR(50) NOT NULL,
                application_type VARCHAR(50),
                sponsor VARCHAR(300),
                crl_date DATE,
                therapeutic_area VARCHAR(200),
                reason_summary TEXT,
                source_url TEXT,
                full_text TEXT,
                ingested_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(application_number, crl_date)
            )
        """)

        # Create fda_crl_chunks table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fda_crl_chunks (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL REFERENCES fda_crl_documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector(1024),
                metadata JSONB,
                content_tsv tsvector,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Create indices for performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crl_docs_app_num ON fda_crl_documents(application_number)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crl_docs_date ON fda_crl_documents(crl_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crl_chunks_doc_id ON fda_crl_chunks(document_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crl_chunks_embedding ON fda_crl_chunks USING hnsw (embedding vector_cosine_ops)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crl_chunks_tsv ON fda_crl_chunks USING gin (content_tsv)")

        # Enable pgvector extension if not already
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

        conn.commit()
        cur.close()
        print("✓ FDA CRL tables created/verified")
        return True

    except Exception as e:
        print(f"  ERROR: Failed to setup CRL tables: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False


# ═══════════════════════════════════════════════════════════════
#  openFDA Fetching
# ═══════════════════════════════════════════════════════════════

def _fetch_from_openfda(endpoint: str, search_query: str = None, limit: int = 100) -> List[Dict]:
    """
    Fetch records from openFDA endpoint with pagination.
    Returns a list of all matching records.
    """
    if not REQUESTS_AVAILABLE:
        print("  WARNING: requests library not available — skipping openFDA fetch")
        return []

    all_records = []
    skip = 0
    page = 1
    max_pages = 500  # Safety limit

    while page <= max_pages:
        try:
            params = {"limit": limit, "skip": skip}

            if search_query:
                params["search"] = search_query

            if OPENFDA_API_KEY:
                params["api_key"] = OPENFDA_API_KEY

            print(f"  Fetching {endpoint} page {page}...")
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if not results:
                break

            all_records.extend(results)

            # Check if there are more pages
            meta = data.get("meta", {})
            if meta.get("results", {}).get("skip", 0) + len(results) >= meta.get("results", {}).get("total", 0):
                break

            skip += limit
            page += 1

            # Rate limiting: be nice to openFDA (240 req/min without key)
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"  WARNING: openFDA request failed: {e}")
            break
        except Exception as e:
            print(f"  WARNING: Error parsing openFDA response: {e}")
            break

    print(f"  Retrieved {len(all_records)} records from openFDA")
    return all_records


def _extract_crl_data_from_drugs_fda(drug_records: List[Dict]) -> List[Dict]:
    """
    Parse openFDA drugs@fda endpoint response and extract CRL records.

    The endpoint returns submission history. We look for records where:
    - submission_status contains "Complete Response" or similar
    - Or where action_type indicates a CRL
    """
    crl_records = []

    for drug in drug_records:
        drug_name = drug.get("openfda", {}).get("brand_name", [None])[0] or \
                    drug.get("openfda", {}).get("generic_name", [None])[0] or \
                    drug.get("name", "Unknown")

        applications = drug.get("applications", [])

        for app in applications:
            app_number = app.get("application_number", "")
            app_type = app.get("application_type", "")

            submissions = app.get("submissions", [])

            for sub in submissions:
                sub_status = sub.get("submission_status", "").lower()
                sub_type = sub.get("submission_type", "")

                # Look for Complete Response Letters
                if "complete response" in sub_status or "crl" in sub_status:
                    sub_date_str = sub.get("submission_date", "")
                    try:
                        sub_date = datetime.strptime(sub_date_str, "%Y%m%d").date() if sub_date_str else None
                    except (ValueError, TypeError):
                        sub_date = None

                    # Extract reason if available
                    reason = sub.get("submission_class_code_description", "") or \
                            sub.get("review_priority", "")

                    crl_records.append({
                        "drug_name": drug_name,
                        "application_number": app_number,
                        "application_type": app_type,
                        "sponsor": drug.get("sponsor_name", "Unknown"),
                        "crl_date": sub_date,
                        "submission_status": sub_status,
                        "reason_summary": reason,
                        "submission_type": sub_type,
                        "source_url": drug.get("source_url", ""),
                    })

    return crl_records


def _fetch_crl_text_from_pdf(url: str) -> Optional[str]:
    """
    Download a PDF from the given URL and extract text.
    Returns extracted text, or None if download/extraction fails.
    """
    if not url or not REQUESTS_AVAILABLE or not PYPDF2_AVAILABLE:
        return None

    try:
        print(f"    Downloading PDF: {url[:80]}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Try to extract text from PDF
        try:
            pdf_bytes = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_bytes)

            text_parts = []
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            full_text = "\n".join(text_parts)

            if len(full_text.strip()) > 100:  # Only consider if we extracted meaningful text
                print(f"    ✓ Extracted {len(full_text)} chars from PDF")
                return full_text
        except Exception as e:
            print(f"    WARNING: PDF extraction failed: {e}")
            return None

    except Exception as e:
        print(f"    WARNING: PDF download failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
#  Text Chunking
# ═══════════════════════════════════════════════════════════════

def _estimate_tokens(text: str) -> int:
    """Rough token count estimate (1 token ≈ 4 chars for English)."""
    return len(text) // 4


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE_TOKENS, overlap: int = CHUNK_OVERLAP_TOKENS) -> List[str]:
    """
    Split text into chunks of approximately chunk_size tokens with overlap.
    Uses sentence boundaries for cleaner splits.
    """
    if not text or len(text) < 100:
        return [text] if text else []

    chunks = []

    # Try to split by sentences for cleaner boundaries
    if NLTK_AVAILABLE:
        try:
            sentences = sent_tokenize(text)
        except Exception:
            # Fallback to simple sentence split
            sentences = re.split(r'[.!?]+\s+', text)
    else:
        # Fallback: split on sentence-like boundaries
        sentences = re.split(r'[.!?]+\s+', text)

    current_chunk = ""
    current_tokens = 0
    overlap_buffer = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        sentence_tokens = _estimate_tokens(sentence)

        # If adding this sentence would exceed chunk size and we have content
        if current_tokens + sentence_tokens > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())

            # Prepare overlap: take last ~overlap_tokens worth of text
            overlap_tokens_needed = min(overlap, current_tokens)
            overlap_buffer = current_chunk

            # Build the overlap from the end of current chunk
            if overlap_tokens_needed > 0:
                overlap_char_count = overlap_tokens_needed * 4  # Rough estimate
                overlap_text = overlap_buffer[-overlap_char_count:] if len(overlap_buffer) > overlap_char_count else overlap_buffer
            else:
                overlap_text = ""

            current_chunk = overlap_text + " " + sentence
            current_tokens = _estimate_tokens(current_chunk)
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
            current_tokens += sentence_tokens

    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


# ═══════════════════════════════════════════════════════════════
#  Embedding and Storage
# ═══════════════════════════════════════════════════════════════

def _embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts using Voyage AI in batches."""
    vo = _get_voyage()
    if not vo:
        return []

    all_embeddings = []

    # Process in batches
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i:i + EMBED_BATCH_SIZE]

        try:
            result = vo.embed(batch, model=EMBED_MODEL, input_type="document")
            all_embeddings.extend(result.embeddings)
            print(f"    Embedded batch {i // EMBED_BATCH_SIZE + 1}/{(len(texts) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE}")
            time.sleep(0.1)  # Small delay between batches
        except Exception as e:
            print(f"    ERROR: Embedding batch failed: {e}")
            return []

    return all_embeddings


def _store_crl_document(conn, crl_data: Dict) -> Optional[int]:
    """
    Store a CRL document record. Returns the document ID if successful.
    """
    try:
        cur = conn.cursor()

        # Check if already exists
        cur.execute(
            "SELECT id FROM fda_crl_documents WHERE application_number = %s AND crl_date = %s",
            (crl_data.get("application_number"), crl_data.get("crl_date"))
        )
        existing = cur.fetchone()
        if existing:
            print(f"    (Skipping {crl_data.get('application_number')} — already ingested)")
            cur.close()
            return existing[0]

        # Insert new document
        cur.execute("""
            INSERT INTO fda_crl_documents
            (drug_name, application_number, application_type, sponsor, crl_date,
             therapeutic_area, reason_summary, source_url, full_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            crl_data.get("drug_name"),
            crl_data.get("application_number"),
            crl_data.get("application_type"),
            crl_data.get("sponsor"),
            crl_data.get("crl_date"),
            crl_data.get("therapeutic_area", ""),
            crl_data.get("reason_summary", ""),
            crl_data.get("source_url", ""),
            crl_data.get("full_text", ""),
        ))

        doc_id = cur.fetchone()[0]
        conn.commit()
        cur.close()

        print(f"    ✓ Stored document: {crl_data.get('drug_name')} ({crl_data.get('application_number')})")
        return doc_id

    except Exception as e:
        print(f"    ERROR: Failed to store CRL document: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def _store_crl_chunks(conn, doc_id: int, chunks: List[str], crl_data: Dict, embeddings: List[List[float]]):
    """Store chunked content with embeddings."""
    try:
        cur = conn.cursor()

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Create tsvector for keyword search
            # Use to_tsvector with english dictionary for better stemming
            metadata = {
                "drug_name": crl_data.get("drug_name"),
                "application_number": crl_data.get("application_number"),
                "crl_date": str(crl_data.get("crl_date", "")),
                "sponsor": crl_data.get("sponsor"),
                "therapeutic_area": crl_data.get("therapeutic_area", ""),
                "reason_summary": crl_data.get("reason_summary", ""),
                "chunk_index": i,
            }

            cur.execute("""
                INSERT INTO fda_crl_chunks
                (document_id, chunk_index, content, embedding, metadata, content_tsv)
                VALUES (%s, %s, %s, %s, %s, to_tsvector('english', %s))
            """, (
                doc_id,
                i,
                chunk,
                str(embedding),  # pgvector format
                json.dumps(metadata),
                chunk,  # For tsvector generation
            ))

        conn.commit()
        cur.close()
        print(f"    ✓ Stored {len(chunks)} chunks with embeddings")

    except Exception as e:
        print(f"    ERROR: Failed to store CRL chunks: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
#  Main Pipeline
# ═══════════════════════════════════════════════════════════════

def ingest_all_crls(force_refresh: bool = False):
    """
    Main pipeline orchestrator.
    Fetches CRL data from openFDA, processes, and stores in Neon.
    """
    print("\n" + "="*70)
    print("FDA CRL INGESTION PIPELINE")
    print("="*70)

    # Check dependencies
    if not PSYCOPG2_AVAILABLE:
        print("ERROR: psycopg2 required but not available")
        return False

    if not VOYAGE_API_KEY:
        print("ERROR: VOYAGE_API_KEY environment variable not set")
        return False

    # Setup database
    print("\n[1/4] Setting up database schema...")
    if not setup_crl_tables():
        print("ERROR: Failed to setup database tables")
        return False

    # Fetch from openFDA
    print("\n[2/4] Fetching CRL data from openFDA...")
    print("  Trying drugs@fda endpoint...")

    # Fetch complete response letters
    drug_records = _fetch_from_openfda(
        OPENFDA_DRUGS_ENDPOINT,
        search_query="complete response",
        limit=100
    )

    if not drug_records:
        print("  WARNING: No records found from drugs@fda")
        return False

    # Parse for CRL records
    crl_records = _extract_crl_data_from_drugs_fda(drug_records)
    print(f"✓ Identified {len(crl_records)} CRL records")

    if not crl_records:
        print("  No CRL records found")
        return False

    # Process each CRL
    print("\n[3/4] Processing and embedding CRL documents...")
    conn = _get_db()
    if not conn:
        print("ERROR: Database connection failed")
        return False

    processed_count = 0

    for idx, crl_data in enumerate(crl_records[:50], 1):  # Limit to first 50 for demo
        print(f"\n  [{idx}/{len(crl_records[:50])}] {crl_data.get('drug_name')}")

        # Try to fetch full text from PDF if URL available
        full_text = None
        if crl_data.get("source_url"):
            full_text = _fetch_crl_text_from_pdf(crl_data.get("source_url"))

        # Fall back to reason summary if no full text
        if not full_text:
            full_text = crl_data.get("reason_summary", "")

        if not full_text or len(full_text.strip()) < 50:
            print(f"    SKIP: Insufficient text content")
            continue

        crl_data["full_text"] = full_text

        # Store document
        doc_id = _store_crl_document(conn, crl_data)
        if not doc_id:
            continue

        # Chunk the text
        chunks = _chunk_text(full_text)
        if not chunks:
            print(f"    SKIP: Failed to chunk text")
            continue

        print(f"    Chunked into {len(chunks)} pieces")

        # Embed chunks
        embeddings = _embed_texts(chunks)
        if len(embeddings) != len(chunks):
            print(f"    ERROR: Embedding count mismatch (got {len(embeddings)}, expected {len(chunks)})")
            continue

        # Store chunks with embeddings
        _store_crl_chunks(conn, doc_id, chunks, crl_data, embeddings)
        processed_count += 1

    print(f"\n[4/4] Finalization")
    print(f"✓ Processed and ingested {processed_count} CRL documents")

    # Verify
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM fda_crl_documents")
        doc_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fda_crl_chunks")
        chunk_count = cur.fetchone()[0]
        cur.close()
        print(f"✓ Database contains {doc_count} CRL documents with {chunk_count} chunks")
    except Exception as e:
        print(f"WARNING: Failed to verify counts: {e}")

    print("\n" + "="*70)
    print("CRL INGESTION COMPLETE")
    print("="*70 + "\n")

    return True


# ═══════════════════════════════════════════════════════════════
#  Search Functions
# ═══════════════════════════════════════════════════════════════

def is_crl_available() -> bool:
    """Check if CRL data exists in database."""
    conn = _get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM fda_crl_documents")
        count = cur.fetchone()[0]
        cur.close()
        return count > 0
    except Exception:
        return False


def search_crl_database(query: str, top_k: int = 5) -> List[Dict]:
    """
    Hybrid search: semantic (vector) + keyword (tsvector).
    Returns list of dicts with content, metadata, and similarity scores.
    """
    conn = _get_db()
    vo = _get_voyage()

    if not conn or not vo:
        return []

    # Embed the query
    try:
        result = vo.embed([query], model=EMBED_MODEL, input_type="query")
        query_embedding = result.embeddings[0]
    except Exception as e:
        print(f"ERROR: Query embedding failed: {e}")
        return []

    cur = conn.cursor()

    try:
        # Vector search
        cur.execute("""
            SELECT
                c.id, c.content, c.chunk_index,
                d.drug_name, d.application_number, d.crl_date, d.sponsor,
                d.therapeutic_area, d.reason_summary,
                1 - (c.embedding <=> %s::vector) AS vector_score
            FROM fda_crl_chunks c
            JOIN fda_crl_documents d ON c.document_id = d.id
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """, (str(query_embedding), str(query_embedding), top_k * 3))

        vector_results = cur.fetchall()

        # Keyword search (tsvector)
        cur.execute("""
            SELECT
                c.id, c.content, c.chunk_index,
                d.drug_name, d.application_number, d.crl_date, d.sponsor,
                d.therapeutic_area, d.reason_summary,
                ts_rank_cd(c.content_tsv, websearch_to_tsquery('english', %s)) AS keyword_score
            FROM fda_crl_chunks c
            JOIN fda_crl_documents d ON c.document_id = d.id
            WHERE c.content_tsv @@ websearch_to_tsquery('english', %s)
            ORDER BY keyword_score DESC
            LIMIT %s
        """, (query, query, top_k * 2))

        keyword_results = cur.fetchall()
        cur.close()

        # Merge results (prefer vector search, supplement with keyword)
        merged = {}

        for row in vector_results:
            chunk_id = row[0]
            merged[chunk_id] = {
                "content": row[1],
                "chunk_index": row[2],
                "drug_name": row[3],
                "application_number": row[4],
                "crl_date": row[5],
                "sponsor": row[6],
                "therapeutic_area": row[7],
                "reason_summary": row[8],
                "vector_score": float(row[9]),
                "keyword_score": 0.0,
            }

        for row in keyword_results:
            chunk_id = row[0]
            if chunk_id in merged:
                merged[chunk_id]["keyword_score"] = float(row[9])
            else:
                merged[chunk_id] = {
                    "content": row[1],
                    "chunk_index": row[2],
                    "drug_name": row[3],
                    "application_number": row[4],
                    "crl_date": row[5],
                    "sponsor": row[6],
                    "therapeutic_area": row[7],
                    "reason_summary": row[8],
                    "vector_score": 0.0,
                    "keyword_score": float(row[9]),
                }

        # Compute hybrid score
        for chunk_id, result in merged.items():
            result["similarity_score"] = (
                0.7 * result.get("vector_score", 0.0) +
                0.3 * min(result.get("keyword_score", 0.0) / 100.0, 1.0)  # Normalize keyword score
            )

        # Sort by hybrid score and return top_k
        results = sorted(merged.values(), key=lambda x: x["similarity_score"], reverse=True)[:top_k]

        return results

    except Exception as e:
        print(f"ERROR: CRL search failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
#  Formatting for Claude
# ═══════════════════════════════════════════════════════════════

def format_crl_for_claude(crl_results: List[Dict]) -> str:
    """
    Format CRL search results as a context block for Claude synthesis.
    Groups by drug/application for readability.
    """
    if not crl_results:
        return ""

    # Group by application number
    by_app = {}
    for result in crl_results:
        app_num = result.get("application_number", "Unknown")
        if app_num not in by_app:
            by_app[app_num] = {
                "drug_name": result.get("drug_name"),
                "sponsor": result.get("sponsor"),
                "crl_date": result.get("crl_date"),
                "therapeutic_area": result.get("therapeutic_area"),
                "reason_summary": result.get("reason_summary"),
                "chunks": [],
            }
        by_app[app_num]["chunks"].append({
            "content": result.get("content"),
            "similarity": result.get("similarity_score", 0.0),
        })

    parts = []
    parts.append("--- FDA COMPLETE RESPONSE LETTERS (CRL Database) ---")
    parts.append(f"Retrieved {len(crl_results)} relevant CRL references.\n")

    for app_num, data in sorted(by_app.items()):
        parts.append(f"[CRL: {app_num}] {data['drug_name']}")
        parts.append(f"  Sponsor: {data['sponsor']}")
        parts.append(f"  CRL Date: {data['crl_date']}")
        parts.append(f"  Therapeutic Area: {data['therapeutic_area']}")
        parts.append(f"  Reason: {data['reason_summary']}\n")

        for chunk in data["chunks"]:
            similarity_pct = int(chunk.get("similarity", 0.0) * 100)
            parts.append(f"  [Relevance: {similarity_pct}%]")
            parts.append(f"  {chunk.get('content')}\n")

    parts.append("--- END CRL CONTEXT ---")
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
#  Main Entry Point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    # Example: python fda_crl_pipeline.py [force_refresh]
    force_refresh = "--force-refresh" in sys.argv or "--force" in sys.argv

    success = ingest_all_crls(force_refresh=force_refresh)
    sys.exit(0 if success else 1)
