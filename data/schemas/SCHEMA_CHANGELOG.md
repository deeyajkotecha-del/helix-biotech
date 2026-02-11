# Schema Changelog

## v2.1 (2026-02-11)

First machine-readable schema release. Schema definitions now live in JSON files
(`asset_schema.json`, `company_schema.json`) that drive both validation and rendering.

### New sections (asset)

- **`pharmacology`** — PK parameters (half-life, Cmax, AUC, Tmax, bioavailability, food effect), dose-response data, target engagement, PK summary
- **`ip_landscape`** — Composition of matter patents, method of use patents, regulatory exclusivity, freedom-to-operate assessment
- **`_extraction_quality`** — Completeness score, missing fields list, data quality notes, extraction date, reviewer

### Restructured sections (asset)

- **`regulatory`** — Previously a flat object with `fda_designations` list. Now uses `designations[]` array (each with designation, indication, date, source) + `planned_pathway` + `filing_timeline`
- **`differentiation_claims`** — Previously freeform object. Now array of `{claim, evidence, source}` objects
- **`competitive_landscape`** — Now explicitly `{competitors: [...], our_advantages: [...]}`

### Backward compatibility

- v2.0 data files remain fully valid under v2.1
- New sections are purely additive — missing sections produce WARNINGs, never ERRORs
- The renderer skips absent sections silently
- `clinical_data` continues to accept all three formats: named sections (KYMR-style), flat structure (NUVL-style), and `trials[]` array

---

## v2.0 (2026-01-01)

Initial documented schema. See `data/companies/SCHEMA.md` for original specification.

### Key features
- Nested `target.biology` object with `simple_explanation`
- Flexible `clinical_data` supporting named sections or flat format
- Source citation objects (`{id, slide, verified}`) replacing bare `source_slide` fields
- Company and asset schemas with required/recommended field tiers
