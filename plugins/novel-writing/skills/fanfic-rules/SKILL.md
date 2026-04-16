---
name: fanfic-rules
description: Fan fiction writing rules with 4 modes and conditional audit dimensions
version: 1.0.0
---

# Fan Fiction Rules

## Overview

InkOS supports fan fiction creation with source material analysis, 4 fanfic modes (canon, au, ooc, cp), and 4 conditional audit dimensions (34-37) that activate only when `book.json` has `fanficMode` set. Fanfic mode controls how strictly the story adheres to source material characterization, world rules, relationships, and events.

## Fanfic Modes

### Mode 1: canon (Faithful)

**Description**: Strict adherence to source material. Characters must act consistently with canon personality, world rules cannot be violated, events must align with source timeline.

**Characteristics**:
- Character behavior must match source material
- World rules (magic systems, technology, physics) are immutable
- Canon events are reference points, cannot be contradicted
- Relationship dynamics follow source material
- Divergence requires explicit justification

**Audit Behavior**:
- Dimension 34 (Character Fidelity): **Active, Critical**
- Dimension 35 (World Rule Compliance): **Active, Critical**
- Dimension 36 (Relationship Dynamics): **Active, Warning**
- Dimension 37 (Canon Event Consistency): **Active, Critical**

**Use Case**: Missing scenes, gap-filling, character studies, canon-compliant continuations

### Mode 2: au (Alternate Universe)

**Description**: World rules and events can diverge from canon. "What if" scenarios where key events happened differently or world mechanics changed.

**Characteristics**:
- World rules can be modified (e.g., "What if magic worked differently?")
- Canon events can diverge after a specified divergence point
- Character personalities should remain recognizable
- Relationship dynamics can shift due to changed circumstances

**Audit Behavior**:
- Dimension 34 (Character Fidelity): **Active, Critical** (personality core preserved)
- Dimension 35 (World Rule Compliance): **Relaxed** (divergence allowed)
- Dimension 36 (Relationship Dynamics): **Active, Warning** (shifts must be justified)
- Dimension 37 (Canon Event Consistency): **Skipped** (events can diverge)

**Use Case**: "What if X never happened?", alternate timelines, world rule changes

### Mode 3: ooc (Out of Character Allowed)

**Description**: Characters can behave differently from source material. Personality changes, different motivations, or character exploration outside canon boundaries.

**Characteristics**:
- Character behavior can deviate from source material
- World rules remain consistent with source
- Canon events are respected
- Relationship dynamics can shift due to character changes

**Audit Behavior**:
- Dimension 34 (Character Fidelity): **Skipped** (OOC allowed)
- Dimension 35 (World Rule Compliance): **Active, Critical**
- Dimension 36 (Relationship Dynamics): **Relaxed** (character-driven shifts allowed)
- Dimension 37 (Canon Event Consistency): **Active, Critical**

**Use Case**: Character redemption arcs, personality inversions, "What if character X was different?"

### Mode 4: cp (Ship-Focused)

**Description**: Relationship dynamics prioritized over strict canon adherence. Romance and character interactions are the focus, with flexibility in characterization to serve the relationship arc.

**Characteristics**:
- Relationship development is the primary goal
- Character behavior adjusted to support romantic arc
- World rules and events serve the relationship story
- Canon events can be modified if they interfere with the ship

**Audit Behavior**:
- Dimension 34 (Character Fidelity): **Relaxed** (adjusted for romance)
- Dimension 35 (World Rule Compliance): **Active, Warning** (world serves story)
- Dimension 36 (Relationship Dynamics): **Relaxed** (ship-focused)
- Dimension 37 (Canon Event Consistency): **Relaxed** (events serve romance)

**Use Case**: Shipping fics, romance-focused stories, relationship exploration

## Source Material Import (REQ-F-37)

### Step 1: Import Source Text

```bash
/novel create --fanfic --title "My Fanfic" --from source.txt --mode canon
```

The import process:
1. Reads source material text
2. Analyzes content for key elements
3. Extracts structured information
4. Stores in `books/<book-id>/story/fanfic_canon.md`

### Step 2: Source Material Analysis

The analyzer extracts:

**Character Profiles**:
- Name, aliases, titles
- Personality traits (core traits vs. situational behavior)
- Motivations and goals
- Speech patterns and mannerisms
- Abilities and limitations
- Character arc trajectory

**World Rules**:
- Magic/power system mechanics
- Technology level and constraints
- Physical laws (if different from reality)
- Social structures and hierarchies
- Geography and locations

**Relationship Dynamics**:
- Character relationships (allies, enemies, family, romantic)
- Relationship history and development
- Power dynamics between characters
- Unresolved tensions or conflicts

**Canon Events**:
- Timeline of major events
- Cause-and-effect chains
- Unresolved plot threads
- Foreshadowed future events

### Step 3: fanfic_canon.md Structure

```markdown
# Fanfic Canon Reference

## Source Material
- Title: [Source work title]
- Author: [Original author]
- Divergence Point: [Chapter/episode where fanfic diverges]

## Characters

### [Character Name]
- **Personality**: [Core traits]
- **Motivations**: [Goals and drives]
- **Abilities**: [Powers, skills, limitations]
- **Speech Patterns**: [Distinctive language use]
- **Relationships**: [Key connections]

## World Rules

### Magic System
[Description of how magic works]

### Technology Level
[Tech constraints and capabilities]

### Social Structure
[Hierarchies, factions, organizations]

## Canon Events Timeline

1. [Event 1] - [Consequences]
2. [Event 2] - [Consequences]
...

## Relationship Map

- [Character A] ↔ [Character B]: [Relationship type and status]
...

## Unresolved Threads

- [Plot thread 1]
- [Plot thread 2]
...
```

## Information Boundary Management (REQ-F-40)

### Divergence Point Tracking

The divergence point is the moment where the fanfic timeline splits from canon:

```yaml
divergencePoint:
  chapter: 15
  event: "Harry refuses to participate in the Triwizard Tournament"
  timestamp: "Year 4, October"
```

### Knowledge Validation Rules

Characters cannot reference information revealed after the divergence point:

**Example (Harry Potter fanfic)**:
- Divergence point: End of Year 4
- ✗ Invalid: Character mentions Horcruxes (revealed in Year 6)
- ✓ Valid: Character mentions Triwizard Tournament (happened before divergence)

**Implementation**:
1. Track divergence point in `fanfic_canon.md`
2. During audit, Dimension 37 checks character knowledge against timeline
3. Flag any references to post-divergence information

### Information Boundary by Mode

- **canon**: Strict boundary enforcement, no future knowledge
- **au**: Boundary at divergence point, post-divergence events don't exist
- **ooc**: Boundary enforced, but character reactions can differ
- **cp**: Relaxed boundary if future knowledge serves relationship arc

## Fanfic Audit Dimensions (34-37)

### Dimension 34: Character Fidelity

**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `fanficMode` is set  
**Exception**: Skipped if `fanficMode="ooc"`

**Description**: Characters act inconsistently with source material characterization.

**Check Process**:
1. Read character profile from `fanfic_canon.md`
2. Compare chapter character actions/dialogue against profile
3. Flag if behavior contradicts core personality traits
4. Allow situational variation if justified by circumstances

**Examples**:
- ✗ Hermione ignoring rules without character development
- ✗ Stoic character suddenly emotional without cause
- ✓ Character acting differently under extreme stress (justified)

### Dimension 35: World Rule Compliance

**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `fanficMode` is set  
**Exception**: Relaxed if `fanficMode="au"`

**Description**: Story violates source material's world rules or magic system.

**Check Process**:
1. Read world rules from `fanfic_canon.md`
2. Compare chapter world mechanics against established rules
3. Flag contradictions (unless mode="au")
4. Allow extensions if they don't contradict existing rules

**Examples**:
- ✗ Magic working differently without AU justification
- ✗ Technology appearing that contradicts era
- ✓ New spell that follows established magic system rules

### Dimension 36: Relationship Dynamics

**Severity**: Warning  
**Detection**: LLM judgment  
**Activation**: Only when `fanficMode` is set  
**Exception**: Relaxed if `fanficMode="cp"`

**Description**: Character relationships deviate from source material without justification.

**Check Process**:
1. Read relationship map from `fanfic_canon.md`
2. Compare chapter relationship developments against map
3. Flag if dynamics shift without buildup
4. Allow gradual development with proper justification

**Examples**:
- ✗ Enemies suddenly friends without reconciliation arc
- ✗ Romance appearing without buildup
- ✓ Relationship shift with clear development over multiple chapters

### Dimension 37: Canon Event Consistency

**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `fanficMode` is set  
**Exception**: Skipped if `fanficMode="au"`

**Description**: Story contradicts source material's established events.

**Check Process**:
1. Read canon timeline from `fanfic_canon.md`
2. Compare chapter events against timeline
3. Flag contradictions (unless mode="au")
4. Verify divergence point is respected

**Examples**:
- ✗ Character alive when canon established their death (mode="canon")
- ✗ Event happening that contradicts pre-divergence timeline
- ✓ Post-divergence events differing from canon (mode="au")

## Conditional Activation Logic

Fanfic dimensions activate based on `book.json` configuration:

```json
{
  "id": "fanfic-001",
  "title": "My Fanfic",
  "genre": "isekai",
  "fanficMode": "au",
  "fanficSource": "story/fanfic_canon.md"
}
```

**Activation Rules**:
- If `fanficMode` is **not set**: Dimensions 34-37 are **skipped**
- If `fanficMode` is **set**: Dimensions 34-37 are **active** with mode-specific adjustments

**Mode-Specific Adjustments**:

| Dimension | canon | au | ooc | cp |
|-----------|-------|----|----|-----|
| 34 (Character Fidelity) | Critical | Critical | **Skipped** | Relaxed |
| 35 (World Rule Compliance) | Critical | **Relaxed** | Critical | Warning |
| 36 (Relationship Dynamics) | Warning | Warning | **Relaxed** | **Relaxed** |
| 37 (Canon Event Consistency) | Critical | **Skipped** | Critical | Relaxed |

## Fanfic Workflow

### 1. Create Fanfic Book

```bash
/novel create --fanfic --title "My Fanfic" --from source.txt --mode au
```

This creates:
- `book.json` with `fanficMode: "au"`
- `story/fanfic_canon.md` with extracted source material
- Standard truth files
- Control documents (author_intent.md, current_focus.md)

### 2. Review Source Analysis

Read `story/fanfic_canon.md` and verify:
- Character profiles are accurate
- World rules are complete
- Relationship map is correct
- Canon timeline is accurate

Edit `fanfic_canon.md` to add missing details or correct errors.

### 3. Set Divergence Point

Edit `fanfic_canon.md` to specify where the story diverges:

```yaml
divergencePoint:
  chapter: 10
  event: "Protagonist refuses the quest"
  timestamp: "Day 15 of the journey"
```

### 4. Write Chapters

Use standard writing commands:

```bash
/novel-write --count 5
```

The writer agent loads `fanfic_canon.md` and respects the fanfic mode.

### 5. Audit with Fanfic Dimensions

```bash
/novel-review --audit --chapter 3
```

Audit report includes dimensions 34-37 with mode-specific severity.

### 6. Revise if Needed

If fanfic dimensions fail:

```bash
/novel-review --audit-fix --chapter 3 --mode spot-fix
```

Reviser agent fixes character fidelity, world rule, relationship, or event consistency issues.

## Quick Reference

**4 Fanfic Modes**: canon (faithful), au (alternate universe), ooc (out of character), cp (ship-focused)  
**Source Import**: `/novel create --fanfic --from source.txt --mode <mode>`  
**Canon Storage**: `books/<book-id>/story/fanfic_canon.md`  
**Divergence Point**: Tracked in fanfic_canon.md, enforces information boundary  
**Fanfic Dimensions**: 34 (Character Fidelity), 35 (World Rules), 36 (Relationships), 37 (Canon Events)  
**Activation**: Dimensions 34-37 only active when `book.json` has `fanficMode` set  
**Mode Adjustments**: Each mode relaxes or skips specific dimensions  
**Information Boundary**: Characters cannot reference knowledge revealed after divergence point
