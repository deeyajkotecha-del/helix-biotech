"""
Extraction Pipeline Orchestrator

Coordinates the full extraction pipeline:
1. Scrape IR website for PDFs
2. Download presentations
3. Extract text from PDFs
4. Use AI to extract structured data (v2.1 two-pass)
5. Validate against schema
6. Deep merge with existing data (preserves manual enrichment)
7. Save to data/companies/{TICKER}/ directory
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..scrapers.ir_scraper import scrape_presentation_links, download_pdf
from ..scrapers.ir_website_mapping import get_ir_config, get_high_priority_tickers
from .pdf_extractor import extract_text_with_markers, get_pdf_metadata
from .ai_extractor import (
    extract_company_data,
    extract_single_asset,
    convert_to_file_format,
)
from .schema_validator import validate_company_json, validate_asset_json

logger = logging.getLogger(__name__)

# Directories
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
COMPANIES_DIR = DATA_DIR / "companies"
DOWNLOADS_DIR = DATA_DIR / "downloads"

# Fields that should never be overwritten by automated extraction
PROTECTED_FIELDS = {"sources", "analyst_note", "_manual_edits"}


class ExtractionOrchestrator:
    """Orchestrates the full extraction pipeline."""

    def __init__(
        self,
        api_key: str = None,
        rate_limit_seconds: float = 2.0,
        dry_run: bool = False,
        force_overwrite: bool = False
    ):
        self.api_key = api_key
        self.rate_limit_seconds = rate_limit_seconds
        self.dry_run = dry_run
        self.force_overwrite = force_overwrite

    def process_company(
        self,
        ticker: str,
        pdf_path: Optional[Path] = None,
        keywords: list[str] = None,
        asset_name: str = None,
        source_text: str = None,
        source_name: str = None
    ) -> dict:
        """
        Process a single company through the full pipeline.

        Args:
            ticker: Company ticker symbol
            pdf_path: Optional path to existing PDF (skips scraping/download)
            keywords: Keywords to filter presentations
            asset_name: If set, only extract this single asset (Pass 2 only)
            source_text: Pre-extracted text (skips PDF step entirely)
            source_name: Name/URL of the source (for attribution)

        Returns:
            Dict with extraction results and status
        """
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "status": "pending",
            "pdf_path": None,
            "extracted_files": [],
            "validation": [],
            "errors": [],
            "started_at": datetime.now().isoformat()
        }

        try:
            if source_text:
                # Text provided directly (e.g., from URL fetch)
                text = source_text
                src_name = source_name or "direct_text"
                logger.info(f"Using provided text: {len(text)} chars from {src_name}")
                result["source"] = src_name
            else:
                # Step 1: Get PDF (either provided or scrape/download)
                if pdf_path and Path(pdf_path).exists():
                    pdf_path = Path(pdf_path)
                    logger.info(f"Using provided PDF: {pdf_path}")
                else:
                    pdf_path = self._get_presentation_pdf(ticker, keywords)

                if not pdf_path:
                    result["status"] = "failed"
                    result["errors"].append("No PDF found or downloaded")
                    return result

                result["pdf_path"] = str(pdf_path)

                # Step 2: Extract text from PDF
                logger.info(f"Extracting text from {pdf_path.name}")
                text = extract_text_with_markers(pdf_path)
                metadata = get_pdf_metadata(pdf_path)
                src_name = pdf_path.name

                result["pdf_metadata"] = metadata
                logger.info(f"Extracted {len(text)} chars from {metadata['page_count']} pages")

            # Step 3: AI extraction
            ir_config = get_ir_config(ticker) or {}
            company_name = ir_config.get("name")

            if asset_name:
                # Single-asset extraction (Pass 2 only)
                logger.info(f"Single-asset extraction: {asset_name} for {ticker}")
                extracted_data = extract_single_asset(
                    pdf_text=text,
                    ticker=ticker,
                    asset_name=asset_name,
                    company_name=company_name,
                    source_filename=src_name,
                    api_key=self.api_key
                )
            else:
                # Full two-pass extraction
                logger.info(f"Running two-pass AI extraction for {ticker}")
                extracted_data = extract_company_data(
                    pdf_text=text,
                    ticker=ticker,
                    company_name=company_name,
                    source_filename=src_name,
                    api_key=self.api_key
                )

            if extracted_data.get("_error"):
                result["status"] = "partial"
                result["errors"].append(extracted_data["_error"])

            # Step 4: Convert to file format
            files_to_save = convert_to_file_format(extracted_data, ticker)

            # Step 5: Validate
            validation_results = self._validate_files(files_to_save, ticker)
            result["validation"] = validation_results

            for v in validation_results:
                if not v["valid"]:
                    for err in v["errors"]:
                        logger.warning(f"Validation error in {v['file']}: {err}")
                for warn in v.get("warnings", []):
                    logger.info(f"Validation warning in {v['file']}: {warn}")

            # Step 6: Save files (with merge)
            if not self.dry_run:
                saved_files = self._save_company_files(ticker, files_to_save)
                result["extracted_files"] = saved_files
            else:
                result["extracted_files"] = list(files_to_save.keys())
                # In dry-run, log the output
                for filename, data in files_to_save.items():
                    logger.debug(f"DRY RUN {filename}:\n{json.dumps(data, indent=2)[:2000]}")
                logger.info(f"DRY RUN: Would save {len(files_to_save)} files")

            result["status"] = "success"
            result["extraction_summary"] = {
                "files_generated": len(files_to_save),
                "assets_extracted": extracted_data.get("_extraction_metadata", {}).get("assets_extracted", []),
                "merge_mode": "overwrite" if self.force_overwrite else "deep_merge"
            }

        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}", exc_info=True)
            result["status"] = "failed"
            result["errors"].append(str(e))

        result["completed_at"] = datetime.now().isoformat()
        return result

    def process_batch(
        self,
        tickers: list[str],
        keywords: list[str] = None,
        stop_on_error: bool = False
    ) -> list[dict]:
        """Process multiple companies with rate limiting."""
        results = []

        for i, ticker in enumerate(tickers):
            logger.info(f"Processing {ticker} ({i+1}/{len(tickers)})")

            result = self.process_company(ticker, keywords=keywords)
            results.append(result)

            if result["status"] == "failed" and stop_on_error:
                logger.error(f"Stopping due to error on {ticker}")
                break

            if i < len(tickers) - 1:
                time.sleep(self.rate_limit_seconds)

        return results

    def process_priority(
        self,
        priority: str = "HIGH",
        keywords: list[str] = None
    ) -> list[dict]:
        """Process all companies of a given priority level."""
        from ..scrapers.ir_website_mapping import get_companies_by_priority

        tickers = get_companies_by_priority(priority)
        logger.info(f"Processing {len(tickers)} {priority} priority companies")

        return self.process_batch(tickers, keywords=keywords)

    def _get_presentation_pdf(
        self,
        ticker: str,
        keywords: list[str] = None
    ) -> Optional[Path]:
        """Scrape and download a presentation PDF."""
        if not keywords:
            ir_config = get_ir_config(ticker) or {}
            keywords = ir_config.get("presentation_patterns", ["Corporate Presentation"])

        logger.info(f"Scraping IR page for {ticker}")
        links = scrape_presentation_links(ticker, max_results=1, keywords=keywords)

        if not links:
            logger.warning(f"No presentation PDFs found for {ticker}")
            return None

        pdf_url = links[0]["url"]
        logger.info(f"Downloading: {links[0].get('title', pdf_url)}")

        try:
            pdf_path = download_pdf(pdf_url, ticker=ticker)
            return pdf_path
        except Exception as e:
            logger.error(f"Failed to download PDF: {e}")
            return None

    def _validate_files(self, files: dict, ticker: str) -> list[dict]:
        """Validate all files against v2.1 schema."""
        results = []
        for filename, data in files.items():
            if filename == "company.json":
                v = validate_company_json(data, ticker)
            else:
                v = validate_asset_json(data, ticker)
            v["file"] = filename
            results.append(v)
        return results

    def _save_company_files(self, ticker: str, files: dict) -> list[str]:
        """Save extracted data files, merging with existing data when present."""
        company_dir = COMPANIES_DIR / ticker.upper()
        company_dir.mkdir(parents=True, exist_ok=True)

        saved = []
        for filename, data in files.items():
            file_path = company_dir / filename
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            # Merge with existing if not force_overwrite
            if file_path.exists() and not self.force_overwrite:
                try:
                    with open(file_path) as f:
                        existing = json.load(f)
                    data = _deep_merge(existing, data)
                    logger.info(f"Merged new data into existing {file_path}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Could not read existing {file_path} for merge: {e}")

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

            saved.append(str(file_path))
            logger.info(f"Saved {file_path}")

        return saved


def _deep_merge(existing: dict, new: dict) -> dict:
    """
    Deep merge new extraction data into existing data.

    Rules:
    - New non-null values overwrite existing nulls
    - Existing non-null values preserved if new is null
    - Lists: new replaces existing only if new is longer or equal length
    - Nested dicts: recursive merge
    - Protected fields (sources, analyst_note) are never overwritten
    """
    merged = dict(existing)

    for key, new_value in new.items():
        # Never overwrite protected fields
        if key in PROTECTED_FIELDS:
            continue

        existing_value = merged.get(key)

        if existing_value is None:
            # Existing is null -> take new value
            merged[key] = new_value
        elif new_value is None:
            # New is null -> keep existing
            pass
        elif isinstance(existing_value, dict) and isinstance(new_value, dict):
            # Both dicts -> recursive merge
            merged[key] = _deep_merge(existing_value, new_value)
        elif isinstance(existing_value, list) and isinstance(new_value, list):
            # Lists: take new if longer or equal (assumes new extraction is fresher)
            if len(new_value) >= len(existing_value):
                merged[key] = new_value
            # else keep existing (it has more data, likely manually enriched)
        else:
            # Scalar: new overwrites existing
            merged[key] = new_value

    # Add any new keys from new that aren't in existing
    for key, new_value in new.items():
        if key not in merged and key not in PROTECTED_FIELDS:
            merged[key] = new_value

    return merged


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def process_company(
    ticker: str,
    pdf_path: Path = None,
    api_key: str = None,
    dry_run: bool = False,
    force_overwrite: bool = False
) -> dict:
    """Process a single company through the extraction pipeline."""
    orchestrator = ExtractionOrchestrator(
        api_key=api_key,
        dry_run=dry_run,
        force_overwrite=force_overwrite
    )
    return orchestrator.process_company(ticker, pdf_path)


def process_batch(
    tickers: list[str],
    api_key: str = None,
    rate_limit: float = 2.0,
    dry_run: bool = False
) -> list[dict]:
    """Process multiple companies with rate limiting."""
    orchestrator = ExtractionOrchestrator(
        api_key=api_key,
        rate_limit_seconds=rate_limit,
        dry_run=dry_run
    )
    return orchestrator.process_batch(tickers)


def process_high_priority(api_key: str = None, dry_run: bool = False) -> list[dict]:
    """Process all HIGH priority companies."""
    tickers = get_high_priority_tickers()
    return process_batch(tickers, api_key=api_key, dry_run=dry_run)
