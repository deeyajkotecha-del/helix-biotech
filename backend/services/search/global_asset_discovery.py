"""
SatyaBio — Global Drug Asset Discovery

Surfaces "under-the-radar" drug assets from non-English sources across
patents, clinical trial registries, and company IR pages worldwide.

Inspired by the "Hunt Globally" paper (arxiv 2602.15019) which showed that
85%+ of patent filings originate outside the US and many novel drug candidates
are disclosed only in regional, non-English channels.

DATA SOURCES (by region):
  ┌──────────────────────────────────────────────────────────────────────┐
  │ SOURCE              │ COVERAGE     │ ACCESS METHOD                  │
  ├──────────────────────────────────────────────────────────────────────┤
  │ WHO ICTRP           │ Global       │ XML web service + CSV download │
  │ ChiCTR              │ China        │ Web scrape + MCP              │
  │ CRIS                │ Korea        │ Web scrape                    │
  │ JRCT/UMIN-CTR       │ Japan        │ Web scrape                    │
  │ CTRI                │ India        │ Web scrape                    │
  │ Google Patents/BQ   │ Global       │ BigQuery SQL (free 1TB/mo)    │
  │ CNIPA PSS           │ China        │ Web scrape                    │
  │ Regional IR pages   │ CN/KR/JP/IN  │ Playwright + LLM translation  │
  │ NMPA (China FDA)    │ China        │ Web scrape                    │
  └──────────────────────────────────────────────────────────────────────┘

PIPELINE:
  1. DISCOVER — Pull trial/patent/IR data from regional sources
  2. TRANSLATE — Use Claude to translate non-English content to English
  3. RESOLVE — Cross-lingual entity resolution (恒瑞医药 → Hengrui, レンビマ → lenvatinib)
  4. ENRICH — Add target, MoA, phase, company metadata from drug_entities.py
  5. EMBED — Chunk + Voyage AI embed → pgvector in Neon
  6. ALERT — Flag novel assets not already in drug_entities.py

Usage:
    # Discover trials from all global registries for a target
    python3 global_asset_discovery.py --trials --target "GLP-1"

    # Search Chinese patents for a therapeutic area
    python3 global_asset_discovery.py --patents --query "KRAS inhibitor"

    # Scrape Chinese biotech IR pages
    python3 global_asset_discovery.py --ir --region china

    # Full pipeline: discover + translate + resolve + embed
    python3 global_asset_discovery.py --full --target "PD-1" --region all

    # Novel asset alert: find drugs NOT in our entity database
    python3 global_asset_discovery.py --novel --target "ADC"

    # Health check on all regional sources
    python3 global_asset_discovery.py --health

Requirements:
    pip install requests beautifulsoup4 psycopg2-binary voyageai anthropic
    pip install python-dotenv lxml playwright
    Optional: pip install google-cloud-bigquery  (for patent search)
"""

import os
import sys
import re
import json
import time
import hashlib
import argparse
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, quote_plus
from collections import OrderedDict

from dotenv import load_dotenv
load_dotenv()

import requests
from bs4 import BeautifulSoup

try:
    import psycopg2
except ImportError:
    print("pip install psycopg2-binary")
    sys.exit(1)

try:
    import voyageai
    VOYAGEAI_AVAILABLE = True
except ImportError:
    VOYAGEAI_AVAILABLE = False

try:
    import anthropic
except ImportError:
    print("pip install anthropic")
    sys.exit(1)

# ─── Config ───
DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
EMBED_MODEL = "voyage-3-lite"
EMBED_BATCH_SIZE = 32
CHUNK_SIZE = 500
CHUNK_OVERLAP = 75

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}


# =============================================================================
# REGIONAL COMPANY UNIVERSE — Non-US biotechs to track
# =============================================================================

GLOBAL_BIOTECH_UNIVERSE = {
    # ─── CHINA ───
    "600276.SS": {
        "name": "Hengrui Medicine (恒瑞医药)",
        "name_local": "恒瑞医药",
        "region": "china",
        "ir_url": "https://www.hengrui.com/en/investor.html",
        "ir_url_local": "https://www.hengrui.com/investor.html",
        "therapeutic_areas": ["oncology", "I&I", "pain"],
        "key_assets": ["camrelizumab (PD-1)", "SHR-A1811 (HER2 ADC)", "SHR-1901 (B7-H3 ADC)"],
    },
    "1801.HK": {
        "name": "Innovent Biologics (信达生物)",
        "name_local": "信达生物",
        "region": "china",
        "ir_url": "https://www.innoventbio.com/InvestorRelationEN",
        "ir_url_local": "https://www.innoventbio.com/InvestorRelation",
        "therapeutic_areas": ["oncology", "I&I", "metabolic"],
        "key_assets": ["sintilimab (PD-1)", "IBI362 (GLP-1/GCGR)", "IBI343 (CLDN18.2 ADC)"],
    },
    "BGNE": {
        "name": "BeiGene (百济神州)",
        "name_local": "百济神州",
        "region": "china",
        "ir_url": "https://ir.beigene.com/",
        "ir_url_local": "https://www.beigene.com.cn/investor-relations",
        "therapeutic_areas": ["oncology", "hematology"],
        "key_assets": ["zanubrutinib (BTK)", "tislelizumab (PD-1)", "BG-68501 (KRAS G12C)"],
    },
    "9688.HK": {
        "name": "Zai Lab (再鼎医药)",
        "name_local": "再鼎医药",
        "region": "china",
        "ir_url": "https://ir.zailaboratory.com/",
        "ir_url_local": "https://ir.zailaboratory.com/",
        "therapeutic_areas": ["oncology", "I&I", "neuro"],
        "key_assets": ["niraparib (PARP)", "bemarituzumab (FGFR2b)", "KarXT license (China)"],
    },
    "2359.HK": {
        "name": "WuXi AppTec (药明康德)",
        "name_local": "药明康德",
        "region": "china",
        "ir_url": "https://ir.wuxiapptec.com/",
        "ir_url_local": "https://www.wuxiapptec.com.cn/ir",
        "therapeutic_areas": ["CDMO/CRO"],
        "key_assets": ["CDMO services", "CRDMO platform"],
    },
    "688180.SS": {
        "name": "Junshi Biosciences (君实生物)",
        "name_local": "君实生物",
        "region": "china",
        "ir_url": "https://www.junshipharma.com/en/investor.html",
        "ir_url_local": "https://www.junshipharma.com/investor.html",
        "therapeutic_areas": ["oncology", "I&I"],
        "key_assets": ["toripalimab (PD-1)", "JS006 (CTLA-4)"],
    },
    "9926.HK": {
        "name": "Akeso (康方生物)",
        "name_local": "康方生物",
        "region": "china",
        "ir_url": "https://www.akesobio.com/en/investor.html",
        "ir_url_local": "https://www.akesobio.com/investor.html",
        "therapeutic_areas": ["oncology", "I&I"],
        "key_assets": ["cadonilimab (PD-1/CTLA-4 bispecific)", "ivonescimab (PD-1/VEGF bispecific)"],
    },

    # ─── KOREA ───
    "068270.KS": {
        "name": "Celltrion",
        "name_local": "셀트리온",
        "region": "korea",
        "ir_url": "https://www.celltrion.com/en-us/ir/financial-highlight",
        "ir_url_local": "https://www.celltrion.com/ko-kr/ir/financial-highlight",
        "therapeutic_areas": ["biosimilars", "I&I"],
        "key_assets": ["Remsima SC (infliximab biosimilar)", "CT-P43 (denosumab biosimilar)"],
    },
    "000100.KS": {
        "name": "Yuhan Corporation",
        "name_local": "유한양행",
        "region": "korea",
        "ir_url": "https://www.yuhan.co.kr/eng/invest/financial.do",
        "ir_url_local": "https://www.yuhan.co.kr/invest/financial.do",
        "therapeutic_areas": ["oncology", "metabolic"],
        "key_assets": ["lazertinib (EGFR)", "YH35324 (KRAS)"],
    },
    "145020.KS": {
        "name": "HLB (formerly HanAll BioPharma)",
        "name_local": "에이치엘비",
        "region": "korea",
        "ir_url": "https://www.hlb.co.kr/en/ir",
        "ir_url_local": "https://www.hlb.co.kr/ir",
        "therapeutic_areas": ["oncology"],
        "key_assets": ["rivoceranib/apatinib (VEGFR2)"],
    },
    "302440.KS": {
        "name": "SK Biopharmaceuticals",
        "name_local": "에스케이바이오팜",
        "region": "korea",
        "ir_url": "https://www.skbp.com/eng/ir/management.do",
        "ir_url_local": "https://www.skbp.com/ir/management.do",
        "therapeutic_areas": ["neuropsych"],
        "key_assets": ["cenobamate (NaV/GABA)", "carisbamate"],
    },

    # ─── JAPAN ───
    "4568.T": {
        "name": "Daiichi Sankyo",
        "name_local": "第一三共",
        "region": "japan",
        "ir_url": "https://www.daiichisankyo.com/investors/",
        "ir_url_local": "https://www.daiichisankyo.co.jp/ir/",
        "therapeutic_areas": ["oncology", "cardio"],
        "key_assets": ["Enhertu (HER2 ADC)", "datopotamab deruxtecan (TROP2 ADC)", "ifinatamab deruxtecan (B7-H3 ADC)"],
    },
    "4503.T": {
        "name": "Astellas Pharma",
        "name_local": "アステラス製薬",
        "region": "japan",
        "ir_url": "https://www.astellas.com/en/investors",
        "ir_url_local": "https://www.astellas.com/jp/investors",
        "therapeutic_areas": ["oncology", "transplant"],
        "key_assets": ["enfortumab vedotin (Nectin-4 ADC)", "zolbetuximab (CLDN18.2)"],
    },
    "4519.T": {
        "name": "Chugai Pharmaceutical (Roche subsidiary)",
        "name_local": "中外製薬",
        "region": "japan",
        "ir_url": "https://www.chugai-pharm.co.jp/english/ir/",
        "ir_url_local": "https://www.chugai-pharm.co.jp/ir/",
        "therapeutic_areas": ["oncology", "I&I", "neuro"],
        "key_assets": ["satralizumab (IL-6R)", "crovalimab (C5)"],
    },
    "4151.T": {
        "name": "Kyowa Kirin",
        "name_local": "協和キリン",
        "region": "japan",
        "ir_url": "https://ir.kyowakirin.com/en/",
        "ir_url_local": "https://ir.kyowakirin.com/ja/",
        "therapeutic_areas": ["oncology", "bone", "neuro"],
        "key_assets": ["mogamulizumab (CCR4)", "KHK4083 (OX40)"],
    },

    # ─── INDIA ───
    "SUNPHARMA.NS": {
        "name": "Sun Pharmaceutical Industries",
        "name_local": "Sun Pharmaceutical Industries",
        "region": "india",
        "ir_url": "https://sunpharma.com/investors/",
        "ir_url_local": "https://sunpharma.com/investors/",
        "therapeutic_areas": ["dermatology", "oncology", "specialty"],
        "key_assets": ["tildrakizumab (IL-23)", "deuruxolitinib (JAK)"],
    },
    "BIOCON.NS": {
        "name": "Biocon",
        "name_local": "Biocon",
        "region": "india",
        "ir_url": "https://www.biocon.com/investors/",
        "ir_url_local": "https://www.biocon.com/investors/",
        "therapeutic_areas": ["biosimilars", "oncology"],
        "key_assets": ["bevacizumab biosimilar", "trastuzumab biosimilar"],
    },

    # ─── EUROPE ───
    "EVT.DE": {
        "name": "Evotec",
        "name_local": "Evotec",
        "region": "europe",
        "ir_url": "https://www.evotec.com/en/invest",
        "ir_url_local": "https://www.evotec.com/en/invest",
        "therapeutic_areas": ["CNS", "oncology", "I&I"],
        "key_assets": ["EVT201 (GABA-A)", "iPSC-derived cell therapies"],
    },
    "BNTX": {
        "name": "BioNTech",
        "name_local": "BioNTech",
        "region": "europe",
        "ir_url": "https://investors.biontech.de/",
        "ir_url_local": "https://investors.biontech.de/",
        "therapeutic_areas": ["oncology", "infectious disease"],
        "key_assets": ["BNT211 (CLDN6 CAR-T)", "BNT327 (PD-L1/VEGF-A bispecific)"],
    },
    "ARGX": {
        "name": "argenx",
        "name_local": "argenx",
        "region": "europe",
        "ir_url": "https://www.argenx.com/investors",
        "ir_url_local": "https://www.argenx.com/investors",
        "therapeutic_areas": ["I&I", "hematology"],
        "key_assets": ["efgartigimod (FcRn)", "ARGX-109 (IL-22R)"],
    },
    "GN.CO": {
        "name": "Genmab",
        "name_local": "Genmab",
        "region": "europe",
        "ir_url": "https://ir.genmab.com/",
        "ir_url_local": "https://ir.genmab.com/",
        "therapeutic_areas": ["oncology"],
        "key_assets": ["epcoritamab (CD3xCD20 bispecific)", "GEN3009 (CD38)"],
    },
}


# =============================================================================
# CROSS-LINGUAL ENTITY RESOLUTION
# =============================================================================

# Common drug name mappings: local_name → english_canonical
# This is the seed; the LLM resolver expands it dynamically
KNOWN_ENTITY_ALIASES = {
    # Chinese drug names
    "恒瑞": "Hengrui",
    "信达": "Innovent",
    "百济神州": "BeiGene",
    "再鼎": "Zai Lab",
    "药明康德": "WuXi AppTec",
    "君实": "Junshi",
    "康方": "Akeso",
    "卡瑞利珠单抗": "camrelizumab",
    "信迪利单抗": "sintilimab",
    "替雷利珠单抗": "tislelizumab",
    "泽布替尼": "zanubrutinib",
    "特瑞普利单抗": "toripalimab",
    "卡度尼利单抗": "cadonilimab",
    "依沃西单抗": "ivonescimab",
    # Japanese drug names
    "エンハーツ": "Enhertu (T-DXd)",
    "レンビマ": "lenvatinib",
    "オプジーボ": "nivolumab",
    "キイトルーダ": "pembrolizumab",
    "テセントリク": "atezolizumab",
    # Korean drug names
    "렉라자": "lazertinib (Leclaza)",
    "램시마": "Remsima (infliximab biosimilar)",
    # Target translations
    "表皮生长因子受体": "EGFR",
    "血管内皮生长因子": "VEGF",
    "程序性死亡受体": "PD-1",
    "抗体偶联药物": "ADC",
    "双特异性抗体": "bispecific antibody",
}

# Regional trial registry IDs → source
TRIAL_REGISTRY_PREFIXES = {
    "NCT": "ClinicalTrials.gov",
    "ChiCTR": "Chinese Clinical Trial Registry",
    "CTR": "Chinese Drug Trial Registry (CDE)",
    "CRIS": "Korean Clinical Research Info Service",
    "KCT": "Korean Clinical Research Info Service",
    "jRCT": "Japan Registry of Clinical Trials",
    "UMIN": "UMIN Clinical Trials Registry (Japan)",
    "CTRI": "Clinical Trials Registry India",
    "EUCTR": "EU Clinical Trials Register",
    "ISRCTN": "ISRCTN Registry (UK)",
    "ACTRN": "Australian NZ Clinical Trials Registry",
}


# =============================================================================
# SOURCE 1: ClinicalTrials.gov API v2 — Global clinical trial search
# =============================================================================
# This is the best free, public, no-auth API for clinical trials.
# Despite being US-based, it covers global trials including many registered
# in China, Korea, Japan, India, and Europe.
# API docs: https://clinicaltrials.gov/data-api/api
# =============================================================================

CTGOV_API_BASE = "https://clinicaltrials.gov/api/v2/studies"

# Map regions to country filter values for ClinicalTrials.gov API
REGION_TO_COUNTRIES = {
    "china": ["China"],
    "korea": ["Korea, Republic of"],
    "japan": ["Japan"],
    "india": ["India"],
    "europe": ["Germany", "France", "United Kingdom", "Netherlands", "Denmark", "Switzerland"],
    "all": [],  # no country filter
}


def search_trials_global(query, region="all", max_results=50, phase=None, status=None):
    """
    Search ClinicalTrials.gov API v2 for trials worldwide.

    This is the PRIMARY trial search — it works, returns JSON, needs no auth.
    Covers global trials including Chinese, Korean, Japanese studies.

    Args:
        query: Drug name, target, or condition (e.g., "GLP-1", "KRAS inhibitor")
        region: "all", "china", "korea", "japan", "india", "europe"
        max_results: Max number of trials to return
        phase: Optional phase filter (e.g., "PHASE3", "PHASE2")
        status: Optional status filter (e.g., "RECRUITING", "COMPLETED")

    Returns:
        List of trial dicts
    """
    trials = []
    page_size = min(max_results, 100)  # API max is 100 per page

    params = {
        "format": "json",
        "pageSize": page_size,
        "countTotal": "true",
    }

    # Build query — search across interventions and conditions
    params["query.intr"] = query

    # Add country filter for non-"all" regions
    countries = REGION_TO_COUNTRIES.get(region, [])
    if countries:
        # ClinicalTrials.gov uses AREA[LocationCountry] for country filter
        country_filter = " OR ".join(f'AREA[LocationCountry] "{c}"' for c in countries)
        params["filter.advanced"] = country_filter

    # Phase filter
    if phase:
        params["filter.phase"] = phase

    # Status filter
    if status:
        params["filter.overallStatus"] = status

    try:
        print(f"  [CT.gov API] Searching: {query} (region={region})...")
        resp = requests.get(CTGOV_API_BASE, params=params, headers=HEADERS, timeout=30)

        if resp.status_code != 200:
            print(f"  [CT.gov API] HTTP {resp.status_code}")
            # Try broader search with query.term instead
            params.pop("query.intr", None)
            params["query.term"] = query
            resp = requests.get(CTGOV_API_BASE, params=params, headers=HEADERS, timeout=30)

        if resp.status_code != 200:
            print(f"  [CT.gov API] HTTP {resp.status_code} on retry")
            return trials

        data = resp.json()
        total = data.get("totalCount", 0)
        studies = data.get("studies", [])

        for study in studies:
            trial = _parse_ctgov_study(study)
            if trial:
                trials.append(trial)

        print(f"  [CT.gov API] Found {len(trials)} trials (total matches: {total})")

        # Fetch additional pages if needed
        next_token = data.get("nextPageToken")
        pages_fetched = 1
        while next_token and len(trials) < max_results and pages_fetched < 5:
            params["pageToken"] = next_token
            time.sleep(0.5)  # rate limit
            try:
                resp = requests.get(CTGOV_API_BASE, params=params, headers=HEADERS, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    for study in data.get("studies", []):
                        trial = _parse_ctgov_study(study)
                        if trial:
                            trials.append(trial)
                    next_token = data.get("nextPageToken")
                    pages_fetched += 1
                else:
                    break
            except Exception:
                break

    except Exception as e:
        print(f"  [CT.gov API] Error: {e}")

    return trials[:max_results]


def _parse_ctgov_study(study):
    """Parse a single study from ClinicalTrials.gov API v2 JSON response."""
    try:
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status_mod = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
        arms = proto.get("armsInterventionsModule", {})
        cond_mod = proto.get("conditionsModule", {})
        contact_mod = proto.get("contactsLocationsModule", {})

        nct_id = ident.get("nctId", "")
        title = ident.get("briefTitle", "") or ident.get("officialTitle", "")

        # Get phase
        phases = design.get("phases", [])
        phase_str = ", ".join(phases) if phases else ""

        # Get sponsor
        lead_sponsor = sponsor_mod.get("leadSponsor", {})
        sponsor_name = lead_sponsor.get("name", "")

        # Get interventions
        interventions = arms.get("interventions", [])
        intervention_names = [i.get("name", "") for i in interventions]

        # Get conditions
        conditions = cond_mod.get("conditions", [])

        # Get countries from locations
        locations = contact_mod.get("locations", [])
        countries = list(set(loc.get("country", "") for loc in locations if loc.get("country")))

        # Get secondary IDs (may include ChiCTR, EUDRACT, etc.)
        secondary_ids = ident.get("secondaryIdInfos", [])
        other_registry_ids = []
        for sid in secondary_ids:
            sid_id = sid.get("id", "")
            if sid_id:
                other_registry_ids.append(sid_id)

        # Determine source registry
        source_registry = "ClinicalTrials.gov"
        for rid in other_registry_ids:
            reg = _identify_registry(rid)
            if reg != "Unknown":
                source_registry += f" + {reg}"
                break

        return {
            "trial_id": nct_id,
            "title": title,
            "status": status_mod.get("overallStatus", ""),
            "phase": phase_str,
            "countries": ", ".join(countries),
            "date_registered": status_mod.get("studyFirstPostDateStruct", {}).get("date", ""),
            "source_registry": source_registry,
            "sponsor": sponsor_name,
            "interventions": ", ".join(intervention_names),
            "conditions": ", ".join(conditions),
            "other_registry_ids": other_registry_ids,
            "source": "ctgov_api_v2",
            "url": f"https://clinicaltrials.gov/study/{nct_id}",
        }

    except Exception as e:
        return None


def _identify_registry(trial_id):
    """Identify which registry a trial ID comes from."""
    for prefix, registry in TRIAL_REGISTRY_PREFIXES.items():
        if trial_id.upper().startswith(prefix.upper()):
            return registry
    return "Unknown"


# =============================================================================
# SOURCE 1b: Search trials by COUNTRY specifically (for regional coverage)
# =============================================================================

def search_trials_by_country(query, country, max_results=30):
    """
    Search ClinicalTrials.gov specifically for trials in a given country.
    Useful for finding China-only, Korea-only, Japan-only trials.
    """
    params = {
        "format": "json",
        "pageSize": min(max_results, 100),
        "query.term": query,
        "filter.advanced": f'AREA[LocationCountry] "{country}"',
        "countTotal": "true",
    }

    trials = []
    try:
        resp = requests.get(CTGOV_API_BASE, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            for study in data.get("studies", []):
                trial = _parse_ctgov_study(study)
                if trial:
                    trials.append(trial)
            total = data.get("totalCount", 0)
            print(f"  [CT.gov] {country}: {len(trials)} trials (total: {total})")
    except Exception as e:
        print(f"  [CT.gov] Error for {country}: {e}")

    return trials


def search_trials_by_term(query, region="all", max_results=100):
    """
    Search ClinicalTrials.gov using query.term (searches titles, conditions,
    interventions, keywords). Use this for gene targets like KRAS, BRAF, EGFR
    where the target isn't always the intervention name.
    """
    params = {
        "format": "json",
        "pageSize": min(max_results, 100),
        "query.term": query,
        "countTotal": "true",
    }

    countries = REGION_TO_COUNTRIES.get(region, [])
    if countries:
        country_filter = " OR ".join(f'AREA[LocationCountry] "{c}"' for c in countries)
        params["filter.advanced"] = country_filter

    trials = []
    try:
        print(f"  [CT.gov term search] Searching: {query} (region={region})...")
        resp = requests.get(CTGOV_API_BASE, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            for study in data.get("studies", []):
                trial = _parse_ctgov_study(study)
                if trial:
                    trials.append(trial)
            total = data.get("totalCount", 0)
            print(f"  [CT.gov term search] Found {len(trials)} trials (total: {total})")
    except Exception as e:
        print(f"  [CT.gov term search] Error: {e}")

    return trials


# =============================================================================
# SOURCE 3: Patent Search — EPO Open Patent Services + Google Patents BigQuery
# =============================================================================
# Two approaches:
#   a) EPO OPS (Open Patent Services) — free API, 4GB/week, covers worldwide patents
#      Docs: https://developers.epo.org/
#   b) Google Patents BigQuery — free 1TB/month, requires google-cloud-bigquery
#   c) Lens.org — free API with 50 requests/min, covers global patents
# =============================================================================

def search_patents_lens(query, countries=None, max_results=50):
    """
    Search Lens.org patent database (free, global coverage, REST API).
    Requires LENS_API_KEY in .env (free account at lens.org).

    Falls back to EPO OPS if no Lens key, then to Google Patents BigQuery.
    """
    lens_key = os.environ.get("LENS_API_KEY", "")
    if not lens_key:
        print("  [Lens.org] No LENS_API_KEY — trying EPO OPS...")
        return search_patents_epo(query, countries, max_results)

    patents = []
    countries = countries or ["CN", "KR", "JP", "IN", "EP", "WO"]

    # Build Lens.org API query
    jurisdiction_filter = [{"term": {"jurisdiction": c}} for c in countries]

    payload = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"title": query}},
                    # IPC class A61 = medical/veterinary
                    {"match": {"classification_ipc.symbol": "A61"}},
                ],
                "should": jurisdiction_filter,
                "minimum_should_match": 1,
            }
        },
        "size": min(max_results, 100),
        "sort": [{"date_published": "desc"}],
        "include": [
            "lens_id", "title", "abstract", "jurisdiction",
            "date_published", "applicant", "classification_ipc",
            "biblio.publication_reference",
        ],
    }

    try:
        resp = requests.post(
            "https://api.lens.org/patent/search",
            json=payload,
            headers={
                "Authorization": f"Bearer {lens_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            total = data.get("total", 0)

            for hit in data.get("data", []):
                patent = {
                    "publication_number": hit.get("biblio", {}).get("publication_reference", {}).get("document_id", {}).get("doc_number", ""),
                    "title": hit.get("title", ""),
                    "abstract": (hit.get("abstract", "") or "")[:500],
                    "assignee": ", ".join(hit.get("applicant", {}).get("name", [])) if isinstance(hit.get("applicant"), dict) else "",
                    "filing_date": "",
                    "publication_date": hit.get("date_published", ""),
                    "country_code": hit.get("jurisdiction", ""),
                    "ipc_code": "",
                    "lens_id": hit.get("lens_id", ""),
                    "source": "lens_org",
                }

                # Extract IPC codes
                ipcs = hit.get("classification_ipc", [])
                if ipcs:
                    patent["ipc_code"] = ipcs[0].get("symbol", "") if isinstance(ipcs[0], dict) else str(ipcs[0])

                patents.append(patent)

            print(f"  [Lens.org] Found {len(patents)} patents (total matches: {total})")
        else:
            print(f"  [Lens.org] HTTP {resp.status_code}: {resp.text[:200]}")
            return search_patents_epo(query, countries, max_results)

    except Exception as e:
        print(f"  [Lens.org] Error: {e}")
        return search_patents_epo(query, countries, max_results)

    return patents


def search_patents_epo(query, countries=None, max_results=50):
    """
    Search EPO Open Patent Services (OPS) — free, no key needed for basic search.
    Covers worldwide patents including CN, KR, JP, IN.

    Endpoint: https://ops.epo.org/3.2/rest-services/published-data/search
    """
    patents = []
    countries = countries or ["CN", "KR", "JP", "IN", "EP", "WO"]

    # Build CQL query for EPO OPS
    # ta = title/abstract, ic = IPC class, pn = publication number country
    country_clause = " OR ".join(f'pn={c}' for c in countries)
    cql_query = f'ta="{query}" AND ic=A61K AND ({country_clause})'

    try:
        # EPO OPS published-data search (no auth needed for basic access)
        url = "https://ops.epo.org/3.2/rest-services/published-data/search"
        params = {
            "q": cql_query,
            "Range": f"1-{min(max_results, 100)}",
        }
        headers = {
            **HEADERS,
            "Accept": "application/json",
        }

        print(f"  [EPO OPS] Searching: {cql_query[:80]}...")
        resp = requests.get(url, params=params, headers=headers, timeout=30)

        if resp.status_code == 200:
            data = resp.json()
            results = data.get("ops:world-patent-data", {}).get("ops:biblio-search", {})
            search_result = results.get("ops:search-result", {})
            total = results.get("@total-result-count", "0")

            # Parse exchange documents
            docs = search_result.get("exchange-documents", {}).get("exchange-document", [])
            if isinstance(docs, dict):
                docs = [docs]

            for doc in docs[:max_results]:
                patent = _parse_epo_document(doc)
                if patent:
                    patents.append(patent)

            print(f"  [EPO OPS] Found {len(patents)} patents (total: {total})")

        elif resp.status_code == 403:
            print(f"  [EPO OPS] Rate limited — try again in a minute")
        else:
            print(f"  [EPO OPS] HTTP {resp.status_code}")

    except Exception as e:
        print(f"  [EPO OPS] Error: {e}")

    # Fallback to BigQuery if EPO returned nothing
    if not patents:
        patents = search_patents_bigquery(query, countries, max_results)

    return patents


def _parse_epo_document(doc):
    """Parse a single patent document from EPO OPS JSON."""
    try:
        bib = doc.get("bibliographic-data", {})

        # Publication reference
        pub_ref = bib.get("publication-reference", {}).get("document-id", [])
        if isinstance(pub_ref, dict):
            pub_ref = [pub_ref]

        pub_number = ""
        country_code = ""
        pub_date = ""
        for ref in pub_ref:
            if ref.get("@document-id-type") == "epodoc":
                pub_number = ref.get("doc-number", {}).get("$", "")
                country_code = ref.get("country", {}).get("$", "")
                pub_date = ref.get("date", {}).get("$", "")

        # Title (may be in multiple languages)
        title_data = bib.get("invention-title", [])
        if isinstance(title_data, dict):
            title_data = [title_data]

        title = ""
        title_original = ""
        for t in title_data:
            lang = t.get("@lang", "")
            text = t.get("$", "")
            if lang == "en":
                title = text
            elif not title_original:
                title_original = text

        if not title:
            title = title_original

        # Applicant
        applicants = bib.get("parties", {}).get("applicants", {}).get("applicant", [])
        if isinstance(applicants, dict):
            applicants = [applicants]
        assignee = ""
        for app in applicants:
            name_data = app.get("applicant-name", {}).get("name", {})
            if isinstance(name_data, dict):
                assignee = name_data.get("$", "")
            elif isinstance(name_data, str):
                assignee = name_data
            if assignee:
                break

        # IPC
        ipc_data = bib.get("classification-ipc", {}).get("text", {})
        ipc_code = ipc_data.get("$", "") if isinstance(ipc_data, dict) else str(ipc_data)

        return {
            "publication_number": pub_number,
            "title": title,
            "title_original": title_original if title_original != title else "",
            "abstract": "",  # OPS search doesn't include abstracts
            "assignee": assignee,
            "filing_date": "",
            "publication_date": pub_date,
            "country_code": country_code,
            "ipc_code": ipc_code,
            "source": "epo_ops",
        }

    except Exception:
        return None


def search_patents_bigquery(query, countries=None, max_results=50):
    """
    Search Google Patents public dataset via BigQuery.
    Requires: pip install google-cloud-bigquery + GOOGLE_APPLICATION_CREDENTIALS env var
    """
    patents = []

    try:
        from google.cloud import bigquery
    except ImportError:
        print("  [Patents BQ] google-cloud-bigquery not installed")
        print("  [Patents BQ] To enable: pip install google-cloud-bigquery")
        print("  [Patents BQ] Or set LENS_API_KEY in .env for Lens.org (free)")
        return patents

    min_date = int((datetime.now() - timedelta(days=365 * 3)).strftime("%Y%m%d"))
    country_list = "', '".join(countries or ["CN", "KR", "JP", "IN", "EP", "WO"])

    sql = f"""
    SELECT
        publication_number,
        title_localized.text AS title,
        title_localized.language AS title_lang,
        abstract_localized.text AS abstract,
        filing_date,
        publication_date,
        assignee_harmonized.name AS assignee,
        country_code
    FROM
        `patents-public-data.patents.publications`,
        UNNEST(title_localized) AS title_localized,
        UNNEST(abstract_localized) AS abstract_localized,
        UNNEST(assignee_harmonized) AS assignee_harmonized,
        UNNEST(ipc) AS ipc
    WHERE
        (ipc.code LIKE 'A61K%' OR ipc.code LIKE 'A61P%')
        AND (LOWER(title_localized.text) LIKE '%{query.lower()}%'
             OR LOWER(abstract_localized.text) LIKE '%{query.lower()}%')
        AND country_code IN ('{country_list}')
        AND publication_date >= {min_date}
    ORDER BY publication_date DESC
    LIMIT {max_results}
    """

    try:
        client = bigquery.Client()
        results = client.query(sql).result()
        for row in results:
            patents.append({
                "publication_number": row.publication_number,
                "title": row.title,
                "abstract": (row.abstract or "")[:500],
                "assignee": row.assignee,
                "publication_date": str(row.publication_date) if row.publication_date else "",
                "country_code": row.country_code,
                "source": "google_patents_bigquery",
            })
        print(f"  [Patents BQ] Found {len(patents)} patents")
    except Exception as e:
        print(f"  [Patents BQ] Error: {e}")

    return patents


# =============================================================================
# SOURCE 4: Regional IR Pages (with translation)
# =============================================================================

def scrape_regional_ir(ticker_or_id, company_info, use_local_url=True):
    """
    Scrape a non-US biotech's IR page for presentations, often in local language.
    Uses Playwright for JS-rendered pages, then Claude for translation.
    """
    pdfs = []

    ir_url = company_info.get("ir_url_local" if use_local_url else "ir_url", "")
    if not ir_url:
        print(f"  No IR URL for {ticker_or_id}")
        return pdfs

    region = company_info.get("region", "")
    company_name = company_info["name"]

    print(f"  Scraping {company_name} IR ({region})...")
    print(f"  URL: {ir_url}")

    # First try requests + BS4
    try:
        resp = requests.get(ir_url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            from ir_scraper_v2 import _extract_pdf_links_from_html, PDFResult
            found = _extract_pdf_links_from_html(resp.text, ir_url, ticker_or_id)
            if found:
                pdfs.extend(found)
                print(f"  [BS4] Found {len(found)} PDFs")
    except Exception as e:
        print(f"  [BS4] Error: {e}")

    # Then try Playwright for JS-rendered pages
    if len(pdfs) < 3:
        try:
            from ir_scraper_v2 import strategy_playwright
            pw_pdfs = strategy_playwright(ticker_or_id, ir_url, timeout=30000)
            pdfs.extend(pw_pdfs)
        except Exception as e:
            print(f"  [Playwright] Error: {e}")

    print(f"  {ticker_or_id}: Found {len(pdfs)} PDFs from regional IR")
    return pdfs


# =============================================================================
# TRANSLATION ENGINE — Claude-powered translation
# =============================================================================

def translate_content(text, source_lang="auto", target_lang="en", context="biotech"):
    """
    Translate non-English biotech content to English using Claude.
    Handles drug names, targets, and biotech-specific terminology.

    Args:
        text: The text to translate
        source_lang: Source language (auto-detected if "auto")
        target_lang: Target language (default: English)
        context: Domain context for better translation (default: biotech)

    Returns:
        Dict with: translated_text, detected_language, entities_found
    """
    if not ANTHROPIC_API_KEY:
        print("  [Translate] No ANTHROPIC_API_KEY set")
        return {"translated_text": text, "detected_language": "unknown", "entities_found": []}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are a biotech/pharma translation specialist. Translate the following text to English.

CRITICAL RULES:
1. Keep drug names in their original form AND add the English/INN name in parentheses
   Example: 卡瑞利珠单抗 → "camrelizumab (卡瑞利珠单抗)"
2. Keep company names in their original form AND add English name
   Example: 恒瑞医药 → "Hengrui Medicine (恒瑞医药)"
3. Translate ALL target names to standard English abbreviations
   Example: 表皮生长因子受体 → EGFR
4. Translate clinical terms to standard English
   Example: 客观缓解率 → ORR (objective response rate)
5. Preserve all numbers, percentages, p-values exactly

After the translation, list ALL biotech entities you found:
- Drug names (both local and English/INN)
- Company names
- Targets/pathways
- Clinical trial IDs
- Diseases/indications

TEXT TO TRANSLATE:
{text[:4000]}

FORMAT YOUR RESPONSE AS JSON:
{{
    "translated_text": "...",
    "detected_language": "zh/ja/ko/hi/de/fr/...",
    "entities": [
        {{"type": "drug", "local_name": "...", "english_name": "...", "context": "..."}},
        {{"type": "company", "local_name": "...", "english_name": "...", "context": "..."}},
        {{"type": "target", "local_name": "...", "english_name": "...", "context": "..."}},
        {{"type": "trial_id", "id": "...", "registry": "..."}},
        {{"type": "indication", "local_name": "...", "english_name": "..."}}
    ]
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        result_text = response.content[0].text

        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            result = json.loads(json_match.group())
            return result
        else:
            return {"translated_text": result_text, "detected_language": "unknown", "entities_found": []}

    except Exception as e:
        print(f"  [Translate] Error: {e}")
        return {"translated_text": text, "detected_language": "unknown", "entities_found": []}


# =============================================================================
# ENTITY RESOLUTION — Map non-English entities to drug_entities.py
# =============================================================================

def resolve_entities(entities, conn=None):
    """
    Cross-lingual entity resolution: match discovered entities to our drug_entities database.

    For each entity:
      1. Check KNOWN_ENTITY_ALIASES for direct match
      2. Check drug_entities.py drug_aliases table
      3. If no match → flag as NOVEL (potential new asset to track)

    Returns:
        resolved: list of matched entities with drug_entity_id
        novel: list of unmatched entities (potential new assets)
    """
    resolved = []
    novel = []

    for entity in entities:
        if entity.get("type") not in ("drug", "company", "target"):
            continue

        local_name = entity.get("local_name", "")
        english_name = entity.get("english_name", "")

        # Step 1: Check known aliases
        canonical = KNOWN_ENTITY_ALIASES.get(local_name) or KNOWN_ENTITY_ALIASES.get(english_name)

        if canonical:
            entity["resolved_name"] = canonical
            entity["resolution_method"] = "known_alias"
            resolved.append(entity)
            continue

        # Step 2: Check drug_entities database
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT d.id, d.generic_name, d.brand_name, d.company
                        FROM drugs d
                        JOIN drug_aliases da ON da.drug_id = d.id
                        WHERE LOWER(da.alias) = LOWER(%s)
                           OR LOWER(da.alias) = LOWER(%s)
                           OR LOWER(d.generic_name) = LOWER(%s)
                           OR LOWER(d.generic_name) = LOWER(%s)
                        LIMIT 1
                    """, (local_name, english_name, local_name, english_name))

                    row = cur.fetchone()
                    if row:
                        entity["resolved_name"] = row[1] or row[2]
                        entity["drug_entity_id"] = row[0]
                        entity["company"] = row[3]
                        entity["resolution_method"] = "database"
                        resolved.append(entity)
                        continue
            except Exception:
                pass

        # Step 3: No match → novel asset
        entity["resolution_method"] = "novel"
        novel.append(entity)

    return resolved, novel


# =============================================================================
# NOVEL ASSET ALERTING
# =============================================================================

def alert_novel_assets(novel_entities, query_context=""):
    """
    Generate an alert for novel drug assets not in our database.
    These are potential investment signals — drugs that aren't on the radar yet.
    """
    if not novel_entities:
        return None

    alert = {
        "timestamp": datetime.now().isoformat(),
        "query_context": query_context,
        "novel_assets_count": len(novel_entities),
        "assets": [],
    }

    for entity in novel_entities:
        asset = {
            "type": entity.get("type"),
            "local_name": entity.get("local_name", ""),
            "english_name": entity.get("english_name", ""),
            "context": entity.get("context", ""),
            "action_needed": "ADD_TO_DATABASE",
        }

        # Determine priority based on context
        context_lower = (entity.get("context", "") + " " + entity.get("english_name", "")).lower()
        if any(kw in context_lower for kw in ["phase 3", "phase iii", "pivotal", "registrational"]):
            asset["priority"] = "HIGH"
        elif any(kw in context_lower for kw in ["phase 2", "phase ii"]):
            asset["priority"] = "MEDIUM"
        else:
            asset["priority"] = "LOW"

        alert["assets"].append(asset)

    # Sort by priority
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    alert["assets"].sort(key=lambda a: priority_order.get(a["priority"], 3))

    return alert


# =============================================================================
# FULL PIPELINE — Discover → Translate → Resolve → Embed → Alert
# =============================================================================

def run_full_pipeline(target=None, query=None, region="all", max_results=50, dry_run=False):
    """
    Run the complete global asset discovery pipeline.

    Args:
        target: Drug target to search for (e.g., "GLP-1", "PD-1", "KRAS")
        query: Free-text query (e.g., "ADC breast cancer")
        region: "all", "china", "korea", "japan", "india", "europe"
        max_results: Max results per source
        dry_run: If True, print results without embedding

    Returns:
        Dict with discovery results, novel assets, and ingestion stats
    """
    search_term = target or query or ""
    if not search_term:
        print("ERROR: Provide --target or --query")
        return None

    print(f"\n{'='*70}")
    print(f"  GLOBAL ASSET DISCOVERY PIPELINE")
    print(f"  Query: {search_term}")
    print(f"  Region: {region}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*70}\n")

    results = {
        "query": search_term,
        "region": region,
        "timestamp": datetime.now().isoformat(),
        "trials": [],
        "patents": [],
        "ir_documents": [],
        "novel_assets": [],
        "stats": {
            "total_trials": 0,
            "total_patents": 0,
            "total_ir_docs": 0,
            "novel_assets": 0,
            "regions_covered": [],
        },
    }

    all_entities = []

    # ─── Step 1: Discover trials from global registries ───
    print("\n  STEP 1: Searching global clinical trial registries...")

    # ClinicalTrials.gov API v2 — primary source (covers global trials)
    global_trials = search_trials_global(search_term, region=region, max_results=max_results)
    results["trials"].extend(global_trials)

    # For specific regions, also do a country-specific search to catch more
    region_country_map = {
        "china": "China",
        "korea": "Korea, Republic of",
        "japan": "Japan",
        "india": "India",
    }
    if region in region_country_map:
        country_trials = search_trials_by_country(search_term, region_country_map[region], max_results=30)
        existing_ids = {t["trial_id"] for t in results["trials"]}
        for trial in country_trials:
            if trial["trial_id"] not in existing_ids:
                results["trials"].append(trial)

    results["stats"]["total_trials"] = len(results["trials"])
    print(f"\n  Found {results['stats']['total_trials']} total trials")

    # ─── Step 2: Search patents ───
    print("\n  STEP 2: Searching global patent databases...")

    countries_map = {
        "all": ["CN", "KR", "JP", "IN", "EP", "WO"],
        "china": ["CN"],
        "korea": ["KR"],
        "japan": ["JP"],
        "india": ["IN"],
        "europe": ["EP", "DE", "FR", "GB"],
    }
    patent_countries = countries_map.get(region, ["CN", "KR", "JP", "IN"])

    patents = search_patents_lens(search_term, countries=patent_countries, max_results=max_results)
    results["patents"] = patents
    results["stats"]["total_patents"] = len(patents)
    print(f"\n  Found {results['stats']['total_patents']} patents")

    # ─── Step 3: Scrape regional IR pages ───
    print("\n  STEP 3: Scraping regional IR pages...")

    for ticker, info in GLOBAL_BIOTECH_UNIVERSE.items():
        company_region = info.get("region", "")
        if region != "all" and company_region != region:
            continue

        # Check if company's key assets mention our target
        key_assets_text = " ".join(info.get("key_assets", [])).lower()
        ta_text = " ".join(info.get("therapeutic_areas", [])).lower()

        if search_term.lower() in key_assets_text or search_term.lower() in ta_text:
            ir_docs = scrape_regional_ir(ticker, info, use_local_url=True)
            results["ir_documents"].extend(ir_docs)
            results["stats"]["regions_covered"].append(company_region)

    results["stats"]["total_ir_docs"] = len(results["ir_documents"])
    results["stats"]["regions_covered"] = list(set(results["stats"]["regions_covered"]))

    # ─── Step 4: Translate non-English content ───
    print("\n  STEP 4: Translating non-English content...")

    translated_count = 0
    for trial in results["trials"]:
        title = trial.get("title", "")
        # Detect non-English content (simple heuristic: contains CJK characters)
        if _contains_cjk(title) or _contains_korean(title):
            translated = translate_content(title, context="clinical trial")
            trial["title_original"] = title
            trial["title"] = translated.get("translated_text", title)
            trial["detected_language"] = translated.get("detected_language", "")
            all_entities.extend(translated.get("entities", []))
            translated_count += 1

    for patent in results["patents"]:
        title = patent.get("title", "")
        if _contains_cjk(title) or _contains_korean(title):
            translated = translate_content(
                f"Title: {title}\nAbstract: {patent.get('abstract', '')}",
                context="pharmaceutical patent"
            )
            patent["title_original"] = title
            patent["title"] = translated.get("translated_text", title)
            all_entities.extend(translated.get("entities", []))
            translated_count += 1

    print(f"  Translated {translated_count} non-English items")

    # ─── Step 5: Entity resolution ───
    print("\n  STEP 5: Cross-lingual entity resolution...")

    conn = None
    if DATABASE_URL and not dry_run:
        conn = psycopg2.connect(DATABASE_URL)

    resolved, novel = resolve_entities(all_entities, conn)
    results["novel_assets"] = novel
    results["stats"]["novel_assets"] = len(novel)

    print(f"  Resolved {len(resolved)} known entities")
    print(f"  Found {len(novel)} NOVEL assets (not in our database)")

    # ─── Step 6: Alert on novel assets ───
    if novel:
        alert = alert_novel_assets(novel, query_context=search_term)
        if alert:
            print(f"\n  {'='*50}")
            print(f"  ⚡ NOVEL ASSET ALERT: {alert['novel_assets_count']} new assets found!")
            print(f"  {'='*50}")
            for asset in alert["assets"]:
                print(f"    [{asset['priority']}] {asset['english_name'] or asset['local_name']}")
                print(f"      Type: {asset['type']}, Context: {asset['context'][:80]}")

    # ─── Step 7: Embed and store (if not dry run) ───
    if not dry_run and conn:
        print("\n  STEP 7: Embedding and storing in Neon...")
        vo_client = voyageai.Client(api_key=VOYAGE_API_KEY)
        _embed_discovery_results(results, conn, vo_client)
        conn.close()

    # Save results to JSON
    output_path = f"global_discovery_{search_term.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(output_path, "w") as f:
        # Convert PDFResult objects to dicts for JSON serialization
        serializable = _make_serializable(results)
        json.dump(serializable, f, indent=2, default=str)
    print(f"\n  Results saved to {output_path}")

    # Print summary
    print(f"\n{'='*70}")
    print(f"  DISCOVERY SUMMARY")
    print(f"{'='*70}")
    print(f"  Trials found:    {results['stats']['total_trials']}")
    print(f"  Patents found:   {results['stats']['total_patents']}")
    print(f"  IR documents:    {results['stats']['total_ir_docs']}")
    print(f"  Novel assets:    {results['stats']['novel_assets']}")
    print(f"  Regions covered: {', '.join(results['stats']['regions_covered']) or 'none'}")
    print(f"{'='*70}\n")

    return results


def _make_serializable(obj):
    """Convert objects to JSON-serializable dicts."""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return obj


def _embed_discovery_results(results, conn, vo_client):
    """Embed and store discovery results in Neon pgvector."""
    from xbi_scraper import embed_and_store, chunk_text

    ingested = 0

    # Embed trials
    for trial in results["trials"]:
        text = _trial_to_text(trial)
        if len(text.split()) < 30:
            continue

        doc_id = embed_and_store(
            conn, vo_client, text,
            ticker=trial.get("trial_id", ""),
            company_name=trial.get("sponsor", ""),
            title=f"[Global Trial] {trial.get('title', '')[:100]}",
            doc_type="global_trial",
            source_url=trial.get("url", ""),
        )
        if doc_id:
            ingested += 1
        time.sleep(0.2)

    # Embed patents
    for patent in results["patents"]:
        text = _patent_to_text(patent)
        if len(text.split()) < 30:
            continue

        doc_id = embed_and_store(
            conn, vo_client, text,
            ticker=patent.get("publication_number", ""),
            company_name=patent.get("assignee", ""),
            title=f"[Patent] {patent.get('title', '')[:100]}",
            doc_type="global_patent",
            source_url=f"https://patents.google.com/patent/{patent.get('publication_number', '')}",
        )
        if doc_id:
            ingested += 1
        time.sleep(0.2)

    print(f"  Embedded {ingested} documents into Neon")


def _trial_to_text(trial):
    """Convert a trial dict to embeddable text."""
    parts = [
        f"Clinical Trial: {trial.get('title', '')}",
        f"Trial ID: {trial.get('trial_id', '')}",
        f"Registry: {trial.get('source_registry', '')}",
        f"Status: {trial.get('status', '')}",
        f"Phase: {trial.get('phase', '')}",
        f"Sponsor: {trial.get('sponsor', '')}",
        f"Countries: {trial.get('countries', '')}",
        f"Interventions: {trial.get('interventions', '')}",
        f"Conditions: {trial.get('conditions', '')}",
        f"Date Registered: {trial.get('date_registered', '')}",
    ]
    if trial.get("title_original"):
        parts.append(f"Original Title: {trial['title_original']}")
    return "\n".join(parts)


def _patent_to_text(patent):
    """Convert a patent dict to embeddable text."""
    parts = [
        f"Patent: {patent.get('title', '')}",
        f"Publication Number: {patent.get('publication_number', '')}",
        f"Country: {patent.get('country_code', '')}",
        f"Assignee: {patent.get('assignee', '')}",
        f"Filing Date: {patent.get('filing_date', '')}",
        f"Abstract: {patent.get('abstract', '')}",
    ]
    if patent.get("title_original"):
        parts.append(f"Original Title: {patent['title_original']}")
    return "\n".join(parts)


# =============================================================================
# HELPERS
# =============================================================================

def _contains_cjk(text):
    """Check if text contains Chinese/Japanese characters."""
    return bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))


def _contains_korean(text):
    """Check if text contains Korean characters."""
    return bool(re.search(r'[\uac00-\ud7af\u1100-\u11ff]', text))


def _detect_language(text):
    """Simple language detection based on character ranges."""
    if _contains_korean(text):
        return "ko"
    if _contains_cjk(text):
        # Distinguish Chinese from Japanese
        # Japanese text often contains hiragana/katakana
        if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
            return "ja"
        return "zh"
    if re.search(r'[\u0900-\u097f]', text):  # Devanagari
        return "hi"
    return "en"


# =============================================================================
# LANDSCAPE VIEW — Extract drug assets from trials, group by drug/company/phase
# =============================================================================

# Known drug name patterns to extract from trial titles and interventions
# Format: regex pattern → (canonical_name, target/MoA)
DRUG_PATTERNS = {
    # GLP-1 / incretin drugs
    r'\b(semaglutide)\b': ("semaglutide", "GLP-1"),
    r'\b(tirzepatide|LY3298176)\b': ("tirzepatide", "GLP-1/GIP"),
    r'\b(liraglutide)\b': ("liraglutide", "GLP-1"),
    r'\b(dulaglutide)\b': ("dulaglutide", "GLP-1"),
    r'\b(exenatide|exendin)\b': ("exenatide", "GLP-1"),
    r'\b(lixisenatide)\b': ("lixisenatide", "GLP-1"),
    r'\b(orforglipron)\b': ("orforglipron", "GLP-1 (oral)"),
    r'\b(retatrutide|LY3437943)\b': ("retatrutide", "GLP-1/GIP/GCGR"),
    r'\b(survodutide|BI 456906)\b': ("survodutide", "GLP-1/GCGR"),
    r'\b(CagriSema|cagrilintide)\b': ("CagriSema", "GLP-1+amylin"),
    r'\b(pemvidutide)\b': ("pemvidutide", "GLP-1/GCGR"),
    r'\b(ecnoglutide|XW003)\b': ("ecnoglutide (XW003)", "GLP-1"),
    r'\b(mazdutide|IBI362)\b': ("mazdutide (IBI362)", "GLP-1/GCGR"),
    r'\b(danuglipron|PF-06882961)\b': ("danuglipron", "GLP-1 (oral)"),
    r'\b(beinaglutide)\b': ("beinaglutide", "GLP-1"),
    r'\b(PB-119)\b': ("PB-119", "GLP-1 (long-acting)"),
    r'\b(PJ009)\b': ("PJ009", "GLP-1"),
    r'\b(HDM1002)\b': ("HDM1002", "GLP-1"),
    r'\b(TG103)\b': ("TG103", "GLP-1"),
    r'\b(DA-30216)\b': ("DA-30216", "GLP-1"),
    r'\b(SY-008)\b': ("SY-008", "GLP-1 (oral)"),
    r'\b(XTL6001)\b': ("XTL6001", "GLP-1"),
    r'\b(ZT006)\b': ("ZT006", "GLP-1"),
    r'\b(DBPR108)\b': ("DBPR108", "DPP-4"),
    r'\b(lotiglipron)\b': ("lotiglipron", "GLP-1 (oral)"),
    r'\b(bimagrumab)\b': ("bimagrumab", "ActRII"),
    r'\b(efpeglenatide)\b': ("efpeglenatide", "GLP-1"),
    r'\b(sitagliptin|[Jj]anuvia)\b': ("sitagliptin", "DPP-4"),
    r'\b(saxagliptin|[Oo]nglyza)\b': ("saxagliptin", "DPP-4"),
    r'\b(glimepiride)\b': ("glimepiride", "SU"),
    r'\b(insulin glargine|[Ll]antus|[Tt]oujeo)\b': ("insulin glargine", "basal insulin"),
    r'\b(insulin degludec|[Tt]resiba)\b': ("insulin degludec", "basal insulin"),
    r'\b(efsitora|LY3209590)\b': ("efsitora alfa", "basal insulin (weekly)"),
    r'\b(HRS-7535)\b': ("HRS-7535 (Hengrui)", "GLP-1/GIP"),
    # PD-1/PD-L1
    r'\b(pembrolizumab|[Kk]eytruda|MK-3475)\b': ("pembrolizumab", "PD-1"),
    r'\b(nivolumab|[Oo]pdivo)\b': ("nivolumab", "PD-1"),
    r'\b(atezolizumab|[Tt]ecentriq)\b': ("atezolizumab", "PD-L1"),
    r'\b(durvalumab|[Ii]mfinzi)\b': ("durvalumab", "PD-L1"),
    r'\b(tislelizumab)\b': ("tislelizumab", "PD-1"),
    r'\b(sintilimab)\b': ("sintilimab", "PD-1"),
    r'\b(camrelizumab)\b': ("camrelizumab", "PD-1"),
    r'\b(toripalimab)\b': ("toripalimab", "PD-1"),
    r'\b(ivonescimab)\b': ("ivonescimab", "PD-1/VEGF bispecific"),
    r'\b(cadonilimab)\b': ("cadonilimab", "PD-1/CTLA-4 bispecific"),
    # ADC
    r'\b([Ee]nhertu|trastuzumab deruxtecan|T-DXd|DS-8201)\b': ("T-DXd (Enhertu)", "HER2 ADC"),
    r'\b(datopotamab deruxtecan|Dato-DXd|DS-1062)\b': ("Dato-DXd", "TROP2 ADC"),
    r'\b(sacituzumab govitecan|[Tt]rodelvy)\b': ("sacituzumab govitecan", "TROP2 ADC"),
    r'\b(enfortumab vedotin|[Pp]adcev)\b': ("enfortumab vedotin", "Nectin-4 ADC"),
    r'\b(mirvetuximab)\b': ("mirvetuximab soravtansine", "FRα ADC"),
    r'\b(SHR-A1811)\b': ("SHR-A1811", "HER2 ADC"),
    r'\b(IBI343)\b': ("IBI343", "CLDN18.2 ADC"),
    # KRAS — US/EU
    r'\b(sotorasib|AMG[- ]?510|[Ll]umakras)\b': ("sotorasib", "KRAS G12C"),
    r'\b(adagrasib|MRTX[- ]?849)\b': ("adagrasib", "KRAS G12C"),
    r'\b(divarasib|GDC[- ]?6036)\b': ("divarasib", "KRAS G12C"),
    r'\b(daraxonrasib|RMC[- ]?6236)\b': ("daraxonrasib", "KRAS multi-select"),
    r'\b(opnurasib|RMC[- ]?6291)\b': ("opnurasib", "KRAS G12C(ON)"),
    r'\b(JDQ443|jabrefonrasib)\b': ("JDQ443", "KRAS G12C"),
    r'\b(glecirasib|JAB[- ]?21822)\b': ("glecirasib", "KRAS G12C"),
    r'\b(fulzerasib|IBI351)\b': ("fulzerasib", "KRAS G12C"),
    # KRAS — China/Asia pipeline
    r'\b(garsorasib|D[- ]?1553)\b': ("garsorasib", "KRAS G12C"),
    r'\b(BG[- ]?68501)\b': ("BG-68501", "KRAS G12C"),
    r'\b(GFH925|AST2818)\b': ("GFH925", "KRAS G12C"),
    r'\b(BI[- ]?1823911)\b': ("BI-1823911", "KRAS G12C tri-complex"),
    r'\b(YL[- ]?15293)\b': ("YL-15293", "KRAS G12C"),
    r'\b(GEC[- ]?215)\b': ("GEC-215", "KRAS G12D"),
    r'\b(ERAS[- ]?801|RMC[- ]?9805)\b': ("ERAS-801", "KRAS G12D"),
    r'\b(HRS[- ]?4642)\b': ("HRS-4642", "KRAS G12D"),
    r'\b(RMC[- ]?4630)\b': ("RMC-4630", "SHP2/KRAS"),
    r'\b(TNO155)\b': ("TNO155", "SHP2/KRAS"),
    r'\b(BBP[- ]?398)\b': ("BBP-398", "SHP2/KRAS"),
    r'\b(KRAS[- ]?G12[CDV])\b': ("KRAS target", "KRAS mutation"),
    # Bispecifics
    r'\b(epcoritamab)\b': ("epcoritamab", "CD3xCD20 bispecific"),
    r'\b(glofitamab)\b': ("glofitamab", "CD3xCD20 bispecific"),
    r'\b(teclistamab)\b': ("teclistamab", "BCMAxCD3 bispecific"),
    r'\b(BNT327)\b': ("BNT327", "PD-L1/VEGF-A bispecific"),
    # BTK
    r'\b(zanubrutinib|[Bb]rukinsa)\b': ("zanubrutinib", "BTK"),
    r'\b(ibrutinib|[Ii]mbruvica)\b': ("ibrutinib", "BTK"),
    r'\b(acalabrutinib|[Cc]alquence)\b': ("acalabrutinib", "BTK"),
    # Neuro
    r'\b(lecanemab|[Ll]eqembi)\b': ("lecanemab", "amyloid-beta"),
    r'\b(donanemab)\b': ("donanemab", "amyloid-beta"),
    r'\b(KarXT|[Cc]obenfy|xanomeline)\b': ("KarXT", "M1/M4 muscarinic"),
    r'\b(cenobamate)\b': ("cenobamate", "NaV/GABA"),
    # I&I
    r'\b(upadacitinib|[Rr]invok)\b': ("upadacitinib", "JAK1"),
    r'\b(dupilumab|[Dd]upixent)\b': ("dupilumab", "IL-4/IL-13"),
    r'\b(secukinumab|[Cc]osentyx)\b': ("secukinumab", "IL-17A"),
    r'\b(risankizumab|[Ss]kyrizi)\b': ("risankizumab", "IL-23"),
    r'\b(efgartigimod|[Vv]yvgart)\b': ("efgartigimod", "FcRn"),
    # Additional ADC drugs (China/Asia pipeline)
    r'\b(disitamab vedotin|RC48)\b': ("disitamab vedotin (RC48)", "HER2 ADC"),
    r'\b(pucotenlimab|HLX10)\b': ("pucotenlimab (HLX10)", "PD-1"),
    r'\b(zolbetuximab|IMAB362)\b': ("zolbetuximab", "CLDN18.2"),
    r'\b(ifinatamab|I-DXd|DS-7300)\b': ("ifinatamab deruxtecan", "B7-H3 ADC"),
    r'\b(telisotuzumab vedotin|ABBV-399)\b': ("telisotuzumab vedotin", "c-Met ADC"),
    r'\b(patritumab deruxtecan|HER3-DXd|U3-1402)\b': ("patritumab deruxtecan", "HER3 ADC"),
    # VEGF/VEGFR
    r'\b(bevacizumab|[Aa]vastin)\b': ("bevacizumab", "VEGF"),
    r'\b(ramucirumab|[Cc]yramza)\b': ("ramucirumab", "VEGFR2"),
    r'\b(lenvatinib|[Ll]envima)\b': ("lenvatinib", "multi-TKI"),
    r'\b(sorafenib|[Nn]exavar)\b': ("sorafenib", "multi-TKI"),
    r'\b(apatinib|rivoceranib)\b': ("apatinib/rivoceranib", "VEGFR2"),
    r'\b(fruquintinib)\b': ("fruquintinib", "VEGFR1/2/3"),
    # EGFR
    r'\b(osimertinib|[Tt]agrisso)\b': ("osimertinib", "EGFR T790M"),
    r'\b(lazertinib)\b': ("lazertinib", "3rd-gen EGFR"),
    r'\b(furmonertinib|AST2818)\b': ("furmonertinib", "3rd-gen EGFR"),
    r'\b(aumolertinib|HS-10296)\b': ("aumolertinib", "3rd-gen EGFR"),
    # JAK / I&I additional
    r'\b(baricitinib|[Oo]lumiant)\b': ("baricitinib", "JAK1/2"),
    r'\b(tofacitinib|[Xx]eljanz)\b': ("tofacitinib", "pan-JAK"),
    r'\b(ruxolitinib|[Jj]akafi)\b': ("ruxolitinib", "JAK1/2"),
    r'\b(deucravacitinib|[Ss]otyktu)\b': ("deucravacitinib", "TYK2"),
    r'\b(adalimumab|[Hh]umira)\b': ("adalimumab", "TNF-alpha"),
    r'\b(infliximab|[Rr]emicade|[Rr]emsima)\b': ("infliximab", "TNF-alpha"),
    r'\b(tocilizumab|[Aa]ctemra)\b': ("tocilizumab", "IL-6R"),
    r'\b(satralizumab)\b': ("satralizumab", "IL-6R"),
    r'\b(guselkumab|[Tt]remfya)\b': ("guselkumab", "IL-23"),
    r'\b(tildrakizumab|[Ii]lumya)\b': ("tildrakizumab", "IL-23"),
    # CDK / other oncology
    r'\b(ribociclib|[Kk]isqali)\b': ("ribociclib", "CDK4/6"),
    r'\b(palbociclib|[Ii]brance)\b': ("palbociclib", "CDK4/6"),
    r'\b(abemaciclib|[Vv]erzenio)\b': ("abemaciclib", "CDK4/6"),
    r'\b(olaparib|[Ll]ynparza)\b': ("olaparib", "PARP"),
    r'\b(niraparib|[Zz]ejula)\b': ("niraparib", "PARP"),
    # FcRn / myasthenia gravis
    r'\b(rozanolixizumab)\b': ("rozanolixizumab", "FcRn"),
    r'\b(nipocalimab)\b': ("nipocalimab", "FcRn"),
    # Atopic Dermatitis / Immunology
    r'\b(tralokinumab|[Aa]dbry|[Aa]dtralza|CAT-354)\b': ("tralokinumab", "IL-13"),
    r'\b(lebrikizumab|[Ee]bglyss|LY3650150)\b': ("lebrikizumab", "IL-13"),
    r'\b(cendakimab|ABT-308|RPC4046)\b': ("cendakimab", "IL-13"),
    r'\b(eblasakimab|ABBV-323)\b': ("eblasakimab", "IL-13R"),
    r'\b(nemolizumab|[Nn]emluvio|CIM331)\b': ("nemolizumab", "IL-31Rα"),
    r'\b(rocatinlimab|AMG[- ]?451|KHK4083)\b': ("rocatinlimab", "OX40"),
    r'\b(amlitelimab|SAR445229|KY1005)\b': ("amlitelimab", "OX40L"),
    r'\b(tezepelumab|[Tt]ezspire|AMG[- ]?157|MEDI9929)\b': ("tezepelumab", "TSLP"),
    r'\b(abrocitinib|[Cc]ibinqo|PF-04965842)\b': ("abrocitinib", "JAK1"),
    r'\b(KT-?621)\b': ("KT-621", "STAT6 degrader"),
    r'\b(rezpegaldesleukin|SAR444336|THOR-707)\b': ("rezpegaldesleukin", "IL-2 mutein"),
    r'\b(itepekimab|REGN3500)\b': ("itepekimab", "IL-33"),
    r'\b(astegolimab|AMG[- ]?282)\b': ("astegolimab", "IL-33"),
    r'\b(dilexit|ASLAN004)\b': ("dilexit", "IL-13Rα1"),
    r'\b(benralizumab|[Ff]asenra)\b': ("benralizumab", "IL-5Rα"),
    r'\b(mepolizumab|[Nn]ucala)\b': ("mepolizumab", "IL-5"),
    r'\b(omalizumab|[Xx]olair)\b': ("omalizumab", "IgE"),
    r'\b(bermekimab)\b': ("bermekimab", "IL-1α"),
    r'\b(spesolimab|[Ss]pexion)\b': ("spesolimab", "IL-36R"),
    r'\b(bimekizumab|[Bb]imzelx)\b': ("bimekizumab", "IL-17A/F"),
    r'\b(ixekizumab|[Tt]altz)\b': ("ixekizumab", "IL-17A"),
    r'\b(delgocitinib)\b': ("delgocitinib", "pan-JAK (topical)"),
    r'\b(rademikibart|CBP-201)\b': ("rademikibart", "IL-4Rα"),
    r'\b(CM310|datrecitinib)\b': ("CM310/datrecitinib", "IL-4Rα"),
    r'\b(tapinarof|[Vv]tama)\b': ("tapinarof", "AhR agonist"),
    r'\b(roflumilast)\b': ("roflumilast", "PDE4 (topical)"),
    r'\b(difamilast|MOH[- ]?22)\b': ("difamilast", "PDE4 (topical)"),
    r'\b(tilrekotide)\b': ("tilrekotide", "TSLP peptide"),
    # Patent-notable AD assets
    r'\b(BM512)\b': ("BM512", "TSLP"),
    r'\b(bosakitug)\b': ("bosakitug", "TSLP"),
    r'\b(EVO301)\b': ("EVO301", "IL-18"),
    r'\b(temtokibart)\b': ("temtokibart", "IL-22"),
    r'\b(galvokimig)\b': ("galvokimig", "IL-17"),
    r'\b(CMK-?389)\b': ("CMK-389", "IL-18"),
    r'\b(aletektug)\b': ("aletektug", "IL-18"),
}

# Phase normalization
PHASE_RANK = {
    "PHASE4": 5, "PHASE3": 4, "PHASE2, PHASE3": 3.5, "PHASE2": 3,
    "PHASE1, PHASE2": 2.5, "PHASE1": 2, "EARLY_PHASE1": 1.5, "NA": 1, "": 0,
}


def build_landscape(target_or_query, region="all", max_trials=200, use_llm=False, use_patents=False):
    """
    Build a drug asset landscape from global trial data + optional patent search.

    Pulls trials from ClinicalTrials.gov API v2, extracts drug names via:
      1. DRUG_PATTERNS regex matching (known drugs)
      2. Direct intervention name extraction (unknown/novel drugs)
      3. Optional LLM extraction for remaining ambiguous trials
      4. Optional patent search for preclinical/early-stage assets

    Args:
        target_or_query: e.g., "GLP-1", "ADC", "PD-1", "KRAS", "Atopic Dermatitis"
        region: "all", "china", "korea", "japan", "india", "europe"
        max_trials: Max trials to fetch
        use_llm: If True, use Claude to extract drug names from ambiguous trials
        use_patents: If True, also search patent databases for early-stage assets

    Returns:
        Dict with landscape data grouped by drug asset
    """
    print(f"\n{'='*80}")
    print(f"  DRUG ASSET LANDSCAPE: {target_or_query}")
    print(f"  Region: {region}")
    print(f"{'='*80}\n")

    # Step 1: Fetch trials
    print("  Step 1: Fetching global trial data...")
    trials = search_trials_global(target_or_query, region=region, max_results=max_trials)

    # For targets like KRAS that are rarely in the intervention field,
    # also do a broader term search to capture trials mentioning the target
    # in titles, conditions, or keywords.
    TARGET_KEYWORDS = {"KRAS", "BRAF", "EGFR", "ALK", "ROS1", "MET", "HER2", "RAS", "SHP2", "STK11"}
    if target_or_query.upper() in TARGET_KEYWORDS:
        print(f"  [Broadening search] {target_or_query} is a gene target — also searching by term...")
        broader = search_trials_by_term(target_or_query, region=region, max_results=max_trials)
        existing = {t["trial_id"] for t in trials}
        added = 0
        for t in broader:
            if t["trial_id"] not in existing:
                trials.append(t)
                existing.add(t["trial_id"])
                added += 1
        if added:
            print(f"  [Broadening] Added {added} additional trials from term search")

    # Also do country-specific search for targeted regions
    region_country_map = {
        "china": "China", "korea": "Korea, Republic of",
        "japan": "Japan", "india": "India",
    }
    if region in region_country_map:
        extra = search_trials_by_country(target_or_query, region_country_map[region], max_results=50)
        existing = {t["trial_id"] for t in trials}
        trials.extend(t for t in extra if t["trial_id"] not in existing)
    elif region == "all":
        # For "all", also fetch from top pharma countries specifically
        for country in ["China", "Japan", "Korea, Republic of"]:
            extra = search_trials_by_country(target_or_query, country, max_results=30)
            existing = {t["trial_id"] for t in trials}
            trials.extend(t for t in extra if t["trial_id"] not in existing)

    print(f"  Total trials fetched: {len(trials)}\n")

    # Step 1b: Optional patent search for preclinical/early-stage assets
    patent_assets = {}
    if use_patents:
        print("  Step 1b: Searching global patent databases...")
        try:
            patents = search_patents_lens(target_or_query, max_results=50)
            print(f"  Found {len(patents)} patent filings")

            for patent in patents:
                title = patent.get("title", "")
                # Try to extract a drug name from patent title using same patterns
                for pattern, (drug_name, moa) in DRUG_PATTERNS.items():
                    if re.search(pattern, title, re.IGNORECASE):
                        if drug_name not in patent_assets:
                            patent_assets[drug_name] = {
                                "drug_name": drug_name,
                                "target_moa": moa,
                                "sponsor": patent.get("applicant", ""),
                                "highest_phase": "Preclinical/Patent",
                                "highest_phase_rank": 0.5,
                                "trials": [],
                                "countries": set(),
                                "indications": set(),
                                "active_trials": 0,
                                "total_trials": 0,
                                "patent_ids": [],
                                "source": "patent_search",
                            }
                        patent_assets[drug_name]["patent_ids"].append(
                            patent.get("id", patent.get("patent_number", ""))
                        )
                        jurisdictions = patent.get("jurisdictions", patent.get("country", ""))
                        if isinstance(jurisdictions, list):
                            patent_assets[drug_name]["countries"].update(jurisdictions)
                        elif jurisdictions:
                            patent_assets[drug_name]["countries"].add(jurisdictions)
                        break

            # Also try extracting code names from patent titles
            for patent in patents:
                title = patent.get("title", "")
                code_matches = re.findall(
                    r'\b([A-Z]{1,5}[\s-]?\d{3,6}[A-Z]?)\b', title
                )
                for code in code_matches:
                    code = code.strip()
                    if code not in patent_assets and len(code) >= 4:
                        patent_assets[code] = {
                            "drug_name": code,
                            "target_moa": f"Patent-disclosed ({target_or_query})",
                            "sponsor": patent.get("applicant", ""),
                            "highest_phase": "Preclinical/Patent",
                            "highest_phase_rank": 0.5,
                            "trials": [],
                            "countries": set(),
                            "indications": set(),
                            "active_trials": 0,
                            "total_trials": 0,
                            "patent_ids": [patent.get("id", "")],
                            "source": "patent_search",
                        }

            print(f"  Patent search found {len(patent_assets)} drug assets")
        except Exception as e:
            print(f"  [Patent search] Error: {e}")

    # Step 2: Extract drug assets from trials
    print("  Step 2: Extracting drug assets...")
    assets = {}  # drug_name → asset dict

    unmatched_trials = []

    for trial in trials:
        # Search in title + interventions
        search_text = f"{trial.get('title', '')} {trial.get('interventions', '')}"

        matched = False
        for pattern, (drug_name, moa) in DRUG_PATTERNS.items():
            if re.search(pattern, search_text, re.IGNORECASE):
                matched = True
                if drug_name not in assets:
                    assets[drug_name] = {
                        "drug_name": drug_name,
                        "target_moa": moa,
                        "sponsor": "",
                        "highest_phase": "",
                        "highest_phase_rank": 0,
                        "trials": [],
                        "countries": set(),
                        "indications": set(),
                        "active_trials": 0,
                        "total_trials": 0,
                    }

                asset = assets[drug_name]
                asset["trials"].append(trial["trial_id"])
                asset["total_trials"] += 1

                # Track highest phase
                phase = trial.get("phase", "")
                phase_rank = PHASE_RANK.get(phase, 0)
                if phase_rank > asset["highest_phase_rank"]:
                    asset["highest_phase"] = phase
                    asset["highest_phase_rank"] = phase_rank

                # Track sponsor (use most common)
                if trial.get("sponsor") and not asset["sponsor"]:
                    asset["sponsor"] = trial["sponsor"]

                # Track countries
                for country in trial.get("countries", "").split(", "):
                    country = country.strip()
                    if country:
                        asset["countries"].add(country)

                # Track indications
                for cond in trial.get("conditions", "").split(", "):
                    cond = cond.strip()
                    if cond and len(cond) > 3:
                        asset["indications"].add(cond)

                # Count active trials
                if trial.get("status") in ("RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING"):
                    asset["active_trials"] += 1

        if not matched:
            unmatched_trials.append(trial)

    # Step 2a: Extract novel drugs directly from intervention names (no regex needed)
    direct_extracted = 0
    if unmatched_trials:
        print(f"\n  Step 2a: Extracting drugs directly from {len(unmatched_trials)} unmatched trial interventions...")
        direct_assets = _extract_interventions_direct(unmatched_trials, set(assets.keys()))
        for drug_name, asset_data in direct_assets.items():
            if drug_name not in assets:
                assets[drug_name] = asset_data
                direct_extracted += 1
            else:
                # Merge into existing
                existing = assets[drug_name]
                existing["trials"].extend(asset_data["trials"])
                existing["total_trials"] += asset_data["total_trials"]
                existing["countries"].update(asset_data["countries"])
                existing["indications"].update(asset_data["indications"])
                existing["active_trials"] += asset_data["active_trials"]
        print(f"  Direct extraction found {direct_extracted} novel drug assets")
        # Update unmatched: remove trials that were matched by direct extraction
        matched_trial_ids = set()
        for a in direct_assets.values():
            matched_trial_ids.update(a["trials"])
        unmatched_trials = [t for t in unmatched_trials if t["trial_id"] not in matched_trial_ids]
        print(f"  Remaining unmatched trials: {len(unmatched_trials)}")

    # Step 2b: Use Claude to extract drugs from remaining unmatched trials (optional)
    llm_extracted = 0
    if use_llm and unmatched_trials and ANTHROPIC_API_KEY:
        print(f"\n  Step 2b: Using Claude to extract drugs from {len(unmatched_trials)} unmatched trials...")
        llm_assets = _extract_drugs_with_llm(unmatched_trials, target_or_query)
        for drug_name, asset_data in llm_assets.items():
            if drug_name not in assets:
                assets[drug_name] = asset_data
                llm_extracted += 1
            else:
                # Merge into existing
                existing = assets[drug_name]
                existing["trials"].extend(asset_data["trials"])
                existing["total_trials"] += asset_data["total_trials"]
                existing["countries"].update(asset_data["countries"])
                existing["indications"].update(asset_data["indications"])
                existing["active_trials"] += asset_data["active_trials"]

        print(f"  Claude extracted {llm_extracted} additional drug assets")

    # Step 2c: Merge patent-discovered assets (if any)
    patent_only = 0
    if patent_assets:
        for drug_name, patent_data in patent_assets.items():
            if drug_name not in assets:
                assets[drug_name] = patent_data
                patent_only += 1
            else:
                # Add patent info to existing clinical asset
                existing = assets[drug_name]
                if "patent_ids" not in existing:
                    existing["patent_ids"] = []
                existing["patent_ids"].extend(patent_data.get("patent_ids", []))
                existing["countries"].update(patent_data.get("countries", set())
                    if isinstance(patent_data.get("countries"), set)
                    else set(patent_data.get("countries", [])))
        if patent_only:
            print(f"\n  Step 2c: {patent_only} additional assets found only in patent filings (preclinical)")

    # Step 3: Sort and format
    asset_list = sorted(assets.values(), key=lambda a: (-a["highest_phase_rank"], -a["total_trials"]))

    # Convert sets to sorted lists for display
    for asset in asset_list:
        asset["countries"] = sorted(asset["countries"])
        asset["indications"] = sorted(asset["indications"])[:5]  # top 5

    # Step 4: Print landscape
    print(f"\n{'='*80}")
    print(f"  LANDSCAPE: {target_or_query.upper()} — {len(asset_list)} drug assets found")
    print(f"  From {len(trials)} clinical trials across {region}")
    print(f"{'='*80}\n")

    if not asset_list:
        print("  No drug assets extracted. Try --landscape-llm for Claude-powered extraction.")
        print(f"  ({len(unmatched_trials)} trials could not be matched to known drugs)")
        return {"assets": [], "unmatched": len(unmatched_trials), "total_trials": len(trials)}

    # Header
    print(f"  {'Drug':30s} {'Target/MoA':22s} {'Phase':10s} {'Trials':7s} {'Active':7s} {'Sponsor':30s} {'Countries'}")
    print(f"  {'─'*140}")

    for asset in asset_list:
        countries_str = ", ".join(asset["countries"][:3])
        if len(asset["countries"]) > 3:
            countries_str += f" +{len(asset['countries'])-3}"

        phase_display = asset["highest_phase"].replace("PHASE", "Ph").replace(", ", "/")
        if not phase_display:
            phase_display = "N/A"

        print(f"  {asset['drug_name']:30s} "
              f"{asset['target_moa']:22s} "
              f"{phase_display:10s} "
              f"{asset['total_trials']:>5d}  "
              f"{asset['active_trials']:>5d}  "
              f"{asset['sponsor'][:28]:30s} "
              f"{countries_str}")

    # Region breakdown
    all_countries = {}
    for asset in asset_list:
        for c in asset["countries"]:
            all_countries[c] = all_countries.get(c, 0) + 1

    print(f"\n  Region breakdown ({len(all_countries)} countries):")
    for country, count in sorted(all_countries.items(), key=lambda x: -x[1])[:10]:
        print(f"    {country}: {count} drug assets in development")

    # Summary stats
    print(f"\n  Summary:")
    print(f"    Total drug assets:    {len(asset_list)}")
    print(f"    Phase 3+:             {sum(1 for a in asset_list if a['highest_phase_rank'] >= 4)}")
    print(f"    Phase 2:              {sum(1 for a in asset_list if 2.5 <= a['highest_phase_rank'] < 4)}")
    print(f"    Phase 1:              {sum(1 for a in asset_list if 1 <= a['highest_phase_rank'] < 2.5)}")
    print(f"    Auto-discovered:      {direct_extracted} (from intervention fields)")
    if llm_extracted:
        print(f"    LLM-extracted:        {llm_extracted} (from Claude)")
    print(f"    Unmatched trials:     {len(unmatched_trials)} (use --landscape-llm to extract)")
    print(f"    Total trials scanned: {len(trials)}")

    # Return structured data
    return {
        "query": target_or_query,
        "region": region,
        "assets": asset_list,
        "total_trials": len(trials),
        "unmatched_trials": len(unmatched_trials),
        "timestamp": datetime.now().isoformat(),
    }


def _extract_interventions_direct(trials, already_found):
    """
    Extract drug assets DIRECTLY from ClinicalTrials.gov intervention names,
    without needing regex patterns. This catches novel/unknown drugs that
    aren't in DRUG_PATTERNS at all.

    Filters out non-drug interventions (placebo, standard of care, procedures,
    devices, generic class names) and returns a dict of newly discovered assets.

    Args:
        trials: List of trial dicts (unmatched by DRUG_PATTERNS)
        already_found: Set of drug names already discovered (to avoid duplicates)

    Returns:
        Dict of drug_name → asset dict
    """
    # ── INN (International Nonproprietary Name) suffix patterns ──
    # These are WHO-assigned naming stems that mark real pharmaceutical compounds.
    # If a word ends with one of these, it's almost certainly a drug.
    INN_PATTERN = re.compile(
        r'^[a-z].*(?:'
        # Monoclonal antibodies
        r'mab|zumab|ximab|mumab|tumab|lumab|numab|rumab|'
        # Kinase inhibitors
        r'tinib|nib|ciclib|sertib|metinib|ratinib|citinib|letinib|lisib|'
        # Peptides & receptor agonists
        r'tide|glutide|reotide|nakin|relbin|'
        # Cardiovascular / metabolic
        r'pril|sartan|olol|statin|vastatin|prazole|gliptin|gliflozin|'
        # Anti-infectives
        r'cillin|floxacin|mycin|cycline|bactam|fungin|vudine|virin|'
        # Anti-coagulants / respiratory
        r'parin|lukast|'
        # Other stems (newer naming)
        r'tug|kibart|kecept|nermin|ceptin|platin|rubicin|'
        r'fenacin|lukine|poetin|tropin|fibatide|gatran|'
        # ADC / fusion / bispecific suffixes
        r'vedotin|mertansine|tansine|ozogamicin|ravtansine|'
        r'fusp|cept'
        r')$',
        re.IGNORECASE
    )

    # ── Code name patterns (e.g., KT-621, PF-06939926, BM512) ──
    # Pharma companies use alphanumeric codes for experimental compounds.
    CODE_NAME_PATTERN = re.compile(
        r'^[A-Z]{1,5}[\-]?\d{2,7}[A-Z]?$|'          # KT-621, PJ009, BM512, PF-06939926
        r'^[A-Z]{2,6}[\-]\d{2,}(?:[\-]\d+)?$|'       # ABT-494, SHR-1819, BAY81-2996
        r'^[A-Z]\d{4,}$',                             # E7080
        re.IGNORECASE
    )

    # ── Known non-drug terms — broad blocklist ──
    # Clinical trials list all sorts of non-drug "interventions" that we need to skip.
    SKIP_LOWER = {
        # Controls & placebos
        "placebo", "sham", "saline", "vehicle", "no treatment", "no intervention",
        "standard of care", "standard care", "best supportive care", "bsc",
        "soc", "usual care", "active comparator", "comparator", "control group",
        # Procedures, devices, diagnostics
        "surgery", "radiation", "radiotherapy", "phototherapy", "cryotherapy",
        "biopsy", "biopsies", "transplant", "dialysis", "device", "laser",
        "ultrasound", "blood draw", "blood test", "clinical examination",
        "phone call", "phone calls", "telemedicine", "telehealth",
        # Behavioral / educational
        "dietary supplement", "supplement", "vitamin", "probiotic", "prebiotic",
        "exercise", "behavioral", "cognitive", "counseling", "psychotherapy",
        "physical therapy", "rehabilitation", "education", "observation",
        "diagnostic test", "questionnaire", "survey", "psychoeducation",
        "routine care", "extended information", "information reports",
        # Dermatology-specific non-drugs (from AD trial noise)
        "emollient", "emollient cream", "moisturizer", "sunscreen",
        "topical corticosteroid", "topical steroid",
        "aquaphor", "aquaphor ointment", "cetaphil", "cetaphil cream",
        "cetaphil restoraderm", "eucerin", "vaseline", "petroleum jelly",
        "wool clothing", "cotton clothing", "dry smear", "wet wrap",
        # Food / dietary
        "mare's milk", "breast milk", "formula", "sunflower oil",
        "coconut oil", "fish oil", "olive oil", "evening primrose oil",
        "dha+epa", "omega-3", "zinc", "iron",
        # Generic drug class names (too vague to be a specific asset)
        "corticosteroid", "antibiotic", "antifungal", "anti-inflammatory",
        "analgesic", "bronchodilator", "diuretic", "antihistamine",
        "immunosuppressant", "statin", "nsaid", "small molecules",
        # Procedures / study arms
        "naet procedures", "conventional treatment", "routine care/education",
        "psychoeducation/coping prevention",
        # Established generics (not novel assets worth tracking)
        "prednisolone", "prednisone", "hydrocortisone", "betamethasone",
        "fluticasone", "mometasone", "clobetasol",
        "pimecrolimus", "tacrolimus", "ciclosporin", "ciclosporin a",
        "cyclosporine", "methotrexate", "azathioprine", "mycophenolate",
        "hydroxychloroquine", "dapsone", "gentamicin", "mupirocin",
        "cetirizine", "loratadine", "fexofenadine", "diphenhydramine",
        "chlorpheniramine", "chlorpheniramine-codeine",
        # Study logistics (not interventions at all)
        "animal allergy", "non-animal allergy", "dna reports",
        "panels", "eswabs", "galenico",
    }

    # ── Additional pattern-based skips ──
    SKIP_PATTERNS = [
        re.compile(r'^\d+(\.\d+)?\s*(mg|ml|mcg|ug|g|%|units?|iu)', re.I),  # Dosages
        re.compile(r'^(low|medium|high)\s+dose', re.I),                      # Dose arms
        re.compile(r'®|©|™', re.I),                                          # Brand symbols (OTC products)
        re.compile(r'\b(cream|ointment|lotion|gel|foam|patch|shampoo)\b', re.I),  # Formulations
        re.compile(r'\b(group|arm|cohort|panel|phase)\b', re.I),             # Study arms
        re.compile(r'\b(procedure|examination|assessment|evaluation)\b', re.I),
        re.compile(r'\b(call|visit|session|interview|report)\b', re.I),      # Study logistics
    ]

    assets = {}
    already_lower = {d.lower() for d in already_found}

    for trial in trials:
        interventions_str = trial.get("interventions", "")
        if not interventions_str:
            continue

        # Split on comma or semicolon
        raw_names = re.split(r'[,;]', interventions_str)

        for raw in raw_names:
            name = raw.strip()
            if not name or len(name) < 3 or len(name) > 60:
                continue

            name_lower = name.lower().strip()

            # Skip known non-drug terms (exact match)
            if name_lower in SKIP_LOWER:
                continue

            # Skip if it's just a number or dosage
            if any(p.match(name) for p in SKIP_PATTERNS):
                continue

            # Skip multi-word descriptions (4+ words = almost never a drug name)
            if len(name.split()) >= 4:
                continue

            # Skip if already found via DRUG_PATTERNS
            if name_lower in already_lower:
                continue

            # ── STRICT acceptance: only INN names or code names ──
            is_drug = False
            clean_name = name
            first_word = name.split()[0].strip('()"\'')

            # 1. INN naming pattern (e.g., nemolizumab, abrocitinib, rocatinlimab)
            if INN_PATTERN.match(first_word):
                is_drug = True
                clean_name = first_word

            # 2. Pharma code name (e.g., KT-621, SHR-1819, PF-07832837)
            elif CODE_NAME_PATTERN.match(first_word):
                is_drug = True
                clean_name = first_word

            # 3. Known branded names ending in common Rx suffixes
            #    (catches things like "Jaungo" which is a Korean herbal Rx)
            #    BUT only if the trial is Phase 1+ (not NA/observational)
            elif (len(name.split()) == 1 and len(name) >= 4
                  and name[0].isupper() and name[1:].islower()
                  and trial.get("phase", "") and trial["phase"] != "NA"
                  and not any(p.search(name) for p in SKIP_PATTERNS)):
                is_drug = True
                clean_name = name

            if not is_drug:
                continue

            # Additional pattern-based rejection on the clean name
            if any(p.search(clean_name) for p in SKIP_PATTERNS):
                continue

            # Normalize
            clean_name = clean_name.strip().strip('"\'()')

            if clean_name.lower() in already_lower or len(clean_name) < 3:
                continue

            # Create or update asset entry
            if clean_name not in assets:
                assets[clean_name] = {
                    "drug_name": clean_name,
                    "target_moa": "Unknown (auto-discovered)",
                    "sponsor": "",
                    "highest_phase": "",
                    "highest_phase_rank": 0,
                    "trials": [],
                    "countries": set(),
                    "indications": set(),
                    "active_trials": 0,
                    "total_trials": 0,
                    "source": "intervention_extraction",  # Flag as auto-discovered
                }

            asset = assets[clean_name]
            asset["trials"].append(trial["trial_id"])
            asset["total_trials"] += 1

            # Track phase
            phase = trial.get("phase", "")
            phase_rank = PHASE_RANK.get(phase, 0)
            if phase_rank > asset["highest_phase_rank"]:
                asset["highest_phase"] = phase
                asset["highest_phase_rank"] = phase_rank

            # Track sponsor
            if trial.get("sponsor") and not asset["sponsor"]:
                asset["sponsor"] = trial["sponsor"]

            # Track countries
            for country in trial.get("countries", "").split(", "):
                country = country.strip()
                if country:
                    asset["countries"].add(country)

            # Track indications
            for cond in trial.get("conditions", "").split(", "):
                cond = cond.strip()
                if cond and len(cond) > 3:
                    asset["indications"].add(cond)

            # Count active trials
            if trial.get("status") in ("RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING"):
                asset["active_trials"] += 1

            already_lower.add(clean_name.lower())

    return assets


def _extract_drugs_with_llm(trials, query_context, batch_size=20):
    """
    Use Claude to extract drug names from trial titles/interventions that
    couldn't be matched by regex patterns.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    assets = {}

    # Process in batches
    for i in range(0, len(trials), batch_size):
        batch = trials[i:i + batch_size]

        trial_text = ""
        for j, trial in enumerate(batch):
            trial_text += f"\n{j+1}. [{trial['trial_id']}] {trial['title']}\n"
            trial_text += f"   Interventions: {trial.get('interventions', 'N/A')}\n"
            trial_text += f"   Sponsor: {trial.get('sponsor', 'N/A')}\n"
            trial_text += f"   Phase: {trial.get('phase', 'N/A')}\n"

        prompt = f"""Extract drug names from these clinical trials related to "{query_context}".
For each drug found, provide:
- drug_name (INN or code name, e.g., "semaglutide" or "PJ009")
- target_moa (mechanism, e.g., "GLP-1" or "KRAS G12C")
- trial_numbers (which trial numbers from the list, as integers)

ONLY extract actual investigational drugs. Skip:
- Generic descriptions like "GLP-1 receptor agonist" without a specific drug name
- Placebo, lifestyle interventions, diet, exercise
- Standard of care comparators unless they're the primary drug being studied

TRIALS:
{trial_text}

Return JSON array:
[{{"drug_name": "...", "target_moa": "...", "trial_numbers": [1, 3]}}]

If no drugs can be extracted, return: []"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            result_text = response.content[0].text

            # Parse JSON
            json_match = re.search(r'\[[\s\S]*?\]', result_text)
            if json_match:
                extracted = json.loads(json_match.group())
                for drug in extracted:
                    drug_name = drug.get("drug_name", "")
                    if not drug_name or len(drug_name) < 2:
                        continue

                    trial_nums = drug.get("trial_numbers", [])
                    matched_trials = [batch[n-1] for n in trial_nums if 0 < n <= len(batch)]

                    if drug_name not in assets:
                        assets[drug_name] = {
                            "drug_name": drug_name,
                            "target_moa": drug.get("target_moa", ""),
                            "sponsor": "",
                            "highest_phase": "",
                            "highest_phase_rank": 0,
                            "trials": [],
                            "countries": set(),
                            "indications": set(),
                            "active_trials": 0,
                            "total_trials": 0,
                        }

                    asset = assets[drug_name]
                    for trial in matched_trials:
                        asset["trials"].append(trial["trial_id"])
                        asset["total_trials"] += 1

                        phase = trial.get("phase", "")
                        phase_rank = PHASE_RANK.get(phase, 0)
                        if phase_rank > asset["highest_phase_rank"]:
                            asset["highest_phase"] = phase
                            asset["highest_phase_rank"] = phase_rank

                        if trial.get("sponsor") and not asset["sponsor"]:
                            asset["sponsor"] = trial["sponsor"]

                        for country in trial.get("countries", "").split(", "):
                            if country.strip():
                                asset["countries"].add(country.strip())

                        for cond in trial.get("conditions", "").split(", "):
                            if cond.strip() and len(cond.strip()) > 3:
                                asset["indications"].add(cond.strip())

                        if trial.get("status") in ("RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING"):
                            asset["active_trials"] += 1

        except Exception as e:
            print(f"    [LLM Extract] Error: {e}")

        time.sleep(0.5)  # rate limit

    return assets


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="SatyaBio Global Drug Asset Discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --landscape --target "GLP-1"                 Drug asset landscape (THE KEY FEATURE)
  %(prog)s --landscape --target "ADC" --region china     ADC landscape, China focus
  %(prog)s --landscape-llm --target "PD-1"              Landscape + Claude extraction
  %(prog)s --landscape-patents --target "KRAS"          Landscape + patent search (preclinical)
  %(prog)s --trials --target "GLP-1"                    Raw trial search
  %(prog)s --trials --target "GLP-1" --region china     China-specific trials
  %(prog)s --patents --query "KRAS inhibitor"           Search global patents
  %(prog)s --full --target "PD-1" --region all          Full discovery pipeline
  %(prog)s --companies                                  List tracked global companies
        """,
    )
    parser.add_argument("--target", type=str, help="Drug target to search (e.g., GLP-1, PD-1, KRAS)")
    parser.add_argument("--query", type=str, help="Free-text search query")
    parser.add_argument("--region", type=str, default="all",
                        choices=["all", "china", "korea", "japan", "india", "europe"],
                        help="Region to search")
    parser.add_argument("--landscape", action="store_true", help="Build drug asset landscape (grouped by drug)")
    parser.add_argument("--landscape-llm", action="store_true", help="Landscape with Claude-powered extraction")
    parser.add_argument("--landscape-patents", action="store_true", help="Landscape + patent search for preclinical assets")
    parser.add_argument("--trials", action="store_true", help="Search clinical trial registries only")
    parser.add_argument("--patents", action="store_true", help="Search patent databases only")
    parser.add_argument("--ir", action="store_true", help="Scrape regional IR pages only")
    parser.add_argument("--full", action="store_true", help="Run full discovery pipeline")
    parser.add_argument("--novel", action="store_true", help="Find novel assets not in our database")
    parser.add_argument("--companies", action="store_true", help="List tracked global companies")
    parser.add_argument("--dry-run", action="store_true", help="Preview without embedding")
    parser.add_argument("--max", type=int, default=50, help="Max results per source")
    args = parser.parse_args()

    if args.companies:
        by_region = {}
        for ticker, info in GLOBAL_BIOTECH_UNIVERSE.items():
            by_region.setdefault(info["region"], []).append((ticker, info))

        for region, companies in sorted(by_region.items()):
            print(f"\n  {region.upper()} ({len(companies)} companies)")
            print(f"  {'─'*60}")
            for ticker, info in companies:
                assets = ", ".join(info.get("key_assets", [])[:2])
                print(f"    {ticker:15s}  {info['name']:35s}")
                print(f"                   Key: {assets}")
        print(f"\n  Total: {len(GLOBAL_BIOTECH_UNIVERSE)} companies tracked globally")
        return

    search_term = args.target or args.query
    if not search_term and not args.companies:
        parser.print_help()
        return

    if args.landscape or args.landscape_llm or args.landscape_patents:
        # THE KEY FEATURE: Drug asset landscape view
        use_llm = args.landscape_llm
        use_patents = args.landscape_patents
        max_trials = args.max * 4 if args.max else 200  # fetch more trials for better coverage
        result = build_landscape(
            search_term, region=args.region,
            max_trials=max_trials, use_llm=use_llm, use_patents=use_patents,
        )

        # Save to JSON
        if result and result.get("assets"):
            output_file = f"landscape_{search_term.replace(' ', '_')}_{args.region}_{datetime.now().strftime('%Y%m%d')}.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2, default=str)
            print(f"\n  Landscape saved to {output_file}")
        return

    if args.trials:
        # Trial search only — uses ClinicalTrials.gov API v2
        trials = search_trials_global(search_term, region=args.region, max_results=args.max)

        # Also search by specific country for the region
        region_country_map = {
            "china": "China", "korea": "Korea, Republic of",
            "japan": "Japan", "india": "India",
        }
        if args.region in region_country_map:
            country_trials = search_trials_by_country(search_term, region_country_map[args.region])
            existing = {t["trial_id"] for t in trials}
            trials.extend(t for t in country_trials if t["trial_id"] not in existing)

        print(f"\n  {'Trial ID':15s} {'Phase':12s} {'Status':15s} {'Countries':20s} {'Title'}")
        print(f"  {'─'*120}")
        for trial in trials:
            countries_short = trial['countries'][:18] if trial['countries'] else ""
            print(f"  {trial['trial_id']:15s} {trial['phase']:12s} {trial['status']:15s} {countries_short:20s} {trial['title'][:55]}")

        # Show region breakdown
        if trials:
            print(f"\n  Region breakdown:")
            by_country = {}
            for t in trials:
                for c in t["countries"].split(", "):
                    c = c.strip()
                    if c:
                        by_country[c] = by_country.get(c, 0) + 1
            for country, count in sorted(by_country.items(), key=lambda x: -x[1])[:10]:
                print(f"    {country}: {count} trials")

    elif args.patents:
        # Patent search — tries Lens.org → EPO OPS → BigQuery
        countries_map = {
            "all": ["CN", "KR", "JP", "IN", "EP", "WO"],
            "china": ["CN"], "korea": ["KR"], "japan": ["JP"],
            "india": ["IN"], "europe": ["EP", "DE", "FR", "GB"],
        }
        patent_countries = countries_map.get(args.region, ["CN", "KR", "JP", "IN"])
        patents = search_patents_lens(search_term, countries=patent_countries, max_results=args.max)

        print(f"\n  {'Patent #':20s} {'Country':8s} {'Assignee':30s} {'Title'}")
        print(f"  {'─'*110}")
        for patent in patents:
            print(f"  {patent.get('publication_number', ''):20s} "
                  f"{patent.get('country_code', ''):8s} "
                  f"{patent.get('assignee', '')[:28]:30s} "
                  f"{patent.get('title', '')[:50]}")

    elif args.ir:
        # IR scrape only
        for ticker, info in GLOBAL_BIOTECH_UNIVERSE.items():
            if args.region != "all" and info.get("region") != args.region:
                continue
            scrape_regional_ir(ticker, info)

    elif args.full or args.novel:
        # Full pipeline
        results = run_full_pipeline(
            target=args.target,
            query=args.query,
            region=args.region,
            max_results=args.max,
            dry_run=args.dry_run,
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
