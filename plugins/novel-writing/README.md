# Novel Writing Plugin

AI 驱动的长篇小说写作插件，基于 Claude Code 插件架构。通过 6 个专业 Agent 和全自动 Pipeline，实现从大纲到成稿的完整创作流程。

## 核心特性

- **全流程自动化**：准备 → 写作 → 状态持久化 → 审计 → 修订，每章自动走完整 Pipeline
- **多 Agent 协作**：6 个 Agent 各司其职，上下文隔离，温度分离（创作 0.7 / 分析 0.3）
- **真值文件系统**：9 个结构化状态文件追踪世界观、角色、伏笔、支线、情感弧线等
- **37 维质量审计**：33 个核心维度 + 4 个条件维度，LLM 判断 + 确定性检测双轨并行
- **中英双语支持**：字数统计、类型模板、语言规则按语言自动切换
- **15 种类型模板**：玄幻、修仙、都市、系统末世、LitRPG、恐怖、科幻等
- **同人 & 衍生**：支持同人创作（4 种模式）和衍生作品（前传/续集/外传/视角转换）
- **风格仿写**：分析参考文本提取风格指纹，后续章节自动匹配

## 快速开始

### 安装

```bash
claude plugin add /path/to/novel-writing
```

### 创建新书

```bash
# 中文小说
/novel create --title "破灭星辰" --genre xuanhuan --lang zh --words 3000 --chapters 200

# 英文小说
/novel create --title "The Last Signal" --genre sci-fi --lang en --words 4000 --chapters 30

# 导入已有章节
/novel create --import manuscript.txt --pattern "^第\d+章"
```

### 写作

```bash
# 写下一章（自动检测章节号）
/novel-continue

# 写下一章，跳过确认
/novel-continue --yes

# 连续写 5 章
/novel-write --count 5 --yes

# 全自动批量写作（无暂停）
/novel-write --count 10 --batch

# 快速草稿（跳过审计）
/novel-draft
```

### 审阅与修订

```bash
# 审计指定章节
/novel-review --audit 15

# 审计 + 自动修订
/novel-review 15

# 批准章节
/novel-review --approve 15

# 快速修复最新章节（审计 + 修订）
/novel-fix
```

### 导出

```bash
# 导出为 EPUB
/novel-export --format epub

# 导出为纯文本
/novel-export --format txt

# 导出为 Markdown
/novel-export --format md
```

## 命令一览

| 命令 | 说明 |
|------|------|
| `/novel` | 书籍管理：创建、列表、更新、删除、模式切换 |
| `/novel-write` | 完整 Pipeline 写作（Prepare → Write → Persist → Audit → Revise） |
| `/novel-draft` | 快速草稿（跳过审计，适合迭代试写） |
| `/novel-continue` | 自动检测最新章节，续写下一章 |
| `/novel-fix` | 检测最新章节，执行审计 + 修订 |
| `/novel-review` | 审阅、审计、修订、批准章节 |
| `/novel-export` | 导出为 TXT / Markdown / EPUB |
| `/novel-stats` | 书籍统计与分析 |
| `/novel-genre` | 类型模板管理（列表、创建、复制） |
| `/novel-style` | 风格分析与仿写 |

## Pipeline 架构

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Preparer │───▶│  Writer  │───▶│ Persist  │───▶│ Auditor  │───▶│ Reviser  │
│  (0.7)   │    │P1(0.7)   │    │(Scripts) │    │  (0.3)   │    │  (0.3)   │
│          │    │P2(0.3)   │    │          │    │          │    │          │
│ 意图生成  │    │P1:创作    │    │ 状态持久化│    │ 37维审计  │    │ 定向修订  │
│ 上下文选择│    │P2:事实提取 │    │ 快照备份  │    │ 双轨并行  │    │ 回归防护  │
│ 规则编译  │    │ 字数治理   │    │ MD投射再生│    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### Agent 职责

| Agent | 温度 | 职责 |
|-------|------|------|
| **Architect** | 0.7 | 建书时生成基础文件（世界观、大纲、规则、初始状态） |
| **Preparer** | 0.7 | 生成章节意图、筛选上下文、编译规则栈 |
| **Writer** | 0.7/0.3 | Phase 1: 创作写作；Phase 2: 事实提取 + Delta 生成 |
| **Auditor** | 0.3 | 37 维质量审计（LLM 判断 + 确定性检测） |
| **Reviser** | 0.3 | 定向修订（5 种模式：spot-fix / rewrite / polish / anti-detect / custom） |
| **Style Analyzer** | — | 分析参考文本，生成风格指南和统计指纹 |

## 真值文件系统

每本书维护 9 个结构化状态文件，保证跨章节一致性：

| 文件 | 追踪内容 |
|------|---------|
| `current_state.json` | 世界观当前状态（时间、地点、角色状态） |
| `pending_hooks.json` | 未解决的叙事伏笔 |
| `chapter_summaries.json` | 各章摘要 |
| `character_matrix.json` | 角色关系矩阵 |
| `emotional_arcs.json` | 情感弧线追踪 |
| `subplot_board.json` | 支线看板 |
| `resource_ledger.json` | 数值系统账本（等级、金币等） |
| `manifest.json` | 元数据清单 |
| `chapter-meta.json` | 章节生命周期状态 |

每个 JSON 文件都有对应的 Markdown 投射（`story/*.md`），供 Agent 阅读。JSON 是持久化格式，Markdown 从 JSON 自动生成。

## 审计系统

### 37 个审计维度

**核心维度（1-27）**：始终启用
- 叙事连贯性、角色一致性、力量体系、数值准确性、时间线、因果逻辑
- 伏笔管理、风格漂移、节奏控制、对话质量、世界观一致性
- POV 一致性、信息泄露、展示 vs 讲述、情感弧线
- AI 痕迹检测（段落均匀性、对冲词密度、公式化转折、列表结构）
- 敏感词检测

**衍生维度（28-31）**：衍生作品启用
- 正典事件冲突、未来信息泄露、跨书世界规则、衍生伏笔隔离

**同人维度（34-37）**：同人创作启用
- 角色忠实度、情节合理性、世界观遵守、关系动态

### 双轨审计

- **Track A**：LLM 审计（维度 1-19, 24+）— 文学判断
- **Track B**：确定性检测（维度 20-23）— 零 LLM 的统计分析 + 敏感词检测
- 三源合并生成最终审计报告

## 类型模板

### 中文

| 类型 | ID |
|------|-----|
| 玄幻 | `xuanhuan` |
| 仙侠 | `xianxia` |
| 修仙 | `cultivation` |
| 都市 | `urban` |
| 系统末世 | `system-apocalypse` |
| LitRPG | `litrpg` |
| 异世界 | `isekai` |
| 地下城核心 | `dungeon-core` |
| 登塔 | `tower-climber` |
| 进阶 | `progression` |
| 浪漫奇幻 | `romantasy` |
| 恐怖 | `horror` |
| 科幻 | `sci-fi` |
| 治愈 | `cozy` |
| 其他 | `other` |

### 英文

同上 15 种类型，ID 相同，模板内容为英文。

支持自定义类型：`/novel-genre create <id>`

## 自动化模式

| 模式 | 说明 |
|------|------|
| `interactive`（默认） | 智能暂停：写作前确认，>2 个严重审计问题时修订前确认 |
| `batch` | 零暂停：全流程自动运行，适合无人值守批量生成 |

切换模式：
```bash
/novel mode batch      # 切换到批量模式
/novel mode interactive  # 切换回交互模式
```

单次覆盖：
```bash
/novel-write --yes           # 跳过确认
/novel-write --batch         # 本次强制批量模式
/novel-write --dry-run       # 只生成意图，不写作
/novel-write --pause-on audit  # 在审计前暂停
```

## 同人 & 衍生

### 同人创作

```bash
/novel create --fanfic source.txt --title "平行时空" --mode au --lang zh
```

4 种模式：
- **canon**：严格遵守原作
- **au**：平行宇宙，世界规则可变
- **ooc**：角色性格可偏离
- **cp**：CP 向，关系动态优先

### 衍生作品

```bash
/novel create --spinoff <parent-id> --title "前传" --type prequel
```

4 种类型：`prequel`（前传）、`sequel`（续集）、`side-story`（外传）、`pov-shift`（视角转换）

## 风格仿写

```bash
# 分析参考文本
/novel-style --analyze reference.txt

# 分析并应用到当前书籍
/novel-style --analyze reference.txt --apply
```

生成两个文件：
- `style_guide.md`：给 Writer 的可执行风格规则
- `style_fingerprint.md`：给 Auditor 的量化基线（用于风格漂移检测）

## 环境要求

- Claude Code
- Python 3.10+（仅标准库，无第三方依赖）
- 中英双语支持

## 项目结构

```
novel-writing/
├── agents/          # 6 个 Pipeline Agent 定义
├── commands/        # 10 个用户命令
├── skills/          # 15 个知识域（按需加载）
├── scripts/
│   ├── analyze/     # 风格分析脚本
│   ├── detect/      # AI 痕迹检测脚本
│   ├── export/      # 导出脚本
│   ├── lib/         # 共享库
│   └── pipeline/    # Pipeline 脚本（持久化、审计、验证等）
├── data/
│   ├── genres/      # 中英类型模板（各 15 种）
│   ├── schemas/     # JSON Schema
│   └── templates/   # 文件模板
└── books/           # 书籍数据（运行时生成）
```
