"""
SatyaBio Open Evidence — AI-powered biotech intelligence search

Replaces the old /extract page with an Open Evidence-style interface:
  - Search bar with streaming AI answers
  - 60-company document universe (IR pages, publications, events)
  - Enrichment module (ClinicalTrials.gov + Claude deep research)
  - Regional biotech trackers (China, Korea, Europe, Japan, India)
  - Source sidebar with citations

Architecture:
    GET  /extract/              → React SPA (Open Evidence page)
    GET  /extract/api/companies → Company universe (60 companies)
    POST /extract/api/search    → SSE streaming search (uses query_router)
    GET  /extract/api/enrichment/status → Enrichment module status
    POST /extract/api/enrichment/lookup → Enrich a drug candidate
    GET  /extract/api/regional/alerts  → Regional news miner alerts
    POST /extract/api/regional/mine    → Mine a specific region
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy-load the search backend (shared with /api/search)
# ---------------------------------------------------------------------------

_SEARCH_DIR = str(Path(__file__).resolve().parent.parent.parent / "backend" / "services" / "search")
if _SEARCH_DIR not in sys.path:
    sys.path.insert(0, _SEARCH_DIR)

_SEARCH_READY = False
_INIT_ERROR = None

try:
    from query_router import (
        classify_query,
        enrich_with_drug_entities,
        execute_query_plan,
        _build_source_list,
        get_client,
        SYNTHESIS_SYSTEM_PROMPT,
        format_global_landscape_for_claude,
        format_news_miner_for_claude,
        RAG_AVAILABLE,
        DRUG_DB_AVAILABLE,
        ENRICHMENT_AVAILABLE,
        IR_EVENTS_AVAILABLE,
    )
    from api_connectors import (
        search_clinical_trials,
        format_api_results_for_claude,
    )
    _SEARCH_READY = True
except Exception as e:
    _INIT_ERROR = str(e)

# Optional modules
try:
    import rag_search as _rag_search
except ImportError:
    _rag_search = None

try:
    from drug_entities import (
        lookup_drug,
        format_landscape_for_claude,
        format_disease_landscape_for_claude,
    )
except ImportError:
    lookup_drug = None
    format_landscape_for_claude = None
    format_disease_landscape_for_claude = None

try:
    from enrichment_agent import (
        get_enriched_for_query,
        format_enriched_for_claude,
        lookup_drug_on_ctgov,
    )
    _ENRICHMENT_READY = True
except ImportError:
    get_enriched_for_query = None
    format_enriched_for_claude = None
    lookup_drug_on_ctgov = None
    _ENRICHMENT_READY = False

try:
    from regional_news_miner import (
        mine_region as news_mine_region,
        get_recent_alerts,
        get_mining_status,
    )
    _NEWS_MINER_READY = True
except ImportError:
    try:
        from regional_news_miner import mine_region as news_mine_region
        _NEWS_MINER_READY = True
        get_recent_alerts = None
        get_mining_status = None
    except ImportError:
        news_mine_region = None
        get_recent_alerts = None
        get_mining_status = None
        _NEWS_MINER_READY = False

try:
    from global_asset_discovery import build_landscape, search_trials_global
    _GLOBAL_DISCOVERY_READY = True
except ImportError:
    build_landscape = None
    search_trials_global = None
    _GLOBAL_DISCOVERY_READY = False

try:
    from ir_events_scraper import get_events_for_query, format_events_for_claude
except ImportError:
    get_events_for_query = None
    format_events_for_claude = None

# Import company universe
try:
    from app.configs.companies import get_all_companies_flat, get_companies_by_category, CATEGORY_LABELS
    _COMPANIES_LOADED = True
except ImportError:
    _COMPANIES_LOADED = False
    def get_all_companies_flat(): return []
    def get_companies_by_category(): return {}
    CATEGORY_LABELS = {}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str
    source_filter: Optional[str] = None
    ticker: Optional[str] = None


class EnrichmentRequest(BaseModel):
    drug_name: str


class RegionalMineRequest(BaseModel):
    region: str  # china, korea, japan, india, europe


# ---------------------------------------------------------------------------
# Company Universe Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/companies")
async def list_companies():
    """Return all 60 companies grouped by category."""
    companies = get_all_companies_flat()
    grouped = get_companies_by_category()
    return {
        "total": len(companies),
        "companies": companies,
        "by_category": {
            cat: {
                "label": CATEGORY_LABELS.get(cat, cat),
                "count": len(items),
                "companies": items,
            }
            for cat, items in sorted(grouped.items())
        },
    }


# ---------------------------------------------------------------------------
# SSE Streaming Search (same engine as /api/search but on /extract path)
# ---------------------------------------------------------------------------

@router.post("/api/search")
async def evidence_search_stream(req: SearchRequest):
    """SSE streaming search — Open Evidence style."""
    if not _SEARCH_READY:
        return JSONResponse(
            status_code=503,
            content={"error": f"Search backend not ready: {_INIT_ERROR}"},
        )

    query = req.query.strip()
    if not query:
        return JSONResponse(status_code=400, content={"error": "Empty query"})

    def generate():
        # Step 1: Classify
        yield f"data: {json.dumps({'type': 'step', 'step': 'classifying'})}\n\n"
        plan = classify_query(query)

        # Step 1.5: Enrich with drug entities
        if DRUG_DB_AVAILABLE:
            plan = enrich_with_drug_entities(query, plan)

        yield f"data: {json.dumps({'type': 'step', 'step': 'searching', 'plan': {'sources': plan.get('sources', []), 'query_type': plan.get('query_type', 'general')}})}\n\n"

        # Step 2: Execute queries in parallel
        query_data = execute_query_plan(plan)
        landscape = query_data.get("global_landscape")
        metadata = {
            "rag_chunks_retrieved": len(query_data.get("rag_results", [])),
            "trials_found": len(query_data.get("trials", [])),
            "fda_drugs_found": len(query_data.get("fda_drugs", [])),
            "papers_found": len(query_data.get("papers", [])),
            "global_landscape_assets": len(landscape["assets"]) if landscape and landscape.get("assets") else 0,
            "enrichment_available": _ENRICHMENT_READY,
            "regional_tracker_available": _NEWS_MINER_READY,
            "companies_loaded": _COMPANIES_LOADED,
        }
        sources = _build_source_list(query_data)

        yield f"data: {json.dumps({'type': 'step', 'step': 'synthesizing', 'metadata': metadata})}\n\n"

        # Step 3: Build context for Claude synthesis
        context_parts = []
        entity_ctx = plan.get("entity_context", {})

        # Drug entity context
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

        # Disease/target landscape
        if entity_ctx.get("disease_landscape") and format_disease_landscape_for_claude:
            context_parts.append(format_disease_landscape_for_claude(entity_ctx["disease_landscape"]))
        elif entity_ctx.get("target_drugs") and format_landscape_for_claude:
            context_parts.append(format_landscape_for_claude(entity_ctx["target_drugs"], indication=plan.get("ct_condition", "")))

        # RAG context
        if query_data.get("rag_results") and _rag_search:
            rag_ctx = _rag_search.format_context_for_claude(query_data["rag_results"])
            if rag_ctx:
                context_parts.append(rag_ctx)

        # API results
        api_ctx = format_api_results_for_claude(
            trials=query_data.get("trials"),
            fda_drugs=query_data.get("fda_drugs"),
            papers=query_data.get("papers"),
        )
        if api_ctx:
            context_parts.append(api_ctx)

        # Global landscape
        if query_data.get("global_landscape"):
            landscape_ctx = format_global_landscape_for_claude(query_data["global_landscape"])
            if landscape_ctx:
                context_parts.append(landscape_ctx)

        # News miner
        if query_data.get("news_miner"):
            news_ctx = format_news_miner_for_claude(query_data["news_miner"])
            if news_ctx:
                context_parts.append(news_ctx)

        # Enriched drug candidates
        if get_enriched_for_query and format_enriched_for_claude:
            try:
                enriched = get_enriched_for_query(query)
                if enriched:
                    enriched_ctx = format_enriched_for_claude(enriched)
                    if enriched_ctx:
                        context_parts.append(enriched_ctx)
            except Exception as e:
                print(f"  Enrichment query failed: {e}")

        # IR events
        if get_events_for_query and format_events_for_claude:
            try:
                events = get_events_for_query(query)
                if events:
                    events_ctx = format_events_for_claude(events)
                    if events_ctx:
                        context_parts.append(events_ctx)
            except Exception as e:
                print(f"  IR events query failed: {e}")

        if not context_parts:
            yield f"data: {json.dumps({'type': 'token', 'text': 'No relevant data found for this query.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'sources': sources, 'timing': query_data.get('timing', {}), 'metadata': metadata, 'query_plan': plan})}\n\n"
            return

        full_context = "\n\n".join(context_parts)
        full_system = f"{SYNTHESIS_SYSTEM_PROMPT}\n\n{full_context}"

        start_time = time.time()
        try:
            with get_client().messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=full_system,
                messages=[{"role": "user", "content": query}],
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'token', 'text': f'Error generating answer: {str(e)}'})}\n\n"

        total_time = round(time.time() - start_time, 2)
        timing = {**query_data.get("timing", {}), "total": total_time}
        yield f"data: {json.dumps({'type': 'done', 'sources': sources, 'timing': timing, 'metadata': metadata, 'query_plan': plan})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Enrichment Module Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/enrichment/status")
async def enrichment_status():
    """Status of the enrichment pipeline."""
    return {
        "enrichment_ready": _ENRICHMENT_READY,
        "news_miner_ready": _NEWS_MINER_READY,
        "global_discovery_ready": _GLOBAL_DISCOVERY_READY,
        "search_ready": _SEARCH_READY,
        "drug_db_available": _SEARCH_READY and DRUG_DB_AVAILABLE if _SEARCH_READY else False,
        "rag_available": _SEARCH_READY and RAG_AVAILABLE if _SEARCH_READY else False,
    }


@router.post("/api/enrichment/lookup")
async def enrichment_lookup(req: EnrichmentRequest):
    """Look up a drug candidate — CT.gov + Claude enrichment."""
    drug_name = req.drug_name.strip()
    if not drug_name:
        return JSONResponse(status_code=400, content={"error": "Empty drug name"})

    result = {"drug_name": drug_name, "ctgov": None, "enriched": None}

    # Layer 1: ClinicalTrials.gov
    if lookup_drug_on_ctgov:
        try:
            ctgov_data = lookup_drug_on_ctgov(drug_name)
            if ctgov_data:
                result["ctgov"] = ctgov_data
        except Exception as e:
            result["ctgov_error"] = str(e)

    # Layer 2: Drug entity DB
    if lookup_drug:
        try:
            drug_info = lookup_drug(drug_name)
            if drug_info:
                result["entity_db"] = drug_info
        except Exception as e:
            result["entity_db_error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# Regional Biotech Tracker Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/regional/status")
async def regional_status():
    """Status and recent alerts from regional news mining."""
    status = {
        "news_miner_ready": _NEWS_MINER_READY,
        "global_discovery_ready": _GLOBAL_DISCOVERY_READY,
        "regions": ["china", "korea", "japan", "india", "europe"],
    }

    if get_mining_status and _NEWS_MINER_READY:
        try:
            mining_stats = get_mining_status()
            status["mining_stats"] = mining_stats
        except Exception:
            pass

    if get_recent_alerts and _NEWS_MINER_READY:
        try:
            alerts = get_recent_alerts()
            status["recent_alerts"] = alerts[:20]
        except Exception:
            pass

    return status


@router.post("/api/regional/mine")
async def regional_mine(req: RegionalMineRequest):
    """Trigger regional news mining for a specific region."""
    if not _NEWS_MINER_READY:
        return JSONResponse(status_code=503, content={"error": "Regional news miner not configured"})

    region = req.region.lower().strip()
    valid_regions = ["china", "korea", "japan", "india", "europe"]
    if region not in valid_regions:
        return JSONResponse(status_code=400, content={"error": f"Invalid region. Choose from: {', '.join(valid_regions)}"})

    try:
        result = news_mine_region(region)
        return {"region": region, "result": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Mining failed: {str(e)}"})


# ---------------------------------------------------------------------------
# System Health
# ---------------------------------------------------------------------------

@router.get("/api/health")
async def evidence_health():
    """Full system health check."""
    return {
        "search_ready": _SEARCH_READY,
        "init_error": _INIT_ERROR,
        "enrichment_ready": _ENRICHMENT_READY,
        "news_miner_ready": _NEWS_MINER_READY,
        "global_discovery_ready": _GLOBAL_DISCOVERY_READY,
        "companies_loaded": _COMPANIES_LOADED,
        "company_count": len(get_all_companies_flat()),
        "rag_available": _SEARCH_READY and RAG_AVAILABLE if _SEARCH_READY else False,
        "drug_db_available": _SEARCH_READY and DRUG_DB_AVAILABLE if _SEARCH_READY else False,
        "anthropic_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "neon_db_set": bool(os.environ.get("NEON_DATABASE_URL")),
    }


# ---------------------------------------------------------------------------
# Frontend — Serve React SPA
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent

@router.get("/", response_class=HTMLResponse)
async def serve_evidence_page():
    """Serve the Open Evidence React SPA."""
    react_index = BASE_DIR / "app" / "dist" / "index.html"
    if react_index.exists():
        return FileResponse(react_index)
    # Fallback: serve a minimal loading page
    return HTMLResponse(_fallback_evidence_html())


def _fallback_evidence_html() -> str:
    """Minimal fallback page if React build isn't available."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SatyaBio Open Evidence</title>
    <style>
        body { font-family: 'Inter', sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #FAF8F4; color: #1A1A1A; }
        .msg { text-align: center; }
        h1 { font-size: 28px; font-weight: 700; }
        h1 span { color: #C4603C; }
        p { color: #5A5650; margin-top: 8px; }
        code { background: #F0EBE4; padding: 2px 8px; border-radius: 4px; font-size: 13px; }
    </style>
</head>
<body>
    <div class="msg">
        <h1>Satya<span>Bio</span> Open Evidence</h1>
        <p>React frontend not built yet.</p>
        <p>Run <code>cd app && npm run build</code> to build.</p>
    </div>
</body>
</html>"""
