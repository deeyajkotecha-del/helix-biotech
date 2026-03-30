"""
SatyaBio FDA Regulatory Decisions Pipeline (Approvals + CRLs).

This module fetches BOTH FDA approvals and Complete Response Letters from openFDA,
extracts text from PDFs, chunks and embeds the content, and stores it in Neon pgvector
for semantic search. This gives the trial forecaster a complete regulatory picture —
not just rejections, but also approvals in the same therapeutic area.

CHANGES (v2 — expanded from CRL-only):
  - Now captures BOTH approvals and CRLs from openFDA drugs@fda endpoint
  - New `fda_decisions` + `fda_decision_chunks` tables with `decision_type` field
  - decision_type = "approval" | "crl" | "tentative_approval" | "withdrawn"
  - Backward-compatible: old CRL-only functions still work as aliases
  - search_fda_decisions() can filter by decision_type or search all
  - format_fda_decisions_for_claude() groups by decision type for clearer context
  - Regulatory scorecards: "3 approved, 1 CRL in [therapeutic area]"

Usage:
    from fda_crl_pipeline import ingest_all_fda_decisions, search_fda_decisions, is_fda_data_available

    # Ingest all FDA decisions (approvals + CRLs)
    ingest_all_fda_decisions(force_refresh=False)

    # Search across all decision types
    results = search_fda_decisions("KRAS inhibitor NSCLC", top_k=5)

    # Search only CRLs (backward compatible)
    results = search_crl_database("why was drug X rejected?", top_k=5)

    # Get regulatory scorecard for a therapeutic area
    scorecard = get_regulatory_scorecard("non-small cell lung cancer")

    # Check availability
    if is_fda_data_available():
        print("FDA decision data is ingested and ready")

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

def setup_fda_tables():
    """Create FDA decision tables (approvals + CRLs) if they don't exist."""
    conn = _get_db()
    if not conn:
        print("  ERROR: Cannot setup FDA tables — no database connection")
        return False

    try:
        cur = conn.cursor()

        # Enable pgvector extension if not already
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # ── Legacy CRL tables (keep for backward compat) ──
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

        # ── NEW: Unified FDA decisions table (approvals + CRLs + more) ──
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fda_decisions (
                id SERIAL PRIMARY KEY,
                drug_name VARCHAR(300) NOT NULL,
                generic_name VARCHAR(300),
                application_number VARCHAR(50) NOT NULL,
                application_type VARCHAR(50),
                sponsor VARCHAR(300),
                decision_date DATE,
                decision_type VARCHAR(50) NOT NULL,
                therapeutic_area VARCHAR(200),
                indication TEXT,
                reason_summary TEXT,
                review_priority VARCHAR(100),
                source_url TEXT,
                full_text TEXT,
                ingested_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(application_number, decision_date, decision_type)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS fda_decision_chunks (
                id SERIAL PRIMARY KEY,
                decision_id INTEGER NOT NULL REFERENCES fda_decisions(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector(1024),
                metadata JSONB,
                content_tsv tsvector,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Indices for legacy tables
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crl_docs_app_num ON fda_crl_documents(application_number)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crl_docs_date ON fda_crl_documents(crl_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crl_chunks_doc_id ON fda_crl_chunks(document_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crl_chunks_embedding ON fda_crl_chunks USING hnsw (embedding vector_cosine_ops)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crl_chunks_tsv ON fda_crl_chunks USING gin (content_tsv)")

        # Indices for new unified tables
        cur.execute("CREATE INDEX IF NOT EXISTS idx_fda_dec_app_num ON fda_decisions(application_number)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_fda_dec_date ON fda_decisions(decision_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_fda_dec_type ON fda_decisions(decision_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_fda_dec_drug ON fda_decisions(drug_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_fda_dec_sponsor ON fda_decisions(sponsor)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_fda_dec_chunks_id ON fda_decision_chunks(decision_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_fda_dec_chunks_emb ON fda_decision_chunks USING hnsw (embedding vector_cosine_ops)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_fda_dec_chunks_tsv ON fda_decision_chunks USING gin (content_tsv)")

        conn.commit()
        cur.close()
        print("✓ FDA decision tables created/verified (approvals + CRLs)")
        return True

    except Exception as e:
        print(f"  ERROR: Failed to setup FDA tables: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False


# Backward compat alias
setup_crl_tables = setup_fda_tables


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


def _classify_submission_status(sub_status: str) -> Optional[str]:
    """
    Classify a submission status string into a decision type.
    Returns: "approval", "crl", "tentative_approval", "withdrawn", or None if not a decision.
    """
    status_lower = sub_status.lower()

    if "complete response" in status_lower or "crl" in status_lower:
        return "crl"
    elif status_lower in ("ap", "approved") or "approv" in status_lower:
        return "approval"
    elif "tentative" in status_lower:
        return "tentative_approval"
    elif "withdraw" in status_lower:
        return "withdrawn"

    return None


def _extract_fda_decisions_from_drugs_fda(
    drug_records: List[Dict],
    decision_types: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Parse openFDA drugs@fda endpoint response and extract FDA decisions.

    Args:
        drug_records: Raw records from the openFDA API
        decision_types: Filter to specific types, e.g. ["approval", "crl"].
                       None = capture all decision types.

    The endpoint returns submission history per application. We extract:
    - Approvals (submission_status contains "AP" or "Approved")
    - CRLs / rejections (submission_status contains "Complete Response")
    - Tentative approvals
    - Withdrawals
    """
    decisions = []

    for drug in drug_records:
        brand_name = drug.get("openfda", {}).get("brand_name", [None])[0] or ""
        generic_name = drug.get("openfda", {}).get("generic_name", [None])[0] or ""
        drug_name = brand_name or generic_name or drug.get("name", "Unknown")

        # Try to extract therapeutic area from product fields
        pharm_class = drug.get("openfda", {}).get("pharm_class_epc", [])
        therapeutic_area = pharm_class[0] if pharm_class else ""

        # Get indication from product descriptions
        indication = ""
        products = drug.get("products", [])
        if products:
            indication = products[0].get("active_ingredients", [{}])[0].get("name", "") if products[0].get("active_ingredients") else ""

        applications = drug.get("applications", []) if isinstance(drug.get("applications"), list) else []

        # openFDA drugs@fda can return data at the top level too
        if not applications:
            applications = [drug] if drug.get("application_number") else []

        for app in applications:
            app_number = app.get("application_number", "")
            app_type = app.get("application_type", "")

            submissions = app.get("submissions", [])

            for sub in submissions:
                sub_status = sub.get("submission_status", "")
                if not sub_status:
                    continue

                decision_type = _classify_submission_status(sub_status)
                if decision_type is None:
                    continue

                # Filter if requested
                if decision_types and decision_type not in decision_types:
                    continue

                sub_date_str = sub.get("submission_status_date", "") or sub.get("submission_date", "")
                try:
                    sub_date = datetime.strptime(sub_date_str, "%Y%m%d").date() if sub_date_str else None
                except (ValueError, TypeError):
                    sub_date = None

                # Extract review priority and reason
                review_priority = sub.get("review_priority", "")
                reason = sub.get("submission_class_code_description", "") or review_priority

                decisions.append({
                    "drug_name": drug_name,
                    "generic_name": generic_name,
                    "application_number": app_number,
                    "application_type": app_type,
                    "sponsor": app.get("sponsor_name", "") or drug.get("sponsor_name", "Unknown"),
                    "decision_date": sub_date,
                    "decision_type": decision_type,
                    "therapeutic_area": therapeutic_area,
                    "indication": indication,
                    "review_priority": review_priority,
                    "submission_status": sub_status,
                    "reason_summary": reason,
                    "submission_type": sub.get("submission_type", ""),
                    "source_url": drug.get("source_url", ""),
                })

    return decisions


# Backward compat: old name still works
def _extract_crl_data_from_drugs_fda(drug_records: List[Dict]) -> List[Dict]:
    """Legacy wrapper — extracts only CRL records."""
    decisions = _extract_fda_decisions_from_drugs_fda(drug_records, decision_types=["crl"])
    # Map new field names back to old format
    for d in decisions:
        d["crl_date"] = d.get("decision_date")
    return decisions


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


def _store_fda_decision(conn, decision_data: Dict) -> Optional[int]:
    """
    Store an FDA decision record in the unified table. Returns the decision ID if successful.
    """
    try:
        cur = conn.cursor()

        # Check if already exists
        cur.execute(
            "SELECT id FROM fda_decisions WHERE application_number = %s AND decision_date = %s AND decision_type = %s",
            (decision_data.get("application_number"), decision_data.get("decision_date"), decision_data.get("decision_type"))
        )
        existing = cur.fetchone()
        if existing:
            cur.close()
            return existing[0]

        # Insert new decision
        cur.execute("""
            INSERT INTO fda_decisions
            (drug_name, generic_name, application_number, application_type, sponsor,
             decision_date, decision_type, therapeutic_area, indication,
             reason_summary, review_priority, source_url, full_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            decision_data.get("drug_name"),
            decision_data.get("generic_name", ""),
            decision_data.get("application_number"),
            decision_data.get("application_type"),
            decision_data.get("sponsor"),
            decision_data.get("decision_date"),
            decision_data.get("decision_type"),
            decision_data.get("therapeutic_area", ""),
            decision_data.get("indication", ""),
            decision_data.get("reason_summary", ""),
            decision_data.get("review_priority", ""),
            decision_data.get("source_url", ""),
            decision_data.get("full_text", ""),
        ))

        decision_id = cur.fetchone()[0]
        conn.commit()
        cur.close()

        dtype = decision_data.get("decision_type", "").upper()
        print(f"    ✓ Stored [{dtype}]: {decision_data.get('drug_name')} ({decision_data.get('application_number')})")
        return decision_id

    except Exception as e:
        print(f"    ERROR: Failed to store FDA decision: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def _store_decision_chunks(conn, decision_id: int, chunks: List[str], decision_data: Dict, embeddings: List[List[float]]):
    """Store chunked content with embeddings in the unified chunks table."""
    try:
        cur = conn.cursor()

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            metadata = {
                "drug_name": decision_data.get("drug_name"),
                "application_number": decision_data.get("application_number"),
                "decision_date": str(decision_data.get("decision_date", "")),
                "decision_type": decision_data.get("decision_type"),
                "sponsor": decision_data.get("sponsor"),
                "therapeutic_area": decision_data.get("therapeutic_area", ""),
                "indication": decision_data.get("indication", ""),
                "reason_summary": decision_data.get("reason_summary", ""),
                "chunk_index": i,
            }

            cur.execute("""
                INSERT INTO fda_decision_chunks
                (decision_id, chunk_index, content, embedding, metadata, content_tsv)
                VALUES (%s, %s, %s, %s, %s, to_tsvector('english', %s))
            """, (
                decision_id,
                i,
                chunk,
                str(embedding),
                json.dumps(metadata),
                chunk,
            ))

        conn.commit()
        cur.close()
        print(f"    ✓ Stored {len(chunks)} chunks with embeddings")

    except Exception as e:
        print(f"    ERROR: Failed to store decision chunks: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


# Legacy wrappers for backward compatibility
def _store_crl_document(conn, crl_data: Dict) -> Optional[int]:
    """Legacy wrapper — stores into old CRL table."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM fda_crl_documents WHERE application_number = %s AND crl_date = %s",
            (crl_data.get("application_number"), crl_data.get("crl_date"))
        )
        existing = cur.fetchone()
        if existing:
            cur.close()
            return existing[0]

        cur.execute("""
            INSERT INTO fda_crl_documents
            (drug_name, application_number, application_type, sponsor, crl_date,
             therapeutic_area, reason_summary, source_url, full_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            crl_data.get("drug_name"), crl_data.get("application_number"),
            crl_data.get("application_type"), crl_data.get("sponsor"),
            crl_data.get("crl_date"), crl_data.get("therapeutic_area", ""),
            crl_data.get("reason_summary", ""), crl_data.get("source_url", ""),
            crl_data.get("full_text", ""),
        ))
        doc_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return doc_id
    except Exception as e:
        print(f"    ERROR: Failed to store CRL document: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def _store_crl_chunks(conn, doc_id: int, chunks: List[str], crl_data: Dict, embeddings: List[List[float]]):
    """Legacy wrapper — stores into old CRL chunks table."""
    try:
        cur = conn.cursor()
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
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
            """, (doc_id, i, chunk, str(embedding), json.dumps(metadata), chunk))
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"    ERROR: Failed to store CRL chunks: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
#  Main Pipeline
# ═══════════════════════════════════════════════════════════════

def ingest_all_fda_decisions(force_refresh: bool = False, max_records: int = 200):
    """
    Main pipeline orchestrator — fetches BOTH approvals and CRLs from openFDA.
    Stores in the unified fda_decisions table.

    Args:
        force_refresh: If True, re-fetch even if data exists
        max_records: Maximum number of decisions to process per type
    """
    print("\n" + "="*70)
    print("FDA REGULATORY DECISIONS PIPELINE (Approvals + CRLs)")
    print("="*70)

    # Check dependencies
    if not PSYCOPG2_AVAILABLE:
        print("ERROR: psycopg2 required but not available")
        return False

    if not VOYAGE_API_KEY:
        print("ERROR: VOYAGE_API_KEY environment variable not set")
        return False

    # Setup database
    print("\n[1/5] Setting up database schema...")
    if not setup_fda_tables():
        print("ERROR: Failed to setup database tables")
        return False

    conn = _get_db()
    if not conn:
        print("ERROR: Database connection failed")
        return False

    # ── PHASE 1: Fetch CRLs (rejections) ──
    print("\n[2/5] Fetching CRL (rejection) data from openFDA...")
    crl_drug_records = _fetch_from_openfda(
        OPENFDA_DRUGS_ENDPOINT,
        search_query='submissions.submission_status:"Complete+Response"',
        limit=100
    )

    crl_decisions = []
    if crl_drug_records:
        crl_decisions = _extract_fda_decisions_from_drugs_fda(crl_drug_records, decision_types=["crl"])
        print(f"  ✓ Found {len(crl_decisions)} CRL records")
    else:
        # Fallback: broader search
        print("  Trying broader CRL search...")
        crl_drug_records = _fetch_from_openfda(OPENFDA_DRUGS_ENDPOINT, search_query="complete response", limit=100)
        if crl_drug_records:
            crl_decisions = _extract_fda_decisions_from_drugs_fda(crl_drug_records, decision_types=["crl"])
            print(f"  ✓ Found {len(crl_decisions)} CRL records (fallback)")

    # ── PHASE 2: Fetch Approvals ──
    print("\n[3/5] Fetching approval data from openFDA...")

    # The drugs@fda endpoint indexes by submission_status
    # "AP" is the standard code for approved applications
    approval_drug_records = _fetch_from_openfda(
        OPENFDA_DRUGS_ENDPOINT,
        search_query='submissions.submission_status:"AP"',
        limit=100
    )

    approval_decisions = []
    if approval_drug_records:
        approval_decisions = _extract_fda_decisions_from_drugs_fda(approval_drug_records, decision_types=["approval"])
        print(f"  ✓ Found {len(approval_decisions)} approval records")

    # Also try tentative approvals and withdrawals
    other_records = _fetch_from_openfda(
        OPENFDA_DRUGS_ENDPOINT,
        search_query='submissions.submission_status:"TA"',
        limit=100
    )
    other_decisions = []
    if other_records:
        other_decisions = _extract_fda_decisions_from_drugs_fda(other_records, decision_types=["tentative_approval"])
        print(f"  ✓ Found {len(other_decisions)} tentative approval records")

    # Combine all decisions
    all_decisions = crl_decisions + approval_decisions + other_decisions
    print(f"\n  TOTAL: {len(all_decisions)} FDA decisions identified")
    print(f"    Approvals: {len(approval_decisions)}")
    print(f"    CRLs: {len(crl_decisions)}")
    print(f"    Tentative: {len(other_decisions)}")

    if not all_decisions:
        print("  No FDA decision records found")
        return False

    # ── PHASE 3: Process and embed ──
    print(f"\n[4/5] Processing and embedding FDA decisions (max {max_records})...")

    processed = {"approval": 0, "crl": 0, "tentative_approval": 0, "withdrawn": 0}

    for idx, decision in enumerate(all_decisions[:max_records], 1):
        dtype = decision.get("decision_type", "unknown")
        dname = decision.get("drug_name", "Unknown")
        print(f"\n  [{idx}/{min(len(all_decisions), max_records)}] [{dtype.upper()}] {dname}")

        # Try to fetch full text from PDF if URL available
        full_text = None
        if decision.get("source_url"):
            full_text = _fetch_crl_text_from_pdf(decision.get("source_url"))

        # Fall back to reason summary / build a metadata-based text block
        if not full_text:
            parts = []
            if decision.get("drug_name"):
                parts.append(f"Drug: {decision['drug_name']}")
            if decision.get("generic_name"):
                parts.append(f"Generic: {decision['generic_name']}")
            if decision.get("sponsor"):
                parts.append(f"Sponsor: {decision['sponsor']}")
            if decision.get("decision_type"):
                parts.append(f"Decision: {decision['decision_type']}")
            if decision.get("decision_date"):
                parts.append(f"Date: {decision['decision_date']}")
            if decision.get("therapeutic_area"):
                parts.append(f"Therapeutic Area: {decision['therapeutic_area']}")
            if decision.get("indication"):
                parts.append(f"Indication: {decision['indication']}")
            if decision.get("review_priority"):
                parts.append(f"Review Priority: {decision['review_priority']}")
            if decision.get("reason_summary"):
                parts.append(f"Summary: {decision['reason_summary']}")
            full_text = ". ".join(parts)

        if not full_text or len(full_text.strip()) < 30:
            print(f"    SKIP: Insufficient text content")
            continue

        decision["full_text"] = full_text

        # Store in unified table
        decision_id = _store_fda_decision(conn, decision)
        if not decision_id:
            continue

        # Chunk the text
        chunks = _chunk_text(full_text)
        if not chunks:
            print(f"    SKIP: Failed to chunk text")
            continue

        # Embed chunks
        embeddings = _embed_texts(chunks)
        if len(embeddings) != len(chunks):
            print(f"    ERROR: Embedding count mismatch (got {len(embeddings)}, expected {len(chunks)})")
            continue

        # Store chunks with embeddings
        _store_decision_chunks(conn, decision_id, chunks, decision, embeddings)
        processed[dtype] = processed.get(dtype, 0) + 1

    # ── PHASE 4: Also populate legacy CRL tables ──
    print(f"\n  Also populating legacy CRL tables...")
    legacy_count = 0
    for decision in all_decisions[:max_records]:
        if decision.get("decision_type") != "crl":
            continue
        decision["crl_date"] = decision.get("decision_date")
        doc_id = _store_crl_document(conn, decision)
        if doc_id and decision.get("full_text"):
            chunks = _chunk_text(decision["full_text"])
            if chunks:
                embeddings = _embed_texts(chunks)
                if len(embeddings) == len(chunks):
                    _store_crl_chunks(conn, doc_id, chunks, decision, embeddings)
                    legacy_count += 1
    print(f"  ✓ Populated {legacy_count} legacy CRL records")

    # ── Finalization ──
    print(f"\n[5/5] Finalization")
    print(f"✓ Processed FDA decisions:")
    for dtype, count in processed.items():
        if count > 0:
            print(f"    {dtype}: {count}")

    # Verify
    try:
        cur = conn.cursor()
        cur.execute("SELECT decision_type, COUNT(*) FROM fda_decisions GROUP BY decision_type ORDER BY decision_type")
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM fda_decision_chunks")
        chunk_count = cur.fetchone()[0]
        cur.close()
        print(f"\n✓ Database contents:")
        for row in rows:
            print(f"    {row[0]}: {row[1]} documents")
        print(f"    Total chunks: {chunk_count}")
    except Exception as e:
        print(f"WARNING: Failed to verify counts: {e}")

    print("\n" + "="*70)
    print("FDA DECISIONS INGESTION COMPLETE")
    print("="*70 + "\n")

    return True


# Backward compat alias
def ingest_all_crls(force_refresh: bool = False):
    """Legacy wrapper — now ingests all FDA decisions (approvals + CRLs)."""
    return ingest_all_fda_decisions(force_refresh=force_refresh)


# ═══════════════════════════════════════════════════════════════
#  Search Functions
# ═══════════════════════════════════════════════════════════════

def is_fda_data_available() -> bool:
    """Check if FDA decision data exists in the unified table."""
    conn = _get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM fda_decisions")
        count = cur.fetchone()[0]
        cur.close()
        return count > 0
    except Exception:
        return False


def is_crl_available() -> bool:
    """Check if CRL data exists (checks both unified and legacy tables)."""
    conn = _get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        # Check unified table first
        try:
            cur.execute("SELECT COUNT(*) FROM fda_decisions WHERE decision_type = 'crl'")
            count = cur.fetchone()[0]
            if count > 0:
                cur.close()
                return True
        except Exception:
            pass

        # Fall back to legacy table
        cur.execute("SELECT COUNT(*) FROM fda_crl_documents")
        count = cur.fetchone()[0]
        cur.close()
        return count > 0
    except Exception:
        return False


def search_fda_decisions(
    query: str,
    top_k: int = 5,
    decision_type: Optional[str] = None,
) -> List[Dict]:
    """
    Hybrid search across all FDA decisions (approvals + CRLs).

    Args:
        query: Search query string
        top_k: Number of results to return
        decision_type: Optional filter — "approval", "crl", "tentative_approval", "withdrawn", or None for all

    Returns list of dicts with content, metadata, decision_type, and similarity scores.
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
        # Build type filter clause
        type_clause = ""
        type_params = []
        if decision_type:
            type_clause = "AND d.decision_type = %s"
            type_params = [decision_type]

        # Vector search
        cur.execute(f"""
            SELECT
                c.id, c.content, c.chunk_index,
                d.drug_name, d.generic_name, d.application_number,
                d.decision_date, d.decision_type, d.sponsor,
                d.therapeutic_area, d.indication, d.reason_summary,
                d.review_priority,
                1 - (c.embedding <=> %s::vector) AS vector_score
            FROM fda_decision_chunks c
            JOIN fda_decisions d ON c.decision_id = d.id
            WHERE 1=1 {type_clause}
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """, [str(query_embedding)] + type_params + [str(query_embedding), top_k * 3])

        vector_results = cur.fetchall()

        # Keyword search
        cur.execute(f"""
            SELECT
                c.id, c.content, c.chunk_index,
                d.drug_name, d.generic_name, d.application_number,
                d.decision_date, d.decision_type, d.sponsor,
                d.therapeutic_area, d.indication, d.reason_summary,
                d.review_priority,
                ts_rank_cd(c.content_tsv, websearch_to_tsquery('english', %s)) AS keyword_score
            FROM fda_decision_chunks c
            JOIN fda_decisions d ON c.decision_id = d.id
            WHERE c.content_tsv @@ websearch_to_tsquery('english', %s) {type_clause}
            ORDER BY keyword_score DESC
            LIMIT %s
        """, [query, query] + type_params + [top_k * 2])

        keyword_results = cur.fetchall()
        cur.close()

        # Merge results
        merged = {}

        def _row_to_dict(row, score_type: str, score_val: float):
            return {
                "content": row[1],
                "chunk_index": row[2],
                "drug_name": row[3],
                "generic_name": row[4],
                "application_number": row[5],
                "decision_date": row[6],
                "decision_type": row[7],
                "sponsor": row[8],
                "therapeutic_area": row[9],
                "indication": row[10],
                "reason_summary": row[11],
                "review_priority": row[12],
                "vector_score": score_val if score_type == "vector" else 0.0,
                "keyword_score": score_val if score_type == "keyword" else 0.0,
                # Also provide backward-compat field
                "crl_date": row[6],
            }

        for row in vector_results:
            chunk_id = row[0]
            merged[chunk_id] = _row_to_dict(row, "vector", float(row[13]))

        for row in keyword_results:
            chunk_id = row[0]
            if chunk_id in merged:
                merged[chunk_id]["keyword_score"] = float(row[13])
            else:
                merged[chunk_id] = _row_to_dict(row, "keyword", float(row[13]))

        # Compute hybrid score
        for chunk_id, res in merged.items():
            res["similarity_score"] = (
                0.7 * res.get("vector_score", 0.0) +
                0.3 * min(res.get("keyword_score", 0.0) / 100.0, 1.0)
            )

        results = sorted(merged.values(), key=lambda x: x["similarity_score"], reverse=True)[:top_k]
        return results

    except Exception as e:
        print(f"ERROR: FDA decision search failed: {e}")
        # Fall back to legacy CRL search
        return _legacy_crl_search(query, top_k, conn, vo)


def _legacy_crl_search(query: str, top_k: int, conn, vo) -> List[Dict]:
    """Fallback search using legacy CRL tables."""
    try:
        result = vo.embed([query], model=EMBED_MODEL, input_type="query")
        query_embedding = result.embeddings[0]
    except Exception:
        return []

    cur = conn.cursor()
    try:
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
        """, (str(query_embedding), str(query_embedding), top_k))

        results = []
        for row in cur.fetchall():
            results.append({
                "content": row[1],
                "chunk_index": row[2],
                "drug_name": row[3],
                "application_number": row[4],
                "crl_date": row[5],
                "decision_date": row[5],
                "decision_type": "crl",
                "sponsor": row[6],
                "therapeutic_area": row[7],
                "reason_summary": row[8],
                "similarity_score": float(row[9]),
            })
        cur.close()
        return results
    except Exception:
        return []


def search_crl_database(query: str, top_k: int = 5) -> List[Dict]:
    """Backward-compatible CRL-only search. Now searches unified table with CRL filter."""
    # Try unified table first, fall back to legacy
    results = search_fda_decisions(query, top_k=top_k, decision_type="crl")
    if not results:
        # Fall back to legacy CRL table
        conn = _get_db()
        vo = _get_voyage()
        if conn and vo:
            results = _legacy_crl_search(query, top_k, conn, vo)
    return results


def get_regulatory_scorecard(therapeutic_area: str) -> Dict[str, Any]:
    """
    Get a regulatory scorecard for a therapeutic area.
    Returns counts of approvals, CRLs, tentative approvals, and withdrawals,
    plus recent decision history.

    Example return:
    {
        "therapeutic_area": "non-small cell lung cancer",
        "total_decisions": 15,
        "approvals": 10,
        "crls": 3,
        "tentative_approvals": 2,
        "approval_rate": 0.67,
        "recent_decisions": [...]
    }
    """
    conn = _get_db()
    if not conn:
        return {"total_decisions": 0, "approval_rate": 0.0}

    try:
        cur = conn.cursor()

        # Count by decision type for this therapeutic area
        cur.execute("""
            SELECT decision_type, COUNT(*)
            FROM fda_decisions
            WHERE LOWER(therapeutic_area) LIKE %s
               OR LOWER(indication) LIKE %s
               OR LOWER(drug_name) LIKE %s
            GROUP BY decision_type
        """, (
            f"%{therapeutic_area.lower()}%",
            f"%{therapeutic_area.lower()}%",
            f"%{therapeutic_area.lower()}%",
        ))
        type_counts = dict(cur.fetchall())

        total = sum(type_counts.values())
        approvals = type_counts.get("approval", 0)
        crls = type_counts.get("crl", 0)
        tentative = type_counts.get("tentative_approval", 0)

        # Get recent decisions
        cur.execute("""
            SELECT drug_name, decision_type, decision_date, sponsor, reason_summary
            FROM fda_decisions
            WHERE LOWER(therapeutic_area) LIKE %s
               OR LOWER(indication) LIKE %s
            ORDER BY decision_date DESC NULLS LAST
            LIMIT 10
        """, (f"%{therapeutic_area.lower()}%", f"%{therapeutic_area.lower()}%"))

        recent = []
        for row in cur.fetchall():
            recent.append({
                "drug_name": row[0],
                "decision_type": row[1],
                "decision_date": str(row[2]) if row[2] else "",
                "sponsor": row[3],
                "reason_summary": row[4],
            })

        cur.close()

        return {
            "therapeutic_area": therapeutic_area,
            "total_decisions": total,
            "approvals": approvals,
            "crls": crls,
            "tentative_approvals": tentative,
            "withdrawn": type_counts.get("withdrawn", 0),
            "approval_rate": approvals / max(approvals + crls, 1),
            "recent_decisions": recent,
        }

    except Exception as e:
        print(f"ERROR: Scorecard query failed: {e}")
        return {"total_decisions": 0, "approval_rate": 0.0}


# ═══════════════════════════════════════════════════════════════
#  Formatting for Claude
# ═══════════════════════════════════════════════════════════════

def format_fda_decisions_for_claude(results: List[Dict], include_scorecard: bool = False) -> str:
    """
    Format FDA decision search results as a context block for Claude synthesis.
    Groups by decision type (approvals vs CRLs) then by drug/application.
    """
    if not results:
        return ""

    # Group by decision_type, then by application number
    by_type: Dict[str, Dict[str, Any]] = {}
    for result in results:
        dtype = result.get("decision_type", "unknown")
        app_num = result.get("application_number", "Unknown")
        key = f"{dtype}|{app_num}"

        if key not in by_type:
            by_type[key] = {
                "drug_name": result.get("drug_name"),
                "generic_name": result.get("generic_name", ""),
                "sponsor": result.get("sponsor"),
                "decision_date": result.get("decision_date") or result.get("crl_date"),
                "decision_type": dtype,
                "application_number": app_num,
                "therapeutic_area": result.get("therapeutic_area"),
                "indication": result.get("indication", ""),
                "reason_summary": result.get("reason_summary"),
                "review_priority": result.get("review_priority", ""),
                "chunks": [],
            }
        by_type[key]["chunks"].append({
            "content": result.get("content"),
            "similarity": result.get("similarity_score", 0.0),
        })

    parts = []
    parts.append("--- FDA REGULATORY DECISIONS (Approvals + CRLs) ---")

    # Count by type
    type_counts: Dict[str, int] = {}
    for data in by_type.values():
        dt = data["decision_type"]
        type_counts[dt] = type_counts.get(dt, 0) + 1

    summary_items = []
    if type_counts.get("approval", 0):
        summary_items.append(f"{type_counts['approval']} approvals")
    if type_counts.get("crl", 0):
        summary_items.append(f"{type_counts['crl']} CRLs/rejections")
    if type_counts.get("tentative_approval", 0):
        summary_items.append(f"{type_counts['tentative_approval']} tentative approvals")
    parts.append(f"Retrieved: {', '.join(summary_items) or f'{len(results)} results'}.\n")

    # Output approvals first, then CRLs
    for dtype_label, dtype_key in [("APPROVED", "approval"), ("CRL/REJECTION", "crl"),
                                     ("TENTATIVE APPROVAL", "tentative_approval"), ("WITHDRAWN", "withdrawn")]:
        type_entries = {k: v for k, v in by_type.items() if v["decision_type"] == dtype_key}
        if not type_entries:
            continue

        parts.append(f"\n  === {dtype_label}S ===")

        for key, data in sorted(type_entries.items()):
            app_num = data["application_number"]
            parts.append(f"\n  [{dtype_label}: {app_num}] {data['drug_name']}")
            if data.get("generic_name"):
                parts.append(f"    Generic: {data['generic_name']}")
            parts.append(f"    Sponsor: {data['sponsor']}")
            parts.append(f"    Date: {data['decision_date']}")
            if data.get("therapeutic_area"):
                parts.append(f"    Therapeutic Area: {data['therapeutic_area']}")
            if data.get("indication"):
                parts.append(f"    Indication: {data['indication']}")
            if data.get("review_priority"):
                parts.append(f"    Review Priority: {data['review_priority']}")
            if data.get("reason_summary"):
                parts.append(f"    Summary: {data['reason_summary']}")

            for chunk in data["chunks"]:
                similarity_pct = int(chunk.get("similarity", 0.0) * 100)
                parts.append(f"    [Relevance: {similarity_pct}%] {chunk.get('content')}")

    parts.append("\n--- END FDA DECISIONS CONTEXT ---")
    return "\n".join(parts)


def format_crl_for_claude(crl_results: List[Dict]) -> str:
    """Backward-compatible CRL formatter. Now uses the unified formatter."""
    if not crl_results:
        return ""
    # Use unified formatter — it handles both formats
    return format_fda_decisions_for_claude(crl_results)


# ═══════════════════════════════════════════════════════════════
#  Main Entry Point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    # Example: python fda_crl_pipeline.py [--force] [--crl-only] [--max N]
    force_refresh = "--force-refresh" in sys.argv or "--force" in sys.argv
    crl_only = "--crl-only" in sys.argv

    max_records = 200
    for i, arg in enumerate(sys.argv):
        if arg == "--max" and i + 1 < len(sys.argv):
            try:
                max_records = int(sys.argv[i + 1])
            except ValueError:
                pass

    if crl_only:
        print("Running CRL-only ingestion (legacy mode)...")
        # Use old behavior
        drug_records = _fetch_from_openfda(OPENFDA_DRUGS_ENDPOINT, search_query="complete response", limit=100)
        if drug_records:
            crl_records = _extract_crl_data_from_drugs_fda(drug_records)
            print(f"Found {len(crl_records)} CRL records")
        success = bool(drug_records)
    else:
        success = ingest_all_fda_decisions(force_refresh=force_refresh, max_records=max_records)

    sys.exit(0 if success else 1)
