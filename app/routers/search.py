"""
SatyaBio — Unified Search Router (FastAPI)

Provides the /api/search/stream SSE endpoint that powers the Open Evidence-style
search frontend. Wraps the query_router module from backend/services/search/.

Architecture:
    POST /api/search/stream  → SSE streaming search
    POST /api/search         → synchronous search (fallback)
    GET  /api/search/health  → system health check
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy-load the search backend (from backend/services/search/)
# ---------------------------------------------------------------------------

_SEARCH_DIR = str(Path(__file__).resolve().parent.parent.parent / "backend" / "services" / "search")
if _SEARCH_DIR not in sys.path:
    sys.path.insert(0, _SEARCH_DIR)

# Import flags — everything is optional so the app still starts if modules are missing
_SEARCH_READY = False
_INIT_ERROR = None

try:
    from query_router import (
        classify_query,
        enrich_with_drug_entities,
        execute_query_plan,
        _build_source_list,
        answer_query,
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
    print("  \u2713 Search router loaded — /api/search endpoints active")
except Exception as e:
    _INIT_ERROR = str(e)
    print(f"  \u26A0 Search router: modules not fully loaded ({e})")
    print(f"    Search will return a helpful error until dependencies are configured.")


# Conditional imports that may not be available
try:
    import rag_search as _rag_search
except ImportError:
    _rag_search = None

try:
    from drug_entities import (
        format_landscape_for_claude,
        format_disease_landscape_for_claude,
    )
except ImportError:
    format_landscape_for_claude = None
    format_disease_landscape_for_claude = None

try:
    from enrichment_agent import get_enriched_for_query, format_enriched_for_claude
except ImportError:
    get_enriched_for_query = None
    format_enriched_for_claude = None

try:
    from ir_events_scraper import get_events_for_query, format_events_for_claude
except ImportError:
    get_events_for_query = None
    format_events_for_claude = None


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class ConversationTurn(BaseModel):
    query: str
    answer: str

class SearchRequest(BaseModel):
    query: str
    source_filter: str | None = None
    ticker: str | None = None
    history: list[ConversationTurn] | None = None  # prior conversation turns for context


# ---------------------------------------------------------------------------
# SSE streaming search endpoint
# ---------------------------------------------------------------------------

@router.post("/stream")
async def search_stream(req: SearchRequest):
    """SSE streaming search — sends progress updates then streams the answer token-by-token."""
    if not _SEARCH_READY:
        return JSONResponse(
            status_code=503,
            content={"error": f"Search backend not ready: {_INIT_ERROR}. "
                     "Ensure ANTHROPIC_API_KEY, NEON_DATABASE_URL, and VOYAGE_API_KEY are set."},
        )

    query = req.query.strip()
    if not query:
        return JSONResponse(status_code=400, content={"error": "Empty query"})

    def generate():
        """Synchronous generator that yields SSE events."""
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
        elif entity_ctx.get("landscape_drugs") and format_landscape_for_claude:
            context_parts.append(format_landscape_for_claude(entity_ctx["landscape_drugs"], indication=plan.get("ct_condition", "")))

        # RAG context
        if query_data.get("rag_results") and _rag_search:
            rag_ctx = _rag_search.format_context_for_claude(query_data["rag_results"])
            if rag_ctx:
                context_parts.append(rag_ctx)

        # API results (trials, FDA, PubMed)
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

        # IR events & catalysts
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

        # Build messages with conversation history for context
        messages = []
        if req.history:
            for turn in req.history[-4:]:  # keep last 4 turns to stay within context limits
                messages.append({"role": "user", "content": turn.query})
                messages.append({"role": "assistant", "content": turn.answer})
        messages.append({"role": "user", "content": query})

        start_time = time.time()
        try:
            with get_client().messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=full_system,
                messages=messages,
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
# Synchronous search (non-streaming fallback)
# ---------------------------------------------------------------------------

@router.post("")
async def search_sync(req: SearchRequest):
    """Non-streaming search endpoint."""
    if not _SEARCH_READY:
        return JSONResponse(status_code=503, content={"error": f"Search backend not ready: {_INIT_ERROR}"})

    query = req.query.strip()
    if not query:
        return JSONResponse(status_code=400, content={"error": "Empty query"})

    result = answer_query(query)
    return result


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@router.get("/health")
async def search_health():
    """Health check for the search subsystem."""
    health = {
        "search_ready": _SEARCH_READY,
        "init_error": _INIT_ERROR,
        "rag_available": _SEARCH_READY and RAG_AVAILABLE,
        "drug_db_available": _SEARCH_READY and DRUG_DB_AVAILABLE,
        "enrichment_available": _SEARCH_READY and ENRICHMENT_AVAILABLE,
        "ir_events_available": _SEARCH_READY and IR_EVENTS_AVAILABLE,
        "anthropic_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "neon_db_set": bool(os.environ.get("NEON_DATABASE_URL")),
        "voyage_key_set": bool(os.environ.get("VOYAGE_API_KEY")),
    }

    if _SEARCH_READY:
        try:
            trials = search_clinical_trials(condition="cancer", max_results=1)
            health["clinical_trials_api"] = len(trials) > 0
        except Exception:
            health["clinical_trials_api"] = False

    return health


# ---------------------------------------------------------------------------
# Landscape chart data endpoint
# ---------------------------------------------------------------------------
# Serves structured clinical endpoint data for the LandscapeChart component.
# Pulls from clinical_endpoints table (populated by endpoint_extractor.py).
# If no data exists, returns empty — frontend shows "run extraction" prompt.

try:
    import psycopg2
    import psycopg2.extras
    _DB_URL = os.environ.get("NEON_DATABASE_URL", "")
    _DB_AVAILABLE = bool(_DB_URL)
except ImportError:
    _DB_AVAILABLE = False
    _DB_URL = ""


@router.get("/chart/{indication}")
async def get_chart_data(
    indication: str,
    endpoint: str = "EASI-75",
    phase_min: str = "Phase 2",
):
    """
    Get structured endpoint data for a landscape chart.

    GET /api/search/chart/Atopic%20Dermatitis?endpoint=EASI-75
    GET /api/search/chart/NSCLC?endpoint=ORR
    GET /api/search/chart/obesity?endpoint=body%20weight%20loss

    Returns JSON array of data points for LandscapeChart component.
    """
    if not _DB_AVAILABLE:
        return JSONResponse({"data": [], "error": "Database not configured"}, status_code=503)

    try:
        conn = psycopg2.connect(_DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Query clinical_endpoints for this indication + endpoint
        # Pull both absolute and pbo_adjusted values
        cur.execute("""
            SELECT
                ce.drug_name,
                ce.trial_name,
                ce.target,
                ce.mechanism,
                ce.company_ticker,
                ce.phase,
                ce.value,
                ce.value_type,
                ce.dose,
                ce.timepoint,
                ce.enrollment,
                ce.source_detail
            FROM clinical_endpoints ce
            WHERE LOWER(ce.indication) LIKE LOWER(%s)
              AND LOWER(ce.endpoint_name) = LOWER(%s)
              AND ce.value IS NOT NULL
            ORDER BY ce.target, ce.value DESC
        """, (f"%{indication}%", endpoint))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return {
                "data": [],
                "indication": indication,
                "endpoint": endpoint,
                "message": f"No {endpoint} data found for {indication}. "
                           f"Run: python3 endpoint_extractor.py --indication \"{indication}\" "
                           f"to extract from your document library."
            }

        # Group by drug+trial to merge absolute and pbo_adjusted into one data point
        merged = {}
        for row in rows:
            key = f"{row['drug_name']}|{row['trial_name'] or ''}|{row['dose'] or ''}"
            if key not in merged:
                merged[key] = {
                    "drug": row["drug_name"],
                    "trial": row["trial_name"],
                    "mechanism": row["target"] or row["mechanism"] or "Other",
                    "ticker": row["company_ticker"],
                    "phase": row["phase"],
                    "dose": row["dose"],
                    "pbo_adjusted": None,
                    "absolute": None,
                }
            if row["value_type"] == "pbo_adjusted":
                merged[key]["pbo_adjusted"] = round(float(row["value"]), 1)
            elif row["value_type"] == "absolute":
                merged[key]["absolute"] = round(float(row["value"]), 1)
            else:
                # If value_type not specified, treat as absolute
                if merged[key]["absolute"] is None:
                    merged[key]["absolute"] = round(float(row["value"]), 1)

        data = list(merged.values())

        return {
            "data": data,
            "indication": indication,
            "endpoint": endpoint,
            "count": len(data),
        }

    except Exception as e:
        return JSONResponse(
            {"data": [], "error": str(e), "indication": indication, "endpoint": endpoint},
            status_code=500
        )


# ---------------------------------------------------------------------------
# Conversation persistence (chat history)
# ---------------------------------------------------------------------------

def _get_db():
    """Get a fresh DB connection for conversation ops."""
    db_url = os.environ.get("NEON_DATABASE_URL", "")
    if not db_url:
        return None
    try:
        import psycopg2
        return psycopg2.connect(db_url)
    except Exception:
        return None


class SaveMessageRequest(BaseModel):
    conversation_id: str
    turn_index: int
    query: str
    answer: str | None = None
    sources: list | None = None
    metadata: dict | None = None
    timing: dict | None = None
    query_plan: dict | None = None
    title: str | None = None  # auto-title from first query


@router.get("/conversations")
async def list_conversations():
    """List recent conversations (newest first)."""
    conn = _get_db()
    if not conn:
        return JSONResponse({"conversations": [], "error": "DB not available"})

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN conversation_messages m ON m.conversation_id = c.id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            LIMIT 50
        """)
        rows = cur.fetchall()
        conversations = [
            {
                "id": r[0],
                "title": r[1],
                "created_at": r[2].isoformat() if r[2] else None,
                "updated_at": r[3].isoformat() if r[3] else None,
                "message_count": r[4],
            }
            for r in rows
        ]
        return {"conversations": conversations}
    except Exception as e:
        return JSONResponse({"conversations": [], "error": str(e)}, status_code=500)
    finally:
        conn.close()


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Load a full conversation with all messages."""
    conn = _get_db()
    if not conn:
        return JSONResponse({"error": "DB not available"}, status_code=503)

    try:
        cur = conn.cursor()
        cur.execute("SELECT id, title, created_at FROM conversations WHERE id = %s", (conversation_id,))
        conv = cur.fetchone()
        if not conv:
            return JSONResponse({"error": "Conversation not found"}, status_code=404)

        cur.execute("""
            SELECT turn_index, query, answer, sources, metadata, timing, query_plan
            FROM conversation_messages
            WHERE conversation_id = %s
            ORDER BY turn_index
        """, (conversation_id,))
        messages = [
            {
                "turn_index": r[0],
                "query": r[1],
                "answer": r[2],
                "sources": r[3] or [],
                "metadata": r[4] or {},
                "timing": r[5] or {},
                "query_plan": r[6] or {},
            }
            for r in cur.fetchall()
        ]
        return {
            "id": conv[0],
            "title": conv[1],
            "created_at": conv[2].isoformat() if conv[2] else None,
            "messages": messages,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        conn.close()


@router.post("/conversations/save")
async def save_message(req: SaveMessageRequest):
    """Save or update a conversation turn. Creates conversation if needed."""
    conn = _get_db()
    if not conn:
        return JSONResponse({"error": "DB not available"}, status_code=503)

    try:
        cur = conn.cursor()

        # Upsert conversation
        title = req.title or req.query[:80]
        cur.execute("""
            INSERT INTO conversations (id, title) VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
        """, (req.conversation_id, title))

        # Update title only on first message
        if req.turn_index == 0 and req.title:
            cur.execute("UPDATE conversations SET title = %s WHERE id = %s",
                        (req.title, req.conversation_id))

        # Upsert message
        cur.execute("""
            INSERT INTO conversation_messages
                (conversation_id, turn_index, query, answer, sources, metadata, timing, query_plan)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            req.conversation_id,
            req.turn_index,
            req.query,
            req.answer,
            json.dumps(req.sources or []),
            json.dumps(req.metadata or {}),
            json.dumps(req.timing or {}),
            json.dumps(req.query_plan or {}),
        ))

        # Update the answer if it was streamed in after the initial save
        if req.answer:
            cur.execute("""
                UPDATE conversation_messages
                SET answer = %s, sources = %s, metadata = %s, timing = %s, query_plan = %s
                WHERE conversation_id = %s AND turn_index = %s
            """, (
                req.answer,
                json.dumps(req.sources or []),
                json.dumps(req.metadata or {}),
                json.dumps(req.timing or {}),
                json.dumps(req.query_plan or {}),
                req.conversation_id,
                req.turn_index,
            ))

        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        conn.close()


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    conn = _get_db()
    if not conn:
        return JSONResponse({"error": "DB not available"}, status_code=503)

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
        conn.commit()
        return {"ok": True, "deleted": cur.rowcount > 0}
    except Exception as e:
        conn.rollback()
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        conn.close()
