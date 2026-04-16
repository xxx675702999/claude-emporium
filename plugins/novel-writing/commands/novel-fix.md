---
name: novel-fix
description: Detect last chapter and run audit + revise — convenience wrapper for novel-review --audit-fix
---

# /novel-fix — Quick Fix Last Chapter

## CRITICAL: Use Subagents

This command delegates to `/novel-review --audit-fix`, which spawns dedicated agents. Do NOT audit or revise chapters directly — use the Agent tool with `subagent_type: "novel-writing:auditor"` and `subagent_type: "novel-writing:reviser"`.

## Usage
/novel-fix [<N>] [--mode <spot-fix|rewrite|polish|anti-detect>] [--max-rounds <N>] [--book <id>]

## Process

```
1. Resolve book directory (--book or active book)
2. Determine target chapter:
   - If <N> provided → target = N
   - If no <N> provided → detect last chapter:
     - List all *.md files in chapters/
     - Extract chapter numbers from filename prefix (both `XXXX_标题.md` and `chapter-XXXX.md`)
     - Take max → target = lastChapter
     - If no chapters found → report "no chapters to fix"
3. Validate chapter file exists (lookup by number prefix)
4. Invoke /novel-review --audit-fix <target>
   - Forward --mode if provided
   - Forward --max-rounds if provided
   - Forward --book if provided
5. Report result
```

### Step 1: Resolve Book Directory

Read `.session.json` `activeBook` field for active book, or use `--book <id>` override.
Verify `books/<id>/book.json` exists.

### Step 2: Determine Target Chapter

```bash
# If explicit chapter number provided, use it
if [ -n "$TARGET_CHAPTER" ]; then
  echo "Target chapter: $TARGET_CHAPTER (explicit)"
else
  LAST_CHAPTER=$(python3 $.plugin.directory/scripts/lib/chapter_utils.py detect-last "books/<id>/chapters")

  if [ "$LAST_CHAPTER" -eq 0 ]; then
    echo "No chapters found. Nothing to fix."
    exit 0
  fi

  TARGET_CHAPTER=$LAST_CHAPTER
  echo "Target chapter: $TARGET_CHAPTER (detected as last chapter)"
fi
```

### Step 3: Validate Chapter File

Find the chapter file by number prefix (zero-padded to 4 digits):
```bash
CHAPTER_FILE=$(python3 $.plugin.directory/scripts/lib/chapter_utils.py find "books/<id>/chapters" "$TARGET_CHAPTER")
if [ -z "$CHAPTER_FILE" ]; then
  echo "Error: Chapter $TARGET_CHAPTER not found."
  exit 1
fi
```
Verify the file exists before invoking audit.

### Step 4: Invoke novel-review --audit-fix

Delegate to `/novel-review --audit-fix <target>`:

- Runs full audit (deterministic AI-tell checks + LLM judgment)
- If critical issues found → enters self-correction loop (reviser agent)
- If audit passes → reports "audit passed, no fix needed"
- `--mode` override forwarded to reviser (default: auto-selected by issue count)
- `--max-rounds` forwarded (default: 2)

## Options
- `<N>`: Target chapter number (default: auto-detect last chapter)
- `--mode <mode>`: Override revision mode forwarded to reviser
  - `spot-fix`: Targeted fixes, minimal changes (default for <=3 critical issues)
  - `rewrite`: Major rework (default for >3 critical issues)
  - `polish`: Minor style fixes only
  - `anti-detect`: Aggressive AI pattern removal
- `--max-rounds <N>`: Max revision rounds (default: 2)
- `--book <id>`: Target book (default: active book)

## Output Example

### Auto-detect Last Chapter — Issues Found and Fixed
```
Detecting last chapter...
  chapters/ → 15 chapter files found
  Last chapter: 15

Fixing Chapter 15...

Audit Report: Chapter 15

Deterministic Checks:
✅ Dim 20 (Paragraph uniformity): PASS (CV = 0.22)
✅ Dim 21 (Hedge density): PASS
✅ Dim 22 (Formulaic transitions): PASS
✅ Dim 23 (List-like structure): PASS

LLM Judgment:
✅ Dim 1 (OOC): PASS
❌ Dim 2 (Timeline): FAIL - Character arrives before departing
✅ Dim 3 (Lore conflict): PASS
... (remaining dimensions)

Overall Verdict: FAIL
- Critical issues: 1

Revising Chapter 15 (mode: spot-fix)

Round 1:
- Fixed timeline inconsistency (added travel scene)
- Word count: 3000 → 3150 (+5%)
- Re-running audit...

Audit Result: PASS
- All critical issues resolved

Fix Complete:
- Chapter: 15
- Rounds used: 1/3
- Final word count: 3,150
- Status: SUCCESS
```

### Auto-detect Last Chapter — Audit Passes (Clean)
```
Detecting last chapter...
  chapters/ → 15 chapter files found
  Last chapter: 15

Fixing Chapter 15...

Audit Report: Chapter 15

Overall Verdict: PASS
- Critical issues: 0
- Warning issues: 1
- Info issues: 0

Audit passed, no fix needed.

Chapter 15 is clean. No revision required.
```

### Explicit Chapter Number
```
/novel-fix 12

Fixing Chapter 12...

[...audit + revise output...]

Fix Complete:
- Chapter: 12
- Rounds used: 2/3
- Final word count: 2,980
- Status: SUCCESS
```

### With Mode Override
```
/novel-fix --mode anti-detect

Detecting last chapter...
  chapters/ → 15 chapter files found
  Last chapter: 15

Fixing Chapter 15 (mode: anti-detect)

[...audit + revise output with anti-detect revision mode...]
```

### No Chapters Exist
```
Detecting last chapter...
  chapters/ → 0 chapter files found

No chapters found. Nothing to fix.

Use /novel-continue to write your first chapter.
```

## Error Handling

### Book Not Found
```
Error: Book not found
Expected path: books/my-book/book.json

Use /novel --list to see available books.
```

### Chapter File Missing (explicit N)
```
Error: Chapter 12 not found
Expected path: books/my-book/chapters/0012_*.md or books/my-book/chapters/chapter-0012.md

Available chapters: 1-10
Use /novel-fix without a chapter number to fix the last chapter.
```

### novel-review Pipeline Failure
Errors from the underlying novel-review audit-fix flow are reported as-is. See `/novel-review` for full error handling details (deterministic script failures, truth file issues, max rounds exceeded, etc.).

## Implementation Notes

### Chapter Detection Logic
- Same logic as `/novel-continue`: list all `*.md` in `chapters/`, extract chapter numbers from filename prefix
- New format `XXXX_标题.md` and old format `chapter-XXXX.md` are both detected
- Non-matching files in chapters/ are ignored

### Delegation to novel-review
This command is a thin wrapper around `/novel-review --audit-fix`. All audit and revision logic (deterministic checks, LLM judgment, self-correction loop, revision modes) is handled by `/novel-review`. This command only adds:
1. Last chapter detection (when no explicit N provided)
2. "No chapters to fix" edge case handling
3. "Audit passed, no fix needed" messaging for clean chapters
4. User-friendly output showing the detection result

### Clean Audit Reporting
When the audit returns `criticalIssues == 0`, this command reports "audit passed, no fix needed" and exits without invoking the reviser. Warnings and info-level issues are displayed but do not trigger revision.

### Automation Mode
Inherits mode from `.session.json` — same behavior as `/novel-review`.

## Related Commands
- `/novel-review`: Full review, audit, and approve (this command wraps its --audit-fix action)
- `/novel-continue`: Detect last chapter and write next
- `/novel-write`: Full pipeline write
- `/novel-draft`: Quick draft without quality loop
