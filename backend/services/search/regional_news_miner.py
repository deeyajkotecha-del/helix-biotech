"""
SatyaBio Regional News Miner Agent
====================================
Inspired by the Bioptic "Hunt Globally" paper (arxiv 2602.15019).

Surfaces early-stage drug assets from non-English regional sources across
China, Korea, Japan, India, and Europe. Uses a recall-oriented approach —
casts a wide net and accepts noisy candidates, which are then validated
by the Enrichment Agent downstream.

Architecture (mirrors the paper's 4-agent pipeline):
  1. Regional News Miner (THIS MODULE) — RSS feeds, news APIs, regulatory
     databases across 5+ regions. Recall-oriented: finds candidates.
  2. Attributes Enrichment Agent — validates candidates with deep-research
     web retrieval. Cross-lingual entity resolution.
  3. Discoverability Agent — checks if asset is already "on the radar"
     in English Google. Prioritizes hard-to-find assets.
  4. Benchmark/Validator — creates realistic investor queries + ground truth.

Data Sources:
  - English biotech feeds (FierceBiotech, BioPharma Dive, Endpoints, BioWorld)
  - BioSpectrum Asia (China/Korea/Japan/India sections)
  - NMPA English database (China drug approvals)
  - CDE (Center for Drug Evaluation) — China IND/NDA filings
  - KBPMA (Korea Pharma & Bio Manufacturers Association)
  - PMDA (Japan regulatory — English summaries)
  - ClinicalTrials.gov country-filtered searches
  - Claude API for translation + entity extraction from non-English content

Usage:
    python3 regional_news_miner.py --mine                    # Mine all regions
    python3 regional_news_miner.py --mine --region china     # China only
    python3 regional_news_miner.py --mine --region korea     # Korea only
    python3 regional_news_miner.py --extract --query "KRAS"  # Extract drug assets from news
    python3 regional_news_miner.py --alerts                  # Show novel assets found
    python3 regional_news_miner.py --status                  # Show mining stats

Requires in .env:
    ANTHROPIC_API_KEY=sk-ant-...
    NEON_DATABASE_URL=postgresql://...
"""

import os
import sys
import re
import json
import hashlib
import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    os.system(f"{sys.executable} -m pip install beautifulsoup4 --quiet")
    from bs4 import BeautifulSoup

try:
    import feedparser
except ImportError:
    os.system(f"{sys.executable} -m pip install feedparser --quiet")
    import feedparser

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import psycopg2
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ─── Config ──────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) SatyaBio-NewsMiner/1.0"
}

# ─── Regional News Sources ───────────────────────────────────────────────────
# Each source has: name, url, region, language, source_type, parse_fn
# parse_fn options: "rss", "html_listing", "api_json"

REGIONAL_SOURCES = {
    # ── Global English (high signal for non-US deals) ──
    "global": [
        {
            "name": "BioPharma Dive - China Deals Tracker",
            "url": "https://www.biopharmadive.com/news/china-biotech-drug-licensing-deals-pipeline/758283/",
            "parse_type": "html_listing",
            "language": "en",
            "focus": "China licensing deals",
        },
        {
            "name": "BioSpectrum Asia",
            "url": "https://www.biospectrumasia.com/feed",
            "parse_type": "rss",
            "language": "en",
            "focus": "Asia-Pacific biotech",
        },
        {
            "name": "Labiotech.eu",
            "url": "https://www.labiotech.eu/feed/",
            "parse_type": "rss",
            "language": "en",
            "focus": "European biotech",
        },
        {
            "name": "FierceBiotech Asia",
            "url": "https://www.fiercebiotech.com/rss/xml",
            "parse_type": "rss",
            "language": "en",
            "focus": "Global biotech with Asia coverage",
        },
    ],

    # ── China ──
    "china": [
        {
            "name": "NMPA English Database",
            "url": "https://english.nmpa.gov.cn/drugs.html",
            "parse_type": "html_listing",
            "language": "en",
            "focus": "NMPA drug approvals and filings",
        },
        {
            "name": "BioSpectrum China",
            "url": "https://www.biospectrumasia.com/category/country/china",
            "parse_type": "html_listing",
            "language": "en",
            "focus": "China biotech company news",
        },
        {
            "name": "ClinicalTrials.gov - China",
            "url": "https://clinicaltrials.gov/api/v2/studies",
            "parse_type": "ctgov_api",
            "language": "en",
            "focus": "Clinical trials with China sites",
            "params": {
                "filter.advanced": 'AREA[LocationCountry] "China"',
                "filter.overallStatus": "NOT_YET_RECRUITING,RECRUITING",
                "sort": "LastUpdatePostDate:desc",
                "pageSize": 50,
            },
        },
    ],

    # ── Korea ──
    "korea": [
        {
            "name": "BioSpectrum Korea",
            "url": "https://www.biospectrumasia.com/category/country/korea",
            "parse_type": "html_listing",
            "language": "en",
            "focus": "Korean biotech company news",
        },
        {
            "name": "KBPMA News",
            "url": "https://www.kpbma.or.kr/eng/resources/news/news/list",
            "parse_type": "html_listing",
            "language": "en",
            "focus": "Korea Pharma & Bio Manufacturers Association",
        },
        {
            "name": "ClinicalTrials.gov - Korea",
            "url": "https://clinicaltrials.gov/api/v2/studies",
            "parse_type": "ctgov_api",
            "language": "en",
            "focus": "Clinical trials with Korea sites",
            "params": {
                "filter.advanced": 'AREA[LocationCountry] "Korea, Republic of"',
                "filter.overallStatus": "NOT_YET_RECRUITING,RECRUITING",
                "sort": "LastUpdatePostDate:desc",
                "pageSize": 50,
            },
        },
    ],

    # ── Japan ──
    "japan": [
        {
            "name": "BioSpectrum Japan",
            "url": "https://www.biospectrumasia.com/category/country/japan",
            "parse_type": "html_listing",
            "language": "en",
            "focus": "Japanese biotech company news",
        },
        {
            "name": "Nikkei Asia - Pharma",
            "url": "https://asia.nikkei.com/business/pharmaceuticals",
            "parse_type": "html_listing",
            "language": "en",
            "focus": "Japanese pharma industry news",
        },
        {
            "name": "ClinicalTrials.gov - Japan",
            "url": "https://clinicaltrials.gov/api/v2/studies",
            "parse_type": "ctgov_api",
            "language": "en",
            "focus": "Clinical trials with Japan sites",
            "params": {
                "filter.advanced": 'AREA[LocationCountry] "Japan"',
                "filter.overallStatus": "NOT_YET_RECRUITING,RECRUITING",
                "sort": "LastUpdatePostDate:desc",
                "pageSize": 50,
            },
        },
    ],

    # ── India ──
    "india": [
        {
            "name": "BioSpectrum India",
            "url": "https://www.biospectrumasia.com/category/country/india",
            "parse_type": "html_listing",
            "language": "en",
            "focus": "Indian biotech company news",
        },
        {
            "name": "ClinicalTrials.gov - India",
            "url": "https://clinicaltrials.gov/api/v2/studies",
            "parse_type": "ctgov_api",
            "language": "en",
            "focus": "Clinical trials with India sites",
            "params": {
                "filter.advanced": 'AREA[LocationCountry] "India"',
                "filter.overallStatus": "NOT_YET_RECRUITING,RECRUITING",
                "sort": "LastUpdatePostDate:desc",
                "pageSize": 50,
            },
        },
    ],

    # ── Europe ──
    "europe": [
        {
            "name": "Labiotech.eu",
            "url": "https://www.labiotech.eu/feed/",
            "parse_type": "rss",
            "language": "en",
            "focus": "European biotech news",
        },
        {
            "name": "ClinicalTrials.gov - Europe",
            "url": "https://clinicaltrials.gov/api/v2/studies",
            "parse_type": "ctgov_api",
            "language": "en",
            "focus": "Clinical trials with European sites",
            "params": {
                "filter.advanced": (
                    'AREA[LocationCountry] "Germany" OR '
                    'AREA[LocationCountry] "France" OR '
                    'AREA[LocationCountry] "United Kingdom" OR '
                    'AREA[LocationCountry] "Netherlands" OR '
                    'AREA[LocationCountry] "Switzerland" OR '
                    'AREA[LocationCountry] "Denmark"'
                ),
                "filter.overallStatus": "NOT_YET_RECRUITING,RECRUITING",
                "sort": "LastUpdatePostDate:desc",
                "pageSize": 50,
            },
        },
    ],
}


# ─── Known Chinese biotech companies & drug codes ────────────────────────────
# These are companies the paper highlights as "under the radar" but developing
# globally competitive assets.

CHINA_BIOTECH_WATCHLIST = {
    "BeiGene": {
        "aliases": ["百济神州", "BeiGene Ltd", "BGNE", "6160.HK"],
        "known_drugs": ["zanubrutinib", "tislelizumab", "BG-68501", "sonrotoclax"],
    },
    "Hengrui Medicine": {
        "aliases": ["恒瑞医药", "Jiangsu Hengrui", "600276.SS"],
        "known_drugs": ["camrelizumab", "fuzuloparib", "SHR-A1811", "SHR-1916"],
    },
    "Innovent Biologics": {
        "aliases": ["信达生物", "Innovent", "1801.HK"],
        "known_drugs": ["sintilimab", "IBI351", "fulzerasib", "IBI343"],
    },
    "Hansoh Pharma": {
        "aliases": ["翰森制药", "Hansoh", "3692.HK"],
        "known_drugs": ["HS-10365", "HS-20093", "almonertinib"],
    },
    "HUTCHMED": {
        "aliases": ["和黄医药", "Chi-Med", "HCM"],
        "known_drugs": ["surufatinib", "fruquintinib", "savolitinib", "HMPL-306"],
    },
    "Zymeworks/Zai Lab": {
        "aliases": ["再鼎医药", "Zai Lab", "ZLAB", "9688.HK"],
        "known_drugs": ["zanidatamab", "margetuximab", "ZL-1211"],
    },
    "Terns Pharmaceuticals": {
        "aliases": ["拓臻生物"],
        "known_drugs": ["TERN-701", "TERN-601"],
    },
    "Akeso": {
        "aliases": ["康方生物", "AK104", "9926.HK"],
        "known_drugs": ["cadonilimab", "AK112", "ivonescimab"],
    },
    "Summit Therapeutics": {
        "aliases": ["SMMT"],
        "known_drugs": ["ivonescimab"],
        "note": "US-listed but drug is China-originated from Akeso",
    },
    "Jacobio Pharma": {
        "aliases": ["加科思", "1167.HK"],
        "known_drugs": ["glecirasib", "JAB-21822", "JAB-23000", "JAB-BX102"],
    },
    "D3 Bio": {
        "aliases": ["迪哲医药"],
        "known_drugs": ["garsorasib", "D-1553", "D-0502"],
    },
    "Adagene": {
        "aliases": ["ADAG"],
        "known_drugs": ["ADG126", "ADG106", "masatinib"],
    },
    "Kelun-Biotech": {
        "aliases": ["科伦博泰", "6990.HK"],
        "known_drugs": ["SKB264", "A166", "A167"],
    },
    "Duality Biologics": {
        "aliases": ["荃信生物"],
        "known_drugs": ["DB-1303", "DB-1311"],
    },
    "LaNova Medicines": {
        "aliases": ["岸迈生物"],
        "known_drugs": ["LM-302", "LM-299"],
    },
}

KOREA_BIOTECH_WATCHLIST = {
    "Yuhan Corp": {
        "aliases": ["유한양행", "000100.KS"],
        "known_drugs": ["lazertinib", "YH35324"],
    },
    "HLB": {
        "aliases": ["028300.KS"],
        "known_drugs": ["rivoceranib", "camonsertib"],
    },
    "ABL Bio": {
        "aliases": ["에이비엘바이오", "298380.KQ"],
        "known_drugs": ["ABL001", "ABL503"],
    },
    "Boryung Pharm": {
        "aliases": ["보령제약", "003850.KS"],
        "known_drugs": ["BR-1015"],
    },
    "Daewoong Pharma": {
        "aliases": ["대웅제약", "069620.KS"],
        "known_drugs": ["DWP213", "enavogliflozin"],
    },
    "SK Biopharmaceuticals": {
        "aliases": ["에스케이바이오", "326030.KS"],
        "known_drugs": ["cenobamate", "SKL-PSY"],
    },
}

JAPAN_BIOTECH_WATCHLIST = {
    "Daiichi Sankyo": {
        "aliases": ["第一三共", "4568.T", "DSNKY"],
        "known_drugs": ["datopotamab deruxtecan", "ifinatamab deruxtecan", "DS-7300"],
    },
    "Ono Pharmaceutical": {
        "aliases": ["小野薬品", "4528.T"],
        "known_drugs": ["ONO-4578", "ONO-7475"],
    },
    "PeptiDream": {
        "aliases": ["ペプチドリーム", "4587.T"],
        "known_drugs": ["PD-001", "PD-0301"],
    },
    "Astellas": {
        "aliases": ["アステラス", "4503.T"],
        "known_drugs": ["zolbetuximab", "enfortumab vedotin"],
    },
    "Eisai": {
        "aliases": ["エーザイ", "4523.T", "ESALY"],
        "known_drugs": ["lecanemab", "E7386", "MORAb-202"],
    },
}

ALL_WATCHLISTS = {
    "china": CHINA_BIOTECH_WATCHLIST,
    "korea": KOREA_BIOTECH_WATCHLIST,
    "japan": JAPAN_BIOTECH_WATCHLIST,
}


# ─── Source Parsers ──────────────────────────────────────────────────────────

def parse_rss_feed(source):
    """Parse an RSS feed. Returns list of article dicts."""
    articles = []
    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries[:30]:  # Cap at 30 per feed
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

            summary = ""
            if hasattr(entry, "summary"):
                summary = BeautifulSoup(entry.summary, "html.parser").get_text(strip=True)
            elif hasattr(entry, "description"):
                summary = BeautifulSoup(entry.description, "html.parser").get_text(strip=True)

            articles.append({
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", ""),
                "published": pub_date,
                "summary": summary[:2000],
                "source_name": source["name"],
                "region": source.get("region", "global"),
                "language": source.get("language", "en"),
                "full_text": "",
            })
        print(f"    [{source['name']}] {len(articles)} articles from RSS")
    except Exception as e:
        print(f"    [{source['name']}] RSS error: {e}")
    return articles


def parse_html_listing(source):
    """Parse an HTML page listing articles/news items. Returns list of article dicts."""
    articles = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"    [{source['name']}] HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Find article links — look for common patterns
        # BioSpectrum, NMPA, and most news sites use <a> inside article/listing containers
        link_elements = []

        # Try structured selectors first
        for selector in [
            "article a", ".article-list a", ".news-list a",
            ".views-row a", ".listing-item a", ".post-item a",
            "h2 a", "h3 a", ".title a", ".headline a",
            ".list-item a", "li.item a", ".card a",
        ]:
            found = soup.select(selector)
            if found:
                link_elements = found
                break

        # Fallback: any link with a pharma/drug keyword in the text
        if not link_elements:
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True).lower()
                if any(kw in text for kw in [
                    "drug", "pharma", "biotech", "clinical", "trial",
                    "approval", "fda", "nmpa", "therapeutic", "oncology",
                    "cancer", "pipeline", "molecule", "antibody", "inhibitor",
                ]):
                    link_elements.append(a)

        seen_urls = set()
        for a in link_elements[:25]:
            href = a.get("href", "")
            title = a.get_text(strip=True)

            if not title or len(title) < 10:
                continue

            # Resolve relative URLs
            if href.startswith("/"):
                from urllib.parse import urljoin
                href = urljoin(source["url"], href)

            if href in seen_urls or not href.startswith("http"):
                continue
            seen_urls.add(href)

            articles.append({
                "title": title,
                "url": href,
                "published": None,
                "summary": "",
                "source_name": source["name"],
                "region": source.get("region", "global"),
                "language": source.get("language", "en"),
                "full_text": "",
            })

        print(f"    [{source['name']}] {len(articles)} articles from HTML")
    except Exception as e:
        print(f"    [{source['name']}] HTML parse error: {e}")
    return articles


def parse_ctgov_api(source):
    """Fetch recently updated trials from ClinicalTrials.gov API. Returns article-like dicts."""
    articles = []
    try:
        params = {
            "format": "json",
            "countTotal": "true",
            **source.get("params", {}),
        }

        resp = requests.get(source["url"], params=params, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            print(f"    [{source['name']}] HTTP {resp.status_code}")
            return []

        data = resp.json()
        studies = data.get("studies", [])

        for study in studies:
            proto = study.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status = proto.get("statusModule", {})
            design = proto.get("designModule", {})
            sponsor = proto.get("sponsorCollaboratorsModule", {})

            nct_id = ident.get("nctId", "")
            title = ident.get("briefTitle", "") or ident.get("officialTitle", "")
            org_name = sponsor.get("leadSponsor", {}).get("name", "")
            phase_list = (design.get("phases") or ["N/A"])
            phase = phase_list[0] if phase_list else "N/A"

            # Get interventions
            arms = proto.get("armsInterventionsModule", {})
            interventions = arms.get("interventions", [])
            intervention_names = [i.get("name", "") for i in interventions]

            # Get conditions
            cond_mod = proto.get("conditionsModule", {})
            conditions = cond_mod.get("conditions", [])

            # Get locations/countries
            contacts = proto.get("contactsLocationsModule", {})
            locations = contacts.get("locations", [])
            countries = list(set(loc.get("country", "") for loc in locations))

            last_update = status.get("lastUpdatePostDateStruct", {}).get("date", "")

            summary = (
                f"{title}\n"
                f"Sponsor: {org_name} | Phase: {phase}\n"
                f"Interventions: {', '.join(intervention_names)}\n"
                f"Conditions: {', '.join(conditions)}\n"
                f"Countries: {', '.join(countries)}"
            )

            articles.append({
                "title": f"[{nct_id}] {title}",
                "url": f"https://clinicaltrials.gov/study/{nct_id}",
                "published": None,
                "summary": summary,
                "source_name": source["name"],
                "region": source.get("region", "global"),
                "language": "en",
                "full_text": summary,
                "metadata": {
                    "nct_id": nct_id,
                    "sponsor": org_name,
                    "phase": phase,
                    "interventions": intervention_names,
                    "conditions": conditions,
                    "countries": countries,
                    "last_update": last_update,
                },
            })

        print(f"    [{source['name']}] {len(articles)} recent trials")
    except Exception as e:
        print(f"    [{source['name']}] CT.gov API error: {e}")
    return articles


# ─── Claude-Powered Entity Extraction ────────────────────────────────────────

def extract_drug_entities_with_claude(articles, region="all"):
    """
    Use Claude to extract drug asset candidates from a batch of articles.
    This is the core "recall-oriented" extraction — cast a wide net.

    Returns list of DrugCandidate dicts.
    """
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        print("  [Claude extraction] No API key — using regex fallback")
        return extract_drug_entities_regex(articles)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Build context from articles
    article_texts = []
    for i, a in enumerate(articles[:40]):  # Cap at 40 to stay within context
        text = f"[{i+1}] {a['source_name']} | {a.get('region', '?')}\n"
        text += f"Title: {a['title']}\n"
        if a.get("summary"):
            text += f"Summary: {a['summary'][:500]}\n"
        if a.get("full_text"):
            text += f"Content: {a['full_text'][:800]}\n"
        article_texts.append(text)

    batch_text = "\n---\n".join(article_texts)

    # Build region-specific watchlist context
    watchlist_ctx = ""
    if region in ALL_WATCHLISTS:
        companies = ALL_WATCHLISTS[region]
        lines = [f"\nKnown {region.upper()} biotech companies to watch for:"]
        for company, info in companies.items():
            drugs = ", ".join(info["known_drugs"])
            lines.append(f"  - {company} ({', '.join(info['aliases'][:2])}): {drugs}")
        watchlist_ctx = "\n".join(lines)

    prompt = f"""You are a biotech drug asset scout for a biopharma investment firm.
Analyze these {len(article_texts)} articles/trials from {region} regional sources and extract ALL drug asset candidates.

Be RECALL-ORIENTED: it's better to include a noisy candidate than miss a real one.
Extract ANY mentioned drug, molecule, compound code, or therapeutic candidate.

{watchlist_ctx}

ARTICLES:
{batch_text}

For each drug asset found, extract:
1. drug_name: The drug name or compound code (e.g., "BG-68501", "garsorasib", "ivonescimab")
2. company: Sponsoring company
3. target_moa: Molecular target or mechanism (e.g., "KRAS G12C", "PD-L1/VEGF bispecific")
4. phase: Development phase (Preclinical, Phase 1, Phase 2, Phase 3, Approved)
5. indication: Primary disease target
6. countries: Countries where being developed
7. source_article: Which article number [N] this was found in
8. confidence: high/medium/low — how confident you are this is a real drug asset
9. novelty_signal: Is this likely under-the-radar? (yes/no/maybe)

Return as JSON array. Include ALL candidates, even if confidence is "low".
Only return the JSON array, no other text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        # Parse JSON — handle markdown code blocks
        if text.startswith("```"):
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)

        candidates = json.loads(text)
        print(f"  [Claude] Extracted {len(candidates)} drug candidates")
        return candidates

    except json.JSONDecodeError as e:
        print(f"  [Claude] JSON parse error: {e}")
        return extract_drug_entities_regex(articles)
    except Exception as e:
        print(f"  [Claude] API error: {e}")
        return extract_drug_entities_regex(articles)


def extract_drug_entities_regex(articles):
    """
    Regex fallback for drug entity extraction when Claude API isn't available.
    Looks for common drug naming patterns: code names, -mab/-nib/-lib suffixes, etc.
    """
    # Common drug name patterns
    patterns = [
        # Code names: ABC-12345, ABC12345
        r'\b([A-Z]{2,5}[-\s]?\d{3,6}[A-Za-z]?)\b',
        # INN suffixes
        r'\b(\w{4,}(?:mab|nib|lib|sib|tib|cib|rib|pib|ertinib|afenib|lisib|tinib))\b',
        # -umab, -zumab, -ximab
        r'\b(\w{4,}(?:umab|zumab|ximab|limab|tumab|vimab|nimab|rimab))\b',
        # ADC names (X vedotin, X deruxtecan, etc.)
        r'\b(\w+ (?:vedotin|deruxtecan|govitecan|maytansine|mafodotin|ravtansine))\b',
    ]

    candidates = []
    seen = set()

    for article in articles:
        search_text = f"{article['title']} {article.get('summary', '')} {article.get('full_text', '')}"

        for pattern in patterns:
            matches = re.findall(pattern, search_text, re.IGNORECASE)
            for match in matches:
                name = match.strip()
                if name.lower() in seen or len(name) < 3:
                    continue
                # Filter out common false positives
                if name.upper() in {"COVID", "SARS", "MERS", "HTTP", "HTML", "NULL"}:
                    continue
                seen.add(name.lower())
                candidates.append({
                    "drug_name": name,
                    "company": "",
                    "target_moa": "",
                    "phase": "",
                    "indication": "",
                    "countries": [],
                    "source_article": article["title"][:60],
                    "confidence": "low",
                    "novelty_signal": "maybe",
                })

    print(f"  [Regex] Extracted {len(candidates)} drug candidates")
    return candidates


# ─── Cross-Lingual Entity Resolution ────────────────────────────────────────

def resolve_cross_lingual(candidates):
    """
    Resolve Chinese/Korean/Japanese drug names to English canonical names.
    Uses the watchlist aliases + Claude for unknown entities.
    """
    # Build a reverse lookup from all watchlists
    alias_to_canonical = {}
    for region_watchlist in ALL_WATCHLISTS.values():
        for company, info in region_watchlist.items():
            for alias in info.get("aliases", []):
                alias_to_canonical[alias.lower()] = company
            for drug in info.get("known_drugs", []):
                alias_to_canonical[drug.lower()] = drug

    resolved = []
    for c in candidates:
        drug_lower = c["drug_name"].lower()
        company_lower = c.get("company", "").lower()

        # Check if drug or company matches a known alias
        if drug_lower in alias_to_canonical:
            c["canonical_name"] = alias_to_canonical[drug_lower]
            c["resolution"] = "alias_match"
        elif company_lower in alias_to_canonical:
            c["parent_company"] = alias_to_canonical[company_lower]
            c["resolution"] = "company_match"
        else:
            c["resolution"] = "unresolved"

        resolved.append(c)

    matched = sum(1 for c in resolved if c["resolution"] != "unresolved")
    print(f"  [Resolution] {matched}/{len(resolved)} candidates matched to known entities")
    return resolved


# ─── Novel Asset Detection ───────────────────────────────────────────────────

def detect_novel_assets(candidates, known_drugs=None):
    """
    Flag drug candidates that are NOT in our known drug database.
    These are the "under the radar" assets the paper talks about.
    """
    if known_drugs is None:
        # Primary: use the curated known drugs baseline (~250 drugs, ~500+ aliases)
        try:
            from known_drugs_baseline import get_known_drug_set
            known_drugs = get_known_drug_set()
            print(f"  [Novelty] Loaded {len(known_drugs)} known drug aliases from baseline")
        except ImportError:
            # Fallback: try old drug_entities.py
            try:
                from drug_entities import DRUG_DATABASE
                known_drugs = set()
                for drug_info in DRUG_DATABASE.values():
                    known_drugs.add(drug_info.get("generic_name", "").lower())
                    for alias in drug_info.get("aliases", []):
                        known_drugs.add(alias.lower())
                print(f"  [Novelty] Loaded {len(known_drugs)} aliases from drug_entities (fallback)")
            except ImportError:
                known_drugs = set()
                print("  [Novelty] WARNING: No known drugs baseline found — all candidates will be flagged as novel")

    # Also try the smarter matching from known_drugs_baseline
    try:
        from known_drugs_baseline import is_known_drug as _is_known
        use_smart_match = True
    except ImportError:
        use_smart_match = False

    novel = []
    known_list = []
    for c in candidates:
        drug_lower = c["drug_name"].lower().strip()
        is_known = False

        if use_smart_match:
            is_known = _is_known(c["drug_name"])
        else:
            # Fallback: exact + substring match (skip very short aliases to avoid false positives)
            if drug_lower in known_drugs:
                is_known = True
            else:
                for kd in known_drugs:
                    if len(kd) >= 4 and (drug_lower in kd or kd in drug_lower):
                        is_known = True
                        break

        if is_known:
            c["novelty"] = "known"
            known_list.append(c)
        else:
            c["novelty"] = "novel"
            novel.append(c)

    print(f"  [Novelty] {len(novel)} novel / {len(known_list)} known drug candidates")
    return novel, known_list


# ─── Database Storage ────────────────────────────────────────────────────────

def ensure_miner_tables(conn):
    """Create tables for the Regional News Miner."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mined_articles (
            id SERIAL PRIMARY KEY,
            article_hash VARCHAR(64) UNIQUE NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            source_name VARCHAR(200),
            region VARCHAR(50),
            language VARCHAR(10),
            published_at TIMESTAMP WITH TIME ZONE,
            summary TEXT,
            full_text TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS drug_candidates (
            id SERIAL PRIMARY KEY,
            drug_name VARCHAR(200) NOT NULL,
            canonical_name VARCHAR(200),
            company VARCHAR(200),
            target_moa VARCHAR(300),
            phase VARCHAR(50),
            indication TEXT,
            countries TEXT[],
            region VARCHAR(50),
            source_article_id INTEGER REFERENCES mined_articles(id),
            confidence VARCHAR(20),
            novelty VARCHAR(20),
            novelty_signal VARCHAR(20),
            resolution VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()


def store_article(conn, article):
    """Store a mined article. Returns article ID or None if duplicate."""
    hash_input = f"{article['title']}:{article.get('url', '')}"
    article_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:32]

    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO mined_articles (article_hash, title, url, source_name, region,
                                        language, published_at, summary, full_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (article_hash) DO NOTHING
            RETURNING id
        """, (
            article_hash,
            article["title"],
            article.get("url", ""),
            article["source_name"],
            article.get("region", "global"),
            article.get("language", "en"),
            article.get("published"),
            article.get("summary", ""),
            article.get("full_text", ""),
        ))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        return result[0] if result else None
    except Exception as e:
        conn.rollback()
        cur.close()
        return None


def store_candidate(conn, candidate, article_id=None):
    """Store a drug candidate."""
    cur = conn.cursor()
    try:
        countries = candidate.get("countries", [])
        if isinstance(countries, str):
            countries = [c.strip() for c in countries.split(",")]

        cur.execute("""
            INSERT INTO drug_candidates (drug_name, canonical_name, company, target_moa,
                                         phase, indication, countries, region,
                                         source_article_id, confidence, novelty,
                                         novelty_signal, resolution)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            candidate["drug_name"],
            candidate.get("canonical_name", ""),
            candidate.get("company", ""),
            candidate.get("target_moa", ""),
            candidate.get("phase", ""),
            candidate.get("indication", ""),
            countries if countries else [],
            candidate.get("region", ""),
            article_id,
            candidate.get("confidence", "low"),
            candidate.get("novelty", "unknown"),
            candidate.get("novelty_signal", "maybe"),
            candidate.get("resolution", "unresolved"),
        ))
        conn.commit()
        cur.close()
    except Exception as e:
        conn.rollback()
        cur.close()


# ─── Main Pipeline ───────────────────────────────────────────────────────────

def mine_region(region, use_llm=True):
    """
    Mine a single region for drug asset candidates.

    Returns:
        dict with articles, candidates, novel_assets
    """
    print(f"\n{'='*70}")
    print(f"  REGIONAL NEWS MINER — {region.upper()}")
    print(f"{'='*70}\n")

    # Determine which sources to fetch
    sources = REGIONAL_SOURCES.get(region, [])
    if region == "all":
        sources = []
        for r, s_list in REGIONAL_SOURCES.items():
            for s in s_list:
                s_copy = dict(s)
                s_copy["region"] = r
                sources.append(s_copy)

    if not sources:
        print(f"  No sources configured for region: {region}")
        return {"articles": [], "candidates": [], "novel": []}

    # Step 1: Fetch articles from all sources
    print(f"  Step 1: Fetching from {len(sources)} sources...")
    all_articles = []
    for source in sources:
        source["region"] = source.get("region", region)
        parse_type = source.get("parse_type", "rss")

        if parse_type == "rss":
            articles = parse_rss_feed(source)
        elif parse_type == "html_listing":
            articles = parse_html_listing(source)
        elif parse_type == "ctgov_api":
            articles = parse_ctgov_api(source)
        else:
            articles = []

        all_articles.extend(articles)
        time.sleep(1)  # Rate limit

    print(f"\n  Total articles fetched: {len(all_articles)}")

    # Step 2: Extract drug entities
    print(f"\n  Step 2: Extracting drug entities...")
    if use_llm:
        candidates = extract_drug_entities_with_claude(all_articles, region=region)
    else:
        candidates = extract_drug_entities_regex(all_articles)

    # Step 3: Cross-lingual resolution
    print(f"\n  Step 3: Cross-lingual entity resolution...")
    candidates = resolve_cross_lingual(candidates)

    # Step 4: Detect novel assets
    print(f"\n  Step 4: Detecting novel assets...")
    novel, known = detect_novel_assets(candidates)

    # Step 5: Store results
    conn = None
    if DB_AVAILABLE and DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            ensure_miner_tables(conn)
            stored_articles = 0
            for a in all_articles:
                aid = store_article(conn, a)
                if aid:
                    stored_articles += 1
            stored_candidates = 0
            for c in candidates:
                store_candidate(conn, c)
                stored_candidates += 1
            print(f"\n  Stored: {stored_articles} articles, {stored_candidates} candidates")
            conn.close()
        except Exception as e:
            print(f"\n  DB storage error: {e}")
            if conn:
                conn.close()

    # Print summary
    print(f"\n{'='*70}")
    print(f"  MINING RESULTS — {region.upper()}")
    print(f"{'='*70}")
    print(f"  Articles scraped:    {len(all_articles)}")
    print(f"  Drug candidates:     {len(candidates)}")
    print(f"  Novel (under radar): {len(novel)}")
    print(f"  Known (in our DB):   {len(known)}")

    if novel:
        print(f"\n  {'─'*60}")
        print(f"  NOVEL DRUG ASSETS DETECTED:")
        print(f"  {'─'*60}")
        for c in sorted(novel, key=lambda x: x.get("confidence", ""), reverse=True)[:20]:
            conf = c.get("confidence", "?")
            phase = c.get("phase", "?")
            company = c.get("company", "?")
            moa = c.get("target_moa", "?")
            print(f"    ★ {c['drug_name']} ({moa}) — {company}")
            print(f"      Phase: {phase} | Confidence: {conf}")

    return {
        "articles": all_articles,
        "candidates": candidates,
        "novel": novel,
        "known": known,
    }


def mine_all_regions(use_llm=True):
    """Mine all regions and aggregate results."""
    all_results = {}
    for region in ["global", "china", "korea", "japan", "india", "europe"]:
        result = mine_region(region, use_llm=use_llm)
        all_results[region] = result

    # Aggregate
    total_articles = sum(len(r["articles"]) for r in all_results.values())
    total_candidates = sum(len(r["candidates"]) for r in all_results.values())
    total_novel = sum(len(r["novel"]) for r in all_results.values())

    print(f"\n{'='*70}")
    print(f"  GLOBAL MINING SUMMARY")
    print(f"{'='*70}")
    print(f"  Total articles:    {total_articles}")
    print(f"  Total candidates:  {total_candidates}")
    print(f"  Total novel:       {total_novel}")
    print(f"{'='*70}")

    return all_results


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SatyaBio Regional News Miner Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mine                          Mine all regions
  %(prog)s --mine --region china           Mine China sources only
  %(prog)s --mine --region korea --no-llm  Mine Korea, regex extraction only
  %(prog)s --status                        Show mining stats from DB
  %(prog)s --watchlist                     Show monitored companies/drugs
""",
    )
    parser.add_argument("--mine", action="store_true", help="Run the news miner")
    parser.add_argument("--region", type=str, default="all",
                        help="Region to mine: all, china, korea, japan, india, europe, global")
    parser.add_argument("--no-llm", action="store_true",
                        help="Skip Claude extraction, use regex only")
    parser.add_argument("--status", action="store_true",
                        help="Show mining statistics from DB")
    parser.add_argument("--watchlist", action="store_true",
                        help="Show monitored companies and drugs")
    parser.add_argument("--sources", action="store_true",
                        help="List all configured news sources")

    args = parser.parse_args()

    if args.watchlist:
        for region, watchlist in ALL_WATCHLISTS.items():
            print(f"\n{'='*50}")
            print(f"  {region.upper()} WATCHLIST")
            print(f"{'='*50}")
            for company, info in watchlist.items():
                drugs = ", ".join(info["known_drugs"])
                aliases = ", ".join(info["aliases"][:2])
                print(f"  {company} ({aliases})")
                print(f"    Drugs: {drugs}")

    elif args.sources:
        for region, sources in REGIONAL_SOURCES.items():
            print(f"\n  {region.upper()} sources:")
            for s in sources:
                print(f"    - {s['name']} ({s['parse_type']})")
                print(f"      {s['url'][:70]}...")

    elif args.status:
        if not DB_AVAILABLE or not DATABASE_URL:
            print("No database connection available.")
            sys.exit(1)
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM mined_articles")
            articles_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM drug_candidates")
            candidates_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM drug_candidates WHERE novelty = 'novel'")
            novel_count = cur.fetchone()[0]
            cur.execute("""
                SELECT region, COUNT(*) FROM mined_articles
                GROUP BY region ORDER BY COUNT(*) DESC
            """)
            region_counts = cur.fetchall()

            print(f"\n  Mining Statistics:")
            print(f"  Articles mined:     {articles_count}")
            print(f"  Drug candidates:    {candidates_count}")
            print(f"  Novel assets:       {novel_count}")
            print(f"\n  By region:")
            for region, count in region_counts:
                print(f"    {region}: {count} articles")
        except Exception as e:
            print(f"  Tables may not exist yet. Run --mine first. ({e})")
        conn.close()

    elif args.mine:
        use_llm = not args.no_llm
        if args.region == "all":
            mine_all_regions(use_llm=use_llm)
        else:
            mine_region(args.region, use_llm=use_llm)

    else:
        parser.print_help()
