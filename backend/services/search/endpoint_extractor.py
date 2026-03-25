"""
SatyaBio Endpoint Extractor — Pulls structured clinical data from embedded documents.

Takes the text chunks already in Neon (from your RAG pipeline) and uses Claude to
extract numeric clinical endpoints into the clinical_endpoints table.

This is how we go from "text about EASI-75 results" to structured rows that can
be charted in landscape comparisons.

Strategy:
    1. Query chunks that contain clinical endpoint keywords (ORR, PFS, EASI, etc.)
    2. Send batches to Claude with a structured extraction prompt
    3. Parse Claude's JSON output into clinical_endpoints rows
    4. Dedup on (drug_name, trial_name, endpoint_name, value_type, dose, timepoint)

Usage:
    python3 endpoint_extractor.py --all                    # Extract from all companies
    python3 endpoint_extractor.py --ticker REGN,ABBV       # Specific companies
    python3 endpoint_extractor.py --indication "Atopic Dermatitis"  # Filter by indication
    python3 endpoint_extractor.py --stats                  # Show what's been extracted
    python3 endpoint_extractor.py --dry-run                # Preview without inserting

Requires:
    NEON_DATABASE_URL, VOYAGE_API_KEY, ANTHROPIC_API_KEY in .env
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import anthropic

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# How many chunks to send to Claude at once
BATCH_SIZE = 5
# Pause between Claude calls (rate limiting)
CLAUDE_DELAY = 1.0

# Keywords that indicate a chunk likely contains extractable clinical data
ENDPOINT_KEYWORDS = [
    # Efficacy endpoints
    "ORR", "overall response rate", "complete response", "partial response",
    "PFS", "progression-free survival", "mPFS", "median PFS",
    "OS ", "overall survival", "mOS", "median OS",
    "DOR", "duration of response", "median duration",
    "EASI", "EASI-75", "EASI-90", "IGA", "SCORAD",
    "ACR20", "ACR50", "ACR70", "DAS28", "HAQ-DI",
    "PASI", "PASI-75", "PASI-90", "PASI-100",
    "HbA1c", "body weight", "weight loss",
    # Statistical
    "hazard ratio", "HR ", "confidence interval", "p-value", "p=", "p<",
    "median follow-up", "data cutoff",
    # Trial results context
    "primary endpoint", "secondary endpoint", "met its primary",
    "demonstrated", "achieved", "showed superiority",
]

# The extraction prompt — tells Claude exactly what JSON to return
EXTRACTION_PROMPT = """You are a clinical data extraction system. Extract ALL numeric clinical trial endpoints from the text below.

For EACH data point, return a JSON object with these fields:
{
  "drug_name": "canonical drug name (lowercase generic, e.g., 'dupilumab')",
  "brand_name": "brand if mentioned (e.g., 'DUPIXENT')",
  "company_ticker": "ticker if identifiable",
  "target": "molecular target (e.g., 'IL-4Ra/IL-13', 'HER2', 'KRAS G12C')",
  "mechanism": "brief mechanism (e.g., 'anti-IL-4Ra mAb', 'ADC')",
  "modality": "drug type (mAb, small_molecule, ADC, bispecific, cell_therapy, etc.)",
  "trial_name": "trial name if mentioned (e.g., 'SOLO 2', 'DESTINY-Breast03')",
  "nct_id": "NCT number if mentioned",
  "phase": "Phase 1/2/3 or Approved",
  "indication": "disease (e.g., 'Atopic Dermatitis', 'HER2+ mBC')",
  "indication_detail": "population detail (e.g., 'moderate-to-severe, adult')",
  "line_of_therapy": "1L, 2L+, 3L+ if mentioned",
  "endpoint_name": "endpoint (e.g., 'EASI-75', 'ORR', 'mPFS', 'mOS')",
  "endpoint_category": "efficacy, safety, pk, or biomarker",
  "value": numeric value (e.g., 48.0 for 48%),
  "value_unit": "% or months or mg/L etc.",
  "value_type": "absolute, pbo_adjusted, or vs_comparator",
  "comparator_name": "placebo, comparator drug name, or null",
  "comparator_value": numeric or null,
  "hazard_ratio": numeric or null,
  "confidence_interval": "e.g., '0.28-0.45' or null",
  "p_value": "e.g., '<0.001' or null",
  "enrollment": integer or null,
  "evaluable_n": integer or null,
  "population_note": "ITT, mITT, PD-L1>=50%, etc.",
  "dose": "e.g., '300mg Q2W', '5.4mg/kg Q3W'",
  "timepoint": "e.g., 'Week 16', '12 months', 'data cutoff'",
  "median_followup": "e.g., '28.4 months'",
  "source_detail": "e.g., 'ASCO 2024', 'NEJM 2023', 'Q4 2025 earnings'"
}

RULES:
1. Extract EVERY numeric endpoint you can find — ORR, PFS, OS, response rates, HRs, etc.
2. If both absolute and placebo-adjusted values are given, create SEPARATE rows for each.
3. If multiple doses are compared, create SEPARATE rows for each dose.
4. If multiple timepoints are given, create SEPARATE rows for each.
5. Use null (not "N/A" or "") for missing fields.
6. The value field MUST be a number (not a string).
7. Normalize endpoint names: use "ORR" not "overall response rate", "mPFS" not "median PFS", "EASI-75" not "EASI 75".

Return ONLY a JSON array of objects. No explanation text, just the JSON array.
If there are no extractable endpoints, return an empty array: []

TEXT TO EXTRACT FROM:
"""


def find_endpoint_chunks(conn, ticker: str = None, indication: str = None,
                         limit: int = 500) -> list[dict]:
    """
    Find chunks in the database that likely contain clinical endpoint data.
    Uses keyword matching to avoid sending irrelevant chunks to Claude.
    """
    cur = conn.cursor()

    # Build a keyword filter using PostgreSQL ILIKE
    keyword_conditions = " OR ".join(
        f"c.content ILIKE '%{kw}%'" for kw in [
            "ORR", "PFS", "overall survival", "EASI-75", "EASI-90",
            "hazard ratio", "response rate", "primary endpoint",
            "Phase 3", "Phase 2", "median", "mPFS", "mOS",
            "ACR20", "PASI-75", "HbA1c", "DOR",
        ]
    )

    query = f"""
        SELECT c.id, c.content, d.ticker, d.company_name, d.title, d.doc_type,
               d.filename, d.date
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE ({keyword_conditions})
    """
    params = []

    if ticker:
        query += " AND d.ticker = %s"
        params.append(ticker.upper())

    if indication:
        query += f" AND c.content ILIKE %s"
        params.append(f"%{indication}%")

    query += " ORDER BY d.date DESC NULLS LAST LIMIT %s"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()

    return [{
        "chunk_id": row[0],
        "content": row[1],
        "ticker": row[2],
        "company_name": row[3],
        "title": row[4],
        "doc_type": row[5],
        "filename": row[6],
        "doc_date": row[7] or "",
    } for row in rows]


def extract_endpoints_from_chunks(client, chunks: list[dict]) -> list[dict]:
    """
    Send a batch of chunks to Claude and get structured endpoint data back.
    """
    # Build the text block from chunks
    text_parts = []
    for i, chunk in enumerate(chunks):
        text_parts.append(
            f"--- Document {i+1}: {chunk['ticker']} | {chunk['title']} "
            f"({chunk['doc_type']}) | Date: {chunk['doc_date']} ---\n"
            f"{chunk['content']}\n"
        )
    full_text = "\n".join(text_parts)

    # Truncate if too long (Claude's context is large but let's be reasonable)
    if len(full_text) > 30000:
        full_text = full_text[:30000]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT + full_text,
            }],
        )

        # Parse the JSON response
        response_text = response.content[0].text.strip()

        # Handle markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

        endpoints = json.loads(response_text)
        if not isinstance(endpoints, list):
            endpoints = [endpoints]

        return endpoints

    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"    Claude extraction error: {e}")
        return []


def store_endpoint(conn, ep: dict, source_chunk: dict) -> bool:
    """
    Insert one endpoint into the clinical_endpoints table.
    Returns True if new, False if duplicate.
    """
    cur = conn.cursor()

    # Required fields
    drug_name = (ep.get("drug_name") or "").strip().lower()
    endpoint_name = (ep.get("endpoint_name") or "").strip()
    indication = (ep.get("indication") or "").strip()
    value = ep.get("value")

    if not drug_name or not endpoint_name or value is None:
        cur.close()
        return False

    try:
        value = float(value)
    except (TypeError, ValueError):
        cur.close()
        return False

    # Build source info
    source_type = source_chunk.get("doc_type", "")
    if "sec" in source_type.lower() or "10-" in source_type.lower():
        source_type = "sec_filing"
    elif "fda" in source_type.lower():
        source_type = "fda_label"
    elif "ir" in source_type.lower() or "presentation" in source_type.lower():
        source_type = "ir_deck"
    else:
        source_type = "publication"

    try:
        cur.execute("""
            INSERT INTO clinical_endpoints (
                drug_name, brand_name, drug_id, company_ticker, company_name,
                target, mechanism, modality,
                trial_name, nct_id, phase,
                indication, indication_detail, line_of_therapy,
                endpoint_name, endpoint_category, value, value_unit, value_type,
                comparator_name, comparator_value, hazard_ratio,
                confidence_interval, p_value,
                enrollment, evaluable_n, population_note,
                dose, schedule, timepoint, median_followup,
                source_type, source_detail, source_ticker, extracted_from,
                extraction_confidence
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s
            )
            ON CONFLICT (drug_name, trial_name, endpoint_name, value_type, dose, timepoint)
            DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = NOW()
        """, (
            drug_name,
            ep.get("brand_name"),
            None,  # drug_id — we'll link later
            ep.get("company_ticker") or source_chunk.get("ticker"),
            ep.get("company_name") or source_chunk.get("company_name"),
            ep.get("target"),
            ep.get("mechanism"),
            ep.get("modality"),
            ep.get("trial_name"),
            ep.get("nct_id"),
            ep.get("phase"),
            indication,
            ep.get("indication_detail"),
            ep.get("line_of_therapy"),
            endpoint_name,
            ep.get("endpoint_category", "efficacy"),
            value,
            ep.get("value_unit", "%"),
            ep.get("value_type", "absolute"),
            ep.get("comparator_name"),
            ep.get("comparator_value"),
            ep.get("hazard_ratio"),
            ep.get("confidence_interval"),
            ep.get("p_value"),
            ep.get("enrollment"),
            ep.get("evaluable_n"),
            ep.get("population_note"),
            ep.get("dose"),
            ep.get("schedule"),
            ep.get("timepoint"),
            ep.get("median_followup"),
            source_type,
            ep.get("source_detail"),
            source_chunk.get("ticker"),
            source_chunk.get("filename"),
            ep.get("extraction_confidence", 0.9),
        ))
        conn.commit()
        cur.close()
        return True

    except Exception as e:
        conn.rollback()
        cur.close()
        if "duplicate" not in str(e).lower():
            print(f"    DB error: {e}")
        return False


def run_extraction(conn, client, tickers: list[str] = None,
                   indication: str = None, dry_run: bool = False,
                   max_chunks: int = 500):
    """Run the full extraction pipeline."""

    print(f"\n{'='*60}")
    print(f"  SatyaBio Endpoint Extractor")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # If tickers specified, process each one
    ticker_list = tickers or [None]  # None = all companies

    total_extracted = 0
    total_stored = 0

    for ticker in ticker_list:
        label = ticker or "ALL"
        print(f"\n  --- {label} ---")

        chunks = find_endpoint_chunks(conn, ticker=ticker, indication=indication,
                                      limit=max_chunks)
        print(f"  Found {len(chunks)} chunks with endpoint keywords")

        if not chunks:
            continue

        # Process in batches
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

            print(f"    Batch {batch_num}/{total_batches} ({len(batch)} chunks)...", end=" ")

            if dry_run:
                print("[dry run — skipping Claude call]")
                continue

            endpoints = extract_endpoints_from_chunks(client, batch)
            total_extracted += len(endpoints)
            print(f"extracted {len(endpoints)} endpoints", end="")

            stored = 0
            for ep in endpoints:
                if store_endpoint(conn, ep, batch[0]):
                    stored += 1
            total_stored += stored
            print(f" -> {stored} new/updated")

            time.sleep(CLAUDE_DELAY)

    print(f"\n{'='*60}")
    print(f"  Extraction complete")
    print(f"  Total endpoints extracted: {total_extracted}")
    print(f"  Total stored/updated: {total_stored}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="SatyaBio Endpoint Extractor — structured clinical data from documents"
    )
    parser.add_argument("--ticker", type=str, help="Comma-separated tickers (e.g., REGN,ABBV)")
    parser.add_argument("--all", action="store_true", help="Process all companies")
    parser.add_argument("--indication", type=str, help="Filter by indication (e.g., 'Atopic Dermatitis')")
    parser.add_argument("--max-chunks", type=int, default=500, help="Max chunks per company (default 500)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without extracting")
    parser.add_argument("--stats", action="store_true", help="Show current extraction stats")
    args = parser.parse_args()

    if not DATABASE_URL:
        print("ERROR: Set NEON_DATABASE_URL in .env")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)

    if args.stats:
        # Reuse the stats function from endpoints_setup
        from endpoints_setup import show_stats
        show_stats(conn)
        conn.close()
        return

    if not ANTHROPIC_API_KEY:
        print("ERROR: Set ANTHROPIC_API_KEY in .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Determine tickers
    tickers = None
    if args.ticker:
        tickers = [t.strip().upper() for t in args.ticker.split(",")]
    elif args.all:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT ticker FROM documents ORDER BY ticker")
        tickers = [row[0] for row in cur.fetchall()]
        cur.close()

    if not tickers and not args.all:
        parser.print_help()
        print("\n  Use --all or --ticker to specify companies")
        sys.exit(1)

    run_extraction(conn, client, tickers=tickers, indication=args.indication,
                   dry_run=args.dry_run, max_chunks=args.max_chunks)

    conn.close()


if __name__ == "__main__":
    main()
