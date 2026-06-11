"""Layer-1 PBT — the harness never reports a pass when any step failed.

This is the property form of the codex false-PASS + "red annotations / green
pipeline" defect class (SPIKE): over ARBITRARY combinations of per-step
outcomes, the lane verdict is PASS iff EVERY step passed; otherwise FAIL with a
non-empty diagnostic. Layer 1 unit -> PBT full (Mandate 9): Hypothesis explores
the 2^4 step-outcome space plus the empty/all-fail boundaries.

Drives SmokeRunner (the application driving port) over in-memory fakes. RED
until DELIVER implements SmokeRunner.run; ``@example`` cases pin the canonical
all-pass and all-fail rows for reviewers.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import example, given, settings
from hypothesis import strategies as st

from scripts.release.rc_smoke.result import SmokeDepth
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
    FakeInstaller,
    FakeProcess,
)


# Outcome flags per (install, provision, boot, artifacts-present).
_step_outcomes = st.tuples(
    st.booleans(),  # install succeeds
    st.booleans(),  # provision succeeds
    st.booleans(),  # boot succeeds
    st.booleans(),  # real artifacts present
)


def _build(outcomes: tuple[bool, bool, bool, bool], target: Path):
    install_ok, provision_ok, boot_ok, artifacts_ok = outcomes
    contract = contract_for(Tool.CLAUDE_CODE)

    scripted_install: dict = {}
    if not install_ok:
        scripted_install[SmokeStepKind.INSTALL_PUBLISHED] = ScriptedStep(
            SmokeStepKind.INSTALL_PUBLISHED, succeeds=False, diagnostic="install x"
        )
    if not provision_ok:
        scripted_install[SmokeStepKind.PROVISION] = ScriptedStep(
            SmokeStepKind.PROVISION, succeeds=False, diagnostic="provision x"
        )

    scripted_boot: dict = {}
    if not boot_ok:
        scripted_boot[SmokeStepKind.BOOT] = ScriptedStep(
            SmokeStepKind.BOOT, succeeds=False, diagnostic="boot x"
        )

    present = set(contract.required_artifact_globs) if artifacts_ok else set()

    return build_composition(
        installer=FakeInstaller(scripted=scripted_install),
        process=FakeProcess(scripted=scripted_boot),
        filesystem=FakeFileSystem(present_globs=present),
    )


# A fixed non-$HOME isolated path. The fakes never touch disk (they only
# refuse a $HOME target), so no real tmp dir / function-scoped fixture is
# needed — keeping the property compatible with Hypothesis (no FailedHealthCheck).
_ISOLATED = Path("/tmp/rc-smoke-pbt-isolated")


@given(outcomes=_step_outcomes)
@example(outcomes=(True, True, True, True))
@example(outcomes=(False, False, False, False))
@settings(max_examples=100, deadline=None)
def test_lane_passes_iff_every_step_passes(outcomes):
    comp = _build(outcomes, _ISOLATED)
    result = comp.runner.run(
        contract=contract_for(Tool.CLAUDE_CODE),
        version="9.9.9rc1",
        target=_ISOLATED,
        depth=SmokeDepth.BOOT,
    )

    every_step_passed = all(outcomes)
    assert result.passed is every_step_passed
    if not every_step_passed:
        assert result.diagnostics, "a failed lane must carry a readable diagnostic"
