"""apply_current_state_patch normalizes predicate keys to book language."""
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


def test_zh_book_normalizes_to_chinese_keys(apply_delta_mod):
    """With book.language=zh, English patch keys are mapped to Chinese canonical side."""
    state = {"version": 1, "chapter": 0, "facts": []}
    delta = {
        "chapter": 1,
        "currentStatePatch": {"currentLocation": "hotel lobby"},
    }
    result = apply_delta_mod.apply_current_state_patch(
        state, delta, chapter=1, book_language="zh"
    )
    preds = [f["predicate"] for f in result["facts"]]
    assert "当前位置" in preds
    assert "currentLocation" not in preds


def test_en_book_normalizes_to_english_keys(apply_delta_mod):
    state = {"version": 1, "chapter": 0, "facts": []}
    delta = {
        "chapter": 1,
        "currentStatePatch": {"当前位置": "地下室"},
    }
    result = apply_delta_mod.apply_current_state_patch(
        state, delta, chapter=1, book_language="en"
    )
    preds = [f["predicate"] for f in result["facts"]]
    assert "currentLocation" in preds
    assert "当前位置" not in preds


def test_unknown_predicate_passes_through(apply_delta_mod):
    state = {"version": 1, "chapter": 0, "facts": []}
    delta = {
        "chapter": 1,
        "currentStatePatch": {"customField": "value"},
    }
    result = apply_delta_mod.apply_current_state_patch(
        state, delta, chapter=1, book_language="zh"
    )
    preds = [f["predicate"] for f in result["facts"]]
    assert "customField" in preds


def test_mixed_language_patch_consolidates(apply_delta_mod):
    """Both zh and en in the same patch collapse to one canonical entry."""
    state = {"version": 1, "chapter": 0, "facts": []}
    delta = {
        "chapter": 1,
        "currentStatePatch": {
            "currentLocation": "lobby",
            "当前目标": "survive",
        },
    }
    result = apply_delta_mod.apply_current_state_patch(
        state, delta, chapter=1, book_language="zh"
    )
    preds = sorted(f["predicate"] for f in result["facts"])
    assert preds == ["当前位置", "当前目标"]


def test_post_apply_duplicate_detection_raises(apply_delta_mod):
    """If historical state already has both zh and en for the same predicate,
    raise PredicateAliasError so migration can be run."""
    from lib.pipeline_errors import PredicateAliasError
    state = {
        "version": 1, "chapter": 0,
        "facts": [
            {"subject": "Protagonist", "predicate": "当前位置",
             "object": "lobby", "validFromChapter": 1, "validUntilChapter": None},
            {"subject": "Protagonist", "predicate": "currentLocation",
             "object": "lobby", "validFromChapter": 1, "validUntilChapter": None},
        ],
    }
    delta = {"chapter": 2, "currentStatePatch": {"currentGoal": "x"}}
    with pytest.raises(PredicateAliasError):
        apply_delta_mod.apply_current_state_patch(
            state, delta, chapter=2, book_language="zh"
        )
