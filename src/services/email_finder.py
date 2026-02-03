"""
Email Finder Service
Searches PubMed and the web to find institutional emails for researchers.
Ported from cli/src/services/email-finder.ts
"""

import re
import requests
from typing import Optional
from functools import lru_cache

# Personal email domains to filter out
PERSONAL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'me.com', 'mail.com', 'protonmail.com', 'ymail.com',
    'live.com', 'msn.com', 'comcast.net', 'verizon.net', 'att.net',
}

# Institutional domain patterns
INSTITUTIONAL_PATTERNS = [
    r'\.edu$',
    r'\.ac\.[a-z]{2}$',  # .ac.uk, .ac.jp, etc.
    r'\.org$',
    r'\.gov$',
    r'jhmi\.edu$',
    r'mskcc\.org$',
    r'mdanderson\.org$',
    r'mayoclinic\.org$',
    r'clevelandclinic\.org$',
    r'partners\.org$',
    r'dfci\.harvard\.edu$',
    r'stanford\.edu$',
    r'ucsf\.edu$',
    r'ucla\.edu$',
    r'upenn\.edu$',
    r'uchicago\.edu$',
    r'northwestern\.edu$',
    r'duke\.edu$',
    r'emory\.edu$',
    r'vanderbilt\.edu$',
    r'cshs\.org$',
    r'mssm\.edu$',
    r'nyulangone\.org$',
    r'columbia\.edu$',
    r'yale\.edu$',
    r'nih\.gov$',
    r'cancer\.gov$',
]

# In-memory cache
_email_cache: dict[str, Optional[str]] = {}


def is_institutional_email(email: str) -> bool:
    """Check if an email domain is institutional (not personal)."""
    parts = email.lower().split('@')
    if len(parts) != 2:
        return False
    domain = parts[1]

    # Reject known personal domains
    if domain in PERSONAL_DOMAINS:
        return False

    # Accept known institutional patterns
    for pattern in INSTITUTIONAL_PATTERNS:
        if re.search(pattern, domain, re.IGNORECASE):
            return True

    # Accept any .edu, .org, .gov domain
    if domain.endswith('.edu') or domain.endswith('.org') or domain.endswith('.gov'):
        return True

    return False


def extract_emails(text: str) -> list[str]:
    """Extract institutional emails from text."""
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(email_regex, text)

    seen = set()
    emails = []
    for email in matches:
        normalized = email.lower()
        if normalized not in seen and is_institutional_email(normalized):
            seen.add(normalized)
            emails.append(normalized)

    return emails


def rank_emails(emails: list[str], first_name: str, last_name: str) -> Optional[str]:
    """Rank emails by how well they match the person's name."""
    if not emails:
        return None

    if not first_name and not last_name:
        return None

    first_name = first_name.lower()
    last_name = last_name.lower()

    scored = []
    for email in emails:
        local_part = email.split('@')[0].lower()
        score = 0

        contains_last = len(last_name) >= 3 and last_name in local_part
        contains_first = len(first_name) >= 2 and first_name in local_part
        contains_first_initial = first_name and first_name[0] in local_part

        # Must contain at least the last name
        if not contains_last:
            if not (contains_first_initial and len(last_name) >= 4 and last_name[:4] in local_part):
                scored.append({'email': email, 'score': -100})
                continue

        # Score based on patterns
        if local_part == f"{first_name}.{last_name}":
            score += 50
        if local_part == f"{first_name}{last_name}":
            score += 45
        if local_part == f"{last_name}.{first_name}":
            score += 45
        if first_name and local_part == f"{first_name[0]}.{last_name}":
            score += 40
        if first_name and local_part == f"{first_name[0]}{last_name}":
            score += 35

        # Partial matches
        if contains_last and contains_first:
            score += 25
        if contains_last and contains_first_initial:
            score += 15
        if contains_last:
            score += 10

        # Penalize generic emails
        if any(x in local_part for x in ['info', 'contact', 'admin', 'support']):
            score -= 50

        scored.append({'email': email, 'score': score})

    # Filter and sort
    valid = [s for s in scored if s['score'] > 0]
    if not valid:
        return None

    valid.sort(key=lambda x: x['score'], reverse=True)
    return valid[0]['email']


def find_email(name: str, institution: str) -> Optional[str]:
    """
    Search for a researcher's email using PubMed.

    Args:
        name: Researcher name (e.g., "John Smith")
        institution: Institution name (e.g., "Johns Hopkins")

    Returns:
        Institutional email if found, None otherwise
    """
    # Check cache
    cache_key = f"{name}|{institution}".lower()
    if cache_key in _email_cache:
        return _email_cache[cache_key]

    # Clean up name
    clean_name = re.sub(r',?\s*(MD|PhD|M\.D\.|Ph\.D\.|DO|DrPH|MPH|MS|RN|FACS|FACP)\.?\s*', '', name, flags=re.IGNORECASE).strip()
    name_parts = [p for p in clean_name.lower().split() if len(p) > 1]
    last_name = name_parts[-1] if name_parts else ''
    first_name = name_parts[0] if name_parts else ''

    best_email = None

    # Method 1: Search PubMed for author's papers with email
    try:
        search_terms = f"{last_name} {first_name}[Author]"
        if institution:
            search_terms += f" AND {institution}[Affiliation]"

        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_resp = requests.get(search_url, params={
            'db': 'pubmed',
            'term': search_terms,
            'retmax': 20,
            'retmode': 'json'
        }, timeout=10)

        pmids = search_resp.json().get('esearchresult', {}).get('idlist', [])

        if pmids:
            fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            fetch_resp = requests.get(fetch_url, params={
                'db': 'pubmed',
                'id': ','.join(pmids),
                'retmode': 'xml'
            }, timeout=15)

            xml = fetch_resp.text

            # Look for emails near author's name in XML
            author_blocks = re.findall(r'<Author[^>]*>[\s\S]*?</Author>', xml)
            for block in author_blocks:
                last_match = re.search(r'<LastName>([\s\S]*?)</LastName>', block)
                if last_match and last_name in last_match.group(1).lower():
                    aff_match = re.search(r'<Affiliation>([\s\S]*?)</Affiliation>', block)
                    if aff_match:
                        emails = extract_emails(aff_match.group(1))
                        ranked = rank_emails(emails, first_name, last_name)
                        if ranked:
                            best_email = ranked
                            break

            # If no author-specific email found, try general extraction
            if not best_email:
                emails = extract_emails(xml)
                best_email = rank_emails(emails, first_name, last_name)

    except Exception:
        pass

    # Cache and return
    _email_cache[cache_key] = best_email
    return best_email


def find_emails_for_kols(
    kols: list[dict],
    max_concurrent: int = 3,
    limit: int = 10
) -> dict[str, Optional[str]]:
    """
    Find emails for multiple KOLs.

    Args:
        kols: List of dicts with 'name' and 'institution' keys
        max_concurrent: Max concurrent requests (not used in sync version)
        limit: Max KOLs to search

    Returns:
        Dict mapping name to email (or None)
    """
    results = {}

    for kol in kols[:limit]:
        name = kol.get('name', '')
        institution = kol.get('institution', '')
        results[name] = find_email(name, institution)

    return results


def clear_email_cache():
    """Clear the email cache."""
    global _email_cache
    _email_cache = {}
