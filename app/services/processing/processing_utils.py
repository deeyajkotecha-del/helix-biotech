"""
Processing status tracking for the oncology document pipeline.

Each document in oncology_metadata.json carries a "processing" dict:

    "processing": {
        "status": "raw" | "extracted" | "chunked" | "embedded",
        "source_hash_at_processing": "<sha256 or null>",
        "extracted_at": "<iso timestamp or null>",
        "chunked_at":  "<iso timestamp or null>",
        "embedded_at": "<iso timestamp or null>"
    }

Pipeline stages in order:
    raw → extracted → chunked → embedded

A document "needs" a stage if its current status is before that stage,
or if the source file changed (hash mismatch) since last processing.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
METADATA_FILE = DATA_DIR / "downloads" / "oncology_metadata.json"

# Pipeline stages in execution order
STAGES = ("extracted", "chunked", "embedded")

_STAGE_ORDER = {"raw": 0, "extracted": 1, "chunked": 2, "embedded": 3}


def _load_metadata() -> dict:
    if METADATA_FILE.exists():
        data = json.loads(METADATA_FILE.read_text())
        data.pop("_errors", None)
        return data
    return {}


def _save_metadata(metadata: dict) -> None:
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    METADATA_FILE.write_text(json.dumps(metadata, indent=2))


def _current_status(doc: dict) -> str:
    return doc.get("processing", {}).get("status", "raw")


def _hash_changed(doc: dict) -> bool:
    """True if the source file has been re-downloaded since last processing."""
    proc = doc.get("processing", {})
    recorded = proc.get("source_hash_at_processing")
    if recorded is None:
        return False  # never processed — not a "change", just unprocessed
    return recorded != doc.get("sha256")


# ── Public API ────────────────────────────────────────────────────────


def needs_processing(doc: dict, stage: str) -> bool:
    """Check if a document needs a given pipeline stage.

    Returns True when:
      - The doc's current status is before the requested stage, OR
      - The source file hash changed since last processing (re-download)

    Skips duplicates (entries with "duplicate_of").
    """
    if stage not in _STAGE_ORDER:
        raise ValueError(f"Unknown stage {stage!r}. Valid: {list(_STAGE_ORDER)}")
    if doc.get("duplicate_of"):
        return False

    current = _current_status(doc)
    if _STAGE_ORDER.get(current, 0) < _STAGE_ORDER[stage]:
        return True

    return _hash_changed(doc)


def get_unprocessed(stage: str, ticker: str | None = None) -> list[tuple[str, dict]]:
    """Return all docs that need a given stage as (url, doc) pairs.

    Args:
        stage:  Pipeline stage to check ("extracted", "chunked", "embedded").
        ticker: Optional filter — only return docs for this ticker.

    Returns:
        List of (url, doc_dict) sorted by scrape date (oldest first).
    """
    metadata = _load_metadata()
    results = []

    for url, doc in metadata.items():
        if not isinstance(doc, dict):
            continue
        if ticker and doc.get("ticker") != ticker.upper():
            continue
        if needs_processing(doc, stage):
            results.append((url, doc))

    results.sort(key=lambda pair: pair[1].get("scraped_at", ""))
    return results


def mark_processed(url: str, stage: str, extra: dict | None = None) -> None:
    """Update a doc's processing status after completing a stage.

    Sets:
      - processing.status = stage
      - processing.source_hash_at_processing = doc's current sha256
      - processing.{stage}_at = current UTC timestamp
      - Any additional keys from `extra` merged into processing

    Args:
        url:   The document URL (metadata key).
        stage: The stage just completed ("extracted", "chunked", "embedded").
        extra: Optional dict of additional fields to store in processing
               (e.g. {"chunk_count": 12, "embedding_model": "..."}).
    """
    if stage not in _STAGE_ORDER:
        raise ValueError(f"Unknown stage {stage!r}. Valid: {list(_STAGE_ORDER)}")

    metadata = _load_metadata()
    doc = metadata.get(url)
    if doc is None:
        raise KeyError(f"URL not found in metadata: {url}")

    proc = doc.get("processing", {"status": "raw", "source_hash_at_processing": None})
    proc["status"] = stage
    proc["source_hash_at_processing"] = doc.get("sha256")
    proc[f"{stage}_at"] = datetime.now(timezone.utc).isoformat()

    if extra:
        proc.update(extra)

    doc["processing"] = proc
    metadata[url] = doc
    _save_metadata(metadata)
    logger.info("Marked %s as %s: %s", stage, url[:80], proc.get(f"{stage}_at"))
