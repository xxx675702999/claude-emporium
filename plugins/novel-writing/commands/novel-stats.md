---
name: novel-stats
description: Display book statistics and analytics
---

# /novel-stats — Book Statistics

## Usage
/novel-stats [--book <id>] [--verbose]

## Output Example
```
Book Statistics: 破灭星辰

Overview:
- Total chapters: 50 / 200 (25%)
- Total words: 165,000
- Avg words/chapter: 3,300
- Status: active

Chapter Metrics:
- Shortest: Chapter 12 (2,800 words)
- Longest: Chapter 23 (3,600 words)
- Std deviation: 250 words

Audit Performance:
- Pass rate: 92% (46/50 chapters)
- Avg critical issues: 0.2 per chapter
- Avg warning issues: 1.5 per chapter

Top Issue Categories:
1. Lexical fatigue (12 occurrences)
2. Pacing issues (8 occurrences)
3. Hedge density (6 occurrences)

Revision Stats:
- Chapters revised: 15 (30%)
- Avg revision rounds: 1.4
- Most common mode: spot-fix (60%)

Timeline:
- Started: 2026-03-01
- Last chapter: 2026-04-14
- Avg chapters/week: 3.5
- Estimated completion: 2026-08-15 (at current pace)
```

## Options
- `--book <id>`: Target book
- `--verbose`: Show per-chapter breakdown

## Implementation Steps

### Step 1: Load Book Data
```bash
BOOK_DIR="books/$BOOK_ID"
BOOK_JSON="$BOOK_DIR/book.json"

# Read book config
eval $(python3 -c "
import json
d = json.load(open('$BOOK_JSON'))
print(f'BOOK_TITLE=\"{d.get(\"title\", \"\")}\"')
print(f'BOOK_STATUS=\"{d.get(\"status\", \"\")}\"')
print(f'TARGET_CHAPTERS=\"{d.get(\"targetChapterCount\", 0)}\"')
print(f'TARGET_WORDS=\"{d.get(\"chapterWordCount\", 0)}\"')
print(f'CREATED_AT=\"{d.get(\"createdAt\", \"\")}\"')
")

# Count chapters (all .md files in chapters/ directory)
CHAPTER_COUNT=$(find "$BOOK_DIR/chapters" -name "*.md" | wc -l | tr -d ' ')
```

### Step 2: Calculate Word Counts
```bash
# Total words across all chapters
TOTAL_WORDS=0
declare -a CHAPTER_WORDS

for chapter_file in $(find "$BOOK_DIR/chapters" -name "*.md" | sort); do
  WORDS=$(wc -w < "$chapter_file" | tr -d ' ')
  TOTAL_WORDS=$((TOTAL_WORDS + WORDS))
  CHAPTER_WORDS+=("$WORDS")
done

# Average words per chapter
AVG_WORDS=$((TOTAL_WORDS / CHAPTER_COUNT))

# Find shortest and longest
SHORTEST_WORDS=${CHAPTER_WORDS[0]}
LONGEST_WORDS=${CHAPTER_WORDS[0]}
SHORTEST_CHAPTER=1
LONGEST_CHAPTER=1

for i in "${!CHAPTER_WORDS[@]}"; do
  if [[ ${CHAPTER_WORDS[$i]} -lt $SHORTEST_WORDS ]]; then
    SHORTEST_WORDS=${CHAPTER_WORDS[$i]}
    SHORTEST_CHAPTER=$((i + 1))
  fi
  if [[ ${CHAPTER_WORDS[$i]} -gt $LONGEST_WORDS ]]; then
    LONGEST_WORDS=${CHAPTER_WORDS[$i]}
    LONGEST_CHAPTER=$((i + 1))
  fi
done

# Calculate standard deviation
# (simplified: use awk for precise calculation)
STDDEV=$(printf '%s\n' "${CHAPTER_WORDS[@]}" | awk -v avg=$AVG_WORDS '{sum+=($1-avg)^2} END {print sqrt(sum/NR)}')
```

### Step 3: Load Audit Results
```bash
# Read audit results from chapter trace files
AUDIT_PASS=0
AUDIT_FAIL=0
TOTAL_CRITICAL=0
TOTAL_WARNINGS=0
declare -A ISSUE_CATEGORIES

eval $(python3 -c "
import json, glob, os

trace_files = sorted(glob.glob(os.path.join('$BOOK_DIR', 'story/runtime/chapter-*.trace.json')))
audit_pass = 0
audit_fail = 0
total_critical = 0
total_warnings = 0
issue_categories = {}

for tf in trace_files:
    d = json.load(open(tf))
    audit = d.get('audit', {})
    if audit.get('verdict') == 'pass':
        audit_pass += 1
    else:
        audit_fail += 1
    for issue in audit.get('issues', []):
        if issue.get('severity') == 'critical':
            total_critical += 1
        elif issue.get('severity') == 'warning':
            total_warnings += 1
        dim = issue.get('dimension', 'unknown')
        issue_categories[dim] = issue_categories.get(dim, 0) + 1

audit_total = audit_pass + audit_fail
pass_rate = (audit_pass * 100 // audit_total) if audit_total > 0 else 0
avg_critical = round(total_critical / audit_total, 1) if audit_total > 0 else 0
avg_warnings = round(total_warnings / audit_total, 1) if audit_total > 0 else 0

print(f'AUDIT_PASS={audit_pass}')
print(f'AUDIT_FAIL={audit_fail}')
print(f'AUDIT_TOTAL={audit_total}')
print(f'TOTAL_CRITICAL={total_critical}')
print(f'TOTAL_WARNINGS={total_warnings}')
print(f'PASS_RATE={pass_rate}')
print(f'AVG_CRITICAL={avg_critical}')
print(f'AVG_WARNINGS={avg_warnings}')

# Export top categories as sorted list
for dim, count in sorted(issue_categories.items(), key=lambda x: -x[1]):
    print(f'ISSUE_CAT_{dim}={count}')
")
```

### Step 4: Load Revision Stats
```bash
# Read revision history from trace files
REVISED_COUNT=0
TOTAL_REVISION_ROUNDS=0
declare -A REVISION_MODES

eval $(python3 -c "
import json, glob, os

trace_files = sorted(glob.glob(os.path.join('$BOOK_DIR', 'story/runtime/chapter-*.trace.json')))
revised_count = 0
total_revision_rounds = 0
revision_modes = {}

for tf in trace_files:
    d = json.load(open(tf))
    revisions = d.get('revisions', [])
    if len(revisions) > 0:
        revised_count += 1
        total_revision_rounds += len(revisions)
        for rev in revisions:
            mode = rev.get('mode', 'unknown')
            revision_modes[mode] = revision_modes.get(mode, 0) + 1

avg_revisions = round(total_revision_rounds / revised_count, 1) if revised_count > 0 else 0

most_common_mode = ''
most_common_pct = 0
if revision_modes and total_revision_rounds > 0:
    most_common_mode = max(revision_modes, key=revision_modes.get)
    most_common_pct = revision_modes[most_common_mode] * 100 // total_revision_rounds

print(f'REVISED_COUNT={revised_count}')
print(f'TOTAL_REVISION_ROUNDS={total_revision_rounds}')
print(f'AVG_REVISIONS={avg_revisions}')
print(f'MOST_COMMON_MODE=\"{most_common_mode}\"')
print(f'MOST_COMMON_PERCENTAGE={most_common_pct}')
")
```

### Step 5: Calculate Timeline
```bash
# Parse created date
CREATED_DATE=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$CREATED_AT" "+%Y-%m-%d" 2>/dev/null || echo "Unknown")

# Last chapter date (from most recent trace file)
LAST_TRACE=$(find "$BOOK_DIR/story/runtime" -name "chapter-*.trace.json" | sort | tail -n 1)
if [[ -f "$LAST_TRACE" ]]; then
  LAST_CHAPTER_DATE=$(python3 -c "
import json
d = json.load(open('$LAST_TRACE'))
ts = d.get('timestamp', '')
print(ts.split('T')[0] if 'T' in ts else ts if ts else 'Unknown')
")
else
  LAST_CHAPTER_DATE="Unknown"
fi

# Calculate chapters per week
if [[ "$CREATED_DATE" != "Unknown" && "$LAST_CHAPTER_DATE" != "Unknown" ]]; then
  DAYS_ELAPSED=$(( ($(date -j -f "%Y-%m-%d" "$LAST_CHAPTER_DATE" "+%s") - $(date -j -f "%Y-%m-%d" "$CREATED_DATE" "+%s")) / 86400 ))
  WEEKS_ELAPSED=$(echo "scale=1; $DAYS_ELAPSED / 7" | bc)
  CHAPTERS_PER_WEEK=$(echo "scale=1; $CHAPTER_COUNT / $WEEKS_ELAPSED" | bc)
  
  # Estimate completion
  REMAINING_CHAPTERS=$((TARGET_CHAPTERS - CHAPTER_COUNT))
  REMAINING_WEEKS=$(echo "scale=0; $REMAINING_CHAPTERS / $CHAPTERS_PER_WEEK" | bc)
  COMPLETION_DATE=$(date -j -v+${REMAINING_WEEKS}w "+%Y-%m-%d")
else
  CHAPTERS_PER_WEEK="N/A"
  COMPLETION_DATE="N/A"
fi
```

### Step 6: Display Statistics
```
Book Statistics: $BOOK_TITLE

Overview:
- Total chapters: $CHAPTER_COUNT / $TARGET_CHAPTERS ($PROGRESS%)
- Total words: $TOTAL_WORDS
- Avg words/chapter: $AVG_WORDS
- Status: $BOOK_STATUS

Chapter Metrics:
- Shortest: Chapter $SHORTEST_CHAPTER ($SHORTEST_WORDS words)
- Longest: Chapter $LONGEST_CHAPTER ($LONGEST_WORDS words)
- Std deviation: $STDDEV words

Audit Performance:
- Pass rate: $PASS_RATE% ($AUDIT_PASS/$AUDIT_TOTAL chapters)
- Avg critical issues: $AVG_CRITICAL per chapter
- Avg warning issues: $AVG_WARNINGS per chapter

Top Issue Categories:
[sorted list of top 5 issue categories with counts]

Revision Stats:
- Chapters revised: $REVISED_COUNT ($REVISED_PERCENTAGE%)
- Avg revision rounds: $AVG_REVISIONS
- Most common mode: $MOST_COMMON_MODE ($MOST_COMMON_PERCENTAGE%)

Timeline:
- Started: $CREATED_DATE
- Last chapter: $LAST_CHAPTER_DATE
- Avg chapters/week: $CHAPTERS_PER_WEEK
- Estimated completion: $COMPLETION_DATE (at current pace)
```

## Verbose Mode (--verbose)

When `--verbose` flag is set, display per-chapter breakdown:

```
Per-Chapter Breakdown:

Chapter 1: 0001_破灭之始.md
- Words: 3,200
- Audit: PASS (0 critical, 1 warning)
- Revisions: 1 (spot-fix)
- Status: approved

Chapter 2: 0002_觉醒.md
- Words: 3,100
- Audit: PASS (0 critical, 0 warnings)
- Revisions: 0
- Status: approved

...

Chapter 50: 0050_新的开始.md
- Words: 3,300
- Audit: PASS (0 critical, 2 warnings)
- Revisions: 2 (polish, spot-fix)
- Status: pending
```

## Error Handling

### Book Not Found
```
Error: Book not found: book-999

Available books:
- book-001: 破灭星辰 (50 chapters)
- book-002: 星辰之路 (30 chapters)
```

### No Chapters
```
Book Statistics: 破灭星辰

Overview:
- Total chapters: 0 / 200 (0%)
- Total words: 0
- Status: incubating

No chapters written yet.

Next steps:
1. Write first chapter: /novel-write
2. Import chapters: /novel create --import <file>
```

### Missing Trace Files
```
Warning: Some chapters missing audit trace files

Chapters with traces: 45 / 50
Audit statistics may be incomplete.

Run /novel-review --audit to generate missing traces.
```

## Integration with Other Commands

Statistics are derived from:
- book.json: book metadata, target counts
- chapters/*.md: chapter files, word counts
- story/runtime/*.trace.json: audit results, revision history
- story/state/chapter-meta.json: chapter approval status and lifecycle (backward compat: review-status.json)

## Performance Considerations

- Fast for books with < 200 chapters (< 1 second)
- Moderate for books with 200-500 chapters (1-3 seconds)
- Verbose mode adds ~50ms per chapter

## Data Sources

### Book Metadata
- Title, status, target counts: book.json
- Created date: book.json createdAt field

### Chapter Data
- Word counts: calculated from chapter files
- Chapter count: file count in chapters/ directory

### Audit Data
- Pass/fail verdict: trace.json audit.verdict
- Issue counts: trace.json audit.issues array
- Issue categories: trace.json audit.issues[].dimension

### Revision Data
- Revision count: trace.json revisions array length
- Revision modes: trace.json revisions[].mode

### Timeline Data
- Start date: book.json createdAt
- Last chapter date: most recent trace.json timestamp
- Pace calculation: chapters / elapsed weeks
