"""
Satya View Generator using Claude API

Generates bull thesis, bear thesis, and key questions for pipeline assets
based on clinical trial data, competitive landscape, and company filings.
"""

import os
import json
from pathlib import Path
from typing import Optional
import anthropic

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SATYA_VIEW_PROMPT = """You are a biotech equity research analyst generating a "Satya View" for a drug development program.

Given the following information about a pipeline asset, generate:
1. **Bull Thesis** (3-4 sentences): The optimistic investment case - why this could succeed and create value
2. **Bear Thesis** (3-4 sentences): The key risks and reasons for skepticism
3. **Key Question** (1 sentence): The single most important question that upcoming data/catalysts will answer

Be specific, use numbers when available, and focus on what differentiates this asset.

Asset Information:
{asset_info}

Clinical Data Available:
{clinical_data}

Competitive Landscape:
{competitors}

Respond in JSON format:
{{
  "bull_thesis": "...",
  "bear_thesis": "...",
  "key_question": "..."
}}"""


def generate_satya_view(
    asset_name: str,
    target: str,
    indication: str,
    stage: str,
    partner: Optional[str],
    clinical_data: list,
    competitors: list,
    mechanism: Optional[dict] = None
) -> dict:
    """
    Generate a Satya View for a pipeline asset using Claude API.

    Returns:
        dict with bull_thesis, bear_thesis, key_question
    """
    # Format asset info
    asset_info = f"""
Drug: {asset_name}
Target: {target}
Indication: {indication}
Stage: {stage}
Partner: {partner or 'No partner (fully owned)'}
"""

    if mechanism:
        asset_info += f"""
Mechanism: {mechanism.get('modality', 'Unknown')}
Description: {mechanism.get('description', 'Not available')}
Dosing: {mechanism.get('dosing', 'Not specified')}
"""

    # Format clinical data
    clinical_str = ""
    for trial in clinical_data[:3]:  # Limit to top 3 trials
        clinical_str += f"\n- {trial.get('trial_name', 'Unknown')}: {trial.get('phase', '')}"
        if trial.get('results', {}).get('primary'):
            primary = trial['results']['primary']
            clinical_str += f"\n  Primary: {primary.get('endpoint', '')}: {primary.get('result', '')}"
            if primary.get('p_value'):
                clinical_str += f" (p{primary['p_value']})"

    if not clinical_str:
        clinical_str = "No clinical data available yet"

    # Format competitors
    comp_str = ""
    for comp in competitors[:4]:  # Limit to top 4 competitors
        comp_str += f"\n- {comp.get('drug_name', 'Unknown')} ({comp.get('company', '')}): {comp.get('stage', '')}"
        if comp.get('efficacy'):
            comp_str += f" - {comp['efficacy']}"

    if not comp_str:
        comp_str = "No direct competitors identified"

    # Generate using Claude
    prompt = SATYA_VIEW_PROMPT.format(
        asset_info=asset_info,
        clinical_data=clinical_str,
        competitors=comp_str
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        content = response.content[0].text
        # Extract JSON from response (handle potential markdown formatting)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())

    except Exception as e:
        print(f"Error generating Satya View: {e}")
        return {
            "bull_thesis": f"Unable to generate - {asset_name} is in {stage} for {indication}.",
            "bear_thesis": "Unable to generate analysis at this time.",
            "key_question": "What will the next clinical readout show?"
        }


def generate_satya_views_for_company(ticker: str) -> dict:
    """
    Generate Satya Views for all programs in a company's pipeline.

    Args:
        ticker: Company ticker symbol

    Returns:
        Updated pipeline data with generated Satya Views
    """
    pipeline_path = Path(__file__).parent.parent / "data" / "pipeline_data" / f"{ticker.lower()}.json"

    if not pipeline_path.exists():
        raise FileNotFoundError(f"No pipeline data found for {ticker}")

    with open(pipeline_path) as f:
        data = json.load(f)

    updated = False
    for program in data.get("programs", []):
        # Skip if already has satya_view
        if program.get("satya_view"):
            continue

        print(f"Generating Satya View for {program['name']}...")

        satya_view = generate_satya_view(
            asset_name=program["name"],
            target=program.get("target", "Unknown"),
            indication=program.get("indication", "Unknown"),
            stage=program.get("stage", "Unknown"),
            partner=program.get("partner"),
            clinical_data=program.get("clinical_data", []),
            competitors=program.get("competitors", []),
            mechanism=program.get("mechanism")
        )

        program["satya_view"] = satya_view
        updated = True

    if updated:
        with open(pipeline_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Updated {pipeline_path}")

    return data


def generate_competitors_for_program(
    asset_name: str,
    target: str,
    indication: str,
    mechanism: Optional[dict] = None
) -> list:
    """
    Generate competitive landscape analysis for a pipeline program using Claude API.

    Returns:
        List of competitor dicts
    """
    prompt = f"""You are a biotech competitive intelligence analyst.

For the following drug program, identify 3-4 key competitors (approved or in development):

Drug: {asset_name}
Target: {target}
Indication: {indication}
Mechanism: {mechanism.get('modality', 'Unknown') if mechanism else 'Unknown'}

For each competitor, provide:
- drug_name: Name of the drug
- company: Company developing it
- mechanism: How it works (brief)
- stage: Development stage (Preclinical, Phase 1, 2, 3, Approved)
- efficacy: Key efficacy data if available
- differentiation: How the subject drug compares (advantage or disadvantage)

Respond in JSON format as a list of competitor objects.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())

    except Exception as e:
        print(f"Error generating competitors: {e}")
        return []


if __name__ == "__main__":
    # Test generation for ARWR
    import sys

    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
    else:
        ticker = "ARWR"

    print(f"Generating Satya Views for {ticker}...")

    try:
        data = generate_satya_views_for_company(ticker)
        print(f"Successfully generated views for {len(data.get('programs', []))} programs")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
