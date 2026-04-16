#!/usr/bin/env python3
"""persist-audit-drift.py — Generate or remove audit_drift.md after audit.

Reads audit-report.json, extracts critical + warning issues, and writes
audit_drift.md as carry-forward guidance for the next chapter. If no
critical/warning issues exist, deletes audit_drift.md.

Also strips any stale audit-drift correction block from current_state.md
to prevent soft guidance from polluting hard state facts.

Follows inkos runner.ts persistAuditDriftGuidance() pattern.

Usage:
  python3 persist-audit-drift.py \
    --book-dir <path> \
    --chapter <N> \
    --audit-report <path>   # audit-report.json
    --language <zh|en>

Output: writes/deletes audit_drift.md, cleans current_state.md. Prints action to stdout.
"""

import argparse
import json
import os
import sys


# Headers used in drift blocks (both languages)
DRIFT_HEADERS = [
    "## 审计纠偏（自动生成，下一章写作前参照）",
    "## Audit Drift Correction",
    "# 审计纠偏",
    "# Audit Drift",
]


def load_json(path: str) -> dict | None:
    """Load a JSON file, returning None on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def read_file(path: str) -> str:
    """Read a text file, returning empty string on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def strip_drift_block(content: str) -> str:
    """Remove any audit-drift correction block from text content."""
    cut_index = -1
    for header in DRIFT_HEADERS:
        idx = content.find(header)
        if idx >= 0 and (cut_index < 0 or idx < cut_index):
            cut_index = idx

    if cut_index < 0:
        return content

    return content[:cut_index].rstrip()


def build_drift_content(chapter: int, issues: list[dict], language: str) -> str:
    """Build audit_drift.md content from issues."""
    if language == "zh":
        lines = [
            "# 审计纠偏",
            "",
            "## 审计纠偏（自动生成，下一章写作前参照）",
            "",
            "> 第%d章审计发现以下问题，下一章写作时必须避免：" % chapter,
        ]
    else:
        lines = [
            "# Audit Drift",
            "",
            "## Audit Drift Correction",
            "",
            "> Chapter %d audit found the following issues to avoid in the next chapter:" % chapter,
        ]

    for issue in issues:
        sev = issue.get("severity", "warning")
        cat = issue.get("category", "Unknown")
        desc = issue.get("description", "")
        lines.append("> - [%s] %s: %s" % (sev, cat, desc))

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="Generate or remove audit_drift.md.")
    p.add_argument("--book-dir", required=True, help="Book directory path")
    p.add_argument("--chapter", type=int, required=True, help="Chapter number")
    p.add_argument("--audit-report", required=True, help="Path to audit-report.json")
    p.add_argument("--language", default="zh", choices=["zh", "en"], help="Book language")
    args = p.parse_args()

    story_dir = os.path.join(args.book_dir, "story")
    drift_path = os.path.join(story_dir, "audit_drift.md")
    state_path = os.path.join(story_dir, "current_state.md")

    # Clean stale drift block from current_state.md
    current_state = read_file(state_path)
    sanitized = strip_drift_block(current_state)
    if sanitized != current_state:
        with open(state_path, "w", encoding="utf-8") as f:
            f.write(sanitized)
        print("Cleaned stale drift block from current_state.md")

    # Load audit report
    report = load_json(args.audit_report)
    if report is None:
        print("Error: cannot read audit report at %s" % args.audit_report, file=sys.stderr)
        sys.exit(1)

    # Filter to critical + warning issues
    actionable = [
        i for i in report.get("issues", [])
        if i.get("severity") in ("critical", "warning")
    ]

    if not actionable:
        # No issues — remove drift file
        if os.path.isfile(drift_path):
            os.remove(drift_path)
            print("Removed audit_drift.md (0 actionable issues)")
        else:
            print("No audit_drift.md to remove (0 actionable issues)")
        return

    # Generate drift file
    content = build_drift_content(args.chapter, actionable, args.language)
    with open(drift_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Generated audit_drift.md (%d issues from chapter %d)" % (len(actionable), args.chapter))


if __name__ == "__main__":
    main()
