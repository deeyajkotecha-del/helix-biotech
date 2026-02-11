#!/usr/bin/env python3
"""
Merge a new asset extraction into an existing asset JSON file.

Merge rules:
  - existing null + new non-null → use new (fill gap)
  - existing non-null + new non-null → keep existing UNLESS --force
  - existing non-null + new null → keep existing (never delete)
  - Arrays: smart matching by trial_name, event, id, etc.

Usage:
    python scripts/merge_asset.py \\
      --existing data/companies/ARGX/efgartigimod.json \\
      --new data/companies/ARGX/_drafts/efgartigimod_asco.json

    python scripts/merge_asset.py --existing x.json --new y.json --force
    python scripts/merge_asset.py --existing x.json --new y.json --diff
"""

import argparse
import json
import logging
import os
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("merge_asset")


# ---------------------------------------------------------------------------
# Merge statistics
# ---------------------------------------------------------------------------

class MergeStats:
    """Track merge operations for summary output."""

    def __init__(self):
        self.filled = []     # (path, old_value, new_value)
        self.skipped = []    # (path, existing_value, new_value)
        self.kept = []       # (path,) — existing kept, new was null
        self.appended = []   # (path, description)
        self.forced = []     # (path, old_value, new_value)

    @property
    def total_changes(self) -> int:
        return len(self.filled) + len(self.appended) + len(self.forced)


# ---------------------------------------------------------------------------
# Array matching helpers
# ---------------------------------------------------------------------------

def _match_key_for_array(items: list) -> str | None:
    """Determine the best key to match array items by.

    Returns the key name to match on, or None if no good key found.
    """
    if not items or not isinstance(items[0], dict):
        return None

    # Priority order of match keys
    match_keys = [
        "trial_name", "nct_id",   # clinical trials
        "event",                   # catalysts
        "id",                      # sources
        "drug", "claim",           # competitors, differentiation_claims
        "designation",             # regulatory.designations
        "name",                    # generic fallback
    ]
    first = items[0]
    for key in match_keys:
        if key in first and first[key] is not None:
            return key
    return None


def _merge_arrays(existing: list, new: list, force: bool, path: str, stats: MergeStats) -> list:
    """Merge two arrays intelligently.

    - Arrays of strings: union (append new items not in existing)
    - Arrays of dicts: match by key, deep-merge matched, append unmatched
    """
    if not new:
        return existing

    if not existing:
        if new:
            stats.filled.append((path, "[]", f"[{len(new)} items]"))
        return deepcopy(new)

    # Both non-empty

    # Arrays of strings → union
    if all(isinstance(x, str) for x in existing) and all(isinstance(x, str) for x in new):
        existing_set = set(existing)
        added = [item for item in new if item not in existing_set]
        if added:
            stats.appended.append((path, f"+{len(added)} string(s)"))
        return existing + added

    # Arrays of dicts → match by key
    match_key = _match_key_for_array(new)
    if match_key:
        # Build index of existing items by match key
        existing_index = {}
        for i, item in enumerate(existing):
            if isinstance(item, dict):
                key_val = item.get(match_key)
                if key_val is not None:
                    existing_index[key_val] = i

        result = deepcopy(existing)
        for new_item in new:
            if not isinstance(new_item, dict):
                continue
            key_val = new_item.get(match_key)
            if key_val is not None and key_val in existing_index:
                # Matched → deep merge
                idx = existing_index[key_val]
                result[idx] = _deep_merge(
                    result[idx], new_item, force,
                    f"{path}[{match_key}={key_val}]", stats
                )
            else:
                # New item → append
                result.append(deepcopy(new_item))
                desc = f"+1 ({match_key}={key_val})" if key_val else "+1 new item"
                stats.appended.append((path, desc))

        return result

    # No match key → keep existing unless force
    if force:
        stats.forced.append((path, f"[{len(existing)} items]", f"[{len(new)} items]"))
        return deepcopy(new)
    else:
        stats.skipped.append((path, f"[{len(existing)} items]", f"[{len(new)} items]"))
        return existing


# ---------------------------------------------------------------------------
# Deep merge
# ---------------------------------------------------------------------------

def _is_null_or_empty(value) -> bool:
    """Check if a value is null, empty string, empty dict, or empty list."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


def _truncate(value, max_len: int = 60) -> str:
    """Truncate a value for display."""
    s = str(value)
    if len(s) > max_len:
        return s[:max_len - 3] + "..."
    return s


def _deep_merge(existing, new, force: bool, path: str, stats: MergeStats):
    """Recursively merge new into existing."""
    # Both dicts → recurse
    if isinstance(existing, dict) and isinstance(new, dict):
        result = deepcopy(existing)
        for key in new:
            child_path = f"{path}.{key}" if path else key
            if key in result:
                result[key] = _deep_merge(result[key], new[key], force, child_path, stats)
            elif not _is_null_or_empty(new[key]):
                result[key] = deepcopy(new[key])
                stats.filled.append((child_path, "null", _truncate(new[key])))
        return result

    # Both lists → smart merge
    if isinstance(existing, list) and isinstance(new, list):
        return _merge_arrays(existing, new, force, path, stats)

    # Scalar merge
    if _is_null_or_empty(existing) and not _is_null_or_empty(new):
        # Fill gap
        stats.filled.append((path, _truncate(existing), _truncate(new)))
        return deepcopy(new)

    if not _is_null_or_empty(existing) and not _is_null_or_empty(new):
        if existing == new:
            # Same value, no change
            return existing
        if force:
            stats.forced.append((path, _truncate(existing), _truncate(new)))
            return deepcopy(new)
        else:
            stats.skipped.append((path, _truncate(existing), _truncate(new)))
            return existing

    # existing non-null, new null → keep existing
    if not _is_null_or_empty(existing):
        stats.kept.append((path,))
        return existing

    return existing


def deep_merge(existing: dict, new: dict, force: bool = False) -> tuple[dict, MergeStats]:
    """Merge new data into existing. Returns (merged_dict, stats)."""
    stats = MergeStats()
    merged = _deep_merge(existing, new, force, "", stats)
    return merged, stats


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_diff(stats: MergeStats, filename: str) -> None:
    """Print a human-readable merge diff."""
    print(f"\nMERGE PREVIEW: {filename}")
    print(f"{'─' * 50}")

    if stats.filled:
        print("\nFILL (null → value):")
        for path, old, new in stats.filled:
            print(f"  {path}: {old} → {new}")

    if stats.forced:
        print("\nFORCE (overwritten):")
        for path, old, new in stats.forced:
            print(f"  {path}: {old} → {new}")

    if stats.skipped:
        print("\nSKIP (both non-null, use --force):")
        for path, existing, new in stats.skipped:
            print(f"  {path}: {existing} vs {new}")

    if stats.appended:
        print("\nAPPEND (new array items):")
        for path, desc in stats.appended:
            print(f"  {path}: {desc}")

    total = stats.total_changes
    skipped = len(stats.skipped)
    print(f"\nSummary: {total} field(s) would update, {skipped} skipped, {len(stats.appended)} appended")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Merge a new asset extraction into an existing asset JSON file.",
        epilog="""
Examples:
  %(prog)s --existing data/companies/ARGX/efgartigimod.json \\
           --new data/companies/ARGX/_drafts/efgartigimod_asco.json

  %(prog)s --existing x.json --new y.json --force
  %(prog)s --existing x.json --new y.json --diff
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--existing", required=True, help="Path to existing asset JSON")
    parser.add_argument("--new", required=True, help="Path to new asset JSON to merge in")
    parser.add_argument("--force", action="store_true", help="Overwrite existing non-null fields")
    parser.add_argument("--diff", action="store_true", help="Show what would change without writing")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    existing_path = Path(args.existing)
    new_path = Path(args.new)

    if not existing_path.exists():
        logger.error("Existing file not found: %s", existing_path)
        sys.exit(1)
    if not new_path.exists():
        logger.error("New file not found: %s", new_path)
        sys.exit(1)

    # Load both files
    try:
        with open(existing_path) as f:
            existing_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in existing file: %s", e)
        sys.exit(1)

    try:
        with open(new_path) as f:
            new_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in new file: %s", e)
        sys.exit(1)

    # Merge
    merged, stats = deep_merge(existing_data, new_data, force=args.force)

    # Diff mode — print and exit
    if args.diff:
        print_diff(stats, existing_path.name)
        sys.exit(0)

    # Print summary
    print_diff(stats, existing_path.name)

    if stats.total_changes == 0 and not stats.skipped:
        logger.info("No changes to make")
        sys.exit(0)

    # Create timestamped backup
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = existing_path.with_name(f"{existing_path.name}.bak.{ts}")
    # Copy (not rename) so the original stays in place until we write
    with open(existing_path) as f:
        backup_data = f.read()
    with open(backup_path, "w") as f:
        f.write(backup_data)
    logger.info("Backed up %s → %s", existing_path.name, backup_path.name)

    # Write merged file atomically
    tmp_path = existing_path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, existing_path)

    logger.info(
        "Merged: %d updated, %d skipped, %d appended",
        len(stats.filled) + len(stats.forced),
        len(stats.skipped),
        len(stats.appended),
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
