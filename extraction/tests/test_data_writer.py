import json
from pathlib import Path

import pytest
from extraction.data_writer import DataWriter
from extraction.exceptions import ValidationError


def _valid_company():
    return {
        "_metadata": {"version": "2.0"},
        "ticker": "TEST",
        "name": "Test Co",
        "company": {"name": "Test Co", "ticker": "TEST"},
    }


def _valid_asset():
    return {
        "_metadata": {"version": "2.2"},
        "asset": {"name": "Drug-1", "company": "Test Co", "ticker": "TEST", "stage": "Phase 1"},
    }


class TestWriteCompany:
    def test_writes_company_json(self, tmp_path):
        dw = DataWriter(data_root=str(tmp_path))
        path = dw.write_company("TEST", _valid_company())
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["ticker"] == "TEST"

    def test_creates_directory_if_needed(self, tmp_path):
        dw = DataWriter(data_root=str(tmp_path))
        dw.write_company("NEW", _valid_company())
        assert (tmp_path / "NEW" / "company.json").exists()


class TestWriteAsset:
    def test_writes_asset_json(self, tmp_path):
        dw = DataWriter(data_root=str(tmp_path))
        path = dw.write_asset("TEST", "drug1", _valid_asset())
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["asset"]["name"] == "Drug-1"


class TestBackupAndAtomicity:
    def test_backup_before_overwrite(self, tmp_path):
        dw = DataWriter(data_root=str(tmp_path))
        dw.write_company("TEST", _valid_company())
        dw.write_company("TEST", _valid_company())
        bak = tmp_path / "TEST" / "company.json.bak"
        assert bak.exists()

    def test_no_backup_on_first_write(self, tmp_path):
        dw = DataWriter(data_root=str(tmp_path))
        dw.write_company("TEST", _valid_company())
        bak = tmp_path / "TEST" / "company.json.bak"
        assert not bak.exists()

    def test_atomic_write_no_tmp_left(self, tmp_path):
        dw = DataWriter(data_root=str(tmp_path))
        dw.write_company("TEST", _valid_company())
        tmp_file = tmp_path / "TEST" / "company.json.tmp"
        assert not tmp_file.exists()


class TestFormatting:
    def test_json_formatting(self, tmp_path):
        dw = DataWriter(data_root=str(tmp_path))
        dw.write_company("TEST", _valid_company())
        content = (tmp_path / "TEST" / "company.json").read_text()
        # 2-space indent
        assert '  "' in content
        # Trailing newline
        assert content.endswith("\n")
        # Not double-newline
        assert not content.endswith("\n\n")


class TestValidation:
    def test_validation_before_write(self, tmp_path):
        dw = DataWriter(data_root=str(tmp_path))
        with pytest.raises(ValidationError):
            dw.write_company("TEST", {})
        # File should not have been created
        assert not (tmp_path / "TEST" / "company.json").exists()

    def test_skip_validation(self, tmp_path):
        dw = DataWriter(data_root=str(tmp_path), validate=False)
        path = dw.write_company("TEST", {"anything": "goes"})
        assert path.exists()
