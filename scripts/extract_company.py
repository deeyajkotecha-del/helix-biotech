#!/usr/bin/env python3
"""
Extract structured company/asset data from a PDF using Claude API.

Produces v2.1 schema-compliant JSON files:
  - data/companies/{TICKER}/company.json
  - data/companies/{TICKER}/{asset_name}.json

Usage:
    python scripts/extract_company.py --pdf downloads/argx_jpm_2026.pdf --ticker ARGX
    python scripts/extract_company.py --pdf downloads/argx_jpm_2026.pdf --ticker ARGX --dry-run
    python scripts/extract_company.py --pdf downloads/argx_jpm_2026.pdf --ticker ARGX --overwrite

Environment:
    ANTHROPIC_API_KEY  — required (unless --dry-run)
"""

import argparse
import base64
import json
import logging
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SCHEMAS_DIR = PROJECT_ROOT / "data" / "schemas"
COMPANIES_DIR = PROJECT_ROOT / "data" / "companies"

DEFAULT_MODEL = "claude-sonnet-4-20250514"
EXPECTED_SCHEMA_VERSION = "2.1"
MAX_PDF_SIZE_MB = 50
WARN_PDF_SIZE_MB = 25
MAX_OUTPUT_TOKENS = 16384

# Pricing per 1M tokens
PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}

logger = logging.getLogger("extract_company")


# ---------------------------------------------------------------------------
# Helpers — self-contained, no imports from app/services/extraction/
# ---------------------------------------------------------------------------

def sanitize_filename(name: str) -> str:
    """Convert asset name to a clean, filesystem-safe filename.

    Examples:
        "KT-621"                → "kt_621"
        "KT-485/SAR447971"      → "kt_485_sar447971"
        "TransCon IL-2β/γ"      → "transcon_il_2b_g"
        "SKYTROFA (TransCon hGH)" → "skytrofa_transcon_hgh"
    """
    greek_map = {
        'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e',
        'ζ': 'z', 'η': 'e', 'θ': 'th', 'ι': 'i', 'κ': 'k',
        'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x', 'ο': 'o',
        'π': 'p', 'ρ': 'r', 'σ': 's', 'τ': 't', 'υ': 'u',
        'φ': 'ph', 'χ': 'ch', 'ψ': 'ps', 'ω': 'o',
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
    return result.strip('_')


def parse_json_response(text: str) -> dict:
    """Parse Claude's response into a dict, stripping markdown fences.

    Handles:
      - Clean JSON
      - ```json ... ``` fences
      - ``` ... ``` fences
      - Trailing text after JSON
      - Nested curly braces

    Raises ValueError on unparseable input.
    """
    text = text.strip()

    # Strip markdown fences
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.rstrip().endswith("```"):
        text = text[:text.rstrip().rfind("```")]

    text = text.strip()

    # Fast path: try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the outermost JSON object
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    # Walk forward to find matching close brace
    depth = 0
    in_string = False
    escape_next = False
    end = -1
    for i in range(start, len(text)):
        c = text[i]
        if escape_next:
            escape_next = False
            continue
        if c == '\\' and in_string:
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end == -1:
        raise ValueError("Truncated JSON: no matching closing brace found")

    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON after extraction: {e}")


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Estimate API cost in USD."""
    p = PRICING.get(model, PRICING[DEFAULT_MODEL])
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


def estimate_input_tokens(pdf_size_bytes: int, system_prompt_len: int) -> int:
    """Rough estimate of input tokens for a PDF + system prompt."""
    # PDF base64 is ~1.37x original size; ~4 chars per token
    pdf_tokens = int(pdf_size_bytes * 1.37 / 4)
    prompt_tokens = system_prompt_len // 4
    return pdf_tokens + prompt_tokens


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

def load_schema(path: Path) -> dict:
    """Load a schema JSON file."""
    with open(path) as f:
        return json.load(f)


def check_schema_version(schema: dict, label: str) -> None:
    """Warn if schema version doesn't match expected."""
    version = schema.get("_schema_meta", {}).get("version", "unknown")
    if version != EXPECTED_SCHEMA_VERSION:
        logger.warning(
            "Schema version mismatch for %s: expected %s, got %s. "
            "Prompt may be out of sync.",
            label, EXPECTED_SCHEMA_VERSION, version
        )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = '''\
You are a PhD-level biotechnology analyst extracting structured data from an investor presentation for institutional investment analysis.

## YOUR TASK

Extract data from the attached PDF and produce JSON files matching the SatyaBio v2.1 schema. You will produce:
1. One company.json file with company-level data
2. One {{asset_name}}.json file per pipeline program mentioned in the presentation

## OUTPUT FORMAT

Return a single JSON object with this wrapper structure:

```json
{{
  "company": {{ "... company.json contents ..." }},
  "assets": [
    {{
      "filename": "asset_name_lowercase.json",
      "data": {{ "... asset JSON contents ..." }}
    }}
  ]
}}
```

## COMPANY SCHEMA (company.json)

Every company.json must match this exact structure. Use null for any field not found in the source material.

```json
{company_template}
```

## ASSET SCHEMA ({{asset_name}}.json)

Every asset file must match this exact structure. Use null for any field not found in the source material.

```json
{asset_template}
```

## SOURCE CITATION RULES

This is the most important rule. Every factual claim must be traceable to a specific slide.

1. Source ID format: {{ticker_lower}}_{{source_type}}_{{year}} (e.g., argx_corporate_2026)
   Valid source types: corporate_presentation, investor_day, conference_poster, sec_filing, earnings_call
2. Source object format (used throughout the schema):
   {{"id": "argx_corporate_2026", "slide": 15, "verified": false}}
3. What MUST have a source: Clinical efficacy numbers, safety data, PK/PD data, trial enrollment, dosing, financial figures, regulatory designations, partnership economics, target biology, competitive claims
4. What gets NO source (SatyaBio analysis): Bull/bear case arguments, probability estimates, peak sales estimates, key debates, investment framing
5. Never use the banned field "source_slide" — always use the "source" object format

## EXTRACTION RULES

1. NEVER infer or fabricate data. If information is not in the PDF, use null. Do not guess market caps, patient populations, or clinical results.
2. Use null for missing values, never empty strings "", "N/A", "TBD", or "Unknown".
3. Preserve exact numbers: Extract percentages, p-values, confidence intervals, and sample sizes exactly as presented. Do not round.
4. Clinical data format: Use named sections format for clinical_data (e.g., "phase2_ad", "phase1_healthy_volunteer"). Each section should have: trial_name, design (type, population, n, dosing), efficacy_results, safety, source.
5. Asset filenames: Lowercase, alphanumeric + underscores only. Examples: kt621.json, plozasiran.json, edg7500.json, aro_inhbe.json
6. One-liners: Write a single compelling sentence capturing the key investment angle for each asset.
7. Stage values: Use exactly one of: "Approved", "Phase 3", "Phase 2/3", "Phase 2", "Phase 1/2", "Phase 1", "Preclinical", "Discovery"
8. Investment analysis: Bull and bear cases should be plain strings (not objects with point/evidence). Each item should be a standalone argument in 1-2 sentences.
9. Completeness: Fill in _extraction_quality.completeness_score (0-100) and _extraction_quality.missing_fields listing sections you could not populate from this source.

## WHAT MAKES A GOOD EXTRACTION

- Every efficacy number has a timepoint, dose group, and comparator context
- Safety data includes AE rates, SAEs, discontinuations, and differentiation vs competitors
- Target biology explains the "why" — why is this target relevant, what is the genetic validation
- Catalysts have specific timing ("H1 2026") not vague ("upcoming")
- Competitive landscape names specific competitor drugs and their limitations'''


def build_system_prompt(company_template: dict, asset_template: dict) -> str:
    """Build the full system prompt with schema templates injected."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        company_template=json.dumps(company_template, indent=2),
        asset_template=json.dumps(asset_template, indent=2),
    )


# ---------------------------------------------------------------------------
# API call with retry
# ---------------------------------------------------------------------------

RETRYABLE_ERRORS = ()  # Populated after import check


def call_api_with_retry(
    client,
    model: str,
    system_prompt: str,
    pdf_b64: str,
    ticker: str,
    source_id: str,
    max_attempts: int = 3,
) -> object:
    """Call Claude API with exponential backoff retry on transient errors."""
    backoff_delays = [2, 8, 30]

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info("API call attempt %d/%d", attempt, max_attempts)
            start_time = time.time()
            response = client.messages.create(
                model=model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system_prompt,
                messages=[{
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
                            "text": (
                                f"Extract all data for {ticker} from this presentation. "
                                f"Source ID: {source_id}"
                            ),
                        },
                    ],
                }],
            )
            elapsed = time.time() - start_time
            logger.info("API call completed in %.1fs", elapsed)
            return response, elapsed

        except RETRYABLE_ERRORS as e:
            if attempt == max_attempts:
                raise
            delay = backoff_delays[attempt - 1] if attempt - 1 < len(backoff_delays) else 30
            logger.warning(
                "API call failed (%s), retrying in %ds (attempt %d/%d)",
                e, delay, attempt, max_attempts
            )
            time.sleep(delay)

    # Should not reach here
    raise RuntimeError("Exhausted retries")


# ---------------------------------------------------------------------------
# Validation bridge — import from scripts/validate_data.py
# ---------------------------------------------------------------------------

def get_validator():
    """Import validate_file and load_schema from scripts/validate_data.py."""
    # Add scripts dir to path so we can import validate_data
    scripts_dir = str(SCRIPT_DIR)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import validate_data
    return validate_data


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------

def write_json_atomic(path: Path, data: dict, backup: bool = False) -> None:
    """Write JSON atomically: write to .tmp, then os.replace().

    If backup=True and the file already exists, create a timestamped backup.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if backup and path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_name(f"{path.name}.bak.{ts}")
        path.rename(backup_path)
        logger.info("Backed up %s → %s", path.name, backup_path.name)

    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract structured biotech data from a PDF using Claude API.",
        epilog="""
Examples:
  %(prog)s --pdf downloads/argx_jpm_2026.pdf --ticker ARGX
  %(prog)s --pdf downloads/argx_jpm_2026.pdf --ticker ARGX --dry-run
  %(prog)s --pdf downloads/argx_jpm_2026.pdf --ticker ARGX --overwrite
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pdf", required=True, help="Path to the PDF file")
    parser.add_argument("--ticker", required=True, help="Company ticker (1-5 uppercase letters)")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost without calling the API")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting existing files")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    # ---- Validate args ----
    ticker = args.ticker.upper()
    if not re.match(r'^[A-Z]{1,5}$', ticker):
        logger.error("Invalid ticker: %s (must be 1-5 uppercase letters)", ticker)
        sys.exit(2)

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        logger.error("PDF not found: %s", pdf_path)
        sys.exit(2)

    pdf_size_bytes = pdf_path.stat().st_size
    pdf_size_mb = pdf_size_bytes / (1024 * 1024)
    if pdf_size_mb > MAX_PDF_SIZE_MB:
        logger.error("PDF too large: %.1fMB (max %dMB)", pdf_size_mb, MAX_PDF_SIZE_MB)
        sys.exit(2)
    if pdf_size_mb > WARN_PDF_SIZE_MB:
        logger.warning("Large PDF: %.1fMB — extraction may be slow or expensive", pdf_size_mb)

    # ---- Load schemas ----
    asset_schema = load_schema(SCHEMAS_DIR / "asset_schema.json")
    company_schema = load_schema(SCHEMAS_DIR / "company_schema.json")
    check_schema_version(asset_schema, "asset_schema")
    check_schema_version(company_schema, "company_schema")

    asset_template = asset_schema.get("_template", {})
    company_template = company_schema.get("_template", {})

    system_prompt = build_system_prompt(company_template, asset_template)
    logger.debug("System prompt length: %d chars", len(system_prompt))

    # ---- Determine output directory ----
    company_dir = COMPANIES_DIR / ticker
    existing_company = (company_dir / "company.json").exists()
    if existing_company and not args.overwrite:
        output_dir = company_dir / "_drafts"
        logger.warning(
            "Existing data found for %s. Writing to _drafts/ (use --overwrite to replace)",
            ticker
        )
    else:
        output_dir = company_dir

    # ---- Dry run ----
    if args.dry_run:
        est_input = estimate_input_tokens(pdf_size_bytes, len(system_prompt))
        est_cost = estimate_cost(est_input, MAX_OUTPUT_TOKENS, args.model)
        print(f"\nDRY RUN: {ticker}")
        print(f"{'─' * 40}")
        print(f"PDF:              {pdf_path.name} ({pdf_size_mb:.1f}MB)")
        print(f"Model:            {args.model}")
        print(f"Est. input tokens: {est_input:,}")
        print(f"Max output tokens: {MAX_OUTPUT_TOKENS:,}")
        print(f"Est. cost:        ${est_cost:.2f}")
        print(f"Output dir:       {output_dir}")
        print(f"Existing data:    {'Yes' if existing_company else 'No'}")
        print(f"Overwrite:        {'Yes' if args.overwrite else 'No'}")
        sys.exit(0)

    # ---- Check API key ----
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set in environment")
        sys.exit(2)

    # ---- Import anthropic and set up retryable errors ----
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed. Run: pip install anthropic")
        sys.exit(2)

    global RETRYABLE_ERRORS
    RETRYABLE_ERRORS = (
        anthropic.APITimeoutError,
        anthropic.RateLimitError,
        anthropic.APIConnectionError,
    )

    client = anthropic.Anthropic(api_key=api_key)

    # ---- Read PDF ----
    logger.info("Reading PDF: %s (%.1fMB)", pdf_path.name, pdf_size_mb)
    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.standard_b64encode(f.read()).decode("ascii")

    # ---- Infer source ID ----
    year = datetime.now().strftime("%Y")
    source_id = f"{ticker.lower()}_corporate_presentation_{year}"

    # ---- Call API ----
    logger.info("Calling Claude API (%s)...", args.model)
    try:
        response, elapsed = call_api_with_retry(
            client, args.model, system_prompt, pdf_b64, ticker, source_id
        )
    except anthropic.AuthenticationError:
        logger.error("Authentication failed — check ANTHROPIC_API_KEY")
        sys.exit(2)
    except anthropic.BadRequestError as e:
        logger.error("Bad request: %s", e)
        sys.exit(2)
    except Exception as e:
        logger.error("API call failed after retries: %s", e)
        sys.exit(2)

    usage = response.usage
    actual_cost = estimate_cost(usage.input_tokens, usage.output_tokens, args.model)
    logger.info("Tokens: %s in / %s out", f"{usage.input_tokens:,}", f"{usage.output_tokens:,}")
    logger.info("Cost: $%.2f", actual_cost)

    # ---- Parse response ----
    response_text = response.content[0].text
    logger.debug("Response length: %d chars", len(response_text))

    # Save raw response for debugging
    raw_dir = company_dir / "_drafts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "_raw_response.json"
    with open(raw_path, "w") as f:
        json.dump({"response_text": response_text, "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}}, f, indent=2)
    logger.debug("Raw response saved to %s", raw_path)

    try:
        extracted = parse_json_response(response_text)
    except ValueError as e:
        logger.error("Failed to parse API response: %s", e)
        sys.exit(2)

    # ---- Split into files ----
    files_to_write = {}

    company_data = extracted.get("company")
    if company_data:
        files_to_write["company.json"] = company_data
    else:
        logger.warning("No company data in extraction response")

    for asset_entry in extracted.get("assets", []):
        filename = asset_entry.get("filename", "")
        data = asset_entry.get("data", {})
        if not filename:
            # Generate filename from asset name
            asset_name = data.get("asset", {}).get("name", "unknown")
            filename = sanitize_filename(asset_name) + ".json"
        # Ensure filename ends with .json
        if not filename.endswith(".json"):
            filename += ".json"
        # Sanitize the filename
        name_part = filename.rsplit(".json", 1)[0]
        filename = sanitize_filename(name_part) + ".json"
        files_to_write[filename] = data

    if not files_to_write:
        logger.error("No files extracted from response")
        sys.exit(2)

    logger.info("Extracted %d file(s): %s", len(files_to_write), ", ".join(files_to_write.keys()))

    # ---- Validate ----
    validator = get_validator()
    v_asset_schema = validator.load_schema(SCHEMAS_DIR / "asset_schema.json")
    v_company_schema = validator.load_schema(SCHEMAS_DIR / "company_schema.json")

    all_valid = True
    validation_results = {}
    for filename, data in files_to_write.items():
        is_company = filename == "company.json"
        # Write to temp file for validation
        tmp_file = output_dir / f".{filename}.validate_tmp"
        tmp_file.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_file, "w") as f:
            json.dump(data, f, indent=2)
        result = validator.validate_file(tmp_file, v_asset_schema, v_company_schema)
        tmp_file.unlink(missing_ok=True)
        validation_results[filename] = result
        if result["errors"]:
            all_valid = False

    # ---- Decide output directory based on validation ----
    if not all_valid and output_dir != (company_dir / "_drafts"):
        output_dir = company_dir / "_drafts"
        logger.warning("Validation failures detected — writing ALL files to _drafts/")

    # ---- Write files ----
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, data in files_to_write.items():
        file_path = output_dir / filename
        should_backup = args.overwrite and file_path.exists()
        write_json_atomic(file_path, data, backup=should_backup)

    # ---- Print summary ----
    quality_score = None
    missing_fields = []
    # Try to get quality from first asset
    for filename, data in files_to_write.items():
        if filename != "company.json":
            eq = data.get("_extraction_quality", {})
            if eq:
                quality_score = eq.get("completeness_score")
                missing_fields = eq.get("missing_fields", [])
                break

    print(f"\nEXTRACTION COMPLETE: {ticker}")
    print(f"{'─' * 40}")
    print(f"Model:          {args.model}")
    print(f"Input tokens:   {usage.input_tokens:,}")
    print(f"Output tokens:  {usage.output_tokens:,}")
    print(f"Cost:           ${actual_cost:.2f}")
    print(f"Duration:       {elapsed:.1f}s")
    print()
    print("Files:")
    for filename, result in validation_results.items():
        errs = len(result["errors"])
        warns = len(result["warnings"])
        dest = output_dir / filename
        if errs:
            status = "FAIL"
            detail = f" ({errs} error{'s' if errs != 1 else ''})"
        elif warns:
            status = "WARN"
            detail = f" ({warns} warning{'s' if warns != 1 else ''})"
        else:
            status = "PASS"
            detail = ""
        print(f"  {status}  {filename:<25s} → {dest}{detail}")

        # Print errors/warnings
        for e in result["errors"]:
            print(f"        ERROR: {e}")
        for w in result["warnings"][:3]:
            print(f"        WARN:  {w}")

    if quality_score is not None:
        missing_str = ", ".join(missing_fields[:5]) if missing_fields else "none"
        print(f"\nQuality: {quality_score}/100 (missing: {missing_str})")

    # ---- Exit code ----
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
