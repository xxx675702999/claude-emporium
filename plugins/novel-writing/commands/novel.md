---
name: novel
description: Book management hub — create, list, update, delete, govern books and switch automation mode
---

# /novel — Book Management

## Usage
/novel [action] [options]

## Actions

### create
Creates a new book with specified configuration.

**Syntax:**
```
/novel create --title <title> --genre <genre-id> --lang <zh|en> --words <number> --chapters <number>
/novel create --import <file> [--pattern <regex>] [--resume <chapter>] [--book <id>]
/novel create --fanfic <source-file> --title <title> --mode <canon|au|ooc|cp> [--lang <zh|en>] [--words <N>] [--chapters <N>]
/novel create --spinoff <parent-id> --title <title> --type <prequel|sequel|side-story|pov-shift> [--lang <zh|en>] [--words <N>] [--chapters <N>]
```

**Process:**
1. Generate unique book ID (timestamp-based: `book-YYYYMMDD-HHMMSS`)
2. Create directory structure: `books/<id>/`
3. Copy `book.json` template from `data/templates/book.json.tpl`
4. Fill in metadata:
   - `id`: generated book ID
   - `title`: user-provided title
   - `genre`: genre ID
   - `language`: zh or en
   - `targetChapters`: target chapter count
   - `chapterWordCount`: words per chapter
   - `status`: "incubating"
   - `platform`: "other" (default)
   - `createdAt`, `updatedAt`: current ISO 8601 timestamp
5. Create subdirectories: `story/`, `story/state/`, `story/runtime/`, `chapters/`, `genres/`
6. Initialize 7 empty truth files from `data/schemas/truth-files/*.json`:
   - Copy each JSON file to `books/<id>/story/state/`
   - Files: `world_state.json`, `character_matrix.json`, `resource_ledger.json`, `chapter_summaries.json`, `subplot_board.json`, `emotional_arcs.json`, `pending_hooks.json`
7. Initialize empty ChapterMeta at `books/<id>/story/state/chapter-meta.json`:
   ```json
   {
     "schemaVersion": 1,
     "lastUpdated": "<current ISO 8601>",
     "chapters": []
   }
   ```
8. Copy genre profile from `data/genres/<lang>/<genre>.md` to `books/<id>/genres/<genre>.md`
9. Create control documents from templates:
   - `story/author_intent.md` from `data/templates/author_intent-<lang>.md.tpl`
   - `story/current_focus.md` from `data/templates/current_focus-<lang>.md.tpl`
10. **Invoke the architect agent** to generate foundation files instead of leaving empty templates:
    - Load `agents/architect.md`
    - Pass inputs: book config from `book.json` (title, genre, language, targetChapters), genre profile from `data/genres/<lang>/<genre>.md`, and `story/author_intent.md` (if user-edited)
    - The architect generates 5 foundation files: `story/story_bible.md`, `story/volume_outline.md`, `story/book_rules.md`, `story/state/current_state.json`, `story/state/pending_hooks.json`
    - If FoundationReviewer average score >= 80 and all dimensions >= 60: foundation accepted
    - If FoundationReviewer fails after 2 retries: fall back to empty templates for the 3 markdown files, keep the empty JSON truth files from step 6, and warn the user: `"⚠ Foundation generation failed (score: XX/100). Empty templates created — edit story/story_bible.md, story/volume_outline.md, and story/book_rules.md manually before writing."`
11. Create `.session.json` with `{"mode": "interactive", "activeBook": "<id>"}`
12. Report success with book ID, foundation summary, and next steps

**Example:**
```
/novel create --title "破灭星辰" --genre xuanhuan --lang zh --words 3000 --chapters 200
```

**Output:**
```
✓ Book created: book-20260414-103045
  Title: 破灭星辰
  Genre: xuanhuan (玄幻)
  Language: Chinese
  Target: 200 chapters × 3000 words
  Mode: interactive

Foundation files generated:
  story_bible.md — 5 characters, 4 locations, 6 world rules
  volume_outline.md — 12 chapters outlined
  book_rules.md — 10 genre rules, 5 book-specific rules
  current_state.json — 4 locations, 5 rules, 1 system
  pending_hooks.json — 4 hooks (mystery, promise, threat, prophecy)
  FoundationReviewer: 86/100 — PASS

Next steps:
1. Review story/author_intent.md and story/story_bible.md — edit if needed
2. Run /novel-write to start writing chapter 1
```

#### create --import
Import chapters from a text file and reverse-engineer truth files.

**Syntax:**
```
/novel create --import <file> [--pattern <regex>] [--resume <chapter>] [--book <id>]
```

**Options:**
- `--import <file>`: Source text file to import
- `--pattern <regex>`: Custom chapter heading pattern (default: auto-detect `第X章`, `Chapter N`)
- `--resume <N>`: Resume import from chapter N (skips chapters 1 to N-1)
- `--book <id>`: Target book (default: active book)

**Process:**
1. Validate import file exists and is not empty
2. Run `python3 $.plugin.directory/scripts/pipeline/chapter-split.py` to split by chapter headings
3. For each chapter:
   - Write to `chapters/chapter-XXXX.md`
   - Run writer settlement phase to extract facts and generate delta, then pipeline persists truth files
4. Generate style guide from imported text
5. Report import summary

**Resume behavior:** When `--resume <N>` is specified, verify chapters 1 to N-1 already exist, skip splitting/import for those, start settlement & persistence from chapter N, continue to end of file, regenerate style guide from all chapters.

**Error handling:**
- Empty file: Report error with expected format hints (Chinese: `第X章`, English: `Chapter N`, or custom `--pattern`)
- No chapter headings detected: Suggest adding headings or using `--pattern` flag
- Invalid resume chapter: Report current state and suggest valid resume point
- Validation failure during settlement: Skip chapter, continue, recommend manual review

**File limits:** Max source file 10 MB, max 500 chapters per import.

**Output:**
```
Importing from novel.txt...
Detected 50 chapters (pattern: 第X章)
✅ Chapter 1-50 imported (165,000 words)
✅ Truth files initialized (current_state, hooks, chapter_summaries)
✅ Style guide generated
```

#### create --fanfic
Create a fan fiction book from source material.

**Syntax:**
```
/novel create --fanfic <source-file> --title <title> --mode <canon|au|ooc|cp> [--lang <zh|en>] [--words <N>] [--chapters <N>]
```

**Fanfic modes:**
- **canon**: Faithful to source material, strict adherence
- **au**: Alternate universe, world rules can differ
- **ooc**: Out of character allowed, behavior can deviate
- **cp**: Ship-focused, relationship dynamics prioritized

**Process:**
1. Read source material file and extract character profiles, world rules, canon events, relationship dynamics
2. Generate `fanfic_canon.md` with extracted information
3. Create book via standard create flow
4. Set `fanficMode` in `book.json`
5. Write `fanfic_canon.md` to `story/` directory
6. Configure audit dimensions (34-37) based on mode:
   - **canon**: Dim 34 critical, 35 critical, 36 warning, 37 critical
   - **au**: Dim 34 warning, 35 skipped, 36 warning, 37 skipped
   - **ooc**: Dim 34 skipped, 35 critical, 36 warning, 37 critical
   - **cp**: Dim 34 warning, 35 critical, 36 skipped, 37 warning

**Information boundary:** Tracks divergence point from canon. Characters cannot reference knowledge revealed after divergence point.

**Error handling:**
- Source file empty: Report error
- Source analysis fails: Prompt user to provide manual canon info
- Invalid mode: List valid modes (canon, au, ooc, cp)

**Output:**
```
Analyzing source material: source.txt
✅ 8 characters, 12 world rules, 25 canon events, 15 relationships
✅ fanfic_canon.md created (5,200 words)
✅ Book created: book-20260414-120000 (mode: au)
✅ Audit dimensions 34-37 configured for AU mode
```

#### create --spinoff
Create a spinoff book linked to a parent book.

**Syntax:**
```
/novel create --spinoff <parent-id> --title <title> --type <prequel|sequel|side-story|pov-shift> [--lang <zh|en>] [--words <N>] [--chapters <N>]
```

**Spinoff types:**
- **prequel**: Events before parent timeline
- **sequel**: Events after parent timeline
- **side-story**: Parallel events, different characters
- **pov-shift**: Same events, different perspective

**Process:**
1. Validate parent book exists and read parent's truth files (read-only access)
2. Generate `parent_canon.md` with canon events, world rules, character profiles, timeline boundaries
3. Create book via standard create flow
4. Set `parentBookId` and `spinoffType` in `book.json`
5. Write `parent_canon.md` to `story/` directory
6. Initialize spinoff's own truth files (separate from parent)
7. Configure audit dimensions (28-31):
   - Dim 28 (canon event conflict): Critical
   - Dim 29 (future information leak): Critical
   - Dim 30 (cross-book world rules): Critical
   - Dim 31 (spinoff hook isolation): Warning
8. Set timeline position based on spinoff type

**Read-only constraints:** Spinoff can READ parent's truth files but CANNOT modify them. Spinoff maintains its own separate truth files.

**Error handling:**
- Parent book not found: List available books
- Parent has no chapters: Warn that canon is empty
- Invalid type: List valid types (prequel, sequel, side-story, pov-shift)
- Timeline conflict: Report validation error

**Output:**
```
Parent book: 破灭星辰 (book-001) — 50 chapters, 165,000 words
✅ parent_canon.md created (8,500 words)
✅ Spinoff created: book-20260414-130000 (type: prequel)
✅ Audit dimensions 28-31 configured
✅ Timeline: -50 chapters before parent
```

### list
Lists all books with status, chapter count, and word count.

**Syntax:**
```
/novel list
```

**Process:**
1. Find all book directories in `books/`
2. For each book:
   - Read `book.json` for metadata
   - Count chapter files in `chapters/` (files matching `chapter-*.md`)
   - Calculate total word count (sum of all chapters using `wc -w` for en, `wc -m` for zh)
   - Read status from `book.json`
   - Read ChapterMeta for chapter status breakdown (if available)
3. Display table with: ID, Title, Genre, Language, Status, Chapters, Words, ChapterMeta breakdown

**Output format:**
```
Books:
1. book-20260414-103045 | 破灭星辰 | xuanhuan | zh | active | 15/200 | 45,000
2. book-20260413-091230 | Tower Ascent | litrpg | en | paused | 8/100 | 24,000
3. book-20260410-154500 | 仙路漫漫 | xianxia | zh | completed | 200/200 | 600,000

Total: 3 books
```

### status
Shows detailed status of the active book.

**Syntax:**
```
/novel status [--book <id>]
```

**Process:**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. If no active book: Report error and suggest `/novel list`
4. Read `book.json` for full metadata
5. Count chapters in `chapters/`
6. Read last chapter file for last chapter info (chapter number, word count, modification date)
7. Read ChapterMeta for status breakdown
8. Calculate progress percentage: `(current chapters / target chapters) × 100`
9. Display detailed status

**Output:**
```
Book Status:
- ID: book-20260414-103045
- Title: 破灭星辰
- Genre: xuanhuan (玄幻)
- Language: zh
- Mode: interactive
- Progress: 15/200 chapters (7.5%)
- Total words: 45,000
- Avg words/chapter: 3,000
- Last chapter: Chapter 15 (2026-04-14 10:30)
- Status: active
- Chapter breakdown: 12 approved, 2 ready-for-review, 1 drafted
```

### update
Updates book metadata.

**Syntax:**
```
/novel update [--book <id>] [--title <title>] [--words <number>] [--chapters <number>] [--status <status>]
```

**Process:**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. Read current `book.json`
4. Merge changes (only update specified fields):
   - `--title`: Update `title`
   - `--words`: Update `chapterWordCount`
   - `--chapters`: Update `targetChapters`
   - `--status`: Update `status`
5. Update `updatedAt` to current timestamp
6. Validate new values:
   - `chapterWordCount` must be > 0
   - `targetChapters` must be > 0
   - `status` must be one of: incubating, outlining, active, paused, completed, dropped
7. Write updated `book.json`
8. Report success

**Status options:** incubating, outlining, active, paused, completed, dropped

**Example:**
```
/novel update --title "破灭星辰：重生" --status active
```

**Output:**
```
✓ Book updated: book-20260414-103045
  Title: 破灭星辰 → 破灭星辰：重生
  Status: incubating → active
```

### delete
Deletes a book and all associated files.

**Syntax:**
```
/novel delete --book <id>
```

**Process:**
1. ALWAYS prompt for confirmation (regardless of automation mode)
2. Read `book.json` to get book details
3. Count chapters and calculate total word count
4. Show book details before deletion
5. Wait for user confirmation (must type "yes")
6. If confirmed: Remove `books/<id>/` directory recursively
7. Report success

**Confirmation prompt:**
```
⚠️  Delete book "破灭星辰" (book-20260414-103045)?
This will permanently delete:
- 15 chapters (45,000 words)
- All truth files and runtime data
- Control documents and genre configs

Type 'yes' to confirm: _
```

**After confirmation:**
```
✓ Book deleted: book-20260414-103045
```

### mode
Switches automation mode for the active book.

**Syntax:**
```
/novel mode <interactive|batch> [--book <id>]
```

**Process:**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. Update `mode` in `.session.json`
4. Report mode change with explanation

**Modes:**
- **interactive** (default): Smart pause — always pauses before write; pauses before revise only when >2 critical audit issues; auto-revises otherwise. All other stages run automatically.
- **batch**: Zero pauses — full pipeline runs unattended. If audit finds critical issues, auto-executes revision and continues. Designed for unattended multi-chapter generation.

**Backward compatibility:** Old mode values are auto-converted on read:
- `auto` → `batch`
- `semi` → `interactive`
- `manual` → `interactive` (with warning: "manual mode has been removed; using interactive mode")

**Example:**
```
/novel mode batch
```

**Output:**
```
✓ Mode changed: interactive → batch
  Book: 破灭星辰 (book-20260414-103045)
  
Batch mode: Full pipeline runs without pauses.
All stages (prepare, write, persist, audit, revise) execute automatically.
If audit finds critical issues, revision runs automatically — pipeline never stops.
```

### --edit-intent
Edit author_intent.md (long-horizon book identity).

**Syntax:**
```
/novel --edit-intent [--book <id>]
```

**Process:**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. Read current `story/author_intent.md`
4. Display current content for user review
5. Prompt user to edit (or provide new content)
6. Validate structure — must contain sections: **Premise**, **Themes**, **Tone**, **Audience**
7. Save changes to `story/author_intent.md`
8. Update `book.json` `updatedAt` timestamp
9. Report success

**Required sections:**
- **Premise**: Core story concept (1-2 sentences)
- **Themes**: Central themes and messages
- **Tone**: Narrative voice and atmosphere
- **Audience**: Target reader demographic and expectations

**Validation:** If any required section is missing, report which sections are missing and do not save. Prompt user to add the missing sections.

**Output:**
```
Current author_intent.md:

# Author Intent
## Premise
A fallen cultivator reborn in a world where cultivation is forbidden...
## Themes
- Revenge vs. redemption
...
---
Edit this content? (y/n): _
```

### --edit-focus
Edit or regenerate current_focus.md (short-term steering).

**Syntax:**
```
/novel --edit-focus [--book <id>]
/novel --edit-focus --regenerate [--book <id>]
```

**Process (default — edit):**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. Read current `story/current_focus.md`
4. Display current content for user review
5. Prompt user to edit (or provide new content)
6. If user adds a `# Local Override` section at the top, it takes highest priority in preparer (overrides outline and auto-generated content)
7. Save changes to `story/current_focus.md`
8. Update `book.json` `updatedAt` timestamp
9. Report success

**Process (--regenerate):**
1. Run: `python3 $.plugin.directory/scripts/pipeline/generate-focus.py "$BOOK_DIR"`
2. Regenerates current_focus.md from latest truth files (summary, hooks, state, outline)
3. Report success

**Note:** current_focus.md is auto-generated after each chapter persist (via `apply-delta.py`). Use `--edit-focus` to manually override or add a `# Local Override` section for specific directions. Use `--regenerate` to force refresh from current data.

**Output:**
```
Current current_focus.md:

# Current Focus
## Short-term Goal (Next 1-3 Chapters)
Protagonist infiltrates the Azure Sect's inner court...
## Key Points
- Establish relationship with Elder Yun
...
## Avoid List
- Don't reveal protagonist's true identity yet
...
---
Edit this content? (y/n): _
```

### --edit-truth
Manually edit truth files.

**Syntax:**
```
/novel --edit-truth <file-name> [--book <id>]
```

**Supported file names (implemented):**
- `current_state` — protagonist situation and known facts
- `hooks` — unresolved cliffhangers, promises, expected resolution
- `chapter_summaries` — events, progression, foreshadowing per chapter

**Supported file names (planned, not yet implemented):**
- `world_state` — maps, locations, technology/magic systems, world rules
- `character_matrix` — names, relationships, arcs, motivations, abilities
- `resource_ledger` — in-world items, money, power levels with opening/closing deltas
- `subplot_board` — active and dormant subplots, hooks, their status
- `emotional_arcs` — character emotional progression with pressure shapes

**Process:**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. Read specified truth file JSON from `story/state/<file-name>.json`
4. Display current content (formatted JSON)
5. Prompt user to edit (or provide new JSON content)
6. Validate against schema using `$.plugin.directory/scripts/pipeline/truth-validate.sh <file-name>.json`
7. If valid:
   - Save to `story/state/<file-name>.json`
   - Regenerate markdown projection to `story/<file-name>.md`
   - Update `book.json` `updatedAt` timestamp
   - Report success
8. If invalid:
   - Report validation errors with line numbers and descriptions
   - Don't save changes
   - Prompt user to fix errors

**Validation error example:**
```
✗ Validation failed for pending_hooks.json:
  Line 5: Missing required field "hookId"
  Line 8: Invalid status "unknown" (must be one of: open, progressing, deferred, resolved)

Changes not saved. Fix errors and try again.
```

### --rename
Rename a book.

**Syntax:**
```
/novel --rename <new-title> [--book <id>]
```

**Process:**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. Read current `book.json`
4. Update `title` field to new title
5. Update `updatedAt` timestamp
6. Write `book.json`
7. Report success

**Output:**
```
✓ Book renamed: book-20260414-103045
  Old title: 破灭星辰
  New title: 破灭星辰：重生篇
```

### --rename-entity
Rename an entity (character name, place name, etc.) across all truth files with exact-match semantics.

**Syntax:**
```
/novel --rename-entity --old "<old-name>" --new "<new-name>" [--scope <scope>] [--book <id>]
```

**Scopes:** `all` (default), `direction`, `foundation`, `runtime-truth`

**Process:**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. Run entity rename script:
   ```bash
   python3 $.plugin.directory/scripts/pipeline/entity-rename.py "$BOOK_DIR" --old "$OLD" --new "$NEW" --scope "$SCOPE"
   ```
4. Display replacement summary (file count, replacement count)
5. Regenerate affected markdown projections

**Output:**
```
Renaming "林远" → "林渊" (scope: all)
  story/author_intent.md: 3 replacements
  story/state/current_state.json: 5 replacements
  story/state/pending_hooks.json: 2 replacements
  story/chapter_summaries.md: 8 replacements
Total: 18 replacements across 4 files
```

### --undo
Rollback the last chapter and reverse its truth file changes.

**Syntax:**
```
/novel --undo [--book <id>]
```

**Process:**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. Detect last chapter:
   - Glob `chapters/chapter-*.md`, extract numeric suffixes, take max → lastChapter
   - If no chapters found → report "no chapters to undo"
4. Read `runtime/chapter-XXXX.delta.json` for the last chapter
   - If delta.json not found → report error: "cannot undo — delta.json missing for chapter N"
5. Display rollback summary and prompt for confirmation (ALWAYS requires confirmation, even in batch mode):
   ```
   ⚠️  Undo Chapter 15?
   This will:
   - Delete chapters/0015_*.md (or legacy chapter-0015.md)
   - Reverse 15 truth file updates from delta.json
   - Remove runtime files for chapter 15
   - Remove ChapterMeta record for chapter 15

   Type 'yes' to confirm: _
   ```
6. If confirmed:
   - Compute reverse operations from delta.json (inverse of each delta entry)
   - Apply reverse operations to truth files in `story/state/*.json`
   - Validate truth files after rollback using `$.plugin.directory/scripts/pipeline/truth-validate.sh`
   - If validation fails → abort rollback, restore original files, report error
   - Delete `chapters/chapter-XXXX.md`
   - Delete runtime files: `runtime/chapter-XXXX.{intent.md,context.json,rule-stack.yaml,trace.json,delta.json,audit.json}`
   - Update ChapterMeta: remove the chapter record for the undone chapter
   - Regenerate markdown projections from rolled-back JSON state
7. Report success

**Reverse operation mapping:**
- Delta `"add"` → reverse to `"remove"` (delete the added entry)
- Delta `"update"` → reverse to `"update"` with previous value (from delta's `"oldValue"` field)
- Delta `"remove"` → reverse to `"add"` (restore the removed entry from delta's `"oldValue"` field)

**Error handling:**
- No chapters exist → "No chapters to undo."
- Delta.json missing → "Cannot undo chapter N — delta.json not found. Manual rollback required."
- Truth file validation fails after rollback → abort, restore pre-rollback state, restore ChapterMeta, report validation errors
- Confirmation declined → "Undo cancelled."
- ChapterMeta missing → create empty ChapterMeta after rollback (no records to remove)

**Output:**
```
Detecting last chapter...
  chapters/ → 15 chapter files found
  Last chapter: 15

⚠️  Undo Chapter 15?
This will:
- Delete chapters/0015_*.md (or legacy chapter-0015.md)
- Reverse 15 truth file updates from delta.json
- Remove runtime files for chapter 15
- Remove ChapterMeta record for chapter 15

Type 'yes' to confirm: yes

Rolling back...
✅ Truth files reversed (15 operations)
✅ Truth file validation passed
✅ Chapter file deleted: chapters/0015_*.md
✅ Runtime files cleaned up
✅ ChapterMeta updated: chapter 15 record removed

Undo complete. Last chapter is now Chapter 14.
```

## Natural Language Routing
If the user's message matches these patterns, route to the corresponding action:
- "create a book/new novel/start writing" → create
- "import chapters/import from file" → create --import
- "create fanfic/fan fiction/write fanfic" → create --fanfic
- "create spinoff/prequel/sequel/side story" → create --spinoff
- "list books/show books/show all books" → list
- "book status/how's the book/show status" → status
- "update book/change title/modify book" → update
- "delete book/remove book" → delete
- "switch mode/interactive mode/batch mode/change mode" → mode
- "undo/rollback/undo last chapter" → --undo
- "edit intent/update author intent/change premise" → --edit-intent
- "edit focus/update current focus/change short-term goal" → --edit-focus
- "edit truth file/update character matrix/modify world state" → --edit-truth
- "rename book/change book title" → --rename
- "rename entity/rename character/change character name" → --rename-entity

Chinese shorthand patterns:
- "新建小说" / "创建小说" / "开新书" → create
- "/new 玄幻小说" / "写本玄幻" / "写本仙侠" → create with matching genre (xuanhuan, xianxia)
- "暂停" → pause (update --status paused)
- "继续写" → continue (/novel-continue)
- "修一下" / "修改" → fix (/novel-fix)
- "导出" → export (/novel-export)
- "统计" → stats (/novel-stats)
- "审核" → review (/novel-review)
- "重写第N章" → rewrite chapter N (/novel-fix with chapter target)
- "新章节" → write next chapter (/novel-write)
- "草稿" → draft (/novel-draft)
- "改名" / "改角色名" / "重命名角色" → --rename-entity

If intent is unclear, ask user to clarify.

## Error Handling
- If no books exist: Suggest `/novel create`
- If book ID not found: List available books with `/novel list`
- If required parameter missing: Show usage and examples
- If delete without confirmation: Abort with message "Deletion cancelled"
- If active book not set: Suggest using `--book <id>` or `/novel list`
- If control document doesn't exist: Create from template (for author_intent, current_focus) or report error (for truth files)
- If truth file validation fails: Show errors with line numbers, don't save
- If truth file name invalid: List valid file names
- If fanfic mode invalid: List valid modes (canon, au, ooc, cp)
- If spinoff type invalid: List valid types (prequel, sequel, side-story, pov-shift)
- If spinoff parent not found: List available books
- If import file empty or not found: Report error with expected format hints

## Notes
- Truth files are the authoritative source of story state
- Always validate truth files before saving to prevent corrupt state
- Markdown projections are auto-generated from JSON — don't edit markdown directly
- Control documents (author_intent, current_focus) are markdown and can be edited freely
- Spinoff books maintain read-only access to parent truth files
- Fanfic audit dimensions (34-37) activate based on `fanficMode` in book.json
- Spinoff audit dimensions (28-31) activate based on `parentBookId` in book.json
