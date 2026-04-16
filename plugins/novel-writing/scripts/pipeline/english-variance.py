#!/usr/bin/env python3
"""english-variance.py — Detect repetitive patterns in English book chapters.

Analyzes the last N chapters for:
1. High-frequency 3-grams (appearing 3+ times across chapters)
2. Repeated opening patterns (first 3 words of each chapter)
3. Repeated ending patterns (last 3 words of each chapter)

Only runs when book.json language = "en". Outputs JSON brief to stdout.

Usage:
  python3 scripts/pipeline/english-variance.py <book-dir> [--current-chapter N] [--window 5]
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter


def load_book_config(book_dir: str) -> dict:
    """Load book.json from the book directory."""
    config_path = os.path.join(book_dir, "book.json")
    if not os.path.isfile(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_chapters(book_dir: str, current_chapter: int, window: int) -> list[tuple[int, str]]:
    """Find chapter files for the analysis window.

    Returns list of (chapter_number, file_path) sorted by chapter number.
    """
    chapters_dir = os.path.join(book_dir, "chapters")
    if not os.path.isdir(chapters_dir):
        return []

    end = current_chapter - 1  # exclude the current chapter being written
    start = max(1, end - window + 1)

    results = []
    for num in range(start, end + 1):
        padded = "%04d" % num
        # Primary: XXXX_*.md
        pattern = os.path.join(chapters_dir, "%s_*.md" % padded)
        matches = glob.glob(pattern)
        if matches:
            results.append((num, sorted(matches)[0]))
            continue
        # Fallback: chapter-XXXX.md
        fallback = os.path.join(chapters_dir, "chapter-%s.md" % padded)
        if os.path.isfile(fallback):
            results.append((num, fallback))

    return results


def read_chapter_text(filepath: str) -> str:
    """Read chapter file and strip markdown header."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # Remove "# Chapter XXXX: Title" header line
    content = re.sub(r"^#\s+Chapter\s+\d+:.*?\n", "", content, count=1)
    return content.strip()


def extract_3grams(text: str) -> list[str]:
    """Extract all lowercase 3-word sequences from text."""
    # Normalize: collapse whitespace, lowercase
    words = text.lower().split()
    if len(words) < 3:
        return []
    return [" ".join(words[i : i + 3]) for i in range(len(words) - 2)]


def get_opening_3gram(text: str) -> str | None:
    """Extract the first 3 words of chapter prose, lowercased."""
    words = text.lower().split()
    if len(words) < 3:
        return None
    return " ".join(words[:3])


def get_ending_3gram(text: str) -> str | None:
    """Extract the last 3 words of chapter prose, lowercased."""
    words = text.lower().split()
    if len(words) < 3:
        return None
    return " ".join(words[-3:])


def analyze_high_frequency_3grams(chapter_3grams: dict[int, list[str]], threshold: int = 3) -> list[str]:
    """Find 3-grams appearing >= threshold times across all chapters."""
    global_counter = Counter()
    for grams in chapter_3grams.values():
        global_counter.update(grams)
    return [gram for gram, count in global_counter.most_common() if count >= threshold]


def analyze_repeated_patterns(chapter_patterns: dict[int, str | None]) -> list[dict]:
    """Detect duplicate opening or ending patterns across chapters.

    Returns list of {"pattern": str, "chapters": [int]}.
    """
    pattern_chapters: dict[str, list[int]] = {}
    for ch_num, pattern in chapter_patterns.items():
        if pattern is None:
            continue
        if pattern not in pattern_chapters:
            pattern_chapters[pattern] = []
        pattern_chapters[pattern].append(ch_num)

    return [
        {"pattern": pattern, "chapters": sorted(chapters)}
        for pattern, chapters in pattern_chapters.items()
        if len(chapters) > 1
    ]


def build_brief(
    high_freq: list[str],
    repeated_openings: list[dict],
    repeated_endings: list[dict],
    counter_3grams: Counter,
) -> str:
    """Build a human-readable brief summarizing findings."""
    parts = []

    if high_freq:
        mentions = []
        for gram in high_freq[:5]:
            count = counter_3grams[gram]
            mentions.append("'%s' appears %d times" % (gram, count))
        parts.append("Avoid these patterns: " + "; ".join(mentions) + ".")

    for entry in repeated_openings:
        ch_str = " and ".join(["ch.%d" % c for c in entry["chapters"]])
        parts.append("Opening '%s' repeated in %s." % (entry["pattern"], ch_str))

    for entry in repeated_endings:
        ch_str = " and ".join(["ch.%d" % c for c in entry["chapters"]])
        parts.append("Ending '%s' repeated in %s." % (entry["pattern"], ch_str))

    if not parts:
        return "No significant repetitive patterns detected."

    return " ".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect repetitive patterns in English book chapters."
    )
    parser.add_argument("book_dir", help="Path to the book directory (contains book.json)")
    parser.add_argument(
        "--current-chapter",
        type=int,
        default=None,
        help="Current chapter number being written (default: auto-detect from chapters dir)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=5,
        help="Number of recent chapters to analyze (default: 5)",
    )
    args = parser.parse_args()

    # Load book config and check language
    config = load_book_config(args.book_dir)
    language = config.get("language", "")

    if language != "en":
        result = {"skipped": True, "reason": "language is not English"}
        print(json.dumps(result, indent=2))
        return

    # Determine current chapter number
    current_chapter = args.current_chapter
    if current_chapter is None:
        # Auto-detect: find highest chapter number in chapters dir
        chapters_dir = os.path.join(args.book_dir, "chapters")
        if not os.path.isdir(chapters_dir):
            result = {
                "highFrequency3grams": [],
                "repeatedOpenings": [],
                "repeatedEndings": [],
                "brief": "No chapters found for analysis.",
            }
            print(json.dumps(result, indent=2))
            return
        max_chapter = 0
        for filename in os.listdir(chapters_dir):
            match = re.match(r"^(\d{4})_", filename) or re.match(r"^chapter-(\d{4})\.md$", filename)
            if match:
                max_chapter = max(max_chapter, int(match.group(1)))
        current_chapter = max_chapter + 1  # next chapter to write

    # Find chapters in the analysis window
    chapters = find_chapters(args.book_dir, current_chapter, args.window)

    if not chapters:
        result = {
            "highFrequency3grams": [],
            "repeatedOpenings": [],
            "repeatedEndings": [],
            "brief": "No chapters found in the analysis window.",
        }
        print(json.dumps(result, indent=2))
        return

    # Analyze chapters
    chapter_3grams: dict[int, list[str]] = {}
    chapter_openings: dict[int, str | None] = {}
    chapter_endings: dict[int, str | None] = {}
    global_counter = Counter()

    for ch_num, filepath in chapters:
        text = read_chapter_text(filepath)
        grams = extract_3grams(text)
        chapter_3grams[ch_num] = grams
        global_counter.update(grams)
        chapter_openings[ch_num] = get_opening_3gram(text)
        chapter_endings[ch_num] = get_ending_3gram(text)

    high_freq = analyze_high_frequency_3grams(chapter_3grams, threshold=3)
    repeated_openings = analyze_repeated_patterns(chapter_openings)
    repeated_endings = analyze_repeated_patterns(chapter_endings)
    brief = build_brief(high_freq, repeated_openings, repeated_endings, global_counter)

    result = {
        "highFrequency3grams": high_freq,
        "repeatedOpenings": repeated_openings,
        "repeatedEndings": repeated_endings,
        "brief": brief,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
