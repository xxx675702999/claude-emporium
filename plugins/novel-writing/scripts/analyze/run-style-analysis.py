#!/usr/bin/env python3
"""run-style-analysis.py — Orchestrator for style analysis scripts

Calls 5 leaf analysis scripts and aggregates their JSON results into
a single JSON object with summary metrics.

Usage: ./run-style-analysis.py <file-path>
Output: Aggregated JSON to stdout
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

CHILD_SCRIPTS = [
    ("sentences", "sentence-stats.py"),
    ("paragraphs", "paragraph-stats.py"),
    ("vocabulary", "vocabulary-diversity.py"),
    ("openings", "opening-patterns.py"),
    ("rhetorical", "rhetorical-patterns.py"),
]


def error_exit(message: str) -> None:
    """Print error JSON to stderr and exit with code 1."""
    print(json.dumps({"error": message}), file=sys.stderr)
    sys.exit(1)


def run_child(script_name: str, file_path: str) -> dict:
    """Run a child analysis script and return its parsed JSON output."""
    script_path = SCRIPT_DIR / script_name
    result = subprocess.run(
        ["python3", str(script_path), file_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr_msg = result.stderr.strip() if result.stderr else "unknown error"
        error_exit("%s failed: %s" % (script_name, stderr_msg))
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        error_exit("%s produced invalid JSON: %s" % (script_name, result.stdout[:200]))


def main() -> None:
    if len(sys.argv) < 2:
        error_exit("Usage: run-style-analysis.py <file_path>")

    file_path = sys.argv[1]

    if not Path(file_path).is_file():
        error_exit("File not found: %s" % file_path)

    # Run all child scripts
    results = {}
    for key, script_name in CHILD_SCRIPTS:
        results[key] = run_child(script_name, file_path)

    # Extract language from sentences result
    lang = results["sentences"].get("language", "unknown")

    # Build summary from child results
    summary = {
        "totalCharacters": results["vocabulary"].get("totalTokens", 0),
        "totalSentences": results["sentences"].get("totalSentences", 0),
        "totalParagraphs": results["paragraphs"].get("totalParagraphs", 0),
        "avgSentenceLength": results["sentences"].get("avgLength", 0),
        "vocabularyDiversity": results["vocabulary"].get("ttr", 0),
    }

    # Build aggregated output
    output = {
        "file": file_path,
        "language": lang,
        "sentences": results["sentences"],
        "paragraphs": results["paragraphs"],
        "vocabulary": results["vocabulary"],
        "openings": results["openings"],
        "rhetorical": results["rhetorical"],
        "summary": summary,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
