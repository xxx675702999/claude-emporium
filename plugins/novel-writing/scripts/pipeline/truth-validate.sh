#!/usr/bin/env bash
# Usage: truth-validate.sh <json-file> [json-file ...]
# Validates truth file JSON structure against JSON Schema definitions.
# Wraps schema-validate.py (zero-dependency Python validator).
#
# Output: JSON array with { file, valid, errors, warnings } per file
# Exit: 0 on success, 1 on failure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ $# -lt 1 ]]; then
  echo '{"error": "Usage: truth-validate.sh <json-file> [json-file ...]"}' >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/schema-validate.py" "$@"
