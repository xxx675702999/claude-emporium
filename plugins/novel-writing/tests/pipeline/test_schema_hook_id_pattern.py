"""Validate HookRecord.hookId pattern in delta.json schema."""
import json
from pathlib import Path

import jsonschema
import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PLUGIN_ROOT / "data" / "schemas" / "delta.json"


@pytest.fixture
def hook_validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    # Resolve the hookRecord subschema via $ref
    registry = {"": schema}
    hook_schema = schema["definitions"]["hookRecord"]
    return jsonschema.Draft7Validator(hook_schema)


def _hook(hook_id):
    return {
        "hookId": hook_id,
        "startChapter": 1,
        "type": "信息/疑点",
        "status": "open",
        "lastAdvancedChapter": 1,
        "notes": "x",
    }


@pytest.mark.parametrize("hid", ["H1", "H15", "H15_1", "H15_23", "H0", "H0_1"])
def test_valid_hook_ids_pass(hook_validator, hid):
    hook_validator.validate(_hook(hid))


@pytest.mark.parametrize("hid", [
    "H15 (新增)",
    "H15(新增)",
    "H15 (new)",
    "h15",
    "H",
    "H15_",
    "H15_1_2",
    "foo",
    "H15-1",
])
def test_invalid_hook_ids_fail(hook_validator, hid):
    with pytest.raises(jsonschema.ValidationError):
        hook_validator.validate(_hook(hid))
