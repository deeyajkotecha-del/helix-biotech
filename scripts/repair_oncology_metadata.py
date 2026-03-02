#!/usr/bin/env python3
"""
Three-pass metadata repair for oncology IR documents.

Pass 1: Fix bad/generic titles using on-disk filenames
Pass 2: Fix null dates using filenames + conference→month mapping
Pass 3: Re-run doc_type classification on repaired titles

Adds tracking fields:
  - title_source:   "scraper" | "filename"
  - date_source:    "scraper" | "filename" | "conference"
  - date_precision: "day" | "month" | "year" | null

Usage:
    python scripts/repair_oncology_metadata.py              # run all 3 passes
    python scripts/repair_oncology_metadata.py --dry-run    # preview changes only
"""

import json
import re
import sys
from pathlib import Path
from copy import deepcopy

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

METADATA_FILE = PROJECT_ROOT / "data" / "downloads" / "oncology_metadata.json"

# ──────────────────────────────────────────────────────────────────────
# Conference → typical month mapping
# ──────────────────────────────────────────────────────────────────────

CONFERENCE_MONTHS = {
    "JPM": 1,       # JP Morgan Healthcare Conference — January
    "ASTCT": 2,     # American Society for Transplantation — February
    "EBMT": 3,      # European Blood and Marrow Transplant — March
    "SGO": 3,       # Society of Gynecologic Oncology — March
    "SSO": 3,       # Society of Surgical Oncology — March
    "HOPA": 3,      # Hematology/Oncology Pharmacy Association — March
    "NCCN": 3,      # National Comprehensive Cancer Network — March
    "ELCC": 3,      # European Lung Cancer Congress — March/April
    "AACR": 4,      # American Association for Cancer Research — April
    "AUA": 5,       # American Urological Association — May
    "ASCO": 6,      # American Society of Clinical Oncology — June
    "EHA": 6,       # European Hematology Association — June
    "EADO": 6,      # European Association of Dermato-Oncology — June
    "WCLC": 9,      # World Conference on Lung Cancer — September
    "ESMO": 9,      # European Society for Medical Oncology — September
    "SMR": 10,      # Society for Melanoma Research — October
    "IGCS": 10,     # International Gynecologic Cancer Society — October
    "NACLC": 10,    # North American Conference on Lung Cancer — October
    "NASLC": 10,    # (variant spelling of NACLC)
    "SUO": 11,      # Society of Urologic Oncology — November
    "SITC": 11,     # Society for Immunotherapy of Cancer — November
    "ISPOR": 11,    # International Society for Pharmacoeconomics — November
    "SNO": 11,      # Society for Neuro-Oncology — November
    "ASH": 12,      # American Society of Hematology — December
    "SABCS": 12,    # San Antonio Breast Cancer Symposium — December
    "MRA": 10,      # Melanoma Research Alliance — fall
}

# ──────────────────────────────────────────────────────────────────────
# Patterns
# ──────────────────────────────────────────────────────────────────────

# Generic/bad titles that should be replaced with filename-derived titles
_BAD_TITLE_RE = re.compile(
    r"^(download|view\s*(poster|presentation|publication|abstract)?|presentation)$",
    re.IGNORECASE,
)

# Suffixes to strip from filenames before using as titles
_STRIP_SUFFIXES = re.compile(
    r"[-_]\d{3,4}[-_]publication"   # IOVA: -3224-publication
    r"|[-_]FINAL[-_]?\d*"           # _FINAL, _FINAL-1
    r"|[-_]v\d+"                    # _v2, _v3, -v14
    r"|[-_]vFINAL"                  # _vFINAL
    r"|[-_]vf"                      # _vf
    r"|[-_]compressed"              # _compressed
    r"|[-_]SIZED[-_]?\d*"           # _SIZED, _SIZED-1
    r"|[-_]PRINT"                   # _PRINT
    r"|[-_]final"                   # _final
    r"|[-_]online"                  # _online
    r"|[-_]for[-_]website"          # _for-website
    r"|[-_]for[-_]esub"             # _for-esub
    r"|[-_]for[-_]review"           # _for-review
    r"|[-_]NSDE"                    # _NSDE
    r"|[-_]SWDE"                    # _SWDE
    r"|[-_]KRDE"                    # _KRDE
    r"|[-_]DE"                      # _DE
    r"|[-_]QA[-_]PrismPictures"     # _QA-PrismPictures
    r"|[-_]Print[-_]POS"            # _Print-POS
    r"|[-_]APP[-_]TO[-_]SUBMIT\d*"  # _APP-TO-SUBMIT52
    r"|[-_]D5[-_]APP"               # _D5-APP
    r"|[-_]?\d*$"                   # trailing numbers like -002, -1
    ,
    re.IGNORECASE,
)

# Date patterns in filenames
_YYYYMMDD_RE = re.compile(r"(\d{4})(\d{2})(\d{2})")  # 20191120
_DDMONYYYY_RE = re.compile(
    r"(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{4})",
    re.IGNORECASE,
)
_YYYY_MM_DD_RE = re.compile(r"(\d{4})[-_](\d{2})[-_](\d{2})")
_MON_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Conference + year: ASCO2025, ASCO_2025, ASCO-2025, ESMO 2025
# Also handles suffixed variants: ESMO-IO, ESMO-Gyn, ISPOR-EU, AACR-NCI-EORTC
_CONF_YEAR_RE = re.compile(
    r"(" + "|".join(CONFERENCE_MONTHS.keys()) + r")(?:[-_](?:IO|EU|Gyn|NCI[-_]EORTC|RPCI))?[-_\s]?(\d{4})",
    re.IGNORECASE,
)

# Bare year in filename: _2024_, -2024-, _2024., (2024)
_BARE_YEAR_RE = re.compile(r"(?:^|[-_\s(])(\d{4})(?:[-_\s).]|$)")


# ──────────────────────────────────────────────────────────────────────
# Doc type classification (same rules as scraper, extended)
# ──────────────────────────────────────────────────────────────────────

_DOC_TYPE_RULES = [
    ("sec_filing", re.compile(
        r"10-[KQ]|8-K|sec\.gov|edgar", re.I)),
    ("poster", re.compile(
        r"poster|ASCO|ESMO|AACR|SABCS|SITC|WCLC|abstract|ePOS|preclin", re.I)),
    ("investor_presentation", re.compile(
        r"investor|corporate.presentation|corporate.deck|earnings|JPM|conference.call", re.I)),
    ("press_release", re.compile(
        r"press.release|announces?|FDA.approv|data.announce", re.I)),
    ("publication", re.compile(
        r"publication|journal|efficacy.and.safety|Phase.\d|TiP|Trial.in.Progress|cohort", re.I)),
]

def classify_doc_type(url: str, title: str) -> str:
    text = f"{url} {title}"
    for doc_type, pattern in _DOC_TYPE_RULES:
        if pattern.search(text):
            return doc_type
    return "other"


# ──────────────────────────────────────────────────────────────────────
# Pass 1: Fix bad titles
# ──────────────────────────────────────────────────────────────────────

def _clean_filename_to_title(filename: str) -> str:
    """Convert on-disk filename to a human-readable title."""
    raw_stem = Path(filename).stem
    stem = raw_stem

    # Strip known junk suffixes (iterative since they stack)
    for _ in range(5):
        cleaned = _STRIP_SUFFIXES.sub("", stem)
        if cleaned == stem:
            break
        stem = cleaned

    # Replace separators with spaces
    title = stem.replace("_", " ").replace("-", " ")

    # Collapse multiple spaces
    title = re.sub(r"\s+", " ", title).strip()

    # If stripping destroyed the title, fall back to raw stem
    if not title or len(title) <= 3:
        title = raw_stem.replace("_", " ").replace("-", " ")
        title = re.sub(r"\s+", " ", title).strip()

    return title


# UUID/hash filenames: 8-4-4-4-12 hex or 30+ hex chars
_HASH_FILENAME_RE = re.compile(r"^[0-9a-f]{8}[-][0-9a-f]{4}[-]|^[0-9a-f]{30,}", re.I)
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def _is_hash_filename(filename: str) -> bool:
    """Check if a filename is a UUID or hex hash (no useful title info)."""
    stem = Path(filename).stem
    return bool(_HASH_FILENAME_RE.match(stem))


def is_bad_title(title: str) -> bool:
    """Check if a title is generic/useless."""
    if not title or len(title.strip()) <= 3:
        return True
    return bool(_BAD_TITLE_RE.match(title.strip()))


def pass1_fix_titles(metadata: dict) -> dict:
    """Replace bad/generic titles with cleaned filenames. Returns counts."""
    fixed = 0
    already_good = 0

    for url, entry in metadata.items():
        if url == "_errors":
            continue
        if entry.get("duplicate_of"):
            continue

        title = entry.get("title", "")
        file_path = entry.get("file_path", "")
        filename = Path(file_path).name if file_path else ""

        if is_bad_title(title):
            if filename and not _is_hash_filename(filename):
                new_title = _clean_filename_to_title(filename)
                if new_title and len(new_title) > 3:
                    entry["title"] = new_title
                    entry["title_source"] = "filename"
                    fixed += 1
                else:
                    entry["title_source"] = "scraper"
            else:
                entry["title_source"] = "scraper"
        else:
            entry["title_source"] = "scraper"
            already_good += 1

    return {"fixed": fixed, "already_good": already_good}


# ──────────────────────────────────────────────────────────────────────
# Pass 2: Fix null dates
# ──────────────────────────────────────────────────────────────────────

def _extract_date_from_filename(filename: str, title: str) -> tuple[str | None, str]:
    """Extract date from filename or title.

    Returns (iso_date, precision) where precision is "day", "month", or "year".
    """
    # Combine filename and title for searching
    text = f"{Path(filename).stem} {title}"

    # 1. Exact date: YYYY-MM-DD or YYYY_MM_DD
    m = _YYYY_MM_DD_RE.search(text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 2000 <= y <= 2099 and 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                from datetime import date
                return date(y, mo, d).isoformat(), "day"
            except ValueError:
                pass

    # 2. Exact date: DDMONYYYY (04JUN2018, 14APR2018)
    m = _DDMONYYYY_RE.search(text)
    if m:
        d, mon, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        mo = _MON_NAMES.get(mon)
        if mo and 2000 <= y <= 2099 and 1 <= d <= 31:
            try:
                from datetime import date
                return date(y, mo, d).isoformat(), "day"
            except ValueError:
                pass

    # 3. Exact date: YYYYMMDD (20191120)
    for m in _YYYYMMDD_RE.finditer(text):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 2015 <= y <= 2099 and 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                from datetime import date
                return date(y, mo, d).isoformat(), "day"
            except ValueError:
                pass

    # 4. Conference + year → month-level precision
    m = _CONF_YEAR_RE.search(text)
    if m:
        conf = m.group(1).upper()
        year = int(m.group(2))
        if 2015 <= year <= 2099 and conf in CONFERENCE_MONTHS:
            month = CONFERENCE_MONTHS[conf]
            return f"{year:04d}-{month:02d}-01", "month"

    # 5. Bare year fallback
    # Strip UUIDs first — they contain 4-digit hex that looks like years (e.g. 2035)
    text_no_uuid = _UUID_RE.sub("", text)
    years_found = []
    for m in _BARE_YEAR_RE.finditer(text_no_uuid):
        y = int(m.group(1))
        if 2015 <= y <= 2099:
            years_found.append(y)
    if years_found:
        # Use the most recent plausible year
        year = max(years_found)
        return f"{year:04d}-01-01", "year"

    return None, ""


def pass2_fix_dates(metadata: dict) -> dict:
    """Fill in null dates from filenames and conference mapping. Returns counts."""
    fixed_day = 0
    fixed_month = 0
    fixed_year = 0
    still_null = 0

    for url, entry in metadata.items():
        if url == "_errors":
            continue
        if entry.get("duplicate_of"):
            continue

        existing_date = entry.get("date")

        if existing_date:
            # Already has a date — mark source and precision
            entry["date_source"] = "scraper"
            entry["date_precision"] = "day"
            continue

        # Try to extract from filename + title
        file_path = entry.get("file_path", "")
        filename = Path(file_path).name if file_path else ""
        title = entry.get("title", "")

        new_date, precision = _extract_date_from_filename(filename, title)

        if new_date:
            entry["date"] = new_date
            entry["date_source"] = "conference" if precision == "month" else "filename"
            entry["date_precision"] = precision
            if precision == "day":
                fixed_day += 1
            elif precision == "month":
                fixed_month += 1
            else:
                fixed_year += 1
        else:
            entry["date_source"] = None
            entry["date_precision"] = None
            still_null += 1

    return {
        "fixed_day": fixed_day,
        "fixed_month": fixed_month,
        "fixed_year": fixed_year,
        "still_null": still_null,
    }


# ──────────────────────────────────────────────────────────────────────
# Pass 3: Re-classify doc_type
# ──────────────────────────────────────────────────────────────────────

def pass3_reclassify(metadata: dict) -> dict:
    """Re-run doc_type classification using repaired titles. Returns counts."""
    changed = 0
    by_type = {}

    for url, entry in metadata.items():
        if url == "_errors":
            continue
        if entry.get("duplicate_of"):
            continue

        old_type = entry.get("doc_type", "other")
        new_type = classify_doc_type(url, entry.get("title", ""))
        entry["doc_type"] = new_type

        by_type[new_type] = by_type.get(new_type, 0) + 1
        if old_type != new_type:
            changed += 1

    return {"changed": changed, "by_type": by_type}


# ──────────────────────────────────────────────────────────────────────
# Audit
# ──────────────────────────────────────────────────────────────────────

def audit(metadata: dict, label: str = ""):
    """Print audit numbers for the metadata."""
    total = 0
    bad_titles = 0
    null_dates = 0
    hash_filenames = 0
    other_doctype = 0
    by_ticker = {}

    for url, entry in metadata.items():
        if url == "_errors":
            continue
        if entry.get("duplicate_of"):
            continue
        total += 1

        ticker = entry.get("ticker", "?")
        if ticker not in by_ticker:
            by_ticker[ticker] = {"bad_title": 0, "null_date": 0, "hash_file": 0, "other_type": 0, "total": 0}
        by_ticker[ticker]["total"] += 1

        if is_bad_title(entry.get("title", "")):
            bad_titles += 1
            by_ticker[ticker]["bad_title"] += 1

        if entry.get("date") is None:
            null_dates += 1
            by_ticker[ticker]["null_date"] += 1

        fname = Path(entry.get("file_path", "")).name
        if re.match(r"^[0-9a-f]{8}[-]", fname) or re.match(r"^[0-9a-f]{30,}", fname):
            hash_filenames += 1
            by_ticker[ticker]["hash_file"] += 1

        if entry.get("doc_type") == "other":
            other_doctype += 1
            by_ticker[ticker]["other_type"] += 1

    header = f"=== AUDIT{': ' + label if label else ''} ==="
    print(f"\n{header}")
    print(f"{'Metric':<25} {'Count':>6} {'%':>6}")
    print("-" * 40)
    print(f"{'Total documents':<25} {total:>6}")
    print(f"{'Bad/generic titles':<25} {bad_titles:>6} {bad_titles*100//max(total,1):>5}%")
    print(f"{'Null dates':<25} {null_dates:>6} {null_dates*100//max(total,1):>5}%")
    print(f"{'Hash filenames':<25} {hash_filenames:>6} {hash_filenames*100//max(total,1):>5}%")
    print(f"{'doc_type = other':<25} {other_doctype:>6} {other_doctype*100//max(total,1):>5}%")

    print(f"\n{'Ticker':<7} {'Total':>5} {'BadTitle':>9} {'NullDate':>9} {'HashFile':>9} {'Other':>6}")
    print("-" * 50)
    for ticker in sorted(by_ticker.keys()):
        d = by_ticker[ticker]
        print(f"{ticker:<7} {d['total']:>5} {d['bad_title']:>9} {d['null_date']:>9} {d['hash_file']:>9} {d['other_type']:>6}")

    # Date precision breakdown
    day_count = sum(1 for u, e in metadata.items() if u != "_errors" and not e.get("duplicate_of") and e.get("date_precision") == "day")
    month_count = sum(1 for u, e in metadata.items() if u != "_errors" and not e.get("duplicate_of") and e.get("date_precision") == "month")
    year_count = sum(1 for u, e in metadata.items() if u != "_errors" and not e.get("duplicate_of") and e.get("date_precision") == "year")
    no_date = sum(1 for u, e in metadata.items() if u != "_errors" and not e.get("duplicate_of") and e.get("date") is None)
    if any(e.get("date_precision") for u, e in metadata.items() if u != "_errors"):
        print(f"\nDate precision breakdown:")
        print(f"  day:   {day_count:>5}")
        print(f"  month: {month_count:>5}")
        print(f"  year:  {year_count:>5}")
        print(f"  null:  {no_date:>5}")

    # Doc type breakdown
    dt_counts = {}
    for u, e in metadata.items():
        if u == "_errors" or e.get("duplicate_of"):
            continue
        dt = e.get("doc_type", "other")
        dt_counts[dt] = dt_counts.get(dt, 0) + 1
    print(f"\nDoc type breakdown:")
    for dt in sorted(dt_counts.keys(), key=lambda k: -dt_counts[k]):
        print(f"  {dt:<25} {dt_counts[dt]:>5}")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Three-pass metadata repair")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving")
    args = parser.parse_args()

    if not METADATA_FILE.exists():
        print(f"Error: {METADATA_FILE} not found")
        sys.exit(1)

    raw = json.loads(METADATA_FILE.read_text())
    metadata = deepcopy(raw)

    print("Loading metadata...")
    doc_count = sum(1 for k in metadata if k != "_errors" and not metadata[k].get("duplicate_of"))
    print(f"  {doc_count} documents loaded\n")

    # Pre-repair audit
    audit(metadata, "BEFORE repair")

    # Pass 1
    print("\n" + "=" * 60)
    print("PASS 1: Fix bad titles from on-disk filenames")
    print("=" * 60)
    p1 = pass1_fix_titles(metadata)
    print(f"  Fixed: {p1['fixed']} titles")
    print(f"  Already good: {p1['already_good']} titles")

    # Pass 2
    print("\n" + "=" * 60)
    print("PASS 2: Fix null dates from filenames + conference mapping")
    print("=" * 60)
    p2 = pass2_fix_dates(metadata)
    print(f"  Fixed (day precision):   {p2['fixed_day']}")
    print(f"  Fixed (month precision): {p2['fixed_month']}")
    print(f"  Fixed (year precision):  {p2['fixed_year']}")
    print(f"  Still null:              {p2['still_null']}")

    # Pass 3
    print("\n" + "=" * 60)
    print("PASS 3: Re-classify doc_type on repaired titles")
    print("=" * 60)
    p3 = pass3_reclassify(metadata)
    print(f"  Reclassified: {p3['changed']} entries")
    for dt, count in sorted(p3["by_type"].items(), key=lambda x: -x[1]):
        print(f"    {dt:<25} {count:>5}")

    # Post-repair audit
    audit(metadata, "AFTER repair")

    if args.dry_run:
        print("\n[DRY RUN] No changes saved.")
    else:
        # Back up original
        backup = METADATA_FILE.with_suffix(".json.bak")
        backup.write_text(json.dumps(raw, indent=2))
        print(f"\n  Backup saved: {backup}")

        # Save repaired
        METADATA_FILE.write_text(json.dumps(metadata, indent=2))
        print(f"  Repaired metadata saved: {METADATA_FILE}")


if __name__ == "__main__":
    main()
