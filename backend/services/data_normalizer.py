"""
Data Normalizer

Combines data from multiple presentations and external sources
into a canonical company data format.
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from services.fda_checker import FDAChecker
from services.trial_status_checker import TrialStatusChecker


DATA_DIR = Path(__file__).parent.parent / "data" / "companies"


class DataNormalizer:
    """Normalize and merge company data from multiple sources."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.company_dir = DATA_DIR / self.ticker.lower()
        self.fda_checker = FDAChecker()
        self.trial_checker = TrialStatusChecker()

    async def normalize(self, presentations: List[dict]) -> dict:
        """
        Normalize data from presentations and external sources.

        Args:
            presentations: List of analyzed presentation dicts

        Returns:
            Normalized company data dict
        """
        normalized = {
            "ticker": self.ticker,
            "name": None,
            "normalized_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sources": {
                "presentations": [],
                "fda_api": False,
                "clinicaltrials_api": False
            },
            "pipeline": [],
            "clinical_trials": [],
            "catalysts": [],
            "financials": {},
            "partnerships": [],
            "key_metrics": []
        }

        # Extract data from presentations
        for pres in presentations:
            normalized["sources"]["presentations"].append({
                "title": pres.get("title"),
                "date": pres.get("date"),
                "url": pres.get("source_url")
            })

            extracted = pres.get("extracted_data", {})

            # Merge pipeline
            for asset in extracted.get("pipeline", []):
                self._merge_pipeline_asset(normalized["pipeline"], asset)

            # Merge clinical results
            for result in extracted.get("clinical_results", []):
                self._merge_clinical_result(normalized["clinical_trials"], result)

            # Merge catalysts
            for catalyst in extracted.get("catalysts", []):
                self._merge_catalyst(normalized["catalysts"], catalyst)

            # Merge key metrics
            for metric in extracted.get("key_metrics", []):
                normalized["key_metrics"].append(metric)

        # Verify pipeline with FDA
        await self._verify_with_fda(normalized)

        # Verify trials with ClinicalTrials.gov
        await self._verify_with_clinicaltrials(normalized)

        # Deduplicate and clean
        self._deduplicate(normalized)

        # Save normalized data
        self._save(normalized)

        return normalized

    def _merge_pipeline_asset(self, pipeline: List[dict], new_asset: dict):
        """Merge a pipeline asset, updating if exists."""
        if not new_asset.get("name"):
            return

        name = new_asset["name"].lower().strip()

        # Find existing
        existing = None
        for asset in pipeline:
            if asset.get("name", "").lower().strip() == name:
                existing = asset
                break

            # Check aliases
            for alias in asset.get("aliases", []):
                if alias.lower().strip() == name:
                    existing = asset
                    break

        if existing:
            # Update with new data (newer takes precedence)
            for key, value in new_asset.items():
                if value and (not existing.get(key) or key in ["stage", "indication"]):
                    existing[key] = value
        else:
            pipeline.append({
                "name": new_asset.get("name"),
                "target": new_asset.get("target"),
                "indication": new_asset.get("indication"),
                "stage": new_asset.get("stage"),
                "partner": new_asset.get("partner"),
                "aliases": [],
                "clinical_data": [],
                "fda_verification": None,
                "ctgov_trials": []
            })

    def _merge_clinical_result(self, trials: List[dict], result: dict):
        """Merge clinical trial result."""
        if not result.get("trial") and not result.get("endpoint"):
            return

        # Try to find existing trial
        trial_name = result.get("trial", "").lower()
        existing = None

        for trial in trials:
            if trial.get("name", "").lower() == trial_name:
                existing = trial
                break

        if existing:
            # Add result to existing trial
            if "results" not in existing:
                existing["results"] = []
            existing["results"].append({
                "endpoint": result.get("endpoint"),
                "result": result.get("result"),
                "p_value": result.get("p_value"),
                "comparator": result.get("comparator")
            })
        else:
            trials.append({
                "name": result.get("trial"),
                "nct_id": None,
                "phase": None,
                "status": None,
                "results": [{
                    "endpoint": result.get("endpoint"),
                    "result": result.get("result"),
                    "p_value": result.get("p_value"),
                    "comparator": result.get("comparator")
                }]
            })

    def _merge_catalyst(self, catalysts: List[dict], new_catalyst: dict):
        """Merge catalyst event."""
        if not new_catalyst.get("event"):
            return

        event = new_catalyst["event"].lower().strip()

        # Check for duplicate
        for existing in catalysts:
            if existing.get("event", "").lower().strip() == event:
                # Update timing if more specific
                if new_catalyst.get("timing") and not existing.get("timing"):
                    existing["timing"] = new_catalyst["timing"]
                return

        catalysts.append({
            "event": new_catalyst.get("event"),
            "timing": new_catalyst.get("timing"),
            "asset": new_catalyst.get("asset"),
            "status": "upcoming"
        })

    async def _verify_with_fda(self, normalized: dict):
        """Verify pipeline drugs with FDA API."""
        for asset in normalized["pipeline"]:
            drug_name = asset.get("name", "").split("(")[0].strip()
            if not drug_name:
                continue

            status = self.fda_checker.check_approval_status(drug_name)

            if status.get("is_approved"):
                approval_date = status.get("approval_date")
                if approval_date and len(approval_date) == 8:
                    approval_date = f"{approval_date[:4]}-{approval_date[4:6]}-{approval_date[6:8]}"

                asset["fda_verification"] = {
                    "is_approved": True,
                    "approval_date": approval_date,
                    "brand_name": status.get("brand_name"),
                    "sponsor": status.get("sponsor"),
                    "indication_summary": status.get("indication", "")[:300] if status.get("indication") else None,
                    "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }

                # Update stage
                if "Approved" not in (asset.get("stage") or ""):
                    asset["stage"] = f"Approved / {asset.get('stage', '')}".strip(" /")

                normalized["sources"]["fda_api"] = True
            else:
                asset["fda_verification"] = {
                    "is_approved": False,
                    "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }

    async def _verify_with_clinicaltrials(self, normalized: dict):
        """Verify trials with ClinicalTrials.gov."""
        # Search for company's trials
        trials_found = self.trial_checker.search_trials_by_drug(
            self.ticker,
            limit=50
        )

        for trial_info in trials_found:
            nct_id = trial_info.get("nct_id")
            if not nct_id:
                continue

            # Get full trial details
            trial_data = self.trial_checker.get_trial_by_nct(nct_id)

            if trial_data.get("found"):
                # Try to match to existing trial
                matched = False
                for existing in normalized["clinical_trials"]:
                    if existing.get("nct_id") == nct_id:
                        existing["ctgov_verification"] = trial_data
                        matched = True
                        break

                if not matched:
                    normalized["clinical_trials"].append({
                        "name": trial_data.get("acronym") or trial_data.get("brief_title"),
                        "nct_id": nct_id,
                        "phase": trial_data.get("phase"),
                        "status": trial_data.get("overall_status"),
                        "enrollment": trial_data.get("enrollment"),
                        "primary_completion": trial_data.get("primary_completion_date"),
                        "ctgov_verification": trial_data
                    })

                normalized["sources"]["clinicaltrials_api"] = True

    def _deduplicate(self, normalized: dict):
        """Deduplicate and clean data."""
        # Deduplicate pipeline by name
        seen_names = set()
        unique_pipeline = []
        for asset in normalized["pipeline"]:
            name = asset.get("name", "").lower().strip()
            if name and name not in seen_names:
                seen_names.add(name)
                unique_pipeline.append(asset)
        normalized["pipeline"] = unique_pipeline

        # Deduplicate trials by NCT ID
        seen_ncts = set()
        unique_trials = []
        for trial in normalized["clinical_trials"]:
            nct = trial.get("nct_id")
            if nct:
                if nct not in seen_ncts:
                    seen_ncts.add(nct)
                    unique_trials.append(trial)
            else:
                unique_trials.append(trial)
        normalized["clinical_trials"] = unique_trials

        # Deduplicate catalysts by event
        seen_events = set()
        unique_catalysts = []
        for catalyst in normalized["catalysts"]:
            event = catalyst.get("event", "").lower().strip()
            if event and event not in seen_events:
                seen_events.add(event)
                unique_catalysts.append(catalyst)
        normalized["catalysts"] = unique_catalysts

    def _save(self, normalized: dict):
        """Save normalized data to file."""
        self.company_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.company_dir / "normalized.json"

        with open(output_path, "w") as f:
            json.dump(normalized, f, indent=2)

        print(f"Saved normalized data to {output_path}")

    def load_existing(self) -> Optional[dict]:
        """Load existing normalized data if available."""
        path = self.company_dir / "normalized.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None


async def normalize_company_data(ticker: str, presentations: List[dict]) -> dict:
    """Convenience function to normalize company data."""
    normalizer = DataNormalizer(ticker)
    return await normalizer.normalize(presentations)


async def main():
    """Test normalizer."""
    print("=" * 70)
    print("Data Normalizer")
    print("=" * 70)
    print("\nUse normalize_company_data(ticker, presentations) to normalize data.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
