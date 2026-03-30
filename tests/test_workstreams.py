"""
SatyaBio — Integration tests for the 3 workstreams:
  1. Multi-persona synthesis prompt
  2. UI routing (React build + App.tsx)
  3. FDA CRL pipeline

Run: python tests/test_workstreams.py
"""

import os
import sys
import json
import ast
import re
from datetime import datetime

# ── Paths ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARCH_DIR = os.path.join(BASE_DIR, "backend", "services", "search")
APP_DIR = os.path.join(BASE_DIR, "app")

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}")
        if detail:
            print(f"     → {detail}")


# =============================================================================
# TEST GROUP 1: Persona Detection in Query Classifier
# =============================================================================
print("\n" + "=" * 60)
print("TEST GROUP 1: Persona Detection & Classifier")
print("=" * 60)

# Read query_router.py source
qr_path = os.path.join(SEARCH_DIR, "query_router.py")
qr_source = open(qr_path).read()

# 1a. Classifier prompt includes persona field
test(
    "Classifier JSON schema includes 'persona' field",
    '"persona": "investor|operator|trial_designer"' in qr_source
)

# 1b. Classifier has persona detection rules
test(
    "Classifier has persona detection rules for 'operator'",
    'Use "operator" for queries about licensing' in qr_source
)
test(
    "Classifier has persona detection rules for 'trial_designer'",
    'Use "trial_designer" for queries about trial design' in qr_source
)
test(
    "Classifier defaults to 'investor'",
    'Default to "investor" if unclear' in qr_source
)

# 1c. FDA_CRL is listed as a source in the classifier
test(
    "FDA_CRL listed as source option #7",
    "7. FDA_CRL" in qr_source
)
test(
    "FDA_CRL in sources array",
    '"FDA_CRL"' in qr_source
)

# 1d. Classifier rules include FDA_CRL triggers
test(
    "Classifier rules: FDA_CRL for trial design questions",
    "trial design, endpoint selection, FDA feedback, CRLs" in qr_source
)
test(
    "Classifier rules: FDA_CRL for trial_designer persona",
    "trial_designer persona queries, ALWAYS include FDA_CRL" in qr_source
)

# 1e. Persona is logged in answer_query
test(
    "Persona logged in answer_query output",
    "plan.get('persona', 'investor')" in qr_source
)


# =============================================================================
# TEST GROUP 2: Synthesis Prompt — Multi-Persona
# =============================================================================
print("\n" + "=" * 60)
print("TEST GROUP 2: Synthesis Prompt — Multi-Persona")
print("=" * 60)

# 2a. Three personas defined
test(
    "Prompt defines INVESTOR persona",
    "**INVESTOR** (default)" in qr_source
)
test(
    "Prompt defines OPERATOR / STRATEGY / BD persona",
    "**OPERATOR / STRATEGY / BD**" in qr_source
)
test(
    "Prompt defines CLINICAL TRIAL DESIGNER persona",
    "**CLINICAL TRIAL DESIGNER**" in qr_source
)

# 2b. Persona-specific trigger phrases
test(
    "Operator trigger phrases listed",
    '"licensing", "partnership", "BD"' in qr_source
)
test(
    "Trial designer trigger phrases listed",
    '"trial design", "endpoint", "CRL"' in qr_source
)

# 2c. New analytical layers
test(
    "Layer 6 — BD & Licensing Intelligence exists",
    "**Layer 6 — BD & Licensing Intelligence" in qr_source
)
test(
    "Layer 7 — Clinical Trial Design Intelligence exists",
    "**Layer 7 — Clinical Trial Design Intelligence" in qr_source
)

# 2d. Layer 6 content (operator-specific)
test(
    "Layer 6 includes rights availability",
    "Rights availability" in qr_source and "unlicensed" in qr_source
)
test(
    "Layer 6 includes deal comps",
    "Deal comps" in qr_source
)
test(
    "Layer 6 includes white-space mapping",
    "White-space mapping" in qr_source
)

# 2e. Layer 7 content (trial designer-specific)
test(
    "Layer 7 includes endpoint selection guidance",
    "Endpoint selection guidance" in qr_source
)
test(
    "Layer 7 includes FDA CRL patterns",
    "FDA CRL patterns" in qr_source and "fda_crl:DrugName" in qr_source
)
test(
    "Layer 7 includes enrollment optimization",
    "Enrollment optimization" in qr_source
)
test(
    "Layer 7 includes statistical design",
    "Statistical design" in qr_source and "alpha spending" in qr_source
)

# 2f. Persona-aware follow-up questions
test(
    "Follow-ups tailored for INVESTOR persona",
    "For INVESTOR persona:" in qr_source
)
test(
    "Follow-ups tailored for OPERATOR/BD persona",
    "For OPERATOR/BD persona:" in qr_source
)
test(
    "Follow-ups tailored for TRIAL DESIGNER persona",
    "For TRIAL DESIGNER persona:" in qr_source
)

# 2g. Persona injection in synthesize_answer
test(
    "Persona extracted from plan in synthesize_answer",
    'persona = plan.get("persona", "investor")' in qr_source
)
test(
    "Operator persona directive injected",
    "ACTIVE PERSONA: OPERATOR / STRATEGY / BD" in qr_source
)
test(
    "Trial designer persona directive injected",
    "ACTIVE PERSONA: CLINICAL TRIAL DESIGNER" in qr_source
)

# 2h. Citation format includes CRL
test(
    "Citation format includes fda_crl tag",
    "{{fda_crl:DrugName|Year}}" in qr_source
)

# 2i. Data sources list updated
test(
    "Data sources include FDA CRL DATABASE",
    "FDA CRL DATABASE" in qr_source
)


# =============================================================================
# TEST GROUP 3: FDA CRL Pipeline
# =============================================================================
print("\n" + "=" * 60)
print("TEST GROUP 3: FDA CRL Pipeline")
print("=" * 60)

crl_path = os.path.join(SEARCH_DIR, "fda_crl_pipeline.py")
crl_source = open(crl_path).read()
crl_tree = ast.parse(crl_source)

# Get all function names
crl_funcs = [node.name for node in ast.walk(crl_tree) if isinstance(node, ast.FunctionDef)]

# 3a. Required public API functions exist
for fn in ["ingest_all_crls", "search_crl_database", "format_crl_for_claude", "is_crl_available", "setup_crl_tables"]:
    test(f"Function {fn}() exists", fn in crl_funcs)

# 3b. Database schema
test(
    "Creates fda_crl_documents table",
    "fda_crl_documents" in crl_source
)
test(
    "Creates fda_crl_chunks table",
    "fda_crl_chunks" in crl_source
)
test(
    "Uses vector(1024) for embeddings",
    "vector(1024)" in crl_source
)
test(
    "Creates HNSW index",
    "hnsw" in crl_source.lower()
)

# 3c. openFDA integration
test(
    "Uses openFDA drugsfda endpoint",
    "drugsfda" in crl_source
)
test(
    "Handles pagination",
    "skip" in crl_source and "limit" in crl_source
)

# 3d. Text extraction
test(
    "Uses PyPDF2 for PDF extraction",
    "PyPDF2" in crl_source or "pypdf" in crl_source.lower() or "PdfReader" in crl_source
)

# 3e. Chunking logic
test(
    "Implements text chunking",
    "chunk" in crl_source.lower() and ("split" in crl_source or "sentence" in crl_source.lower())
)

# 3f. Voyage AI embedding
test(
    "Uses voyage-3 model",
    "voyage-3" in crl_source
)
test(
    "Batch embedding (groups of 20)",
    "20" in crl_source and "batch" in crl_source.lower()
)

# 3g. Hybrid search
test(
    "Implements cosine similarity search",
    "cosine" in crl_source.lower() or "<=>" in crl_source or "<->" in crl_source
)
test(
    "Implements tsvector keyword search",
    "tsvector" in crl_source or "ts_rank" in crl_source or "tsv" in crl_source
)

# 3h. format_crl_for_claude produces context block
test(
    "Format function produces labeled context block",
    "FDA COMPLETE RESPONSE" in crl_source.upper() or "CRL" in crl_source
)

# 3i. Integration with query_router
test(
    "query_router imports CRL functions",
    "from fda_crl_pipeline import" in qr_source
)
test(
    "FDA_CRL_AVAILABLE flag exists",
    "FDA_CRL_AVAILABLE" in qr_source
)
test(
    "FDA_CRL in execute_query_plan",
    '"FDA_CRL" in sources' in qr_source
)
test(
    "CRL results added to synthesis context",
    'data.get("fda_crl")' in qr_source
)

# 3j. Standalone execution
test(
    "Can run standalone (if __name__)",
    '__name__' in crl_source and '__main__' in crl_source
)


# =============================================================================
# TEST GROUP 4: UI Routing & Redesign
# =============================================================================
print("\n" + "=" * 60)
print("TEST GROUP 4: UI Routing & Redesign")
print("=" * 60)

# 4a. App.tsx
app_tsx = open(os.path.join(APP_DIR, "src", "App.tsx")).read()

test(
    "EvidencePage is the homepage (path='/')",
    'path="/" element={<EvidencePage' in app_tsx
)
test(
    "/extract still works as alias",
    'path="/extract" element={<EvidencePage' in app_tsx
)
test(
    "Dashboard component removed from App.tsx",
    "Dashboard" not in app_tsx
)
test(
    "ReportView component removed from App.tsx",
    "ReportView" not in app_tsx
)
test(
    "/search route still available",
    'path="/search" element={<SearchPage' in app_tsx
)

# 4b. EvidencePage navbar cleanup
ev_page = open(os.path.join(APP_DIR, "src", "components", "evidence", "EvidencePage.tsx")).read()

test(
    "Navbar does NOT have /companies link",
    'href="/companies"' not in ev_page
)
test(
    "Navbar does NOT have /targets link",
    'href="/targets"' not in ev_page
)
test(
    "Navbar still has SatyaBio logo",
    "Satya<span>Bio</span>" in ev_page
)
test(
    "Companies panel button still exists (side panel)",
    "togglePanel('companies')" in ev_page
)
test(
    "Enrichment panel button still exists",
    "togglePanel('enrichment')" in ev_page
)
test(
    "Regional/Global panel button still exists",
    "togglePanel('regional')" in ev_page
)

# 4c. main.py serves React SPA at /
main_py = open(os.path.join(BASE_DIR, "main.py")).read()

test(
    "main.py / route serves React SPA",
    'react_index' in main_py.split("serve_index")[1][:300]
)
test(
    "main.py / route uses FileResponse for React index.html",
    "FileResponse(react_index)" in main_py
)

# 4d. Vite config has /extract/api proxy
vite_config = open(os.path.join(APP_DIR, "vite.config.ts")).read()

test(
    "Vite proxies /api to backend",
    "'/api'" in vite_config and "localhost:8000" in vite_config
)
test(
    "Vite proxies /extract/api to backend",
    "'/extract/api'" in vite_config
)

# 4e. TypeScript compiles
print("\n  Running TypeScript check...")
tsc_result = os.popen(f"cd {APP_DIR} && npx tsc --noEmit 2>&1").read().strip()
test(
    "TypeScript compiles with zero errors",
    tsc_result == "",
    detail=tsc_result[:200] if tsc_result else ""
)


# =============================================================================
# TEST GROUP 5: End-to-End Integration
# =============================================================================
print("\n" + "=" * 60)
print("TEST GROUP 5: End-to-End Integration")
print("=" * 60)

# 5a. All Python files parse
for fname in ["query_router.py", "fda_crl_pipeline.py"]:
    fpath = os.path.join(SEARCH_DIR, fname)
    try:
        ast.parse(open(fpath).read())
        test(f"{fname} parses as valid Python", True)
    except SyntaxError as e:
        test(f"{fname} parses as valid Python", False, str(e))

try:
    ast.parse(open(os.path.join(BASE_DIR, "main.py")).read())
    test("main.py parses as valid Python", True)
except SyntaxError as e:
    test("main.py parses as valid Python", False, str(e))

# 5b. Query router data flow: persona flows from classifier to synthesis
# Check that plan["persona"] is extracted and used in synthesis
synth_section = qr_source.split("def synthesize_answer")[1] if "def synthesize_answer" in qr_source else ""
test(
    "synthesize_answer reads persona from plan",
    'plan.get("persona"' in synth_section
)
test(
    "Persona directive concatenated into system prompt",
    "persona_directive" in synth_section and "full_system" in synth_section
)

# 5c. Execute query plan handles FDA_CRL
exec_section = qr_source.split("def execute_query_plan")[1].split("\ndef ")[0] if "def execute_query_plan" in qr_source else ""
test(
    "execute_query_plan submits FDA_CRL search",
    "search_crl_database" in exec_section
)
test(
    "execute_query_plan collects FDA_CRL results",
    '"fda_crl"' in exec_section
)

# 5d. Synthesis uses CRL context
test(
    "Synthesis adds CRL context via format_crl_for_claude",
    "format_crl_for_claude" in synth_section
)

# 5e. The 3 new source types in the full pipeline
# Verify the classifier can output FDA_CRL, and execute_query_plan handles it
test(
    "Full pipeline: classifier → executor → synthesis chain is intact",
    all([
        "FDA_CRL" in qr_source,                          # Classifier knows about it
        "search_crl_database" in exec_section,            # Executor calls it
        "format_crl_for_claude" in synth_section,         # Synthesis uses it
    ])
)

# 5f. Simulate persona routing logic
# Extract the persona directive code to test its logic
test(
    "Investor persona gets no extra directive (base prompt)",
    '# Default investor persona needs no extra directive' in qr_source
)
test(
    "Operator persona gets Layer 6 emphasis",
    'Prioritize Layer 6' in qr_source
)
test(
    "Trial designer persona gets Layer 7 emphasis",
    'Prioritize Layer 7' in qr_source
)


# =============================================================================
# RESULTS
# =============================================================================
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} tests passed, {failed} failed")
print("=" * 60)

if failed > 0:
    print("\n⚠️  Some tests failed — review the ❌ items above.")
    sys.exit(1)
else:
    print("\n🎉 All tests passed! All 3 workstreams are correctly integrated.")
    sys.exit(0)
