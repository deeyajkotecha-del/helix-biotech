"""
SatyaBio RAG Search — Semantic search across all embedded documents.

Used by app.py for the cross-document search feature.
Connects to Neon Postgres + pgvector, embeds the query with Voyage AI,
and returns the most relevant chunks with source citations.
"""

import os
from dotenv import load_dotenv
load_dotenv()

import psycopg2
import voyageai

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
EMBED_MODEL = "voyage-3-lite"

# Lazy-initialized clients
_db_conn = None
_vo_client = None


def _get_db():
    global _db_conn
    try:
        if _db_conn is not None and not _db_conn.closed:
            # Test the connection is actually alive (handles SSL drops)
            _db_conn.cursor().execute("SELECT 1")
            return _db_conn
    except Exception:
        # Connection is broken — close and reconnect
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


def search(query: str, top_k: int = 10, ticker_filter: str = None) -> list[dict]:
    """
    Semantic search across all embedded documents.

    Args:
        query: The user's question (natural language)
        top_k: Number of results to return (default 10)
        ticker_filter: Optional ticker to limit search to one company

    Returns:
        List of dicts with: content, page_number, filename, ticker, company_name,
        title, doc_type, similarity_score
    """
    vo = _get_voyage()
    conn = _get_db()
    if not vo or not conn:
        return []

    # Embed the query
    try:
        result = vo.embed([query], model=EMBED_MODEL, input_type="query")
        query_embedding = result.embeddings[0]
    except Exception as e:
        print(f"RAG search embedding error: {e}")
        return []

    # Search with pgvector cosine similarity
    try:
        cur = conn.cursor()

        if ticker_filter:
            cur.execute("""
                SELECT
                    c.content,
                    c.page_number,
                    d.filename,
                    d.ticker,
                    d.company_name,
                    d.title,
                    d.doc_type,
                    d.file_path,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE d.ticker = %s
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """, (str(query_embedding), ticker_filter.upper(), str(query_embedding), top_k))
        else:
            cur.execute("""
                SELECT
                    c.content,
                    c.page_number,
                    d.filename,
                    d.ticker,
                    d.company_name,
                    d.title,
                    d.doc_type,
                    d.file_path,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """, (str(query_embedding), str(query_embedding), top_k))

        rows = cur.fetchall()
        cur.close()

        results = []
        for row in rows:
            results.append({
                "content": row[0],
                "page_number": row[1],
                "filename": row[2],
                "ticker": row[3],
                "company_name": row[4],
                "title": row[5],
                "doc_type": row[6],
                "file_path": row[7],
                "similarity": round(float(row[8]), 4),
            })

        return results

    except Exception as e:
        print(f"RAG search query error: {e}")
        return []


def format_context_for_claude(results: list[dict]) -> str:
    """
    Format RAG search results into a context block for Claude's system prompt.
    Groups results by document for cleaner reading.
    """
    if not results:
        return ""

    # Group by document
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

    # Build context string
    parts = []
    parts.append("--- CROSS-DOCUMENT SEARCH RESULTS (from embedded document library) ---")
    parts.append("The following excerpts were found via semantic search across the full document library.")
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
