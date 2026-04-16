---
name: novel-continue
description: Detect last chapter and write next — convenience wrapper for novel-write
---

# /novel-continue — Continue Writing

## CRITICAL: Use Subagents

This command delegates to `/novel-write`, which spawns dedicated agents for each pipeline stage (preparer, writer, auditor, reviser). Do NOT read truth files or write chapter prose directly — use the Agent tool to spawn `novel-writing:preparer`, `novel-writing:writer`, `novel-writing:auditor`, and `novel-writing:reviser` subagents. See `/novel-write` for full pipeline details.

## Usage
/novel-continue [--count <N>] [--context "<guidance>"] [--book <id>]

## Process

```
1. Resolve book directory (--book or active book)
2. Detect last chapter:
   - List all *.md files in chapters/
   - Extract chapter numbers from filename prefix (0001_标题.md → 1, 0042_标题.md → 42, chapter-0001.md → 1)
   - Take max → lastChapter
   - If no chapters found → lastChapter = 0
3. Compute next chapter: nextChapter = lastChapter + 1
4. Invoke /novel-write pipeline starting at nextChapter
   - Forward --count and --context if provided
   - Forward --book if provided
```

### Step 1: Resolve Book Directory

Read `.session.json` `activeBook` field for active book, or use `--book <id>` override.
Verify `books/<id>/book.json` exists.

### Step 2: Detect Last Chapter

```bash
# Shared chapter detection (scripts/lib/chapter_utils.py)
LAST_CHAPTER=$(python3 $.plugin.directory/scripts/lib/chapter_utils.py detect-last "books/<id>/chapters")
NEXT_CHAPTER=$((LAST_CHAPTER + 1))
```

### Step 3: Invoke novel-write Pipeline

Delegate to `/novel-write` with the detected chapter number:

- If `--count` is specified, write N chapters starting from nextChapter
- If `--context` is specified, forward to novel-write as additional guidance
- The full pipeline runs: Prepare → Write → Persist → Audit → [Revise]

## Options
- `--count <N>`: Number of chapters to write (default: 1)
- `--context "<text>"`: Additional guidance for this chapter
- `--book <id>`: Target book (default: active book)

## Output Example

### First Chapter (no existing chapters)
```
Detecting last chapter...
  chapters/ → 0 chapter files found
  Starting from chapter 1

Writing Chapter 1...

Mode: interactive (smart pause: always before write, before revise only if >2 critical)

Stage 1: Prepare
✅ Prepare: Generated intent (goal: Introduce protagonist), selected context (4.1K chars),
   compiled rule stack (4 layers), recorded trace

Stage 2: Write
⏸️  Write: Ready to generate chapter (3000 words target)
   Proceed? (yes/no): yes
✅ Write P1: Chapter generated (3,050 words)
✅ Length check: Within range (75%-125%), no adjustment needed
✅ Write P2: Extracted 52 facts, generated delta (8 updates, 3 hook ops)

Stage 3: Persist
✅ Persist: Updated 5 truth files, validation passed

Stage 4: Audit
✅ Audit: PASS (0 critical issues)

Chapter 1 complete!
- Word count: 3,050
- Audit: PASS
- Revision rounds: 0
```

### Continuing After Existing Chapters
```
Detecting last chapter...
  chapters/ → 14 chapter files found
  Last chapter: 14
  Next chapter: 15

Writing Chapter 15...

[...standard novel-write output...]

Chapter 15 complete!
```

### Batch Continue (--count N)
```
/novel-continue --count 3

Detecting last chapter...
  chapters/ → 14 chapter files found
  Last chapter: 14
  Writing chapters 15-17

Chapter 15: ✅ PASS (3,150 words, 0 revisions)
Chapter 16: ✅ PASS (3,080 words, 1 revision)
Chapter 17: ✅ PASS (3,200 words, 0 revisions)

Batch complete:
- 3 chapters written (15-17)
- 9,430 total words
- Avg 3,143 words/chapter
- 1 revision total
```

## Error Handling

### Book Not Found
```
Error: Book not found
Expected path: books/my-book/book.json

Use /novel --list to see available books.
```

### Chapters Directory Missing
```
Detecting last chapter...
  chapters/ → directory not found, creating it
  Starting from chapter 1

Writing Chapter 1...
```

### novel-write Pipeline Failure
Errors from the underlying novel-write pipeline are reported as-is. See `/novel-write` for full error handling details.

## Implementation Notes

### Chapter Detection Logic
- New format: `chapters/XXXX_标题.md` — extract number from leading digits before underscore
- Old format (backward compat): `chapters/chapter-XXXX.md` — extract number from `chapter-` prefix
- Both formats are detected; the highest chapter number across all formats is used
- Non-matching files in chapters/ are ignored
- Detection runs once at the start, not between batch chapters (batch writes are sequential N+1, N+2, ...)

### Delegation to novel-write
This command is a thin wrapper. All pipeline logic (prepare, write, persist, audit, revise, auto-consolidation) is handled by `/novel-write`. This command only adds:
1. Last chapter detection
2. Next chapter number computation
3. User-friendly output showing the detection result

### Automation Mode
Inherits mode from `.session.json` — same behavior as `/novel-write`.

## Related Commands
- `/novel-write`: Full pipeline write (this command wraps it)
- `/novel-fix`: Detect last chapter and run audit + revise
- `/novel-draft`: Quick draft without quality loop
- `/novel-review`: Review, audit, and approve chapters
