COMPANY_EXPECTED_KEYS = {
    "_metadata", "ticker", "name", "company",
    "investment_thesis_summary", "platform", "financials",
    "investment_analysis", "pipeline_summary", "catalysts",
    "management_track_record", "sources",
}

ASSET_EXPECTED_KEYS = {
    "_metadata", "asset", "target", "mechanism", "regulatory",
    "partnership", "indications", "market_opportunity", "pharmacology",
    "clinical_data", "upcoming_trials", "biomarkers",
    "differentiation_claims", "investment_analysis", "catalysts",
    "competitive_landscape", "ip_landscape", "sources",
    "preclinical_data", "safety_summary",
}


class ValidationResult:
    def __init__(self, valid: bool, errors: list[str], warnings: list[str]):
        self.valid = valid
        self.errors = errors
        self.warnings = warnings


class SchemaValidator:
    def validate(self, data: dict, schema_type: str) -> ValidationResult:
        if schema_type == "company":
            return self.validate_company(data)
        elif schema_type == "asset":
            return self.validate_asset(data)
        else:
            raise ValueError(f"Unknown schema type: '{schema_type}'")

    def validate_company(self, data: dict) -> ValidationResult:
        errors = []
        warnings = []

        # Required fields
        if "_metadata" not in data:
            errors.append("Missing '_metadata'")
        elif "version" not in data["_metadata"]:
            errors.append("Missing '_metadata.version'")

        if "ticker" not in data:
            errors.append("Missing 'ticker' at root")
        if "name" not in data:
            errors.append("Missing 'name' at root")

        if "company" not in data:
            errors.append("Missing 'company' dict")
        elif isinstance(data["company"], dict):
            if "name" not in data["company"]:
                errors.append("Missing 'company.name'")
            if "ticker" not in data["company"]:
                errors.append("Missing 'company.ticker'")

        # Banned fields
        self._check_source_slide(data, "", errors)

        # Warnings
        for key in ("investment_thesis_summary", "platform", "financials"):
            if key not in data:
                warnings.append(f"Missing recommended section: '{key}'")

        if "investment_thesis_summary" in data:
            its = data["investment_thesis_summary"]
            if isinstance(its, dict) and not its.get("key_value_drivers"):
                warnings.append("Empty 'key_value_drivers'")

        # Unknown keys
        unknown = set(data.keys()) - COMPANY_EXPECTED_KEYS
        for key in sorted(unknown):
            warnings.append(f"Unknown top-level key: '{key}'")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_asset(self, data: dict) -> ValidationResult:
        errors = []
        warnings = []

        # Required fields
        if "_metadata" not in data:
            errors.append("Missing '_metadata'")
        elif "version" not in data["_metadata"]:
            errors.append("Missing '_metadata.version'")

        if "asset" not in data:
            errors.append("Missing 'asset' dict")
        elif isinstance(data["asset"], dict):
            for field in ("name", "company", "ticker", "stage"):
                if field not in data["asset"]:
                    errors.append(f"Missing 'asset.{field}'")

        # Banned fields
        self._check_source_slide(data, "", errors)

        # Warnings
        for key in ("target", "clinical_data", "competitive_landscape"):
            if key not in data:
                warnings.append(f"Missing recommended section: '{key}'")

        # Unknown keys
        unknown = set(data.keys()) - ASSET_EXPECTED_KEYS
        for key in sorted(unknown):
            warnings.append(f"Unknown top-level key: '{key}'")

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
