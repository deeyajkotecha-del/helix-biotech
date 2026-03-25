"""
SatyaBio RAG Search v2 — Upgraded with hybrid search + reranking.

CHANGES FROM v1:
  - Embedding model: voyage-3 (1024d) instead of voyage-3-lite (512d)
  - Hybrid search: Combines vector similarity + full-text keyword search
  - Reranking: Uses Voyage AI reranker as a second pass for best results
  - Preserves: get_document_library, get_document_chunks, embed_document_text

Used by app.py for the cross-document search feature and document library.
"""

import os
import re as _re
from dotenv import load_dotenv
load_dotenv()

import psycopg2
import voyageai

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")

# ── UPGRADED SETTINGS ──
EMBED_MODEL = "voyage-3"           # Full model, 1024 dims (was voyage-3-lite / 512)
RERANK_MODEL = "rerank-2"          # Voyage AI reranker for second-pass scoring
VECTOR_WEIGHT = 0.65
KEYWORD_WEIGHT = 0.35

# Lazy-initialized clients
_db_conn = None
_vo_client = None


def _get_db():
    global _db_conn
    if _db_conn is None or _db_conn.closed:
        if not DATABASE_URL:
            return None
        _db_conn = psycopg2.connect(DATABASE_URL)
        _db_conn.autocommit = True
        return _db_conn
    try:
        cur = _db_conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
    except Exception:
        print("  DB connection stale — reconnecting to Neon...")
        try:
            _db_conn.close()
        except Exception:
            pass
        _db_conn = psycopg2.connect(DATABASE_URL)
        _db_conn.autocommit = True
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
        return {"total_documents": 0, "total_chunks": 0, "companies": 0}
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM documents")
        doc_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT ticker) FROM documents")
        company_count = cur.fetchone()[0]
        cur.close()
        return {"total_documents": doc_count, "total_chunks": chunk_count, "companies": company_count}
    except Exception as e:
        print(f"Library stats error: {e}")
        return {"total_documents": 0, "total_chunks": 0, "companies": 0}


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
                1 - (c.embedding <=> %s::vector) AS similarity
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
                1 - (c.embedding <=> %s::vector) AS similarity
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
    } for row in rows]


def _keyword_search(conn, query: str, top_k: int, ticker_filter: str = None) -> list[dict]:
    """Phase 1b: Full-text keyword search. Falls back gracefully if tsvector not set up yet."""
    candidate_k = top_k * 2
    cur = conn.cursor()

    try:
        if ticker_filter:
            cur.execute("""
                SELECT
                    c.id, c.content, c.page_number,
                    d.filename, d.ticker, d.company_name, d.title, d.doc_type, d.file_path,
                    ts_rank_cd(c.content_tsv, websearch_to_tsquery('english', %s)) AS rank
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
                    ts_rank_cd(c.content_tsv, websearch_to_tsquery('english', %s)) AS rank
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.content_tsv @@ websearch_to_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s
            """, (query, query, candidate_k))

        rows = cur.fetchall()
        cur.close()
        return [{
            "chunk_id": row[0], "content": row[1], "page_number": row[2],
            "filename": row[3], "ticker": row[4], "company_name": row[5],
            "title": row[6], "doc_type": row[7], "file_path": row[8],
            "keyword_score": float(row[9]),
        } for row in rows]

    except Exception as e:
        print(f"  Keyword search unavailable (run rag_setup_v2.py to enable): {e}")
        cur.close()
        return []


def _merge_and_score(vector_results: list[dict], keyword_results: list[dict]) -> list[dict]:
    """Merge vector and keyword results with weighted scoring."""
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
                merged[cid]["vector_score"] = 0.0
                merged[cid]["vector_score_norm"] = 0.0
                merged[cid]["keyword_score_norm"] = r["keyword_score"] / max_kscore

    for cid, r in merged.items():
        r["hybrid_score"] = (
            VECTOR_WEIGHT * r.get("vector_score_norm", 0.0) +
            KEYWORD_WEIGHT * r.get("keyword_score_norm", 0.0)
        )

    return sorted(merged.values(), key=lambda x: x["hybrid_score"], reverse=True)


def _rerank(vo_client, query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """Phase 2: Rerank candidates using Voyage AI reranker. Falls back to hybrid scores."""
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


def search(query: str, top_k: int = 10, ticker_filter: str = None) -> list[dict]:
    """
    UPGRADED semantic search with hybrid retrieval + reranking.

    Pipeline:
      1. Vector search (3x candidates)
      2. Keyword search (2x candidates)
      3. Merge + normalize scores
      4. Rerank top candidates
    """
    vo = _get_voyage()
    conn = _get_db()
    if not vo or not conn:
        return []

    try:
        result = vo.embed([query], model=EMBED_MODEL, input_type="query")
        query_embedding = result.embeddings[0]
    except Exception as e:
        print(f"RAG search embedding error: {e}")
        return []

    vector_results = _vector_search(conn, query_embedding, top_k, ticker_filter)
    keyword_results = _keyword_search(conn, query, top_k, ticker_filter)
    merged = _merge_and_score(vector_results, keyword_results)
    rerank_pool = merged[:top_k * 3]
    reranked = _rerank(vo, query, rerank_pool, top_k)

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
            "similarity": round(float(r.get("similarity", 0)), 4),
        })
    return results


# ═══════════════════════════════════════════════════════════════
#  DOCUMENT LIBRARY (preserved from v1)
# ═══════════════════════════════════════════════════════════════

def _clean_display_name(title: str, filename: str) -> str:
    """Create a human-readable display name from title/filename."""
    name = title or filename or "Untitled"
    if _re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-', name):
        name = filename or name
    name = _re.sub(r'\.pdf$', '', name, flags=_re.IGNORECASE)
    if _re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-', name):
        return "Untitled Document"
    name = name.replace("_", " ").replace("-", " ")
    name = _re.sub(r'\s+', ' ', name).strip()
    if name == name.lower():
        name = name.title()
    return name


def get_document_library() -> list[dict]:
    """Return all documents grouped by company for the sidebar."""
    conn = _get_db()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT d.id, d.ticker, d.company_name, d.title, d.doc_type, d.filename,
                   COUNT(c.id) as chunk_count
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            GROUP BY d.id, d.ticker, d.company_name, d.title, d.doc_type, d.filename
            HAVING COUNT(c.id) > 0
            ORDER BY d.ticker, d.title
        """)
        rows = cur.fetchall()
        cur.close()
        results = []
        for row in rows:
            raw_title = row[3] or ""
            raw_filename = row[5] or ""
            display_name = _clean_display_name(raw_title, raw_filename)
            results.append({
                "id": row[0],
                "ticker": row[1],
                "company_name": row[2],
                "title": display_name,
                "doc_type": row[4] or "document",
                "filename": raw_filename,
            })
        return results
    except Exception as e:
        print(f"Library fetch error: {e}")
        raise RuntimeError(f"Failed to load document library: {e}")


def get_document_chunks(doc_id: int) -> list[dict]:
    """Return all chunks for a specific document (for loading into chat)."""
    conn = _get_db()
    if not conn:
        raise RuntimeError("Database connection unavailable")
    try:
        doc_id = int(doc_id)
        cur = conn.cursor()
        cur.execute("""
            SELECT content, page_number
            FROM chunks
            WHERE document_id = %s
            ORDER BY page_number, id
        """, (doc_id,))
        rows = cur.fetchall()
        cur.close()
        print(f"Chunk fetch: doc_id={doc_id}, found {len(rows)} chunks")
        return [{"content": row[0], "page": row[1]} for row in rows]
    except Exception as e:
        print(f"Chunk fetch error for doc_id={doc_id}: {e}")
        raise RuntimeError(f"Failed to load document chunks: {e}")


def embed_document_text(text: str, ticker: str, company_name: str,
                        title: str, filename: str, doc_type: str = "uploaded_pdf",
                        chunk_size: int = 800, chunk_overlap: int = 150) -> dict:
    """
    Chunk, embed, and permanently store a document's text into Neon.
    Called by the Save to Library feature on the Extract page.

    UPGRADED: Now uses voyage-3 (1024d) and larger chunks (800 words, 150 overlap).
    """
    vo = _get_voyage()
    conn = _get_db()
    if not vo or not conn:
        raise RuntimeError("RAG not available — check Neon/Voyage configuration")

    words = text.split()
    word_count = len(words)

    # Build page number mapping from [Page N] markers
    _page_at_word = []
    _current_page = 1
    for w in words:
        if w == "[Page":
            pass
        elif _page_at_word and len(_page_at_word) >= 1 and words[len(_page_at_word)-1] == "[Page":
            m = _re.match(r'(\d+)\]?', w)
            if m:
                _current_page = int(m.group(1))
        _page_at_word.append(_current_page)

    if word_count <= chunk_size:
        chunks = [(text, _page_at_word[0] if _page_at_word else 1)]
    else:
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk_text = " ".join(words[start:end])
            chunk_page = _page_at_word[start] if start < len(_page_at_word) else 1
            chunks.append((chunk_text, chunk_page))
            start = end - chunk_overlap

    # Embed all chunks with UPGRADED model
    chunk_texts = [c[0] for c in chunks]
    chunk_pages = [c[1] for c in chunks]
    embeddings = []
    batch_size = 16  # Smaller batches for larger model
    for i in range(0, len(chunk_texts), batch_size):
        batch = chunk_texts[i:i + batch_size]
        try:
            result = vo.embed(batch, model=EMBED_MODEL, input_type="document")
            embeddings.extend(result.embeddings)
        except Exception as e:
            print(f"  Embed error at batch {i}: {e}")
            embeddings.extend([None] * len(batch))

    # Store in database atomically
    old_autocommit = conn.autocommit
    conn.autocommit = False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO documents (ticker, company_name, filename, file_path, doc_type, title, word_count, page_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (ticker, company_name, filename, "", doc_type, title, word_count, 1))
        doc_id = cur.fetchone()[0]

        inserted = 0
        for i, (chunk_text, embedding) in enumerate(zip(chunk_texts, embeddings)):
            if embedding is None:
                continue
            page_num = chunk_pages[i] if i < len(chunk_pages) else 1
            cur.execute("""
                INSERT INTO chunks (document_id, chunk_index, page_number, content, token_count, embedding)
                VALUES (%s, %s, %s, %s, %s, %s::vector)
            """, (doc_id, i, page_num, chunk_text, len(chunk_text.split()), str(embedding)))
            inserted += 1

        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.autocommit = old_autocommit

    print(f"  Saved to library: {title} ({ticker}) — {inserted} chunks, {word_count} words, doc #{doc_id}")
    return {"doc_id": doc_id, "chunks_stored": inserted, "word_count": word_count}


def format_context_for_claude(results: list[dict]) -> str:
    """Format RAG search results into a context block for Claude's system prompt."""
    if not results:
        return ""

    by_doc = {}
    for r in results:
        key = f"{r['ticker']}:{r['filename']}"
        if key not in by_doc:
            by_doc[key] = {
                "ticker": r["ticker"],
                "company": r["company_name"],
                "title": r["title"],
                "filename": r["filename"],
                "doc_type": r["doc_type"],
                "chunks": [],
            }
        by_doc[key]["chunks"].append({
            "content": r["content"],
            "page": r["page_number"],
            "similarity": r["similarity"],
        })

    parts = []
    parts.append("--- CROSS-DOCUMENT SEARCH RESULTS (from embedded document library) ---")
    parts.append("The following excerpts were found via semantic + keyword hybrid search with reranking.")
    parts.append("Cite the source document and page number when referencing this data.\n")

    for doc_key, doc in by_doc.items():
        parts.append(f"== {doc['ticker']} | {doc['company']} | {doc['title']} ({doc['doc_type']}) ==")
        parts.append(f"   File: {doc['filename']}")
        for chunk in doc["chunks"]:
            parts.append(f"   [Page {chunk['page']}, relevance: {chunk['similarity']}]")
            parts.append(f"   {chunk['content']}")
            parts.append("")
        parts.append("")

    parts.append("--- END SEARCH RESULTS ---")
    return "\n".join(parts)
