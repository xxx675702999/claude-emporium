# Novel Writing Plugin - Conventions

## File Structure
- Skills: `skills/<domain>/SKILL.md` — knowledge domains loaded on demand
- Agents: `agents/<name>.md` — pipeline stage definitions
- Commands: `commands/<name>.md` — user slash command entry points
- Data: `data/schemas/`, `data/genres/`, `data/templates/` — static reference files
- Scripts: `scripts/<category>/<name>.sh|.py` — deterministic utilities. All pipeline scripts are now Python (stdlib only, no third-party packages), with `truth-validate.sh` as the sole remaining bash wrapper. No Node.js/npm dependencies. Python 3.10+ required.

## Book Path Resolution
- Book config: `books/<book-id>/book.json`
- Markdown projections (read by agents): `books/<book-id>/story/*.md` — current_state, pending_hooks, chapter_summaries, resource_ledger, style_guide, story_bible, volume_outline, author_intent, current_focus, book_rules, audit_drift, parent_canon, fanfic_canon, emotional_arcs, subplot_board, character_matrix
- Structured state (internal): `books/<book-id>/story/state/*.json` — manifest, current_state, pending_hooks, chapter_summaries, chapter-meta, subplot_board, emotional_arcs, character_matrix, resource_ledger
- Chapters: `books/<book-id>/chapters/{XXXX}_{sanitized_title}.md` (new format) or `chapter-XXXX.md` (legacy, backward compat)
- Chapter filename sanitization: remove `/ \ ? % * : | " < >`, spaces to underscores, truncate title to 50 chars; CJK preserved
- Chapter file lookup: find by zero-padded number prefix (`XXXX_*.md`), fallback to `chapter-XXXX.md`
- Runtime: `books/<book-id>/story/runtime/` (intent, context, rule-stack, trace)
- Control documents: `books/<book-id>/story/author_intent.md`, `books/<book-id>/story/current_focus.md`
- Global config: `.session.json` (`activeBook` field)

## Automation Mode (.session.json)
- Mode stored in `books/<book-id>/.session.json` as `{"mode": "interactive"|"batch"}`
- Default: `interactive` if no session file
- `interactive`: smart pause — always pause before write; pause before revise only when >2 critical audit issues; auto-revise otherwise
- `batch`: zero pauses, full pipeline runs unattended; if audit finds critical issues, auto-executes revision and continues
- Every command reads `.session.json` before execution
- `/novel mode <mode>` updates the session file
- Backward compat: old values auto-convert on read (`auto`→`batch`, `semi`→`interactive`, `manual`→`interactive` with warning)
- Command flags override session mode per invocation: `--yes` (skip confirmations), `--dry-run` (run prepare, display intent, stop before writing), `--pause-on <stage>` (pause at specific stage), `--batch` (force batch mode for single run)

## Language Rules
- Book language from `book.json` field `language` (`"zh"` or `"en"`)
- Controls which language skill to load (`language-zh` or `language-en`)
- Controls genre profile subdirectory (`data/genres/zh/` or `data/genres/en/`)
- Controls word count logic (zh: character count, en: word count)
- All command outputs match the book language
- Skill prompts, agent instructions, and command definitions are in English. Chinese content patterns (e.g., `第5章：`, `局部覆盖`) preserved for matching against zh book content.

## Variable Naming
- File names: kebab-case for scripts (e.g., `cache-manager.py`), snake_case for truth files (e.g., `current_state.json`); chapter files use `{XXXX}_{sanitized_title}.md` format
- JSON keys: camelCase (e.g., `chapterCount`, `chapterWordCount`)
- Shell script names: kebab-case with .sh extension
- Agent/command IDs: match file names without extension

## Truth File Rules
- Agents read markdown projections (`story/*.md`); JSON (`story/state/*.json`) is internal structured state
- Both exist: JSON is the persistence format, markdown is regenerated from JSON for agent consumption
- State updates are immutable: append new, never mutate existing
- Every update must pass schema validation (via `scripts/pipeline/truth-validate.sh`)
- On validation failure, roll back to previous valid state
- Markdown projections regenerated from JSON after every update
- Bootstrap from markdown when JSON is missing (backward compat)

## Pipeline Overview
- 6 agents: architect, preparer, writer, auditor, reviser, style-analyzer
- 10 commands: novel, novel-write, novel-draft, novel-review, novel-export, novel-stats, novel-genre, novel-style, novel-continue, novel-fix
- Pipeline stages: Prepare → Write (Phase 1: creative writing + inline length check; Phase 2: settlement + delta generation) → Persist → Audit → Revise

## Component Size
- Every skill SKILL.md: <= 500 lines (Anthropic official recommendation; use references/ for overflow)
- If a skill exceeds 500 lines, split into SKILL.md + references/ sub-files (per skill-creator pattern)
- Agents, commands, and scripts: no hard line limit, but keep concise for context window efficiency
