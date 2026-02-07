import json
import os
import shutil
from pathlib import Path

from extraction.exceptions import ValidationError, WriteError
from extraction.schema_validator import SchemaValidator


class DataWriter:
    def __init__(self, data_root: str = "data/companies", validate: bool = True):
        self.data_root = Path(data_root)
        self.validate = validate
        self._validator = SchemaValidator()

    def write_company(self, ticker: str, data: dict) -> Path:
        if self.validate:
            result = self._validator.validate_company(data)
            if not result.valid:
                raise ValidationError(result.errors, result.warnings)
        path = self.data_root / ticker / "company.json"
        self._write_json(path, data)
        return path

    def write_asset(self, ticker: str, asset_id: str, data: dict) -> Path:
        if self.validate:
            result = self._validator.validate_asset(data)
            if not result.valid:
                raise ValidationError(result.errors, result.warnings)
        path = self.data_root / ticker / f"{asset_id}.json"
        self._write_json(path, data)
        return path

    def _write_json(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        # Backup existing file
        if path.exists():
            shutil.copy2(path, str(path) + ".bak")

        tmp_path = Path(str(path) + ".tmp")
        try:
            content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
            tmp_path.write_text(content, encoding="utf-8")
            os.replace(tmp_path, path)
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            raise WriteError(f"Failed to write {path}: {e}") from e
