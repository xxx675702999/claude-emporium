#!/usr/bin/env python3
"""aigc-heuristics.py -- Heuristic AI pattern detection (7 patterns)

Detects AI-generation heuristics beyond deterministic checks:
1. Repetitive sentence structures
2. Unnatural emotional escalation
3. Excessive summarization
4. Lack of sensory detail
5. Uniform paragraph rhythm
6. Missing character voice differentiation
7. Formulaic chapter openings/endings

Usage: ./aigc-heuristics.py <file-path>
Output: JSON to stdout
"""
import json, math, re, sys
from collections import Counter

def is_chinese(text):
    return any('\u4e00' <= ch <= '\u9fff' for ch in text)

def heuristic(score, flagged, examples):
    return {"score": score, "flagged": flagged, "examples": examples}

# 1. Repetitive sentence structures
def detect_repetitive_structures(content, lang):
    splitter = re.split(r'[。！？]', content) if lang == "zh" else re.split(r'[.!?]', content)
    sentences = [s.strip() for s in splitter if s.strip()]
    total = len(sentences)
    if total < 3:
        return heuristic(0, False, [])
    if lang == "zh":
        prefixes = [s[:2] for s in sentences if len(s) >= 2]
    else:
        prefixes = [s.split()[0].lower() for s in sentences if s.split()]
    counts = Counter(prefixes)
    prefix, max_repeat = counts.most_common(1)[0]
    ratio = max_repeat / total
    score = round(ratio * 100)
    flagged = max_repeat >= 3 and ratio > 0.3
    return heuristic(score, flagged, [f"{prefix} repeated {max_repeat} times"])

# 2. Unnatural emotional escalation
def detect_emotional_escalation(content, lang):
    if lang == "zh":
        words = r'高兴|兴奋|狂喜|愤怒|暴怒|悲伤|绝望|害怕|恐惧|惊恐'
    else:
        words = r'happy|excited|ecstatic|angry|furious|sad|depressed|scared|terrified|horrified'
    matches = len(re.findall(words, content, re.IGNORECASE))
    total_chars = len(content)
    if total_chars == 0:
        return heuristic(0, False, [])
    density = matches / (total_chars / 1000)
    score = round(min(density / 5, 1) * 100)
    flagged = density > 5
    return heuristic(score, flagged, [f"emotion density: {density:.1f} per 1k chars"])

# 3. Excessive summarization
def detect_excessive_summarization(content, lang):
    if lang == "zh":
        abstract = r'感觉|似乎|显然|明显|清楚|理解|意识到|发现|注意到|决定'
    else:
        abstract = r'feel|felt|seem|obvious|clear|understand|realize|notice|decide|thought'
    abstract_count = len(re.findall(abstract, content, re.IGNORECASE))
    if lang == "zh":
        word_count = len(re.findall(r'[\u4e00-\u9fff]{2,}', content))
    else:
        word_count = len([w for w in re.findall(r'[A-Za-z]+', content) if 3 <= len(w) <= 8])
    if word_count == 0:
        return heuristic(0, False, [])
    ratio = abstract_count / word_count
    score = round(min(ratio / 0.15, 1) * 100)
    flagged = ratio > 0.15
    return heuristic(score, flagged, [f"abstract/concrete ratio: {ratio:.2f}"])

# 4. Lack of sensory detail
def detect_lack_sensory(content, lang):
    if lang == "zh":
        words = r'看到|看见|听到|听见|闻到|感觉到|触摸|尝到|味道|声音|气味|温度|颜色|光线'
    else:
        words = r'saw|see|heard|hear|smelled|smell|felt|feel|touched|touch|tasted|taste|sound|scent|warm|cold|color|light'
    sensory_count = len(re.findall(words, content, re.IGNORECASE))
    total_chars = len(content)
    if total_chars == 0:
        return heuristic(0, False, [])
    density = sensory_count / (total_chars / 1000)
    deficit = max(0, (5 - density) / 5)
    score = round(deficit * 100)
    flagged = density < 2
    return heuristic(score, flagged, [f"sensory density: {density:.1f} per 1k chars (expected ~5)"])

# 5. Uniform paragraph rhythm
def detect_uniform_rhythm(content):
    paragraphs = [p for p in re.split(r'\n\n+', content) if p.strip()]
    lengths = [len(p) for p in paragraphs]
    count = len(lengths)
    if count < 3:
        return heuristic(0, False, [])
    mean = sum(lengths) / count
    variance = sum((l - mean) ** 2 for l in lengths) / count
    stddev = math.sqrt(variance)
    cv = stddev / mean if mean > 0 else 0
    raw = (0.20 - cv) / 0.20
    score = max(0, round(raw * 100))
    flagged = cv < 0.20
    return heuristic(score, flagged, [f"paragraph CV: {cv:.3f} (threshold <0.20)"])

# 6. Missing character voice differentiation
def detect_missing_voice(content, lang):
    if lang == "zh":
        dialogues = re.findall(r'[「"][^」"]*[」"]', content)
        dialogues = [d.strip('「」""') for d in dialogues]
    else:
        dialogues = [d.strip('"') for d in re.findall(r'"[^"]*"', content)]
    dialogues = [d for d in dialogues if d]
    if len(dialogues) < 3:
        return heuristic(0, False, [])
    lengths = [len(d) for d in dialogues]
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    stddev = math.sqrt(variance)
    cv = stddev / mean if mean > 0 else 0
    raw = (0.30 - cv) / 0.30
    score = max(0, round(raw * 100))
    flagged = cv < 0.30
    return heuristic(score, flagged, [f"dialogue length CV: {cv:.3f} (threshold <0.30)"])

# 7. Formulaic chapter openings/endings
def detect_formulaic_patterns(content, lang):
    lines = content.splitlines()
    opening = "\n".join(lines[:5])
    ending = "\n".join(lines[-5:]) if len(lines) >= 5 else "\n".join(lines)
    if lang == "zh":
        op = r'清晨|黎明|太阳升起|新的一天|又是一天|晨光|破晓'
        ep = r'殊不知|却不知道|然而他不知道|小did.*know|未曾想到|谁也没想到'
    else:
        op = r'As the sun rose|The morning|A new day|Dawn broke|The day began'
        ep = r'Little did.*know|However.*didn\'t know|Unbeknownst|What.*didn\'t know'
    opening_match = len(re.findall(op, opening, re.IGNORECASE))
    ending_match = len(re.findall(ep, ending, re.IGNORECASE))
    total_matches = opening_match + ending_match
    score = min(total_matches * 50, 100)
    flagged = total_matches > 0
    examples = []
    if opening_match > 0:
        examples.append("formulaic opening detected")
    if ending_match > 0:
        examples.append("formulaic ending detected")
    if not examples:
        examples.append("none")
    return heuristic(score, flagged, examples)

def main():
    if len(sys.argv) < 2:
        json.dump({"file": "", "heuristics": {}, "overallAILikelihood": 0,
                    "summary": "Error: missing file"}, sys.stdout)
        sys.exit(1)
    filepath = sys.argv[1]
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError):
        json.dump({"file": filepath, "heuristics": {}, "overallAILikelihood": 0,
                    "summary": "Error: cannot read file"}, sys.stdout)
        sys.exit(1)
    lang = "zh" if is_chinese(content) else "en"
    h = {
        "repetitiveSentenceStructures": detect_repetitive_structures(content, lang),
        "unnaturalEmotionalEscalation": detect_emotional_escalation(content, lang),
        "excessiveSummarization": detect_excessive_summarization(content, lang),
        "lackOfSensoryDetail": detect_lack_sensory(content, lang),
        "uniformParagraphRhythm": detect_uniform_rhythm(content),
        "missingCharacterVoice": detect_missing_voice(content, lang),
        "formulaicOpeningsEndings": detect_formulaic_patterns(content, lang),
    }
    scores = [v["score"] for v in h.values()]
    overall = round(sum(scores) / len(scores))
    summary = "Low" if overall < 40 else ("Medium" if overall < 70 else "High")
    result = {
        "file": filepath,
        "heuristics": h,
        "overallAILikelihood": overall,
        "summary": f"{summary} AI likelihood",
    }
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()

if __name__ == "__main__":
    main()
