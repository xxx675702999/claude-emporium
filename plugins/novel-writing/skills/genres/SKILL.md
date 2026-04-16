---
name: genres
description: Genre profile management for built-in and custom genres
version: 1.0.0
---

# Genre Management

## Overview

InkOS supports 15 built-in genre profiles (5 Chinese, 10 English) and allows custom genre creation. Genre profiles control writing style, fatigue word detection, audit dimension selection, pacing rules, and satisfaction types. Each book must specify a genre, which affects all pipeline stages (prepare, write, audit).

## Built-in Genres

### Chinese Genres (5)

Located in `data/genres/zh/`:

1. **xuanhuan** (玄幻) — Power fantasy with numerical progression, combat-driven, fast feedback loops
2. **xianxia** (仙侠) — Cultivation with sect politics, moral codes, slower progression
3. **urban** (都市) — Modern setting, realistic constraints, relationship-driven
4. **horror** (恐怖) — Atmosphere-focused, tension building, psychological dread
5. **other** (其他) — Generic fallback with minimal constraints

### English Genres (10)

Located in `data/genres/en/`:

1. **litrpg** — System-driven progression with stats, skills, and level-ups
2. **progression** — Power growth focus without explicit system mechanics
3. **isekai** — Portal fantasy with world transition and adaptation
4. **cultivation** — Western cultivation with training, breakthroughs, and martial arts
5. **system-apocalypse** — Post-apocalyptic with system integration
6. **dungeon-core** — Dungeon management and defense mechanics
7. **romantasy** — Romance-driven fantasy with relationship arcs
8. **sci-fi** — Science fiction with technology and world-building
9. **tower-climber** — Vertical progression through tower floors
10. **cozy** — Low-stakes, comfort-focused, slice-of-life fantasy

## Genre Profile Structure

Each genre profile is a Markdown file with YAML frontmatter and markdown sections:

```yaml
---
name: "Genre Display Name"
id: genre-id
language: zh|en
chapterTypes: ["Type1", "Type2", ...]
fatigueWords: ["word1", "word2", ...]
numericalSystem: true|false
powerScaling: true|false
eraResearch: true|false
pacingRule: "Description of pacing expectations"
satisfactionTypes: ["Type1", "Type2", ...]
auditDimensions: [1,2,3,4,...]
---

## Genre Prohibitions
(List of tropes to avoid)

## [Genre-Specific Rules]
(Additional sections as needed)

## Pacing Guidance
(Chapter structure and rhythm)
```

### Required Fields

- **name**: Human-readable genre name (can be localized)
- **id**: Unique identifier (kebab-case, used in book.json)
- **language**: `zh` or `en` (determines word count logic)
- **chapterTypes**: Array of chapter type labels for planning
- **fatigueWords**: Array of overused words to detect in audit (Dimension 10)
- **numericalSystem**: Whether genre uses explicit numbers (stats, levels)
- **powerScaling**: Whether power progression is a core mechanic
- **eraResearch**: Whether historical/era accuracy matters
- **pacingRule**: String describing expected pacing rhythm
- **satisfactionTypes**: Array of reader satisfaction moments
- **auditDimensions**: Array of dimension IDs to activate (1-37)

### Optional Fields

- **contentGuidelines**: Markdown section with content restrictions
- **tropesToAvoid**: Markdown section listing cliches
- **expectedWordCount**: Override default chapter word count

## Custom Genre Creation

### Step 1: Create Genre File

Create a new Markdown file with YAML frontmatter in `books/<book-id>/genres/<genre-id>.md`:

```yaml
---
name: "Dark Xuanhuan"
id: dark-xuanhuan
language: zh
chapterTypes: ["战斗章", "阴谋章", "过渡章", "回收章"]
fatigueWords: ["冷笑", "蝼蚁", "倒吸凉气", "血雾", "惨叫"]
numericalSystem: true
powerScaling: true
eraResearch: false
pacingRule: "每章必有死亡或背叛，两章内必有反转"
satisfactionTypes: ["背叛", "复仇", "屠杀", "阴谋得逞"]
auditDimensions: [1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,18,19,24,25,26,29]
---

## 题材禁忌
- 主角心软留活口
- 反派智商下线
- 无铺垫的力量觉醒

## 叙事指导
黑暗向玄幻，主角冷酷无情，背叛与复仇是核心主题。
```

### Step 2: Validate Required Fields

All custom genres must include:
- `name`, `id`, `language`
- `chapterTypes` (at least 3 types)
- `fatigueWords` (at least 5 words)
- `auditDimensions` (at least 10 dimensions)

Missing required fields will cause validation errors during book creation.

### Step 3: Reference in book.json

```json
{
  "id": "book-001",
  "title": "暗影崛起",
  "genre": "dark-xuanhuan",
  "customGenrePath": "genres/dark-xuanhuan.md"
}
```

## Copying Built-in Genres

To modify a built-in genre:

1. Copy from `data/genres/{zh|en}/<genre-id>.md` to `books/<book-id>/genres/<new-id>.md`
2. Edit the copied file (change `id` and `name`)
3. Modify fields as needed
4. Update `book.json` to reference the custom genre

Example:

```bash
cp data/genres/zh/xuanhuan.md books/book-001/genres/fast-xuanhuan.md
# Edit fast-xuanhuan.md: change pacingRule to "每章必有爽点"
# Update book.json: "genre": "fast-xuanhuan"
```

## Genre Application

### During Preparation (preparer agent)

- `chapterTypes` → suggests chapter type for current chapter
- `pacingRule` → influences goal and scene directive
- `satisfactionTypes` → guides hook agenda and payoff timing

### During Writing (writer agent)

- `fatigueWords` → writer avoids these words
- `numericalSystem` → determines whether to include stat blocks
- `powerScaling` → affects power progression descriptions
- Genre-specific rules → loaded into rule stack
- `expectedWordCount` → overrides default 3000-word target for the writer's inline length check

### During Audit (auditor agent)

- `auditDimensions` → only listed dimensions are checked
- `fatigueWords` → Dimension 10 (Lexical Fatigue) counts these words
- `contentGuidelines` → Dimension 29 (Sensitive Content) references these

## Genre Inheritance

Custom genres can reference a built-in genre as a base:

```yaml
---
name: "Fast Xuanhuan"
id: fast-xuanhuan
base: xuanhuan
language: zh
pacingRule: "每章必有爽点，不得过渡超过500字"
# Other fields inherited from xuanhuan
---
```

When `base` is set, missing fields are inherited from the base genre profile.

## Genre Switching

To change a book's genre mid-writing:

1. Update `book.json` field `genre`
2. Run `/novel-review --audit` to check existing chapters against new genre rules
3. Revise chapters that fail new audit dimensions

**Warning**: Switching genres may cause existing chapters to fail audit if new genre has stricter rules or different audit dimensions.

## Validation Rules

Genre profiles are validated on load:

- **Required fields present**: name, id, chapterTypes, fatigueWords, auditDimensions
- **chapterTypes**: Array with ≥3 entries
- **fatigueWords**: Array with ≥5 entries
- **auditDimensions**: Array with ≥10 valid dimension IDs (1-37)
- **language**: Must be "zh" or "en"
- **numericalSystem, powerScaling, eraResearch**: Must be boolean
- **id**: Must match filename (without .md extension)

Invalid genre profiles will cause book creation to fail with a validation error message.

## Quick Reference

**Create custom genre**: `books/<book-id>/genres/<genre-id>.md` with required fields  
**Copy built-in genre**: `cp data/genres/{zh|en}/<id>.md books/<book-id>/genres/<new-id>.md`  
**Apply genre**: Set `book.json` field `genre` to genre `id`  
**Built-in locations**: `data/genres/zh/` (5 genres), `data/genres/en/` (10 genres)  
**Required fields**: name, id, language, chapterTypes, fatigueWords, auditDimensions  
**Audit activation**: Only dimensions listed in `auditDimensions` are checked  
**Fatigue detection**: Dimension 10 counts words from `fatigueWords` array
