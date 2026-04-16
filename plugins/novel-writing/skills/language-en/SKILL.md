---
name: language-en
description: English language constraints - sentence variation, banned words, English anti-AI rules, show-don't-tell in English prose, dialogue conventions, POV consistency
version: 1.0.0
---

# Language-EN - English Language Constraints

## Overview
This skill contains English-specific writing rules extracted from InkOS writer prompts. Covers sentence variation, banned words, English anti-AI patterns, show-don't-tell techniques, dialogue conventions, and POV consistency rules.

## Core Language Rules

### 1. Language Foundation
- Write in English
- Vary sentence length
- Mix short punchy sentences with longer flowing ones
- Maintain consistent narrative voice throughout

### 2. Sentence Variation
Mix short punchy sentences with longer flowing ones. Avoid repetitive sentence structure.

**Anti-pattern:**
```
✗ He walked into the room. He saw a table. He picked up a cup. He drank from it.
```

**Correct:**
```
✓ He walked into the room. A cup sat on the table. He picked it up and drank. The water was cold.
```

**Techniques:**
- Short sentences (5-10 words) for impact
- Long sentences (15-30 words) for flow and detail
- Vary sentence openings (subject, verb, adverb, prepositional phrase)
- Mix simple, compound, and complex sentences

### 3. Vocabulary Control
Drive scenes with verbs and nouns, minimize adjectives. Max 1-2 precise adjectives per sentence.

**Adjective limits:**
- ✗ "She was a very beautiful, elegant, and graceful woman."
- ✓ "She moved without sound, white dress trailing."

**Verb-driven narrative:**
- ✗ "He said angrily"
- ✓ "He slammed the table"

**Noun precision:**
- ✗ "He grabbed a weapon"
- ✓ "He drew his short blade"

### 4. Paragraph Structure
Paragraph breaks more frequent than Chinese (2-4 sentences typical).

**Paragraph rhythm:**
- Dialogue: New paragraph per speaker
- Action: One action sequence per paragraph
- Description: One scene/object per paragraph
- Internal thought: One thought per paragraph

**Rhythm variation:**
- Tense scenes: Short paragraphs (1-2 sentences)
- Calm scenes: Medium paragraphs (3-4 sentences)
- Description/reflection: Can extend (4-6 sentences)

## English-Specific Anti-AI Patterns

### 1. AI-Tell Words (Rate-Limited)
Max 1 occurrence per 3,000 words.

**Banned high-frequency words:**
- delve
- tapestry
- testament
- intricate
- pivotal
- vibrant
- embark
- comprehensive
- nuanced
- landscape (metaphorical use)
- realm (metaphorical use)
- foster
- underscore

**Replacement strategy:**
- ✗ "He delved into the mystery"
- ✓ "He dug into the mystery" / "He investigated"

### 2. Analytical Language Ban
No analytical/report language in prose.

**Banned terms in narrative:**
- core motivation
- information asymmetry
- strategic advantage
- calculated risk
- optimal outcome
- key takeaway
- it's worth noting
- fundamentally
- essentially
- basically

**Replacement:**
- ✗ "His core motivation was survival."
- ✓ "He needed to get out. That was it. Everything else was noise."

### 3. "Not X; Y" Construction
Max once per chapter.

**Anti-pattern:**
```
✗ It wasn't fear. It was something deeper.
✗ Not anger—rage.
✗ He didn't walk. He ran.
```

**Replacement:**
- State the thing directly
- ✓ "Terror gripped him."
- ✓ "Rage burned through him."
- ✓ "He ran."

### 4. Lists of Three Ban
Max once per 2,000 words in descriptive prose.

**Anti-pattern:**
```
✗ ancient, terrible, and vast
✗ dark, cold, and empty
✗ strong, fast, and deadly
```

**Replacement:**
- Use pairs: "ancient and terrible"
- Use single precise word: "vast"
- Use different structure: "Ancient. Terrible. And vast beyond measure." (rare exception)

### 5. Filter Words
Remove filter words that distance reader from action.

**Common filter words:**
- saw / watched / observed
- heard / listened
- felt / sensed
- thought / wondered
- realized / understood
- seemed / appeared

**Replacement:**
- ✗ "He saw a shadow move across the wall."
- ✓ "A shadow slid across the wall."
- ✗ "She felt the cold wind."
- ✓ "The wind cut through her coat."

### 6. Weak Verbs
Replace weak verbs with strong action verbs.

**Weak verbs to minimize:**
- was / were / is / are (in action scenes)
- got / get
- went / go
- came / come

**Replacement:**
- ✗ "He was angry."
- ✓ "Anger burned through him." / "He slammed the door."
- ✗ "She went to the door."
- ✓ "She crossed to the door." / "She strode to the door."

## Show, Don't Tell in English Prose

### 1. Emotion Externalization
Replace emotion labels with physical reactions, actions, or sensory details.

**Examples:**

| Tell (✗) | Show (✓) |
|---|---|
| He felt a surge of anger. | He slammed the table. The water glass toppled. |
| She was overwhelmed with sadness. | She held the phone with both hands, knuckles white. |
| He was terrified. | His back went cold. His feet felt like ice. |
| She was excited. | She bounced on her toes, grinning. |

### 2. Character Traits
Show traits through behavior, not description.

**Examples:**

| Tell (✗) | Show (✓) |
|---|---|
| He was a cautious man. | He checked the lock three times before leaving. |
| She was arrogant. | She didn't look up when he entered. |
| He was clever. | He spotted the trap before anyone else moved. |

### 3. Setting and Atmosphere
Show mood through sensory details, not labels.

**Examples:**

| Tell (✗) | Show (✓) |
|---|---|
| The room was creepy. | Shadows pooled in the corners. Something dripped in the dark. |
| It was a beautiful day. | Sunlight warmed his face. Birds sang in the trees. |
| The place was abandoned. | Dust coated every surface. Cobwebs hung from the ceiling. |

## Dialogue Conventions

### 1. Basic Format
```
"Dialogue content," he said.
"Dialogue content." He crossed his arms.
"Dialogue content!" He slammed the door.
"Dialogue content?" He raised an eyebrow.
```

### 2. Action Beats
Prefer action beats over adverbs and fancy dialogue tags.

**Anti-pattern:**
```
✗ "I won't do it," she exclaimed defiantly.
✗ "Really?" he asked sarcastically.
✗ "Get out," she hissed angrily.
```

**Correct:**
```
✓ "I won't do it." She crossed her arms.
✓ "Really?" He raised an eyebrow.
✓ "Get out." She pointed at the door.
```

### 3. Dialogue Tags
**Simple tags (preferred):**
- said
- asked
- replied
- answered

**Avoid fancy tags:**
- exclaimed
- shouted (use sparingly)
- hissed
- growled
- purred
- breathed

**Avoid adverbs:**
- said angrily → He slammed the table. "No."
- asked nervously → She twisted her hands. "Can I...?"
- replied coldly → "No." He didn't look up.

### 4. Multi-Speaker Scenes
- New paragraph per speaker
- Limit to 3 speakers in same scene (for clarity)
- Use action beats to identify speakers (avoid repetitive "he said")

**Example:**
```
"We need to move." John checked his watch.

"Now?" Sarah glanced at the door. "It's not safe."

"It's never safe." He grabbed his coat. "That's the point."
```

### 5. Dialogue Proportion
- Character interaction scenes: 50-70% dialogue
- Solo/escape/exploration scenes: 0-30% dialogue
- Deliver conflict and information through dialogue first, narration second

## POV Consistency

### 1. POV Types
**Third Person Limited (most common in web fiction):**
- Stay in one character's head per scene
- Reader knows only what POV character knows
- Can switch POV between scenes/chapters

**Third Person Omniscient:**
- Narrator knows all characters' thoughts
- Can reveal information any character doesn't know
- Requires careful handling to avoid confusion

**First Person:**
- "I" narrator
- Deepest immersion
- Limited to narrator's knowledge

### 2. POV Discipline
**Rules:**
- Choose POV at scene start, maintain throughout scene
- Don't head-hop (switching POV mid-scene without clear break)
- POV character can't know what they didn't witness (information boundary)

**Anti-pattern:**
```
✗ John walked into the room. Mary thought he looked tired. (POV violation if in John's POV)
```

**Correct:**
```
✓ John walked into the room. Mary's eyes narrowed. "You look tired," she said. (Show Mary's observation through action/dialogue)
```

### 3. Information Boundary
Character can only act on information they have access to.

**Check:**
- Did character witness this event?
- Did someone tell them?
- Could they reasonably infer this?

**Anti-pattern:**
```
✗ He knew the villain was planning to attack tomorrow. (How does he know?)
```

**Correct:**
```
✓ He'd overheard the villain's conversation. Tomorrow. They were coming tomorrow.
```

## Web Fiction Conventions (English Platforms)

### 1. Chapter Structure
- Hook opening: Start with action or compelling question
- Rising tension: Build conflict through chapter
- Cliffhanger ending: Leave reader wanting more

### 2. Pacing
- Small payoff every 3-5 chapters
- Medium payoff every 10-15 chapters
- Major payoff every volume/arc

### 3. Genre-Specific Patterns

**LitRPG/Progression Fantasy:**
- System notifications in distinct formatting
- Stat blocks separate from prose
- Power progression clearly tracked

**Isekai:**
- World rules established early
- Culture clash moments
- Protagonist advantage clearly defined

**Romantasy:**
- Relationship development through events
- Emotional beats balanced with plot
- Chemistry shown through interaction

## Sentence Opening Patterns

### Avoid Repetitive Openings
**Anti-pattern:**
```
✗ He walked into the room.
  He saw a table.
  He picked up a cup.
  He drank from it.
```

**Correct:**
```
✓ He walked into the room.
  A cup sat on the table.
  He picked it up and drank.
  The water was cold.
```

### Opening Variety
- Subject: He/The table/The water
- Verb: Walking/Picking/Drinking
- Adverb: Slowly/Suddenly/Carefully
- Prepositional phrase: In the room/On the table/From the cup
- Participle: Walking into the room/Picking up the cup

## Rhetorical Patterns

### 1. Metaphor and Simile
Use concrete comparisons, avoid clichés.

**Effective:**
- ✓ "His eyes were like a wolf spotting meat."
- ✓ "The silence pressed down like a physical weight."

**Avoid clichés:**
- ✗ "as cold as ice"
- ✗ "as strong as an ox"
- ✗ "as light as a feather"

### 2. Parallelism
Use for emphasis and rhythm. Limit to 3 elements.

**Effective:**
- ✓ "He didn't trust fate. He didn't trust luck. He trusted the blade in his hand."

### 3. Rhetorical Questions
Use in internal monologue. Don't overuse.

**Effective:**
- ✓ "What choice did he have? None. He'd go forward or die trying."

### 4. Short Sentence Rhythm
Use for tension and impact.

**Effective:**
```
✓ He ran. The wind howled. Shadows lengthened. Night was coming.
```

## Genre-Specific Fatigue Words

### LitRPG
Max 1 per chapter:
- delve
- dungeon crawl
- loot
- grind

### Progression Fantasy
Max 1 per chapter:
- cultivation
- breakthrough
- ascend
- transcend

### Isekai
Max 1 per chapter:
- summoned
- transported
- another world
- reincarnated

## Quick Reference Checklist

Before finalizing English chapter:
1. **Sentence variety:** Repetitive structure? Same openings?
2. **AI-tell words:** Delve/tapestry/testament/etc. > 1 per 3k words?
3. **Analytical language:** Core motivation/strategic advantage in prose?
4. **"Not X; Y":** More than once per chapter?
5. **Lists of three:** More than once per 2k words?
6. **Filter words:** Saw/felt/heard instead of direct description?
7. **Weak verbs:** Was/were/got in action scenes?
8. **Dialogue tags:** Fancy tags or adverbs instead of action beats?
9. **POV consistency:** Head-hopping? Information boundary violations?
10. **Paragraph length:** Walls of text without breaks?

## Integration with Other Skills

This skill works with:
- **writing-craft:** English implementation of narrative techniques
- **character-building:** English character voice and dialogue
- **anti-ai:** English-specific anti-AI patterns
- **audit-dimensions:** Language-specific audit checks
