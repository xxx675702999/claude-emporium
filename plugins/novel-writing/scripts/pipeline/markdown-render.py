#!/usr/bin/env python3
"""markdown-render.py — Convert a truth JSON file to human-readable markdown.

Usage: markdown-render.py <json-file> <output-md>
Output: writes markdown file, prints path to stdout
Exit codes: 0 success, 1 error
"""

import argparse
import json
import sys
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.json_utils import read_json


def render_current_state(data: dict) -> str:
    chapter = data.get("chapter", 0)
    lines = [f"# Current State (Chapter {chapter})", ""]
    facts = data.get("facts") or []
    if not facts:
        lines.append("No facts recorded.")
        return "\n".join(lines)
    lines.extend([
        "| 字段 | 值 |",
        "|------|-----|",
    ])
    for fact in facts:
        if fact.get("validUntilChapter") is not None:
            continue  # skip superseded facts
        pred = fact.get("predicate", "")
        obj = fact.get("object", "")
        lines.append(f"| {pred} | {obj} |")
    return "\n".join(lines)


def render_pending_hooks(data: dict) -> str:
    lines = [
        "| hook_id | 起始章节 | 类型 | 状态 | 最近推进 | 预期回收 | 回收节奏 | 备注 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for hook in data.get("hooks") or []:
        hid = hook.get("hookId", "?")
        start = hook.get("startChapter", "?")
        htype = hook.get("type", "")
        status = hook.get("status", "open")
        last = hook.get("lastAdvancedChapter", "?")
        payoff = hook.get("expectedPayoff", "")
        timing = hook.get("payoffTiming", "")
        notes = hook.get("notes", "")
        # Bold non-standard statuses for emphasis
        if status in ("critical", "escalating"):
            status = f"**{status}**"
        elif status == "progressing" and hook.get("lastAdvancedChapter", 0) > 0:
            status = f"**{status}**"
        lines.append(f"| {hid} | {start} | {htype} | {status} | {last} | {payoff} | {timing} | {notes} |")
    return "\n".join(lines)


def render_chapter_summaries(data: dict) -> str:
    lines = [
        "| 章节 | 标题 | 出场人物 | 关键事件 | 状态变化 | 伏笔动态 | 情绪基调 | 章节类型 |",
        "|------|------|----------|----------|----------|----------|----------|----------|",
    ]
    for ch in data.get("chapters") or []:
        num = ch.get("chapter", "?")
        title = ch.get("title", "")
        chars = ch.get("characters", "")
        events = ch.get("events", "")
        state = ch.get("stateChanges", "")
        hooks = ch.get("hookActivity", "")
        mood = ch.get("mood", "")
        ctype = ch.get("chapterType", "")
        lines.append(f"| {num} | {title} | {chars} | {events} | {state} | {hooks} | {mood} | {ctype} |")

    # Add recent titles section for writer agent reference
    chapters = data.get("chapters") or []
    if chapters:
        recent = chapters[-5:]
        lines.append("")
        lines.append("## Recent Titles")
        for ch in recent:
            num = ch.get("chapter", "?")
            title = ch.get("title", "")
            lines.append(f"- Ch{num}: {title}")

    return "\n".join(lines)


def render_world_state(data: dict) -> str:
    lines = ["# World State", ""]
    lines.append("## Locations")
    for item in data.get("locations") or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Rules")
    for item in data.get("rules") or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Technology")
    for item in data.get("technology") or []:
        lines.append(f"- {item}")
    return "\n".join(lines)


def render_character_matrix(data: dict) -> str:
    """Render character matrix with 3 sub-tables matching inkos format."""
    characters = data.get("characters") or []
    if not characters:
        return "# 角色交互矩阵\n\n(暂无角色数据)"

    lines = ["### 角色档案"]
    lines.append("| 角色 | 核心标签 | 状态 | 首次出场 | 最近出场 | 动机 | 当前弧线 | 能力 |")
    lines.append("|------|----------|------|----------|----------|------|----------|------|")
    for char in characters:
        name = char.get("name", "?")
        desc = char.get("description", "")
        status = char.get("status", "active")
        intro = char.get("introducedInChapter", "?")
        last = char.get("lastAppearedInChapter", "?")
        motivation = char.get("motivation", "")
        arc = char.get("arc", "")
        abilities = ", ".join(char.get("abilities") or [])
        lines.append(f"| {name} | {desc} | {status} | {intro} | {last} | {motivation} | {arc} | {abilities} |")

    # Relationship sub-table
    rel_rows = []
    for char in characters:
        char_name = char.get("name", "?")
        for rel in char.get("relationships") or []:
            target = rel.get("targetCharacterId", "?")
            rtype = rel.get("relationship", "")
            rstatus = rel.get("status", "active")
            notes = rel.get("notes", "")
            rel_rows.append(f"| {char_name} | {target} | {intro} | {char.get('lastAppearedInChapter', '?')} | {rtype} ({rstatus}) | {notes} |")

    if rel_rows:
        lines.append("")
        lines.append("### 相遇记录")
        lines.append("| 角色A | 角色B | 首次相遇章 | 最近交互章 | 关系性质 | 关系变化 |")
        lines.append("|-------|-------|------------|------------|----------|----------|")
        lines.extend(rel_rows)

    # Information boundary sub-table (derived from character knowledge)
    lines.append("")
    lines.append("### 信息边界")
    lines.append("| 角色 | 已知信息 | 未知信息 | 信息来源章 |")
    lines.append("|------|----------|----------|------------|")
    for char in characters:
        name = char.get("name", "?")
        last = char.get("lastAppearedInChapter", "?")
        lines.append(f"| {name} | (从正文推断) | (从正文推断) | {last} |")

    return "\n".join(lines)


def render_resource_ledger(data: dict) -> str:
    lines = [
        "# Resource Ledger",
        "",
        "| Resource | Opening | Delta | Closing |",
        "|----------|---------|-------|---------|",
    ]
    for res in data.get("resources") or []:
        name = res.get("name", "N/A")
        opening = res.get("openingState", res.get("opening", ""))
        delta = res.get("delta", "")
        closing = res.get("closingState", res.get("closing", ""))
        lines.append(f"| {name} | {opening} | {delta} | {closing} |")
    return "\n".join(lines)


def render_subplot_board(data: dict) -> str:
    """Render subplot board as table matching inkos format."""
    subplots = data.get("subplots") or []
    if not subplots:
        return "# 支线进度板\n\n(暂无支线数据)"

    lines = [
        "| 支线ID | 支线名 | 相关角色 | 起始章 | 最近活跃章 | 状态 | 进度概述 | 回收ETA |",
        "|--------|--------|----------|--------|------------|------|----------|---------|",
    ]
    for sp in subplots:
        sid = sp.get("id", "?")
        name = sp.get("name", "")
        chars = ", ".join(sp.get("involvedCharacters") or [])
        intro = sp.get("introducedInChapter", "?")
        last = sp.get("lastUpdatedChapter", "?")
        status = sp.get("status", "unknown")
        desc = sp.get("description", "")
        resolution = sp.get("expectedResolution", "")
        lines.append(f"| {sid} | {name} | {chars} | {intro} | {last} | {status} | {desc} | {resolution} |")
    return "\n".join(lines)


def render_emotional_arcs(data: dict) -> str:
    """Render emotional arcs as flat table matching inkos format."""
    arcs = data.get("arcs") or []
    if not arcs:
        return "# 情感弧线\n\n(暂无情感弧线数据)"

    lines = [
        "| 角色 | 章节 | 情绪状态 | 触发事件 | 强度(1-10) | 弧线方向 |",
        "|------|------|----------|----------|------------|----------|",
    ]
    for arc in arcs:
        char = arc.get("characterName", arc.get("character", "Unknown"))
        for entry in arc.get("progression", arc.get("timeline", [])) or []:
            chapter = entry.get("chapter", "?")
            emotion = entry.get("emotion", "N/A")
            trigger = entry.get("trigger", entry.get("cause", ""))
            intensity = entry.get("intensity", "N/A")
            pressure = entry.get("pressureShape", "")
            lines.append(f"| {char} | {chapter} | {emotion} | {trigger} | {intensity} | {pressure} |")
    return "\n".join(lines)


def render_unknown(data) -> str:
    lines = [
        "# Unknown Truth File",
        "",
        "```json",
        json.dumps(data, indent=2, ensure_ascii=False),
        "```",
    ]
    return "\n".join(lines)


RENDERERS = {
    "world_state.json": render_world_state,
    "character_matrix.json": render_character_matrix,
    "resource_ledger.json": render_resource_ledger,
    "chapter_summaries.json": render_chapter_summaries,
    "subplot_board.json": render_subplot_board,
    "emotional_arcs.json": render_emotional_arcs,
    "pending_hooks.json": render_pending_hooks,
    "current_state.json": render_current_state,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a truth JSON file to human-readable markdown."
    )
    parser.add_argument("json_file", metavar="json-file", help="Input JSON file path")
    parser.add_argument("output_md", metavar="output-md", help="Output markdown file path")
    args = parser.parse_args()

    json_path = Path(args.json_file)
    output_path = Path(args.output_md)

    if not json_path.is_file():
        print(f"Error: JSON file not found: {json_path}", file=sys.stderr)
        return 1

    data = read_json(str(json_path))
    if data is None:
        print(f"Error: Invalid JSON in file: {json_path}", file=sys.stderr)
        return 1

    basename = json_path.name
    renderer = RENDERERS.get(basename, render_unknown)
    content = renderer(data)

    # Atomic write via temp file in same directory
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=str(output_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.write("\n")
        os.replace(tmp_path, str(output_path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
