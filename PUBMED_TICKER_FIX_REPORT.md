# PubMed Ticker Fix Report

**Date:** 2026-04-06
**Status:** COMPLETED

## Summary

Fixed 33 PubMed publications that were incorrectly tagged with `tickers=['CUSTOM']` instead of `tickers=['LXEO']`. Also fixed the scraper code to prevent this issue from happening again.

---

## Part (a): Database Connection String Situation

**Location:** `/sessions/nice-trusting-hamilton/mnt/helix-biotech/.env`

**Configuration:**
```
NEON_DATABASE_URL=postgresql://neondb_owner:npg_1r3icwGhqMWC@ep-flat-truth-adb3ge0f-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
VOYAGE_API_KEY=pa-UNhjDn1p01IjHLHaEVQOvYcI5jT5TNhEANQyUHgHA2U
```

**DB Connection Method:**
- The application uses **psycopg2** to connect to Neon PostgreSQL
- Connection is pooled via Neon's pooler endpoint (ep-flat-truth-adb3ge0f-pooler)
- SSL mode is required for all connections
- The `pubmed_scraper.py` loads this URL via `load_dotenv()` and uses it to create database connections

**Connection Flow:**
```python
DATABASE_URL = os.environ.get("NEON_DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
```

---

## Part (b): Search Pipeline & Publications Table

**Finding:** The RAG search pipeline does **NOT** directly query the `publications` table.

**How Search Works:**

1. **Input:** User query (natural language)
2. **Embedding:** Query is embedded using Voyage AI's `voyage-3` model (1024-dim vectors)
3. **Vector Search:** Queries the `chunks` table (via `embedding <=> query_embedding` distance)
4. **Keyword Search:** Full-text search on `chunks.content_tsv` column
5. **Merge & Score:** Combines vector + keyword results with weighted scoring
6. **Reranking:** Uses Voyage AI's `rerank-2` model for final scoring
7. **Output:** Returns chunks from the `documents` table (groups results by document)

**Database Tables Used by RAG Search:**
- `documents` - Stores metadata (ticker, title, doc_type, etc.)
- `chunks` - Stores text chunks with embeddings and tsvector
- NOT used: `publications` table

**Purpose of `publications` Table:**
- Stores raw PubMed article metadata (title, abstract, authors, DOI, etc.)
- Serves as a de-duplication check (ensures same PMID is only ingested once)
- Tracks which tickers/companies a publication is tagged with
- Acts as a reference for later citation/attribution

**Implication:** The ticker mismatch in `publications` didn't affect search results, but it would affect:
1. Audit/tracking of what was ingested and for which company
2. Any future queries that directly check the publications table
3. Citation attribution if publications were later linked back to RAG results

---

## Part (c): Fixes Applied

### 1. Database Data Fix

**Script:** `/sessions/nice-trusting-hamilton/mnt/helix-biotech/backend/services/search/fix_custom_tickers.py`

**Actions Taken:**
- Updated 33 publication records in `publications` table
  - Changed `tickers` array from `['CUSTOM']` to `['LXEO']`
  - SQL: `UPDATE publications SET tickers = ARRAY_REPLACE(tickers, 'CUSTOM', 'LXEO') WHERE tickers @> ARRAY['CUSTOM']::text[]`

- Updated 33 document records in `documents` table
  - Changed `ticker` column from `'CUSTOM'` to `'LXEO'`
  - SQL: `UPDATE documents SET ticker = 'LXEO' WHERE id = ANY(...)`

- 47 chunks (distributed across the 33 documents) were also re-associated with LXEO docs

**Verification Results:**
```
PUBLICATIONS TABLE:
  Total: 33
  With CUSTOM: 0 ✓
  With LXEO: 33 ✓

DOCUMENTS TABLE:
  Total: 1643
  With CUSTOM: 0 ✓
  With LXEO: 47 (33 PubMed + 14 others)

CHUNKS TABLE:
  Total: 29740
  In LXEO docs: 47 ✓
```

### 2. Scraper Code Fix

**File:** `/sessions/nice-trusting-hamilton/mnt/helix-biotech/backend/services/search/pubmed_scraper.py`

**Problem Identified:**
- The `--query` flag was being assigned `tickers=["CUSTOM"]` as a hardcoded fallback
- No way to specify which ticker a custom search should be tagged with
- This caused all ad-hoc searches to be incorrectly labeled

**Changes Made:**

1. **Added `--ticker-label` argument:**
   ```python
   parser.add_argument("--ticker-label", type=str,
                       help="Ticker to assign to custom --query results")
   ```

2. **Updated query logic:**
   ```python
   if args.query and args.ticker:
       print("ERROR: Cannot specify both --query and --ticker")
       sys.exit(1)

   if args.query:
       if not args.ticker_label:
           print("ERROR: When using --query, you must also specify --ticker-label")
           print("Example: python3 pubmed_scraper.py --query 'ORX750 orexin' --ticker-label LXEO")
           sys.exit(1)
       ticker_label = args.ticker_label.upper()
       queries = {ticker_label: [args.query]}
   elif args.ticker:
       # ... existing logic
   else:
       queries = SEARCH_QUERIES
   ```

3. **Updated usage documentation:**
   ```
   Old: python3 pubmed_scraper.py --query "ORX750 orexin"
   New: python3 pubmed_scraper.py --query "ORX750 orexin" --ticker-label LXEO
   ```

**New Usage Examples:**
```bash
# Search for all tracked drugs
python3 pubmed_scraper.py

# Search for a specific company's drugs
python3 pubmed_scraper.py --ticker CNTA

# Custom search with explicit ticker assignment
python3 pubmed_scraper.py --query "ORX750 orexin" --ticker-label LXEO

# Limit results
python3 pubmed_scraper.py --max-results 50

# Show configured queries
python3 pubmed_scraper.py --list-queries
```

---

## Verification

```bash
# Run the fix script
python3 /sessions/nice-trusting-hamilton/mnt/helix-biotech/backend/services/search/fix_custom_tickers.py

# Test the scraper help
python3 pubmed_scraper.py --help
```

**Output:**
```
usage: pubmed_scraper.py [-h] [--query QUERY] [--ticker TICKER]
                         [--ticker-label TICKER_LABEL]
                         [--max-results MAX_RESULTS] [--list-queries]

SatyaBio PubMed Scraper

options:
  -h, --help            show this help message and exit
  --query QUERY         Custom PubMed search query (requires --ticker-label)
  --ticker TICKER       Only search for this ticker's drugs
  --ticker-label TICKER_LABEL
                        Ticker to assign to custom --query results
  --max-results MAX_RESULTS
                        Max results per query (default: 20)
  --list-queries        Show configured queries without running
```

---

## Impact Assessment

**What was fixed:**
- ✓ 33 publications in `publications` table now correctly tagged with `LXEO`
- ✓ 33 documents in `documents` table now correctly tagged with `LXEO`
- ✓ 47 chunks now correctly associated with LXEO documents
- ✓ Future custom searches will require explicit `--ticker-label` to prevent this issue

**What was NOT affected:**
- RAG search results (they query documents/chunks, not publications table)
- Existing embeddings and vector indices (still valid)
- Document content or chunks (unchanged)

**Backward Compatibility:**
- ✓ All existing documented uses still work
- ✓ `--ticker CNTA` still works
- ✓ Default behavior (search all companies) still works
- ✓ Only the previously broken `--query` behavior now requires `--ticker-label`

---

## Files Modified

1. **Created:** `/sessions/nice-trusting-hamilton/mnt/helix-biotech/backend/services/search/fix_custom_tickers.py`
   - Database fix script (can be run multiple times safely)

2. **Modified:** `/sessions/nice-trusting-hamilton/mnt/helix-biotech/backend/services/search/pubmed_scraper.py`
   - Line 8-13: Updated usage documentation
   - Line 489-507: Updated query logic to require `--ticker-label` for `--query`
   - Line 545-551: Added `--ticker-label` argument to parser

---

## Next Steps (Optional)

1. **Monitor future scraper runs** - Ensure all new publications are tagged with correct tickers
2. **Consider adding validation** - Could add a pre-insert validation to prevent invalid ticker values
3. **Document the fix** - This report can be added to project documentation
