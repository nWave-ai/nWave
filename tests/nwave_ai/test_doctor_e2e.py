"""E2E regression tests for `nwave-ai doctor`.

Stages a fake healthy ~/.claude in tmp_path and exercises the full
doctor stack (runner + all 7 checks + formatter) through DoctorContext.
Each broken-variant test removes or corrupts exactly one piece and asserts
the correct check fails with the expected remediation text.

AC coverage:
  01-05 AC1: healthy install → exit 0, 7 passing checks
  01-05 AC2: shims missing → ShimsDeployedCheck fails, remediation mentions nwave-ai install
  01-05 AC3: empty hooks in settings.json → HooksRegisteredCheck fails
  01-05 AC4: non-existent Python binary in hook command → HookPythonPathCheck fails
  01-05 AC5: JSON summary.passed == ✅ count in human output
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

from nwave_ai.doctor.context import DoctorContext
from nwave_ai.doctor.formatter import render_human, render_json
from nwave_ai.doctor.runner import run_doctor


if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Staging helper
# ---------------------------------------------------------------------------


def stage_healthy_install(base: Path) -> Path:
    """Stage a complete healthy fake ~/.claude directory under base.

    Creates the minimum layout that satisfies all 7 doctor checks:
      - bin/ with 5 shims (chmod 755)
      - settings.json with all 5 hook types + real python binary + env.PATH
      - lib/python/des/domain/phase_events.py
      - agents/, skills/, commands/ each containing >= 1 file

    Args:
        base: Root directory for the staged home (i.e. tmp_path).

    Returns:
        Path to the staged .claude directory.
    """
    claude_dir = base / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # 1. bin/ with all 5 shims, executable
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

    # 2. DES runtime module
    des_dir = claude_dir / "lib" / "python" / "des" / "domain"
    des_dir.mkdir(parents=True)
    (des_dir / "phase_events.py").write_text("# stub\n")

    # 3. Framework directories — realistic install layout:
    #    agents/nw/*.md (nested under nw/ subdir)
    #    skills/*/SKILL.md (each skill is a subdirectory)
    #    commands/*.md (direct files)
    agents_nw = claude_dir / "agents" / "nw"
    agents_nw.mkdir(parents=True)
    (agents_nw / "nw-foo.md").write_text("# agent stub\n")

    skill_dir = claude_dir / "skills" / "nw-bar"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# skill stub\n")

    commands_dir = claude_dir / "commands"
    commands_dir.mkdir()
    (commands_dir / "nw-baz.md").write_text("# command stub\n")

    # 4. settings.json — all 5 hook types, real python binary, env.PATH
    python_path = sys.executable
    hook_command = (
        f"PYTHONPATH=$HOME/.claude/lib/python {python_path} "
        "-m des.adapters.drivers.hooks.claude_code_hook_adapter PreToolUse"
    )
    settings: dict = {
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


# ---------------------------------------------------------------------------
# AC1 — healthy install: exit 0, all 7 checks pass
# ---------------------------------------------------------------------------


def test_doctor_reports_healthy_install(tmp_path: Path) -> None:
    """Healthy staged install: runner returns 9 results, all passed=True.

    Given a complete fake ~/.claude with shims, settings.json, DES module,
    and framework directories,
    When doctor runs,
    Then all 9 checks pass and there are no failures.

    Step 02-02 added DensityCheck (D6 + D12), bumping the count from 7 to 8.
    The claude-code-attribution-migration feature added AttributionCheck (R7),
    a read-only diagnostic that always passes, bumping the count from 8 to 9.
    A fresh tmp_path home has no `~/.nwave/global-config.json`, so density
    resolves to the lean default branch and the check passes.
    """
    stage_healthy_install(tmp_path)
    context = DoctorContext(home_dir=tmp_path)

    results = run_doctor(context)

    assert len(results) == 9, f"Expected 9 results, got {len(results)}"
    failed = [r for r in results if not r.passed]
    assert not failed, "Expected all checks to pass, but these failed: " + ", ".join(
        f"{r.check_name}: {r.message}" for r in failed
    )


# ---------------------------------------------------------------------------
# AC2 — missing shims → ShimsDeployedCheck fails
# ---------------------------------------------------------------------------


def test_doctor_detects_missing_shims(tmp_path: Path) -> None:
    """Missing bin/ shims: ShimsDeployedCheck fails with nwave-ai install remediation.

    Given a healthy install with the entire bin/ directory removed,
    When doctor runs,
    Then exactly ShimsDeployedCheck fails and its remediation mentions nwave-ai install.
    """
    claude_dir = stage_healthy_install(tmp_path)

    # Remove the shims dir entirely
    import shutil

    shutil.rmtree(claude_dir / "bin")

    context = DoctorContext(home_dir=tmp_path)
    results = run_doctor(context)

    # Find the shims check result
    shims_result = next((r for r in results if r.check_name == "shims_deployed"), None)
    assert shims_result is not None, "shims_deployed check not found in results"
    assert not shims_result.passed, (
        f"Expected shims_deployed to fail, but it passed: {shims_result.message}"
    )
    assert shims_result.remediation is not None
    assert "nwave-ai install" in shims_result.remediation, (
        f"Expected remediation to mention 'nwave-ai install', got: {shims_result.remediation!r}"
    )

    # Overall: at least one failure (shims), so aggregate should detect failures
    failed_names = [r.check_name for r in results if not r.passed]
    assert "shims_deployed" in failed_names


# ---------------------------------------------------------------------------
# AC3 — empty hooks in settings.json → HooksRegisteredCheck fails
# ---------------------------------------------------------------------------


def test_doctor_detects_missing_hook_entries(tmp_path: Path) -> None:
    """Empty hooks dict: HooksRegisteredCheck fails.

    Given a healthy install where settings.json has an empty 'hooks' object,
    When doctor runs,
    Then HooksRegisteredCheck fails.
    """
    claude_dir = stage_healthy_install(tmp_path)

    # Overwrite settings.json with empty hooks
    settings_path = claude_dir / "settings.json"
    current = json.loads(settings_path.read_text())
    current["hooks"] = {}
    settings_path.write_text(json.dumps(current))

    context = DoctorContext(home_dir=tmp_path)
    results = run_doctor(context)

    hooks_result = next(
        (r for r in results if r.check_name == "hooks_registered"), None
    )
    assert hooks_result is not None, "hooks_registered check not found in results"
    assert not hooks_result.passed, (
        f"Expected hooks_registered to fail, but it passed: {hooks_result.message}"
    )


# ---------------------------------------------------------------------------
# AC4 — stale python path in hook command → HookPythonPathCheck fails
# ---------------------------------------------------------------------------


def test_doctor_detects_stale_hook_python_path(tmp_path: Path) -> None:
    """Non-existent python binary in hook command: HookPythonPathCheck fails.

    Given a healthy install where settings.json references a python binary
    at a path that does not exist on disk,
    When doctor runs,
    Then HookPythonPathCheck fails.
    """
    claude_dir = stage_healthy_install(tmp_path)

    # Overwrite hook command to reference a non-existent python path
    stale_python = "/nonexistent/path/to/python3"
    stale_command = (
        f"PYTHONPATH=$HOME/.claude/lib/python {stale_python} "
        "-m des.adapters.drivers.hooks.claude_code_hook_adapter PreToolUse"
    )
    settings_path = claude_dir / "settings.json"
    current = json.loads(settings_path.read_text())
    for hook_type in current["hooks"]:
        current["hooks"][hook_type] = [{"hooks": [{"command": stale_command}]}]
    settings_path.write_text(json.dumps(current))

    context = DoctorContext(home_dir=tmp_path)
    results = run_doctor(context)

    python_path_result = next(
        (r for r in results if r.check_name == "hook_python_path"), None
    )
    assert python_path_result is not None, "hook_python_path check not found in results"
    assert not python_path_result.passed, (
        f"Expected hook_python_path to fail, but it passed: {python_path_result.message}"
    )


# ---------------------------------------------------------------------------
# AC5 — JSON summary.passed == ✅ count in human output
# ---------------------------------------------------------------------------


def test_doctor_json_output_matches_human_semantics(tmp_path: Path) -> None:
    """JSON summary.passed equals the number of ✅ lines in human output.

    Given the same staged environment,
    When doctor produces both human and JSON output,
    Then JSON summary.passed equals the count of ✅ lines in human output.
    """
    stage_healthy_install(tmp_path)
    context = DoctorContext(home_dir=tmp_path)

    results = run_doctor(context)

    human_output = render_human(results)
    json_output = render_json(results)

    # Count ✅ lines in human output
    checkmark_count = sum(1 for line in human_output.splitlines() if "✅" in line)

    data = json.loads(json_output)
    json_passed = data["summary"]["passed"]

    assert json_passed == checkmark_count, (
        f"JSON summary.passed={json_passed} != ✅ count={checkmark_count} in human output.\n"
        f"Human output:\n{human_output}\n"
        f"JSON:\n{json_output}"
    )
