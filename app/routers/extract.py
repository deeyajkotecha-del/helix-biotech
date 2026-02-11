"""PDF extraction demo router - YC demo page for AI clinical data extraction."""
import os
import json
import base64
import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.pages import _render_head, _render_nav

router = APIRouter()

# =============================================================================
# MOCK DATA FOR DEMO (CIRRUS-HCM style)
# =============================================================================

MOCK_EXTRACTION = {
    "drug_name": "Aficamten (CK-3773274)",
    "company": "Cytokinetics",
    "target": "Cardiac myosin",
    "mechanism": "Next-generation selective cardiac myosin inhibitor that reduces excess contractility by decreasing the number of actin-myosin cross-bridges, with a shorter half-life enabling more precise LVEF titration than mavacamten.",
    "indication": "Symptomatic obstructive hypertrophic cardiomyopathy (oHCM)",
    "trial_phase": "Phase 2",
    "trial_design": "Open-label, dose-finding study (CIRRUS-HCM). Sequential dose titration from 5mg to 10mg to 15mg QD over 10 weeks based on LVOT gradient and LVEF response. No placebo arm. 4-week treatment periods per dose level with echocardiographic monitoring.",
    "key_takeaway": "Aficamten demonstrated rapid, dose-dependent reductions in LVOT gradients and NT-proBNP with robust symptomatic improvement (65% NYHA improvement, KCCQ +11.2 points) in oHCM patients. Critically, no patient experienced LVEF <50%, a key differentiator vs. mavacamten's REMS requirement. The clean LVEF safety profile may support a simpler label without mandatory echo monitoring, which would be a significant commercial advantage.",
    "patient_population": {
        "n": 41,
        "inclusion_criteria": "Adults >= 18 years with symptomatic oHCM, NYHA class II-III, LVEF >= 60%, resting LVOT gradient >= 30 mmHg or provoked >= 50 mmHg, on stable background medical therapy",
        "demographics": "Mean age 59 years, 54% male, mean BMI 30.1"
    },
    "baseline_characteristics": {
        "columns": ["Parameter", "All Patients (N=41)"],
        "rows": [
            {"parameter": "Age, years (mean +/- SD)", "values": ["58.7 +/- 12.4"]},
            {"parameter": "Female, n (%)", "values": ["19 (46%)"]},
            {"parameter": "BMI, kg/m2 (mean +/- SD)", "values": ["30.1 +/- 5.8"]},
            {"parameter": "Sarcomere variant positive, n (%)", "values": ["18 (44%)"]},
            {"parameter": "NYHA Class II, n (%)", "values": ["30 (73%)"]},
            {"parameter": "NYHA Class III, n (%)", "values": ["11 (27%)"]},
            {"parameter": "Prior septal reduction therapy, n (%)", "values": ["3 (7%)"]},
            {"parameter": "ICD present, n (%)", "values": ["8 (20%)"]},
            {"parameter": "History of atrial fibrillation, n (%)", "values": ["9 (22%)"]},
            {"parameter": "Beta-blocker use, n (%)", "values": ["31 (76%)"]},
            {"parameter": "Calcium channel blocker use, n (%)", "values": ["7 (17%)"]},
            {"parameter": "LVEF, % (mean +/- SD)", "values": ["71.2 +/- 5.8"]},
            {"parameter": "Resting LVOT-G, mmHg (mean +/- SD)", "values": ["55.3 +/- 28.6"]},
            {"parameter": "Valsalva LVOT-G, mmHg (mean +/- SD)", "values": ["73.8 +/- 32.1"]},
            {"parameter": "Septal e', cm/s (mean +/- SD)", "values": ["5.8 +/- 1.9"]},
            {"parameter": "KCCQ-OSS (mean +/- SD)", "values": ["68.4 +/- 18.2"]},
            {"parameter": "KCCQ-CSS (mean +/- SD)", "values": ["71.1 +/- 17.5"]},
            {"parameter": "NT-proBNP, pg/mL (median [IQR])", "values": ["892 [412-1,680]"]}
        ]
    },
    "efficacy_endpoints": [
        {
            "name": "Resting LVOT gradient",
            "population": "oHCM",
            "dose": "10mg",
            "baseline": "55.3 mmHg",
            "value": "18.2 mmHg",
            "change": "-37.1 mmHg (-67%)",
            "timepoint": "Week 8",
            "p_value": "<0.001",
            "n": 38,
            "confidence": "high"
        },
        {
            "name": "Valsalva LVOT gradient",
            "population": "oHCM",
            "dose": "10mg",
            "baseline": "73.8 mmHg",
            "value": "28.5 mmHg",
            "change": "-45.3 mmHg (-61%)",
            "timepoint": "Week 8",
            "p_value": "<0.001",
            "n": 38,
            "confidence": "high"
        },
        {
            "name": "LVOT gradient <30 mmHg (resting)",
            "population": "oHCM",
            "dose": "All doses",
            "baseline": "N/A",
            "value": "82% achieved",
            "change": "N/A",
            "timepoint": "End of study",
            "p_value": None,
            "n": 41,
            "confidence": "high"
        },
        {
            "name": "NT-proBNP",
            "population": "oHCM",
            "dose": "10mg",
            "baseline": "892 pg/mL",
            "value": "285 pg/mL",
            "change": "-68% (geometric mean ratio)",
            "timepoint": "Week 8",
            "p_value": "<0.001",
            "n": 38,
            "confidence": "high"
        },
        {
            "name": "KCCQ-CSS",
            "population": "oHCM",
            "dose": "All doses",
            "baseline": "71.1",
            "value": "82.3",
            "change": "+11.2 points",
            "timepoint": "End of study",
            "p_value": "0.002",
            "n": 41,
            "confidence": "high"
        },
        {
            "name": "KCCQ responder rate (>= 5pt improvement)",
            "population": "oHCM",
            "dose": "All doses",
            "baseline": "N/A",
            "value": "72% responders",
            "change": "N/A",
            "timepoint": "End of study",
            "p_value": None,
            "n": 41,
            "confidence": "high"
        },
        {
            "name": "NYHA class improvement >= 1 class",
            "population": "oHCM",
            "dose": "All doses",
            "baseline": "N/A",
            "value": "65% improved",
            "change": "N/A",
            "timepoint": "End of study",
            "p_value": None,
            "n": 41,
            "confidence": "high"
        },
        {
            "name": "Septal e' velocity",
            "population": "oHCM",
            "dose": "10mg",
            "baseline": "5.8 cm/s",
            "value": "7.4 cm/s",
            "change": "+1.6 cm/s (+28%)",
            "timepoint": "Week 8",
            "p_value": "0.008",
            "n": 38,
            "confidence": "medium"
        }
    ],
    "time_course_data": [
        {
            "endpoint": "NT-proBNP % change from baseline",
            "unit": "%",
            "data": [
                {"timepoint": "Week 1", "dose": "5mg", "value": -18},
                {"timepoint": "Week 2", "dose": "5mg", "value": -32},
                {"timepoint": "Week 4", "dose": "5mg", "value": -41},
                {"timepoint": "Week 4", "dose": "10mg", "value": -55},
                {"timepoint": "Week 8", "dose": "10mg", "value": -68},
                {"timepoint": "EOS", "dose": "10-15mg", "value": -72}
            ]
        },
        {
            "endpoint": "Septal e' % change from baseline",
            "unit": "%",
            "data": [
                {"timepoint": "Week 2", "dose": "5mg", "value": 8},
                {"timepoint": "Week 4", "dose": "5mg", "value": 15},
                {"timepoint": "Week 4", "dose": "10mg", "value": 22},
                {"timepoint": "Week 8", "dose": "10mg", "value": 28},
                {"timepoint": "EOS", "dose": "10-15mg", "value": 31}
            ]
        },
        {
            "endpoint": "KCCQ improvement distribution",
            "unit": "% of patients",
            "data": [
                {"timepoint": "EOS", "dose": "All", "value": "Very large (>20pt): 34%"},
                {"timepoint": "EOS", "dose": "All", "value": "Large (10-20pt): 22%"},
                {"timepoint": "EOS", "dose": "All", "value": "Moderate (5-10pt): 17%"},
                {"timepoint": "EOS", "dose": "All", "value": "Small (<5pt): 15%"},
                {"timepoint": "EOS", "dose": "All", "value": "No change/worsening: 12%"}
            ]
        },
        {
            "endpoint": "NYHA class distribution over time",
            "unit": "n",
            "data": [
                {"timepoint": "Baseline", "dose": "All", "value": "Class I: 0, Class II: 30, Class III: 11"},
                {"timepoint": "Week 4", "dose": "5mg", "value": "Class I: 5, Class II: 28, Class III: 8"},
                {"timepoint": "Week 8", "dose": "10mg", "value": "Class I: 12, Class II: 24, Class III: 5"},
                {"timepoint": "EOS", "dose": "All", "value": "Class I: 15, Class II: 22, Class III: 4"}
            ]
        }
    ],
    "safety": {
        "teae_table": {
            "columns": ["Event", "n (%)", "N=41"],
            "rows": [
                {"event": "Any TEAE", "values": ["28 (68%)"]},
                {"event": "Headache", "values": ["6 (15%)"]},
                {"event": "Dizziness", "values": ["5 (12%)"]},
                {"event": "Fatigue", "values": ["4 (10%)"]},
                {"event": "Nausea", "values": ["3 (7%)"]},
                {"event": "Upper respiratory tract infection", "values": ["3 (7%)"]},
                {"event": "Palpitations", "values": ["3 (7%)"]},
                {"event": "Dyspnea", "values": ["2 (5%)"]},
                {"event": "Diarrhea", "values": ["2 (5%)"]},
                {"event": "Arthralgia", "values": ["2 (5%)"]},
                {"event": "Back pain", "values": ["2 (5%)"]},
                {"event": "Insomnia", "values": ["1 (2%)"]},
                {"event": "Peripheral edema", "values": ["1 (2%)"]},
                {"event": "Atrial fibrillation", "values": ["1 (2%)"]},
                {"event": "Cough", "values": ["1 (2%)"]}
            ]
        },
        "serious_adverse_events": [
            "Atrial fibrillation: 1 patient (2%), pre-existing history, resolved without drug discontinuation",
            "Syncope: 1 patient (2%), unrelated to study drug per investigator assessment"
        ],
        "discontinuation_details": "1 patient (2%) discontinued due to AE (dizziness at 15mg dose level). No discontinuations at 5mg or 10mg doses.",
        "lvef_safety": {
            "narrative": "No patient experienced LVEF <50% at any point during the study, including during dose up-titration. This is a critical differentiator from mavacamten, which saw LVEF <50% in 5.6% of EXPLORER-HCM patients and requires a REMS program with mandatory echocardiographic monitoring every 12 weeks.",
            "findings": [
                "0/41 patients (0%) experienced LVEF <50% at any timepoint",
                "Mean LVEF change from baseline: -3.8% (from 71.2% to 67.4%) at peak dose",
                "All LVEF values remained within normal range (>55%) throughout the study",
                "4 nHCM patients with baseline LVEF 55-60% remained stable (mean change +2.5%)",
                "9 patients with history of atrial fibrillation: none experienced LVEF <50%",
                "Shorter half-life (~3.5 days vs ~9 days for mavacamten) allows faster LVEF recovery if needed"
            ]
        },
        "key_signals": [
            "Favorable safety profile supports potential for label without mandatory REMS/echo monitoring",
            "No drug-drug interaction concerns with CYP2C19 (unlike mavacamten)",
            "Dose-dependent mild systolic function reduction as expected from mechanism, all within normal range"
        ]
    },
    "regulatory_status": "Phase 3 SEQUOIA-HCM trial completed. NDA submission planned. Breakthrough Therapy Designation granted by FDA for oHCM.",
    "next_catalyst": "SEQUOIA-HCM Phase 3 topline results (primary: exercise capacity + NYHA composite); NDA filing timeline; potential label differentiation vs. CAMZYOS on REMS requirement",
    "study_limitations": [
        "Open-label design without placebo control limits causal inference",
        "Small sample size (N=41) limits safety signal detection",
        "Short treatment duration (4 weeks per dose level, 10-12 weeks total)",
        "Sequential dose-escalation design (not randomized to dose groups)",
        "Single-arm: no direct comparator to mavacamten or placebo",
        "Predominantly NYHA Class II population (73%); may not generalize to more symptomatic patients"
    ]
}


# =============================================================================
# EXTRACTION PROMPT
# =============================================================================

EXTRACTION_PROMPT = """You are an expert biotech equity research analyst extracting structured clinical trial data from a PDF document. Your output will be used directly by portfolio managers to make investment decisions — be precise, thorough, and quantitative.

Analyze every page, table, figure, and chart in this PDF. Extract ALL data into the JSON schema below.

## CRITICAL INSTRUCTIONS

### 1. BASELINE CHARACTERISTICS TABLE
Extract the complete baseline characteristics table as structured data. Pull EVERY row: demographics (age, sex, race, BMI), disease characteristics (sarcomere variant status, NYHA class distribution, prior SRT, ICD, atrial fibrillation history, medication use), and baseline measurements (LVEF, LVOT-G resting and Valsalva, e', KCCQ-OSS, KCCQ-CSS, NT-proBNP, and any others present). Preserve the exact column headers (each study arm/population). Analysts need this to assess cross-trial comparability.

### 2. CHART AND FIGURE DATA EXTRACTION
Read quantitative values from ALL bar charts, line charts, waterfall plots, forest plots, and Kaplan-Meier curves. Do NOT just describe the charts — extract the actual numbers. For time-course data, extract the value at EACH timepoint shown. Specifically look for:
- Biomarker trajectories (NT-proBNP, troponin, CRP, etc.) at each timepoint per dose/arm
- Functional measure trajectories (e', LVEF, 6MWD, FVC, etc.) at each timepoint per dose/arm
- Patient-reported outcome distributions: extract the full distribution (e.g., % with very large >20pt, large 10-20pt, moderate 5-10pt, small improvements), not just the headline responder rate
- NYHA/functional class shifts at each timepoint per arm (how many shifted from III to II, II to I, etc.)
- Waterfall plot individual patient data where visible
Report these as arrays of {timepoint, dose, value} objects.

### 3. COMPLETE SAFETY TABLE
Extract EVERY row from the TEAE table with exact n and percentage for each arm. Do not omit or summarize — include all adverse events listed. Also extract:
- Full SAE details with context (relatedness, resolution, action taken)
- Discontinuation details (reason, dose level, timing)
- LVEF/cardiac safety narrative with specific findings: any LVEF <50%, LVEF <30%, mean LVEF change, any REMS implications
- Special population safety notes (e.g., patients with AF, elderly, low baseline LVEF)

### 4. STUDY LIMITATIONS
Note all limitations: open-label vs blinded, sample size, duration, control arm, enrichment/selection bias, generalizability concerns.

Return ONLY valid JSON (no markdown fences, no explanation text). Match this exact schema:

{
  "drug_name": "string - include brand name in parentheses if available",
  "company": "string",
  "target": "string - molecular target",
  "mechanism": "string - mechanism of action, 1-2 sentences",
  "indication": "string - disease/condition being treated",
  "trial_phase": "string - Phase 1/1b/2/2b/3/etc",
  "trial_design": "string - describe randomization, blinding, control, arms, duration, dose levels",
  "key_takeaway": "string - 2-3 sentence investment-relevant summary. What matters for the stock? Lead with the most important finding.",
  "patient_population": {
    "n": "number - total enrolled",
    "inclusion_criteria": "string - key inclusion criteria",
    "demographics": "string - brief summary"
  },
  "baseline_characteristics": {
    "columns": ["Parameter", "Arm 1 Label", "Arm 2 Label"],
    "rows": [
      {"parameter": "string - row label", "values": ["value for arm 1", "value for arm 2"]}
    ]
  },
  "efficacy_endpoints": [
    {
      "name": "string - endpoint name",
      "population": "string - analysis population or subgroup",
      "dose": "string - dose level or arm",
      "baseline": "string - baseline value if available",
      "value": "string - post-treatment or final value",
      "change": "string - change from baseline with absolute and/or percent",
      "timepoint": "string - when measured",
      "p_value": "string or null",
      "n": "number - N for this analysis",
      "confidence": "high|medium|low"
    }
  ],
  "time_course_data": [
    {
      "endpoint": "string - what is being tracked",
      "unit": "string",
      "data": [
        {"timepoint": "string", "dose": "string", "value": "number or string"}
      ]
    }
  ],
  "safety": {
    "teae_table": {
      "columns": ["Event", "Arm 1 n (%)", "Arm 2 n (%)"],
      "rows": [
        {"event": "string", "values": ["n (%)", "n (%)"]}
      ]
    },
    "serious_adverse_events": ["string - each SAE with full detail"],
    "discontinuation_details": "string - full detail on discontinuations",
    "lvef_safety": {
      "narrative": "string - comprehensive LVEF/cardiac safety narrative",
      "findings": ["string - each specific finding"]
    },
    "key_signals": ["string - notable safety observations and implications"]
  },
  "regulatory_status": "string - approval status, key dates, designations",
  "next_catalyst": "string - upcoming milestones, data readouts, regulatory dates",
  "study_limitations": ["string - each limitation"]
}"""


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/api/extract")
async def extract_pdf(file: UploadFile = File(...)):
    """Extract structured clinical data from an uploaded PDF using Claude API."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    try:
        import anthropic

        pdf_bytes = await file.read()
        if len(pdf_bytes) > 30 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="PDF must be under 30MB")

        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=16384,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        }
                    ],
                }
            ],
        )

        raw_text = message.content[0].text.strip()

        # Try to parse JSON - handle potential markdown wrapping
        json_text = raw_text
        if json_text.startswith("```"):
            json_text = json_text.split("\n", 1)[1]
            json_text = json_text.rsplit("```", 1)[0]
        json_text = json_text.strip()

        extracted = json.loads(json_text)

        return JSONResponse(content={
            "success": True,
            "data": extracted,
            "source": file.filename,
            "model": "claude-sonnet-4-5-20250929",
            "tokens_used": message.usage.input_tokens + message.usage.output_tokens,
        })

    except json.JSONDecodeError as e:
        return JSONResponse(
            status_code=422,
            content={"success": False, "error": f"Failed to parse extraction output as JSON: {str(e)}", "raw": raw_text[:2000]}
        )
    except anthropic.APIError as e:
        return JSONResponse(
            status_code=502,
            content={"success": False, "error": f"Claude API error: {str(e)}"}
        )
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/api/extract/mock")
async def extract_mock():
    """Return mock extraction data for demo purposes."""
    return JSONResponse(content={
        "success": True,
        "data": MOCK_EXTRACTION,
        "source": "CIRRUS-HCM Phase 2 Poster (ACC 2024)",
        "model": "claude-sonnet-4-5-20250929",
        "tokens_used": 0,
        "is_demo": True,
    })


# =============================================================================
# PUBLISH: Map extraction to asset schema and write to data layer
# =============================================================================

def _map_extraction_to_asset(data: dict, ticker: str, asset_name: str, source_filename: str) -> dict:
    """Map extraction output to the v2.2 asset JSON schema."""
    from datetime import date as _date

    today = _date.today().isoformat()
    asset_normalized = asset_name.lower().replace("-", "").replace(" ", "")
    drug = data.get("drug_name", asset_name)

    asset_json = {
        "_metadata": {
            "version": "2.2",
            "ticker": ticker.upper(),
            "asset_name": asset_normalized,
            "last_updated": today,
            "sources": [{
                "id": f"{ticker.lower()}_extraction_{today.replace('-', '')}",
                "type": "ai_extraction",
                "title": f"AI extraction from {source_filename}",
                "date": today,
                "model": "claude-sonnet-4-5-20250929",
            }]
        },
        "asset": {
            "name": drug.split("(")[0].strip() if "(" in drug else drug,
            "company": data.get("company", ""),
            "ticker": ticker.upper(),
            "stage": data.get("trial_phase", ""),
            "modality": "",
            "one_liner": data.get("key_takeaway", "")[:200] if data.get("key_takeaway") else "",
        },
        "target": {
            "name": data.get("target", ""),
            "biology": {
                "simple_explanation": data.get("mechanism", ""),
            },
        },
        "mechanism": {
            "type": data.get("mechanism", ""),
            "how_it_works": data.get("mechanism", ""),
        },
        "indications": {
            "lead": {
                "name": data.get("indication", ""),
                "patient_population": str(data.get("patient_population", {}).get("n", "")) if data.get("patient_population") else "",
                "rationale": "",
            },
        },
    }

    # Clinical data section
    trial_key = f"extracted_{asset_normalized}"
    clinical = {}

    pop = data.get("patient_population", {})
    clinical["trial_name"] = data.get("trial_design", "").split(".")[0] if data.get("trial_design") else "",
    clinical["design"] = {
        "type": data.get("trial_design", ""),
        "population": pop.get("inclusion_criteria", "") if pop else "",
        "n": pop.get("n", 0) if pop else 0,
    }

    # Baseline characteristics
    bc = data.get("baseline_characteristics")
    if bc and bc.get("rows"):
        clinical["baseline_characteristics"] = {}
        for row in bc["rows"]:
            param_key = row["parameter"].lower().replace(",", "").replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")[:40]
            vals = row.get("values", [])
            clinical["baseline_characteristics"][param_key] = vals[0] if len(vals) == 1 else vals

    # Efficacy endpoints
    if data.get("efficacy_endpoints"):
        clinical["efficacy_endpoints"] = {}
        for ep in data["efficacy_endpoints"]:
            ep_key = ep["name"].lower().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")[:40]
            clinical["efficacy_endpoints"][ep_key] = {
                "name": ep.get("name", ""),
                "population": ep.get("population", ""),
                "dose": ep.get("dose", ""),
                "baseline": ep.get("baseline", ""),
                "result": ep.get("value", ""),
                "change": ep.get("change", ""),
                "timepoint": ep.get("timepoint", ""),
                "p_value": ep.get("p_value"),
                "n": ep.get("n"),
                "confidence": ep.get("confidence", "medium"),
            }

    # Time-course data
    if data.get("time_course_data"):
        clinical["time_course_data"] = data["time_course_data"]

    # Safety
    if data.get("safety"):
        s = data["safety"]
        clinical["safety"] = {
            "summary": "",
            "teae_table": s.get("teae_table"),
            "serious_adverse_events": s.get("serious_adverse_events", []),
            "discontinuation_details": s.get("discontinuation_details", ""),
            "lvef_safety": s.get("lvef_safety"),
            "key_findings": s.get("key_signals", []),
        }

    asset_json["clinical_data"] = {trial_key: clinical}

    # Catalysts
    if data.get("next_catalyst"):
        asset_json["catalysts"] = [{
            "event": data["next_catalyst"],
            "importance": "High",
        }]

    # Regulatory
    if data.get("regulatory_status"):
        asset_json["regulatory_path"] = {
            "status": data["regulatory_status"],
        }

    # Investment analysis from key takeaway + limitations
    if data.get("key_takeaway") or data.get("study_limitations"):
        asset_json["investment_analysis"] = {}
        if data.get("key_takeaway"):
            asset_json["investment_analysis"]["bull_case"] = [{
                "point": data["key_takeaway"],
                "confidence": "Medium - single extraction",
            }]
        if data.get("study_limitations"):
            asset_json["investment_analysis"]["bear_case"] = [
                {"point": lim, "probability": ""} for lim in data["study_limitations"]
            ]

    return asset_json


@router.post("/api/extract/publish")
async def publish_extraction(request: Request):
    """Map extraction data to asset schema and write to data layer."""
    from pathlib import Path as _Path

    body = await request.json()
    data = body.get("data")
    ticker = body.get("ticker", "").upper().strip()
    asset_name = body.get("asset_name", "").strip()
    source_filename = body.get("source", "unknown.pdf")

    if not data or not ticker or not asset_name:
        raise HTTPException(status_code=400, detail="Missing data, ticker, or asset_name")

    asset_normalized = asset_name.lower().replace("-", "").replace(" ", "")
    company_dir = _Path("data/companies") / ticker
    asset_path = company_dir / f"{asset_normalized}.json"

    # Map extraction to asset schema
    asset_json = _map_extraction_to_asset(data, ticker, asset_name, source_filename)

    # Check if file exists
    existing = None
    if asset_path.exists():
        with open(asset_path) as f:
            existing = json.load(f)

    # Write
    company_dir.mkdir(parents=True, exist_ok=True)
    with open(asset_path, "w") as f:
        json.dump(asset_json, f, indent=2, default=str)

    return JSONResponse(content={
        "success": True,
        "path": str(asset_path),
        "ticker": ticker,
        "asset_name": asset_normalized,
        "is_new": existing is None,
        "asset_json": asset_json,
    })


@router.post("/api/extract/preview")
async def preview_publish(request: Request):
    """Preview what publishing would write without actually writing."""
    from pathlib import Path as _Path

    body = await request.json()
    data = body.get("data")
    ticker = body.get("ticker", "").upper().strip()
    asset_name = body.get("asset_name", "").strip()
    source_filename = body.get("source", "unknown.pdf")

    if not data or not ticker or not asset_name:
        raise HTTPException(status_code=400, detail="Missing data, ticker, or asset_name")

    asset_normalized = asset_name.lower().replace("-", "").replace(" ", "")
    asset_path = _Path("data/companies") / ticker / f"{asset_normalized}.json"

    asset_json = _map_extraction_to_asset(data, ticker, asset_name, source_filename)

    existing = None
    if asset_path.exists():
        with open(asset_path) as f:
            existing = json.load(f)

    return JSONResponse(content={
        "success": True,
        "path": str(asset_path),
        "is_new": existing is None,
        "existing": existing,
        "proposed": asset_json,
    })


# =============================================================================
# HTML PAGE GENERATION
# =============================================================================

def _generate_extract_page_html() -> str:
    """Generate the PDF extraction demo page HTML."""
    extract_styles = """
        /* Page-specific vars */
        :root {
            --green: #16a34a;
            --green-bg: rgba(22,163,74,0.08);
            --amber: #d97706;
            --amber-bg: rgba(245,158,11,0.08);
            --red: #dc2626;
            --red-bg: rgba(220,38,38,0.08);
            --coral: var(--accent);
            --coral-hover: var(--accent-hover);
            --surface-alt: #f5f5f3;
        }

        /* Hero section */
        .hero {
            text-align: center;
            padding: 56px 24px 40px;
        }
        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(224,122,95,0.1);
            color: var(--coral);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-bottom: 20px;
        }
        .hero h1 {
            font-family: 'Fraunces', serif;
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--navy);
            margin-bottom: 12px;
            line-height: 1.2;
        }
        .hero p {
            color: var(--text-secondary);
            font-size: 1.1rem;
            max-width: 600px;
            margin: 0 auto;
        }

        /* Container */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px 80px;
        }

        /* Upload zone */
        .upload-zone {
            border: 2px dashed var(--border);
            border-radius: 16px;
            padding: 56px 32px;
            text-align: center;
            background: var(--surface);
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 24px;
        }
        .upload-zone:hover, .upload-zone.dragover {
            border-color: var(--coral);
            background: rgba(224,122,95,0.03);
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(224,122,95,0.1);
        }
        .upload-zone.dragover { border-style: solid; }
        .upload-icon {
            width: 64px; height: 64px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, rgba(224,122,95,0.12) 0%, rgba(224,122,95,0.05) 100%);
            border-radius: 16px;
            display: flex; align-items: center; justify-content: center;
        }
        .upload-icon svg { width: 32px; height: 32px; color: var(--coral); }
        .upload-zone h3 { font-size: 1.15rem; color: var(--navy); margin-bottom: 8px; }
        .upload-zone p { color: var(--text-muted); font-size: 0.9rem; }
        .upload-zone .browse-link { color: var(--coral); font-weight: 600; }
        .upload-zone input { display: none; }
        .upload-hint { margin-top: 16px; font-size: 0.8rem; color: var(--text-muted); }

        /* Demo button */
        .demo-bar { text-align: center; margin-bottom: 40px; }
        .demo-btn {
            display: inline-flex; align-items: center; gap: 8px;
            background: none; border: 1.5px solid var(--border);
            color: var(--text-secondary); padding: 10px 24px;
            border-radius: 10px; font-size: 0.9rem; font-family: inherit;
            cursor: pointer; transition: all 0.2s;
        }
        .demo-btn:hover { border-color: var(--coral); color: var(--coral); background: rgba(224,122,95,0.04); }

        /* Loading state */
        .loading-overlay { display: none; text-align: center; padding: 80px 24px; }
        .loading-overlay.active { display: block; }
        .spinner {
            width: 48px; height: 48px;
            border: 3px solid var(--border); border-top-color: var(--coral);
            border-radius: 50%; animation: spin 0.8s linear infinite;
            margin: 0 auto 24px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-overlay h3 { font-size: 1.15rem; color: var(--navy); margin-bottom: 8px; }
        .loading-overlay p { color: var(--text-muted); font-size: 0.9rem; }
        .loading-steps {
            margin-top: 32px; display: inline-flex; flex-direction: column;
            gap: 12px; text-align: left;
        }
        .loading-step {
            display: flex; align-items: center; gap: 10px;
            font-size: 0.85rem; color: var(--text-muted); transition: color 0.3s;
        }
        .loading-step.active { color: var(--navy); font-weight: 500; }
        .loading-step.done { color: var(--green); }
        .step-indicator {
            width: 20px; height: 20px; border-radius: 50%;
            border: 2px solid var(--border);
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0; font-size: 0.65rem;
        }
        .loading-step.active .step-indicator { border-color: var(--coral); background: rgba(224,122,95,0.1); }
        .loading-step.done .step-indicator { border-color: var(--green); background: var(--green); color: #fff; }

        /* Results */
        .results-section { display: none; }
        .results-section.active { display: block; }
        .results-header {
            display: flex; align-items: center; justify-content: space-between;
            margin-bottom: 24px; flex-wrap: wrap; gap: 12px;
        }
        .results-header h2 { font-family: 'Fraunces', serif; font-size: 1.5rem; color: var(--navy); }
        .results-meta { display: flex; align-items: center; gap: 16px; font-size: 0.8rem; color: var(--text-muted); }
        .results-meta span { display: flex; align-items: center; gap: 4px; }

        .toolbar {
            display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
        }
        .view-toggle {
            display: inline-flex; background: var(--surface-alt);
            border-radius: 8px; padding: 3px; gap: 2px;
        }
        .view-toggle button {
            padding: 6px 16px; border: none; background: none; border-radius: 6px;
            font-size: 0.8rem; font-family: inherit; font-weight: 500;
            cursor: pointer; color: var(--text-secondary); transition: all 0.2s;
        }
        .view-toggle button.active {
            background: var(--surface); color: var(--navy);
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        .btn-new {
            padding: 6px 16px; border: 1.5px solid var(--border); background: none;
            border-radius: 6px; font-size: 0.8rem; font-family: inherit;
            cursor: pointer; color: var(--text-secondary); transition: all 0.2s;
        }
        .btn-new:hover { border-color: var(--coral); color: var(--coral); }

        /* Cards */
        .card {
            background: var(--surface); border-radius: 12px;
            border: 1px solid var(--border); padding: 24px; margin-bottom: 16px;
        }
        .card-header {
            display: flex; align-items: center; gap: 10px; margin-bottom: 16px;
        }
        .card-icon {
            width: 36px; height: 36px; border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1rem; flex-shrink: 0;
        }
        .card-icon.blue { background: rgba(59,130,246,0.1); }
        .card-icon.green { background: var(--green-bg); }
        .card-icon.amber { background: var(--amber-bg); }
        .card-icon.red { background: var(--red-bg); }
        .card-icon.purple { background: rgba(139,92,246,0.1); }
        .card-icon.teal { background: rgba(20,184,166,0.1); }
        .card-header h3 { font-size: 0.95rem; color: var(--navy); }

        /* Key takeaway card */
        .takeaway-card {
            background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 100%);
            border-radius: 12px; padding: 28px 32px; margin-bottom: 20px;
            color: #fff;
        }
        .takeaway-card .label {
            font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: 1px; color: var(--coral); margin-bottom: 10px;
        }
        .takeaway-card .text {
            font-size: 1rem; line-height: 1.7; color: rgba(255,255,255,0.92);
        }

        /* Field rows */
        .field-row {
            display: flex; justify-content: space-between; align-items: flex-start;
            padding: 10px 0; border-bottom: 1px solid var(--border); gap: 16px;
        }
        .field-row:last-child { border-bottom: none; }
        .field-label {
            font-size: 0.8rem; color: var(--text-muted); font-weight: 500;
            min-width: 120px; flex-shrink: 0;
            text-transform: uppercase; letter-spacing: 0.3px;
        }
        .field-value { font-size: 0.9rem; color: var(--text); text-align: right; flex: 1; }

        /* Confidence badges */
        .confidence {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 2px 10px; border-radius: 12px;
            font-size: 0.7rem; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.3px;
            margin-left: 8px; white-space: nowrap;
        }
        .confidence.high { background: var(--green-bg); color: var(--green); }
        .confidence.medium { background: var(--amber-bg); color: var(--amber); }
        .confidence.low { background: var(--red-bg); color: var(--red); }

        /* Data tables */
        .data-table-wrap { overflow-x: auto; margin: 0 -4px; }
        .data-table {
            width: 100%; border-collapse: collapse; font-size: 0.82rem;
        }
        .data-table th {
            background: var(--navy); color: #fff;
            padding: 10px 14px; text-align: left; font-weight: 600;
            font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.3px;
            white-space: nowrap; position: sticky; top: 0;
        }
        .data-table th:first-child { border-radius: 8px 0 0 0; }
        .data-table th:last-child { border-radius: 0 8px 0 0; }
        .data-table td {
            padding: 9px 14px; border-bottom: 1px solid var(--border);
            vertical-align: top;
        }
        .data-table tr:last-child td { border-bottom: none; }
        .data-table tr:hover td { background: rgba(224,122,95,0.03); }
        .data-table .row-label { font-weight: 600; color: var(--navy); white-space: nowrap; }
        .data-table .num { text-align: right; font-variant-numeric: tabular-nums; }

        /* Efficacy table */
        .efficacy-table th { font-size: 0.7rem; }
        .efficacy-table td { font-size: 0.8rem; }
        .efficacy-table .endpoint-col { min-width: 180px; font-weight: 500; color: var(--navy); }
        .efficacy-table .change-col { font-weight: 700; color: var(--coral); }
        .efficacy-table .pval-col { color: var(--text-muted); font-size: 0.78rem; }

        /* Time-course cards */
        .timecourse-card {
            background: var(--surface-alt); border-radius: 10px;
            padding: 16px; margin-bottom: 10px;
        }
        .timecourse-card:last-child { margin-bottom: 0; }
        .timecourse-title { font-weight: 600; font-size: 0.88rem; color: var(--navy); margin-bottom: 10px; }
        .timecourse-grid {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 8px;
        }
        .tc-point {
            background: var(--surface); border: 1px solid var(--border);
            border-radius: 8px; padding: 8px 10px; text-align: center;
        }
        .tc-timepoint { font-size: 0.7rem; color: var(--text-muted); font-weight: 500; text-transform: uppercase; }
        .tc-dose { font-size: 0.68rem; color: var(--text-muted); }
        .tc-value { font-size: 1rem; font-weight: 700; color: var(--navy); margin-top: 2px; font-family: 'Fraunces', serif; }
        .tc-value.negative { color: var(--green); }
        .tc-value.positive { color: var(--coral); }

        /* LVEF safety highlight */
        .lvef-card {
            background: linear-gradient(135deg, var(--green-bg) 0%, rgba(22,163,74,0.02) 100%);
            border: 1px solid rgba(22,163,74,0.2);
            border-radius: 12px; padding: 24px; margin-bottom: 16px;
        }
        .lvef-card .lvef-header {
            display: flex; align-items: center; gap: 10px; margin-bottom: 14px;
        }
        .lvef-card .lvef-icon {
            width: 36px; height: 36px; border-radius: 10px;
            background: rgba(22,163,74,0.15); display: flex;
            align-items: center; justify-content: center; font-size: 1.1rem;
        }
        .lvef-card h3 { font-size: 0.95rem; color: var(--green); }
        .lvef-narrative {
            font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;
            margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px solid rgba(22,163,74,0.15);
        }
        .lvef-finding {
            display: flex; align-items: flex-start; gap: 8px;
            padding: 5px 0; font-size: 0.82rem; color: var(--text-secondary);
        }
        .lvef-check { color: var(--green); font-weight: 700; flex-shrink: 0; }

        /* Safety items */
        .safety-item {
            display: flex; align-items: flex-start; gap: 8px;
            padding: 8px 0; font-size: 0.85rem; color: var(--text-secondary);
        }
        .safety-dot { width: 6px; height: 6px; border-radius: 50%; margin-top: 7px; flex-shrink: 0; }
        .safety-dot.sae { background: var(--red); }
        .safety-dot.signal { background: var(--amber); }

        /* Limitations */
        .limitation-item {
            display: flex; align-items: flex-start; gap: 8px;
            padding: 6px 0; font-size: 0.82rem; color: var(--text-secondary);
        }
        .limitation-icon { color: var(--amber); flex-shrink: 0; font-size: 0.75rem; margin-top: 2px; }

        /* JSON view */
        .json-view { display: none; background: var(--navy); border-radius: 12px; padding: 24px; overflow-x: auto; }
        .json-view.active { display: block; }
        .json-view pre {
            color: #e2e8f0; font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
            font-size: 0.78rem; line-height: 1.7; white-space: pre-wrap; word-break: break-all;
        }
        .json-key { color: #93c5fd; }
        .json-string { color: #86efac; }
        .json-number { color: #fbbf24; }
        .json-null { color: #a78bfa; }

        /* Structured view wrapper */
        .structured-view { display: block; }
        .structured-view.hidden { display: none; }

        /* Grids */
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        @media (max-width: 768px) {
            .grid-2 { grid-template-columns: 1fr; }
            .hero h1 { font-size: 1.8rem; }
            .data-table { font-size: 0.75rem; }
            .data-table th, .data-table td { padding: 6px 8px; }
        }

        /* Error state */
        .error-msg {
            background: var(--red-bg); border: 1px solid rgba(220,38,38,0.2);
            color: var(--red); padding: 16px 20px; border-radius: 10px;
            font-size: 0.9rem; display: none;
        }
        .error-msg.active { display: block; }

        /* Source banner */
        .source-banner {
            background: linear-gradient(135deg, rgba(224,122,95,0.06) 0%, rgba(224,122,95,0.02) 100%);
            border: 1px solid rgba(224,122,95,0.15); border-radius: 10px;
            padding: 14px 20px; margin-bottom: 24px;
            display: flex; align-items: center; gap: 10px; font-size: 0.85rem;
        }
        .source-banner strong { color: var(--navy); }
        .source-banner span { color: var(--text-secondary); }

        /* Animations */
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(16px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-in { animation: fadeInUp 0.4s ease-out both; }
        .delay-1 { animation-delay: 0.05s; }
        .delay-2 { animation-delay: 0.12s; }
        .delay-3 { animation-delay: 0.2s; }
        .delay-4 { animation-delay: 0.28s; }
        .delay-5 { animation-delay: 0.36s; }
        .delay-6 { animation-delay: 0.44s; }
        .delay-7 { animation-delay: 0.52s; }
        .delay-8 { animation-delay: 0.6s; }
        .delay-9 { animation-delay: 0.68s; }
        .delay-10 { animation-delay: 0.76s; }

        /* Limitations banner */
        .limitations-banner {
            background: linear-gradient(135deg, var(--amber-bg) 0%, rgba(245,158,11,0.02) 100%);
            border: 1px solid rgba(245,158,11,0.2);
            border-radius: 10px;
            padding: 12px 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .limitations-banner .lim-label {
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--amber);
            white-space: nowrap;
        }
        .limitations-banner .lim-pills {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }
        .lim-pill {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 12px;
            border-radius: 20px;
            background: rgba(245,158,11,0.1);
            color: #92400e;
            font-size: 0.75rem;
            font-weight: 500;
            white-space: nowrap;
        }
        .lim-pill .lim-icon { font-size: 0.7rem; }

        /* Publish button */
        .btn-publish {
            padding: 6px 16px;
            border: 1.5px solid var(--green);
            background: var(--green-bg);
            border-radius: 6px;
            font-size: 0.8rem;
            font-family: inherit;
            font-weight: 600;
            cursor: pointer;
            color: var(--green);
            transition: all 0.2s;
        }
        .btn-publish:hover {
            background: var(--green);
            color: #fff;
        }

        /* Modal overlay */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }
        .modal-overlay.active {
            display: flex;
        }
        .modal {
            background: var(--surface);
            border-radius: 16px;
            max-width: 800px;
            width: 100%;
            max-height: 85vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 24px 64px rgba(0,0,0,0.2);
        }
        .modal-header {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .modal-header h3 {
            font-family: 'Fraunces', serif;
            font-size: 1.15rem;
            color: var(--navy);
        }
        .modal-close {
            background: none; border: none; font-size: 1.3rem;
            color: var(--text-muted); cursor: pointer; padding: 4px 8px;
        }
        .modal-close:hover { color: var(--text); }
        .modal-body {
            padding: 24px;
            overflow-y: auto;
            flex: 1;
        }
        .modal-footer {
            padding: 16px 24px;
            border-top: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 10px;
        }
        .modal-footer .btn-cancel {
            padding: 8px 20px; border: 1.5px solid var(--border);
            background: none; border-radius: 8px; font-size: 0.85rem;
            font-family: inherit; cursor: pointer; color: var(--text-secondary);
        }
        .modal-footer .btn-confirm {
            padding: 8px 20px; border: none;
            background: var(--green); border-radius: 8px; font-size: 0.85rem;
            font-family: inherit; cursor: pointer; color: #fff; font-weight: 600;
        }
        .modal-footer .btn-confirm:hover { background: #15803d; }

        /* Publish form */
        .publish-form { margin-bottom: 20px; }
        .publish-field {
            margin-bottom: 14px;
        }
        .publish-field label {
            display: block;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }
        .publish-field input {
            width: 100%;
            padding: 8px 12px;
            border: 1.5px solid var(--border);
            border-radius: 8px;
            font-size: 0.9rem;
            font-family: inherit;
            color: var(--text);
            background: var(--bg);
        }
        .publish-field input:focus {
            outline: none;
            border-color: var(--coral);
        }
        .publish-path {
            font-size: 0.8rem;
            color: var(--text-muted);
            background: var(--surface-alt);
            padding: 8px 12px;
            border-radius: 6px;
            font-family: 'SF Mono', monospace;
            margin-bottom: 16px;
        }
        .publish-status {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 16px;
        }
        .publish-status.new-file { background: rgba(59,130,246,0.1); color: #2563eb; }
        .publish-status.update { background: var(--amber-bg); color: var(--amber); }

        /* Diff preview */
        .diff-preview {
            background: var(--navy);
            border-radius: 10px;
            padding: 16px;
            max-height: 350px;
            overflow-y: auto;
        }
        .diff-preview pre {
            color: #e2e8f0;
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.75rem;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .diff-section-label {
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 8px;
        }

        /* Publish success toast */
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 14px 24px;
            border-radius: 10px;
            font-size: 0.88rem;
            font-weight: 500;
            z-index: 2000;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s ease;
        }
        .toast.active { transform: translateY(0); opacity: 1; }
        .toast.success { background: var(--green); color: #fff; }
        .toast.error { background: var(--red); color: #fff; }
    """
    head = _render_head("AI Clinical Data Extraction | Satya Bio", extract_styles)
    nav = _render_nav("extract")
    return head + nav + '''

    <div class="hero">
        <div class="hero-badge">AI-POWERED EXTRACTION</div>
        <h1>Clinical Data Extraction</h1>
        <p>Drop a biotech PDF and watch analyst-grade structured data appear in seconds. Powered by Claude.</p>
    </div>

    <div class="container">
        <div class="upload-zone" id="uploadZone">
            <div class="upload-icon">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
            </div>
            <h3>Drop a clinical trial PDF here</h3>
            <p>or <span class="browse-link">browse files</span> to upload</p>
            <div class="upload-hint">Posters, publications, corporate decks, FDA labels, press releases</div>
            <input type="file" id="fileInput" accept=".pdf">
        </div>

        <div class="demo-bar">
            <button class="demo-btn" id="demoBtn" onclick="loadDemo()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                Try an example &mdash; CIRRUS-HCM Phase 2
            </button>
        </div>

        <div class="error-msg" id="errorMsg"></div>

        <div class="loading-overlay" id="loadingOverlay">
            <div class="spinner"></div>
            <h3>Extracting clinical data...</h3>
            <p id="loadingFile">Analyzing document</p>
            <div class="loading-steps">
                <div class="loading-step active" id="step1"><div class="step-indicator"></div>Reading PDF pages & figures</div>
                <div class="loading-step" id="step2"><div class="step-indicator"></div>Extracting baseline characteristics</div>
                <div class="loading-step" id="step3"><div class="step-indicator"></div>Parsing efficacy endpoints & chart data</div>
                <div class="loading-step" id="step4"><div class="step-indicator"></div>Extracting complete safety table</div>
                <div class="loading-step" id="step5"><div class="step-indicator"></div>Structuring analyst-grade output</div>
            </div>
        </div>

        <div class="results-section" id="resultsSection">
            <div class="results-header">
                <h2 id="resultsTitle">Extraction Results</h2>
                <div class="toolbar">
                    <div class="results-meta">
                        <span id="metaSource"></span>
                        <span id="metaModel"></span>
                        <span id="metaTokens"></span>
                    </div>
                    <div class="view-toggle">
                        <button class="active" onclick="showView('structured')">Structured</button>
                        <button onclick="showView('json')">View as JSON</button>
                    </div>
                    <button class="btn-publish" onclick="openPublishModal()">Publish to asset page</button>
                    <button class="btn-new" onclick="resetPage()">+ New extraction</button>
                </div>
            </div>
            <div id="sourceBanner" class="source-banner" style="display:none;"></div>
            <div class="structured-view" id="structuredView"></div>
            <div class="json-view" id="jsonView"><pre id="jsonPre"></pre></div>
        </div>
    </div>

    <!-- Publish modal -->
    <div class="modal-overlay" id="publishModal">
        <div class="modal">
            <div class="modal-header">
                <h3>Publish to Asset Page</h3>
                <button class="modal-close" onclick="closePublishModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="publish-form">
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                        <div class="publish-field">
                            <label>Ticker</label>
                            <input type="text" id="publishTicker" placeholder="e.g. KYMR" />
                        </div>
                        <div class="publish-field">
                            <label>Asset Name</label>
                            <input type="text" id="publishAsset" placeholder="e.g. KT-621" />
                        </div>
                    </div>
                </div>
                <div class="publish-path" id="publishPath">data/companies/TICKER/asset.json</div>
                <div id="publishStatus"></div>
                <div class="diff-section-label">Preview: data to be written</div>
                <div class="diff-preview"><pre id="publishPreview">Loading preview...</pre></div>
            </div>
            <div class="modal-footer">
                <button class="btn-cancel" onclick="closePublishModal()">Cancel</button>
                <button class="btn-confirm" id="publishConfirmBtn" onclick="confirmPublish()">Publish</button>
            </div>
        </div>
    </div>

    <!-- Toast -->
    <div class="toast" id="toast"></div>

    <script>
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');

        uploadZone.addEventListener('click', () => fileInput.click());
        uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); });
        uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault(); uploadZone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type === 'application/pdf') uploadFile(file);
            else showError('Please drop a PDF file.');
        });
        fileInput.addEventListener('change', (e) => { if (e.target.files[0]) uploadFile(e.target.files[0]); });

        function showError(msg) {
            const el = document.getElementById('errorMsg');
            el.textContent = msg; el.classList.add('active');
            setTimeout(() => el.classList.remove('active'), 8000);
        }

        function setState(state) {
            document.getElementById('uploadZone').style.display = state === 'upload' ? '' : 'none';
            document.querySelector('.demo-bar').style.display = state === 'upload' ? '' : 'none';
            document.getElementById('loadingOverlay').classList.toggle('active', state === 'loading');
            document.getElementById('resultsSection').classList.toggle('active', state === 'results');
        }

        function resetPage() {
            setState('upload');
            fileInput.value = '';
        }

        function animateLoading(filename) {
            document.getElementById('loadingFile').textContent = filename || 'Analyzing document';
            const steps = ['step1','step2','step3','step4','step5'].map(id => document.getElementById(id));
            steps.forEach(s => { s.className = 'loading-step'; s.querySelector('.step-indicator').innerHTML = ''; });
            steps[0].classList.add('active');
            const timings = [1500, 3000, 5000, 7000];
            timings.forEach((t, i) => {
                setTimeout(() => {
                    steps[i].classList.remove('active'); steps[i].classList.add('done');
                    steps[i].querySelector('.step-indicator').innerHTML = '&#10003;';
                    if (i + 1 < steps.length) steps[i + 1].classList.add('active');
                }, t);
            });
        }

        let uploadStartTime = 0;

        async function uploadFile(file) {
            setState('loading'); animateLoading(file.name);
            uploadStartTime = Date.now();
            const formData = new FormData();
            formData.append('file', file);
            try {
                const resp = await fetch('/extract/api/extract', { method: 'POST', body: formData });
                const data = await resp.json();
                if (!resp.ok || !data.success) { setState('upload'); showError(data.error || 'Extraction failed.'); return; }
                const elapsed = Date.now() - uploadStartTime;
                const minWait = 8500;
                setTimeout(() => { renderResults(data); setState('results'); }, Math.max(0, minWait - elapsed));
            } catch (err) { setState('upload'); showError('Network error. Check connection and try again.'); }
        }

        async function loadDemo() {
            setState('loading'); animateLoading('CIRRUS-HCM Phase 2 Poster');
            const resp = await fetch('/extract/api/extract/mock');
            const data = await resp.json();
            setTimeout(() => { renderResults(data); setState('results'); }, 8500);
        }

        function showView(view) {
            const btns = document.querySelectorAll('.view-toggle button');
            btns.forEach(b => b.classList.remove('active'));
            if (view === 'json') {
                btns[1].classList.add('active');
                document.getElementById('jsonView').classList.add('active');
                document.getElementById('structuredView').classList.add('hidden');
            } else {
                btns[0].classList.add('active');
                document.getElementById('jsonView').classList.remove('active');
                document.getElementById('structuredView').classList.remove('hidden');
            }
        }

        // =====================================================================
        // RENDERING
        // =====================================================================
        function esc(str) {
            if (str === null || str === undefined) return '';
            return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }

        function confidenceBadge(level) {
            const l = (level || 'medium').toLowerCase();
            return '<span class="confidence ' + l + '">' + l + '</span>';
        }

        function fieldRow(label, value) {
            return '<div class="field-row"><div class="field-label">' + esc(label) + '</div><div class="field-value">' + esc(value || 'N/A') + '</div></div>';
        }

        function syntaxHighlight(json) {
            const str = JSON.stringify(json, null, 2);
            return str.replace(/(\"(\\\\u[a-zA-Z0-9]{4}|\\\\[^u]|[^\\\\\"])*\"(\\s*:)?|\\b(true|false|null)\\b|-?\\d+(?:\\.\\d*)?(?:[eE][+\\-]?\\d+)?)/g, function(match) {
                let cls = 'json-number';
                if (/^\"/.test(match)) {
                    if (/:$/.test(match)) {
                        return '<span class="json-key">' + match.slice(0,-1) + '</span>:';
                    } else { cls = 'json-string'; }
                } else if (/true|false/.test(match)) { cls = 'json-string'; }
                else if (/null/.test(match)) { cls = 'json-null'; }
                return '<span class="' + cls + '">' + match + '</span>';
            });
        }

        function renderResults(resp) {
            const d = resp.data;

            document.getElementById('resultsTitle').textContent = d.drug_name || 'Extraction Results';
            document.getElementById('metaSource').innerHTML = resp.source ? '&#128196; ' + esc(resp.source) : '';
            document.getElementById('metaModel').innerHTML = '&#9881; ' + (resp.model || 'Claude');
            document.getElementById('metaTokens').innerHTML = resp.tokens_used ? '&#9889; ' + resp.tokens_used.toLocaleString() + ' tokens' : '';

            const banner = document.getElementById('sourceBanner');
            if (resp.is_demo) {
                banner.innerHTML = '<strong>Demo mode</strong> <span>&#8212; Pre-loaded CIRRUS-HCM example. Upload your own PDF for real extraction.</span>';
            } else {
                banner.innerHTML = '<strong>Live extraction</strong> <span>&#8212; Data extracted from <em>' + esc(resp.source) + '</em> by Claude Sonnet</span>';
            }
            banner.style.display = 'flex';

            document.getElementById('jsonPre').innerHTML = syntaxHighlight(d);

            // Store for publish feature
            currentExtraction = d;
            currentSource = resp.source;

            let html = '';
            let delay = 1;

            // === KEY TAKEAWAY ===
            if (d.key_takeaway) {
                html += '<div class="takeaway-card animate-in delay-' + (delay++) + '">';
                html += '<div class="label">Key Takeaway</div>';
                html += '<div class="text">' + esc(d.key_takeaway) + '</div>';
                html += '</div>';
            }

            // === AUTO-GENERATED LIMITATIONS BANNER ===
            const pills = detectLimitations(d);
            if (pills.length) {
                html += '<div class="limitations-banner animate-in delay-' + (delay++) + '">';
                html += '<span class="lim-label">Study caveats</span>';
                html += '<div class="lim-pills">';
                pills.forEach(p => {
                    html += '<span class="lim-pill"><span class="lim-icon">' + p.icon + '</span>' + esc(p.label) + '</span>';
                });
                html += '</div></div>';
            }

            // === OVERVIEW + TRIAL DESIGN (2-col) ===
            html += '<div class="grid-2 animate-in delay-' + (delay++) + '">';
            html += '<div class="card"><div class="card-header"><div class="card-icon blue">&#128138;</div><h3>Drug Overview</h3></div>';
            html += fieldRow('Drug', d.drug_name);
            html += fieldRow('Company', d.company);
            html += fieldRow('Target', d.target);
            html += fieldRow('Indication', d.indication);
            html += fieldRow('Phase', d.trial_phase);
            html += fieldRow('Mechanism', d.mechanism);
            html += '</div>';

            html += '<div class="card"><div class="card-header"><div class="card-icon purple">&#128202;</div><h3>Trial Design</h3></div>';
            html += fieldRow('Design', d.trial_design);
            if (d.patient_population) {
                html += fieldRow('Enrolled', d.patient_population.n ? 'N = ' + d.patient_population.n : 'N/A');
                html += fieldRow('Key Criteria', d.patient_population.inclusion_criteria);
                html += fieldRow('Demographics', d.patient_population.demographics);
            }
            html += '</div>';
            html += '</div>';

            // === BASELINE CHARACTERISTICS TABLE ===
            if (d.baseline_characteristics && d.baseline_characteristics.rows && d.baseline_characteristics.rows.length) {
                const bc = d.baseline_characteristics;
                html += '<div class="card animate-in delay-' + (delay++) + '">';
                html += '<div class="card-header"><div class="card-icon teal">&#128203;</div><h3>Baseline Characteristics</h3></div>';
                html += '<div class="data-table-wrap"><table class="data-table">';
                html += '<thead><tr>';
                (bc.columns || ['Parameter', 'Value']).forEach(col => { html += '<th>' + esc(col) + '</th>'; });
                html += '</tr></thead><tbody>';
                bc.rows.forEach(row => {
                    html += '<tr><td class="row-label">' + esc(row.parameter) + '</td>';
                    (row.values || []).forEach(v => { html += '<td class="num">' + esc(v) + '</td>'; });
                    html += '</tr>';
                });
                html += '</tbody></table></div></div>';
            }

            // === EFFICACY TABLE ===
            if (d.efficacy_endpoints && d.efficacy_endpoints.length) {
                html += '<div class="card animate-in delay-' + (delay++) + '">';
                html += '<div class="card-header"><div class="card-icon green">&#9989;</div><h3>Efficacy Endpoints</h3></div>';
                html += '<div class="data-table-wrap"><table class="data-table efficacy-table">';

                // Check which columns have data
                const hasPopulation = d.efficacy_endpoints.some(e => e.population);
                const hasDose = d.efficacy_endpoints.some(e => e.dose);
                const hasBaseline = d.efficacy_endpoints.some(e => e.baseline);
                const hasValue = d.efficacy_endpoints.some(e => e.value);
                const hasChange = d.efficacy_endpoints.some(e => e.change);
                const hasTimepoint = d.efficacy_endpoints.some(e => e.timepoint);
                const hasPval = d.efficacy_endpoints.some(e => e.p_value);
                const hasN = d.efficacy_endpoints.some(e => e.n);

                html += '<thead><tr><th>Endpoint</th>';
                if (hasPopulation) html += '<th>Population</th>';
                if (hasDose) html += '<th>Dose</th>';
                if (hasBaseline) html += '<th>Baseline</th>';
                if (hasValue) html += '<th>Result</th>';
                if (hasChange) html += '<th>Change</th>';
                if (hasTimepoint) html += '<th>Timepoint</th>';
                if (hasPval) html += '<th>p-value</th>';
                if (hasN) html += '<th>N</th>';
                html += '<th></th></tr></thead><tbody>';

                d.efficacy_endpoints.forEach(ep => {
                    html += '<tr>';
                    html += '<td class="endpoint-col">' + esc(ep.name) + '</td>';
                    if (hasPopulation) html += '<td>' + esc(ep.population) + '</td>';
                    if (hasDose) html += '<td>' + esc(ep.dose) + '</td>';
                    if (hasBaseline) html += '<td class="num">' + esc(ep.baseline) + '</td>';
                    if (hasValue) html += '<td class="num">' + esc(ep.value) + '</td>';
                    if (hasChange) html += '<td class="change-col">' + esc(ep.change) + '</td>';
                    if (hasTimepoint) html += '<td>' + esc(ep.timepoint) + '</td>';
                    if (hasPval) html += '<td class="pval-col">' + (ep.p_value ? esc(ep.p_value) : '') + '</td>';
                    if (hasN) html += '<td class="num">' + (ep.n || '') + '</td>';
                    html += '<td>' + confidenceBadge(ep.confidence) + '</td>';
                    html += '</tr>';
                });
                html += '</tbody></table></div></div>';
            }

            // === TIME-COURSE DATA ===
            if (d.time_course_data && d.time_course_data.length) {
                html += '<div class="card animate-in delay-' + (delay++) + '">';
                html += '<div class="card-header"><div class="card-icon blue">&#128200;</div><h3>Time-Course Data</h3></div>';
                d.time_course_data.forEach(tc => {
                    html += '<div class="timecourse-card">';
                    html += '<div class="timecourse-title">' + esc(tc.endpoint) + (tc.unit ? ' (' + esc(tc.unit) + ')' : '') + '</div>';
                    html += '<div class="timecourse-grid">';
                    tc.data.forEach(pt => {
                        html += '<div class="tc-point">';
                        html += '<div class="tc-timepoint">' + esc(pt.timepoint) + '</div>';
                        if (pt.dose) html += '<div class="tc-dose">' + esc(pt.dose) + '</div>';
                        const val = pt.value;
                        let valClass = '';
                        if (typeof val === 'number') valClass = val < 0 ? ' negative' : val > 0 ? ' positive' : '';
                        const display = typeof val === 'number' ? (val > 0 ? '+' + val + '%' : val + '%') : val;
                        html += '<div class="tc-value' + valClass + '">' + esc(String(display)) + '</div>';
                        html += '</div>';
                    });
                    html += '</div></div>';
                });
                html += '</div>';
            }

            // === COMPLETE SAFETY TABLE ===
            if (d.safety) {
                const s = d.safety;

                // TEAE table
                if (s.teae_table && s.teae_table.rows && s.teae_table.rows.length) {
                    html += '<div class="card animate-in delay-' + (delay++) + '">';
                    html += '<div class="card-header"><div class="card-icon red">&#9888;&#65039;</div><h3>Treatment-Emergent Adverse Events (Complete)</h3></div>';
                    html += '<div class="data-table-wrap"><table class="data-table">';
                    html += '<thead><tr>';
                    const teaeCols = s.teae_table.columns || ['Event', 'n (%)'];
                    teaeCols.forEach(col => { html += '<th>' + esc(col) + '</th>'; });
                    html += '</tr></thead><tbody>';
                    s.teae_table.rows.forEach((row, i) => {
                        const isBold = i === 0;
                        html += '<tr>';
                        html += '<td' + (isBold ? ' class="row-label"' : '') + '>' + esc(row.event) + '</td>';
                        (row.values || []).forEach(v => { html += '<td class="num"' + (isBold ? ' style="font-weight:600"' : '') + '>' + esc(v) + '</td>'; });
                        html += '</tr>';
                    });
                    html += '</tbody></table></div></div>';
                }

                // LVEF Safety highlight
                if (s.lvef_safety && (s.lvef_safety.narrative || (s.lvef_safety.findings && s.lvef_safety.findings.length))) {
                    html += '<div class="lvef-card animate-in delay-' + (delay++) + '">';
                    html += '<div class="lvef-header"><div class="lvef-icon">&#128154;</div><h3>LVEF Safety Profile (Key Differentiator)</h3></div>';
                    if (s.lvef_safety.narrative) {
                        html += '<div class="lvef-narrative">' + esc(s.lvef_safety.narrative) + '</div>';
                    }
                    if (s.lvef_safety.findings && s.lvef_safety.findings.length) {
                        s.lvef_safety.findings.forEach(f => {
                            html += '<div class="lvef-finding"><span class="lvef-check">&#10003;</span>' + esc(f) + '</div>';
                        });
                    }
                    html += '</div>';
                }

                // SAE + Discontinuation + Signals
                html += '<div class="grid-2 animate-in delay-' + (delay++) + '">';

                html += '<div class="card"><div class="card-header"><div class="card-icon red">&#128680;</div><h3>SAEs & Discontinuations</h3></div>';
                if (s.serious_adverse_events && s.serious_adverse_events.length) {
                    html += '<div style="font-size:0.72rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.3px;margin-bottom:6px;">Serious Adverse Events</div>';
                    s.serious_adverse_events.forEach(sae => {
                        html += '<div class="safety-item"><div class="safety-dot sae"></div>' + esc(sae) + '</div>';
                    });
                }
                if (s.discontinuation_details) {
                    html += '<div style="font-size:0.72rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.3px;margin:14px 0 6px;">Discontinuations</div>';
                    html += '<div style="font-size:0.85rem;color:var(--text-secondary);">' + esc(s.discontinuation_details) + '</div>';
                }
                // Fallback for old schema
                if (!s.discontinuation_details && s.discontinuation_rate) {
                    html += '<div style="font-size:0.85rem;color:var(--text-secondary);margin-top:10px;"><strong>Discontinuation rate:</strong> ' + esc(s.discontinuation_rate) + '</div>';
                }
                html += '</div>';

                html += '<div class="card"><div class="card-header"><div class="card-icon amber">&#128161;</div><h3>Key Safety Signals</h3></div>';
                if (s.key_signals && s.key_signals.length) {
                    s.key_signals.forEach(sig => {
                        html += '<div class="safety-item"><div class="safety-dot signal"></div>' + esc(sig) + '</div>';
                    });
                }
                html += '</div>';

                html += '</div>';
            }

            // === REGULATORY + CATALYSTS ===
            html += '<div class="grid-2 animate-in delay-' + (delay++) + '">';
            html += '<div class="card"><div class="card-header"><div class="card-icon amber">&#128640;</div><h3>Regulatory & Catalysts</h3></div>';
            html += fieldRow('Status', d.regulatory_status);
            html += fieldRow('Next Catalyst', d.next_catalyst);
            html += '</div>';

            // === STUDY LIMITATIONS ===
            if (d.study_limitations && d.study_limitations.length) {
                html += '<div class="card"><div class="card-header"><div class="card-icon amber">&#9888;&#65039;</div><h3>Study Limitations</h3></div>';
                d.study_limitations.forEach(lim => {
                    html += '<div class="limitation-item"><span class="limitation-icon">&#9679;</span>' + esc(lim) + '</div>';
                });
                html += '</div>';
            }
            html += '</div>';

            document.getElementById('structuredView').innerHTML = html;
            showView('structured');
        }

        // =====================================================================
        // AUTO-DETECT STUDY LIMITATIONS
        // =====================================================================
        function detectLimitations(d) {
            const pills = [];
            const design = (d.trial_design || '').toLowerCase();
            const limitations = (d.study_limitations || []).map(s => s.toLowerCase()).join(' ');
            const all = design + ' ' + limitations;

            // Open-label
            if (all.includes('open-label') || all.includes('open label') || all.includes('unblinded')) {
                pills.push({icon: '&#9675;', label: 'Open-label'});
            }

            // No placebo / single-arm
            if (all.includes('single-arm') || all.includes('single arm') || all.includes('no placebo') || all.includes('no control') ||
                (all.includes('without') && all.includes('placebo'))) {
                pills.push({icon: '&#8709;', label: 'No placebo control'});
            }

            // Small sample
            const pop = d.patient_population || {};
            const n = pop.n || 0;
            if (n > 0 && n < 50) {
                pills.push({icon: '&#9660;', label: 'Small sample (N=' + n + ')'});
            } else if (n >= 50 && n < 100) {
                pills.push({icon: '&#9660;', label: 'Modest sample (N=' + n + ')'});
            }

            // Short duration
            const durationMatch = design.match(/(\d+)[\s-]*(week|month|day)/i);
            if (durationMatch) {
                const num = parseInt(durationMatch[1]);
                const unit = durationMatch[2].toLowerCase();
                const months = unit === 'week' ? num / 4.33 : unit === 'day' ? num / 30 : num;
                if (months < 6) {
                    pills.push({icon: '&#9201;', label: num + ' ' + durationMatch[2] + ' duration'});
                }
            } else if (all.includes('short') && (all.includes('duration') || all.includes('treatment'))) {
                pills.push({icon: '&#9201;', label: 'Short duration'});
            }

            // Preliminary / interim
            if (all.includes('interim') || all.includes('preliminary') || all.includes('initial results')) {
                pills.push({icon: '&#9888;', label: 'Preliminary data'});
            }

            // Dose-escalation / non-randomized
            if (all.includes('dose-escalation') || all.includes('dose escalation') || all.includes('sequential')) {
                pills.push({icon: '&#8644;', label: 'Dose-escalation design'});
            }

            return pills;
        }

        // =====================================================================
        // PUBLISH TO ASSET PAGE
        // =====================================================================
        let currentExtraction = null;
        let currentSource = null;

        function openPublishModal() {
            if (!currentExtraction) return;

            // Auto-fill ticker and asset from extraction
            const company = (currentExtraction.company || '').toUpperCase();
            const drug = (currentExtraction.drug_name || '').split('(')[0].trim();

            // Try to guess ticker from company name (first word or known patterns)
            let ticker = '';
            if (company.length <= 5 && company.match(/^[A-Z]+$/)) ticker = company;
            document.getElementById('publishTicker').value = ticker;
            document.getElementById('publishAsset').value = drug;

            updatePublishPreview();
            document.getElementById('publishModal').classList.add('active');

            // Live update preview on input change
            document.getElementById('publishTicker').oninput = updatePublishPreview;
            document.getElementById('publishAsset').oninput = updatePublishPreview;
        }

        function closePublishModal() {
            document.getElementById('publishModal').classList.remove('active');
        }

        async function updatePublishPreview() {
            const ticker = document.getElementById('publishTicker').value.trim().toUpperCase();
            const asset = document.getElementById('publishAsset').value.trim();
            const assetNorm = asset.toLowerCase().replace(/-/g, '').replace(/ /g, '');

            document.getElementById('publishPath').textContent =
                'data/companies/' + (ticker || 'TICKER') + '/' + (assetNorm || 'asset') + '.json';

            if (!ticker || !asset || !currentExtraction) {
                document.getElementById('publishPreview').textContent = 'Enter ticker and asset name to preview...';
                document.getElementById('publishStatus').innerHTML = '';
                return;
            }

            try {
                const resp = await fetch('/extract/api/extract/preview', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        data: currentExtraction,
                        ticker: ticker,
                        asset_name: asset,
                        source: currentSource || 'unknown.pdf',
                    }),
                });
                const result = await resp.json();

                if (result.is_new) {
                    document.getElementById('publishStatus').innerHTML =
                        '<span class="publish-status new-file">&#10010; New asset file</span>';
                } else {
                    document.getElementById('publishStatus').innerHTML =
                        '<span class="publish-status update">&#8635; Will overwrite existing file</span>';
                }

                document.getElementById('publishPreview').innerHTML = syntaxHighlight(result.proposed);
            } catch (e) {
                document.getElementById('publishPreview').textContent = 'Error generating preview';
            }
        }

        async function confirmPublish() {
            const ticker = document.getElementById('publishTicker').value.trim().toUpperCase();
            const asset = document.getElementById('publishAsset').value.trim();

            if (!ticker || !asset) {
                showError('Please enter both ticker and asset name.');
                return;
            }

            const btn = document.getElementById('publishConfirmBtn');
            btn.textContent = 'Publishing...';
            btn.disabled = true;

            try {
                const resp = await fetch('/extract/api/extract/publish', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        data: currentExtraction,
                        ticker: ticker,
                        asset_name: asset,
                        source: currentSource || 'unknown.pdf',
                    }),
                });
                const result = await resp.json();

                if (result.success) {
                    closePublishModal();
                    showToast('Published to ' + result.path, 'success');
                } else {
                    showToast('Failed: ' + (result.error || 'Unknown error'), 'error');
                }
            } catch (e) {
                showToast('Network error during publish', 'error');
            } finally {
                btn.textContent = 'Publish';
                btn.disabled = false;
            }
        }

        function showToast(msg, type) {
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.className = 'toast ' + type + ' active';
            setTimeout(() => { toast.classList.remove('active'); }, 4000);
        }
    </script>
</body>
</html>'''


@router.get("/", response_class=HTMLResponse)
async def serve_extract_page():
    """Serve the PDF extraction demo page."""
    return HTMLResponse(content=_generate_extract_page_html())
