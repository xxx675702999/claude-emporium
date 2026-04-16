---
name: schemas-recovery
description: JSON corruption recovery rules for truth files
version: 1.0.0
---

# JSON Recovery Rules

## Overview

Truth files are stored as schema-validated JSON with markdown projections for human readability. When JSON files become corrupt or missing required fields, this skill defines recovery procedures to restore valid state.

## Recovery Hierarchy

1. **Primary source**: JSON file in `books/<id>/story/state/*.json`
2. **Fallback 1**: Markdown projection in `books/<id>/story/*.md`
3. **Fallback 2**: Reconstruct from latest chapter content
4. **Last resort**: Initialize with empty valid structure

## REQ-F-60: JSON Corruption Recovery

### Detection

JSON corruption detected when:
- File is not parseable as valid JSON
- Required top-level keys are missing
- Field types don't match schema
- Array fields contain invalid entries

### Recovery Procedure

```
1. Attempt to parse JSON
   └─ If parse fails → Go to step 2
   └─ If parse succeeds but schema invalid → Go to step 2

2. Check for markdown projection
   └─ If projection exists → Parse markdown to JSON (step 3)
   └─ If no projection → Reconstruct from chapters (step 4)

3. Parse markdown projection
   └─ Use file-type-specific parsing rules (see below)
   └─ Validate reconstructed JSON against schema
   └─ If valid → Write JSON, mark as recovered
   └─ If invalid → Go to step 4

4. Reconstruct from latest chapter
   └─ Read last 3 chapters
   └─ Extract facts relevant to this truth file type
   └─ Build minimal valid JSON structure
   └─ Mark as partial reconstruction

5. Validate recovered JSON
   └─ Run truth-validate.sh script
   └─ If valid → Write to file, log recovery
   └─ If invalid → Initialize empty structure, log failure
```

## Markdown-to-JSON Parsing Rules

### world_state.md → world_state.json

**Markdown structure:**
```markdown
# World State

## Locations
- Location Name: description

## Rules
- Rule: description

## Technology/Magic
- System: description
```

**Parsing logic:**
- Extract sections by `## ` headers
- Each bullet point becomes an entry
- Split on first `:` for name/description
- Preserve order

### character_matrix.md → character_matrix.json

**Markdown structure:**
```markdown
# Character Matrix

## Character Name
- **Aliases**: alias1, alias2
- **Description**: text
- **Motivation**: text
- **Arc**: text
- **Abilities**: ability1, ability2
- **Relationships**: char1 (relation), char2 (relation)
- **Status**: active/inactive
- **Introduced**: Chapter N
```

**Parsing logic:**
- Each `## ` header is a character
- Extract bold fields as keys
- Parse comma-separated lists for arrays
- Extract chapter number from "Chapter N"

### resource_ledger.md → resource_ledger.json

**Markdown structure:**
```markdown
# Resource Ledger

| Resource | Type | Owner | Opening | Closing | Delta | Chapter |
|----------|------|-------|---------|---------|-------|---------|
| Item     | type | owner | state   | state   | +/-   | N       |
```

**Parsing logic:**
- Parse markdown table rows
- Skip header and separator rows
- Map columns to JSON fields
- Parse delta as string (preserve +/- prefix)

### chapter_summaries.md → chapter_summaries.json

**Markdown structure:**
```markdown
# Chapter Summaries

## Chapter N: Title
- **Events**: event1, event2
- **Progression**: text
- **Foreshadowing**: item1, item2
- **Word Count**: N
```

**Parsing logic:**
- Each `## Chapter N:` is a chapter entry
- Extract chapter number and title
- Parse bold fields as keys
- Comma-separated lists become arrays

### subplot_board.md → subplot_board.json

**Markdown structure:**
```markdown
# Subplot Board

## Subplot Name [status]
- **Description**: text
- **Involved Characters**: char1, char2
- **Introduced**: Chapter N
- **Last Updated**: Chapter M
```

**Parsing logic:**
- Extract subplot name and status from header
- Status in brackets: [active], [dormant], [resolved]
- Parse bold fields as keys
- Extract chapter numbers

### emotional_arcs.md → emotional_arcs.json

**Markdown structure:**
```markdown
# Emotional Arcs

## Character Name
- Chapter N: emotion (intensity: N, pressure: shape, trigger: text)
```

**Parsing logic:**
- Each `## ` header is a character
- Each bullet is a progression entry
- Parse chapter number, emotion, intensity, pressure shape, trigger
- Build progression array

### pending_hooks.md → pending_hooks.json

**Markdown structure:**
```markdown
# Pending Hooks

## Hook ID [status]
- **Type**: category
- **Description**: text
- **Introduced**: Chapter N
- **Pressure**: low/medium/high/critical
- **Related Subplots**: subplot1, subplot2
- **Expected Resolution**: text
```

**Parsing logic:**
- Extract hook ID and status from header
- Parse bold fields as keys
- Comma-separated lists become arrays
- Extract chapter number

## Validation After Recovery

After reconstructing JSON from markdown or chapters:

1. Run `$.plugin.directory/scripts/pipeline/truth-validate.sh <file>`
2. Check validation result:
   - `valid: true` → Recovery successful
   - `valid: false` → Check errors array
3. If validation fails:
   - Log errors to `books/<id>/story/runtime/recovery-errors.log`
   - Initialize empty valid structure
   - Mark file as requiring manual review

## Rollback on Failure

If recovery fails and no valid state can be reconstructed:

1. Check for backup files: `books/<id>/story/state/*.json.backup`
2. If backup exists and valid → Restore from backup
3. If no backup → Initialize empty structure with schema version
4. Log failure with details for manual intervention

## REQ-NF-6: State Update Rollback

When a state update fails validation:

1. **Before update**: Copy current JSON to `.backup` file
2. **Apply update**: Write new JSON
3. **Validate**: Run truth-validate.sh
4. **On failure**:
   - Restore from `.backup`
   - Log failed update to `books/<id>/story/runtime/failed-updates.log`
   - Return error to caller with validation details
5. **On success**:
   - Delete `.backup` file
   - Regenerate markdown projection

## Recovery Logging

All recovery operations logged to `books/<id>/story/runtime/recovery.log`:

```json
{
  "timestamp": "ISO-8601",
  "file": "world_state.json",
  "issue": "JSON parse error",
  "recoveryMethod": "markdown-projection",
  "result": "success|partial|failed",
  "warnings": ["list of issues"],
  "manualReviewRequired": false
}
```

## Quick Reference

**Recovery priority:**
1. Parse JSON (if valid)
2. Parse markdown projection
3. Reconstruct from chapters
4. Initialize empty structure

**Always validate after recovery**
**Always backup before state updates**
**Always log recovery operations**
