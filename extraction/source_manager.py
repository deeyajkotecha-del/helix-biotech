import json
import re
from pathlib import Path

from extraction.exceptions import DuplicateSourceError

VALID_SOURCE_TYPES = {
    "corporate_presentation",
    "investor_day",
    "conference_poster",
    "sec_filing",
    "earnings_call",
    "press_release",
}

TICKER_RE = re.compile(r"^[A-Z]{1,5}$")


class SourceManager:
    def __init__(self, data_root: str = "data/companies"):
        self.data_root = Path(data_root)

    def register_source(
        self, ticker: str, source_id: str, metadata: dict, overwrite: bool = False
    ) -> dict:
        self._validate_ticker(ticker)
        self._validate_metadata(metadata)

        ticker_dir = self.data_root / ticker
        index_path = ticker_dir / "sources" / "index.json"
        source_dir = ticker_dir / "sources" / source_id

        # Check for duplicates
        index = self._read_index(index_path)
        existing_ids = {s["id"] for s in index.get("sources", [])}
        if source_id in existing_ids and not overwrite:
            raise DuplicateSourceError(
                f"Source '{source_id}' already exists for {ticker}"
            )

        # Create directory
        source_dir.mkdir(parents=True, exist_ok=True)

        # Write metadata.json
        meta = {
            "id": source_id,
            "name": metadata["name"],
            "type": metadata["type"],
            "company": ticker,
            "date": metadata["date"],
            "event": metadata.get("event"),
            "total_slides": None,
            "extraction_status": "pending",
            "verification_status": "unverified",
            "slide_map": {},
        }
        meta_path = source_dir / "metadata.json"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

        # Update index.json
        entry = {
            "id": source_id,
            "name": metadata["name"],
            "type": metadata["type"],
            "date": metadata["date"],
            "total_slides": None,
            "verified": False,
        }
        sources = index.get("sources", [])
        if overwrite:
            sources = [s for s in sources if s["id"] != source_id]
        sources.append(entry)
        index["sources"] = sources

        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")

        return meta

    def get_source(self, ticker: str, source_id: str) -> dict:
        meta_path = (
            self.data_root / ticker / "sources" / source_id / "metadata.json"
        )
        if not meta_path.exists():
            raise FileNotFoundError(
                f"Source '{source_id}' not found for {ticker}"
            )
        return json.loads(meta_path.read_text())

    def list_sources(self, ticker: str) -> list[dict]:
        index_path = self.data_root / ticker / "sources" / "index.json"
        if not index_path.exists():
            return []
        index = json.loads(index_path.read_text())
        return index.get("sources", [])

    def update_source(self, ticker: str, source_id: str, updates: dict) -> dict:
        meta_path = (
            self.data_root / ticker / "sources" / source_id / "metadata.json"
        )
        if not meta_path.exists():
            raise FileNotFoundError(
                f"Source '{source_id}' not found for {ticker}"
            )

        meta = json.loads(meta_path.read_text())
        meta.update(updates)
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

        # Sync relevant fields to index
        index_path = self.data_root / ticker / "sources" / "index.json"
        if index_path.exists():
            index = json.loads(index_path.read_text())
            sync_keys = {"name", "type", "date", "total_slides", "verified"}
            for entry in index.get("sources", []):
                if entry["id"] == source_id:
                    for k in sync_keys:
                        if k in updates:
                            entry[k] = updates[k]
                    break
            index_path.write_text(
                json.dumps(index, indent=2, ensure_ascii=False) + "\n"
            )

        return meta

    def _validate_ticker(self, ticker: str) -> None:
        if not TICKER_RE.match(ticker):
            raise ValueError(
                f"Invalid ticker '{ticker}': must be 1-5 uppercase letters"
            )

    def _validate_metadata(self, metadata: dict) -> None:
        for field in ("name", "date", "type"):
            if field not in metadata:
                raise ValueError(f"Missing required metadata field: '{field}'")
        if metadata["type"] not in VALID_SOURCE_TYPES:
            raise ValueError(
                f"Invalid source type '{metadata['type']}'. "
                f"Must be one of: {', '.join(sorted(VALID_SOURCE_TYPES))}"
            )

    def _read_index(self, index_path: Path) -> dict:
        if index_path.exists():
            return json.loads(index_path.read_text())
        return {"sources": []}
