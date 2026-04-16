#!/usr/bin/env python3
"""memory-db.py — SQLite-backed fast query layer for novel-writing truth files.

Uses sqlite3 stdlib to maintain an indexed mirror of truth file data for
low-latency queries during the prepare stage. The preparer queries MemoryDB
first; on empty or stale DB it falls back to file reads.

Tables: facts, chapter_summaries, hooks
DB location: <book-dir>/story/state/memory.db

Usage:
  memory-db.py sync <book-dir>          Sync from truth files to DB
  memory-db.py bootstrap <book-dir>     Bootstrap from JSON when DB empty
  memory-db.py query <book-dir> <type> <query-json>
  memory-db.py stale <book-dir>         Check if DB is stale
  memory-db.py rebuild <book-dir>       Force rebuild from truth files
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

# Allow importing shared lib from scripts/lib/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.json_utils import read_json  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRUTH_FILES = [
    "current_state.json",
    "pending_hooks.json",
    "chapter_summaries.json",
]

ALLOWED_QUERY_TYPES = {"facts", "chapter_summaries", "hooks", "fact", "chapter_summary", "hook"}

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  subject TEXT NOT NULL,
  predicate TEXT NOT NULL,
  object TEXT NOT NULL,
  valid_from_chapter INTEGER NOT NULL,
  valid_until_chapter INTEGER,
  source_chapter INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_facts_predicate ON facts(predicate);
CREATE INDEX IF NOT EXISTS idx_facts_valid ON facts(valid_until_chapter);

CREATE TABLE IF NOT EXISTS chapter_summaries (
  chapter INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  characters TEXT,
  events TEXT,
  state_changes TEXT,
  hook_activity TEXT,
  mood TEXT,
  chapter_type TEXT
);
CREATE INDEX IF NOT EXISTS idx_summaries_characters ON chapter_summaries(characters);

CREATE TABLE IF NOT EXISTS hooks (
  hook_id TEXT PRIMARY KEY,
  start_chapter INTEGER NOT NULL,
  type TEXT NOT NULL,
  status TEXT NOT NULL,
  last_advanced_chapter INTEGER NOT NULL,
  expected_payoff TEXT,
  payoff_timing TEXT,
  notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_hooks_status ON hooks(status);
CREATE INDEX IF NOT EXISTS idx_hooks_type ON hooks(type);

CREATE TABLE IF NOT EXISTS _meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def log(event: str, detail: str) -> None:
    print(f"[memory-db] [{event}] {detail}", file=sys.stderr)


def exit_with_error(msg: str) -> None:
    log("ERROR", msg)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def db_path(book_dir: str) -> Path:
    return Path(book_dir) / "story" / "state" / "memory.db"


def state_dir(book_dir: str) -> Path:
    return Path(book_dir) / "story" / "state"


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------


def open_db(db_file: Path) -> sqlite3.Connection:
    """Open (or create) the SQLite database and apply the schema."""
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.executescript(SCHEMA_DDL)
    return conn


# ---------------------------------------------------------------------------
# Data loading from truth files
# ---------------------------------------------------------------------------


def load_current_state(state_path: Path) -> list[dict]:
    """Load facts from current_state.json."""
    data = read_json(str(state_path))
    if not data or not isinstance(data.get("facts"), list):
        return []
    return data["facts"]


def load_pending_hooks(state_path: Path) -> list[dict]:
    """Load hooks from pending_hooks.json."""
    data = read_json(str(state_path))
    if not data:
        return []
    hooks = data.get("hooks", [])
    if not isinstance(hooks, list):
        return []
    return hooks


def load_chapter_summaries(state_path: Path) -> list[dict]:
    """Load summaries from chapter_summaries.json. Supports both {chapters:[]} and legacy {rows:[]} formats."""
    data = read_json(str(state_path))
    if not data:
        return []
    chapters = data.get("chapters") or data.get("rows")
    if not isinstance(chapters, list):
        return []
    return chapters


# ---------------------------------------------------------------------------
# Sync helpers — insert truth file data into DB
# ---------------------------------------------------------------------------


def sync_facts(conn: sqlite3.Connection, facts: list[dict]) -> int:
    conn.execute("DELETE FROM facts")
    if not facts:
        return 0
    count = 0
    sql = (
        "INSERT INTO facts "
        "(subject, predicate, object, valid_from_chapter, valid_until_chapter, source_chapter) "
        "VALUES (?, ?, ?, ?, ?, ?)"
    )
    for f in facts:
        conn.execute(
            sql,
            (
                f.get("subject", ""),
                f.get("predicate", ""),
                f.get("object", ""),
                f.get("validFromChapter", 0),
                f.get("validUntilChapter"),
                f.get("sourceChapter", 0),
            ),
        )
        count += 1
    return count


def sync_summaries(conn: sqlite3.Connection, rows: list[dict]) -> int:
    conn.execute("DELETE FROM chapter_summaries")
    if not rows:
        return 0
    count = 0
    sql = (
        "INSERT INTO chapter_summaries "
        "(chapter, title, characters, events, state_changes, hook_activity, mood, chapter_type) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    for r in rows:
        conn.execute(
            sql,
            (
                r.get("chapter", 0),
                r.get("title", ""),
                r.get("characters", ""),
                r.get("events", ""),
                r.get("stateChanges", ""),
                r.get("hookActivity", ""),
                r.get("mood", ""),
                r.get("chapterType", ""),
            ),
        )
        count += 1
    return count


def sync_hooks(conn: sqlite3.Connection, hooks: list[dict]) -> int:
    conn.execute("DELETE FROM hooks")
    if not hooks:
        return 0
    count = 0
    sql = (
        "INSERT INTO hooks "
        "(hook_id, start_chapter, type, status, last_advanced_chapter, "
        "expected_payoff, payoff_timing, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    for h in hooks:
        conn.execute(
            sql,
            (
                h.get("hookId", ""),
                h.get("startChapter", 0),
                h.get("type", ""),
                h.get("status", ""),
                h.get("lastAdvancedChapter", 0),
                h.get("expectedPayoff", ""),
                h.get("payoffTiming", ""),
                h.get("notes", ""),
            ),
        )
        count += 1
    return count


# ---------------------------------------------------------------------------
# _meta table helpers
# ---------------------------------------------------------------------------


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM _meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO _meta (key, value) VALUES (?, ?)", (key, value))


def save_mtimes(conn: sqlite3.Connection, book_dir: str) -> None:
    """Store truth file mtimes in _meta for staleness detection."""
    s_dir = state_dir(book_dir)
    for tf in TRUTH_FILES:
        file_path = s_dir / tf
        if file_path.exists():
            mtime = str(file_path.stat().st_mtime_ns)
            set_meta(conn, f"mtime_{tf}", mtime)


# ---------------------------------------------------------------------------
# SQL safety check
# ---------------------------------------------------------------------------


def is_safe_sql_fragment(fragment: str) -> bool:
    """Basic validation to prevent SQL injection in where/order clauses.

    Blocks semicolons, comments, and dangerous DDL/DML keywords.
    """
    if ";" in fragment:
        return False
    if "--" in fragment:
        return False
    if re.search(r"\b(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|EXEC|EXECUTE)\b", fragment, re.IGNORECASE):
        return False
    return True


# ---------------------------------------------------------------------------
# Public operations
# ---------------------------------------------------------------------------


def do_sync(book_dir: str) -> None:
    """Sync all truth files into MemoryDB."""
    s_dir = state_dir(book_dir)
    db_file = db_path(book_dir)
    conn = open_db(db_file)

    try:
        facts = load_current_state(s_dir / "current_state.json")
        hooks = load_pending_hooks(s_dir / "pending_hooks.json")
        summaries = load_chapter_summaries(s_dir / "chapter_summaries.json")

        with conn:
            fact_count = sync_facts(conn, facts)
            hook_count = sync_hooks(conn, hooks)
            summary_count = sync_summaries(conn, summaries)
            set_meta(conn, "last_sync", __import__("datetime").datetime.utcnow().isoformat())
            save_mtimes(conn, book_dir)

        log("SYNC", f"facts={fact_count} hooks={hook_count} summaries={summary_count}")
    finally:
        conn.close()


def do_bootstrap(book_dir: str) -> None:
    """Populate DB only when it is empty or missing."""
    db_file = db_path(book_dir)
    if db_file.exists():
        try:
            conn = sqlite3.connect(str(db_file))
            conn.row_factory = sqlite3.Row
            try:
                facts_cnt = conn.execute("SELECT count(*) as cnt FROM facts").fetchone()["cnt"]
                hooks_cnt = conn.execute("SELECT count(*) as cnt FROM hooks").fetchone()["cnt"]
                sums_cnt = conn.execute("SELECT count(*) as cnt FROM chapter_summaries").fetchone()["cnt"]
                if facts_cnt > 0 or hooks_cnt > 0 or sums_cnt > 0:
                    log("BOOTSTRAP", "DB already populated — skipping")
                    conn.close()
                    return
            except sqlite3.OperationalError:
                # Tables may not exist yet — fall through to do_sync
                pass
            finally:
                conn.close()
        except sqlite3.Error:
            pass  # Cannot open DB — fall through to do_sync

    log("BOOTSTRAP", "populating from truth files")
    do_sync(book_dir)


def do_stale(book_dir: str) -> None:
    """Check if DB is stale by comparing truth file mtimes against stored values."""
    db_file = db_path(book_dir)
    result: dict = {"stale": False, "details": []}

    if not db_file.exists():
        result["stale"] = True
        result["details"].append("DB file does not exist")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    try:
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        result["stale"] = True
        result["details"].append("Cannot open DB file")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    try:
        s_dir = state_dir(book_dir)
        for tf in TRUTH_FILES:
            file_path = s_dir / tf
            if not file_path.exists():
                continue
            stored_mtime = get_meta(conn, f"mtime_{tf}")
            current_mtime = str(file_path.stat().st_mtime_ns)
            if stored_mtime is None:
                result["stale"] = True
                result["details"].append(f"{tf}: no stored mtime (never synced)")
            elif stored_mtime != current_mtime:
                result["stale"] = True
                result["details"].append(
                    f"{tf}: mtime changed (stored={stored_mtime}, current={current_mtime})"
                )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        conn.close()


def do_rebuild(book_dir: str) -> None:
    """Force rebuild: delete DB and re-sync."""
    db_file = db_path(book_dir)
    if db_file.exists():
        for suffix in ("", "-wal", "-shm"):
            target = Path(str(db_file) + suffix)
            try:
                if target.exists():
                    target.unlink()
            except OSError:
                pass
        log("REBUILD", "removed existing DB")

    do_sync(book_dir)
    log("REBUILD", "complete")


def do_query(book_dir: str, query_type: str, query_json: str) -> None:
    """Run a query against MemoryDB.

    query_type must be one of: fact, chapter_summary, hook
    query-json format:
      {"where": "status != 'resolved'"}
      {"order": "chapter DESC", "limit": 5}
      {"where": "predicate = 'Current Location' AND valid_until_chapter IS NULL"}
    """
    if query_type not in ALLOWED_QUERY_TYPES:
        exit_with_error(
            f"Invalid type '{query_type}'. Allowed: {', '.join(sorted(ALLOWED_QUERY_TYPES))}"
        )

    # Map query_type to table name (accept both singular and plural)
    type_to_table = {
        "facts": "facts", "fact": "facts",
        "chapter_summaries": "chapter_summaries", "chapter_summary": "chapter_summaries",
        "hooks": "hooks", "hook": "hooks",
    }
    table = type_to_table[query_type]

    try:
        query = json.loads(query_json)
    except json.JSONDecodeError:
        exit_with_error(f"Invalid query JSON: {query_json}")

    if not isinstance(query, dict):
        exit_with_error("Query JSON must be an object")

    db_file = db_path(book_dir)
    if not db_file.exists():
        print(json.dumps({"rows": [], "stale": True, "error": "DB does not exist"}, indent=2))
        return

    try:
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        print(json.dumps({"rows": [], "stale": True, "error": "Cannot open DB"}, indent=2))
        return

    try:
        where = query.get("where") if isinstance(query.get("where"), str) else None
        order = query.get("order") if isinstance(query.get("order"), str) else None
        limit = query.get("limit") if isinstance(query.get("limit"), int) else None

        if where and not is_safe_sql_fragment(where):
            exit_with_error(f"Unsafe SQL fragment in 'where': {where}")
        if order and not is_safe_sql_fragment(order):
            exit_with_error(f"Unsafe SQL fragment in 'order': {order}")

        # Build SELECT using whitelisted table name (no user input in table position)
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        if order:
            sql += f" ORDER BY {order}"
        if limit is not None:
            sql += f" LIMIT {min(limit, 1000)}"

        cursor = conn.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]

        # Check staleness
        s_dir = state_dir(book_dir)
        is_stale = False
        for tf in TRUTH_FILES:
            file_path = s_dir / tf
            if not file_path.exists():
                continue
            stored_mtime = get_meta(conn, f"mtime_{tf}")
            current_mtime = str(file_path.stat().st_mtime_ns)
            if stored_mtime is None or stored_mtime != current_mtime:
                is_stale = True
                break

        output = {"rows": rows, "stale": is_stale}
        print(json.dumps(output, indent=2, ensure_ascii=False))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="memory-db.py",
        description="SQLite-backed fast query layer for novel-writing truth files.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # sync
    p_sync = subparsers.add_parser("sync", help="Sync from truth files to DB")
    p_sync.add_argument("book_dir", help="Path to book directory")

    # bootstrap
    p_boot = subparsers.add_parser("bootstrap", help="Bootstrap from JSON when DB empty")
    p_boot.add_argument("book_dir", help="Path to book directory")

    # stale
    p_stale = subparsers.add_parser("stale", help="Check if DB is stale")
    p_stale.add_argument("book_dir", help="Path to book directory")

    # rebuild
    p_rebuild = subparsers.add_parser("rebuild", help="Force rebuild from truth files")
    p_rebuild.add_argument("book_dir", help="Path to book directory")

    # query
    p_query = subparsers.add_parser("query", help="Query MemoryDB")
    p_query.add_argument("book_dir", help="Path to book directory")
    p_query.add_argument(
        "type",
        choices=sorted(ALLOWED_QUERY_TYPES),
        help="Query type: fact, chapter_summary, hook",
    )
    p_query.add_argument("query_json", help="JSON query object")

    args = parser.parse_args()

    book_dir = str(Path(args.book_dir).resolve())
    if not Path(book_dir).exists():
        exit_with_error(f"Book directory not found: {book_dir}")

    # Ensure state directory exists
    state_dir(book_dir).mkdir(parents=True, exist_ok=True)

    if args.command == "sync":
        do_sync(book_dir)
    elif args.command == "bootstrap":
        do_bootstrap(book_dir)
    elif args.command == "stale":
        do_stale(book_dir)
    elif args.command == "rebuild":
        do_rebuild(book_dir)
    elif args.command == "query":
        do_query(book_dir, args.type, args.query_json)
    else:
        exit_with_error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
