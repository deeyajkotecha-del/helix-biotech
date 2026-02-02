"""
Figure Annotation Service using Claude Vision API

Analyzes clinical data figures from presentations and generates
structured annotations including chart type, extracted data, and analysis.
"""

import os
import json
import base64
from pathlib import Path
from typing import Optional
from datetime import datetime

import anthropic

# Initialize Anthropic client
client = None
if os.getenv("ANTHROPIC_API_KEY"):
    client = anthropic.Anthropic()

# Data directory
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "figures"
DATA_DIR.mkdir(parents=True, exist_ok=True)


FIGURE_ANALYSIS_PROMPT = """You are a biotech equity research analyst analyzing a clinical trial data figure from an investor presentation.

Analyze this figure and provide:

1. **Figure Type**: Identify the chart type (waterfall plot, line chart, bar chart, Kaplan-Meier curve, forest plot, scatter plot, box plot, spider plot, etc.)

2. **Title/Description**: What does this figure show? Be specific about the endpoint, timepoint, and population.

3. **Extracted Data**: Pull out key quantitative data points visible in the figure:
   - Primary result (e.g., mean change, response rate, etc.)
   - Comparison to placebo/control if shown
   - Statistical significance (p-values if visible)
   - Sample sizes if shown
   - Any subgroup results

4. **Analysis**: Provide 3-4 bullet points of investment-relevant analysis:
   - How does this compare to the competitive landscape?
   - What are the clinical implications?
   - Any concerns or limitations visible in the data?
   - What questions does this raise?

Context about this figure:
- Company: {company}
- Drug: {drug}
- Trial: {trial}
- Indication: {indication}

Respond in JSON format:
{{
  "figure_type": "waterfall_plot",
  "title": "Individual Patient Change in Triglycerides from Baseline at Week 10",
  "description": "Waterfall plot showing percent change in fasting triglycerides for each patient in the PALISADE trial",
  "extracted_data": {{
    "primary_endpoint": "Fasting triglyceride change at Week 10",
    "treatment_result": "-80%",
    "placebo_result": "-11%",
    "p_value": "<0.001",
    "n_treatment": 50,
    "n_placebo": 25,
    "response_rate": "100% achieved >50% reduction",
    "additional_metrics": {{}}
  }},
  "analysis": [
    "Mean TG reduction of 80% significantly exceeds standard of care fibrates (30-50%)",
    "All patients responded (100% achieved >50% reduction), suggesting consistent mechanism",
    "Robust placebo-corrected effect of 69% reduction supports quarterly dosing benefit",
    "Data positions plozasiran as potential best-in-class for severe hypertriglyceridemia"
  ],
  "limitations": ["Small sample size", "Short duration (10 weeks)"],
  "competitive_context": "Superior to Ionis olezarsen (~60% reduction) and Akcea volanesorsen (~77%)"
}}"""


def encode_image(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_image_media_type(image_path: str) -> str:
    """Get media type from file extension."""
    ext = Path(image_path).suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }
    return media_types.get(ext, "image/png")


def annotate_figure(
    image_path: str,
    company: str = "Unknown",
    drug: str = "Unknown",
    trial: str = "Unknown",
    indication: str = "Unknown",
    additional_context: str = ""
) -> dict:
    """
    Analyze a clinical figure using Claude Vision API.

    Args:
        image_path: Path to the figure image
        company: Company name
        drug: Drug name
        trial: Trial name
        indication: Therapeutic indication
        additional_context: Any additional context

    Returns:
        dict with figure analysis
    """
    if not client:
        return {"error": "ANTHROPIC_API_KEY not configured"}

    if not Path(image_path).exists():
        return {"error": f"Image not found: {image_path}"}

    # Prepare the prompt
    prompt = FIGURE_ANALYSIS_PROMPT.format(
        company=company,
        drug=drug,
        trial=trial,
        indication=indication
    )

    if additional_context:
        prompt += f"\n\nAdditional context: {additional_context}"

    # Encode the image
    image_data = encode_image(image_path)
    media_type = get_image_media_type(image_path)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        # Parse response
        content = response.content[0].text

        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())

    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse response: {e}",
            "raw_response": content if 'content' in dir() else None
        }
    except Exception as e:
        return {"error": str(e)}


def annotate_presentation_figures(
    extraction_result: dict,
    asset_name: str,
    trial_name: str,
    indication: str,
    slides_to_analyze: Optional[list] = None
) -> dict:
    """
    Annotate multiple figures from a presentation extraction.

    Args:
        extraction_result: Result from figure_extractor
        asset_name: Name of the drug/asset
        trial_name: Name of the clinical trial
        indication: Therapeutic indication
        slides_to_analyze: Optional list of slide numbers to analyze (default: all)

    Returns:
        dict with annotated figures
    """
    ticker = extraction_result.get("ticker", "UNKNOWN")
    presentation = extraction_result.get("presentation_name", "Unknown Presentation")

    annotated_figures = {
        "asset": asset_name,
        "trial": trial_name,
        "indication": indication,
        "presentation": presentation,
        "source_url": extraction_result.get("source_url"),
        "annotated_at": datetime.utcnow().isoformat(),
        "figures": []
    }

    slides = extraction_result.get("slides", [])

    if slides_to_analyze:
        slides = [s for s in slides if s["slide_number"] in slides_to_analyze]

    for slide in slides:
        print(f"Analyzing slide {slide['slide_number']}...")

        annotation = annotate_figure(
            image_path=slide["path"],
            company=ticker,
            drug=asset_name,
            trial=trial_name,
            indication=indication
        )

        if "error" not in annotation:
            figure_data = {
                "id": f"{ticker.lower()}-{trial_name.lower().replace(' ', '-')}-slide-{slide['slide_number']}",
                "source": presentation,
                "source_url": extraction_result.get("source_url"),
                "slide_number": slide["slide_number"],
                "image_path": slide.get("web_path", slide["path"]),
                "figure_type": annotation.get("figure_type"),
                "title": annotation.get("title"),
                "description": annotation.get("description"),
                "extracted_data": annotation.get("extracted_data", {}),
                "analysis": annotation.get("analysis", []),
                "limitations": annotation.get("limitations", []),
                "competitive_context": annotation.get("competitive_context")
            }
            annotated_figures["figures"].append(figure_data)
        else:
            print(f"  Error: {annotation['error']}")

    return annotated_figures


def save_annotations(ticker: str, annotations: dict) -> Path:
    """Save annotations to JSON file."""
    filename = DATA_DIR / f"{ticker.lower()}.json"

    # Load existing data if present
    existing = {}
    if filename.exists():
        with open(filename) as f:
            existing = json.load(f)

    # Merge annotations by asset
    asset_name = annotations.get("asset")
    if "assets" not in existing:
        existing["assets"] = {}

    if asset_name not in existing["assets"]:
        existing["assets"][asset_name] = {"trials": {}}

    trial_name = annotations.get("trial")
    existing["assets"][asset_name]["trials"][trial_name] = annotations

    existing["updated_at"] = datetime.utcnow().isoformat()

    with open(filename, "w") as f:
        json.dump(existing, f, indent=2)

    return filename


def load_annotations(ticker: str) -> dict:
    """Load annotations for a ticker."""
    filename = DATA_DIR / f"{ticker.lower()}.json"

    if not filename.exists():
        return {}

    with open(filename) as f:
        return json.load(f)


def get_figures_for_asset(ticker: str, asset_name: str) -> list:
    """Get all figures for a specific asset."""
    data = load_annotations(ticker)

    if not data or "assets" not in data:
        return []

    asset_data = data["assets"].get(asset_name, {})
    all_figures = []

    for trial_name, trial_data in asset_data.get("trials", {}).items():
        for fig in trial_data.get("figures", []):
            fig["trial"] = trial_name
            all_figures.append(fig)

    return all_figures


if __name__ == "__main__":
    # Test annotation
    import sys

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        result = annotate_figure(
            image_path=image_path,
            company="ARWR",
            drug="Plozasiran",
            trial="PALISADE",
            indication="FCS"
        )
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python figure_annotator.py <image_path>")
        print("\nChecking API configuration...")
        if client:
            print("ANTHROPIC_API_KEY is configured")
        else:
            print("ANTHROPIC_API_KEY is NOT configured")
