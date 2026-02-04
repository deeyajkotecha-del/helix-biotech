"""
AI-Powered Clinical Data Extractor

Uses Claude API to extract structured clinical data from PDF presentations.
Outputs JSON matching our data/companies/{TICKER}/ schema.
"""

import os
import json
import logging
from typing import Optional
from datetime import datetime

import anthropic

logger = logging.getLogger(__name__)

# Default model for extraction
DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AIExtractor:
    """Extract structured clinical data from text using Claude."""

    def __init__(self, api_key: str = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable required")

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
        """Build the extraction prompt for Claude."""

        return f'''You are a PhD-level biotechnology analyst extracting structured data from an investor presentation.

COMPANY: {ticker}{f" ({company_name})" if company_name else ""}

Extract data from the following presentation text. The text includes [PAGE X] markers - ALWAYS cite page numbers in your extractions for traceability.

<presentation_text>
{pdf_text}
</presentation_text>

Extract and return a JSON object with this exact structure:

```json
{{
  "company": {{
    "name": "Company Name",
    "ticker": "{ticker}",
    "description": "2-3 sentence company description",
    "headquarters": "City, State if found",
    "website": "URL if found",
    "modality": "Small molecule / Antibody / Gene therapy / etc.",
    "therapeutic_focus": ["Area 1", "Area 2"],
    "source_pages": [1, 2]
  }},

  "financials": {{
    "cash_mm": null,
    "cash_runway": "Statement like 'Into 2027'",
    "market_cap": "If mentioned",
    "source_pages": []
  }},

  "pipeline_assets": [
    {{
      "name": "Asset name (e.g., KT-621)",
      "target": "Target protein/pathway",
      "mechanism": "Mechanism of action",
      "modality": "Small molecule degrader / mAb / etc.",
      "stage": "Phase 1 / Phase 2 / etc.",
      "lead_indication": "Primary indication",
      "other_indications": ["Other indication 1"],
      "partner": "Partner company if any",
      "source_pages": [5, 6, 7]
    }}
  ],

  "clinical_trials": [
    {{
      "asset": "Asset name",
      "trial_name": "Trial name if given",
      "nct_id": "NCT number if shown",
      "phase": "Phase 1 / Phase 2 / etc.",
      "indication": "Indication being studied",
      "status": "Ongoing / Completed / Planned",
      "design": "Trial design description",
      "population": "Patient population",
      "n_enrolled": null,
      "arms": [
        {{"name": "Arm name", "dose": "Dose", "n": null}}
      ],
      "primary_endpoint": "Primary endpoint",
      "key_results": [
        {{
          "endpoint": "Endpoint name",
          "result": "Result value",
          "timepoint": "When measured",
          "p_value": null,
          "vs_comparator": "Comparison if given"
        }}
      ],
      "safety_summary": "Safety summary if provided",
      "source_pages": [10, 11, 12]
    }}
  ],

  "investment_thesis": [
    {{
      "point": "Key investment thesis point",
      "source_page": 3
    }}
  ],

  "key_risks": [
    {{
      "risk": "Key risk",
      "source_page": 25
    }}
  ],

  "upcoming_catalysts": [
    {{
      "event": "Catalyst description",
      "timing": "Expected timing (Q1 2027, 2H 2027, etc.)",
      "asset": "Related asset",
      "source_page": 4
    }}
  ],

  "partnerships": [
    {{
      "partner": "Partner name",
      "asset": "Asset involved",
      "deal_value": "Deal terms if disclosed",
      "status": "Active / Completed",
      "source_page": 20
    }}
  ],

  "competitive_landscape": [
    {{
      "competitor": "Competitor name",
      "asset": "Their asset",
      "differentiation": "How company differentiates",
      "source_page": 15
    }}
  ]
}}
```

IMPORTANT GUIDELINES:
1. ALWAYS include source_page or source_pages for EVERY piece of data
2. Use null for missing numeric values, not "N/A" or empty strings
3. Extract ALL pipeline assets mentioned, even if limited data
4. For clinical results, include exact numbers and statistical values when shown
5. Capture comparator benchmarks (e.g., "vs Dupixent: 70% at Week 16")
6. If data is ambiguous or unclear, include a "_notes" field with your interpretation
7. Extract cash/runway information if mentioned (usually in financial slides)
8. Capture mechanism of action details for each asset

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


def convert_to_file_format(extracted_data: dict, ticker: str) -> dict:
    """
    Convert extracted data to our file format for saving.

    Returns dict with:
    - "company.json": company data
    - "{asset_name}.json": asset data for each asset
    """
    ticker = ticker.upper()
    files = {}

    # Build company.json
    company = extracted_data.get("company", {})
    company_json = {
        "name": company.get("name"),
        "ticker": ticker,
        "headquarters": company.get("headquarters"),
        "website": company.get("website"),
        "description": company.get("description"),
        "modalities": [company.get("modality")] if company.get("modality") else [],
        "therapeutic_focus": company.get("therapeutic_focus", []),
        "cash_runway": extracted_data.get("financials", {}).get("cash_runway"),
        "partnerships": extracted_data.get("partnerships", []),
        "investment_thesis": [p.get("point") for p in extracted_data.get("investment_thesis", [])],
        "key_risks": [r.get("risk") for r in extracted_data.get("key_risks", [])],
        "_source_pages": company.get("source_pages", []),
        "_extracted_at": extracted_data.get("_extraction_metadata", {}).get("extracted_at")
    }
    files["company.json"] = company_json

    # Build asset files
    for asset in extracted_data.get("pipeline_assets", []):
        asset_name = asset.get("name", "unknown")
        # Normalize filename: KT-621 -> kt621.json
        filename = asset_name.lower().replace("-", "").replace(" ", "") + ".json"

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

        asset_json = {
            "asset": {
                "name": asset_name,
                "company": company.get("name"),
                "ticker": ticker,
                "target": asset.get("target"),
                "mechanism": asset.get("mechanism"),
                "modality": asset.get("modality"),
                "partner": asset.get("partner")
            },
            "clinical_development": {
                "current_stage": asset.get("stage"),
                "indications_in_development": (
                    [asset.get("lead_indication")] +
                    asset.get("other_indications", [])
                )
            },
            "trials": [
                {
                    "name": t.get("trial_name"),
                    "nct_id": t.get("nct_id"),
                    "phase": t.get("phase"),
                    "status": t.get("status"),
                    "indication": t.get("indication"),
                    "design": t.get("design"),
                    "population": t.get("population"),
                    "arms": t.get("arms", []),
                    "primary_endpoint": t.get("primary_endpoint"),
                    "endpoints": t.get("key_results", []),
                    "safety": t.get("safety_summary"),
                    "_source_pages": t.get("source_pages", [])
                }
                for t in asset_trials
            ],
            "investment_thesis": [p.get("point") for p in extracted_data.get("investment_thesis", [])
                                  if asset_name.lower() in p.get("point", "").lower()],
            "key_risks": [r.get("risk") for r in extracted_data.get("key_risks", [])
                         if asset_name.lower() in r.get("risk", "").lower()],
            "upcoming_catalysts": [
                {"event": c.get("event"), "timing": c.get("timing")}
                for c in asset_catalysts
            ],
            "_source_pages": asset.get("source_pages", [])
        }
        files[filename] = asset_json

    return files
