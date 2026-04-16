#!/usr/bin/env python3
"""entity-rename.py — Global exact-match entity rename across truth files.

Renames an entity (character name, place name, etc.) across all book files
with strict exact-match semantics. "林远" -> "林渊" but "林远征" stays unchanged.

Supports scope filtering via TruthAuthority classification:
  - direction: author_intent.md, current_focus.md, volume_outline.md
  - foundation: story_bible.md, book_rules.md
  - rules: system rules (not user-modifiable, skipped)
  - runtime-truth: current_state, pending_hooks, chapter_summaries (JSON + MD)
  - memory: future MemoryDB (reserved, skipped)
  - all: all of the above (default)

Usage:
  entity-rename.py <book-dir> --old "旧名" --new "新名" [--scope all|direction|foundation|rules|runtime-truth|memory]

Output: JSON summary of replacements to stdout.
"""

import argparse
import json
import os
import sys


# ---------------------------------------------------------------------------
# Scope definitions — maps scope name to relative file patterns
# ---------------------------------------------------------------------------

SCOPE_DIRECTION_FILES = [
    "story/author_intent.md",
    "story/current_focus.md",
    "story/volume_outline.md",
]

SCOPE_FOUNDATION_FILES = [
    "story/story_bible.md",
    "story/book_rules.md",
]

SCOPE_RUNTIME_TRUTH_FILES = [
    # JSON truth files
    "story/state/current_state.json",
    "story/state/pending_hooks.json",
    "story/state/chapter_summaries.json",
    "story/state/manifest.json",
    # Markdown projections
    "story/current_state.md",
    "story/pending_hooks.md",
    "story/chapter_summaries.md",
]

SCOPE_MAP = {
    "direction": SCOPE_DIRECTION_FILES,
    "foundation": SCOPE_FOUNDATION_FILES,
    "rules": [],       # system rules, not user-modifiable
    "runtime-truth": SCOPE_RUNTIME_TRUTH_FILES,
    "memory": [],      # reserved for future MemoryDB
}

ALL_SCOPES = ["direction", "foundation", "rules", "runtime-truth", "memory"]


# ---------------------------------------------------------------------------
# Exact-match replacement logic
# ---------------------------------------------------------------------------

def exact_replace_in_string(text: str, old: str, new: str) -> tuple:
    """Replace all exact occurrences of old with new in text.

    Uses str.replace() which is literal (no regex). Returns (new_text, count).
    This is safe for CJK because str.replace operates on exact character sequences.
    """
    count = text.count(old)
    if count == 0:
        return text, 0
    result = text.replace(old, new)
    return result, count


def replace_in_json_value(obj, old: str, new: str) -> tuple:
    """Recursively replace exact matches in all JSON string values.

    Returns (new_obj, total_count). Preserves structure and non-string types.
    """
    total = 0

    if isinstance(obj, str):
        new_val, cnt = exact_replace_in_string(obj, old, new)
        return new_val, cnt

    elif isinstance(obj, list):
        new_list = []
        for item in obj:
            new_item, cnt = replace_in_json_value(item, old, new)
            total += cnt
            new_list.append(new_item)
        return new_list, total

    elif isinstance(obj, dict):
        new_dict = {}
        for key, val in obj.items():
            # Replace in keys too — entity names may appear as JSON keys
            new_key, key_cnt = exact_replace_in_string(key, old, new)
            total += key_cnt

            new_val, val_cnt = replace_in_json_value(val, old, new)
            total += val_cnt

            new_dict[new_key] = new_val
        return new_dict, total

    # Numbers, booleans, None — no replacement possible
    return obj, 0


# ---------------------------------------------------------------------------
# File processing
# ---------------------------------------------------------------------------

def collect_target_files(book_dir: str, scopes: list) -> list:
    """Collect all existing target files for the given scopes.

    Returns list of (relative_path, absolute_path, is_json) tuples.
    """
    targets = []
    seen = set()

    for scope in scopes:
        patterns = SCOPE_MAP.get(scope, [])
        for rel_path in patterns:
            if rel_path in seen:
                continue
            seen.add(rel_path)

            abs_path = os.path.join(book_dir, rel_path)
            if os.path.isfile(abs_path):
                is_json = rel_path.endswith(".json")
                targets.append((rel_path, abs_path, is_json))

    return targets


def collect_chapter_files(book_dir: str) -> list:
    """Collect all chapter files in books/<id>/chapters/.

    Returns list of (relative_path, absolute_path, is_json=False) tuples.
    """
    chapters_dir = os.path.join(book_dir, "chapters")
    if not os.path.isdir(chapters_dir):
        return []

    results = []
    for fname in sorted(os.listdir(chapters_dir)):
        if fname.startswith("chapter-") and fname.endswith(".md"):
            rel = os.path.join("chapters", fname)
            abs_path = os.path.join(chapters_dir, fname)
            results.append((rel, abs_path, False))

    return results


def process_file(abs_path: str, is_json: bool, old: str, new: str) -> int:
    """Process a single file, performing exact replacements.

    Returns the number of replacements made. Writes back only if changes occurred.
    """
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError) as exc:
        print(
            json.dumps({"error": "Cannot read %s: %s" % (abs_path, str(exc))}),
            file=sys.stderr,
        )
        return 0

    if is_json:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            print(
                json.dumps({"error": "Invalid JSON in %s: %s" % (abs_path, str(exc))}),
                file=sys.stderr,
            )
            return 0

        new_data, count = replace_in_json_value(data, old, new)
        if count > 0:
            # Preserve pretty-printed formatting with ensure_ascii=False for CJK
            new_content = json.dumps(new_data, indent=2, ensure_ascii=False)
            # Ensure trailing newline
            if not new_content.endswith("\n"):
                new_content += "\n"
            _write_file(abs_path, new_content)
        return count

    else:
        new_content, count = exact_replace_in_string(content, old, new)
        if count > 0:
            _write_file(abs_path, new_content)
        return count


def _write_file(abs_path: str, content: str) -> None:
    """Write content to file with UTF-8 encoding."""
    try:
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
    except (OSError, IOError) as exc:
        print(
            json.dumps({"error": "Cannot write %s: %s" % (abs_path, str(exc))}),
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Global exact-match entity rename across truth files."
    )
    parser.add_argument(
        "book_dir",
        help="Path to the book directory (e.g., books/book-20260414-103045)",
    )
    parser.add_argument(
        "--old",
        required=True,
        help="Old entity name to replace",
    )
    parser.add_argument(
        "--new",
        required=True,
        dest="new_name",
        help="New entity name to use",
    )
    parser.add_argument(
        "--scope",
        default="all",
        choices=ALL_SCOPES + ["all"],
        help="Scope of files to rename in (default: all)",
    )
    parser.add_argument(
        "--no-chapters",
        action="store_true",
        help="Skip chapter files (only rename truth/state files)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    book_dir = os.path.abspath(args.book_dir)
    old_name = args.old
    new_name = args.new_name

    # Validate book directory
    if not os.path.isdir(book_dir):
        result = {
            "error": "Book directory not found: %s" % book_dir,
            "oldName": old_name,
            "newName": new_name,
            "filesModified": 0,
            "replacements": 0,
            "details": [],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    # Validate old != new
    if old_name == new_name:
        result = {
            "error": "Old name and new name are identical.",
            "oldName": old_name,
            "newName": new_name,
            "filesModified": 0,
            "replacements": 0,
            "details": [],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    # Determine scopes
    if args.scope == "all":
        active_scopes = ALL_SCOPES
    else:
        active_scopes = [args.scope]

    # Collect target files
    target_files = collect_target_files(book_dir, active_scopes)

    # Optionally include chapter files
    chapter_files = []
    if not args.no_chapters:
        chapter_files = collect_chapter_files(book_dir)

    all_files = target_files + chapter_files

    # Process all files
    details = []
    total_replacements = 0
    files_modified = 0

    for rel_path, abs_path, is_json in all_files:
        count = process_file(abs_path, is_json, old_name, new_name)
        if count > 0:
            details.append({"file": rel_path, "count": count})
            total_replacements += count
            files_modified += 1

    # Sort details by replacement count descending
    details.sort(key=lambda d: d["count"], reverse=True)

    result = {
        "oldName": old_name,
        "newName": new_name,
        "scope": args.scope,
        "filesModified": files_modified,
        "replacements": total_replacements,
        "details": details,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
