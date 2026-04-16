---
name: anti-ai
description: Anti-AI detection avoidance — 7 principles framework with contextual guidance, comparison tables, and reference files for genre adaptations and word lists
version: 2.0.0
---

# Anti-AI Detection Avoidance — Principles Framework

## Overview

Seven principles to avoid AI-generated content detection patterns. Each principle includes rationale, when to break, and implementation guidance with zh+en examples. Genre-specific adaptations and banned word lists are in reference files, loaded on demand.

## Reference Files

- For genre-specific application of all 7 principles → read `references/genre-adaptations.md`
- For banned/flagged word lists (zh+en, soft guidance) → read `references/banned-words.md`

## P1: Narrator Never Concludes for Reader

**Rationale**: AI models over-explain because they optimize for clarity. Human writers trust the reader. When the narrator states what action already implies, the prose reads like a summary rather than a story.

**When to Break**: Omniscient narrator voice in literary fiction may editorialize deliberately. First-person narrators with a strong analytical personality may state conclusions as characterization.

**Implementation**:
- If the reader can infer intent from action, the narrator must not state it
- Delete narrator commentary that summarizes what just happened

| AI Pattern (反例) | Human Version (正例) | Why (要点) |
|---|---|---|
| He realized this was the most important battle of his life. | Just write the battle — let the stakes speak. | Action externalizes importance |
| 他想看陆焚能不能活 | 只写踢水囊的动作，让读者自己判断 | 用动作传递意图 |
| At this moment, he finally understood what true power was. | (Delete — let reader feel it from context) | Don't conclude for reader |
| 这一刻，他终于明白了什么是真正的力量。 | （删掉——让读者自己从前文感受） | 不替读者下结论 |
| Obviously, the opponent underestimated his strength. | (Only write opponent's expression change, let reader judge) | "Obviously" is author preaching |
| 显然，对方低估了他的实力。 | （只写对方的表情变化，让读者自己判断） | "显然"是作者在说教 |
| He knew this would be the battle that changed his fate. | He drew the blade an inch, then pushed it back. | Hesitant action implies importance |
| 他知道，这将是改变命运的一战。 | 他把刀从鞘里拔了一寸，又推回去。 | 用犹豫的动作暗示重要性 |

## P2: No Analytical/Report Language in Prose

**Rationale**: AI models default to analytical framing because they are trained on essays and reports. Narrative prose should feel like a person thinking, not a case study.

**When to Break**: A character who is explicitly an analyst, strategist, or scientist may think in analytical terms — but only in internal monologue, clearly marked as their personality, and sparingly.

**Implementation**:
- Character internal monologue must be colloquial and intuitive, not analytical framework terms
- Planning-stage terms (see P5) never appear in chapter text

| AI Pattern (反例) | Human Version (正例) | Why (要点) |
|---|---|---|
| His core motivation was survival. | He needed to get out. That was it. Everything else was noise. | Colloquial replaces analytical |
| 核心风险不在今晚吵赢 | 他心里转了一圈，知道今晚不是吵赢的问题 | 口语化替代分析框架 |

## P3: AI-Tell Words — Judgment-Based Frequency Control

**Rationale**: Certain words appear at unnaturally high frequency in AI output. They are not inherently bad — the problem is mechanical repetition that creates a detectable pattern.

**When to Break**: Poetry, lyrical passages, or deliberate stylistic repetition may use these words more freely. The test is whether usage feels intentional and varied, not mechanical.

**Implementation**:
- Use judgment: if a word feels repetitive or automatic, replace with specific action or sensory description
- Guideline: no more than ~1 occurrence per 3,000 words for any single flagged word
- Full word lists → `references/banned-words.md`

## P4: No Repetitive Image Cycling

**Rationale**: AI models recycle the same metaphors because they pattern-match on "what worked before." Human writers move forward — each beat adds new information.

**When to Break**: Deliberate callbacks (e.g., a motif that recurs with evolved meaning across chapters) are valid literary devices. The key is evolved meaning — not identical repetition.

**Implementation**:
- If the same metaphor appears twice, the third occurrence must switch to a new image or new information
- Move forward: each sensory/emotional beat should add something the previous one didn't

| AI Pattern (反例) | Human Version (正例) | Why (要点) |
|---|---|---|
| First: "Fire flowed through his veins." Second: "The heat spread." Third: "Fire coursed through him again." | Third must switch to new information or action. | Avoid circling the same sensation |

## P5: Planning Terms Never Appear in Chapter Text

**Rationale**: Terms like "core motivation" and "information boundary" are internal tools for the writing agent. When they leak into prose, it breaks immersion and is a clear AI-tell signature.

**When to Break**: Never. These are system-internal terms with no literary purpose.

**Implementation**:
- The following terms are for PRE_WRITE_CHECK only, never for chapter prose:
  - 当前处境 / current situation
  - 核心动机 / core motivation
  - 信息边界 / information boundary
  - 性格过滤 / personality filter
  - 行为选择 / behavioral choice
  - 核心风险 / core risk
  - 利益最大化 / optimal outcome
  - 信息落差 / information asymmetry

## P6: Minimize "Not X; Y" Construction

**Rationale**: AI models overuse negation-then-correction ("It wasn't fear — it was something deeper") because it creates an illusion of depth without committing to specificity. Human writers name the thing directly.

**When to Break**: Dialogue where a character is correcting themselves or another character. Internal monologue where the character genuinely reconsiders in real-time. Limit to ~1 per chapter.

**Implementation**:
- State the thing directly instead of defining it by what it's not
- Ban pattern: "不是……而是……" / "不是……，是……" / "不是A，是B" / "It wasn't X. It was Y."

| AI Pattern (反例) | Human Version (正例) | Why (要点) |
|---|---|---|
| It wasn't fear. It was something deeper. | State the thing directly. | Negation-correction is vague |
| 不是恐惧，是更深的东西 | 直接说出那个东西 | 否定句式回避了具体描述 |

## P7: Minimize Lists of Three in Descriptive Prose

**Rationale**: AI models default to tricolon ("ancient, terrible, and vast") because training data is full of rhetorical threes. In prose, it creates a rhythmic monotony that signals machine generation.

**When to Break**: Dialogue (people naturally list things). Intentional rhetorical effect in key moments (~1 per 2,000 words).

**Implementation**:
- Use pairs or single precise words instead of tricolon
- If a list of three is necessary, ensure each item adds distinct meaning (not synonyms)

| AI Pattern (反例) | Human Version (正例) | Why (要点) |
|---|---|---|
| ancient, terrible, and vast | Use pairs or single precise words | Tricolon is AI default rhythm |
| 古老、可怕、广阔 | 用单个精准词或成对词 | 三连形容词是AI节奏特征 |

## Anti-AI Comparison Tables

### Emotion Description (情绪描写)

| AI Pattern (反例) | Human Version (正例) | Why (要点) |
|---|---|---|
| He felt a surge of anger. | He slammed the table. The water glass toppled. | Action externalizes emotion |
| 他感到非常愤怒。 | 他捏碎了手中的茶杯，滚烫的茶水流过指缝，但他像没感觉一样。 | 用动作外化情绪 |
| She was overwhelmed with sadness. | She held the phone with both hands, knuckles white. | Physical detail replaces label |
| 她心里很悲伤，眼泪流了下来。 | 她攥紧手机，指节发白，屏幕上的聊天记录模糊成一片。 | 用身体细节替代直白标签 |
| He felt a wave of fear. | His back went cold. His feet felt like they were on ice. | Five senses convey fear |
| 他感到一阵恐惧。 | 他后背的汗毛竖了起来，脚底像踩在了冰上。 | 五感传递恐惧 |

### Transitions and Connectives (转折与衔接)

| AI Pattern (反例) | Human Version (正例) | Why (要点) |
|---|---|---|
| However, things were not as simple. | Yeah, right. Nothing's ever that easy. | Character voice replaces narrator hedge |
| 然而，事情并没有那么简单。 | 哪有那么便宜的事。 | "然而"换成角色内心吐槽 |
| Although he was strong, he still lost. | He was strong, sure. But the old bastard was dirtier. | Colloquial transition |
| 虽然他很强，但是他还是输了。 | 他确实强，可对面那个老东西更脏。 | 口语化转折 |
| Therefore, he decided to take action. | He stood up and kicked the chair aside. | Delete causal connective, write action |
| 因此，他决定采取行动。 | 他站起来，把凳子踢到一边。 | 删掉因果连词，直接写动作 |

### Vocabulary and Sentence Structure (词汇与句式)

| AI Pattern (反例) | Human Version (正例) | Why (要点) |
|---|---|---|
| Those eyes were full of wisdom and depth. | Those eyes looked like a wolf spotting meat. | Specific metaphor replaces empty adjectives |
| 那双眼睛充满了智慧和深邃。 | 那双眼睛像饿狼见了肉。 | 用具体比喻替代空洞形容词 |
| His heart was full of conflict and struggle. | He stood there fist clenched, then cursed and walked away. | Internal activity externalized as action |
| 他的内心充满了矛盾和挣扎。 | 他攥着拳头站了半天，最后骂了句脏话，转身走了。 | 内心活动外化为行动 |
| The whole room was shocked. | Old Chen's cigarette fell on his pants. He jumped up, yelping. | Group reaction specific to individual |
| 全场为之震惊。 | 老陈的烟掉在了裤子上，烫得他跳起来。 | 群像反应具体到个人 |

### "了" Particle Control (Chinese) / Filter Words

| AI Pattern (反例) | Human Version (正例) | Why (要点) |
|---|---|---|
| 他走了过去，拿了杯子，喝了一口水。 | 他走过去，端起杯子，灌了一口。 | 连续"了"字削弱节奏，保留最有力的一个 |
| 他看了看四周，发现了一个洞口。 | 他扫了一眼四周，墙根裂开一道缝。 | 两个"了"减为一个，"发现"换成画面 |
| He saw a shadow move across the wall. | A shadow slid across the wall. | Remove filter word "saw" |
| 他看到墙上有影子移动。 | 墙上的影子滑过去。 | 删除"看到"过滤词 |
| She felt the cold wind. | The wind cut through her coat. | Direct sensory experience |
| 她感觉到冷风。 | 风钻进她的外套。 | 直接感官体验 |

### Dialogue Tags (对话标签)

| AI Pattern (反例) | Human Version (正例) | Why (要点) |
|---|---|---|
| "I won't do it," she exclaimed defiantly. | "I won't do it." She crossed her arms. | Action beat > adverb + fancy tag |
| "我不干，"她愤怒地喊道。 | "我不干。"她抱起胳膊。 | 动作替代副词+花哨标签 |

## Quick Reference Checklist

Before finalizing any chapter:
1. **P1**: Any narrator conclusions? Delete them.
2. **P2**: Any analytical terms in prose? Replace with character voice.
3. **P3**: AI-tell words feeling repetitive? Replace with specific action/sensory detail.
4. **P4**: Same metaphor 3+ times? Switch to new image.
5. **P5**: Any planning terms in text? Remove.
6. **P6**: "Not X; Y" construction? Max ~1 per chapter.
7. **P7**: Lists of three? Max ~1 per 2,000 words.
8. Emotion labels → action/physical detail.
9. Filter words ("saw," "felt," "heard") → direct description.
10. Narrator stance: delete "obviously," "clearly," "finally understood."

## Integration with Other Skills

This skill works with:
- **writing-craft**: Show-don't-tell is core anti-AI technique
- **character-building**: Six-step method terms are planning tools, never in prose
- **language-zh/en**: Language-specific anti-AI patterns
- **audit-dimensions**: Dimensions 20-23 check AI-tell patterns (principle deviation detection)
