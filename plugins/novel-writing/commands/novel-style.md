---
name: novel-style
description: Analyze and apply writing style from reference text
---

# /novel-style — Style Management

## CRITICAL: Use Subagents

Style analysis runs via a dedicated agent. Spawn via the Agent tool with `subagent_type: "novel-writing:style-analyzer"`. Do NOT analyze writing style directly.

## Usage
/novel-style --analyze <file> [--apply] [--book <id>]

## Actions

### --analyze
Analyze reference text to extract style profile (REQ-F-34).

**Process:**
1. Spawn style-analyzer agent with reference file
2. Agent runs deterministic analysis + qualitative LLM analysis
3. Generate style_guide.md and style_fingerprint.md
4. If --apply: Write to book directory
5. Display style summary

### --apply
Apply analyzed style to book (REQ-F-35).

**Process:**
1. Copy style_guide.md and style_fingerprint.md to book directory
2. Update book.json with `"styleImported": true`
3. Report success

## Implementation Steps

### Step 1: Validate Reference File
```bash
if [[ ! -f "$REFERENCE_FILE" ]]; then
  echo "Error: Reference file not found: $REFERENCE_FILE"
  exit 1
fi

if [[ ! -s "$REFERENCE_FILE" ]]; then
  echo "Error: Reference file is empty"
  exit 1
fi
```

### Step 2: Run Style Analysis
Spawn style-analyzer agent (see agents/style-analyzer.md):

**Agent Process:**
1. Run deterministic analysis script:
   ```bash
   python3 $.plugin.directory/scripts/analyze/run-style-analysis.py "$REFERENCE_FILE"
   ```
   
   Output: JSON with statistical metrics
   ```json
   {
     "sentenceStats": {
       "avgLength": 18.2,
       "stddev": 7.4,
       "distribution": {
         "0-10": 142,
         "11-20": 180,
         "21-30": 60,
         "31-50": 18,
         "51-100": 4,
         "100+": 0
       }
     },
     "paragraphStats": {
       "avgLength": 68.5,
       "min": 8,
       "max": 180,
       "totalParagraphs": 87
     },
     "vocabularyDiversity": {
       "ttr": 0.42,
       "totalTokens": 5420,
       "uniqueTokens": 2276,
       "topWords": [
         {"word": "他", "count": 280},
         {"word": "的", "count": 156}
       ]
     },
     "openingPatterns": [
       {"pattern": "他", "count": 42},
       {"pattern": "这", "count": 38}
     ],
     "rhetoricalPatterns": {
       "metaphor": 24,
       "parallelism": 0,
       "rhetoricalQuestions": 8,
       "hyperbole": 18,
       "personification": 0,
       "shortRhythm": 32
     }
   }
   ```

2. Read reference text and perform qualitative analysis:
   - Tone & Voice (formal/casual, serious/humorous, intimate/distant)
   - Pacing Feel (fast/slow, scene/summary, dialogue/narration)
   - Dialogue Patterns (attribution style, exchange length)
   - Description Density (sparse/rich, sensory emphasis)
   - Sentence Structure (simple/complex, variety, fragments)
   - Paragraph Structure (length variation, rhythm)

3. Generate style_guide.md with actionable rules
4. Generate style_fingerprint.md with quantitative baseline

### Step 3: Display Style Summary
```
Analyzing style from reference.txt...

Statistical Analysis:
- Avg sentence length: 18 words (std dev: 7.2)
- Avg paragraph length: 4.5 sentences
- Vocabulary diversity (TTR): 0.68
- Top opening patterns: "他", "这", "在"

Qualitative Analysis:
- Tone: Serious with occasional humor
- Voice: Third-person limited, intimate
- Pacing: Fast-paced action with contemplative moments
- Dialogue: Short exchanges, action beats over attribution
- Description: Moderate density, visual emphasis

Style guide created: style_guide.md
Style fingerprint created: style_fingerprint.md

Apply to book? (--apply flag to confirm)
```

### Step 4: Apply to Book (if --apply flag)
```bash
BOOK_DIR="books/$BOOK_ID"
cp style_guide.md "$BOOK_DIR/story/style_guide.md"
cp style_fingerprint.md "$BOOK_DIR/story/style_fingerprint.md"

# Update book.json
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from lib.json_utils import update_json
update_json('$BOOK_DIR/book.json', lambda d: {**d, 'styleImported': True})
"
```

Report:
```
Style applied to book: 破灭星辰

Files written:
- books/book-001/story/style_guide.md
- books/book-001/story/style_fingerprint.md

Future chapters will adopt this style.

Note: This overwrites any auto-generated style from /novel create --import
```

## Output Files

### style_guide.md
Actionable rules for writer agent. Structure:

```markdown
# Style Guide

## Tone & Voice
[Qualitative description]

**Rules:**
- [Specific guideline 1]
- [Specific guideline 2]

## Sentence Structure
- **Average length**: [X words/chars] (±[Y stddev])
- **Variety**: [description]

**Rules:**
- Target sentence length: [X-Y range]
- Mix [short/medium/long] in ratio [A:B:C]

## Vocabulary
- **Lexical density**: TTR [X]
- **Common words to use**: [list]
- **Words to avoid**: [list]

**Rules:**
- Maintain TTR around [X]
- Prefer [style] word choices

## Dialogue
- **Attribution style**: [said-heavy / action-beat-heavy / minimal]
- **Typical exchange length**: [X lines]

**Rules:**
- [Dialogue formatting guideline]
- [Character voice guideline]

## Description
- **Density**: [sparse / moderate / rich]
- **Sensory emphasis**: [which senses]

**Rules:**
- [Description length guideline]
- [Sensory detail guideline]

## Pacing
- **Scene/summary ratio**: [estimate]
- **Chapter rhythm**: [description]

**Rules:**
- [Scene length guideline]
- [Transition guideline]

## Rhetorical Devices
- **Metaphor frequency**: [X per 1000 words/chars]
- **Parallelism**: [frequency]

**Rules:**
- Use metaphors [sparingly/moderately/frequently]
- Apply parallelism for [specific effect]

## Opening Patterns
- **Common sentence starts**: [list top 5]

**Rules:**
- Vary sentence openings
- Acceptable patterns: [list]
- Avoid overusing: [list]
```

### style_fingerprint.md
Quantitative baseline for auditor. Structure:

```markdown
# Style Fingerprint

## Statistical Baseline

### Sentence Statistics
- **Average length**: [X] words/chars
- **Standard deviation**: [Y]
- **Distribution**: [table]

### Paragraph Statistics
- **Average length**: [X] words/chars
- **Range**: [min]-[max]
- **Total paragraphs**: [count]

### Vocabulary Diversity
- **Type-Token Ratio (TTR)**: [X]
- **Total tokens**: [count]
- **Unique tokens**: [count]
- **Top 20 frequent words**: [list with counts]

### Opening Patterns
[Top 10 with frequencies]

### Rhetorical Patterns
- **Metaphor/Simile**: [count]
- **Parallelism**: [count]
- **Rhetorical questions**: [count]
- **Hyperbole**: [count]
- **Personification**: [count]
- **Short rhythm**: [count]

## Qualitative Markers

### Tone
[1-2 sentence description]

### Voice
[1-2 sentence description]

### Pacing
[1-2 sentence description]

### Dialogue Style
[1-2 sentence description]

### Description Style
[1-2 sentence description]

## Usage
This fingerprint serves as baseline for style consistency checks. Future chapters should match these metrics within ±20% variance.

The auditor agent (dimension 8: style drift) compares new chapters against this fingerprint.

## Source
- **Reference file**: [path]
- **Analyzed at**: [timestamp]
- **Language**: [zh/en]
```

## Error Handling

### Reference File Empty
```
Error: Reference file is empty or contains no analyzable text.
Cannot extract style profile from empty file.
```

### Scripts Fail
If deterministic scripts fail:
1. Report script error to user
2. Fall back to qualitative analysis only
3. Generate style_guide.md without quantitative baseline
4. Generate style_fingerprint.md with "N/A" for missing metrics
5. Note in fingerprint: "Partial analysis — deterministic metrics unavailable"

### Book ID Invalid
```
Error: Book ID 'book-999' not found.
Expected book.json at: books/book-999/book.json

Options:
1. Create book first: /novel create --id book-999 ...
2. Save style to current directory: /novel-style --analyze <file> (no --apply)
```

### File Encoding Issues
If reference file has invalid UTF-8:
```bash
# Detect encoding
ENCODING=$(file -i "$REFERENCE_FILE" | sed 's/.*charset=//')

if [[ "$ENCODING" != "utf-8" ]]; then
  echo "Warning: File encoding is $ENCODING, converting to UTF-8..."
  iconv -f "$ENCODING" -t UTF-8 "$REFERENCE_FILE" > "$REFERENCE_FILE.utf8"
  REFERENCE_FILE="$REFERENCE_FILE.utf8"
fi
```

If conversion fails:
```
Error: Cannot convert file encoding from $ENCODING to UTF-8

Please convert the file manually:
iconv -f $ENCODING -t UTF-8 reference.txt > reference-utf8.txt

Then run:
/novel-style --analyze reference-utf8.txt
```

## Style Override Behavior (REQ-F-35)

When `/novel-style --analyze --apply` is run:
- Overwrites any auto-generated style from `/novel create --import`
- Updates book.json with `"styleImported": true`
- Future chapters use the new style guide
- Previous chapters retain their original style (no retroactive changes)

## Integration with Writer Agent

Writer agent loads style guide during compose phase:
1. Read `books/<id>/story/style_guide.md`
2. Include style rules in runtime context
3. Apply style constraints during chapter generation
4. Auditor checks style drift against `style_fingerprint.md`

## Performance Considerations

- Reference text size: Recommended 10k-50k words for accurate analysis
- Very short texts (<5k words): May produce unreliable statistical metrics
- Very long texts (>100k words): Analyze first 50k words only (representative sample)

## Language Support

- Chinese (zh): Character-based metrics (sentence length in chars, TTR by chars)
- English (en): Word-based metrics (sentence length in words, TTR by words)
- Language auto-detected from reference text
- Style guide language matches reference text language
