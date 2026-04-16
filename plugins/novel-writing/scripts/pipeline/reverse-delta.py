#!/usr/bin/env python3
"""reverse-delta.py — Apply inverse delta operations to roll back truth files.

Used by `novel-review --rewrite` to cascade-delete chapters and undo their
state changes. Also reusable by `novel --undo` for single-chapter rollback.

Algorithm:
  1. Discover all delta files for chapters >= startingChapter
  2. Sort by chapter descending (newest first)
  3. For each delta, apply the inverse of every operation to truth files
  4. Validate all modified truth files via schema-validate
  5. On validation failure, restore backups and report errors

Reverse operation mapping:
  hookOps.upsert       → remove the hookId from pending_hooks.json
  hookOps.resolve      → restore the resolved hook (set status back to what it
                         was, or to "open" if no prior status is available)
  hookOps.mention      → decrement lastAdvancedChapter if it matches delta chapter
  hookOps.defer        → restore status from "deferred" to previous status
  newHookCandidates    → remove hooks whose startChapter matches delta chapter
  chapterSummary       → remove the summary entry from chapter_summaries.json
  currentStatePatch    → not reversible (no oldValue); remove facts by sourceChapter
  subplotOps           → remove entries added by this chapter
  emotionalArcOps      → remove entries added by this chapter
  characterMatrixOps   → remove entries added by this chapter

Usage:
  python3 reverse-delta.py --book-dir <path> --from-chapter <N> [--validate]

Exit codes:
  0 — all reversals applied and validated successfully
  1 — error (invalid args, file not found, validation failure)

Output: JSON to stdout:
  { "reversed": number, "errors": [...], "warnings": [...] }
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared lib import
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.json_utils import read_json, write_json  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Delta discovery
# ---------------------------------------------------------------------------


def discover_deltas(runtime_dir: Path, from_chapter: int) -> list[dict]:
    """Return list of {chapter, path} for deltas >= from_chapter, sorted descending."""
    deltas = []
    if not runtime_dir.exists():
        return deltas

    pattern = re.compile(r"^chapter-(\d+)\.delta\.json$")
    for entry in runtime_dir.iterdir():
        m = pattern.match(entry.name)
        if not m:
            continue
        ch = int(m.group(1))
        if ch >= from_chapter:
            deltas.append({"chapter": ch, "path": entry})

    deltas.sort(key=lambda x: x["chapter"], reverse=True)
    return deltas


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_truth_files(state_dir: Path) -> tuple[bool, list[str]]:
    """Validate truth files using schema-validate.py.

    Returns (valid, errors).
    """
    truth_files = [
        "pending_hooks.json",
        "chapter_summaries.json",
        "current_state.json",
        "manifest.json",
    ]

    files_to_validate = [
        str(state_dir / f) for f in truth_files if (state_dir / f).exists()
    ]

    if not files_to_validate:
        return True, []

    validator_script = SCRIPT_DIR / "schema-validate.py"
    if not validator_script.exists():
        return False, ["schema-validate.py not found, cannot validate"]

    try:
        proc = subprocess.run(
            ["python3", str(validator_script)] + files_to_validate,
            capture_output=True,
            text=True,
            timeout=30,
        )
        results = json.loads(proc.stdout)
        errors = []
        all_valid = True
        for r in results:
            if not r.get("valid", False):
                all_valid = False
                for e in r.get("errors", []):
                    errors.append(f"{Path(r['file']).name}: {e}")
        return all_valid, errors
    except Exception as exc:
        return False, [f"Validation script failed: {exc}"]


# ---------------------------------------------------------------------------
# Reverse operations
# ---------------------------------------------------------------------------


def reverse_hook_upsert(delta: dict, hooks_file: dict, errors: list, warnings: list) -> None:
    """Reverse hookOps.upsert: remove upserted hooks or revert lastAdvancedChapter."""
    chapter = delta["chapter"]
    hooks = hooks_file.get("hooks", [])

    for upserted in delta.get("hookOps", {}).get("upsert", []):
        hook_id = upserted.get("hookId")
        idx = next((i for i, h in enumerate(hooks) if h.get("hookId") == hook_id), -1)

        if idx == -1:
            warnings.append(
                f"chapter {chapter}: hook '{hook_id}' not found in pending_hooks.json "
                "during upsert reversal"
            )
            continue

        existing = hooks[idx]

        if upserted.get("startChapter") == chapter:
            # Newly created hook in this chapter — remove entirely
            hooks.pop(idx)
        else:
            # Update to existing hook — revert lastAdvancedChapter
            existing["lastAdvancedChapter"] = min(
                existing.get("lastAdvancedChapter", chapter),
                chapter - 1,
            )
            # Revert status to "open" if it was set to progressing/deferred
            if existing.get("status") in ("progressing", "deferred"):
                existing["status"] = "open"

    hooks_file["hooks"] = hooks


def reverse_hook_resolve(delta: dict, hooks_file: dict, errors: list, warnings: list) -> None:
    """Reverse hookOps.resolve: restore resolved hooks back to progressing."""
    chapter = delta["chapter"]
    hooks = hooks_file.get("hooks", [])

    for hook_id in delta.get("hookOps", {}).get("resolve", []):
        existing = next((h for h in hooks if h.get("hookId") == hook_id), None)

        if existing:
            if existing.get("status") == "resolved":
                existing["status"] = "progressing"
                if existing.get("lastAdvancedChapter") == chapter:
                    existing["lastAdvancedChapter"] = chapter - 1
        else:
            # Hook was removed — try to recreate from upsert data in the same delta
            upserted = next(
                (h for h in delta.get("hookOps", {}).get("upsert", []) if h.get("hookId") == hook_id),
                None,
            )
            if upserted:
                restored = dict(upserted)
                restored["status"] = "progressing"
                restored["lastAdvancedChapter"] = chapter - 1
                hooks.append(restored)
            else:
                warnings.append(
                    f"chapter {chapter}: resolved hook '{hook_id}' not found in "
                    "pending_hooks.json and no upsert data for restoration"
                )

    hooks_file["hooks"] = hooks


def reverse_hook_mention(delta: dict, hooks_file: dict, warnings: list) -> None:
    """Reverse hookOps.mention: decrement lastAdvancedChapter if it matches delta chapter."""
    chapter = delta["chapter"]
    hooks = hooks_file.get("hooks", [])

    for hook_id in delta.get("hookOps", {}).get("mention", []):
        existing = next((h for h in hooks if h.get("hookId") == hook_id), None)
        if existing and existing.get("lastAdvancedChapter") == chapter:
            existing["lastAdvancedChapter"] = chapter - 1


def reverse_hook_defer(delta: dict, hooks_file: dict, warnings: list) -> None:
    """Reverse hookOps.defer: restore deferred hooks back to open."""
    hooks = hooks_file.get("hooks", [])

    for hook_id in delta.get("hookOps", {}).get("defer", []):
        existing = next((h for h in hooks if h.get("hookId") == hook_id), None)
        if existing and existing.get("status") == "deferred":
            existing["status"] = "open"


def reverse_new_hook_candidates(delta: dict, hooks_file: dict) -> None:
    """Reverse newHookCandidates: remove hooks that started in this chapter."""
    chapter = delta["chapter"]
    hooks = hooks_file.get("hooks", [])

    hooks_file["hooks"] = [
        h for h in hooks
        if not (
            h.get("startChapter") == chapter
            and h.get("lastAdvancedChapter", 0) <= chapter
        )
    ]


def reverse_chapter_summary(delta: dict, summaries_file: dict) -> None:
    """Reverse chapterSummary: remove the summary entry for this chapter."""
    chapter = delta["chapter"]
    rows = summaries_file.get("chapters", [])
    summaries_file["chapters"] = [r for r in rows if r.get("chapter") != chapter]


def reverse_current_state_patch(delta: dict, state_file: dict, warnings: list) -> None:
    """Remove facts introduced by this chapter (partial reversal only)."""
    if not delta.get("currentStatePatch"):
        return

    chapter = delta["chapter"]
    facts = state_file.get("facts", [])
    before_count = len(facts)
    state_file["facts"] = [f for f in facts if f.get("sourceChapter") != chapter]
    removed = before_count - len(state_file["facts"])

    if removed == 0:
        warnings.append(
            f"chapter {chapter}: currentStatePatch present but no facts with "
            "matching sourceChapter found"
        )


def reverse_generic_ops(
    delta: dict,
    state_dir: Path,
    ops_type: str,
    target_file: str,
    match_field: str,
    warnings: list,
) -> None:
    """Reverse generic ops arrays (subplotOps, emotionalArcOps, characterMatrixOps).

    For "add" ops: remove the added entry.
    For "remove" ops with oldValue: restore the removed entry.
    For "update" ops: emit a warning (no oldValue to revert to).
    """
    chapter = delta["chapter"]
    ops = delta.get(ops_type)
    if not ops:
        return

    file_path = state_dir / target_file
    if not file_path.exists():
        warnings.append(
            f"chapter {chapter}: {ops_type} present but {target_file} not found"
        )
        return

    data = read_json(str(file_path))
    if data is None:
        return

    # Find the array key in the data object
    rows_key = next((k for k, v in data.items() if isinstance(v, list)), None)
    if rows_key is None:
        return

    rows: list = data[rows_key]

    for op in ops:
        op_type = op.get("op") or op.get("type") or ""
        match_value = op.get(match_field)

        if op_type == "add" and match_value is not None:
            before_len = len(rows)
            rows = [r for r in rows if r.get(match_field) != match_value]
            if len(rows) < before_len:
                data[rows_key] = rows
        elif op_type == "remove" and op.get("oldValue") is not None:
            old_val = op["oldValue"]
            try:
                if isinstance(old_val, str):
                    restored = json.loads(old_val)
                else:
                    restored = old_val
                rows.append(restored)
                data[rows_key] = rows
            except (json.JSONDecodeError, ValueError):
                warnings.append(
                    f"chapter {chapter}: failed to restore {ops_type} entry from oldValue"
                )
        elif op_type == "update":
            warnings.append(
                f"chapter {chapter}: {ops_type} update for '{match_value}' "
                "cannot be fully reverted (no oldValue)"
            )

    write_json(str(file_path), data)


# ---------------------------------------------------------------------------
# Main reversal logic
# ---------------------------------------------------------------------------


def apply_reverse_deltas(book_dir: Path, from_chapter: int, should_validate: bool) -> dict:
    """Apply inverse delta operations to roll back truth files.

    Returns { reversed: int, errors: list[str], warnings: list[str] }.
    """
    errors: list[str] = []
    warnings: list[str] = []

    state_dir = book_dir / "story" / "state"
    runtime_dir = book_dir / "story" / "runtime"

    # Step 1: Discover deltas for chapters >= from_chapter, sorted descending
    deltas = discover_deltas(runtime_dir, from_chapter)

    if not deltas:
        return {"reversed": 0, "errors": [], "warnings": ["No delta files found"]}

    # Step 2: Read truth files
    hooks_path = state_dir / "pending_hooks.json"
    summaries_path = state_dir / "chapter_summaries.json"
    state_path = state_dir / "current_state.json"
    manifest_path = state_dir / "manifest.json"

    hooks_file = read_json(str(hooks_path)) if hooks_path.exists() else None
    summaries_file = read_json(str(summaries_path)) if summaries_path.exists() else None
    state_file = read_json(str(state_path)) if state_path.exists() else None

    if hooks_file is None and summaries_file is None and state_file is None:
        return {
            "reversed": 0,
            "errors": ["No truth files found in state directory"],
            "warnings": [],
        }

    # Create backups before mutation
    backup_paths: dict[Path, Path] = {}
    for fp in [hooks_path, summaries_path, state_path, manifest_path]:
        if fp.exists():
            backup = fp.with_suffix(fp.suffix + ".bak")
            shutil.copy2(fp, backup)
            backup_paths[fp] = backup

    def restore_backups() -> None:
        for original, backup in backup_paths.items():
            if backup.exists():
                shutil.copy2(backup, original)
                backup.unlink()

    def cleanup_backups() -> None:
        for backup in backup_paths.values():
            if backup.exists():
                backup.unlink()

    # Step 3: Apply reverse operations for each delta (newest first)
    reversed_count = 0

    for item in deltas:
        chapter = item["chapter"]
        delta_path = item["path"]

        delta = read_json(str(delta_path))
        if delta is None:
            errors.append(f"Failed to read or parse delta for chapter {chapter}: {delta_path}")
            continue

        if delta.get("chapter") != chapter:
            errors.append(
                f"Delta file chapter mismatch: expected {chapter}, got {delta.get('chapter')}"
            )
            continue

        # Reverse hook operations
        if hooks_file is not None:
            reverse_hook_upsert(delta, hooks_file, errors, warnings)
            reverse_hook_resolve(delta, hooks_file, errors, warnings)
            reverse_hook_mention(delta, hooks_file, warnings)
            reverse_hook_defer(delta, hooks_file, warnings)
            reverse_new_hook_candidates(delta, hooks_file)

        # Reverse chapter summary
        if summaries_file is not None:
            reverse_chapter_summary(delta, summaries_file)

        # Reverse current state patch
        if state_file is not None:
            reverse_current_state_patch(delta, state_file, warnings)
            # Roll back chapter counter if it was advanced by this delta
            if state_file.get("chapter") == chapter:
                state_file["chapter"] = chapter - 1

        # Reverse generic ops (writes their files inline)
        reverse_generic_ops(delta, state_dir, "subplotOps", "subplot_board.json", "id", warnings)
        reverse_generic_ops(delta, state_dir, "emotionalArcOps", "emotional_arcs.json", "characterId", warnings)
        reverse_generic_ops(delta, state_dir, "characterMatrixOps", "character_matrix.json", "id", warnings)

        reversed_count += 1

    # Step 4: Update manifest.lastAppliedChapter
    manifest_file = read_json(str(manifest_path)) if manifest_path.exists() else None
    if manifest_file is not None:
        manifest_file["lastAppliedChapter"] = from_chapter - 1
        manifest_file["projectionVersion"] = manifest_file.get("projectionVersion", 0) + 1
        write_json(str(manifest_path), manifest_file)

    # Step 5: Write modified in-memory truth files
    if hooks_file is not None:
        write_json(str(hooks_path), hooks_file)
    if summaries_file is not None:
        write_json(str(summaries_path), summaries_file)
    if state_file is not None:
        write_json(str(state_path), state_file)

    # Step 6: Validate truth files
    if should_validate:
        valid, validation_errors = validate_truth_files(state_dir)
        if not valid:
            restore_backups()
            return {
                "reversed": 0,
                "errors": [
                    *errors,
                    "Truth file validation failed after reversal — original files restored:",
                    *validation_errors,
                ],
                "warnings": warnings,
            }

    cleanup_backups()
    return {"reversed": reversed_count, "errors": errors, "warnings": warnings}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="reverse-delta.py",
        description="Apply inverse delta operations to roll back truth files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Deltas for chapters >= N are processed newest-first.\n"
            "\n"
            "Exit codes:\n"
            "  0 — all reversals applied and validated successfully\n"
            "  1 — error (invalid args, file not found, validation failure)\n"
        ),
    )
    parser.add_argument(
        "--book-dir",
        required=True,
        metavar="<path>",
        help="Path to the book directory (e.g., books/my-book)",
    )
    parser.add_argument(
        "--from-chapter",
        required=True,
        type=int,
        metavar="<N>",
        help="Starting chapter number (inclusive, must be >= 1)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=True,
        help="Validate truth files after reversal (default: enabled)",
    )
    parser.add_argument(
        "--no-validate",
        dest="validate",
        action="store_false",
        help="Skip validation after reversal",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    book_dir = Path(args.book_dir).resolve()
    from_chapter: int = args.from_chapter
    should_validate: bool = args.validate

    if from_chapter < 1:
        print("Error: --from-chapter must be a positive integer", file=sys.stderr)
        sys.exit(1)

    if not book_dir.exists():
        print(f"Error: book directory not found: {book_dir}", file=sys.stderr)
        sys.exit(1)

    result = apply_reverse_deltas(book_dir, from_chapter, should_validate)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    sys.exit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()
