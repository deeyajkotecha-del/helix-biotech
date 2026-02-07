import json
from pathlib import Path

import pytest
from extraction.schema_validator import SchemaValidator

KYMR_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "companies" / "KYMR"


@pytest.fixture
def validator():
    return SchemaValidator()


@pytest.fixture
def kymr_company():
    return json.loads((KYMR_DIR / "company.json").read_text())


@pytest.fixture
def kymr_kt621():
    return json.loads((KYMR_DIR / "kt621.json").read_text())


class TestCompanyValidation:
    def test_valid_company_json_passes(self, validator, kymr_company):
        result = validator.validate(kymr_company, "company")
        assert result.valid, f"Unexpected errors: {result.errors}"

    def test_missing_company_key_fails(self, validator):
        data = {
            "_metadata": {"version": "2.0"},
            "ticker": "TEST",
            "name": "Test Co",
            # no "company" key
        }
        result = validator.validate_company(data)
        assert not result.valid
        assert any("company" in e for e in result.errors)


class TestAssetValidation:
    def test_valid_asset_json_passes(self, validator, kymr_kt621):
        result = validator.validate(kymr_kt621, "asset")
        assert result.valid, f"Unexpected errors: {result.errors}"

    def test_all_kymr_assets_pass(self, validator):
        for fname in ("kt579.json", "kt485.json"):
            data = json.loads((KYMR_DIR / fname).read_text())
            result = validator.validate_asset(data)
            assert result.valid, f"{fname} failed: {result.errors}"

    def test_missing_asset_name_fails(self, validator):
        data = {
            "_metadata": {"version": "2.2"},
            "asset": {"company": "X", "ticker": "X", "stage": "Phase 1"},
        }
        result = validator.validate_asset(data)
        assert not result.valid
        assert any("asset.name" in e for e in result.errors)


class TestGeneralValidation:
    def test_missing_metadata_fails(self, validator):
        result = validator.validate({}, "asset")
        assert not result.valid
        assert any("_metadata" in e for e in result.errors)

    def test_returns_all_errors_not_just_first(self, validator):
        # Empty dict should produce errors for _metadata, asset
        result = validator.validate_asset({})
        assert len(result.errors) >= 2

    def test_banned_source_slide_fails(self, validator):
        data = {
            "_metadata": {"version": "2.2"},
            "asset": {"name": "X", "company": "Y", "ticker": "Z", "stage": "Phase 1"},
            "clinical_data": {"source_slide": 5},
        }
        result = validator.validate_asset(data)
        assert not result.valid
        assert any("source_slide" in e for e in result.errors)

    def test_unknown_keys_warn(self, validator):
        data = {
            "_metadata": {"version": "2.2"},
            "asset": {"name": "X", "company": "Y", "ticker": "Z", "stage": "Phase 1"},
            "totally_new_key": {},
        }
        result = validator.validate_asset(data)
        assert result.valid  # warnings don't fail validation
        assert any("totally_new_key" in w for w in result.warnings)

    def test_validate_dispatches(self, validator):
        company_data = {
            "_metadata": {"version": "2.0"},
            "ticker": "X",
            "name": "X",
            "company": {"name": "X", "ticker": "X"},
        }
        result = validator.validate(company_data, "company")
        assert result.valid

        asset_data = {
            "_metadata": {"version": "2.2"},
            "asset": {"name": "X", "company": "Y", "ticker": "Z", "stage": "P1"},
        }
        result = validator.validate(asset_data, "asset")
        assert result.valid

        with pytest.raises(ValueError, match="Unknown schema type"):
            validator.validate({}, "bogus")
