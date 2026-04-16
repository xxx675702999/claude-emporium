"""chapter_utils — Shared chapter file discovery and number extraction.

Supports two filename formats:
  - New format: 0001_Title.md, 0042_The_Beginning.md (4-digit prefix + underscore)
  - Old format: chapter-0001.md (legacy backward compat)

CJK filenames are fully supported (e.g. 0001_修炼突破.md).
"""

import glob
import os
import re


def extract_chapter_number(filepath: str) -> int | None:
    """Extract chapter number from a chapter filename.

    Handles both new format (0015_The_Beginning.md) and
    legacy format (chapter-0003.md). Returns None if the
    filename does not match any known pattern.
    """
    basename = os.path.basename(filepath)
    name = os.path.splitext(basename)[0]

    # New format: leading digits before underscore
    m = re.match(r"^(\d+)_", name)
    if m:
        return int(m.group(1))

    # Legacy format: chapter-XXXX
    m = re.match(r"^chapter-(\d+)$", name)
    if m:
        return int(m.group(1))

    return None


def find_chapter_file(chapters_dir: str, num: int) -> str | None:
    """Find a chapter file by number.

    Zero-pads the number to 4 digits, globs for {padded}_*.md.
    Tiebreaker: shortest filename wins when multiple matches exist.
    Falls back to chapter-{padded}.md (legacy format).
    Returns None if no file is found.
    """
    padded = "%04d" % num

    # Primary: XXXX_*.md
    pattern = os.path.join(chapters_dir, "%s_*.md" % padded)
    matches = glob.glob(pattern)
    if matches:
        # Tiebreaker: shortest filename wins
        return min(matches, key=len)

    # Fallback: chapter-XXXX.md
    fallback = os.path.join(chapters_dir, "chapter-%s.md" % padded)
    if os.path.isfile(fallback):
        return fallback

    return None


def detect_last_chapter(chapters_dir: str) -> int:
    """Return the highest chapter number found in the directory.

    Scans all .md files for recognized chapter filename patterns.
    Returns 0 if no chapters are found or the directory does not exist.
    """
    if not os.path.isdir(chapters_dir):
        return 0

    highest = 0
    for entry in os.listdir(chapters_dir):
        if not entry.endswith(".md"):
            continue
        num = extract_chapter_number(entry)
        if num is not None and num > highest:
            highest = num

    return highest


def discover_chapters(
    chapters_dir: str, max_chapter: int | None = None
) -> list[tuple[int, str]]:
    """Return sorted (number, path) tuples for all chapter files.

    If max_chapter is provided, only chapters with number <= max_chapter
    are included. Results are sorted by chapter number ascending.
    """
    if not os.path.isdir(chapters_dir):
        return []

    results: list[tuple[int, str]] = []
    for entry in os.listdir(chapters_dir):
        if not entry.endswith(".md"):
            continue
        num = extract_chapter_number(entry)
        if num is None:
            continue
        if max_chapter is not None and num > max_chapter:
            continue
        results.append((num, os.path.join(chapters_dir, entry)))

    results.sort(key=lambda x: x[0])
    return results


_TITLE_RE = re.compile(r"^#\s+Chapter\s+\d+\s*:\s*(.+)$")

_SANITIZE_RE = re.compile(r"[/\\?%*:|\"<>]")


def sanitize_title(title: str) -> str:
    """Sanitize a chapter title for use in a filename."""
    sanitized = _SANITIZE_RE.sub("", title)
    sanitized = sanitized.replace(" ", "_")
    return sanitized[:50]


def read_title_from_file(filepath: str) -> str | None:
    """Extract the chapter title from the first heading line of a chapter file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                m = _TITLE_RE.match(line.strip())
                if m:
                    return m.group(1).strip()
                if line.strip():
                    break
    except OSError:
        pass
    return None


def rename_chapter_to_title(filepath: str) -> str | None:
    """Rename a chapter file to match its current title.

    Reads the title from the file's heading, sanitizes it, and renames
    the file if the sanitized title differs from the current filename.
    Returns the new filepath, or None if no rename was needed.
    """
    title = read_title_from_file(filepath)
    if not title:
        return None

    dirname = os.path.dirname(filepath)
    basename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(basename)[0]

    # Extract the number prefix (e.g. "0002" from "0002_暗夜")
    m = re.match(r"^(\d+)_", name_no_ext)
    if not m:
        return None

    padded = m.group(1)
    new_name = "%s_%s.md" % (padded, sanitize_title(title))
    new_path = os.path.join(dirname, new_name)

    if new_path == filepath:
        return None

    os.rename(filepath, new_path)
    return new_path


if __name__ == "__main__":
    import sys

    cmd, path = sys.argv[1], sys.argv[2]
    if cmd == "detect-last":
        print(detect_last_chapter(path))
    elif cmd == "find":
        result = find_chapter_file(path, int(sys.argv[3]))
        print(result or "")
    elif cmd == "discover":
        max_ch = int(sys.argv[3]) if len(sys.argv) > 3 else None
        for num, fp in discover_chapters(path, max_ch):
            print(f"{num}\t{fp}")
    elif cmd == "rename-chapter":
        new_path = rename_chapter_to_title(path)
        print(new_path or "")
