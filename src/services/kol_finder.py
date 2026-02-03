"""
KOL Finder Service
Orchestrates PubMed and ClinicalTrials.gov data to find Key Opinion Leaders.
Ported from cli/src/services/kol-finder.ts
"""

import re
import time
import requests
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from functools import lru_cache

from .email_finder import find_emails_for_kols
from .trial_investigators import search_trial_investigators, extract_country


@dataclass
class PublicationInfo:
    """Publication information for a KOL."""
    pmid: str
    title: str
    journal: str
    year: str


@dataclass
class TrialInfo:
    """Trial information for a KOL."""
    nct_id: str
    title: str
    phase: str
    status: str


@dataclass
class KOL:
    """Key Opinion Leader profile."""
    name: str
    first_name: str
    last_name: str
    institution: str
    country: str
    email: Optional[str]
    publication_count: int
    trial_count: int
    role: str  # 'PI', 'Author', 'PI + Author'
    score: float
    publications: list[PublicationInfo] = field(default_factory=list)
    trials: list[TrialInfo] = field(default_factory=list)


@dataclass
class KOLSearchResult:
    """Result of a KOL search."""
    query: str
    total_kols: int
    kols: list[KOL]
    search_time_ms: int


# Pharma/biotech company names to filter out
PHARMA_COMPANIES = [
    'daiichi sankyo', 'pfizer', 'novartis', 'roche', 'genentech', 'merck', 'msd',
    'gsk', 'glaxosmithkline', 'astrazeneca', 'sanofi', 'bristol-myers squibb',
    'bristol myers squibb', 'bms', 'eli lilly', 'lilly', 'abbvie', 'amgen',
    'gilead', 'regeneron', 'vertex', 'biogen', 'moderna', 'biontech',
    'johnson & johnson', 'johnson and johnson', 'janssen', 'takeda', 'astellas',
    'bayer', 'boehringer ingelheim', 'novo nordisk', 'incyte', 'alnylam',
    'jazz pharmaceuticals', 'biomarin', 'alexion', 'neurocrine', 'seagen',
    'celgene', 'allergan', 'mylan', 'teva', 'viatris', 'eisai', 'otsuka',
    'ucb', 'ipsen', 'servier', 'lundbeck', 'blueprint medicines', 'agios',
    'ultragenyx', 'sarepta', 'bluebird bio', 'crispr therapeutics', 'intellia',
    'editas', 'beam therapeutics', 'prime medicine', 'verve therapeutics',
]

# Industry indicator patterns
INDUSTRY_PATTERNS = [
    r'\binc\b\.?',
    r'\bltd\b\.?',
    r'\bllc\b',
    r'\bcorporation\b',
    r'\bcorp\b\.?',
    r'\bpharmaceuticals?\b',
    r'\btherapeutics?\b',
    r'\bbiosciences?\b',
    r'\bbiotechnology\b',
    r'\bbiotech\b',
    r'\bpharma\b',
]


def is_industry_employee(institution: str) -> bool:
    """Check if institution indicates pharma/biotech industry employee."""
    if not institution:
        return False

    inst_lower = institution.lower()

    # Check for company names
    for company in PHARMA_COMPANIES:
        if company in inst_lower:
            return True

    # Check for industry patterns
    for pattern in INDUSTRY_PATTERNS:
        if re.search(pattern, institution, re.IGNORECASE):
            return True

    return False


def normalize_key(last_name: str, first_name: str) -> str:
    """Normalize name for deduplication."""
    normalized_last = re.sub(r'[^a-z]', '', last_name.lower())
    normalized_first = re.sub(r'[^a-z]', '', first_name.lower())
    return f"{normalized_last}_{normalized_first[0] if normalized_first else ''}"


def extract_institution_name(affiliation: str) -> str:
    """Extract shortened institution name from full affiliation."""
    if not affiliation:
        return ''

    # Clean up affiliation
    cleaned = affiliation
    cleaned = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', cleaned)
    cleaned = re.sub(r'Electronic address:\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b\d{5}(-\d{4})?\b', '', cleaned)
    cleaned = re.sub(r',?\s*(United States|USA|U\.S\.A\.?|U\.S\.?)\s*\.?\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r',?\s*[A-Z]{2}\s*\.?\s*$', '', cleaned)
    cleaned = re.sub(r'[,.\s]+$', '', cleaned).strip()

    # Known institution shortcuts
    known_institutions = [
        (r'dana[- ]?farber', 'Dana-Farber Cancer Institute'),
        (r'memorial sloan[- ]?kettering|mskcc', 'Memorial Sloan Kettering'),
        (r'md anderson', 'MD Anderson Cancer Center'),
        (r'mayo clinic', 'Mayo Clinic'),
        (r'cleveland clinic', 'Cleveland Clinic'),
        (r'johns hopkins', 'Johns Hopkins'),
        (r'massachusetts general|mass general|mgh', 'Massachusetts General Hospital'),
        (r'brigham and women|brigham & women', "Brigham and Women's Hospital"),
        (r'cedars[- ]?sinai', 'Cedars-Sinai Medical Center'),
        (r'mount sinai', 'Mount Sinai'),
        (r'nyu langone', 'NYU Langone'),
        (r'stanford', 'Stanford Medicine'),
        (r'ucsf|uc san francisco', 'UCSF'),
        (r'ucla', 'UCLA'),
        (r'duke university|duke medical', 'Duke University'),
        (r'university of pennsylvania|upenn|penn medicine', 'University of Pennsylvania'),
        (r'university of michigan', 'University of Michigan'),
        (r'university of chicago', 'University of Chicago'),
        (r'northwestern university|northwestern memorial', 'Northwestern University'),
        (r'vanderbilt', 'Vanderbilt University'),
        (r'emory', 'Emory University'),
        (r'cornell|weill cornell', 'Weill Cornell Medicine'),
        (r'columbia university', 'Columbia University'),
        (r'yale', 'Yale University'),
        (r'harvard', 'Harvard Medical School'),
        (r'nih|national institutes of health', 'NIH'),
        (r'fred hutch|hutchinson', 'Fred Hutchinson Cancer Center'),
    ]

    for pattern, name in known_institutions:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return name

    # Try to extract institution using patterns
    institution_patterns = [
        r'\b([\w\s\-\.]+(?:Cancer Center|Cancer Institute|Comprehensive Cancer Center))\b',
        r'\b([\w\s\-\.]+Medical Center)\b',
        r'\b([\w\s\-\.]+(?:Hospital|Hospitals))\b',
        r'\b((?:University of [\w\s]+|[\w\s]+ University|[\w\s]+ School of Medicine))\b',
        r'\b([\w\s\-\.]+Institute(?:\s+of\s+[\w\s]+)?)\b',
    ]

    for pattern in institution_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            inst = match.group(1).strip()
            inst = re.sub(r'^(the|from|at)\s+', '', inst, flags=re.IGNORECASE)
            inst = re.sub(r',.*$', '', inst)
            inst = re.sub(r'\s+', ' ', inst)
            if 5 < len(inst) < 80:
                return inst

    # Fallback
    if len(cleaned) > 50:
        return cleaned[:47] + '...'
    return cleaned or affiliation[:47] if affiliation else ''


def calculate_kol_score(kol: KOL) -> float:
    """Calculate a KOL score based on publications and trials."""
    pub_weight = 2
    trial_weight = 5
    both_bonus = 10

    score = 0.0
    score += kol.publication_count * pub_weight
    score += kol.trial_count * trial_weight

    if kol.role == 'PI + Author':
        score += both_bonus

    if kol.email:
        score += 3

    return score


def search_pubmed_authors(query: str, max_results: int = 100) -> list[dict]:
    """Search PubMed and extract top authors."""
    try:
        # Search for article IDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_resp = requests.get(search_url, params={
            'db': 'pubmed',
            'term': query,
            'retmax': max_results,
            'retmode': 'json',
            'sort': 'relevance'
        }, timeout=15)

        pmids = search_resp.json().get('esearchresult', {}).get('idlist', [])
        if not pmids:
            return []

        # Fetch article details
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_resp = requests.get(fetch_url, params={
            'db': 'pubmed',
            'id': ','.join(pmids),
            'retmode': 'xml'
        }, timeout=30)

        xml = fetch_resp.text

        # Parse articles
        author_map: dict[str, dict] = {}
        article_matches = re.findall(r'<PubmedArticle>[\s\S]*?</PubmedArticle>', xml)

        for article_xml in article_matches:
            pmid_match = re.search(r'<PMID[^>]*>(\d+)</PMID>', article_xml)
            pmid = pmid_match.group(1) if pmid_match else ''

            title_match = re.search(r'<ArticleTitle[^>]*>([\s\S]*?)</ArticleTitle>', article_xml)
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ''

            journal_match = re.search(r'<Title>([\s\S]*?)</Title>', article_xml) or \
                           re.search(r'<ISOAbbreviation>([\s\S]*?)</ISOAbbreviation>', article_xml)
            journal = journal_match.group(1).strip() if journal_match else ''

            year_match = re.search(r'<PubDate>[\s\S]*?<Year>(\d{4})</Year>', article_xml) or \
                        re.search(r'<ArticleDate[^>]*>[\s\S]*?<Year>(\d{4})</Year>', article_xml)
            year = year_match.group(1) if year_match else ''

            # Extract authors
            author_matches = re.findall(r'<Author[^>]*>[\s\S]*?</Author>', article_xml)
            for author_xml in author_matches:
                last_name_match = re.search(r'<LastName>([\s\S]*?)</LastName>', author_xml)
                first_name_match = re.search(r'<ForeName>([\s\S]*?)</ForeName>', author_xml)
                affiliation_match = re.search(r'<Affiliation>([\s\S]*?)</Affiliation>', author_xml)

                if not last_name_match:
                    continue

                last_name = last_name_match.group(1).strip()
                first_name = first_name_match.group(1).strip() if first_name_match else ''
                affiliation = affiliation_match.group(1).strip() if affiliation_match else ''

                # Extract email from affiliation
                email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', affiliation)
                email = email_match.group(1) if email_match else None

                # Clean affiliation
                affiliation = re.sub(r'\s*Electronic address:.*$', '', affiliation, flags=re.IGNORECASE).strip()

                key = normalize_key(last_name, first_name)
                name = f"{first_name} {last_name}".strip()
                country = extract_country(affiliation)

                if key in author_map:
                    existing = author_map[key]
                    existing['publication_count'] += 1
                    existing['publications'].append({
                        'pmid': pmid,
                        'title': title,
                        'journal': journal,
                        'year': year
                    })
                    if affiliation and (not existing['affiliation'] or len(affiliation) > len(existing['affiliation'])):
                        existing['affiliation'] = affiliation
                        existing['country'] = country
                    if email and not existing['email']:
                        existing['email'] = email
                else:
                    author_map[key] = {
                        'name': name,
                        'first_name': first_name,
                        'last_name': last_name,
                        'affiliation': affiliation,
                        'country': country,
                        'email': email,
                        'publication_count': 1,
                        'publications': [{
                            'pmid': pmid,
                            'title': title,
                            'journal': journal,
                            'year': year
                        }]
                    }

        # Sort by publication count
        sorted_authors = sorted(
            author_map.values(),
            key=lambda x: x['publication_count'],
            reverse=True
        )[:50]

        return sorted_authors

    except Exception as e:
        print(f"PubMed search error: {e}")
        return []


def find_kols(
    query: str,
    min_publications: int = 0,
    role_filter: str = 'all',  # 'all', 'pi', 'author'
    max_results: int = 50,
    include_email_search: bool = True
) -> KOLSearchResult:
    """
    Main KOL search function.
    Combines PubMed authors and ClinicalTrials.gov investigators.

    Args:
        query: Search query (e.g., "GLP-1 obesity")
        min_publications: Minimum publications required
        role_filter: Filter by role ('all', 'pi', 'author')
        max_results: Maximum KOLs to return
        include_email_search: Whether to search for emails for top KOLs

    Returns:
        KOLSearchResult with list of KOLs
    """
    start_time = time.time()

    # Run both searches
    print(f"Searching PubMed for: {query}")
    pubmed_authors = search_pubmed_authors(query, 100)
    print(f"Found {len(pubmed_authors)} PubMed authors")

    print(f"Searching ClinicalTrials.gov for: {query}")
    trial_investigators = search_trial_investigators(query, 100)
    print(f"Found {len(trial_investigators)} trial investigators")

    # Merge results
    kol_map: dict[str, KOL] = {}

    # Process PubMed authors
    for author in pubmed_authors:
        key = normalize_key(author['last_name'], author['first_name'])
        kol_map[key] = KOL(
            name=author['name'],
            first_name=author['first_name'],
            last_name=author['last_name'],
            institution=extract_institution_name(author['affiliation']),
            country=author['country'],
            email=author['email'],
            publication_count=author['publication_count'],
            trial_count=0,
            role='Author',
            score=0,
            publications=[PublicationInfo(**p) for p in author['publications'][:10]],
            trials=[]
        )

    # Merge trial investigators
    for investigator in trial_investigators:
        key = normalize_key(investigator.last_name, investigator.first_name)

        if key in kol_map:
            existing = kol_map[key]
            existing.trial_count = investigator.trial_count
            existing.role = 'PI + Author'
            existing.trials = [
                TrialInfo(nct_id=t.nct_id, title=t.title, phase=t.phase, status=t.status)
                for t in investigator.trials[:10]
            ]
            if not existing.institution and investigator.affiliation:
                existing.institution = extract_institution_name(investigator.affiliation)
            if not existing.country and investigator.country:
                existing.country = investigator.country
        else:
            kol_map[key] = KOL(
                name=investigator.name,
                first_name=investigator.first_name,
                last_name=investigator.last_name,
                institution=extract_institution_name(investigator.affiliation),
                country=investigator.country,
                email=None,
                publication_count=0,
                trial_count=investigator.trial_count,
                role='PI',
                score=0,
                publications=[],
                trials=[
                    TrialInfo(nct_id=t.nct_id, title=t.title, phase=t.phase, status=t.status)
                    for t in investigator.trials[:10]
                ]
            )

    # Calculate scores
    kols = list(kol_map.values())
    for kol in kols:
        kol.score = calculate_kol_score(kol)

    # Filter: US only
    kols = [k for k in kols if k.country == 'US']

    # Filter: exclude industry employees
    kols = [k for k in kols if not is_industry_employee(k.institution)]

    # Apply filters
    if min_publications > 0:
        kols = [k for k in kols if k.publication_count >= min_publications]

    if role_filter == 'pi':
        kols = [k for k in kols if k.trial_count > 0]
    elif role_filter == 'author':
        kols = [k for k in kols if k.publication_count > 0]

    # Sort by publication + trial count
    kols.sort(key=lambda k: k.publication_count + (k.trial_count * 2), reverse=True)

    # Limit results
    kols = kols[:max_results]

    # Search for emails for top KOLs who don't have one
    if include_email_search:
        kols_needing_email = [
            {'name': k.name, 'institution': k.institution}
            for k in kols if not k.email and k.institution
        ][:10]

        if kols_needing_email:
            print(f"Searching for emails for {len(kols_needing_email)} KOLs...")
            email_results = find_emails_for_kols(kols_needing_email, limit=10)

            for kol in kols:
                if not kol.email and kol.name in email_results:
                    kol.email = email_results[kol.name]

    # Re-sort: email first, then by publication count
    kols.sort(key=lambda k: (1 if k.email else 0, k.publication_count), reverse=True)

    search_time = int((time.time() - start_time) * 1000)

    return KOLSearchResult(
        query=query,
        total_kols=len(kols),
        kols=kols,
        search_time_ms=search_time
    )


# Cache for KOL results
_kol_cache: dict[str, tuple[KOLSearchResult, float]] = {}
CACHE_TTL = 30 * 60  # 30 minutes


def find_kols_cached(
    query: str,
    min_publications: int = 0,
    role_filter: str = 'all',
    max_results: int = 50
) -> KOLSearchResult:
    """Find KOLs with caching."""
    cache_key = f"{query}|{min_publications}|{role_filter}|{max_results}"

    if cache_key in _kol_cache:
        result, timestamp = _kol_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return result

    result = find_kols(query, min_publications, role_filter, max_results)
    _kol_cache[cache_key] = (result, time.time())

    return result
