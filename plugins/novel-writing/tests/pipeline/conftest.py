"""Shared fixtures for subsystem-1 tests."""
from pathlib import Path
import shutil
import sys

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
FIXTURES_DIR = PLUGIN_ROOT / "tests" / "fixtures" / "subsystem-1"

# Make scripts/lib importable
sys.path.insert(0, str(SCRIPTS_DIR))
# Allow `from conftest import ...` in sibling test files
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture
def zh_book(tmp_path):
    """Copy the zh-book fixture into a tmp dir and return the book path."""
    src = FIXTURES_DIR / "books" / "zh-book"
    dst = tmp_path / "zh-book"
    shutil.copytree(src, dst)
    return dst


@pytest.fixture
def malformed_hooks_book(tmp_path):
    """Copy the malformed-hooks fixture into a tmp dir and return the book path."""
    src = FIXTURES_DIR / "books" / "malformed-hooks"
    dst = tmp_path / "malformed-hooks"
    shutil.copytree(src, dst)
    return dst
