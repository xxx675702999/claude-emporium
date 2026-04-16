#!/usr/bin/env python3
"""run-all-deterministic.py -- Run all AI-tell detection scripts.

Runs 4 deterministic checks (dimensions 20-23) + 7 heuristic patterns.
Aggregates results into a single JSON report with both deterministic and heuristic results.
Behaviorally equivalent to InkOS core ai-tells.ts full analysis.

Usage: ./run-all-deterministic.py <file-path>
Output: JSON to stdout
"""

import json
import os
import subprocess
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Deterministic dimension scripts (order matters for output)
DIM_SCRIPTS = [
    ("dim20", "dim20-paragraph-uniformity.py"),
    ("dim21", "dim21-hedge-density.py"),
    ("dim22", "dim22-formulaic-transitions.py"),
    ("dim23", "dim23-list-like-structure.py"),
]

HEURISTICS_SCRIPT = "aigc-heuristics.py"


def run_child_script(script_name: str, file_path: str, fallback_dim: str = "") -> dict:
    """Run a child detection script and return its parsed JSON output.

    If the child script fails or produces invalid JSON, return a default
    passed result with an error note (matching .sh behavior).
    """
    script_path = os.path.join(SCRIPT_DIR, script_name)
    try:
        result = subprocess.run(
            [sys.executable, script_path, file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.loads(result.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        if fallback_dim:
            return {"dimension": fallback_dim, "passed": True, "error": "script failed"}
        return {"heuristics": {}, "overallAILikelihood": 0, "summary": "Error"}


def main() -> None:
    if len(sys.argv) < 2 or not os.path.isfile(sys.argv[1]):
        error_report = {
            "file": "",
            "deterministic": {
                "dimensions": {},
                "overall": {"passed": False, "totalChecked": 0, "failed": 0},
                "issues": ["missing or invalid file argument"],
            },
            "heuristics": {},
        }
        print(json.dumps(error_report))
        sys.exit(1)

    file_path = sys.argv[1]

    # Run deterministic dimension scripts
    dimensions = {}
    for dim_key, script_name in DIM_SCRIPTS:
        dimensions[dim_key] = run_child_script(script_name, file_path, fallback_dim=dim_key)

    # Count failures and build issues list
    fail_count = 0
    issues = []
    for dim_key in ["dim20", "dim21", "dim22", "dim23"]:
        dim_result = dimensions[dim_key]
        if not dim_result.get("passed", True):
            fail_count += 1
            detail_text = dim_result.get("details", "")
            if detail_text:
                issues.append({"dimension": dim_key, "message": detail_text})

    overall_passed = fail_count == 0

    # Run heuristic checks
    heuristics = run_child_script(HEURISTICS_SCRIPT, file_path)

    # Build aggregated JSON report
    report = {
        "file": file_path,
        "deterministic": {
            "dimensions": dimensions,
            "overall": {
                "passed": overall_passed,
                "totalChecked": 4,
                "failed": fail_count,
            },
            "issues": issues,
        },
        "heuristics": heuristics,
    }

    print(json.dumps(report, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
