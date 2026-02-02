"""
ClinicalTrials.gov Status Checker

Queries ClinicalTrials.gov API v2 to get current trial status,
enrollment, and completion dates for pipeline drugs.
"""

import requests
from typing import Optional, List
from datetime import datetime, timezone
import json
import re


class TrialStatusChecker:
    """Check clinical trial status using ClinicalTrials.gov API v2."""

    BASE_URL = "https://clinicaltrials.gov/api/v2"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Helix-Biotech-Research/1.0"
        })

    def get_trial_by_nct(self, nct_id: str) -> dict:
        """
        Get trial details by NCT ID.

        Args:
            nct_id: ClinicalTrials.gov identifier (e.g., NCT04568434)

        Returns:
            dict with trial information
        """
        # Normalize NCT ID
        nct_id = nct_id.upper().strip()
        if not nct_id.startswith("NCT"):
            nct_id = f"NCT{nct_id}"

        url = f"{self.BASE_URL}/studies/{nct_id}"

        try:
            response = self.session.get(url, timeout=30)

            if response.status_code == 404:
                return {
                    "nct_id": nct_id,
                    "found": False,
                    "error": "Trial not found"
                }

            if response.status_code != 200:
                return {
                    "nct_id": nct_id,
                    "found": False,
                    "error": f"API error: {response.status_code}"
                }

            data = response.json()
            return self._parse_trial_data(nct_id, data)

        except Exception as e:
            return {
                "nct_id": nct_id,
                "found": False,
                "error": str(e)
            }

    def _parse_trial_data(self, nct_id: str, data: dict) -> dict:
        """Parse ClinicalTrials.gov API response."""
        protocol = data.get("protocolSection", {})

        # Identification
        id_module = protocol.get("identificationModule", {})

        # Status
        status_module = protocol.get("statusModule", {})

        # Design
        design_module = protocol.get("designModule", {})

        # Arms/Interventions
        arms_module = protocol.get("armsInterventionsModule", {})

        # Outcomes
        outcomes_module = protocol.get("outcomesModule", {})

        # Eligibility
        eligibility_module = protocol.get("eligibilityModule", {})

        # Sponsor
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})

        # Results (if posted)
        results_section = data.get("resultsSection", {})

        # Extract phase
        phases = design_module.get("phases", [])
        phase = phases[0] if phases else "Unknown"
        # Normalize phase format
        phase = phase.replace("PHASE", "Phase ").replace("_", "/").strip()

        # Extract dates
        start_date = status_module.get("startDateStruct", {}).get("date")
        primary_completion = status_module.get("primaryCompletionDateStruct", {}).get("date")
        completion_date = status_module.get("completionDateStruct", {}).get("date")

        # Extract enrollment
        enrollment_info = design_module.get("enrollmentInfo", {})
        enrollment_count = enrollment_info.get("count")
        enrollment_type = enrollment_info.get("type", "").lower()  # "actual" or "estimated"

        # Extract primary outcome
        primary_outcomes = outcomes_module.get("primaryOutcomes", [])
        primary_endpoint = None
        if primary_outcomes:
            primary_endpoint = primary_outcomes[0].get("measure")

        # Check if results are posted
        has_results = bool(results_section)

        # Get arms/interventions
        arms = []
        for arm in arms_module.get("armGroups", []):
            arms.append({
                "name": arm.get("label"),
                "type": arm.get("type"),
                "description": arm.get("description", "")[:200]
            })

        # Get sponsor
        lead_sponsor = sponsor_module.get("leadSponsor", {})
        sponsor_name = lead_sponsor.get("name")

        result = {
            "nct_id": nct_id,
            "found": True,
            "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),

            # Basic info
            "official_title": id_module.get("officialTitle"),
            "brief_title": id_module.get("briefTitle"),
            "acronym": id_module.get("acronym"),

            # Status
            "overall_status": status_module.get("overallStatus"),
            "phase": phase,
            "study_type": design_module.get("studyType"),

            # Dates
            "start_date": start_date,
            "primary_completion_date": primary_completion,
            "completion_date": completion_date,
            "last_update_posted": status_module.get("lastUpdatePostDateStruct", {}).get("date"),

            # Enrollment
            "enrollment": enrollment_count,
            "enrollment_type": enrollment_type,

            # Design
            "primary_endpoint": primary_endpoint,
            "arms": arms,

            # Sponsor
            "sponsor": sponsor_name,

            # Results
            "has_results": has_results,

            # URL
            "url": f"https://clinicaltrials.gov/study/{nct_id}"
        }

        return result

    def search_trials_by_drug(self, drug_name: str, sponsor: Optional[str] = None,
                               limit: int = 10) -> List[dict]:
        """
        Search for trials by drug name.

        Args:
            drug_name: Drug name to search
            sponsor: Optional sponsor name to filter
            limit: Max results

        Returns:
            List of trial summaries
        """
        url = f"{self.BASE_URL}/studies"

        # Build query
        query_parts = [f'AREA[InterventionName]{drug_name}']
        if sponsor:
            query_parts.append(f'AREA[LeadSponsorName]{sponsor}')

        params = {
            "query.term": " AND ".join(query_parts),
            "pageSize": limit,
            "fields": "NCTId,BriefTitle,OverallStatus,Phase,EnrollmentCount,StartDate,PrimaryCompletionDate,LeadSponsorName"
        }

        try:
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code != 200:
                return []

            data = response.json()
            studies = data.get("studies", [])

            results = []
            for study in studies:
                protocol = study.get("protocolSection", {})
                id_module = protocol.get("identificationModule", {})
                status_module = protocol.get("statusModule", {})
                design_module = protocol.get("designModule", {})
                sponsor_module = protocol.get("sponsorCollaboratorsModule", {})

                results.append({
                    "nct_id": id_module.get("nctId"),
                    "title": id_module.get("briefTitle"),
                    "status": status_module.get("overallStatus"),
                    "phase": design_module.get("phases", ["Unknown"])[0],
                    "enrollment": design_module.get("enrollmentInfo", {}).get("count"),
                    "sponsor": sponsor_module.get("leadSponsor", {}).get("name")
                })

            return results

        except Exception as e:
            print(f"Search error: {e}")
            return []

    def check_multiple_trials(self, nct_ids: List[str]) -> dict:
        """
        Check status of multiple trials.

        Args:
            nct_ids: List of NCT IDs

        Returns:
            dict mapping NCT ID to trial data
        """
        results = {}
        for nct_id in nct_ids:
            if nct_id:  # Skip None/empty
                results[nct_id] = self.get_trial_by_nct(nct_id)
        return results


def check_arwr_trials():
    """Test trial checker on ARWR pipeline."""
    checker = TrialStatusChecker()

    # Known ARWR trial NCT IDs
    nct_ids = [
        "NCT04568434",  # PALISADE (Plozasiran FCS)
        "NCT04720534",  # SHASTA-2 (Plozasiran sHTG)
        "NCT04832971",  # Zodasiran Phase 2
        "NCT05638191",  # ARO-INHBE Phase 1/2
        "NCT03946449",  # Fazirsiran Phase 2
        "NCT05677971",  # SEQUOIA (Fazirsiran Phase 2/3)
    ]

    print("=" * 70)
    print("ClinicalTrials.gov Status Check - Arrowhead Pharmaceuticals")
    print("=" * 70)

    for nct_id in nct_ids:
        print(f"\n{nct_id}:")
        trial = checker.get_trial_by_nct(nct_id)

        if trial.get("found"):
            print(f"  Title: {trial.get('brief_title', 'N/A')[:60]}...")
            print(f"  Status: {trial.get('overall_status')}")
            print(f"  Phase: {trial.get('phase')}")
            print(f"  Enrollment: {trial.get('enrollment')} ({trial.get('enrollment_type')})")
            print(f"  Primary Completion: {trial.get('primary_completion_date')}")
            print(f"  Has Results: {trial.get('has_results')}")
            print(f"  Sponsor: {trial.get('sponsor')}")
        else:
            print(f"  ERROR: {trial.get('error')}")


if __name__ == "__main__":
    check_arwr_trials()
