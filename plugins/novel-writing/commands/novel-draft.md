---
name: novel-draft
description: Self-contained draft — runs prepare + write (with settlement + persist), skips quality loop
---

# /novel-draft — Draft Only

## CRITICAL: Use Subagents

This command is an **orchestrator only**. Spawn dedicated agents via the Agent tool for each pipeline stage:
- Preparer → `subagent_type: "novel-writing:preparer"`
- Writer → `subagent_type: "novel-writing:writer"`
Do NOT read truth files or write chapter prose directly. See `/novel-write` for details.

## Pipeline Rules

Same as `/novel-write`: do NOT manually edit truth file JSONs, do NOT re-run scripts that succeeded, do NOT skip stages. See `/novel-write → Pipeline Rules` for full list.

## Usage
/novel-draft [--chapter <N>] [--context "<guidance>"] [--book <id>] [--yes] [--dry-run] [--pause-on <stage>] [--batch]

## Pipeline (REQ-F-2)

Draft runs Prepare + Write (including Settlement + Inline Length Check) + Persist. It skips Audit + Revise. Chapter format is identical to `/novel-write` output (no `## Metadata` block). Delta data comes from real settlement, not fabricated.

```
Prepare (preparer 0.7)
  → intent.md + context.json + rule-stack.yaml + trace.json
Write (writer P1 0.7 + P2 0.3 + inline length check)
  → chapter.md + delta.json
Persist (pipeline function + StateValidatorAgent)
  → updated truth files
  → ChapterMeta: status → drafted
```

## Process

```
1. Read automation mode from .session.json
   - Migrate from review-status.json if chapter-meta.json does not exist (see novel-write Backward Compat section)
   - (chapter-meta record is auto-created by apply-delta.py in step 5 — do NOT create it here)
   - **Pre-check optional files**: Check existence of these conditional files and record which ones exist.
     Only include existing files when spawning subagents — do NOT pass missing files to any agent.
     - `story/style_guide.md` — exists only after `/novel-style` has been run
     - `story/parent_canon.md` — exists only for spinoff books (`book.json` has `parentBookId`)
     - `story/fanfic_canon.md` — exists only for fanfic books (`book.json` has `fanficMode`)

2. Spawn preparer agent (temp 0.7)
   - If --pause-on prepare: Wait for user confirmation
   - Output: intent.md, context.json, rule-stack.yaml, trace.json
   - If --dry-run: Display intent (goal, conflicts, hook agenda, directives) and STOP here

3. Spawn writer agent Phase 1 (creative writing, temp 0.7)
   - If interactive (and not --yes): Wait for user confirmation
   - If --pause-on write: Wait for user confirmation
   - Output: chapter file
   - Inline length check: self-expand or self-compress if outside +/-25% of target
     (single pass — deliver as-is regardless of result)

4. Writer agent Phase 2 (settlement, temp 0.3)
   - Fact extraction across 9 categories
   - Output: delta.json (REAL settlement data, not fabricated)

5. Pipeline persists truth files via apply-delta.py
   - Run: `python3 $.plugin.directory/scripts/pipeline/apply-delta.py "$BOOK_DIR" "$BOOK_DIR/story/runtime/chapter-XXXX.delta.json"`
   - Applies hookOps, currentStatePatch, chapterSummary to truth file JSONs, validates, regenerates MD projections
   - If validation fails after retry → set ChapterMeta status=state-degraded, keep old truth files
   - Output: updated truth files + regenerated markdown projections

6. Update ChapterMeta:
   - status → drafted
   - wordCount from chapter file
   - lengthTelemetry from inline length check
   - updatedAt = now

7. Display draft summary

8. Report chapter completion
```

## Chapter File Format
```markdown
# Chapter 15: [Title]

[Prose content...]
```

No `## Metadata` block. Format is identical to `/novel-write` output (REQ-F-2).

## Output Example
```
Drafting Chapter 15...

Mode: interactive (will pause before write)

Phase 1: Prepare
✅ Prepare: Generated chapter intent (goal: Confront mentor, 2 hooks to advance)
   - Context: 8.2K chars, 45 entries
   - Rule stack: 4 layers, 1 active override
   - Trace: 8 source files

Phase 2: Write
⏸️  Write: Ready to generate chapter (3000 words target)
   Proceed? (yes/no): yes
✅ Write: Chapter generated (3,120 words)

Phase 3: Persist
✅ Persist: Updated 5 truth files, validation passed
✅ ChapterMeta: status → drafted

Draft Summary:
- Word count: 3,120 (target: 3,000 ±10%)
- Language: zh
- Scenes: 3 (training → confrontation → revelation)
- Dialogue: 45% (genre-appropriate)
- Hook operations: 2 advanced, 1 resolved

Chapter saved: chapters/0015_[sanitized_title].md
ChapterMeta status: drafted

Note: Chapter not audited. Run /novel-review to audit and approve.
```

## Use Cases
- Quick draft without quality loop
- Manual review before audit
- Iterative writing (draft → review → redraft)
- Fast prototyping when you want to iterate quickly on content

## ChapterMeta Integration (REQ-F-7, REQ-NF-3)

### Status Transition
- After step 5 (apply-delta.py auto-creates record): `auditing`
- After step 6 (update meta): `drafted`

### When Drafted Chapters Enter Review
When `/novel-review` processes a `drafted` chapter:
- Status transitions: `drafted` → `auditing` (entering audit)
- Subsequent transitions follow the standard lifecycle (see novel-write.md)

### Record Fields Updated by Draft
- `number`: chapter number
- `title`: from chapter file heading
- `status`: `drafted`
- `wordCount`: from inline length check
- `lengthTelemetry`: target, actual, adjustment
- `createdAt`: when record was first created (step 1)
- `updatedAt`: when persist completed (step 6)
- `tokenUsage`: accumulated across preparer + writer phases
- `auditIssues`: omitted (not audited)
- `revisionCount`: 0

## Implementation Notes

### Agent Spawning
- Preparer agent: temp 0.7 (intent generation + context selection)
- Writer agent Phase 1: temp 0.7 (creative writing)
- Writer agent Phase 2: temp 0.3 (settlement — real fact extraction, not fabricated)
- Preparer generates intent, context, rule stack, and trace internally — no pre-existing files required

### Prepare Stage
The preparer agent runs two internal phases:

**Phase A — Generate Intent**:
- Determines chapter number
- Extracts chapter goal (from external context, current_focus, volume_outline, author_intent)
- Collects mustKeep, mustAvoid, styleEmphasis
- Generates hook agenda and structured directives
- Detects and resolves conflicts

**Phase B — Context Selection & Rule Compilation**:
- Selects relevant context from story projections (≤10K chars budget)
- Compiles 4-layer rule stack (hard_facts → author_intent → planning → current_task)
- Builds chapter trace for provenance tracking
- Validates outputs against schemas

Missing control documents (author_intent.md, current_focus.md, etc.) are handled gracefully with defaults — the preparer tolerates missing files without failing.

### Writing Process
1. Load genre profile (from book.json language + genre)
2. Load language skill (zh or en)
3. Apply rule stack (4 layers)
4. Generate prose following intent
5. Execute hook operations
6. Write chapter file

### Inline Length Check (same as novel-write)
- After Phase 1 generation, writer runs `word-count.py` and self-adjusts if needed
- Within ±25% of target: no action
- Outside ±25% but within ±50%: single-pass self-expand or self-compress
- Beyond ±50% of target: report failure, proceed to Phase 2 settlement
- This is a single-pass operation — no retry loop

### Hook Operations
Writer executes hook operations specified in intent:
- **Advance**: Increase pressure level (low → medium → high → critical)
- **Resolve**: Close hook with payoff
- **Plant**: Introduce new hook (if specified)

### Automation Mode
- Reads `.session.json` for mode (with backward compat: auto→batch, semi→interactive, manual→interactive with warning)
- In interactive mode: pauses before write step for user confirmation
- In batch mode: runs all steps immediately, no pauses
- Command flags override session mode: --yes, --dry-run, --pause-on, --batch

## Options
- `--chapter <N>`: Target chapter number (default: next chapter)
- `--context "<text>"`: Additional guidance passed to preparer as external context
- `--book <id>`: Target book (default: active book)
- `--yes`: Skip all confirmation prompts (overrides interactive pause behavior)
- `--dry-run`: Run prepare phase, display intent (goal, conflicts, hook agenda, directives), stop before writing
- `--pause-on <stage>`: Force a pause at the specified stage (`prepare`, `write`, `persist`)
- `--batch`: Override session mode to batch for this single run

## Error Handling
- If preparer fails schema validation: report error, offer to retry
- If genre profile missing: error and list available genres
- If language skill missing: error and suggest checking book.json language field
- If writer agent fails: report error, offer to retry
- If settlement validation fails: auto-retry once with feedback (REQ-F-18); if still fails, set ChapterMeta status=state-degraded

## Skipped Stages
This command skips:
- **Audit**: No quality check
- **Revise**: No revision loop

Drafted chapters are audited when processed by `/novel-review`.

Use `/novel-write` for full pipeline with all stages.

## Related Commands
- `/novel-write`: Full pipeline including all stages (prepare → write → persist → audit → revise)
- `/novel-review`: Post-draft quality check (audit + optional revise)
