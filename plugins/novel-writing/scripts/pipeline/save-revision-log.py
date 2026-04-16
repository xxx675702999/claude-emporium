#!/usr/bin/env python3
"""save-revision-log.py — Append a revision round to the chapter revision log.

Reads or creates chapter-XXXX.revision-log.json, appends a round record,
validates against the revision-log schema, and writes to disk.

Usage:
  python3 save-revision-log.py \
    --book-dir <path> \
    --chapter <N> \
    --round <N> \
    --mode <polish|spot-fix|rewrite|rework|anti-detect> \
    --before-wc <N> \
    --after-wc <N> \
    --issues-addressed '<json-array>' \
    --remaining-issues '<json-array>' \
    --verdict <pass|fail>

Output: writes updated revision-log.json, prints summary to stdout.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


VALID_MODES = {"polish", "spot-fix", "rewrite", "rework", "anti-detect"}
VALID_VERDICTS = {"pass", "fail"}


def load_log(path: str, chapter: int) -> dict:
    """Load existing revision log or create a new one."""
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("chapterNumber") == chapter:
                return data
        except (OSError, json.JSONDecodeError):
            pass

    return {"chapterNumber": chapter, "revisions": []}


def main() -> None:
    p = argparse.ArgumentParser(description="Append revision round to revision log.")
    p.add_argument("--book-dir", required=True, help="Book directory path")
    p.add_argument("--chapter", type=int, required=True, help="Chapter number")
    p.add_argument("--round", type=int, required=True, help="Revision round number")
    p.add_argument("--mode", required=True, choices=sorted(VALID_MODES), help="Revision mode")
    p.add_argument("--before-wc", type=int, required=True, help="Word count before revision")
    p.add_argument("--after-wc", type=int, required=True, help="Word count after revision")
    p.add_argument("--issues-addressed", default="[]", help="JSON array of issue description strings")
    p.add_argument("--remaining-issues", default="[]", help="JSON array of remaining issue strings")
    p.add_argument("--verdict", default="fail", choices=sorted(VALID_VERDICTS), help="Audit verdict after this round")
    args = p.parse_args()

    # Parse JSON arrays
    try:
        addressed = json.loads(args.issues_addressed)
        if not isinstance(addressed, list):
            raise ValueError("issues-addressed must be a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        print("Error parsing --issues-addressed: %s" % e, file=sys.stderr)
        sys.exit(1)

    try:
        remaining = json.loads(args.remaining_issues)
        if not isinstance(remaining, list):
            raise ValueError("remaining-issues must be a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        print("Error parsing --remaining-issues: %s" % e, file=sys.stderr)
        sys.exit(1)

    # Build file path
    padded = "%04d" % args.chapter
    runtime_dir = os.path.join(args.book_dir, "story", "runtime")
    log_path = os.path.join(runtime_dir, "chapter-%s.revision-log.json" % padded)

    # Ensure runtime directory exists
    os.makedirs(runtime_dir, exist_ok=True)

    # Load or create log
    log = load_log(log_path, args.chapter)

    # Append round
    record = {
        "round": args.round,
        "mode": args.mode,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "beforeWordCount": args.before_wc,
        "afterWordCount": args.after_wc,
        "issuesAddressed": addressed,
        "remainingIssues": remaining,
        "auditVerdict": args.verdict,
    }

    log["revisions"].append(record)

    # Write
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(json.dumps({
        "path": log_path,
        "chapter": args.chapter,
        "round": args.round,
        "mode": args.mode,
        "verdict": args.verdict,
        "totalRounds": len(log["revisions"]),
    }, indent=2))


if __name__ == "__main__":
    main()
