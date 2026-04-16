---
name: spinoff-rules
description: Spinoff writing rules with parent book linking and conditional audit dimensions
version: 1.0.0
---

# Spinoff Rules

## Overview

InkOS supports spinoff books that link to a parent book's truth files for canon consistency. Spinoffs include prequels, sequels, side stories, and POV shifts. Four conditional audit dimensions (28-31) activate only when `book.json` has `parentBookId` set, enforcing cross-book consistency while maintaining spinoff independence.

## Spinoff Types

### Prequel

**Description**: Events occurring before the parent book's timeline.

**Characteristics**:
- Timeline position: Before parent book chapter 1
- Characters may be younger or not yet introduced
- World state reflects earlier era
- Cannot reference parent book's future events
- Sets up conditions that lead to parent book

**Timeline Management**:
- Track spinoff timeline relative to parent: `timelineOffset: -365` (days before parent start)
- Validate character knowledge: no future information leaks
- World state must be consistent with parent's backstory

**Example**: Parent book starts with a war; prequel shows the political tensions that caused it.

### Sequel

**Description**: Events occurring after the parent book's timeline.

**Characteristics**:
- Timeline position: After parent book's final chapter
- Inherits parent book's ending state
- Characters may have aged or evolved
- Can reference parent book events as history
- Resolves unresolved parent book threads or introduces new conflicts

**Timeline Management**:
- Track spinoff timeline relative to parent: `timelineOffset: 730` (days after parent end)
- Import parent book's final state as spinoff's initial state
- Characters can reference parent events as past experiences

**Example**: Parent book ends with protagonist becoming king; sequel shows their reign 10 years later.

### Side Story

**Description**: Parallel events with different characters, same timeframe as parent book.

**Characteristics**:
- Timeline position: Overlaps with parent book timeline
- Different protagonist or POV character
- Events occur simultaneously with parent book
- May intersect with parent book events from different perspective
- Independent plot that doesn't require reading parent book

**Timeline Management**:
- Track spinoff timeline relative to parent: `timelineOffset: 0, timelineOverlap: true`
- Validate cross-book event consistency: same events must match across books
- Characters may reference shared events

**Example**: Parent book follows hero's journey; side story follows villain's parallel campaign.

### POV Shift

**Description**: Same events as parent book, different character's perspective.

**Characteristics**:
- Timeline position: Identical to parent book
- Same events, different internal experience
- Reveals information hidden from parent book's POV
- Adds depth to parent book events
- Requires reading parent book for full context

**Timeline Management**:
- Track spinoff timeline relative to parent: `timelineOffset: 0, timelineLocked: true`
- Strict event consistency: all shared events must match exactly
- Different character knowledge boundaries

**Example**: Parent book shows battle from hero's POV; POV shift shows same battle from ally's perspective.

## Parent Book Linking (REQ-F-41)

### Step 1: Create Spinoff Book

```bash
/novel create --spinoff --parent parent-book-id --type prequel --title "Origins"
```

This creates:
- `book.json` with `parentBookId: "parent-book-id"` and `spinoffType: "prequel"`
- `story/parent_canon.md` with parent book reference
- Standard truth files (initially empty or inherited)
- Control documents (author_intent.md, current_focus.md)

### Step 2: Link to Parent Truth Files

The spinoff reads parent truth files as **read-only** references:

**Parent Markdown Projections** (read by agents):
- `../parent-book-id/story/current_state.md`
- `../parent-book-id/story/pending_hooks.md`
- `../parent-book-id/story/chapter_summaries.md`
- `../parent-book-id/story/resource_ledger.md`
- `../parent-book-id/story/story_bible.md`
- `../parent-book-id/story/style_guide.md`

**Internal Structured State** (not read directly by agents):
- `../parent-book-id/story/state/current_state.json`
- `../parent-book-id/story/state/pending_hooks.json`
- `../parent-book-id/story/state/chapter_summaries.json`

**Read-Only Constraint**: Spinoff cannot modify parent files. All spinoff state updates go to spinoff's own truth files.

### Step 3: parent_canon.md Structure

```markdown
# Parent Canon Reference

## Parent Book
- ID: parent-book-id
- Title: [Parent book title]
- Status: [completed|active]
- Final Chapter: [Last chapter number]

## Timeline Relationship
- Spinoff Type: [prequel|sequel|side-story|pov-shift]
- Timeline Offset: [Days before/after parent start, or 0 for parallel]
- Timeline Overlap: [true|false]
- Timeline Locked: [true|false for POV shift]

## Inherited World State

### Locations
[Key locations from parent book]

### World Rules
[Magic systems, technology, physics from parent]

### Factions
[Organizations, groups, hierarchies from parent]

## Inherited Characters

### [Character Name]
- **Status in Parent**: [alive|dead|unknown]
- **Last Known Location**: [From parent book]
- **Abilities**: [From parent book]
- **Relationships**: [From parent book]

## Canon Events (Parent Timeline)

1. [Event 1] - Chapter X - [Consequences]
2. [Event 2] - Chapter Y - [Consequences]
...

## Constraints

### Cannot Contradict
- [World rule 1]
- [World rule 2]
...

### Cannot Reference (Future Events for Prequel)
- [Event A] (happens in parent Chapter X)
- [Event B] (happens in parent Chapter Y)
...

## Unresolved Threads from Parent
- [Thread 1] - Potential spinoff hook
- [Thread 2] - Potential spinoff hook
...
```

## Spinoff Audit Dimensions (28-31)

### Dimension 28: Canon Event Conflict

**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `parentBookId` is set  

**Description**: Spinoff contradicts parent book's established events.

**Check Process**:
1. Read parent book's `chapter_summaries.md`
2. Read spinoff's `parent_canon.md` for event timeline
3. Compare spinoff chapter events against parent timeline
4. Flag any contradictions

**Examples**:
- ✗ Spinoff shows character alive when parent established their death
- ✗ Spinoff changes outcome of event that parent book described
- ✗ Spinoff contradicts parent's world history
- ✓ Spinoff adds new events that don't contradict parent

**Spinoff Type Considerations**:
- **Prequel**: Cannot contradict parent's backstory or setup
- **Sequel**: Cannot contradict parent's ending state
- **Side Story**: Cannot contradict shared events
- **POV Shift**: Must match parent events exactly

### Dimension 29: Future Information Leak

**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `parentBookId` is set  

**Description**: Spinoff characters reference events from parent book's future timeline.

**Check Process**:
1. Determine spinoff timeline position relative to parent
2. Identify parent book events that occur after spinoff timeline
3. Check if spinoff characters reference future events
4. Flag any future knowledge leaks

**Examples**:
- ✗ Prequel character mentions event that happens in parent book
- ✗ Prequel character knows outcome of parent book's conflict
- ✗ Side story character references parent book's ending
- ✓ Sequel character references parent book events as history

**Timeline Validation**:

```yaml
# Prequel (timelineOffset: -365)
- Parent Chapter 1 event: "War begins" → Spinoff CANNOT reference
- Spinoff can reference: events >365 days before parent start

# Sequel (timelineOffset: 730)
- Parent Chapter 100 event: "War ends" → Spinoff CAN reference
- Spinoff can reference: all parent book events

# Side Story (timelineOffset: 0, overlap: true)
- Parent Chapter 50 event: "Battle of X" → Spinoff can reference if timeline reached
- Spinoff Chapter 10 cannot reference Parent Chapter 60 events

# POV Shift (timelineOffset: 0, locked: true)
- Same timeline as parent → Can reference same events from different perspective
```

### Dimension 30: Cross-Book World Rules

**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `parentBookId` is set  

**Description**: Spinoff violates parent book's world rules or magic system.

**Check Process**:
1. Read parent book's `story_bible.md` (world rules)
2. Extract world rules, magic systems, technology constraints
3. Compare spinoff chapter world mechanics against parent rules
4. Flag any contradictions

**Examples**:
- ✗ Spinoff allows magic that parent established as impossible
- ✗ Spinoff changes technology level without justification
- ✗ Spinoff violates parent's physics or world laws
- ✓ Spinoff extends world rules without contradicting parent

**World Rule Categories**:
- **Magic Systems**: Mechanics, limitations, costs
- **Technology**: Available tech, constraints, era
- **Physics**: World laws, natural phenomena
- **Social Structures**: Hierarchies, organizations, customs
- **Geography**: Locations, distances, climate

**Prequel Considerations**:
- World rules can be less developed (earlier era)
- Technology can be more primitive
- Magic systems can be less understood
- Social structures can be different (historical change)

### Dimension 31: Spinoff Hook Isolation

**Severity**: Warning  
**Detection**: LLM judgment  
**Activation**: Only when `parentBookId` is set  

**Description**: Spinoff introduces hooks that require parent book knowledge to resolve.

**Check Process**:
1. Read spinoff's `pending_hooks.md`
2. Evaluate if each hook is self-contained
3. Check if hook resolution depends on parent book events
4. Flag hooks that require parent book context

**Examples**:
- ✗ Spinoff hook about "the prophecy" that only makes sense if you read parent
- ✗ Spinoff mystery whose answer is revealed in parent book
- ✗ Spinoff character motivation that requires parent book backstory
- ✓ Spinoff hook that resolves within spinoff's own narrative

**Hook Isolation Levels**:
- **Fully Isolated**: Hook introduced and resolved in spinoff, no parent knowledge needed
- **Lightly Connected**: Hook references parent events but is understandable standalone
- **Dependent**: Hook requires parent book knowledge to understand (flagged as warning)

**Acceptable Connections**:
- Spinoff can reference parent book events as world history
- Spinoff can feature parent book characters (with proper introduction)
- Spinoff can resolve parent book's unresolved threads (if explained in spinoff)

## Read-Only Constraints

### Parent Truth Files are Immutable

Spinoff cannot modify parent book's truth files:

**Prohibited Operations**:
- ✗ Modifying parent's `current_state.json`
- ✗ Modifying parent's `pending_hooks.json`
- ✗ Updating parent's `chapter_summaries.json`
- ✗ Modifying parent's markdown projections

**Allowed Operations**:
- ✓ Reading parent truth files for reference
- ✓ Copying parent entries to spinoff truth files
- ✓ Extending parent world rules in spinoff truth files
- ✓ Creating spinoff-specific entries

### Spinoff Maintains Own Truth Files

Spinoff has independent truth files in `books/<spinoff-id>/story/state/`:

**Spinoff Markdown Projections** (read by agents):
- `current_state.md` — Spinoff protagonist state (extends parent)
- `pending_hooks.md` — Spinoff hooks (must be isolated per Dimension 31)
- `chapter_summaries.md` — Spinoff chapter events
- `resource_ledger.md` — Spinoff resources (independent from parent)
- `story_bible.md` — Spinoff world rules (extends parent)
- `style_guide.md` — Spinoff writing style

**Spinoff Internal State** (`story/state/`):
- `current_state.json` — Structured current state
- `pending_hooks.json` — Structured hook records
- `chapter_summaries.json` — Structured chapter summaries

**Inheritance Pattern**:
1. Spinoff reads parent truth files
2. Spinoff copies relevant entries to own truth files
3. Spinoff extends or modifies copied entries in own files
4. Spinoff updates only affect spinoff truth files

## Timeline Management

**Offset Values** (stored in `book.json` as `timelineOffset`):
- **Negative**: Prequel (e.g., -365 = 1 year before parent start)
- **Positive**: Sequel (e.g., 730 = 2 years after parent end)
- **Zero**: Side story or POV shift (parallel timeline)

**Overlap** (side stories): `timelineOverlap: true` with `overlapStart`/`overlapEnd` chapter range. Spinoff events must align with parent events in overlap range.

**Locked Timeline** (POV shifts): `timelineLocked: true`. Chapters map 1:1, all shared events must match exactly, only internal character experience differs. Dimension 28 is strictest for POV shifts.

## Spinoff Workflow

### 1. Create Spinoff Book

```bash
/novel create --spinoff --parent parent-book-id --type prequel --title "Origins" --offset -365
```

This creates spinoff book with parent link.

### 2. Review Parent Canon

Read `story/parent_canon.md` and verify:
- Parent book events are accurate
- World rules are complete
- Character states are correct
- Timeline relationship is clear

Edit `parent_canon.md` to add constraints or clarifications.

### 3. Import Parent State

For sequels, import parent's final state:

```bash
/novel create --spinoff --import-parent-state
```

This copies parent's final truth file state to spinoff's initial state.

### 4. Write Chapters

Use standard writing commands:

```bash
/novel-write --count 5
```

The writer agent loads `parent_canon.md` and respects parent book constraints.

### 5. Audit with Spinoff Dimensions

```bash
/novel-review --audit --chapter 3
```

Audit report includes dimensions 28-31 with spinoff-specific checks.

### 6. Validate Cross-Book Consistency

Run cross-book validation:

```bash
/novel-review --audit --validate-consistency
```

This checks:
- No canon event conflicts (Dimension 28)
- No future information leaks (Dimension 29)
- No world rule violations (Dimension 30)
- Hook isolation (Dimension 31)

## Conditional Activation Logic

Spinoff dimensions activate based on `book.json` configuration:

```json
{
  "id": "spinoff-001",
  "title": "Origins",
  "genre": "xuanhuan",
  "parentBookId": "parent-001",
  "spinoffType": "prequel",
  "timelineOffset": -365
}
```

**Activation Rules**:
- If `parentBookId` is **not set**: Dimensions 28-31 are **skipped**
- If `parentBookId` is **set**: Dimensions 28-31 are **active**

**All Spinoff Dimensions are Critical or Warning**:
- Dimension 28 (Canon Event Conflict): **Critical**
- Dimension 29 (Future Information Leak): **Critical**
- Dimension 30 (Cross-Book World Rules): **Critical**
- Dimension 31 (Spinoff Hook Isolation): **Warning**

## Quick Reference

**4 Spinoff Types**: prequel (before parent), sequel (after parent), side-story (parallel), pov-shift (same events)  
**Create Spinoff**: `/novel create --spinoff --parent <id> --type <type> --title <title>`  
**Parent Link**: `book.json` field `parentBookId`  
**Canon Storage**: `books/<spinoff-id>/story/parent_canon.md`  
**Timeline Offset**: Negative (prequel), Positive (sequel), Zero (parallel)  
**Spinoff Dimensions**: 28 (Canon Event Conflict), 29 (Future Info Leak), 30 (World Rules), 31 (Hook Isolation)  
**Activation**: Dimensions 28-31 only active when `parentBookId` is set  
**Read-Only**: Parent truth files cannot be modified by spinoff  
**Independent State**: Spinoff maintains own truth files  
**Timeline Validation**: Characters cannot reference future events (Dimension 29)
