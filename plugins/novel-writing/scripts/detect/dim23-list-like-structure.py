#!/usr/bin/env python3
"""dim23-list-like-structure.py — Detect AI-tell: list-like sentence structure.

Detects 3+ consecutive sentences with the same opening pattern.
Chinese: first 2 characters of each sentence (split by 。！？\\n)
English: first word of each sentence (split by . ! ? \\n)
Behaviorally equivalent to InkOS core ai-tells.ts dim 23.

Usage: ./dim23-list-like-structure.py <file-path>
Output: JSON to stdout
"""

import json
import re
import sys


def detect_language(text: str) -> str:
    """Detect language using Unicode CJK range."""
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "zh"
    return "en"


def split_sentences(text: str, lang: str) -> list[str]:
    """Split text into sentences, trim and filter length > 2."""
    if lang == "zh":
        parts = re.split(r"[。！？\n]", text)
    else:
        parts = re.split(r"[.!?\n]", text)
    return [s.strip() for s in parts if s.strip() and len(s.strip()) > 2]


def get_prefix(sentence: str, lang: str) -> str:
    """Extract prefix: first word (lowercased) for English, first 2 chars for Chinese."""
    if lang == "zh":
        return sentence[:2]
    words = sentence.split()
    return words[0].lower() if words else ""


def analyze(file_path: str) -> dict:
    """Run dim23 list-like structure detection."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError) as e:
        return {
            "dimension": "dim23",
            "passed": False,
            "error": f"cannot read file: {e}",
        }

    if not content.strip():
        return {
            "dimension": "dim23",
            "passed": True,
            "details": "empty file",
            "maxConsecutive": 0,
        }

    lang = detect_language(content)
    sentences = split_sentences(content, lang)

    if len(sentences) < 3:
        return {
            "dimension": "dim23",
            "passed": True,
            "details": f"fewer than 3 sentences ({len(sentences)})",
            "maxConsecutive": 0,
            "language": lang,
            "patternGroups": [],
        }

    # Extract prefixes for all sentences
    prefixes = [get_prefix(s, lang) for s in sentences]

    # Walk through sentences tracking consecutive same-prefix runs
    consecutive_same_prefix = 1
    max_consecutive = 1
    for i in range(1, len(sentences)):
        if prefixes[i] == prefixes[i - 1]:
            consecutive_same_prefix += 1
            max_consecutive = max(max_consecutive, consecutive_same_prefix)
        else:
            consecutive_same_prefix = 1

    if max_consecutive >= 3:
        # Find all runs of length >= 3
        flagged_passages = []
        pattern_group_map = {}

        run_start = 0
        for i in range(1, len(sentences) + 1):
            if i < len(sentences) and prefixes[i] == prefixes[i - 1]:
                continue
            # End of a run: from run_start to i-1
            run_len = i - run_start
            if run_len >= 3:
                prefix = prefixes[run_start]
                if prefix in pattern_group_map:
                    pattern_group_map[prefix] += run_len
                else:
                    pattern_group_map[prefix] = run_len
                for j in range(run_start, i):
                    sent_text = sentences[j]
                    if len(sent_text) > 60:
                        sent_text = sent_text[:60] + "..."
                    flagged_passages.append({
                        "prefix": prefixes[j],
                        "sentence": sent_text,
                        "line": j + 1,
                    })
            run_start = i

        # Sort pattern groups by count descending
        pattern_groups = sorted(
            [{"prefix": p, "count": c} for p, c in pattern_group_map.items()],
            key=lambda x: x["count"],
            reverse=True,
        )

        details = (
            f"{max_consecutive} consecutive sentences share the same opening pattern"
        )
        return {
            "dimension": "dim23",
            "passed": False,
            "details": details,
            "maxConsecutive": max_consecutive,
            "language": lang,
            "patternGroups": pattern_groups,
            "flaggedPassages": flagged_passages,
        }

    return {
        "dimension": "dim23",
        "passed": True,
        "details": "no 3+ consecutive sentences with same opening",
        "maxConsecutive": max_consecutive,
        "language": lang,
        "patternGroups": [],
        "flaggedPassages": [],
    }


def main():
    if len(sys.argv) < 2:
        json.dump(
            {
                "dimension": "dim23",
                "passed": False,
                "error": "missing or invalid file argument",
            },
            sys.stdout,
        )
        print()
        sys.exit(1)

    file_path = sys.argv[1]
    import os

    if not os.path.isfile(file_path):
        json.dump(
            {
                "dimension": "dim23",
                "passed": False,
                "error": "missing or invalid file argument",
            },
            sys.stdout,
        )
        print()
        sys.exit(1)

    result = analyze(file_path)
    json.dump(result, sys.stdout, ensure_ascii=False)
    print()
    sys.exit(0)


if __name__ == "__main__":
    main()
