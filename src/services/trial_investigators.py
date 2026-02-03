"""
Clinical Trial Investigators Service
Searches ClinicalTrials.gov for trial investigators.
Ported from cli/src/services/trial-investigators.ts
"""

import re
import requests
from dataclasses import dataclass, field
from typing import Optional

CTGOV_API_BASE = "https://clinicaltrials.gov/api/v2"


@dataclass
class TrialInfo:
    """Information about a clinical trial."""
    nct_id: str
    title: str
    phase: str
    status: str
    sponsor: str
    role: str = ""


@dataclass
class TrialInvestigator:
    """A clinical trial investigator."""
    name: str
    first_name: str
    last_name: str
    affiliation: str
    country: str
    role: str  # 'PI', 'Study Chair', 'Study Director'
    trial_count: int = 0
    trials: list[TrialInfo] = field(default_factory=list)


# Country code mapping
COUNTRY_MAP = {
    'united states': 'US', 'usa': 'US',
    'china': 'CN', 'united kingdom': 'UK',
    'germany': 'DE', 'france': 'FR',
    'japan': 'JP', 'south korea': 'KR', 'korea, republic of': 'KR',
    'canada': 'CA', 'australia': 'AU',
    'italy': 'IT', 'spain': 'ES',
    'netherlands': 'NL', 'switzerland': 'CH',
    'sweden': 'SE', 'brazil': 'BR',
    'india': 'IN', 'taiwan': 'TW',
    'israel': 'IL', 'belgium': 'BE',
    'austria': 'AT', 'poland': 'PL',
    'denmark': 'DK', 'norway': 'NO',
    'finland': 'FI', 'ireland': 'IE',
    'singapore': 'SG', 'hong kong': 'HK',
    'new zealand': 'NZ', 'south africa': 'ZA',
}


def extract_country(affiliation: str) -> str:
    """Extract country code from affiliation string."""
    if not affiliation:
        return ''

    aff_lower = affiliation.lower()

    # Check common patterns
    country_patterns = [
        (r'\bunited states\b|\busa\b|\bu\.s\.a\b|\bu\.s\.\b', 'US'),
        (r'\bchina\b|\bbeijing\b|\bshanghai\b', 'CN'),
        (r'\bunited kingdom\b|\bengland\b|\buk\b|\blondon\b', 'UK'),
        (r'\bgermany\b|\bdeutschland\b|\bberlin\b', 'DE'),
        (r'\bfrance\b|\bparis\b', 'FR'),
        (r'\bjapan\b|\btokyo\b', 'JP'),
        (r'\bsouth korea\b|\bkorea\b|\bseoul\b', 'KR'),
        (r'\bcanada\b|\btoronto\b|\bvancouver\b', 'CA'),
        (r'\baustralia\b|\bsydney\b|\bmelbourne\b', 'AU'),
        (r'\bitaly\b|\brome\b|\bmilan\b', 'IT'),
        (r'\bspain\b|\bmadrid\b|\bbarcelona\b', 'ES'),
        (r'\bnetherlands\b|\bamsterdam\b', 'NL'),
        (r'\bswitzerland\b|\bzurich\b|\bgeneva\b', 'CH'),
        (r'\bsweden\b|\bstockholm\b', 'SE'),
        (r'\bbrazil\b|\bsao paulo\b', 'BR'),
        (r'\bindia\b|\bmumbai\b|\bdelhi\b', 'IN'),
        (r'\btaiwan\b|\btaipei\b', 'TW'),
        (r'\bisrael\b|\btel aviv\b', 'IL'),
    ]

    for pattern, code in country_patterns:
        if re.search(pattern, aff_lower):
            return code

    # Check for US state abbreviations
    us_states = r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b'
    if re.search(us_states, affiliation):
        return 'US'

    # Check for major US institutions
    us_institutions = r'\b(harvard|stanford|mit|yale|columbia|johns hopkins|mayo clinic|nih|cdc|fda|ucla|ucsf|duke|northwestern|cornell|upenn|uchicago|emory|vanderbilt|washington university|memorial sloan|md anderson|dana-farber|cleveland clinic)\b'
    if re.search(us_institutions, aff_lower):
        return 'US'

    return ''


def parse_name_parts(full_name: str) -> tuple[str, str]:
    """Parse name into first and last name parts."""
    # Handle "Last, First" format
    if ',' in full_name:
        parts = [p.strip() for p in full_name.split(',')]
        last_name = parts[0]
        first_name = ' '.join(parts[1:]).strip() if len(parts) > 1 else ''
        # Remove MD, PhD suffixes
        first_name = re.sub(r',?\s*M\.?D\.?.*$', '', first_name, flags=re.IGNORECASE).strip()
        return first_name, last_name

    # Handle "First Last" format
    clean_name = re.sub(r',?\s*M\.?D\.?.*$', '', full_name, flags=re.IGNORECASE).strip()
    parts = clean_name.split()

    if len(parts) == 1:
        return '', parts[0]

    return ' '.join(parts[:-1]), parts[-1]


def normalize_investigator_name(last_name: str, first_name: str) -> str:
    """Normalize investigator name for deduplication."""
    normalized_last = re.sub(r'[^a-z]', '', last_name.lower())
    normalized_first = re.sub(r'[^a-z]', '', first_name.lower())
    return f"{normalized_last}_{normalized_first[0] if normalized_first else ''}"


def map_role(role: str) -> str:
    """Map ClinicalTrials.gov role to standard role."""
    role_lower = role.lower()
    if 'principal investigator' in role_lower or 'pi' in role_lower:
        return 'PI'
    if 'chair' in role_lower:
        return 'Study Chair'
    if 'director' in role_lower:
        return 'Study Director'
    return 'PI'


def map_country_name(country: str) -> str:
    """Map full country name to country code."""
    return COUNTRY_MAP.get(country.lower(), '')


def search_trial_investigators(
    query: str,
    max_trials: int = 100
) -> list[TrialInvestigator]:
    """
    Search ClinicalTrials.gov for investigators working on a specific topic.

    Args:
        query: Search query (e.g., "GLP-1 obesity")
        max_trials: Maximum number of trials to search

    Returns:
        List of TrialInvestigator objects sorted by trial count
    """
    try:
        search_url = f"{CTGOV_API_BASE}/studies"
        response = requests.get(search_url, params={
            'query.term': query,
            'pageSize': min(max_trials, 100),
            'fields': ','.join([
                'NCTId', 'BriefTitle', 'OfficialTitle', 'OverallStatus',
                'Phase', 'LeadSponsorName',
                'OverallOfficialName', 'OverallOfficialAffiliation', 'OverallOfficialRole',
                'LocationFacility', 'LocationCity', 'LocationState', 'LocationCountry',
                'LocationContactName', 'LocationContactRole', 'LocationContactEMail',
            ])
        }, timeout=20)

        response.raise_for_status()
        studies = response.json().get('studies', [])

        if not studies:
            return []

        # Aggregate investigators
        investigator_map: dict[str, TrialInvestigator] = {}

        for study in studies:
            protocol = study.get('protocolSection', {})
            if not protocol:
                continue

            identification = protocol.get('identificationModule', {})
            nct_id = identification.get('nctId', '')
            title = identification.get('briefTitle') or identification.get('officialTitle', '')

            status_module = protocol.get('statusModule', {})
            status = status_module.get('overallStatus', '')

            design_module = protocol.get('designModule', {})
            phases = design_module.get('phases', [])
            phase = '/'.join(phases) if phases else 'N/A'

            sponsor_module = protocol.get('sponsorCollaboratorsModule', {})
            lead_sponsor = sponsor_module.get('leadSponsor', {})
            sponsor = lead_sponsor.get('name', '')

            trial_info = TrialInfo(
                nct_id=nct_id,
                title=title,
                phase=phase,
                status=status,
                sponsor=sponsor
            )

            contacts_module = protocol.get('contactsLocationsModule', {})

            # Process overall officials
            officials = contacts_module.get('overallOfficials', [])
            for official in officials:
                name = official.get('name')
                if not name:
                    continue

                first_name, last_name = parse_name_parts(name)
                key = normalize_investigator_name(last_name, first_name)
                role = map_role(official.get('role', ''))
                affiliation = official.get('affiliation', '')
                country = extract_country(affiliation)

                if key in investigator_map:
                    existing = investigator_map[key]
                    existing.trial_count += 1
                    existing.trials.append(TrialInfo(
                        nct_id=trial_info.nct_id,
                        title=trial_info.title,
                        phase=trial_info.phase,
                        status=trial_info.status,
                        sponsor=trial_info.sponsor,
                        role=official.get('role', '')
                    ))
                    if affiliation and (not existing.affiliation or len(affiliation) > len(existing.affiliation)):
                        existing.affiliation = affiliation
                        existing.country = country
                else:
                    investigator_map[key] = TrialInvestigator(
                        name=name,
                        first_name=first_name,
                        last_name=last_name,
                        affiliation=affiliation,
                        country=country,
                        role=role,
                        trial_count=1,
                        trials=[TrialInfo(
                            nct_id=trial_info.nct_id,
                            title=trial_info.title,
                            phase=trial_info.phase,
                            status=trial_info.status,
                            sponsor=trial_info.sponsor,
                            role=official.get('role', '')
                        )]
                    )

            # Process location contacts (site PIs)
            locations = contacts_module.get('locations', [])
            for location in locations:
                contacts = location.get('contacts', [])
                for contact in contacts:
                    name = contact.get('name')
                    role = contact.get('role', '')
                    if not name or 'principal investigator' not in role.lower():
                        continue

                    first_name, last_name = parse_name_parts(name)
                    key = normalize_investigator_name(last_name, first_name)

                    # Build affiliation from location
                    affiliation_parts = [
                        location.get('facility'),
                        location.get('city'),
                        location.get('state'),
                        location.get('country')
                    ]
                    affiliation = ', '.join([p for p in affiliation_parts if p])
                    country = map_country_name(location.get('country', '')) or extract_country(affiliation)

                    if key in investigator_map:
                        existing = investigator_map[key]
                        # Check if this trial is already counted
                        if not any(t.nct_id == nct_id for t in existing.trials):
                            existing.trial_count += 1
                            existing.trials.append(TrialInfo(
                                nct_id=nct_id,
                                title=title,
                                phase=phase,
                                status=status,
                                sponsor=sponsor,
                                role='Site PI'
                            ))
                        if not existing.country and country:
                            existing.country = country
                        if not existing.affiliation and affiliation:
                            existing.affiliation = affiliation
                    else:
                        investigator_map[key] = TrialInvestigator(
                            name=name,
                            first_name=first_name,
                            last_name=last_name,
                            affiliation=affiliation,
                            country=country,
                            role='PI',
                            trial_count=1,
                            trials=[TrialInfo(
                                nct_id=nct_id,
                                title=title,
                                phase=phase,
                                status=status,
                                sponsor=sponsor,
                                role='Site PI'
                            )]
                        )

        # Sort by trial count and return top 50
        sorted_investigators = sorted(
            investigator_map.values(),
            key=lambda x: x.trial_count,
            reverse=True
        )[:50]

        return sorted_investigators

    except Exception as e:
        print(f"ClinicalTrials.gov search error: {e}")
        return []
