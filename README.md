# claude-emporium

Personal AI skill plugins marketplace for Claude Code.

## Available Plugins

| Plugin | Description |
|--------|-------------|
| [novel-writing](plugins/novel-writing/README.md) | AI-assisted novel writing with multi-agent pipeline, anti-AI detection, genre profiles, and audit-driven revision |

## Adding This Marketplace

### SSH Setup (Recommended)

Using SSH is the simplest way to authenticate with GitHub. Run this once to configure git:

```bash
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

> **Tip:** Need to set up an SSH key? Ask Claude Code: `"Help me set up an SSH key for github.com"`

### Install the Marketplace

1. Open Claude Code
2. Type: `/plugin`
3. Select **"Add marketplace"**
4. Paste the marketplace URL:
   ```
   https://github.com/xxx675702999/claude-emporium.git
   ```
5. Browse and install available plugins

### Enable Auto-Updates (Recommended)

To automatically receive new plugins and updates:

1. Run `/plugin` in Claude Code
2. Go to the **Marketplaces** tab
3. Select **claude-emporium**
4. Choose **Enable auto-update**

This ensures you always have access to the latest plugins and improvements.

## Plugin Structure

```
.claude-plugin/
├── marketplace.json          # Marketplace registry
└── plugins/
    └── novel-writing.json    # Per-plugin metadata

plugins/
└── <plugin-name>/
    ├── skills/
    │   └── <plugin-name>/
    │       └── SKILL.md      # Skill definition (YAML frontmatter + markdown body)
    ├── .claude-plugin/
    │   └── plugin.json       # Plugin metadata (name, description, version, author)
    ├── agents/               # Subagent definitions (optional)
    ├── commands/              # Slash command definitions (optional)
    ├── data/                  # Static data files (optional)
    ├── scripts/               # Helper scripts (optional)
    └── evals/
        └── evals.json        # Evaluation test cases
```

## Adding a New Plugin

1. Create `plugins/<plugin-name>/skills/<plugin-name>/SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: your-plugin-name
   description: >
     When to trigger this skill...
   ---
   ```
2. Create `plugins/<plugin-name>/evals/evals.json` with test cases
3. Create `plugins/<plugin-name>/.claude-plugin/plugin.json` with plugin metadata
4. Add an entry to `.claude-plugin/marketplace.json` under `plugins`

## License

Private repository. All rights reserved.
