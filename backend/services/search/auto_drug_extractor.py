"""
SatyaBio — Automated Drug Entity Extractor

Solves the cold-start problem: instead of manually curating drugs for each company,
this pipeline reads embedded document chunks (10-Ks, presentations, trial data) and
uses Claude to extract a structured drug portfolio automatically.

WHY THIS EXISTS:
  The drug entity DB (drugs, drug_aliases, drug_targets tables) powers competitive
  landscape queries: "competitors to alixorexton" → OX2R agonist → narcolepsy landscape.
  But it was manually seeded with ~100 drugs from ~20 companies. We track 94 companies.
  80 of them had ZERO drug intelligence, meaning landscape/comparison queries fail.

HOW IT WORKS:
  1. For each company with embedded documents, gather the richest chunks
     (10-K business sections, investor presentations, clinical trials)
  2. Send to Claude with a structured extraction prompt
  3. Parse the response into drug records with aliases, targets, indications
  4. Upsert into drugs + drug_aliases + drug_targets tables
  5. Auto-generate PubMed search terms

USAGE:
    # Extract drugs for one company
    python3 auto_drug_extractor.py --ticker ALKS

    # Extract drugs for ALL companies missing from the drug entity DB
    python3 auto_drug_extractor.py --all

    # Extract drugs for all companies (refresh everything)
    python3 auto_drug_extractor.py --refresh
"""

import os
import sys
import json
import time
import argparse
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor
import anthropic

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def get_company_chunks(conn, ticker: str, max_chunks: int = 30) -> list[dict]:
    """
    Gather the most informative document chunks for a company.
    Prioritizes: 10-K business sections > investor presentations > trial data > 10-Qs
    Filters out XBRL/financial junk.
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get chunks, ranked by drug-content score.
    # Priority: chunks mentioning drug/pipeline keywords > document type > recency.
    # This skips boilerplate (cover page, forward-looking statements) and XBRL junk.
    cur.execute("""
        SELECT c.content, d.title, d.doc_type, d.ticker, d.company_name,
               c.page_number, c.section_title,
               (
                   CASE WHEN lower(c.content) ~ '(phase [123]|clinical trial|our product|product candidate|pipeline|indication|mechanism|inhibitor|agonist|antagonist|antibody|adc|bispecific|ind-enabling|preclinical|fda approval|approved for|indicated for)' THEN 3 ELSE 0 END
                   + CASE WHEN lower(c.content) ~ '(target|receptor|kinase|protein|pathway|modality|molecule)' THEN 1 ELSE 0 END
                   + CASE WHEN d.doc_type = 'investor_presentation' THEN 2 ELSE 0 END
                   + CASE WHEN d.doc_type = 'sec_10k' THEN 1 ELSE 0 END
               ) AS relevance_score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.ticker = %s
          AND length(c.content) > 200
          AND c.content NOT LIKE '%%us-gaap:%%'
          AND c.content NOT LIKE '%%FairValue%%'
          AND c.content NOT LIKE '%%http://fasb.org%%'
          AND c.content NOT LIKE '%%forward-looking statements%%'
          AND c.content NOT LIKE '%%check mark%%'
          AND c.content NOT LIKE '%%Exchange Act%%'
        ORDER BY relevance_score DESC, d.date DESC NULLS LAST, c.chunk_index
        LIMIT %s
    """, (ticker, max_chunks))

    chunks = [dict(r) for r in cur.fetchall()]
    cur.close()
    return chunks


def extract_drugs_with_claude(ticker: str, company_name: str, chunks: list[dict]) -> list[dict]:
    """
    Use Claude to extract a structured drug portfolio from document chunks.
    Returns a list of drug dicts ready for DB insertion.
    """
    client = anthropic.Anthropic()

    # Build context from chunks
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"[Source {i+1}: {chunk['title']} ({chunk['doc_type']})]:\n{chunk['content']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are an expert biotech investment analyst extracting the complete R&D portfolio of {company_name} (ticker: {ticker}).

TASK: Extract EVERY drug, product, AND early-stage program from the documents below. Investors need the FULL competitive landscape — including unnamed preclinical and IND-enabling programs described only by mechanism (e.g., "our oral CDK2 inhibitor program" or "undisclosed FLT3 asset in IND-enabling studies"). These unnamed programs are often the most valuable competitive intelligence.

WHAT TO INCLUDE:
1. **Named assets** — approved drugs, brand names, INN names, internal codes (e.g., VIVITROL, alixorexton, ALKS-2680)
2. **Unnamed programs by mechanism/target** — if a 10-K or presentation says "we have a preclinical CDK2 inhibitor" or "our undisclosed oral GLP-1 receptor agonist," create an entry with canonical_name = "Undisclosed CDK2 program ({ticker})" and is_named = false
3. **Licensed-in AND licensed-out products** — include with relationship flag
4. **Platform technologies if they generate specific drug candidates** (e.g., "our LNP-delivered mRNA vaccine program for RSV")

WHAT TO EXCLUDE:
- Competitor drugs mentioned only for context (e.g., "our drug competes with Keytruda" — don't list Keytruda)
- Generic drug ingredients unless {company_name} has a proprietary formulation
- Drugs from clinical trials where {company_name} is only testing a competitor drug as a comparator arm
- Pure platform/tech mentions without specific programs (e.g., "we use AI for drug discovery" — too vague)

For EACH entry (named or unnamed), provide:
1. **canonical_name**: Brand name if approved; INN if in clinical trials; internal code if disclosed; "Undisclosed [MECHANISM] program ({ticker})" if unnamed
2. **is_named**: true if disclosed by name/code, false if only described by mechanism
3. **aliases**: ALL other names — codes, brand names, INN, formulation names, previous names
4. **target_moa**: Molecular target or mechanism (e.g., "OX2R agonist", "CDK2 selective inhibitor", "anti-CLDN18.2 ADC")
5. **target_names**: Specific molecular targets as a list (e.g., ["CDK2"], ["FLT3"], ["OX2R"])
6. **indication_primary**: Main indication/disease
7. **indications**: ALL indications being pursued
8. **modality**: small_molecule, antibody, ADC, bispecific, cell_therapy, gene_therapy, vaccine, peptide, oligonucleotide, mRNA, formulation, other
9. **phase**: Discovery, Preclinical, IND-enabling, Phase 1, Phase 1/2, Phase 2, Phase 3, Approved, Marketed
10. **status**: Active, Approved, Marketed, Discontinued, On Hold
11. **mechanism_detail**: 1-2 sentence mechanism description
12. **is_proprietary**: true if {company_name} owns/developed it, false if licensed-in
13. **relationship**: "proprietary", "licensed_out", "licensed_in", "co_developed", "manufactured_for"

Respond ONLY with a JSON array, no other text:
```json
[
  {{
    "canonical_name": "VIVITROL",
    "is_named": true,
    "aliases": ["vivitrol", "naltrexone for extended-release injectable suspension", "naltrexone XR"],
    "target_moa": "Extended-release mu-opioid receptor antagonist",
    "target_names": ["mu-opioid receptor"],
    "indication_primary": "Alcohol Dependence",
    "indications": ["Alcohol Dependence", "Opioid Dependence"],
    "modality": "formulation",
    "phase": "Approved",
    "status": "Marketed",
    "mechanism_detail": "Extended-release injectable naltrexone using Medisorb microsphere technology.",
    "is_proprietary": true,
    "relationship": "proprietary"
  }},
  {{
    "canonical_name": "Undisclosed CDK2 program ({ticker})",
    "is_named": false,
    "aliases": [],
    "target_moa": "Selective CDK2 inhibitor",
    "target_names": ["CDK2"],
    "indication_primary": "HR+ breast cancer",
    "indications": ["HR+ breast cancer"],
    "modality": "small_molecule",
    "phase": "Preclinical",
    "status": "Active",
    "mechanism_detail": "Preclinical selective CDK2 inhibitor program for resistance setting in hormone receptor-positive breast cancer.",
    "is_proprietary": true,
    "relationship": "proprietary"
  }}
]
```

DOCUMENT EXCERPTS:
{context}
"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "max_tokens":
            print(f"  ⚠ Response hit max_tokens for {ticker}; attempting salvage")
            # Try to salvage: truncate at last complete object before the cut
            # Find last '},' before the truncation and close the array
            last_obj_end = text.rfind("},")
            if last_obj_end > 0:
                text = text[:last_obj_end + 1] + "\n]"

        # Parse JSON from response (handle markdown code blocks)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            drugs = json.loads(text)
        except json.JSONDecodeError as je:
            print(f"  ✗ JSON parse error for {ticker}: {je}")
            print(f"  Raw response (first 500 chars): {text[:500]}")
            return []
        print(f"  ✓ Claude extracted {len(drugs)} drugs for {ticker}")
        if len(drugs) == 0:
            print(f"  ⚠ Empty response — raw text: {text[:300]}")
        return drugs

    except Exception as e:
        print(f"  ✗ Claude extraction error for {ticker}: {e}")
        return []


def upsert_extracted_drugs(conn, ticker: str, company_name: str, drugs: list[dict]):
    """
    Insert extracted drugs into the drugs, drug_aliases, and drug_targets tables.
    Uses ON CONFLICT to safely merge with existing data.
    """
    cur = conn.cursor()
    count_new = 0
    count_updated = 0

    for drug in drugs:
        canonical = drug.get("canonical_name", "").strip()
        if not canonical:
            continue

        # Map modality
        modality = drug.get("modality", "small_molecule")
        phase = drug.get("phase", "Unknown")
        status = drug.get("status", "Active")
        indication_primary = drug.get("indication_primary", "")
        indications = drug.get("indications", [])
        mechanism = drug.get("mechanism_detail", drug.get("target_moa", ""))
        target_moa = drug.get("target_moa", "")
        pathway = target_moa  # Use MOA as pathway for now
        is_named = drug.get("is_named", True)
        relationship = drug.get("relationship", "proprietary")

        # Upsert drug
        try:
            # indications is a PostgreSQL ARRAY column — pass Python list directly
            cur.execute("""
                INSERT INTO drugs (canonical_name, company_ticker, company_name,
                    indication_primary, indications, modality, mechanism,
                    pathway, phase_highest, status, is_named, relationship)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (canonical_name, company_ticker) DO UPDATE SET
                    indication_primary = EXCLUDED.indication_primary,
                    indications = EXCLUDED.indications,
                    modality = EXCLUDED.modality,
                    mechanism = EXCLUDED.mechanism,
                    pathway = EXCLUDED.pathway,
                    phase_highest = EXCLUDED.phase_highest,
                    status = EXCLUDED.status,
                    is_named = EXCLUDED.is_named,
                    relationship = EXCLUDED.relationship,
                    updated_at = NOW()
                RETURNING drug_id, (xmax = 0) AS is_new
            """, (canonical, ticker, company_name, indication_primary,
                  indications, modality, mechanism, pathway, phase, status,
                  is_named, relationship))

            row = cur.fetchone()
            drug_id = row[0]
            is_new = row[1]
            if is_new:
                count_new += 1
            else:
                count_updated += 1

            # Add canonical name as alias
            cur.execute("""
                INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current)
                VALUES (%s, %s, 'canonical', TRUE)
                ON CONFLICT (alias) DO NOTHING
            """, (drug_id, canonical))

            # Add all other aliases
            for alias in drug.get("aliases", []):
                alias = alias.strip()
                if not alias or alias.lower() == canonical.lower():
                    continue
                # Determine alias type
                alias_type = "code" if any(c.isdigit() for c in alias) and "-" in alias else "brand"
                if alias.lower() == alias:
                    alias_type = "inn"
                cur.execute("""
                    INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current, notes)
                    VALUES (%s, %s, %s, TRUE, %s)
                    ON CONFLICT (alias) DO NOTHING
                """, (drug_id, alias, alias_type, f"Auto-extracted from {ticker} documents"))

            # Link to targets
            for target_name in drug.get("target_names", []):
                target_name = target_name.strip()
                if not target_name:
                    continue
                # Try exact match first, then partial
                cur.execute("SELECT target_id FROM targets WHERE LOWER(name) = LOWER(%s)", (target_name,))
                trow = cur.fetchone()
                if not trow:
                    cur.execute("SELECT target_id FROM targets WHERE LOWER(name) LIKE LOWER(%s) LIMIT 1",
                                (f"%{target_name}%",))
                    trow = cur.fetchone()
                if trow:
                    cur.execute("""
                        INSERT INTO drug_targets (drug_id, target_id, role, selectivity)
                        VALUES (%s, %s, 'primary', 'selective')
                        ON CONFLICT (drug_id, target_id) DO NOTHING
                    """, (drug_id, trow[0]))

            # Auto-generate PubMed search terms
            _auto_pubmed_terms(cur, drug_id, canonical, drug.get("aliases", []),
                               indication_primary, target_moa)

        except Exception as e:
            print(f"  ⚠ Error inserting {canonical}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    print(f"  ✓ Upserted: {count_new} new, {count_updated} updated for {ticker}")


def _auto_pubmed_terms(cur, drug_id, canonical, aliases, indication, moa):
    """Auto-generate PubMed search terms for a drug."""
    terms = []

    # Drug name terms
    terms.append((drug_id, indication, f'"{canonical}"', "drug"))
    for alias in aliases:
        alias = alias.strip()
        if len(alias) > 3:
            terms.append((drug_id, indication, f'"{alias}"', "drug"))

    # MOA terms
    if moa:
        terms.append((drug_id, indication, f"{moa} clinical trial", "mechanism"))
        if indication:
            terms.append((drug_id, indication, f"{moa} {indication}", "mechanism"))

    for (did, ind, term, ttype) in terms:
        try:
            cur.execute("""
                INSERT INTO drug_pubmed_terms (drug_id, indication, search_term, term_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (did, ind, term, ttype))
        except Exception:
            pass  # Skip duplicates silently


def get_companies_missing_drugs(conn) -> list[tuple]:
    """Find companies that have documents but no drugs in the entity DB.
    Deduplicates on ticker and skips news/feed pseudo-tickers."""
    cur = conn.cursor()
    cur.execute("""
        SELECT d.ticker, MAX(d.company_name) AS company_name
        FROM documents d
        WHERE d.ticker IS NOT NULL
          AND d.ticker NOT IN ('NEWS', 'FDA_BPAC', 'NEWS_FEED', 'FDA')
          AND d.ticker NOT IN (SELECT DISTINCT company_ticker FROM drugs WHERE company_ticker IS NOT NULL)
        GROUP BY d.ticker
        ORDER BY d.ticker
    """)
    result = cur.fetchall()
    cur.close()
    return result


def extract_for_ticker(ticker: str):
    """Extract and populate drugs for a single company."""
    conn = get_conn()

    # Get company name
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT company_name FROM documents WHERE ticker = %s LIMIT 1", (ticker,))
    row = cur.fetchone()
    if not row:
        print(f"  ✗ No documents found for {ticker}")
        return
    company_name = row[0] or ticker
    cur.close()

    print(f"\n{'='*60}")
    print(f"  Extracting drugs for {ticker} — {company_name}")
    print(f"{'='*60}")

    # Gather chunks
    chunks = get_company_chunks(conn, ticker)
    if not chunks:
        print(f"  ✗ No usable chunks for {ticker}")
        return

    print(f"  Found {len(chunks)} chunks across {len(set(c['title'] for c in chunks))} documents")

    # Extract with Claude
    drugs = extract_drugs_with_claude(ticker, company_name, chunks)
    if not drugs:
        print(f"  ✗ No drugs extracted for {ticker}")
        return

    # Print what we found
    for d in drugs:
        aliases_str = ", ".join(d.get("aliases", [])[:3])
        print(f"    • {d['canonical_name']} ({aliases_str}) — {d.get('phase', '?')} — {d.get('indication_primary', '?')}")

    # Upsert into DB
    upsert_extracted_drugs(conn, ticker, company_name, drugs)
    conn.close()


def extract_all_missing():
    """Extract drugs for all companies missing from the entity DB."""
    conn = get_conn()
    missing = get_companies_missing_drugs(conn)
    conn.close()

    print(f"\n{'='*60}")
    print(f"  Found {len(missing)} companies missing drug data")
    print(f"{'='*60}")

    for ticker, company_name in missing:
        try:
            extract_for_ticker(ticker)
            time.sleep(1)  # Rate limit Claude calls
        except Exception as e:
            print(f"  ✗ Failed for {ticker}: {e}")
            continue


def extract_refresh_all():
    """Re-extract drugs for ALL companies (refresh everything)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT ticker FROM documents
        WHERE ticker IS NOT NULL
        ORDER BY ticker
    """)
    tickers = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()

    print(f"\n{'='*60}")
    print(f"  Refreshing drug data for {len(tickers)} companies")
    print(f"{'='*60}")

    for ticker in tickers:
        try:
            extract_for_ticker(ticker)
            time.sleep(1)
        except Exception as e:
            print(f"  ✗ Failed for {ticker}: {e}")
            continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-extract drug entities from embedded documents")
    parser.add_argument("--ticker", type=str, help="Extract drugs for a single company ticker")
    parser.add_argument("--all", action="store_true", help="Extract for all companies missing drug data")
    parser.add_argument("--refresh", action="store_true", help="Re-extract for ALL companies")
    args = parser.parse_args()

    if args.ticker:
        extract_for_ticker(args.ticker.upper())
    elif args.all:
        extract_all_missing()
    elif args.refresh:
        extract_refresh_all()
    else:
        parser.print_help()
