---
name: language-zh
description: Chinese language constraints - sentence variety, vocabulary control, paragraph rhythm, Chinese-specific anti-AI patterns, web novel conventions
version: 1.0.0
---

# Language-ZH - Chinese Language Constraints

## Overview
This skill contains Chinese-specific writing rules extracted from InkOS writer prompts. Covers sentence variety, vocabulary control, paragraph rhythm, Chinese anti-AI patterns, web novel conventions, and dialogue formatting.

## Core Language Rules

### 1. Language Foundation (语言基础)
- 以简体中文工作
- 句子长短交替
- 段落适合手机阅读（3-5行/段）

### 2. Sentence Variety (句式多样化)
长短句交替，严禁连续使用相同句式或相同主语开头

**Anti-pattern:**
```
✗ 他走进房间。他看到桌子。他拿起杯子。他喝了一口。
```

**Correct:**
```
✓ 他走进房间，桌上放着一只杯子。端起来，灌了一口。
```

**Techniques:**
- 长句（15-25字）+ 短句（5-10字）交替
- 变换主语：他/桌子/杯子/水
- 省略主语：连续动作可省略重复主语
- 句式变化：陈述句/疑问句/感叹句/祈使句混用

### 3. Vocabulary Control (词汇控制)
多用动词和名词驱动画面，少用形容词；一句话中最多1-2个精准形容词

**Adjective limits:**
- ✗ "那是一个非常美丽、优雅、高贵的女人"
- ✓ "那女人一身白衣，走路不带声"

**Verb-driven narrative:**
- ✗ "他很生气地说"
- ✓ "他一拍桌子"

**Noun precision:**
- ✗ "他拿起武器"
- ✓ "他抽出短刀"

### 4. Paragraph Rhythm (段落节奏)
段落适合手机阅读：3-5行/段

**Paragraph structure:**
- 对话：每人一段
- 动作：一个动作序列一段
- 描写：一个场景/物体一段
- 内心独白：一个念头一段

**Rhythm variation:**
- 紧张场景：短段（1-2行）
- 平缓场景：中段（3-5行）
- 描写/回忆：可适当延长（5-7行）

**Anti-pattern:**
- ✗ 超过8行的大段落（手机阅读疲劳）
- ✗ 连续10个以上的单行段落（节奏过碎）

## Chinese-Specific Anti-AI Patterns

### 1. "了" Character Control (了字控制)
连续"了"字削弱节奏，保留最有力的一个

**Anti-pattern:**
```
✗ 他走了过去，拿了杯子，喝了一口水，放了下来。
```

**Correct:**
```
✓ 他走过去，端起杯子，灌了一口，放下。
```

**Rule:** 一个动作序列中，最多保留1-2个"了"

### 2. Transition Markers (转折标记词)
转折/惊讶标记词（仿佛、忽然、竟、竟然、猛地、猛然、不禁、宛如）全篇总数不超过每3000字1次

**Banned high-frequency words:**
- 仿佛
- 忽然
- 竟 / 竟然
- 猛地 / 猛然
- 不禁
- 宛如

**Replacement strategy:**
- ✗ "他忽然发现了一个洞口"
- ✓ "墙根裂开一道缝"

### 3. "Not X, But Y" Construction (不是...而是...)
全文严禁出现"不是……而是……""不是……，是……""不是A，是B"句式

**Banned patterns:**
- 不是……而是……
- 不是……，是……
- 不是A，是B

**Replacement:**
- ✗ "不是恐惧，而是更深的东西"
- ✓ "那不是恐惧。是更深的东西。"（拆成两句）
- ✓ 直接说出那个东西："一种无力感"

### 4. Dash Ban (破折号禁令)
全文严禁出现破折号"——"，用逗号或句号断句

**Anti-pattern:**
```
✗ 他看着远方——那里曾是他的家。
```

**Correct:**
```
✓ 他看着远方，那里曾是他的家。
✓ 他看着远方。那里曾是他的家。
```

### 5. Analytical Language Ban (分析报告式语言禁令)
正文中严禁出现分析报告式语言

**Banned terms in prose:**
- 核心动机
- 信息边界
- 信息落差
- 核心风险
- 利益最大化
- 当前处境
- 战略优势
- 最优结果

**Replacement:**
- ✗ "核心风险不在今晚吵赢"
- ✓ "他心里转了一圈，知道今晚不是吵赢的问题"

### 6. Emotion Intermediary Ban (情绪中介词禁令)
删除无意义的情绪中介词

**Banned phrases:**
- 不禁感叹道
- 不由得想到
- 忍不住说道
- 情不自禁地

**Replacement:**
- ✗ "他不禁感叹道：'真是不容易啊。'"
- ✓ "'真是不容易啊。'他说。"
- ✓ "'真是不容易啊。'"（直接对话）

### 7. Group Reaction Specificity (群像反应具体化)
群像反应不要一律"全场震惊"，改写成1-2个具体角色的身体反应

**Anti-pattern:**
```
✗ 全场为之震惊。
✗ 众人齐声惊呼。
✗ 所有人都愣住了。
```

**Correct:**
```
✓ 老陈的烟掉在了裤子上，烫得他跳起来。
✓ 角落里有人倒吸一口冷气。
✓ 王老板的茶杯停在半空。
```

## Web Novel Conventions (网文惯例)

### 1. Chapter Structure (章节结构)
- 开头：直接进入场景，不要背景介绍
- 中段：冲突推进，节奏紧凑
- 结尾：钩子/悬念/伏笔

### 2. Pacing (节奏)
- 每3-5章一个小爽点
- 每10-15章一个中爽点
- 每卷一个大爽点

### 3. Information Delivery (信息交代)
- 角色身份/外貌/背景通过行动和对话带出
- 禁止"资料卡式"直接罗列
- 世界观设定随剧情自然揭示

### 4. Dialogue Proportion (对话比例)
- 有角色互动的场景：对话占50-70%
- 独处/逃生/探索场景：对话占0-30%
- 对话驱动叙事，不要用大段叙述替代角色交锋

## Dialogue Formatting (对话格式)

### 1. Basic Format (基本格式)
```
"对话内容，"他说。
"对话内容。"他说。
"对话内容！"他说。
"对话内容？"他说。
```

### 2. Action Beats (动作节拍)
```
他一拍桌子："我不干！"
"我不干。"他抱起胳膊。
"我不干！"他转身就走。
```

### 3. Dialogue Tags (对话标签)
**Prefer action beats over fancy tags:**
- ✗ "我不干，"他愤怒地喊道。
- ✓ "我不干。"他一拍桌子。

**Simple tags:**
- 他说
- 他问
- 他答
- 他道

**Avoid:**
- 他愤怒地说
- 他冷笑道
- 他不屑地说
- 他嘲讽道

### 4. Multi-Speaker Scenes (多人对话)
- 每人一段
- 说话人控制在3人以内（同场景）
- 超过3人时，聚焦1-2个主要说话人

## Vocabulary Fatigue Management (词汇疲劳管理)

### High-Fatigue Words (高疲劳词)
Genre-specific fatigue words should appear max 1 time per chapter.

**Common fatigue words (varies by genre):**
- 玄幻：灵气、修为、境界、突破
- 都市：集团、总裁、秘书、合同
- 仙侠：仙缘、道心、天劫、飞升

**Management strategy:**
- 用同义词替换
- 用具体描写替代抽象词
- 省略不必要的重复

## Sentence Opening Patterns (句首模式)

### Avoid Repetitive Openings (避免重复句首)
**Anti-pattern:**
```
✗ 他走进房间。
  他看到桌子。
  他拿起杯子。
  他喝了一口。
```

**Correct:**
```
✓ 他走进房间。
  桌上放着一只杯子。
  端起来，灌了一口。
  水是凉的。
```

### Opening Variety (句首多样化)
- 主语开头：他/桌子/水
- 动词开头：走进/端起/灌了
- 时间开头：三天后/此刻/那一瞬
- 地点开头：房间里/墙角/门外
- 状态开头：安静/混乱/黑暗

## Rhetorical Patterns (修辞模式)

### 1. Metaphor (比喻)
- 用具体比喻替代空洞形容词
- ✗ "那双眼睛充满了智慧和深邃"
- ✓ "那双眼睛像饿狼见了肉"

### 2. Parallelism (排比)
- 用于强调和节奏
- 不要超过3个分句
- ✓ "他不信命，不信天，只信手里的刀"

### 3. Rhetorical Question (反问)
- 用于内心独白
- 不要连续使用
- ✓ "他能怎么办？只能硬着头皮上"

### 4. Exaggeration (夸张)
- 用于情绪渲染
- 不要过度使用
- ✓ "他的心跳得像要炸开"

### 5. Personification (拟人)
- 用于环境描写
- 不要滥用
- ✓ "风钻进他的外套"

### 6. Short Sentence Rhythm (短句节奏)
- 用于紧张场景
- 3-5个短句连用
- ✓ "他跑。风追。影子长。天快黑了。"

## 黄金三章 (Golden Chapters)

开篇三章决定读者是否追读。当 `chapterNumber <= 3` 时，以下规则自动注入。

### 通用规则（第1-3章）
- 开篇不要从第一块砖头开始砌楼——从炸了一栋楼开始写
- 禁止信息轰炸：世界观、力量体系等设定随剧情自然揭示
- 每章聚焦1条故事线，人物数量控制在3个以内
- 强情绪优先：利用读者共情（亲情纽带、不公待遇、被低估）快速建立代入感

### 第一章：抛出核心冲突
- 开篇直接进入冲突场景，禁止用背景介绍/世界观设定开头
- 第一段必须有动作或对话，让读者"看到"画面
- 开篇场景限制：最多1-2个场景，最多3个角色
- 主角身份/外貌/背景通过行动自然带出，禁止资料卡式罗列
- 本章结束前，核心矛盾必须浮出水面
- 一句对话能交代的信息不要用一段叙述

### 第二章：展现金手指/核心能力
- 主角的核心优势（金手指/特殊能力/信息差等）必须在本章初现
- 金手指的展现必须通过具体事件，不能只是内心独白"我获得了XX"
- 开始建立"主角有什么不同"的读者认知
- 第一个小爽点应在本章出现
- 继续收紧核心冲突，不引入新支线

### 第三章：明确短期目标
- 主角的第一个阶段性目标必须在本章确立
- 目标必须具体可衡量（打败某人/获得某物/到达某处），不能是抽象的"变强"
- 读完本章，读者应能说出"接下来主角要干什么"
- 章尾钩子要足够强，这是读者决定是否继续追读的关键章

## Quick Reference Checklist

Before finalizing Chinese chapter:
1. **句式多样化:** 连续相同句式？相同主语开头？
2. **了字控制:** 一个动作序列超过2个"了"？
3. **转折标记词:** 仿佛/忽然/竟/猛地 超过1次/3000字？
4. **不是...而是...:** 出现此句式？
5. **破折号:** 出现"——"？
6. **分析语言:** 核心动机/信息边界等术语在正文？
7. **情绪中介词:** 不禁/不由得/忍不住？
8. **群像反应:** "全场震惊"类集体反应？
9. **形容词:** 一句话超过2个形容词？
10. **段落长度:** 超过8行的段落？

## Integration with Other Skills

This skill works with:
- **writing-craft:** Chinese implementation of narrative techniques
- **character-building:** Chinese character voice and dialogue
- **anti-ai:** Chinese-specific anti-AI patterns
- **audit-dimensions:** Language-specific audit checks
