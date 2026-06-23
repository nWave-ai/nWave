"""Acceptance steps: pi forces the crafter through RED -> GREEN -> refactor.

Driving port = the DES decision at each pi tool-call boundary, exercised model-free
by a real DES adapter subprocess round-trip with constructed Claude-Code-shaped
payloads (ADR-PI-001 D6 Hybrid; SPIKE-0 Half-1 pattern). No live LLM turn except
the single ``@requires_external`` scenario, which is skipped by default.

Layer 3 (`@adapter-integration`): example-only (Mandate 11), no PBT (Mandate 9).

RED-by-design note: the per-step "block production-write while no failing test
exists" and "reject commit when the cycle is incomplete" gates are wired by
DELIVER (the pi extension selects the action; the engine's per-step cycle state
decides). Until then these scenarios are RED for MISSING_FUNCTIONALITY -- the
engine currently allows where the target behavior is to block. The proven
standing block (the execution-log sentinel) anchors the RED-gate observable so the
suite is RED, not BROKEN.
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
    world["project"] = project


@given("no failing test justifies a production-code edit yet")
def _no_failing_test(world: dict) -> None:
    world["failing_test_present"] = False


@given("the current step has not recorded a completed cycle")
def _incomplete_cycle(world: dict) -> None:
    world["cycle_complete"] = False


@given("the current step recorded a completed cycle with a Step-Id trailered commit")
def _completed_cycle(world: dict) -> None:
    # Marks intent; the deterministic completed-cycle fixture (execution-log phase
    # records + Step-Id/Task-Id commit) is wired by DELIVER alongside the gate.
    world["cycle_complete"] = True


@given("a real pi model backend is available")
def _model_backend(world: dict) -> None:
    pytest.skip("requires a live pi model backend (SPIKE-0 CI caveat, R4)")


# --------------------------------------------------------------------------- #
# When
# --------------------------------------------------------------------------- #


@when("the crafter attempts to write production code")
def _write_production(world: dict) -> None:
    project: Path = world["project"]
    code, out = _adapter_roundtrip(
        "pre-write",
        {
            "cwd": str(project),
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(project / "src" / "feature.py"),
                "content": "def add(a, b):\n    return a + b\n",
            },
        },
        cwd=project,
    )
    world["exit"] = code
    world["stdout"] = out
    world["target"] = project / "src" / "feature.py"


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
    project: Path = world["project"]
    code, out = _adapter_roundtrip(
        "subagent-stop",
        {"cwd": str(project)},
        cwd=project,
    )
    world["exit"] = code
    world["stdout"] = out


@when("the crafter model turn issues a production-code write tool call")
def _model_write(world: dict) -> None:  # pragma: no cover - skipped path
    raise AssertionError("unreachable: model backend skip fires first")


# --------------------------------------------------------------------------- #
# Then
# --------------------------------------------------------------------------- #


@then("the write is blocked at the pi tool-call boundary with a reason")
def _write_blocked(world: dict) -> None:
    assert world["exit"] == 2, (
        "RED gate: a production-code write with no failing test must be blocked "
        f"(exit 2), engine returned exit {world['exit']}: {world['stdout']}"
    )
    parsed = json.loads(world["stdout"])
    assert parsed.get("decision") == "block" and parsed.get("reason")


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


@then("the step completion is rejected at the commit boundary with a reason")
def _commit_rejected(world: dict) -> None:
    assert world["exit"] == 2, (
        "step-completion gate: committing a step whose cycle is incomplete must be "
        f"rejected (exit 2) at the commit boundary, got exit {world['exit']}: "
        f"{world['stdout']}"
    )
    parsed = json.loads(world["stdout"])
    assert parsed.get("decision") == "block" and parsed.get("reason")


@then("the step completion is accepted at the commit boundary")
def _commit_accepted(world: dict) -> None:
    assert world["exit"] == 0, (
        f"a completed cycle with a Step-Id trailered commit must be accepted "
        f"(exit 0), got {world['exit']}: {world['stdout']}"
    )


@then("pi honors the block and the write does not occur")
def _pi_honors_block(world: dict) -> None:  # pragma: no cover - skipped path
    raise AssertionError("unreachable: model backend skip fires first")
