# Extraction Pipeline Design

## 1. Overview

The extraction pipeline converts a source PDF (corporate presentation, investor deck, conference poster) into structured JSON data files that power the SatyaBio application.

**End-to-end flow:**

```
PDF file
  → Split into per-page PNGs + extracted text
  → Store in sources/{source_id}/
  → Feed text to Claude API with schema-aware prompts
  → Parse response into company.json + {asset}.json files
  → Validate against expected schema
  → Write to data/companies/{TICKER}/
```

**Target output structure:**

```
data/companies/{TICKER}/
├── company.json              # Company profile, thesis, platform
├── {asset_slug}.json         # One per pipeline asset (e.g. kt579.json)
└── sources/
    ├── index.json            # Registry of all sources for this ticker
    └── {source_id}/
        ├── metadata.json     # Source details, slide map, extraction status
        ├── original.pdf      # Archived input PDF
        ├── slide_01.png      # Page renders (300 DPI)
        ├── slide_02.png
        ├── ...
        └── text/
            ├── slide_01.txt  # Extracted text per page
            ├── slide_02.txt
            └── ...
```

## 2. Modules

### PDFProcessor

**Responsibility:** Convert a PDF into per-page PNG images and extracted text files.

**Input:**
- `pdf_path: str` — path to input PDF
- `ticker: str` — company ticker (e.g. "KYMR")
- `source_id: str` — identifier for this source (e.g. "kymr_corporate_2026")

**Output:**
- Directory `data/companies/{TICKER}/sources/{source_id}/` containing:
  - `original.pdf` — copy of the input PDF
  - `slide_XX.png` — one PNG per page, 300 DPI, zero-padded numbering
  - `text/slide_XX.txt` — extracted text per page

**External deps:**
- `poppler-utils` — provides `pdftoppm` (PDF → PNG) and `pdftotext` (PDF → text)

**Error cases:**
| Error | Behavior |
|---|---|
| PDF not found | Raise `FileNotFoundError` with path |
| Corrupted PDF | Raise `PDFProcessingError` if pdftoppm returns non-zero |
| poppler not installed | Raise `DependencyError` with install instructions (`brew install poppler`) |
| Zero pages extracted | Raise `PDFProcessingError` — empty or image-only PDF |

**Key decisions:**
- 300 DPI balances readability with file size (~200-400KB per slide PNG)
- `pdftotext -layout` preserves spatial positioning of text (important for tables)
- Zero-padded slide numbers (`slide_01` not `slide_1`) for consistent sorting

---

### SourceManager

**Responsibility:** Manage `sources/index.json` and per-source `metadata.json` files. Handles source registration, deduplication, and status tracking.

**Input:**
- `ticker: str`
- Source metadata: `name`, `date`, `type`, `event` (optional)

**Output:**
- Created/updated `sources/index.json` with source entry
- Created `sources/{source_id}/metadata.json` with full metadata

**External deps:** None

**Error cases:**
| Error | Behavior |
|---|---|
| Invalid ticker | Raise `ValueError` — ticker must be 1-5 uppercase letters |
| Duplicate source_id | Raise `SourceExistsError` — must explicitly pass `overwrite=True` |
| Malformed existing index.json | Raise `SchemaError` with details |

**index.json schema** (matches existing KYMR structure):
```json
{
  "sources": [
    {
      "id": "kymr_corporate_2026",
      "name": "Kymera Therapeutics Corporate Presentation January 2026",
      "type": "corporate_presentation",
      "date": "2026-01-13",
      "total_slides": 67,
      "verified": false
    }
  ]
}
```

**metadata.json schema** (matches existing KYMR structure):
```json
{
  "id": "kymr_corporate_2026",
  "name": "...",
  "type": "corporate_presentation",
  "company": "KYMR",
  "date": "2026-01-13",
  "event": "JPM Healthcare Conference",
  "total_slides": 67,
  "extraction_status": "pending",
  "verification_status": "unverified",
  "slide_map": {
    "1": {"title": "...", "relevant_assets": []},
    "2": {"title": "...", "relevant_assets": ["kt621"]}
  }
}
```

**source_id generation:** `{ticker}_{type}_{year}` lowercased (e.g. `kymr_corporate_2026`). If a collision exists, append `_2`, `_3`, etc.

**Source types:** `corporate_presentation`, `investor_day`, `conference_poster`, `sec_filing`, `earnings_call`

---

### ExtractionEngine

**Responsibility:** Generate prompts from slide text, call Claude API, and parse the structured JSON response.

**Input:**
- `text_dir: str` — path to `text/` directory with slide_XX.txt files
- `company_name: str`
- `ticker: str`
- Existing data (optional) — for incremental updates

**Output:**
- `dict` — structured JSON matching company.json or asset.json schema

**External deps:**
- `anthropic` Python SDK

**Error cases:**
| Error | Behavior |
|---|---|
| API error (500, timeout) | Retry up to 3 times with exponential backoff |
| Rate limit (429) | Respect `retry-after` header, log warning |
| Malformed JSON response | Re-prompt once asking for valid JSON; if still bad, raise `ExtractionError` |
| Response missing required fields | Pass to SchemaValidator, return validation errors |

**Prompt strategy:**

The extraction runs in two passes:

1. **Company pass** — All slide text concatenated. Prompt asks for company-level fields: `company`, `investment_thesis_summary`, `platform`, `financials`. Uses the company.json schema as the expected output format.

2. **Asset pass** — For each asset detected, relevant slides only. Prompt asks for asset-level fields: `asset`, `target`, `clinical_data`, `competitive_landscape`. Uses the asset.json schema as the expected output format.

**Prompt template structure:**
```
You are extracting structured data from a {source_type} for {company_name} ({ticker}).

Here is the text content from the presentation:
---
{concatenated_slide_text}
---

Extract the following JSON structure. Only include information explicitly stated
in the source material. Use null for fields where information is not available.

{json_schema}
```

**Asset detection:** The engine scans slide text for drug/asset names and groups slides by asset. This produces the `slide_map.relevant_assets` in metadata.json and determines which slides feed into each asset extraction.

---

### SchemaValidator

**Responsibility:** Validate generated JSON against the expected structure for company and asset files.

**Input:**
- `data: dict` — the JSON data to validate
- `schema_type: str` — either `"company"` or `"asset"`

**Output:**
- `ValidationResult` with `valid: bool`, `errors: list[str]`, `warnings: list[str]`

**External deps:** None (hand-written validation, not jsonschema library — our schemas are small and specific enough)

**Error cases:**
| Error | Behavior |
|---|---|
| Missing `_metadata` block | Error — always required |
| Missing `_metadata.version` | Error — must be "2.0" |
| Missing `company`/`asset` top-level key | Error |
| Missing `ticker` or `name` at root | Error |
| Empty `key_value_drivers` array | Warning — likely incomplete extraction |
| Unknown top-level keys | Warning — may indicate schema drift |

**Validation rules by schema type:**

Company (`company.json`):
- Required: `_metadata`, `ticker`, `name`, `company` (with `name`, `ticker`)
- Optional but expected: `investment_thesis_summary`, `platform`, `financials`

Asset (`{asset}.json`):
- Required: `_metadata`, `asset` (with `name`, `company`, `ticker`, `stage`)
- Optional but expected: `target`, `clinical_data`, `competitive_landscape`

---

### DataWriter

**Responsibility:** Write validated JSON to the correct file paths under `data/companies/{TICKER}/`.

**Input:**
- `data: dict` — validated JSON
- `ticker: str`
- `file_type: str` — `"company"` or asset slug (e.g. `"kt579"`)

**Output:**
- Written file at `data/companies/{TICKER}/company.json` or `data/companies/{TICKER}/{slug}.json`

**External deps:** None

**Error cases:**
| Error | Behavior |
|---|---|
| Permission error | Raise `OSError` with path |
| Company directory doesn't exist | Create it (`mkdir -p` equivalent) |
| File already exists | Back up to `{file}.bak` before overwriting, log warning |

**Write behavior:**
- JSON formatted with 2-space indent, no trailing whitespace
- Atomic write: write to `{file}.tmp`, then `os.rename` to final path
- Backup existing file before overwrite (not on first creation)

## 3. Test Cases

Define tests for each module. These must pass before the module is considered complete.

### test_pdf_processor.py

```python
class TestPDFProcessor:
    def test_creates_source_directory_structure(self):
        """Given a valid PDF, creates data/companies/{TICKER}/sources/{source_id}/"""

    def test_converts_all_pages_to_png(self):
        """67-page PDF produces 67 slide_XX.png files"""

    def test_png_files_named_correctly(self):
        """Files named slide_01.png, slide_02.png, etc. (zero-padded)"""

    def test_extracts_text_from_all_pages(self):
        """67-page PDF produces 67 text/slide_XX.txt files"""

    def test_handles_nonexistent_pdf(self):
        """Raises FileNotFoundError with clear message"""

    def test_handles_corrupted_pdf(self):
        """Raises PDFProcessingError, doesn't create partial files"""

    def test_handles_empty_pdf(self):
        """Raises PDFProcessingError for 0-page PDF"""

    def test_idempotent_reprocessing(self):
        """Running twice on same PDF doesn't duplicate/corrupt files"""
```

### test_source_manager.py

```python
class TestSourceManager:
    def test_creates_index_if_not_exists(self):
        """Creates sources/index.json if company has no sources yet"""

    def test_adds_to_existing_index(self):
        """Appends new source to existing index.json"""

    def test_creates_metadata_json(self):
        """Creates {source_id}/metadata.json with correct fields"""

    def test_prevents_duplicate_source_id(self):
        """Raises DuplicateSourceError if source_id already exists"""

    def test_validates_required_metadata_fields(self):
        """Raises ValidationError if name, date, or type missing"""
```

### test_extraction_engine.py

```python
class TestExtractionEngine:
    def test_builds_prompt_with_all_slides(self):
        """Prompt includes text from all slide files"""

    def test_prompt_includes_company_context(self):
        """Prompt includes ticker and company name"""

    def test_parses_valid_json_response(self):
        """Extracts JSON from Claude response"""

    def test_handles_malformed_json_response(self):
        """Raises ExtractionError with details if JSON invalid"""

    def test_handles_api_rate_limit(self):
        """Raises RateLimitError, allows retry"""

    def test_handles_api_timeout(self):
        """Raises TimeoutError after configured threshold"""
```

### test_schema_validator.py

```python
class TestSchemaValidator:
    def test_valid_company_json_passes(self):
        """KYMR company.json passes validation"""

    def test_valid_asset_json_passes(self):
        """KYMR kt621.json passes validation"""

    def test_missing_meta_fails(self):
        """JSON without _meta section fails"""

    def test_missing_asset_name_fails(self):
        """Asset JSON without asset.name fails"""

    def test_invalid_stage_value_fails(self):
        """Stage not in allowed enum fails"""

    def test_returns_all_errors_not_just_first(self):
        """Multiple validation errors all reported"""
```

### test_data_writer.py

```python
class TestDataWriter:
    def test_writes_company_json(self):
        """Creates data/companies/{TICKER}/company.json"""

    def test_writes_asset_json(self):
        """Creates data/companies/{TICKER}/{asset_id}.json"""

    def test_creates_company_directory_if_needed(self):
        """Creates data/companies/{TICKER}/ if doesn't exist"""

    def test_backup_before_overwrite(self):
        """Existing file backed up before overwrite"""

    def test_atomic_write(self):
        """Write failure doesn't corrupt existing file"""
```

### test_integration.py

```python
class TestIntegration:
    def test_full_pipeline_with_kymr_pdf(self):
        """End-to-end: KYMR PDF → valid company + asset JSONs"""

    def test_output_structure_matches_existing_kymr(self):
        """Generated files have same structure as manual KYMR files"""

    def test_source_references_point_to_real_slides(self):
        """Every source.slide in output has corresponding PNG"""

    def test_pipeline_idempotent(self):
        """Running twice produces identical output"""
```

## 4. Pipeline Flow

```
                         ┌──────────────┐
                         │   CLI Entry   │
                         │  extract.py   │
                         └──────┬───────┘
                                │
                    pdf_path, ticker, source metadata
                                │
                                ▼
                      ┌─────────────────┐
                      │  SourceManager   │
                      │                  │
                      │ • Generate       │
                      │   source_id      │
                      │ • Create dirs    │
                      │ • Write initial  │
                      │   metadata.json  │
                      │ • Update         │
                      │   index.json     │
                      └────────┬────────┘
                               │
                          source_id, paths
                               │
                               ▼
                      ┌─────────────────┐
                      │  PDFProcessor    │
                      │                  │
                      │ • Copy original  │
                      │   PDF            │
                      │ • pdftoppm →     │
                      │   slide PNGs     │
                      │ • pdftotext →    │
                      │   slide TXTs     │
                      │ • Update         │
                      │   metadata with  │
                      │   total_slides   │
                      └────────┬────────┘
                               │
                         text files ready
                               │
                               ▼
                      ┌─────────────────┐
                      │ ExtractionEngine │
                      │                  │
                      │ • Read slide     │
                      │   text files     │
                      │ • Company pass:  │
                      │   all slides →   │
                      │   company.json   │
                      │ • Detect assets  │
                      │ • Asset pass:    │
                      │   per-asset      │
                      │   slides →       │
                      │   {asset}.json   │
                      │ • Build          │
                      │   slide_map      │
                      └────────┬────────┘
                               │
                       raw JSON dicts + slide_map
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
          ┌─────────────────┐   ┌─────────────────┐
          │ SchemaValidator  │   │  SourceManager   │
          │                  │   │                  │
          │ • Validate each  │   │ • Update         │
          │   JSON dict      │   │   metadata with  │
          │ • Collect errors  │   │   slide_map      │
          │   and warnings   │   │ • Set status     │
          └────────┬────────┘   └─────────────────┘
                   │
              validated data
                   │
                   ▼
          ┌─────────────────┐
          │   DataWriter     │
          │                  │
          │ • Backup         │
          │   existing files │
          │ • Atomic write   │
          │   company.json   │
          │ • Atomic write   │
          │   {asset}.json   │
          │   for each asset │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  SourceManager   │
          │                  │
          │ • Set            │
          │   extraction_    │
          │   status =       │
          │   "completed"    │
          └─────────────────┘
```

**CLI invocation:**

```bash
python -m extraction.extract \
  --pdf /path/to/presentation.pdf \
  --ticker KYMR \
  --name "Kymera Therapeutics Corporate Presentation January 2026" \
  --type corporate_presentation \
  --date 2026-01-13 \
  --event "JPM Healthcare Conference"
```

**Pipeline states tracked in metadata.json `extraction_status`:**
- `pending` — source registered, PDF not yet processed
- `processing` — PDF split into slides, extraction in progress
- `completed` — all JSON files written and validated
- `failed` — extraction failed (error details in metadata)

**Idempotency:** Re-running the pipeline on the same source_id with `--overwrite` will back up existing JSON files and re-extract. Without `--overwrite`, it fails if the source already exists.
