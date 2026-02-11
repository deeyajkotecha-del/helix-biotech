#!/usr/bin/env python3
"""
Validate biotech company/asset JSON files against v2.1 schema definitions.

Usage:
    python scripts/validate_data.py data/companies/KYMR/           # Validate folder
    python scripts/validate_data.py data/companies/KYMR/kt621.json # Single file
    python scripts/validate_data.py --all                          # All companies
    python scripts/validate_data.py --all --summary                # One-line summary
    python scripts/validate_data.py --all --fix-suggestions        # Show what's missing
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Resolve project root relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SCHEMAS_DIR = PROJECT_ROOT / "data" / "schemas"
COMPANIES_DIR = PROJECT_ROOT / "data" / "companies"


def load_schema(schema_path: Path) -> dict:
    """Load and return a schema JSON file."""
    with open(schema_path) as f:
        return json.load(f)


def get_nested(data: dict, dotted_path: str):
    """Walk a dotted path like 'asset.name' into nested dicts. Returns (found, value)."""
    parts = dotted_path.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def infer_type_str(value) -> str:
    """Return a human-friendly type string for a Python value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) or isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def check_banned_fields(data, path: str, banned: list[str], errors: list[str]):
    """Recursively scan for banned field names."""
    if isinstance(data, dict):
        for key, val in data.items():
            full = f"{path}.{key}" if path else key
            if key in banned:
                errors.append(f"Banned field '{key}' at {full} — use 'source' object instead")
            check_banned_fields(val, full, banned, errors)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            check_banned_fields(item, f"{path}[{i}]", banned, errors)


def validate_file(filepath: Path, asset_schema: dict, company_schema: dict) -> dict:
    """
    Validate a single JSON file against the appropriate schema.
    Returns {"path": str, "type": str, "errors": [...], "warnings": [...]}.
    """
    result = {"path": str(filepath), "type": "unknown", "errors": [], "warnings": []}

    # Load JSON
    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result["errors"].append(f"Invalid JSON: {e}")
        return result

    if not isinstance(data, dict):
        result["errors"].append("Root must be a JSON object")
        return result

    # Detect schema type
    is_company = filepath.name == "company.json"
    schema = company_schema if is_company else asset_schema
    result["type"] = "company" if is_company else "asset"

    meta = schema.get("_schema_meta", {})
    required_fields = meta.get("required_fields", [])
    known_sections = set(meta.get("sections", []))
    banned = meta.get("banned_fields", [])
    v21_new = set(meta.get("v21_new_sections", []))

    # 1. Required field check
    for field_path in required_fields:
        found, _ = get_nested(data, field_path)
        if not found:
            result["errors"].append(f"Missing required field: {field_path}")

    # 2. Banned field check
    check_banned_fields(data, "", banned, result["errors"])

    # 3. Unknown top-level key check
    for key in data.keys():
        if key not in known_sections:
            result["warnings"].append(f"Unknown top-level key: '{key}'")

    # 4. v2.1-only section check (warning only, not error)
    for section in v21_new:
        if section not in data:
            result["warnings"].append(f"Missing v2.1 section: '{section}' (optional)")

    # 5. Basic type checks against template
    template = schema.get("_template", {})
    for key, expected in template.items():
        if key.startswith("_") and key != "_metadata" and key != "_extraction_quality":
            continue
        if key not in data:
            continue
        actual = data[key]
        # Check top-level type expectations
        if isinstance(expected, dict) and not isinstance(actual, (dict, type(None))):
            result["warnings"].append(
                f"Type mismatch for '{key}': expected object, got {infer_type_str(actual)}"
            )
        elif isinstance(expected, list) and not isinstance(actual, (list, type(None))):
            result["warnings"].append(
                f"Type mismatch for '{key}': expected array, got {infer_type_str(actual)}"
            )

    # 6. Recommended sections for company files
    if is_company:
        for section in meta.get("recommended_sections", []):
            if section not in data:
                result["warnings"].append(f"Missing recommended section: '{section}'")

    return result


def collect_json_files(target: Path) -> list[Path]:
    """Collect JSON files from a path (file or directory)."""
    if target.is_file():
        return [target] if target.suffix == ".json" else []
    if target.is_dir():
        return sorted(
            p for p in target.glob("*.json")
            if p.name != "index.json"
        )
    return []


def format_result(r: dict, fix_suggestions: bool = False) -> str:
    """Format a single file's validation result."""
    lines = []
    status = "PASS" if not r["errors"] else "FAIL"
    warn_count = len(r["warnings"])
    err_count = len(r["errors"])

    short_path = r["path"]
    # Shorten path for readability
    if "data/companies/" in short_path:
        short_path = short_path.split("data/companies/")[-1]

    summary = f"{'FAIL' if err_count else 'PASS'} {short_path}"
    if err_count:
        summary += f"  ({err_count} error{'s' if err_count != 1 else ''})"
    if warn_count:
        summary += f"  ({warn_count} warning{'s' if warn_count != 1 else ''})"

    lines.append(summary)

    if err_count:
        for e in r["errors"]:
            lines.append(f"    ERROR: {e}")
    if fix_suggestions and (err_count or warn_count):
        for w in r["warnings"]:
            lines.append(f"    WARN:  {w}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validate biotech data JSON files against v2.1 schema")
    parser.add_argument("path", nargs="?", help="File or directory to validate")
    parser.add_argument("--all", action="store_true", help="Validate all companies")
    parser.add_argument("--summary", action="store_true", help="Single-line summary only")
    parser.add_argument("--fix-suggestions", action="store_true", help="Show fix suggestions for failing files")
    args = parser.parse_args()

    if not args.all and not args.path:
        parser.print_help()
        sys.exit(1)

    # Load schemas once
    asset_schema = load_schema(SCHEMAS_DIR / "asset_schema.json")
    company_schema = load_schema(SCHEMAS_DIR / "company_schema.json")

    # Collect files
    files: list[Path] = []
    if args.all:
        for company_dir in sorted(COMPANIES_DIR.iterdir()):
            if company_dir.is_dir() and company_dir.name != "TEMPLATE":
                files.extend(collect_json_files(company_dir))
    else:
        target = Path(args.path)
        if not target.is_absolute():
            target = Path.cwd() / target
        files = collect_json_files(target)

    if not files:
        print("No JSON files found.")
        sys.exit(1)

    # Validate
    results = []
    for f in files:
        results.append(validate_file(f, asset_schema, company_schema))

    pass_count = sum(1 for r in results if not r["errors"])
    fail_count = len(results) - pass_count
    warn_count = sum(1 for r in results if r["warnings"])

    # Output
    if args.summary:
        print(f"{pass_count}/{len(results)} files valid, {fail_count} need attention")
        sys.exit(0 if fail_count == 0 else 1)

    # Detailed output
    passed = [r for r in results if not r["errors"]]
    failed = [r for r in results if r["errors"]]

    if failed:
        print(f"--- FAILING ({len(failed)} file{'s' if len(failed) != 1 else ''}) ---\n")
        for r in failed:
            print(format_result(r, args.fix_suggestions))
            print()

    if passed:
        if args.fix_suggestions:
            # Show each passing file with its warnings
            for r in passed:
                print(format_result(r, fix_suggestions=True))
        else:
            pass_paths = []
            for r in passed:
                p = r["path"]
                if "data/companies/" in p:
                    p = p.split("data/companies/")[-1]
                pass_paths.append(p)
            print(f"PASS  {len(passed)} file{'s' if len(passed) != 1 else ''} passed: {', '.join(pass_paths)}")

    if warn_count and not args.fix_suggestions:
        print(f"\n({warn_count} file{'s' if warn_count != 1 else ''} with warnings — use --fix-suggestions to see details)")

    print(f"\nTotal: {pass_count}/{len(results)} valid, {fail_count} error{'s' if fail_count != 1 else ''}")
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
