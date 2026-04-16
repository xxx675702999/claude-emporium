#!/usr/bin/env python3
"""vocabulary-diversity.py — Vocabulary diversity analysis

Computes vocabulary diversity metrics: total tokens, unique tokens,
type-token ratio (TTR), and top 20 most frequent tokens.
Chinese: character-level tokens. English: word-level tokens.

Usage: ./vocabulary-diversity.py <file-path>
Output: JSON to stdout
"""

import json
import re
import sys
from collections import Counter


def detect_cjk(text: str) -> bool:
    """Detect CJK characters using native Python Unicode comparison."""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def extract_tokens(text: str, is_cjk: bool) -> list:
    """Extract tokens from text based on language."""
    if is_cjk:
        return [ch for ch in text if "\u4e00" <= ch <= "\u9fff"]
    else:
        # Lowercase, split on non-alpha, filter empty
        words = re.split(r"[^a-zA-Z]+", text.lower())
        return [w for w in words if w]


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: vocabulary-diversity.py <file_path>"}), file=sys.stderr)
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

    tokens = extract_tokens(content, is_cjk)

    if not tokens:
        print(json.dumps({
            "language": lang,
            "totalTokens": 0,
            "uniqueTokens": 0,
            "ttr": 0,
            "topFrequent": [],
        }))
        sys.exit(0)

    total = len(tokens)
    counter = Counter(tokens)
    unique = len(counter)
    ttr = unique / total

    # Top 20 most frequent
    top_frequent = [
        {"token": token, "count": count}
        for token, count in counter.most_common(20)
    ]

    result = {
        "language": lang,
        "totalTokens": total,
        "uniqueTokens": unique,
        "ttr": float("%.4f" % ttr),
        "topFrequent": top_frequent,
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
