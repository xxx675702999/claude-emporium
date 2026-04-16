---
name: schemas-truth
description: Truth file schemas with field-level validation rules
version: 1.0.0
---

# Truth File Schemas

## Overview

InkOS maintains structured state as schema-validated JSON in `books/<id>/story/state/` (internal) with markdown projections in `books/<id>/story/` for agent consumption. Agents read markdown; JSON is the persistence format. Implemented: all 7 truth files (current_state, pending_hooks, chapter_summaries, world_state, character_matrix, resource_ledger, subplot_board, emotional_arcs).

## Schema Version

All truth files use schema version 2 with the following manifest:

```json
{
  "schemaVersion": 2,
  "language": "zh" | "en",
  "lastAppliedChapter": number,
  "projectionVersion": number,
  "migrationWarnings": string[]
}
```

## 1. current_state.json

Tracks the protagonist's current situation and known facts.

### Schema

```typescript
{
  chapter: number,           // Current chapter number (≥0)
  facts: Array<{
    subject: string,         // Fact subject (required, min 1 char)
    predicate: string,       // Fact predicate/label (required, min 1 char)
    object: string,          // Fact value (required, min 1 char)
    validFromChapter: number,    // When this fact became true (≥0)
    validUntilChapter: number | null,  // When invalidated (null = still valid)
    sourceChapter: number    // Chapter that introduced this fact (≥0)
  }>
}
```

### Standard Predicates

- `Current Location` / `当前位置`: Where protagonist is now
- `Protagonist State` / `主角状态`: Physical/mental condition
- `Current Goal` / `当前目标`: Active objective
- `Current Constraint` / `当前限制`: Limitations or restrictions
- `Current Alliances` / `当前敌我`: Relationship status with factions
- `Current Conflict` / `当前冲突`: Active conflict description

### Validation Rules

- `chapter` must be non-negative integer
- Each fact must have non-empty `subject`, `predicate`, `object`
- `validFromChapter` ≤ `validUntilChapter` (when not null)
- `sourceChapter` ≤ `validFromChapter`
- No duplicate facts with same predicate (latest wins)

### Markdown Projection

Rendered as a two-column table with standard predicates first, then additional facts as bullet points.

## 2. hooks.json (pending_hooks.json)

Tracks unresolved plot hooks, cliffhangers, and promises.

### Schema

```typescript
{
  hooks: Array<{
    hookId: string,              // Unique identifier (required, min 1 char)
    startChapter: number,        // Chapter where hook was introduced (≥0)
    type: string,                // Hook category (required, min 1 char)
    status: "open" | "progressing" | "deferred" | "resolved",
    lastAdvancedChapter: number, // Last chapter that moved this hook (≥0)
    expectedPayoff: string,      // What resolution looks like (default "")
    payoffTiming?: "immediate" | "near-term" | "mid-arc" | "slow-burn" | "endgame",
    notes: string                // Additional context (default "")
  }>
}
```

### Hook Status Semantics

- `open`: Introduced but not yet advanced
- `progressing`: Actively being developed
- `deferred`: Intentionally postponed
- `resolved`: Payoff delivered

### Payoff Timing

- `immediate`: Resolve within 1-3 chapters
- `near-term`: Resolve within 5-10 chapters
- `mid-arc`: Resolve within current arc (10-30 chapters)
- `slow-burn`: Long-term setup (30+ chapters)
- `endgame`: Book-level payoff

### Validation Rules

- `hookId` must be unique across all hooks
- `startChapter` ≤ `lastAdvancedChapter`
- `status` must be one of the four valid values
- `payoffTiming` must be one of the five valid values (when present)
- No duplicate `hookId` entries

### Markdown Projection

Rendered as an 8-column table sorted by `startChapter`, then `lastAdvancedChapter`, then `hookId`.

## 3. chapter_summaries.json

Stores per-chapter summaries for context retrieval and pacing analysis.

### Schema

```typescript
{
  rows: Array<{
    chapter: number,        // Chapter number (≥1)
    title: string,          // Chapter title (required, min 1 char)
    characters: string,     // Characters who appeared (default "")
    events: string,         // Key events summary (default "")
    stateChanges: string,   // State transitions (default "")
    hookActivity: string,   // Hook movements (default "")
    mood: string,           // Emotional tone (default "")
    chapterType: string     // Chapter category (default "")
  }>
}
```

### Chapter Types (Genre-Specific)

Common types: `setup`, `conflict`, `payoff`, `transition`, `climax`, `resolution`, `breather`

### Validation Rules

- `chapter` must be positive integer (≥1)
- `title` must be non-empty
- No duplicate chapter numbers (deduplicated on load)
- Rows sorted by chapter number ascending

### Markdown Projection

Rendered as an 8-column table sorted by chapter number.

## 4. world_state.json

Tracks world rules, locations, technology/magic systems, geography.

### Schema

```typescript
{
  locations: Array<{
    id: string,
    name: string,
    description: string,
    geography: string,
    introducedInChapter: number
  }>,
  rules: Array<{
    id: string,
    category: string,
    rule: string,
    exceptions: string[],
    establishedInChapter: number
  }>,
  technology: Array<{
    id: string,
    name: string,
    capabilities: string,
    limitations: string,
    introducedInChapter: number
  }>
}
```

## 5. character_matrix.json

Tracks character profiles, relationships, arcs, motivations, abilities.

### Schema

```typescript
{
  characters: Array<{
    id: string,
    name: string,
    aliases: string[],
    description: string,
    motivation: string,
    arc: string,
    abilities: string[],
    relationships: Array<{
      targetId: string,
      type: string,
      description: string
    }>,
    status: "active" | "inactive" | "deceased",
    introducedInChapter: number
  }>
}
```

## 6. resource_ledger.json

Tracks in-world resources with opening/closing balances and deltas.

### Schema

```typescript
{
  hardCap: number,           // Maximum allowed total (for power systems)
  currentTotal: number,      // Current sum of all resources
  entries: Array<{
    chapter: number,         // Chapter number (≥1)
    openingValue: number,    // Balance at chapter start
    source: string,          // Resource source/category
    resourceCompleteness: string,  // Completeness description
    delta: number,           // Change during chapter
    closingValue: number,    // Balance at chapter end
    basis: string            // Explanation for delta
  }>
}
```

### Validation Rules

- `chapter` must be positive integer
- `openingValue + delta = closingValue` (accounting identity)
- Entries sorted by chapter ascending
- `currentTotal` should match latest `closingValue`

### Markdown Projection

Rendered as a 7-column table with hardCap and currentTotal in header.

## 7. subplot_board.json

Tracks active and dormant subplots with status and involved characters.

### Schema

```typescript
{
  subplots: Array<{
    id: string,
    name: string,
    status: "active" | "dormant" | "resolved",
    description: string,
    involvedCharacters: string[],
    introducedInChapter: number,
    lastUpdatedChapter: number
  }>
}
```

## 8. emotional_arcs.json

Tracks character emotional progression with pressure shapes.

### Schema

```typescript
{
  arcs: Array<{
    characterId: string,
    characterName: string,
    progression: Array<{
      chapter: number,
      emotion: string,
      intensity: "low" | "medium" | "high" | "critical",
      pressureShape: "rising" | "plateau" | "release" | "reversal",
      trigger: string
    }>
  }>
}
```

## State Update Rules

### Immutability

- Never mutate existing entries
- Append new entries with updated values
- Mark old entries as invalid by setting `validUntilChapter`

### Delta Application

All state updates go through `applyRuntimeStateDelta()` which:

1. Validates delta schema
2. Checks chapter ordering (no backwards deltas)
3. Applies hook operations (upsert/mention/resolve/defer)
4. Applies current state patches
5. Appends chapter summary
6. Validates final state
7. Rolls back on validation failure

### Recovery from Corruption

When JSON is corrupt or missing required fields:

1. Attempt to re-parse markdown projection
2. If no projection exists, reconstruct from latest chapter content
3. If reconstruction fails, bootstrap with empty state at chapter 0
4. Log warning in `manifest.migrationWarnings`

## Quick Reference

### File Locations

- JSON (authoritative): `books/<id>/story/state/*.json`
- Markdown (projection): `books/<id>/story/*.md`
- Manifest: `books/<id>/story/state/manifest.json`

### Validation Entry Points

- `validateRuntimeState()`: Cross-file consistency checks
- Schema parsers: Per-file schema validation
- `applyRuntimeStateDelta()`: Delta validation before application

### Common Validation Errors

- `duplicate_hook_id`: Hook ID appears multiple times
- `duplicate_summary_chapter`: Chapter summary exists twice
- `current_state_ahead_of_manifest`: State chapter > manifest lastAppliedChapter
- `delta chapter goes backwards`: Delta chapter ≤ lastAppliedChapter
- `duplicate summary row`: Chapter summary already exists (when not allowing reapply)
