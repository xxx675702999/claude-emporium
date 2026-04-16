"""apply_hook_ops rejects malformed hookIds and raises HookIdFormatError."""
import importlib.util
import sys

import pytest

from conftest import SCRIPTS_DIR


def _load_apply_delta():
    """Load apply-delta.py (name contains a hyphen so importlib is needed)."""
    path = SCRIPTS_DIR / "pipeline" / "apply-delta.py"
    spec = importlib.util.spec_from_file_location("apply_delta_mod", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["apply_delta_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def apply_delta_mod():
    return _load_apply_delta()


def _delta_with_upsert(hook_id):
    return {
        "chapter": 1,
        "hookOps": {
            "upsert": [{
                "hookId": hook_id,
                "startChapter": 1,
                "type": "信息/疑点",
                "status": "open",
                "lastAdvancedChapter": 1,
                "notes": "x",
            }]
        },
    }


def test_valid_hook_id_upserts(apply_delta_mod):
    result = apply_delta_mod.apply_hook_ops([], _delta_with_upsert("H1_1"), chapter=1)
    assert any(h["hookId"] == "H1_1" for h in result)


@pytest.mark.parametrize("bad_id", ["H15 (新增)", "H15(新增)", "h15", "H15-1", "foo"])
def test_malformed_hook_id_upsert_raises(apply_delta_mod, bad_id):
    from lib.pipeline_errors import HookIdFormatError
    with pytest.raises(HookIdFormatError) as exc:
        apply_delta_mod.apply_hook_ops([], _delta_with_upsert(bad_id), chapter=1)
    assert bad_id in str(exc.value)


def test_malformed_hook_id_mention_raises(apply_delta_mod):
    from lib.pipeline_errors import HookIdFormatError
    delta = {"chapter": 1, "hookOps": {"mention": ["H15 (新增)"]}}
    with pytest.raises(HookIdFormatError):
        apply_delta_mod.apply_hook_ops([{"hookId": "H1_1"}], delta, chapter=1)


def test_malformed_hook_id_resolve_raises(apply_delta_mod):
    from lib.pipeline_errors import HookIdFormatError
    delta = {"chapter": 1, "hookOps": {"resolve": ["H15 (新增)"]}}
    with pytest.raises(HookIdFormatError):
        apply_delta_mod.apply_hook_ops([{"hookId": "H1_1"}], delta, chapter=1)


def test_malformed_hook_id_defer_raises(apply_delta_mod):
    from lib.pipeline_errors import HookIdFormatError
    delta = {"chapter": 1, "hookOps": {"defer": ["H15 (新增)"]}}
    with pytest.raises(HookIdFormatError):
        apply_delta_mod.apply_hook_ops([{"hookId": "H1_1"}], delta, chapter=1)
