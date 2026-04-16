#!/usr/bin/env python3
"""fatigue-detector.py — Long-span structural fatigue detection.

Analyzes the last N chapters for repetitive patterns that signal
structural fatigue: similar openings/endings, pacing monotony,
sustained high tension, and title keyword collapse.

All warnings are advisory — they never block the pipeline.

Usage:
  python3 fatigue-detector.py <chapters-dir> <current-chapter-num> \
      [--window N] [--language zh|en]
"""

import argparse
import glob
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Chapter file discovery
# ---------------------------------------------------------------------------

def find_chapter_file(chapters_dir: str, chapter_num: int) -> str | None:
    """Find a chapter file by zero-padded number prefix.

    Looks for {XXXX}_{title}.md first, then chapter-XXXX.md as fallback.
    """
    padded = "%04d" % chapter_num
    pattern = os.path.join(chapters_dir, "%s_*.md" % padded)
    matches = glob.glob(pattern)
    if matches:
        return sorted(matches)[0]
    fallback = os.path.join(chapters_dir, "chapter-%s.md" % padded)
    if os.path.isfile(fallback):
        return fallback
    return None


def collect_chapters(chapters_dir: str, current_chapter: int, window: int) -> list[dict]:
    """Collect chapter metadata and content for the analysis window.

    Returns list of dicts with keys: num, path, title, text.
    """
    end = current_chapter - 1  # exclude the chapter being written
    start = max(1, end - window + 1)

    chapters = []
    for num in range(start, end + 1):
        path = find_chapter_file(chapters_dir, num)
        if path is None:
            continue
        title = extract_title_from_filename(os.path.basename(path))
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except (OSError, IOError):
            continue
        # Strip markdown heading
        text = re.sub(r"^#\s+.*?\n", "", text, count=1).strip()
        chapters.append({"num": num, "path": path, "title": title, "text": text})

    return chapters


def extract_title_from_filename(filename: str) -> str:
    """Extract the title portion from a chapter filename.

    For '0003_The_Dark_Tower.md' returns 'The_Dark_Tower'.
    For 'chapter-0003.md' returns ''.
    """
    name = os.path.splitext(filename)[0]
    m = re.match(r"^\d{4}_(.*)", name)
    if m:
        return m.group(1)
    return ""


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def first_sentence(text: str, language: str) -> str:
    """Extract the first sentence from text."""
    if not text:
        return ""
    if language == "zh":
        m = re.search(r"^(.*?[。！？\n])", text, re.DOTALL)
    else:
        m = re.search(r"^(.*?[.!?\n])", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # No sentence-ending punctuation found — return first 100 chars
    return text[:100].strip()


def last_sentence(text: str, language: str) -> str:
    """Extract the last sentence from text."""
    if not text:
        return ""
    if language == "zh":
        sentences = re.split(r"(?<=[。！？])", text)
    else:
        sentences = re.split(r"(?<=[.!?])\s+", text)
    # Filter empty strings
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        return sentences[-1]
    return text[-100:].strip()


# ---------------------------------------------------------------------------
# (a) Opening/Ending Similarity — Dice coefficient on bigrams
# ---------------------------------------------------------------------------

def char_bigrams(text: str) -> set[str]:
    """Character bigrams for Chinese text."""
    text = re.sub(r"\s+", "", text)
    if len(text) < 2:
        return set()
    return {text[i:i + 2] for i in range(len(text) - 1)}


def word_bigrams(text: str) -> set[str]:
    """Word bigrams for English text."""
    words = text.lower().split()
    if len(words) < 2:
        return set()
    return {"%s %s" % (words[i], words[i + 1]) for i in range(len(words) - 1)}


def dice_coefficient(set_a: set, set_b: set) -> float:
    """Compute Dice coefficient between two sets."""
    if not set_a or not set_b:
        return 0.0
    return 2 * len(set_a & set_b) / (len(set_a) + len(set_b))


def bigrams_for(text: str, language: str) -> set[str]:
    """Get bigrams appropriate for the language."""
    if language == "zh":
        return char_bigrams(text)
    return word_bigrams(text)


def detect_opening_ending_similarity(chapters: list[dict], language: str, threshold: float = 0.4) -> list[dict]:
    """Detect similar consecutive openings and endings via Dice coefficient."""
    warnings = []

    for i in range(len(chapters) - 1):
        ch_a = chapters[i]
        ch_b = chapters[i + 1]

        # Openings
        open_a = first_sentence(ch_a["text"], language)
        open_b = first_sentence(ch_b["text"], language)
        bg_a = bigrams_for(open_a, language)
        bg_b = bigrams_for(open_b, language)
        score = dice_coefficient(bg_a, bg_b)
        if score > threshold:
            warnings.append({
                "type": "opening_similarity",
                "severity": "advisory",
                "chapters": [ch_a["num"], ch_b["num"]],
                "detail": "Chapters %d and %d have similar openings (Dice=%.2f). Vary the opening structure." % (
                    ch_a["num"], ch_b["num"], score
                ),
            })

        # Endings
        end_a = last_sentence(ch_a["text"], language)
        end_b = last_sentence(ch_b["text"], language)
        bg_a = bigrams_for(end_a, language)
        bg_b = bigrams_for(end_b, language)
        score = dice_coefficient(bg_a, bg_b)
        if score > threshold:
            warnings.append({
                "type": "ending_similarity",
                "severity": "advisory",
                "chapters": [ch_a["num"], ch_b["num"]],
                "detail": "Chapters %d and %d have similar endings (Dice=%.2f). Vary the closing structure." % (
                    ch_a["num"], ch_b["num"], score
                ),
            })

    return warnings


# ---------------------------------------------------------------------------
# (b) Consecutive Chapter Type Repetition (pacing monotony)
# ---------------------------------------------------------------------------

# Marker patterns for chapter type classification
_TYPE_MARKERS = {
    "action": {
        "zh": re.compile(r"[砍刺劈斩挡闪冲杀击打攻防拳掌剑刀枪矛]|战斗|冲突|打斗|追逐|爆炸"),
        "en": re.compile(r"\b(fight|battle|attack|slash|dodge|punch|kick|clash|charge|explode|sword|blade)\b", re.I),
    },
    "dialogue": {
        "zh": re.compile(r"[""「」『』]"),
        "en": re.compile(r'["""\u201c\u201d]'),
    },
    "reflection": {
        "zh": re.compile(r"想到|回忆|沉思|心想|思索|意识到|明白|领悟|感到|感觉"),
        "en": re.compile(r"\b(thought|remember|realize|reflect|ponder|wonder|felt|sense|mind|memory)\b", re.I),
    },
    "transition": {
        "zh": re.compile(r"第[二三]天|次日|翌日|过了|几天后|一周后|不久|随后|离开|出发|前往|抵达"),
        "en": re.compile(r"\b(next day|days later|weeks later|arrived|departed|traveled|journey|moved on)\b", re.I),
    },
}


def classify_chapter_type(text: str, language: str) -> str:
    """Classify chapter type based on content marker density."""
    scores = {}
    for ctype, patterns in _TYPE_MARKERS.items():
        pattern = patterns.get(language, patterns.get("en"))
        if pattern is None:
            continue
        matches = pattern.findall(text)
        scores[ctype] = len(matches)

    if not scores or max(scores.values()) == 0:
        return "mixed"

    return max(scores, key=scores.get)


def detect_pacing_monotony(chapters: list[dict], language: str, run_length: int = 3) -> list[dict]:
    """Flag if run_length+ consecutive chapters share the same type."""
    warnings = []
    if len(chapters) < run_length:
        return warnings

    types = [(ch["num"], classify_chapter_type(ch["text"], language)) for ch in chapters]

    # Find consecutive runs
    run_start = 0
    while run_start < len(types):
        run_end = run_start + 1
        while run_end < len(types) and types[run_end][1] == types[run_start][1]:
            run_end += 1
        run_len = run_end - run_start
        if run_len >= run_length and types[run_start][1] != "mixed":
            ch_nums = [types[i][0] for i in range(run_start, run_end)]
            repeated_type = types[run_start][1]
            warnings.append({
                "type": "pacing_monotony",
                "severity": "advisory",
                "chapters": ch_nums,
                "detail": "%d consecutive chapters (%s) are classified as '%s'. Vary the pacing." % (
                    run_len,
                    ", ".join(str(n) for n in ch_nums),
                    repeated_type,
                ),
            })
        run_start = run_end

    return warnings


# ---------------------------------------------------------------------------
# (c) Sustained High-Tension Mood (emotional monotony)
# ---------------------------------------------------------------------------

def compute_tension_score(text: str, language: str) -> float:
    """Compute a tension score (0-1) from content markers.

    Markers: exclamation density, short sentence ratio, action verbs.
    """
    if not text:
        return 0.0

    scores = []

    # Exclamation density
    if language == "zh":
        sentence_endings = len(re.findall(r"[。！？]", text)) or 1
        exclamations = len(re.findall(r"[！]", text))
    else:
        sentence_endings = len(re.findall(r"[.!?]", text)) or 1
        exclamations = len(re.findall(r"!", text))
    excl_ratio = exclamations / sentence_endings
    scores.append(min(excl_ratio / 0.3, 1.0))  # 30%+ exclamations = max

    # Short sentence ratio
    if language == "zh":
        sentences = re.split(r"[。！？]", text)
    else:
        sentences = re.split(r"[.!?]\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        if language == "zh":
            short_count = sum(1 for s in sentences if len(re.sub(r"\s", "", s)) <= 10)
        else:
            short_count = sum(1 for s in sentences if len(s.split()) <= 6)
        short_ratio = short_count / len(sentences)
        scores.append(min(short_ratio / 0.4, 1.0))  # 40%+ short = max
    else:
        scores.append(0.0)

    # Action verb density
    action_pattern = _TYPE_MARKERS["action"].get(language, _TYPE_MARKERS["action"]["en"])
    action_count = len(action_pattern.findall(text))
    word_count = len(text.split()) if language == "en" else len(re.sub(r"\s", "", text))
    if word_count > 0:
        action_density = action_count / (word_count / 100)  # per 100 tokens
        scores.append(min(action_density / 3.0, 1.0))  # 3+ per 100 tokens = max
    else:
        scores.append(0.0)

    return sum(scores) / len(scores)


def detect_sustained_tension(chapters: list[dict], language: str, run_length: int = 3, threshold: float = 0.5) -> list[dict]:
    """Flag if run_length+ consecutive chapters show high tension."""
    warnings = []
    if len(chapters) < run_length:
        return warnings

    tension_scores = [(ch["num"], compute_tension_score(ch["text"], language)) for ch in chapters]

    # Find consecutive high-tension runs
    run_start = 0
    while run_start < len(tension_scores):
        if tension_scores[run_start][1] < threshold:
            run_start += 1
            continue
        run_end = run_start + 1
        while run_end < len(tension_scores) and tension_scores[run_end][1] >= threshold:
            run_end += 1
        run_len = run_end - run_start
        if run_len >= run_length:
            ch_nums = [tension_scores[i][0] for i in range(run_start, run_end)]
            warnings.append({
                "type": "sustained_tension",
                "severity": "advisory",
                "chapters": ch_nums,
                "detail": "%d consecutive chapters (%s) show high tension. Insert a quieter scene for breathing room." % (
                    run_len,
                    ", ".join(str(n) for n in ch_nums),
                ),
            })
        run_start = run_end

    return warnings


# ---------------------------------------------------------------------------
# (d) Title Keyword Collapse
# ---------------------------------------------------------------------------

def extract_title_keywords_zh(title: str) -> list[str]:
    """Extract 2+ character keywords from a Chinese title."""
    # Remove underscores and digits, split on punctuation
    title = re.sub(r"[_\d]", "", title)
    # Extract sequences of 2+ CJK characters
    return re.findall(r"[\u4e00-\u9fff]{2,}", title)


def extract_title_keywords_en(title: str) -> list[str]:
    """Extract meaningful words from an English title (lowercased)."""
    # Replace underscores with spaces
    title = title.replace("_", " ")
    words = title.lower().split()
    # Filter out short/common words
    stopwords = {"the", "a", "an", "of", "in", "on", "at", "to", "and", "or", "is", "was", "for", "with", "by"}
    return [w for w in words if len(w) >= 3 and w not in stopwords]


def detect_title_keyword_collapse(chapters: list[dict], language: str, threshold: int = 3) -> list[dict]:
    """Flag if threshold+ chapters share a keyword in their titles."""
    warnings = []

    keyword_chapters: dict[str, list[int]] = {}
    for ch in chapters:
        title = ch["title"]
        if not title:
            continue
        if language == "zh":
            keywords = extract_title_keywords_zh(title)
        else:
            keywords = extract_title_keywords_en(title)
        # Deduplicate per chapter
        for kw in set(keywords):
            if kw not in keyword_chapters:
                keyword_chapters[kw] = []
            keyword_chapters[kw].append(ch["num"])

    for kw, ch_nums in keyword_chapters.items():
        if len(ch_nums) >= threshold:
            warnings.append({
                "type": "title_keyword_collapse",
                "severity": "advisory",
                "chapters": sorted(ch_nums),
                "detail": "Keyword '%s' appears in %d chapter titles (%s). Choose a fresh image or focus." % (
                    kw,
                    len(ch_nums),
                    ", ".join(str(n) for n in sorted(ch_nums)),
                ),
            })

    return warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect long-span structural fatigue across recent chapters."
    )
    parser.add_argument("chapters_dir", help="Path to the chapters directory")
    parser.add_argument("current_chapter_num", type=int, help="Current chapter number being written")
    parser.add_argument("--window", type=int, default=5, help="Number of recent chapters to analyze (default: 5)")
    parser.add_argument("--language", choices=["zh", "en"], default="zh", help="Book language (default: zh)")
    args = parser.parse_args()

    try:
        chapters = collect_chapters(args.chapters_dir, args.current_chapter_num, args.window)

        if not chapters:
            print(json.dumps({"fatigueWarnings": []}, indent=2))
            return

        warnings = []
        warnings.extend(detect_opening_ending_similarity(chapters, args.language))
        warnings.extend(detect_pacing_monotony(chapters, args.language))
        warnings.extend(detect_sustained_tension(chapters, args.language))
        warnings.extend(detect_title_keyword_collapse(chapters, args.language))

        print(json.dumps({"fatigueWarnings": warnings}, indent=2, ensure_ascii=False))

    except Exception as exc:
        # Always exit 0 — warnings are advisory, never blocking
        print(json.dumps({
            "fatigueWarnings": [],
            "error": "Fatigue detection failed: %s" % str(exc),
        }, indent=2, ensure_ascii=False), file=sys.stdout)


if __name__ == "__main__":
    sys.exit(main() or 0)
