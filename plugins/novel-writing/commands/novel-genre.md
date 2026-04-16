---
name: novel-genre
description: List, create, and copy genre profiles
---

# /novel-genre — Genre Management

## Usage
/novel-genre [action] [options]

## Actions

### list
List all available genres (built-in + custom).

**Syntax:**
```
/novel-genre list [--lang <zh|en>] [--book <id>]
```

**Process:**
1. If `--lang` specified: Filter by language
2. Else: Show both Chinese and English genres
3. List built-in genres from `data/genres/<lang>/`
4. If `--book` specified: List custom genres from `books/<id>/genres/`
5. Display with: ID, Name, Language, Type (built-in/custom)

**Output:**
```
Built-in Genres (Chinese):
- xuanhuan: 玄幻
- xianxia: 仙侠
- urban: 都市
- horror: 恐怖
- other: 其他

Built-in Genres (English):
- litrpg: LitRPG
- progression: Progression Fantasy
- isekai: Isekai
- cultivation: Cultivation
- system-apocalypse: System Apocalypse
- dungeon-core: Dungeon Core
- romantasy: Romantasy
- sci-fi: Science Fiction
- tower-climber: Tower Climber
- cozy: Cozy Fantasy

Custom Genres (book-20260414-103045):
- dark-xuanhuan: Dark Xuanhuan (based on xuanhuan)

Total: 15 built-in, 1 custom
```

### show
Show detailed genre profile.

**Syntax:**
```
/novel-genre show <genre-id> [--lang <zh|en>] [--book <id>]
```

**Process:**
1. If `--book` specified: Check custom genres first in `books/<id>/genres/<genre-id>.md`
2. If not found in custom: Check built-in genres in `data/genres/<lang>/<genre-id>.md`
3. If `--lang` not specified: Try both zh and en
4. Read genre file (YAML frontmatter + markdown content)
5. Display formatted output with all fields

**Output:**
```
Genre: 玄幻 (xuanhuan)
Type: Built-in
Language: Chinese

Chapter Types: 战斗章, 布局章, 过渡章, 回收章
Fatigue Words: 冷笑, 蝼蚁, 倒吸凉气, 瞳孔骤缩, 不可置信, 轰然炸裂, 满场死寂, 难以置信, 仿佛, 不禁, 宛如, 竟然
Numerical System: Yes
Power Scaling: Yes
Era Research: No
Pacing Rule: 三章内必有明确反馈：打脸、收益兑现、信息反转、地位变化
Satisfaction Types: 打脸, 升级突破, 收益兑现, 智斗碾压, 身份揭示, 底牌亮出
Audit Dimensions: 1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,18,19,24,25,26

Content Guidelines:
- 题材禁忌 (Genre Taboos)
- 数值规则 (Numerical Rules)
- 语言铁律 (Language Rules)
- 叙事指导 (Narrative Guidance)

(Full content available in data/genres/zh/xuanhuan.md)
```

### create
Create a custom genre profile.

**Syntax:**
```
/novel-genre create <genre-id> --name <name> [--base <base-genre>] [--book <id>]
```

**Process:**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. Check if genre ID already exists (in built-in or custom)
4. If `--base` specified: Copy base genre from `data/genres/<lang>/<base>.md`
5. Else: Use empty template with required fields
6. Fill in `name` field
7. Open for editing (user fills in remaining fields)
8. Validate required fields:
   - `name`: Genre display name
   - `chapterTypes`: Array of chapter types (at least 1)
   - `fatigueWords`: Array of overused words (can be empty)
   - `auditDimensions`: Array of applicable dimension numbers (at least 1)
   - `pacingRule`: Pacing guidelines (string)
   - `satisfactionTypes`: Array of satisfaction types (at least 1)
9. Save to `books/<id>/genres/<genre-id>.md`
10. Report success

**Required fields:**
- `name`: Genre display name
- `id`: Genre identifier (from command argument)
- `chapterTypes`: Array of chapter types
- `fatigueWords`: Array of overused words
- `auditDimensions`: Array of applicable dimension numbers (1-37)
- `pacingRule`: Pacing guidelines
- `satisfactionTypes`: Array of satisfaction types

**Optional fields:**
- `numericalSystem`: Boolean (default: false)
- `powerScaling`: Boolean (default: false)
- `eraResearch`: Boolean (default: false)

**Example:**
```
/novel-genre create dark-xuanhuan --name "Dark Xuanhuan" --base xuanhuan
```

**Output:**
```
Creating custom genre: dark-xuanhuan
Base genre: xuanhuan (玄幻)

Template created with base genre content.
Edit the following fields:

---
name: Dark Xuanhuan
id: dark-xuanhuan
chapterTypes: ["战斗章", "布局章", "过渡章", "回收章"]
fatigueWords: ["冷笑", "蝼蚁", "倒吸凉气", "瞳孔骤缩"]
numericalSystem: true
powerScaling: true
eraResearch: false
pacingRule: "三章内必有明确反馈：打脸、收益兑现、信息反转、地位变化"
satisfactionTypes: ["打脸", "升级突破", "收益兑现", "智斗碾压"]
auditDimensions: [1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,18,19,24,25,26]
---

## 题材禁忌
(Add your custom taboos here)

---
Save this genre? (y/n): _
```

**After save:**
```
✓ Custom genre created: dark-xuanhuan
  Name: Dark Xuanhuan
  Base: xuanhuan
  Location: books/book-20260414-103045/genres/dark-xuanhuan.md

Use this genre when creating a new book:
/novel create --title "My Novel" --genre dark-xuanhuan --lang zh --words 3000 --chapters 200
```

### copy
Copy and modify a built-in genre.

**Syntax:**
```
/novel-genre copy <source-genre> <new-genre-id> [--book <id>]
```

**Process:**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. Check if source genre exists in built-in genres
4. Read book language from `book.json` to determine source path
5. Copy genre file from `data/genres/<lang>/<source>.md`
6. Save to `books/<id>/genres/<new-genre-id>.md`
7. Update `id` field in YAML frontmatter to new genre ID
8. Open for editing (user modifies as needed)
9. Validate required fields
10. Save changes
11. Report success

**Example:**
```
/novel-genre copy xuanhuan dark-xuanhuan --book book-20260414-103045
```

**Output:**
```
Copying genre: xuanhuan → dark-xuanhuan

Source: data/genres/zh/xuanhuan.md
Destination: books/book-20260414-103045/genres/dark-xuanhuan.md

Genre copied. Edit as needed:

---
name: 玄幻
id: dark-xuanhuan
chapterTypes: ["战斗章", "布局章", "过渡章", "回收章"]
...
---

(Full content displayed for editing)

---
Save changes? (y/n): _
```

### delete
Delete a custom genre.

**Syntax:**
```
/novel-genre delete <genre-id> [--book <id>]
```

**Process:**
1. If `--book` specified: Use that book ID
2. Else: Read `.session.json` for `activeBook`
3. Check if genre exists in `books/<id>/genres/<genre-id>.md`
4. If genre is built-in: Report error (cannot delete built-in genres)
5. Prompt for confirmation
6. If confirmed: Delete `books/<id>/genres/<genre-id>.md`
7. Report success

**Confirmation prompt:**
```
⚠️  Delete custom genre "dark-xuanhuan"?
This will permanently delete the genre profile.
Books using this genre will fall back to the base genre or "other".

Type 'yes' to confirm: _
```

**After confirmation:**
```
✓ Custom genre deleted: dark-xuanhuan
```

## Natural Language Routing
If the user's message matches these patterns, route to the corresponding action:
- "list genres/show genres/available genres" → list
- "show genre/genre details/describe genre" → show
- "create genre/new genre/add genre" → create
- "copy genre/duplicate genre" → copy
- "delete genre/remove genre" → delete

If intent is unclear, ask user to clarify.

## Error Handling
- If genre not found: List available genres with `/novel-genre list`
- If required field missing: Report validation error with field name
- If custom genre conflicts with built-in: Warn user and suggest different ID
- If trying to delete built-in genre: Report error "Cannot delete built-in genres"
- If book not found: List available books with `/novel list`
- If active book not set: Suggest using `--book <id>` or `/novel list`

## Notes
- Built-in genres are read-only — use `copy` to create a modifiable version
- Custom genres are book-specific — each book can have its own custom genres
- Genre profiles control chapter types, fatigue words, audit dimensions, and pacing rules
- When creating a book, you can use either built-in or custom genres
- Custom genres inherit from base genres but can override any field
