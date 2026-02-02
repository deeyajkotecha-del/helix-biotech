"""
Master Refresh Service

Orchestrates the complete data refresh pipeline for any biotech company:
1. Discover IR page
2. Scrape presentations
3. Analyze with Vision API
4. Normalize and merge data
5. Verify with FDA/ClinicalTrials.gov
6. Generate thesis HTML

Usage: python -m services.master_refresh ARWR
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List

from services.ir_discoverer import IRDiscoverer
from services.presentation_scraper import PresentationScraper
from services.pdf_vision_analyzer import PDFVisionAnalyzer, PYMUPDF_AVAILABLE, PDF2IMAGE_AVAILABLE
from services.data_normalizer import DataNormalizer
from services.fda_checker import FDAChecker
from services.trial_status_checker import TrialStatusChecker


DATA_DIR = Path(__file__).parent.parent / "data" / "companies"
LOGS_DIR = Path(__file__).parent.parent / "logs"


class MasterRefresh:
    """Orchestrate complete company data refresh."""

    def __init__(self, ticker: str, verbose: bool = True):
        self.ticker = ticker.upper()
        self.verbose = verbose
        self.company_dir = DATA_DIR / self.ticker.lower()
        self.log_entries = []

    def _log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entry = f"[{timestamp}] [{level}] {message}"
        self.log_entries.append(entry)
        if self.verbose:
            print(entry)

    async def refresh(
        self,
        months_back: int = 12,
        max_presentations: int = 10,
        max_slides_per_pdf: int = 50,
        skip_vision_analysis: bool = False
    ) -> dict:
        """
        Run complete refresh pipeline for a company.

        Args:
            months_back: How many months of presentations to fetch
            max_presentations: Maximum presentations to analyze
            max_slides_per_pdf: Maximum slides per PDF to analyze
            skip_vision_analysis: Skip PDF analysis (use cached data)

        Returns:
            Refresh result with status, data, and logs
        """
        result = {
            "ticker": self.ticker,
            "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "completed_at": None,
            "status": "in_progress",
            "steps": {
                "ir_discovery": {"status": "pending"},
                "presentation_scraping": {"status": "pending"},
                "vision_analysis": {"status": "pending"},
                "data_normalization": {"status": "pending"},
                "fda_verification": {"status": "pending"},
                "trials_verification": {"status": "pending"}
            },
            "data_sources": {
                "ir_page": None,
                "presentations_found": 0,
                "presentations_analyzed": 0,
                "fda_verified": False,
                "trials_verified": False
            },
            "output_files": [],
            "errors": [],
            "logs": []
        }

        # Create company directory
        self.company_dir.mkdir(parents=True, exist_ok=True)

        self._log(f"Starting refresh for {self.ticker}")
        self._log("=" * 60)

        # Step 1: Discover IR page
        self._log("Step 1: Discovering IR page...")
        result["steps"]["ir_discovery"]["status"] = "running"

        try:
            async with IRDiscoverer() as discoverer:
                ir_info = await discoverer.discover(self.ticker)

            if ir_info.get("ir_base_url"):
                # Accept both verified and unverified (known) IR URLs
                status = "completed" if ir_info.get("verified") else "completed_unverified"
                result["steps"]["ir_discovery"]["status"] = status
                result["steps"]["ir_discovery"]["data"] = ir_info
                result["data_sources"]["ir_page"] = ir_info.get("download_library_url") or ir_info.get("ir_base_url")
                self._log(f"  Found IR page: {result['data_sources']['ir_page']}")
                self._log(f"  Discovery method: {ir_info.get('discovery_method')}")
                if not ir_info.get("verified"):
                    self._log("  Note: URL not verified (network may be restricted)")

                # Save IR info
                ir_path = self.company_dir / "ir_info.json"
                with open(ir_path, "w") as f:
                    json.dump(ir_info, f, indent=2)
                result["output_files"].append(str(ir_path))
            else:
                result["steps"]["ir_discovery"]["status"] = "failed"
                result["steps"]["ir_discovery"]["error"] = "Could not discover IR page"
                self._log("  FAILED: Could not discover IR page", "ERROR")

        except Exception as e:
            result["steps"]["ir_discovery"]["status"] = "failed"
            result["steps"]["ir_discovery"]["error"] = str(e)
            result["errors"].append(f"IR discovery: {e}")
            self._log(f"  ERROR: {e}", "ERROR")

        # Step 2: Scrape presentations
        self._log("")
        self._log("Step 2: Scraping presentations...")
        result["steps"]["presentation_scraping"]["status"] = "running"

        presentations_list = []
        if result["data_sources"]["ir_page"]:
            try:
                async with PresentationScraper() as scraper:
                    presentations_list = await scraper.scrape(
                        result["data_sources"]["ir_page"],
                        months_back=months_back
                    )

                result["data_sources"]["presentations_found"] = len(presentations_list)
                result["steps"]["presentation_scraping"]["status"] = "completed"
                result["steps"]["presentation_scraping"]["count"] = len(presentations_list)
                self._log(f"  Found {len(presentations_list)} presentations")

                # Save presentations list
                pres_list_path = self.company_dir / "presentations_list.json"
                with open(pres_list_path, "w") as f:
                    json.dump(presentations_list, f, indent=2)
                result["output_files"].append(str(pres_list_path))

                # Log each presentation
                for p in presentations_list[:5]:
                    self._log(f"    [{p.get('date', 'No date')}] {p.get('title', 'No title')[:50]}...")

                if len(presentations_list) > 5:
                    self._log(f"    ... and {len(presentations_list) - 5} more")

            except Exception as e:
                error_str = str(e)
                if "Cannot connect" in error_str or "timeout" in error_str.lower():
                    result["steps"]["presentation_scraping"]["status"] = "skipped_network"
                    result["steps"]["presentation_scraping"]["reason"] = "Network access restricted"
                    self._log(f"  SKIPPED: Cannot access IR page (network restricted)")
                else:
                    result["steps"]["presentation_scraping"]["status"] = "failed"
                    result["steps"]["presentation_scraping"]["error"] = error_str
                    result["errors"].append(f"Presentation scraping: {e}")
                    self._log(f"  ERROR: {e}", "ERROR")
        else:
            result["steps"]["presentation_scraping"]["status"] = "skipped"
            result["steps"]["presentation_scraping"]["reason"] = "No IR page found"
            self._log("  SKIPPED: No IR page found")

        # Step 3: Vision analysis of PDFs
        self._log("")
        self._log("Step 3: Analyzing presentations with Vision API...")
        result["steps"]["vision_analysis"]["status"] = "running"

        analyzed_presentations = []

        if skip_vision_analysis:
            result["steps"]["vision_analysis"]["status"] = "skipped"
            result["steps"]["vision_analysis"]["reason"] = "Skip flag set"
            self._log("  SKIPPED: Vision analysis disabled")

            # Try to load cached analysis
            cache_path = self.company_dir / "analyzed_presentations.json"
            if cache_path.exists():
                with open(cache_path) as f:
                    analyzed_presentations = json.load(f)
                self._log(f"  Loaded {len(analyzed_presentations)} cached analyses")

        elif not presentations_list:
            result["steps"]["vision_analysis"]["status"] = "skipped"
            result["steps"]["vision_analysis"]["reason"] = "No presentations to analyze"
            self._log("  SKIPPED: No presentations found")

        elif not PYMUPDF_AVAILABLE and not PDF2IMAGE_AVAILABLE:
            result["steps"]["vision_analysis"]["status"] = "failed"
            result["steps"]["vision_analysis"]["error"] = "No PDF library available (install pymupdf or pdf2image)"
            self._log("  FAILED: No PDF library available", "ERROR")

        else:
            try:
                analyzer = PDFVisionAnalyzer()

                # Analyze top presentations (limit to max_presentations)
                to_analyze = [p for p in presentations_list if p.get("url")][:max_presentations]
                self._log(f"  Analyzing {len(to_analyze)} presentations...")

                for i, pres in enumerate(to_analyze):
                    self._log(f"  [{i+1}/{len(to_analyze)}] {pres.get('title', 'Unknown')[:50]}...")

                    try:
                        analysis = await analyzer.analyze_presentation(
                            pres["url"],
                            max_slides=max_slides_per_pdf
                        )

                        # Merge presentation metadata with analysis
                        analysis["title"] = pres.get("title")
                        analysis["date"] = pres.get("date")
                        analysis["type"] = pres.get("type")

                        analyzed_presentations.append(analysis)
                        self._log(f"    Analyzed {analysis.get('analyzed_slides', 0)} slides")

                        if analysis.get("errors"):
                            for err in analysis["errors"][:3]:
                                self._log(f"    Warning: {err}", "WARN")

                    except Exception as e:
                        self._log(f"    ERROR analyzing: {e}", "ERROR")
                        result["errors"].append(f"PDF analysis ({pres.get('title')}): {e}")

                result["data_sources"]["presentations_analyzed"] = len(analyzed_presentations)
                result["steps"]["vision_analysis"]["status"] = "completed"
                result["steps"]["vision_analysis"]["analyzed"] = len(analyzed_presentations)

                # Save analyzed presentations
                analysis_path = self.company_dir / "analyzed_presentations.json"
                with open(analysis_path, "w") as f:
                    json.dump(analyzed_presentations, f, indent=2)
                result["output_files"].append(str(analysis_path))

            except Exception as e:
                result["steps"]["vision_analysis"]["status"] = "failed"
                result["steps"]["vision_analysis"]["error"] = str(e)
                result["errors"].append(f"Vision analysis: {e}")
                self._log(f"  ERROR: {e}", "ERROR")

        # Step 4: Normalize and merge data
        self._log("")
        self._log("Step 4: Normalizing data...")
        result["steps"]["data_normalization"]["status"] = "running"

        normalized_data = None
        try:
            normalizer = DataNormalizer(self.ticker)
            normalized_data = await normalizer.normalize(analyzed_presentations)

            result["steps"]["data_normalization"]["status"] = "completed"
            result["steps"]["data_normalization"]["pipeline_count"] = len(normalized_data.get("pipeline", []))
            result["steps"]["data_normalization"]["trials_count"] = len(normalized_data.get("clinical_trials", []))
            result["steps"]["data_normalization"]["catalysts_count"] = len(normalized_data.get("catalysts", []))

            self._log(f"  Pipeline assets: {len(normalized_data.get('pipeline', []))}")
            self._log(f"  Clinical trials: {len(normalized_data.get('clinical_trials', []))}")
            self._log(f"  Catalysts: {len(normalized_data.get('catalysts', []))}")

            # normalized.json already saved by normalizer
            result["output_files"].append(str(self.company_dir / "normalized.json"))

        except Exception as e:
            result["steps"]["data_normalization"]["status"] = "failed"
            result["steps"]["data_normalization"]["error"] = str(e)
            result["errors"].append(f"Normalization: {e}")
            self._log(f"  ERROR: {e}", "ERROR")

        # Step 5: FDA verification (already done in normalizer, but log status)
        self._log("")
        self._log("Step 5: FDA verification status...")

        if normalized_data and normalized_data.get("sources", {}).get("fda_api"):
            result["steps"]["fda_verification"]["status"] = "completed"
            result["data_sources"]["fda_verified"] = True

            # Count FDA-verified assets
            verified_count = sum(
                1 for asset in normalized_data.get("pipeline", [])
                if asset.get("fda_verification", {}).get("is_approved")
            )
            self._log(f"  {verified_count} assets have FDA approval verification")
            result["steps"]["fda_verification"]["verified_count"] = verified_count
        else:
            result["steps"]["fda_verification"]["status"] = "skipped"
            self._log("  No FDA verifications performed")

        # Step 6: ClinicalTrials.gov verification status
        self._log("")
        self._log("Step 6: ClinicalTrials.gov verification status...")

        if normalized_data and normalized_data.get("sources", {}).get("clinicaltrials_api"):
            result["steps"]["trials_verification"]["status"] = "completed"
            result["data_sources"]["trials_verified"] = True

            # Count verified trials
            verified_count = sum(
                1 for trial in normalized_data.get("clinical_trials", [])
                if trial.get("ctgov_verification")
            )
            self._log(f"  {verified_count} trials verified with ClinicalTrials.gov")
            result["steps"]["trials_verification"]["verified_count"] = verified_count
        else:
            result["steps"]["trials_verification"]["status"] = "skipped"
            self._log("  No ClinicalTrials.gov verifications performed")

        # Complete
        result["completed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        result["status"] = "completed" if not result["errors"] else "completed_with_errors"
        result["logs"] = self.log_entries

        # Save refresh log
        self._log("")
        self._log("=" * 60)
        self._log(f"Refresh complete. Status: {result['status']}")

        if result["errors"]:
            self._log(f"Errors: {len(result['errors'])}")

        # Save full result
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_filename = f"refresh_{self.ticker.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_path = LOGS_DIR / log_filename
        with open(log_path, "w") as f:
            json.dump(result, f, indent=2)
        result["output_files"].append(str(log_path))

        self._log(f"Log saved to: {log_path}")

        return result


async def refresh_company(
    ticker: str,
    months_back: int = 12,
    max_presentations: int = 10,
    skip_vision: bool = False,
    verbose: bool = True
) -> dict:
    """Convenience function to refresh a company."""
    refresher = MasterRefresh(ticker, verbose=verbose)
    return await refresher.refresh(
        months_back=months_back,
        max_presentations=max_presentations,
        skip_vision_analysis=skip_vision
    )


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Refresh company data from IR presentations")
    parser.add_argument("ticker", help="Stock ticker (e.g., ARWR)")
    parser.add_argument("--months", type=int, default=12, help="Months of history to fetch")
    parser.add_argument("--max-presentations", type=int, default=10, help="Max presentations to analyze")
    parser.add_argument("--skip-vision", action="store_true", help="Skip Vision API analysis (use cache)")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")

    args = parser.parse_args()

    print("=" * 70)
    print(f"Master Refresh: {args.ticker.upper()}")
    print("=" * 70)
    print()

    result = await refresh_company(
        args.ticker,
        months_back=args.months,
        max_presentations=args.max_presentations,
        skip_vision=args.skip_vision,
        verbose=not args.quiet
    )

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Status: {result['status']}")
    print(f"Presentations found: {result['data_sources']['presentations_found']}")
    print(f"Presentations analyzed: {result['data_sources']['presentations_analyzed']}")
    print(f"FDA verified: {result['data_sources']['fda_verified']}")
    print(f"Trials verified: {result['data_sources']['trials_verified']}")

    if result['errors']:
        print(f"\nErrors ({len(result['errors'])}):")
        for err in result['errors']:
            print(f"  - {err}")

    print(f"\nOutput files:")
    for f in result['output_files']:
        print(f"  - {f}")


if __name__ == "__main__":
    asyncio.run(main())
