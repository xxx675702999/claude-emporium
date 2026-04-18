"""apply_resource_ledger_ops raises on missing required fields."""
import importlib.util
import sys

import pytest

from conftest import SCRIPTS_DIR


def _load_apply_delta():
    path = SCRIPTS_DIR / "pipeline" / "apply-delta.py"
    spec = importlib.util.spec_from_file_location("apply_delta_mod", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["apply_delta_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def apply_delta_mod():
    return _load_apply_delta()


def _complete_op(**overrides):
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


def test_complete_op_applies(apply_delta_mod):
    data = {"version": 1, "resources": []}
    delta = {"resourceLedgerOps": [_complete_op()]}
    result = apply_delta_mod.apply_resource_ledger_ops(data, delta, chapter=1)
    assert len(result["resources"]) == 1
    assert result["resources"][0]["delta"] == "-100 spent"


@pytest.mark.parametrize("missing_field", [
    "op", "id", "name", "type", "owner", "openingState", "closingState", "delta",
])
def test_missing_required_field_raises(apply_delta_mod, missing_field):
    from lib.pipeline_errors import ResourceLedgerFieldError
    op = _complete_op()
    del op[missing_field]
    delta = {"resourceLedgerOps": [op]}
    with pytest.raises(ResourceLedgerFieldError) as exc:
        apply_delta_mod.apply_resource_ledger_ops(
            {"version": 1, "resources": []}, delta, chapter=1
        )
    assert missing_field in str(exc.value)


def test_invalid_op_value_raises(apply_delta_mod):
    from lib.pipeline_errors import ResourceLedgerFieldError
    delta = {"resourceLedgerOps": [_complete_op(op="delete")]}
    with pytest.raises(ResourceLedgerFieldError) as exc:
        apply_delta_mod.apply_resource_ledger_ops(
            {"version": 1, "resources": []}, delta, chapter=1
        )
    assert "'delete'" in str(exc.value)


def test_empty_delta_string_raises(apply_delta_mod):
    from lib.pipeline_errors import ResourceLedgerFieldError
    delta = {"resourceLedgerOps": [_complete_op(delta="")]}
    with pytest.raises(ResourceLedgerFieldError):
        apply_delta_mod.apply_resource_ledger_ops(
            {"version": 1, "resources": []}, delta, chapter=1
        )
