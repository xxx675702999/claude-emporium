# Anti-AI — Banned / Flagged Word Lists

Soft guidance for word frequency control. These words are not absolutely banned — the goal is to avoid mechanical repetition that creates detectable AI patterns. Use judgment: if a word feels automatic rather than intentional, replace it.

**General guideline**: No more than ~1 occurrence of any single flagged word per 3,000 words.

## Chinese Flagged Words (中文标记词)

### AI-Tell High-Frequency Words (AI高频词)

These words appear at unnaturally high rates in AI-generated Chinese prose:

| Word | Why Flagged | Replacement Strategy |
|------|------------|---------------------|
| 仿佛 | AI default for simile; overused to fake literary quality | Use specific comparison or delete — "仿佛火焰在燃烧" → "烫得他缩手" |
| 忽然 | AI uses as cheap surprise device | Delete or use action that implies suddenness — "忽然一声巨响" → "墙炸开了" |
| 竟 / 竟然 | AI overuses for fake contrast/surprise | Reserve for genuine surprise; often deletable — "他竟然赢了" → "他赢了" (context provides surprise) |
| 猛地 / 猛然 | AI default for sudden action | Use specific action verb — "猛地站起来" → "椅子翻了，他已经站着了" |
| 不禁 | AI emotional intermediary; adds nothing | Delete — "不禁感叹" → directly write the exclamation |
| 宛如 | Same problem as 仿佛; literary cliche | Use grounded comparison or delete |

### Analytical/Report Terms (分析/报告用语)

These must never appear in narrative prose (see P2, P5). They are planning-stage tools:

| Term | Context |
|------|---------|
| 核心动机 | Planning only — character motivation analysis |
| 信息边界 / 信息落差 | Planning only — character knowledge tracking |
| 核心风险 | Planning only — conflict analysis |
| 利益最大化 | Planning only — decision modeling |
| 当前处境 | Planning only — situation assessment |
| 信息不对称 | Planning only — character knowledge gap |
| 战略格局 | Planning only — power dynamics |

### Formulaic Transitions (公式化转折词)

Overuse of these creates a detectable AI rhythm:

| Word | Guideline |
|------|-----------|
| 然而 | Max ~1 per 1,000 words. Replace with character voice: "哪有那么便宜的事" |
| 不过 | Same guideline. Often deletable — let the contrast speak through juxtaposition |
| 与此同时 | Rarely needed. Switch scenes with action, not transition words |
| 虽然……但是…… | Replace with colloquial: "他确实强，可对面那个老东西更脏" |

### "了" Particle Overuse (了字过度使用)

Sequential "了" is a strong AI-tell signal in Chinese prose:

- **Rule**: In a sequence of actions, keep only the most impactful "了"
- ✗ "他走了过去，拿了杯子，喝了一口水"
- ✓ "他走过去，端起杯子，灌了一口"

### Hard Bans — Chinese-Specific (硬性禁令)

| Ban | Rationale |
|-----|-----------|
| Dash "——" | Use comma or period to break sentences. AI overuses em-dash in Chinese prose |
| Ledger-style data in prose (hook_id, "余量由X%降到Y%") | Numerical settlements belong in POST_SETTLEMENT only |
| Meta-narrative ("到这里算是钉死了") | Breaks fourth wall. Never use screenwriter-voice in chapter text |

## English Flagged Words

### AI-Tell High-Frequency Words

These words appear at unnaturally high rates in AI-generated English prose:

| Word | Why Flagged | Replacement Strategy |
|------|------------|---------------------|
| delve | AI signature word; rarely used by human writers | Delete or use specific verb — "delve into" → "dig into" / "examine" / "pick apart" |
| tapestry | AI metaphor for complexity; almost always metaphorical | Use specific image — "a tapestry of emotions" → describe the actual emotions |
| testament | AI summary word | Delete — "It was a testament to his strength" → show the strength |
| intricate | AI adjective for "complex" | Use specific detail — "intricate patterns" → describe what the patterns look like |
| pivotal | AI word for "important" | Show importance through consequences, not labeling |
| vibrant | AI visual adjective | Use specific color/texture — "vibrant marketplace" → "the market smelled like cumin and sweat" |
| embark | AI journey-start word | Use concrete action — "embark on a journey" → "he packed a bag and left" |
| comprehensive | Report language, not prose | Delete from narrative; acceptable in system/UI text |
| nuanced | Report/essay language | Delete — show the nuance instead of labeling it |
| landscape (metaphorical) | AI metaphor for "situation" | Use specific detail — "the political landscape" → "who had power and who wanted it" |
| realm (metaphorical) | AI metaphor for "area/domain" | Use concrete term |
| foster | Report language | Use natural verb — "foster understanding" → "get them to see" |
| underscore | Report language | Show emphasis through action, not labeling |

### Formulaic Transitions

| Word | Guideline |
|------|-----------|
| however | Max ~1 per 1,000 words. Often deletable — use juxtaposition |
| meanwhile | Max ~1 per 1,000 words. Scene breaks > transition words |
| nevertheless | Almost always deletable. Let the contrast speak |
| furthermore | Essay word. Delete from prose |
| moreover | Essay word. Delete from prose |

### Filter Words

Remove the perception layer — put the reader directly in the experience:

| Filter Word | Replacement |
|------------|-------------|
| He saw / She saw | Write what was there — "A shadow slid across the wall" |
| He felt / She felt | Write the sensation — "The wind cut through her coat" |
| He heard / She heard | Write the sound — "Glass shattered somewhere behind him" |
| He noticed | Delete — write the thing directly |
| He realized | Delete — show the realization through action/dialogue |
| He thought | Use italics for direct thought, or show through behavior |

### Hard Bans — English-Specific

| Ban | Rationale |
|-----|-----------|
| Adverb + dialogue tag overuse ("exclaimed defiantly") | Use action beats — "She crossed her arms" > "she said defiantly" |
| Passive voice in action scenes | Active voice: "The sword cut his arm" > "His arm was cut by the sword" |
| Weak verb chains ("was going to be able to") | Strong single verbs: "He could" or rewrite entirely |
