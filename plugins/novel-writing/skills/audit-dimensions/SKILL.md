---
name: audit-dimensions
description: 29 core + 4 spinoff conditional + 4 fanfic conditional audit dimensions with severity classification
version: 1.0.0
---

# Audit Dimensions

## Overview

InkOS audits chapters across 37 dimensions (29 core + 4 spinoff conditional + 4 fanfic conditional). Each dimension has a severity classification (critical/warning/info) and detection method (deterministic script or LLM judgment).

## Severity Levels

- **Critical**: Must fix before chapter approval (blocks progression)
- **Warning**: Should fix but not blocking (quality issue)
- **Info**: Informational only (style suggestion)

## Core Dimensions (1-9)

### Dimension 1: Out of Character (OOC)
**Severity**: Critical  
**Detection**: LLM judgment  
**Description**: Character acts inconsistently with established personality, motivations, or arc.  
**Check**: Compare character actions/dialogue against character_matrix.json entries. Flag if behavior contradicts established traits without justification.  
**Example**: A cautious character suddenly taking reckless action without character development explaining the change.

### Dimension 2: Timeline Inconsistency
**Severity**: Critical  
**Detection**: LLM judgment + fact checking  
**Description**: Events occur in impossible temporal order or contradict established timeline.  
**Check**: Cross-reference chapter events with chapter_summaries.json timeline. Flag if event order is impossible or time references conflict.  
**Example**: Character arrives at location before departing from previous location.

### Dimension 3: Lore Conflict
**Severity**: Critical  
**Detection**: LLM judgment  
**Description**: Chapter contradicts established world rules, magic systems, or technology constraints.  
**Check**: Compare chapter content against world_state.json rules and technology entries. Flag contradictions.  
**Example**: Magic system suddenly allows previously impossible feats without explanation.

### Dimension 4: Power Scaling Violation
**Severity**: Critical  
**Detection**: LLM judgment  
**Description**: Character power levels fluctuate inconsistently or violate progression rules.  
**Check**: Compare character abilities against resource_ledger.json and character_matrix.json abilities. Flag unexplained power jumps or regressions.  
**Example**: Character defeats enemy they previously couldn't harm, without training or power-up.

### Dimension 5: Numerical Inconsistency
**Severity**: Warning  
**Detection**: LLM judgment  
**Description**: Numbers (distances, quantities, time) contradict previous statements.  
**Check**: Extract numerical facts from chapter, compare against chapter_summaries.json and world_state.json. Flag conflicts.  
**Example**: City described as "50 miles away" in chapter 10, "200 miles away" in chapter 15.

### Dimension 6: Hook Health
**Severity**: Warning  
**Detection**: Script + LLM judgment  
**Description**: Hooks are stale (not advanced in 10+ chapters), overdue for payoff, or introduced without advancement.  
**Check**: Read pending_hooks.json, calculate chapters since lastAdvancedChapter. Flag hooks with pressure="critical" or stale debt.  
**Script**: Check hook status and chapter deltas.

### Dimension 7: Pacing Issues
**Severity**: Warning  
**Detection**: LLM judgment  
**Description**: Chapter pacing is too fast (rushed events) or too slow (stagnant).  
**Check**: Evaluate event density, scene transitions, and information release rate. Flag if pacing feels unnatural for genre.  
**Example**: Major plot resolution in 2 paragraphs, or 3000 words of internal monologue with no action.

### Dimension 8: Style Drift
**Severity**: Info  
**Detection**: LLM judgment  
**Description**: Writing style deviates from established voice or genre conventions.  
**Check**: Compare chapter style against style_guide.md and genre profile. Flag significant deviations.  
**Example**: Suddenly formal language in a casual-voice story, or modern slang in historical fiction.

### Dimension 9: Information Boundary Violation
**Severity**: Critical  
**Detection**: LLM judgment  
**Description**: Character knows information they shouldn't have access to (POV leak, future knowledge).  
**Check**: Verify character knowledge against their information boundary in character_matrix.json. Flag if character references events they didn't witness or knowledge they couldn't have.  
**Example**: Character A knows Character B's secret thoughts without being told.

## Quality Dimensions (10-17)

### Dimension 10: Lexical Fatigue
**Severity**: Warning  
**Detection**: Script + LLM judgment  
**Description**: Overuse of specific words or phrases (genre fatigue words).  
**Check**: Count occurrences of genre-specific fatigue words from genre profile. Flag if frequency exceeds threshold (typically >3 per 1000 chars).  
**Script**: Word frequency analysis against genre fatigueWords list.

### Dimension 11: Incentive Chain Break
**Severity**: Warning  
**Detection**: LLM judgment  
**Description**: Character actions lack clear motivation or logical connection to goals.  
**Check**: Trace character decisions back to established motivations in character_matrix.json. Flag if action-motivation link is weak or missing.  
**Example**: Character pursues goal without clear reason, or abandons goal without explanation.

### Dimension 12: Era Accuracy
**Severity**: Warning  
**Detection**: LLM judgment  
**Description**: Anachronistic elements (technology, language, social norms) for the story's time period.  
**Check**: Compare chapter elements against world_state.json era constraints. Flag anachronisms.  
**Example**: Medieval setting with modern idioms, or futuristic tech in historical fiction.

### Dimension 13: Side Character Competence
**Severity**: Info  
**Detection**: LLM judgment  
**Description**: Supporting characters are unrealistically incompetent to make protagonist look good.  
**Check**: Evaluate side character actions for realism. Flag if side characters consistently fail at tasks they should be capable of.  
**Example**: Experienced warrior makes rookie mistakes to let protagonist win.

### Dimension 14: Side Character Instrumentalization
**Severity**: Warning  
**Detection**: LLM judgment  
**Description**: Supporting characters exist only to serve plot, lack agency or depth (tool characters).  
**Check**: Evaluate side character actions and dialogue for agency. Flag if character only appears to deliver information or advance plot without own goals.  
**Example**: Character appears only to give protagonist a key, then disappears.

### Dimension 15: Payoff Dilution
**Severity**: Warning  
**Detection**: LLM judgment  
**Description**: Major payoffs are rushed, underwhelming, or lack emotional impact.  
**Check**: Identify payoff moments (hook resolutions, arc completions). Evaluate if buildup justifies payoff weight. Flag if payoff feels rushed or anticlimactic.  
**Example**: Long-awaited confrontation resolved in one paragraph.

### Dimension 16: Dialogue Authenticity
**Severity**: Warning  
**Detection**: LLM judgment  
**Description**: Dialogue sounds unnatural, all characters speak the same way, or exposition-heavy.  
**Check**: Evaluate dialogue for character voice differentiation and naturalism. Flag if dialogue is info-dump or lacks character-specific patterns.  
**Example**: All characters use same vocabulary and sentence structure.

### Dimension 17: Chronicle Drift
**Severity**: Info  
**Detection**: LLM judgment  
**Description**: Narrative voice shifts between showing and telling, or becomes overly summarizing.  
**Check**: Evaluate narrative mode consistency. Flag if chapter shifts from scene-based to summary-based narration without justification.  
**Example**: Detailed scene suddenly becomes "Three days passed and they trained."

## Structural Dimensions (18-26)

### Dimension 18: Knowledge Pollution
**Severity**: Warning  
**Detection**: LLM judgment  
**Description**: Narrator reveals information characters don't know (omniscient leak in limited POV).  
**Check**: Verify all revealed information is accessible to POV character. Flag if narrator provides knowledge beyond character's scope.  
**Example**: Third-person limited POV reveals villain's thoughts.

### Dimension 19: POV Consistency
**Severity**: Critical  
**Detection**: LLM judgment  
**Description**: Point of view shifts mid-scene without clear transition.  
**Check**: Track POV throughout chapter. Flag if perspective jumps between characters without scene break.  
**Example**: Paragraph 1 in Character A's head, paragraph 2 in Character B's head, same scene.

### Dimension 20: Paragraph Uniformity (AI-tell, principle deviation)
**Severity**: Warning  
**Detection**: Deterministic script  
**Description**: Paragraphs are unnaturally uniform in length (coefficient of variation < 0.15). Indicates deviation from P3/P7 principles (mechanical repetition patterns).  
**Check**: Calculate paragraph length CV. Flag if CV < 0.15 across ≥3 paragraphs.  
**Script**: `dim20-paragraph-uniformity.py`  
**Threshold**: CV < 0.15

### Dimension 21: Hedge Density (AI-tell, principle deviation)
**Severity**: Warning  
**Detection**: Deterministic script  
**Description**: Overuse of hedge words (似乎/可能/seems/perhaps). Indicates deviation from P1 principle (narrator hedging instead of committing).  
**Check**: Count hedge words per 1000 characters. Flag if >3 occurrences.  
**Script**: `dim21-hedge-density.py`  
**Threshold**: >3 per 1000 chars  
**Words (zh)**: 似乎, 可能, 或许, 大概, 某种程度上  
**Words (en)**: seems, perhaps, maybe, apparently, in some ways

### Dimension 22: Formulaic Transitions (AI-tell, principle deviation)
**Severity**: Warning  
**Detection**: Deterministic script  
**Description**: Same transition word repeated ≥3 times. Indicates deviation from P3 principle (mechanical word repetition).  
**Check**: Count transition word occurrences. Flag if any single word appears ≥3 times.  
**Script**: `dim22-formulaic-transitions.py`  
**Threshold**: ≥3 occurrences  
**Words (zh)**: 然而, 不过, 与此同时  
**Words (en)**: however, meanwhile, nevertheless

### Dimension 23: List-like Structure (AI-tell, principle deviation)
**Severity**: Warning  
**Detection**: Deterministic script  
**Description**: ≥3 consecutive sentences with same opening pattern. Indicates deviation from P7 principle (mechanical list/tricolon patterns).  
**Check**: Extract sentence openings (first 2-4 chars/words). Flag if ≥3 consecutive sentences match.  
**Script**: `dim23-list-like-structure.py`  
**Threshold**: ≥3 consecutive matches

### Dimension 24: Subplot Stagnation
**Severity**: Warning  
**Detection**: Script + LLM judgment  
**Description**: Active subplots not advanced in 15+ chapters.  
**Check**: Read subplot_board.json, calculate chapters since lastUpdatedChapter. Flag subplots with status="active" and no recent updates.  
**Script**: Check subplot status and chapter deltas.

### Dimension 25: Arc Flatline
**Severity**: Warning  
**Detection**: LLM judgment  
**Description**: Character emotional arcs show no progression or change.  
**Check**: Read emotional_arcs.json, evaluate if character emotions/intensity change over recent chapters. Flag if arc is static.  
**Example**: Character stuck in same emotional state for 20+ chapters.

### Dimension 26: Pacing Monotony
**Severity**: Info  
**Detection**: LLM judgment  
**Description**: Chapter pacing is repetitive (same rhythm every chapter).  
**Check**: Evaluate pacing variation across recent chapters. Flag if all chapters follow identical structure (e.g., always action → dialogue → introspection).  
**Example**: Every chapter ends with cliffhanger, every chapter starts with action.

## Governance Dimensions (27-33)

### Dimension 27: Sensitive Content
**Severity**: Critical  
**Detection**: LLM judgment + deterministic script  
**Description**: Content violates platform guidelines or genre expectations (excessive violence, explicit content, prohibited words).  
**Check**: Two-layer detection:
1. **Deterministic** (`sensitive-words.py`): Exact-match prohibited words. "block" severity → auto-fail at merge level (bypasses LLM). "warn" severity → warning issue.
2. **LLM judgment**: Evaluate content-level sensitivity against genre profile guidelines (e.g., graphic violence in cozy fantasy, explicit content in YA). Catches context-dependent violations that word lists miss.  
**Note**: A single "block"-severity prohibited word forces `overallVerdict=fail` regardless of LLM result. This is enforced by `build-audit-report.py` at the three-source merge step, not by the auditor agent.  
**Example**: Graphic violence in cozy fantasy, explicit content in YA, politically sensitive terms in any genre.

### Dimension 28: Canon Event Conflict (Conditional: Spinoff)
**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `parentBookId` is set  
**Description**: Spinoff contradicts parent book's established events.  
**Check**: Compare chapter events against parent book's chapter_summaries.json. Flag contradictions.  
**Example**: Spinoff shows character alive when parent book established their death.

### Dimension 29: Future Information Leak (Conditional: Spinoff)
**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `parentBookId` is set  
**Description**: Spinoff characters reference events from parent book's future timeline.  
**Check**: Verify spinoff timeline position relative to parent. Flag if characters know future events.  
**Example**: Prequel character mentions event that happens in main story.

### Dimension 30: Cross-book World Rules (Conditional: Spinoff)
**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `parentBookId` is set  
**Description**: Spinoff violates parent book's world rules or magic system.  
**Check**: Compare spinoff world_state.json against parent's world rules. Flag contradictions.  
**Example**: Spinoff allows magic that parent book established as impossible.

### Dimension 31: Spinoff Hook Isolation (Conditional: Spinoff)
**Severity**: Warning  
**Detection**: LLM judgment  
**Activation**: Only when `parentBookId` is set  
**Description**: Spinoff introduces hooks that require parent book knowledge to resolve.  
**Check**: Evaluate if spinoff hooks are self-contained. Flag if resolution depends on parent book events.  
**Example**: Spinoff hook about "the prophecy" that only makes sense if you read parent book.

### Dimension 32: Reader Expectation Management
**Severity**: Info  
**Detection**: LLM judgment  
**Activation**: Always active  
**Description**: Chapter violates genre expectations without justification.  
**Check**: Compare chapter content against genre profile conventions. Flag if major deviation without setup.  
**Example**: Romance novel suddenly becomes horror without foreshadowing.

### Dimension 33: Outline Drift Detection
**Severity**: Info  
**Detection**: LLM judgment  
**Activation**: Always active  
**Description**: Chapter deviates significantly from volume_outline.md without justification.  
**Check**: Compare chapter events against outline beats. Flag if major deviation occurs.  
**Example**: Outline says "character reconciles with father" but chapter shows escalating conflict.

## Fanfic Dimensions (34-37, Conditional)

### Dimension 34: Character Fidelity (Fanfic)
**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `fanficMode` is set  
**Description**: Characters act inconsistently with source material characterization.  
**Check**: Compare character actions/dialogue against fanfic_canon.md character profiles. Flag OOC behavior (unless mode="ooc").  
**Exception**: Dimension skipped if `fanficMode="ooc"`.

### Dimension 35: World Rule Compliance (Fanfic)
**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `fanficMode` is set  
**Description**: Story violates source material's world rules or magic system.  
**Check**: Compare chapter world rules against fanfic_canon.md world rules. Flag contradictions (unless mode="au").  
**Exception**: Dimension relaxed if `fanficMode="au"`.

### Dimension 36: Relationship Dynamics (Fanfic)
**Severity**: Warning  
**Detection**: LLM judgment  
**Activation**: Only when `fanficMode` is set  
**Description**: Character relationships deviate from source material without justification.  
**Check**: Compare relationship developments against fanfic_canon.md relationships. Flag if dynamics shift without buildup.  
**Exception**: Dimension relaxed if `fanficMode="cp"` (ship-focused).

### Dimension 37: Canon Event Consistency (Fanfic)
**Severity**: Critical  
**Detection**: LLM judgment  
**Activation**: Only when `fanficMode` is set  
**Description**: Story contradicts source material's established events.  
**Check**: Compare chapter events against fanfic_canon.md timeline. Flag contradictions (unless mode="au").  
**Exception**: Dimension skipped if `fanficMode="au"`.

## Audit Report Format

The auditor returns an `AuditResult`:

```typescript
AuditResult = {
  passed: boolean,
  issues: AuditIssue[],
  summary: string,
  tokenUsage?: { promptTokens: number, completionTokens: number, totalTokens: number }
}

AuditIssue = {
  severity: "critical" | "warning" | "info",
  category: string,
  description: string,
  suggestion: string
}
```

- `passed`: `true` if no critical issues found
- `issues`: All detected issues across evaluated dimensions
- `summary`: Brief overall assessment of the chapter
- `category`: Dimension name or detection area (e.g., "OOC", "Timeline", "Hook Health")

## Quick Reference

**LLM dimensions**: 1-19, 24-33 (evaluated by auditor agent)  
**Deterministic dimensions**: 20-23 (AI-tell scripts), 27 (sensitive-words "block" level)  
**Three-source merge**: LLM + deterministic + sensitive-words → `build-audit-report.py` → `audit-report.json`  
**Conditional dimensions**: 28-31 (spinoff), 34-37 (fanfic)  
**Critical severity**: Must fix before approval  
**Block-severity sensitive word**: Forces audit failure regardless of LLM result  
**Auto-revision**: Triggered if any critical issues exist in merged audit report  
**Max revision rounds**: 2 (configurable via book.json qualityGates.maxAuditRetries)
