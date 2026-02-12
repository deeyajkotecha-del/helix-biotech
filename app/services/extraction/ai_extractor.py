"""
AI-Powered Clinical Data Extractor (v2.1 Schema)

Uses Claude API to extract structured clinical data from PDF presentations.
Two-pass architecture:
  Pass 1: Company-level data -> company.json
  Pass 2: Per-asset data -> {asset-name}.json (one API call per asset)

Outputs JSON matching data/companies/{TICKER}/ v2.1 schema directly.
"""

import os
import json
import logging
import re
import time
import unicodedata
from typing import Optional
from datetime import datetime

from dotenv import load_dotenv
import anthropic

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AIExtractor:
    """Extract structured clinical data from text using Claude (v2.1 schema)."""

    def __init__(
        self,
        api_key: str = None,
        model: str = DEFAULT_MODEL,
        rate_limit_delay: float = 2.0
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Add it to .env file or environment variables.")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.rate_limit_delay = rate_limit_delay

    def extract_company_data(
        self,
        pdf_text: str,
        ticker: str,
        company_name: str = None,
        source_filename: str = None
    ) -> dict:
        """
        Two-pass extraction: company-level data + per-asset data.

        Returns dict with:
          "company.json": company data matching v2.1
          "{asset-name}.json": per-asset data matching v2.1
          "_extraction_metadata": extraction run info
        """
        ticker = ticker.upper()
        source_id = _generate_source_id(ticker, source_filename)

        # === Pass 1: Company extraction ===
        logger.info(f"Pass 1: Extracting company data for {ticker}")
        company_prompt = self._build_company_extraction_prompt(
            pdf_text, ticker, company_name, source_id
        )
        company_response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            messages=[{"role": "user", "content": company_prompt}]
        )
        company_data = self._parse_response(company_response.content[0].text)

        # Discover assets from pipeline_summary
        programs = []
        pipeline = company_data.get("pipeline_summary", {})
        if isinstance(pipeline, dict):
            programs = pipeline.get("programs", [])

        asset_names = []
        for prog in programs:
            name = prog.get("asset")
            if name:
                asset_names.append(name)

        logger.info(f"Pass 1 complete. Found {len(asset_names)} assets: {asset_names}")

        # === Pass 2: Per-asset extraction ===
        files = {}
        files["company.json"] = company_data

        for i, asset_name in enumerate(asset_names):
            if i > 0:
                time.sleep(self.rate_limit_delay)

            logger.info(f"Pass 2 ({i+1}/{len(asset_names)}): Extracting {asset_name}")
            asset_prompt = self._build_asset_extraction_prompt(
                pdf_text, ticker, asset_name, company_name, source_id
            )
            asset_response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                messages=[{"role": "user", "content": asset_prompt}]
            )
            asset_data = self._parse_response(asset_response.content[0].text)

            filename = asset_to_dashed_filename(asset_name)
            files[filename] = asset_data

        # Add extraction metadata
        files["_extraction_metadata"] = {
            "ticker": ticker,
            "extracted_at": datetime.now().isoformat(),
            "source_file": source_filename,
            "source_id": source_id,
            "model_used": self.model,
            "input_chars": len(pdf_text),
            "assets_extracted": asset_names,
            "company_output_tokens": company_response.usage.output_tokens
        }

        return files

    def extract_single_asset(
        self,
        pdf_text: str,
        ticker: str,
        asset_name: str,
        company_name: str = None,
        source_filename: str = None
    ) -> dict:
        """
        Extract data for a single asset (Pass 2 only).

        Returns dict with:
          "{asset-name}.json": asset data matching v2.1
        """
        ticker = ticker.upper()
        source_id = _generate_source_id(ticker, source_filename)

        logger.info(f"Single-asset extraction: {asset_name} for {ticker}")
        asset_prompt = self._build_asset_extraction_prompt(
            pdf_text, ticker, asset_name, company_name, source_id
        )
        asset_response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            messages=[{"role": "user", "content": asset_prompt}]
        )
        asset_data = self._parse_response(asset_response.content[0].text)

        filename = asset_to_dashed_filename(asset_name)
        return {
            filename: asset_data,
            "_extraction_metadata": {
                "ticker": ticker,
                "extracted_at": datetime.now().isoformat(),
                "source_file": source_filename,
                "source_id": source_id,
                "model_used": self.model,
                "asset_name": asset_name,
            }
        }

    def _build_company_extraction_prompt(
        self,
        pdf_text: str,
        ticker: str,
        company_name: str = None,
        source_id: str = None
    ) -> str:
        """Build the v2.1 company-level extraction prompt."""
        today = datetime.now().strftime("%Y-%m-%d")

        return f'''You are a PhD-level biotechnology analyst at a top healthcare fund (Avoro, RA Capital, OrbiMed level).
Extract COMPANY-LEVEL data from this investor presentation for {ticker}{f" ({company_name})" if company_name else ""}.

The text includes [PAGE X] markers. Cite page numbers where possible.

<presentation_text>
{pdf_text}
</presentation_text>

Return a JSON object with this EXACT v2.1 schema:

```json
{{
  "_metadata": {{
    "version": "2.1",
    "ticker": "{ticker}",
    "company_name": "<company name>",
    "data_source": "{source_id or ticker.lower() + '_presentation'}",
    "extraction_date": "{today}"
  }},
  "ticker": "{ticker}",
  "name": "<full company name>",
  "company": {{
    "name": "<full company name>",
    "ticker": "{ticker}",
    "exchange": "<exchange, e.g. NASDAQ>",
    "headquarters": "<city, state>",
    "website": "<URL if found>",
    "one_liner": "<1-2 sentence investment-oriented summary of what the company does and why it matters>"
  }},
  "investment_thesis_summary": {{
    "core_thesis": "<2-3 sentence thesis: what the company is, key catalyst, and why it matters>",
    "key_value_drivers": [
      "<driver 1 — specific, data-backed>",
      "<driver 2>",
      "<driver 3>",
      "<driver 4>"
    ]
  }},
  "investment_analysis": {{
    "bull_case": [
      "<specific bull point with evidence — these are simple strings>",
      "<bull point 2>",
      "<bull point 3>"
    ],
    "bear_case": [
      "<specific bear/risk point — simple strings>",
      "<bear point 2>",
      "<bear point 3>"
    ],
    "key_debates": [
      {{
        "question": "<what the market is debating>",
        "bull_view": "<bull perspective with evidence>",
        "bear_view": "<bear perspective with evidence>",
        "what_resolves_it": "<data/catalyst that answers this>"
      }}
    ]
  }},
  "pipeline_summary": {{
    "total_programs": null,
    "clinical_stage": null,
    "programs": [
      {{
        "asset": "<asset name, e.g. KT-621>",
        "target": "<target protein/pathway>",
        "stage": "<Phase 1 / Phase 2 / Pivotal / Approved>",
        "indications": "<indication(s)>",
        "ownership": "<Wholly-owned / Partnered with X>",
        "next_catalyst": "<next key event and timing>",
        "source": {{"id": "{source_id}", "slide": null, "verified": false}}
      }}
    ]
  }},
  "platform": {{
    "name": "<platform technology name if applicable, null if none>",
    "description": "<1-2 sentence description of the platform>"
  }},
  "financials": {{
    "cash_position": "<$XXM or $X.XB with date>",
    "cash_runway": "<into YYYY or through YYYY>",
    "market_cap": "<approximate>",
    "enterprise_value": null,
    "revenue": "<revenue or 'Pre-revenue'>",
    "r_and_d_expense": "<quarterly R&D if mentioned>",
    "net_loss": "<quarterly net loss if mentioned>",
    "shares_outstanding": "<shares outstanding if mentioned>",
    "source": {{"id": "{source_id}", "slide": null, "verified": false}}
  }},
  "catalysts": [
    {{
      "asset": "<asset name>",
      "event": "<catalyst description>",
      "timing": "<H1 2026 / Q4 2026 / 2027>",
      "importance": "<critical / high / medium / low>",
      "what_to_watch": "<specific metrics or outcomes to monitor>"
    }}
  ]
}}
```

CRITICAL GUIDELINES:
1. bull_case and bear_case at company level are SIMPLE STRING ARRAYS — not objects.
2. Include ALL pipeline assets, even early/undisclosed ones.
3. Catalysts should be chronologically ordered with specific timing.
4. core_thesis should be actionable investment thesis, not generic description.
5. key_value_drivers should be specific and data-backed.
6. Use null for unknown values, never "N/A" or empty strings.
7. key_debates should capture what sophisticated investors are debating.

Return ONLY the JSON object, no additional text.'''

    def _build_asset_extraction_prompt(
        self,
        pdf_text: str,
        ticker: str,
        asset_name: str,
        company_name: str = None,
        source_id: str = None
    ) -> str:
        """Build the v2.1 per-asset extraction prompt."""
        today = datetime.now().strftime("%Y-%m-%d")

        return f'''You are a PhD-level biotechnology analyst extracting detailed asset data.

COMPANY: {ticker}{f" ({company_name})" if company_name else ""}
ASSET: {asset_name}

Extract ALL available data about {asset_name} from this presentation.
The text includes [PAGE X] markers. Cite pages in source fields.

<presentation_text>
{pdf_text}
</presentation_text>

Return a JSON object with this EXACT v2.1 asset schema:

```json
{{
  "_metadata": {{
    "version": "2.1",
    "ticker": "{ticker}",
    "asset_name": "{asset_name}",
    "extraction_date": "{today}",
    "source_id": "{source_id}"
  }},
  "asset": {{
    "name": "{asset_name}",
    "company": "{company_name or ''}",
    "ticker": "{ticker}",
    "stage": "<Phase 1 / Phase 2 / Pivotal / Approved>",
    "modality": "<Small molecule / mAb / ASO / etc.>",
    "ownership": "<Wholly-owned / Partnered with X>",
    "one_liner": "<1-2 sentence: what the drug is, what it targets, and why it matters>"
  }},
  "target": {{
    "name": "<target name>",
    "full_name": "<full scientific target name>",
    "class": "<target class, e.g. Kinase / Motor protein / Receptor>",
    "pathway": "<biological pathway>",
    "biology": {{
      "simple_explanation": "<2-3 sentence accessible explanation of disease biology and how the drug addresses it>",
      "pathway_detail": "<detailed pathway description if available>",
      "downstream_effects": ["<effect 1>", "<effect 2>"]
    }},
    "why_good_target": {{
      "clinical_validation": "<evidence this target works>",
      "genetic_validation": {{
        "gain_of_function": null,
        "loss_of_function": "<genetic evidence if any>"
      }},
      "source": {{"id": "{source_id}", "slide": null, "verified": false}}
    }}
  }},
  "mechanism": {{
    "type": "<mechanism type>",
    "how_it_works": "<detailed MOA>",
    "differentiation": "<what makes this approach unique>",
    "source": {{"id": "{source_id}", "slide": null, "verified": false}}
  }},
  "regulatory": {{
    "designations": [
      {{
        "type": "<Orphan Drug / Fast Track / Breakthrough / etc.>",
        "indication": "<indication>",
        "date_granted": null,
        "source": {{"id": "{source_id}", "slide": null, "verified": false}}
      }}
    ],
    "planned_pathway": {{
      "type": "<Traditional NDA / Accelerated approval / etc.>",
      "surrogate_endpoint": "<details on regulatory strategy>",
      "source": {{"id": "{source_id}", "slide": null, "verified": false}}
    }}
  }},
  "partnership": {{
    "_note": "<partnership note or 'Wholly-owned; no partnership'>",
    "partner": null,
    "territory": null,
    "economics": null
  }},
  "pharmacology": {{
    "pk_parameters": {{
      "half_life": {{"value": null, "population": null, "source": {{"id": "{source_id}", "slide": null, "verified": false}}}},
      "cmax": {{"value": null, "source": {{"id": "{source_id}", "slide": null, "verified": false}}}},
      "auc": {{"value": null, "source": {{"id": "{source_id}", "slide": null, "verified": false}}}},
      "tmax": {{"value": null, "source": {{"id": "{source_id}", "slide": null, "verified": false}}}},
      "bioavailability": {{"value": null, "source": {{"id": "{source_id}", "slide": null, "verified": false}}}},
      "volume_of_distribution": {{"value": null, "source": {{"id": "{source_id}", "slide": null, "verified": false}}}}
    }},
    "dose_response": {{
      "doses_tested": null,
      "dose_rationale": null,
      "exposure_response": null,
      "recommended_dose": {{"dose": null, "rationale": null, "source": {{"id": "{source_id}", "slide": null, "verified": false}}}},
      "by_dose": null
    }},
    "target_engagement": {{
      "metric": null,
      "by_dose": null
    }},
    "pk_summary": "<brief PK summary>"
  }},
  "indications": {{
    "lead": {{
      "name": "<lead indication>",
      "patient_population": "<patient population description>",
      "current_penetration": "<current treatment landscape>",
      "rationale": "<why this indication>",
      "source": {{"id": "{source_id}", "slide": null, "verified": false}}
    }},
    "expansion": [
      {{
        "name": "<expansion indication>",
        "stage": "<development stage>",
        "rationale": "<rationale>",
        "source": {{"id": "{source_id}", "slide": null, "verified": false}}
      }}
    ]
  }},
  "clinical_data": {{
    "trials": [
      {{
        "name": "<trial name>",
        "nct_id": "<NCT number if available>",
        "phase": "<Phase 1 / Phase 2 / Phase 3 / Pivotal>",
        "status": "<Ongoing / Completed / Planned>",
        "design": "<trial design description>",
        "enrollment": "<N=XX or enrollment description>",
        "arms": [
          {{"name": "<arm name>", "dose": "<dose>", "n": null}}
        ],
        "primary_endpoint": {{
          "name": "<endpoint name>",
          "definition": "<what it measures>",
          "result": "<result if available>",
          "source": {{"id": "{source_id}", "slide": null, "verified": false}}
        }},
        "secondary_endpoints": [
          {{
            "name": "<endpoint>",
            "result": "<result>",
            "source": {{"id": "{source_id}", "slide": null, "verified": false}}
          }}
        ],
        "biomarkers": [
          {{
            "name": "<biomarker>",
            "result": "<result>",
            "clinical_significance": "<why it matters>",
            "source": {{"id": "{source_id}", "slide": null, "verified": false}}
          }}
        ],
        "safety": {{
          "summary": "<safety summary>",
          "key_aes": null,
          "discontinuations": null,
          "saes": null,
          "deaths": null
        }},
        "source": {{"id": "{source_id}", "slide": null, "verified": false}}
      }}
    ]
  }},
  "differentiation_claims": [
    {{
      "claim": "<differentiation claim>",
      "evidence_level": "<management_claim / phase_2 / phase_3 / cross_trial>",
      "caveat": "<important caveat>",
      "source": {{"id": "{source_id}", "slide": null, "verified": false}}
    }}
  ],
  "competitive_landscape": {{
    "competitors": [
      {{
        "drug": "<competitor drug>",
        "company": "<company>",
        "stage": "<stage>",
        "mechanism": "<mechanism>",
        "key_data": null,
        "limitation": "<limitation>",
        "differentiation_vs_us": "<how our asset differentiates>"
      }}
    ],
    "_note": "<general competitive context>"
  }},
  "ip_landscape": {{
    "composition_of_matter": {{"patent_expiry": null, "source": {{"id": "{source_id}", "slide": null, "verified": false}}}},
    "method_of_use": {{"patent_expiry": null, "source": {{"id": "{source_id}", "slide": null, "verified": false}}}},
    "regulatory_exclusivity": {{"type": null, "expiry": null}},
    "freedom_to_operate": null
  }},
  "market_opportunity": {{
    "tam": null,
    "patient_population": null,
    "unmet_need": "<unmet medical need>",
    "pricing_benchmark": null,
    "peak_sales_estimate": null,
    "source": {{"id": "{source_id}", "slide": null, "verified": false}}
  }},
  "catalysts": [
    {{
      "event": "<catalyst description>",
      "timing": "<H1 2026 / Q4 2026 / 2027>",
      "importance": "<critical / high / medium / low>",
      "what_to_watch": "<metrics to monitor>",
      "bull_scenario": "<what good looks like>",
      "bear_scenario": "<what bad looks like>"
    }}
  ],
  "investment_analysis": {{
    "probability_of_success": null,
    "key_risks": ["<risk 1>", "<risk 2>"],
    "bull_case": [
      {{
        "thesis": "<bull thesis>",
        "evidence": "<supporting evidence>",
        "confidence": "<high / medium / low>"
      }}
    ],
    "bear_case": [
      {{
        "thesis": "<bear thesis>",
        "evidence": "<supporting evidence>",
        "confidence": "<high / medium / low>"
      }}
    ],
    "key_debates": [
      {{
        "question": "<key debate>",
        "bull_view": "<bull perspective>",
        "bear_view": "<bear perspective>",
        "what_resolves_it": "<what data/catalyst resolves this>"
      }}
    ]
  }},
  "_extraction_quality": {{
    "completeness_score": "<high / medium / low>",
    "missing_critical_fields": ["<field 1>", "<field 2>"],
    "recommended_supplementary_sources": ["<source 1>", "<source 2>"]
  }}
}}
```

CRITICAL GUIDELINES:
1. bull_case and bear_case at ASSET level are OBJECTS with thesis/evidence/confidence — NOT simple strings.
2. Extract ALL clinical trials mentioned, including completed, ongoing, and planned.
3. Include EXACT numbers (percentages, p-values, CIs) where available.
4. Biomarkers should explain WHAT they measure and WHY they matter.
5. Safety: note AEs of interest, discontinuations, SAEs, deaths.
6. Differentiation claims: specify evidence_level honestly (management_claim vs data-backed).
7. competitive_landscape: include ALL named competitors with their limitations.
8. catalysts: include bull_scenario and bear_scenario for each.
9. Use null for unknown values, never "N/A" or empty strings.
10. _extraction_quality should honestly assess what's missing.

Return ONLY the JSON object, no additional text.'''

    def _parse_response(self, response_text: str) -> dict:
        """Parse Claude's response into structured data."""
        text = response_text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {
                "_error": "Failed to parse extraction response",
                "_raw_response": response_text[:2000],
            }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def asset_to_dashed_filename(name: str) -> str:
    """
    Convert asset name to dashed filename convention.

    Examples:
        "Sevasemten" -> "sevasemten.json"
        "EDG-7500" -> "edg-7500.json"
        "KT-621" -> "kt-621.json"
        "ARGX-121" -> "argx-121.json"
        "TransCon IL-2" -> "transcon-il-2.json"
    """
    result = name.lower().strip()
    # Normalize unicode
    result = unicodedata.normalize('NFKD', result)
    result = result.encode('ascii', 'ignore').decode('ascii')
    # Replace whitespace and underscores with dashes
    result = re.sub(r'[\s_]+', '-', result)
    # Remove anything that isn't alphanumeric or dash
    result = re.sub(r'[^a-z0-9-]', '', result)
    # Collapse multiple dashes
    result = re.sub(r'-+', '-', result)
    result = result.strip('-')
    return result + ".json"


def sanitize_filename(name: str) -> str:
    """
    Legacy filename sanitizer (underscore convention).
    Kept for backwards compatibility.
    """
    greek_map = {
        'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e',
        'ζ': 'z', 'η': 'e', 'θ': 'th', 'ι': 'i', 'κ': 'k',
        'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x', 'ο': 'o',
        'π': 'p', 'ρ': 'r', 'σ': 's', 'τ': 't', 'υ': 'u',
        'φ': 'ph', 'χ': 'ch', 'ψ': 'ps', 'ω': 'o',
        'Α': 'A', 'Β': 'B', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E',
    }

    result = name.lower()
    for greek, ascii_char in greek_map.items():
        result = result.replace(greek, ascii_char)

    result = unicodedata.normalize('NFKD', result)
    result = result.encode('ascii', 'ignore').decode('ascii')
    result = re.sub(r'[/\\()\[\]{}]', '_', result)
    result = re.sub(r'[-\s]+', '_', result)
    result = re.sub(r'[^a-z0-9_]', '', result)
    result = re.sub(r'_+', '_', result)
    result = result.strip('_')
    return result


def _generate_source_id(ticker: str, filename: str = None) -> str:
    """
    Generate a source ID from ticker and filename.

    Examples:
        ("EWTX", "ewtx_jpm_2026.pdf") -> "ewtx_jpm_2026"
        ("EWTX", "Edgewise JPM January 2026.pdf") -> "ewtx_jpm_january_2026"
        ("EWTX", None) -> "ewtx_presentation_2026"
    """
    ticker_lower = ticker.lower()

    if not filename:
        year = datetime.now().strftime("%Y")
        return f"{ticker_lower}_presentation_{year}"

    # Strip extension
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename

    # Clean up
    result = stem.lower().strip()
    result = re.sub(r'[\s-]+', '_', result)
    result = re.sub(r'[^a-z0-9_]', '', result)
    result = re.sub(r'_+', '_', result)
    result = result.strip('_')

    # Ensure ticker prefix
    if not result.startswith(ticker_lower):
        result = f"{ticker_lower}_{result}"

    return result


def convert_to_file_format(extracted_data: dict, ticker: str) -> dict:
    """
    Convert extraction output to file format for saving.

    With v2.1 two-pass extraction, the AI outputs are already in the correct
    schema. This function just separates the files dict from metadata.

    Returns dict mapping filename -> JSON data.
    """
    files = {}
    for key, value in extracted_data.items():
        if key.startswith("_"):
            continue
        if key.endswith(".json"):
            files[key] = value
    return files


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def extract_company_data(
    pdf_text: str,
    ticker: str,
    company_name: str = None,
    source_filename: str = None,
    api_key: str = None
) -> dict:
    """
    Extract structured company data from PDF text.

    Returns dict with "company.json", "{asset}.json" keys, and "_extraction_metadata".
    """
    extractor = AIExtractor(api_key=api_key)
    return extractor.extract_company_data(
        pdf_text, ticker, company_name, source_filename
    )


def extract_single_asset(
    pdf_text: str,
    ticker: str,
    asset_name: str,
    company_name: str = None,
    source_filename: str = None,
    api_key: str = None
) -> dict:
    """
    Extract data for a single asset (Pass 2 only).

    Returns dict with "{asset-name}.json" key.
    """
    extractor = AIExtractor(api_key=api_key)
    return extractor.extract_single_asset(
        pdf_text, ticker, asset_name, company_name, source_filename
    )
