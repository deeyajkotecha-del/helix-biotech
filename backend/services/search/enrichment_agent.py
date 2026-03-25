"""
SatyaBio — Enrichment Agent
==============================
Second agent in the Hunt Globally pipeline: takes raw drug candidates from the
Regional News Miner and enriches them with structured metadata.

Two-layer approach:
  Layer 1: ClinicalTrials.gov API lookup
    - Search by drug name / code name as intervention
    - Extract: phase, sponsor, indication, countries, enrollment, NCT ID, status
    - Fast, free, authoritative for trials that exist on CT.gov

  Layer 2: Claude batch enrichment
    - For candidates that CT.gov can't resolve (too new, pre-IND, regional-only)
    - Claude researches using its training knowledge
    - Extracts: mechanism of action, target, modality, development stage, company

The enriched candidates are stored back in the database and made available
to the RAG pipeline for investor queries.

Usage:
    # Enrich all unenriched candidates
    python3 enrichment_agent.py --enrich

    # Enrich specific drug
    python3 enrichment_agent.py --enrich --drug "BG-68501"

    # Only Layer 1 (CT.gov lookup, no Claude)
    python3 enrichment_agent.py --enrich --no-llm

    # Show enrichment stats
    python3 enrichment_agent.py --status

    # Export enriched candidates as JSON
    python3 enrichment_agent.py --export

Requires in .env:
    ANTHROPIC_API_KEY=sk-ant-...
    NEON_DATABASE_URL=postgresql://...
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

import requests

# ─── Optional imports ─────────────────────────────────────────────────────────

try:
    import psycopg2
    import psycopg2.extras
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

DATABASE_URL = os.getenv("NEON_DATABASE_URL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CTGOV_BASE = "https://clinicaltrials.gov/api/v2/studies"


# ─── Layer 1: ClinicalTrials.gov Lookup ──────────────────────────────────────

def lookup_drug_on_ctgov(drug_name, max_results=10):
    """
    Search ClinicalTrials.gov for a drug candidate by name.
    Tries multiple search strategies:
      1. Exact intervention search (query.intr)
      2. Broad term search (query.term) — catches title/condition mentions
    Returns enriched metadata dict or None.
    """
    # Clean up the drug name for searching
    search_terms = [drug_name]
    # If it's a code like "BG-68501", also try without hyphen
    if "-" in drug_name:
        search_terms.append(drug_name.replace("-", ""))
    # If it's a code like "RMC6236", also try with hyphen
    if not "-" in drug_name and any(c.isdigit() for c in drug_name) and any(c.isalpha() for c in drug_name):
        # Find where letters end and digits begin
        for i, c in enumerate(drug_name):
            if c.isdigit() and i > 0:
                search_terms.append(f"{drug_name[:i]}-{drug_name[i:]}")
                break

    all_studies = []

    for term in search_terms:
        # Strategy 1: intervention search
        try:
            params = {
                "format": "json",
                "query.intr": term,
                "pageSize": max_results,
            }
            resp = requests.get(
                CTGOV_BASE, params=params,
                headers={"User-Agent": "SatyaBio-Enrichment/1.0"},
                timeout=15,
            )
            if resp.ok:
                data = resp.json()
                for study in data.get("studies", []):
                    all_studies.append(study)
        except Exception as e:
            print(f"    [CT.gov] Intervention search error for '{term}': {e}")

        # Strategy 2: broad term search
        try:
            params = {
                "format": "json",
                "query.term": term,
                "pageSize": max_results,
            }
            resp = requests.get(
                CTGOV_BASE, params=params,
                headers={"User-Agent": "SatyaBio-Enrichment/1.0"},
                timeout=15,
            )
            if resp.ok:
                data = resp.json()
                for study in data.get("studies", []):
                    all_studies.append(study)
        except Exception as e:
            print(f"    [CT.gov] Term search error for '{term}': {e}")

    if not all_studies:
        return None

    # Deduplicate by NCT ID
    seen_ncts = set()
    unique_studies = []
    for study in all_studies:
        protocol = study.get("protocolSection", {})
        nct = protocol.get("identificationModule", {}).get("nctId", "")
        if nct and nct not in seen_ncts:
            seen_ncts.add(nct)
            unique_studies.append(study)

    if not unique_studies:
        return None

    # Extract structured data from all matching trials
    trials = []
    for study in unique_studies:
        protocol = study.get("protocolSection", {})
        id_mod = protocol.get("identificationModule", {})
        status_mod = protocol.get("statusModule", {})
        design_mod = protocol.get("designModule", {})
        sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})
        cond_mod = protocol.get("conditionsModule", {})
        interv_mod = protocol.get("armsInterventionsModule", {})
        contact_mod = protocol.get("contactsLocationsModule", {})

        # Extract countries from locations
        countries = set()
        for loc in contact_mod.get("locations", []):
            country = loc.get("country", "")
            if country:
                countries.add(country)

        # Extract interventions
        interventions = []
        for arm in interv_mod.get("interventions", []):
            interventions.append(arm.get("name", ""))

        phases = design_mod.get("phases", [])
        trial_info = {
            "nct_id": id_mod.get("nctId", ""),
            "title": id_mod.get("briefTitle", ""),
            "status": status_mod.get("overallStatus", ""),
            "phase": ", ".join(phases) if phases else "N/A",
            "sponsor": sponsor_mod.get("leadSponsor", {}).get("name", ""),
            "conditions": cond_mod.get("conditions", []),
            "interventions": interventions,
            "countries": sorted(countries),
            "enrollment": design_mod.get("enrollmentInfo", {}).get("count", 0),
            "start_date": status_mod.get("startDateStruct", {}).get("date", ""),
        }
        trials.append(trial_info)

    # Determine the "best" phase (highest) across all trials
    phase_rank = {"PHASE4": 4, "PHASE3": 3, "PHASE2": 2, "PHASE1": 1, "EARLY_PHASE1": 0.5}
    best_phase = "Pre-clinical"
    best_rank = -1
    for t in trials:
        for p in t["phase"].replace(" ", "").split(","):
            rank = phase_rank.get(p.upper().replace(" ", ""), -1)
            if rank > best_rank:
                best_rank = rank
                best_phase = p

    # Aggregate countries and conditions
    all_countries = set()
    all_conditions = set()
    all_sponsors = set()
    for t in trials:
        all_countries.update(t["countries"])
        all_conditions.update(t["conditions"])
        if t["sponsor"]:
            all_sponsors.add(t["sponsor"])

    # Find the lead sponsor (most common)
    lead_sponsor = ""
    if all_sponsors:
        from collections import Counter
        sponsor_counts = Counter(t["sponsor"] for t in trials if t["sponsor"])
        lead_sponsor = sponsor_counts.most_common(1)[0][0] if sponsor_counts else ""

    enriched = {
        "source": "ctgov",
        "num_trials": len(trials),
        "highest_phase": best_phase,
        "lead_sponsor": lead_sponsor,
        "all_sponsors": sorted(all_sponsors),
        "indications": sorted(all_conditions)[:10],  # top 10
        "countries": sorted(all_countries),
        "trials": [
            {
                "nct_id": t["nct_id"],
                "title": t["title"],
                "phase": t["phase"],
                "status": t["status"],
                "sponsor": t["sponsor"],
                "enrollment": t["enrollment"],
            }
            for t in trials[:5]  # top 5 most relevant
        ],
        "enriched_at": datetime.now(timezone.utc).isoformat(),
    }

    return enriched


# ─── Layer 2: Claude Batch Enrichment ─────────────────────────────────────────

ENRICHMENT_PROMPT = """You are a biopharma analyst. Given a drug candidate name that was found in regional biotech news, provide structured metadata about it.

Drug candidate: {drug_name}
Context (from news article): {context}

Respond with ONLY a JSON object (no markdown, no explanation) with these fields:
{{
  "generic_name": "INN or generic name if known, otherwise the code name",
  "brand_name": "brand/trade name if approved, otherwise null",
  "mechanism_of_action": "brief description of MOA (e.g., 'KRAS G12C covalent inhibitor')",
  "target": "molecular target (e.g., 'KRAS G12C', 'PD-L1', 'HER2')",
  "modality": "drug modality (e.g., 'small molecule', 'ADC', 'bispecific antibody', 'CAR-T', 'mRNA')",
  "therapeutic_area": "primary therapeutic area (e.g., 'oncology', 'immunology', 'neuroscience')",
  "indication": "primary indication being studied (e.g., 'NSCLC', 'breast cancer', 'rheumatoid arthritis')",
  "development_stage": "current highest stage (e.g., 'Phase 1', 'Phase 2', 'Phase 3', 'Approved', 'Pre-clinical')",
  "company": "developing company name",
  "company_country": "HQ country of developing company",
  "first_disclosure_year": "year first publicly disclosed, or null if unknown",
  "competitive_landscape": "brief note on competitive context (e.g., '4th KRAS G12C inhibitor to enter Phase 2')",
  "confidence": "high/medium/low — your confidence in this information"
}}

If you don't know a field, set it to null. Be precise — don't guess wildly."""


def enrich_with_claude(drug_name, context="", model="claude-sonnet-4-20250514"):
    """
    Use Claude to enrich a drug candidate with metadata.
    Returns a dict of enriched fields or None on failure.
    """
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        print(f"    [Claude] Anthropic API not available — skipping LLM enrichment for {drug_name}")
        return None

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = ENRICHMENT_PROMPT.format(
        drug_name=drug_name,
        context=context[:500] if context else "No additional context available.",
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Parse JSON from response (handle potential markdown wrapping)
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        enriched = json.loads(text)
        enriched["source"] = "claude"
        enriched["enriched_at"] = datetime.now(timezone.utc).isoformat()
        return enriched

    except json.JSONDecodeError as e:
        print(f"    [Claude] JSON parse error for {drug_name}: {e}")
        return None
    except Exception as e:
        print(f"    [Claude] API error for {drug_name}: {e}")
        return None


def enrich_batch_with_claude(candidates, model="claude-sonnet-4-20250514", delay=0.5):
    """
    Enrich multiple candidates with Claude, with rate limiting.
    Returns list of (candidate, enrichment_data) tuples.
    """
    results = []
    for i, candidate in enumerate(candidates):
        drug_name = candidate.get("drug_name", candidate.get("name", ""))
        context = candidate.get("context", candidate.get("title", ""))

        print(f"    [{i+1}/{len(candidates)}] Enriching '{drug_name}' with Claude...")
        enrichment = enrich_with_claude(drug_name, context=context, model=model)

        if enrichment:
            results.append((candidate, enrichment))
            print(f"      → {enrichment.get('mechanism_of_action', 'unknown MOA')}, "
                  f"{enrichment.get('development_stage', '?')}, "
                  f"{enrichment.get('company', '?')}")
        else:
            results.append((candidate, None))
            print(f"      → Could not enrich")

        if delay and i < len(candidates) - 1:
            time.sleep(delay)

    return results


# ─── Combined Two-Layer Enrichment ────────────────────────────────────────────

def enrich_candidate(candidate, use_llm=True):
    """
    Two-layer enrichment for a single drug candidate:
      1. Try ClinicalTrials.gov first (structured, authoritative)
      2. If CT.gov has no/limited data, use Claude to fill gaps
    Returns a merged enrichment dict.
    """
    drug_name = candidate.get("drug_name", candidate.get("name", ""))
    context = candidate.get("context", candidate.get("title", ""))

    enrichment = {
        "drug_name": drug_name,
        "ctgov": None,
        "claude": None,
        "merged": {},
    }

    # Layer 1: ClinicalTrials.gov
    print(f"  [Layer 1] Searching CT.gov for '{drug_name}'...")
    ctgov_data = lookup_drug_on_ctgov(drug_name)

    if ctgov_data and ctgov_data.get("num_trials", 0) > 0:
        enrichment["ctgov"] = ctgov_data
        print(f"    → Found {ctgov_data['num_trials']} trials, "
              f"highest phase: {ctgov_data['highest_phase']}, "
              f"sponsor: {ctgov_data['lead_sponsor']}")

        # Build merged from CT.gov data
        enrichment["merged"] = {
            "development_stage": ctgov_data["highest_phase"],
            "company": ctgov_data["lead_sponsor"],
            "indication": ", ".join(ctgov_data["indications"][:3]),
            "countries": ctgov_data["countries"],
            "num_trials": ctgov_data["num_trials"],
            "nct_ids": [t["nct_id"] for t in ctgov_data.get("trials", [])],
            "source": "ctgov",
        }
    else:
        print(f"    → No trials found on CT.gov")

    # Layer 2: Claude enrichment (if CT.gov didn't find much, or for additional metadata)
    needs_claude = (
        ctgov_data is None or
        ctgov_data.get("num_trials", 0) == 0 or
        not ctgov_data.get("lead_sponsor")
    )

    if use_llm and needs_claude:
        print(f"  [Layer 2] Enriching '{drug_name}' with Claude...")
        claude_data = enrich_with_claude(drug_name, context=context)

        if claude_data:
            enrichment["claude"] = claude_data
            # Merge: Claude fills gaps that CT.gov didn't cover
            merged = enrichment["merged"]
            if not merged.get("development_stage") or merged["development_stage"] == "Pre-clinical":
                merged["development_stage"] = claude_data.get("development_stage", merged.get("development_stage"))
            if not merged.get("company"):
                merged["company"] = claude_data.get("company", "")
            if not merged.get("indication"):
                merged["indication"] = claude_data.get("indication", "")

            # Claude-only fields
            merged["mechanism_of_action"] = claude_data.get("mechanism_of_action")
            merged["target"] = claude_data.get("target")
            merged["modality"] = claude_data.get("modality")
            merged["therapeutic_area"] = claude_data.get("therapeutic_area")
            merged["company_country"] = claude_data.get("company_country")
            merged["competitive_landscape"] = claude_data.get("competitive_landscape")
            merged["confidence"] = claude_data.get("confidence", "low")
            merged["source"] = "ctgov+claude" if ctgov_data else "claude"
    elif not use_llm and not enrichment["merged"]:
        enrichment["merged"] = {
            "development_stage": "Unknown",
            "company": candidate.get("company", ""),
            "source": "none",
        }

    return enrichment


def enrich_all_candidates(candidates, use_llm=True, delay=1.0):
    """
    Enrich a list of drug candidates using the two-layer approach.
    Returns list of enrichment results.
    """
    results = []
    for i, candidate in enumerate(candidates):
        drug_name = candidate.get("drug_name", candidate.get("name", ""))
        print(f"\n[{i+1}/{len(candidates)}] Enriching: {drug_name}")
        print(f"  Source article: {candidate.get('title', 'N/A')[:80]}")

        result = enrich_candidate(candidate, use_llm=use_llm)
        results.append(result)

        if delay and i < len(candidates) - 1:
            time.sleep(delay)

    return results


# ─── Database Storage ─────────────────────────────────────────────────────────

def ensure_enrichment_table(conn):
    """Create the enriched_candidates table if it doesn't exist."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS enriched_candidates (
            id SERIAL PRIMARY KEY,
            drug_name TEXT NOT NULL,
            canonical_name TEXT,
            ctgov_data JSONB,
            claude_data JSONB,
            merged_data JSONB NOT NULL,
            novelty TEXT DEFAULT 'unknown',
            source_article_title TEXT,
            source_region TEXT,
            enriched_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(drug_name)
        )
    """)
    conn.commit()
    cur.close()


def store_enrichment(conn, candidate, enrichment):
    """Store or update enrichment data in the database."""
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO enriched_candidates
                (drug_name, canonical_name, ctgov_data, claude_data, merged_data,
                 novelty, source_article_title, source_region)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (drug_name)
            DO UPDATE SET
                ctgov_data = EXCLUDED.ctgov_data,
                claude_data = EXCLUDED.claude_data,
                merged_data = EXCLUDED.merged_data,
                enriched_at = NOW()
        """, (
            enrichment["drug_name"],
            candidate.get("canonical_name", enrichment["drug_name"]),
            json.dumps(enrichment.get("ctgov")) if enrichment.get("ctgov") else None,
            json.dumps(enrichment.get("claude")) if enrichment.get("claude") else None,
            json.dumps(enrichment["merged"]),
            candidate.get("novelty", "unknown"),
            candidate.get("title", "")[:200],
            candidate.get("region", "unknown"),
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"    [DB] Error storing enrichment for {enrichment['drug_name']}: {e}")
    finally:
        cur.close()


def get_unenriched_candidates(conn):
    """Get drug candidates from the miner that haven't been enriched yet."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT dc.drug_name, dc.company, dc.region, dc.confidence,
               dc.source_article_title as title, dc.novelty
        FROM drug_candidates dc
        LEFT JOIN enriched_candidates ec ON LOWER(dc.drug_name) = LOWER(ec.drug_name)
        WHERE ec.id IS NULL
          AND dc.novelty = 'novel'
        ORDER BY dc.confidence DESC, dc.mined_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]


def get_enrichment_stats(conn):
    """Get enrichment statistics."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    stats = {}

    cur.execute("SELECT COUNT(*) as total FROM drug_candidates WHERE novelty = 'novel'")
    stats["total_novel"] = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) as total FROM enriched_candidates")
    stats["total_enriched"] = cur.fetchone()["total"]

    cur.execute("""
        SELECT merged_data->>'source' as source, COUNT(*) as count
        FROM enriched_candidates
        GROUP BY merged_data->>'source'
    """)
    stats["by_source"] = {r["source"]: r["count"] for r in cur.fetchall()}

    cur.execute("""
        SELECT merged_data->>'development_stage' as stage, COUNT(*) as count
        FROM enriched_candidates
        GROUP BY merged_data->>'development_stage'
        ORDER BY count DESC
    """)
    stats["by_stage"] = {r["stage"]: r["count"] for r in cur.fetchall()}

    cur.close()
    return stats


# ─── Query Integration ────────────────────────────────────────────────────────

def get_enriched_for_query(query_text, conn=None, limit=20):
    """
    Retrieve enriched candidates relevant to a query.
    Used by the RAG pipeline to add enrichment context to answers.
    """
    own_conn = False
    if not conn:
        if not DB_AVAILABLE or not DATABASE_URL:
            return []
        try:
            conn = psycopg2.connect(DATABASE_URL)
            own_conn = True
        except Exception:
            return []

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if table exists first (avoids crash if scraper hasn't run yet)
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'enriched_candidates'
            )
        """)
        if not cur.fetchone()["exists"]:
            cur.close()
            return []

        # Simple keyword matching for now — could add vector search later
        keywords = [w.lower() for w in query_text.split() if len(w) > 2]

        # Build a flexible search
        conditions = []
        params = []
        for kw in keywords[:5]:  # max 5 keywords
            conditions.append(
                "(LOWER(drug_name) LIKE %s OR LOWER(merged_data->>'indication') LIKE %s "
                "OR LOWER(merged_data->>'target') LIKE %s OR LOWER(merged_data->>'company') LIKE %s)"
            )
            pattern = f"%{kw}%"
            params.extend([pattern, pattern, pattern, pattern])

        if not conditions:
            cur.close()
            return []

        where = " OR ".join(conditions)
        cur.execute(f"""
            SELECT drug_name, canonical_name, merged_data, novelty, source_article_title, enriched_at
            FROM enriched_candidates
            WHERE {where}
            ORDER BY enriched_at DESC
            LIMIT %s
        """, params + [limit])

        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"  [Enrichment DB] Query error: {e}")
        return []
    finally:
        if own_conn and conn:
            conn.close()


def format_enriched_for_claude(enriched_candidates):
    """
    Format enriched candidate data for the synthesis prompt.
    """
    if not enriched_candidates:
        return ""

    lines = [
        "## ENRICHED DRUG CANDIDATES (from Regional News Mining + Enrichment Agent)",
        "These are under-the-radar assets discovered from non-English regional sources.",
        ""
    ]

    for ec in enriched_candidates:
        merged = ec.get("merged_data", {})
        if isinstance(merged, str):
            try:
                merged = json.loads(merged)
            except:
                merged = {}

        name = ec.get("drug_name", "Unknown")
        stage = merged.get("development_stage", "Unknown")
        company = merged.get("company", "Unknown")
        moa = merged.get("mechanism_of_action", "")
        target = merged.get("target", "")
        indication = merged.get("indication", "")
        countries = merged.get("countries", [])
        num_trials = merged.get("num_trials", 0)

        lines.append(f"**{name}** ({stage})")
        if company:
            lines.append(f"  Company: {company}")
        if moa:
            lines.append(f"  MOA: {moa}")
        if target:
            lines.append(f"  Target: {target}")
        if indication:
            lines.append(f"  Indication: {indication}")
        if countries:
            lines.append(f"  Countries: {', '.join(countries[:5])}")
        if num_trials:
            lines.append(f"  Active trials: {num_trials}")
        lines.append("")

    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SatyaBio Enrichment Agent")
    parser.add_argument("--enrich", action="store_true", help="Enrich unenriched candidates")
    parser.add_argument("--drug", type=str, help="Enrich a specific drug name")
    parser.add_argument("--no-llm", action="store_true", help="Skip Claude enrichment (Layer 1 only)")
    parser.add_argument("--status", action="store_true", help="Show enrichment stats")
    parser.add_argument("--export", action="store_true", help="Export enriched candidates as JSON")
    parser.add_argument("--test", action="store_true", help="Test enrichment on sample drugs")
    args = parser.parse_args()

    if args.test:
        # Quick test without database
        test_drugs = [
            {"drug_name": "BG-68501", "title": "BeiGene KRAS G12C inhibitor enters Phase 1"},
            {"drug_name": "garsorasib", "title": "益方生物 D-1553 KRAS G12C results at ASCO"},
            {"drug_name": "LOXO-435", "title": "Lilly LOXO-435 Phase 1 first-in-human"},
        ]
        print("=" * 70)
        print("SatyaBio Enrichment Agent — Test Mode")
        print("=" * 70)

        for candidate in test_drugs:
            print(f"\n{'─' * 60}")
            result = enrich_candidate(candidate, use_llm=not args.no_llm)
            merged = result["merged"]
            print(f"\n  Summary for {result['drug_name']}:")
            print(f"    Stage:      {merged.get('development_stage', '?')}")
            print(f"    Company:    {merged.get('company', '?')}")
            print(f"    MOA:        {merged.get('mechanism_of_action', '?')}")
            print(f"    Target:     {merged.get('target', '?')}")
            print(f"    Indication: {merged.get('indication', '?')}")
            print(f"    Source:     {merged.get('source', '?')}")
        return

    if args.drug:
        # Enrich a specific drug
        candidate = {"drug_name": args.drug, "title": "Manual lookup"}
        result = enrich_candidate(candidate, use_llm=not args.no_llm)
        print(f"\nEnrichment result for {args.drug}:")
        print(json.dumps(result["merged"], indent=2))

        if DB_AVAILABLE and DATABASE_URL:
            try:
                conn = psycopg2.connect(DATABASE_URL)
                ensure_enrichment_table(conn)
                store_enrichment(conn, candidate, result)
                print(f"\n  → Stored in database")
                conn.close()
            except Exception as e:
                print(f"\n  → DB error: {e}")
        return

    if args.status:
        if not DB_AVAILABLE or not DATABASE_URL:
            print("Database not available — cannot show stats")
            return
        conn = psycopg2.connect(DATABASE_URL)
        stats = get_enrichment_stats(conn)
        conn.close()

        print("=" * 50)
        print("SatyaBio Enrichment Agent — Stats")
        print("=" * 50)
        print(f"  Novel candidates:  {stats['total_novel']}")
        print(f"  Enriched:          {stats['total_enriched']}")
        print(f"  Remaining:         {stats['total_novel'] - stats['total_enriched']}")
        print(f"\n  By source:")
        for src, count in stats.get("by_source", {}).items():
            print(f"    {src}: {count}")
        print(f"\n  By stage:")
        for stage, count in stats.get("by_stage", {}).items():
            print(f"    {stage}: {count}")
        return

    if args.export:
        if not DB_AVAILABLE or not DATABASE_URL:
            print("Database not available — cannot export")
            return
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM enriched_candidates ORDER BY enriched_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()

        # Serialize datetime objects
        for row in rows:
            for key, val in row.items():
                if hasattr(val, "isoformat"):
                    row[key] = val.isoformat()

        print(json.dumps(rows, indent=2))
        return

    if args.enrich:
        if not DB_AVAILABLE or not DATABASE_URL:
            print("Database not available — run with --test for non-DB enrichment")
            return

        conn = psycopg2.connect(DATABASE_URL)
        ensure_enrichment_table(conn)

        candidates = get_unenriched_candidates(conn)
        if not candidates:
            print("No unenriched novel candidates found. Run the news miner first!")
            conn.close()
            return

        print(f"Found {len(candidates)} unenriched novel candidates")
        print("=" * 70)

        results = enrich_all_candidates(candidates, use_llm=not args.no_llm)

        # Store results
        stored = 0
        for result in results:
            if result["merged"]:
                # Find the matching candidate
                candidate = next(
                    (c for c in candidates if c["drug_name"] == result["drug_name"]),
                    {"drug_name": result["drug_name"]}
                )
                store_enrichment(conn, candidate, result)
                stored += 1

        print(f"\n{'=' * 70}")
        print(f"Enrichment complete: {stored}/{len(candidates)} candidates enriched")

        conn.close()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
