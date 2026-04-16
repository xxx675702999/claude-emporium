#!/usr/bin/env python3
"""state-manager.py — State lifecycle manager for novel-writing truth files.

Three capabilities:
  1. Bootstrap (MD→JSON): Parse markdown projections back to JSON when truth
     file JSONs are missing.
  2. Recovery: Auto-retry settlement once after validation failure; mark
     chapter `state-degraded` on second failure.
  3. Snapshots: Copy truth file JSONs to per-chapter snapshot directories
     after each persist, with auto-cleanup (keep last 10 + one per
     10-chapter interval) and MemoryDB valid_until_chapter updates.

Usage:
  state-manager.py bootstrap <book-dir>
  state-manager.py snapshot <book-dir> <chapter>
  state-manager.py snapshot-cleanup <book-dir> <current-chapter>
  state-manager.py recovery <book-dir> <chapter> [validation-errors-json]

Exit codes:
  0 — success
  1 — error (see stderr for details)
"""

import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared lib import
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.json_utils import read_json, write_json

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent

TRUTH_FILES = [
    "manifest.json",
    "current_state.json",
    "pending_hooks.json",
    "chapter_summaries.json",
    "chapter-meta.json",
    "subplot_board.json",
    "emotional_arcs.json",
    "character_matrix.json",
    "resource_ledger.json",
]

MD_PROJECTIONS: dict[str, str] = {
    "current_state.json": "current_state.md",
    "pending_hooks.json": "pending_hooks.md",
    "chapter_summaries.json": "chapter_summaries.md",
    "subplot_board.json": "subplot_board.md",
    "emotional_arcs.json": "emotional_arcs.md",
    "character_matrix.json": "character_matrix.md",
    "resource_ledger.json": "resource_ledger.md",
}

KEEP_RECENT_COUNT = 10
INTERVAL_SIZE = 10
STATE_DEGRADED = "state-degraded"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    print(f"[state-manager] {msg}", file=sys.stderr)


def exit_with_error(msg: str) -> None:
    log(f"ERROR: {msg}")
    sys.exit(1)


def pad_chapter(n: int) -> str:
    return str(n).zfill(4)


def validate_truth_files(files: list[str]) -> tuple[bool, list[str]]:
    """Run schema-validate.py and return (valid, errors)."""
    existing = [f for f in files if Path(f).exists()]
    if not existing:
        return True, []

    schema_validate = str(SCRIPT_DIR / "schema-validate.py")
    result = subprocess.run(
        ["python3", schema_validate] + existing,
        capture_output=True,
        text=True,
    )

    # schema-validate.py exits 1 on validation failure; output is JSON on stdout
    raw = result.stdout.strip()
    all_errors: list[str] = []

    if raw:
        try:
            parsed = json.loads(raw)
            for entry in parsed:
                if not entry.get("valid", True):
                    all_errors.extend(entry.get("errors", []))
        except (json.JSONDecodeError, TypeError, AttributeError):
            all_errors.append("Failed to parse validation output")
    elif result.returncode != 0:
        stderr = result.stderr.strip()
        all_errors.append(stderr if stderr else "Validation command failed")

    return len(all_errors) == 0, all_errors


# ---------------------------------------------------------------------------
# 1. Bootstrap: MD → JSON
# ---------------------------------------------------------------------------


def parse_markdown_table(md: str) -> list[dict[str, str]]:
    """Parse a markdown table into a list of row dicts keyed by header.

    Handles:
      | col1 | col2 | col3 |
      |------|------|------|
      | val1 | val2 | val3 |
    """
    lines = [l.strip() for l in md.split("\n") if l.strip().startswith("|")]

    if len(lines) < 3:
        return []

    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    # Skip separator line (index 1)
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        row: dict[str, str] = {}
        for j, header in enumerate(headers):
            row[header] = cells[j] if j < len(cells) else ""
        rows.append(row)
    return rows


_HOOK_STATUS_VALID = {"open", "progressing", "escalating", "critical", "deferred", "resolved"}


def _normalize_hook_status(raw: str) -> str:
    """Normalize hook status to schema-valid values.

    escalating/critical are high-priority variants of progressing.
    """
    s = raw.lower().strip()
    if s in _HOOK_STATUS_VALID:
        return s
    return "open"


def _get_value(row: dict[str, str], possible_keys: list[str]) -> str:
    for k in possible_keys:
        if k in row:
            # Strip markdown bold markers (**text** → text)
            val = row[k].strip()
            if val.startswith("**") and val.endswith("**"):
                val = val[2:-2]
            return val
    return ""


def parse_current_state_md(md: str, chapter: int) -> dict:
    """Parse current_state.md → current_state.json structure."""
    rows = parse_markdown_table(md)
    facts = []

    for row in rows:
        keys = list(row.keys())
        if len(keys) < 2:
            continue
        predicate = row[keys[0]]
        obj = row[keys[1]]
        if not predicate or not obj:
            continue
        facts.append({
            "subject": "Protagonist",
            "predicate": predicate,
            "object": obj,
            "validFromChapter": chapter,
            "validUntilChapter": None,
            "sourceChapter": chapter,
        })

    # Also capture bullet-point facts after the table
    lines = md.split("\n")
    # Find the last table line index
    last_table_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("|"):
            last_table_idx = i

    for line in lines[last_table_idx + 1:]:
        match = re.match(r"^- \*\*(.+?)\*\*:\s*(.+)", line.strip())
        if match:
            facts.append({
                "subject": "Protagonist",
                "predicate": match.group(1),
                "object": match.group(2),
                "validFromChapter": chapter,
                "validUntilChapter": None,
                "sourceChapter": chapter,
            })

    return {"version": 1, "chapter": chapter, "facts": facts}


def parse_pending_hooks_md(md: str) -> dict:
    """Parse pending_hooks.md → pending_hooks.json structure."""
    rows = parse_markdown_table(md)

    if rows:
        hooks = []
        for row in rows:
            hook_id = _get_value(row, ["hookId", "Hook ID", "hook_id", "ID"])
            if not hook_id:
                continue
            start_raw = _get_value(row, ["startChapter", "Start Chapter", "start_chapter", "起始章节"])
            last_raw = _get_value(row, ["lastAdvancedChapter", "Last Advanced", "last_advanced_chapter", "最近推进"])
            payoff_timing = _get_value(row, ["payoffTiming", "Payoff Timing", "payoff_timing", "回收节奏"])
            hook: dict = {
                "hookId": hook_id,
                "startChapter": int(start_raw) if start_raw.isdigit() else 0,
                "type": _get_value(row, ["type", "Type", "类型"]),
                "status": _normalize_hook_status(_get_value(row, ["status", "Status", "状态"])),
                "lastAdvancedChapter": int(last_raw) if last_raw.isdigit() else 0,
                "expectedPayoff": _get_value(row, ["expectedPayoff", "Expected Payoff", "expected_payoff", "预期回收"]),
                "notes": _get_value(row, ["notes", "Notes", "备注"]),
            }
            if payoff_timing:
                hook["payoffTiming"] = payoff_timing
            hooks.append(hook)
        return {"version": 1, "hooks": hooks}

    # Fallback: section-based format (## HookId [status])
    hooks = []
    sections = re.split(r"^## ", md, flags=re.MULTILINE)[1:]
    for section in sections:
        header_line = section.split("\n")[0] if section else ""
        header_match = re.match(r"^(.+?)\s*\[(.+?)\]", header_line)
        if not header_match:
            continue

        hook_id = header_match.group(1).strip()
        status = header_match.group(2).strip()

        field_map: dict[str, str] = {}
        for line in section.split("\n")[1:]:
            m = re.match(r"^- \*\*(.+?)\*\*:\s*(.+)", line)
            if m:
                field_map[m.group(1).lower()] = m.group(2).strip()

        intro_raw = field_map.get("introduced", "Chapter 0")
        intro_digits = re.sub(r"\D", "", intro_raw)
        intro_chapter = int(intro_digits) if intro_digits else 0

        hooks.append({
            "hookId": hook_id,
            "startChapter": intro_chapter,
            "type": field_map.get("type", ""),
            "status": status,
            "lastAdvancedChapter": intro_chapter,
            "expectedPayoff": field_map.get("expected resolution", field_map.get("expectedresolution", "")),
            "notes": field_map.get("description", ""),
        })

    return {"version": 1, "hooks": hooks}


def parse_chapter_summaries_md(md: str) -> dict:
    """Parse chapter_summaries.md → chapter_summaries.json structure."""
    rows = parse_markdown_table(md)

    if rows:
        result = []
        for row in rows:
            ch_raw = _get_value(row, ["chapter", "Chapter", "Ch", "章节"])
            ch_int = int(ch_raw) if ch_raw.isdigit() else 0
            if ch_int <= 0:
                continue
            result.append({
                "chapter": ch_int,
                "title": _get_value(row, ["title", "Title", "标题"]),
                "characters": _get_value(row, ["characters", "Characters", "出场人物"]),
                "events": _get_value(row, ["events", "Events", "关键事件"]),
                "stateChanges": _get_value(row, ["stateChanges", "State Changes", "state_changes", "状态变化"]),
                "hookActivity": _get_value(row, ["hookActivity", "Hook Activity", "hook_activity", "伏笔动态"]),
                "mood": _get_value(row, ["mood", "Mood", "情绪基调"]),
                "chapterType": _get_value(row, ["chapterType", "Chapter Type", "chapter_type", "章节类型"]),
            })
        result.sort(key=lambda r: r["chapter"])
        return {"version": 1, "chapters": result}

    # Fallback: section-based format (## Chapter N: Title)
    summaries = []
    sections = re.split(r"^## ", md, flags=re.MULTILINE)[1:]
    for section in sections:
        header_line = section.split("\n")[0] if section else ""
        header_match = re.match(r"^Chapter\s+(\d+):\s*(.+)", header_line, re.IGNORECASE)
        if not header_match:
            continue

        chapter = int(header_match.group(1))
        title = header_match.group(2).strip()

        field_map: dict[str, str] = {}
        for line in section.split("\n")[1:]:
            m = re.match(r"^- \*\*(.+?)\*\*:\s*(.+)", line)
            if m:
                key = m.group(1).lower().replace(" ", "")
                field_map[key] = m.group(2).strip()

        summaries.append({
            "chapter": chapter,
            "title": title,
            "characters": field_map.get("characters", ""),
            "events": field_map.get("events", ""),
            "stateChanges": field_map.get("progression", field_map.get("statechanges", "")),
            "hookActivity": field_map.get("foreshadowing", field_map.get("hookactivity", "")),
            "mood": field_map.get("mood", ""),
            "chapterType": field_map.get("chaptertype", ""),
        })

    summaries.sort(key=lambda r: r["chapter"])
    return {"version": 1, "chapters": summaries}


def determine_chapter_number(state_dir: Path, _md: str) -> int:
    """Determine the current chapter number from manifest."""
    manifest = read_json(str(state_dir / "manifest.json"))
    if isinstance(manifest, dict):
        val = manifest.get("lastAppliedChapter")
        if isinstance(val, int):
            return val
    return 0


def determine_latest_chapter(state_dir: Path) -> int:
    """Determine the latest chapter number from existing truth files."""
    summaries = read_json(str(state_dir / "chapter_summaries.json"))
    if isinstance(summaries, dict):
        rows = summaries.get("chapters", summaries.get("rows", []))
        if rows:
            return max(r["chapter"] for r in rows if isinstance(r.get("chapter"), int))

    current_state = read_json(str(state_dir / "current_state.json"))
    if isinstance(current_state, dict):
        ch = current_state.get("chapter")
        if isinstance(ch, int):
            return ch

    return 0


def bootstrap(book_dir: Path) -> list[str]:
    """Rebuild missing JSON truth files from markdown projections.

    Returns the list of file paths that were bootstrapped.
    """
    story_dir = book_dir / "story"
    state_dir = story_dir / "state"

    if not story_dir.exists():
        exit_with_error(f"Story directory not found: {story_dir}")

    state_dir.mkdir(parents=True, exist_ok=True)
    bootstrapped: list[str] = []

    # Empty defaults for truth files without markdown parsers
    _EMPTY_DEFAULTS: dict[str, dict] = {
        "subplot_board.json": {"version": 1, "subplots": []},
        "emotional_arcs.json": {"version": 1, "arcs": []},
        "character_matrix.json": {"version": 1, "characters": []},
        "resource_ledger.json": {"version": 1, "resources": []},
    }

    for json_name, md_name in MD_PROJECTIONS.items():
        json_path = state_dir / json_name
        md_path = story_dir / md_name

        # Skip if JSON already exists and is valid
        if json_path.exists() and read_json(str(json_path)) is not None:
            continue

        if not md_path.exists():
            # No markdown and no parser — create empty default if available
            if json_name in _EMPTY_DEFAULTS:
                write_json(str(json_path), _EMPTY_DEFAULTS[json_name])
                bootstrapped.append(str(json_path))
                log(f"  [BOOTSTRAP] Created empty default: {json_name}")
                continue
            log(f"No markdown projection for {json_name}, skipping")
            continue

        log(f"Bootstrapping {json_name} from {md_name}...")
        md = md_path.read_text(encoding="utf-8")

        if json_name == "current_state.json":
            chapter = determine_chapter_number(state_dir, md)
            json_data = parse_current_state_md(md, chapter)
        elif json_name == "pending_hooks.json":
            json_data = parse_pending_hooks_md(md)
        elif json_name == "chapter_summaries.json":
            json_data = parse_chapter_summaries_md(md)
        else:
            # Has markdown but no parser — create empty default if available
            if json_name in _EMPTY_DEFAULTS:
                write_json(str(json_path), _EMPTY_DEFAULTS[json_name])
                bootstrapped.append(str(json_path))
                log(f"  [BOOTSTRAP] Created empty default: {json_name}")
            continue

        write_json(str(json_path), json_data)
        bootstrapped.append(str(json_path))
        log(f"Bootstrapped {json_name} successfully")

    # Bootstrap manifest.json if missing
    manifest_path = state_dir / "manifest.json"
    if not manifest_path.exists():
        chapter = determine_latest_chapter(state_dir)
        manifest = {
            "schemaVersion": 2,
            "lastAppliedChapter": chapter,
            "projectionVersion": 1,
            "migrationWarnings": ["Bootstrapped from markdown projections"],
        }
        write_json(str(manifest_path), manifest)
        bootstrapped.append(str(manifest_path))
        log("Bootstrapped manifest.json")

    if bootstrapped:
        valid, errors = validate_truth_files(bootstrapped)
        if not valid:
            log(f"Bootstrapped files have validation errors: {'; '.join(errors)}")
            log("Files written but may need manual review")
        else:
            log("All bootstrapped files passed validation")

    return bootstrapped


# ---------------------------------------------------------------------------
# 2. Recovery: retry settlement after validation failure
# ---------------------------------------------------------------------------


def _create_empty_chapter_meta() -> dict:
    from datetime import datetime, timezone
    return {
        "schemaVersion": 1,
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "chapters": [],
    }


def update_chapter_status(
    book_dir: Path,
    chapter: int,
    status: str,
    extra: dict | None = None,
) -> None:
    """Update a chapter's status in chapter-meta.json."""
    from datetime import datetime, timezone

    meta_path = book_dir / "story" / "state" / "chapter-meta.json"
    now = datetime.now(timezone.utc).isoformat()

    parsed = read_json(str(meta_path)) if meta_path.exists() else None
    meta: dict = parsed if isinstance(parsed, dict) else _create_empty_chapter_meta()

    chapters: list = meta.setdefault("chapters", [])
    record = next((c for c in chapters if c.get("number") == chapter), None)

    if record is not None:
        record["status"] = status
        record["updatedAt"] = now
        if extra:
            record.update(extra)
    else:
        new_record: dict = {
            "number": chapter,
            "title": f"Chapter {chapter}",
            "status": status,
            "wordCount": 0,
            "createdAt": now,
            "updatedAt": now,
        }
        if extra:
            new_record.update(extra)
        chapters.append(new_record)
        chapters.sort(key=lambda c: c.get("number", 0))

    meta["lastUpdated"] = now
    write_json(str(meta_path), meta)


def clean_dir(dir_path: Path) -> None:
    """Remove all files in a directory and then remove the directory itself."""
    if not dir_path.exists():
        return
    for entry in dir_path.iterdir():
        entry.unlink(missing_ok=True)
    try:
        dir_path.rmdir()
    except OSError:
        pass  # Non-fatal on some platforms


def recovery(book_dir: Path, chapter: int, validation_feedback: list[str]) -> bool:
    """Run the recovery flow for a chapter.

    Validates current truth files. If validation fails, marks the chapter as
    state-degraded and restores the pre-recovery backup.

    Returns True if recovery succeeded (truth files valid), False if degraded.
    """
    story_dir = book_dir / "story"
    state_dir = story_dir / "state"

    log(f"Running recovery for chapter {chapter}")

    if not state_dir.exists():
        exit_with_error(f"State directory not found: {state_dir}")

    # Back up current truth files before attempting recovery
    backup_dir = state_dir / ".recovery-backup"
    backup_dir.mkdir(parents=True, exist_ok=True)

    for fname in TRUTH_FILES:
        src = state_dir / fname
        if src.exists():
            shutil.copy2(str(src), str(backup_dir / fname))

    # Write recovery guidance for the settlement agent if errors provided
    if validation_feedback:
        from datetime import datetime, timezone
        guidance_path = book_dir / "story" / "runtime" / "recovery-guidance.json"
        write_json(str(guidance_path), {
            "chapter": chapter,
            "validationErrors": validation_feedback,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "Use these validation errors as correction guidance for retry settlement",
        })
        log(f"Wrote recovery guidance with {len(validation_feedback)} errors")

    # Re-validate current truth files (caller should have already retried settlement)
    truth_file_paths = [
        str(state_dir / f) for f in TRUTH_FILES if (state_dir / f).exists()
    ]
    valid, errors = validate_truth_files(truth_file_paths)

    if valid:
        log("Recovery succeeded — truth files are valid after retry")
        clean_dir(backup_dir)
        return True

    # Second failure: mark state-degraded and restore backups
    log(f"Recovery failed — validation errors: {'; '.join(errors)}")
    log("Restoring previous truth files and marking chapter as state-degraded")

    for fname in TRUTH_FILES:
        backup_path = backup_dir / fname
        if backup_path.exists():
            shutil.copy2(str(backup_path), str(state_dir / fname))

    clean_dir(backup_dir)

    update_chapter_status(book_dir, chapter, STATE_DEGRADED, {"recoveryErrors": errors})
    log(f"Chapter {chapter} marked as {STATE_DEGRADED}")
    return False


# ---------------------------------------------------------------------------
# 3. Snapshots: per-chapter truth file backup with cleanup
# ---------------------------------------------------------------------------


def snapshot(book_dir: Path, chapter: int) -> str:
    """Create a snapshot of truth file JSONs + markdown projections.

    Saves both JSON state files and markdown projections (matching inkos
    snapshotStateAt pattern) so restore can recover the complete readable state.

    Returns the snapshot directory path as a string.
    """
    state_dir = book_dir / "story" / "state"
    story_dir = book_dir / "story"
    snapshot_dir = state_dir / "snapshots" / f"chapter-{pad_chapter(chapter)}"

    if not state_dir.exists():
        exit_with_error(f"State directory not found: {state_dir}")

    snapshot_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    # 1. Snapshot JSON truth files
    for fname in TRUTH_FILES:
        src = state_dir / fname
        if src.exists():
            shutil.copy2(str(src), str(snapshot_dir / fname))
            copied += 1

    # 2. Snapshot markdown projections
    for md_name in MD_PROJECTIONS.values():
        src = story_dir / md_name
        if src.exists():
            shutil.copy2(str(src), str(snapshot_dir / md_name))
            copied += 1

    if copied == 0:
        log(f"Warning: No truth files found to snapshot for chapter {chapter}")
    else:
        log(f"Created snapshot for chapter {chapter} ({copied} files)")

    update_memory_db_valid_until(state_dir, chapter)
    return str(snapshot_dir)


def restore(book_dir: Path, chapter: int) -> bool:
    """Restore truth files + markdown projections from a snapshot.

    Copies JSON files back to story/state/ and markdown files back to story/.
    Rebuilds MemoryDB after restore. Returns True on success, False if snapshot
    not found.

    Follows inkos restoreState() pattern: required files must exist, optional
    files are restored if present or deleted if absent in snapshot.
    """
    state_dir = book_dir / "story" / "state"
    story_dir = book_dir / "story"
    snapshot_dir = state_dir / "snapshots" / f"chapter-{pad_chapter(chapter)}"

    if not snapshot_dir.exists():
        log(f"Snapshot not found for chapter {chapter}: {snapshot_dir}")
        return False

    # Required JSON files (fail if missing from snapshot)
    required_json = ["current_state.json", "pending_hooks.json"]
    for fname in required_json:
        src = snapshot_dir / fname
        if not src.exists():
            log(f"Required file missing from snapshot: {fname}")
            return False

    # Restore all JSON truth files
    json_restored = 0
    for fname in TRUTH_FILES:
        src = snapshot_dir / fname
        dst = state_dir / fname
        if src.exists():
            shutil.copy2(str(src), str(dst))
            json_restored += 1
        elif dst.exists():
            # Snapshot doesn't have this file — remove it (inkos pattern)
            dst.unlink()

    # Restore markdown projections
    md_restored = 0
    for md_name in MD_PROJECTIONS.values():
        src = snapshot_dir / md_name
        dst = story_dir / md_name
        if src.exists():
            shutil.copy2(str(src), str(dst))
            md_restored += 1
        elif dst.exists():
            dst.unlink()

    # Nuke and rebuild MemoryDB (prevent stale data from discarded chapters)
    db_path = state_dir / "memory.db"
    for suffix in ("", "-shm", "-wal"):
        p = db_path.parent / (db_path.name + suffix)
        if p.exists():
            p.unlink()

    # Re-sync MemoryDB from restored truth files
    sync_script = SCRIPT_DIR / "memory-db.py"
    if sync_script.exists():
        subprocess.run(
            [sys.executable, str(sync_script), "sync", str(book_dir)],
            capture_output=True, text=True, timeout=30,
        )

    log(f"Restored snapshot for chapter {chapter} ({json_restored} JSON + {md_restored} MD)")
    return True


def snapshot_cleanup(book_dir: Path, current_chapter: int) -> None:
    """Remove old snapshots.

    Keeps the last KEEP_RECENT_COUNT + one per INTERVAL_SIZE chapters + current.
    """
    snapshots_dir = book_dir / "story" / "state" / "snapshots"

    if not snapshots_dir.exists():
        log("No snapshots directory, nothing to clean up")
        return

    pattern = re.compile(r"^chapter-(\d+)$")
    entries: list[tuple[int, Path]] = []
    for entry in snapshots_dir.iterdir():
        if entry.is_dir():
            m = pattern.match(entry.name)
            if m:
                entries.append((int(m.group(1)), entry))

    entries.sort(key=lambda x: x[0])

    if not entries:
        return

    to_keep: set[int] = set()

    # Keep last KEEP_RECENT_COUNT by chapter number
    for ch, _ in entries[-KEEP_RECENT_COUNT:]:
        to_keep.add(ch)

    # Keep one per INTERVAL_SIZE
    for ch, _ in entries:
        if ch % INTERVAL_SIZE == 0:
            to_keep.add(ch)

    # Always keep current chapter
    to_keep.add(current_chapter)

    removed = 0
    for ch, dir_path in entries:
        if ch not in to_keep:
            try:
                shutil.rmtree(str(dir_path), ignore_errors=True)
            except OSError:
                pass  # Non-fatal
            removed += 1

    if removed > 0:
        log(f"Cleaned up {removed} old snapshot(s), kept {len(entries) - removed}")
    else:
        log(f"No snapshots to clean up ({len(entries)} snapshots, all within retention policy)")


def update_memory_db_valid_until(state_dir: Path, chapter: int) -> None:
    """Update MemoryDB old facts' valid_until_chapter via sqlite3.

    No-op if memory.db does not exist.
    """
    db_path = state_dir / "memory.db"
    if not db_path.exists():
        return

    try:
        conn = sqlite3.connect(str(db_path))
        try:
            cursor = conn.execute(
                "UPDATE facts SET valid_until_chapter = ? "
                "WHERE valid_until_chapter IS NULL AND valid_from_chapter < ?",
                (chapter, chapter),
            )
            updated = cursor.rowcount
            conn.commit()
            if updated > 0:
                log(f"Updated valid_until_chapter for {updated} MemoryDB facts")
        finally:
            conn.close()
    except sqlite3.Error as e:
        log(f"MemoryDB update skipped: {e}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="state-manager.py",
        description="State lifecycle manager for novel-writing truth files.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="subcommand")

    # bootstrap
    p_boot = subparsers.add_parser(
        "bootstrap",
        help="Parse markdown projections to JSON for missing truth files",
    )
    p_boot.add_argument("book_dir", help="Path to the book directory")

    # snapshot
    p_snap = subparsers.add_parser(
        "snapshot",
        help="Create per-chapter snapshot of truth files (JSON + markdown)",
    )
    p_snap.add_argument("book_dir", help="Path to the book directory")
    p_snap.add_argument("chapter", type=int, help="Chapter number")

    # restore
    p_restore = subparsers.add_parser(
        "restore",
        help="Restore truth files from a per-chapter snapshot",
    )
    p_restore.add_argument("book_dir", help="Path to the book directory")
    p_restore.add_argument("chapter", type=int, help="Chapter number to restore to")

    # snapshot-cleanup
    p_clean = subparsers.add_parser(
        "snapshot-cleanup",
        help="Remove old snapshots (keep last 10 + per-10-chapter interval)",
    )
    p_clean.add_argument("book_dir", help="Path to the book directory")
    p_clean.add_argument("chapter", type=int, help="Current chapter number")

    # recovery
    p_rec = subparsers.add_parser(
        "recovery",
        help="Handle settlement validation failure with retry",
    )
    p_rec.add_argument("book_dir", help="Path to the book directory")
    p_rec.add_argument("chapter", type=int, help="Chapter number")
    p_rec.add_argument(
        "validation_errors",
        nargs="?",
        default=None,
        help='Optional JSON array or plain string of validation errors',
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Resolve and validate book_dir for all subcommands
    book_dir = Path(args.book_dir).resolve()
    if not book_dir.exists():
        exit_with_error(f"Book directory not found: {book_dir}")

    # Validate positive chapter for subcommands that require it
    if args.command in ("snapshot", "snapshot-cleanup", "recovery", "restore"):
        if args.chapter < 1:
            exit_with_error("Chapter must be a positive integer")

    if args.command == "bootstrap":
        result = bootstrap(book_dir)
        print(json.dumps({"bootstrapped": result}, indent=2))
        if not result:
            log("No bootstrap needed — all truth files present")

    elif args.command == "snapshot":
        snap_dir = snapshot(book_dir, args.chapter)
        print(json.dumps({"snapshot": snap_dir}, indent=2))

    elif args.command == "snapshot-cleanup":
        snapshot_cleanup(book_dir, args.chapter)

    elif args.command == "recovery":
        # Parse optional validation errors argument
        validation_errors: list[str] = []
        if args.validation_errors:
            try:
                parsed_errors = json.loads(args.validation_errors)
                if isinstance(parsed_errors, list):
                    validation_errors = [str(e) for e in parsed_errors]
                else:
                    validation_errors = [args.validation_errors]
            except json.JSONDecodeError:
                validation_errors = [args.validation_errors]

        success = recovery(book_dir, args.chapter, validation_errors)
        print(json.dumps({"success": success, "status": "recovered" if success else STATE_DEGRADED}, indent=2))
        sys.exit(0 if success else 1)

    elif args.command == "restore":
        success = restore(book_dir, args.chapter)
        print(json.dumps({"success": success, "restoredTo": args.chapter}, indent=2))
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
