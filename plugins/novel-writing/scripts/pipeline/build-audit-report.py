#!/usr/bin/env python3
"""build-audit-report.py — Merge three audit sources into a single report.

Combines:
  1. LLM audit result (Track A) — auditor agent output
  2. Deterministic AI-tell checks (Track B) — run-all-deterministic.py output
  3. Sensitive-word detection — sensitive-words.py output

A single "block"-severity sensitive word forces overallVerdict=fail regardless
of other sources (matching inkos chapter-review-cycle.ts behavior).

Usage:
  python3 build-audit-report.py \
    --chapter <N> \
    --llm-audit <path>         # auditor agent AuditResult JSON
    --deterministic <path>     # run-all-deterministic.py output JSON
    --sensitive-words <path>   # sensitive-words.py output JSON
    --output <path>            # target audit-report.json path

All three input paths are optional — missing sources are recorded in the
report's "sources" field and skipped gracefully.

Output: writes merged audit-report.json to --output path, also prints to stdout.
"""

import argparse
import json
import sys
from datetime import datetime, timezone


def load_json(path: str) -> dict | None:
    """Load a JSON file, returning None if missing or invalid."""
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def extract_llm_issues(llm: dict) -> list[dict]:
    """Extract issues from LLM AuditResult and tag with source."""
    issues = []
    for issue in llm.get("issues", []):
        tagged = dict(issue)
        tagged["source"] = "llm"
        issues.append(tagged)
    return issues


def extract_deterministic_issues(det: dict) -> list[dict]:
    """Extract issues from run-all-deterministic.py output and tag with source."""
    issues = []

    # Dimension-level failures
    dim_map = {"dim20": 20, "dim21": 21, "dim22": 22, "dim23": 23}
    dim_names = {
        "dim20": "Paragraph Uniformity",
        "dim21": "Hedge Density",
        "dim22": "Formulaic Transitions",
        "dim23": "List-like Structure",
    }

    dimensions = det.get("deterministic", {}).get("dimensions", {})
    for dim_key, dim_result in dimensions.items():
        if not dim_result.get("passed", True):
            detail = dim_result.get("details", dim_result.get("message", ""))
            issues.append({
                "severity": "warning",
                "category": dim_names.get(dim_key, dim_key),
                "description": detail or f"{dim_key} check failed",
                "suggestion": f"Review and fix {dim_names.get(dim_key, dim_key).lower()} patterns",
                "source": "deterministic",
                "dimensionId": dim_map.get(dim_key),
            })

    # Heuristic issues (from aigc-heuristics.py)
    heuristics = det.get("heuristics", {})
    heuristic_issues = heuristics.get("issues", [])
    for h_issue in heuristic_issues:
        issues.append({
            "severity": h_issue.get("severity", "info"),
            "category": h_issue.get("category", "AI-tell heuristic"),
            "description": h_issue.get("description", ""),
            "suggestion": h_issue.get("suggestion", ""),
            "source": "deterministic",
        })

    return issues


def extract_sensitive_issues(sw: dict) -> tuple[list[dict], bool]:
    """Extract issues from sensitive-words.py output.

    Returns (issues, has_blocked) where has_blocked is True if any
    "block"-severity word was found.
    """
    issues = []
    has_blocked = False

    for error in sw.get("sensitiveWordErrors", []):
        severity_map = {"block": "critical", "warn": "warning"}
        sev = severity_map.get(error.get("severity", "warn"), "warning")
        if error.get("severity") == "block":
            has_blocked = True
        issues.append({
            "severity": sev,
            "category": "Sensitive Content",
            "description": "Prohibited word '%s' found at line %d: %s"
                % (error.get("word", ""), error.get("line", 0), error.get("excerpt", "")),
            "suggestion": "Remove or rephrase to avoid prohibited content",
            "source": "sensitive-words",
            "dimensionId": 27,
        })

    return issues, has_blocked


def count_by_severity(issues: list[dict]) -> tuple[int, int, int]:
    """Count critical, warning, info issues."""
    c = sum(1 for i in issues if i.get("severity") == "critical")
    w = sum(1 for i in issues if i.get("severity") == "warning")
    n = sum(1 for i in issues if i.get("severity") == "info")
    return c, w, n


def build_report(
    chapter: int,
    llm: dict | None,
    det: dict | None,
    sw: dict | None,
) -> dict:
    """Build the merged audit report."""
    all_issues: list[dict] = []
    has_blocked = False

    # Extract issues from each source
    if llm is not None:
        all_issues.extend(extract_llm_issues(llm))
    if det is not None:
        all_issues.extend(extract_deterministic_issues(det))
    if sw is not None:
        sw_issues, has_blocked = extract_sensitive_issues(sw)
        all_issues.extend(sw_issues)

    # Determine verdict: block-severity sensitive word overrides LLM passed
    llm_passed = llm.get("passed", True) if llm else True
    critical, warning, info = count_by_severity(all_issues)

    if has_blocked:
        verdict = "fail"
    elif critical > 0:
        verdict = "fail"
    elif llm_passed:
        verdict = "pass"
    else:
        verdict = "fail"

    report: dict = {
        "chapter": chapter,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overallVerdict": verdict,
        "criticalIssues": critical,
        "warningIssues": warning,
        "infoIssues": info,
        "issues": all_issues,
        "sources": {
            "llmAudit": llm is not None,
            "deterministic": det is not None,
            "sensitiveWords": sw is not None,
        },
        "restoredIssues": 0,
    }

    # Optional fields from LLM
    if llm:
        if llm.get("summary"):
            report["summary"] = llm["summary"]
        if llm.get("literaryQualityCommentary"):
            report["literaryQualityCommentary"] = llm["literaryQualityCommentary"]
        if llm.get("tokenUsage"):
            report["tokenUsage"] = llm["tokenUsage"]

    # Attach raw deterministic results
    if det:
        report["deterministicResults"] = {
            "dimensions": det.get("deterministic", {}).get("dimensions", {}),
            "overall": det.get("deterministic", {}).get("overall", {}),
            "heuristics": det.get("heuristics", {}),
        }

    # Attach raw sensitive-word results
    if sw:
        report["sensitiveWordResults"] = sw

    return report


def update_chapter_meta_audit(book_dir: str, chapter: int, report: dict) -> None:
    """Update chapter-meta.json with audit results.

    Sets auditIssues counts, status (audit-passed or audit-failed),
    and formats issue strings matching inkos ChapterMeta.auditIssues format.
    """
    import os

    meta_path = os.path.join(book_dir, "story", "state", "chapter-meta.json")
    if not os.path.isfile(meta_path):
        return

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError):
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    critical = report.get("criticalIssues", 0)
    warning = report.get("warningIssues", 0)
    info = report.get("infoIssues", 0)
    new_status = "audit-failed" if critical > 0 else "audit-passed"

    # Format issue strings matching inkos format: "[severity] description"
    issue_strings = []
    for issue in report.get("issues", []):
        sev = issue.get("severity", "info")
        cat = issue.get("category", "")
        desc = issue.get("description", "")
        issue_strings.append(f"[{sev}] {cat}: {desc}")

    # Find and update chapter record
    for ch in meta.get("chapters", []):
        if ch.get("number") == chapter:
            ch["status"] = new_status
            ch["auditIssues"] = issue_strings
            ch["updatedAt"] = now
            break

    meta["lastUpdated"] = now

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> None:
    p = argparse.ArgumentParser(description="Merge audit sources into a single report.")
    p.add_argument("--chapter", type=int, required=True, help="Chapter number")
    p.add_argument("--llm-audit", default="", help="Path to LLM AuditResult JSON")
    p.add_argument("--deterministic", default="", help="Path to run-all-deterministic.py output")
    p.add_argument("--sensitive-words", default="", help="Path to sensitive-words.py output")
    p.add_argument("--output", default="", help="Output path for merged audit-report.json")
    p.add_argument("--book-dir", default="", help="Book directory — if provided, updates chapter-meta.json with audit results")
    args = p.parse_args()

    llm = load_json(args.llm_audit)
    det = load_json(args.deterministic)
    sw = load_json(args.sensitive_words)

    if llm is None and det is None and sw is None:
        print("Error: at least one audit source must be provided", file=sys.stderr)
        sys.exit(1)

    report = build_report(args.chapter, llm, det, sw)
    report_json = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report_json)
            f.write("\n")

    # Update chapter-meta.json if book-dir provided
    if args.book_dir:
        update_chapter_meta_audit(args.book_dir, args.chapter, report)

    print(report_json)


if __name__ == "__main__":
    main()
