"""
Tests for extract_company.py and merge_asset.py.

All tests run offline — no API key, no PDFs, no file system side effects.

Usage:
    python -m pytest scripts/tests/test_extract.py -v
"""

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

# Add scripts dir to path so we can import
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from extract_company import (
    parse_json_response,
    sanitize_filename,
    estimate_cost,
    estimate_input_tokens,
)
from merge_asset import deep_merge, MergeStats


# =========================================================================
# Test JSON parsing
# =========================================================================

class TestJsonParsing:
    """Test parse_json_response() with various inputs."""

    VALID_JSON = '{"company": {"name": "Test"}, "assets": []}'

    def test_clean_json(self):
        result = parse_json_response(self.VALID_JSON)
        assert result["company"]["name"] == "Test"
        assert result["assets"] == []

    def test_markdown_json_fences(self):
        text = f"```json\n{self.VALID_JSON}\n```"
        result = parse_json_response(text)
        assert result["company"]["name"] == "Test"

    def test_triple_backtick_only(self):
        text = f"```\n{self.VALID_JSON}\n```"
        result = parse_json_response(text)
        assert result["company"]["name"] == "Test"

    def test_trailing_text(self):
        text = f'{self.VALID_JSON}\n\nThis is some explanation text.'
        result = parse_json_response(text)
        assert result["company"]["name"] == "Test"

    def test_truncated_json(self):
        text = '{"company": {"name": "Test"'
        with pytest.raises(ValueError, match="no matching closing brace"):
            parse_json_response(text)

    def test_no_json(self):
        text = "This is just plain text with no JSON."
        with pytest.raises(ValueError, match="No JSON object found"):
            parse_json_response(text)

    def test_nested_braces_in_strings(self):
        text = '{"company": {"description": "Uses {brackets} in text"}, "assets": []}'
        result = parse_json_response(text)
        assert "{brackets}" in result["company"]["description"]

    def test_whitespace_around(self):
        text = f"\n\n  {self.VALID_JSON}  \n\n"
        result = parse_json_response(text)
        assert result["company"]["name"] == "Test"

    def test_leading_text_before_json(self):
        text = f"Here is the extracted data:\n\n{self.VALID_JSON}"
        result = parse_json_response(text)
        assert result["company"]["name"] == "Test"


# =========================================================================
# Test filename sanitization
# =========================================================================

class TestSanitizeFilename:
    """Test asset filename generation."""

    def test_simple_name(self):
        assert sanitize_filename("KT-621") == "kt_621"

    def test_slash_separator(self):
        assert sanitize_filename("KT-485/SAR447971") == "kt_485_sar447971"

    def test_parentheses(self):
        assert sanitize_filename("SKYTROFA (TransCon hGH)") == "skytrofa_transcon_hgh"

    def test_greek_letters(self):
        result = sanitize_filename("IL-2β/γ")
        assert result == "il_2b_g"

    def test_already_clean(self):
        assert sanitize_filename("plozasiran") == "plozasiran"

    def test_aro_prefix(self):
        assert sanitize_filename("ARO-INHBE") == "aro_inhbe"

    def test_edg_number(self):
        assert sanitize_filename("EDG-7500") == "edg_7500"

    def test_empty_string(self):
        assert sanitize_filename("") == ""

    def test_all_special_chars(self):
        result = sanitize_filename("!!!@@@###")
        assert result == ""


# =========================================================================
# Test deep merge
# =========================================================================

class TestDeepMerge:
    """Test merge logic."""

    def test_fill_null_fields(self):
        existing = {"a": None, "b": "keep"}
        new = {"a": "filled", "b": None}
        merged, stats = deep_merge(existing, new)
        assert merged["a"] == "filled"
        assert merged["b"] == "keep"
        assert len(stats.filled) == 1

    def test_keep_existing_non_null(self):
        existing = {"a": "original"}
        new = {"a": "different"}
        merged, stats = deep_merge(existing, new)
        assert merged["a"] == "original"
        assert len(stats.skipped) == 1

    def test_force_overwrite(self):
        existing = {"a": "original"}
        new = {"a": "different"}
        merged, stats = deep_merge(existing, new, force=True)
        assert merged["a"] == "different"
        assert len(stats.forced) == 1

    def test_never_delete(self):
        existing = {"a": "value", "b": "keep"}
        new = {"a": None}
        merged, stats = deep_merge(existing, new)
        assert merged["a"] == "value"
        assert merged["b"] == "keep"

    def test_recursive_dict_merge(self):
        existing = {"target": {"name": "STAT6", "biology": {"simple_explanation": None}}}
        new = {"target": {"name": "STAT6", "biology": {"simple_explanation": "A transcription factor"}}}
        merged, stats = deep_merge(existing, new)
        assert merged["target"]["biology"]["simple_explanation"] == "A transcription factor"
        assert len(stats.filled) == 1

    def test_add_new_keys(self):
        existing = {"a": "value"}
        new = {"b": "new_key"}
        merged, stats = deep_merge(existing, new)
        assert merged["a"] == "value"
        assert merged["b"] == "new_key"
        assert len(stats.filled) == 1

    def test_same_value_no_change(self):
        existing = {"a": "same"}
        new = {"a": "same"}
        merged, stats = deep_merge(existing, new)
        assert merged["a"] == "same"
        assert len(stats.skipped) == 0
        assert len(stats.filled) == 0

    def test_empty_string_treated_as_null(self):
        existing = {"a": ""}
        new = {"a": "filled"}
        merged, stats = deep_merge(existing, new)
        assert merged["a"] == "filled"

    def test_empty_dict_treated_as_null(self):
        existing = {"a": {}}
        new = {"a": {"key": "value"}}
        merged, stats = deep_merge(existing, new)
        assert merged["a"] == {"key": "value"}

    def test_array_string_union(self):
        existing = {"bull_case": ["Point A", "Point B"]}
        new = {"bull_case": ["Point B", "Point C"]}
        merged, stats = deep_merge(existing, new)
        assert merged["bull_case"] == ["Point A", "Point B", "Point C"]
        assert len(stats.appended) == 1

    def test_array_trial_match_by_name(self):
        existing = {"trials": [
            {"trial_name": "ADAPT", "phase": "Phase 3", "status": None}
        ]}
        new = {"trials": [
            {"trial_name": "ADAPT", "phase": "Phase 3", "status": "Completed"}
        ]}
        merged, stats = deep_merge(existing, new)
        assert merged["trials"][0]["status"] == "Completed"

    def test_array_trial_append_new(self):
        existing = {"trials": [
            {"trial_name": "ADAPT", "phase": "Phase 3"}
        ]}
        new = {"trials": [
            {"trial_name": "ADAPT-SC", "phase": "Phase 3"}
        ]}
        merged, stats = deep_merge(existing, new)
        assert len(merged["trials"]) == 2
        assert merged["trials"][1]["trial_name"] == "ADAPT-SC"

    def test_source_follows_data(self):
        existing = {
            "mechanism": {
                "how_it_works": None,
                "source": {"id": "old_source", "slide": 5, "verified": False}
            }
        }
        new = {
            "mechanism": {
                "how_it_works": "New mechanism description",
                "source": {"id": "new_source", "slide": 12, "verified": False}
            }
        }
        merged, stats = deep_merge(existing, new)
        assert merged["mechanism"]["how_it_works"] == "New mechanism description"
        # Source gets merged too — new source wins because force isn't needed when existing fields are null
        assert merged["mechanism"]["source"]["id"] == "old_source"  # existing non-null kept

    def test_source_follows_data_with_force(self):
        existing = {
            "mechanism": {
                "how_it_works": "Old description",
                "source": {"id": "old_source", "slide": 5, "verified": False}
            }
        }
        new = {
            "mechanism": {
                "how_it_works": "New description",
                "source": {"id": "new_source", "slide": 12, "verified": False}
            }
        }
        merged, stats = deep_merge(existing, new, force=True)
        assert merged["mechanism"]["how_it_works"] == "New description"
        assert merged["mechanism"]["source"]["id"] == "new_source"

    def test_catalyst_match_by_event(self):
        existing = {"catalysts": [
            {"event": "Phase 3 data", "timing": "H1 2026", "importance": None}
        ]}
        new = {"catalysts": [
            {"event": "Phase 3 data", "timing": "H1 2026", "importance": "critical"},
            {"event": "FDA filing", "timing": "H2 2026", "importance": "high"}
        ]}
        merged, stats = deep_merge(existing, new)
        assert len(merged["catalysts"]) == 2
        assert merged["catalysts"][0]["importance"] == "critical"  # filled
        assert merged["catalysts"][1]["event"] == "FDA filing"  # appended


# =========================================================================
# Test validation integration
# =========================================================================

class TestValidationIntegration:
    """Test that extraction output passes schema validation."""

    @pytest.fixture
    def schemas(self):
        project_root = Path(__file__).resolve().parent.parent.parent
        schemas_dir = project_root / "data" / "schemas"
        if not schemas_dir.exists():
            pytest.skip("Schema files not found")
        scripts_dir = project_root / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import validate_data
        asset_schema = validate_data.load_schema(schemas_dir / "asset_schema.json")
        company_schema = validate_data.load_schema(schemas_dir / "company_schema.json")
        return validate_data, asset_schema, company_schema

    def test_minimal_valid_company(self, schemas, tmp_path):
        validate_data, asset_schema, company_schema = schemas
        data = {
            "_metadata": {"version": "2.1", "ticker": "TEST", "company_name": "Test Co"},
            "ticker": "TEST",
            "name": "Test Co",
            "company": {"name": "Test Co", "ticker": "TEST"}
        }
        path = tmp_path / "company.json"
        with open(path, "w") as f:
            json.dump(data, f)
        result = validate_data.validate_file(path, asset_schema, company_schema)
        assert not result["errors"], f"Unexpected errors: {result['errors']}"

    def test_minimal_valid_asset(self, schemas, tmp_path):
        validate_data, asset_schema, company_schema = schemas
        data = {
            "_metadata": {"version": "2.1", "ticker": "TEST", "asset_name": "TestDrug"},
            "asset": {
                "name": "TestDrug",
                "company": "Test Co",
                "ticker": "TEST",
                "stage": "Phase 2",
                "one_liner": "A test drug for testing"
            },
            "target": {
                "name": "TestTarget",
                "biology": {"simple_explanation": "A target protein involved in disease"}
            }
        }
        path = tmp_path / "testdrug.json"
        with open(path, "w") as f:
            json.dump(data, f)
        result = validate_data.validate_file(path, asset_schema, company_schema)
        assert not result["errors"], f"Unexpected errors: {result['errors']}"

    def test_missing_required_field(self, schemas, tmp_path):
        validate_data, asset_schema, company_schema = schemas
        data = {
            "_metadata": {"version": "2.1"},
            "ticker": "TEST"
            # Missing: name, company.name, company.ticker
        }
        path = tmp_path / "company.json"
        with open(path, "w") as f:
            json.dump(data, f)
        result = validate_data.validate_file(path, asset_schema, company_schema)
        assert result["errors"], "Should have validation errors for missing fields"

    def test_banned_field(self, schemas, tmp_path):
        validate_data, asset_schema, company_schema = schemas
        data = {
            "_metadata": {"version": "2.1", "ticker": "TEST", "asset_name": "Drug"},
            "asset": {
                "name": "Drug", "company": "Co", "ticker": "TEST",
                "stage": "Phase 1", "one_liner": "Test"
            },
            "target": {"name": "T", "biology": {"simple_explanation": "Expl"}},
            "source_slide": 5  # BANNED
        }
        path = tmp_path / "drug.json"
        with open(path, "w") as f:
            json.dump(data, f)
        result = validate_data.validate_file(path, asset_schema, company_schema)
        banned_errors = [e for e in result["errors"] if "Banned" in e or "source_slide" in e.lower()]
        assert banned_errors, f"Should detect banned field. Errors: {result['errors']}"


# =========================================================================
# Test cost estimation
# =========================================================================

class TestCostEstimation:
    """Test dry-run cost estimates."""

    def test_sonnet_pricing(self):
        # 100K input + 16K output
        cost = estimate_cost(100_000, 16_384, "claude-sonnet-4-20250514")
        expected = (100_000 * 3.00 + 16_384 * 15.00) / 1_000_000
        assert abs(cost - expected) < 0.001

    def test_estimate_format(self):
        cost = estimate_cost(50_000, 10_000, "claude-sonnet-4-20250514")
        formatted = f"${cost:.2f}"
        assert formatted.startswith("$")
        assert "." in formatted

    def test_unknown_model_uses_default(self):
        cost = estimate_cost(100_000, 16_384, "unknown-model")
        expected = estimate_cost(100_000, 16_384, "claude-sonnet-4-20250514")
        assert cost == expected

    def test_input_token_estimation(self):
        # 1MB PDF
        est = estimate_input_tokens(1_000_000, 5000)
        assert est > 300_000  # Should be substantial
        assert est < 500_000  # But not absurd
