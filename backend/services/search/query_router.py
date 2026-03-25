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

# Global asset discovery — provides multi-country landscape data
try:
    from global_asset_discovery import (
        build_landscape,
        search_trials_global,
        search_trials_by_country,
    )
    GLOBAL_LANDSCAPE_AVAILABLE = True
except ImportError:
    GLOBAL_LANDSCAPE_AVAILABLE = False
    print("  ⚠ Global asset discovery not loaded — global landscape disabled")

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

# Claude client
_client = None

def get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


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

Return a JSON object with:
{
    "sources": ["RAG", "CLINICAL_TRIALS", "FDA", "PUBMED", "GLOBAL_LANDSCAPE", "NEWS_MINER"],  // which sources to query (at least 1)
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
    "reasoning": "brief explanation of source selection"
}

Important rules:
- For landscape/overview questions (e.g., "GLP-1 landscape", "ADC competitive landscape", "what PD-1 drugs are in development in China"), ALWAYS include GLOBAL_LANDSCAPE
- For questions mentioning China, Korea, Japan, Asia, global, or non-US markets, include GLOBAL_LANDSCAPE AND NEWS_MINER
- For questions about drug classes or targets across companies, include GLOBAL_LANDSCAPE
- For questions about "under the radar" assets, emerging biotech, recent deals, or novel drug candidates, include NEWS_MINER
- For questions about licensing deals, regulatory filings, or regional pipeline intelligence, include NEWS_MINER
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
        response = get_client().messages.create(
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
                    top_k=15,
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
                ct_kwargs["max_results"] = 20
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

        # Submit Global Landscape search
        if "GLOBAL_LANDSCAPE" in sources and GLOBAL_LANDSCAPE_AVAILABLE:
            landscape_target = plan.get("landscape_target", plan.get("ct_intervention", ""))
            landscape_region = plan.get("landscape_region", "all")
            if landscape_target:
                futures["GLOBAL_LANDSCAPE"] = executor.submit(
                    build_landscape,
                    landscape_target,
                    region=landscape_region,
                    max_trials=200,
                    use_llm=False,  # Don't use LLM extraction in real-time (too slow)
                )

        # Submit News Miner search
        if "NEWS_MINER" in sources and NEWS_MINER_AVAILABLE:
            news_region = plan.get("landscape_region", "all")
            futures["NEWS_MINER"] = executor.submit(
                news_mine_region, news_region, use_llm=False,  # regex-only for speed
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

    return results


# =============================================================================
# Step 2b: Format Global Landscape for Claude
# =============================================================================

def format_global_landscape_for_claude(landscape_data):
    """
    Format the global landscape result into a context block Claude can use
    to generate investor-grade landscape answers.
    """
    if not landscape_data or not landscape_data.get("assets"):
        return ""

    assets = landscape_data["assets"]
    query = landscape_data.get("query", "")
    region = landscape_data.get("region", "all")
    total_trials = landscape_data.get("total_trials", 0)

    lines = [
        f"=== GLOBAL DRUG ASSET LANDSCAPE: {query.upper()} ===",
        f"Region: {region} | Total trials scanned: {total_trials} | Drug assets found: {len(assets)}",
        "",
        "IMPORTANT: This landscape includes drugs from MULTIPLE countries and regions.",
        "Your answer MUST cover non-US programs (China, Korea, Japan, Europe) if present below.",
        "Do NOT omit Asian or European drug programs from your answer.",
        "",
        "Drug assets ranked by development stage (highest phase first):",
        "",
    ]

    for i, asset in enumerate(assets, 1):
        phase = asset.get("highest_phase", "N/A").replace("PHASE", "Phase ")
        countries = asset.get("countries", [])
        countries_str = ", ".join(countries[:5])
        if len(countries) > 5:
            countries_str += f" +{len(countries)-5} more"
        indications = ", ".join(asset.get("indications", [])[:3])

        lines.append(
            f"{i}. {asset['drug_name']} ({asset.get('target_moa', '?')})"
        )
        lines.append(
            f"   Phase: {phase} | Trials: {asset.get('total_trials', 0)} "
            f"(active: {asset.get('active_trials', 0)}) | Sponsor: {asset.get('sponsor', '?')}"
        )
        if countries_str:
            lines.append(f"   Countries: {countries_str}")
        if indications:
            lines.append(f"   Indications: {indications}")
        lines.append("")

    # Add region summary
    all_countries = {}
    for asset in assets:
        for c in asset.get("countries", []):
            all_countries[c] = all_countries.get(c, 0) + 1

    lines.append("Country-level activity:")
    for country, count in sorted(all_countries.items(), key=lambda x: -x[1])[:10]:
        lines.append(f"  {country}: {count} drug assets in development")

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

SYNTHESIS_SYSTEM_PROMPT = f"""You are SatyaBio, an AI-powered biotech diligence intelligence platform — Open Evidence for biotech investors. You answer questions ONLY using the retrieved documents and data provided below. You never use your training knowledge to fill in gaps.

TODAY'S DATE: {datetime.now().strftime('%B %d, %Y')}

STRICT GROUNDING RULES (CRITICAL — this is what makes SatyaBio trustworthy):
1. You may ONLY make factual claims that are directly supported by the provided context documents.
2. If the retrieved documents do NOT contain information to answer a question (or part of a question), you MUST explicitly say: "Our document library does not currently contain data on [topic]. Additional sources such as [specific data type] would be needed to answer this."
3. NEVER supplement with your training knowledge. Biotech data changes weekly — training data is stale and will mislead investors. A wrong ORR number or outdated trial status could cause real financial harm.
4. If you are uncertain whether a claim is supported by the context, err on the side of NOT making it.
5. It is far better to give a shorter, fully-grounded answer than a longer answer that mixes retrieved data with general knowledge.
6. DATE AWARENESS: Each document in the index has a date. When citing financial figures (revenue, cash position) or data that changes over time, ALWAYS note the reporting period (e.g., "FY2024 revenue" not just "revenue"). Prefer data from the most recent documents. If only older data is available, flag it: "As of [date], ..." so investors know the vintage.

DATA SOURCES:
1. ENTITY DB — Curated drug entities with targets, aliases, hierarchies, and competitive landscapes
2. INTERNAL LIBRARY — Investor presentations, SEC filings (10-K, 10-Q, 8-K), FDA drug labels, FDA approval review documents, clinical papers, conference posters across 60 biotech and pharma companies
3. LIVE APIs — ClinicalTrials.gov, FDA drug labels, PubMed publications
4. GLOBAL LANDSCAPE — Drug asset discovery across 61+ countries. Provides competitive landscape tables with drug name, target/MoA, highest phase, sponsor, countries, and trial counts.
5. REGIONAL NEWS MINER — Under-the-radar drug assets from regional news sources (Chinese, Korean, Japanese, Indian, European biotech news). Novel assets marked with ★ are NOT yet in standard databases.

CITATION FORMAT (CRITICAL — follow exactly):
Use inline source tags after EVERY factual claim. Format: {{source_type:label}}

Source tag types and when to use each:
- {{pubmed:PMID|AuthorName}} — for PubMed papers. Use the numeric PMID then a pipe then first author surname.
- {{trial:NCT12345678}} — for ClinicalTrials.gov data
- {{fda:DrugName}} — for FDA drug label or FDA review document data
- {{doc:CompanyTicker|DocTitle}} — for internal document library data. Include doc title for source links.
- {{sec:CompanyTicker|FilingType}} — for SEC filing data (e.g. {{sec:RVMD|10-K}})
- {{entity:db}} — for data from the drug entity database

Examples of correct citation:
  "Sotorasib demonstrated ORR of 37% in previously treated NSCLC {{pubmed:36028218|Skoulidis}} {{trial:NCT04303780}}."
  "Revolution Medicines reported RMC-6236 Phase 1 data at ASCO 2024 {{doc:RVMD|ASCO 2024 Investor Presentation}}."
  "The FDA label notes hepatotoxicity as a boxed warning {{fda:REZDIFFRA}}."
  "RVMD reported cash position of $1.8B as of Q3 2025 {{sec:RVMD|10-Q}}."

IMPORTANT: For PubMed citations, include the numeric PMID before the pipe. If exact PMID unavailable, use author name only: {{pubmed:AuthorName}}.

EVERY sentence with a factual claim MUST have at least one citation tag. Any uncited factual claim is a grounding violation.

ANSWER STRUCTURE:
- Open with a 1-2 sentence summary of the key finding
- Use ## headers to organize sections
- Include specific numbers: ORR, PFS, OS, HR, p-values, enrollment, dates
- For drug profiles: include mechanism, dosing, key trial name, primary endpoint data
- For landscapes: organize by approved therapies → late-stage pipeline → early-stage
- CRITICAL FOR LANDSCAPE QUERIES: When GLOBAL LANDSCAPE data is provided, cover ALL geographic regions present. Do NOT focus only on US/Western drugs.
- Be data-dense. An investor wants signal, not filler.
- Keep sentences concise. One claim per sentence when possible.
- End with a "Sources" section listing the key documents cited, so users can verify.

TABLE FORMAT REQUIREMENTS (CRITICAL — investors need granular data, not summaries):
- When clinical trial data is available, ALWAYS present individual trials in a markdown table with columns: NCT ID | Drug | Phase | Status | Indication | Enrollment | Sponsor
- NEVER summarize trials as "X active trials" — list each one individually in the table. The user needs to see every trial.
- When landscape/pipeline data mentions multiple drug assets by country or region, list each asset individually in a table: Drug | Target/MoA | Phase | Sponsor | Country
- NEVER summarize assets as "19 drug assets in China" without listing them — expand every asset into the table.
- Tables should be sorted by phase (Phase 3 first) then by enrollment (largest first).
- If there are more than 20 trials or assets, show the top 20 and note how many more exist.

NEVER make investment recommendations. Present data for the user to make their own decisions.

FOLLOW-UP QUESTIONS (REQUIRED):
At the very end of your answer, generate exactly 3 follow-up questions the user might want to ask next.
These should be from the perspective of a biotech investor with an MD PhD doing diligence — think about:
- Deeper clinical data questions (subgroup analyses, safety signals, biomarker stratification)
- Competitive positioning (head-to-head comparisons, differentiation, best-in-class potential)
- Commercial/strategic angles (patent cliffs, market sizing, pricing power, regulatory timelines)
- Mechanistic depth (resistance mechanisms, combination rationale, PK/PD considerations)

Format them EXACTLY like this at the end:
{{followup}}
What are the key resistance mechanisms to KRAS G12C inhibitors and how do next-gen agents address them?
How does sotorasib's safety profile compare to adagrasib in the post-hoc crossover analysis?
What is the estimated peak sales potential for KRAS inhibitors in NSCLC vs CRC?
{{/followup}}"""


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
    full_system = f"{SYNTHESIS_SYSTEM_PROMPT}\n\n{full_context}"

    try:
        response = get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=full_system,
            messages=[{"role": "user", "content": query}],
        )

        answer = response.content[0].text

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


def _build_source_list(data: dict) -> list[dict]:
    """Build a unified, deduplicated source list for the frontend."""
    sources = []
    seen = set()

    # RAG sources
    for r in data.get("rag_results", []):
        key = f"rag:{r.get('ticker', '')}:{r.get('filename', '')}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "type": "internal",
                "source_name": "Document Library",
                "ticker": r.get("ticker", ""),
                "company": r.get("company_name", ""),
                "title": r.get("title", r.get("filename", "")),
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

            try:
                with get_client().messages.stream(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=full_system,
                    messages=[{"role": "user", "content": query}],
                ) as stream:
                    for text in stream.text_stream:
                        yield f"data: {_json.dumps({'type': 'token', 'text': text})}\n\n"
            except Exception as e:
                yield f"data: {_json.dumps({'type': 'token', 'text': f'Error: {str(e)}'})}\n\n"

            yield f"data: {_json.dumps({'type': 'done', 'sources': sources, 'timing': query_data.get('timing', {}), 'metadata': metadata, 'query_plan': plan})}\n\n"

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
