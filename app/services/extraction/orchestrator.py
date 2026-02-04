"""
Extraction Pipeline Orchestrator

Coordinates the full extraction pipeline:
1. Scrape IR website for PDFs
2. Download presentations
3. Extract text from PDFs
4. Use AI to extract structured data
5. Save to data/companies/{TICKER}/ directory
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
from .ai_extractor import extract_company_data, convert_to_file_format

logger = logging.getLogger(__name__)

# Directories
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
COMPANIES_DIR = DATA_DIR / "companies"
DOWNLOADS_DIR = DATA_DIR / "downloads"


class ExtractionOrchestrator:
    """Orchestrates the full extraction pipeline."""

    def __init__(
        self,
        api_key: str = None,
        rate_limit_seconds: float = 2.0,
        dry_run: bool = False
    ):
        """
        Initialize the orchestrator.

        Args:
            api_key: Anthropic API key (uses env var if not provided)
            rate_limit_seconds: Seconds to wait between API calls
            dry_run: If True, don't actually save files
        """
        self.api_key = api_key
        self.rate_limit_seconds = rate_limit_seconds
        self.dry_run = dry_run

    def process_company(
        self,
        ticker: str,
        pdf_path: Optional[Path] = None,
        keywords: list[str] = None
    ) -> dict:
        """
        Process a single company through the full pipeline.

        Args:
            ticker: Company ticker symbol
            pdf_path: Optional path to existing PDF (skips scraping/download)
            keywords: Keywords to filter presentations

        Returns:
            Dict with extraction results and status
        """
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "status": "pending",
            "pdf_path": None,
            "extracted_files": [],
            "errors": [],
            "started_at": datetime.now().isoformat()
        }

        try:
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
            pdf_text = extract_text_with_markers(pdf_path)
            metadata = get_pdf_metadata(pdf_path)

            result["pdf_metadata"] = metadata
            logger.info(f"Extracted {len(pdf_text)} chars from {metadata['page_count']} pages")

            # Step 3: AI extraction
            logger.info(f"Running AI extraction for {ticker}")
            ir_config = get_ir_config(ticker) or {}
            company_name = ir_config.get("name")

            extracted_data = extract_company_data(
                pdf_text=pdf_text,
                ticker=ticker,
                company_name=company_name,
                source_filename=pdf_path.name,
                api_key=self.api_key
            )

            if extracted_data.get("_error"):
                result["status"] = "partial"
                result["errors"].append(extracted_data["_error"])

            # Step 4: Convert to file format
            files_to_save = convert_to_file_format(extracted_data, ticker)

            # Step 5: Save files
            if not self.dry_run:
                saved_files = self._save_company_files(ticker, files_to_save)
                result["extracted_files"] = saved_files
            else:
                result["extracted_files"] = list(files_to_save.keys())
                logger.info(f"DRY RUN: Would save {len(files_to_save)} files")

            result["status"] = "success"
            result["extraction_summary"] = {
                "assets_found": len(extracted_data.get("pipeline_assets", [])),
                "trials_found": len(extracted_data.get("clinical_trials", [])),
                "catalysts_found": len(extracted_data.get("upcoming_catalysts", []))
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
        """
        Process multiple companies with rate limiting.

        Args:
            tickers: List of ticker symbols
            keywords: Keywords to filter presentations
            stop_on_error: If True, stop on first error

        Returns:
            List of result dicts for each company
        """
        results = []

        for i, ticker in enumerate(tickers):
            logger.info(f"Processing {ticker} ({i+1}/{len(tickers)})")

            result = self.process_company(ticker, keywords=keywords)
            results.append(result)

            if result["status"] == "failed" and stop_on_error:
                logger.error(f"Stopping due to error on {ticker}")
                break

            # Rate limiting
            if i < len(tickers) - 1:
                time.sleep(self.rate_limit_seconds)

        return results

    def process_priority(
        self,
        priority: str = "HIGH",
        keywords: list[str] = None
    ) -> list[dict]:
        """
        Process all companies of a given priority level.

        Args:
            priority: Priority level (HIGH, MED-HIGH, MEDIUM, etc.)

        Returns:
            List of result dicts
        """
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
        # Use company's preferred keywords if not specified
        if not keywords:
            ir_config = get_ir_config(ticker) or {}
            keywords = ir_config.get("presentation_patterns", ["Corporate Presentation"])

        # Scrape for PDF links
        logger.info(f"Scraping IR page for {ticker}")
        links = scrape_presentation_links(ticker, max_results=1, keywords=keywords)

        if not links:
            logger.warning(f"No presentation PDFs found for {ticker}")
            return None

        # Download the first PDF
        pdf_url = links[0]["url"]
        logger.info(f"Downloading: {links[0].get('title', pdf_url)}")

        try:
            pdf_path = download_pdf(pdf_url, ticker=ticker)
            return pdf_path
        except Exception as e:
            logger.error(f"Failed to download PDF: {e}")
            return None

    def _save_company_files(self, ticker: str, files: dict) -> list[str]:
        """Save extracted data files to the company directory."""
        company_dir = COMPANIES_DIR / ticker.upper()
        company_dir.mkdir(parents=True, exist_ok=True)

        saved = []
        for filename, data in files.items():
            file_path = company_dir / filename

            # Ensure parent directory exists (handles nested paths like kt485/sar447971.json)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            # Add extraction metadata
            data["_last_extracted"] = datetime.now().isoformat()

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

            saved.append(str(file_path))
            logger.info(f"Saved {file_path}")

        return saved


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def process_company(
    ticker: str,
    pdf_path: Path = None,
    api_key: str = None,
    dry_run: bool = False
) -> dict:
    """
    Process a single company through the extraction pipeline.

    Args:
        ticker: Company ticker symbol
        pdf_path: Optional path to existing PDF
        api_key: Anthropic API key
        dry_run: If True, don't save files

    Returns:
        Dict with extraction results
    """
    orchestrator = ExtractionOrchestrator(api_key=api_key, dry_run=dry_run)
    return orchestrator.process_company(ticker, pdf_path)


def process_batch(
    tickers: list[str],
    api_key: str = None,
    rate_limit: float = 2.0,
    dry_run: bool = False
) -> list[dict]:
    """
    Process multiple companies with rate limiting.

    Args:
        tickers: List of ticker symbols
        api_key: Anthropic API key
        rate_limit: Seconds between API calls
        dry_run: If True, don't save files

    Returns:
        List of result dicts
    """
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
