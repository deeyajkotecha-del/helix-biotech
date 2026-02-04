"""
AI-Powered Clinical Data Extractor

Uses Claude API to extract structured clinical data from PDF presentations.
Outputs JSON matching our data/companies/{TICKER}/ schema.
"""

import os
import json
import logging
import re
import unicodedata
from typing import Optional
from datetime import datetime

from dotenv import load_dotenv
import anthropic

# Load .env file for local development (Render uses environment variables directly)
load_dotenv()

logger = logging.getLogger(__name__)

# Default model for extraction
DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AIExtractor:
    """Extract structured clinical data from text using Claude."""

    def __init__(self, api_key: str = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Add it to .env file or environment variables.")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model

    def extract_company_data(
        self,
        pdf_text: str,
        ticker: str,
        company_name: str = None,
        source_filename: str = None
    ) -> dict:
        """
        Extract structured company data from PDF text.

        Args:
            pdf_text: Full text extracted from PDF (with page markers)
            ticker: Company ticker symbol
            company_name: Company name (optional, will be extracted if not provided)
            source_filename: Original PDF filename for attribution

        Returns:
            Dict with company.json and asset JSONs ready to save
        """
        ticker = ticker.upper()

        # Build the extraction prompt
        prompt = self._build_extraction_prompt(pdf_text, ticker, company_name)

        # Call Claude API
        logger.info(f"Extracting data for {ticker} using {self.model}")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse the response
        response_text = response.content[0].text
        extracted_data = self._parse_response(response_text)

        # Add metadata
        extracted_data["_extraction_metadata"] = {
            "ticker": ticker,
            "extracted_at": datetime.now().isoformat(),
            "source_file": source_filename,
            "model_used": self.model,
            "input_chars": len(pdf_text),
            "output_tokens": response.usage.output_tokens
        }

        return extracted_data

    def _build_extraction_prompt(
        self,
        pdf_text: str,
        ticker: str,
        company_name: str = None
    ) -> str:
        """Build the PhD-level extraction prompt for Claude."""

        return f'''You are a PhD-level biotechnology analyst at a top healthcare fund (Avoro, RA Capital, OrbiMed level).
Extract structured data from this investor presentation for institutional investment analysis.

COMPANY: {ticker}{f" ({company_name})" if company_name else ""}

The text includes [PAGE X] markers - ALWAYS cite page numbers for traceability.

<presentation_text>
{pdf_text}
</presentation_text>

Extract and return a JSON object with this EXACT structure:

```json
{{
  "company": {{
    "name": "Company Name",
    "ticker": "{ticker}",
    "description": "2-3 sentence company description",
    "one_liner": "Single sentence capturing the key investment angle",
    "headquarters": "City, State if found",
    "website": "URL if found",
    "modality": "Primary modality (Small molecule degrader / mAb / etc.)",
    "therapeutic_focus": ["Area 1", "Area 2"],
    "source_pages": [1, 2]
  }},

  "financials": {{
    "cash_position": "$XXM or $X.XB",
    "cash_runway": "Statement like 'Into 2027' or 'Through 2028'",
    "burn_rate_quarterly": "$XXM if mentioned",
    "source_pages": []
  }},

  "investment_thesis": {{
    "bull_case": [
      {{
        "point": "Key bull thesis point",
        "evidence": "Specific data/fact supporting this point",
        "source_page": 10,
        "confidence": "high/medium/low"
      }}
    ],
    "bear_case": [
      {{
        "point": "Key bear thesis point or risk",
        "evidence": "Why this is a concern",
        "counter": "Management's response or mitigating factor if any",
        "source_page": 25,
        "confidence": "high/medium/low"
      }}
    ],
    "key_debates": [
      {{
        "question": "Key question the market is debating",
        "bull_view": "Bull perspective",
        "bear_view": "Bear perspective",
        "data_to_watch": "What data will resolve this"
      }}
    ]
  }},

  "pipeline_assets": [
    {{
      "name": "Asset name (e.g., KT-621)",
      "target": {{
        "name": "Target protein/pathway",
        "full_name": "Full scientific name",
        "pathway": "Signaling pathway",
        "biology": "Brief explanation of target biology and role in disease",
        "genetic_validation": "Human genetic evidence if mentioned",
        "why_undruggable_before": "Why traditional approaches failed"
      }},
      "mechanism": {{
        "type": "Mechanism type (degrader, inhibitor, agonist, etc.)",
        "description": "How the drug works",
        "differentiation": "What makes this approach unique"
      }},
      "modality": "Small molecule degrader / mAb / etc.",
      "stage": "Phase 1 / Phase 2 / etc.",
      "ownership": "Wholly-owned / Partnered with X",
      "lead_indication": "Primary indication",
      "expansion_indications": ["Other indication 1", "Other indication 2"],
      "market_opportunity": {{
        "tam": "Total addressable market if mentioned",
        "patient_population": "Number of patients",
        "current_treatment": "Standard of care",
        "unmet_need": "Why new therapy is needed"
      }},
      "source_pages": [5, 6, 7]
    }}
  ],

  "clinical_trials": [
    {{
      "asset": "Asset name",
      "trial_name": "Trial name (e.g., BroADen, BREADTH)",
      "nct_id": "NCT number if shown",
      "phase": "Phase 1 / Phase 1b / Phase 2 / Phase 2b / Phase 3",
      "indication": "Indication being studied",
      "status": "Completed / Ongoing / Planned",
      "design": {{
        "type": "Open-label / Randomized, double-blind, placebo-controlled",
        "description": "Trial design details",
        "limitations": "Design limitations (e.g., 'open-label - no placebo arm')"
      }},
      "population": {{
        "description": "Patient population description",
        "inclusion_criteria": "Key inclusion criteria",
        "baseline_severity": "Baseline disease severity"
      }},
      "n_enrolled": null,
      "arms": [
        {{"name": "Arm name", "dose": "Dose", "n": null, "duration": "Treatment duration"}}
      ],
      "efficacy_endpoints": [
        {{
          "name": "Endpoint name (e.g., EASI % change)",
          "category": "primary / secondary / exploratory",
          "definition": {{
            "full_name": "Full endpoint name",
            "what_it_measures": "What this endpoint measures",
            "scoring": "How it's scored (0-72 for EASI, etc.)",
            "clinical_meaning": "Why this matters clinically"
          }},
          "result": "Result value (e.g., -63%)",
          "timepoint": "When measured (Day 29, Week 16, etc.)",
          "dose_group": "Which dose/arm",
          "p_value": null,
          "vs_comparator": {{
            "comparator": "Dupixent / Placebo / etc.",
            "comparator_result": "Comparator's result at similar timepoint",
            "interpretation": "How this compares"
          }},
          "caveats": "Important caveats (e.g., 'open-label, cross-trial comparison')",
          "source_page": 28
        }}
      ],
      "biomarker_endpoints": [
        {{
          "name": "Biomarker name (e.g., STAT6 degradation)",
          "result": "Result value",
          "method": "Measurement method (Flow cytometry, ELISA, Mass spec, etc.)",
          "tissue": "Blood / Skin / etc.",
          "what_it_measures": "What this biomarker indicates",
          "interpretation": "What this result means",
          "clinical_significance": "Why this matters for the drug",
          "vs_comparator": "How this compares to competitor if mentioned",
          "source_page": 22
        }}
      ],
      "safety": {{
        "summary": "Overall safety summary",
        "saes": null,
        "discontinuations": null,
        "aes_of_interest": {{
          "ae_name": "incidence (e.g., 'conjunctivitis': '0 vs 10-20% Dupixent')"
        }},
        "differentiation": "Safety differentiation from competitors"
      }},
      "key_takeaways": ["Takeaway 1", "Takeaway 2"],
      "limitations": ["Limitation 1 (e.g., 'small sample size n=22')", "Limitation 2"],
      "source_pages": [10, 11, 12]
    }}
  ],

  "upcoming_catalysts": [
    {{
      "event": "Catalyst description",
      "asset": "Related asset",
      "timing": "Expected timing (Mid-2027, 2H 2026, etc.)",
      "importance": "Critical / High / Medium",
      "what_to_watch": ["Key metric 1 to watch", "Key metric 2"],
      "bull_scenario": {{
        "outcome": "What good looks like",
        "rationale": "Why this would be bullish"
      }},
      "bear_scenario": {{
        "outcome": "What bad looks like",
        "rationale": "Why this would be bearish"
      }},
      "source_page": 4
    }}
  ],

  "partnerships": [
    {{
      "partner": "Partner name (e.g., Sanofi)",
      "asset": "Asset involved",
      "deal_type": "Co-development / License / Option",
      "upfront": "$XXM",
      "milestones": "$X.XB potential",
      "royalties": "Terms if disclosed",
      "status": "Active / Completed",
      "strategic_value": "Why this partnership matters",
      "source_page": 20
    }}
  ],

  "competitive_landscape": [
    {{
      "competitor": "Competitor name",
      "asset": "Their asset",
      "stage": "Competitor's development stage",
      "differentiation": "How company differentiates vs this competitor",
      "threat_level": "High / Medium / Low",
      "source_page": 15
    }}
  ]
}}
```

CRITICAL GUIDELINES FOR PhD-LEVEL EXTRACTION:

1. SOURCE PAGES: ALWAYS include source_page for EVERY data point. This is non-negotiable.

2. CLINICAL DATA PRECISION:
   - Extract EXACT numbers (percentages, p-values, confidence intervals)
   - Include measurement METHODS (flow cytometry, ELISA, etc.)
   - Note the TIMEPOINT for every result
   - Always capture COMPARATOR benchmarks (e.g., "vs Dupixent: -52% at Day 28")

3. CAVEATS AND LIMITATIONS:
   - Flag open-label designs (high placebo response risk)
   - Note small sample sizes
   - Highlight cross-trial comparison limitations
   - Include any data the company downplays

4. BIOMARKER DEPTH:
   - Explain WHAT each biomarker measures and WHY it matters
   - Include the measurement method
   - Note tissue/sample type (blood vs skin vs tissue biopsy)

5. INVESTMENT FRAMING:
   - Bull case: What could go right and the evidence
   - Bear case: What could go wrong and counter-arguments
   - Key debates: What the market is arguing about

6. CATALYST ANALYSIS:
   - What specific metrics to watch
   - What "good" vs "bad" outcomes look like
   - Timing confidence (company-guided vs estimated)

7. Use null for missing numeric values, never "N/A" or empty strings.

8. If data is ambiguous, include a "_notes" field with your interpretation.

Return ONLY the JSON object, no additional text.'''

    def _parse_response(self, response_text: str) -> dict:
        """Parse Claude's response into structured data."""
        # Try to extract JSON from the response
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
            # Return a structured error
            return {
                "_error": "Failed to parse extraction response",
                "_raw_response": response_text[:2000],
                "company": {},
                "pipeline_assets": [],
                "clinical_trials": []
            }

    def extract_asset_details(
        self,
        pdf_text: str,
        ticker: str,
        asset_name: str
    ) -> dict:
        """
        Extract detailed data for a specific asset.

        Use this for deeper extraction when the main extraction
        doesn't capture enough detail for an important asset.
        """
        prompt = f'''You are extracting detailed clinical data for a specific drug asset.

COMPANY: {ticker}
ASSET: {asset_name}

From the presentation text below, extract ALL available information about {asset_name}.
Focus on: mechanism, clinical data, efficacy results, safety, and competitive positioning.

<presentation_text>
{pdf_text}
</presentation_text>

Return a detailed JSON object matching our asset schema:

```json
{{
  "asset": {{
    "name": "{asset_name}",
    "target": "Target",
    "target_full_name": "Full target name",
    "mechanism": "Detailed mechanism of action",
    "modality": "Modality type",
    "pathway": "Biological pathway",
    "competitor_reference": "Key competitor for comparison"
  }},

  "clinical_development": {{
    "current_stage": "Current development stage",
    "indications_in_development": ["Indication 1", "Indication 2"],
    "market_opportunity": "Market size if mentioned"
  }},

  "trials": [
    {{
      "name": "Trial name",
      "phase": "Phase",
      "status": "Status",
      "indication": "Indication",
      "design": "Trial design",
      "population": "Population details",
      "n_target": null,
      "arms": [],
      "primary_endpoint": "Primary endpoint",
      "endpoints": [
        {{
          "name": "Endpoint",
          "category": "primary/secondary/biomarker",
          "result": "Result",
          "dose_group": "Dose group",
          "timepoint": "Timepoint",
          "notes": "Additional notes"
        }}
      ],
      "safety": "Safety summary",
      "source_pages": []
    }}
  ],

  "graph_analyses": {{
    "efficacy_data": [
      {{
        "title": "Graph title",
        "key_findings": ["Finding 1", "Finding 2"],
        "clinical_significance": "Why this matters",
        "source_page": null
      }}
    ]
  }},

  "investment_thesis": ["Point 1", "Point 2"],
  "key_risks": ["Risk 1", "Risk 2"],
  "upcoming_catalysts": [
    {{"event": "Event", "timing": "Timing"}}
  ]
}}
```

Return ONLY the JSON object.'''

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return self._parse_response(response.content[0].text)


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

    Args:
        pdf_text: Full text extracted from PDF
        ticker: Company ticker symbol
        company_name: Company name (optional)
        source_filename: Original PDF filename
        api_key: Anthropic API key (optional, uses env var if not provided)

    Returns:
        Dict with extracted company and asset data
    """
    extractor = AIExtractor(api_key=api_key)
    return extractor.extract_company_data(
        pdf_text, ticker, company_name, source_filename
    )


def extract_asset_details(
    pdf_text: str,
    ticker: str,
    asset_name: str,
    api_key: str = None
) -> dict:
    """
    Extract detailed data for a specific asset.

    Args:
        pdf_text: Full text extracted from PDF
        ticker: Company ticker symbol
        asset_name: Asset name to extract
        api_key: Anthropic API key (optional)

    Returns:
        Dict with detailed asset data
    """
    extractor = AIExtractor(api_key=api_key)
    return extractor.extract_asset_details(pdf_text, ticker, asset_name)


def sanitize_filename(name: str) -> str:
    """
    Convert asset name to a clean, filesystem-safe filename.

    Examples:
        "KT-485/SAR447971" -> "kt485_sar447971"
        "TransCon IL-2β/γ" -> "transcon_il2b_g"
        "SKYTROFA (TransCon hGH)" -> "skytrofa_transcon_hgh"
    """
    # Greek letter replacements
    greek_map = {
        'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e',
        'ζ': 'z', 'η': 'e', 'θ': 'th', 'ι': 'i', 'κ': 'k',
        'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x', 'ο': 'o',
        'π': 'p', 'ρ': 'r', 'σ': 's', 'τ': 't', 'υ': 'u',
        'φ': 'ph', 'χ': 'ch', 'ψ': 'ps', 'ω': 'o',
        'Α': 'A', 'Β': 'B', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E',
    }

    result = name.lower()

    # Replace Greek letters
    for greek, ascii_char in greek_map.items():
        result = result.replace(greek, ascii_char)

    # Normalize unicode (handle accents, etc.)
    result = unicodedata.normalize('NFKD', result)
    result = result.encode('ascii', 'ignore').decode('ascii')

    # Replace common separators with underscore
    result = re.sub(r'[/\\()\[\]{}]', '_', result)

    # Replace dashes and spaces with underscore
    result = re.sub(r'[-\s]+', '_', result)

    # Remove any remaining non-alphanumeric chars (except underscore)
    result = re.sub(r'[^a-z0-9_]', '', result)

    # Collapse multiple underscores
    result = re.sub(r'_+', '_', result)

    # Strip leading/trailing underscores
    result = result.strip('_')

    return result


def convert_to_file_format(extracted_data: dict, ticker: str) -> dict:
    """
    Convert extracted data to our v2 file format for saving.

    Returns dict with:
    - "company.json": company data with bull/bear thesis
    - "{asset_name}.json": asset data with full clinical trials

    Filenames are sanitized for filesystem compatibility.
    Original names are preserved inside JSON for display.
    """
    ticker = ticker.upper()
    files = {}

    # Build company.json with v2 schema
    company = extracted_data.get("company", {})
    financials = extracted_data.get("financials", {})
    thesis = extracted_data.get("investment_thesis", {})

    # Handle both old format (list) and new format (dict with bull_case/bear_case)
    if isinstance(thesis, list):
        # Old format - convert to simple list
        bull_case = thesis
        bear_case = []
        key_debates = []
    else:
        # New v2 format
        bull_case = thesis.get("bull_case", [])
        bear_case = thesis.get("bear_case", [])
        key_debates = thesis.get("key_debates", [])

    company_json = {
        "name": company.get("name"),
        "ticker": ticker,
        "one_liner": company.get("one_liner"),
        "headquarters": company.get("headquarters"),
        "website": company.get("website"),
        "description": company.get("description"),
        "modality": company.get("modality"),
        "therapeutic_focus": company.get("therapeutic_focus", []),
        "financials": {
            "cash_position": financials.get("cash_position"),
            "cash_runway": financials.get("cash_runway"),
            "burn_rate_quarterly": financials.get("burn_rate_quarterly"),
        },
        "investment_thesis": {
            "bull_case": bull_case,
            "bear_case": bear_case,
            "key_debates": key_debates
        },
        "partnerships": extracted_data.get("partnerships", []),
        "competitive_landscape": extracted_data.get("competitive_landscape", []),
        "_source_pages": company.get("source_pages", []),
        "_extracted_at": extracted_data.get("_extraction_metadata", {}).get("extracted_at")
    }
    files["company.json"] = company_json

    # Build asset files with full v2 clinical data
    for asset in extracted_data.get("pipeline_assets", []):
        asset_name = asset.get("name", "unknown")
        filename = sanitize_filename(asset_name) + ".json"

        # Find trials for this asset
        asset_trials = [
            t for t in extracted_data.get("clinical_trials", [])
            if t.get("asset", "").lower() == asset_name.lower()
        ]

        # Find catalysts for this asset
        asset_catalysts = [
            c for c in extracted_data.get("upcoming_catalysts", [])
            if c.get("asset", "").lower() == asset_name.lower()
        ]

        # Handle target - could be string (old) or dict (new v2)
        target_data = asset.get("target", {})
        if isinstance(target_data, str):
            target_obj = {"name": target_data}
        else:
            target_obj = target_data

        # Handle mechanism - could be string (old) or dict (new v2)
        mechanism_data = asset.get("mechanism", {})
        if isinstance(mechanism_data, str):
            mechanism_obj = {"description": mechanism_data}
        else:
            mechanism_obj = mechanism_data

        # Build full trial objects with v2 schema
        trials_v2 = []
        for t in asset_trials:
            # Handle design - could be string or dict
            design_data = t.get("design", {})
            if isinstance(design_data, str):
                design_obj = {"description": design_data}
            else:
                design_obj = design_data

            # Handle population - could be string or dict
            pop_data = t.get("population", {})
            if isinstance(pop_data, str):
                pop_obj = {"description": pop_data}
            else:
                pop_obj = pop_data

            trial_obj = {
                "trial_name": t.get("trial_name"),
                "nct_id": t.get("nct_id"),
                "phase": t.get("phase"),
                "status": t.get("status"),
                "indication": t.get("indication"),
                "design": design_obj,
                "population": pop_obj,
                "n_enrolled": t.get("n_enrolled"),
                "arms": t.get("arms", []),
                "efficacy_endpoints": t.get("efficacy_endpoints", []),
                "biomarker_endpoints": t.get("biomarker_endpoints", []),
                "safety": t.get("safety", {}),
                "key_takeaways": t.get("key_takeaways", []),
                "limitations": t.get("limitations", []),
                "_source_pages": t.get("source_pages", [])
            }
            trials_v2.append(trial_obj)

        # Build catalyst objects with v2 schema
        catalysts_v2 = []
        for c in asset_catalysts:
            catalyst_obj = {
                "event": c.get("event"),
                "timing": c.get("timing"),
                "importance": c.get("importance"),
                "what_to_watch": c.get("what_to_watch", []),
                "bull_scenario": c.get("bull_scenario"),
                "bear_scenario": c.get("bear_scenario"),
                "_source_page": c.get("source_page")
            }
            catalysts_v2.append(catalyst_obj)

        asset_json = {
            "asset": {
                "name": asset_name,
                "company": company.get("name"),
                "ticker": ticker,
                "target": target_obj,
                "mechanism": mechanism_obj,
                "modality": asset.get("modality"),
                "ownership": asset.get("ownership"),
            },
            "clinical_development": {
                "current_stage": asset.get("stage"),
                "lead_indication": asset.get("lead_indication"),
                "expansion_indications": asset.get("expansion_indications", []),
            },
            "market_opportunity": asset.get("market_opportunity", {}),
            "trials": trials_v2,
            "upcoming_catalysts": catalysts_v2,
            "_source_pages": asset.get("source_pages", [])
        }
        files[filename] = asset_json

    return files
