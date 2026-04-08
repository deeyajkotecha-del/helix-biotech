"""
SatyaBio — Source Priority Router (Agent-in-the-Loop)

Replaces flat vector similarity search with an intelligent document selection
agent. Instead of "find the 25 most similar chunks," this module:

  1. Classifies the query type (regulatory, financial, clinical, competitive)
  2. Determines source priority order (AdCom > 10-K, or 10-K > AdCom, etc.)
  3. Checks for mechanism-class linkage (fast-follower queries)
  4. Constructs a multi-pass retrieval plan
  5. Returns prioritized, annotated results

The key insight: for a regulatory question, a 10-K paragraph about FDA risk
should rank BELOW an AdCom transcript where a committee member actually
raised that exact concern. For a financial question, the opposite is true.

Integration:
    This module is called by query_router.py AFTER classification but BEFORE
    the raw RAG search. It wraps rag_search.search() with priority logic.

Usage:
    from source_router import prioritized_search, get_adcom_context

    # Full prioritized search
    results = prioritized_search(query, plan)

    # Just get AdCom context for a drug/mechanism
    adcom_context = get_adcom_context(query, plan)
"""

import os
import re
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

# RAG search (for the actual vector/keyword retrieval)
try:
    import rag_search
    RAG_AVAILABLE = rag_search.is_rag_available()
except ImportError:
    RAG_AVAILABLE = False

# AdCom structured data
try:
    from adcom_extractor import (
        get_adcom_for_mechanism_class,
        get_adcom_for_product,
        get_adcom_for_committee,
        get_concerns_by_mechanism_class,
        format_adcom_for_claude,
        MECHANISM_CLASSES,
    )
    ADCOM_AVAILABLE = True
except ImportError:
    ADCOM_AVAILABLE = False
    print("  ⚠ AdCom extractor not available — structured AdCom data disabled")

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")


# ── Source priority profiles ──
# Each profile defines which document types matter most for that query type.
# Higher weight = more important. Documents matching higher-priority sources
# get a boost in the final ranking.

SOURCE_PROFILES = {
    "regulatory": {
        # Questions about FDA guidance, approval pathways, committee decisions
        # AdCom transcripts are PRIMARY. 10-K boilerplate is DEPRIORITIZED.
        "description": "FDA guidance, approval pathways, regulatory decisions",
        "boost": {
            "transcript": 2.0,           # AdCom transcript = gold standard
            "briefing_document": 1.8,     # FDA briefing docs = near-gold
            "meeting_summary": 1.5,       # Meeting minutes
            "presentation": 0.8,          # Committee presentations
            "fda_label": 1.2,             # Drug labels (for approved products)
        },
        "penalize": {
            "sec_10k": 0.3,              # 10-K regulatory boilerplate is noise
            "sec_10q": 0.3,              # Same for 10-Q
            "sec_8k": 0.5,              # 8-K can have regulatory events
            "investor_deck": 0.4,        # Company spin on regulatory
        },
        "use_adcom_structured": True,     # Always pull structured AdCom data
        "use_mechanism_class": True,      # Enable fast-follower linkage
    },

    "financial": {
        # Questions about revenue, margins, guidance, valuation
        # 10-K/10-Q are PRIMARY. AdCom transcripts are irrelevant.
        "description": "Revenue, financials, guidance, valuation, stock",
        "boost": {
            "sec_10k": 2.0,
            "sec_10q": 1.8,
            "sec_8k": 1.5,
            "sec_20f": 2.0,
            "investor_deck": 1.5,
        },
        "penalize": {
            "transcript": 0.3,          # AdCom transcript ≠ financial data
            "briefing_document": 0.3,
            "clinical_trials": 0.4,
        },
        "use_adcom_structured": False,
        "use_mechanism_class": False,
    },

    "clinical": {
        # Questions about clinical data, trial results, endpoints, safety
        # Mix of AdCom (for FDA's take), publications, and company data.
        "description": "Clinical trial data, results, safety, endpoints",
        "boost": {
            "transcript": 1.5,          # AdCom discussion of clinical data
            "briefing_document": 1.8,    # FDA's analysis of clinical data
            "presentation": 1.3,         # Company's data presentations
            "poster": 1.5,              # Conference posters
            "publication": 1.8,         # Peer-reviewed publications
        },
        "penalize": {
            "sec_10k": 0.5,             # 10-K clinical summaries are stale
            "sec_10q": 0.4,
        },
        "use_adcom_structured": True,
        "use_mechanism_class": True,
    },

    "competitive": {
        # Questions about competitive landscape, fast-followers, mechanism class
        # Uses mechanism-class linkage heavily.
        "description": "Competitive landscape, mechanism class, fast-followers",
        "boost": {
            "transcript": 1.3,
            "briefing_document": 1.3,
            "investor_deck": 1.5,       # Company positioning data
            "presentation": 1.5,
        },
        "penalize": {
            "sec_10k": 0.6,
        },
        "use_adcom_structured": True,
        "use_mechanism_class": True,     # Critical for competitive queries
    },

    "general": {
        # Default — no strong preference
        "description": "General query, balanced source weighting",
        "boost": {},
        "penalize": {},
        "use_adcom_structured": True,
        "use_mechanism_class": False,
    },
}


# ── Query type detection ──

REGULATORY_SIGNALS = [
    r'\bFDA\b', r'\bAdCom\b', r'\badvisory committee\b', r'\bapproval\b',
    r'\bBLA\b', r'\bNDA\b', r'\bsNDA\b', r'\bsBLA\b', r'\bPDUFA\b',
    r'\baccelerated approval\b', r'\bbreakthrough\b', r'\bpriority review\b',
    r'\bguidance\b', r'\bregulat\w+\b', r'\bCRL\b', r'\bcomplete response\b',
    r'\bRems\b', r'\bbiosimilar\b', r'\blabel\b.*\bexpan\w+',
    r'\bcommittee\b', r'\bvote\b', r'\bpanel\b',
]

FINANCIAL_SIGNALS = [
    r'\brevenue\b', r'\bearnings\b', r'\b10-?K\b', r'\b10-?Q\b', r'\b8-?K\b',
    r'\bmargin\b', r'\bguidance\b', r'\bforecast\b', r'\bvaluation\b',
    r'\bstock\b', r'\bshare\b', r'\bprice\b', r'\bmarket cap\b',
    r'\bfinancial\b', r'\bP[&/]?L\b', r'\bcash\b', r'\bdebt\b',
    r'\bROI\b', r'\bEBITDA\b', r'\bR&D spend\b', r'\brunway\b',
]

CLINICAL_SIGNALS = [
    r'\btrial\b', r'\bphase [123]\b', r'\bORR\b', r'\bPFS\b', r'\bOS\b',
    r'\bendpoint\b', r'\befficacy\b', r'\bsafety\b', r'\badverse\b',
    r'\bsurrogate\b', r'\bKaplan.?Meier\b', r'\brespons\w+ rate\b',
    r'\benrollment\b', r'\bpivotal\b', r'\bdata\b.*\bread\w*out\b',
    r'\barm\b', r'\brandomiz\w+\b', r'\bblind\w*\b',
]

COMPETITIVE_SIGNALS = [
    r'\blandscape\b', r'\bcompetit\w+\b', r'\bfast.?follow\w*\b',
    r'\bsimilar drug\b', r'\bsame (class|mechanism|target)\b',
    r'\bhead.?to.?head\b', r'\bvs\.?\b', r'\bversus\b',
    r'\bclass effect\b', r'\bmechanism class\b', r'\bmarket share\b',
]


def detect_query_type(query: str, plan: dict) -> str:
    """
    Detect the query type for source prioritization.
    Returns: 'regulatory', 'financial', 'clinical', 'competitive', or 'general'
    """
    q = query.lower()

    scores = {
        "regulatory": 0,
        "financial": 0,
        "clinical": 0,
        "competitive": 0,
    }

    for pattern in REGULATORY_SIGNALS:
        if re.search(pattern, q, re.IGNORECASE):
            scores["regulatory"] += 1

    for pattern in FINANCIAL_SIGNALS:
        if re.search(pattern, q, re.IGNORECASE):
            scores["financial"] += 1

    for pattern in CLINICAL_SIGNALS:
        if re.search(pattern, q, re.IGNORECASE):
            scores["clinical"] += 1

    for pattern in COMPETITIVE_SIGNALS:
        if re.search(pattern, q, re.IGNORECASE):
            scores["competitive"] += 1

    # Also use the classifier's persona hint
    persona = plan.get("persona", "investor")
    if persona == "trial_designer":
        scores["regulatory"] += 2
        scores["clinical"] += 1
    elif persona == "operator":
        scores["competitive"] += 1

    # Pick the highest scoring type, or 'general' if no clear winner
    max_score = max(scores.values())
    if max_score == 0:
        return "general"

    # If there's a tie or near-tie between regulatory and clinical, prefer regulatory
    # (AdCom data is the differentiator)
    if scores["regulatory"] >= max_score - 1 and scores["regulatory"] > 0:
        return "regulatory"

    for qtype, score in scores.items():
        if score == max_score:
            return qtype

    return "general"


def _detect_mechanism_classes(query: str, plan: dict) -> list[str]:
    """
    Detect which mechanism classes are relevant to this query.
    Returns a list of mechanism_class keys.
    """
    q = f"{query} {plan.get('ct_intervention', '')} {plan.get('fda_drug', '')}".lower()
    matches = []

    for mclass, keywords in MECHANISM_CLASSES.items():
        for kw in keywords:
            if kw.lower() in q:
                matches.append(mclass)
                break

    return matches


def _reweight_rag_results(results: list[dict], profile: dict) -> list[dict]:
    """
    Apply source-priority weights to RAG search results.
    Boosts results from priority sources and penalizes noise sources.
    """
    boost_map = profile.get("boost", {})
    penalize_map = profile.get("penalize", {})

    for r in results:
        doc_type = (r.get("doc_type") or "").lower()
        ticker = (r.get("ticker") or "").lower()

        # Determine weight multiplier
        multiplier = 1.0

        # Check boost
        for dtype, weight in boost_map.items():
            if dtype in doc_type:
                multiplier = max(multiplier, weight)
                break

        # Check penalize (only if no boost matched)
        if multiplier == 1.0:
            for dtype, weight in penalize_map.items():
                if dtype in doc_type:
                    multiplier = weight
                    break

        # Apply to score
        original_score = r.get("score", r.get("relevance", 0.5))
        r["original_score"] = original_score
        r["adjusted_score"] = original_score * multiplier
        r["source_priority"] = "boosted" if multiplier > 1.0 else "penalized" if multiplier < 1.0 else "neutral"

    # Re-sort by adjusted score
    results.sort(key=lambda r: r.get("adjusted_score", 0), reverse=True)
    return results


def get_adcom_context(query: str, plan: dict) -> dict:
    """
    Get structured AdCom context for a query.
    Returns both product-specific and mechanism-class data.

    This is the key function that provides intelligence no other platform has:
    structured committee decisions linked by mechanism class.
    """
    if not ADCOM_AVAILABLE:
        return {"products": [], "mechanism_context": [], "formatted": ""}

    products = []
    mechanism_context = []

    # 1. Check for specific product mentions
    drug_name = plan.get("ct_intervention") or plan.get("fda_drug")
    if drug_name:
        products = get_adcom_for_product(drug_name)

    # 2. Check for mechanism class linkage
    mclasses = _detect_mechanism_classes(query, plan)
    for mc in mclasses:
        mc_products = get_adcom_for_mechanism_class(mc)
        mechanism_context.extend(mc_products)

    # Deduplicate (a product might appear in both)
    seen_ids = {p.get("id") for p in products}
    for mp in mechanism_context:
        if mp.get("id") not in seen_ids:
            products.append(mp)
            seen_ids.add(mp.get("id"))

    # Format for Claude
    formatted = ""
    if products:
        formatted = format_adcom_for_claude(
            products,
            f"FDA Advisory Committee Intelligence ({len(products)} product reviews)"
        )

    # Add mechanism-class concern aggregation
    for mc in mclasses:
        concern_data = get_concerns_by_mechanism_class(mc)
        if concern_data["total_concerns"] > 0:
            formatted += f"\n── Regulatory Risk Profile: {mc} ──\n"
            formatted += f"  {concern_data['total_products_reviewed']} products reviewed by FDA committees\n"
            formatted += f"  Top concerns raised across the class:\n"
            for concern, count in concern_data["concerns"][:5]:
                formatted += f"    ({count}x) {concern}\n"

    return {
        "products": products,
        "mechanism_classes": mclasses,
        "mechanism_context": mechanism_context,
        "formatted": formatted,
    }


def prioritized_search(query: str, plan: dict, top_k: int = 25) -> dict:
    """
    Main entry point. Performs an intelligent, source-prioritized search.

    Returns:
        {
            "rag_results": [...],         # Re-weighted RAG results
            "adcom_context": {...},       # Structured AdCom intelligence
            "query_type": str,            # Detected query type
            "source_profile": str,        # Which profile was used
            "mechanism_classes": [...],   # Detected mechanism classes
        }
    """
    # Step 1: Detect query type
    qtype = detect_query_type(query, plan)
    profile = SOURCE_PROFILES.get(qtype, SOURCE_PROFILES["general"])

    # Step 2: Run RAG search (the base retrieval)
    rag_results = []
    if RAG_AVAILABLE:
        rag_query = plan.get("rag_query", query)
        ticker_filter = plan.get("rag_ticker_filter")
        rag_results = rag_search.search(
            rag_query,
            top_k=top_k * 2,  # Over-fetch so reweighting has room to work
            ticker_filter=ticker_filter,
        )

    # Step 3: Reweight based on source priority
    if rag_results:
        rag_results = _reweight_rag_results(rag_results, profile)
        rag_results = rag_results[:top_k]  # Trim to requested size

    # Step 4: Get structured AdCom context if appropriate
    adcom_context = {"products": [], "mechanism_context": [], "formatted": ""}
    if profile.get("use_adcom_structured"):
        adcom_context = get_adcom_context(query, plan)

    return {
        "rag_results": rag_results,
        "adcom_context": adcom_context,
        "query_type": qtype,
        "source_profile": qtype,
        "mechanism_classes": adcom_context.get("mechanism_classes", []),
    }


def format_source_routing_for_claude(routing_result: dict) -> str:
    """
    Format the routing metadata for injection into Claude's system prompt.
    Tells Claude which sources are most trustworthy for this query type.
    """
    qtype = routing_result.get("query_type", "general")
    profile = SOURCE_PROFILES.get(qtype, SOURCE_PROFILES["general"])

    lines = [f"\n── Source Priority: {qtype.upper()} query ──"]
    lines.append(f"  {profile['description']}")

    if routing_result.get("mechanism_classes"):
        lines.append(f"  Mechanism classes detected: {', '.join(routing_result['mechanism_classes'])}")
        lines.append(f"  → Fast-follower intelligence active: concerns and decisions from related drugs are included")

    lines.append("")
    lines.append("  IMPORTANT: For this query type, prioritize:")
    if qtype == "regulatory":
        lines.append("  - AdCom transcripts and briefing documents (PRIMARY evidence)")
        lines.append("  - De-prioritize 10-K/10-Q boilerplate regulatory risk language")
        lines.append("  - When citing regulatory positions, prefer committee member statements over company filings")
    elif qtype == "financial":
        lines.append("  - SEC filings (10-K, 10-Q, 8-K) and earnings webcasts (PRIMARY evidence)")
        lines.append("  - De-prioritize clinical/regulatory documents for financial analysis")
    elif qtype == "clinical":
        lines.append("  - FDA briefing documents and publications (PRIMARY evidence for clinical data)")
        lines.append("  - AdCom transcripts for committee interpretation of clinical data")
        lines.append("  - Company presentations for additional context")
    elif qtype == "competitive":
        lines.append("  - Cross-reference multiple sources for competitive intelligence")
        lines.append("  - AdCom data from similar mechanism-class drugs is highly relevant")
        lines.append("  - Use mechanism-class linkage to identify relevant precedents from fast-followers")

    return "\n".join(lines)
