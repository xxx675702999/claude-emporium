"""Validate ResourceLedgerOp.delta is required and non-empty."""
import json

import jsonschema
import pytest

from conftest import PLUGIN_ROOT

SCHEMA_PATH = PLUGIN_ROOT / "data" / "schemas" / "delta.json"


@pytest.fixture
def ledger_op_validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return jsonschema.Draft7Validator(schema["definitions"]["resourceLedgerOp"])


def _op(**overrides):
    base = {
        "op": "snapshot",
        "id": "r1",
        "name": "灵石",
        "type": "currency",
        "owner": "protagonist",
        "openingState": "1000",
        "closingState": "900",
        "delta": "-100 spent",
    }
    base.update(overrides)
    return base


def test_complete_op_passes(ledger_op_validator):
    ledger_op_validator.validate(_op())


def test_missing_delta_fails(ledger_op_validator):
    op = _op()
    del op["delta"]
    with pytest.raises(jsonschema.ValidationError):
        ledger_op_validator.validate(op)


def test_empty_delta_string_fails(ledger_op_validator):
    with pytest.raises(jsonschema.ValidationError):
        ledger_op_validator.validate(_op(delta=""))


def test_initial_keyword_passes(ledger_op_validator):
    ledger_op_validator.validate(_op(delta="initial"))
