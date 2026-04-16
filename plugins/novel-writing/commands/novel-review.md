---
name: novel-review
description: Review, audit, revise, and approve chapters
---

# /novel-review — Chapter Review, Audit & Revise

## CRITICAL: Use Subagents

This command is an **orchestrator only**. Spawn dedicated agents via the Agent tool:
- Auditor → `subagent_type: "novel-writing:auditor"`
- Reviser → `subagent_type: "novel-writing:reviser"`
Do NOT read truth files or evaluate audit dimensions directly. Run deterministic scripts (Track B) via Bash.

## Pipeline Rules

Same as `/novel-write`: do NOT manually edit truth file JSONs, do NOT re-run scripts that succeeded, do NOT skip stages. If a script fails, use the designated recovery command — never manually patch JSON files. See `/novel-write → Pipeline Rules` for full list.

## Usage
/novel-review [action] [options]

## ChapterMeta Integration (REQ-F-7, REQ-NF-3)

All review actions read from and write to `story/state/chapter-meta.json` (replaces review-status.json).

### Status Transitions in Review
```
drafted → auditing                  (entering audit for a drafted chapter)
incubating → auditing               (entering audit for an incubating chapter)
auditing → audit-passed             (criticalCount == 0)
auditing → audit-failed             (criticalCount > 0, entering revision)
audit-failed → audit-passed         (re-audit after successful revision)
audit-failed → state-degraded       (settlement validation fails during revision)
audit-passed → ready-for-review     (post-audit, awaiting human approval)
ready-for-review → approved         (--approve)
approved → incubating               (--rewrite: chapter removed and re-created)
```

### Backward Compat
If `chapter-meta.json` does not exist but `review-status.json` exists, migrate first (see novel-write.md Backward Compat section).

## Actions

### Default: `/novel-review <N>`
Run audit + auto-revise on chapter N (equivalent to `--audit-fix <N>`).

### --audit `<N>`
Run full quality audit on chapter N and display the report. No revision is performed.

**Process:**
1. Validate chapter file exists
2. Read or create ChapterMeta. Set status to `auditing`.
3. Pre-audit validation (deterministic, zero LLM):
   ```bash
   python3 $.plugin.directory/scripts/pipeline/post-write-validator.py "$CHAPTER_FILE" "$LANGUAGE" "$BOOK_RULES_FILE"
   ```
   If postWriteErrors is non-empty → spot-fix revision before audit → replace chapter file
4. Run audit (parallel execution):
   - Track A: Spawn auditor agent (LLM-based, dimensions 1-19, 24+)
     The auditor agent has Read-only tools — it returns AuditResult JSON as text in its response.
     **Orchestrator** must write this JSON to `$RUNTIME_DIR/chapter-XXXX.llm-audit.json`.
   - Track B (concurrent, no LLM):
     ```bash
     python3 $.plugin.directory/scripts/detect/run-all-deterministic.py "$CHAPTER_FILE" > chapter-XXXX.deterministic.json
     python3 $.plugin.directory/scripts/pipeline/sensitive-words.py "$CHAPTER_FILE" > chapter-XXXX.sensitive.json
     ```
5. Three-source merge (also updates chapter-meta.json status + auditIssues):
   ```bash
   python3 $.plugin.directory/scripts/pipeline/build-audit-report.py \
     --chapter "$CHAPTER_NUM" \
     --llm-audit chapter-XXXX.llm-audit.json \
     --deterministic chapter-XXXX.deterministic.json \
     --sensitive-words chapter-XXXX.sensitive.json \
     --output "$RUNTIME_DIR/chapter-XXXX.audit.json" \
     --book-dir "$BOOK_DIR"
   ```
6. Audit drift guidance:
   ```bash
   python3 $.plugin.directory/scripts/pipeline/persist-audit-drift.py \
     --book-dir "$BOOK_DIR" --chapter "$CHAPTER_NUM" \
     --audit-report "$RUNTIME_DIR/chapter-XXXX.audit.json" --language "$LANGUAGE"
   ```
7. Update ChapterMeta: `auditIssues = {critical, warning, info}`, `status → audit-passed` (if 0 critical) or `audit-failed` (if critical > 0)
8. Display formatted audit summary

**Output:**
```
Audit Report: Chapter 15

ChapterMeta status: auditing → audit-passed

Deterministic Checks:
✅ Dim 20 (Paragraph uniformity): PASS (CV = 0.22)
⚠️  Dim 21 (Hedge density): WARNING (4.2 per 1000 chars)
   Flagged: "似乎", "可能", "或许" (paragraphs 5, 8, 12)
✅ Dim 22 (Formulaic transitions): PASS
✅ Dim 23 (List-like structure): PASS

LLM Judgment:
✅ Dim 1 (OOC): PASS
❌ Dim 2 (Timeline): FAIL - Character arrives before departing
   Location: Paragraph 12
   Suggestion: Add travel scene or adjust timeline
✅ Dim 3 (Lore conflict): PASS
... (remaining dimensions)

Overall Verdict: FAIL
- Critical issues: 1
- Warning issues: 2
- Info issues: 0

ChapterMeta status: audit-failed

Critical Issues:
1. [Dim 2] Timeline inconsistency at paragraph 12
   Suggestion: Add travel scene or adjust timeline

Literary Quality Commentary:
The chapter maintains good pacing and character voice, but the timeline
issue needs resolution before approval.
```

**Verbose mode** (`--audit <N> --verbose`): Includes full dimension definitions, detailed issue descriptions, and all truth file cross-references used in evaluation.

### --audit-fix `<N>`
Run audit on chapter N, then auto-revise if critical issues are found (self-correction loop, max rounds from `book.json` `qualityGates.maxAuditRetries`, default 2).

**Process:**
1. Read or create ChapterMeta. Set status to `auditing`.
2. Run full audit (same as `--audit` — includes pre-audit validation, parallel Track A+B, three-source merge)
3. If `criticalIssues == 0`: report PASS, set ChapterMeta status to `audit-passed` then `ready-for-review`, done
4. If `criticalIssues > 0`: set ChapterMeta status to `audit-failed`, enter self-correction loop
   - Select revision mode: `spot-fix` (≤3 critical) or `rewrite` (>3 critical)
   - Spawn reviser agent → revisedContent + revisionDelta (written to story/runtime/chapter-<NNNN>.revision-delta.json)
   - Word count check: verify delta within mode limit (spot-fix ±10%, rewrite ±20%)
   - AI-tell regression guard: compare pre/post `run-all-deterministic.py` failed count
     If post > pre → discard revision, keep original, skip re-persist/re-audit
   - **Re-persist via apply-delta.py** (same invocation writer Phase 2 uses):
     ```bash
     python3 $.plugin.directory/scripts/pipeline/apply-delta.py \
       "$BOOK_DIR" "$BOOK_DIR/story/runtime/chapter-$CHAPTER_PAD.revision-delta.json"
     ```
     Any `DeltaValidationError` exits 1 with a structured stderr message. `state-manager.py recovery` will pick it up and retry settlement.
   - Incremental re-audit:
     a. Extract failed dims (`incremental-audit.py --mode dimensions`)
     b. Spawn auditor with `--dimensions <failed-ids>` (temp 0)
     c. Re-run Track B (`run-all-deterministic.py` + `sensitive-words.py`) on revised content
     d. Three-source merge via `build-audit-report.py`
     e. Restore lost issues (`incremental-audit.py --mode full`)
   - Save revision log (`save-revision-log.py`)
   - Update audit drift (`persist-audit-drift.py`)
   - Repeat until `criticalIssues == 0` or max rounds reached
   - Update ChapterMeta each round: `auditIssues`, `revisionCount++`
5. Display revision summary with rounds used and final status
6. Update ChapterMeta: `status → audit-passed → ready-for-review` (if passed) or remain `audit-failed` (if max rounds exceeded)

**Self-correction loop:**
```
Round 1: Apply fixes based on audit report
  → Reviser (spot-fix/rewrite) → word count check → AI-tell regression guard
  → Re-persist truth files → Incremental re-audit (LLM + Track B + merge)
  → save-revision-log.py → persist-audit-drift.py
  → criticalIssues == 0? Done. Otherwise → Round 2

Round 2: Targeted fixes for remaining issues
  → Same flow as Round 1
  → criticalIssues == 0? Done. Otherwise → STOP, report failure
```

**Loop rules:**
- Max rounds from `book.json` `qualityGates.maxAuditRetries` (default 2, override with `--max-rounds <N>`)
- **qualityGates.pauseAfterConsecutiveFailures** (default 3): If N consecutive chapters fail audit after max retries, pause and prompt user for guidance
- Only critical issues trigger additional rounds; warnings/info do not
- AI-tell regression guard: if revision introduces more deterministic failures, pre-revision content is kept
- A single "block"-severity sensitive word forces audit failure regardless of LLM result
- Between rounds: compare audit results, adjust strategy for next round

**Successful output:**
```
Revising Chapter 15 (mode: spot-fix)

Round 1:
- Fixed timeline inconsistency (added travel scene)
- Word count: 3000 → 3150 (+5%)
- Re-running audit...

Audit Result: PASS
- All critical issues resolved

ChapterMeta: audit-failed → audit-passed → ready-for-review

Revision Complete:
- Rounds used: 1/2
- Final word count: 3150
- Status: SUCCESS
```

**Failed output (max rounds exceeded):**
```
Revising Chapter 15 (mode: rewrite)

Round 1-2: [revision details per round]

Revision Failed:
- Rounds used: 2/2 (max exceeded)
- Status: FAILURE
- Remaining issues: 1 critical

ChapterMeta status: audit-failed

Remaining Critical Issues:
1. [Dim 4] Power scaling inconsistency
   Recommendation: Add power-up event in previous chapter

Manual intervention required.
```

**Revision modes:**
- **spot-fix** (default for ≤3 critical): Targeted issue resolution, minimal changes, preserve structure, word count ±10%
- **rewrite** (default for >3 critical): Major rework, add/remove content, word count ±20%
- **polish**: Minor style fixes only (word choice, flow, grammar), no structural changes
- **anti-detect**: Aggressive AI pattern removal targeting dimensions 20-23, preserve meaning
- Override with `--mode <mode>`

### --list
List chapters with quality metrics from ChapterMeta.

**Process:**
1. Read `story/state/chapter-meta.json`
2. Display all chapters grouped by status

**Output:**
```
Chapter Status Overview:

Ready for Review:
  Ch 15: 破灭之始 (3,120 words) — audit: 0 critical, 1 warning
  Ch 16: 觉醒 (2,980 words) — audit: 0 critical, 0 warnings

Audit Failed:
  Ch 17: 新的开始 (3,050 words) — audit: 1 critical (Dim 2: Timeline)

Drafted (not yet audited):
  Ch 18: 修炼之路 (2,950 words)

Approved:
  Ch 1-14: approved

Total: 18 chapters (14 approved, 2 ready-for-review, 1 audit-failed, 1 drafted)
```

### --approve `<N>`
Approve individual chapter.

**Process:**
1. Read ChapterMeta for chapter N
2. Validate chapter status is `ready-for-review` (warn if not, proceed anyway)
3. Update ChapterMeta: `status → approved`, `approvedAt = now`, `updatedAt = now`
4. Report success

**Output:**
```
✅ Chapter 15 approved

ChapterMeta status: ready-for-review → approved
Approved at: 2026-04-14 12:00
```

### --approve-all
Approve all chapters with status `ready-for-review`.

**Process:**
1. Read ChapterMeta
2. Find all chapters with `status == "ready-for-review"`
3. Update each: `status → approved`, `approvedAt = now`, `updatedAt = now`

**Output:**
```
Approving all ready-for-review chapters...

✅ Chapter 15 approved (ready-for-review → approved)
✅ Chapter 16 approved (ready-for-review → approved)

Total: 2 chapters approved
```

### --rewrite `<N>`
Rewrite chapter and cascade-delete all subsequent chapters (REQ-F-1, REQ-F-7).

**Process:**
1. Find all chapters >= specified chapter number
2. Display deletion preview with confirmation prompt
3. If confirmed:
   - Apply reverse deltas for all deleted chapters (sort by chapter descending, apply reverse operations — reuse --undo logic)
   - Delete chapter files
   - Remove deleted chapters from ChapterMeta (remove entries where number >= N)
   - Remove from chapter_summaries.json
   - Validate truth files after all reversals
   - Regenerate markdown projections from rolled-back JSON state
   - Update book.json chapter count
4. Report deletion and suggest next action

**Confirmation Prompt:**
```
⚠️  This will delete:
- Chapter 15: 破灭之始 (3,120 words, status: approved)
- Chapter 16: 觉醒 (2,980 words, status: ready-for-review)
- Chapter 17: 新的开始 (3,050 words, status: drafted)
Total: 3 chapters, 9,150 words

Truth files will be rolled back using reverse deltas.

This action cannot be undone.
Confirm deletion? (yes/no):
```

**After Confirmation:**
```bash
# Apply reverse deltas (newest first, REQ-F-1) — single script handles all chapters
python3 $.plugin.directory/scripts/pipeline/reverse-delta.py \
  --book-dir "$BOOK_DIR" --from-chapter "$N"
# reverse-delta.py runs schema-validate.py internally on success
# On failure (exit 1), truth files are restored to pre-reversal state

# Delete chapter files (find by number prefix, fallback to old format)
for ch in 15 16 17; do
  PADDED=$(printf '%04d' $ch)
  FILE=$(ls "$BOOK_DIR/chapters/${PADDED}_"*.md 2>/dev/null | head -1)
  if [ -z "$FILE" ]; then
    FILE="$BOOK_DIR/chapters/chapter-${PADDED}.md"
  fi
  rm -f "$FILE"
done

# Safe state updates via Python json_utils (replaces jq)
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from lib.json_utils import update_json
book_dir = '$BOOK_DIR'
from_ch = $FROM_CH
update_json(f'{book_dir}/story/state/chapter-meta.json',
    lambda d: {**d, 'chapters': [c for c in d['chapters'] if c['number'] < from_ch]})
update_json(f'{book_dir}/story/state/chapter_summaries.json',
    lambda d: {**d, 'chapters': [r for r in d['chapters'] if r['chapter'] < from_ch]})
"

# Regenerate markdown projections
python3 $.plugin.directory/scripts/pipeline/markdown-render.py "$BOOK_DIR/story/state/chapter_summaries.json" "$BOOK_DIR/story/chapter_summaries.md"

# Update book.json chapter count
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from lib.chapter_utils import discover_chapters
from lib.json_utils import update_json
count = len(discover_chapters('$BOOK_DIR/chapters'))
update_json('$BOOK_DIR/book.json', lambda d: {**d, 'chapterCount': count})
"
```

**Report:**
```
Deleted chapters 15-17.
- Reverse deltas applied: 3 chapters
- Truth files rolled back and validated
- ChapterMeta updated: 3 entries removed

Remaining chapters: 14
Total words removed: 9,150

Next steps:
1. Run /novel-write to continue from chapter 15
```

## Options
- `<N>` (no flag): Default to `--audit-fix <N>`
- `--audit <N>`: Run audit only on chapter N
- `--audit-fix <N>`: Run audit + auto-revise on chapter N
- `--list`: List chapters with status from ChapterMeta
- `--approve <N>`: Approve chapter N (sets ChapterMeta status to approved)
- `--approve-all`: Approve all ready-for-review chapters
- `--rewrite <N>`: Cascade rewrite from chapter N (removes chapters from ChapterMeta)
- `--book <id>`: Target book
- `--verbose`: Show full audit details (with `--audit` or `--audit-fix`)
- `--mode <mode>`: Override revision mode (spot-fix, rewrite, polish, anti-detect)
- `--max-rounds <N>`: Max revision rounds (default: from book.json qualityGates.maxAuditRetries, fallback 2)

## Implementation Steps

### Step 1: Load ChapterMeta
Read or create `books/<id>/story/state/chapter-meta.json`:
```json
{
  "schemaVersion": 1,
  "lastUpdated": "2026-04-14T12:00:00Z",
  "chapters": [
    {
      "number": 15,
      "title": "破灭之始",
      "status": "ready-for-review",
      "wordCount": 3120,
      "createdAt": "2026-04-14T10:00:00Z",
      "updatedAt": "2026-04-14T11:00:00Z",
      "auditIssues": { "critical": 0, "warning": 1, "info": 0 },
      "lengthWarnings": [],
      "lengthTelemetry": { "target": 3000, "actual": 3120, "adjustment": "none" },
      "tokenUsage": { "prompt": 12000, "completion": 5000, "total": 17000 },
      "revisionCount": 1
    }
  ]
}
```

If `chapter-meta.json` missing but `review-status.json` exists: migrate (see novel-write.md Backward Compat section).

### Step 1b: Pre-check Optional Files
Check existence of these conditional files and record which ones exist.
Only include existing files when spawning subagents — do NOT pass missing files to any agent.
- `story/style_guide.md` — exists only after `/novel-style` has been run
- `story/parent_canon.md` — exists only for spinoff books (`book.json` has `parentBookId`)
- `story/fanfic_canon.md` — exists only for fanfic books (`book.json` has `fanficMode`)

### Step 2: Route Action
Parse command arguments and route to the appropriate handler:

```
if no flag, just <N>     → run --audit-fix handler
if --audit <N>           → run audit handler
if --audit-fix <N>       → run audit-fix handler
if --list                → run list handler
if --approve <N>         → run approve handler
if --approve-all         → run approve-all handler
if --rewrite <N>         → run rewrite handler
```

### Step 3: Audit Handler (--audit)
1. Validate chapter file: find by number prefix `books/<id>/chapters/XXXX_*.md`, fallback `chapter-XXXX.md`
2. Read ChapterMeta. Set status to `auditing` if current status allows it.
3. Pre-audit validation (deterministic, zero LLM):
   ```bash
   python3 $.plugin.directory/scripts/pipeline/post-write-validator.py "$CHAPTER_FILE" "$LANGUAGE" "$BOOK_RULES_FILE"
   ```
   If postWriteErrors is non-empty → spot-fix revision → replace chapter file
4. Run audit (parallel execution):
   - **Track A**: Spawn auditor agent (LLM-based, dim 1-19, 24+)
     The auditor agent has Read-only tools — it returns AuditResult JSON as text.
     **Orchestrator** must write this JSON to `$RUNTIME_DIR/chapter-XXXX.llm-audit.json`.
   - **Track B** (concurrent, no LLM):
     ```bash
     python3 $.plugin.directory/scripts/detect/run-all-deterministic.py "$CHAPTER_FILE" > chapter-XXXX.deterministic.json
     python3 $.plugin.directory/scripts/pipeline/sensitive-words.py "$CHAPTER_FILE" > chapter-XXXX.sensitive.json
     ```
   Track B covers:
   - Dim 20-23: AI-tell detection (paragraph uniformity, hedge density, formulaic transitions, list-like structure)
   - 7 heuristic rules: repetitive structures, emotional escalation, summarization, sensory detail, paragraph rhythm, character voice, formulaic openings
   - Dim 27: Sensitive-word detection ("block" severity forces audit failure)
5. If deterministic scripts fail: mark dimensions 20-23 as "skipped", continue with LLM audit, add warning to report
6. Three-source merge (also updates chapter-meta.json status + auditIssues):
   ```bash
   python3 $.plugin.directory/scripts/pipeline/build-audit-report.py \
     --chapter "$CHAPTER_NUM" \
     --llm-audit chapter-XXXX.llm-audit.json \
     --deterministic chapter-XXXX.deterministic.json \
     --sensitive-words chapter-XXXX.sensitive.json \
     --output "$RUNTIME_DIR/chapter-XXXX.audit.json" \
     --book-dir "$BOOK_DIR"
   ```
7. Audit drift guidance:
   ```bash
   python3 $.plugin.directory/scripts/pipeline/persist-audit-drift.py \
     --book-dir "$BOOK_DIR" --chapter "$CHAPTER_NUM" \
     --audit-report "$RUNTIME_DIR/chapter-XXXX.audit.json" --language "$LANGUAGE"
   ```
8. Update ChapterMeta:
   - `auditIssues = {critical: <count>, warning: <count>, info: <count>}`
   - `status → audit-passed` (if 0 critical) or `audit-failed` (if critical > 0)
   - `updatedAt = now`
9. Display formatted summary (standard or verbose)

### Step 4: Audit-Fix Handler (--audit-fix)
1. Read ChapterMeta, set status to `auditing`
2. Run audit handler (Step 3)
3. Check audit verdict:
   - `criticalIssues == 0` → set ChapterMeta status `audit-passed` then `ready-for-review`, report PASS, done
   - `criticalIssues > 0` → proceed to revision loop
4. Auto-select revision mode:
   ```
   if criticalIssues <= 3:  mode = "spot-fix"
   elif criticalIssues > 3: mode = "rewrite"
   ```
   (Override with `--mode` if specified)
5. Enter self-correction loop (max rounds from `book.json` `qualityGates.maxAuditRetries`, default 2):
   - Spawn reviser agent → revisedContent + revisionDelta (written to story/runtime/chapter-<NNNN>.revision-delta.json)
   - Word count check: verify delta within mode limit
   - AI-tell regression guard: compare pre/post `run-all-deterministic.py` failed count
     If post > pre → discard revision, keep original, skip re-persist/re-audit
   - **Re-persist via apply-delta.py** (same invocation writer Phase 2 uses):
     ```bash
     python3 $.plugin.directory/scripts/pipeline/apply-delta.py \
       "$BOOK_DIR" "$BOOK_DIR/story/runtime/chapter-$CHAPTER_PAD.revision-delta.json"
     ```
     Any `DeltaValidationError` exits 1 with a structured stderr message. `state-manager.py recovery` will pick it up and retry settlement.
   - Incremental re-audit:
     a. Extract failed dims (`incremental-audit.py --mode dimensions`)
     b. Spawn auditor with `--dimensions <failed-ids>` (temp 0)
     c. Re-run Track B (`run-all-deterministic.py` + `sensitive-words.py`) on revised content
     d. Three-source merge via `build-audit-report.py`
     e. Restore lost issues (`incremental-audit.py --mode full`)
     f. Write final result to `chapter-XXXX.audit.json`
   - Save revision log: `save-revision-log.py`
   - Update audit drift: `persist-audit-drift.py` with final audit report
   - Check: `criticalIssues == 0`? → success. Otherwise → next round
   - Between rounds: compare results, adjust strategy
   - Update ChapterMeta each round: `auditIssues`, `revisionCount++`
6. On success: update ChapterMeta `status → audit-passed → ready-for-review`, display summary
7. On failure (max rounds exceeded): keep best version, ChapterMeta status remains `audit-failed`, report remaining issues, recommend manual intervention

### Step 5: List Chapters (--list)
Read ChapterMeta and display grouped by status. No review-status.json read.

### Step 6: Approve Chapter (--approve)
Update ChapterMeta entry for chapter N:
```json
{
  "status": "approved",
  "approvedAt": "2026-04-14T12:00:00Z",
  "updatedAt": "2026-04-14T12:00:00Z"
}
```
Validate that status was `ready-for-review` (warn if not, proceed anyway).

### Step 7: Approve All (--approve-all)
Update all `ready-for-review` chapters to `approved`.

### Step 8: Rewrite Chapter (--rewrite)
1. Read ChapterMeta to identify all chapters >= specified chapter number
2. Display deletion preview with confirmation prompt (includes ChapterMeta status for each chapter)
3. If confirmed:
   - Run `python3 $.plugin.directory/scripts/pipeline/reverse-delta.py --book-dir $BOOK_DIR --from-chapter $N` to apply all reverse deltas (handles discovery, ordering, reversal, and validation internally)
   - Delete chapter files
   - Regenerate markdown projections
   - Update book.json chapter count
4. Report deletion and suggest next action

## Audit Report Storage

Report saved to: `books/<id>/story/runtime/chapter-XXXX.audit.json`

```json
{
  "chapter": 15,
  "timestamp": "2026-04-14T10:30:00Z",
  "dimensions": [
    {
      "id": 2,
      "name": "Timeline consistency",
      "severity": "critical",
      "passed": false,
      "issues": [
        {
          "location": "Paragraph 12",
          "description": "Character arrives before departing",
          "suggestion": "Add travel scene or adjust timeline"
        }
      ]
    }
  ],
  "deterministicResults": {
    "dim20": {"passed": true, "cv": 0.22},
    "dim21": {"passed": false, "density": 4.2, "hedgeWords": ["似乎", "可能"]},
    "dim22": {"passed": true},
    "dim23": {"passed": true},
    "heuristics": {"overallAILikelihood": 0.35}
  },
  "overallVerdict": "fail",
  "criticalIssues": 1,
  "warningIssues": 2,
  "infoIssues": 0,
  "literaryQualityCommentary": "Chapter maintains good pacing..."
}
```

## Revision Log Storage

After each revision round, log to `books/<id>/story/runtime/chapter-XXXX.revision-log.json`:

```json
{
  "chapterNumber": 15,
  "revisions": [
    {
      "round": 1,
      "mode": "spot-fix",
      "timestamp": "2026-04-14T10:35:00Z",
      "beforeWordCount": 3200,
      "afterWordCount": 3150,
      "issuesAddressed": [
        {
          "dimension": 2,
          "description": "Fixed timeline by adding travel scene"
        }
      ],
      "remainingIssues": [],
      "auditVerdict": "pass"
    }
  ]
}
```

## Conditional Audit Dimensions

### Spinoff Dimensions (28-31)
Activated when `book.json` has `parentBookId` set AND `fanficMode` is NOT set:
- Dim 28: Canon event conflict
- Dim 29: Future information leak
- Dim 30: Cross-book world rules
- Dim 31: Spinoff hook isolation

### Fanfic Dimensions (34-37)
Activated when `book.json` has `fanficMode` set:
- Dim 34: Character fidelity (skip if `fanficMode="ooc"`)
- Dim 35: World rule compliance (relaxed if `fanficMode="au"`)
- Dim 36: Relationship dynamics (relaxed if `fanficMode="cp"`)
- Dim 37: Canon event consistency (skip if `fanficMode="au"`)

## Error Handling

### Chapter Not Found
```
Error: Chapter 15 not found
Expected path: books/my-book/chapters/0015_*.md (or legacy chapter-0015.md)
```

### ChapterMeta Record Not Found
If ChapterMeta has no record for the chapter:
- Create new record with `status=incubating`, `createdAt=now`
- Proceed with action
- Warn: "No existing ChapterMeta record for chapter N. Created new record."

### Deterministic Scripts Fail
If `run-all-deterministic.py` fails:
- Log error details
- Mark dimensions 20-23 as "skipped"
- Continue with LLM-only audit
- Add warning to report: "Deterministic checks unavailable, LLM judgment only"

### Truth File Missing
If truth file cannot be read:
- Note in report which file is missing
- Skip dimensions that depend on that file
- Mark skipped dimensions with reason: "Truth file unavailable"
- Continue with remaining dimensions

### Auditor Agent Fails
```
Error: Auditor agent failed
Details: [error message]
Suggestion: Check truth files for corruption, verify chapter format
```

### No Pending Chapters
```
No chapters awaiting review.

Chapter status summary:
- Approved: 14
- Ready-for-review: 0
- Audit-failed: 0
- Drafted: 0
```

### Invalid Rewrite Target
```
Error: Cannot rewrite chapter 1

Rewriting chapter 1 would delete the entire book.

Options:
1. Delete the book: /novel delete --book <id>
2. Rewrite from chapter 2: /novel-review --rewrite 2
```

### Rewrite Cancelled
```
Rewrite cancelled by user.

No chapters were deleted. ChapterMeta unchanged.
```

### Revision Creates New Issues
If revision introduces new critical issues:
1. Revert to previous version
2. Try different revision approach
3. If still failing → escalate to next round with more aggressive mode

### Truth File Persistence Fails During Loop
If truth file persistence fails:
1. Log error
2. Skip truth file update for this round
3. Continue with chapter revision only
4. Mark in revision log: "Truth files not updated due to persistence failure"
5. Update ChapterMeta: set warning in reviewerNotes

### Max Rounds Exceeded
If all rounds exhausted with critical issues remaining:
1. Keep best version (fewest critical issues)
2. ChapterMeta status remains `audit-failed`
3. Report failure with detailed issue list
4. Provide recommendations for manual intervention

For detailed error recovery strategies across all pipeline stages, see `skills/error-recovery/SKILL.md`.

## Automation Mode Behavior

- **batch**: Chapters auto-transition to `approved` after passing audit (skip `ready-for-review` pause)
- **interactive**: Chapters transition to `ready-for-review`, require explicit `--approve`

## Performance Notes

- Audit (deterministic checks): <5 seconds
- Audit (LLM judgment): 30-60 seconds
- Revision per round: 1-3 minutes (depends on mode and chapter length)
- Token usage per audit: ~5000-8000 tokens
- Token usage per revision round: ~5000-15000 tokens
- ChapterMeta file is lightweight (< 100 KB for 500 chapters)
- Rewrite operation includes reverse delta application (proportional to deleted chapters)

## Bilingual Support

Output language matches book's configured language (`book.json` → `language` field):
- **Chinese mode**: Dimension names, issue descriptions, suggestions in Chinese
- **English mode**: All output in English

Detection rules adapt to language:
- Chinese: Detects Chinese-specific hedge words (似乎/可能/或许)
- English: Detects English-specific hedge words (seems/perhaps/maybe)

## Examples

### Audit + Auto-Revise (Default)
```bash
/novel-review 15
```
Equivalent to `--audit-fix 15`. Runs audit, auto-revises if critical issues found. Updates ChapterMeta through status transitions.

### Audit Only
```bash
/novel-review --audit 15
```
Runs audit and displays report. No revision. Updates ChapterMeta: `auditing → audit-passed|audit-failed`.

### Audit + Revise with Explicit Mode
```bash
/novel-review --audit-fix 15 --mode anti-detect
```
Forces anti-detect revision mode regardless of audit results.

### Audit with Verbose Output
```bash
/novel-review --audit 15 --verbose
```

### List Chapters with Status
```bash
/novel-review --list
```
Displays ChapterMeta status overview for all chapters.

### Approve Chapter
```bash
/novel-review --approve 15
```
Transitions ChapterMeta: `ready-for-review → approved`.

### Approve All
```bash
/novel-review --approve-all
```
Approves all `ready-for-review` chapters.

### Cascade Rewrite
```bash
/novel-review --rewrite 15
```
Removes chapters 15+ from ChapterMeta, applies reverse deltas, rolls back truth files.

### Custom Max Rounds
```bash
/novel-review --audit-fix 15 --max-rounds 5
```

### Specific Book
```bash
/novel-review --audit 15 --book my-xuanhuan-novel
```

## Related Commands

- `/novel-write` — Write chapter with auto-audit, updates ChapterMeta through full lifecycle
- `/novel-draft` — Draft chapter (sets ChapterMeta status to `drafted`)
- `/novel-fix` — Quick fix last chapter (wrapper for audit-fix)
- `/novel-continue` — Write next chapter
- `/novel-export` — Export approved chapters
