#!/usr/bin/env python3
"""
Clinical Figure Analysis using Claude Vision API

Extracts numerical data and generates investment-grade analysis from
clinical trial presentation slides.
"""

import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime

# Check for API key first
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("ERROR: ANTHROPIC_API_KEY environment variable not set")
    print("Usage: ANTHROPIC_API_KEY=sk-xxx python3 analyze_figures_vision.py")
    sys.exit(1)

import anthropic

client = anthropic.Anthropic()

# Paths
FIGURES_DIR = Path(__file__).parent.parent.parent / "app" / "public" / "figures" / "arwr" / "palisade"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "figures" / "arwr.json"

# Figure-specific prompts for maximum data extraction
FIGURE_PROMPTS = {
    30: """This is a bar chart showing the primary endpoint results from the PALISADE Phase 3 trial of plozasiran in FCS patients.

EXTRACT ALL NUMERICAL DATA:
1. Triglyceride (TG) reduction percentages for each treatment arm (placebo, 25mg, 50mg)
2. APOC3 reduction percentages for each treatment arm
3. P-values for each comparison
4. Sample sizes (n) for each arm
5. Timepoints (Month 10, Month 10/12 average)
6. Any confidence intervals shown

PROVIDE INVESTMENT ANALYSIS:
- Key takeaway (1 sentence summarizing the result)
- Clinical significance (what does 80% TG reduction mean for FCS patients?)
- Competitive context (compare to Tryngolza/volanesorsen ~77%, olezarsen ~60%, fibrates 30-50%)
- Investment implication (what does this mean for ARWR stock, market opportunity, pricing power?)""",

    31: """This is a time-course line chart showing durability of TG and APOC3 reduction over 12 months from the PALISADE trial.

EXTRACT ALL NUMERICAL DATA:
1. TG reduction at each timepoint (Month 1, 2, 3, etc.)
2. APOC3 reduction at each timepoint
3. Placebo response over time
4. Error bars/variability if shown
5. Dosing interval (Q3M = quarterly)

PROVIDE INVESTMENT ANALYSIS:
- Key takeaway (is the effect durable with quarterly dosing?)
- Clinical significance (what does sustained effect mean for patient compliance?)
- Competitive context (compare dosing to volanesorsen weekly, olezarsen monthly)
- Investment implication (quarterly dosing = convenience advantage, potential pricing premium)""",

    34: """This is a waterfall plot showing individual patient TG responses, with a responder analysis table below.

EXTRACT ALL NUMERICAL DATA:
1. Percentage of patients achieving different TG thresholds:
   - <500 mg/dL (5.5 mmol/L) - low risk threshold
   - <880 mg/dL (10 mmol/L) - moderate risk threshold
   - <1000 mg/dL (11 mmol/L)
2. Response rates by treatment arm (25mg vs 50mg vs placebo)
3. Range of individual responses (best responder, worst responder)
4. Proportion achieving >50% TG reduction

PROVIDE INVESTMENT ANALYSIS:
- Key takeaway (what % of patients achieve clinically meaningful response?)
- Clinical significance (reaching <500 mg/dL dramatically reduces pancreatitis risk)
- Competitive context (responder rates vs other APOC3 therapies)
- Investment implication (high responder rate = predictable clinical benefit, supports broad label)""",

    35: """This is a Kaplan-Meier survival curve showing time to first acute pancreatitis event.

EXTRACT ALL NUMERICAL DATA:
1. Event rate in plozasiran arm (number and percentage)
2. Event rate in placebo arm (number and percentage)
3. Odds ratio or hazard ratio
4. 95% confidence interval
5. P-value
6. Relative risk reduction percentage
7. Number at risk at each timepoint

PROVIDE INVESTMENT ANALYSIS:
- Key takeaway (83% reduction in pancreatitis - the most feared FCS complication)
- Clinical significance (pancreatitis is life-threatening, drives FCS morbidity)
- Competitive context (first APOC3 therapy to show pancreatitis reduction in Phase 3)
- Investment implication (clinical outcome data strengthens FDA label, supports premium pricing, differentiates from competitors)""",

    36: """This is a safety summary table showing adverse events from the PALISADE trial.

EXTRACT ALL NUMERICAL DATA:
1. Any TEAE rates by arm
2. Serious TEAE rates by arm
3. Discontinuation rates by arm
4. Deaths (should be 0)
5. Specific AEs of interest:
   - Injection site reactions
   - Platelet counts (critical vs volanesorsen)
   - Liver enzymes
6. HbA1c changes

PROVIDE INVESTMENT ANALYSIS:
- Key takeaway (clean safety profile, no platelet issues unlike volanesorsen)
- Clinical significance (no boxed warning needed, no monitoring requirements)
- Competitive context (volanesorsen has thrombocytopenia boxed warning requiring platelet monitoring)
- Investment implication (better safety = broader prescriber adoption, no REMS needed, commercial advantage)"""
}

GENERAL_PROMPT = """You are a senior biotech equity research analyst at a top investment bank. Analyze this clinical trial figure and extract investment-grade insights.

EXTRACT ALL NUMERICAL DATA visible in the figure:
- Percentages, p-values, sample sizes, confidence intervals
- Timepoints, doses, comparator results
- Any statistical measures shown

PROVIDE INVESTMENT ANALYSIS with these sections:
1. KEY_TAKEAWAY: One sentence summary of the most important finding
2. CLINICAL_SIGNIFICANCE: What does this mean for patients? Why does it matter clinically?
3. COMPETITIVE_CONTEXT: How does this compare to competing drugs (volanesorsen/Tryngolza, olezarsen, fibrates)?
4. INVESTMENT_IMPLICATION: What does this mean for the stock? Market opportunity? Pricing power? Regulatory path?

Context: This is from the PALISADE Phase 3 trial of plozasiran (ARO-APOC3), an RNAi therapeutic for Familial Chylomicronemia Syndrome (FCS). FCS patients have extremely high triglycerides (>880 mg/dL) and recurrent pancreatitis. Plozasiran targets APOC3 to reduce triglycerides.

Respond in JSON format:
{
  "figure_type": "bar_chart|line_chart|waterfall_plot|kaplan_meier|table",
  "title": "Descriptive title",
  "extracted_data": {
    "primary_endpoint": "what was measured",
    "treatment_result": "main efficacy result",
    "placebo_result": "comparator result",
    "p_value": "statistical significance",
    "additional_metrics": {}
  },
  "analysis": {
    "key_takeaway": "One sentence summary",
    "clinical_significance": "Patient impact explanation",
    "competitive_context": "vs Tryngolza, olezarsen, fibrates",
    "investment_implication": "Stock/market implications"
  },
  "limitations": ["list of caveats"],
  "data_quality": "high|medium|low"
}"""


def encode_image(path: Path) -> str:
    """Encode image to base64."""
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def analyze_figure(slide_num: int) -> dict:
    """Analyze a single figure using Claude Vision."""
    image_path = FIGURES_DIR / f"slide-{slide_num:02d}.png"

    if not image_path.exists():
        print(f"  ERROR: Image not found: {image_path}")
        return None

    print(f"  Analyzing slide {slide_num} with Claude Vision...")

    # Use figure-specific prompt if available, otherwise general
    prompt = FIGURE_PROMPTS.get(slide_num, GENERAL_PROMPT)
    full_prompt = f"""{prompt}

Respond ONLY with valid JSON (no markdown code blocks, no explanation text).
Start your response with {{ and end with }}"""

    image_data = encode_image(image_path)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
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
                            "text": full_prompt
                        }
                    ]
                }
            ]
        )

        content = response.content[0].text.strip()

        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        # Find JSON boundaries
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            content = content[start:end]

        return json.loads(content)

    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e}")
        print(f"    Raw content: {content[:500]}...")
        return None
    except Exception as e:
        print(f"    API error: {e}")
        return None


def build_figure_entry(slide_num: int, analysis: dict) -> dict:
    """Build a complete figure entry for the JSON."""

    # Convert nested analysis to flat bullet points for UI
    analysis_bullets = []
    if "analysis" in analysis:
        a = analysis["analysis"]
        if isinstance(a, dict):
            if a.get("key_takeaway"):
                analysis_bullets.append(f"Key Finding: {a['key_takeaway']}")
            if a.get("clinical_significance"):
                analysis_bullets.append(f"Clinical Impact: {a['clinical_significance']}")
            if a.get("competitive_context"):
                analysis_bullets.append(f"vs Competition: {a['competitive_context']}")
            if a.get("investment_implication"):
                analysis_bullets.append(f"Investment View: {a['investment_implication']}")
        elif isinstance(a, list):
            analysis_bullets = a

    # Extract key data points for display
    extracted = analysis.get("extracted_data", {})

    return {
        "id": f"arwr-palisade-slide-{slide_num}",
        "source": "ESC 2024 Investor Webinar - PALISADE Results",
        "source_url": "https://ir.arrowheadpharma.com/events/event-details/investor-conference-call-plozasiran-palisade-results-esc-2024",
        "slide_number": slide_num,
        "image_path": f"/figures/arwr/palisade/slide-{slide_num:02d}.png",
        "figure_type": analysis.get("figure_type", "unknown"),
        "title": analysis.get("title", f"PALISADE Slide {slide_num}"),
        "description": analysis.get("description", ""),
        "extracted_data": extracted,
        "analysis": analysis_bullets,
        "satya_analysis": analysis.get("analysis", {}),  # Keep structured analysis
        "limitations": analysis.get("limitations", []),
        "data_quality": analysis.get("data_quality", "medium"),
        "competitive_context": analysis.get("analysis", {}).get("competitive_context", ""),
        "citation_number": 1,
        "analyzed_at": datetime.utcnow().isoformat() + "Z"
    }


def main():
    print("=" * 60)
    print("PALISADE Clinical Figure Analysis")
    print("Using Claude Vision API for Investment-Grade Insights")
    print("=" * 60)

    # Key slides to analyze
    slides = [30, 31, 34, 35, 36]

    figures = []

    for slide_num in slides:
        analysis = analyze_figure(slide_num)
        if analysis:
            figure = build_figure_entry(slide_num, analysis)
            figures.append(figure)
            print(f"    Title: {figure['title'][:60]}...")
            print(f"    Type: {figure['figure_type']}")
            if figure.get('satya_analysis', {}).get('key_takeaway'):
                print(f"    Key: {figure['satya_analysis']['key_takeaway'][:80]}...")
            print()
        else:
            print(f"    FAILED to analyze slide {slide_num}")
            print()

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

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print("=" * 60)
    print(f"Saved {len(figures)} analyzed figures to {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
