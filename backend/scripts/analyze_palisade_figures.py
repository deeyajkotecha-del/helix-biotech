#!/usr/bin/env python3
"""
Analyze PALISADE clinical figures using Claude Vision API.
Usage: ANTHROPIC_API_KEY=sk-xxx python3 analyze_palisade_figures.py
"""

import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime

# Check for API key
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("ERROR: ANTHROPIC_API_KEY environment variable not set")
    print("Usage: ANTHROPIC_API_KEY=sk-xxx python3 analyze_palisade_figures.py")
    sys.exit(1)

import anthropic

client = anthropic.Anthropic()

FIGURES_DIR = Path(__file__).parent.parent.parent / "app" / "public" / "figures" / "arwr" / "palisade"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "figures" / "arwr.json"

# Key slides to analyze
KEY_SLIDES = [30, 31, 34, 35, 36]

ANALYSIS_PROMPT = """You are a biotech equity research analyst analyzing a clinical trial data figure from the PALISADE Phase 3 study of plozasiran (ARO-APOC3) in patients with Familial Chylomicronemia Syndrome (FCS).

Analyze this figure and provide:

1. **Figure Type**: Identify the chart type (waterfall plot, line chart, bar chart, Kaplan-Meier curve, table, etc.)

2. **Title**: A concise descriptive title for this figure

3. **Description**: What does this figure show? Be specific about the endpoint, timepoint, and population.

4. **Extracted Data**: Pull out key quantitative data points visible in the figure:
   - Primary result (e.g., mean change, response rate, hazard ratio, etc.)
   - Comparison to placebo/control if shown
   - Statistical significance (p-values if visible)
   - Sample sizes if shown

5. **Analysis**: Provide 3-4 bullet points of investment-relevant analysis:
   - How do these results compare to the competitive landscape?
   - What are the clinical implications?
   - What does this mean for the investment thesis?

6. **Limitations**: Any caveats or limitations visible in the data

7. **Competitive Context**: How does this compare to competitors like volanesorsen, olezarsen, or fibrates?

Respond ONLY with valid JSON (no markdown, no explanation), in this format:
{
  "figure_type": "bar_chart",
  "title": "Primary Endpoint: TG and APOC3 Reduction at Month 10",
  "description": "Bar chart showing median percent change from baseline in triglycerides and APOC3",
  "extracted_data": {
    "primary_endpoint": "TG change at Month 10",
    "treatment_result": "-80%",
    "placebo_result": "-17%",
    "p_value": "<0.0001",
    "n_treatment": 46,
    "n_placebo": 19
  },
  "analysis": [
    "80% TG reduction significantly exceeds standard of care fibrates (30-50%)",
    "Consistent effect across both 25mg and 50mg dose groups",
    "Near-complete APOC3 knockdown (-96%) validates RNAi mechanism"
  ],
  "limitations": ["12-month data only", "Small sample size"],
  "competitive_context": "Superior to volanesorsen (~77%) and olezarsen (~60%)"
}"""

def encode_image(path):
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")

def analyze_figure(slide_num):
    image_path = FIGURES_DIR / f"slide-{slide_num:02d}.png"
    if not image_path.exists():
        print(f"    Image not found: {image_path}")
        return None

    print(f"  Analyzing slide {slide_num}...")

    image_data = encode_image(image_path)

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
                            "media_type": "image/png",
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": ANALYSIS_PROMPT
                    }
                ]
            }
        ]
    )

    content = response.content[0].text

    # Extract JSON from response
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    try:
        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        print(f"    Failed to parse JSON: {e}")
        print(f"    Raw content: {content[:300]}...")
        return None


def main():
    print(f"Figures directory: {FIGURES_DIR}")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Analyzing PALISADE figures with Claude Vision API...")

    figures = []

    for slide_num in KEY_SLIDES:
        result = analyze_figure(slide_num)
        if result:
            figure_data = {
                "id": f"arwr-palisade-slide-{slide_num}",
                "source": "ESC 2024 Investor Webinar - PALISADE Results",
                "source_url": "https://ir.arrowheadpharma.com/events/event-details/investor-conference-call-plozasiran-palisade-results-esc-2024",
                "slide_number": slide_num,
                "image_path": f"/figures/arwr/palisade/slide-{slide_num:02d}.png",
                "figure_type": result.get("figure_type"),
                "title": result.get("title"),
                "description": result.get("description"),
                "extracted_data": result.get("extracted_data", {}),
                "analysis": result.get("analysis", []),
                "limitations": result.get("limitations", []),
                "competitive_context": result.get("competitive_context"),
                "citation_number": 1
            }
            figures.append(figure_data)
            title = result.get('title', 'Unknown')
            print(f"    Done: {title[:60]}...")

    # Build output structure
    output = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "assets": {
            "Plozasiran": {
                "trials": {
                    "PALISADE": {
                        "asset": "Plozasiran",
                        "trial": "PALISADE",
                        "indication": "Familial Chylomicronemia Syndrome (FCS)",
                        "presentation": "ESC 2024 Investor Webinar - PALISADE Phase 3 Results",
                        "source_url": "https://ir.arrowheadpharma.com/events/event-details/investor-conference-call-plozasiran-palisade-results-esc-2024",
                        "annotated_at": datetime.utcnow().isoformat() + "Z",
                        "figures": figures
                    }
                }
            }
        }
    }

    # Save output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved {len(figures)} figures to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
