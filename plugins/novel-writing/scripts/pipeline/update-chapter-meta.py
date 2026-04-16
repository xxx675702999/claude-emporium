#!/usr/bin/env python3
"""update-chapter-meta.py — Incremental updates to chapter-meta.json.

A general-purpose tool for updating individual fields in a chapter's
metadata record. Called by pipeline scripts and agents at various stages.

Usage:
  # Set status
  python3 update-chapter-meta.py <book-dir> <chapter> --status ready-for-review

  # Set length telemetry (after word-count.py)
  python3 update-chapter-meta.py <book-dir> <chapter> \
    --length-telemetry '{"target":3000,"softMin":2250,"softMax":3750,...}'

  # Set length warnings
  python3 update-chapter-meta.py <book-dir> <chapter> \
    --length-warnings '["Over soft max: 3800 > 3750"]'

  # Increment revision count
  python3 update-chapter-meta.py <book-dir> <chapter> --inc-revision

  # Set reviewer notes
  python3 update-chapter-meta.py <book-dir> <chapter> --reviewer-notes "dialogue feels stilted"

  # Set approved
  python3 update-chapter-meta.py <book-dir> <chapter> --status approved

  # Combine multiple updates
  python3 update-chapter-meta.py <book-dir> <chapter> \
    --status ready-for-review --inc-revision \
    --length-telemetry '{"target":3000,...}'

Exit codes: 0 success, 1 error
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.json_utils import read_json, write_json


VALID_STATUSES = {
    "incubating", "drafted", "auditing", "audit-passed", "audit-failed",
    "state-degraded", "ready-for-review", "approved",
}


def main() -> int:
    p = argparse.ArgumentParser(description="Update chapter-meta.json fields.")
    p.add_argument("book_dir", help="Book directory path")
    p.add_argument("chapter", type=int, help="Chapter number")
    p.add_argument("--status", choices=sorted(VALID_STATUSES), help="Set chapter status")
    p.add_argument("--length-telemetry", help="JSON object with length telemetry fields")
    p.add_argument("--length-warnings", help="JSON array of warning strings")
    p.add_argument("--inc-revision", action="store_true", help="Increment revisionCount by 1")
    p.add_argument("--reviewer-notes", help="Set reviewer notes text")
    p.add_argument("--word-count", type=int, help="Override word count")
    args = p.parse_args()

    book_dir = Path(args.book_dir)
    state_dir = book_dir / "story" / "state"
    meta_path = state_dir / "chapter-meta.json"

    meta = read_json(str(meta_path))
    if meta is None:
        print(f"Error: chapter-meta.json not found at {meta_path}", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chapter = args.chapter

    # Find chapter record
    record = None
    for ch in meta.get("chapters", []):
        if ch.get("number") == chapter:
            record = ch
            break

    if record is None:
        print(f"Error: chapter {chapter} not found in chapter-meta.json", file=sys.stderr)
        return 1

    updates = []

    if args.status:
        record["status"] = args.status
        updates.append(f"status={args.status}")
        if args.status == "approved":
            record["approvedAt"] = now

    if args.length_telemetry:
        try:
            telemetry = json.loads(args.length_telemetry)
            record["lengthTelemetry"] = telemetry
            updates.append("lengthTelemetry")
        except json.JSONDecodeError as e:
            print(f"Error: invalid --length-telemetry JSON: {e}", file=sys.stderr)
            return 1

    if args.length_warnings:
        try:
            warnings = json.loads(args.length_warnings)
            record["lengthWarnings"] = warnings
            updates.append(f"lengthWarnings ({len(warnings)} items)")
        except json.JSONDecodeError as e:
            print(f"Error: invalid --length-warnings JSON: {e}", file=sys.stderr)
            return 1

    if args.inc_revision:
        record["revisionCount"] = record.get("revisionCount", 0) + 1
        updates.append(f"revisionCount={record['revisionCount']}")

    if args.reviewer_notes is not None:
        record["reviewerNotes"] = args.reviewer_notes
        updates.append("reviewerNotes")

    if args.word_count is not None:
        record["wordCount"] = args.word_count
        updates.append(f"wordCount={args.word_count}")

    if not updates:
        print("No updates specified.")
        return 0

    record["updatedAt"] = now
    meta["lastUpdated"] = now

    write_json(str(meta_path), meta)
    print(json.dumps({"chapter": chapter, "updates": updates}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
