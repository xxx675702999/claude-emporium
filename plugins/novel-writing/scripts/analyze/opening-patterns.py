#!/usr/bin/env python3
"""opening-patterns.py — Sentence opening pattern analysis

Extracts the most frequent sentence-opening patterns.
Chinese: first 3 characters of each sentence.
English: first 3 words (lowercased, punctuation removed).

Usage: ./opening-patterns.py <file-path>
Output: JSON to stdout
"""

import json
import re
import sys
from collections import Counter


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


def extract_opening(sentence: str, is_cjk: bool) -> str:
    """Extract the opening pattern from a sentence."""
    if is_cjk:
        clean = sentence.replace(" ", "").replace("\t", "").replace("\n", "")
        if len(clean) >= 2:
            return clean[:3]
        return ""
    else:
        # Lowercase, extract first 3 words, remove punctuation
        words = sentence.lower().split()
        words = [re.sub(r"[^\w]", "", w) for w in words[:3]]
        words = [w for w in words if w]
        return " ".join(words)


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: opening-patterns.py <file_path>"}), file=sys.stderr)
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
    openings = [extract_opening(s, is_cjk) for s in sentences]
    openings = [o for o in openings if o]

    if not openings:
        print(json.dumps({"language": lang, "patterns": []}))
        sys.exit(0)

    counter = Counter(openings)
    # Top 10 most frequent
    top_patterns = [
        {"pattern": pattern, "count": count}
        for pattern, count in counter.most_common(10)
    ]

    result = {
        "language": lang,
        "patterns": top_patterns,
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
