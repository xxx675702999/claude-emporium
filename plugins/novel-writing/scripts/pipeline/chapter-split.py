#!/usr/bin/env python3
"""
chapter-split.py — Split a text file into individual chapter files.

Usage:
    chapter-split.py <text-file> [output-dir] [custom-regex]

Output:
    JSON list of created files (chapter number, title, file path) to stdout.

Exit codes:
    0  success
    1  error
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Default bilingual chapter heading pattern:
#   Chinese: 第X章 / 第X节 / 第X回  (X = Arabic or Chinese numerals)
#   English: Chapter N / CHAPTER N
DEFAULT_PATTERN = (
    r"^#{0,2}\s*"
    r"(第[零〇○Ｏ０一二三四五六七八九十百千万0-9]+[章节回]"
    r"|Chapter\s+[0-9]+"
    r"|CHAPTER\s+[0-9]+)"
)

# Used to strip the chapter marker prefix when extracting the title
MARKER_STRIP_PATTERN = re.compile(
    r"^#{0,2}\s*"
    r"(第[零〇○Ｏ０一二三四五六七八九十百千万0-9]+[章节回]"
    r"|Chapter\s+[0-9]+"
    r"|CHAPTER\s+[0-9]+)"
    r"[：:\s]*",
    re.UNICODE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split a text file into individual chapter files.",
        usage="chapter-split.py <text-file> [output-dir] [custom-regex]",
    )
    parser.add_argument("text_file", metavar="text-file", help="Input text file to split")
    parser.add_argument(
        "output_dir",
        metavar="output-dir",
        nargs="?",
        default=".",
        help="Directory to write chapter files (default: current directory)",
    )
    parser.add_argument(
        "custom_regex",
        metavar="custom-regex",
        nargs="?",
        default="",
        help="Custom regex pattern for chapter headings (overrides default)",
    )
    return parser.parse_args()


def error(msg: str, extra: dict | None = None) -> None:
    """Print an error JSON object to stderr and exit with code 1."""
    payload: dict = {"error": msg}
    if extra:
        payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


def main() -> None:
    args = parse_args()

    text_path = Path(args.text_file)
    if not text_path.is_file():
        error(f"Text file not found: {args.text_file}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pattern_str = args.custom_regex if args.custom_regex else DEFAULT_PATTERN
    try:
        heading_re = re.compile(pattern_str, re.UNICODE)
    except re.error as exc:
        error(f"Invalid regex pattern: {exc}")

    # Read all lines (preserve line endings for accurate slicing)
    lines = text_path.read_text(encoding="utf-8").splitlines(keepends=True)

    # Locate chapter headings (1-based line numbers to match grep -n behaviour)
    chapters: list[tuple[int, str]] = []  # (line_index_0based, title)
    for idx, line in enumerate(lines):
        if heading_re.search(line.rstrip("\n\r")):
            title = MARKER_STRIP_PATTERN.sub("", line.rstrip("\n\r"), count=1).strip()
            chapters.append((idx, title))

    if not chapters:
        error(
            "No chapter headings detected. "
            "Expected patterns: 第X章, 第X节, Chapter N, or custom regex.",
            {"guidance": "Ensure your text file contains chapter markers matching the expected format."},
        )

    results: list[dict] = []

    for i, (start_idx, title) in enumerate(chapters):
        chapter_num = i + 1

        # Content starts on the line after the heading
        content_start = start_idx + 1
        if i + 1 < len(chapters):
            content_end = chapters[i + 1][0]  # up to (not including) next heading
        else:
            content_end = len(lines)

        chapter_file = output_dir / f"chapter-{chapter_num:04d}.md"
        chapter_file.write_text(
            "".join(lines[content_start:content_end]),
            encoding="utf-8",
        )

        results.append(
            {
                "chapter": chapter_num,
                "title": title,
                "file": str(chapter_file),
            }
        )

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
