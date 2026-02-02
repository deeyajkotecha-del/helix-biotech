"""
FDA Approval Status Checker

Pulls current drug approval data from OpenFDA API to verify
approval status, dates, and indications.
"""

import requests
from typing import Optional
from datetime import datetime, timezone
import json


class FDAChecker:
    """Check FDA approval status using OpenFDA API."""

    BASE_URL = "https://api.fda.gov/drug"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Helix-Biotech-Research/1.0"
        })

    def search_drug_approvals(self, drug_name: str, limit: int = 10) -> dict:
        """
        Search for drug approvals by drug name.

        Args:
            drug_name: Generic or brand name of the drug
            limit: Max results to return

        Returns:
            dict with approval information
        """
        # Search drugsfda.json endpoint for approval info
        url = f"{self.BASE_URL}/drugsfda.json"

        # Try multiple search strategies
        results = {
            "drug_name": drug_name,
            "searched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "approvals": [],
            "labels": [],
            "source": "OpenFDA"
        }

        # Strategy 1: Search by brand name
        try:
            params = {
                "search": f'openfda.brand_name:"{drug_name}"',
                "limit": limit
            }
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                results["approvals"].extend(self._parse_drugsfda_results(data))
        except Exception as e:
            results["errors"] = results.get("errors", []) + [f"Brand name search: {str(e)}"]

        # Strategy 2: Search by generic name
        try:
            params = {
                "search": f'openfda.generic_name:"{drug_name}"',
                "limit": limit
            }
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                results["approvals"].extend(self._parse_drugsfda_results(data))
        except Exception as e:
            results["errors"] = results.get("errors", []) + [f"Generic name search: {str(e)}"]

        # Strategy 3: Search by substance name (for newer drugs)
        try:
            params = {
                "search": f'openfda.substance_name:"{drug_name}"',
                "limit": limit
            }
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                results["approvals"].extend(self._parse_drugsfda_results(data))
        except Exception as e:
            results["errors"] = results.get("errors", []) + [f"Substance search: {str(e)}"]

        # Deduplicate results
        seen = set()
        unique_approvals = []
        for approval in results["approvals"]:
            key = (approval.get("application_number"), approval.get("brand_name"))
            if key not in seen:
                seen.add(key)
                unique_approvals.append(approval)
        results["approvals"] = unique_approvals

        # Also search drug labels for indication info
        results["labels"] = self.search_drug_labels(drug_name)

        return results

    def _parse_drugsfda_results(self, data: dict) -> list:
        """Parse drugsfda.json API results."""
        approvals = []

        for result in data.get("results", []):
            approval = {
                "application_number": result.get("application_number"),
                "sponsor_name": result.get("sponsor_name"),
                "brand_name": None,
                "generic_name": None,
                "approval_date": None,
                "submissions": []
            }

            # Get OpenFDA fields
            openfda = result.get("openfda", {})
            if openfda.get("brand_name"):
                approval["brand_name"] = openfda["brand_name"][0]
            if openfda.get("generic_name"):
                approval["generic_name"] = openfda["generic_name"][0]
            if openfda.get("manufacturer_name"):
                approval["manufacturer"] = openfda["manufacturer_name"][0]

            # Get products info
            products = result.get("products", [])
            for product in products:
                if product.get("brand_name"):
                    approval["brand_name"] = product["brand_name"]
                if product.get("dosage_form"):
                    approval["dosage_form"] = product["dosage_form"]
                if product.get("route"):
                    approval["route"] = product["route"]
                if product.get("marketing_status"):
                    approval["marketing_status"] = product["marketing_status"]

            # Get submission history (approvals, supplements)
            submissions = result.get("submissions", [])
            for sub in submissions:
                sub_info = {
                    "submission_type": sub.get("submission_type"),
                    "submission_number": sub.get("submission_number"),
                    "submission_status": sub.get("submission_status"),
                    "submission_status_date": sub.get("submission_status_date"),
                    "review_priority": sub.get("review_priority")
                }

                # Check for approval
                if sub.get("submission_type") == "ORIG" and sub.get("submission_status") == "AP":
                    approval["approval_date"] = sub.get("submission_status_date")
                    approval["original_approval"] = True

                # Get application docs (labels, reviews)
                if sub.get("application_docs"):
                    for doc in sub["application_docs"]:
                        if doc.get("type") == "Label":
                            sub_info["label_url"] = doc.get("url")

                approval["submissions"].append(sub_info)

            approvals.append(approval)

        return approvals

    def search_drug_labels(self, drug_name: str, limit: int = 5) -> list:
        """
        Search drug labels for indication and safety information.

        Args:
            drug_name: Drug name to search
            limit: Max results

        Returns:
            list of label information
        """
        url = f"{self.BASE_URL}/label.json"
        labels = []

        try:
            # Search by brand or generic name
            params = {
                "search": f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
                "limit": limit
            }
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                for result in data.get("results", []):
                    label = {
                        "brand_name": None,
                        "generic_name": None,
                        "indications_and_usage": None,
                        "dosage_and_administration": None,
                        "warnings_and_precautions": None,
                        "effective_date": result.get("effective_time")
                    }

                    openfda = result.get("openfda", {})
                    if openfda.get("brand_name"):
                        label["brand_name"] = openfda["brand_name"][0]
                    if openfda.get("generic_name"):
                        label["generic_name"] = openfda["generic_name"][0]
                    if openfda.get("manufacturer_name"):
                        label["manufacturer"] = openfda["manufacturer_name"][0]

                    # Get key label sections
                    if result.get("indications_and_usage"):
                        label["indications_and_usage"] = result["indications_and_usage"][0][:1000]
                    if result.get("dosage_and_administration"):
                        label["dosage_and_administration"] = result["dosage_and_administration"][0][:500]
                    if result.get("boxed_warning"):
                        label["boxed_warning"] = result["boxed_warning"][0][:500]

                    labels.append(label)

        except Exception as e:
            pass  # Labels are supplementary

        return labels

    def check_approval_status(self, drug_name: str, company_name: Optional[str] = None) -> dict:
        """
        Get simplified approval status for a drug.

        Args:
            drug_name: Name of the drug
            company_name: Optional company name to filter results

        Returns:
            dict with:
              - is_approved: bool
              - approval_date: str or None
              - brand_name: str or None
              - indication: str or None
              - source: str
        """
        results = self.search_drug_approvals(drug_name)

        status = {
            "drug_name": drug_name,
            "is_approved": False,
            "approval_date": None,
            "brand_name": None,
            "generic_name": None,
            "indication": None,
            "sponsor": None,
            "source": "OpenFDA",
            "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "raw_results_count": len(results.get("approvals", []))
        }

        for approval in results.get("approvals", []):
            # Filter by company if specified
            if company_name:
                sponsor = approval.get("sponsor_name", "").lower()
                if company_name.lower() not in sponsor:
                    continue

            if approval.get("approval_date"):
                status["is_approved"] = True
                status["approval_date"] = approval["approval_date"]
                status["brand_name"] = approval.get("brand_name")
                status["generic_name"] = approval.get("generic_name")
                status["sponsor"] = approval.get("sponsor_name")
                status["application_number"] = approval.get("application_number")
                break

        # Get indication from labels
        for label in results.get("labels", []):
            if label.get("indications_and_usage"):
                status["indication"] = label["indications_and_usage"][:500]
                break

        return status


def check_arwr_drugs():
    """Test FDA checker on ARWR's pipeline."""
    checker = FDAChecker()

    drugs_to_check = [
        ("plozasiran", "Arrowhead"),
        ("REDEMPLO", "Arrowhead"),  # Brand name
        ("fazirsiran", "Arrowhead"),
        ("zodasiran", "Arrowhead"),
    ]

    print("=" * 60)
    print("FDA Approval Status Check - Arrowhead Pharmaceuticals")
    print("=" * 60)

    for drug_name, company in drugs_to_check:
        print(f"\nChecking: {drug_name}")
        status = checker.check_approval_status(drug_name, company)

        print(f"  Approved: {status['is_approved']}")
        if status['is_approved']:
            print(f"  Brand Name: {status['brand_name']}")
            print(f"  Approval Date: {status['approval_date']}")
            print(f"  Sponsor: {status['sponsor']}")
        if status['indication']:
            print(f"  Indication: {status['indication'][:200]}...")
        print(f"  Raw Results: {status['raw_results_count']}")


if __name__ == "__main__":
    check_arwr_drugs()
