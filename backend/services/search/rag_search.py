"""
SatyaBio RAG Search v2 — Upgraded with hybrid search + reranking.

CHANGES FROM v1:
  - Embedding model: voyage-3 (1024d) instead of voyage-3-lite (512d)
  - Hybrid search: Combines vector similarity + full-text keyword search
  - Reranking: Uses Voyage AI reranker as a second pass for best results
  - Larger candidate pool: Fetches 3x top_k candidates, reranks down to top_k
  - Better handling of exact terms (NCT numbers, drug names, gene symbols)

Used by the search router for cross-document search.
"""

import os
import re
from datetime import datetime, date
from dotenv import load_dotenv
load_dotenv()

import psycopg2
import voyageai

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")

# ── UPGRADED SETTINGS ──
EMBED_MODEL = "voyage-3"           # Full model, 1024 dims (was voyage-3-lite / 512)
RERANK_MODEL = "rerank-2"          # Voyage AI reranker for second-pass scoring
VECTOR_WEIGHT = 0.55               # Weight for semantic similarity in hybrid score
KEYWORD_WEIGHT = 0.30              # Weight for keyword match in hybrid score
RECENCY_WEIGHT = 0.15              # Weight for document recency (newer = higher)

# Lazy-initialized clients
_db_conn = None
_vo_client = None


def _get_db():
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

    if not DATABASE_URL:
        return None
    try:
        _db_conn = psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"  RAG DB reconnect failed: {e}")
        _db_conn = None
    return _db_conn


def _get_voyage():
    global _vo_client
    if _vo_client is None:
        if not VOYAGE_API_KEY:
            return None
        _vo_client = voyageai.Client(api_key=VOYAGE_API_KEY)
    return _vo_client


def is_rag_available() -> bool:
    """Check if RAG search is configured (Neon + Voyage keys present)."""
    return bool(DATABASE_URL) and bool(VOYAGE_API_KEY)


def get_library_stats() -> dict:
    """Get counts of documents and chunks in the database."""
    conn = _get_db()
    if not conn:
        return {"documents": 0, "chunks": 0, "companies": 0}
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM documents")
        doc_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT ticker) FROM documents")
        company_count = cur.fetchone()[0]
        cur.close()
        return {"documents": doc_count, "chunks": chunk_count, "companies": company_count}
    except Exception:
        return {"documents": 0, "chunks": 0, "companies": 0}


# ═══════════════════════════════════════════════════════════════
#  HYBRID SEARCH: Vector + Keyword + Reranking
# ═══════════════════════════════════════════════════════════════

def _vector_search(conn, query_embedding: list, top_k: int, ticker_filter: str = None) -> list[dict]:
    """Phase 1a: Pure vector similarity search. Over-fetches 3x for reranking."""
    candidate_k = top_k * 3
    cur = conn.cursor()

    if ticker_filter:
        cur.execute("""
            SELECT
                c.id, c.content, c.page_number,
                d.filename, d.ticker, d.company_name, d.title, d.doc_type, d.file_path,
                1 - (c.embedding <=> %s::vector) AS similarity,
                d.date
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.ticker = %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """, (str(query_embedding), ticker_filter.upper(), str(query_embedding), candidate_k))
    else:
        cur.execute("""
            SELECT
                c.id, c.content, c.page_number,
                d.filename, d.ticker, d.company_name, d.title, d.doc_type, d.file_path,
                1 - (c.embedding <=> %s::vector) AS similarity,
                d.date
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """, (str(query_embedding), str(query_embedding), candidate_k))

    rows = cur.fetchall()
    cur.close()

    return [{
        "chunk_id": row[0],
        "content": row[1],
        "page_number": row[2],
        "filename": row[3],
        "ticker": row[4],
        "company_name": row[5],
        "title": row[6],
        "doc_type": row[7],
        "file_path": row[8],
        "vector_score": float(row[9]),
        "doc_date": row[10] or "",
    } for row in rows]


def _keyword_search(conn, query: str, top_k: int, ticker_filter: str = None) -> list[dict]:
    """
    Phase 1b: Full-text keyword search using PostgreSQL tsvector.
    Catches exact matches that vector search might miss (NCT IDs, drug codes, gene names).
    Falls back gracefully if content_tsv column doesn't exist yet.
    """
    candidate_k = top_k * 2
    cur = conn.cursor()

    try:
        if ticker_filter:
            cur.execute("""
                SELECT
                    c.id, c.content, c.page_number,
                    d.filename, d.ticker, d.company_name, d.title, d.doc_type, d.file_path,
                    ts_rank_cd(c.content_tsv, websearch_to_tsquery('english', %s)) AS rank,
                    d.date
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.content_tsv @@ websearch_to_tsquery('english', %s)
                  AND d.ticker = %s
                ORDER BY rank DESC
                LIMIT %s
            """, (query, query, ticker_filter.upper(), candidate_k))
        else:
            cur.execute("""
                SELECT
                    c.id, c.content, c.page_number,
                    d.filename, d.ticker, d.company_name, d.title, d.doc_type, d.file_path,
                    ts_rank_cd(c.content_tsv, websearch_to_tsquery('english', %s)) AS rank,
                    d.date
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.content_tsv @@ websearch_to_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s
            """, (query, query, candidate_k))

        rows = cur.fetchall()
        cur.close()

        return [{
            "chunk_id": row[0],
            "content": row[1],
            "page_number": row[2],
            "filename": row[3],
            "ticker": row[4],
            "company_name": row[5],
            "title": row[6],
            "doc_type": row[7],
            "file_path": row[8],
            "keyword_score": float(row[9]),
            "doc_date": row[10] or "",
        } for row in rows]

    except Exception as e:
        # content_tsv column may not exist yet (before schema migration)
        print(f"  Keyword search unavailable (run rag_setup_v2.py to enable): {e}")
        cur.close()
        return []


def _parse_doc_date(date_str: str) -> float:
    """
    Parse a document date string and return a recency score between 0 and 1.
    Newer documents score higher. Documents with no date get 0.3 (neutral).

    Scoring: A document from today scores 1.0. A document from 3+ years ago scores 0.0.
    Linear decay over a 3-year window.
    """
    if not date_str:
        return 0.3  # Neutral score for undated docs

    # Try common date formats found in our corpus
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%B %d, %Y", "%b %d, %Y"):
        try:
            doc_date = datetime.strptime(date_str.strip()[:10], fmt).date()
            break
        except (ValueError, IndexError):
            continue
    else:
        # Try to extract a year from the string (e.g. "2025" or "FY2025")
        year_match = re.search(r'20[12]\d', date_str)
        if year_match:
            year = int(year_match.group())
            doc_date = date(year, 6, 15)  # Assume mid-year
        else:
            return 0.3  # Can't parse — neutral

    today = date.today()
    days_old = (today - doc_date).days
    max_age_days = 3 * 365  # 3-year window

    if days_old <= 0:
        return 1.0
    if days_old >= max_age_days:
        return 0.0

    return 1.0 - (days_old / max_age_days)


def _merge_and_score(vector_results: list[dict], keyword_results: list[dict]) -> list[dict]:
    """Merge vector and keyword results with weighted scoring, including recency bias."""
    merged = {}

    if vector_results:
        max_vscore = max(r["vector_score"] for r in vector_results) or 1.0
        for r in vector_results:
            cid = r["chunk_id"]
            merged[cid] = r.copy()
            merged[cid]["vector_score_norm"] = r["vector_score"] / max_vscore
            merged[cid]["keyword_score_norm"] = 0.0

    if keyword_results:
        max_kscore = max(r["keyword_score"] for r in keyword_results) or 1.0
        for r in keyword_results:
            cid = r["chunk_id"]
            if cid in merged:
                merged[cid]["keyword_score_norm"] = r["keyword_score"] / max_kscore
            else:
                merged[cid] = r.copy()
                merged[cid]["vector_score"] = merged[cid].get("vector_score", 0.0)
                merged[cid]["vector_score_norm"] = 0.0
                merged[cid]["keyword_score_norm"] = r["keyword_score"] / max_kscore

    for cid, r in merged.items():
        recency_score = _parse_doc_date(r.get("doc_date", ""))
        r["recency_score"] = recency_score
        r["hybrid_score"] = (
            VECTOR_WEIGHT * r.get("vector_score_norm", 0.0) +
            KEYWORD_WEIGHT * r.get("keyword_score_norm", 0.0) +
            RECENCY_WEIGHT * recency_score
        )

    return sorted(merged.values(), key=lambda x: x["hybrid_score"], reverse=True)


def _rerank(vo_client, query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """
    Phase 2: Rerank candidates using Voyage AI's reranker.
    Falls back to hybrid scores if reranking fails.
    """
    if not candidates:
        return []

    try:
        documents = [c["content"] for c in candidates]
        result = vo_client.rerank(
            query=query,
            documents=documents,
            model=RERANK_MODEL,
            top_k=min(top_k, len(candidates)),
        )

        reranked = []
        for item in result.results:
            candidate = candidates[item.index].copy()
            candidate["rerank_score"] = item.relevance_score
            candidate["similarity"] = item.relevance_score
            reranked.append(candidate)

        return reranked

    except Exception as e:
        print(f"  Reranking failed (using hybrid scores): {e}")
        for c in candidates[:top_k]:
            c["similarity"] = c.get("hybrid_score", c.get("vector_score", 0.0))
        return candidates[:top_k]


def search(query: str, top_k: int = 50, ticker_filter: str = None) -> list[dict]:
    """
    UPGRADED semantic search with hybrid retrieval + reranking.

    Pipeline:
      1. Vector search (3x candidates) — catches semantic matches
      2. Keyword search (2x candidates) — catches exact terms
      3. Merge + normalize scores — weighted combination
      4. Rerank top candidates — Voyage AI reranker picks the best

    v3 change: top_k increased from 10 to 50 for deeper retrieval.
    More context = better grounding = fewer hallucinations.
    Cost impact: ~$0.02 more per query (Claude input tokens).

    Args:
        query: The user's question (natural language)
        top_k: Number of results to return (default 50)
        ticker_filter: Optional ticker to limit search to one company

    Returns:
        List of dicts with: content, page_number, filename, ticker, company_name,
        title, doc_type, file_path, similarity (rerank score)
    """
    vo = _get_voyage()
    conn = _get_db()
    if not vo or not conn:
        return []

    # Step 1: Embed the query
    try:
        result = vo.embed([query], model=EMBED_MODEL, input_type="query")
        query_embedding = result.embeddings[0]
    except Exception as e:
        print(f"RAG search embedding error: {e}")
        return []

    # Step 2: Vector search (semantic)
    vector_results = _vector_search(conn, query_embedding, top_k, ticker_filter)

    # Step 3: Keyword search (exact terms — NCT numbers, drug names, genes)
    keyword_results = _keyword_search(conn, query, top_k, ticker_filter)

    # Step 4: Merge and score
    merged = _merge_and_score(vector_results, keyword_results)

    # Step 5: Rerank the top candidates
    rerank_pool = merged[:top_k * 3]
    reranked = _rerank(vo, query, rerank_pool, top_k)

    # Clean up output format
    results = []
    for r in reranked:
        results.append({
            "content": r["content"],
            "page_number": r["page_number"],
            "filename": r["filename"],
            "ticker": r["ticker"],
            "company_name": r["company_name"],
            "title": r["title"],
            "doc_type": r["doc_type"],
            "file_path": r.get("file_path", ""),
            "doc_date": r.get("doc_date", ""),
            "similarity": round(float(r.get("similarity", 0)), 4),
        })

    return results


def format_context_for_claude(results: list[dict]) -> str:
    """
    Format RAG search results into a context block for Claude's system prompt.
    Groups results by document for cleaner reading.
    Includes doc_id and source links for citation.
    """
    if not results:
        return ""

    by_doc = {}
    doc_index = 1
    for r in results:
        key = f"{r['ticker']}:{r['filename']}"
        if key not in by_doc:
            by_doc[key] = {
                "doc_num": doc_index,
                "ticker": r["ticker"],
                "company": r["company_name"],
                "title": r["title"],
                "filename": r["filename"],
                "doc_type": r["doc_type"],
                "file_path": r.get("file_path", ""),
                "doc_date": r.get("doc_date", ""),
                "chunks": [],
            }
            doc_index += 1
        by_doc[key]["chunks"].append({
            "content": r["content"],
            "page": r["page_number"],
            "similarity": r["similarity"],
        })

    parts = []
    parts.append("--- INTERNAL DOCUMENT LIBRARY (embedded investor decks, SEC filings, clinical papers) ---")
    parts.append(f"Retrieved {len(results)} chunks from {len(by_doc)} documents via hybrid search + reranking.")
    parts.append("CITATION RULE: When citing data from these documents, use {{doc:TICKER|DocTitle}} format.")
    parts.append("Example: {{doc:RVMD|ASCO 2024 Investor Presentation}} — do NOT use [Doc N] format.\n")

    # Document index — maps Doc N to ticker|title so Claude can build proper citations
    parts.append("DOCUMENT INDEX:")
    for doc_key, doc in by_doc.items():
        date_str = f" | Date: {doc['doc_date']}" if doc["doc_date"] else ""
        parts.append(f"  [Doc {doc['doc_num']}] → Cite as: {{doc:{doc['ticker']}|{doc['title']}}} | Type: {doc['doc_type']}{date_str}")
    parts.append("")

    for doc_key, doc in by_doc.items():
        parts.append(f"== [Doc {doc['doc_num']}] {doc['ticker']} | {doc['company']} | {doc['title']} ({doc['doc_type']}) ==")
        parts.append(f"   CITE THIS AS: {{doc:{doc['ticker']}|{doc['title']}}}")
        for chunk in doc["chunks"]:
            parts.append(f"   [Page {chunk['page']}, relevance: {chunk['similarity']}]")
            parts.append(f"   {chunk['content']}")
            parts.append("")
        parts.append("")

    parts.append("--- END DOCUMENT LIBRARY ---")
    return "\n".join(parts)
