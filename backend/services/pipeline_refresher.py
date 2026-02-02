"""
Pipeline Data Refresher

Automatically updates pipeline data files with verified information from
authoritative APIs: FDA, ClinicalTrials.gov, SEC EDGAR.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from services.fda_checker import FDAChecker


DATA_DIR = Path(__file__).parent.parent / "data" / "pipeline_data"


class PipelineRefresher:
    """Refresh pipeline data with verified API data."""

    def __init__(self):
        self.fda_checker = FDAChecker()
        self.changes = []

    def refresh_ticker(self, ticker: str) -> dict:
        """
        Refresh pipeline data for a specific ticker.

        Args:
            ticker: Stock ticker (e.g., 'ARWR')

        Returns:
            dict with refresh results
        """
        ticker = ticker.upper()
        file_path = DATA_DIR / f"{ticker.lower()}.json"

        if not file_path.exists():
            return {
                "ticker": ticker,
                "status": "error",
                "message": f"No pipeline data file found: {file_path}"
            }

        with open(file_path, "r") as f:
            data = json.load(f)

        self.changes = []
        original_data = json.dumps(data)

        # Refresh FDA approval status for each program
        for program in data.get("programs", []):
            self._refresh_fda_status(program, data.get("name", ""))

        # Add refresh metadata
        data["_refresh"] = {
            "last_refreshed": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sources_checked": ["OpenFDA"],
            "changes_made": len(self.changes),
            "change_details": self.changes
        }

        # Save if changed
        if json.dumps(data) != original_data:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

        return {
            "ticker": ticker,
            "status": "success",
            "changes_made": len(self.changes),
            "changes": self.changes
        }

    def _refresh_fda_status(self, program: dict, company_name: str):
        """Refresh FDA approval status for a program."""
        drug_name = program.get("name", "")
        if not drug_name:
            return

        # Extract generic name from "Plozasiran (ARO-APOC3)" format
        generic_name = drug_name.split("(")[0].strip()

        # Check FDA for approval status
        fda_status = self.fda_checker.check_approval_status(generic_name)

        if fda_status.get("is_approved"):
            # Update program with FDA-verified data
            fda_approval_date = fda_status.get("approval_date")
            fda_brand_name = fda_status.get("brand_name")

            # Convert FDA date format (YYYYMMDD) to ISO (YYYY-MM-DD)
            if fda_approval_date and len(fda_approval_date) == 8:
                iso_date = f"{fda_approval_date[:4]}-{fda_approval_date[4:6]}-{fda_approval_date[6:8]}"
            else:
                iso_date = fda_approval_date

            # Update catalysts with FDA-verified approval date
            for catalyst in program.get("catalysts", []):
                if "approval" in catalyst.get("event", "").lower() and "FDA" in catalyst.get("event", ""):
                    old_date = catalyst.get("actual_date")
                    if old_date != iso_date:
                        catalyst["actual_date"] = iso_date
                        catalyst["fda_verified"] = True
                        catalyst["status"] = "completed"
                        if fda_brand_name:
                            catalyst["outcome"] = f"Approved as {fda_brand_name}"

                        self.changes.append({
                            "program": drug_name,
                            "field": "catalyst.actual_date",
                            "old_value": old_date,
                            "new_value": iso_date,
                            "source": "OpenFDA"
                        })

            # Update stage if approved
            current_stage = program.get("stage", "")
            if "Approved" not in current_stage:
                indication = fda_status.get("indication", "")[:50] if fda_status.get("indication") else ""
                if indication:
                    # Extract short indication
                    if "familial chylomicronemia" in indication.lower():
                        indication_short = "FCS"
                    else:
                        indication_short = indication.split(".")[0][:20]
                    new_stage = f"Approved ({indication_short})"
                else:
                    new_stage = "Approved"

                # Don't overwrite if already shows approved for different indication
                if "Approved" not in current_stage:
                    self.changes.append({
                        "program": drug_name,
                        "field": "stage",
                        "old_value": current_stage,
                        "new_value": new_stage,
                        "source": "OpenFDA"
                    })

            # Update aliases with brand name if not present
            aliases = program.get("aliases", [])
            if fda_brand_name and fda_brand_name not in aliases:
                aliases.append(fda_brand_name)
                self.changes.append({
                    "program": drug_name,
                    "field": "aliases",
                    "action": "added",
                    "new_value": fda_brand_name,
                    "source": "OpenFDA"
                })

            # Add FDA verification metadata to program
            program["fda_verification"] = {
                "is_approved": True,
                "approval_date": iso_date,
                "brand_name": fda_brand_name,
                "sponsor": fda_status.get("sponsor"),
                "application_number": fda_status.get("application_number"),
                "indication_summary": fda_status.get("indication", "")[:200] if fda_status.get("indication") else None,
                "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }

        else:
            # Program not approved - add verification that we checked
            program["fda_verification"] = {
                "is_approved": False,
                "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "raw_results_count": fda_status.get("raw_results_count", 0)
            }


def refresh_arwr():
    """Test refresh on ARWR."""
    refresher = PipelineRefresher()
    result = refresher.refresh_ticker("ARWR")

    print("=" * 60)
    print("Pipeline Data Refresh - ARWR")
    print("=" * 60)
    print(f"\nStatus: {result['status']}")
    print(f"Changes made: {result['changes_made']}")

    if result.get('changes'):
        print("\nChanges:")
        for change in result['changes']:
            print(f"  - {change['program']}: {change['field']}")
            if 'old_value' in change:
                print(f"    Old: {change['old_value']}")
            print(f"    New: {change['new_value']}")
            print(f"    Source: {change['source']}")


if __name__ == "__main__":
    refresh_arwr()
