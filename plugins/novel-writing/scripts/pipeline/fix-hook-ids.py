#!/usr/bin/env python3
"""fix-hook-ids.py — one-shot migration for malformed hookIds.

Scans pending_hooks.json for hookIds that don't match ^H\\d+(_\\d+)?$,
resolves each one via rename or merge, then cross-updates references
to the old id in other state JSONs.

Usage:
    python3 fix-hook-ids.py <book-dir>               # interactive
    python3 fix-hook-ids.py <book-dir> --dry-run     # report only, no writes
    python3 fix-hook-ids.py <book-dir> --auto-merge  # non-interactive: drop
                                                      # dup, rename orphan
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
from lib.json_utils import read_json, write_json  # noqa: E402

HOOK_ID_RE = re.compile(r"^H\d+(_\d+)?$")
SUFFIX_RE = re.compile(r"\s*[(\uff08][^)\uff09]*[)\uff09]\s*$")


def infer_base(bad_id: str) -> str:
    """Strip trailing (新增)/(new)/whitespace annotations."""
    cleaned = SUFFIX_RE.sub("", bad_id).strip()
    if HOOK_ID_RE.match(cleaned):
        return cleaned
    # Fallback: keep only leading "H\d+" prefix
    m = re.match(r"(H\d+(?:_\d+)?)", cleaned)
    return m.group(1) if m else cleaned


def next_free_seq(existing_ids: set[str], chapter_prefix: str) -> str:
    """Given prefix like 'H15', return 'H15_N' where N is the smallest free seq."""
    seq = 1
    while f"{chapter_prefix}_{seq}" in existing_ids:
        seq += 1
    return f"{chapter_prefix}_{seq}"


def plan_rename(hooks: list[dict]) -> list[dict]:
    """Return list of operations describing what will change.

    Each op: {'bad_id', 'base', 'action', 'new_id'} where action is
    'rename' or 'merge' (merge means drop the malformed entry).
    """
    ids = {h.get("hookId", "") for h in hooks}
    bad = [h for h in hooks if h.get("hookId", "") and not HOOK_ID_RE.match(h["hookId"])]
    ops = []
    for h in bad:
        bad_id = h["hookId"]
        base = infer_base(bad_id)
        if base in ids and base != bad_id:
            ops.append({
                "bad_id": bad_id,
                "base": base,
                "action": "merge",
                "new_id": base,
            })
        else:
            # No collision: rename to base (claiming that id)
            ops.append({
                "bad_id": bad_id,
                "base": base,
                "action": "rename",
                "new_id": base,
            })
            ids.add(base)  # now reserved
    return ops


def apply_plan(hooks: list[dict], ops: list[dict]) -> list[dict]:
    """Apply rename/merge operations to the hooks list."""
    out = []
    merges = {op["bad_id"] for op in ops if op["action"] == "merge"}
    renames = {op["bad_id"]: op["new_id"] for op in ops if op["action"] == "rename"}
    for h in hooks:
        hid = h.get("hookId", "")
        if hid in merges:
            continue  # drop
        if hid in renames:
            new_h = dict(h)
            new_h["hookId"] = renames[hid]
            out.append(new_h)
        else:
            out.append(h)
    return out


def update_references(state_dir: Path, ops: list[dict]) -> list[str]:
    """Walk every *.json under state_dir and do literal string replacements
    of bad_id with new_id. Returns list of files touched."""
    touched = []
    replacements = [(op["bad_id"], op["new_id"]) for op in ops]
    for jf in state_dir.glob("**/*.json"):
        if jf.name == "pending_hooks.json":
            continue  # handled separately
        text = jf.read_text(encoding="utf-8")
        new_text = text
        for bad, good in replacements:
            new_text = new_text.replace(bad, good)
        if new_text != text:
            jf.write_text(new_text, encoding="utf-8")
            touched.append(jf.name)
    return touched


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate malformed hookIds.")
    ap.add_argument("book_dir")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--auto-merge", action="store_true",
                    help="Non-interactive: merge collisions, rename orphans.")
    args = ap.parse_args()

    book_dir = Path(args.book_dir)
    state_dir = book_dir / "story" / "state"
    hooks_path = state_dir / "pending_hooks.json"

    if not hooks_path.is_file():
        print(f"Error: no pending_hooks.json at {hooks_path}", file=sys.stderr)
        return 1

    data = read_json(str(hooks_path))
    hooks = data.get("hooks", [])

    ops = plan_rename(hooks)
    if not ops:
        print("No malformed hookIds found. Nothing to do.")
        return 0

    print(f"Found {len(ops)} malformed hookId(s):")
    for op in ops:
        print(f"  {op['bad_id']!r} → {op['action']} as {op['new_id']!r}")

    if args.dry_run:
        print("[DRY RUN] No files written.")
        return 0

    if not args.auto_merge:
        # Interactive: require a TTY so we don't hang on piped input.
        if not sys.stdin.isatty():
            print(
                "Error: refusing to run interactively without a TTY. "
                "Re-run with --auto-merge to accept the default plan.",
                file=sys.stderr,
            )
            return 1
        ans = input("Proceed with plan above? [y/N]: ").strip().lower()
        if ans != "y":
            print("Aborted.")
            return 0

    new_hooks = apply_plan(hooks, ops)
    data["hooks"] = new_hooks
    write_json(str(hooks_path), data)

    touched = update_references(state_dir, ops)
    print(f"pending_hooks.json rewritten ({len(hooks)} → {len(new_hooks)} entries).")
    if touched:
        print(f"Updated references in: {', '.join(touched)}")
    else:
        print("No cross-references needed updating.")
    print("Next apply-delta.py run will regenerate markdown projections.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
