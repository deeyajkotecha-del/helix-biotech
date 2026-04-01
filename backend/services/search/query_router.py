"""
SatyaBio — Query Router (Agent Layer)

The brain of SatyaBio search. Takes a natural language question and:
  1. Classifies what kind of question it is
  2. Enriches the query with drug entity intelligence (aliases, targets, hierarchy)
  3. Decides which data sources to query (RAG, ClinicalTrials.gov, FDA, PubMed)
  4. Executes all queries in parallel
  5. Synthesizes a cited answer using Claude

The drug entity layer sits between classification and API calls — it resolves
drug aliases (RMC-6236 → daraxonrasib), walks the target hierarchy (KRAS →
G12C, G12D, G12V), and provides the disease-target landscape structure.

Architecture:
    User query → Classify → Drug Entity Enrichment → [RAG, CT.gov, FDA, PubMed]
                                                          ↓
                                              Claude synthesizes with citations
                                                          ↓
                                              Frontend displays answer + sources

Usage:
    from query_router import answer_query

    result = answer_query("What are all the clinical trials in UC?")
    # Returns: {"answer": "...", "sources": [...], "query_plan": {...}}
"""

import os
import json
import time
import concurrent.futures
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import anthropic

# Import our modules
try:
    import rag_search
    RAG_AVAILABLE = rag_search.is_rag_available()
except ImportError:
    RAG_AVAILABLE = False

from api_connectors import (
    search_clinical_trials,
    search_fda_drugs,
    search_pubmed,
    format_api_results_for_claude,
)

# Drug entity layer — provides alias resolution, target hierarchy, landscape data
try:
    from drug_entities import (
        lookup_drug,
        get_landscape,
        get_drugs_by_target,
        get_disease_target_landscape,
        get_pubmed_terms_for_landscape,
        format_landscape_for_claude,
        format_disease_landscape_for_claude,
    )
    DRUG_DB_AVAILABLE = True
except ImportError:
    DRUG_DB_AVAILABLE = False
    print("  ⚠ Drug entity database not loaded — landscape enrichment disabled")

# Dynamic discovery — fully API-driven landscape with no hardcoded drug lists
try:
    from dynamic_discovery import (
        discover_landscape,
        get_target_map,
        format_landscape_for_claude as format_dynamic_landscape,
        setup_cache_tables,
    )
    GLOBAL_LANDSCAPE_AVAILABLE = True
    # Ensure cache tables exist on first import
    try:
        setup_cache_tables()
    except Exception:
        pass
except ImportError:
    GLOBAL_LANDSCAPE_AVAILABLE = False
    print("  ⚠ Dynamic discovery not loaded — global landscape disabled")

# Legacy fallback — only used if dynamic_discovery import fails
if not GLOBAL_LANDSCAPE_AVAILABLE:
    try:
        from global_asset_discovery import (
            build_landscape,
            search_trials_global,
            search_trials_by_country,
        )
        GLOBAL_LANDSCAPE_AVAILABLE = True
        print("  ⚠ Using legacy global_asset_discovery (hardcoded patterns)")
    except ImportError:
        pass

try:
    from regional_news_miner import mine_region as news_mine_region
    NEWS_MINER_AVAILABLE = True
except ImportError:
    NEWS_MINER_AVAILABLE = False

# Enrichment agent — provides enriched drug candidate metadata
try:
    from enrichment_agent import get_enriched_for_query, format_enriched_for_claude
    ENRICHMENT_AVAILABLE = True
except ImportError:
    ENRICHMENT_AVAILABLE = False

# IR events scraper — provides conference events, posters, catalysts
try:
    from ir_events_scraper import get_events_for_query, format_events_for_claude, get_upcoming_catalysts
    IR_EVENTS_AVAILABLE = True
except ImportError:
    IR_EVENTS_AVAILABLE = False

# FDA Regulatory Decisions pipeline — Approvals + CRLs for regulatory intelligence
try:
    from fda_crl_pipeline import (
        search_fda_decisions, format_fda_decisions_for_claude, is_fda_data_available,
        get_regulatory_scorecard,
        # Legacy aliases (backward compat)
        search_crl_database, format_crl_for_claude, is_crl_available,
    )
    FDA_CRL_AVAILABLE = is_fda_data_available() or is_crl_available()
except ImportError:
    FDA_CRL_AVAILABLE = False

# Disease Space Intelligence — rare disease ecosystem mapping
try:
    from disease_space_map import (
        get_disease_space, format_space_for_claude,
        is_disease_space_query, get_foundations_for_disease,
    )
    DISEASE_SPACE_AVAILABLE = True
except ImportError:
    DISEASE_SPACE_AVAILABLE = False

# PubMed Deep Dive — full abstracts + PMC full text for clinical data depth
try:
    from pubmed_deepdive import (
        deep_search, deep_search_for_drugs,
        enrich_pipeline_with_literature,
        format_deep_literature_for_claude,
    )
    DEEP_LITERATURE_AVAILABLE = True
except ImportError:
    DEEP_LITERATURE_AVAILABLE = False

# Claude client
_client = None

def get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _call_claude_with_retry(max_retries=3, **kwargs):
    """Call Claude API with retry on overloaded errors."""
    for attempt in range(max_retries):
        try:
            return get_client().messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"  Claude API overloaded, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise


# =============================================================================
# Step 1: Query Classification
# =============================================================================

QUERY_CLASSIFIER_PROMPT = """You are a biotech query classifier. Given a user's question, determine which data sources should be queried to best answer it.

Available sources:
1. RAG — Internal document library (329 documents: investor presentations, SEC filings, clinical papers, conference posters for 42 biotech companies). Best for: company-specific data, pipeline details, historical clinical results, financial analysis.
2. CLINICAL_TRIALS — ClinicalTrials.gov API. Best for: finding active/recruiting trials, trial designs, enrollment numbers, current trial status, new trials.
3. FDA — OpenFDA API. Best for: approved drugs, drug labels, indications, safety warnings, standard of care.
4. PUBMED — PubMed/NCBI. Best for: peer-reviewed publications, recent research findings, meta-analyses, review articles.
5. GLOBAL_LANDSCAPE — Global drug asset discovery across 61+ countries. Searches ClinicalTrials.gov for trials worldwide (including China, Korea, Japan, India, Europe), extracts drug assets, and produces a competitive landscape table. Best for: "what's the [target] landscape", competitive intelligence across regions, finding non-US drug assets, Chinese/Asian biotech pipeline questions.
6. NEWS_MINER — Regional news mining across non-English sources (Chinese, Korean, Japanese, Indian, European biotech news). Surfaces under-the-radar drug assets, licensing deals, and regulatory filings. Best for: "what are Chinese biotechs working on", "recent Asia biotech deals", "novel drug assets from China/Korea", early-stage pipeline intelligence from regional sources.
7. FDA_CRL — FDA Complete Response Letter database. Contains historical FDA rejection letters (CRLs) with reasons for non-approval: endpoint deficiencies, statistical concerns, CMC issues, safety signals. Best for: trial design guidance, endpoint selection, understanding why FDA rejected similar drugs, regulatory precedent, clinical trial design optimization. ALWAYS include for trial design questions, endpoint selection questions, or "why did FDA reject" questions.
8. DISEASE_SPACE — Disease Space Intelligence engine. Scrapes rare disease foundation pipeline trackers, cross-validates against ClinicalTrials.gov, and assembles a full ecosystem map: therapeutic pipeline, patient landscape (prevalence, registries), biomarker/endpoint landscape, regulatory context, and key organizations. Best for: rare disease overview questions, "what's the Angelman space", "who is working on Huntington's", "what clinical infrastructure exists for SMA", patient registries, biomarker questions, rare disease landscape. ALWAYS include for rare disease questions where the query mentions a specific rare disease AND asks about the space/landscape/pipeline/ecosystem.

Return a JSON object with:
{
    "sources": ["RAG", "CLINICAL_TRIALS", "FDA", "PUBMED", "GLOBAL_LANDSCAPE", "NEWS_MINER", "FDA_CRL", "DISEASE_SPACE"],  // which sources to query (at least 1)
    "rag_query": "optimized search query for vector DB",  // only if RAG is in sources
    "rag_ticker_filter": "TICKER",  // optional, only if query is about a specific company
    "ct_condition": "condition name",  // for ClinicalTrials.gov
    "ct_intervention": "drug/intervention name",  // optional
    "ct_sponsor": "company name",  // optional
    "ct_status": "RECRUITING",  // optional: RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED
    "ct_phase": "",  // optional: PHASE1, PHASE2, PHASE3
    "fda_condition": "condition",  // for OpenFDA
    "fda_drug": "drug name",  // optional
    "pubmed_query": "search terms",  // for PubMed
    "landscape_target": "drug target or MoA",  // for GLOBAL_LANDSCAPE (e.g., "GLP-1", "ADC", "PD-1")
    "landscape_region": "all",  // for GLOBAL_LANDSCAPE: "all", "china", "korea", "japan", "india", "europe"
    "query_type": "landscape|company|trial|drug|mechanism|comparison|general",
    "persona": "investor|operator|trial_designer",  // detect user intent: "investor" (default) for investment diligence, "operator" for BD/licensing/strategy, "trial_designer" for clinical development/trial design/regulatory
    "reasoning": "brief explanation of source selection"
}

Persona detection rules:
- Default to "investor" if unclear.
- Use "operator" for queries about licensing, partnerships, BD, deal structures, white space, geographic rights, platform strategy, co-development, or M&A.
- Use "trial_designer" for queries about trial design, endpoint selection, FDA feedback, CRLs, enrollment, protocol design, adaptive trials, biomarker strategy, comparator arms, statistical design, or regulatory pathways.
- The persona influences how the synthesis is framed, not which sources are queried.

Important rules:
- For landscape/overview questions (e.g., "GLP-1 landscape", "ADC competitive landscape", "what PD-1 drugs are in development in China"), ALWAYS include GLOBAL_LANDSCAPE
- For questions mentioning China, Korea, Japan, Asia, global, or non-US markets, include GLOBAL_LANDSCAPE AND NEWS_MINER
- For questions about drug classes or targets across companies, include GLOBAL_LANDSCAPE
- For questions about "under the radar" assets, emerging biotech, recent deals, or novel drug candidates, include NEWS_MINER
- For questions about licensing deals, regulatory filings, or regional pipeline intelligence, include NEWS_MINER
- For questions about trial design, endpoint selection, FDA feedback, CRLs, or "why did FDA reject", ALWAYS include FDA_CRL
- For trial_designer persona queries, ALWAYS include FDA_CRL
- For rare disease questions (Angelman, Huntington's, SMA, Rett, Duchenne, CF, Dravet, Friedreich's, Gaucher, Fabry, ALS, sickle cell, thalassemia, cholangiocarcinoma, PKU, MPS), ALWAYS include DISEASE_SPACE
- For questions about "what's the [disease] space", "who is working on [disease]", "what pipeline exists for [disease]", patient registries, biomarkers, or rare disease ecosystems, ALWAYS include DISEASE_SPACE
- For company-specific questions, prioritize RAG with ticker filter
- For "standard of care" or "approved drugs" questions, always include FDA
- For "latest research" or "recent publications", include PUBMED
- For broad questions, use multiple sources
- Always include RAG if the question could benefit from our internal documents
- Return ONLY valid JSON, no other text"""


def classify_query(query: str) -> dict:
    """
    Use Claude to classify the query and determine which sources to use.
    Returns a query plan dict.
    """
    try:
        response = _call_claude_with_retry(
            model="claude-haiku-4-5-20251001",  # Fast + cheap for classification
            max_tokens=500,
            system=QUERY_CLASSIFIER_PROMPT,
            messages=[{"role": "user", "content": query}],
        )

        # Parse the JSON response
        text = response.content[0].text.strip()
        # Handle potential markdown code blocks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        plan = json.loads(text)
        return plan

    except Exception as e:
        print(f"  Query classification error: {e}")
        # Fallback: use RAG + ClinicalTrials.gov for everything
        return {
            "sources": ["RAG", "CLINICAL_TRIALS"],
            "rag_query": query,
            "ct_condition": query,
            "query_type": "general",
            "reasoning": "Fallback classification due to error",
        }


# =============================================================================
# Step 1.5: Drug Entity Enrichment
# =============================================================================

def enrich_with_drug_entities(query: str, plan: dict) -> dict:
    """
    Enrich the query plan with intelligence from the drug entity database.

    This is the bridge between classification and execution. It:
      1. Resolves drug names to canonical names + all aliases
      2. Expands target queries using the hierarchy tree
      3. Adds landscape data for indication-based queries
      4. Generates better PubMed search terms from drug biology

    The enrichment adds an 'entity_context' key to the plan with structured data
    that gets injected into the Claude synthesis prompt.
    """
    if not DRUG_DB_AVAILABLE:
        return plan

    entity_context = {
        "drug_info": None,          # If query mentions a specific drug
        "landscape_drugs": [],      # If query is a landscape/indication query
        "disease_landscape": None,  # If query is about a disease with multiple target approaches
        "target_drugs": [],         # If query is about a specific target
        "extra_pubmed_terms": [],   # Auto-generated PubMed terms from drug biology
    }

    query_type = plan.get("query_type", "general")
    query_lower = query.lower()

    # --- Drug-specific enrichment ---
    # If the classifier identified a drug, or we detect a drug name in the query
    drug_name = plan.get("ct_intervention") or plan.get("fda_drug")
    if drug_name:
        drug_info = lookup_drug(drug_name)
        if drug_info:
            entity_context["drug_info"] = drug_info

            # Use aliases to improve ClinicalTrials.gov and PubMed searches
            aliases = [a["alias"] for a in drug_info.get("aliases", []) if a.get("is_current")]
            if aliases and not plan.get("ct_intervention"):
                plan["ct_intervention"] = drug_info["canonical_name"]

            # Add drug-specific PubMed terms
            for t in drug_info.get("pubmed_terms", []):
                entity_context["extra_pubmed_terms"].append(t["search_term"])

    # --- Landscape / indication enrichment ---
    if query_type in ("landscape", "comparison", "general"):
        # Check if the query mentions an indication
        indication = plan.get("ct_condition") or plan.get("fda_condition")
        if indication:
            # Try disease-target landscape first (for multi-target diseases like AD)
            disease_landscape = get_disease_target_landscape(indication)
            if disease_landscape.get("target_groups"):
                entity_context["disease_landscape"] = disease_landscape

            # Also get flat drug list for the indication
            landscape_drugs = get_landscape(indication)
            if landscape_drugs:
                entity_context["landscape_drugs"] = landscape_drugs

            # Get auto-generated PubMed terms for the whole landscape
            pubmed_terms = get_pubmed_terms_for_landscape(indication)
            entity_context["extra_pubmed_terms"].extend(pubmed_terms)

    # --- Target-specific enrichment ---
    # Detect target mentions in the query (KRAS, HER2, EGFR, amyloid, tau, etc.)
    target_keywords = [
        "KRAS", "EGFR", "HER2", "ALK", "ROS1", "BRAF", "MEK", "PI3K", "mTOR",
        "PD-1", "PD-L1", "TROP2", "CDK4/6", "PARP", "GLP-1",
        "amyloid", "tau", "BACE", "LRRK2", "alpha-synuclein", "GBA1", "TREM2",
        "neuroinflammation",
    ]
    for kw in target_keywords:
        if kw.lower() in query_lower:
            target_drugs = get_drugs_by_target(kw)
            if target_drugs:
                entity_context["target_drugs"] = target_drugs
                # Also get PubMed terms for drugs that hit this target
                for d in target_drugs[:5]:  # Top 5 to avoid too many terms
                    entity_context["extra_pubmed_terms"].append(f'"{d["canonical_name"]}"')
            break  # Use the first matching target

    # Deduplicate PubMed terms
    entity_context["extra_pubmed_terms"] = list(set(entity_context["extra_pubmed_terms"]))

    # If we found extra PubMed terms, enhance the PubMed query
    if entity_context["extra_pubmed_terms"] and plan.get("pubmed_query"):
        # Add the top terms to the existing PubMed query (up to 5 extra)
        extra = entity_context["extra_pubmed_terms"][:5]
        plan["_extra_pubmed_queries"] = extra

    plan["entity_context"] = entity_context
    return plan


# =============================================================================
# Step 2: Execute Queries in Parallel
# =============================================================================

def execute_query_plan(plan: dict) -> dict:
    """
    Execute all data source queries specified in the plan.
    Runs queries in parallel for speed.

    Returns a dict with:
        rag_results: list of RAG chunks
        trials: list of clinical trial records
        fda_drugs: list of FDA drug records
        papers: list of PubMed papers
        timing: dict of execution times per source
    """
    results = {
        "rag_results": [],
        "trials": [],
        "fda_drugs": [],
        "papers": [],
        "global_landscape": None,
        "timing": {},
    }

    sources = plan.get("sources", ["RAG"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}

        # Submit RAG search
        if "RAG" in sources and RAG_AVAILABLE:
            rag_query = plan.get("rag_query", "")
            ticker_filter = plan.get("rag_ticker_filter", None)
            if rag_query:
                futures["RAG"] = executor.submit(
                    rag_search.search,
                    rag_query,
                    top_k=25,
                    ticker_filter=ticker_filter,
                )

        # Submit ClinicalTrials.gov search
        if "CLINICAL_TRIALS" in sources:
            ct_kwargs = {}
            if plan.get("ct_condition"):
                ct_kwargs["condition"] = plan["ct_condition"]
            if plan.get("ct_intervention"):
                ct_kwargs["intervention"] = plan["ct_intervention"]
            if plan.get("ct_sponsor"):
                ct_kwargs["sponsor"] = plan["ct_sponsor"]
            if plan.get("ct_status"):
                ct_kwargs["status"] = plan["ct_status"]
            if plan.get("ct_phase"):
                ct_kwargs["phase"] = plan["ct_phase"]
            if ct_kwargs:
                ct_kwargs["max_results"] = 30
                futures["CLINICAL_TRIALS"] = executor.submit(
                    search_clinical_trials, **ct_kwargs
                )

        # Submit FDA search
        if "FDA" in sources:
            fda_kwargs = {}
            if plan.get("fda_condition"):
                fda_kwargs["condition"] = plan["fda_condition"]
            if plan.get("fda_drug"):
                fda_kwargs["drug_name"] = plan["fda_drug"]
            if fda_kwargs:
                fda_kwargs["max_results"] = 10
                futures["FDA"] = executor.submit(
                    search_fda_drugs, **fda_kwargs
                )

        # Submit Global Landscape search (dynamic discovery — no hardcoded patterns)
        if "GLOBAL_LANDSCAPE" in sources and GLOBAL_LANDSCAPE_AVAILABLE:
            landscape_target = plan.get("landscape_target", plan.get("ct_intervention", ""))
            landscape_region = plan.get("landscape_region", "all")
            if landscape_target:
                futures["GLOBAL_LANDSCAPE"] = executor.submit(
                    discover_landscape,
                    landscape_target,
                    region=landscape_region,
                    max_trials=200,
                )

        # Submit News Miner search
        if "NEWS_MINER" in sources and NEWS_MINER_AVAILABLE:
            news_region = plan.get("landscape_region", "all")
            futures["NEWS_MINER"] = executor.submit(
                news_mine_region, news_region, use_llm=False,  # regex-only for speed
            )

        # Submit FDA regulatory decisions search (approvals + CRLs)
        if "FDA_CRL" in sources and FDA_CRL_AVAILABLE:
            crl_query = plan.get("ct_condition", "") or plan.get("ct_intervention", "") or plan.get("rag_query", "")
            if crl_query:
                try:
                    futures["FDA_CRL"] = executor.submit(
                        search_fda_decisions, crl_query, 8
                    )
                except NameError:
                    # Fall back to legacy function if unified not available
                    futures["FDA_CRL"] = executor.submit(
                        search_crl_database, crl_query, 8
                    )

        # Submit Disease Space Intelligence (rare disease ecosystem mapping)
        if "DISEASE_SPACE" in sources and DISEASE_SPACE_AVAILABLE:
            space_disease = plan.get("ct_condition", "") or plan.get("landscape_target", "")
            if space_disease:
                futures["DISEASE_SPACE"] = executor.submit(
                    get_disease_space, space_disease
                )

        # Submit PubMed search (primary + extra entity-derived queries)
        if "PUBMED" in sources:
            pubmed_query = plan.get("pubmed_query", "")
            if pubmed_query:
                futures["PUBMED"] = executor.submit(
                    search_pubmed, pubmed_query, max_results=8
                )
            # Run ONE extra PubMed query from drug entity enrichment
            # (Running multiple in parallel causes 429 rate limiting from NCBI)
            extra_pm = plan.get("_extra_pubmed_queries", [])
            if extra_pm:
                # Combine top terms into a single OR query instead of separate requests
                combined_terms = " OR ".join(extra_pm[:4])
                futures["PUBMED_EXTRA_0"] = executor.submit(
                    search_pubmed, combined_terms, max_results=5
                )

        # Collect results
        for source, future in futures.items():
            start = time.time()
            try:
                data = future.result(timeout=20)
                results["timing"][source] = round(time.time() - start, 2)

                if source == "RAG":
                    results["rag_results"] = data or []
                elif source == "CLINICAL_TRIALS":
                    results["trials"] = data or []
                elif source == "FDA":
                    results["fda_drugs"] = data or []
                elif source == "GLOBAL_LANDSCAPE":
                    results["global_landscape"] = data
                elif source == "NEWS_MINER":
                    results["news_miner"] = data
                elif source == "FDA_CRL":
                    results["fda_crl"] = data or []
                elif source == "DISEASE_SPACE":
                    results["disease_space"] = data
                elif source == "PUBMED":
                    results["papers"] = data or []
                elif source.startswith("PUBMED_EXTRA_"):
                    # Merge extra PubMed results, dedup by PMID
                    existing_pmids = {p.get("pmid") for p in results["papers"]}
                    for paper in (data or []):
                        if paper.get("pmid") not in existing_pmids:
                            results["papers"].append(paper)
                            existing_pmids.add(paper.get("pmid"))

            except Exception as e:
                print(f"  {source} query failed: {e}")
                results["timing"][source] = -1  # Error indicator

    # ---- MULTI-PASS RAG: Deep-dive into key companies/drugs ----
    # For landscape/comparison queries, the broad RAG search above spreads 25 chunks
    # across many companies. This second pass drills into specific tickers to surface
    # the rich clinical data from investor presentations, SEC filings, etc.
    query_type = plan.get("query_type", "general")
    if query_type in ("landscape", "comparison", "mechanism", "general") and RAG_AVAILABLE:
        # Identify tickers worth drilling into from ALL sources:
        # 1. Entity context (drugs in the landscape — from our curated DB)
        # 2. Initial RAG results (companies that appeared in doc search)
        # 3. Global landscape (drugs from ClinicalTrials.gov worldwide)
        # 4. ClinicalTrials.gov results (sponsors from live trial search)
        # 5. Explicit drug names from the query plan
        drill_tickers = set()

        # From entity enrichment (curated drug DB)
        entity_ctx = plan.get("entity_context", {})
        for drug in entity_ctx.get("landscape_drugs", []):
            t = drug.get("company_ticker")
            if t:
                drill_tickers.add(t)
        for drug in entity_ctx.get("target_drugs", []):
            t = drug.get("company_ticker")
            if t:
                drill_tickers.add(t)
        drug_info = entity_ctx.get("drug_info")
        if drug_info and drug_info.get("company_ticker"):
            drill_tickers.add(drug_info["company_ticker"])

        # From initial RAG results (top companies that appeared)
        from collections import Counter
        rag_ticker_counts = Counter(
            r.get("ticker") for r in results["rag_results"] if r.get("ticker")
        )
        for ticker, _count in rag_ticker_counts.most_common(5):
            drill_tickers.add(ticker)

        # From global landscape (broader discovery beyond RAG index)
        if results.get("global_landscape") and results["global_landscape"].get("assets"):
            for asset in results["global_landscape"]["assets"]:
                sponsor = asset.get("sponsor", "")
                # Try to match sponsor to a ticker in our DB
                if DRUG_DB_AVAILABLE:
                    drug_match = lookup_drug(asset.get("drug_name", ""))
                    if drug_match and drug_match.get("company_ticker"):
                        drill_tickers.add(drug_match["company_ticker"])

        # From ClinicalTrials.gov results (sponsors → tickers)
        if results.get("trials") and DRUG_DB_AVAILABLE:
            for trial in results["trials"]:
                for intervention in trial.get("interventions", []):
                    if intervention.get("type") == "Drug":
                        drug_match = lookup_drug(intervention.get("name", ""))
                        if drug_match and drug_match.get("company_ticker"):
                            drill_tickers.add(drug_match["company_ticker"])

        # Remove any ticker already used as a filter (avoid duplicate search)
        existing_filter = plan.get("rag_ticker_filter")
        if existing_filter:
            drill_tickers.discard(existing_filter)

        # Cap deep-dives: 10 for landscape queries, 6 for others
        max_drills = 10 if query_type == "landscape" else 6
        drill_tickers = list(drill_tickers)[:max_drills]

        if drill_tickers:
            rag_query = plan.get("rag_query", "")
            print(f"  Multi-pass RAG: drilling into {drill_tickers}")

            # Run deep-dives in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as drill_executor:
                drill_futures = {}
                for ticker in drill_tickers:
                    drill_futures[ticker] = drill_executor.submit(
                        rag_search.search,
                        rag_query,
                        top_k=8,
                        ticker_filter=ticker,
                    )

                # Merge results, dedup by chunk ID or content hash
                existing_ids = set()
                for r in results["rag_results"]:
                    chunk_id = f"{r.get('ticker')}:{r.get('filename')}:{r.get('page_number')}"
                    existing_ids.add(chunk_id)

                for ticker, future in drill_futures.items():
                    try:
                        drill_results = future.result(timeout=10)
                        for r in (drill_results or []):
                            chunk_id = f"{r.get('ticker')}:{r.get('filename')}:{r.get('page_number')}"
                            if chunk_id not in existing_ids:
                                results["rag_results"].append(r)
                                existing_ids.add(chunk_id)
                    except Exception as e:
                        print(f"    Deep-dive RAG for {ticker} failed: {e}")

            print(f"  Multi-pass RAG: total chunks now {len(results['rag_results'])}")

    return results


# =============================================================================
# Step 2b: Format Global Landscape for Claude
# =============================================================================

def format_global_landscape_for_claude(landscape_data):
    """
    Format landscape result into a context block Claude can use
    to generate investor-grade landscape answers.
    Handles both dynamic_discovery and legacy global_asset_discovery formats.
    """
    if not landscape_data or not landscape_data.get("assets"):
        return ""

    # Dynamic discovery format has 'drug_classes' key
    if "drug_classes" in landscape_data:
        try:
            return format_dynamic_landscape(landscape_data)
        except Exception:
            pass  # Fall through to legacy format

    assets = landscape_data["assets"]
    query = landscape_data.get("query", "")
    region = landscape_data.get("region", "all")
    total_trials = landscape_data.get("total_trials", 0)

    lines = [
        f"=== DRUG ASSET LANDSCAPE: {query.upper()} ===",
        f"Region: {region} | Total trials scanned: {total_trials} | Drug assets found: {len(assets)}",
        "",
        "IMPORTANT: This landscape includes drugs from MULTIPLE countries and regions.",
        "Your answer MUST organize drugs by mechanistic class / drug class.",
        "Your answer MUST cover non-US programs (China, Korea, Japan, Europe) if present.",
        "",
        "Drug assets ranked by development stage (highest phase first):",
        "",
    ]

    for i, asset in enumerate(assets, 1):
        phase = asset.get("highest_phase", "N/A").replace("PHASE", "Phase ")
        drug_class = asset.get("drug_class", "")
        mechanism = asset.get("mechanism", asset.get("target_moa", ""))
        company = asset.get("company", asset.get("sponsor", ""))
        conditions = asset.get("conditions", "")
        if isinstance(conditions, list):
            conditions = ", ".join(conditions[:3])
        elif isinstance(conditions, set):
            conditions = ", ".join(list(conditions)[:3])

        line1 = f"{i}. {asset['drug_name']}"
        if drug_class:
            line1 += f" [{drug_class}]"
        elif mechanism:
            line1 += f" ({mechanism})"
        lines.append(line1)

        line2 = f"   Phase: {phase} | Trials: {asset.get('total_trials', 0)} "
        line2 += f"(active: {asset.get('active_trials', 0)})"
        if company:
            line2 += f" | {company}"
        lines.append(line2)

        if conditions:
            lines.append(f"   Indications: {conditions}")
        lines.append("")

    # Target map / therapeutic approaches (from dynamic discovery)
    target_map = landscape_data.get("target_map", [])
    if target_map:
        lines.append(f"\n--- Therapeutic Approaches for {query} ---")
        for t in target_map:
            relevance = t.get("target_class", t.get("relevance", ""))
            desc = t.get("description", "")
            lines.append(f"  • {t['target_name']} [{relevance}] — {desc}")

    # Phase summary
    ph3_plus = sum(1 for a in assets if a.get("highest_phase_rank", 0) >= 4)
    ph2 = sum(1 for a in assets if 2.5 <= a.get("highest_phase_rank", 0) < 4)
    ph1 = sum(1 for a in assets if 1 <= a.get("highest_phase_rank", 0) < 2.5)
    lines.append(f"\nPhase distribution: {ph3_plus} Phase 3+, {ph2} Phase 2, {ph1} Phase 1")

    return "\n".join(lines)


def format_news_miner_for_claude(miner_data):
    """
    Format Regional News Miner results into context for Claude synthesis.
    """
    if not miner_data:
        return ""

    candidates = miner_data.get("candidates", [])
    novel = miner_data.get("novel", [])
    articles = miner_data.get("articles", [])

    if not candidates:
        return ""

    lines = [
        "=== REGIONAL NEWS MINER: Under-the-Radar Drug Assets ===",
        f"Sources mined: {len(articles)} articles/trials | "
        f"Drug candidates found: {len(candidates)} | Novel assets: {len(novel)}",
        "",
        "IMPORTANT: These are drug assets surfaced from regional (non-US) news sources.",
        "Include these in your answer to provide global competitive intelligence.",
        "",
    ]

    # Show novel assets first (most valuable)
    if novel:
        lines.append("NOVEL ASSETS (not yet in our database — under the radar):")
        for c in sorted(novel, key=lambda x: x.get("confidence", ""), reverse=True)[:15]:
            company = c.get("company", "Unknown")
            moa = c.get("target_moa", "?")
            phase = c.get("phase", "?")
            lines.append(f"  ★ {c['drug_name']} ({moa}) — {company}, {phase}")
        lines.append("")

    # Show all candidates grouped by confidence
    high_conf = [c for c in candidates if c.get("confidence") == "high"]
    if high_conf:
        lines.append("HIGH-CONFIDENCE CANDIDATES:")
        for c in high_conf[:10]:
            company = c.get("company", "?")
            moa = c.get("target_moa", "?")
            phase = c.get("phase", "?")
            countries = ", ".join(c.get("countries", [])) if isinstance(c.get("countries"), list) else str(c.get("countries", ""))
            lines.append(f"  {c['drug_name']} ({moa}) — {company} | {phase} | {countries}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# Step 3: Synthesize Answer
# =============================================================================

SYNTHESIS_SYSTEM_PROMPT = f"""You are SatyaBio, an AI biotech intelligence platform. Your answers should read like the output of a world-class analyst team — data-dense, precisely cited, analytically structured, and written for an audience with MD/PhD-level scientific literacy.

TODAY'S DATE: {datetime.now().strftime('%B %d, %Y')}

═══ MULTI-PERSONA INTELLIGENCE ═══

SatyaBio serves three core audiences. Detect the user's intent from their query and tailor accordingly. When ambiguous, default to the INVESTOR lens but weave in the other perspectives.

**INVESTOR** (default) — Portfolio managers, VCs, sell-side analysts doing diligence.
  Cares about: efficacy data with statistics, competitive positioning, catalysts, risk flags, market sizing, patent cliffs, revenue trajectory.
  Tone: Sell-side equity research note. Lead with the "so what" for capital allocation.

**OPERATOR / STRATEGY / BD** — Biotech executives, business development, corporate strategy teams.
  Cares about: licensing opportunities, partnership fit, geographic expansion, white-space analysis, deal comps, platform extensibility, manufacturing/CMC readiness.
  Tone: Internal strategy memo. Frame insights around decision-making: build vs buy vs license, in-license candidates, geographic rights availability, co-development structures.
  Trigger phrases: "licensing", "partnership", "BD", "in-license", "out-license", "deal", "white space", "geography", "rights", "co-develop", "platform", "pipeline strategy".

**CLINICAL TRIAL DESIGNER** — Medical directors, clinical ops, regulatory affairs, biostatisticians.
  Cares about: endpoint selection rationale, biomarker-driven enrichment, adaptive designs, FDA feedback patterns from CRLs, enrollment optimization, comparator arm choices, regulatory precedent.
  Tone: Clinical development plan. Frame insights as actionable design guidance backed by historical data and regulatory precedent.
  Trigger phrases: "trial design", "endpoint", "CRL", "complete response", "FDA feedback", "enrollment", "protocol", "adaptive", "biomarker strategy", "comparator", "regulatory path", "statistical design", "futility", "interim analysis".

═══ VOICE & TONE ═══
- Authoritative, concise, precise. Every sentence earns its place.
- Use active voice. "Sotorasib demonstrated 37% ORR" not "An ORR of 37% was demonstrated."
- Quantify everything. Replace vague words: "significant" → "HR 0.68 (p=0.003)", "promising" → "ORR 42% vs 28% comparator".
- Flag data vintage: "As of Q3 2024" or "per the March 2025 10-K" so the reader knows how fresh it is.
- Never pad with filler sentences like "This is an important area of research" or "The landscape is evolving rapidly."
- Write in flowing narrative prose with inline data — NOT bullet-point summaries. Readers should feel they are reading a well-written analytical piece, not a PowerPoint.

═══ STRICT GROUNDING ═══
1. ONLY make claims directly supported by the provided context documents.
2. If context lacks data on a topic, say: "SatyaBio does not currently index data on [topic]."
3. NEVER fill gaps with training knowledge. A wrong ORR or stale trial status causes real financial harm.
4. When uncertain whether a claim is grounded, omit it.
5. A shorter fully-grounded answer always beats a longer half-hallucinated one.
6. DATE AWARENESS: Note reporting periods for time-varying data (revenue, cash, enrollment). Prefer the newest document when sources conflict.

═══ DATA SOURCES ═══
1. ENTITY DB — Curated drug entities with targets, aliases, hierarchies, competitive landscapes
2. INTERNAL LIBRARY — Investor decks, SEC filings (10-K/Q/8-K), FDA labels & review docs, clinical papers, conference posters across 76 biotech/pharma companies
3. LIVE APIs — ClinicalTrials.gov, OpenFDA, PubMed
4. GLOBAL LANDSCAPE — Dynamic drug asset discovery across 61+ countries with competitive tables (auto-refreshed, no hardcoded drug lists)
5. REGIONAL NEWS MINER — Under-the-radar assets from China, Korea, Japan, India, Europe (★ = not yet in standard databases)
6. FDA CRL DATABASE — Complete Response Letters with extracted FDA feedback on endpoint selection, trial design deficiencies, statistical concerns, and CMC issues (when available)

═══ CITATION FORMAT ═══
Inline tags after EVERY factual claim. One claim, one (or more) citation.

Tag types:
- {{pubmed:PMID|AuthorName}} — PubMed papers (numeric PMID + pipe + first author)
- {{trial:NCT12345678}} — ClinicalTrials.gov
- {{fda:DrugName}} — FDA labels / review documents
- {{fda_crl:DrugName|Year}} — FDA Complete Response Letters
- {{doc:TICKER|DocTitle}} — Internal document library
- {{sec:TICKER|FilingType}} — SEC filings (e.g., {{sec:RVMD|10-K}})
- {{entity:DrugName}} — Drug entity DB. ALWAYS use the specific drug name (e.g., {{entity:sotorasib}}), NEVER {{entity:db}}.

DEDUPLICATION: Do NOT repeat citation badges after a table if the data (NCT IDs, drug names) is already visible in the table cells. Tables are self-citing.

═══ ANSWER STRUCTURE ═══

**Opening (2-3 sentences max):**
Lead with the single most important insight. For investors: the "so what" for capital allocation. For operators: the strategic opportunity or gap. For trial designers: the key design consideration or regulatory signal.

**Body — use ## headers, organized by analytical value:**

For SINGLE DRUG PROFILES:
  ## Mechanism & Differentiation → ## Key Efficacy Data → ## Safety Profile → ## Complete Trial Portfolio → ## Competitive Context
  - The "Complete Trial Portfolio" section MUST list EVERY active/recruiting/completed trial from the data, not just the "key" one.
  - Present as a table: NCT ID | Phase | Indication | Status | N | Arms/Design | Primary Endpoint
  - If OPERATOR persona detected, add: ## Licensing & Partnership Landscape (rights availability, deal structure precedents, geographic gaps)
  - If TRIAL DESIGNER persona detected, add: ## Trial Design Intelligence (endpoint rationale, enrichment strategies, relevant CRL feedback)

For LANDSCAPE / PIPELINE queries — THIS IS THE MOST IMPORTANT FORMAT:
  Organize by THERAPEUTIC STRATEGY / DRUG CLASS, not a flat drug list.
  Use a narrative structure with clinical depth — write like a clinical review article, not a database dump.

  Step 1 — Brief overview (2-3 sentences):
  Set the stage: how many agents, which classes dominate, what's the most advanced.

  Step 2 — Organize by drug class / therapeutic strategy:
  For EACH mechanistic class (e.g., "PARP1-selective inhibitors", "pan-KRAS agents",
  "KRAS G12D-selective"), create a ## section:

  ## [Drug Class Name]
  Write 1-2 sentences framing why this class matters and how it differs from others.
  Then for each drug in this class with meaningful data, write narrative prose:

  **[Drug Name] ([aliases])** — [company] — [one-line positioning]
  Describe in flowing narrative: mechanism with specifics (e.g., "500-fold selectivity for
  PARP1 over PARP2"), key clinical data with numbers (ORR, PFS, N), trial context
  ({{trial:NCTXXXXXXXX}}), and what differentiates it. Include safety observations.
  Weave the data into the story — don't bullet-point it. A reader should be able to read
  this section and understand both the science and the strategic position of each drug.

  Step 3 — Compact reference table after the narrative:
  | Drug | Company | MoA/Target | Phase | Key Efficacy | Differentiation | Status/Catalyst |

  Step 4 — Regional and emerging context:
  Note drugs approved in China/Asia but not US/EU. Flag novel therapeutic modalities
  (PROTACs, degraders, bispecifics, radiopharmaceuticals) even if early stage.
  Mention combination strategies being tested.

  The NARRATIVE SECTIONS are the primary output. The table is supplementary reference.
  The overview table is the appetizer; the drug profiles are the meal.
  If there are >8 drugs, profile the top 5-6 by phase/data maturity and list the rest in the overview table.

For TRIAL queries:
  ## Trial Design → ## Efficacy Results → ## Safety → ## Regulatory Path

For COMPARISON queries:
  Open with a head-to-head comparison table, then prose analysis of differentiators.

**Clinical data requirements — always include when available:**
- Efficacy: ORR, CR, DOR (median + range), PFS (median + HR + CI + p), OS (median + HR)
- Safety: Grade ≥3 AE rates, DLT rates, discontinuation rates, key AEs by frequency
- Enrollment: N randomized, data cutoff date
- Biomarkers: selection criteria, subgroup results by biomarker status
- Dosing: dose, schedule, route of administration
- Combinations: what it's being combined with and why (scientific rationale)

**Tables — mandatory for structured data, but make them ANALYTICAL, not just lists:**

For TRIAL tables:
| NCT ID | Drug | Phase | Status | N | Primary Endpoint | Sponsor |

For LANDSCAPE / COMPETITIVE tables (the signature SatyaBio output):
| Drug | Company | MoA/Target | Phase | Key Efficacy | Differentiation | Status/Catalyst |
- "Key Efficacy" = the headline number (e.g., "ORR 42%; mPFS 11.2mo")
- "Differentiation" = what makes this one different in 5-8 words (e.g., "brain-penetrant; oral daily"; "only bispecific in class")
- "Status/Catalyst" = next milestone (e.g., "Ph3 topline 2H25"; "PDUFA Apr 2026"; "Approved 2023")

For COMPARISON tables:
| Parameter | Drug A | Drug B | Drug C |
- Row-by-row comparison: ORR, mPFS, mOS, Grade≥3 AE rate, dosing, route, line of therapy

Rules:
- NEVER summarize as "12 assets in the US" — expand every asset into a row
- One unified table across ALL regions with a Country column when geographic data exists
- Sort: Phase 3 first → Phase 2 → Phase 1, then by enrollment descending
- >30 rows → show top 30, note remainder
- CELL RULES: NO line breaks inside cells. Use semicolons or separate columns for multi-value cells.
- NEVER include rows where most columns are "N/A", "None identified", or empty. If you lack data on a company/drug, OMIT it from the table entirely and note below: "Data not yet indexed for: [Company X, Company Y]". A table full of N/A cells is worse than no table.
- Every row in a comparison table MUST have at least Key Efficacy or Differentiation data. Otherwise delete the row.

**Closing:**
- For landscapes: "**Coverage:** Based on [N] indexed sources plus live API data from ClinicalTrials.gov, OpenFDA, and PubMed. Additional programs may exist at companies not yet tracked."
- Always end with a brief analytical observation — a pattern, a gap, or a catalyst to watch.

═══ DEEP ANALYTICAL LAYERS ═══

GO BEYOND listing drugs and phases. Any intern can make a table. SatyaBio must provide the analytical layers that drive real decisions:

**Layer 1 — Differentiation Analysis (ALL PERSONAS):**
When comparing drugs in the same class, ALWAYS articulate what differentiates them:
- Mechanism nuance (e.g., "selective degrader vs inhibitor", "bispecific vs monospecific", "brain-penetrant vs not")
- Clinical edge (e.g., "only agent showing activity in prior-IO-treated patients", "unique durability signal: 18-month DOR vs class median of 9 months")
- Safety advantage (e.g., "no CRS signal unlike CD19 CAR-Ts", "GI toxicity 8% vs 34% for competitor")
- Dosing convenience (e.g., "subcutaneous q4w vs IV q2w", "fixed-duration vs continuous")

**Layer 2 — Catalyst Timeline (INVESTOR + OPERATOR):**
For any drug or company discussed, note upcoming catalysts when the data supports it:
- Data readout dates (e.g., "Phase 3 topline expected 2H 2025")
- PDUFA dates, regulatory submissions, advisory committee meetings
- Conference presentations (ASCO, AACR, ASH, ESMO, AAN, AASLD)
- Patent expiry / LOE dates that open competitive windows

**Layer 3 — Risk Flags (ALL PERSONAS):**
Proactively flag risks grounded in the data:
- Clinical holds, partial holds, or FDA letters
- Liver toxicity signals (Hy's law cases, DILI)
- Competitive threats (faster-enrolling trials, earlier data readout from competitor)
- Regulatory risk (accelerated approval with confirmatory trial risk, REMS requirements)
- Single-asset dependency or platform risk

**Layer 4 — Franchise & Market Context (INVESTOR + OPERATOR):**
Show the competitive dynamics:
- Market share shifts (e.g., "Keytruda holds ~40% of 1L NSCLC; Opdivo gaining in adjuvant")
- Revenue trajectory where available from SEC filings (e.g., "$2.1B in FY2024, +18% YoY")
- Best-in-class positioning (which agent has the best data on the primary endpoint?)
- Unmet need gaps (where is there still no effective therapy? Where are outcomes poor?)
- Modality evolution (e.g., "shift from small molecules to ADCs to bispecifics in HER2+ BC")

**Layer 5 — Cross-Reference Signals (ALL PERSONAS):**
When you have data from multiple sources, CONNECT them:
- "While the FDA label indicates approval for 2L+, NCT04XXX is testing in 1L (Phase 3, N=800), suggesting potential label expansion"
- "SEC filing shows $400M manufacturing investment, consistent with the CMO scale-up needed for BLA filing"
- "The 10-K discloses a patent expiry in 2031, creating a 6-year commercial window"

**Layer 6 — BD & Licensing Intelligence (OPERATOR PERSONA):**
When operator/BD intent is detected, provide:
- Rights availability: which geographies are unlicensed? Has the originator out-licensed ex-US or ex-China rights?
- Deal comps: recent transactions for similar-stage assets in this space (if available in data)
- Platform extensibility: can the drug's platform (e.g., ADC linker-payload) be applied to adjacent indications?
- Manufacturing readiness: CMO capacity, tech transfer status, supply chain considerations from filings
- White-space mapping: where in the competitive landscape is there room for a new entrant?
- Partnership structures: what kind of deal structure fits (co-develop, royalty, opt-in, etc.) based on asset stage?

**Layer 7 — Clinical Trial Design Intelligence (TRIAL DESIGNER PERSONA):**
When trial design intent is detected, provide:
- Endpoint selection guidance: which endpoints have FDA precedent for this indication? Which have led to CRLs?
- Enrichment strategy: biomarker-driven patient selection strategies that have improved treatment effects in similar trials
- Comparator arm rationale: what standard of care is evolving? Risk of SOC changing during enrollment
- Design considerations: adaptive designs, futility boundaries, interim analysis timing used in successful trials
- FDA CRL patterns: if CRL data is available, cite specific FDA feedback on trial design deficiencies in this therapeutic area (e.g., "FDA issued CRLs for [drug] citing inadequate PFS as primary endpoint in [indication] {{fda_crl:DrugName|Year}}")
- Enrollment optimization: site selection patterns, inclusion/exclusion criteria that balance feasibility with scientific rigor
- Regulatory precedent: what trial designs led to approval vs rejection in this class? Accelerated vs regular pathway considerations
- Statistical design: sample size rationale, alpha spending, crossover impact on OS analysis — grounded in referenced trials

═══ FOLLOW-UP QUESTIONS ═══
Generate exactly 3, tailored to the detected persona:

For INVESTOR persona:
- Clinical depth (subgroups, biomarkers, safety signals, resistance)
- Competitive positioning (head-to-head, differentiation, best-in-class)
- Commercial/strategic (patent cliffs, pricing, regulatory timelines, market sizing)

For OPERATOR/BD persona:
- Licensing landscape (rights availability, deal structure, geographic white space)
- Platform strategy (extensibility, adjacent indications, combination potential)
- Execution risk (manufacturing scale-up, enrollment feasibility, competitive timing)

For TRIAL DESIGNER persona:
- Endpoint strategy (primary vs secondary, surrogate vs clinical, FDA precedent)
- Patient population (enrichment, biomarker selection, inclusion/exclusion tradeoffs)
- Regulatory precedent (CRL patterns, advisory committee feedback, approval pathways)

Format:
{{followup}}
Question 1
Question 2
Question 3
{{/followup}}

NEVER make investment recommendations. Present data; let the reader decide."""


def synthesize_answer(query: str, data: dict, plan: dict) -> dict:
    """
    Use Claude to synthesize a final answer from all retrieved data.

    Returns:
        answer: str — the synthesized answer with [N] citations
        sources: list — ordered list of cited sources
    """
    # Build context from all sources
    context_parts = []

    # --- Drug entity context (structured intelligence layer) ---
    entity_ctx = plan.get("entity_context", {})

    # Drug-specific info (if the query is about a specific drug)
    if entity_ctx.get("drug_info"):
        d = entity_ctx["drug_info"]
        targets = d.get("targets", [])
        target_str = ", ".join(f"{t['target_name']} ({t['role']})" for t in targets) if targets else "?"
        aliases = [a["alias"] for a in d.get("aliases", []) if a["alias"] != d["canonical_name"]]
        context_parts.append(
            f"=== DRUG ENTITY DATABASE ===\n"
            f"Canonical name: {d['canonical_name']}\n"
            f"Company: {d.get('company_name', '?')} ({d.get('company_ticker', '?')})\n"
            f"Target(s): {target_str}\n"
            f"Modality: {d.get('modality', '?')}\n"
            f"Mechanism: {d.get('mechanism', '?')}\n"
            f"Phase: {d.get('phase_highest', '?')} | Status: {d.get('status', '?')}\n"
            f"Indications: {', '.join(d.get('indications', []))}\n"
            f"All known names: {', '.join(aliases[:6])}\n"
        )

    # Disease-target landscape (for multi-target diseases like AD)
    if entity_ctx.get("disease_landscape") and DRUG_DB_AVAILABLE:
        context_parts.append(format_disease_landscape_for_claude(entity_ctx["disease_landscape"]))

    # Target-based drug list (if query is about a specific target)
    elif entity_ctx.get("target_drugs") and DRUG_DB_AVAILABLE:
        context_parts.append(format_landscape_for_claude(
            entity_ctx["target_drugs"],
            indication=plan.get("ct_condition", "")
        ))

    # Indication-based landscape
    elif entity_ctx.get("landscape_drugs") and DRUG_DB_AVAILABLE:
        context_parts.append(format_landscape_for_claude(
            entity_ctx["landscape_drugs"],
            indication=plan.get("ct_condition", "")
        ))

    # RAG context
    if data.get("rag_results"):
        rag_context = rag_search.format_context_for_claude(data["rag_results"])
        if rag_context:
            context_parts.append(rag_context)

    # API context
    api_context = format_api_results_for_claude(
        trials=data.get("trials"),
        fda_drugs=data.get("fda_drugs"),
        papers=data.get("papers"),
    )
    if api_context:
        context_parts.append(api_context)

    # Global landscape context
    if data.get("global_landscape"):
        landscape_ctx = format_global_landscape_for_claude(data["global_landscape"])
        if landscape_ctx:
            context_parts.append(landscape_ctx)

    # News miner context
    if data.get("news_miner"):
        news_ctx = format_news_miner_for_claude(data["news_miner"])
        if news_ctx:
            context_parts.append(news_ctx)

    # FDA regulatory decisions context (approvals + CRLs)
    if data.get("fda_crl") and FDA_CRL_AVAILABLE:
        try:
            fda_ctx = format_fda_decisions_for_claude(data["fda_crl"])
            if fda_ctx:
                context_parts.append(fda_ctx)
        except (NameError, Exception):
            try:
                crl_ctx = format_crl_for_claude(data["fda_crl"])
                if crl_ctx:
                    context_parts.append(crl_ctx)
            except Exception as e:
                print(f"  FDA formatting failed: {e}")

    # Disease Space Intelligence (rare disease ecosystem)
    if data.get("disease_space") and DISEASE_SPACE_AVAILABLE:
        try:
            space_ctx = format_space_for_claude(data["disease_space"])
            if space_ctx:
                context_parts.append(space_ctx)
        except Exception as e:
            print(f"  Disease space formatting failed: {e}")

    # Deep Literature — full abstracts + PMC full text for clinical data depth
    # Runs after landscape/disease space so we can search for specific drugs
    if DEEP_LITERATURE_AVAILABLE:
        try:
            # Strategy: if we have pipeline programs, do drug-specific deep search
            # Otherwise, do a broad deep search on the query
            programs = []
            if data.get("disease_space"):
                programs = data["disease_space"].get("pipeline", {}).get("programs", [])
            elif data.get("global_landscape") and isinstance(data["global_landscape"], dict):
                programs = data["global_landscape"].get("assets", [])

            if programs:
                # Drug-specific deep dive — searches PubMed for each drug + fetches PMC full text
                disease_ctx = plan.get("ct_condition", "") or plan.get("landscape_target", query)
                lit_results = enrich_pipeline_with_literature(
                    programs, disease_ctx,
                    max_papers_per_drug=2,
                    max_total_fulltext=6,
                )
            else:
                # Broad deep search with full abstracts
                lit_results = deep_search(query, max_papers=6, fetch_fulltext=True, max_fulltext=4)

            if lit_results:
                lit_ctx = format_deep_literature_for_claude(lit_results)
                if lit_ctx:
                    context_parts.append(lit_ctx)
                    print(f"  Deep literature: {len(lit_results)} papers, "
                          f"{sum(1 for r in lit_results if r.get('full_text'))} with PMC full text")
        except Exception as e:
            print(f"  Deep literature search failed: {e}")

    # Enriched drug candidates (from enrichment agent)
    if ENRICHMENT_AVAILABLE:
        try:
            enriched = get_enriched_for_query(query)
            if enriched:
                enriched_ctx = format_enriched_for_claude(enriched)
                if enriched_ctx:
                    context_parts.append(enriched_ctx)
        except Exception as e:
            print(f"  Enrichment query failed: {e}")

    # IR events & catalysts
    if IR_EVENTS_AVAILABLE:
        try:
            events = get_events_for_query(query)
            if events:
                events_ctx = format_events_for_claude(events)
                if events_ctx:
                    context_parts.append(events_ctx)
        except Exception as e:
            print(f"  IR events query failed: {e}")

    # If no data at all, tell the user
    if not context_parts:
        return {
            "answer": "I couldn't find relevant data for this query in our document library or live APIs. Try rephrasing your question or uploading a relevant document.",
            "sources": [],
        }

    full_context = "\n\n".join(context_parts)

    # Inject detected persona directive so the synthesis adapts its framing
    persona = plan.get("persona", "investor")
    persona_directive = ""
    if persona == "operator":
        persona_directive = (
            "\n\n═══ ACTIVE PERSONA: OPERATOR / STRATEGY / BD ═══\n"
            "This query is from a biotech operator, BD, or strategy professional. "
            "Prioritize Layer 6 (BD & Licensing Intelligence). Frame insights around "
            "actionable decisions: in-license candidates, geographic rights availability, "
            "white-space opportunities, platform extensibility, and partnership structures. "
            "Still include clinical data but frame it through an operator lens "
            "(e.g., 'Phase 2 data de-risks the asset for a potential licensing deal')."
        )
    elif persona == "trial_designer":
        persona_directive = (
            "\n\n═══ ACTIVE PERSONA: CLINICAL TRIAL DESIGNER ═══\n"
            "This query is from a clinical development professional (medical director, "
            "clinical ops, regulatory affairs, or biostatistician). "
            "Prioritize Layer 7 (Clinical Trial Design Intelligence). Frame insights around "
            "endpoint selection, biomarker enrichment strategies, adaptive designs, "
            "comparator arm choices, FDA feedback patterns, enrollment optimization, "
            "and regulatory precedent. When discussing trials, emphasize DESIGN CHOICES "
            "and their rationale, not just results."
        )
    # Default investor persona needs no extra directive — it's the base prompt

    full_system = f"{SYNTHESIS_SYSTEM_PROMPT}{persona_directive}\n\n{full_context}"

    try:
        response = get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16384,
            system=full_system,
            messages=[{"role": "user", "content": query}],
        )

        answer = response.content[0].text

        # Post-process: clean up citations and garbled text
        answer = _postprocess_answer(answer, data)

        # Build the source list for the frontend sidebar
        sources = _build_source_list(data)

        return {
            "answer": answer,
            "sources": sources,
        }

    except Exception as e:
        print(f"  Synthesis error: {e}")
        return {
            "answer": f"Error synthesizing answer: {str(e)}",
            "sources": [],
        }


import re as _re

def _postprocess_answer(answer: str, data: dict) -> str:
    """
    Clean up Claude's answer:
    1. Convert plain-text doc references to {doc:TICKER|Title} badge format
    2. Strip garbled PDF extraction artifacts (download icons, broken text)
    3. Clean up [Doc N] references that slipped through
    """
    # Build a map of doc titles → proper badge format from RAG results
    doc_map = {}
    for r in data.get("rag_results", []):
        ticker = r.get("ticker", "")
        title = r.get("title", "")
        filename = r.get("filename", "")
        if ticker and title:
            # Map various ways Claude might reference the doc
            doc_map[title] = f"{{doc:{ticker}|{title}}}"
            doc_map[f"{ticker} {title}"] = f"{{doc:{ticker}|{title}}}"
            # Handle "TICKER DocType (date)" pattern
            for doc_type in ["10-K", "10-Q", "8-K", "Investor Presentation", "Annual Report"]:
                if doc_type.lower() in title.lower():
                    doc_map[f"{ticker} {doc_type}"] = f"{{doc:{ticker}|{title}}}"

    # 1. Convert "[Doc N]" references to proper badges
    def replace_doc_ref(match):
        doc_num = int(match.group(1))
        # Find the doc with this number in our RAG results
        seen_keys = {}
        idx = 1
        for r in data.get("rag_results", []):
            key = f"{r.get('ticker')}:{r.get('filename')}"
            if key not in seen_keys:
                seen_keys[key] = idx
                if idx == doc_num:
                    ticker = r.get("ticker", "")
                    title = r.get("title", r.get("filename", ""))
                    return f"{{doc:{ticker}|{title}}}"
                idx += 1
        return match.group(0)  # Keep original if not found

    answer = _re.sub(r'\[Doc\s+(\d+)\]', replace_doc_ref, answer)

    # 2. Convert plain-text doc title references to badges
    # Sort by length (longest first) to avoid partial matches
    for plain_text, badge in sorted(doc_map.items(), key=lambda x: -len(x[0])):
        if plain_text in answer and badge not in answer:
            answer = answer.replace(plain_text, badge, 1)  # Replace first occurrence only

    # 3. Strip garbled PDF artifacts
    # "Download icon..." patterns from bad OCR
    answer = _re.sub(r'Download\s+icon\S*', '', answer)
    # Clean up resulting double spaces
    answer = _re.sub(r'  +', ' ', answer)
    # Clean up empty citation-like patterns
    answer = _re.sub(r'\s*\.\s*\.{2,}', '.', answer)

    return answer.strip()


def _clean_filename_to_title(filename: str, ticker: str = "", doc_type: str = "") -> str:
    """Derive a readable title from a filename when the real title is missing."""
    if not filename:
        return f"{ticker} Document" if ticker else "Untitled Document"

    import re
    # Strip hash-like prefixes (e.g. "6e52618eefcf28a97b0c")
    name = filename
    if re.match(r'^[0-9a-f]{16,}$', name.split('.')[0]):
        # Entire stem is a hash — use ticker + doc_type
        type_labels = {
            'sec_10k': '10-K Annual Report',
            'sec_10q': '10-Q Quarterly Report',
            'sec_8k': '8-K Filing',
            'investor_deck': 'Investor Presentation',
            'clinical_trials': 'Clinical Trials Summary',
            'poster': 'Conference Poster',
            'publication': 'Publication',
            'other': 'Document',
        }
        label = type_labels.get(doc_type, doc_type.replace('_', ' ').title() if doc_type else 'Document')
        return f"{ticker} {label}" if ticker else label

    # Remove extension
    name = re.sub(r'\.(pdf|docx?|xlsx?|pptx?|txt|html?)$', '', name, flags=re.IGNORECASE)
    # Replace separators with spaces
    name = re.sub(r'[._-]+', ' ', name)
    # Trim extra whitespace
    name = name.strip()
    # Capitalize if all lowercase
    if name == name.lower():
        name = name.title()

    return name if name else (f"{ticker} Document" if ticker else "Untitled Document")


def _build_source_list(data: dict) -> list[dict]:
    """Build a unified, deduplicated source list for the frontend."""
    sources = []
    seen = set()

    # RAG sources
    for r in data.get("rag_results", []):
        key = f"rag:{r.get('ticker', '')}:{r.get('filename', '')}"
        if key not in seen:
            seen.add(key)
            title = r.get("title", "") or ""
            filename = r.get("filename", "") or ""
            # Fix unhelpful titles like "Download" — derive from filename instead
            if not title or title.lower() in ("download", "untitled", "none", ""):
                title = _clean_filename_to_title(filename, r.get("ticker", ""), r.get("doc_type", ""))
            sources.append({
                "type": "internal",
                "source_name": "Document Library",
                "ticker": r.get("ticker", ""),
                "company": r.get("company_name", ""),
                "title": title,
                "doc_type": r.get("doc_type", ""),
                "ref": f"Page {r.get('page_number', '?')}",
                "relevance": r.get("similarity", 0),
            })

    # ClinicalTrials.gov sources
    for t in data.get("trials", []):
        key = f"ct:{t['nct_id']}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "type": "clinical_trial",
                "source_name": "ClinicalTrials.gov",
                "ticker": "",
                "company": t.get("sponsor", ""),
                "title": t.get("title", ""),
                "doc_type": f"{t.get('phase', '')} | {t.get('status', '')}",
                "ref": t.get("nct_id", ""),
                "url": t.get("url", ""),
                "relevance": 0.8,
            })

    # FDA sources
    for d in data.get("fda_drugs", []):
        key = f"fda:{d.get('brand_name', '')}:{d.get('generic_name', '')}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "type": "fda",
                "source_name": "FDA",
                "ticker": "",
                "company": d.get("manufacturer", ""),
                "title": f"{d.get('brand_name', '')} ({d.get('generic_name', '')})",
                "doc_type": "Drug Label",
                "ref": "FDA Approved",
                "relevance": 0.85,
            })

    # PubMed sources
    for p in data.get("papers", []):
        key = f"pubmed:{p['pmid']}"
        if key not in seen:
            seen.add(key)
            authors = p.get("authors", [])
            author_str = authors[0] if authors else ""
            if len(authors) > 1:
                author_str += " et al."
            sources.append({
                "type": "pubmed",
                "source_name": "PubMed",
                "ticker": "",
                "company": author_str,
                "title": p.get("title", ""),
                "doc_type": p.get("journal", ""),
                "ref": f"PMID {p['pmid']}",
                "url": p.get("url", ""),
                "relevance": 0.75,
            })

    return sources


# =============================================================================
# Main entry point
# =============================================================================

def answer_query(query: str) -> dict:
    """
    Main entry point. Takes a natural language question and returns a
    comprehensive, cited answer.

    Returns:
        answer: str — the synthesized answer
        sources: list — cited sources
        query_plan: dict — how the query was classified
        timing: dict — execution time per source
        metadata: dict — total docs searched, chunks retrieved, etc.
    """
    total_start = time.time()

    # Step 1: Classify the query
    print(f"\n{'='*60}")
    print(f"  Query: {query}")
    print(f"{'='*60}")

    plan = classify_query(query)
    print(f"  Sources: {plan.get('sources', [])}")
    print(f"  Type: {plan.get('query_type', 'unknown')}")
    print(f"  Persona: {plan.get('persona', 'investor')}")
    print(f"  Reasoning: {plan.get('reasoning', '')}")

    # Step 1.5: Enrich with drug entity intelligence
    if DRUG_DB_AVAILABLE:
        plan = enrich_with_drug_entities(query, plan)
        entity_ctx = plan.get("entity_context", {})
        if entity_ctx.get("drug_info"):
            print(f"  Drug entity: {entity_ctx['drug_info']['canonical_name']}")
        if entity_ctx.get("disease_landscape"):
            groups = entity_ctx["disease_landscape"].get("target_groups", [])
            print(f"  Disease landscape: {len(groups)} target approaches")
        if entity_ctx.get("target_drugs"):
            print(f"  Target drugs: {len(entity_ctx['target_drugs'])} drugs found via hierarchy")
        if entity_ctx.get("extra_pubmed_terms"):
            print(f"  Extra PubMed terms: {len(entity_ctx['extra_pubmed_terms'])}")

    # Step 2: Execute queries in parallel
    data = execute_query_plan(plan)
    print(f"  Timing: {data['timing']}")
    landscape = data.get("global_landscape")
    landscape_count = len(landscape["assets"]) if landscape and landscape.get("assets") else 0
    print(f"  RAG chunks: {len(data['rag_results'])}, Trials: {len(data['trials'])}, "
          f"FDA: {len(data['fda_drugs'])}, Papers: {len(data['papers'])}, "
          f"Global landscape: {landscape_count} assets")

    # Step 3: Synthesize answer
    result = synthesize_answer(query, data, plan)

    total_time = round(time.time() - total_start, 2)
    print(f"  Total time: {total_time}s")
    print(f"  Sources cited: {len(result['sources'])}")

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "query_plan": plan,
        "timing": {**data["timing"], "total": total_time},
        "metadata": {
            "rag_chunks_retrieved": len(data["rag_results"]),
            "trials_found": len(data["trials"]),
            "fda_drugs_found": len(data["fda_drugs"]),
            "papers_found": len(data["papers"]),
        },
    }


# =============================================================================
# Flask endpoint (to add to app.py)
# =============================================================================

def register_search_routes(app):
    """
    Register the unified search endpoint on a Flask app.
    Call this from app.py: register_search_routes(app)
    """
    from flask import jsonify, request as flask_request

    @app.route("/api/search", methods=["POST"])
    def unified_search():
        """The main search endpoint that powers the frontend."""
        data = flask_request.get_json()
        query = data.get("query", "").strip()

        if not query:
            return jsonify({"error": "Empty query"}), 400

        # Optional filters from frontend
        source_filter = data.get("source_filter", None)  # e.g., "clinical_trials"
        ticker_filter = data.get("ticker", None)

        result = answer_query(query)
        return jsonify(result)

    @app.route("/api/search/stream", methods=["POST"])
    def unified_search_stream():
        """SSE streaming search — sends progress updates then streams the answer."""
        from flask import Response, stream_with_context
        data = flask_request.get_json()
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"error": "Empty query"}), 400

        def generate():
            import json as _json
            # Step 1: Classify
            yield f"data: {_json.dumps({'type': 'step', 'step': 'classifying'})}\n\n"
            plan = classify_query(query)

            # Step 1.5: Enrich with entities
            if DRUG_DB_AVAILABLE:
                plan = enrich_with_drug_entities(query, plan)

            yield f"data: {_json.dumps({'type': 'step', 'step': 'searching', 'plan': {'sources': plan.get('sources', []), 'query_type': plan.get('query_type', 'general')}})}\n\n"

            # Step 2: Execute queries
            query_data = execute_query_plan(plan)
            landscape = query_data.get("global_landscape")
            metadata = {
                "rag_chunks_retrieved": len(query_data["rag_results"]),
                "trials_found": len(query_data["trials"]),
                "fda_drugs_found": len(query_data["fda_drugs"]),
                "papers_found": len(query_data["papers"]),
                "global_landscape_assets": len(landscape["assets"]) if landscape and landscape.get("assets") else 0,
            }
            sources = _build_source_list(query_data)

            yield f"data: {_json.dumps({'type': 'step', 'step': 'synthesizing', 'metadata': metadata})}\n\n"

            # Step 3: Build context and stream Claude response
            context_parts = []
            entity_ctx = plan.get("entity_context", {})
            if entity_ctx.get("drug_info"):
                d = entity_ctx["drug_info"]
                targets = d.get("targets", [])
                target_str = ", ".join(f"{t['target_name']} ({t['role']})" for t in targets) if targets else "?"
                aliases = [a["alias"] for a in d.get("aliases", []) if a["alias"] != d["canonical_name"]]
                context_parts.append(
                    f"=== DRUG ENTITY DATABASE ===\n"
                    f"Canonical name: {d['canonical_name']}\nCompany: {d.get('company_name', '?')} ({d.get('company_ticker', '?')})\n"
                    f"Target(s): {target_str}\nModality: {d.get('modality', '?')}\nMechanism: {d.get('mechanism', '?')}\n"
                    f"Phase: {d.get('phase_highest', '?')} | Status: {d.get('status', '?')}\n"
                    f"Indications: {', '.join(d.get('indications', []))}\nAll known names: {', '.join(aliases[:6])}\n"
                )
            if entity_ctx.get("disease_landscape") and DRUG_DB_AVAILABLE:
                context_parts.append(format_disease_landscape_for_claude(entity_ctx["disease_landscape"]))
            elif entity_ctx.get("target_drugs") and DRUG_DB_AVAILABLE:
                context_parts.append(format_landscape_for_claude(entity_ctx["target_drugs"], indication=plan.get("ct_condition", "")))
            elif entity_ctx.get("landscape_drugs") and DRUG_DB_AVAILABLE:
                context_parts.append(format_landscape_for_claude(entity_ctx["landscape_drugs"], indication=plan.get("ct_condition", "")))
            if query_data.get("rag_results"):
                rag_ctx = rag_search.format_context_for_claude(query_data["rag_results"]) if RAG_AVAILABLE else ""
                if rag_ctx:
                    context_parts.append(rag_ctx)
            api_ctx = format_api_results_for_claude(
                trials=query_data.get("trials"), fda_drugs=query_data.get("fda_drugs"), papers=query_data.get("papers"),
            )
            if api_ctx:
                context_parts.append(api_ctx)

            # Global landscape data (if available)
            if query_data.get("global_landscape"):
                landscape_ctx = format_global_landscape_for_claude(query_data["global_landscape"])
                if landscape_ctx:
                    context_parts.append(landscape_ctx)

            # News miner data (if available)
            if query_data.get("news_miner"):
                news_ctx = format_news_miner_for_claude(query_data["news_miner"])
                if news_ctx:
                    context_parts.append(news_ctx)

            # Enriched drug candidates (from enrichment agent)
            if ENRICHMENT_AVAILABLE:
                try:
                    enriched = get_enriched_for_query(query)
                    if enriched:
                        enriched_ctx = format_enriched_for_claude(enriched)
                        if enriched_ctx:
                            context_parts.append(enriched_ctx)
                except Exception as e:
                    print(f"  Enrichment query failed: {e}")

            # IR events & catalysts
            if IR_EVENTS_AVAILABLE:
                try:
                    events = get_events_for_query(query)
                    if events:
                        events_ctx = format_events_for_claude(events)
                        if events_ctx:
                            context_parts.append(events_ctx)
                except Exception as e:
                    print(f"  IR events query failed: {e}")

            if not context_parts:
                yield f"data: {_json.dumps({'type': 'token', 'text': 'No relevant data found for this query.'})}\n\n"
                yield f"data: {_json.dumps({'type': 'done', 'sources': sources, 'timing': query_data['timing'], 'metadata': metadata, 'query_plan': plan})}\n\n"
                return

            full_context = "\n\n".join(context_parts)
            full_system = f"{SYNTHESIS_SYSTEM_PROMPT}\n\n{full_context}"

            accumulated_text = ""
            try:
                with get_client().messages.stream(
                    model="claude-sonnet-4-20250514",
                    max_tokens=16384,
                    system=full_system,
                    messages=[{"role": "user", "content": query}],
                ) as stream:
                    for text in stream.text_stream:
                        accumulated_text += text
                        yield f"data: {_json.dumps({'type': 'token', 'text': text})}\n\n"
            except Exception as e:
                yield f"data: {_json.dumps({'type': 'token', 'text': f'Error: {str(e)}'})}\n\n"

            # Post-process the full answer (fix citations, strip garbled text)
            corrected = _postprocess_answer(accumulated_text, query_data)
            done_payload = {
                'type': 'done',
                'sources': sources,
                'timing': query_data.get('timing', {}),
                'metadata': metadata,
                'query_plan': plan,
            }
            # Only send corrected_answer if post-processing actually changed something
            if corrected != accumulated_text:
                done_payload['corrected_answer'] = corrected
            yield f"data: {_json.dumps(done_payload)}\n\n"

        return Response(stream_with_context(generate()), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    @app.route("/api/search/health", methods=["GET"])
    def search_health():
        """Health check for the search system."""
        health = {
            "rag_available": RAG_AVAILABLE,
            "drug_db_available": DRUG_DB_AVAILABLE,
            "anthropic_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        }
        # Quick check of external APIs
        try:
            trials = search_clinical_trials(condition="cancer", max_results=1)
            health["clinical_trials_api"] = len(trials) > 0
        except Exception:
            health["clinical_trials_api"] = False

        return jsonify(health)


# =============================================================================
# Quick test
# =============================================================================

if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What are the clinical trials in ulcerative colitis?"

    result = answer_query(query)

    print(f"\n{'='*60}")
    print("ANSWER:")
    print(f"{'='*60}")
    print(result["answer"])

    print(f"\n{'='*60}")
    print(f"SOURCES ({len(result['sources'])}):")
    print(f"{'='*60}")
    for i, s in enumerate(result["sources"], 1):
        print(f"  [{i}] {s['source_name']}: {s['title']} ({s['doc_type']})")
