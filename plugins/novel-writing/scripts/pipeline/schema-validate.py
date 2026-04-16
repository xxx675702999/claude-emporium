#!/usr/bin/env python3
"""schema-validate.py -- JSON Schema validator for novel-writing truth files.

Validates structured state JSON files against JSON Schema (draft-07 subset)
definitions in data/schemas/. Zero external dependencies -- uses only Python
standard library.

Usage:
  python3 schema-validate.py <file> [file ...]

Exit codes:
  0 -- all files valid
  1 -- one or more validation errors

Output: JSON array to stdout:
  [{ "file": "...", "valid": true/false, "errors": [...], "warnings": [...] }]
"""

import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = SCRIPT_DIR / ".." / ".." / "data" / "schemas"

_ISO8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
)


def load_schemas() -> dict[str, dict]:
    """Load all .json schema files from data/schemas/ and subdirectories."""
    schemas: dict[str, dict] = {}
    schema_dir = SCHEMA_DIR.resolve()
    if not schema_dir.is_dir():
        return schemas
    for entry in sorted(schema_dir.iterdir()):
        if entry.suffix == ".json" and entry.is_file():
            with open(entry, encoding="utf-8") as f:
                schemas[entry.name] = json.load(f)
    # Also load truth file schemas from subdirectory
    truth_dir = schema_dir / "truth-files"
    if truth_dir.is_dir():
        for entry in sorted(truth_dir.iterdir()):
            if entry.suffix == ".json" and entry.is_file():
                with open(entry, encoding="utf-8") as f:
                    schemas[entry.name] = json.load(f)
    return schemas


# ---------------------------------------------------------------------------
# Inline schemas with no canonical file
# ---------------------------------------------------------------------------

HOOK_STATUS_ENUM = ["open", "progressing", "escalating", "critical", "deferred", "resolved"]
PAYOFF_TIMING_ENUM = ["immediate", "near-term", "mid-arc", "slow-burn", "endgame"]

MANIFEST_SCHEMA: dict = {
    "type": "object",
    "required": ["schemaVersion", "lastAppliedChapter", "projectionVersion"],
    "properties": {
        "schemaVersion": {"type": "integer", "minimum": 1},
        "language": {"type": "string", "enum": ["zh", "en"]},
        "lastAppliedChapter": {"type": "integer", "minimum": 0},
        "projectionVersion": {"type": "integer", "minimum": 1},
        "migrationWarnings": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": True,
}

# ---------------------------------------------------------------------------
# Lightweight JSON Schema validator (draft-07 subset)
# ---------------------------------------------------------------------------

# Supported keywords: type, required, properties, additionalProperties,
# items, enum, const, minLength, minimum, format, $ref, definitions.


def _resolve_ref(ref: str, root_schema: dict) -> dict | None:
    """Resolve a $ref like '#/definitions/Foo' against the root schema."""
    if not ref.startswith("#/definitions/"):
        return None
    name = ref[len("#/definitions/"):]
    defs = root_schema.get("definitions", {})
    return defs.get(name)


def _type_name(value) -> str:
    """Map Python type to JSON Schema type name."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _check_type(value, expected_type, path: str) -> list[str]:
    """Check value against a JSON Schema type (string or array of strings)."""
    if isinstance(expected_type, list):
        actual = _type_name(value)
        # integer also satisfies "number"
        for t in expected_type:
            if actual == t:
                return []
            if t == "number" and actual == "integer":
                return []
        return [f"schema: {path} must be one of types [{', '.join(expected_type)}], got {actual}"]
    else:
        actual = _type_name(value)
        if actual == expected_type:
            return []
        if expected_type == "number" and actual == "integer":
            return []
        return [f"schema: {path} must be type {expected_type}, got {actual}"]


def validate_against_schema(
    data,
    schema: dict,
    root_schema: dict,
    path: str = "(root)",
) -> list[str]:
    """Validate data against a JSON Schema node. Returns list of error strings."""
    errors: list[str] = []

    # Handle $ref
    ref = schema.get("$ref")
    if ref:
        resolved = _resolve_ref(ref, root_schema)
        if resolved is None:
            errors.append(f"schema: {path} unresolved $ref '{ref}'")
            return errors
        return validate_against_schema(data, resolved, root_schema, path)

    # type check
    expected_type = schema.get("type")
    if expected_type is not None:
        type_errors = _check_type(data, expected_type, path)
        if type_errors:
            errors.extend(type_errors)
            return errors  # type mismatch -- skip deeper checks

    # const
    if "const" in schema:
        if data != schema["const"]:
            errors.append(f"schema: {path} must be {schema['const']!r}, got {data!r}")

    # enum
    if "enum" in schema:
        if data not in schema["enum"]:
            allowed = ", ".join(repr(v) for v in schema["enum"])
            errors.append(
                f"schema: {path} must be one of [{allowed}], got {data!r}"
            )

    # minLength (strings)
    if "minLength" in schema and isinstance(data, str):
        if len(data) < schema["minLength"]:
            errors.append(
                f"schema: {path} string length {len(data)} < minLength {schema['minLength']}"
            )

    # minimum (numbers)
    if "minimum" in schema and isinstance(data, (int, float)):
        if data < schema["minimum"]:
            errors.append(
                f"schema: {path} value {data} < minimum {schema['minimum']}"
            )

    # format (basic date-time check)
    if schema.get("format") == "date-time" and isinstance(data, str):
        if not _ISO8601_RE.match(data):
            errors.append(f"schema: {path} '{data}' is not a valid date-time")

    # object validation
    if isinstance(data, dict):
        # required
        for field in schema.get("required", []):
            if field not in data:
                errors.append(f"schema: {path} missing required property '{field}'")

        # properties
        prop_schemas = schema.get("properties", {})
        for key, value in data.items():
            if key in prop_schemas:
                child_path = f"{path}/{key}" if path != "(root)" else f"/{key}"
                errors.extend(
                    validate_against_schema(value, prop_schemas[key], root_schema, child_path)
                )

        # additionalProperties
        additional = schema.get("additionalProperties")
        if additional is False:
            allowed_keys = set(prop_schemas.keys())
            extra = set(data.keys()) - allowed_keys
            for key in sorted(extra):
                errors.append(
                    f"schema: {path} has unexpected property '{key}'"
                )

    # array validation
    if isinstance(data, list) and "items" in schema:
        items_schema = schema["items"]
        for i, item in enumerate(data):
            child_path = f"{path}/{i}" if path != "(root)" else f"/{i}"
            errors.extend(
                validate_against_schema(item, items_schema, root_schema, child_path)
            )

    return errors


# ---------------------------------------------------------------------------
# Cross-file consistency checks
# ---------------------------------------------------------------------------


def check_duplicate_hook_ids(data: dict) -> list[str]:
    """Check for duplicate hookId entries in pending_hooks.json."""
    errors: list[str] = []
    hooks = data.get("hooks")
    if not isinstance(hooks, list):
        return errors
    seen: dict[str, int] = {}
    for i, hook in enumerate(hooks):
        hook_id = hook.get("hookId") if isinstance(hook, dict) else None
        if isinstance(hook_id, str) and hook_id:
            if hook_id in seen:
                errors.append(
                    f"duplicate_hook_id: hookId '{hook_id}' appears at indices {seen[hook_id]} and {i}"
                )
            else:
                seen[hook_id] = i
    return errors


def check_hook_status_values(data: dict) -> list[str]:
    """Check that hook status values are within the valid enum."""
    errors: list[str] = []
    hooks = data.get("hooks")
    if not isinstance(hooks, list):
        return errors
    valid_statuses = set(HOOK_STATUS_ENUM)
    valid_timings = set(PAYOFF_TIMING_ENUM)
    for i, hook in enumerate(hooks):
        if not isinstance(hook, dict):
            continue
        status = hook.get("status")
        hook_id = hook.get("hookId", i)
        if isinstance(status, str) and status not in valid_statuses:
            errors.append(
                f"invalid_hook_status: hook '{hook_id}' has status '{status}', "
                f"expected one of [{', '.join(HOOK_STATUS_ENUM)}]"
            )
        timing = hook.get("payoffTiming")
        if isinstance(timing, str) and timing and timing not in valid_timings:
            errors.append(
                f"invalid_payoff_timing: hook '{hook_id}' has payoffTiming '{timing}', "
                f"expected one of [{', '.join(PAYOFF_TIMING_ENUM)}]"
            )
    return errors


def check_duplicate_chapter_numbers(data: dict) -> list[str]:
    """Check for duplicate chapter numbers in chapter_summaries.json."""
    errors: list[str] = []
    chapters = data.get("chapters")
    if not isinstance(chapters, list):
        return errors
    seen: dict[int, int] = {}
    for i, chapter_entry in enumerate(chapters):
        chapter = chapter_entry.get("chapter") if isinstance(chapter_entry, dict) else None
        if isinstance(chapter, int):
            if chapter in seen:
                errors.append(
                    f"duplicate_summary_chapter: chapter {chapter} appears at indices {seen[chapter]} and {i}"
                )
            else:
                seen[chapter] = i
    return errors


def check_current_state_vs_manifest(
    state_dir: str, current_state_data: dict | None
) -> list[str]:
    """Check current_state.chapter <= manifest.lastAppliedChapter."""
    errors: list[str] = []
    if current_state_data is None:
        return errors
    manifest_path = os.path.join(state_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        return errors
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError):
        return errors
    state_chapter = current_state_data.get("chapter")
    manifest_chapter = manifest.get("lastAppliedChapter")
    if (
        isinstance(state_chapter, int)
        and isinstance(manifest_chapter, int)
        and state_chapter > manifest_chapter
    ):
        errors.append(
            f"current_state_ahead_of_manifest: current_state.chapter ({state_chapter}) "
            f"> manifest.lastAppliedChapter ({manifest_chapter})"
        )
    return errors


def check_delta_consistency(data: dict) -> list[str]:
    """Check delta-specific consistency: chapter mismatch, duplicate upsert hookIds."""
    errors: list[str] = []
    delta_chapter = data.get("chapter")
    summary = data.get("chapterSummary")
    if isinstance(summary, dict) and isinstance(delta_chapter, int):
        summary_chapter = summary.get("chapter")
        if isinstance(summary_chapter, int) and summary_chapter != delta_chapter:
            errors.append(
                f"delta_chapter_mismatch: delta.chapter ({delta_chapter}) "
                f"!= chapterSummary.chapter ({summary_chapter})"
            )
    hook_ops = data.get("hookOps")
    if isinstance(hook_ops, dict):
        upsert = hook_ops.get("upsert")
        if isinstance(upsert, list):
            seen: dict[str, int] = {}
            for i, hook in enumerate(upsert):
                hook_id = hook.get("hookId") if isinstance(hook, dict) else None
                if isinstance(hook_id, str) and hook_id:
                    if hook_id in seen:
                        errors.append(
                            f"duplicate_upsert_hook_id: hookId '{hook_id}' "
                            f"appears in upsert at indices {seen[hook_id]} and {i}"
                        )
                    else:
                        seen[hook_id] = i
    return errors


# ---------------------------------------------------------------------------
# Main validation logic
# ---------------------------------------------------------------------------


def find_schema(
    base_name: str, loaded_schemas: dict[str, dict]
) -> dict | None:
    """Determine which schema applies to a file by its basename."""
    # 1. Direct name match (covers both truth files and pipeline artifacts)
    if base_name in loaded_schemas:
        return loaded_schemas[base_name]
    # 2. Pattern-based matching for runtime files
    if base_name.endswith(".delta.json"):
        return loaded_schemas.get("delta.json")
    if base_name.endswith(".context.json"):
        return loaded_schemas.get("context-package.json")
    if base_name.endswith(".intent.json"):
        return loaded_schemas.get("chapter-intent.json")
    if base_name.endswith(".rule-stack.json"):
        return loaded_schemas.get("rule-stack.json")
    if base_name.endswith(".review-status.json") or base_name == "review-status.json":
        return loaded_schemas.get("review-status.json")
    if base_name.endswith(".revision-log.json") or base_name == "revision-log.json":
        return loaded_schemas.get("revision-log.json")
    if base_name.endswith(".audit.json") or base_name == "audit-report.json":
        return loaded_schemas.get("audit-report.json")
    # 3. Manifest (inline schema, no canonical file)
    if base_name == "manifest.json":
        return MANIFEST_SCHEMA
    return None


def validate_file(file_path: str, loaded_schemas: dict[str, dict]) -> dict:
    """Validate a single JSON file. Returns {file, valid, errors, warnings}."""
    errors: list[str] = []
    warnings: list[str] = []

    if not os.path.isfile(file_path):
        return {"file": file_path, "valid": False, "errors": ["File not found"], "warnings": []}

    # Parse JSON
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {"file": file_path, "valid": False, "errors": [f"Invalid JSON: {e}"], "warnings": []}
    except OSError as e:
        return {"file": file_path, "valid": False, "errors": [f"Cannot read file: {e}"], "warnings": []}

    base_name = os.path.basename(file_path)
    state_dir = os.path.dirname(file_path)

    # Find matching schema
    schema = find_schema(base_name, loaded_schemas)
    if schema is not None:
        root_schema = schema
        errors.extend(validate_against_schema(data, schema, root_schema))
    else:
        warnings.append(f"No matching schema for {base_name} (skipping schema validation)")

    # Cross-file / semantic checks
    if base_name == "pending_hooks.json":
        errors.extend(check_duplicate_hook_ids(data))
        errors.extend(check_hook_status_values(data))

    if base_name == "chapter_summaries.json":
        errors.extend(check_duplicate_chapter_numbers(data))

    if base_name == "current_state.json":
        errors.extend(check_current_state_vs_manifest(state_dir, data))

    if base_name.endswith(".delta.json") or base_name == "delta.json":
        errors.extend(check_delta_consistency(data))

    return {
        "file": file_path,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(
            "Usage: schema-validate.py <file> [file ...]\n"
            "  Validates JSON files against their JSON Schema definitions.\n"
            "  Exit 0 if all valid, 1 if any errors.",
            file=sys.stderr,
        )
        return 1 if not args else 0

    loaded_schemas = load_schemas()
    results = []
    all_valid = True

    for arg in args:
        file_path = os.path.abspath(arg)
        result = validate_file(file_path, loaded_schemas)
        results.append(result)
        if not result["valid"]:
            all_valid = False

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
