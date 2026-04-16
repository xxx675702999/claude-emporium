---
name: style-analyzer
description: Pure text analysis function that extracts StyleProfile from reference text
tools: []
skills: []
---

# Style Analyzer (Pure Function)

## Role
`analyzeStyle()` is a **pure function** (not an agent) that performs deterministic text analysis on reference text. It extracts quantitative statistical features and returns a `StyleProfile` object. There is no LLM call involved — all analysis is regex-based counting and statistics.

## Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | `string` | Yes | The reference text to analyze |
| `sourceName` | `string` | No | Label identifying the source of the text |
| `language` | `"zh"` \| `"en"` | No | Language code from `book.json` `language` field. Defaults to `"zh"` for backward compatibility |

## Process

At the start of analysis, read the `language` parameter (from `book.json` `language` field). Branch into Chinese or English analysis paths. Both paths produce the same `StyleProfile` output structure.

---

### Path A: Chinese Analysis (`language == "zh"`)

#### 1. Sentence Length Analysis (Chinese)
- **Split** the text on sentence-ending delimiters: `。`, `！`, `？`, `\n`
- **Trim and filter** empty segments
- **Compute**:
  - `avgSentenceLength` — mean character count per sentence (rounded to 1 decimal)
  - `sentenceLengthStdDev` — population standard deviation (rounded to 1 decimal)
- Returns `0` for both if no sentences are found

#### 2. Paragraph Length Analysis (Chinese)
- **Split** the text on double newlines (`\n\s*\n`)
- **Trim and filter** empty segments
- **Compute**:
  - `avgParagraphLength` — mean character count per paragraph (rounded to integer)
  - `paragraphLengthRange` — `{ min, max }` character counts across all paragraphs
- Returns `0` for all values if no paragraphs are found

#### 3. Vocabulary Diversity — Character-Level TTR (Chinese)
- **Strip** whitespace, punctuation (`，。！？、：；""''（）【】《》`), and digits from the text
- **Count** total characters and unique characters (using `Set`)
- **Compute** `vocabularyDiversity` = unique / total (rounded to 3 decimals)
- Character-level TTR is used because Chinese text does not have word-level tokenization boundaries
- Returns `0` if no analyzable characters remain

#### 4. Opening Pattern Detection (Chinese)
- For each sentence with length >= 2, extract the **first 2 characters** as the opening pattern
- **Count** occurrences of each pattern
- **Sort** by frequency descending, take the **top 5**
- **Filter** to patterns with >= 3 occurrences
- Format each entry as `"XX...(N次)"` (e.g., `"他的...(12次)"`)

#### 5. Rhetorical Feature Detection (Chinese)
Six rhetorical patterns are detected via regex:

| Pattern | Chinese Name | What It Matches |
|---------|-------------|-----------------|
| Simile | 比喻 | `像/如/仿佛/似` followed by `是/同/一般/一样` |
| Parallelism | 排比 | Repeated phrases (2-6 chars) between delimiters |
| Rhetorical question | 反问 | `难道/怎么可能/岂不是/何尝不` |
| Hyperbole | 夸张 | Fixed expressions: `天崩地裂/惊天动地/翻天覆地/震耳欲聋` |
| Personification | 拟人 | Nature nouns (`风雨雪月花树草石`) + human actions (`笑哭叹呻吟怒舞`) |
| Short rhythm | 短句节奏 | Sentences of 1-8 characters between sentence-ending punctuation |

- Each pattern requires **>= 2 matches** to be included
- Format each entry as `"PatternName(N处)"` (e.g., `"比喻(像/如/仿佛)(5处)"`)

---

### Path B: English Analysis (`language == "en"`)

#### 1. Sentence Length Analysis (English)
- **Split** the text on sentence-ending delimiters: `.`, `?`, `!`, `\n`
- **Trim** whitespace, **filter** empty segments
- **For each sentence**, count **words** (split on whitespace, filter empty tokens)
- **Compute**:
  - `avgSentenceLength` — mean word count per sentence (rounded to 1 decimal)
  - `sentenceLengthStdDev` — population standard deviation of word counts (rounded to 1 decimal)
- Returns `0` for both if no sentences are found

#### 2. Paragraph Length Analysis (English)
- **Split** the text on double newlines (`\n\s*\n`)
- **Trim and filter** empty segments
- **For each paragraph**, count **words** (split on whitespace, filter empty tokens)
- **Compute**:
  - `avgParagraphLength` — mean word count per paragraph (rounded to integer)
  - `paragraphLengthRange` — `{ min, max }` word counts across all paragraphs
- Returns `0` for all values if no paragraphs are found

#### 3. Vocabulary Diversity — Word-Level TTR (English)
- **Lowercase** the text for case-insensitive comparison
- **Split** on whitespace to produce a word list
- **Strip** trailing/leading punctuation from each word (`,.;:!?—"'()[]{}"`)
- **Filter** out empty tokens
- **Count** total words and unique words (using `Set`)
- **Compute** `vocabularyDiversity` = unique words / total words (rounded to 3 decimals)
- Word-level TTR is used because English has clear whitespace-delimited word boundaries
- Returns `0` if no analyzable words remain

#### 4. Opening Pattern Detection (English)
- For each sentence with >= 3 words, extract the **first 3 to 5 full words** as the opening pattern
  - Take first 3 words as the base pattern
  - Extend to 4 or 5 words if the 4th/5th word is a common function word (`the`, `a`, `an`, `of`, `in`, `to`, `for`, `on`, `at`, `by`, `with`, `from`, `as`, `into`, `is`, `are`, `was`, `were`) — conjunctions (`and`, `but`, `or`) are excluded because they signal clause boundaries — this keeps the pattern meaningful rather than cutting mid-phrase
- **Lowercase** patterns for comparison, but display in original casing
- **Count** occurrences of each case-insensitive pattern
- **Sort** by frequency descending, take the **top 5**
- **Filter** to patterns with >= 3 occurrences
- Format each entry as `"Word1 word2 word3...(N times)"` (e.g., `"He didn't want...(5 times)"`)

#### 5. Rhetorical Feature Detection (English)
Two rhetorical patterns are detected:

| Pattern | What It Matches |
|---------|-----------------|
| Alliteration | Repeated first consonant sound across consecutive words or within a sentence |
| Anaphora | Repeated word or phrase at the start of consecutive sentences |

**Alliteration detection:**
- For each sentence, extract the **first letter** (case-insensitive, alphabetic only) of each word
- A sequence of **3 or more** words sharing the same first consonant letter counts as one alliteration instance
- Common letter pairs treated as same sound: `c`/`k`, `c`/`s` (before e/i), `ph`/`f` — use first letter only for simplicity
- Ignore common function words (`the`, `a`, `an`, `and`, `or`, `but`, `in`, `on`, `at`, `to`, `of`, `is`, `it`)
- Requires **>= 2 instances** across the text to include in output

**Anaphora detection:**
- For each pair of consecutive sentences, compare the first 2-3 words (case-insensitive)
- If the opening sequence matches exactly across **3 or more** consecutive sentences, count as one anaphora instance
- Requires **>= 2 instances** across the text to include in output

- Format each entry as `"PatternName(N instances)"` (e.g., `"Alliteration(7 instances)"`, `"Anaphora(3 instances)"`)

## Output

Returns a `StyleProfile` object:

```typescript
interface StyleProfile {
  readonly avgSentenceLength: number;        // rounded to 1 decimal
  readonly sentenceLengthStdDev: number;     // rounded to 1 decimal
  readonly avgParagraphLength: number;       // rounded to integer
  readonly paragraphLengthRange: {
    readonly min: number;
    readonly max: number;
  };
  readonly vocabularyDiversity: number;      // TTR, rounded to 3 decimals
  readonly topPatterns: ReadonlyArray<string>;          // top 5, >= 3 occurrences
  readonly rhetoricalFeatures: ReadonlyArray<string>;   // detected patterns, >= 2 occurrences
  readonly sourceName?: string;
  readonly analyzedAt?: string;              // ISO 8601 timestamp
}
```

### Example Output (Chinese)

```json
{
  "avgSentenceLength": 18.3,
  "sentenceLengthStdDev": 7.1,
  "avgParagraphLength": 142,
  "paragraphLengthRange": { "min": 28, "max": 380 },
  "vocabularyDiversity": 0.421,
  "topPatterns": [
    "他的...(12次)",
    "这个...(8次)",
    "那一...(5次)",
    "一道...(4次)",
    "只见...(3次)"
  ],
  "rhetoricalFeatures": [
    "比喻(像/如/仿佛)(5处)",
    "短句节奏(18处)",
    "排比(3处)"
  ],
  "sourceName": "reference-xuanhuan.txt",
  "analyzedAt": "2026-04-14T08:30:00.000Z"
}
```

### Example Output (English)

```json
{
  "avgSentenceLength": 14.7,
  "sentenceLengthStdDev": 6.2,
  "avgParagraphLength": 58,
  "paragraphLengthRange": { "min": 12, "max": 145 },
  "vocabularyDiversity": 0.538,
  "topPatterns": [
    "He didn't want...(5 times)",
    "She looked at...(4 times)",
    "The door was...(3 times)",
    "There was a...(3 times)",
    "He turned to...(3 times)"
  ],
  "rhetoricalFeatures": [
    "Alliteration(7 instances)",
    "Anaphora(3 instances)"
  ],
  "sourceName": "reference-dark-fantasy.txt",
  "analyzedAt": "2026-04-14T08:30:00.000Z"
}
```

## Usage Notes

### Relationship to style_guide.md
The `StyleProfile` returned by `analyzeStyle()` contains only quantitative metrics. The `style_guide.md` file used by the writer agent is a **separate concern** — it is an LLM-generated document that incorporates these metrics alongside qualitative analysis. This function does not generate `style_guide.md`.

### Bilingual Support
The analyzer supports both Chinese and English text via the `language` parameter:
- **Chinese path** (`"zh"`): Character-level TTR, Chinese punctuation delimiters (`。！？`), Chinese rhetorical patterns (比喻, 排比, etc.), 2-character opening patterns
- **English path** (`"en"`): Word-level TTR (whitespace-split), English punctuation delimiters (`.?!`), English rhetorical patterns (alliteration, anaphora), 3-5 word opening patterns
- If `language` is not provided, defaults to `"zh"` for backward compatibility

## Error Handling

### Empty or Whitespace-Only Text
If the input text is empty or contains no analyzable content:
- All numeric fields return `0`
- `paragraphLengthRange` returns `{ min: 0, max: 0 }`
- `topPatterns` returns `[]`
- `rhetoricalFeatures` returns `[]`
- The function does NOT throw — it always returns a valid `StyleProfile`
