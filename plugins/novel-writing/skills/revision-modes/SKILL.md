---
name: revision-modes
description: 5 revision modes with scope, limitations, and self-correction loop rules
version: 1.0.0
---

# Revision Modes

## Overview

InkOS supports 5 revision modes for chapter refinement. Each mode has specific scope, limitations, and use cases. Revisions follow a self-correction loop with max 2 rounds (configurable via book.json qualityGates.maxAuditRetries).

## Mode Selection

Choose revision mode based on audit results and user intent:

| Mode | Use When | Scope | Preserves Structure |
|------|----------|-------|---------------------|
| polish | Minor style issues, no critical failures | Surface-level fixes | Yes |
| spot-fix | Specific audit failures (1-3 issues) | Targeted sections | Yes |
| rewrite | Multiple critical issues, poor quality | Major rework | Mostly |
| rework | Structural problems, arc issues | Fundamental changes | No |
| anti-detect | High AI-tell scores, deterministic failures | AI pattern removal | Yes |

## Mode 1: Polish

### Scope
- Minor style improvements
- Word choice refinement
- Sentence flow optimization
- Punctuation and grammar fixes
- Lexical fatigue reduction (dimension 10)

### Limitations
- **No structural changes**: Paragraph order, scene structure unchanged
- **No content addition**: Cannot add new events, dialogue, or descriptions
- **No content removal**: Cannot delete scenes or major elements
- **Preserve word count**: ±5% of original

### When to Use
- Audit passed with only info-level issues
- Style drift (dimension 8) flagged
- Lexical fatigue (dimension 10) detected
- User requests "light polish"

### Process
1. Read chapter and audit report
2. Identify style issues (word repetition, awkward phrasing, weak verbs)
3. Apply targeted fixes without changing meaning
4. Verify word count within ±5%
5. Re-run audit (dimensions 8, 10, 24)

### Example Fixes
- "He walked quickly" → "He strode"
- "很大的房间" → "宽敞的房间" (avoid 很 overuse)
- "However, ... However, ..." → "However, ... Yet, ..."

## Mode 2: Spot-Fix

### Scope
- Targeted issue resolution
- Fix specific audit failures (1-3 dimensions)
- Minimal surrounding changes
- Preserve overall structure and flow

### Limitations
- **Fix only flagged issues**: Don't rewrite unflagged sections
- **Minimal context changes**: Only modify what's necessary to fix issue
- **Preserve word count**: ±10% of original
- **No scope creep**: Don't fix issues not in audit report

### When to Use
- 1-3 critical or warning issues flagged
- Specific dimension failures (OOC, timeline, lore conflict)
- User requests "fix this specific issue"
- Auto-revision after audit (if criticalIssues ≤ 3)

### Process
1. Read audit report, identify flagged issues
2. For each issue:
   - Locate problematic section (paragraph/line reference)
   - Understand root cause
   - Apply minimal fix (rewrite sentence/paragraph)
   - Verify fix resolves issue without creating new problems
3. Re-run audit on fixed dimensions only
4. If new issues appear, revert and try different fix

### Example Fixes
- **OOC (dimension 1)**: Character acts rashly → Add internal monologue showing motivation
- **Timeline (dimension 2)**: Event order wrong → Reorder paragraphs, adjust time references
- **Lore conflict (dimension 3)**: Magic violates rules → Change magic effect to comply with world_state.json

## Mode 3: Rewrite

### Scope
- Major rework of problematic sections
- Rewrite entire scenes or sequences
- Add/remove content as needed
- Restructure paragraphs and dialogue
- Fix multiple critical issues simultaneously

### Limitations
- **Preserve core events**: Chapter goal and major plot points unchanged
- **Preserve character arcs**: Don't change character development trajectory
- **Preserve hooks**: Keep hook advancements/resolutions from original
- **Word count flexibility**: ±20% acceptable

### When to Use
- 4+ critical issues flagged
- Multiple dimensions failed (OOC + timeline + pacing)
- Chapter quality is poor overall
- User requests "major rewrite"
- Auto-revision after audit (if criticalIssues > 3)

### Process
1. Read chapter, audit report, and chapter intent
2. Identify core elements to preserve:
   - Chapter goal (from intent)
   - Major events (from chapter_summaries.json)
   - Hook operations (from delta)
3. Rewrite problematic sections from scratch:
   - Maintain core events
   - Fix all flagged issues
   - Improve overall quality
4. Integrate rewrites with preserved sections
5. Re-run full audit
6. If still failing, enter self-correction loop (max 2 rounds)

### Example Fixes
- **Multiple OOC + pacing issues**: Rewrite entire dialogue scene with proper character voices and better pacing
- **Timeline + lore conflicts**: Restructure event sequence and adjust magic usage to comply with rules
- **Poor quality overall**: Rewrite chapter maintaining plot points but improving prose quality

## Mode 4: Rework

### Scope
- Fundamental structural changes
- Reorder scenes or events
- Change narrative approach (e.g., dialogue-driven → action-driven)
- Add/remove entire scenes
- Adjust character arcs within chapter

### Limitations
- **Preserve chapter goal**: Must achieve intent goal
- **Preserve truth file deltas**: Final state changes must match original delta
- **Preserve hook operations**: Must advance/resolve same hooks
- **No word count limit**: Can expand or compress significantly

### When to Use
- Structural problems (dimension 18-26 failures)
- Arc flatline (dimension 27)
- Pacing monotony (dimension 28)
- Chapter doesn't achieve intent goal
- User requests "structural rework"

### Process
1. Read chapter, intent, audit report, and truth file deltas
2. Identify structural problems:
   - Scene order issues
   - Pacing problems (too fast/slow)
   - Narrative mode issues (show vs tell)
3. Plan new structure:
   - Reorder scenes for better flow
   - Adjust pacing (expand/compress sections)
   - Change narrative approach if needed
4. Rewrite chapter with new structure
5. Verify truth file deltas still apply
6. Re-run full audit

### Example Fixes
- **Pacing issues**: Expand rushed climax scene, compress slow setup
- **Arc flatline**: Add character introspection scene showing emotional progression
- **Structural problems**: Reorder scenes (flashback → chronological), change POV approach

## Mode 5: Anti-Detect

### Scope
- Aggressive AI pattern removal
- Fix all deterministic AI-tell failures (dimensions 20-23)
- Apply anti-AI rules from anti-ai skill
- Reduce heuristic AI likelihood scores
- Improve narrative naturalism

### Limitations
- **Preserve meaning**: Don't change plot, events, or character actions
- **Preserve structure**: Keep scene order and paragraph organization
- **Focus on surface patterns**: Fix AI tells without deep rewrites
- **Word count**: ±15% acceptable

### When to Use
- Deterministic AI-tell failures (dimensions 20-23)
- High heuristic AI likelihood (>70%)
- User requests "reduce AI traces"
- Before final export or publication

### Process
1. Run deterministic AI-tell scripts (dim20-23) and heuristic checks
2. Read anti-ai skill for specific rules
3. Apply fixes systematically:
   - **Dim20 (paragraph uniformity)**: Vary paragraph lengths (merge short, split long)
   - **Dim21 (hedge density)**: Remove hedge words (似乎/seems), replace with concrete statements
   - **Dim22 (formulaic transitions)**: Vary transition words, remove unnecessary transitions
   - **Dim23 (list-like structure)**: Vary sentence openings, break repetitive patterns
   - **Heuristics**: Apply anti-AI rules (no analysis language, vary sentence structure, concrete over abstract)
4. Re-run deterministic checks and heuristics
5. Verify all AI-tell scores improved

### Example Fixes
- **Hedge words**: "他似乎很生气" → "他握紧拳头，眼中闪过怒火" (show, don't hedge)
- **Formulaic transitions**: "However, ... However, ..." → "Yet ... Still, ..."
- **List-like structure**: "他走进房间。他看到桌子。他拿起书。" → Vary openings: "他走进房间。桌上放着一本书。他拿起来翻阅。"
- **Analysis language**: "这让他感到困惑" → "他皱起眉头，不明白这是怎么回事"

## Self-Correction Loop (REQ-F-27)

All revision modes follow this loop:

```
Round 1: Initial revision
  ↓
  Run audit
  ↓
  Critical issues remaining? → Yes → Round 2
  ↓ No
  Done

Round 2: Final attempt
  ↓
  Run audit
  ↓
  Critical issues remaining? → Yes → STOP, report failure
  ↓ No
  Done
```

### Loop Rules
- **Max 2 rounds**: Stop after round 2 regardless of result (configurable via book.json qualityGates.maxAuditRetries)
- **Only critical issues**: Loop continues only if criticalIssues > 0
- **Warning/info issues**: Don't trigger additional rounds
- **Failure reporting**: If round 2 still has critical issues, log failure and report to user

### Between Rounds
1. Re-run truth file persistence to update truth files (if content changed)
2. Re-run auditor agent with full dimension set
3. Compare audit results: which issues fixed, which remain, any new issues
4. Adjust revision strategy for next round

## Revision History Tracking (REQ-F-28)

After each revision, log to `books/<id>/story/runtime/chapter-XXXX.revision-log.json`:

```json
{
  "chapterNumber": number,
  "revisions": [
    {
      "round": 1,
      "mode": "polish|spot-fix|rewrite|rework|anti-detect",
      "timestamp": "ISO-8601",
      "beforeWordCount": number,
      "afterWordCount": number,
      "issuesAddressed": [
        { "dimension": number, "description": "string" }
      ],
      "remainingIssues": [
        { "dimension": number, "severity": "critical|warning|info" }
      ],
      "auditVerdict": "pass|fail"
    }
  ]
}
```

## Mode Comparison

| Aspect | Polish | Spot-Fix | Rewrite | Rework | Anti-Detect |
|--------|--------|----------|---------|--------|-------------|
| Word count change | ±5% | ±10% | ±20% | No limit | ±15% |
| Structure preserved | Yes | Yes | Mostly | No | Yes |
| Content addition | No | Minimal | Yes | Yes | No |
| Content removal | No | Minimal | Yes | Yes | No |
| Scene reordering | No | No | No | Yes | No |
| Typical duration | Fast | Fast | Medium | Slow | Medium |
| Auto-triggered | No | Yes (≤3 issues) | Yes (>3 issues) | No | No |

## Quick Reference

**Auto-revision trigger**: criticalIssues > 0 after audit  
**Mode selection**: ≤3 issues → spot-fix, >3 issues → rewrite  
**Max rounds**: 2 (configurable via book.json qualityGates.maxAuditRetries)  
**Stop condition**: criticalIssues = 0 OR round = 2  
**Always log**: Revision history to revision-log.json  
**Always re-audit**: After each revision round
