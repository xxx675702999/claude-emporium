#!/usr/bin/env python3
"""paragraph-stats.py — Paragraph length statistics analysis

Computes paragraph length statistics: average, min, max, range, count.
Handles both Chinese (character-level) and English (word-level) texts.

Usage: ./paragraph-stats.py <file-path>
Output: JSON to stdout
"""

import json
import re
import sys


def detect_cjk(text: str) -> bool:
    """Detect CJK characters using native Python Unicode comparison."""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def paragraph_length(para: str, is_cjk: bool) -> int:
    """Compute paragraph length: character count for CJK, word count for English."""
    if is_cjk:
        return len(para.replace(" ", "").replace("\t", "").replace("\n", ""))
    else:
        return len(para.split())


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: paragraph-stats.py <file_path>"}), file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError):
        print(json.dumps({"error": "File not found: %s" % file_path}), file=sys.stderr)
        sys.exit(1)

    is_cjk = detect_cjk(content)
    lang = "zh" if is_cjk else "en"

    # Split on blank lines
    raw_paragraphs = re.split(r"\n\s*\n", content)
    paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

    if not paragraphs:
        print(json.dumps({
            "language": lang,
            "totalParagraphs": 0,
            "avgLength": 0,
            "min": 0,
            "max": 0,
            "range": 0,
        }))
        sys.exit(0)

    lengths = [paragraph_length(p, is_cjk) for p in paragraphs]
    # Filter out zero-length paragraphs
    lengths = [l for l in lengths if l > 0]

    if not lengths:
        print(json.dumps({
            "language": lang,
            "totalParagraphs": 0,
            "avgLength": 0,
            "min": 0,
            "max": 0,
            "range": 0,
        }))
        sys.exit(0)

    total = len(lengths)
    avg = sum(lengths) / total
    min_len = min(lengths)
    max_len = max(lengths)
    range_len = max_len - min_len

    result = {
        "language": lang,
        "totalParagraphs": total,
        "avgLength": float("%.2f" % avg),
        "min": min_len,
        "max": max_len,
        "range": range_len,
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
