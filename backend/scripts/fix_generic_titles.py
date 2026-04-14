#!/usr/bin/env python3
"""
Fix generic document titles ("see publication", "download", etc.)
across all document_index.json files AND the database.

Derives better titles from the PDF filename in the source_url.
Run from repo root:  python backend/scripts/fix_generic_titles.py [--dry-run]
"""

import json
import os
import sys
import re
from pathlib import Path
from urllib.parse import urlparse

# Generic titles that should be replaced
GENERIC_TITLES = {
    "see publication", "see poster", "see abstract", "see presentation",
    "download", "download pdf", "view", "view pdf", "click here",
    "pdf", "open", "read more", "learn more", "full text",
    "see", "view document",
}

def title_from_filename(href: str) -> str:
    """Derive a human-readable title from a URL's filename."""
    filename = Path(urlparse(href).path).stem
    # Clean up: replace separators, remove trailing dates/versions
    title = filename.replace("-", " ").replace("_", " ")
    # Collapse multiple spaces
    title = re.sub(r"\s+", " ", title).strip()
    return title.title() if title else ""


def fix_document_index(index_path: str, dry_run: bool = False) -> int:
    """Fix generic titles in a single document_index.json file."""
    with open(index_path) as f:
        index = json.load(f)

    fixed = 0
    for filename, meta in index.items():
        title = meta.get("title", "")
        if title.lower().strip() in GENERIC_TITLES:
            source_url = meta.get("source_url", "")
            # Try deriving from source_url first, then from the filename key
            new_title = title_from_filename(source_url) if source_url else ""
            if not new_title or new_title.lower() in GENERIC_TITLES:
                new_title = title_from_filename(f"/{filename}")
            if new_title and new_title.lower() not in GENERIC_TITLES:
                if dry_run:
                    print(f"  Would fix: '{title}' → '{new_title}'")
                else:
                    meta["title"] = new_title
                fixed += 1

    if fixed and not dry_run:
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    return fixed


def fix_database(dry_run: bool = False) -> int:
    """Fix generic titles in the documents database table."""
    db_url = os.environ.get("NEON_DATABASE_URL", "")
    if not db_url:
        print("  NEON_DATABASE_URL not set — skipping DB update")
        return 0

    try:
        import psycopg2
    except ImportError:
        print("  psycopg2 not installed — skipping DB update")
        return 0

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    # Find all documents with generic titles
    placeholders = ",".join(["%s"] * len(GENERIC_TITLES))
    cur.execute(f"""
        SELECT id, title, file_path, ticker
        FROM documents
        WHERE LOWER(TRIM(title)) IN ({placeholders})
    """, list(GENERIC_TITLES))
    rows = cur.fetchall()

    fixed = 0
    for doc_id, title, file_path, ticker in rows:
        new_title = ""
        if file_path:
            new_title = title_from_filename(f"/{os.path.basename(file_path)}")
        if not new_title or new_title.lower() in GENERIC_TITLES:
            continue

        if dry_run:
            print(f"  DB [{ticker}] doc {doc_id}: '{title}' → '{new_title}'")
        else:
            cur.execute("UPDATE documents SET title = %s WHERE id = %s", (new_title, doc_id))
        fixed += 1

    cur.close()
    conn.close()
    return fixed


def main():
    dry_run = "--dry-run" in sys.argv

    # Find all document_index.json files
    base_dirs = [
        "backend/services/data/companies",
        "data/companies",
    ]

    total_fixed = 0
    for base in base_dirs:
        if not os.path.isdir(base):
            continue
        for ticker_dir in sorted(os.listdir(base)):
            index_path = os.path.join(base, ticker_dir, "metadata", "document_index.json")
            if os.path.isfile(index_path):
                fixed = fix_document_index(index_path, dry_run)
                if fixed:
                    print(f"  {ticker_dir}: fixed {fixed} titles in {index_path}")
                    total_fixed += fixed

    print(f"\nMetadata files: {total_fixed} titles {'would be ' if dry_run else ''}fixed")

    # Fix database
    db_fixed = fix_database(dry_run)
    print(f"Database: {db_fixed} titles {'would be ' if dry_run else ''}fixed")

    if dry_run:
        print("\n(Dry run — no changes made. Remove --dry-run to apply.)")


if __name__ == "__main__":
    main()
