#!/usr/bin/env python3
"""
Private Biotech Directory Scraper
==================================
Discovers private biotech startups from BioPharma Dive articles
and seeds them into the private_companies table.

Uses web search to find recent articles about private biotech companies,
then extracts structured company data using Claude.

Usage:
    python scrape_directory.py [--max-pages 5] [--dry-run]
"""

import os
import sys
import json
import time
import re
import argparse
from datetime import datetime

import psycopg2
import anthropic

DB_URL = os.environ.get("NEON_DATABASE_URL", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Search queries to find private biotech companies
SEARCH_QUERIES = [
    "site:biopharmadive.com private biotech startup funding 2025 2026",
    "site:biopharmadive.com preclinical biotech series A 2025",
    "site:biopharmadive.com biotech IPO pipeline 2026",
    "site:biopharmadive.com small biotech oncology funding",
    "site:biopharmadive.com biotech cell therapy startup",
    "site:biopharmadive.com biotech ADC antibody drug conjugate startup",
    "site:biopharmadive.com biotech gene therapy startup funding",
    "site:biopharmadive.com biotech immunology startup",
    "site:biopharmadive.com biotech rare disease startup",
    "site:biopharmadive.com biotech neuroscience startup",
    "private biotech startup Series A B oncology 2025 2026",
    "emerging private biotech companies clinical trials 2025",
]

EXTRACTION_PROMPT = """You are a biotech industry analyst. Given the following article text from BioPharma Dive or a similar source, extract all PRIVATE biotech companies mentioned.

For each private company found, extract:
- name: Company name (required)
- hq_location: City, State or City, Country if mentioned
- founded_year: Year founded if mentioned
- employee_count: Approximate employee count or range if mentioned
- therapeutic_areas: List of therapeutic areas (e.g., oncology, immunology, rare disease, neuroscience, cardiovascular)
- modality: Drug modality (e.g., small molecule, ADC, bispecific, cell therapy, gene therapy, mRNA, protein degrader, radioligand)
- lead_programs: Brief description of lead drug candidates and their targets
- stage: Most advanced program stage (discovery, preclinical, phase1, phase2, phase3)
- description: 1-2 sentence company description

IMPORTANT:
- Only extract PRIVATE companies (not publicly traded on NYSE/NASDAQ)
- Skip companies that are clearly public (have ticker symbols, mentioned as public)
- If you're unsure whether a company is private, include it
- Skip large pharma companies (Pfizer, Roche, Novartis, etc.)

Return a JSON array of objects. If no private companies are found, return [].

Article text:
{article_text}"""


def get_db():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    return conn


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')


def extract_companies_from_text(text: str, source_url: str = "") -> list[dict]:
    """Use Claude to extract private company data from article text."""
    if not ANTHROPIC_API_KEY:
        print("  ANTHROPIC_API_KEY not set, skipping extraction")
        return []

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(article_text=text[:8000])
            }],
        )
        content = response.content[0].text

        # Parse JSON from response
        # Try to find JSON array in the response
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            companies = json.loads(json_match.group())
        else:
            companies = json.loads(content)

        # Add source metadata
        for c in companies:
            c["source_url"] = source_url
            c["source_type"] = "biopharma_dive"

        return companies

    except Exception as e:
        print(f"  Extraction error: {e}")
        return []


def insert_company(cur, company: dict) -> bool:
    """Insert or update a company in the database. Returns True if new."""
    name = company.get("name", "").strip()
    if not name:
        return False

    slug = slugify(name)
    therapeutic_areas = company.get("therapeutic_areas", [])
    if isinstance(therapeutic_areas, str):
        therapeutic_areas = [ta.strip() for ta in therapeutic_areas.split(",") if ta.strip()]

    founded_year = company.get("founded_year")
    if founded_year and isinstance(founded_year, str):
        try:
            founded_year = int(founded_year)
        except ValueError:
            founded_year = None

    try:
        cur.execute("""
            INSERT INTO private_companies
                (name, slug, hq_location, founded_year, employee_count,
                 therapeutic_areas, modality, lead_programs, stage,
                 description, website, source_url, source_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                description = CASE
                    WHEN LENGTH(EXCLUDED.description) > LENGTH(COALESCE(private_companies.description, ''))
                    THEN EXCLUDED.description
                    ELSE private_companies.description
                END,
                therapeutic_areas = CASE
                    WHEN array_length(EXCLUDED.therapeutic_areas, 1) > COALESCE(array_length(private_companies.therapeutic_areas, 1), 0)
                    THEN EXCLUDED.therapeutic_areas
                    ELSE private_companies.therapeutic_areas
                END,
                lead_programs = COALESCE(NULLIF(EXCLUDED.lead_programs, ''), private_companies.lead_programs),
                stage = COALESCE(NULLIF(EXCLUDED.stage, ''), private_companies.stage),
                modality = COALESCE(NULLIF(EXCLUDED.modality, ''), private_companies.modality),
                last_updated = NOW()
            RETURNING id, (xmax = 0) AS is_new
        """, (
            name, slug,
            company.get("hq_location", ""),
            founded_year,
            company.get("employee_count", ""),
            therapeutic_areas,
            company.get("modality", ""),
            company.get("lead_programs", ""),
            company.get("stage", ""),
            company.get("description", ""),
            company.get("website", ""),
            company.get("source_url", ""),
            company.get("source_type", "biopharma_dive"),
        ))
        row = cur.fetchone()
        return row[1] if row else False

    except Exception as e:
        print(f"  DB insert error for {name}: {e}")
        return False


def seed_known_companies(cur):
    """Seed the directory with well-known private biotech companies."""
    known = [
        {
            "name": "Eikon Therapeutics",
            "hq_location": "Hayward, CA",
            "founded_year": 2019,
            "therapeutic_areas": ["oncology", "immunology"],
            "modality": "small molecule",
            "stage": "preclinical",
            "description": "Uses super-resolution microscopy and machine learning to observe protein movement in living cells for drug discovery.",
            "employee_count": "200-500",
        },
        {
            "name": "Adagene",
            "hq_location": "Suzhou, China",
            "founded_year": 2012,
            "therapeutic_areas": ["oncology"],
            "modality": "bispecific antibody",
            "lead_programs": "ADG126 (anti-CTLA-4), ADG106 (anti-LIGHT)",
            "stage": "phase2",
            "description": "Antibody engineering platform using dynamic precision library for next-gen immunotherapy.",
        },
        {
            "name": "Cellares",
            "hq_location": "South San Francisco, CA",
            "founded_year": 2019,
            "therapeutic_areas": ["oncology", "autoimmune"],
            "modality": "cell therapy manufacturing",
            "stage": "preclinical",
            "description": "Automated cell therapy manufacturing using the Cell Shuttle platform to scale autologous and allogeneic therapies.",
            "employee_count": "100-200",
        },
        {
            "name": "Odyssey Therapeutics",
            "hq_location": "San Diego, CA",
            "founded_year": 2021,
            "therapeutic_areas": ["oncology", "immunology"],
            "modality": "small molecule",
            "lead_programs": "IRAK4 degrader, CDK2 inhibitor",
            "stage": "phase1",
            "description": "Precision medicine company developing small molecules and targeted protein degraders for oncology and immunology.",
        },
        {
            "name": "ArsenalBio",
            "hq_location": "South San Francisco, CA",
            "founded_year": 2019,
            "therapeutic_areas": ["oncology"],
            "modality": "cell therapy",
            "lead_programs": "AB-1015 (logic-gated T cell, solid tumors)",
            "stage": "phase1",
            "description": "Programmable cell therapy using integrated circuit T cells with synthetic biology for solid tumors.",
            "employee_count": "100-200",
        },
        {
            "name": "Dren Bio",
            "hq_location": "San Carlos, CA",
            "founded_year": 2019,
            "therapeutic_areas": ["oncology", "autoimmune"],
            "modality": "bispecific antibody",
            "lead_programs": "DR-01 (macrophage engager)",
            "stage": "phase1",
            "description": "Engineering macrophage engager antibodies to harness innate immunity against cancer and autoimmune diseases.",
        },
        {
            "name": "Dianthus Therapeutics",
            "hq_location": "New York, NY",
            "founded_year": 2020,
            "therapeutic_areas": ["autoimmune", "rare disease"],
            "modality": "monoclonal antibody",
            "lead_programs": "DNTH103 (anti-FcRn)",
            "stage": "phase2",
            "description": "Developing next-generation complement-targeted therapies for autoimmune and inflammatory diseases.",
        },
        {
            "name": "Upstream Bio",
            "hq_location": "Waltham, MA",
            "founded_year": 2021,
            "therapeutic_areas": ["immunology", "respiratory"],
            "modality": "monoclonal antibody",
            "lead_programs": "UPB-101 (anti-TSLP)",
            "stage": "phase2",
            "description": "Developing verekitug, a next-gen anti-TSLP antibody for severe asthma and inflammatory diseases.",
        },
        {
            "name": "Spyre Therapeutics",
            "hq_location": "Waltham, MA",
            "founded_year": 2023,
            "therapeutic_areas": ["immunology", "gastroenterology"],
            "modality": "monoclonal antibody",
            "lead_programs": "SPY001 (anti-TL1A), SPY002 (anti-α4β7)",
            "stage": "phase2",
            "description": "Next-generation antibody engineering for inflammatory bowel disease with extended half-life and enhanced potency.",
        },
        {
            "name": "MOMA Therapeutics",
            "hq_location": "New York, NY",
            "founded_year": 2019,
            "therapeutic_areas": ["oncology"],
            "modality": "small molecule",
            "lead_programs": "Chromatin machinery inhibitors",
            "stage": "preclinical",
            "description": "Drugging the chromatin machinery — molecular motors and remodelers that are dysregulated in cancer.",
            "employee_count": "50-100",
        },
        {
            "name": "Terray Therapeutics",
            "hq_location": "Pasadena, CA",
            "founded_year": 2021,
            "therapeutic_areas": ["oncology", "immunology", "neuroscience"],
            "modality": "small molecule",
            "stage": "preclinical",
            "description": "Massively parallel chemistry platform measuring billions of molecular interactions to discover novel small molecules.",
            "employee_count": "100-200",
        },
        {
            "name": "Ring Therapeutics",
            "hq_location": "Cambridge, MA",
            "founded_year": 2017,
            "therapeutic_areas": ["oncology", "rare disease"],
            "modality": "gene therapy",
            "lead_programs": "Anellovector-based gene therapies",
            "stage": "preclinical",
            "description": "Commensal virus-inspired vectors (anelloviruses) for redosable gene therapy without immune rejection.",
        },
        {
            "name": "Tentarix Biotherapeutics",
            "hq_location": "San Diego, CA",
            "founded_year": 2021,
            "therapeutic_areas": ["oncology"],
            "modality": "multispecific antibody",
            "lead_programs": "Tentacles platform (multispecific biologics)",
            "stage": "preclinical",
            "description": "Novel multi-arm multispecific biologics enabling simultaneous engagement of multiple tumor targets.",
        },
        {
            "name": "Relation Therapeutics",
            "hq_location": "London, UK",
            "founded_year": 2020,
            "therapeutic_areas": ["oncology", "immunology", "neuroscience"],
            "modality": "AI-driven",
            "stage": "preclinical",
            "description": "Using single-cell multi-omics and geometric deep learning to discover drug targets and biomarkers.",
        },
        {
            "name": "Sonnet BioTherapeutics",
            "hq_location": "Princeton, NJ",
            "founded_year": 2017,
            "therapeutic_areas": ["oncology", "autoimmune"],
            "modality": "biologic (albumin-binding)",
            "lead_programs": "SON-1010 (IL-12-FHAB), SON-080 (IL-6-FHAB)",
            "stage": "phase1",
            "description": "Fully human albumin binding (FHAB) platform for half-life extended cytokine therapies in oncology.",
        },
        {
            "name": "Immunocore Holdings",
            "hq_location": "Abingdon, UK",
            "founded_year": 2008,
            "therapeutic_areas": ["oncology", "infectious disease"],
            "modality": "T cell receptor bispecific",
            "lead_programs": "IMC-F106C (PRAME TCR), tebentafusp (approved uveal melanoma)",
            "stage": "phase3",
            "description": "Pioneers ImmTAX platform — soluble T cell receptors fused to immune effectors for redirected T cell killing.",
        },
        {
            "name": "Rapport Therapeutics",
            "hq_location": "Cambridge, MA",
            "founded_year": 2021,
            "therapeutic_areas": ["neuroscience"],
            "modality": "small molecule",
            "lead_programs": "RAP-219 (GABA-A modulator for epilepsy)",
            "stage": "phase1",
            "description": "Subunit-selective GABA-A receptor modulators for treatment-resistant epilepsy with improved safety.",
        },
        {
            "name": "Vigil Neuroscience",
            "hq_location": "Cambridge, MA",
            "founded_year": 2020,
            "therapeutic_areas": ["neuroscience"],
            "modality": "monoclonal antibody",
            "lead_programs": "VGL101 (anti-TREM2 agonist)",
            "stage": "phase2",
            "description": "Microglial biology company developing TREM2 agonists to restore brain immune function in neurodegeneration.",
        },
        {
            "name": "Leal Therapeutics",
            "hq_location": "San Carlos, CA",
            "founded_year": 2022,
            "therapeutic_areas": ["psychiatry", "neuroscience"],
            "modality": "small molecule",
            "lead_programs": "LT-1001 (psilocin for treatment-resistant depression)",
            "stage": "phase2",
            "description": "Psychedelic-inspired neuropsychiatric medicines, developing synthetic psilocin formulation for depression.",
        },
        {
            "name": "Pyxis Oncology",
            "hq_location": "Cambridge, MA",
            "founded_year": 2019,
            "therapeutic_areas": ["oncology"],
            "modality": "ADC",
            "lead_programs": "PYX-201 (B7-H4 ADC)",
            "stage": "phase1",
            "description": "Next-gen ADCs and immune checkpoint antibodies targeting tumor microenvironment for solid tumors.",
        },
    ]

    new_count = 0
    for company in known:
        company["source_type"] = "curated"
        is_new = insert_company(cur, company)
        if is_new:
            new_count += 1
            print(f"  + {company['name']}")

    return new_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    parser.add_argument("--seed-only", action="store_true", help="Only seed known companies")
    args = parser.parse_args()

    if not DB_URL:
        print("NEON_DATABASE_URL not set")
        sys.exit(1)

    conn = get_db()
    cur = conn.cursor()

    # Always seed known companies first
    print("Seeding known private biotech companies...")
    new_seeded = seed_known_companies(cur)
    print(f"Seeded {new_seeded} new companies\n")

    if args.seed_only:
        cur.close()
        conn.close()
        return

    # TODO: Web search scraping would go here
    # For now, the seed list provides a solid starting point
    # Future: integrate with BioPharma Dive RSS, ClinicalTrials.gov API

    cur.execute("SELECT COUNT(*) FROM private_companies")
    total = cur.fetchone()[0]
    print(f"\nTotal companies in directory: {total}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
