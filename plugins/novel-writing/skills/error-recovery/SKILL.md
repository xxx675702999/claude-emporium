---
name: error-recovery
description: Unified error handling strategies for REQ-F-60 to REQ-F-64
version: 1.0.0
---

# Error Recovery

## Overview

This skill defines error handling strategies for 5 critical error scenarios (REQ-F-60 to REQ-F-64). Each scenario has detection logic, recovery procedure, and fallback strategy.

## Error Scenarios

1. **REQ-F-60**: JSON corruption or missing required fields
2. **REQ-F-61**: Delta logical contradiction
3. **REQ-F-62**: Empty import file or no chapter headings
4. **REQ-F-63**: Context window overflow during writing
5. **REQ-F-64**: First chapter special handling (no existing truth files)

---

## REQ-F-60: JSON Corruption Recovery

### Detection

Truth file JSON is corrupt when:
- File cannot be parsed as valid JSON (syntax error)
- Parsed JSON fails schema-validate.py validation (missing keys, wrong types)

InkOS manages 4 structured state files in `books/<id>/story/state/`:
- `manifest.json` — schema version, language, lastAppliedChapter
- `current_state.json` — protagonist state, location, goals
- `pending_hooks.json` — active plot threads and hook records
- `chapter_summaries.json` — per-chapter summary rows

**Detection point**: `$.plugin.directory/scripts/pipeline/state-manager.py (bootstrap command)` — `loadJsonIfValid()` attempts parse + schema validation on each file

### Recovery Procedure (3-step cascade)

```
1. loadJsonIfValid(filePath, schema)
   ├─ Valid JSON + passes schema → Use it
   └─ Invalid or missing → Go to step 2

2. bootstrapStructuredStateFromMarkdown(bookDir)
   ├─ Parse story/*.md projections (pending_hooks.md, current_state.md, etc.)
   ├─ Reconstruct structured JSON from markdown content
   ├─ Write recovered JSON to state/ directory
   ├─ Success → Log recovery warnings in manifest.migrationWarnings
   └─ Markdown also missing/unparseable → Go to step 3

3. Empty defaults
   ├─ Use schema-valid empty structures (empty arrays, zero chapters)
   ├─ Write to state/ directory
   └─ Continue pipeline with empty state
```

### Fallback Strategy

- Each file recovers independently (one corrupt file does not block others)
- Recovery warnings are accumulated in `manifest.migrationWarnings`
- Pipeline always continues — empty defaults are schema-valid
- No manual review flag; warnings are visible in manifest

### Example

```bash
# Corruption detected
pending_hooks.json fails pending_hooks schema validation

# Recovery step 2: Bootstrap from markdown
Reading pending_hooks.md...
Parsed 5 hook entries from markdown projection
Reconstructed pending_hooks.json validated successfully

# manifest.json migrationWarnings entry
["pending_hooks.json bootstrapped from markdown projection"]
```

---

## REQ-F-61: Delta Validation (Two-Phase)

Delta validation in InkOS uses two distinct phases — structural checks before application, and semantic checks via LLM after application.

### Phase 1: Pre-Apply Structural Validation

**Location**: `$.plugin.directory/scripts/pipeline/state-manager.py (apply-delta command)` — `applyRuntimeStateDelta()`

Structural checks performed before the delta is applied to state:

1. **Chapter ordering**: `delta.chapter > lastAppliedChapter` (no backwards or duplicate chapters)
2. **Chapter summary match**: `chapterSummary.chapter === delta.chapter`
3. **Duplicate detection**: No duplicate summary row for same chapter number
4. **Schema validation**: After computing the next state snapshot, `validateRuntimeState()` checks:
   - All 4 state files pass JSON schema validation
   - No duplicate hook IDs
   - No duplicate chapter summary entries
   - `currentState.chapter` does not exceed `manifest.lastAppliedChapter`

If any structural check fails, the reducer throws an error and the delta is **not** applied.

### Phase 2: Post-Apply Semantic Validation (LLM)

**Location**: `$.plugin.directory/scripts/pipeline/schema-validate.py` — called by pipeline runner **after** the delta is applied

The validator compares old vs new truth file state against the chapter text. It checks for:

1. **State change without narrative support** — truth file says something changed but the chapter text does not describe it
2. **Missing state change** — chapter text describes something happening but the truth file did not capture it
3. **Temporal impossibility** — character moves locations without transition, injury heals without time passing
4. **Hook anomaly** — hook disappeared without being resolved, or new hook has no basis in chapter
5. **Retroactive edit** — truth file change implies something from a previous chapter, not the current one

Output: `PASS` or `FAIL` with per-line warnings. Only hard contradictions trigger `FAIL`; reasonable inferences get `PASS` with warnings.

### Recovery on Failure

- **Structural failure** (Phase 1): Delta rejected, error propagates, pipeline retries settlement
- **Semantic failure** (Phase 2): Flagged as validation warning/failure; pipeline may retry settlement or proceed to audit depending on severity

---

## REQ-F-62: Empty Import File or No Chapter Headings

### Detection

Import file is invalid when:
- File is empty (0 bytes or only whitespace)
- File contains text but no chapter heading patterns detected
- Chapter heading regex matches 0 times

**Detection point**: `/novel create --import` command, before calling chapter-split.py

### Recovery Procedure

```
1. Check file size and content
   ├─ Empty file → Go to step 2
   └─ Has content → Go to step 3

2. Empty file error
   ├─ Report error with guidance
   ├─ DO NOT create empty chapters
   └─ Exit import

3. Check for chapter headings
   ├─ Run chapter-split.py with default patterns
   ├─ 0 matches → Go to step 4
   └─ ≥1 matches → Continue import

4. No headings detected
   ├─ Report error with format guidance
   ├─ Suggest patterns to try
   ├─ DO NOT create single chapter from entire file
   └─ Exit import
```

### Error Messages

**Empty file:**
```
Error: Import file is empty

The file at <path> contains no content.

Expected format:
- Text file with chapter headings
- Chinese: 第1章, 第2章, etc.
- English: Chapter 1, Chapter 2, etc.

Please provide a valid text file with chapter content.
```

**No headings detected:**
```
Error: No chapter headings detected

The file at <path> contains text but no recognizable chapter headings.

Tried patterns:
- Chinese: 第X章, 第X节
- English: Chapter N, CHAPTER N

Suggestions:
1. Check if your chapters use different heading format
2. Use --pattern flag to specify custom regex:
   /novel create --import file.txt --pattern "^Chapter \d+:"
3. If single chapter, use /novel-draft instead of import

Example heading formats:
- 第1章 标题
- Chapter 1: Title
- Chapter One
```

### Fallback Strategy

- Never create empty chapters
- Never treat entire file as single chapter (ambiguous intent)
- Provide clear error message with examples
- Suggest alternative commands if appropriate

---

## REQ-F-63: Context Window Overflow During Writing

### Detection

Stream interruption during chapter generation — the LLM stream terminates before the response is complete.

**Detection point**: LLM provider (handled by Claude Code runtime) — stream error handler wraps partial content in `PartialResponseError`

### Recovery Procedure

**Prevention**: Writer pre-emptively scales `maxTokens` based on the chapter's length spec:
```
creativeMaxTokens = max(8192, ceil(targetWords * 2))
```
This ensures the model has sufficient output budget for the requested chapter length.

**Salvage on interruption**: When the stream is interrupted mid-generation:
1. `PartialResponseError` captures whatever content was received
2. If `partialContent.length >= MIN_SALVAGEABLE_CHARS` (500 chars), the partial content is silently salvaged and used as the chapter output
3. If below the threshold, the error propagates and the pipeline reports failure

There is no chapter-splitting workflow. Partial content is either long enough to use as-is, or the operation fails.

### Fallback Strategy

- Partial content >= 500 chars is treated as a valid (short) chapter
- Partial content < 500 chars causes pipeline failure with error message
- No automatic retry or chapter splitting

---

## REQ-F-64: First Chapter Special Handling

### How InkOS Handles It

There is no explicit `if (chapterNumber === 1)` detection in the preparer or writer. First-chapter handling is implicit:

1. **Empty state files produce graceful defaults**: When state files are missing or empty, `bootstrapStructuredStateFromMarkdown` returns schema-valid empty structures (empty arrays, zero-valued counters). The preparer and writer operate normally with these empty inputs.

2. **Writer receives a text marker**: When `recentChapters` is empty (no previous chapters exist), the writer prompt includes the literal text `"(This is the first chapter, no previous text)"` (`agents/writer.md`). This signals the LLM to write an opening chapter without requiring special code paths.

3. **Preparer uses the same goal-derivation logic for all chapters**: The preparer reads author_intent.md, current_focus.md, genre profile, and volume outline — the same inputs regardless of chapter number. For chapter 1, truth file state is simply empty, so the preparer naturally focuses on setup.

4. **Truth file initialization happens naturally**: The first chapter's settlement phase generates a delta, and `applyRuntimeStateDelta()` creates the initial state. No special initialization step exists — the reducer handles chapter 1 deltas the same as any other.

### Key Design Principle

First-chapter behavior emerges from empty state + standard pipeline, not from branching logic. This avoids special-case code and ensures the pipeline is uniform across all chapters.

---

## Error Logging

All error recovery operations logged to `books/<id>/story/runtime/error-recovery.log`:

```json
{
  "timestamp": "ISO-8601",
  "scenario": "REQ-F-60|REQ-F-61|REQ-F-62|REQ-F-63|REQ-F-64",
  "chapter": number,
  "description": "string",
  "recoveryAction": "string",
  "result": "success|partial|failed",
  "manualReviewRequired": boolean,
  "details": {}
}
```

## Quick Reference

| Scenario | Detection Point | Action | Block Pipeline |
|----------|----------------|--------|----------------|
| REQ-F-60 | $.plugin.directory/scripts/pipeline/state-manager.py (bootstrap command), loadJsonIfValid | 3-step cascade: JSON → markdown → empty defaults | No |
| REQ-F-61 | $.plugin.directory/scripts/pipeline/state-manager.py (apply-delta command) (pre) + $.plugin.directory/scripts/pipeline/schema-validate.py (post) | Structural reject or semantic warning | Structural: Yes, Semantic: No |
| REQ-F-62 | Import command start | Report error, exit | Yes |
| REQ-F-63 | LLM provider (handled by Claude Code runtime), stream handler | Salvage partial content if >= 500 chars | No (if salvageable) |
| REQ-F-64 | Implicit (no special detection) | Empty state + text marker in prompt | No |

**General principle**: Recover when possible, fail gracefully when not, never corrupt data.
