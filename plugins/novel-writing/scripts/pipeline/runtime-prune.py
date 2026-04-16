#!/usr/bin/env python3
# Usage: runtime-prune.py <book-dir> <current-chapter>
# Sliding window cleanup for runtime files.
#
# Each chapter generates up to 10 runtime files:
#   intent, context, rule-stack, trace, delta,
#   llm-audit, deterministic, sensitive, audit, reaudit
#
# Retention policy:
#   - Current + 2 previous chapters: keep all files
#   - Older chapters: keep only delta.json and revision-log.json (provenance)
#   - Delta and revision-log files are NEVER deleted
#
# Max prunable files = (currentChapter + 2) x len(PRUNABLE_TYPES)
# Execute after persist stage.
#
# Output:
#   Runtime pruning: keeping ch.N-ch.M (window=3), pruning older
#   Deleted: X files (5 types x Y chapters)
#   Retained: Z delta files (ch.A-ch.B)
#   Total runtime files: N (<= M = (X+2)x6)
#
# Exit: 0 on success, 1 on error

import argparse
import os
import sys
from pathlib import Path

PRUNABLE_TYPES = [
    "intent.md",
    "context.json",
    "rule-stack.yaml",
    "trace.json",
    "audit.json",
    "llm-audit.json",
    "deterministic.json",
    "sensitive.json",
    "reaudit.json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sliding window cleanup for novel runtime files."
    )
    parser.add_argument("book_dir", metavar="<book-dir>", help="Path to book directory")
    parser.add_argument(
        "current_chapter",
        metavar="<current-chapter>",
        help="Current chapter number (positive integer)",
    )
    return parser.parse_args()


def validate_args(book_dir: str, current_chapter_str: str) -> tuple[Path, int]:
    book_path = Path(book_dir)
    if not book_path.is_dir():
        print(f"Error: book directory does not exist: {book_dir}", file=sys.stderr)
        sys.exit(1)

    if not current_chapter_str.isdigit() or int(current_chapter_str) < 1:
        print(
            f"Error: current-chapter must be a positive integer, got: {current_chapter_str}",
            file=sys.stderr,
        )
        sys.exit(1)

    return book_path, int(current_chapter_str)


def main() -> None:
    args = parse_args()
    book_path, current_chapter = validate_args(args.book_dir, args.current_chapter)

    runtime_dir = book_path / "story" / "runtime"
    if not runtime_dir.is_dir():
        print("Runtime pruning: no runtime directory, nothing to prune")
        sys.exit(0)

    # Determine retention window: keep [threshold, current_chapter] inclusive
    threshold = max(1, current_chapter - 2)

    # Find all delta files to identify chapters older than the threshold
    pruned_chapters: list[int] = []
    for delta_file in sorted(runtime_dir.glob("chapter-*.delta.json")):
        stem = delta_file.name  # chapter-XXXX.delta.json
        # Extract the numeric part between "chapter-" and the first "."
        chapter_str = stem.removeprefix("chapter-").split(".")[0]
        try:
            chapter_num = int(chapter_str, 10)
        except ValueError:
            continue
        if chapter_num < threshold:
            pruned_chapters.append(chapter_num)

    # Delete prunable file types for old chapters
    deleted_count = 0
    for ch_num in pruned_chapters:
        padded = f"{ch_num:04d}"
        for ftype in PRUNABLE_TYPES:
            target = runtime_dir / f"chapter-{padded}.{ftype}"
            if target.is_file():
                os.unlink(target)
                deleted_count += 1

    # Count total remaining files
    total_files = sum(1 for _ in runtime_dir.rglob("*") if Path(_).is_file())

    window_count = current_chapter - threshold + 1
    max_files = (current_chapter + 2) * 6
    delta_retained_count = len(pruned_chapters)
    types_per_chapter = len(PRUNABLE_TYPES)

    # Report
    if not pruned_chapters:
        print(
            f"Runtime pruning: keeping ch.1-{current_chapter}"
            f" (window={window_count}), no older chapters to prune"
        )
    else:
        first_pruned = pruned_chapters[0]
        last_pruned = pruned_chapters[-1]
        print(
            f"Runtime pruning: keeping ch.{threshold}-{current_chapter}"
            f" (window={window_count}), pruning older"
        )
        print(
            f"Deleted: {deleted_count} files"
            f" ({types_per_chapter} types x {len(pruned_chapters)} chapters)"
        )
        print(
            f"Retained: {delta_retained_count} delta files"
            f" (ch.{first_pruned}-{last_pruned})"
        )

    if total_files <= max_files:
        print(
            f"Total runtime files: {total_files}"
            f" (<= {max_files} = ({current_chapter}+2)x6)"
        )
    else:
        print(
            f"Warning: total runtime files {total_files}"
            f" exceeds max {max_files} = ({current_chapter}+2)x6",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
