---
name: settlement
description: Detailed instructions for Phase 2 settlement — fact extraction and delta generation within WriterAgent.settleChapterState()
---

# Settlement Skill

This skill contains the detailed instructions for **Phase 2: Settlement** of the WriterAgent.
Phase 2 runs at **temperature 0.3** (analytical mode) after Phase 1 creative writing completes.

In InkOS, settlement is an integrated part of `WriterAgent.settleChapterState()` — there are no
separate observer or reflector agents. The writer agent performs both fact extraction and delta
generation in a single settlement pass.

---

## Step 1: Fact Extraction (9 Categories)

Read the newly written chapter and comprehensively extract all observable fact changes across 9 categories.
The goal is to **over-extract** — better to capture too much than miss something.

### 9 Fact Categories

1. **Characters**: Names, introductions, actions, dialogue, descriptions
2. **Locations**: Places mentioned, descriptions, travel between locations
3. **Events**: What happened, sequence, outcomes, significance
4. **Items**: Objects introduced, used, transferred, destroyed
5. **Abilities**: Powers/skills demonstrated, learned, lost, limitations
6. **Relationships**: Character interactions, relationship changes, conflicts, alliances
7. **Emotional States**: Character emotions, intensity (1-10), triggers, changes
8. **Timeline**: Time references (hours, days, seasons), duration, sequence markers
9. **World Rules**: Magic/tech demonstrated, constraints revealed, lore established

### Extraction Principles

For each fact, record:
- Category
- Description (specific, concrete — "Lin Chen's left arm fractured" not "Lin Chen got hurt")
- Location in chapter (paragraph number or scene)
- Significance (major plot point vs minor detail)

### Over-Extraction Principle

Extract MORE rather than less. Include:
- **Obvious facts**: Character names, major events
- **Subtle facts**: Implied emotions, background details
- **Negative facts**: Character did NOT do something significant
- **Continuity facts**: Character still at location X, still has item Y

### Critical Extraction Rules

1. **Extract from TEXT ONLY** — Do not infer, predict, or add content not in the chapter
2. **Be specific** — Use precise descriptions, not vague summaries
3. **Include scene context** — Note which characters are present in each scene
4. **Over-extract** — If unsure whether something is significant, include it
5. **No interpretation** — Record what happened, not why it matters

### Extraction Output Format

Return structured text organized by category:

```
=== OBSERVATIONS ===

[CHARACTERS]
- Alice: Introduced as protagonist, age 17, orphan, lives in village (paragraph 1)
- Bob: Mentioned as Alice's mentor, not present in this scene (paragraph 3)

[LOCATIONS]
- Forest clearing: Described as "ancient trees, moss-covered stones, quiet" (paragraph 5)
- Travel: Alice walked from village to forest clearing, took 2 hours (paragraph 4-5)

[EVENTS]
- Alice left village at dawn to search for herbs (paragraph 2)
- Alice discovered glowing stone in clearing (paragraph 7)

[ITEMS]
- Glowing stone: Blue, palm-sized, warm to touch, found in clearing (paragraph 7-9)

[ABILITIES]
- Alice: Demonstrated knowledge of forest paths (paragraph 4)

[RELATIONSHIPS]
- Alice -> Bob: Trusts him as mentor, plans to show him the stone (paragraph 11)

[EMOTIONAL_STATES]
- Alice: Curious -> Excited (intensity: 7, trigger: finding stone, paragraph 7-9)
- Alice: Excited -> Fearful (intensity: 6, trigger: hearing roar, paragraph 12)

[TIMELINE]
- Dawn: Alice left village (paragraph 2)
- 2 hours later: Arrived at clearing (paragraph 5)

[WORLD_RULES]
- Magic stones exist in this world, can react to human touch (paragraph 9)
```

---

## Step 2: Delta Generation (Structured JSON)

Convert the extracted facts into a structured JSON delta. This delta is then applied to truth files
by the settler to update the book's state.

### Process

1. Read current truth files from `books/<id>/story/state/*.json`
2. For each extracted fact, determine:
   - Which truth file(s) it affects
   - What operation to perform (add, update, resolve)
   - Whether it's a hook operation
3. Generate **hookOps** (see below)
4. Generate **currentStatePatch** for each truth file
5. Generate **chapterSummary** with events, progression, foreshadowing
6. Write delta to `books/<id>/story/runtime/chapter-XXXX.delta.json`

### Hook Operations (hookOps)

| Operation | When to Use |
|-----------|-------------|
| **upsert** | New cliffhanger/promise/mystery introduced, OR existing hook advanced with new information |
| **mention** | Existing hook referenced in dialogue/narration, but no new information or progress |
| **resolve** | Hook payoff delivered (answer revealed, promise fulfilled) |
| **defer** | Hook explicitly postponed ("we'll deal with this later") |

### Hook Operation Rules

1. **Only upsert existing hookIds** — Do NOT invent new hookIds
2. **Brand-new threads -> newHookCandidates** — Let the system decide if it's truly new
3. **Mention vs Advance**: If hook is only mentioned without new info -> `mention`; if hook has new facts/evidence -> `upsert` with updated `lastAdvancedChapter`
4. **payoffTiming semantics**:
   - `immediate`: Resolve within 1-3 chapters
   - `near-term`: Resolve within 5-10 chapters
   - `mid-arc`: Resolve within current arc (10-30 chapters)
   - `slow-burn`: Long-term setup (30+ chapters)
   - `endgame`: Book-level payoff

### Truth Files Affected by currentStatePatch

| Truth File | What Changes |
|------------|-------------|
| `world_state` | New locations, rules, technology |
| `character_matrix` | New characters, ability changes, relationship updates |
| `resource_ledger` | Item transfers, power level changes |
| `chapter_summaries` | This chapter's summary |
| `subplot_board` | Subplot status changes |
| `emotional_arcs` | Character emotion progressions |
| `pending_hooks` | Hook status updates (via hookOps) |

> **Persistence note**: subplotOps, emotionalArcOps, characterMatrixOps, and resourceLedgerOps are persisted to JSON state files and rendered to markdown projections read by the auditor. They are NOT decorative — omitting them when changes occur causes stale audit data.

### resourceLedgerOps (Genre-Conditional)

Only generate `resourceLedgerOps` for genres whose profile includes a `numericalSystem` field (e.g. xianxia, litrpg, progression fantasy). For genres without `numericalSystem`, omit the field entirely.

Each operation is a `snapshot` that records the opening and closing state of a tracked resource for the current chapter.

| Field | Required | Description |
|-------|----------|-------------|
| `op` | Yes | Always `"snapshot"` |
| `id` | Yes | Unique resource identifier (e.g. `"spirit-stones"`, `"cultivation-level"`) |
| `name` | Yes | Display name (e.g. `"Spirit Stones"`) |
| `type` | Yes | Resource type: `"currency"`, `"power-level"`, `"item"`, `"reputation"` |
| `owner` | Yes | Character ID who owns/controls this resource |
| `openingState` | Yes | State at chapter start (e.g. `"1000 spirit stones"`) |
| `closingState` | Yes | State at chapter end (e.g. `"750 spirit stones"`) |
| `delta` | Yes | Change description (e.g. `"-250 spent on formation materials"`) — see required-field rules below |
| `source` | No | Source of the change (e.g. `"purchased from merchant"`) |
| `notes` | No | Additional context |

Example:
```json
"resourceLedgerOps": [
  {
    "op": "snapshot",
    "id": "spirit-stones",
    "name": "Spirit Stones",
    "type": "currency",
    "owner": "lin-chen",
    "openingState": "1000 spirit stones",
    "closingState": "750 spirit stones",
    "delta": "-250 spent on formation materials",
    "source": "purchased from merchant"
  },
  {
    "op": "snapshot",
    "id": "cultivation-level",
    "name": "Cultivation Level",
    "type": "power-level",
    "owner": "lin-chen",
    "openingState": "Qi Condensation Stage 7",
    "closingState": "Qi Condensation Stage 8",
    "delta": "Breakthrough after absorbing spirit stone energy"
  }
]
```

### ResourceLedgerOp.delta (REQUIRED as of subsystem 1)

Every resourceLedgerOp MUST include a non-empty `delta` string describing the change. Format: `<sign><magnitude> <reason>`. Examples:
- `"-250 spent on formation materials"`
- `"+50 looted from beast"`
- `"0 no change this chapter"` — when opening equals closing
- `"initial"` — when this is the resource's first appearance

Writer and reviser both must populate this field. `apply-delta.py` raises `ResourceLedgerFieldError` on any missing or empty delta and exits 1, which triggers settlement recovery.

### Delta JSON Structure

Write to `books/<id>/story/runtime/chapter-XXXX.delta.json`:

```json
{
  "chapter": 12,
  "currentStatePatch": {
    "currentLocation": "Forest clearing",
    "protagonistState": "Injured, left shoulder",
    "currentGoal": "Find mentor",
    "currentConstraint": "Limited spiritual energy",
    "currentAlliances": "None",
    "currentConflict": "Confrontation with mysterious woman"
  },
  "hookOps": {
    "upsert": [
      {
        "hookId": "glowing-stone-mystery",
        "startChapter": 12,
        "type": "mystery",
        "status": "open",
        "lastAdvancedChapter": 12,
        "expectedPayoff": "Reveal stone's origin and power",
        "payoffTiming": "near-term",
        "notes": "Stone reacted to protagonist's touch, emitted blue light"
      }
    ],
    "mention": ["mentor-relationship"],
    "resolve": [],
    "defer": []
  },
  "newHookCandidates": [
    {
      "type": "threat",
      "expectedPayoff": "Identify source of distant roar",
      "payoffTiming": "immediate",
      "notes": "Protagonist heard roar, felt danger"
    }
  ],
  "chapterSummary": {
    "chapter": 12,
    "title": "Discovery in the Forest",
    "characters": "Alice, Bob (mentioned)",
    "events": "Alice found glowing stone, heard mysterious roar",
    "stateChanges": "Acquired glowing stone, moved to forest clearing",
    "hookActivity": "glowing-stone-mystery opened",
    "mood": "Curious -> Fearful",
    "chapterType": "setup"
  },
  "subplotOps": [],
  "emotionalArcOps": [
    {
      "characterId": "alice",
      "characterName": "Alice",
      "progression": [
        {
          "chapter": 12,
          "emotion": "fear",
          "intensity": "medium",
          "pressureShape": "rising",
          "trigger": "Heard distant roar in forest"
        }
      ]
    }
  ],
  "characterMatrixOps": [],
  "resourceLedgerOps": [
    {
      "op": "snapshot",
      "id": "spirit-stones",
      "name": "Spirit Stones",
      "type": "currency",
      "owner": "alice",
      "openingState": "1000 spirit stones",
      "closingState": "750 spirit stones",
      "delta": "-250 spent on formation materials",
      "source": "purchased from merchant in forest clearing"
    }
  ],
  "notes": [
    "Stone's properties need further investigation",
    "Roar source unidentified, potential threat"
  ]
}
```

### Validation Rules

1. `chapter` must match input chapter number
2. `chapterSummary.chapter` must equal `delta.chapter`
3. `hookOps.upsert` must only contain existing hookIds OR be empty
4. `newHookCandidates` for brand-new threads only
5. All hookIds in mention/resolve/defer must be non-empty strings
6. `delta.chapter` must be > `lastAppliedChapter` (no backwards chapter numbers)

### Mapping Example: Extraction -> Delta

**Extracted fact**:
```
[EVENTS]
- Alice discovered glowing stone in clearing
- Stone reacted to Alice's touch, emitted blue light
```

**Generated delta**:
```json
{
  "hookOps": {
    "upsert": [
      {
        "hookId": "glowing-stone-mystery",
        "type": "mystery",
        "expectedPayoff": "Reveal stone's origin and power",
        "notes": "Stone reacted to touch, emitted blue light"
      }
    ]
  },
  "chapterSummary": {
    "events": "Alice found glowing stone, stone reacted to touch"
  }
}
```

---

## Step 3: Hook Admission Control (`evaluateHookAdmission`)

Before adding any entry from `newHookCandidates` to the hook registry, validate and deduplicate.

### 3a: Required Field Check

Each candidate MUST have:
- `type` — hook category (e.g. mystery, promise, cliffhanger, threat, prophecy)
- `expectedPayoff` — what the reader expects to learn or see resolved

If either field is missing or empty, **REJECT** the candidate. Record the rejection reason in `notes`:
```
"Rejected hook candidate: missing required field 'type'"
"Rejected hook candidate: missing required field 'expectedPayoff'"
```

### 3b: Family Dedup Detection

For candidates that pass the required field check, scan existing active hooks (status `open` or `progressing`) for family matches.

**Family match = same `type` AND semantic overlap.**

#### Semantic Overlap Detection

**Chinese (zh)**: Bigram overlap
1. Extract all consecutive two-character pairs from both the candidate's `notes`/`expectedPayoff` and the existing hook's `notes`/`expectedPayoff`
2. Count shared bigrams
3. Match threshold: >= 3 shared bigrams

Example:
- Existing hook notes: "主角在古墓中发现神秘玉佩" → bigrams: 主角, 角在, 在古, 古墓, 墓中, 中发, 发现, 现神, 神秘, 秘玉, 玉佩
- Candidate notes: "神秘玉佩发出微弱光芒" → bigrams: 神秘, 秘玉, 玉佩, 佩发, 发出, 出微, 微弱, 弱光, 光芒
- Shared: 神秘, 秘玉, 玉佩 = 3 shared bigrams → MATCH

**English (en)**: Significant term overlap
1. Extract significant terms (nouns, verbs) from both descriptions. Exclude stop words (the, a, an, is, was, has, it, in, on, at, to, of, and, or, but, for, with, this, that)
2. Compare term sets (case-insensitive)
3. Match threshold: >= 2 shared significant terms

Example:
- Existing hook notes: "ancient artifact discovered in hidden chamber"
- Candidate notes: "artifact emits strange energy signal"
- Shared terms: artifact = 1 → NO MATCH (< 2)
- Candidate notes: "ancient artifact emits energy pulses"
- Shared terms: ancient, artifact = 2 → MATCH

### 3c: Merge Strategy

When a family match is found, MERGE into the existing hook instead of creating a new one.

Apply these merge rules:

| Field | Merge Rule |
|-------|-----------|
| `hookId` | Keep existing (never create new) |
| `startChapter` | Take **min** (earlier introduction) |
| `lastAdvancedChapter` | Take **max** (most recent advancement) |
| `expectedPayoff` | Take **longer** by character count; if equal, take candidate (newer) |
| `notes` | Take **longer** by character count; if equal, take candidate (newer) |
| `status` | Take more advanced: `progressing` > `open` |
| `payoffTiming` | Keep the shorter horizon (e.g. near-term > mid-arc) |

The merged hook goes into `hookOps.upsert` (with the existing `hookId`). The candidate is removed from `newHookCandidates`.

If no family match, the candidate stays in `newHookCandidates` for the pipeline to create a new hook record.

---

## Step 4: Predicate Alias Replacement (`currentStatePatch`)

### 4a: Predicate Alias Map

When applying `currentStatePatch`, field names may appear in multiple languages. Use this alias map to resolve field identity:

| Canonical Field | Aliases |
|----------------|---------|
| `currentLocation` | `当前位置`, `Current Location`, `location` |
| `protagonistState` | `主角状态`, `Protagonist State`, `state` |
| `currentGoal` | `当前目标`, `Current Goal`, `goal` |
| `currentConstraint` | `当前限制`, `Current Constraint`, `constraint` |
| `currentAlliances` | `当前敌我`, `Current Alliances`, `alliances` |
| `currentConflict` | `当前冲突`, `Current Conflict`, `conflict` |

### 4b: Replacement (Not Append) Semantics

When `currentStatePatch` contains a field that matches an existing fact's predicate (via the alias map above):
- **REPLACE** the existing value — do NOT append a new fact
- If no existing fact matches the predicate, **ADD** as a new entry

Example:
```
Existing current_state facts:
  { predicate: "当前目标", value: "修炼突破筑基" }

currentStatePatch:
  { "currentGoal": "寻找失落的功法" }

Result:
  { predicate: "当前目标", value: "寻找失落的功法" }
  (old value "修炼突破筑基" is replaced, not kept alongside)
```

### 4c: Processing Order

1. Normalize all patch field names using the alias map → canonical field names
2. For each canonical field in the patch, search existing facts for any predicate matching any alias of that canonical field
3. If match found: replace the value in place
4. If no match: add new fact with canonical field name as predicate

---

## Error Handling

### Fact Extraction Errors
- **If chapter is empty**: Return empty extraction
- **If chapter is truncated**: Extract what's available, note truncation
- **If chapter contains no facts**: Return minimal extraction with note

### Delta Generation Errors
- **If extraction is empty**: Generate minimal delta (chapter summary only)
- **If truth files are corrupt**: Note in delta, settler will handle recovery
- **If hookId not found in current hooks**: Put in newHookCandidates instead

---

## Critical Rules Summary

1. Extract from TEXT ONLY — no inference, no prediction
2. Cross-validate with truth files — ensure consistency
3. Preserve immutability — delta is append-only
4. Over-extract facts, but generate precise deltas
5. Hook operations follow strict rules (no invented hookIds)
6. Hook admission: reject candidates missing `type` or `expectedPayoff` (Step 3a)
7. Hook family dedup: merge same-type hooks with semantic overlap (Step 3b-3c)
8. Predicate aliases: currentStatePatch replaces (never appends) via alias map (Step 4)
9. Settlement output feeds into settler for truth file updates and markdown projection regeneration

---

## Recovery Integration

When settlement validation fails, the pipeline invokes `python3 $.plugin.directory/scripts/pipeline/state-manager.py recovery` to handle the failure:

1. **Validation failure detected**: `truth-validate.sh` reports errors on persisted truth files
2. **Recovery invoked**: `python3 $.plugin.directory/scripts/pipeline/state-manager.py recovery <book-dir> <chapter> '<errors-json>'`
3. **Backup created**: Current truth files are backed up to `story/state/.recovery-backup/`
4. **Recovery guidance written**: Validation errors written to `runtime/recovery-guidance.json` as correction hints for the retry settlement pass
5. **Retry validation**: After the pipeline re-runs settlement, the recovery function re-validates truth files
6. **On success**: Backup is cleaned up, pipeline continues
7. **On failure**: Old truth files are restored from backup, chapter is marked `state-degraded` in `chapter-meta.json`

The settlement agent should check for `runtime/recovery-guidance.json` before generating a retry delta. If present, use the validation errors as correction guidance to avoid repeating the same mistakes.
