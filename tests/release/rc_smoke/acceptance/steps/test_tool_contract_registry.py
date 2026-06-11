"""Tier A step definitions — per-tool ToolContract behaviour (US-2).

Same SmokeRunner orchestration runs over each tool's contract; the per-tool
difference is pure DATA (DESIGN D-2). The unsupported-tool scenario pins that
the registry rejects a tool with no contract (the Copilot class) loudly via the
production ``tool_contract`` lookup (the driving port for the registry).

Layer 2 in-memory acceptance: finite tool set -> Scenario Outline parametrize,
NOT PBT (closed-world falsifier-gate). Step bodies delegate to the composition;
no business logic inlined (Mandate-12 criterion 3).
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from scripts.release.rc_smoke import contracts as registry
from scripts.release.rc_smoke.result import SmokeDepth
from tests.common.state_delta import assert_state_delta, set_to
from tests.release.rc_smoke.acceptance.steps.composition import (
    build_composition,
    contract_for,
)
from tests.release.rc_smoke.acceptance.steps.domain_types import (
    ScriptedStep,
    SmokeStepKind,
    Tool,
)
from tests.release.rc_smoke.acceptance.steps.fakes import (
    FakeFileSystem,
    FakeProcess,
)


scenarios("../tool-contract-registry.feature")


@pytest.fixture
def run_state() -> dict:
    return {"scripted_boot": {}, "present_globs": set()}


def _tool(name: str) -> Tool:
    return Tool(name)


# --- Given -----------------------------------------------------------------


@given("a published release candidate and an isolated install target")
def given_rc_and_target(run_state, tmp_path):
    run_state["version"] = "9.9.9rc1"
    run_state["target"] = tmp_path / "isolated"


@given(
    parsers.parse(
        'the supported tool "{tool}" installs, provisions, boots, and writes its artifacts'
    )
)
def given_tool_all_succeed(run_state, tool):
    t = _tool(tool)
    run_state["tool"] = t
    run_state["present_globs"] = set(contract_for(t).required_artifact_globs)


@given(
    parsers.parse(
        'the supported tool "{tool}" is installed and provisioned but fails to boot'
    )
)
def given_tool_boot_fails(run_state, tool):
    t = _tool(tool)
    run_state["tool"] = t
    run_state["present_globs"] = set(contract_for(t).required_artifact_globs)
    run_state["scripted_boot"][SmokeStepKind.BOOT] = ScriptedStep(
        SmokeStepKind.BOOT, succeeds=False, diagnostic="boot failed"
    )


@given(
    parsers.parse('the supported tool "{tool}" boots but provisioned no real artifacts')
)
def given_tool_no_artifacts(run_state, tool):
    run_state["tool"] = _tool(tool)
    run_state["present_globs"] = set()


@given("the smoke harness contract registry")
def given_registry(run_state):
    run_state["registry"] = registry


# --- When ------------------------------------------------------------------


@when(parsers.parse('the release engineer runs the smoke lane for "{tool}"'))
def when_run_for_tool(run_state, tool):
    comp = build_composition(
        process=FakeProcess(scripted=run_state["scripted_boot"]),
        filesystem=FakeFileSystem(present_globs=run_state["present_globs"]),
    )
    run_state["result"] = comp.runner.run(
        contract=contract_for(_tool(tool)),
        version=run_state["version"],
        target=run_state["target"],
        depth=SmokeDepth.BOOT,
    )


@when(
    parsers.parse(
        'the release engineer requests a lane for an unsupported tool "{tool}"'
    )
)
def when_request_unsupported(run_state, tool):
    try:
        run_state["registry"].tool_contract(tool)
        run_state["error"] = None
    except Exception as exc:
        run_state["error"] = exc


# --- Then ------------------------------------------------------------------


@then("the lane passes")
def then_passes(run_state):
    assert_state_delta(
        {"lane.passed": None},
        {"lane.passed": run_state["result"].passed},
        universe={"lane.passed"},
        expected={"lane.passed": set_to(True)},
    )


@then("the lane fails")
def then_fails(run_state):
    assert_state_delta(
        {"lane.passed": None},
        {"lane.passed": run_state["result"].passed},
        universe={"lane.passed"},
        expected={"lane.passed": set_to(False)},
    )


@then("the failure names the missing artifacts in a readable diagnostic")
def then_names_missing(run_state):
    diag = run_state["result"].diagnostics
    globs = contract_for(run_state["tool"]).required_artifact_globs
    assert any(g in diag for g in globs), diag


@then("the request is rejected with a readable unsupported-tool diagnostic")
def then_rejected(run_state):
    err = run_state["error"]
    assert err is not None, "unsupported tool was NOT rejected"
    assert "copilot" in str(err).lower() or "unsupported" in str(err).lower(), str(err)
