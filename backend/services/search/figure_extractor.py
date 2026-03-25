"""
SatyaBio — Figure Extraction Pipeline

Extracts clinical figures (KM curves, waterfall plots, forest plots, swimmer
plots, spider plots, IC50 charts, brain penetrance data, etc.) from PDFs in the
document library, annotates them with structured metadata using Claude Vision,
and stores them for retrieval during search.

This is what makes the platform work like the NEJM/OpenEvidence screenshot — when
someone asks "show me the INAVO120 OS data", we surface the actual KM curve with
the hazard ratio, median OS, and p-value already extracted.

HOW IT WORKS:
  1. PyMuPDF (fitz) extracts every image from every PDF in the doc library
  2. Images are filtered by size (too small = logos/icons, too large = full pages)
  3. Claude Vision analyzes each candidate image to determine:
     - Is it a clinical figure? (vs. logo, diagram, org chart, etc.)
     - What type? (KM curve, waterfall, forest, swimmer, spider, bar chart, etc.)
     - What drug/trial? (extract NCT number, drug name, trial name)
     - What endpoints? (OS, PFS, ORR, DOR, etc.)
     - Key data points (HR, median, p-value, ORR %, etc.)
  4. Metadata is stored in Postgres; images are stored as files + referenced by path
  5. During search, the query router can find and surface relevant figures

SCHEMA:
  document_figures — one row per extracted figure with:
    - Source doc reference (filename, page, company ticker)
    - Image storage path
    - Figure type classification
    - Drug/trial identification
    - Endpoint data (structured JSON)
    - Claude's description of what the figure shows
    - Embedding vector for semantic search over figures

USAGE:
    # Extract figures from all PDFs in the library
    python3 figure_extractor.py --extract-all

    # Extract from a single PDF
    python3 figure_extractor.py --extract "path/to/document.pdf"

    # Search for figures
    python3 figure_extractor.py --search "inavolisib overall survival"

    # From module:
    from figure_extractor import search_figures, get_figures_for_drug
"""

import os
import sys
import json
import argparse
import base64
import hashlib
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")

if not DATABASE_URL:
    raise ImportError("NEON_DATABASE_URL not set — figure extractor disabled")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


# =============================================================================
# Schema
# =============================================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS document_figures (
    figure_id       SERIAL PRIMARY KEY,

    -- Source document reference
    source_filename TEXT NOT NULL,                  -- e.g., "RVMD_Q3_2024_Earnings.pdf"
    source_page     INTEGER,                       -- page number in the PDF
    source_ticker   TEXT,                          -- company ticker if known
    source_company  TEXT,                          -- company name
    source_doc_type TEXT,                          -- earnings, poster, 10-K, publication, deck

    -- Image storage
    image_path      TEXT NOT NULL,                  -- path to extracted image file
    image_hash      TEXT NOT NULL UNIQUE,           -- SHA256 hash for dedup
    image_width     INTEGER,
    image_height    INTEGER,

    -- Figure classification (from Claude Vision)
    figure_type     TEXT,                           -- km_curve, waterfall, forest, swimmer, spider,
                                                   -- bar_chart, line_chart, table, dose_response,
                                                   -- brain_penetrance, pk_curve, safety_profile
    is_clinical     BOOLEAN DEFAULT FALSE,          -- is this a clinical data figure?
    confidence      REAL DEFAULT 0.0,               -- Claude's confidence in classification (0-1)

    -- Drug / trial identification
    drug_names      TEXT[] DEFAULT '{}',            -- drugs shown in the figure
    trial_name      TEXT,                           -- e.g., "INAVO120", "CodeBreaK 200"
    nct_id          TEXT,                           -- NCT number if mentioned
    phase           TEXT,                           -- trial phase if visible

    -- Endpoint data (structured)
    endpoints       TEXT[] DEFAULT '{}',            -- e.g., ["OS", "PFS", "ORR"]
    key_data        JSONB DEFAULT '{}',             -- structured extraction:
                                                   -- {"hazard_ratio": 0.67, "median_os_arm1": 34.0,
                                                   --  "median_os_arm2": 27.0, "p_value": 0.02,
                                                   --  "orr": 0.58, "n_arm1": 161, "n_arm2": 164}

    -- Claude's narrative description
    description     TEXT,                           -- "Kaplan-Meier curve showing overall survival
                                                   --  in the INAVO120 trial comparing inavolisib +
                                                   --  palbociclib + fulvestrant vs placebo..."
    caption         TEXT,                           -- original figure caption if extractable

    -- Indication / target context
    indication      TEXT,                           -- primary indication shown
    targets         TEXT[] DEFAULT '{}',            -- targets relevant to this figure

    -- Search
    embedding       vector(512),                   -- Voyage embedding of description for semantic search
    search_text     TEXT,                           -- concatenated searchable text

    -- Metadata
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_figures_type ON document_figures (figure_type);
CREATE INDEX IF NOT EXISTS idx_figures_clinical ON document_figures (is_clinical);
CREATE INDEX IF NOT EXISTS idx_figures_ticker ON document_figures (source_ticker);
CREATE INDEX IF NOT EXISTS idx_figures_drugs ON document_figures USING GIN (drug_names);
CREATE INDEX IF NOT EXISTS idx_figures_endpoints ON document_figures USING GIN (endpoints);
CREATE INDEX IF NOT EXISTS idx_figures_targets ON document_figures USING GIN (targets);
CREATE INDEX IF NOT EXISTS idx_figures_trial ON document_figures (trial_name);
CREATE INDEX IF NOT EXISTS idx_figures_nct ON document_figures (nct_id);
"""


def setup_tables():
    """Create the document_figures table."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(SCHEMA_SQL)
    conn.commit()
    print("  ✓ document_figures table created")
    cur.close()
    conn.close()


# =============================================================================
# Image Extraction from PDFs
# =============================================================================

# Min/max dimensions for candidate clinical figures (in pixels)
MIN_WIDTH = 200
MIN_HEIGHT = 150
MAX_ASPECT_RATIO = 5.0  # Skip very narrow banners

# Supported figure types for classification
FIGURE_TYPES = [
    "km_curve",           # Kaplan-Meier survival curves
    "waterfall",          # Waterfall plots (tumor response)
    "forest",             # Forest plots (subgroup analysis, meta-analysis)
    "swimmer",            # Swimmer plots (individual patient timelines)
    "spider",             # Spider/spaghetti plots (individual tumor change over time)
    "bar_chart",          # Bar charts (ORR, response rates, etc.)
    "line_chart",         # Line charts (PK curves, dose-response, biomarker kinetics)
    "dose_response",      # IC50/dose-response curves
    "brain_penetrance",   # Brain/CSF concentration data
    "pk_curve",           # Pharmacokinetic curves
    "safety_profile",     # AE tables, safety bar charts
    "study_design",       # Trial design schematics
    "moa_diagram",        # Mechanism of action diagrams
    "pipeline_table",     # Pipeline/portfolio tables
    "other_clinical",     # Other clinical data figures
    "not_clinical",       # Logos, decorative, org charts, etc.
]


def extract_images_from_pdf(pdf_path: str, output_dir: str) -> list[dict]:
    """
    Extract all candidate images from a PDF using PyMuPDF.

    Returns a list of dicts with:
        - image_path: path to saved PNG
        - page_number: which page
        - width, height: dimensions
        - image_hash: SHA256 for dedup
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("ERROR: PyMuPDF not installed. Run: pip3 install PyMuPDF --break-system-packages")
        return []

    os.makedirs(output_dir, exist_ok=True)
    pdf_name = Path(pdf_path).stem
    candidates = []
    seen_hashes = set()

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"  ⚠ Could not open {pdf_path}: {e}")
        return []

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)

        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]

            try:
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue

                image_bytes = base_image["image"]
                width = base_image["width"]
                height = base_image["height"]

                # Filter by size
                if width < MIN_WIDTH or height < MIN_HEIGHT:
                    continue

                # Filter extreme aspect ratios (banners, thin lines)
                aspect = max(width, height) / max(min(width, height), 1)
                if aspect > MAX_ASPECT_RATIO:
                    continue

                # Dedup by hash
                img_hash = hashlib.sha256(image_bytes).hexdigest()
                if img_hash in seen_hashes:
                    continue
                seen_hashes.add(img_hash)

                # Save image
                ext = base_image.get("ext", "png")
                img_filename = f"{pdf_name}_p{page_num + 1}_img{img_idx}.{ext}"
                img_path = os.path.join(output_dir, img_filename)

                with open(img_path, "wb") as f:
                    f.write(image_bytes)

                candidates.append({
                    "image_path": img_path,
                    "page_number": page_num + 1,
                    "width": width,
                    "height": height,
                    "image_hash": img_hash,
                    "ext": ext,
                })

            except Exception as e:
                continue  # Skip problematic images silently

    doc.close()
    return candidates


# Also extract full-page renders for pages that might have embedded charts
# (some PDFs embed charts as vector graphics, not raster images)
def render_pages_as_images(pdf_path: str, output_dir: str, dpi: int = 200) -> list[dict]:
    """
    Render each PDF page as a high-res PNG. This catches vector-based charts
    that don't appear in get_images().

    Only renders pages that have minimal extracted images (likely vector charts).
    """
    try:
        import fitz
    except ImportError:
        return []

    os.makedirs(output_dir, exist_ok=True)
    pdf_name = Path(pdf_path).stem
    renders = []

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Only render pages with few/no extracted images (likely vector graphics)
        image_count = len(page.get_images(full=True))
        if image_count > 3:
            continue  # Page has raster images, skip render

        # Render page at high DPI
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)

        img_filename = f"{pdf_name}_p{page_num + 1}_render.png"
        img_path = os.path.join(output_dir, img_filename)
        pix.save(img_path)

        img_hash = hashlib.sha256(pix.tobytes()).hexdigest()

        renders.append({
            "image_path": img_path,
            "page_number": page_num + 1,
            "width": pix.width,
            "height": pix.height,
            "image_hash": img_hash,
            "ext": "png",
            "is_page_render": True,
        })

    doc.close()
    return renders


# =============================================================================
# Claude Vision Analysis
# =============================================================================

FIGURE_ANALYSIS_PROMPT = """You are an expert biotech/pharma analyst. Analyze this image from a clinical/scientific document and extract structured data.

First determine: is this a clinical data figure (KM curve, waterfall plot, forest plot, efficacy/safety data, PK curve, dose-response, etc.) or something else (logo, org chart, decorative image, mechanism diagram, etc.)?

If it IS a clinical data figure, extract ALL of the following:

1. figure_type: One of: km_curve, waterfall, forest, swimmer, spider, bar_chart, line_chart, dose_response, brain_penetrance, pk_curve, safety_profile, study_design, pipeline_table, other_clinical
2. drug_names: List of drug names visible (both generic and brand names)
3. trial_name: Trial name if shown (e.g., "INAVO120", "CodeBreaK 200", "DESTINY-Breast04")
4. nct_id: NCT number if shown
5. phase: Trial phase if visible
6. endpoints: List of endpoints shown (e.g., ["OS", "PFS", "ORR", "DOR"])
7. key_data: Structured data extraction — extract ALL numbers visible:
   - For KM curves: hazard_ratio, p_value, median values for each arm, N per arm, confidence intervals
   - For waterfall: best_overall_response, orr_percentage, dcr_percentage
   - For forest: subgroup HRs, interaction p-values
   - For bar charts: response rates, percentages
   - For PK: Cmax, AUC, half-life, trough levels
   Include units where visible.
8. description: 2-3 sentence description of what this figure shows and its clinical significance
9. indication: Primary indication/disease being studied
10. targets: Biological targets relevant to drugs in the figure
11. confidence: Your confidence this is correctly classified (0.0-1.0)

If it is NOT a clinical figure, return:
- figure_type: "not_clinical" or "moa_diagram" or "study_design" or "pipeline_table"
- A brief description
- confidence: your confidence

Return ONLY valid JSON, no other text."""


def analyze_figure_with_claude(image_path: str, source_context: str = "") -> dict:
    """
    Use Claude Vision to analyze an extracted figure.

    Args:
        image_path: path to the image file
        source_context: optional context (e.g., "from RVMD Q3 2024 Earnings Deck, page 12")

    Returns structured metadata dict.
    """
    import anthropic

    # Read and encode the image
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # Determine media type
    ext = Path(image_path).suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(ext, "image/png")

    prompt = FIGURE_ANALYSIS_PROMPT
    if source_context:
        prompt += f"\n\nContext: This image was extracted {source_context}."

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }],
        )

        text = response.content[0].text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        if text.endswith("```"):
            text = text[:-3].strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse error for {image_path}: {e}")
        return {"figure_type": "unknown", "description": "Could not parse analysis", "confidence": 0}
    except Exception as e:
        print(f"  ⚠ Claude Vision error for {image_path}: {e}")
        return {"figure_type": "error", "description": str(e), "confidence": 0}


# =============================================================================
# Store Figures in Database
# =============================================================================

def store_figure(
    image_path: str,
    image_hash: str,
    page_number: int,
    width: int,
    height: int,
    source_filename: str,
    source_ticker: str = None,
    source_company: str = None,
    source_doc_type: str = None,
    analysis: dict = None,
) -> Optional[int]:
    """
    Store an analyzed figure in the database.
    Returns the figure_id, or None if it already exists.
    """
    conn = get_conn()
    cur = conn.cursor()

    if analysis is None:
        analysis = {}

    figure_type = analysis.get("figure_type", "unknown")
    is_clinical = figure_type not in ("not_clinical", "moa_diagram", "unknown", "error")

    drug_names = analysis.get("drug_names", [])
    if isinstance(drug_names, str):
        drug_names = [drug_names]

    endpoints = analysis.get("endpoints", [])
    if isinstance(endpoints, str):
        endpoints = [endpoints]

    targets = analysis.get("targets", [])
    if isinstance(targets, str):
        targets = [targets]

    key_data = analysis.get("key_data", {})
    if isinstance(key_data, str):
        try:
            key_data = json.loads(key_data)
        except json.JSONDecodeError:
            key_data = {}

    # Build search text for full-text search
    search_parts = [
        analysis.get("description", ""),
        analysis.get("trial_name", ""),
        " ".join(drug_names),
        " ".join(endpoints),
        " ".join(targets),
        analysis.get("indication", ""),
        source_filename,
        source_ticker or "",
        source_company or "",
    ]
    search_text = " ".join(filter(None, search_parts))

    try:
        cur.execute("""
            INSERT INTO document_figures (
                source_filename, source_page, source_ticker, source_company, source_doc_type,
                image_path, image_hash, image_width, image_height,
                figure_type, is_clinical, confidence,
                drug_names, trial_name, nct_id, phase,
                endpoints, key_data,
                description, caption,
                indication, targets,
                search_text
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s
            )
            ON CONFLICT (image_hash) DO UPDATE SET
                figure_type = EXCLUDED.figure_type,
                is_clinical = EXCLUDED.is_clinical,
                confidence = EXCLUDED.confidence,
                drug_names = EXCLUDED.drug_names,
                trial_name = EXCLUDED.trial_name,
                nct_id = EXCLUDED.nct_id,
                endpoints = EXCLUDED.endpoints,
                key_data = EXCLUDED.key_data,
                description = EXCLUDED.description,
                targets = EXCLUDED.targets,
                search_text = EXCLUDED.search_text,
                updated_at = NOW()
            RETURNING figure_id
        """, (
            source_filename, page_number, source_ticker, source_company, source_doc_type,
            image_path, image_hash, width, height,
            figure_type, is_clinical, analysis.get("confidence", 0),
            drug_names, analysis.get("trial_name"), analysis.get("nct_id"), analysis.get("phase"),
            endpoints, json.dumps(key_data),
            analysis.get("description"), analysis.get("caption"),
            analysis.get("indication"), targets,
            search_text,
        ))

        figure_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return figure_id

    except Exception as e:
        conn.rollback()
        print(f"  ⚠ DB error storing figure: {e}")
        cur.close()
        conn.close()
        return None


# =============================================================================
# Full Pipeline: Extract → Analyze → Store
# =============================================================================

def process_pdf(
    pdf_path: str,
    output_dir: str = None,
    ticker: str = None,
    company: str = None,
    doc_type: str = None,
    analyze: bool = True,
    include_renders: bool = False,
) -> dict:
    """
    Full pipeline for one PDF: extract images → classify with Claude → store.

    Args:
        pdf_path: path to the PDF
        output_dir: where to save extracted images (default: ./figures/<pdf_name>/)
        ticker: company ticker for this document
        company: company name
        doc_type: document type (earnings, poster, 10-K, publication, deck)
        analyze: whether to run Claude Vision analysis (costs API credits)
        include_renders: also render full pages as images (catches vector charts)

    Returns summary dict with counts.
    """
    pdf_name = Path(pdf_path).stem
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(pdf_path), "figures", pdf_name)

    print(f"\n  Processing: {pdf_name}")

    # Step 1: Extract images
    candidates = extract_images_from_pdf(pdf_path, output_dir)
    print(f"  Extracted {len(candidates)} candidate images")

    if include_renders:
        renders = render_pages_as_images(pdf_path, output_dir)
        print(f"  Rendered {len(renders)} pages as images")
        candidates.extend(renders)

    results = {
        "pdf": pdf_name,
        "total_extracted": len(candidates),
        "clinical_figures": 0,
        "non_clinical": 0,
        "errors": 0,
    }

    source_filename = Path(pdf_path).name
    source_context = f"from {source_filename}"
    if ticker:
        source_context += f" ({ticker})"

    for img in candidates:
        # Step 2: Analyze with Claude Vision (if enabled)
        if analyze:
            analysis = analyze_figure_with_claude(
                img["image_path"],
                source_context=f"{source_context}, page {img['page_number']}"
            )
        else:
            analysis = {"figure_type": "unanalyzed", "confidence": 0}

        # Step 3: Store in database
        figure_id = store_figure(
            image_path=img["image_path"],
            image_hash=img["image_hash"],
            page_number=img["page_number"],
            width=img["width"],
            height=img["height"],
            source_filename=source_filename,
            source_ticker=ticker,
            source_company=company,
            source_doc_type=doc_type,
            analysis=analysis,
        )

        if figure_id:
            fig_type = analysis.get("figure_type", "unknown")
            if fig_type not in ("not_clinical", "moa_diagram", "unknown", "error"):
                results["clinical_figures"] += 1
                print(f"    ✓ p{img['page_number']}: {fig_type} — {', '.join(analysis.get('drug_names', ['?']))}")
            else:
                results["non_clinical"] += 1
        else:
            results["errors"] += 1

    return results


# =============================================================================
# Search Functions (used by query router)
# =============================================================================

def search_figures(
    query: str = None,
    drug_name: str = None,
    trial_name: str = None,
    endpoint: str = None,
    figure_type: str = None,
    indication: str = None,
    target: str = None,
    ticker: str = None,
    clinical_only: bool = True,
    limit: int = 10,
) -> list[dict]:
    """
    Search for figures by various criteria.
    Returns matching figures with metadata, sorted by relevance.

    The query router calls this to find figures to surface in the answer.
    """
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    conditions = []
    params = []

    if clinical_only:
        conditions.append("is_clinical = TRUE")

    if drug_name:
        conditions.append("%s = ANY(drug_names) OR search_text ILIKE %s")
        params.extend([drug_name, f"%{drug_name}%"])

    if trial_name:
        conditions.append("(trial_name ILIKE %s OR search_text ILIKE %s)")
        params.extend([f"%{trial_name}%", f"%{trial_name}%"])

    if endpoint:
        conditions.append("%s = ANY(endpoints)")
        params.append(endpoint)

    if figure_type:
        conditions.append("figure_type = %s")
        params.append(figure_type)

    if indication:
        conditions.append("(indication ILIKE %s OR search_text ILIKE %s)")
        params.extend([f"%{indication}%", f"%{indication}%"])

    if target:
        conditions.append("(%s = ANY(targets) OR search_text ILIKE %s)")
        params.extend([target, f"%{target}%"])

    if ticker:
        conditions.append("source_ticker = %s")
        params.append(ticker)

    if query:
        # Full-text search on the search_text column
        conditions.append("search_text ILIKE %s")
        params.append(f"%{query}%")

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    cur.execute(f"""
        SELECT figure_id, source_filename, source_page, source_ticker, source_company,
               image_path, figure_type, is_clinical, confidence,
               drug_names, trial_name, nct_id, phase,
               endpoints, key_data,
               description, indication, targets
        FROM document_figures
        WHERE {where_clause}
        ORDER BY confidence DESC, figure_id DESC
        LIMIT %s
    """, params + [limit])

    figures = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return figures


def get_figures_for_drug(drug_name: str, endpoint: str = None) -> list[dict]:
    """Shortcut to find all clinical figures for a specific drug."""
    return search_figures(drug_name=drug_name, endpoint=endpoint)


def get_figures_for_trial(trial_name: str) -> list[dict]:
    """Shortcut to find all clinical figures for a specific trial."""
    return search_figures(trial_name=trial_name)


def format_figures_for_claude(figures: list[dict]) -> str:
    """
    Format figure metadata as context for Claude synthesis.
    The actual images get served to the frontend separately — this gives Claude
    the data it needs to reference specific figures in its answer.
    """
    if not figures:
        return ""

    parts = ["=== CLINICAL FIGURES FROM DOCUMENT LIBRARY ==="]
    parts.append(f"Found {len(figures)} relevant figures\n")

    for i, fig in enumerate(figures, 1):
        parts.append(f"[Figure {i}] {fig.get('figure_type', '?').replace('_', ' ').title()}")
        parts.append(f"  Source: {fig.get('source_filename', '?')} (p{fig.get('source_page', '?')})")
        parts.append(f"  Company: {fig.get('source_company', '?')} ({fig.get('source_ticker', '?')})")

        drugs = fig.get("drug_names", [])
        if drugs:
            parts.append(f"  Drug(s): {', '.join(drugs)}")

        trial = fig.get("trial_name")
        if trial:
            nct = fig.get("nct_id", "")
            parts.append(f"  Trial: {trial} {nct}")

        endpoints = fig.get("endpoints", [])
        if endpoints:
            parts.append(f"  Endpoints: {', '.join(endpoints)}")

        key_data = fig.get("key_data", {})
        if key_data and isinstance(key_data, dict):
            data_parts = []
            for k, v in key_data.items():
                data_parts.append(f"{k.replace('_', ' ')}: {v}")
            if data_parts:
                parts.append(f"  Key data: {'; '.join(data_parts)}")

        desc = fig.get("description")
        if desc:
            parts.append(f"  Description: {desc}")

        parts.append(f"  [FIGURE_REF:{fig['figure_id']}]")  # Frontend uses this to render the image
        parts.append("")

    return "\n".join(parts)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SatyaBio Figure Extractor")
    parser.add_argument("--setup", action="store_true", help="Create database tables")
    parser.add_argument("--extract", type=str, help="Extract figures from a single PDF")
    parser.add_argument("--extract-all", type=str, help="Extract from all PDFs in a directory")
    parser.add_argument("--search", type=str, help="Search for figures")
    parser.add_argument("--drug", type=str, help="Find figures for a drug")
    parser.add_argument("--trial", type=str, help="Find figures for a trial")
    parser.add_argument("--no-analyze", action="store_true", help="Skip Claude Vision analysis (just extract)")
    parser.add_argument("--ticker", type=str, help="Company ticker for the document")
    parser.add_argument("--company", type=str, help="Company name for the document")
    parser.add_argument("--doc-type", type=str, help="Document type (earnings, poster, 10-K, etc.)")
    parser.add_argument("--render-pages", action="store_true", help="Also render full pages (catches vector charts)")
    args = parser.parse_args()

    if args.setup:
        print("Setting up figure extraction tables...")
        setup_tables()
        print("Done!")

    elif args.extract:
        result = process_pdf(
            args.extract,
            ticker=args.ticker,
            company=args.company,
            doc_type=args.doc_type,
            analyze=not args.no_analyze,
            include_renders=args.render_pages,
        )
        print(f"\n  Summary: {result['clinical_figures']} clinical figures, "
              f"{result['non_clinical']} non-clinical, {result['errors']} errors")

    elif args.extract_all:
        pdf_dir = args.extract_all
        pdfs = list(Path(pdf_dir).glob("**/*.pdf"))
        print(f"Found {len(pdfs)} PDFs in {pdf_dir}")

        total_clinical = 0
        for pdf_path in pdfs:
            result = process_pdf(
                str(pdf_path),
                ticker=args.ticker,
                company=args.company,
                doc_type=args.doc_type,
                analyze=not args.no_analyze,
                include_renders=args.render_pages,
            )
            total_clinical += result["clinical_figures"]

        print(f"\n  Total clinical figures extracted: {total_clinical}")

    elif args.search:
        figures = search_figures(query=args.search)
        if figures:
            print(f"\n  Found {len(figures)} figures:\n")
            print(format_figures_for_claude(figures))
        else:
            print(f"  No figures found for: {args.search}")

    elif args.drug:
        figures = get_figures_for_drug(args.drug)
        if figures:
            print(f"\n  Found {len(figures)} figures for {args.drug}:\n")
            print(format_figures_for_claude(figures))
        else:
            print(f"  No figures found for drug: {args.drug}")

    elif args.trial:
        figures = get_figures_for_trial(args.trial)
        if figures:
            print(f"\n  Found {len(figures)} figures for {args.trial}:\n")
            print(format_figures_for_claude(figures))
        else:
            print(f"  No figures found for trial: {args.trial}")

    else:
        parser.print_help()
