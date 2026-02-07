class ExtractionError(Exception):
    """Base exception for extraction pipeline."""


class PDFProcessingError(ExtractionError):
    """PDF conversion or parsing failed."""


class ValidationError(ExtractionError):
    """Schema validation failed."""

    def __init__(self, errors: list[str], warnings: list[str] = None):
        self.errors = errors
        self.warnings = warnings or []
        super().__init__(
            f"Validation failed with {len(errors)} error(s): {'; '.join(errors)}"
        )


class DuplicateSourceError(ExtractionError):
    """Source ID already exists in index."""


class WriteError(ExtractionError):
    """Failed to write data file."""
