"""
Master Company Data Refresher

Orchestrates all data sources (FDA, ClinicalTrials.gov, IR News)
to refresh pipeline data for a company with verified information.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List
import copy

from services.fda_checker import FDAChecker
from services.trial_status_checker import TrialStatusChecker
from services.ir_scraper import IRScraper


DATA_DIR = Path(__file__).parent.parent / "data" / "pipeline_data"

# Company IR URL mapping
COMPANY_IR_URLS = {
    "ARWR": "https://ir.arrowheadpharma.com/news-releases",
    "IONS": "https://ir.ionispharma.com/news-releases",
    "ALNY": "https://investors.alnylam.com/press-releases",
    "REGN": "https://investor.regeneron.com/news-releases",
    "VRTX": "https://investors.vrtx.com/news-releases",
    "BIIB": "https://investors.biogen.com/news-releases",
    "BMRN": "https://investors.biomarin.com/news-releases",
}


class CompanyRefresher:
    """
    Master refresher that pulls data from all verified sources.
    """

    def __init__(self, verbose: bool = True):
        self.fda_checker = FDAChecker()
        self.trial_checker = TrialStatusChecker()
        self.ir_scraper = IRScraper()
        self.verbose = verbose
        self.changes = []

    def refresh(self, ticker: str) -> dict:
        """
        Refresh all data for a company.

        Args:
            ticker: Stock ticker (e.g., 'ARWR')

        Returns:
            dict with refresh results and summary
        """
        ticker = ticker.upper()
        file_path = DATA_DIR / f"{ticker.lower()}.json"

        if not file_path.exists():
            return {
                "ticker": ticker,
                "status": "error",
                "message": f"No pipeline data file found: {file_path}"
            }

        # Load existing data
        with open(file_path, "r") as f:
            data = json.load(f)

        # Keep original for diff
        original_data = copy.deepcopy(data)
        self.changes = []

        self._log(f"\n{'='*70}")
        self._log(f"REFRESHING: {ticker} - {data.get('name', 'Unknown')}")
        self._log(f"{'='*70}")

        # 1. FDA Approval Status
        self._log("\n[1/3] Checking FDA approval status...")
        self._refresh_fda_data(data)

        # 2. ClinicalTrials.gov Status
        self._log("\n[2/3] Checking ClinicalTrials.gov...")
        self._refresh_trial_data(data)

        # 3. IR News
        self._log("\n[3/3] Scraping IR news...")
        ir_url = COMPANY_IR_URLS.get(ticker)
        if ir_url:
            self._refresh_ir_data(data, ir_url)
        else:
            self._log(f"  No IR URL configured for {ticker}")

        # Add refresh metadata
        data["_refresh"] = {
            "last_refreshed": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sources_checked": ["OpenFDA", "ClinicalTrials.gov", "IR News"],
            "changes_made": len(self.changes),
            "change_summary": self._summarize_changes()
        }

        # Save updated data
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

        # Generate report
        result = {
            "ticker": ticker,
            "status": "success",
            "file_path": str(file_path),
            "changes_made": len(self.changes),
            "changes": self.changes,
            "summary": self._summarize_changes()
        }

        self._print_summary(result)

        return result

    def _refresh_fda_data(self, data: dict):
        """Refresh FDA approval status for all programs."""
        company_name = data.get("name", "")

        for program in data.get("programs", []):
            drug_name = program.get("name", "")
            if not drug_name:
                continue

            # Extract generic name
            generic_name = drug_name.split("(")[0].strip()
            self._log(f"  Checking FDA for: {generic_name}")

            status = self.fda_checker.check_approval_status(generic_name)

            # Update program with FDA data
            fda_data = {
                "is_approved": status.get("is_approved", False),
                "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }

            if status.get("is_approved"):
                # Convert date format
                approval_date = status.get("approval_date")
                if approval_date and len(approval_date) == 8:
                    iso_date = f"{approval_date[:4]}-{approval_date[4:6]}-{approval_date[6:8]}"
                else:
                    iso_date = approval_date

                fda_data.update({
                    "approval_date": iso_date,
                    "brand_name": status.get("brand_name"),
                    "sponsor": status.get("sponsor"),
                    "application_number": status.get("application_number"),
                    "indication_summary": status.get("indication", "")[:300] if status.get("indication") else None
                })

                self._log(f"    APPROVED: {status.get('brand_name')} on {iso_date}")

                # Update catalysts with FDA-verified date
                self._update_approval_catalyst(program, iso_date, status.get("brand_name"))

            else:
                fda_data["raw_results_count"] = status.get("raw_results_count", 0)
                self._log(f"    Not approved (checked {status.get('raw_results_count', 0)} results)")

            program["fda_verification"] = fda_data

    def _update_approval_catalyst(self, program: dict, approval_date: str, brand_name: Optional[str]):
        """Update catalyst entry with FDA-verified approval date."""
        for catalyst in program.get("catalysts", []):
            event = catalyst.get("event", "").lower()
            if "approval" in event and ("fda" in event or "us" in event):
                old_date = catalyst.get("actual_date")
                if old_date != approval_date:
                    self.changes.append({
                        "type": "fda_date_correction",
                        "program": program.get("name"),
                        "field": "catalyst.actual_date",
                        "old_value": old_date,
                        "new_value": approval_date,
                        "source": "OpenFDA"
                    })

                catalyst["actual_date"] = approval_date
                catalyst["status"] = "completed"
                catalyst["fda_verified"] = True
                if brand_name:
                    catalyst["outcome"] = f"Approved as {brand_name}"

    def _refresh_trial_data(self, data: dict):
        """Refresh clinical trial status for all programs."""
        for program in data.get("programs", []):
            clinical_data = program.get("clinical_data", [])

            for trial in clinical_data:
                nct_id = trial.get("nct_id")
                if not nct_id:
                    continue

                self._log(f"  Checking {nct_id}: {trial.get('trial_name', 'Unknown')}")

                ctgov_data = self.trial_checker.get_trial_by_nct(nct_id)

                if ctgov_data.get("found"):
                    # Add verification data
                    trial["ctgov_verification"] = {
                        "verified_at": ctgov_data.get("verified_at"),
                        "official_title": ctgov_data.get("official_title"),
                        "overall_status": ctgov_data.get("overall_status"),
                        "phase": ctgov_data.get("phase"),
                        "enrollment": ctgov_data.get("enrollment"),
                        "enrollment_type": ctgov_data.get("enrollment_type"),
                        "primary_completion_date": ctgov_data.get("primary_completion_date"),
                        "has_results": ctgov_data.get("has_results"),
                        "sponsor": ctgov_data.get("sponsor"),
                        "url": ctgov_data.get("url")
                    }

                    # Check for status changes
                    if trial.get("status") != ctgov_data.get("overall_status"):
                        old_status = trial.get("status")
                        new_status = ctgov_data.get("overall_status")
                        if old_status:  # Only log if there was a previous value
                            self.changes.append({
                                "type": "trial_status_change",
                                "program": program.get("name"),
                                "trial": trial.get("trial_name"),
                                "nct_id": nct_id,
                                "old_value": old_status,
                                "new_value": new_status,
                                "source": "ClinicalTrials.gov"
                            })
                        trial["status"] = new_status

                    # Check enrollment
                    design = trial.get("design", {})
                    ctgov_enrollment = ctgov_data.get("enrollment")
                    if ctgov_enrollment and design.get("n_enrolled") != ctgov_enrollment:
                        old_enrollment = design.get("n_enrolled")
                        if old_enrollment:
                            self.changes.append({
                                "type": "enrollment_update",
                                "program": program.get("name"),
                                "trial": trial.get("trial_name"),
                                "old_value": old_enrollment,
                                "new_value": ctgov_enrollment,
                                "source": "ClinicalTrials.gov"
                            })
                        design["n_enrolled"] = ctgov_enrollment
                        design["enrollment_verified"] = True

                    self._log(f"    Status: {ctgov_data.get('overall_status')} | "
                             f"Enrolled: {ctgov_data.get('enrollment')} | "
                             f"Results: {'Yes' if ctgov_data.get('has_results') else 'No'}")

                else:
                    self._log(f"    ERROR: {ctgov_data.get('error')}")
                    trial["ctgov_verification"] = {
                        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "error": ctgov_data.get("error")
                    }

    def _refresh_ir_data(self, data: dict, ir_url: str):
        """Refresh with recent IR news."""
        self._log(f"  Scraping: {ir_url}")

        news_result = self.ir_scraper.scrape_news(ir_url, days_back=90)

        if news_result.get("errors"):
            self._log(f"    Errors: {news_result['errors']}")
            data["ir_news"] = {
                "scraped_at": news_result.get("scraped_at"),
                "errors": news_result.get("errors"),
                "items": []
            }
            return

        news_items = news_result.get("news_items", [])
        catalyst_news = [item for item in news_items if item.get("is_catalyst")]

        self._log(f"    Found {len(news_items)} news items, {len(catalyst_news)} catalysts")

        # Extract drug names from programs
        drug_names = []
        for program in data.get("programs", []):
            drug_names.append(program.get("name", "").split("(")[0].strip())
            drug_names.extend(program.get("aliases", []))

        # Find drug-specific news
        drug_news = self.ir_scraper.extract_drug_mentions(news_items, drug_names)

        # Store IR data
        data["ir_news"] = {
            "scraped_at": news_result.get("scraped_at"),
            "url": ir_url,
            "total_items": len(news_items),
            "catalyst_items": len(catalyst_news),
            "recent_catalysts": catalyst_news[:10],  # Keep top 10 catalyst news
            "drug_mentions": {k: len(v) for k, v in drug_news.items() if v}
        }

        # Check for potential catalyst updates
        for item in catalyst_news[:5]:
            self._log(f"    CATALYST: {item.get('date')} - {item.get('title', '')[:50]}...")

        # Match news to existing catalysts
        self._match_news_to_catalysts(data, catalyst_news)

    def _match_news_to_catalysts(self, data: dict, news_items: List[dict]):
        """Try to match news items to existing catalyst entries."""
        for program in data.get("programs", []):
            drug_name = program.get("name", "").lower()
            aliases = [a.lower() for a in program.get("aliases", [])]

            for catalyst in program.get("catalysts", []):
                if catalyst.get("status") == "completed":
                    continue  # Skip already completed

                event = catalyst.get("event", "").lower()

                for news in news_items:
                    title = news.get("title", "").lower()

                    # Check if news mentions this drug
                    if not any(name in title for name in [drug_name.split("(")[0].strip()] + aliases):
                        continue

                    # Check if news matches catalyst type
                    if "approval" in event and "approval" in title:
                        catalyst["potential_match"] = {
                            "news_date": news.get("date"),
                            "news_title": news.get("title"),
                            "news_url": news.get("url")
                        }
                        break
                    elif "data" in event and any(kw in title for kw in ["data", "results", "endpoint"]):
                        catalyst["potential_match"] = {
                            "news_date": news.get("date"),
                            "news_title": news.get("title"),
                            "news_url": news.get("url")
                        }
                        break

    def _summarize_changes(self) -> dict:
        """Summarize changes by type."""
        summary = {
            "fda_updates": 0,
            "trial_status_changes": 0,
            "enrollment_updates": 0,
            "news_catalysts_found": 0
        }

        for change in self.changes:
            change_type = change.get("type", "")
            if "fda" in change_type:
                summary["fda_updates"] += 1
            elif "trial_status" in change_type:
                summary["trial_status_changes"] += 1
            elif "enrollment" in change_type:
                summary["enrollment_updates"] += 1

        return summary

    def _print_summary(self, result: dict):
        """Print refresh summary."""
        self._log(f"\n{'='*70}")
        self._log("REFRESH COMPLETE")
        self._log(f"{'='*70}")
        self._log(f"Ticker: {result['ticker']}")
        self._log(f"Status: {result['status']}")
        self._log(f"Total Changes: {result['changes_made']}")

        if result.get('summary'):
            self._log("\nChange Summary:")
            for key, value in result['summary'].items():
                if value > 0:
                    self._log(f"  - {key}: {value}")

        if result.get('changes'):
            self._log("\nDetailed Changes:")
            for change in result['changes']:
                self._log(f"  [{change.get('source')}] {change.get('program', '')} - "
                         f"{change.get('type')}: {change.get('old_value')} -> {change.get('new_value')}")

    def _log(self, message: str):
        """Print message if verbose mode."""
        if self.verbose:
            print(message)


def refresh_arwr():
    """Run full refresh on ARWR."""
    refresher = CompanyRefresher(verbose=True)
    result = refresher.refresh("ARWR")
    return result


if __name__ == "__main__":
    refresh_arwr()
