#!/usr/bin/env python3
"""word-count.py — Language-aware word/character counting for text files.

Counts words, characters, paragraphs, sentences, and reading time
with proper CJK support (fixes macOS BSD grep Unicode bug).

Usage: word-count.py <file> [language]
  language: "zh", "en", or "auto" (default: auto)
Output: JSON to stdout
"""

import json
import math
import re
import sys


def detect_cjk(text: str) -> bool:
    """Detect whether text is predominantly CJK."""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def auto_detect_language(text: str) -> str:
    """Auto-detect language by comparing CJK character count to ASCII letter count."""
    cn_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    en_count = len(re.findall(r"[a-zA-Z]", text))
    return "zh" if cn_count > en_count else "en"


def count_paragraphs(text: str) -> int:
    """Count non-empty lines (lines containing at least one non-whitespace character)."""
    return sum(1 for line in text.splitlines() if line.strip())


def count_sentences(text: str) -> int:
    """Count sentence-ending punctuation marks (English and Chinese)."""
    return len(re.findall(r"[.!?。！？]", text))


def count_zh(text: str) -> tuple:
    """Count Chinese characters and approximate words.

    Returns (characters, words) where:
    - characters = CJK characters excluding whitespace and punctuation
    - words = characters / 2 (approximate)
    """
    stripped = re.sub(r"\s", "", text)
    stripped = re.sub(r"[^\u4e00-\u9fff]", "", stripped)
    chars = len(stripped)
    words = chars // 2
    return chars, words


def count_en(text: str) -> tuple:
    """Count English words and characters.

    Returns (characters, words) where:
    - words = whitespace-delimited token count (matching wc -w behavior)
    - characters = total characters excluding whitespace
    """
    words = len(text.split())
    chars = len(re.sub(r"\s", "", text))
    return chars, words


def compute_reading_time(count: int, rate: int) -> int:
    """Compute reading time in minutes (minimum 1)."""
    minutes = math.ceil(count / rate) if count > 0 else 1
    return max(1, minutes)


def main() -> None:
    if len(sys.argv) < 2:
        print(
            json.dumps({"error": "Usage: word-count.py <file> [language]"}),
            file=sys.stderr,
        )
        sys.exit(1)

    file_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "auto"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError) as exc:
        print(
            json.dumps({"error": "File not found: %s" % file_path}),
            file=sys.stderr,
        )
        sys.exit(1)

    if language == "auto":
        language = auto_detect_language(content)

    paragraphs = count_paragraphs(content)
    sentences = count_sentences(content)

    if language == "zh":
        characters, words = count_zh(content)
        reading_time = compute_reading_time(characters, 500)
    else:
        characters, words = count_en(content)
        reading_time = compute_reading_time(words, 250)

    result = {
        "file": file_path,
        "language": language,
        "characters": characters,
        "words": words,
        "paragraphs": paragraphs,
        "sentences": sentences,
        "readingTime": "%d min" % reading_time,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
