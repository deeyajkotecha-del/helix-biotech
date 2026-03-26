"""Fix rag_search.py: hide empty docs from library + track page numbers in chunks."""
import re

p = 'extraction/rag_search.py'
with open(p) as f:
    code = f.read()

changes = 0

# Fix 1: Library query — only show documents that have chunks
old_query = '''        cur.execute("""
            SELECT id, ticker, company_name, title, doc_type, filename
            FROM documents
            ORDER BY ticker, title
        """)'''

new_query = '''        cur.execute("""
            SELECT d.id, d.ticker, d.company_name, d.title, d.doc_type, d.filename,
                   COUNT(c.id) as chunk_count
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            GROUP BY d.id, d.ticker, d.company_name, d.title, d.doc_type, d.filename
            HAVING COUNT(c.id) > 0
            ORDER BY d.ticker, d.title
        """)'''

if old_query in code:
    code = code.replace(old_query, new_query)
    changes += 1
    print("Fix 1 applied: Library query now filters out empty documents")
else:
    print("Fix 1: already applied or pattern not found")

# Fix 2: Chunk page number tracking during embed_document_text
old_chunk = '''    # Chunk the text
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
            start = end - chunk_overlap'''

new_chunk = '''    # Chunk the text, tracking page numbers from [Page N] markers
    import re as _re
    words = text.split()
    word_count = len(words)

    # Build a mapping: word index -> page number
    _page_at_word = []
    _current_page = 1
    for idx, w in enumerate(words):
        if w == "[Page":
            pass
        elif idx > 0 and words[idx-1] == "[Page":
            m = _re.match(r'(\\d+)\\]?', w)
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
            start = end - chunk_overlap'''

if old_chunk in code:
    code = code.replace(old_chunk, new_chunk)
    changes += 1
    print("Fix 2 applied: Chunks now track correct page numbers")
else:
    print("Fix 2: already applied or pattern not found")

# Fix 3: Update embed loop to use tuple format
old_embed = '''    # Embed all chunks
    import hashlib
    embeddings = []
    batch_size = 32
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]'''

new_embed = '''    # Embed all chunks (chunks is now list of (text, page_num) tuples)
    import hashlib
    chunk_texts = [c[0] for c in chunks]
    chunk_pages = [c[1] for c in chunks]
    embeddings = []
    batch_size = 32
    for i in range(0, len(chunk_texts), batch_size):
        batch = chunk_texts[i:i + batch_size]'''

if old_embed in code:
    code = code.replace(old_embed, new_embed)
    changes += 1
    print("Fix 3 applied: Embed loop uses separated text/page lists")
else:
    print("Fix 3: already applied or pattern not found")

# Fix 4: Update chunk insert to use correct page numbers
old_insert = '''        # Insert chunks with embeddings
        inserted = 0
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            if embedding is None:
                continue
            cur.execute("""
                INSERT INTO chunks (document_id, chunk_index, page_number, content, token_count, embedding)
                VALUES (%s, %s, %s, %s, %s, %s::vector)
            """, (doc_id, i, 1, chunk, len(chunk.split()), str(embedding)))'''

new_insert = '''        # Insert chunks with embeddings and correct page numbers
        inserted = 0
        for i, (chunk_text, embedding) in enumerate(zip(chunk_texts, embeddings)):
            if embedding is None:
                continue
            page_num = chunk_pages[i] if i < len(chunk_pages) else 1
            cur.execute("""
                INSERT INTO chunks (document_id, chunk_index, page_number, content, token_count, embedding)
                VALUES (%s, %s, %s, %s, %s, %s::vector)
            """, (doc_id, i, page_num, chunk_text, len(chunk_text.split()), str(embedding)))'''

if old_insert in code:
    code = code.replace(old_insert, new_insert)
    changes += 1
    print("Fix 4 applied: Chunk insert now uses correct page numbers")
else:
    print("Fix 4: already applied or pattern not found")

if changes > 0:
    with open(p, 'w') as f:
        f.write(code)
    print(f"\nDone — {changes} fixes applied to {p}")
else:
    print(f"\nNo changes needed — all fixes already applied")
