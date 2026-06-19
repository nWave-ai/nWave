"""SmokeRunner — orchestrates one tool's smoke lane.

Application layer. Pure-ish: all side effects go through the injected ports.
Orchestration order (DESIGN component table / L4):

    install published nwave-ai  (InstallerPort)
    -> nwave-ai install --platform TOOL --target ISOLATED  (InstallerPort)
    -> boot tool via version flag  (ProcessPort)
    -> assert REAL nWave artifacts under the isolated target  (FileSystemPort)
    -> SmokeResult

Contract the acceptance suite pins:
  * EVERY step passes  -> SmokeResult.passed is True.
  * ANY step fails     -> SmokeResult.passed is False, with a readable
                          diagnostic, and NO later step masks the failure
                          (the codex false-PASS + "red annotations / green
                          pipeline" regression class, SPIKE). The lane
                          short-circuits at the first failure: a tool that
                          failed to install is never booted.
  * the harness ALWAYS provisions through ``--target`` (isolation, D-6) and
    never writes outside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.release.rc_smoke.result import (
    SmokeDepth,
    SmokeResult,
    SmokeStep,
    StepOutcome,
)


if TYPE_CHECKING:
    from pathlib import Path

    from scripts.release.rc_smoke.contracts import ToolContract
    from scripts.release.rc_smoke.ports import (
        FileSystemPort,
        InstallerPort,
        ProcessPort,
    )


class SmokeRunner:
    """Runs one tool's lane through the injected ports."""

    def __init__(
        self,
        installer: InstallerPort,
        process: ProcessPort,
        filesystem: FileSystemPort,
    ) -> None:
        self._installer = installer
        self._process = process
        self._filesystem = filesystem

    def run(
        self,
        contract: ToolContract,
        version: str,
        target: Path,
        depth: SmokeDepth = SmokeDepth.BOOT,
    ) -> SmokeResult:
        """Run the lane and return an aggregate SmokeResult.

        Steps run in order and short-circuit at the first failure, so the
        verdict is PASS iff every executed step passed and no failed step is
        ever masked by a later one.
        """
        # Steps run in order; the first failure short-circuits the lane BEFORE
        # the next port is touched (a broken install is never booted).
        steps: list[StepOutcome] = []

        install = self._install_step(version, target)
        steps.append(install)
        if not install.passed:
            return self._failed(contract, steps)

        provision = self._provision_step(contract, target)
        steps.append(provision)
        if not provision.passed:
            return self._failed(contract, steps)

        boot = self._boot_step(contract)
        steps.append(boot)
        if not boot.passed:
            return self._failed(contract, steps)

        artifacts = self._artifacts_step(contract, target)
        steps.append(artifacts)
        if not artifacts.passed:
            return self._failed(contract, steps)

        return SmokeResult(tool=contract.tool_id, passed=True, steps=tuple(steps))

    def _install_step(self, version: str, target: Path) -> StepOutcome:
        result = self._installer.install_published_nwave(version, target)
        return StepOutcome(
            step=SmokeStep.INSTALL_PUBLISHED,
            passed=result.succeeded,
            diagnostic=result.diagnostic,
        )

    def _provision_step(self, contract: ToolContract, target: Path) -> StepOutcome:
        result = self._installer.provision_tool(contract, target)
        return StepOutcome(
            step=SmokeStep.PROVISION,
            passed=result.succeeded,
            diagnostic=result.diagnostic,
        )

    def _boot_step(self, contract: ToolContract) -> StepOutcome:
        result = self._process.boot(contract)
        passed = result.exit_code == 0
        diagnostic = (
            "" if passed else (result.stderr or f"boot exit {result.exit_code}")
        )
        return StepOutcome(step=SmokeStep.BOOT, passed=passed, diagnostic=diagnostic)

    def _artifacts_step(self, contract: ToolContract, target: Path) -> StepOutcome:
        missing = self._filesystem.missing_artifacts(contract, target)
        if not missing:
            return StepOutcome(step=SmokeStep.ASSERT_ARTIFACTS, passed=True)
        return StepOutcome(
            step=SmokeStep.ASSERT_ARTIFACTS,
            passed=False,
            diagnostic="missing real nWave artifacts: " + ", ".join(missing),
        )

    def _failed(self, contract: ToolContract, steps: list[StepOutcome]) -> SmokeResult:
        last = steps[-1]
        diagnostics = (
            f"{contract.tool_id} smoke FAILED at step "
            f"{last.step.value}: {last.diagnostic}"
        )
        return SmokeResult(
            tool=contract.tool_id,
            passed=False,
            steps=tuple(steps),
            diagnostics=diagnostics,
        )
