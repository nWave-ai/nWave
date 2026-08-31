"""Acceptance steps: pi forces the crafter through RED -> GREEN -> refactor.

Driving port = the DES decision at each pi tool-call boundary, exercised model-free
by a real DES adapter subprocess round-trip with constructed Claude-Code-shaped
payloads (ADR-PI-001 D6 Hybrid; SPIKE-0 Half-1 pattern). No live LLM turn except
the single ``@requires_external`` scenario, which is skipped by default.

Layer 3 (`@adapter-integration`): example-only (Mandate 11), no PBT (Mandate 9).

Boundary signals (engine reused unchanged, ADR-PI-001 D5):
  - RED gate (production write with no failing test): the ``pre-write`` action
    blocks the standing execution-log sentinel with **exit 2** + a JSON reason.
    This is the proven within-cycle ordering observable (SPIKE-0 Half-1).
  - Step-completion gate (the ``git commit`` boundary): the unchanged
    ``subagent-stop`` action validates the step's phase events
    (``StepCompletionValidator``) and the ``Step-Id``/``Task-Id`` trailered
    commit (``GitCommitVerifier``). A failure is signalled as a JSON
    ``{"decision":"block","reason":...}`` on stdout (exit 0 so Claude Code reads
    the JSON); a pass is a bare exit-0 allow with no output. The pi extension's
    relay surfaces either engine block signal verbatim.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when


scenarios("../tdd-enforcement-gates.feature")

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SRC = _REPO_ROOT / "src"


@pytest.fixture
def world() -> dict:
    return {}


def _adapter_roundtrip(action: str, payload: dict, cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "des.adapters.drivers.hooks.claude_code_hook_adapter",
            action,
        ],
        input=json.dumps(payload),
        env={
            "PYTHONPATH": str(_SRC),
            "PATH": os.environ.get("PATH", ""),
            "DES_AUDIT_LOG_DIR": str(cwd / ".nwave" / "des" / "logs"),
        },
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode, (proc.stdout or "")


_FEATURE_ID = "pi-feature"
_STEP_ID = "01-01"


def _git(project: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=str(project),
        capture_output=True,
        text=True,
        check=True,
    )


def _execution_log_path(project: Path) -> Path:
    return project / "docs" / "feature" / _FEATURE_ID / "deliver" / "execution-log.json"


def _write_execution_log(project: Path, events: list[str]) -> Path:
    log_path = _execution_log_path(project)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        json.dumps({"project_id": _FEATURE_ID, "events": events}, indent=2),
        encoding="utf-8",
    )
    return log_path


_COMPLETE_CYCLE_EVENTS = [
    f"{_STEP_ID}|RED|EXECUTED|PASS|2026-06-24T10:00:00Z",
    f"{_STEP_ID}|GREEN|EXECUTED|PASS|2026-06-24T10:20:00Z",
    f"{_STEP_ID}|COMMIT|EXECUTED|PASS|2026-06-24T11:00:00Z",
]


def _commit_roundtrip(world: dict) -> None:
    """Drive the unchanged subagent-stop step-completion validation.

    Uses the direct DES protocol (executionLogPath/projectId/stepId/cwd) so the
    engine reads the constructed execution-log + git commit state -- this is the
    same SubagentStopService.validate() the pi extension relays at the
    ``git commit`` tool-call boundary (ADR-PI-001 D6 Hybrid).
    """
    project: Path = world["project"]
    code, out = _adapter_roundtrip(
        "subagent-stop",
        {
            "executionLogPath": str(_execution_log_path(project)),
            "projectId": _FEATURE_ID,
            "stepId": _STEP_ID,
            "cwd": str(project),
        },
        cwd=project,
    )
    world["exit"] = code
    world["stdout"] = out


# --------------------------------------------------------------------------- #
# Given
# --------------------------------------------------------------------------- #


@given("the crafter is working in an activated pi project")
@given("the crafter is working in an activated pi project with no failing test")
def _activated_pi_project(world: dict, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    (project / ".nwave" / "des" / "logs").mkdir(parents=True)
    (project / ".nwave" / "local-config.json").write_text(
        '{"enabled_for_repo": true}', encoding="utf-8"
    )
    (project / "src").mkdir()
    (project / "tests").mkdir()
    _git(project, "init")
    _git(project, "config", "user.email", "crafter@pi.test")
    _git(project, "config", "user.name", "pi crafter")
    world["project"] = project


@given("no failing test justifies a production-code edit yet")
def _no_failing_test(world: dict) -> None:
    world["failing_test_present"] = False


@given("the current step has not recorded a completed cycle")
def _incomplete_cycle(world: dict) -> None:
    # Only the first phase is recorded -- GREEN and COMMIT never ran, so the
    # engine's StepCompletionValidator reports the cycle as incomplete.
    _write_execution_log(
        world["project"],
        [f"{_STEP_ID}|RED|EXECUTED|PASS|2026-06-24T10:00:00Z"],
    )


@given("the current step recorded a completed cycle with a Step-Id trailered commit")
def _completed_cycle(world: dict) -> None:
    project: Path = world["project"]
    _write_execution_log(project, _COMPLETE_CYCLE_EVENTS)
    _git(project, "add", "-A")
    _git(
        project,
        "commit",
        "-m",
        f"feat: implement step\n\nStep-Id: {_STEP_ID}\nTask-Id: {_FEATURE_ID}",
    )


@given("the current step recorded a completed cycle committed outside the pi harness")
def _completed_cycle_out_of_harness(world: dict) -> None:
    # A2 durable trust boundary: the cycle is complete in the log, but the commit
    # was made outside pi and carries only a Step-Id trailer (no matching
    # Task-Id). GitCommitVerifier's AND-semantics catch it post-hoc.
    project: Path = world["project"]
    _write_execution_log(project, _COMPLETE_CYCLE_EVENTS)
    _git(project, "add", "-A")
    _git(
        project,
        "commit",
        "-m",
        f"feat: out-of-harness commit\n\nStep-Id: {_STEP_ID}",
    )


@given("a real pi model backend is available")
def _model_backend(world: dict) -> None:
    pytest.skip("requires a live pi model backend (SPIKE-0 CI caveat, R4)")


# --------------------------------------------------------------------------- #
# When
# --------------------------------------------------------------------------- #


@when("the crafter attempts to write production code")
def _write_production(world: dict) -> None:
    # RED-gate observable: the standing execution-log sentinel the engine always
    # blocks at the pre-write boundary in an activated project (SPIKE-0 Half-1).
    project: Path = world["project"]
    target = project / "execution-log.json"
    code, out = _adapter_roundtrip(
        "pre-write",
        {
            "cwd": str(project),
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(target),
                "content": "x = 1\n",
            },
        },
        cwd=project,
    )
    world["exit"] = code
    world["stdout"] = out
    world["target"] = target


@when("the crafter attempts to write a test file")
def _write_test(world: dict) -> None:
    project: Path = world["project"]
    code, out = _adapter_roundtrip(
        "pre-write",
        {
            "cwd": str(project),
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(project / "tests" / "test_feature.py"),
                "content": "def test_add():\n    assert add(1, 2) == 3\n",
            },
        },
        cwd=project,
    )
    world["exit"] = code
    world["stdout"] = out


@when("the crafter attempts to commit the step")
def _commit_step(world: dict) -> None:
    _commit_roundtrip(world)


@when("the step is validated at the commit boundary")
def _validate_commit_boundary(world: dict) -> None:
    _commit_roundtrip(world)


@when("the crafter model turn issues a production-code write tool call")
def _model_write(world: dict) -> None:  # pragma: no cover - skipped path
    raise AssertionError("unreachable: model backend skip fires first")


# --------------------------------------------------------------------------- #
# Then
# --------------------------------------------------------------------------- #


def _assert_engine_block(world: dict) -> None:
    """Assert the engine emitted a block verdict with a reason on stdout."""
    parsed = json.loads(world["stdout"])
    assert parsed.get("decision") == "block" and parsed.get("reason"), (
        f"expected a block decision with a reason, got: {world['stdout']!r}"
    )


@then("the write is blocked at the pi tool-call boundary with a reason")
def _write_blocked(world: dict) -> None:
    assert world["exit"] == 2, (
        "RED gate: a production-code write with no failing test must be blocked "
        f"(exit 2), engine returned exit {world['exit']}: {world['stdout']}"
    )
    _assert_engine_block(world)


@then("the production file is not created")
def _file_not_created(world: dict) -> None:
    assert not world["target"].exists(), (
        "the blocked production file must not exist on disk"
    )


@then("the write is allowed at the pi tool-call boundary")
def _write_allowed(world: dict) -> None:
    assert world["exit"] == 0, (
        f"writing a test first must be allowed (exit 0), got {world['exit']}: "
        f"{world['stdout']}"
    )
    assert world["stdout"].strip() == "", (
        f"an allowed write must emit no block decision, got: {world['stdout']!r}"
    )


@then("the step completion is rejected at the commit boundary with a reason")
def _commit_rejected(world: dict) -> None:
    assert world["stdout"].strip() != "", (
        "step-completion gate: committing a step whose cycle is incomplete must "
        f"emit a block verdict at the commit boundary, got exit {world['exit']} "
        f"with no output: {world['stdout']!r}"
    )
    _assert_engine_block(world)


@then("the step completion is accepted at the commit boundary")
def _commit_accepted(world: dict) -> None:
    assert world["exit"] == 0 and world["stdout"].strip() == "", (
        f"a completed cycle with a Step-Id trailered commit must be accepted "
        f"(exit 0, no block), got exit {world['exit']}: {world['stdout']!r}"
    )


@then("the out-of-harness commit is caught by the commit verifier with a reason")
def _out_of_harness_caught(world: dict) -> None:
    _assert_engine_block(world)
    parsed = json.loads(world["stdout"])
    assert "COMMIT_NOT_VERIFIED" in parsed["reason"], (
        "the durable git trust boundary (GitCommitVerifier) must reject a commit "
        f"missing the matching Task-Id trailer, got: {parsed['reason']!r}"
    )


@then("pi honors the block and the write does not occur")
def _pi_honors_block(world: dict) -> None:  # pragma: no cover - skipped path
    raise AssertionError("unreachable: model backend skip fires first")
