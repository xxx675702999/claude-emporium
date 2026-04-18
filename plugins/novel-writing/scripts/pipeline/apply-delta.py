#!/usr/bin/env python3
"""apply-delta.py — Apply a RuntimeStateDelta to truth files.

Port of InkOS core's applyRuntimeStateDelta() + buildRuntimeStateArtifacts().

Flow:
  1. Load current truth file JSONs (snapshot)
  2. Apply hookOps (upsert/mention/resolve/defer + new hook candidates)
  3. Apply currentStatePatch (replace matching predicates)
  4. Apply chapterSummary (append/replace summary row)
  5. Apply subplotOps (add/update/resolve subplots)
  6. Apply emotionalArcOps (add/update character emotional arcs)
  7. Apply characterMatrixOps (add/update character matrix entries)
  8. Apply resourceLedgerOps (snapshot resource state changes)
  9. Update manifest.lastAppliedChapter
  10. Validate updated truth files
  11. Write JSON + regenerate markdown projections

Usage:
  python3 apply-delta.py <book-dir> <delta-file>
  python3 apply-delta.py <book-dir> <delta-file> --dry-run
  python3 apply-delta.py <book-dir> <delta-file> --skip-validation

Exit codes:
  0 — success
  1 — error (invalid delta, validation failure, etc.)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = SCRIPT_DIR.parent.parent

sys.path.insert(0, str(SCRIPT_DIR.parent))
from lib.json_utils import read_json, write_json
from lib.chapter_utils import find_chapter_file
from lib.pipeline_errors import (
    HookIdFormatError,
    HookStatusEnumError,
    ResourceLedgerFieldError,
    PredicateAliasError,
    DeltaValidationError,
)

# ---------------------------------------------------------------------------
# Valid enums (must match schemas)
# ---------------------------------------------------------------------------

VALID_HOOK_STATUSES = {"open", "progressing", "escalating", "critical", "deferred", "resolved"}
VALID_PAYOFF_TIMINGS = {"immediate", "near-term", "mid-arc", "slow-burn", "endgame"}
HOOK_ID_RE = re.compile(r"^H\d+(_\d+)?$")


# ---------------------------------------------------------------------------
# Hook operations — port of InkOS state-reducer.ts applyHookOps()
# ---------------------------------------------------------------------------

def apply_hook_ops(hooks_list: list, delta: dict, chapter: int) -> list:
    """Apply hookOps to hooks list. Returns updated list."""
    hook_ops = delta.get("hookOps")
    if not hook_ops or not isinstance(hook_ops, dict):
        return hooks_list

    hooks_map: dict[str, dict] = {h["hookId"]: h for h in hooks_list if "hookId" in h}

    # 1. Upsert: add or replace hooks
    for record in hook_ops.get("upsert") or []:
        if not isinstance(record, dict):
            continue
        hid = record.get("hookId")
        if not hid:
            continue
        if not HOOK_ID_RE.match(hid):
            raise HookIdFormatError(
                f"Illegal hookId {hid!r} in hookOps.upsert. "
                f"Expected format ^H\\d+(_\\d+)?$. "
                f"To introduce a new hook, use delta.newHookCandidates, not upsert."
            )
        # Enforce status enum (fail-fast)
        status = record.get("status")
        if status is None or status == "":
            raise HookStatusEnumError(
                f"hookId={hid} has no status. "
                f"Expected one of {sorted(VALID_HOOK_STATUSES)}."
            )
        if status not in VALID_HOOK_STATUSES:
            raise HookStatusEnumError(
                f"hookId={hid} has invalid status={status!r}. "
                f"Expected one of {sorted(VALID_HOOK_STATUSES)}."
            )
        record["status"] = status
        # Ensure lastAdvancedChapter is current
        record["lastAdvancedChapter"] = max(
            record.get("lastAdvancedChapter", 0), chapter
        )
        hooks_map[hid] = record

    # 2. Mention: update lastAdvancedChapter only
    for hid in hook_ops.get("mention") or []:
        if not isinstance(hid, str):
            continue
        if not HOOK_ID_RE.match(hid):
            raise HookIdFormatError(
                f"Illegal hookId {hid!r} in hookOps.mention."
            )
        if hid in hooks_map:
            hooks_map[hid]["lastAdvancedChapter"] = max(
                hooks_map[hid].get("lastAdvancedChapter", 0), chapter
            )

    # 3. Resolve: mark as resolved (handle both string and object formats)
    for item in hook_ops.get("resolve") or []:
        hid = item if isinstance(item, str) else item.get("hookId", "") if isinstance(item, dict) else ""
        if not hid:
            continue
        if not HOOK_ID_RE.match(hid):
            raise HookIdFormatError(
                f"Illegal hookId {hid!r} in hookOps.resolve."
            )
        if hid in hooks_map:
            hooks_map[hid]["status"] = "resolved"
            hooks_map[hid]["lastAdvancedChapter"] = max(
                hooks_map[hid].get("lastAdvancedChapter", 0), chapter
            )

    # 4. Defer: mark as deferred
    for hid in hook_ops.get("defer") or []:
        if not isinstance(hid, str):
            continue
        if not HOOK_ID_RE.match(hid):
            raise HookIdFormatError(
                f"Illegal hookId {hid!r} in hookOps.defer."
            )
        if hid in hooks_map:
            hooks_map[hid]["status"] = "deferred"
            hooks_map[hid]["lastAdvancedChapter"] = max(
                hooks_map[hid].get("lastAdvancedChapter", 0), chapter
            )

    # 5. New hook candidates: add with generated ID
    for candidate in delta.get("newHookCandidates") or []:
        if not isinstance(candidate, dict):
            continue
        htype = candidate.get("type", "")
        notes = candidate.get("notes", "")
        if not htype and not notes:
            continue  # reject empty candidates

        # Generate hook ID: H{chapter}_{sequence}
        existing_ids = set(hooks_map.keys())
        seq = 1
        while f"H{chapter}_{seq}" in existing_ids:
            seq += 1
        hid = f"H{chapter}_{seq}"

        hooks_map[hid] = {
            "hookId": hid,
            "startChapter": chapter,
            "type": htype,
            "status": "open",
            "lastAdvancedChapter": chapter,
            "expectedPayoff": candidate.get("expectedPayoff", ""),
            "payoffTiming": candidate.get("payoffTiming", "near-term"),
            "notes": notes,
        }

    # Sort by (startChapter, lastAdvancedChapter, hookId)
    result = sorted(
        hooks_map.values(),
        key=lambda h: (h.get("startChapter", 0), h.get("lastAdvancedChapter", 0), h.get("hookId", "")),
    )
    return result


# ---------------------------------------------------------------------------
# Current state patch — port of InkOS state-reducer.ts applyCurrentStatePatch()
# ---------------------------------------------------------------------------

# Predicate alias map (zh → canonical field name)
PREDICATE_ALIASES = {
    "当前位置": "currentLocation",
    "主角状态": "protagonistState",
    "当前目标": "currentGoal",
    "当前限制": "currentConstraint",
    "当前敌我": "currentAlliances",
    "当前冲突": "currentConflict",
}


def apply_current_state_patch(state_data: dict, delta: dict, chapter: int) -> dict:
    """Apply currentStatePatch to current_state facts."""
    patch = delta.get("currentStatePatch")
    if not patch or not isinstance(patch, dict):
        return state_data

    state_data["chapter"] = chapter
    facts = state_data.get("facts", [])

    for field, value in patch.items():
        if not value:
            continue
        canonical = PREDICATE_ALIASES.get(field, field)

        # Invalidate old fact with same predicate
        for fact in facts:
            pred = fact.get("predicate", "")
            canonical_pred = PREDICATE_ALIASES.get(pred, pred)
            if canonical_pred == canonical and fact.get("validUntilChapter") is None:
                fact["validUntilChapter"] = chapter

        # Add new fact
        facts.append({
            "subject": "Protagonist",
            "predicate": canonical,
            "object": str(value),
            "validFromChapter": chapter,
            "validUntilChapter": None,
            "sourceChapter": chapter,
        })

    state_data["facts"] = facts
    return state_data


# ---------------------------------------------------------------------------
# Chapter summary — port of InkOS state-reducer.ts applySummaryDelta()
# ---------------------------------------------------------------------------

def apply_chapter_summary(summaries_data: dict, delta: dict) -> dict:
    """Add or replace chapter summary row."""
    cs = delta.get("chapterSummary")
    if not cs or not isinstance(cs, dict):
        return summaries_data

    ch_num = cs.get("chapter")
    if not ch_num:
        return summaries_data

    chapters = summaries_data.get("chapters", [])

    # Remove existing entry for this chapter (allow reapply)
    chapters = [c for c in chapters if c.get("chapter") != ch_num]

    chapters.append({
        "chapter": ch_num,
        "title": cs.get("title", ""),
        "characters": cs.get("characters", ""),
        "events": cs.get("events", ""),
        "stateChanges": cs.get("stateChanges", ""),
        "hookActivity": cs.get("hookActivity", ""),
        "mood": cs.get("mood", ""),
        "chapterType": cs.get("chapterType", ""),
    })

    chapters.sort(key=lambda c: c.get("chapter", 0))
    summaries_data["chapters"] = chapters
    return summaries_data


# ---------------------------------------------------------------------------
# Subplot operations
# ---------------------------------------------------------------------------

def apply_subplot_ops(data: dict, delta: dict, chapter: int) -> dict:
    """Apply subplotOps to subplot board. Returns updated data."""
    ops = delta.get("subplotOps")
    if not ops or not isinstance(ops, list):
        return data

    subplots_map: dict[str, dict] = {s["id"]: s for s in data.get("subplots", []) if "id" in s}

    for op_entry in ops:
        if not isinstance(op_entry, dict):
            continue
        op = op_entry.get("op")
        sid = op_entry.get("id")
        if not op or not sid:
            print(f"  [WARN] Skipping malformed subplotOp (missing id or op): {op_entry}", file=sys.stderr)
            continue

        if op == "add":
            subplots_map[sid] = {
                "id": sid,
                "name": op_entry.get("name", ""),
                "status": op_entry.get("status", "active"),
                "description": op_entry.get("description", ""),
                "involvedCharacters": op_entry.get("involvedCharacters", []),
                "introducedInChapter": chapter,
                "lastUpdatedChapter": chapter,
                "expectedResolution": op_entry.get("expectedResolution", ""),
                "notes": op_entry.get("notes", ""),
            }
        elif op == "update":
            if sid not in subplots_map:
                # Upsert: create entry if not found (handles empty-bootstrap case)
                subplots_map[sid] = {
                    "id": sid,
                    "name": op_entry.get("name", "") or sid,
                    "status": op_entry.get("status", "active"),
                    "description": "",
                    "involvedCharacters": [],
                    "introducedInChapter": chapter,
                    "lastUpdatedChapter": chapter,
                    "expectedResolution": "",
                    "notes": "",
                }
            for key in ("name", "status", "description", "involvedCharacters", "expectedResolution", "notes"):
                if key in op_entry:
                    subplots_map[sid][key] = op_entry[key]
            subplots_map[sid]["lastUpdatedChapter"] = chapter
        elif op == "resolve":
            if sid in subplots_map:
                subplots_map[sid]["status"] = "resolved"
                subplots_map[sid]["lastUpdatedChapter"] = chapter
            else:
                print(f"  [WARN] subplotOp resolve: id '{sid}' not found, skipping", file=sys.stderr)

    data["subplots"] = list(subplots_map.values())
    return data


# ---------------------------------------------------------------------------
# Emotional arc operations
# ---------------------------------------------------------------------------

def apply_emotional_arc_ops(data: dict, delta: dict, chapter: int) -> dict:
    """Apply emotionalArcOps to emotional arcs. Returns updated data."""
    ops = delta.get("emotionalArcOps")
    if not ops or not isinstance(ops, list):
        return data

    arcs_map: dict[str, dict] = {a["characterId"]: a for a in data.get("arcs", []) if "characterId" in a}

    for op_entry in ops:
        if not isinstance(op_entry, dict):
            continue
        op = op_entry.get("op")
        cid = op_entry.get("characterId")
        if not cid:
            print(f"  [WARN] Skipping malformed emotionalArcOp (missing characterId): {op_entry}", file=sys.stderr)
            continue

        # Extract timeline entries from delta op.
        # Format A (writer puts fields at top level): {op, characterId, emotion, intensity, ...}
        # Format B (writer puts fields inside "progression" array): {op, characterId, progression: [{...}]}
        # Also map "cause" → "trigger" for backward compat.
        raw_entries = op_entry.get("progression", [])
        if not raw_entries:
            # Format A: build a single entry from top-level fields
            raw_entries = [{
                "emotion": op_entry.get("emotion", ""),
                "intensity": op_entry.get("intensity", 0),
                "pressureShape": op_entry.get("pressureShape", ""),
                "cause": op_entry.get("cause", ""),
                "notes": op_entry.get("notes", ""),
            }]

        for raw in raw_entries:
            if not isinstance(raw, dict):
                continue
            timeline_entry = {
                "chapter": chapter,
                "emotion": raw.get("emotion", ""),
                "intensity": raw.get("intensity", 0),
                "pressureShape": raw.get("pressureShape", ""),
                "trigger": raw.get("cause", "") or raw.get("trigger", ""),
                "notes": raw.get("notes", ""),
            }

            if op in ("add", "update"):
                if cid in arcs_map:
                    arcs_map[cid]["progression"].append(timeline_entry)
                else:
                    # Implicit add if arc doesn't exist
                    arcs_map[cid] = {
                        "characterId": cid,
                        "characterName": op_entry.get("characterName", "") or cid,
                        "progression": [timeline_entry],
                    }

    data["arcs"] = list(arcs_map.values())
    return data


# ---------------------------------------------------------------------------
# Character matrix operations
# ---------------------------------------------------------------------------

def apply_character_matrix_ops(data: dict, delta: dict, chapter: int) -> dict:
    """Apply characterMatrixOps to character matrix. Returns updated data."""
    ops = delta.get("characterMatrixOps")
    if not ops or not isinstance(ops, list):
        return data

    chars_map: dict[str, dict] = {c["id"]: c for c in data.get("characters", []) if "id" in c}

    for op_entry in ops:
        if not isinstance(op_entry, dict):
            continue
        op = op_entry.get("op")
        cid = op_entry.get("id")
        if not cid:
            print(f"  [WARN] Skipping malformed characterMatrixOp (missing id): {op_entry}", file=sys.stderr)
            continue

        if op == "add":
            # Map relationship fields: delta {targetId, type, description} → schema {targetCharacterId, relationship, status, notes}
            relationships = []
            for rel in op_entry.get("relationshipChanges", []):
                relationships.append({
                    "targetCharacterId": rel.get("targetId", ""),
                    "relationship": rel.get("type", ""),
                    "status": "active",
                    "notes": rel.get("description", ""),
                })

            chars_map[cid] = {
                "id": cid,
                "name": op_entry.get("name", ""),
                "status": op_entry.get("status", "active"),
                "introducedInChapter": chapter,
                "lastAppearedInChapter": chapter,
                "abilities": op_entry.get("newAbilities", []),
                "relationships": relationships,
            }
        elif op == "update":
            if cid not in chars_map:
                # Upsert: create entry if not found (handles empty-bootstrap case)
                chars_map[cid] = {
                    "id": cid,
                    "name": op_entry.get("name", "") or cid,
                    "status": op_entry.get("status", "active"),
                    "introducedInChapter": chapter,
                    "lastAppearedInChapter": chapter,
                    "abilities": [],
                    "relationships": [],
                }

            char = chars_map[cid]
            char["lastAppearedInChapter"] = chapter

            if "status" in op_entry:
                char["status"] = op_entry["status"]
            if "name" in op_entry:
                char["name"] = op_entry["name"]

            # Append new abilities (dedup)
            if "newAbilities" in op_entry:
                existing = set(char.get("abilities", []))
                for ability in op_entry["newAbilities"]:
                    if ability not in existing:
                        char.setdefault("abilities", []).append(ability)
                        existing.add(ability)

            # Append/update relationships (match by targetCharacterId)
            if "relationshipChanges" in op_entry:
                rels = char.get("relationships", [])
                rels_map: dict[str, dict] = {r["targetCharacterId"]: r for r in rels if "targetCharacterId" in r}
                for rel in op_entry["relationshipChanges"]:
                    tid = rel.get("targetId", "")
                    if tid in rels_map:
                        rels_map[tid]["relationship"] = rel.get("type", rels_map[tid].get("relationship", ""))
                        rels_map[tid]["notes"] = rel.get("description", rels_map[tid].get("notes", ""))
                    else:
                        rels_map[tid] = {
                            "targetCharacterId": tid,
                            "relationship": rel.get("type", ""),
                            "status": "active",
                            "notes": rel.get("description", ""),
                        }
                char["relationships"] = list(rels_map.values())

    data["characters"] = list(chars_map.values())
    return data


# ---------------------------------------------------------------------------
# Resource ledger operations
# ---------------------------------------------------------------------------

REQUIRED_LEDGER_FIELDS = (
    "op", "id", "name", "type", "owner",
    "openingState", "closingState", "delta",
)


def apply_resource_ledger_ops(data: dict, delta: dict, chapter: int) -> dict:
    """Apply resourceLedgerOps to resource ledger. Returns updated data.

    Raises ResourceLedgerFieldError on any missing/empty required field or
    invalid `op` value. See pipeline_errors.py.
    """
    ops = delta.get("resourceLedgerOps")
    if not ops or not isinstance(ops, list):
        return data

    resources = data.get("resources", [])

    for op_entry in ops:
        if not isinstance(op_entry, dict):
            raise ResourceLedgerFieldError(
                f"resourceLedgerOp must be dict, got {type(op_entry).__name__}"
            )

        missing = [k for k in REQUIRED_LEDGER_FIELDS if not op_entry.get(k)]
        if missing:
            raise ResourceLedgerFieldError(
                f"resourceLedgerOp missing required fields {missing}: "
                f"id={op_entry.get('id')!r}"
            )

        if op_entry["op"] != "snapshot":
            raise ResourceLedgerFieldError(
                f"resourceLedgerOp.op must be 'snapshot', got {op_entry['op']!r}"
            )

        resources.append({
            "id": op_entry["id"],
            "name": op_entry["name"],
            "type": op_entry["type"],
            "owner": op_entry["owner"],
            "chapter": chapter,
            "openingState": op_entry["openingState"],
            "closingState": op_entry["closingState"],
            "delta": op_entry["delta"],
            "source": op_entry.get("source", ""),
            "notes": op_entry.get("notes", ""),
        })

    data["resources"] = resources
    return data


# ---------------------------------------------------------------------------
# Markdown projection regeneration
# ---------------------------------------------------------------------------

def regenerate_projections(book_dir: Path, state_dir: Path, story_dir: Path) -> list[str]:
    """Regenerate markdown projections from JSON state files."""
    render_script = PLUGIN_DIR / "scripts" / "pipeline" / "markdown-render.py"
    rendered = []

    pairs = [
        (state_dir / "chapter_summaries.json", story_dir / "chapter_summaries.md"),
        (state_dir / "pending_hooks.json", story_dir / "pending_hooks.md"),
        (state_dir / "current_state.json", story_dir / "current_state.md"),
        (state_dir / "subplot_board.json", story_dir / "subplot_board.md"),
        (state_dir / "emotional_arcs.json", story_dir / "emotional_arcs.md"),
        (state_dir / "character_matrix.json", story_dir / "character_matrix.md"),
        (state_dir / "resource_ledger.json", story_dir / "resource_ledger.md"),
    ]

    for json_file, md_file in pairs:
        if json_file.is_file():
            result = subprocess.run(
                [sys.executable, str(render_script), str(json_file), str(md_file)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                rendered.append(md_file.name)
            else:
                print(f"  [WARN] Failed to render {md_file.name}: {result.stderr.strip()}", file=sys.stderr)

    return rendered


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_truth_files(state_dir: Path) -> list[str]:
    """Validate truth files using schema-validate.py. Returns list of errors."""
    validate_script = PLUGIN_DIR / "scripts" / "pipeline" / "schema-validate.py"
    files = [
        state_dir / "chapter_summaries.json",
        state_dir / "current_state.json",
        state_dir / "pending_hooks.json",
        state_dir / "subplot_board.json",
        state_dir / "emotional_arcs.json",
        state_dir / "character_matrix.json",
        state_dir / "resource_ledger.json",
    ]
    existing = [str(f) for f in files if f.is_file()]
    if not existing:
        return []

    result = subprocess.run(
        [sys.executable, str(validate_script)] + existing,
        capture_output=True, text=True, timeout=30,
    )

    errors = []
    try:
        reports = json.loads(result.stdout)
        for report in reports:
            if not report.get("valid"):
                fname = Path(report["file"]).name
                for err in report.get("errors", []):
                    errors.append(f"{fname}: {err}")
    except (json.JSONDecodeError, KeyError):
        if result.returncode != 0:
            errors.append(f"Validation script failed: {result.stderr.strip()}")

    return errors


# ---------------------------------------------------------------------------
# Chapter-meta update
# ---------------------------------------------------------------------------

def _count_words(text: str, language: str) -> int:
    """Simple word/character count without external script dependency."""
    if language == "zh":
        import re as _re
        return len(_re.findall(r"[\u4e00-\u9fff]", text))
    return len(text.split())


def update_chapter_meta(book_dir: Path, delta: dict, chapter: int) -> None:
    """Create or update chapter-meta.json with this chapter's record.

    Called automatically after truth file persist. Sets status to 'auditing'
    (the pipeline will update to audit-passed/audit-failed after audit completes).
    """
    from datetime import datetime, timezone

    state_dir = book_dir / "story" / "state"
    meta_path = state_dir / "chapter-meta.json"

    # Load or create
    meta = read_json(str(meta_path)) or {
        "schemaVersion": 1,
        "lastUpdated": "",
        "chapters": [],
    }
    meta.setdefault("schemaVersion", 1)
    meta.setdefault("chapters", [])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Get chapter title from delta
    summary = delta.get("chapterSummary") or {}
    title = summary.get("title", f"Chapter {chapter}")

    # Get word count from chapter file
    word_count = 0
    chapters_dir = str(book_dir / "chapters")
    chapter_file = find_chapter_file(chapters_dir, chapter)
    if chapter_file:
        try:
            with open(chapter_file, encoding="utf-8") as f:
                content = f.read()
            # Detect language from book.json
            book_json = read_json(str(book_dir / "book.json")) or {}
            lang = book_json.get("language", "zh")
            word_count = _count_words(content, lang)
        except OSError:
            pass

    # Find existing record or create new
    chapters = meta["chapters"]
    existing = next((c for c in chapters if c.get("number") == chapter), None)

    if existing:
        # Update existing record
        existing["title"] = title
        existing["wordCount"] = word_count
        existing["status"] = "auditing"
        existing["updatedAt"] = now
    else:
        # Create new record
        chapters.append({
            "number": chapter,
            "title": title,
            "status": "auditing",
            "wordCount": word_count,
            "createdAt": now,
            "updatedAt": now,
            "revisionCount": 0,
        })

    # Sort by chapter number
    chapters.sort(key=lambda c: c.get("number", 0))
    meta["chapters"] = chapters
    meta["lastUpdated"] = now

    write_json(str(meta_path), meta)
    print(f"  [CHAPTER-META] ch{chapter}: '{title}' ({word_count} words) → auditing")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply a RuntimeStateDelta to truth files."
    )
    parser.add_argument("book_dir", help="Book directory path")
    parser.add_argument("delta_file", help="Delta JSON file path")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--skip-validation", action="store_true", help="Skip post-apply validation")
    args = parser.parse_args()

    book_dir = Path(args.book_dir)
    delta_path = Path(args.delta_file)
    state_dir = book_dir / "story" / "state"
    story_dir = book_dir / "story"

    # Load delta
    if not delta_path.is_file():
        print(f"Error: delta file not found: {delta_path}", file=sys.stderr)
        return 1

    try:
        with open(delta_path, encoding="utf-8") as f:
            delta = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in delta: {e}", file=sys.stderr)
        return 1

    chapter = delta.get("chapter")
    if not isinstance(chapter, int) or chapter < 1:
        print(f"Error: invalid chapter number in delta: {delta.get('chapter')}", file=sys.stderr)
        return 1

    print(f"Applying delta for chapter {chapter}...")

    # Load current truth files
    summaries = read_json(str(state_dir / "chapter_summaries.json")) or {"version": 1, "chapters": []}
    current_state = read_json(str(state_dir / "current_state.json")) or {"version": 1, "chapter": 0, "facts": []}
    hooks_data = read_json(str(state_dir / "pending_hooks.json")) or {"version": 1, "hooks": []}
    manifest = read_json(str(state_dir / "manifest.json")) or {"schemaVersion": 1, "lastAppliedChapter": 0, "projectionVersion": 1}
    subplot_board = read_json(str(state_dir / "subplot_board.json")) or {"version": 1, "subplots": []}
    emotional_arcs = read_json(str(state_dir / "emotional_arcs.json")) or {"version": 1, "arcs": []}
    character_matrix = read_json(str(state_dir / "character_matrix.json")) or {"version": 1, "characters": []}
    resource_ledger = read_json(str(state_dir / "resource_ledger.json")) or {"version": 1, "resources": []}

    # Check ordering
    last_applied = manifest.get("lastAppliedChapter", 0)
    if chapter <= last_applied:
        print(f"  [WARN] Delta chapter {chapter} <= manifest.lastAppliedChapter {last_applied}. Reapplying.")

    try:
        # Apply operations
        changes = []

        # 1. Hook operations
        old_hook_count = len(hooks_data.get("hooks", []))
        hooks_data["hooks"] = apply_hook_ops(hooks_data.get("hooks", []), delta, chapter)
        new_hook_count = len(hooks_data["hooks"])
        resolved = [item if isinstance(item, str) else item.get("hookId", "") for item in (delta.get("hookOps", {}).get("resolve") or [])]
        upserted = [h.get("hookId", "") for h in (delta.get("hookOps", {}).get("upsert") or [])]
        new_candidates = len(delta.get("newHookCandidates") or [])
        changes.append(f"hooks: {old_hook_count}→{new_hook_count} (upsert:{len(upserted)}, resolve:{len(resolved)}, new:{new_candidates})")

        # 2. Current state patch
        old_chapter = current_state.get("chapter", 0)
        current_state = apply_current_state_patch(current_state, delta, chapter)
        patch_fields = list((delta.get("currentStatePatch") or {}).keys())
        if patch_fields:
            changes.append(f"state: ch{old_chapter}→ch{chapter} ({len(patch_fields)} fields)")

        # 3. Chapter summary
        old_summary_count = len(summaries.get("chapters", []))
        summaries = apply_chapter_summary(summaries, delta)
        new_summary_count = len(summaries.get("chapters", []))
        if new_summary_count > old_summary_count:
            changes.append(f"summaries: {old_summary_count}→{new_summary_count}")
        elif new_summary_count == old_summary_count:
            changes.append(f"summaries: updated ch{chapter}")

        # 4. Subplot operations
        old_subplot_count = len(subplot_board.get("subplots", []))
        subplot_board = apply_subplot_ops(subplot_board, delta, chapter)
        new_subplot_count = len(subplot_board.get("subplots", []))
        subplot_ops = delta.get("subplotOps") or []
        if subplot_ops:
            changes.append(f"subplots: {old_subplot_count}→{new_subplot_count} ({len(subplot_ops)} ops)")

        # 5. Emotional arc operations
        old_arc_count = len(emotional_arcs.get("arcs", []))
        emotional_arcs = apply_emotional_arc_ops(emotional_arcs, delta, chapter)
        new_arc_count = len(emotional_arcs.get("arcs", []))
        arc_ops = delta.get("emotionalArcOps") or []
        if arc_ops:
            changes.append(f"arcs: {old_arc_count}→{new_arc_count} ({len(arc_ops)} ops)")

        # 6. Character matrix operations
        old_char_count = len(character_matrix.get("characters", []))
        character_matrix = apply_character_matrix_ops(character_matrix, delta, chapter)
        new_char_count = len(character_matrix.get("characters", []))
        char_ops = delta.get("characterMatrixOps") or []
        if char_ops:
            changes.append(f"characters: {old_char_count}→{new_char_count} ({len(char_ops)} ops)")

        # 7. Resource ledger operations
        old_res_count = len(resource_ledger.get("resources", []))
        resource_ledger = apply_resource_ledger_ops(resource_ledger, delta, chapter)
        new_res_count = len(resource_ledger.get("resources", []))
        res_ops = delta.get("resourceLedgerOps") or []
        if res_ops:
            changes.append(f"resources: {old_res_count}→{new_res_count} ({len(res_ops)} ops)")

        # 8. Update manifest
        manifest["lastAppliedChapter"] = max(manifest.get("lastAppliedChapter", 0), chapter)
        changes.append(f"manifest: lastAppliedChapter={manifest['lastAppliedChapter']}")

        # Ensure version fields
        summaries.setdefault("version", 1)
        current_state.setdefault("version", 1)
        hooks_data.setdefault("version", 1)
        subplot_board.setdefault("version", 1)
        emotional_arcs.setdefault("version", 1)
        character_matrix.setdefault("version", 1)
        resource_ledger.setdefault("version", 1)

        # Report changes
        for change in changes:
            print(f"  {change}")

        if args.dry_run:
            print("\n[DRY RUN] No files written.")
            return 0

        # Write JSON files
        write_json(str(state_dir / "chapter_summaries.json"), summaries)
        write_json(str(state_dir / "current_state.json"), current_state)
        write_json(str(state_dir / "pending_hooks.json"), hooks_data)
        write_json(str(state_dir / "manifest.json"), manifest)
        write_json(str(state_dir / "subplot_board.json"), subplot_board)
        write_json(str(state_dir / "emotional_arcs.json"), emotional_arcs)
        write_json(str(state_dir / "character_matrix.json"), character_matrix)
        # Only write resource_ledger if it has data (TD-4)
        if resource_ledger.get("resources"):
            write_json(str(state_dir / "resource_ledger.json"), resource_ledger)

        # Validate
        if not args.skip_validation:
            errors = validate_truth_files(state_dir)
            if errors:
                print(f"\n  [VALIDATION] {len(errors)} issues:")
                for err in errors[:10]:
                    print(f"    {err}")
                # Don't fail — validation issues may be pre-existing
            else:
                print("  [VALIDATION] All truth files valid")

        # Regenerate markdown projections
        rendered = regenerate_projections(book_dir, state_dir, story_dir)
        if rendered:
            print(f"  [RENDER] Regenerated: {', '.join(rendered)}")

        # Update chapter-meta.json (auto-create if missing)
        update_chapter_meta(book_dir, delta, chapter)

        # Snapshot truth files for rollback capability
        snapshot_result = subprocess.run(
            [sys.executable, str(PLUGIN_DIR / "scripts" / "pipeline" / "state-manager.py"),
             "snapshot", str(book_dir), str(chapter)],
            capture_output=True, text=True, timeout=30,
        )
        if snapshot_result.returncode == 0:
            print(f"  [SNAPSHOT] Created for chapter {chapter}")
        else:
            print(f"  [SNAPSHOT] Warning: {snapshot_result.stderr.strip()}", file=sys.stderr)

        # Cleanup old snapshots (keep last 10 + one per 10-chapter interval)
        subprocess.run(
            [sys.executable, str(PLUGIN_DIR / "scripts" / "pipeline" / "state-manager.py"),
             "snapshot-cleanup", str(book_dir), str(chapter)],
            capture_output=True, text=True, timeout=30,
        )

        # Prune old runtime files (keep current + 2 previous, delta never deleted)
        subprocess.run(
            [sys.executable, str(PLUGIN_DIR / "scripts" / "pipeline" / "runtime-prune.py"),
             str(book_dir), str(chapter)],
            capture_output=True, text=True, timeout=30,
        )

        # Sync MemoryDB so preparer can query fresh data next chapter
        sync_result = subprocess.run(
            [sys.executable, str(PLUGIN_DIR / "scripts" / "pipeline" / "memory-db.py"),
             "sync", str(book_dir)],
            capture_output=True, text=True, timeout=30,
        )
        if sync_result.returncode == 0:
            print(f"  [MEMORYDB] Synced")
        else:
            # Non-fatal — preparer falls back to file reads
            print(f"  [MEMORYDB] Sync skipped: {sync_result.stderr.strip()[:80]}", file=sys.stderr)

        # Auto-generate current_focus.md for next chapter
        focus_result = subprocess.run(
            [sys.executable, str(PLUGIN_DIR / "scripts" / "pipeline" / "generate-focus.py"),
             str(book_dir)],
            capture_output=True, text=True, timeout=30,
        )
        if focus_result.returncode == 0:
            print(f"  [FOCUS] Generated current_focus.md for ch{chapter + 1}")
        else:
            print(f"  [FOCUS] Skipped: {focus_result.stderr.strip()[:80]}", file=sys.stderr)

        print(f"\nDelta for chapter {chapter} applied successfully.")
        return 0
    except DeltaValidationError as e:
        print(f"\n[{type(e).__name__}] {e}", file=sys.stderr)
        print(
            "  Hint: delta.json breached a hardened contract. "
            "See docs/specs/2026-04-18-subsystem-1-persist-contracts-design.md. "
            "If running in the pipeline, state-manager.py recovery should trigger.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
