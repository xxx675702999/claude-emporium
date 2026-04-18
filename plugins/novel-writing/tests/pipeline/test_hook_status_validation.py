"""apply_hook_ops raises HookStatusEnumError on invalid status."""
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


def _upsert_with_status(status):
    return {
        "chapter": 1,
        "hookOps": {
            "upsert": [{
                "hookId": "H1_1",
                "startChapter": 1,
                "type": "信息/疑点",
                "status": status,
                "lastAdvancedChapter": 1,
                "notes": "x",
            }]
        },
    }


@pytest.mark.parametrize("status", [
    "open", "progressing", "escalating", "critical", "deferred", "resolved",
])
def test_valid_statuses_accepted(apply_delta_mod, status):
    result = apply_delta_mod.apply_hook_ops([], _upsert_with_status(status), chapter=1)
    assert result[0]["status"] == status


@pytest.mark.parametrize("status", ["crítica", "unknown", "", "CRITICAL"])
def test_invalid_status_raises(apply_delta_mod, status):
    from lib.pipeline_errors import HookStatusEnumError
    with pytest.raises(HookStatusEnumError) as exc:
        apply_delta_mod.apply_hook_ops([], _upsert_with_status(status), chapter=1)
    # Error message mentions the hookId
    assert "H1_1" in str(exc.value)
