"""json_utils — Safe JSON file read/write with atomic updates.

Replaces all jq calls with pure-Python equivalents. Uses atomic
write (tempfile + os.replace) to prevent partial writes on crash.
CJK content is preserved via ensure_ascii=False.
"""

import json
import os
import tempfile
from typing import Any, Callable


def read_json(path: str) -> dict | list | None:
    """Read a JSON file and return its parsed content.

    Returns None if the file is missing, unreadable, or contains
    invalid JSON.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def write_json(path: str, data: Any, indent: int = 2) -> None:
    """Atomically write data as JSON to the given path.

    Writes to a temporary file in the same directory, then uses
    os.replace() for an atomic rename. Always ends with a newline.
    CJK characters are preserved (ensure_ascii=False).
    """
    dir_name = os.path.dirname(path) or "."
    os.makedirs(dir_name, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up temp file on any failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def update_json(
    path: str,
    transform_fn: Callable[[Any], Any],
    default: Any = None,
) -> Any:
    """Read a JSON file, apply a transform function, and write it back atomically.

    Returns the transformed data. The transform_fn receives the parsed
    JSON data and must return the new data to write. If the file does
    not exist and no default is provided, raises FileNotFoundError.
    If default is provided, it is used when the file is missing.
    """
    data = read_json(path)
    if data is None:
        if not os.path.exists(path) and default is None:
            raise FileNotFoundError(f"JSON file not found: {path}")
        data = default

    new_data = transform_fn(data)
    write_json(path, new_data)
    return new_data
