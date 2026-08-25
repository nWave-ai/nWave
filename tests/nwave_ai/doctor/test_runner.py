"""Acceptance tests for run_doctor() runner integration.

Tests enter through run_doctor() as the driving port.
Integration tests stage a fake ~/.claude in tmp_path for hermetic filesystem checks.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

from nwave_ai.doctor.runner import run_doctor


if TYPE_CHECKING:
    from pathlib import Path


def _stage_healthy_claude(base: Path) -> Path:
    """Stage a minimal healthy ~/.claude directory under base.

    Returns:
        Path to the staged .claude directory.
    """
    claude_dir = base / ".claude"
    claude_dir.mkdir(parents=True)

    # Create bin/ with all 5 shims
    bin_dir = claude_dir / "bin"
    bin_dir.mkdir()
    for shim in (
        "des-log-phase",
        "des-init-log",
        "des-verify-integrity",
        "des-roadmap",
        "des-health-check",
    ):
        shim_path = bin_dir / shim
        shim_path.write_text("#!/usr/bin/env python3\n")
        shim_path.chmod(0o755)

    # Create lib/python/des/domain/phase_events.py
    des_dir = claude_dir / "lib" / "python" / "des" / "domain"
    des_dir.mkdir(parents=True)
    (des_dir / "phase_events.py").write_text("")

    # Create framework dirs with at least 1 .md file each (mirrors FrameworkFilesCheck expectations)
    for subdir in ("agents", "skills", "commands"):
        dir_path = claude_dir / subdir
        dir_path.mkdir()
        (dir_path / "placeholder.md").write_text("# placeholder\n")

    # Create settings.json with all 5 hooks and env.PATH
    python_path = sys.executable
    hook_command = (
        f"PYTHONPATH=$HOME/.claude/lib/python {python_path} "
        "-m des.adapters.drivers.hooks.claude_code_hook_adapter PreToolUse"
    )
    settings = {
        "hooks": {
            "PreToolUse": [{"hooks": [{"command": hook_command}]}],
            "PostToolUse": [{"hooks": [{"command": hook_command}]}],
            "SubagentStop": [{"hooks": [{"command": hook_command}]}],
            "SessionStart": [{"hooks": [{"command": hook_command}]}],
            "SubagentStart": [{"hooks": [{"command": hook_command}]}],
        },
        "env": {
            "PATH": f"{bin_dir}:/usr/bin:/bin",
        },
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings))

    return claude_dir


def test_runner_executes_all_10_checks(tmp_path: Path) -> None:
    """run_doctor() returns exactly 10 results — one per check.

    Step 02-02 added DensityCheck (D6 + D12), bumping the total from 7 to 8.
    The claude-code-attribution-migration feature added AttributionCheck (R7),
    bumping the total from 8 to 9. The install-version-drift feature added
    VersionSyncCheck, bumping the total from 9 to 10.
    """
    from nwave_ai.doctor.context import DoctorContext

    _stage_healthy_claude(tmp_path)
    context = DoctorContext(home_dir=tmp_path)

    results = run_doctor(context)

    assert len(results) == 10


def test_runner_preserves_check_order(tmp_path: Path) -> None:
    """result order matches registration order: PythonVersion first, attribution last."""
    from nwave_ai.doctor.context import DoctorContext

    _stage_healthy_claude(tmp_path)
    context = DoctorContext(home_dir=tmp_path)

    results = run_doctor(context)

    assert results[0].check_name == "python_version"
    assert results[1].check_name == "des_module"
    assert results[2].check_name == "hooks_registered"
    assert results[3].check_name == "hook_python_path"
    assert results[4].check_name == "shims_deployed"
    assert results[5].check_name == "path_env"
    assert results[6].check_name == "framework_files"
    assert results[7].check_name == "documentation_density"
    assert results[8].check_name == "attribution"
    assert results[9].check_name == "version_sync"
