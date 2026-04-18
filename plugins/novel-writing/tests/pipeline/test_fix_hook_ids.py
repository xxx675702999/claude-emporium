"""fix-hook-ids.py migration script (C7)."""
import json
import subprocess
import sys

from conftest import SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "pipeline" / "fix-hook-ids.py"


def test_dry_run_reports_plan_without_writing(malformed_hooks_book):
    hooks_file = malformed_hooks_book / "story" / "state" / "pending_hooks.json"
    original = hooks_file.read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(malformed_hooks_book),
         "--dry-run", "--auto-merge"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "H15 (新增)" in result.stdout
    assert "H16 (新增)" in result.stdout
    # File untouched
    assert hooks_file.read_text(encoding="utf-8") == original


def test_auto_merge_drops_dup_and_renames_orphan(malformed_hooks_book):
    hooks_file = malformed_hooks_book / "story" / "state" / "pending_hooks.json"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(malformed_hooks_book), "--auto-merge"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr

    data = json.loads(hooks_file.read_text(encoding="utf-8"))
    ids = sorted(h["hookId"] for h in data["hooks"])

    # "H15 (新增)" collided with existing H15 → dropped under --auto-merge
    assert "H15 (新增)" not in ids
    assert "H15" in ids

    # "H16 (新增)" had no collision → renamed to H16 (or H16_1 if H16 existed)
    assert "H16 (新增)" not in ids
    h16_like = [i for i in ids if i == "H16" or i.startswith("H16_")]
    assert len(h16_like) == 1, f"unexpected H16 family: {h16_like}"

    # Every remaining id matches the canonical pattern
    import re
    pat = re.compile(r"^H\d+(_\d+)?$")
    for hid in ids:
        assert pat.match(hid), f"leftover bad id: {hid}"


def test_interactive_mode_without_tty_fails_cleanly(malformed_hooks_book):
    """Without --auto-merge and with stdin closed, the script exits non-zero cleanly."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(malformed_hooks_book)],
        input="",
        capture_output=True, text=True, timeout=30,
    )
    assert (
        result.returncode != 0
        or "conflict" in result.stdout.lower()
        or "non-interactive" in result.stderr.lower()
    )
