#!/usr/bin/env python3
"""
Incremental re-audit: only check previously-failed dimensions.
Restore issues that LLM "forgets" during re-audit.

Usage:
  python incremental-audit.py --mode dimensions --audit-report <path>
  python incremental-audit.py --mode full --audit-report <path> --reaudit-report <path> \
      [--original-text <path>] [--revised-text <path>]
"""
import argparse, json, re, sys
from difflib import SequenceMatcher

# Category label -> dimension ID (en + zh, short + long forms)
_DIM_MAP = {
    "OOC": 1, "Out of Character": 1, "人设崩坏": 1,
    "Timeline": 2, "Timeline Inconsistency": 2, "时间线矛盾": 2,
    "Lore": 3, "Lore Conflict": 3, "世界观冲突": 3,
    "Power Scaling": 4, "Power Scaling Violation": 4, "战力崩坏": 4,
    "Numerical": 5, "Numerical Inconsistency": 5, "数值矛盾": 5,
    "Hook Health": 6, "伏笔健康": 6,
    "Pacing": 7, "Pacing Issues": 7, "节奏问题": 7,
    "Style Drift": 8, "风格漂移": 8,
    "Information Boundary": 9, "Information Boundary Violation": 9, "信息越界": 9,
    "Lexical Fatigue": 10, "词汇疲劳": 10,
    "Incentive Chain": 11, "Incentive Chain Break": 11, "动机断裂": 11,
    "Era Accuracy": 12, "时代感失真": 12,
    "Side Character Competence": 13, "Side Character Instrumentalization": 14, "配角工具化": 14,
    "Payoff Dilution": 15, "Dialogue Authenticity": 16, "Chronicle Drift": 17,
    "Knowledge Pollution": 18, "POV Consistency": 19, "POV": 19,
    "Paragraph Uniformity": 20, "Hedge Density": 21,
    "Formulaic Transitions": 22, "List-like Structure": 23,
    "Subplot Stagnation": 24, "支线停滞": 24,
    "Arc Flatline": 25, "弧线平坦": 25, "Pacing Monotony": 26,
    "Sensitive Content": 27, "敏感内容": 27,
    "Canon Event Conflict": 28, "Future Information Leak": 29,
    "Cross-book World Rules": 30, "Spinoff Hook Isolation": 31,
    "Reader Expectation": 32, "Reader Expectation Management": 32,
    "Outline Drift": 33, "Outline Drift Detection": 33,
    "Character Fidelity": 34, "World Rule Compliance": 35,
    "Relationship Dynamics": 36, "Canon Event Consistency": 37,
}
_DIM_MAP_LOWER = {k.lower(): v for k, v in _DIM_MAP.items()}


def category_to_dim_id(category: str) -> int | None:
    if category in _DIM_MAP:
        return _DIM_MAP[category]
    if category.lower() in _DIM_MAP_LOWER:
        return _DIM_MAP_LOWER[category.lower()]
    m = re.match(r"(?:dim(?:ension)?\s*)(\d+)", category, re.I)
    return int(m.group(1)) if m else None


def get_failed_dimensions(report: dict) -> list[int]:
    """Extract dimension IDs with critical/warning issues (sorted, unique)."""
    dims = set()
    for issue in report.get("issues", []):
        if issue.get("severity") in ("critical", "warning"):
            d = category_to_dim_id(issue.get("category", ""))
            if d is not None:
                dims.add(d)
    return sorted(dims)


def _extract_quotes(text: str) -> list[str]:
    """Pull quoted substrings (>=4 chars) from text."""
    quotes = []
    for m in re.finditer(r'["\u201c](.{4,}?)["\u201d]|[\'\u2018](.{4,}?)[\'\u2019]', text):
        quotes.append(m.group(1) or m.group(2))
    return quotes


def _text_was_revised(desc: str, orig: str, revised: str) -> bool:
    """Heuristic: did the reviser actually change the text relevant to this issue?"""
    if not orig or not revised:
        return False
    for snippet in _extract_quotes(desc):
        if snippet in orig and snippet not in revised:
            return True
    if SequenceMatcher(None, orig, revised).ratio() > 0.95:
        return False
    return True  # texts differ significantly, assume revision addressed it


def _issue_key(issue: dict) -> str:
    return f"{issue.get('category','')}|{issue.get('severity','')}|{issue.get('description','')[:80]}"


def restore_lost_issues(orig_issues, reaudit_issues, orig_text, revised_text):
    """Restore issues present in original but absent in re-audit when text wasn't revised."""
    reaudit_keys = {_issue_key(i) for i in reaudit_issues}
    restored = []
    for issue in orig_issues:
        if _issue_key(issue) in reaudit_keys:
            continue
        if not _text_was_revised(issue.get("description", ""), orig_text, revised_text):
            ri = dict(issue)
            ri["_restored"] = True
            ri["_restoreReason"] = (
                "Issue present in original audit but absent in re-audit; "
                "relevant text was not revised — restored to prevent LLM forgetting."
            )
            restored.append(ri)
    return restored


def merge_audit_results(reaudit: dict, restored: list[dict]) -> dict:
    """Merge re-audit results with restored issues into final report."""
    merged = dict(reaudit)
    all_issues = list(reaudit.get("issues", [])) + restored
    merged["issues"] = all_issues
    merged["passed"] = not any(i.get("severity") == "critical" for i in all_issues)
    if restored:
        n = len(restored)
        merged["summary"] = merged.get("summary", "") + (
            f" ({n} issue(s) restored from original audit — LLM forgetting protection)"
        )
    return merged


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    p = argparse.ArgumentParser(description="Incremental re-audit helper.")
    p.add_argument("--audit-report", required=True)
    p.add_argument("--reaudit-report", default=None)
    p.add_argument("--original-text", default=None)
    p.add_argument("--revised-text", default=None)
    p.add_argument("--mode", choices=["dimensions", "restore", "full"], default="full")
    args = p.parse_args()

    report = json.loads(_load(args.audit_report))
    failed = get_failed_dimensions(report)

    if args.mode == "dimensions":
        json.dump({"failedDimensions": failed}, sys.stdout, indent=2)
        print()
        return

    if not args.reaudit_report:
        print("Error: --reaudit-report required for restore/full mode", file=sys.stderr)
        sys.exit(1)

    reaudit = json.loads(_load(args.reaudit_report))
    orig_text = _load(args.original_text) if args.original_text else ""
    rev_text = _load(args.revised_text) if args.revised_text else ""

    restored = restore_lost_issues(
        report.get("issues", []), reaudit.get("issues", []), orig_text, rev_text
    )

    if args.mode == "restore":
        json.dump({"restoredIssues": restored}, sys.stdout, indent=2)
        print()
        return

    merged = merge_audit_results(reaudit, restored)
    json.dump(
        {"failedDimensions": failed, "restoredIssues": restored, "mergedResult": merged},
        sys.stdout, indent=2, ensure_ascii=False,
    )
    print()


if __name__ == "__main__":
    main()
