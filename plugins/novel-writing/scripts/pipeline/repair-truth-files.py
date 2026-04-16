#!/usr/bin/env python3
"""repair-truth-files.py — One-time repair: apply missing deltas to truth files.

Reads existing deltas, extracts usable data (currentStatePatch, hookOps,
chapterSummary), and applies them to catch up truth files.

Handles known delta format issues:
- Non-standard hookOps status values (improving→progressing, etc.)
- Invalid JSON (attempts auto-fix of common syntax errors)
- Missing chapterSummary fields

Usage: python3 repair-truth-files.py <book-dir> [--dry-run]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.json_utils import read_json, write_json

VALID_HOOK_STATUSES = {"open", "progressing", "escalating", "critical", "deferred", "resolved"}
STATUS_MAP = {
    "improving": "progressing",
    "partial-resolved": "progressing",
    "active": "progressing",
    "stale": "deferred",
}


def load_delta(path: str) -> dict | None:
    """Load a delta file, attempting to fix common JSON errors."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Try to fix common issues: trailing commas, etc.
        with open(path, encoding="utf-8") as f:
            text = f.read()
        # Remove trailing commas before } or ]
        text = re.sub(r",\s*([}\]])", r"\1", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"  [SKIP] Cannot parse {os.path.basename(path)}: {e}", file=sys.stderr)
            return None


def normalize_hook_status(status: str) -> str:
    s = status.lower().strip().strip("*")
    if s in VALID_HOOK_STATUSES:
        return s
    return STATUS_MAP.get(s, "progressing")


def apply_chapter_summary(summaries_data: dict, delta: dict) -> bool:
    cs = delta.get("chapterSummary")
    if not cs or not isinstance(cs, dict):
        return False
    ch_num = cs.get("chapter")
    if not ch_num:
        return False

    chapters = summaries_data.setdefault("chapters", [])
    # Remove existing entry for this chapter
    chapters[:] = [c for c in chapters if c.get("chapter") != ch_num]
    chapters.append({
        "chapter": ch_num,
        "title": cs.get("title", ""),
        "characters": cs.get("characters", ""),
        "events": cs.get("events", ""),
        "stateChanges": cs.get("stateChanges", ""),
        "hookActivity": cs.get("hookActivity", ""),
        "mood": cs.get("mood", ""),
        "chapterType": cs.get("chapterType", ""),
    })
    chapters.sort(key=lambda c: c.get("chapter", 0))
    return True


def apply_current_state_patch(state_data: dict, delta: dict) -> bool:
    patch = delta.get("currentStatePatch")
    ch_num = delta.get("chapter")
    if not patch or not isinstance(patch, dict) or not ch_num:
        return False

    state_data["chapter"] = ch_num
    facts = state_data.setdefault("facts", [])

    # Invalidate old facts that are being replaced
    for pred, obj in patch.items():
        if not obj:
            continue
        for fact in facts:
            if fact.get("predicate") == pred and fact.get("validUntilChapter") is None:
                fact["validUntilChapter"] = ch_num
        facts.append({
            "subject": "Protagonist",
            "predicate": pred,
            "object": str(obj),
            "validFromChapter": ch_num,
            "validUntilChapter": None,
            "sourceChapter": ch_num,
        })
    return True


def apply_hook_ops(hooks_data: dict, delta: dict) -> bool:
    hook_ops = delta.get("hookOps")
    ch_num = delta.get("chapter")
    if not hook_ops or not isinstance(hook_ops, dict):
        return False

    hooks = hooks_data.setdefault("hooks", [])
    changed = False

    # Process upserts
    for upsert in hook_ops.get("upsert") or []:
        if not isinstance(upsert, dict):
            continue
        hid = upsert.get("hookId")
        if not hid:
            continue
        # Normalize status
        raw_status = upsert.get("status", "open")
        upsert["status"] = normalize_hook_status(raw_status)
        upsert["lastAdvancedChapter"] = ch_num
        # Find and replace existing hook
        hooks[:] = [h for h in hooks if h.get("hookId") != hid]
        hooks.append(upsert)
        changed = True

    # Process mentions (update lastAdvancedChapter)
    for hid in hook_ops.get("mention") or []:
        if isinstance(hid, str):
            for h in hooks:
                if h.get("hookId") == hid:
                    h["lastAdvancedChapter"] = ch_num
                    changed = True

    # Process resolves
    for item in hook_ops.get("resolve") or []:
        hid = item if isinstance(item, str) else item.get("hookId", "") if isinstance(item, dict) else ""
        if hid:
            for h in hooks:
                if h.get("hookId") == hid:
                    h["status"] = "resolved"
                    h["lastAdvancedChapter"] = ch_num
                    changed = True

    # Process defers
    for hid in hook_ops.get("defer") or []:
        if isinstance(hid, str):
            for h in hooks:
                if h.get("hookId") == hid:
                    h["status"] = "deferred"
                    h["lastAdvancedChapter"] = ch_num
                    changed = True

    return changed


def main():
    parser = argparse.ArgumentParser(description="Repair truth files from existing deltas")
    parser.add_argument("book_dir", help="Book directory path")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    args = parser.parse_args()

    book_dir = Path(args.book_dir)
    state_dir = book_dir / "story" / "state"
    runtime_dir = book_dir / "story" / "runtime"

    # Load current truth files
    summaries = read_json(str(state_dir / "chapter_summaries.json")) or {"version": 1, "chapters": []}
    current_state = read_json(str(state_dir / "current_state.json")) or {"version": 1, "chapter": 0, "facts": []}
    hooks = read_json(str(state_dir / "pending_hooks.json")) or {"version": 1, "hooks": []}

    existing_summary_chapters = {c["chapter"] for c in summaries.get("chapters", [])}
    state_chapter = current_state.get("chapter", 0)
    print(f"Current state: chapter_summaries has {len(existing_summary_chapters)} chapters, "
          f"current_state at ch{state_chapter}, "
          f"pending_hooks has {len(hooks.get('hooks', []))} hooks")

    # Find and sort deltas
    delta_files = sorted(runtime_dir.glob("*.delta.json"))
    print(f"Found {len(delta_files)} delta files")

    for delta_path in delta_files:
        delta = load_delta(str(delta_path))
        if delta is None:
            continue

        ch_num = delta.get("chapter", 0)
        actions = []

        # Apply chapter summary if missing
        if ch_num not in existing_summary_chapters:
            if apply_chapter_summary(summaries, delta):
                existing_summary_chapters.add(ch_num)
                actions.append("summary")

        # Apply current state patch if this chapter is newer
        if ch_num > current_state.get("chapter", 0):
            if apply_current_state_patch(current_state, delta):
                actions.append("state")

        # Always apply hook ops (they accumulate)
        if apply_hook_ops(hooks, delta):
            actions.append("hooks")

        status = ", ".join(actions) if actions else "no changes"
        print(f"  ch{ch_num:04d}: {status}")

    # Ensure version fields
    summaries.setdefault("version", 1)
    current_state.setdefault("version", 1)
    hooks.setdefault("version", 1)

    # Summary
    print(f"\nAfter repair: chapter_summaries has {len(summaries.get('chapters', []))} chapters, "
          f"current_state at ch{current_state.get('chapter', 0)}, "
          f"pending_hooks has {len(hooks.get('hooks', []))} hooks")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    # Write updated truth files
    write_json(str(state_dir / "chapter_summaries.json"), summaries)
    write_json(str(state_dir / "current_state.json"), current_state)
    write_json(str(state_dir / "pending_hooks.json"), hooks)
    print("\nTruth files updated successfully.")


if __name__ == "__main__":
    main()
