---
name: character-building
description: Character construction rules - consistency, dimensionality, supporting character depth, psychology analysis, voice distinction, relationship dynamics
version: 1.0.0
---

# Character Building - Character Construction

## Overview
This skill contains character construction rules extracted from InkOS writer prompts. Covers character consistency, dimensionality, supporting character design, six-step psychology analysis, voice distinction, and relationship dynamics.

## Core Character Rules

### 1. Character Consistency (人设一致性)
Behavior driven by "past experience + current interests + core personality." Never break character without cause.

**Formula:**
```
Character Action = Past Experience + Current Interests + Core Personality
```

**Consistency check (三连反问自检):**
1. Why would they do this?
2. Does this serve their interests?
3. Does this match their established personality?

**Example:**
- ✗ Cautious character suddenly takes reckless risk without setup
- ✓ Cautious character takes calculated risk when stakes justify it

### 2. Dimensionality (人物立体化)
Core trait + contrasting detail = real person. Perfect characters are failed characters.

**Formula:**
```
Dimensional Character = Core Label + Contrasting Detail
```

**Examples:**
- Cold, ruthless leader + secretly cares for stray animals
- Rough, crude warrior + has refined taste in poetry
- Villain boss + completely obedient to elderly mother

**Anti-pattern:**
- ✗ Character with only positive traits (Mary Sue/Gary Stu)
- ✗ Character with only negative traits (flat villain)

### 3. No Puppets (拒绝工具人)
Side characters must have independent motivation and agency. MC's strength comes from outmaneuvering smart people, not steamrolling idiots.

**Supporting character B-side principle (配角B面原则):**
- Every supporting character has their own agenda
- Allies help MC because of shared enemy or debt, not unconditional loyalty
- Antagonists oppose MC because of their own goals, not "villain face"

**Design method:**
1. **Motivation tied to main plot:** Every supporting character's motivation must connect to main storyline
2. **Core label + contrasting detail:** Make them "alive"
3. **Establish through events:** Show personality through reactions, choices, tone—not appearance descriptions
4. **Voice distinction:** Different speaking styles (vocabulary, sentence length, verbal tics, dialect traces)
5. **Reject collective reactions:** In group scenes, don't write "everyone gasped"—pick 1-2 characters for specific reactions

### 4. Voice Distinction (角色区分度)
Different characters must speak differently—vocabulary, sentence length, slang, verbal tics.

**Voice elements:**
- **Vocabulary level:** Educated vs street, formal vs casual
- **Sentence length:** Short and clipped vs long and flowing
- **Verbal tics:** Catchphrases, repeated words, speech patterns
- **Dialect/accent markers:** Regional speech patterns (use sparingly)
- **Emotional expression:** How they show anger, joy, fear

**Example:**
- Scholar: "The situation presents certain complications."
- Street fighter: "We're screwed."
- Noble: "This development is... unfortunate."

### 5. Relationship Logic (情感/动机逻辑链)
Any relationship change must be set up by events and motivated by interests.

**Relationship progression:**
- ✗ First meeting → immediate loyalty
- ✓ First meeting → shared crisis → mutual respect → trust → loyalty

**Event-driven relationship changes:**
- Alliance: Shared enemy or mutual benefit
- Betrayal: Interest conflict or broken trust
- Subordination: Debt, defeat, or recognition of strength

**Forbidden:**
- Sudden brotherhood without buildup
- Instant deep affection without events
- Title changes (称呼变化) without event support

## Six-Step Character Psychology Method (六步走人物心理分析)

Before writing any character's action or dialogue in a key scene, run this mental checklist (NOT in prose):

### Step 1: Current Situation (当前处境)
What situation does this character face RIGHT NOW? What cards do they hold?

### Step 2: Core Motivation (核心动机)
What do they want most? What do they fear most?

### Step 3: Information Boundary (信息边界)
What does this character know? What don't they know? What misjudgments do they have about the situation?

### Step 4: Personality Filter (性格过滤)
Given the same situation, how does THIS character's personality shape their response? (Impulsive/cautious/cunning/decisive)

### Step 5: Behavioral Choice (行为选择)
Based on steps 1-4, what choice will this character make?

### Step 6: Emotional Externalization (情绪外化)
What emotion accompanies this choice? How is it expressed through body language, expression, tone?

**CRITICAL:** This method is for YOUR planning. These terms (当前处境, 核心动机, 信息边界, 性格过滤) never appear in chapter text.

**Anti-pattern:**
- ✗ "His core motivation was survival." (analytical language in prose)
- ✓ "He needed to get out. That was it. Everything else was noise." (character voice)

## Character Arc Design (人物弧线)

### Arc Structure
1. **Establish baseline:** Character's starting state, beliefs, capabilities
2. **Pressure points:** Events that challenge their worldview
3. **Crisis moment:** Forced to choose between old self and growth
4. **Transformation:** Character changes (or refuses to change)
5. **New equilibrium:** Character operates from new baseline

### Arc Types
- **Growth arc:** Character overcomes flaw, becomes better
- **Fall arc:** Character succumbs to flaw, becomes worse
- **Flat arc:** Character's beliefs are tested but remain true (they change the world, not themselves)

### Tracking
Use emotional_arcs truth file to track:
- Chapter number
- Emotional state
- Triggering event
- Intensity (1-10)
- Arc direction (rising/falling/stable)

## Relationship Dynamics (关系动态)

### Relationship Development Framework
Relationships (friendship, romance, subordination) must progress through event-driven nodes:

**3-5 Key Events:**
1. Shared enemy/crisis
2. Secret sharing/vulnerability
3. Interest conflict/test
4. Trust test/sacrifice
5. Commitment/resolution

**Progression levels:**
- Strangers → Acquaintances → Allies → Friends → Close friends/lovers
- Each level requires event trigger
- Forbidden: Skip levels without buildup

### Emotional Scenes
Convey emotion through scene, not labels:
- **Environment:** Rain, isolation, confined space
- **Micro-actions:** Clenched fists, white knuckles, avoiding eye contact
- **Dialogue subtext:** What's NOT said

**Anti-pattern:**
- ✗ "She felt overwhelmed with sadness."
- ✓ "She held the phone with both hands, knuckles white."

## Character Matrix Management

### Character File Structure
Track in character_matrix truth file:

**Character Profile:**
- Name
- Core label (核心标签)
- Contrasting detail (反差细节)
- Speaking style (说话风格)
- Personality base (性格底色)
- Relationship to MC
- Core motivation
- Current goal

**Encounter Record:**
- Character A + Character B
- First meeting chapter
- Most recent interaction chapter
- Relationship nature
- Relationship changes

**Information Boundary:**
- Character name
- Known information
- Unknown information
- Information source chapter

## Full Cast Tracking (Optional)

When enabled, track at chapter end:
- Characters who appeared (name + one-line status change)
- Relationship changes (if any)
- Characters mentioned but not present (name + reason for mention)

## Quick Reference Checklist

Before writing any character action:
1. **Consistency:** Does this match their established personality?
2. **Motivation:** Why would they do this? What's their interest?
3. **Information:** What do they know vs not know?
4. **Voice:** Does their dialogue sound like THEM?
5. **Reaction:** How do others respond to their action?
6. **Change:** Has this event changed their relationship with others?

## Anti-Patterns to Avoid

1. **OOC (Out of Character):** Behavior without setup or motivation
2. **Puppet characters:** Supporting characters with no independent agency
3. **Perfect characters:** No flaws or contrasting details
4. **Flat villains:** Antagonists who oppose MC "because villain"
5. **Instant loyalty:** Deep relationships without event buildup
6. **Collective reactions:** "Everyone was shocked" instead of specific character reactions
7. **Voice uniformity:** All characters sound the same
8. **Information boundary violation:** Character acts on info they couldn't know
9. **Unmotivated relationship changes:** Sudden alliance/betrayal without cause
10. **Analytical language:** "His core motivation was..." in narrative prose

## Language-Specific Notes

### Chinese (中文)
- 角色说话语气、发怒方式、处事模式必须有显著差异
- 群像反应不要一律"全场震惊"，改写成1-2个具体角色的身体反应
- 关系改变必须事件驱动：如果主角要救人必须给出利益理由

### English
- Different characters must speak differently—vocabulary, sentence length, slang, verbal tics
- Action beats replace adverbs: "He crossed his arms" vs "he said defiantly"
- Relationship changes must be set up by events and motivated by interests

## Integration with Other Skills

This skill works with:
- **writing-craft:** Character voice supports dialogue-driven narrative
- **anti-ai:** Six-step method is planning tool, terms never appear in prose
- **language-zh/en:** Language-specific character voice implementation
- **audit-dimensions:** Character consistency and OOC checks
