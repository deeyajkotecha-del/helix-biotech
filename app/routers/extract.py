"""PDF extraction demo router - YC demo page for AI clinical data extraction."""
import os
import json
import base64
import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()

# =============================================================================
# MOCK DATA FOR DEMO
# =============================================================================

MOCK_EXTRACTION = {
    "drug_name": "Mavacamten (CAMZYOS)",
    "company": "Bristol-Myers Squibb (via MyoKardia)",
    "target": "Cardiac myosin",
    "mechanism": "Selective allosteric inhibitor of cardiac myosin ATPase that reduces actin-myosin cross-bridge formation, decreasing contractility in hypercontractile states",
    "indication": "Obstructive hypertrophic cardiomyopathy (oHCM)",
    "trial_phase": "Phase 3",
    "trial_design": "Randomized, double-blind, placebo-controlled, multicenter (EXPLORER-HCM). 1:1 randomization, 30-week treatment period with 8-week washout.",
    "patient_population": {
        "n": 251,
        "inclusion_criteria": "Adults with symptomatic oHCM, NYHA class II-III, LVEF >= 55%, resting or provoked LVOT gradient >= 50 mmHg",
        "demographics": "Mean age 58.5 years, 59% male, 93% White, mean BMI 29.7"
    },
    "efficacy_endpoints": [
        {
            "name": "Composite primary endpoint (pVO2 + NYHA improvement)",
            "result": "37% vs 17% (mavacamten vs placebo)",
            "p_value": "0.0005",
            "clinical_significance": "Clinically meaningful improvement in exercise capacity and functional class. Exceeded pre-specified success threshold.",
            "confidence": "high"
        },
        {
            "name": "Change in peak VO2 (mL/kg/min)",
            "result": "+1.4 vs -0.05 (treatment difference: +1.4)",
            "p_value": "0.0006",
            "clinical_significance": "Meaningful improvement in cardiopulmonary exercise capacity, correlates with functional status and prognosis in HCM.",
            "confidence": "high"
        },
        {
            "name": "Post-exercise LVOT gradient (mmHg)",
            "result": "-47.0 vs -10.4 (treatment difference: -36.6)",
            "p_value": "<0.0001",
            "clinical_significance": "Dramatic reduction in obstruction. 74% of mavacamten patients achieved gradient <30 mmHg vs 21% placebo.",
            "confidence": "high"
        },
        {
            "name": "NYHA class improvement",
            "result": "65% improved >= 1 class vs 31% placebo",
            "p_value": "<0.0001",
            "clinical_significance": "Majority of patients experienced meaningful symptomatic improvement in heart failure functional class.",
            "confidence": "high"
        },
        {
            "name": "KCCQ-CSS (Kansas City Cardiomyopathy Questionnaire)",
            "result": "+14.9 vs +5.4 (treatment difference: +9.1)",
            "p_value": "<0.0001",
            "clinical_significance": "Exceeds MCID of 5 points. Represents substantial improvement in patient-reported quality of life.",
            "confidence": "high"
        },
        {
            "name": "NT-proBNP reduction",
            "result": "-80% vs -2% (geometric mean ratio)",
            "p_value": "<0.0001",
            "clinical_significance": "Robust biomarker response indicating reduced cardiac wall stress, consistent with disease modification hypothesis.",
            "confidence": "medium"
        }
    ],
    "safety": {
        "serious_adverse_events": [
            "Atrial fibrillation (2.4% vs 0.8%)",
            "Syncope (0.8% vs 0%)",
            "Stress cardiomyopathy (0.8% vs 0%) - resolved after drug discontinuation"
        ],
        "discontinuation_rate": "0.8% mavacamten vs 0.8% placebo due to AEs",
        "key_signals": [
            "LVEF reduction <50% in 7 patients (5.6%) - all recovered with dose adjustment or temporary hold",
            "Requires REMS program with echocardiographic monitoring every 12 weeks",
            "Drug-drug interactions with CYP2C19 and CYP3A4 inhibitors require dose adjustment"
        ]
    },
    "regulatory_status": "FDA approved June 2022 (CAMZYOS). EMA approved June 2023. Requires REMS (CAMZYOS REMS) with certified prescribers and pharmacies.",
    "next_catalyst": "VALOR-HCM long-term extension data; septal reduction therapy avoidance outcomes; label expansion to non-obstructive HCM (ODYSSEY-HCM Phase 3)"
}


# =============================================================================
# EXTRACTION PROMPT
# =============================================================================

EXTRACTION_PROMPT = """You are an expert biotech analyst extracting structured clinical trial data from a PDF document.

Analyze this PDF and extract all clinical trial data into the following JSON schema. Be precise with numbers, p-values, and statistical results. If a field cannot be determined from the document, use null.

For the confidence field on each endpoint, rate as:
- "high" = clearly stated with statistics in the document
- "medium" = stated but without full statistical detail, or inferred from figures
- "low" = estimated or partially inferred from context

Return ONLY valid JSON matching this exact schema (no markdown, no explanation):

{
  "drug_name": "string - include brand name in parentheses if available",
  "company": "string",
  "target": "string - molecular target",
  "mechanism": "string - mechanism of action, 1-2 sentences",
  "indication": "string - disease/condition being treated",
  "trial_phase": "string - Phase 1/2/3/etc",
  "trial_design": "string - describe randomization, blinding, control, duration",
  "patient_population": {
    "n": "number - total enrolled",
    "inclusion_criteria": "string - key inclusion criteria",
    "demographics": "string - age, sex, race, relevant baseline characteristics"
  },
  "efficacy_endpoints": [
    {
      "name": "string - endpoint name",
      "result": "string - result with numbers",
      "p_value": "string - p-value if available",
      "clinical_significance": "string - why this matters clinically",
      "confidence": "high|medium|low"
    }
  ],
  "safety": {
    "serious_adverse_events": ["string - each SAE with rate"],
    "discontinuation_rate": "string - rate due to AEs",
    "key_signals": ["string - notable safety findings"]
  },
  "regulatory_status": "string - approval status, key dates",
  "next_catalyst": "string - upcoming milestones or data readouts"
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
            max_tokens=4096,
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
        "source": "EXPLORER-HCM Phase 3 Results (Olivotto et al., Lancet 2020)",
        "model": "claude-sonnet-4-5-20250929",
        "tokens_used": 0,
        "is_demo": True,
    })


# =============================================================================
# HTML PAGE GENERATION
# =============================================================================

def _generate_extract_page_html() -> str:
    """Generate the PDF extraction demo page HTML."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Clinical Data Extraction | Satya Bio</title>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --navy: #1a2b3c;
            --navy-light: #2d4a5e;
            --coral: #e07a5f;
            --coral-hover: #d06a4f;
            --bg: #fafaf8;
            --surface: #ffffff;
            --surface-alt: #f5f5f3;
            --border: #e5e5e0;
            --text: #1a1d21;
            --text-secondary: #5f6368;
            --text-muted: #9aa0a6;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }

        /* Navigation */
        .topnav {
            background: var(--navy);
            padding: 16px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .topnav-brand {
            font-family: 'Fraunces', serif;
            color: #fff;
            font-size: 1.25rem;
            font-weight: 700;
            text-decoration: none;
        }
        .topnav-brand span { color: var(--coral); }
        .topnav-links a {
            color: rgba(255,255,255,0.7);
            text-decoration: none;
            margin-left: 24px;
            font-size: 0.9rem;
            transition: color 0.2s;
        }
        .topnav-links a:hover { color: #fff; }

        /* Hero section */
        .hero {
            text-align: center;
            padding: 56px 24px 40px;
            position: relative;
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
            max-width: 1100px;
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
            position: relative;
            margin-bottom: 24px;
        }
        .upload-zone:hover, .upload-zone.dragover {
            border-color: var(--coral);
            background: rgba(224,122,95,0.03);
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(224,122,95,0.1);
        }
        .upload-zone.dragover {
            border-style: solid;
        }
        .upload-icon {
            width: 64px;
            height: 64px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, rgba(224,122,95,0.12) 0%, rgba(224,122,95,0.05) 100%);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .upload-icon svg { width: 32px; height: 32px; color: var(--coral); }
        .upload-zone h3 {
            font-size: 1.15rem;
            color: var(--navy);
            margin-bottom: 8px;
        }
        .upload-zone p { color: var(--text-muted); font-size: 0.9rem; }
        .upload-zone .browse-link { color: var(--coral); font-weight: 600; }
        .upload-zone input { display: none; }
        .upload-hint {
            margin-top: 16px;
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        /* Demo button */
        .demo-bar {
            text-align: center;
            margin-bottom: 40px;
        }
        .demo-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: none;
            border: 1.5px solid var(--border);
            color: var(--text-secondary);
            padding: 10px 24px;
            border-radius: 10px;
            font-size: 0.9rem;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.2s;
        }
        .demo-btn:hover {
            border-color: var(--coral);
            color: var(--coral);
            background: rgba(224,122,95,0.04);
        }

        /* Loading state */
        .loading-overlay {
            display: none;
            text-align: center;
            padding: 80px 24px;
        }
        .loading-overlay.active { display: block; }
        .spinner {
            width: 48px; height: 48px;
            border: 3px solid var(--border);
            border-top-color: var(--coral);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 24px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-overlay h3 {
            font-size: 1.15rem;
            color: var(--navy);
            margin-bottom: 8px;
        }
        .loading-overlay p {
            color: var(--text-muted);
            font-size: 0.9rem;
        }
        .loading-steps {
            margin-top: 32px;
            display: inline-flex;
            flex-direction: column;
            gap: 12px;
            text-align: left;
        }
        .loading-step {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.85rem;
            color: var(--text-muted);
            transition: color 0.3s;
        }
        .loading-step.active { color: var(--navy); font-weight: 500; }
        .loading-step.done { color: #16a34a; }
        .step-indicator {
            width: 20px; height: 20px;
            border-radius: 50%;
            border: 2px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-size: 0.65rem;
        }
        .loading-step.active .step-indicator {
            border-color: var(--coral);
            background: rgba(224,122,95,0.1);
        }
        .loading-step.done .step-indicator {
            border-color: #16a34a;
            background: #16a34a;
            color: #fff;
        }

        /* Results */
        .results-section {
            display: none;
        }
        .results-section.active { display: block; }

        .results-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 12px;
        }
        .results-header h2 {
            font-family: 'Fraunces', serif;
            font-size: 1.5rem;
            color: var(--navy);
        }
        .results-meta {
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 0.8rem;
            color: var(--text-muted);
        }
        .results-meta span {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .view-toggle {
            display: inline-flex;
            background: var(--surface-alt);
            border-radius: 8px;
            padding: 3px;
            gap: 2px;
        }
        .view-toggle button {
            padding: 6px 16px;
            border: none;
            background: none;
            border-radius: 6px;
            font-size: 0.8rem;
            font-family: inherit;
            font-weight: 500;
            cursor: pointer;
            color: var(--text-secondary);
            transition: all 0.2s;
        }
        .view-toggle button.active {
            background: var(--surface);
            color: var(--navy);
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }

        /* Cards */
        .card {
            background: var(--surface);
            border-radius: 12px;
            border: 1px solid var(--border);
            padding: 24px;
            margin-bottom: 16px;
        }
        .card-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 16px;
        }
        .card-icon {
            width: 36px; height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            flex-shrink: 0;
        }
        .card-icon.blue { background: rgba(59,130,246,0.1); }
        .card-icon.green { background: rgba(22,163,74,0.1); }
        .card-icon.amber { background: rgba(245,158,11,0.1); }
        .card-icon.red { background: rgba(220,38,38,0.1); }
        .card-icon.purple { background: rgba(139,92,246,0.1); }
        .card-header h3 {
            font-size: 0.95rem;
            color: var(--navy);
        }

        /* Field rows */
        .field-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
            gap: 16px;
        }
        .field-row:last-child { border-bottom: none; }
        .field-label {
            font-size: 0.8rem;
            color: var(--text-muted);
            font-weight: 500;
            min-width: 120px;
            flex-shrink: 0;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }
        .field-value {
            font-size: 0.9rem;
            color: var(--text);
            text-align: right;
            flex: 1;
        }

        /* Confidence badges */
        .confidence {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            margin-left: 8px;
            white-space: nowrap;
        }
        .confidence.high { background: rgba(22,163,74,0.1); color: #16a34a; }
        .confidence.medium { background: rgba(245,158,11,0.1); color: #d97706; }
        .confidence.low { background: rgba(220,38,38,0.1); color: #dc2626; }

        /* Endpoint cards */
        .endpoint-card {
            background: var(--surface-alt);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 10px;
        }
        .endpoint-card:last-child { margin-bottom: 0; }
        .endpoint-name {
            font-weight: 600;
            font-size: 0.9rem;
            color: var(--navy);
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 6px;
        }
        .endpoint-result {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--coral);
            margin-bottom: 4px;
            font-family: 'Fraunces', serif;
        }
        .endpoint-pval {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 6px;
        }
        .endpoint-significance {
            font-size: 0.82rem;
            color: var(--text-secondary);
            line-height: 1.5;
        }

        /* Safety signals */
        .safety-item {
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 8px 0;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        .safety-dot {
            width: 6px; height: 6px;
            border-radius: 50%;
            margin-top: 7px;
            flex-shrink: 0;
        }
        .safety-dot.sae { background: #dc2626; }
        .safety-dot.signal { background: #d97706; }

        /* JSON view */
        .json-view {
            display: none;
            background: var(--navy);
            border-radius: 12px;
            padding: 24px;
            overflow-x: auto;
        }
        .json-view.active { display: block; }
        .json-view pre {
            color: #e2e8f0;
            font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
            font-size: 0.8rem;
            line-height: 1.7;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .json-key { color: #93c5fd; }
        .json-string { color: #86efac; }
        .json-number { color: #fbbf24; }
        .json-null { color: #a78bfa; }
        .json-bracket { color: #94a3b8; }

        /* Structured view wrapper */
        .structured-view { display: block; }
        .structured-view.hidden { display: none; }

        /* 2-col grid */
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }
        @media (max-width: 768px) {
            .grid-2 { grid-template-columns: 1fr; }
            .hero h1 { font-size: 1.8rem; }
            .endpoint-name { flex-direction: column; align-items: flex-start; }
        }

        /* Error state */
        .error-msg {
            background: rgba(220,38,38,0.05);
            border: 1px solid rgba(220,38,38,0.2);
            color: #dc2626;
            padding: 16px 20px;
            border-radius: 10px;
            font-size: 0.9rem;
            display: none;
        }
        .error-msg.active { display: block; }

        /* Fade-in animation for results */
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(16px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-in {
            animation: fadeInUp 0.4s ease-out both;
        }
        .delay-1 { animation-delay: 0.1s; }
        .delay-2 { animation-delay: 0.2s; }
        .delay-3 { animation-delay: 0.3s; }
        .delay-4 { animation-delay: 0.4s; }
        .delay-5 { animation-delay: 0.5s; }

        /* Source banner */
        .source-banner {
            background: linear-gradient(135deg, rgba(224,122,95,0.06) 0%, rgba(224,122,95,0.02) 100%);
            border: 1px solid rgba(224,122,95,0.15);
            border-radius: 10px;
            padding: 14px 20px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.85rem;
        }
        .source-banner strong { color: var(--navy); }
        .source-banner span { color: var(--text-secondary); }
    </style>
</head>
<body>
    <nav class="topnav">
        <a href="/" class="topnav-brand">Satya<span>Bio</span></a>
        <div class="topnav-links">
            <a href="/companies">Companies</a>
            <a href="/targets">Targets</a>
            <a href="/extract" style="color:#fff;">Extract</a>
        </div>
    </nav>

    <div class="hero">
        <div class="hero-badge">AI-POWERED EXTRACTION</div>
        <h1>Clinical Data Extraction</h1>
        <p>Drop a biotech PDF and watch structured clinical trial data appear in seconds. Powered by Claude.</p>
    </div>

    <div class="container">
        <!-- Upload zone -->
        <div class="upload-zone" id="uploadZone">
            <div class="upload-icon">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
            </div>
            <h3>Drop a clinical trial PDF here</h3>
            <p>or <span class="browse-link">browse files</span> to upload</p>
            <div class="upload-hint">Supports clinical trial publications, corporate presentations, FDA labels, press releases</div>
            <input type="file" id="fileInput" accept=".pdf">
        </div>

        <div class="demo-bar">
            <button class="demo-btn" id="demoBtn" onclick="loadDemo()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                Try an example &mdash; EXPLORER-HCM Phase 3
            </button>
        </div>

        <!-- Error -->
        <div class="error-msg" id="errorMsg"></div>

        <!-- Loading -->
        <div class="loading-overlay" id="loadingOverlay">
            <div class="spinner"></div>
            <h3>Extracting clinical data...</h3>
            <p id="loadingFile">Analyzing document</p>
            <div class="loading-steps">
                <div class="loading-step active" id="step1">
                    <div class="step-indicator"></div>
                    Reading PDF content
                </div>
                <div class="loading-step" id="step2">
                    <div class="step-indicator"></div>
                    Identifying trial design & endpoints
                </div>
                <div class="loading-step" id="step3">
                    <div class="step-indicator"></div>
                    Extracting efficacy & safety data
                </div>
                <div class="loading-step" id="step4">
                    <div class="step-indicator"></div>
                    Structuring output
                </div>
            </div>
        </div>

        <!-- Results -->
        <div class="results-section" id="resultsSection">
            <div class="results-header">
                <h2 id="resultsTitle">Extraction Results</h2>
                <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
                    <div class="results-meta">
                        <span id="metaSource"></span>
                        <span id="metaModel"></span>
                        <span id="metaTokens"></span>
                    </div>
                    <div class="view-toggle">
                        <button class="active" onclick="showView('structured')">Structured</button>
                        <button onclick="showView('json')">View as JSON</button>
                    </div>
                </div>
            </div>

            <div id="sourceBanner" class="source-banner" style="display:none;"></div>

            <div class="structured-view" id="structuredView"></div>
            <div class="json-view" id="jsonView"><pre id="jsonPre"></pre></div>
        </div>
    </div>

    <script>
        // =====================================================================
        // DRAG & DROP + FILE UPLOAD
        // =====================================================================
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');

        uploadZone.addEventListener('click', () => fileInput.click());
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type === 'application/pdf') {
                uploadFile(file);
            } else {
                showError('Please drop a PDF file.');
            }
        });
        fileInput.addEventListener('change', (e) => {
            if (e.target.files[0]) uploadFile(e.target.files[0]);
        });

        // =====================================================================
        // STATE MANAGEMENT
        // =====================================================================
        function showError(msg) {
            const el = document.getElementById('errorMsg');
            el.textContent = msg;
            el.classList.add('active');
            setTimeout(() => el.classList.remove('active'), 8000);
        }

        function setState(state) {
            document.getElementById('uploadZone').style.display = state === 'upload' ? '' : 'none';
            document.querySelector('.demo-bar').style.display = state === 'upload' ? '' : 'none';
            document.getElementById('loadingOverlay').classList.toggle('active', state === 'loading');
            document.getElementById('resultsSection').classList.toggle('active', state === 'results');
        }

        // =====================================================================
        // LOADING ANIMATION
        // =====================================================================
        let loadingInterval;

        function animateLoading(filename) {
            document.getElementById('loadingFile').textContent = filename || 'Analyzing document';
            const steps = [
                document.getElementById('step1'),
                document.getElementById('step2'),
                document.getElementById('step3'),
                document.getElementById('step4'),
            ];
            steps.forEach(s => { s.className = 'loading-step'; });
            steps[0].classList.add('active');

            let current = 0;
            const timings = [2000, 3500, 5000];
            timings.forEach((t, i) => {
                setTimeout(() => {
                    steps[i].classList.remove('active');
                    steps[i].classList.add('done');
                    steps[i].querySelector('.step-indicator').innerHTML = '&#10003;';
                    if (i + 1 < steps.length) steps[i + 1].classList.add('active');
                }, t);
            });
        }

        // =====================================================================
        // FILE UPLOAD
        // =====================================================================
        async function uploadFile(file) {
            setState('loading');
            animateLoading(file.name);

            const formData = new FormData();
            formData.append('file', file);

            try {
                const resp = await fetch('/extract/api/extract', {
                    method: 'POST',
                    body: formData,
                });
                const data = await resp.json();

                if (!resp.ok || !data.success) {
                    setState('upload');
                    showError(data.error || 'Extraction failed. Please try again.');
                    return;
                }

                // Wait for loading animation to finish
                setTimeout(() => {
                    renderResults(data);
                    setState('results');
                }, Math.max(0, 6500 - 0));

            } catch (err) {
                setState('upload');
                showError('Network error. Please check your connection and try again.');
            }
        }

        // =====================================================================
        // DEMO
        // =====================================================================
        async function loadDemo() {
            setState('loading');
            animateLoading('EXPLORER-HCM Phase 3 Publication');

            const resp = await fetch('/extract/api/extract/mock');
            const data = await resp.json();

            // Simulate extraction time for demo feel
            setTimeout(() => {
                renderResults(data);
                setState('results');
            }, 6500);
        }

        // =====================================================================
        // VIEW TOGGLE
        // =====================================================================
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
        // RENDER RESULTS
        // =====================================================================
        function confidenceBadge(level) {
            const l = (level || 'medium').toLowerCase();
            return `<span class="confidence ${l}">${l}</span>`;
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }

        function syntaxHighlight(json) {
            const str = JSON.stringify(json, null, 2);
            return str.replace(/("(\\\\u[a-zA-Z0-9]{4}|\\\\[^u]|[^\\\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function(match) {
                let cls = 'json-number';
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        cls = 'json-key';
                        match = match.replace(/:$/, '') + ':';
                        return '<span class="' + cls + '">' + match.replace(/:$/, '') + '</span>:';
                    } else {
                        cls = 'json-string';
                    }
                } else if (/true|false/.test(match)) {
                    cls = 'json-string';
                } else if (/null/.test(match)) {
                    cls = 'json-null';
                }
                return '<span class="' + cls + '">' + match + '</span>';
            });
        }

        function renderResults(resp) {
            const d = resp.data;

            // Meta info
            document.getElementById('resultsTitle').textContent = d.drug_name || 'Extraction Results';
            document.getElementById('metaSource').innerHTML = resp.source ? ('&#128196; ' + escapeHtml(resp.source)) : '';
            document.getElementById('metaModel').innerHTML = '&#9881; ' + (resp.model || 'Claude');
            document.getElementById('metaTokens').innerHTML = resp.tokens_used ? ('&#9889; ' + resp.tokens_used.toLocaleString() + ' tokens') : '';

            // Source banner
            const banner = document.getElementById('sourceBanner');
            if (resp.is_demo) {
                banner.innerHTML = '<strong>Demo mode</strong> <span>&#8212; This is pre-loaded example data from the EXPLORER-HCM trial. Upload your own PDF to see real extraction.</span>';
                banner.style.display = 'flex';
            } else {
                banner.innerHTML = '<strong>Live extraction</strong> <span>&#8212; Data extracted from <em>' + escapeHtml(resp.source) + '</em> by Claude Sonnet</span>';
                banner.style.display = 'flex';
            }

            // JSON view
            document.getElementById('jsonPre').innerHTML = syntaxHighlight(d);

            // Structured view
            let html = '';

            // Row 1: Overview + Trial Design
            html += '<div class="grid-2 animate-in delay-1">';

            // Overview card
            html += '<div class="card"><div class="card-header"><div class="card-icon blue">&#128138;</div><h3>Drug Overview</h3></div>';
            html += fieldRow('Drug', d.drug_name);
            html += fieldRow('Company', d.company);
            html += fieldRow('Target', d.target);
            html += fieldRow('Indication', d.indication);
            html += fieldRow('Phase', d.trial_phase);
            html += fieldRow('Mechanism', d.mechanism);
            html += '</div>';

            // Trial design card
            html += '<div class="card"><div class="card-header"><div class="card-icon purple">&#128202;</div><h3>Trial Design</h3></div>';
            html += fieldRow('Design', d.trial_design);
            if (d.patient_population) {
                const pop = d.patient_population;
                html += fieldRow('Enrolled', pop.n ? ('N = ' + pop.n) : 'N/A');
                html += fieldRow('Key Criteria', pop.inclusion_criteria);
                html += fieldRow('Demographics', pop.demographics);
            }
            html += '</div>';

            html += '</div>'; // end grid-2

            // Efficacy endpoints
            if (d.efficacy_endpoints && d.efficacy_endpoints.length) {
                html += '<div class="card animate-in delay-2"><div class="card-header"><div class="card-icon green">&#9989;</div><h3>Efficacy Endpoints</h3></div>';
                d.efficacy_endpoints.forEach(ep => {
                    html += '<div class="endpoint-card">';
                    html += '<div class="endpoint-name">' + escapeHtml(ep.name) + confidenceBadge(ep.confidence) + '</div>';
                    html += '<div class="endpoint-result">' + escapeHtml(ep.result) + '</div>';
                    if (ep.p_value) html += '<div class="endpoint-pval">p = ' + escapeHtml(ep.p_value) + '</div>';
                    if (ep.clinical_significance) html += '<div class="endpoint-significance">' + escapeHtml(ep.clinical_significance) + '</div>';
                    html += '</div>';
                });
                html += '</div>';
            }

            // Row 3: Safety + Regulatory
            html += '<div class="grid-2 animate-in delay-3">';

            // Safety card
            html += '<div class="card"><div class="card-header"><div class="card-icon red">&#9888;&#65039;</div><h3>Safety Profile</h3></div>';
            if (d.safety) {
                const s = d.safety;
                if (s.discontinuation_rate) {
                    html += '<div style="margin-bottom:12px;font-size:0.85rem;"><strong>Discontinuation rate:</strong> ' + escapeHtml(s.discontinuation_rate) + '</div>';
                }
                if (s.serious_adverse_events && s.serious_adverse_events.length) {
                    html += '<div style="font-size:0.75rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.3px;margin-bottom:6px;">Serious Adverse Events</div>';
                    s.serious_adverse_events.forEach(sae => {
                        html += '<div class="safety-item"><div class="safety-dot sae"></div>' + escapeHtml(sae) + '</div>';
                    });
                }
                if (s.key_signals && s.key_signals.length) {
                    html += '<div style="font-size:0.75rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.3px;margin:12px 0 6px;">Key Safety Signals</div>';
                    s.key_signals.forEach(sig => {
                        html += '<div class="safety-item"><div class="safety-dot signal"></div>' + escapeHtml(sig) + '</div>';
                    });
                }
            }
            html += '</div>';

            // Regulatory + Catalysts card
            html += '<div class="card"><div class="card-header"><div class="card-icon amber">&#128640;</div><h3>Regulatory & Catalysts</h3></div>';
            html += fieldRow('Status', d.regulatory_status);
            html += fieldRow('Next Catalyst', d.next_catalyst);
            html += '</div>';

            html += '</div>'; // end grid-2

            document.getElementById('structuredView').innerHTML = html;

            // Reset view
            showView('structured');
        }

        function fieldRow(label, value) {
            return '<div class="field-row"><div class="field-label">' + escapeHtml(label) + '</div><div class="field-value">' + escapeHtml(value || 'N/A') + '</div></div>';
        }
    </script>
</body>
</html>'''


@router.get("/", response_class=HTMLResponse)
async def serve_extract_page():
    """Serve the PDF extraction demo page."""
    return HTMLResponse(content=_generate_extract_page_html())
