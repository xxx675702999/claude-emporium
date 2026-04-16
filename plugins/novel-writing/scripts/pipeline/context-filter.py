#!/usr/bin/env python3
"""context-filter.py — Filter markdown table rows from truth file projections.

Operates on pipe-delimited markdown tables in story/*.md files.
Parses header row to identify column positions, filters data rows
based on type-specific rules, preserves header/separator rows.

Usage:
  context-filter.py <type> <file> [options]

Types:
  hooks            Remove rows where status is resolved or closed
  summaries        Keep last N chapter rows (default 5)
  subplots         Remove rows where status is resolved or closed
  emotional-arcs   Keep last N chapter rows (default 5)
  character-matrix Filter rows by character names

Options:
  --keep-last <N>       Keep last N rows (summaries, emotional-arcs; default 5)
  --characters <list>   Comma-separated character names (character-matrix)
  --output <file>       Output file (default: stdout)

Exit codes:
  0 — success (filtered or fallback to original)
  1 — usage error
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Import shared md_table library
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.md_table import ParsedTable, find_column, get_cell, parse_table, reassemble

VALID_TYPES = ("hooks", "summaries", "subplots", "emotional-arcs", "character-matrix")


# ---------------------------------------------------------------------------
# Filter implementations
# ---------------------------------------------------------------------------


def filter_status(table: ParsedTable) -> list[str]:
    """Remove rows where status column is 'resolved' or 'closed' (hooks/subplots)."""
    status_col = find_column(table.headers, "status")
    if status_col == -1:
        return list(table.rows)

    filtered: list[str] = []
    for row in table.rows:
        val = get_cell(row, status_col).lower()
        if val not in ("resolved", "closed"):
            filtered.append(row)
    return filtered


def _extract_chapter_number(value: str) -> int:
    """Extract the first integer from a cell value for sorting."""
    m = re.search(r"\d+", value)
    return int(m.group()) if m else 0


def filter_keep_last(table: ParsedTable, n: int) -> list[str]:
    """Keep last N rows, optionally sorting by chapter column first (summaries/emotional-arcs)."""
    rows = list(table.rows)
    if len(rows) <= n:
        return rows

    chapter_col = find_column(table.headers, "chapter")
    if chapter_col != -1:
        rows.sort(key=lambda r: _extract_chapter_number(get_cell(r, chapter_col)))

    return rows[-n:]


def filter_character_matrix(table: ParsedTable, characters: str) -> list[str]:
    """Keep rows where name/character/characterName column contains any specified character."""
    if not characters:
        return list(table.rows)

    # Find name column with fallback alternatives
    name_col = find_column(table.headers, "name")
    if name_col == -1:
        name_col = find_column(table.headers, "character")
    if name_col == -1:
        name_col = find_column(table.headers, "characterName")
    if name_col == -1:
        return list(table.rows)

    # Parse and normalize character names
    names = [n.strip().lower() for n in characters.split(",") if n.strip()]
    if not names:
        return list(table.rows)

    filtered: list[str] = []
    for row in table.rows:
        cell_val = get_cell(row, name_col).lower()
        if any(name in cell_val for name in names):
            filtered.append(row)
    return filtered


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="context-filter.py",
        description="Filter markdown table rows from truth file projections.",
    )
    parser.add_argument(
        "type",
        choices=VALID_TYPES,
        help="Filter type: hooks, summaries, subplots, emotional-arcs, character-matrix",
    )
    parser.add_argument("file", help="Input markdown file")
    parser.add_argument(
        "--keep-last",
        type=int,
        default=5,
        help="Keep last N rows (summaries, emotional-arcs; default 5)",
    )
    parser.add_argument(
        "--characters",
        default="",
        help="Comma-separated character names (character-matrix)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output file (default: stdout)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.is_file():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    content = input_path.read_text(encoding="utf-8")

    # Empty file: output empty and exit
    if not content.strip():
        _write_output(content, args.output)
        return 0

    table = parse_table(content)

    # No valid table found: output original content unchanged
    if table is None:
        _write_output(content, args.output)
        return 0

    # Apply filter
    filter_type = args.type
    if filter_type in ("hooks", "subplots"):
        filtered_rows = filter_status(table)
    elif filter_type in ("summaries", "emotional-arcs"):
        filtered_rows = filter_keep_last(table, args.keep_last)
    elif filter_type == "character-matrix":
        filtered_rows = filter_character_matrix(table, args.characters)
    else:
        # Should not reach here due to argparse choices
        print(f"Error: Unknown filter type: {filter_type}", file=sys.stderr)
        return 1

    # Empty result: fall back to original content
    if not filtered_rows:
        _write_output(content, args.output)
        return 0

    result = reassemble(table, filtered_rows)
    _write_output(result, args.output)
    return 0


def _write_output(text: str, output_path: str) -> None:
    """Write text to file or stdout."""
    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
        # Ensure trailing newline if content doesn't end with one
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")


if __name__ == "__main__":
    sys.exit(main())
