#!/usr/bin/env python3
"""dim22-formulaic-transitions.py — Detect AI-tell: formulaic transition repetition.

Detects repeated transition words. Flags if any single transition appears >= 3 times.
Chinese: 然而/不过/与此同时/另一方面/尽管如此/话虽如此/但值得注意的是
English: however/meanwhile/on the other hand/nevertheless/even so/still
Behaviorally equivalent to InkOS core ai-tells.ts dim 22 (lines 96-121).

Usage: ./dim22-formulaic-transitions.py <file-path>
Output: JSON to stdout
"""

import json
import re
import sys

# Transition word lists — must match ai-tells.ts lines 29-31 exactly
TRANSITION_WORDS = {
    "zh": ["然而", "不过", "与此同时", "另一方面", "尽管如此", "话虽如此", "但值得注意的是"],
    "en": ["however", "meanwhile", "on the other hand", "nevertheless", "even so", "still"],
}


def detect_language(text: str) -> str:
    """Detect language based on CJK character presence."""
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "zh"
    return "en"


def count_word(content: str, word: str, language: str) -> int:
    """Count occurrences of a transition word in content.

    English: case-insensitive regex matching (matches ai-tells.ts RegExp with 'gi').
    Chinese: exact substring count.
    """
    if language == "en":
        return len(re.findall(re.escape(word), content, re.IGNORECASE))
    return content.count(word)


def find_passages(content: str, word: str, language: str, max_passages: int = 5):
    """Find line numbers and previews where a flagged word appears."""
    passages = []
    lines = content.split("\n")
    flags = re.IGNORECASE if language == "en" else 0
    pattern = re.compile(re.escape(word), flags)
    word_key = word.lower() if language == "en" else word

    for line_num, line in enumerate(lines, start=1):
        if pattern.search(line):
            preview = line[:80]
            passages.append({
                "line": line_num,
                "word": word_key,
                "preview": preview,
            })
            if len(passages) >= max_passages:
                break

    return passages


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "dimension": "dim22",
            "passed": False,
            "error": "missing or invalid file argument",
        }))
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError) as e:
        print(json.dumps({
            "dimension": "dim22",
            "passed": False,
            "error": f"cannot read file: {e}",
        }))
        sys.exit(1)

    if not content.strip():
        print(json.dumps({
            "dimension": "dim22",
            "passed": True,
            "details": "empty file",
            "transitionCounts": {},
        }))
        sys.exit(0)

    language = detect_language(content)
    is_english = language == "en"
    joiner = ", " if is_english else "\u3001"
    words = TRANSITION_WORDS[language]

    # Step 1: Count all transition words (ai-tells.ts lines 96-103)
    transition_counts = {}
    for word in words:
        count = count_word(content, word, language)
        if count > 0:
            key = word.lower() if is_english else word
            transition_counts[key] = count

    # Step 2: Filter for repeated transitions (count >= 3) (ai-tells.ts lines 104-105)
    repeated_transitions = {
        w: c for w, c in transition_counts.items() if c >= 3
    }

    # Step 3: Determine pass/fail (ai-tells.ts lines 106-120)
    passed = len(repeated_transitions) == 0

    if passed:
        details = "no transition word repeated 3+ times"
        flagged_passages = []
    else:
        detail_parts = [
            f'"{w}"\u00d7{c}' for w, c in repeated_transitions.items()
        ]
        details = f"transitions repeated 3+ times: {joiner.join(detail_parts)}"

        flagged_passages = []
        for word in words:
            key = word.lower() if is_english else word
            if key in repeated_transitions:
                passages = find_passages(content, word, language)
                flagged_passages.extend(passages)

    result = {
        "dimension": "dim22",
        "passed": passed,
        "details": details,
        "language": language,
        "transitionCounts": transition_counts,
        "flaggedTransitions": repeated_transitions,
        "flaggedPassages": flagged_passages,
    }

    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
