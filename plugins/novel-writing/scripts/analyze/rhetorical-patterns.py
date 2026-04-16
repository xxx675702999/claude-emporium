#!/usr/bin/env python3
"""rhetorical-patterns.py — Rhetorical device pattern analysis

Detects rhetorical devices in text: metaphor, parallelism,
rhetorical questions, hyperbole, personification, and short rhythm.
Has separate logic for Chinese and English texts.

Usage: ./rhetorical-patterns.py <file-path>
Output: JSON to stdout
"""

import json
import re
import sys


def detect_cjk(text: str) -> bool:
    """Detect CJK characters using native Python Unicode comparison."""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def find_matches(text: str, pattern: str, context: int = 15) -> tuple:
    """Find pattern matches and return (count, examples with context)."""
    regex = re.compile(pattern)
    matches = list(regex.finditer(text))
    count = len(matches)
    examples = []
    for m in matches[:3]:
        start = max(0, m.start() - context)
        end = min(len(text), m.end() + context)
        examples.append(text[start:end])
    return count, examples


def find_matches_simple(text: str, pattern: str, context: int = 20) -> tuple:
    """Find pattern matches using findall, extract examples with surrounding context."""
    regex = re.compile(pattern, re.IGNORECASE)
    all_matches = list(regex.finditer(text))
    count = len(all_matches)
    examples = []
    for m in all_matches[:3]:
        start = max(0, m.start() - context)
        end = min(len(text), m.end() + context)
        examples.append(text[start:end])
    return count, examples


def analyze_chinese(content: str) -> dict:
    """Analyze rhetorical devices in Chinese text."""
    # Metaphors (像/如/仿佛/似)
    metaphor_count, metaphor_ex = find_matches(
        content, r"[像如仿佛似](?:是|同|一般|一样)"
    )

    # Parallelism (repeated structures)
    parallelism_count, parallelism_ex = find_matches(
        content, r"[，。；]([^，。；]{2,6})[，。；]\1", context=20
    )

    # Rhetorical questions
    rq_count, rq_ex = find_matches(
        content, r"难道|怎么可能|岂不是|何尝不"
    )

    # Hyperbole
    hyp_count, hyp_ex = find_matches(
        content, r"天崩地裂|惊天动地|翻天覆地|震耳欲聋"
    )

    # Personification
    pers_count, pers_ex = find_matches(
        content, r"[风雨雪月花树草石](?:在|像|仿佛).*?(?:笑|哭|叹|呻|吟|怒|舞)", context=10
    )

    # Short sentence rhythm (consecutive sentences < 8 chars)
    sr_count, sr_ex = find_matches(
        content, r"[。！？][^。！？]{1,8}[。！？]"
    )

    return {
        "metaphor": {"count": metaphor_count, "examples": metaphor_ex},
        "parallelism": {"count": parallelism_count, "examples": parallelism_ex},
        "rhetoricalQuestion": {"count": rq_count, "examples": rq_ex},
        "hyperbole": {"count": hyp_count, "examples": hyp_ex},
        "personification": {"count": pers_count, "examples": pers_ex},
        "shortRhythm": {"count": sr_count, "examples": sr_ex},
    }


def analyze_english(content: str) -> dict:
    """Analyze rhetorical devices in English text."""
    # Similes (like/as)
    metaphor_count, metaphor_ex = find_matches_simple(
        content, r"\b(?:like|as)\s+\w+"
    )

    # Parallelism (hard to detect with regex in English, keep at 0)
    parallelism_count = 0
    parallelism_ex = []

    # Rhetorical questions
    rq_count, rq_ex = find_matches_simple(
        content, r"\b(?:how could|why would|isn't it|don't you)\b.*?\?"
    )

    # Hyperbole
    hyp_count, hyp_ex = find_matches_simple(
        content, r"\b(?:never|always|forever|impossible|unbelievable|incredible)\b"
    )

    # Personification (hard to detect with regex in English, keep at 0)
    personification_count = 0
    personification_ex = []

    # Short sentence rhythm (< 5 words)
    sr_matches = re.finditer(r"[.!?]\s*([A-Z][^.!?]{1,30}[.!?])", content)
    sr_count = 0
    sr_ex = []
    for m in sr_matches:
        sentence = m.group(1)
        if len(sentence.split()) <= 5:
            sr_count += 1
            if len(sr_ex) < 3:
                sr_ex.append(m.group(0))

    return {
        "metaphor": {"count": metaphor_count, "examples": metaphor_ex},
        "parallelism": {"count": parallelism_count, "examples": parallelism_ex},
        "rhetoricalQuestion": {"count": rq_count, "examples": rq_ex},
        "hyperbole": {"count": hyp_count, "examples": hyp_ex},
        "personification": {"count": personification_count, "examples": personification_ex},
        "shortRhythm": {"count": sr_count, "examples": sr_ex},
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: rhetorical-patterns.py <file_path>"}), file=sys.stderr)
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

    if is_cjk:
        devices = analyze_chinese(content)
    else:
        devices = analyze_english(content)

    result = {
        "language": lang,
        "devices": devices,
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
