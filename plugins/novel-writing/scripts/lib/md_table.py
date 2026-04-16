"""md_table — Markdown pipe-delimited table parser and filter.

Parses the first markdown table found in content, extracts headers,
rows, and surrounding text. Provides cell extraction and column
lookup utilities for filtering rows without regex gymnastics.

Replaces the table-parsing logic in context-filter.sh.
"""

import re
from dataclasses import dataclass, field


@dataclass
class ParsedTable:
    """Components of a parsed markdown table with surrounding content."""

    preamble: list[str] = field(default_factory=list)
    """Lines before the table."""

    headers: list[str] = field(default_factory=list)
    """Trimmed header cell values."""

    header_line: str = ""
    """Raw header row as it appeared in the source."""

    separator_line: str = ""
    """Raw separator row (e.g. |------|--------|)."""

    rows: list[str] = field(default_factory=list)
    """Raw data rows (pipe-delimited lines)."""

    postamble: list[str] = field(default_factory=list)
    """Lines after the table."""


def _is_pipe_row(line: str) -> bool:
    """Check if a line is a pipe-delimited table row."""
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _is_separator(line: str) -> bool:
    """Check if a line is a markdown table separator (e.g. |---|---|)."""
    stripped = line.strip()
    if not _is_pipe_row(stripped):
        return False
    # After removing pipes and whitespace, should be only dashes and colons
    inner = stripped.strip("|")
    cells = inner.split("|")
    return all(re.match(r"^\s*:?-+:?\s*$", cell) for cell in cells)


def _parse_header_cells(header_line: str) -> list[str]:
    """Extract trimmed cell values from a header row."""
    stripped = header_line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def parse_table(content: str) -> ParsedTable | None:
    """Find and parse the first markdown table in the content.

    A valid table requires at least 3 consecutive pipe-delimited lines:
    header row, separator row, and at least 1 data row.

    Returns None if no valid table is found.
    """
    lines = content.split("\n")

    # Scan for a sequence: pipe-row, separator, pipe-row(s)
    table_start = None
    for i in range(len(lines) - 2):
        if (
            _is_pipe_row(lines[i])
            and _is_separator(lines[i + 1])
            and _is_pipe_row(lines[i + 2])
        ):
            table_start = i
            break

    if table_start is None:
        return None

    header_line = lines[table_start]
    separator_line = lines[table_start + 1]
    headers = _parse_header_cells(header_line)

    # Collect data rows (consecutive pipe-delimited lines after separator)
    data_rows: list[str] = []
    for i in range(table_start + 2, len(lines)):
        if _is_pipe_row(lines[i]):
            data_rows.append(lines[i])
        else:
            break

    table_end = table_start + 2 + len(data_rows)

    preamble = lines[:table_start]
    postamble = lines[table_end:]

    return ParsedTable(
        preamble=preamble,
        headers=headers,
        header_line=header_line,
        separator_line=separator_line,
        rows=data_rows,
        postamble=postamble,
    )


def get_cell(row: str, col_index: int) -> str:
    """Extract cell value at a 0-based column index from a pipe-delimited row.

    Returns an empty string if the index is out of range.
    """
    stripped = row.strip().strip("|")
    cells = stripped.split("|")
    if 0 <= col_index < len(cells):
        return cells[col_index].strip()
    return ""


def find_column(headers: list[str], name: str) -> int:
    """Find a column index by name (case-insensitive, ignoring spaces/underscores).

    Returns -1 if not found.
    """
    normalized = name.lower().replace(" ", "").replace("_", "")
    for i, header in enumerate(headers):
        h = header.lower().replace(" ", "").replace("_", "")
        if h == normalized:
            return i
    return -1


def reassemble(table: ParsedTable, filtered_rows: list[str]) -> str:
    """Rebuild content with filtered rows replacing the original data rows.

    Preserves preamble, header, separator, and postamble exactly as they
    were in the original content.
    """
    parts: list[str] = []
    parts.extend(table.preamble)
    parts.append(table.header_line)
    parts.append(table.separator_line)
    parts.extend(filtered_rows)
    parts.extend(table.postamble)
    return "\n".join(parts)
