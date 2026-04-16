#!/usr/bin/env python3
"""generate-focus.py — Auto-generate current_focus.md from latest state.

Reads chapter summary, active hooks, and volume outline to produce
a current_focus.md for the next chapter. Preserves any existing
"Local Override" section if present (manual overrides survive regeneration).

Usage:
  python3 generate-focus.py <book-dir> [--chapter <N>]

If --chapter is omitted, uses manifest.lastAppliedChapter.

Output: writes story/current_focus.md, prints path to stdout.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.json_utils import read_json


def get_next_outline_node(outline_path: Path, next_chapter: int) -> str:
    """Extract the outline node for the next chapter from volume_outline.md."""
    if not outline_path.is_file():
        return ""
    text = outline_path.read_text(encoding="utf-8")

    # Match patterns: "Chapter 16:", "第16章：", "Chapter 15-17:", "第15-17章："
    for line in text.split("\n"):
        # Exact match
        m = re.match(
            rf"^[#\s]*(?:Chapter\s+{next_chapter}|第{next_chapter}章)[：:]\s*(.+)",
            line, re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()
        # Range match
        m = re.match(
            rf"^[#\s]*(?:Chapter\s+(\d+)\s*-\s*(\d+)|第(\d+)-(\d+)章)[：:]\s*(.+)",
            line, re.IGNORECASE,
        )
        if m:
            start = int(m.group(1) or m.group(3))
            end = int(m.group(2) or m.group(4))
            if start <= next_chapter <= end:
                return m.group(5).strip()
    return ""


def get_active_hooks_summary(hooks_path: Path) -> list[dict]:
    """Get active hooks sorted by priority."""
    data = read_json(str(hooks_path))
    if not data:
        return []

    hooks = data.get("hooks", [])
    active = [
        h for h in hooks
        if h.get("status") not in ("resolved", "deferred")
    ]

    # Sort: critical > escalating > progressing > open, then by lastAdvancedChapter asc
    priority = {"critical": 0, "escalating": 1, "progressing": 2, "open": 3}
    active.sort(key=lambda h: (
        priority.get(h.get("status", "open"), 9),
        h.get("lastAdvancedChapter", 0),
    ))
    return active


def get_latest_summary(summaries_path: Path, chapter: int) -> dict | None:
    """Get the summary for a specific chapter."""
    data = read_json(str(summaries_path))
    if not data:
        return None
    for ch in data.get("chapters", []):
        if ch.get("chapter") == chapter:
            return ch
    return None


def get_current_state_snapshot(state_path: Path) -> dict[str, str]:
    """Get current valid facts as key-value pairs."""
    data = read_json(str(state_path))
    if not data:
        return {}
    result = {}
    for fact in data.get("facts", []):
        if fact.get("validUntilChapter") is None:
            result[fact.get("predicate", "")] = fact.get("object", "")
    return result


def generate_focus(
    book_dir: Path,
    chapter: int,
    next_chapter: int,
    language: str,
) -> str:
    """Generate current_focus.md content."""
    state_dir = book_dir / "story" / "state"
    story_dir = book_dir / "story"

    # Gather data
    summary = get_latest_summary(state_dir / "chapter_summaries.json", chapter)
    active_hooks = get_active_hooks_summary(state_dir / "pending_hooks.json")
    outline_node = get_next_outline_node(story_dir / "volume_outline.md", next_chapter)
    state = get_current_state_snapshot(state_dir / "current_state.json")

    lines = []

    # Section 1: What just happened
    if language == "zh":
        lines.append(f"# 当前聚焦（第{chapter}章后）")
        lines.append("")
        if summary:
            events = summary.get("events", "")
            if events and "pending" not in events:
                lines.append(f"## 上章回顾（第{chapter}章：{summary.get('title', '')}）")
                lines.append(events)
                lines.append("")
    else:
        lines.append(f"# Current Focus (after Chapter {chapter})")
        lines.append("")
        if summary:
            events = summary.get("events", "")
            if events and "pending" not in events:
                lines.append(f"## Previous Chapter (Ch {chapter}: {summary.get('title', '')})")
                lines.append(events)
                lines.append("")

    # Section 2: Current state snapshot
    if state:
        if language == "zh":
            lines.append("## 当前状态")
        else:
            lines.append("## Current State")
        for pred, obj in state.items():
            # Truncate long values
            display = obj[:120] + "..." if len(obj) > 120 else obj
            lines.append(f"- **{pred}**: {display}")
        lines.append("")

    # Section 3: Outline direction for next chapter
    if outline_node:
        if language == "zh":
            lines.append(f"## 下章方向（第{next_chapter}章）")
            lines.append(outline_node)
        else:
            lines.append(f"## Next Chapter Direction (Ch {next_chapter})")
            lines.append(outline_node)
        lines.append("")

    # Section 4: Active hooks by priority
    if active_hooks:
        if language == "zh":
            lines.append("## 活跃伏笔")
        else:
            lines.append("## Active Hooks")

        for h in active_hooks[:10]:
            hid = h.get("hookId", "?")
            htype = h.get("type", "")
            status = h.get("status", "open")
            notes = h.get("notes", "")
            last = h.get("lastAdvancedChapter", 0)
            # Truncate notes
            if len(notes) > 80:
                notes = notes[:80] + "..."
            badge = f"**{status}**" if status in ("critical", "escalating") else status
            lines.append(f"- {hid}（{htype}, {badge}, 最近推进: ch{last}）: {notes}")
        lines.append("")

    # Section 5: Suggested priorities
    critical_hooks = [h for h in active_hooks if h.get("status") == "critical"]
    escalating_hooks = [h for h in active_hooks if h.get("status") == "escalating"]
    stale_hooks = [
        h for h in active_hooks
        if h.get("status") in ("open", "progressing")
        and chapter - h.get("lastAdvancedChapter", 0) >= 8
    ]

    if critical_hooks or escalating_hooks or stale_hooks:
        if language == "zh":
            lines.append("## 建议优先级")
            if critical_hooks:
                ids = ", ".join(h["hookId"] for h in critical_hooks)
                lines.append(f"- **必须处理**: {ids}")
            if escalating_hooks:
                ids = ", ".join(h["hookId"] for h in escalating_hooks)
                lines.append(f"- **需要推进**: {ids}")
            if stale_hooks:
                ids = ", ".join(h["hookId"] for h in stale_hooks)
                lines.append(f"- **长期未推进（≥8章）**: {ids}")
        else:
            lines.append("## Suggested Priorities")
            if critical_hooks:
                ids = ", ".join(h["hookId"] for h in critical_hooks)
                lines.append(f"- **Must address**: {ids}")
            if escalating_hooks:
                ids = ", ".join(h["hookId"] for h in escalating_hooks)
                lines.append(f"- **Should advance**: {ids}")
            if stale_hooks:
                ids = ", ".join(h["hookId"] for h in stale_hooks)
                lines.append(f"- **Stale (≥8 chapters)**: {ids}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-generate current_focus.md")
    parser.add_argument("book_dir", help="Book directory path")
    parser.add_argument("--chapter", type=int, help="Chapter number (default: from manifest)")
    args = parser.parse_args()

    book_dir = Path(args.book_dir)
    state_dir = book_dir / "story" / "state"
    story_dir = book_dir / "story"

    # Read book config
    book_json = read_json(str(book_dir / "book.json"))
    if not book_json:
        print("Error: book.json not found or invalid", file=sys.stderr)
        return 1
    language = book_json.get("language", "zh")

    # Determine chapter
    if args.chapter:
        chapter = args.chapter
    else:
        manifest = read_json(str(state_dir / "manifest.json"))
        if manifest:
            chapter = manifest.get("lastAppliedChapter", 0)
        else:
            chapter = 0

    if chapter <= 0:
        print("Error: no chapter to generate focus from", file=sys.stderr)
        return 1

    next_chapter = chapter + 1

    # Generate
    content = generate_focus(book_dir, chapter, next_chapter, language)

    # Write
    output_path = story_dir / "current_focus.md"
    output_path.write_text(content, encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
