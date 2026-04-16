#!/usr/bin/env python3
"""dim20-paragraph-uniformity.py — Detect AI-tell: paragraph length uniformity

Measures the coefficient of variation (CV) of paragraph lengths.
Flags if CV < 0.15 across 3+ paragraphs (unnaturally uniform sizing).
Behaviorally equivalent to InkOS core ai-tells.ts dim 20.

Usage: ./dim20-paragraph-uniformity.py <file-path>
Output: JSON to stdout
"""

import json
import math
import re
import sys


def detect_cjk(text: str) -> bool:
    """Detect CJK characters using native Python Unicode comparison."""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({
            "dimension": "dim20",
            "passed": False,
            "error": "missing or invalid file argument",
        }))
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError):
        print(json.dumps({
            "dimension": "dim20",
            "passed": False,
            "error": "missing or invalid file argument",
        }))
        sys.exit(1)

    if not content.strip():
        print(json.dumps({
            "dimension": "dim20",
            "passed": True,
            "details": "empty file",
            "cv": 0,
            "paragraphCount": 0,
        }))
        sys.exit(0)

    is_cjk = detect_cjk(content)

    # Split on blank lines (matching ai-tells.ts: /\n\s*\n/)
    raw_paragraphs = re.split(r"\n\s*\n", content)
    paragraphs = [p.strip() for p in raw_paragraphs]
    paragraphs = [p for p in paragraphs if len(p) > 0]

    para_count = len(paragraphs)

    if para_count < 3:
        print(json.dumps({
            "dimension": "dim20",
            "passed": True,
            "details": "fewer than 3 paragraphs (%d)" % para_count,
            "cv": 0,
            "paragraphCount": para_count,
        }))
        sys.exit(0)

    # Compute paragraph lengths (character count, matching JS .length)
    lengths = [len(p) for p in paragraphs]

    mean_length = sum(lengths) / len(lengths)

    if mean_length == 0:
        print(json.dumps({
            "dimension": "dim20",
            "passed": True,
            "details": "zero mean length",
            "cv": 0,
            "paragraphCount": para_count,
        }))
        sys.exit(0)

    # Population variance (not sample)
    variance = sum((l - mean_length) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean_length

    passed = cv >= 0.15

    if passed:
        details = "paragraph lengths are varied enough"
        flagged_passages = []
    else:
        details = "CV %.6f is below 0.15 threshold, paragraphs are unnaturally uniform" % cv
        flagged_passages = []
        for i, p in enumerate(paragraphs):
            preview = p[:40]
            if len(p) > 40:
                preview += "..."
            flagged_passages.append({
                "length": lengths[i],
                "preview": preview,
            })

    # Format numeric fields to match shell script precision
    result = {
        "dimension": "dim20",
        "passed": passed,
        "details": details,
        "cv": float("%.6f" % cv),
        "meanLength": float("%.1f" % mean_length),
        "stdDev": float("%.6f" % std_dev),
        "paragraphCount": para_count,
        "flaggedPassages": flagged_passages,
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
