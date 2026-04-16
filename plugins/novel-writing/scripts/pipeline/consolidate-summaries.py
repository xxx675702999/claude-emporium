#!/usr/bin/env python3
"""consolidate-summaries.py — Consolidate chapter summaries into volume-level archives.

Usage: consolidate-summaries.py <book-dir> <current-chapter>

Detects threshold overflow, archives old summaries, and outputs a
consolidation prompt for Claude to execute.

Claude (the LLM) generates the actual narrative summary at temp 0.3,
maxTokens 1024, output <= 500 words.

Threshold is read from book.json.consolidationThreshold (default: 50).
Null or 0 disables consolidation.

Exit codes:
  0 — success (or consolidation not needed)
  1 — fatal error (invalid args, missing file)
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.json_utils import read_json, write_json


def fatal(msg: str) -> None:
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


def skip(reason: str, **extra) -> None:
    print(json.dumps({"action": "skip", "reason": reason, **extra}))
    sys.exit(0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consolidate chapter summaries into volume-level narrative summaries."
    )
    parser.add_argument("book_dir", metavar="<book-dir>", help="Path to the book directory")
    parser.add_argument(
        "current_chapter",
        metavar="<current-chapter>",
        type=int,
        help="Current chapter number (positive integer)",
    )
    return parser.parse_args()


def build_chapters_text(chapters: list) -> str:
    if not chapters:
        return "  (no summaries)"
    lines = []
    for ch in chapters:
        lines.append(f"Chapter {ch.get('chapter')}: {ch.get('title') or 'Untitled'}")
        lines.append(f"  Characters: {ch.get('characters') or 'N/A'}")
        lines.append(f"  Events: {ch.get('events') or 'N/A'}")
        lines.append(f"  State Changes: {ch.get('stateChanges') or 'N/A'}")
        lines.append(f"  Hook Activity: {ch.get('hookActivity') or 'N/A'}")
        lines.append(f"  Mood: {ch.get('mood') or 'N/A'}")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    book_dir = Path(args.book_dir)
    current_chapter: int = args.current_chapter

    # --- Validate arguments ---
    if not book_dir.is_dir():
        fatal(f"Book directory not found: {book_dir}")

    if current_chapter < 1:
        fatal(f"current-chapter must be a positive integer, got: {current_chapter}")

    # --- Resolve threshold from book.json ---
    threshold = 50
    book_json_path = book_dir / "book.json"

    if book_json_path.is_file():
        book_data = read_json(str(book_json_path))
        if book_data is None:
            fatal("Invalid JSON in book.json")
        raw_threshold = book_data.get("consolidationThreshold")
        if isinstance(raw_threshold, int) and raw_threshold >= 1:
            threshold = raw_threshold
        elif isinstance(raw_threshold, float) and raw_threshold >= 1:
            threshold = int(raw_threshold)

    # --- Load chapter summaries ---
    summaries_path = book_dir / "story" / "state" / "chapter_summaries.json"

    if not summaries_path.is_file():
        skip("no_summaries_file", threshold=threshold, currentChapter=current_chapter)

    summaries_data = read_json(str(summaries_path))
    if summaries_data is None:
        skip("invalid_json", threshold=threshold, currentChapter=current_chapter)

    all_chapters: list = summaries_data.get("chapters", [])
    total_chapters = len(all_chapters)

    if total_chapters == 0:
        skip("empty_summaries", threshold=threshold, totalChapters=0)

    # --- Check if consolidation is needed ---
    current_vol_start = ((current_chapter - 1) // threshold) * threshold + 1
    completed_vol_count = (current_vol_start - 1) // threshold

    if completed_vol_count == 0:
        skip(
            "no_completed_volumes",
            threshold=threshold,
            totalChapters=total_chapters,
            currentChapter=current_chapter,
        )

    # --- Determine which volumes need consolidation ---
    archive_dir = book_dir / "story" / "summaries_archive"
    vols_to_consolidate = [
        vol
        for vol in range(1, completed_vol_count + 1)
        if not (archive_dir / f"volume-{vol}.json").is_file()
    ]

    if not vols_to_consolidate:
        skip(
            "already_consolidated",
            threshold=threshold,
            totalChapters=total_chapters,
            currentChapter=current_chapter,
        )

    # --- Prepare archival and consolidation prompt ---
    archive_dir.mkdir(parents=True, exist_ok=True)

    prompt_blocks = []
    volume_metadata = []
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for vol in vols_to_consolidate:
        vol_start = (vol - 1) * threshold + 1
        vol_end = min(vol * threshold, total_chapters)
        chapter_count = vol_end - vol_start + 1

        vol_chapters = [
            ch for ch in all_chapters if vol_start <= ch.get("chapter", 0) <= vol_end
        ]
        if not vol_chapters:
            continue

        # Archive original summaries
        archive_file = archive_dir / f"volume-{vol}.json"
        archive_data = {
            "volume": vol,
            "startChapter": vol_start,
            "endChapter": vol_end,
            "archivedAt": now_iso,
            "chapters": vol_chapters,
        }
        write_json(str(archive_file), archive_data)

        # Build human-readable chapter list for the prompt
        chapters_text = build_chapters_text(vol_chapters)

        prompt_blocks.append(
            {"volume": vol, "chapterCount": chapter_count, "chaptersText": chapters_text}
        )
        volume_metadata.append(
            {
                "volume": vol,
                "startChapter": vol_start,
                "endChapter": vol_end,
                "chapterCount": chapter_count,
            }
        )

    # --- Prune archived chapters from chapter_summaries.json ---
    kept_chapters = [ch for ch in all_chapters if ch.get("chapter", 0) >= current_vol_start]

    # Backup before modifying
    shutil.copy2(str(summaries_path), str(summaries_path) + ".bak")

    updated_summaries = dict(summaries_data)
    updated_summaries["chapters"] = kept_chapters
    write_json(str(summaries_path), updated_summaries)

    keep_chapters = len(kept_chapters)

    # --- Output consolidation instructions ---
    output = {
        "action": "consolidate",
        "threshold": threshold,
        "totalChapters": total_chapters,
        "currentChapter": current_chapter,
        "completedVolumes": completed_vol_count,
        "volumesToConsolidate": volume_metadata,
        "archivedChapters": total_chapters - keep_chapters,
        "remainingChapters": keep_chapters,
        "consolidationPrompt": {
            "instructions": (
                "Generate a narrative summary for each completed volume below. "
                "Requirements: (1) Temperature 0.3, maxTokens 1024. "
                "(2) Each volume summary must be <= 500 words. "
                "(3) Retain specific character names, locations, and plot points "
                "— do NOT genericize or abstract away proper nouns. "
                "(4) Cover: major plot arcs, character development, key turning points, "
                "unresolved hooks, and emotional trajectory. "
                "(5) Write in the same language as the book content. "
                "(6) Output format: a JSON object with key 'volumeSummaries' containing "
                "an array of {volume, summary} objects."
            ),
            "volumes": prompt_blocks,
        },
        "archiveDir": str(archive_dir),
        "afterConsolidation": {
            "writeVolumeSummaries": (
                f"Write generated summaries to {book_dir}/story/state/volume_summaries.json"
            ),
            "regenerateProjection": (
                "Run markdown-render.sh to regenerate volume_summaries.md"
            ),
        },
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
