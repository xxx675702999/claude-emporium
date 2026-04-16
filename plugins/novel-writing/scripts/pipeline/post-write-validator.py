#!/usr/bin/env python3
"""post-write-validator.py — Deterministic post-write validation (zero LLM calls).

Checks chapter text against language-specific rules and optional book-rules
prohibitions. All checks are pure regex/string matching.

Title rules (both languages):
  - Chinese title must have >= 3 CJK characters (block)
  - English title must have >= 2 words (block)

Chinese rules (language=zh):
  - "不是…而是" negative-then-positive structure
  - Meta-narrative phrases: 到这里算是, 接下来就是, 故事进入, 下面我们, 笔者认为
  - Collective reaction phrases: 众人皆, 所有人都, 全场, 无不
  - Didactic words: 显然, 毋庸置疑, 不言而喻, 众所周知, 理所当然
  - Paragraph length > 500 characters

English rules (language=en):
  - Paragraph length > 300 words

Both languages:
  - Book-specific prohibitions from book_rules file (if provided)

Usage:
  python3 post-write-validator.py <chapter-file> <language> [book-rules-file]

Output: JSON to stdout
  {"postWriteErrors": [{"rule": "...", "severity": "warn"|"block", "line": N, "excerpt": "..."}]}

Exit code: always 0 (errors reported in JSON output).
"""

import json
import re
import sys


# -- Chinese pattern definitions --

ZH_NEGATIVE_POSITIVE = re.compile(r"不是[^。！？\n]{1,30}而是")

ZH_META_NARRATIVE = [
    "到这里算是",
    "接下来就是",
    "故事进入",
    "下面我们",
    "笔者认为",
]

ZH_COLLECTIVE_REACTION = [
    "众人皆",
    "所有人都",
    "全场",
    "无不",
]

ZH_DIDACTIC = [
    "显然",
    "毋庸置疑",
    "不言而喻",
    "众所周知",
    "理所当然",
]

ZH_PARAGRAPH_CHAR_LIMIT = 500
ZH_TITLE_MIN_LENGTH = 3
EN_PARAGRAPH_WORD_LIMIT = 300
EN_TITLE_MIN_WORDS = 2

TITLE_HEADING_RE = re.compile(r"^#\s+Chapter\s+\d+\s*:\s*(.+)$")


def read_file(path: str) -> str:
    """Read a UTF-8 file and return its content."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def excerpt_around(line_text: str, match_start: int, radius: int = 20) -> str:
    """Extract a short excerpt around a match position."""
    start = max(0, match_start - radius)
    end = min(len(line_text), match_start + radius + 10)
    snippet = line_text[start:end].replace("\n", " ")
    if start > 0:
        snippet = "..." + snippet
    if end < len(line_text):
        snippet = snippet + "..."
    return snippet


def check_zh_patterns(lines: list[str]) -> list[dict]:
    """Run all Chinese-specific pattern checks."""
    errors = []

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue

        # "不是…而是" pattern
        for m in ZH_NEGATIVE_POSITIVE.finditer(stripped):
            errors.append({
                "rule": "zh-negative-positive",
                "severity": "warn",
                "line": line_num,
                "excerpt": excerpt_around(stripped, m.start()),
            })

        # Meta-narrative phrases
        for phrase in ZH_META_NARRATIVE:
            idx = stripped.find(phrase)
            if idx >= 0:
                errors.append({
                    "rule": "zh-meta-narrative",
                    "severity": "warn",
                    "line": line_num,
                    "excerpt": excerpt_around(stripped, idx),
                })

        # Collective reaction phrases
        for phrase in ZH_COLLECTIVE_REACTION:
            idx = stripped.find(phrase)
            if idx >= 0:
                errors.append({
                    "rule": "zh-collective-reaction",
                    "severity": "warn",
                    "line": line_num,
                    "excerpt": excerpt_around(stripped, idx),
                })

        # Didactic words
        for phrase in ZH_DIDACTIC:
            idx = stripped.find(phrase)
            if idx >= 0:
                errors.append({
                    "rule": "zh-didactic",
                    "severity": "warn",
                    "line": line_num,
                    "excerpt": excerpt_around(stripped, idx),
                })

    return errors


def check_paragraph_length_zh(lines: list[str]) -> list[dict]:
    """Check paragraph length for Chinese text (character count)."""
    errors = []
    para_start = None
    para_chars = 0

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            # End of paragraph
            if para_start is not None and para_chars > ZH_PARAGRAPH_CHAR_LIMIT:
                errors.append({
                    "rule": "zh-paragraph-length",
                    "severity": "warn",
                    "line": para_start,
                    "excerpt": "Paragraph starting at line %d has %d characters (limit: %d)"
                        % (para_start, para_chars, ZH_PARAGRAPH_CHAR_LIMIT),
                })
            para_start = None
            para_chars = 0
        else:
            if para_start is None:
                para_start = line_num
            para_chars += len(stripped)

    # Handle last paragraph (no trailing blank line)
    if para_start is not None and para_chars > ZH_PARAGRAPH_CHAR_LIMIT:
        errors.append({
            "rule": "zh-paragraph-length",
            "severity": "warn",
            "line": para_start,
            "excerpt": "Paragraph starting at line %d has %d characters (limit: %d)"
                % (para_start, para_chars, ZH_PARAGRAPH_CHAR_LIMIT),
        })

    return errors


def check_paragraph_length_en(lines: list[str]) -> list[dict]:
    """Check paragraph length for English text (word count)."""
    errors = []
    para_start = None
    para_words = 0

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            if para_start is not None and para_words > EN_PARAGRAPH_WORD_LIMIT:
                errors.append({
                    "rule": "en-paragraph-length",
                    "severity": "warn",
                    "line": para_start,
                    "excerpt": "Paragraph starting at line %d has %d words (limit: %d)"
                        % (para_start, para_words, EN_PARAGRAPH_WORD_LIMIT),
                })
            para_start = None
            para_words = 0
        else:
            if para_start is None:
                para_start = line_num
            para_words += len(stripped.split())

    if para_start is not None and para_words > EN_PARAGRAPH_WORD_LIMIT:
        errors.append({
            "rule": "en-paragraph-length",
            "severity": "warn",
            "line": para_start,
            "excerpt": "Paragraph starting at line %d has %d words (limit: %d)"
                % (para_start, para_words, EN_PARAGRAPH_WORD_LIMIT),
        })

    return errors


def load_book_rules(rules_path: str) -> list[dict]:
    """Load book-specific prohibitions from a book_rules markdown file.

    Expected format in the markdown: a JSON code block containing an array of
    {"pattern": "...", "severity": "warn"|"block", "rule": "..."} objects,
    or a simpler structure where each prohibition is a line like:
      - BLOCK: <pattern> — <description>
      - WARN: <pattern> — <description>

    Returns list of {"pattern": str, "severity": str, "rule": str}.
    """
    content = read_file(rules_path)
    prohibitions = []

    # Try JSON block first
    json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "pattern" in item:
                        prohibitions.append({
                            "pattern": item["pattern"],
                            "severity": item.get("severity", "warn"),
                            "rule": item.get("rule", "book-rule-custom"),
                        })
                return prohibitions
        except json.JSONDecodeError:
            pass

    # Try markdown list format: - BLOCK: pattern — description
    for line in content.splitlines():
        m = re.match(
            r"^\s*[-*]\s*(BLOCK|WARN|block|warn)\s*:\s*(.+?)(?:\s*[—\-]\s*(.*))?$",
            line,
        )
        if m:
            severity = m.group(1).lower()
            pattern = m.group(2).strip()
            desc = m.group(3).strip() if m.group(3) else ""
            prohibitions.append({
                "pattern": pattern,
                "severity": severity,
                "rule": "book-rule: %s" % (desc or pattern),
            })

    return prohibitions


def check_book_rules(lines: list[str], prohibitions: list[dict]) -> list[dict]:
    """Check chapter text against book-specific prohibition patterns."""
    errors = []

    for prohibition in prohibitions:
        pattern_str = prohibition["pattern"]
        severity = prohibition.get("severity", "warn")
        rule_name = prohibition.get("rule", "book-rule-custom")

        try:
            compiled = re.compile(pattern_str)
        except re.error:
            # Fall back to literal match if pattern is not valid regex
            compiled = None

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            if compiled is not None:
                m = compiled.search(stripped)
                if m:
                    errors.append({
                        "rule": rule_name,
                        "severity": severity,
                        "line": line_num,
                        "excerpt": excerpt_around(stripped, m.start()),
                    })
            else:
                idx = stripped.find(pattern_str)
                if idx >= 0:
                    errors.append({
                        "rule": rule_name,
                        "severity": severity,
                        "line": line_num,
                        "excerpt": excerpt_around(stripped, idx),
                    })

    return errors


def check_title_length(lines: list[str], language: str) -> list[dict]:
    """Check chapter title length from the first heading line."""
    errors = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        m = TITLE_HEADING_RE.match(stripped)
        if m:
            title = m.group(1).strip()
            if language == "zh":
                cjk_count = sum(1 for ch in title if "\u4e00" <= ch <= "\u9fff")
                if cjk_count < ZH_TITLE_MIN_LENGTH:
                    errors.append({
                        "rule": "zh-title-too-short",
                        "severity": "block",
                        "line": 1,
                        "excerpt": "Title '%s' has only %d CJK characters (minimum: %d). Chinese titles MUST be 3-6 characters." % (title, cjk_count, ZH_TITLE_MIN_LENGTH),
                    })
            elif language == "en":
                word_count = len(title.split())
                if word_count < EN_TITLE_MIN_WORDS:
                    errors.append({
                        "rule": "en-title-too-short",
                        "severity": "block",
                        "line": 1,
                        "excerpt": "Title '%s' has only %d word(s) (minimum: %d). English titles MUST be 2-6 words." % (title, word_count, EN_TITLE_MIN_WORDS),
                    })
        break  # only check the first heading
    return errors


def main() -> None:
    if len(sys.argv) < 3:
        print(
            json.dumps({
                "error": "Usage: post-write-validator.py <chapter-file> <language> [book-rules-file]"
            }),
            file=sys.stderr,
        )
        sys.exit(0)

    chapter_path = sys.argv[1]
    language = sys.argv[2].lower()
    rules_path = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        content = read_file(chapter_path)
    except (OSError, IOError):
        result = {"postWriteErrors": [{
            "rule": "file-read-error",
            "severity": "block",
            "line": 0,
            "excerpt": "Cannot read file: %s" % chapter_path,
        }]}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    lines = content.splitlines()
    errors = []

    errors.extend(check_title_length(lines, language))

    if language == "zh":
        errors.extend(check_zh_patterns(lines))
        errors.extend(check_paragraph_length_zh(lines))
    elif language == "en":
        errors.extend(check_paragraph_length_en(lines))

    # Book-specific rules (both languages)
    if rules_path:
        try:
            prohibitions = load_book_rules(rules_path)
            errors.extend(check_book_rules(lines, prohibitions))
        except (OSError, IOError):
            errors.append({
                "rule": "book-rules-read-error",
                "severity": "warn",
                "line": 0,
                "excerpt": "Cannot read book rules file: %s" % rules_path,
            })

    result = {"postWriteErrors": errors}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
