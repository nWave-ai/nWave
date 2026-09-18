"""Acceptance steps: the pi extension is a pure protocol translator.

Driving port = the rendered pi extension (the TS translator). Exercised model-free
two ways, per the SPIKE-0 CI caveat and ADR-PI-001:

  1. Event-to-action MAPPING is asserted against the rendered extension source --
     which pi event selects which Claude-Code adapter action (`pre-write` for
     write/edit RED gate; `subagent-stop` for the git-commit step-completion
     boundary; `post-tool-use` for the test-run suite-state recording).
  2. The decision RELAY is asserted by a real DES adapter subprocess round-trip
     with constructed Claude-Code-shaped payloads (`pre-write`), confirming the
     engine -- not the extension -- owns the block/allow verdict.

No live LLM turn (that path is `@requires_external`, see model-driven feature).

Layer 3 (`@adapter-integration`): example-only (Mandate 11), no PBT (Mandate 9).
The commit->subagent-stop and test-run->post-tool-use mappings are the gate-set
the extension must GROW beyond the committed skeleton (D10 / ADR-PI-002); those
scenarios are RED-by-design until DELIVER extends the template.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when


scenarios("../extension-translation-contract.feature")

_REPO_ROOT = Path(__file__).resolve().parents[5]
_TEMPLATE = _REPO_ROOT / "nWave" / "templates" / "pi-des-extension.ts.template"
_SRC = _REPO_ROOT / "src"


@pytest.fixture
def world() -> dict:
    return {}


def _render(project: Path) -> str:
    return (
        _TEMPLATE.read_text(encoding="utf-8")
        .replace("{{PYTHON_PATH}}", sys.executable)
        .replace("{{PYTHONPATH}}", str(_SRC))
    )


def _adapter_roundtrip(action: str, payload: dict, cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "des.adapters.drivers.hooks.claude_code_hook_adapter",
            action,
        ],
        input=json.dumps(payload),
        env={"PYTHONPATH": str(_SRC), "PATH": os.environ.get("PATH", "")},
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode, (proc.stdout or "")


def _activated_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / ".nwave").mkdir(parents=True)
    (project / ".nwave" / "local-config.json").write_text(
        '{"enabled_for_repo": true}', encoding="utf-8"
    )
    (project / ".nwave" / "des" / "logs").mkdir(parents=True)
    return project


# --------------------------------------------------------------------------- #
# Given
# --------------------------------------------------------------------------- #


@given("the rendered pi extension for an activated project")
def _rendered_extension(world: dict, tmp_path: Path) -> None:
    project = _activated_project(tmp_path)
    world["project"] = project
    world["extension"] = _render(project)


# --------------------------------------------------------------------------- #
# When
# --------------------------------------------------------------------------- #


@when("a production-code write tool call is presented to the translator")
def _present_write(world: dict) -> None:
    world["tool_name"] = "write"


@when("an allowed write tool call is presented to the DES engine")
def _present_allowed_write(world: dict) -> None:
    project: Path = world["project"]
    target = project / "src" / "feature.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    code, out = _adapter_roundtrip(
        "pre-write",
        {
            "cwd": str(project),
            "tool_name": "Write",
            "tool_input": {"file_path": str(target), "content": "x = 1\n"},
        },
        cwd=project,
    )
    world["adapter_exit"] = code
    world["adapter_stdout"] = out


@when("a git commit tool call is presented to the translator")
def _present_commit(world: dict) -> None:
    world["tool_name"] = "bash:git commit"


@when("a test-run result is presented to the translator")
def _present_test_run(world: dict) -> None:
    world["tool_name"] = "tool_result:bash:pytest"


@when("a read-only tool call is presented to the translator")
def _present_read(world: dict) -> None:
    world["tool_name"] = "read"


@when("the DES engine cannot be reached during a tool call")
def _engine_unreachable(world: dict) -> None:
    world["tool_name"] = "write"
    world["engine_unreachable"] = True


# --------------------------------------------------------------------------- #
# Then
# --------------------------------------------------------------------------- #


@then("the translator selects the pre-write gate action")
def _selects_pre_write(world: dict) -> None:
    ext = world["extension"]
    assert '"pre-write"' in ext, "extension must map write/edit to the pre-write action"
    assert 'name === "write"' in ext or "'write'" in ext, (
        "extension must recognize the write tool name"
    )


@then(
    "a guarded write presented to the DES engine is answered with a block and a reason"
)
def _engine_blocks(world: dict) -> None:
    project: Path = world["project"]
    code, out = _adapter_roundtrip(
        "pre-write",
        {
            "cwd": str(project),
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(project / "execution-log.json"),
                "content": "x",
            },
        },
        cwd=project,
    )
    world["adapter_exit"] = code
    world["adapter_stdout"] = out
    assert code == 2, f"expected the engine to block (exit 2), got {code}: {out}"
    parsed = json.loads(out)
    assert parsed.get("decision") == "block" and parsed.get("reason"), out


@then("the extension relays that block and reason without inventing its own")
def _relays_block(world: dict) -> None:
    ext = world["extension"]
    # The extension must relay exit-code-2 + the engine's reason; it must not
    # synthesize block decisions from its own logic.
    assert "exitCode === 2" in ext
    assert "block: true" in ext
    assert "parsed.reason" in ext, "extension must relay the engine's reason field"


@then("the DES engine answers allow and the translator blocks nothing")
def _engine_allows(world: dict) -> None:
    assert world["adapter_exit"] == 0, (
        f"expected allow (exit 0), got {world['adapter_exit']}: {world['adapter_stdout']}"
    )


@then("the translator selects the step-completion validation action")
def _selects_subagent_stop(world: dict) -> None:
    ext = world["extension"]
    assert '"subagent-stop"' in ext, (
        "extension must map the git-commit tool call to the subagent-stop "
        "step-completion validation (ADR-PI-001 D6 Hybrid)"
    )
    assert "git commit" in ext or "commit" in ext


@then("the translator selects the suite-state recording action")
def _selects_post_tool_use(world: dict) -> None:
    ext = world["extension"]
    assert '"post-tool-use"' in ext, (
        "extension must map the test-run tool_result to the post-tool-use "
        "suite-state recording action (ADR-PI-001 / D12)"
    )
    assert "tool_result" in ext


@then("the translator selects no DES action and blocks nothing")
def _no_action_for_read(world: dict) -> None:
    ext = world["extension"]
    # The mapping returns null for unmapped tools; a read must not map to any action.
    assert "return null" in ext or "=> null" in ext or "mapTool" in ext
    assert 'name === "read"' not in ext, "read must not be a gated tool"


@then("the translator fails open and blocks nothing")
def _fails_open(world: dict) -> None:
    ext = world["extension"]
    assert "fail-open" in ext.lower(), "extension must document/implement fail-open"
    assert "catch" in ext, "extension must catch subprocess errors and not block"


@then(
    "the extension defines no enforcement decision beyond relaying the engine's verdict"
)
def _thin_translator(world: dict) -> None:
    ext = world["extension"]
    # Strip line/block comments so the assertion is about decision LOGIC, not
    # prose (refactoring-resilient: rewording a comment must not red the test).
    code_only = re.sub(r"/\*.*?\*/", "", ext, flags=re.S)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    # The ONLY block-decision statement permitted is the relay of engine exit 2.
    block_returns = len(re.findall(r"block:\s*true", code_only))
    assert block_returns == 1, (
        f"extension must contain exactly one block decision (the engine relay), "
        f"found {block_returns} in code -- the translator owns no decision logic"
    )
    assert "exitCode === 2" in code_only, (
        "the single block must be gated on the engine's exit code 2"
    )
