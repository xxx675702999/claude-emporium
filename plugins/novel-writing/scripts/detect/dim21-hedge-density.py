#!/usr/bin/env python3
"""dim21-hedge-density.py — Detect AI-tell: hedge word density.

Counts hedge words per 1000 characters. Flags if density > 3.
Chinese: 似乎/可能/或许/大概/某种程度上/一定程度上/在某种意义上
English: seems/seemed/perhaps/maybe/apparently/in some ways/to some extent
Behaviorally equivalent to InkOS core ai-tells.ts dim 21.

Usage: ./dim21-hedge-density.py <file-path>
Output: JSON to stdout
"""

import json
import re
import sys

# Hedge word lists — MUST match ai-tells.ts lines 23-26 exactly
HEDGE_WORDS = {
    "zh": ["似乎", "可能", "或许", "大概", "某种程度上", "一定程度上", "在某种意义上"],
    "en": ["seems", "seemed", "perhaps", "maybe", "apparently", "in some ways", "to some extent"],
}


def detect_language(text: str) -> str:
    """Detect language using CJK Unicode range (fixes macOS BSD grep bug)."""
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "zh"
    return "en"


def count_hedge_words(content: str, language: str) -> list[dict]:
    """Count occurrences of each hedge word in content.

    English: case-insensitive regex matching.
    Chinese: exact string count.
    """
    results = []
    for word in HEDGE_WORDS[language]:
        if language == "en":
            count = len(re.findall(re.escape(word), content, re.IGNORECASE))
        else:
            count = content.count(word)
        if count > 0:
            results.append({"word": word, "count": count})
    return results


def find_flagged_passages(content: str, language: str, max_passages: int = 5) -> list[dict]:
    """Find lines containing hedge words, up to max_passages."""
    passages = []
    lines = content.splitlines()
    flags = re.IGNORECASE if language == "en" else 0

    for word in HEDGE_WORDS[language]:
        if len(passages) >= max_passages:
            break
        pattern = re.compile(re.escape(word), flags)
        for line_num, line in enumerate(lines, start=1):
            if len(passages) >= max_passages:
                break
            if pattern.search(line):
                preview = line[:80]
                passages.append({
                    "line": line_num,
                    "word": word,
                    "preview": preview,
                })
    return passages


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({
            "dimension": "dim21",
            "passed": False,
            "error": "missing or invalid file argument",
        }))
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, PermissionError, OSError) as e:
        print(json.dumps({
            "dimension": "dim21",
            "passed": False,
            "error": f"cannot read file: {e}",
        }))
        sys.exit(1)

    # Empty file → pass
    if not content.strip():
        print(json.dumps({
            "dimension": "dim21",
            "passed": True,
            "details": "empty file",
            "density": 0,
            "totalChars": 0,
            "totalHedges": 0,
            "language": "en",
            "hedgeWords": [],
            "flaggedPassages": [],
        }))
        sys.exit(0)

    language = detect_language(content)
    total_chars = len(content)

    # Count hedge words
    hedge_results = count_hedge_words(content, language)
    total_hedges = sum(item["count"] for item in hedge_results)

    # Compute density: hedgeCount / (totalChars / 1000)
    density = total_hedges / (total_chars / 1000) if total_chars > 0 else 0.0

    # Threshold: density > 3 flags as AI-tell
    passed = density <= 3

    if passed:
        details = "hedge word density is acceptable"
        flagged_passages: list[dict] = []
    else:
        details = f"hedge word density {density:.1f} per 1k chars exceeds threshold of 3"
        flagged_passages = find_flagged_passages(content, language)

    result = {
        "dimension": "dim21",
        "passed": passed,
        "details": details,
        "density": round(density, 1),
        "totalChars": total_chars,
        "totalHedges": total_hedges,
        "language": language,
        "hedgeWords": hedge_results,
        "flaggedPassages": flagged_passages,
    }

    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
