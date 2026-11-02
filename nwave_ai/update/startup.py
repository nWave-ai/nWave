"""Project idle evidence and non-mutating native-startup guidance."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from nwave_ai.platform.update_timing import UPDATE_TIMING
from nwave_ai.update.permissions import update_permissions


def _idle_root(cwd: Path) -> tuple[Path | None, str]:
    try:
        top = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=UPDATE_TIMING.repository_probe_seconds,
        )
        if top.returncode or not top.stdout.strip():
            return None, "repository work state could not be established"
        root = Path(top.stdout.strip()).resolve()
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
            check=False,
            timeout=UPDATE_TIMING.repository_probe_seconds,
        )
        if status.returncode:
            return None, "repository work state could not be established"
        if status.stdout.strip():
            return None, "the repository has work in progress"
        des_dir = root / ".nwave" / "des"
        # The hook's own freshness/audit output lands in ``logs`` before this
        # handler runs; it records hook activity, not wave state. Every other
        # entry still counts as possible work in progress.
        if des_dir.exists() and any(
            entry.name != "logs" for entry in des_dir.iterdir()
        ):
            return None, "DES work state is present and may still be in progress"
        feature_dir = root / "docs" / "feature"
        if feature_dir.exists() and any(feature_dir.iterdir()):
            return (
                None,
                "feature work state is present and wave completion is not established",
            )
        return root, ""
    except (OSError, subprocess.TimeoutExpired):
        return None, "repository work state could not be established"


def startup_update_context(envelope: str) -> str:
    """Native hooks advise; only controlled prelaunch may check or install."""
    try:
        event = json.loads(envelope)
    except (TypeError, json.JSONDecodeError):
        return ""
    if not isinstance(event, dict) or event.get("source") != "startup":
        return ""
    check, _install = update_permissions()
    if not check:
        return ""
    from nwave_ai.update.service import UpdateService

    pending = UpdateService.pending_update()
    if pending is not None:
        return (
            f"Automatic update refused: {pending.cause}. Recovery: {pending.recovery}"
        )
    return (
        "Automatic update skipped: native hooks cannot prove global idle or block "
        "new work. Use `nwave-ai run HOST -- ARGS` for consented startup checks "
        "and installation before the host starts."
    )
