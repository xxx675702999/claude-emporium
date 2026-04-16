---
name: novel-write
description: Full pipeline write — orchestrates all agents from prepare to revise
---

# /novel-write — Full Pipeline

## CRITICAL: Agent Architecture

This command is an **orchestrator only** — it does NOT read truth files or write chapters itself. Each pipeline stage must be executed by spawning a dedicated subagent via the Agent tool. This is mandatory because:

1. **Context isolation**: Each agent gets its own context window, preventing context bloat
2. **Temperature control**: Preparer/Writer Phase 1 run at 0.7 (creative); Writer Phase 2/Auditor/Reviser run at 0.3 (analytical)
3. **Parallel execution**: Track A (auditor) and Track B (deterministic scripts) run concurrently

**How to spawn agents**: Use the Agent tool with `subagent_type` set to the agent name:
- Preparer → `subagent_type: "novel-writing:preparer"`
- Writer → `subagent_type: "novel-writing:writer"`
- Auditor → `subagent_type: "novel-writing:auditor"`
- Reviser → `subagent_type: "novel-writing:reviser"`

The orchestrator (this command) only: reads `.session.json`, calls Python scripts (apply-delta, build-audit-report, etc.), updates chapter-meta, and coordinates timing. It must NOT read story/*.md truth files or generate chapter prose directly.

## Usage
/novel-write [--count <N>] [--context "<guidance>"] [--book <id>] [--yes] [--dry-run] [--pause-on <stage>] [--batch]

## ChapterMeta Status Lifecycle (REQ-F-7, REQ-NF-3)

ChapterMeta tracks per-chapter state in `story/state/chapter-meta.json`. Every pipeline mutation must update it.

```
Status transitions:
  (new chapter via novel-write) → auditing       (apply-delta.py auto-creates during persist)
  (new chapter via novel-draft) → drafted         (apply-delta.py creates, then step 6 updates)
  drafted → auditing                (novel-review: when auditing a drafted chapter)
  auditing → audit-passed           (audit: criticalCount == 0)
  auditing → audit-failed           (audit: criticalCount > 0, entering revision)
  audit-failed → audit-passed       (re-audit after successful revision)
  audit-failed → state-degraded     (settlement validation fails after retry)
  audit-passed → ready-for-review   (post-audit, awaiting human approval)
  ready-for-review → approved       (novel-review --approve)
  approved → auditing               (novel-review --rewrite: chapter removed and re-created)

Invalid transitions (enforce in code):
  - Cannot skip stages (e.g., drafted → audit-passed)
  - approved is terminal (only rewrite can reset)
  - state-degraded requires manual intervention before re-auditing

Note: chapter-meta records are auto-created by apply-delta.py during Persist.
Do NOT create chapter-meta records manually before Persist.
```

## Pipeline Rules

These rules apply to ALL stages of the pipeline:

1. **Do NOT manually edit truth file JSONs** (`story/state/*.json`). All mutations go through scripts (`apply-delta.py`, `state-manager.py`, `build-audit-report.py`, etc.). If a script fails, use the designated recovery command — never use Read/Write/Edit to patch JSON directly.
2. **Do NOT manually edit chapter files** between stages. The writer writes the chapter; the reviser revises it. The orchestrator never modifies chapter content.
3. **Do NOT re-run a script that already succeeded.** If `apply-delta.py` exits 0, move to the next stage. Re-running causes duplicate entries.
4. **Do NOT skip stages.** Each stage depends on the previous stage's output. Jumping from Write directly to Audit skips Persist and leaves truth files stale.

## Pipeline Stages (REQ-F-6)

```
Prepare (preparer 0.7)
  → intent.md + context.json + rule-stack.yaml + trace.json
Write (writer P1 0.7 + P2 0.3 + inline length check)
  → chapter.md + delta.json
Persist (apply-delta.py — single script handles apply + validate + snapshot + prune)
  → updated truth files [+ auto-consolidation if threshold exceeded]
  → ChapterMeta: status → auditing (or state-degraded on validation failure)
Pre-audit Validation (deterministic, zero LLM)
  ├─ post-write-validator.py → postWriteErrors
  └─ [If errors] spot-fix revision before audit
Audit (parallel execution) — NEVER SKIPPED (REQ-NF-6)
  ├─ Track A: auditor agent (LLM-based, dimensions 1-19, 24+)
  ├─ Track B: run-all-deterministic.py (dim 20-23) + sensitive-words.py
  └─ Three-source merge → build-audit-report.py → audit-report.json
  → persist-audit-drift.py → audit_drift.md
  → ChapterMeta: status → audit-passed | audit-failed, auditIssues updated
[If critical issues] Revise (reviser, single spot-fix pass)
  → AI-tell regression guard (discard if worse)
  → re-persist truth files (apply-delta.py)
  → incremental re-audit (LLM --dimensions + Track B re-run)
  → build-audit-report.py + incremental-audit.py → final audit-report.json
  → save-revision-log.py → revision-log.json
  → persist-audit-drift.py → audit_drift.md (updated)
  → ChapterMeta: status → audit-passed | audit-failed (after re-audit)
Final → ChapterMeta: status → ready-for-review
```

### Stage 1: Prepare
Spawn preparer agent (temp 0.7) → generates chapter intent, selects context, compiles rule stack, and records trace — all in a single agent call.

### Stage 2: Write
Spawn writer agent with preparer outputs + lengthSpec:
- **Phase 1** (creative writing, temp 0.7): reads **only** intent.md + context.json + rule-stack.yaml + style_guide.md + lengthSpec. Does NOT read raw story files — context.json has curated excerpts.
- **Inline length check**: writer uses lengthSpec (softMin/softMax) to self-adjust if outside range (single pass)
- **Phase 2** (settlement, temp 0.3): reads **fresh truth files** (current_state.md, pending_hooks.md, character_matrix.md, etc.) for delta generation. These are read here, not in Phase 1.

### Stage 3: Persist
Pipeline applies delta to truth files via `$.plugin.directory/scripts/pipeline/apply-delta.py` — updates hooks, current state, chapter summaries, manifest, then validates and regenerates markdown projections. After persistence completes, auto-consolidation may trigger (see below).

### Stage 3.5: Pre-audit Validation (deterministic, zero LLM)
Run deterministic post-write checks before LLM audit to catch obvious rule violations at zero cost:
```bash
python3 $.plugin.directory/scripts/pipeline/post-write-validator.py "$CHAPTER_FILE" "$LANGUAGE" "$BOOK_RULES_FILE"
```

If `postWriteErrors` is non-empty:
1. Convert errors to `AuditIssue` format (rule → category, severity → severity)
2. Spawn reviser agent (spot-fix mode) with these issues only
3. Replace chapter file with revised content
4. Continue to Stage 4 with the cleaned content

If `postWriteErrors` is empty, proceed directly to Stage 4.

This prevents wasting LLM audit tokens on content with known deterministic violations (meta-narrative phrases, didactic words, paragraph overflow, etc.).

### Stage 4: Audit (parallel execution)
Pipeline dispatches two tracks concurrently (REQ-F-8):
- **Track A**: Spawn auditor agent (LLM-based, dimensions 1-19, 24+)
- **Track B**: Run deterministic checks (no LLM):
  ```bash
  # AI-tell detection (dimensions 20-23 + 7 heuristic patterns)
  python3 $.plugin.directory/scripts/detect/run-all-deterministic.py "$CHAPTER_FILE" > "$RUNTIME_DIR/chapter-XXXX.deterministic.json"

  # Sensitive-word detection (dimension 27) — built-in lists always active; optional custom words file
  python3 $.plugin.directory/scripts/pipeline/sensitive-words.py "$CHAPTER_FILE" > "$RUNTIME_DIR/chapter-XXXX.sensitive.json"
  ```

Both tracks execute simultaneously. After both complete, merge three sources into a single audit report:
```bash
python3 $.plugin.directory/scripts/pipeline/build-audit-report.py \
  --chapter "$CHAPTER_NUM" \
  --llm-audit "$RUNTIME_DIR/chapter-XXXX.llm-audit.json" \
  --deterministic "$RUNTIME_DIR/chapter-XXXX.deterministic.json" \
  --sensitive-words "$RUNTIME_DIR/chapter-XXXX.sensitive.json" \
  --output "$RUNTIME_DIR/chapter-XXXX.audit.json" \
  --book-dir "$BOOK_DIR"
```

This also auto-updates `chapter-meta.json`: sets `status` to `audit-passed`/`audit-failed` and writes `auditIssues` strings.

**Three-source merge rules:**
- All issues from LLM + deterministic + sensitive-words are combined into `issues[]`
- Each issue is tagged with `source` field ("llm", "deterministic", "sensitive-words")
- A single "block"-severity sensitive word forces `overallVerdict=fail` regardless of LLM result
- `overallVerdict=fail` if `criticalIssues > 0`, `pass` otherwise

After merge, generate audit drift guidance for the next chapter:
```bash
python3 $.plugin.directory/scripts/pipeline/persist-audit-drift.py \
  --book-dir "$BOOK_DIR" --chapter "$CHAPTER_NUM" \
  --audit-report "$RUNTIME_DIR/chapter-XXXX.audit.json" \
  --language "$LANGUAGE"
```

This stage is **non-optional** — every chapter is audited regardless of mode, chapter length, or any other condition (REQ-NF-6).

### Stage 5: Revise (conditional)
If the audit finds critical issues:

1. **Spawn reviser agent** (single spot-fix pass) with chapter, audit issues, truth files, and mode
2. **Word count check**: Run `python3 $.plugin.directory/scripts/pipeline/word-count.py "$REVISED_CHAPTER"` — record `lengthWarning` in ChapterMeta if delta exceeds mode limit (spot-fix ±10%, rewrite ±20%)
3. **AI-tell regression guard**: Compare pre/post deterministic markers:
   ```bash
   # Pre-revision markers (already available from Stage 4 Track B)
   PRE_FAILED=$( python3 -c "import json; d=json.load(open('$PRE_DET')); print(d['deterministic']['overall']['failed'])" )
   # Post-revision markers
   python3 $.plugin.directory/scripts/detect/run-all-deterministic.py "$REVISED_CHAPTER" > "$POST_DET"
   POST_FAILED=$( python3 -c "import json; d=json.load(open('$POST_DET')); print(d['deterministic']['overall']['failed'])" )
   ```
   If `POST_FAILED > PRE_FAILED` → **discard revision**, keep pre-revision content, skip re-audit
4. **Re-persist truth files**: Apply reviser's revisionDelta via apply-delta.py on `story/runtime/chapter-XXXX.revision-delta.json` (same invocation writer Phase 2 uses; any `DeltaValidationError` exits 1 and triggers state-manager.py recovery)
5. **Incremental re-audit** at temperature 0 (deterministic):
   a. Extract failed dimension IDs:
      ```bash
      python3 $.plugin.directory/scripts/pipeline/incremental-audit.py --mode dimensions \
        --audit-report "$RUNTIME_DIR/chapter-XXXX.audit.json"
      ```
   b. Spawn auditor with `--dimensions <failed-ids>` — only re-check previously-failed dimensions
   c. Re-run Track B on revised content:
      ```bash
      python3 $.plugin.directory/scripts/detect/run-all-deterministic.py "$REVISED_CHAPTER" > "$REAUDIT_DET"
      python3 $.plugin.directory/scripts/pipeline/sensitive-words.py "$REVISED_CHAPTER" > "$REAUDIT_SW"
      ```
   d. Merge re-audit results via build-audit-report.py → `chapter-XXXX.reaudit.json`
   e. Restore lost issues and produce final report:
      ```bash
      python3 $.plugin.directory/scripts/pipeline/incremental-audit.py --mode full \
        --audit-report "$RUNTIME_DIR/chapter-XXXX.audit.json" \
        --reaudit-report "$RUNTIME_DIR/chapter-XXXX.reaudit.json" \
        --original-text "$ORIGINAL_CHAPTER" --revised-text "$REVISED_CHAPTER"
      ```
   f. Write final merged result back to `chapter-XXXX.audit.json`
6. **Save revision log**:
   ```bash
   python3 $.plugin.directory/scripts/pipeline/save-revision-log.py \
     --book-dir "$BOOK_DIR" --chapter "$CHAPTER_NUM" \
     --round 1 --mode spot-fix \
     --before-wc "$BEFORE_WC" --after-wc "$AFTER_WC" \
     --issues-addressed "$ADDRESSED_JSON" \
     --remaining-issues "$REMAINING_JSON" \
     --verdict "$VERDICT"
   ```
7. **Update audit drift**: Re-run `persist-audit-drift.py` with the final audit report
8. **Update chapter-meta**: `python3 $.plugin.directory/scripts/pipeline/update-chapter-meta.py "$BOOK_DIR" "$CHAPTER_NUM" --inc-revision`
   (status + auditIssues already updated by `build-audit-report.py --book-dir` in step 5e)
9. At most **qualityGates.maxAuditRetries** revision rounds (default 2) — controlled by `book.json` `qualityGates.maxAuditRetries`
9. If **qualityGates.pauseAfterConsecutiveFailures** consecutive chapters fail after max retries (default 3), pause pipeline and prompt user for guidance — controlled by `book.json` `qualityGates.pauseAfterConsecutiveFailures`

## Automation Modes (REQ-F-17, REQ-F-18)

Read `.session.json` to determine mode. Backward compat: `auto`→`batch`, `semi`→`interactive`, `manual`→`interactive` (with warning that manual mode is removed).

**interactive** (default): Smart pause
- Always pause before write stage — user confirms "Proceed with writing?"
- Pause before revise ONLY when >2 critical issues (severity `"critical"` in audit-report.json)
- When <=2 critical issues: auto-revise without pause
- All other stages run automatically

**batch**: Zero pauses, full automation
- Run all stages sequentially, no pauses for user confirmation
- If audit finds critical issues: auto-execute revision and continue pipeline — never stop or error out
- Designed for unattended multi-chapter generation

Pause logic is implemented in `$.plugin.directory/scripts/pipeline/pause-manager.py` — provides `resolve_mode()` for mode resolution with backward compat, and `should_pause()` for per-stage pause decisions based on mode, audit results, and command flags.

### Command Flags (REQ-F-19)

Flags override session mode for a single invocation:

- `--yes`: Skip all confirmation prompts (equivalent to batch for pause behavior)
- `--dry-run`: Run prepare phase, display intent (goal, conflicts, hook agenda, directives), stop before writing. No chapter file is created.
- `--pause-on <stage>`: Force a pause at the specified stage (`prepare`, `write`, `persist`, `audit`, `revise`), regardless of mode
- `--batch`: Override session mode to batch for this single run

## Process

```
For each chapter (1 to --count):
  1. Read automation mode from .session.json (with backward compat conversion)
     - Apply flag overrides: --yes, --dry-run, --pause-on, --batch
     - Migrate from review-status.json if chapter-meta.json does not exist (see Backward Compat section)
     - (chapter-meta record is auto-created by apply-delta.py in step 5e — do NOT create it here)
     - **Pre-check optional files**: Check existence of these conditional files and record which ones exist.
       Only include existing files when spawning subagents — do NOT pass missing files to any agent.
       - `story/style_guide.md` — exists only after `/novel-style` has been run
       - `story/parent_canon.md` — exists only for spinoff books (`book.json` has `parentBookId`)
       - `story/fanfic_canon.md` — exists only for fanfic books (`book.json` has `fanficMode`)

  1b. Bootstrap truth files (if needed)
     - If any truth file JSON is missing but markdown projection exists:
       Run `python3 $.plugin.directory/scripts/pipeline/state-manager.py bootstrap <book-dir>`
     - Parses markdown tables back to JSON for hooks, summaries, current_state
     - Triggered automatically, no user action required

  2. Spawn preparer agent (temp 0.7)
     - If --pause-on prepare: Wait for user confirmation
     - Output: intent.md, context.json, rule-stack.yaml, trace.json
     - If --dry-run: Display intent (goal, conflicts, hook agenda, directives) and STOP here

  3. Spawn writer agent Phase 1 (creative writing, temp 0.7)
     - If interactive (and not --yes): Wait for user confirmation
     - If --pause-on write: Wait for user confirmation
     - **Inputs** (from preparer + book config — only include optional files confirmed in step 1 pre-check):
       a. `runtime/chapter-XXXX.intent.md` — goal, conflicts, hook agenda, directives
       b. `runtime/chapter-XXXX.context.json` — curated excerpts from story files
       c. `runtime/chapter-XXXX.rule-stack.yaml` — compiled 4-layer rules
       d. `story/style_guide.md` — style rules (**only if file exists**, skip otherwise)
       e. `book.json` — language, genre
       f. lengthSpec: `{target, softMin, softMax, hardMin, hardMax}` computed from book.json chapterWordCount
     - Does NOT read raw story/*.md files — context.json already has preparer's excerpts
     - Output: chapter file (`{XXXX}_{sanitized_title}.md`)
     - Inline length check: writer uses lengthSpec softMin/softMax to self-adjust
       (single pass — deliver as-is regardless of result)

  4. Writer agent Phase 2 (settlement, temp 0.3)
     - **Now reads fresh truth files** for delta generation:
       `current_state.md`, `pending_hooks.md`, `chapter_summaries.md`,
       `character_matrix.md`, `emotional_arcs.md`, `subplot_board.md`,
       `resource_ledger.md` (if exists), `volume_outline.md`, `book_rules.md`
     - Fact extraction across 9 categories
     - Output: delta.json

  5. Pipeline persists truth files via apply-delta.py
     - Run: `python3 $.plugin.directory/scripts/pipeline/apply-delta.py "$BOOK_DIR" "$BOOK_DIR/story/runtime/chapter-XXXX.delta.json"`
     - Exit 0 → proceed to step 5b. Exit 1 → use recovery below. (See Pipeline Rules above.)
     - This single script handles the full persist pipeline:
       a. Apply hookOps, currentStatePatch, chapterSummary, subplotOps, emotionalArcOps, characterMatrixOps, resourceLedgerOps to truth file JSONs
       b. Update manifest.lastAppliedChapter
       c. Validate all truth files via schema-validate.py
       d. Regenerate markdown projections from JSON (all 7 pairs)
       e. Auto-create/update chapter-meta.json (number, title, wordCount, status→auditing)
       f. Create state snapshot (`state-manager.py snapshot` — JSON + markdown)
       g. Auto-cleanup old snapshots (`state-manager.py snapshot-cleanup`)
       h. Prune old runtime files (`runtime-prune.py`)
     - If validation fails → run `python3 $.plugin.directory/scripts/pipeline/state-manager.py recovery <book-dir> <chapter> '<validation-errors-json>'`
       Recovery auto-retries settlement once with validation feedback as correction guidance
       On retry failure: marks chapter `state-degraded` in ChapterMeta and restores old truth files
     - If --pause-on persist: Wait for user confirmation
     - Output: updated truth files + regenerated markdown projections
     - Auto-consolidation check (see below)
     - Update ChapterMeta: status → auditing, wordCount from chapter file, lengthTelemetry from inline check

  5b. Pre-audit validation (deterministic, zero LLM)
     - Run `python3 $.plugin.directory/scripts/pipeline/post-write-validator.py "$CHAPTER_FILE" "$LANGUAGE" "$BOOK_RULES_FILE"`
     - If postWriteErrors is non-empty:
       a. Convert errors to AuditIssue format
       b. Spawn reviser (spot-fix) with these issues only
       c. Replace chapter file with revised content
       d. Sync chapter filename: `python3 $.plugin.directory/scripts/lib/chapter_utils.py rename-chapter "$CHAPTER_FILE"` — if title changed during revision, this renames the file to match the new title. Update `$CHAPTER_FILE` to the returned path if non-empty
     - If postWriteErrors is empty: proceed directly to step 6

  6. Audit (parallel execution) — NEVER SKIPPED (REQ-NF-6)
     - Track A: Spawn auditor agent (LLM-based, dimensions 1-19, 24+)
       The auditor agent has Read-only tools — it returns AuditResult JSON as text in its response.
       **Orchestrator** must write this JSON to `$RUNTIME_DIR/chapter-XXXX.llm-audit.json`.
     - Track B (concurrent, no LLM):
       a. `python3 $.plugin.directory/scripts/detect/run-all-deterministic.py "$CHAPTER_FILE"` → `chapter-XXXX.deterministic.json`
       b. `python3 $.plugin.directory/scripts/pipeline/sensitive-words.py "$CHAPTER_FILE"` → `chapter-XXXX.sensitive.json`
     - Three-source merge (also updates chapter-meta.json status + auditIssues):
       ```bash
       python3 $.plugin.directory/scripts/pipeline/build-audit-report.py \
         --chapter "$CHAPTER_NUM" \
         --llm-audit "$RUNTIME_DIR/chapter-XXXX.llm-audit.json" \
         --deterministic "$RUNTIME_DIR/chapter-XXXX.deterministic.json" \
         --sensitive-words "$RUNTIME_DIR/chapter-XXXX.sensitive.json" \
         --output "$RUNTIME_DIR/chapter-XXXX.audit.json" \
         --book-dir "$BOOK_DIR"
       ```
     - Audit drift guidance:
       ```bash
       python3 $.plugin.directory/scripts/pipeline/persist-audit-drift.py \
         --book-dir "$BOOK_DIR" --chapter "$CHAPTER_NUM" \
         --audit-report "$RUNTIME_DIR/chapter-XXXX.audit.json" --language "$LANGUAGE"
       ```
     - If --pause-on audit: Wait for user confirmation (after merge, before revise decision)
     - Update ChapterMeta: auditIssues = {critical, warning, info}, status → audit-passed | audit-failed

  7. If critical issues > 0:
     - If interactive + criticalCount > 2 (and not --yes): Wait for user confirmation
     - If interactive + criticalCount <= 2: Auto-revise without pause
     - If batch: Auto-revise without pause
     - If --pause-on revise: Wait for user confirmation
     - 7a. Spawn reviser agent (single spot-fix pass) → revisedContent + revisionDelta (written to story/runtime/chapter-<NNNN>.revision-delta.json)
     - 7b. Word count check: `python3 $.plugin.directory/scripts/pipeline/word-count.py "$REVISED_CHAPTER"`
       Record lengthWarning in ChapterMeta if delta exceeds mode limit
     - 7c. AI-tell regression guard:
       Compare pre-revision deterministic.overall.failed (from step 6 Track B)
       vs post-revision `python3 $.plugin.directory/scripts/detect/run-all-deterministic.py "$REVISED_CHAPTER"`
       If post > pre → discard revision, keep original, skip steps 7d-7g
     - 7d. **Re-persist via apply-delta.py** (same invocation writer Phase 2 uses):
       ```bash
       python3 $.plugin.directory/scripts/pipeline/apply-delta.py \
         "$BOOK_DIR" "$BOOK_DIR/story/runtime/chapter-$CHAPTER_PAD.revision-delta.json"
       ```
       Any `DeltaValidationError` exits 1 with a structured stderr message. `state-manager.py recovery` will pick it up and retry settlement.
     - 7e. Incremental re-audit (temperature 0):
       1. Extract failed dims: `incremental-audit.py --mode dimensions --audit-report <original>`
       2. Spawn auditor with `--dimensions <failed-ids>`
       3. Re-run Track B: `run-all-deterministic.py` + `sensitive-words.py` on revised content
       4. Three-source merge via `build-audit-report.py` → `chapter-XXXX.reaudit.json`
       5. Restore lost issues: `incremental-audit.py --mode full --audit-report <original> --reaudit-report <reaudit> --original-text <pre> --revised-text <post>`
       6. Write final merged result to `chapter-XXXX.audit.json`
     - 7f. Save revision log: `save-revision-log.py --book-dir ... --chapter ... --round ... --mode ... --verdict ...`
     - 7g. Update audit drift: `persist-audit-drift.py` with final audit report
     - Update ChapterMeta: status → audit-passed | audit-failed, auditIssues updated, revisionCount++
     - Repeat from 7a if criticalIssues > 0 and rounds < maxAuditRetries (default 2)

  8. Update ChapterMeta: status → ready-for-review, updatedAt = now
  9. Report chapter completion

  Next chapter...
```

## ChapterMeta Management (REQ-F-7, REQ-NF-3)

### File Location
`books/<id>/story/state/chapter-meta.json`

### Initialization
If `chapter-meta.json` does not exist, create with:
```json
{
  "schemaVersion": 1,
  "lastUpdated": "<ISO 8601 now>",
  "chapters": []
}
```

### Backward Compat: Migrate from review-status.json
If `chapter-meta.json` does not exist but `review-status.json` exists:
1. Read `review-status.json`
2. For each chapter in the old format, create a ChapterMeta record:
   - `number`: from old `chapterNumber`
   - `title`: from chapter file heading (read first line of chapter file, found by number prefix)
   - `status`: map old `pending` → `ready-for-review`, old `approved` → `approved`, old `rejected` → `audit-failed`, old `revising` → `audit-failed`, old `drafting` → `drafted`, old `published` → `approved`, old `imported` → `approved`, old `card-generated` → `ready-for-review`
   - `wordCount`: from old `wordCount` or 0
   - `createdAt` / `updatedAt`: from old `reviewedAt` or current timestamp
   - `auditIssues`, `lengthWarnings`, `lengthTelemetry`, `tokenUsage`: omitted (no data in old format)
3. Write `chapter-meta.json` with migrated records
4. Do NOT delete `review-status.json` (keep for reference)

### Update Helpers
When updating ChapterMeta, always:
- Read the full file, modify the target chapter record (or append new), write back
- Set `updatedAt` on the modified record and `lastUpdated` on the root object
- Sort `chapters` array by `number` ascending
- Preserve all existing records (only modify the target chapter)

### Querying Chapter Status
To find the current state of a chapter:
```python
import json
with open('story/state/chapter-meta.json') as f:
    meta = json.load(f)
record = next((c for c in meta['chapters'] if c['number'] == chapter_number), None)
```

## Auto-Consolidation (absorbs /novel-consolidate per REQ-F-9)

After the Persist stage (step 5), the pipeline checks whether chapter summaries exceed the consolidation threshold. This eliminates the need for a separate `/novel-consolidate` command.

### Trigger Condition
- Read `chapter_summaries.json` entry count after persistence
- If count exceeds threshold (default: 50 chapters per volume), trigger consolidation
- Threshold is configurable in `book.json` via `consolidationThreshold` (default: 50)

### Consolidation Process
1. Group chapters into volumes (threshold determines chapters per volume)
2. Run consolidation script:
   ```bash
   python3 $.plugin.directory/scripts/pipeline/consolidate-summaries.py "$BOOK_DIR" "$CHAPTER_NUM"
   ```
3. Generate volume-level summaries for older chapters (LLM-based summarization)
4. Write to `volume_summaries.json` + regenerate `volume_summaries.md` projection
5. Keep most recent N chapters (= threshold) as individual summaries
6. Update `book.json` consolidation metadata

### Isolation Guarantees
- Consolidation runs **after** the current chapter's truth files are persisted and validated
- Consolidation writes to `volume_summaries.json` — a separate file from `chapter_summaries.json`
- No conflict with chapter generation: the writer has already completed its work
- If consolidation fails, the chapter is still considered successfully written (consolidation failure is non-fatal)

### Consolidation Strategy
- **First N chapters**: Use individual chapter summaries (full detail)
- **Older chapters**: Consolidate into volume summaries (10-15 key events, character arcs, subplot status per volume)
- **Context window savings**: 80-90% for older chapters
- **Preparer agent**: Loads volume summaries for older chapters, individual summaries for recent chapters

## Runtime Pruning (REQ-F-20)

After the Persist stage, the pipeline runs `python3 $.plugin.directory/scripts/pipeline/runtime-prune.py` to enforce a sliding window cleanup of runtime files. This keeps the `story/runtime/` directory bounded as the book grows.

### Retention Policy
- **Current + 2 previous chapters**: retain all runtime files (intent, context, rule-stack, trace, delta, llm-audit, deterministic, sensitive, audit, reaudit)
- **Older chapters**: retain only `delta.json` and `revision-log.json` (provenance records); delete the other types
- **Delta and revision-log files are NEVER deleted** regardless of chapter age

### Script Interface
```bash
python3 $.plugin.directory/scripts/pipeline/runtime-prune.py <book-dir> <current-chapter>
```

### Idempotency
The script is safe to run multiple times. If files are already pruned, it reports no changes.

### Failure Handling
If pruning fails, the pipeline continues — pruning failure is non-fatal (the chapter is already persisted).

## Options
- `--count <N>`: Number of chapters to write (default: 1)
- `--context "<text>"`: Additional guidance for this chapter
- `--book <id>`: Target book (default: active book)
- `--yes`: Skip all confirmation prompts (overrides interactive pause behavior)
- `--dry-run`: Run prepare phase, display intent (goal, conflicts, hook agenda, directives), stop before writing
- `--pause-on <stage>`: Force a pause at the specified stage (`prepare`, `write`, `persist`, `audit`, `revise`)
- `--batch`: Override session mode to batch for this single run

## Output Example
```
Writing Chapter 15...

Mode: interactive (smart pause: always before write, before revise only if >2 critical)

Stage 1: Prepare
✅ Prepare: Generated intent (goal: Confront mentor), selected context (8.2K chars),
   compiled rule stack (4 layers), recorded trace

Stage 2: Write
⏸️  Write: Ready to generate chapter (3000 words target)
   Proceed? (yes/no): yes
✅ Write P1: Chapter generated (3,120 words)
✅ Length check: Within range (75%-125%), no adjustment needed
✅ Write P2: Extracted 87 facts, generated delta (15 updates, 2 hook ops)

Stage 3: Persist
✅ Persist: Updated 5 truth files, validation passed
   Consolidation: Not triggered (42 chapters, threshold: 50)

Stage 3.5: Pre-audit Validation
✅ Post-write validator: 0 errors (skip pre-audit fix)

Stage 4: Audit (parallel)
✅ Audit Track A (LLM): 1 critical issue
✅ Audit Track B (deterministic): PASS | Sensitive words: PASS
✅ Three-source merge → audit-report.json: FAIL (1 critical issue)
   - [llm] Dim 2: Timeline inconsistency
✅ Audit drift: Generated audit_drift.md (1 issue)

Stage 5: Revise
⏸️  Revise: Ready to fix critical issues (mode: spot-fix)
   Proceed? (yes/no): yes
✅ Revise: Fixed timeline issue (3,000 → 3,150 words, within ±10%)
✅ AI-tell guard: PASS (0 → 0 deterministic failures)
✅ Re-persist: Truth files updated
✅ Re-audit: PASS (0 critical issues)
✅ Revision log: Saved round 1/2
✅ Audit drift: Removed (0 actionable issues)

Chapter 15 complete!
- Word count: 3,150
- Audit: PASS
- Revision rounds: 1
```

## Batch Writing (--count N)
```
/novel-write --count 5

Writing 5 chapters...

Chapter 15: ✅ PASS (3,150 words, 1 revision)
Chapter 16: ✅ PASS (3,080 words, 0 revisions)
Chapter 17: ✅ PASS (3,200 words, 2 revisions)
Chapter 18: ✅ PASS (2,950 words, 0 revisions)
Chapter 19: ✅ PASS (3,100 words, 1 revision)

Batch complete:
- 5 chapters written
- 15,480 total words
- Avg 3,096 words/chapter
- 4 revisions total
```

## Error Handling
- If agent fails: Report error, offer to retry or skip
- If context window overflow: Split chapter, continue in next operation
- If revision fails to resolve issues: Save chapter as-is with audit report
- If auto-consolidation fails: Log warning, proceed (non-fatal)

For detailed error recovery strategies across all pipeline stages, see `skills/error-recovery/SKILL.md`.

## Implementation Notes

### Agent Spawning
Each stage spawns a dedicated agent with appropriate temperature:
- Prepare (preparer): temp 0.7
- Write Phase 1 (writer, creative): temp 0.7, reads only preparer outputs + style_guide + lengthSpec
- Write Phase 2 (writer, settlement): temp 0.3, reads fresh truth files for delta generation
- Pre-audit validation: deterministic only (post-write-validator.py), no LLM
- Audit (parallel dispatch):
  - Track A — auditor agent (LLM-based, dim 1-19, 24+): temp 0.3
  - Track B — deterministic scripts (run-all-deterministic.py + sensitive-words.py): no LLM, runs concurrently with Track A
  - Pipeline merges three sources via build-audit-report.py before revise decision
- Revise (reviser): temp 0.3
- Re-audit (incremental): auditor at temp 0 + Track B re-run on revised content
- Persist: `$.plugin.directory/scripts/pipeline/apply-delta.py` (apply delta → validate → snapshot → prune → render MD projections)

### State Management
- Read `.session.json` at start to determine automation mode (with backward compat: auto→batch, semi→interactive, manual→interactive with warning)
- Apply command flag overrides (--yes, --dry-run, --pause-on, --batch) after mode resolution
- Track chapter progress in runtime directory
- Maintain audit history for revision decisions

### Context Budget
- Preparer enforces 10K char limit for context.json
- If overflow: prioritize recent events, active hooks, current-scene characters

### Chapter Review Cycle

The review cycle runs after the Persist stage. It is orchestrated by the pipeline runner, not the reviser agent.

```
Persist complete (truth files updated)
  │
  ├─ Pre-audit validation (post-write-validator.py):
  │   └─ If errors → spot-fix revision → continue with cleaned content
  │
  ├─ Audit chapter (NEVER SKIPPED, parallel execution):
  │   ┌─ Track A (LLM): Continuity audit (dim 1-19, 24+)
  │   ├─ Track B (deterministic): run-all-deterministic.py (dim 20-23) + sensitive-words.py (dim 27)
  │   └─ build-audit-report.py → three-source merge → audit-report.json
  │
  ├─ persist-audit-drift.py → audit_drift.md (carry-forward guidance)
  │
  ├─ Audit passed? → Done
  │
  └─ Critical issues? → Revision round:
      1. Reviser → single spot-fix pass → revisedContent + revisionDelta (chapter-<NNNN>.revision-delta.json)
      2. Word count check (word-count.py)
      3. AI-tell regression guard:
         Compare pre/post run-all-deterministic.py failed count
         If post > pre → discard revision, keep original, skip to end
      4. Re-persist truth files (apply-delta.py with reviser's updated state)
      5. Incremental re-audit at temperature 0:
         a. incremental-audit.py --mode dimensions → failed dimension IDs
         b. Auditor with --dimensions <failed-ids> (LLM, temp 0)
         c. Re-run Track B (run-all-deterministic.py + sensitive-words.py) on revised content
         d. build-audit-report.py → reaudit report
         e. incremental-audit.py --mode full → restore lost issues → final audit-report.json
      6. save-revision-log.py → revision-log.json
      7. persist-audit-drift.py → updated audit_drift.md
      └─ Return final content + merged audit result
```

Key behaviors:
- At most **qualityGates.maxAuditRetries** revision rounds (default 2) — controlled by `book.json` `qualityGates.maxAuditRetries`. Each round is a single reviser pass (spot-fix).
- **qualityGates.pauseAfterConsecutiveFailures** (default 3): If N consecutive chapters fail audit after max retries, pause pipeline and prompt user for guidance.
- Revision mode is always `spot-fix` in the automated pipeline
- A single "block"-severity sensitive word forces audit failure regardless of LLM result
- AI-tell regression guard: if revision introduces more deterministic failures than it fixes, the pre-revision content is kept and the revision is discarded
- After revision, truth files are re-persisted (revised content may change events/hooks/state)
- Re-audit is **incremental**: only previously-failed dimensions are re-checked by LLM (saves 15-25s), but Track B always re-runs fully on revised content
- Re-audit uses temperature 0 for deterministic comparison
- Lost audit issues (present in first audit but missing in re-audit where text was NOT revised) are restored via `incremental-audit.py` forgetting protection
- Restored issues are marked with `_restored: true` and `_restoreReason` in the merged report
- Revision log is persisted after each round via `save-revision-log.py`
- Audit drift is regenerated after each audit/re-audit via `persist-audit-drift.py`

### Two-Phase Writer
- Phase 1 (creative writing, temp 0.7): generates chapter prose + inline length check
- Phase 2 (settlement, temp 0.3): extracts facts across 9 categories, generates delta.json
- Both phases use the same writer agent with different temperature settings

### Inline Length Check (replaces normalizer)
- After Phase 1 generation, writer runs `word-count.py` and self-adjusts if needed
- Within ±25% of target: no action
- Outside ±25% but within ±50%: single-pass self-expand or self-compress
- Beyond ±50% of target: report failure, proceed to Phase 2 settlement and Audit
- This is a single-pass operation — no retry loop

### File Outputs
```
runtime/
  chapter-XXXX.intent.md          (preparer — chapter intent with hook agenda)
  chapter-XXXX.context.json       (preparer — selected context package)
  chapter-XXXX.rule-stack.yaml    (preparer — compiled 4-layer rule stack)
  chapter-XXXX.trace.json         (preparer — input provenance trace)
  chapter-XXXX.delta.json         (writer Phase 2 — state delta)
  chapter-XXXX.llm-audit.json     (auditor agent — raw LLM AuditResult)
  chapter-XXXX.deterministic.json (run-all-deterministic.py — Track B AI-tell results)
  chapter-XXXX.sensitive.json     (sensitive-words.py — Track B sensitive-word results)
  chapter-XXXX.audit.json         (build-audit-report.py — merged three-source audit report)
  chapter-XXXX.reaudit.json       (build-audit-report.py — re-audit report, if revision occurred)
  chapter-XXXX.revision-log.json  (save-revision-log.py — revision history per round)

chapters/
  XXXX_标题.md                 (writer — new format: zero-padded number + underscore + sanitized title)
  chapter-XXXX.md              (legacy format — still found by backward compat lookup)

story/state/
  manifest.json                (pipeline persist — lastAppliedChapter, projectionVersion)
  current_state.json           (pipeline persist + validator)
  pending_hooks.json           (pipeline persist + validator)
  chapter_summaries.json       (pipeline persist + validator)
  chapter-meta.json            (pipeline — ChapterMeta lifecycle tracking)
  subplot_board.json           (pipeline persist + validator)
  emotional_arcs.json          (pipeline persist + validator)
  character_matrix.json        (pipeline persist + validator)
  resource_ledger.json         (pipeline persist + validator, conditional on numericalSystem)
  volume_summaries.json        (auto-consolidation, if triggered)
```

## Related Commands
- `/novel-draft`: Run prepare + write only (no persist, no audit)
- `/novel-review`: Run audit + revise on existing chapter
- `/novel-continue`: Detect last chapter and write next
- `/novel-fix`: Detect last chapter and run audit + revise
