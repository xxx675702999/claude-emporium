#!/usr/bin/env python3
"""sentence-stats.py — Sentence length statistics analysis

Computes sentence length statistics: average, standard deviation,
and distribution buckets. Handles both Chinese (character-level)
and English (word-level) texts.

Usage: ./sentence-stats.py <file-path>
Output: JSON to stdout
"""

import json
import math
import re
import sys


def detect_cjk(text: str) -> bool:
    """Detect CJK characters using native Python Unicode comparison."""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def split_sentences(text: str, is_cjk: bool) -> list:
    """Split text into sentences based on language."""
    if is_cjk:
        parts = re.split(r"[。！？]", text)
    else:
        parts = re.split(r"[.!?]", text)
    return [s.strip() for s in parts if s.strip()]


def sentence_length(sentence: str, is_cjk: bool) -> int:
    """Compute sentence length: character count for CJK, word count for English."""
    if is_cjk:
        return len(sentence.replace(" ", "").replace("\t", "").replace("\n", ""))
    else:
        return len(sentence.split())


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: sentence-stats.py <file_path>"}), file=sys.stderr)
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

    sentences = split_sentences(content, is_cjk)

    if not sentences:
        print(json.dumps({
            "language": lang,
            "totalSentences": 0,
            "avgLength": 0,
            "stddev": 0,
            "distribution": {},
        }))
        sys.exit(0)

    lengths = [sentence_length(s, is_cjk) for s in sentences]
    total = len(lengths)
    avg = sum(lengths) / total
    variance = sum((l - avg) ** 2 for l in lengths) / total
    stddev = math.sqrt(variance)

    # Distribution buckets
    buckets = {"0-10": 0, "11-20": 0, "21-30": 0, "31-50": 0, "51-100": 0, "100+": 0}
    for l in lengths:
        if l <= 10:
            buckets["0-10"] += 1
        elif l <= 20:
            buckets["11-20"] += 1
        elif l <= 30:
            buckets["21-30"] += 1
        elif l <= 50:
            buckets["31-50"] += 1
        elif l <= 100:
            buckets["51-100"] += 1
        else:
            buckets["100+"] += 1

    result = {
        "language": lang,
        "totalSentences": total,
        "avgLength": float("%.2f" % avg),
        "stddev": float("%.2f" % stddev),
        "distribution": buckets,
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
