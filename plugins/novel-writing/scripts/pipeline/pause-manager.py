#!/usr/bin/env python3
"""
pause-manager.py — Smart pause logic for the novel-writing pipeline.

Determines whether the pipeline should pause at a given stage based on
the resolved automation mode, audit results, and command-flag overrides.

Usage:
    from pause_manager import should_pause, resolve_mode
    result = resolve_mode(session_mode, flags)
    pause = should_pause(result.mode, stage, audit_result, flags)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# -- Types --------------------------------------------------------------------

Mode = Literal["interactive", "batch"]
LegacyMode = Literal["auto", "semi", "manual"]
SessionMode = Mode | LegacyMode
Stage = Literal["prepare", "write", "persist", "audit", "revise"]


@dataclass
class AuditResult:
    """Number of issues with severity 'critical' in audit-report.json."""
    critical_count: int


@dataclass
class FlagOverrides:
    yes: bool = field(default=False)       # --yes: skip all confirmation prompts
    dry_run: bool = field(default=False)   # --dry-run: stop after prepare (display intent only)
    pause_on: Stage | None = field(default=None)  # --pause-on: force pause at specific stage
    batch: bool = field(default=False)     # --batch: override session mode to batch for this run


@dataclass
class ModeResolution:
    mode: Mode
    warning: str | None = field(default=None)


# -- Mode resolution (REQ-F-20) -----------------------------------------------

def resolve_mode(
    session_mode: SessionMode | None,
    flags: FlagOverrides,
) -> ModeResolution:
    """
    Resolve the effective automation mode from the session value and flags.

    Legacy mapping: "auto"→"batch", "semi"→"interactive",
      "manual"→"interactive" (+ warning)
    The --batch flag overrides any resolved mode to "batch".
    """
    mode: Mode
    warning: str | None = None

    if session_mode == "batch":
        mode = "batch"
    elif session_mode == "interactive":
        mode = "interactive"
    elif session_mode == "auto":
        mode = "batch"
    elif session_mode == "semi":
        mode = "interactive"
    elif session_mode == "manual":
        mode = "interactive"
        warning = (
            'manual mode has been removed; using interactive mode. '
            'Update .session.json to "interactive" or "batch".'
        )
    else:
        mode = "interactive"

    if flags.batch:
        mode = "batch"
        warning = None

    return ModeResolution(mode=mode, warning=warning)


# -- Pause decision (REQ-F-17, REQ-F-18, REQ-F-19) ---------------------------

def should_pause(
    mode: Mode,
    stage: Stage,
    audit: AuditResult | None,
    flags: FlagOverrides,
) -> bool:
    """
    Determine whether the pipeline should pause at the given stage.

    | Mode        | Stage  | Condition          | Pause? |
    |-------------|--------|--------------------|--------|
    | interactive | write  | always             | true   |
    | interactive | revise | criticalCount > 2  | true   |
    | interactive | revise | criticalCount <= 2 | false  |
    | interactive | other  | -                  | false  |
    | batch       | any    | -                  | false  |

    Overrides: --yes → false, --pause-on <stage> → true for that stage.
    --dry-run is handled externally (pipeline stops after prepare).
    """
    # --yes skips all pauses (unless --pause-on targets this stage)
    if flags.yes:
        return flags.pause_on == stage

    # --pause-on forces a pause at the specified stage regardless of mode
    if flags.pause_on == stage:
        return True

    # Batch mode: zero pauses
    if mode == "batch":
        return False

    # Interactive mode: smart pause logic
    if stage == "write":
        return True
    if stage == "revise":
        return audit is not None and audit.critical_count > 2
    return False


# -- Auto-revise decision -----------------------------------------------------

def should_auto_revise(
    mode: Mode,
    audit: AuditResult | None,
    flags: FlagOverrides,
) -> bool:
    """
    Returns True when revision should be auto-executed without user prompt.
    In batch mode, always auto-revise on critical issues.
    In interactive mode, auto-revise when <=2 critical issues or --yes.
    """
    if not audit or audit.critical_count == 0:
        return False

    if mode == "batch" or flags.yes:
        return True

    # Interactive: auto-revise when <=2 critical (no pause needed)
    return mode == "interactive" and audit.critical_count <= 2
