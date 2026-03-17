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
    if _db_conn is None or _db_conn.closed:
        if not DATABASE_URL:
            return None
        _db_conn = psycopg2.connect(DATABASE_URL)
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


import re as _re

def _clean_display_name(title: str, filename: str) -> str:
    """Create a human-readable display name from title/filename."""
    name = title or filename or "Untitled"
    # If it's a UUID, use the filename instead
    if _re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-', name):
        name = filename or name
    # Strip .pdf extension
    name = _re.sub(r'\.pdf$', '', name, flags=_re.IGNORECASE)
    # If still a UUID after trying filename, just show "Document"
    if _re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-', name):
        return "Untitled Document"
    # Clean up separators
    name = name.replace("_", " ").replace("-", " ")
    # Collapse multiple spaces
    name = _re.sub(r'\s+', ' ', name).strip()
    # Capitalize if all lowercase
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
            SELECT id, ticker, company_name, title, doc_type, filename
            FROM documents
            ORDER BY ticker, title
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
        return []


def get_document_chunks(doc_id: int) -> list[dict]:
    """Return all chunks for a specific document (for loading into chat)."""
    conn = _get_db()
    if not conn:
        print(f"Chunk fetch: no DB connection")
        return []
    try:
        cur = conn.cursor()
        # Ensure doc_id is an integer
        doc_id = int(doc_id)
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
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def embed_document_text(text: str, ticker: str, company_name: str,
                        title: str, filename: str, doc_type: str = "uploaded_pdf",
                        chunk_size: int = 500, chunk_overlap: int = 75) -> dict:
    """
    Chunk, embed, and permanently store a document's text into Neon.
    Called by the Save to Library feature on the Extract page.

    Returns dict with doc_id and chunks_stored count.
    """
    vo = _get_voyage()
    conn = _get_db()
    if not vo or not conn:
        raise RuntimeError("RAG not available — check Neon/Voyage configuration")

    # Chunk the text
    words = text.split()
    word_count = len(words)
    if word_count <= chunk_size:
        chunks = [text]
    else:
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunks.append(" ".join(words[start:end]))
            start = end - chunk_overlap

    # Embed all chunks
    import hashlib
    embeddings = []
    batch_size = 32
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        try:
            result = vo.embed(batch, model=EMBED_MODEL, input_type="document")
            embeddings.extend(result.embeddings)
        except Exception as e:
            print(f"  Embed error at batch {i}: {e}")
            embeddings.extend([None] * len(batch))

    # Store in database
    cur = conn.cursor()

    # Insert document record
    cur.execute("""
        INSERT INTO documents (ticker, company_name, filename, file_path, doc_type, title, word_count, page_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        ticker, company_name,
        filename,
        "",  # no file_path for web uploads (will be R2 URL later)
        doc_type, title, word_count, 1
    ))
    doc_id = cur.fetchone()[0]

    # Insert chunks with embeddings
    inserted = 0
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        if embedding is None:
            continue
        cur.execute("""
            INSERT INTO chunks (document_id, chunk_index, page_number, content, token_count, embedding)
            VALUES (%s, %s, %s, %s, %s, %s::vector)
        """, (doc_id, i, 1, chunk, len(chunk.split()), str(embedding)))
        inserted += 1

    conn.commit()
    cur.close()
    print(f"  Saved to library: {title} ({ticker}) — {inserted} chunks, {word_count} words, doc #{doc_id}")

    return {"doc_id": doc_id, "chunks_stored": inserted, "word_count": word_count}


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
