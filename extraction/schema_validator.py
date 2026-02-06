from pathlib import Path
import json


class ValidationResult:
    def __init__(self, valid: bool, errors: list[str], warnings: list[str]):
        self.valid = valid
        self.errors = errors
        self.warnings = warnings


class SchemaValidator:
    def validate(self, data: dict, schema_type: str) -> ValidationResult:
        errors = []
        warnings = []

        self._check_source_slide(data, "", errors)

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _check_source_slide(self, obj, path: str, errors: list[str]):
        """Recursively check for bare source_slide keys."""
        if isinstance(obj, dict):
            if "source_slide" in obj:
                errors.append(
                    f"Banned field 'source_slide' at {path or 'root'}. "
                    "Use 'source' object instead."
                )
            for k, v in obj.items():
                self._check_source_slide(v, f"{path}.{k}", errors)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._check_source_slide(item, f"{path}[{i}]", errors)
