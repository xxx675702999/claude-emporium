#!/usr/bin/env python3
"""sensitive-words.py — Detect prohibited words in chapter text (zero LLM calls).

Ships with built-in word lists (political/sexual/violence) that run by default.
An optional custom words file can add project-specific terms.

Usage:
  python3 sensitive-words.py <chapter-file> [custom-words-json]

  custom-words-json (optional): Either a JSON string like
    [{"word": "xxx", "severity": "block"}, {"word": "yyy", "severity": "warn"}]
  or a file path pointing to a JSON file containing such an array.
  If omitted, missing, or empty, only built-in lists are checked.

Output: JSON to stdout
  {"sensitiveWordErrors": [{"word": "...", "severity": "block"|"warn", "line": N, "excerpt": "..."}]}

Exit code: always 0 (errors reported in JSON output).
"""

from __future__ import annotations

import json
import os
import sys


# ---------------------------------------------------------------------------
# Built-in word lists (aligned with inkos sensitive-words.ts)
# ---------------------------------------------------------------------------

# Political terms — severity "block"
POLITICAL_WORDS: list[str] = [
    "习近平", "习主席", "习总书记", "共产党", "中国共产党", "共青团",
    "六四", "天安门事件", "天安门广场事件", "法轮功", "法轮大法",
    "台独", "藏独", "疆独", "港独",
    "新疆集中营", "再教育营",
    "维吾尔", "达赖喇嘛", "达赖",
    "刘晓波", "艾未未", "赵紫阳",
    "文化大革命", "文革", "大跃进",
    "反右运动", "镇压", "六四屠杀",
    "中南海", "政治局常委",
    "翻墙", "防火长城",
]

# Sexual terms — severity "warn"
SEXUAL_WORDS: list[str] = [
    "性交", "做爱", "口交", "肛交", "自慰", "手淫",
    "阴茎", "阴道", "阴蒂", "乳房", "乳头",
    "射精", "高潮", "潮吹",
    "淫荡", "淫乱", "荡妇", "婊子",
    "强奸", "轮奸",
]

# Extreme violence — severity "warn"
VIOLENCE_EXTREME: list[str] = [
    "肢解", "碎尸", "挖眼", "剥皮", "开膛破肚",
    "虐杀", "凌迟", "活剥", "活埋", "烹煮活人",
]

# Assembled built-in list with severity tags
BUILTIN_WORDS: list[dict] = (
    [{"word": w, "severity": "block"} for w in POLITICAL_WORDS]
    + [{"word": w, "severity": "warn"} for w in SEXUAL_WORDS]
    + [{"word": w, "severity": "warn"} for w in VIOLENCE_EXTREME]
)


# ---------------------------------------------------------------------------
# Custom word loading
# ---------------------------------------------------------------------------


def load_custom_words(raw: str) -> list[dict]:
    """Parse custom words from a JSON string or file path.

    Tries inline JSON first, then treats as file path. Returns empty list
    if the input is empty, the file does not exist, or parsing fails.
    """
    if not raw or not raw.strip():
        return []

    # Try inline JSON first
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Try as file path
    if os.path.isfile(raw):
        try:
            with open(raw, "r", encoding="utf-8") as f:
                result = json.load(f)
            if isinstance(result, list):
                return result
            print("Warning: custom-words file is not a JSON array, skipping", file=sys.stderr)
            return []
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            print("Warning: cannot parse custom-words file: %s" % exc, file=sys.stderr)
            return []

    # Neither valid JSON nor existing file
    print("Warning: custom-words not found (not JSON, not a file): %s" % raw[:80], file=sys.stderr)
    return []


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def excerpt_around(line_text: str, match_start: int, word_len: int, radius: int = 20) -> str:
    """Extract a short excerpt around a match position."""
    start = max(0, match_start - radius)
    end = min(len(line_text), match_start + word_len + radius)
    snippet = line_text[start:end].replace("\n", " ")
    if start > 0:
        snippet = "..." + snippet
    if end < len(line_text):
        snippet = snippet + "..."
    return snippet


def find_all_occurrences(text: str, word: str) -> list[int]:
    """Find all start positions of exact matches of word in text."""
    positions: list[int] = []
    start = 0
    while True:
        idx = text.find(word, start)
        if idx < 0:
            break
        positions.append(idx)
        start = idx + 1
    return positions


def check_sensitive_words(lines: list[str], word_list: list[dict]) -> list[dict]:
    """Check each line for prohibited words using exact match."""
    errors: list[dict] = []

    for entry in word_list:
        word = entry.get("word", "")
        severity = entry.get("severity", "warn")
        if not word:
            continue

        for line_num, line in enumerate(lines, start=1):
            positions = find_all_occurrences(line, word)
            for pos in positions:
                errors.append({
                    "word": word,
                    "severity": severity,
                    "line": line_num,
                    "excerpt": excerpt_around(line, pos, len(word)),
                })

    return errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: sensitive-words.py <chapter-file> [custom-words-json]", file=sys.stderr)
        sys.exit(1)

    chapter_path = sys.argv[1]
    custom_raw = sys.argv[2] if len(sys.argv) > 2 else ""

    # Load custom words (additive to built-in)
    custom = load_custom_words(custom_raw)
    all_words = BUILTIN_WORDS + custom

    # Read chapter file
    try:
        with open(chapter_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError):
        result = {"sensitiveWordErrors": [{
            "word": "",
            "severity": "block",
            "line": 0,
            "excerpt": "Cannot read file: %s" % chapter_path,
        }]}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    lines = content.splitlines()
    errors = check_sensitive_words(lines, all_words)

    result = {"sensitiveWordErrors": errors}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
