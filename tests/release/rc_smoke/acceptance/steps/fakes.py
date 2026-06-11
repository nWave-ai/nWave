"""In-memory fakes for the rc_smoke harness driven ports (DISTILL contract).

Port-to-port principle: the driving port is the harness CLI / SmokeRunner;
these fakes stand in for the driven ports (InstallerPort / ProcessPort /
FileSystemPort). They let the LOCAL acceptance suite verify orchestration,
the exit-code contract, per-tool ToolContract behaviour, and the
failure -> non-zero mapping WITHOUT shelling out to npm / TestPyPI / real
tools (which can only run in the ``validate-rc-multitool`` CI gate).

Test-doubles policy (nw-tdd-methodology): a fake MUST enforce the same input
preconditions as the real adapter, else it hides wiring bugs. Each fake here
validates its inputs and refuses ``$HOME`` targets (D-6 isolation), mirroring
what the real CLI/adapter does.

These classes are NOT scaffolds — they are real test infrastructure DELIVER
keeps. The production code they exercise (SmokeRunner, __main__) is the RED
scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from tests.release.rc_smoke.acceptance.steps.domain_types import (
    ScriptedStep,
    SmokeStepKind,
)


if TYPE_CHECKING:
    from scripts.release.rc_smoke.contracts import ToolContract


@dataclass
class _Result:
    succeeded: bool
    diagnostic: str = ""


@dataclass
class _ProcResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""


def _reject_home_target(target: Path) -> None:
    """Mirror the real CLI's refusal to write to the real user tree (D-6)."""
    home = Path("~").expanduser().resolve()
    if target.resolve() == home:
        raise AssertionError(
            "isolation violation: target resolved to $HOME "
            "(harness must always pass an isolated --target)"
        )


@dataclass
class FakeInstaller:
    """Scripted in-memory InstallerPort.

    ``scripted`` maps a step kind to its scripted outcome. ``calls`` records
    every invocation so a Then-step can assert isolation (the harness always
    passes an isolated --target) and ordering.
    """

    scripted: dict[SmokeStepKind, ScriptedStep] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)

    def install_published_nwave(self, version: str, venv: Path) -> _Result:
        assert version, "version must be a non-empty published version"
        assert venv is not None, "install requires an explicit venv (ENV_NO_VENV)"
        self.calls.append(("install_published", str(venv)))
        s = self.scripted.get(SmokeStepKind.INSTALL_PUBLISHED)
        if s and not s.succeeds:
            return _Result(False, s.diagnostic or "install aborted")
        return _Result(True)

    def provision_tool(self, contract: ToolContract, target: Path) -> _Result:
        assert contract is not None, "ToolContract required to provision"
        assert target is not None, "provision requires an explicit --target"
        _reject_home_target(target)
        self.calls.append(("provision", str(target)))
        s = self.scripted.get(SmokeStepKind.PROVISION)
        if s and not s.succeeds:
            return _Result(False, s.diagnostic or "provision aborted")
        return _Result(True)


@dataclass
class FakeProcess:
    """Scripted in-memory ProcessPort (tool boot via version flag)."""

    scripted: dict[SmokeStepKind, ScriptedStep] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)

    def boot(self, contract: ToolContract) -> _ProcResult:
        assert contract is not None, "ToolContract required to boot"
        assert contract.boot_argv, "boot requires a non-empty boot_argv"
        self.calls.append(contract.tool_id)
        s = self.scripted.get(SmokeStepKind.BOOT)
        if s and not s.succeeds:
            return _ProcResult(1, "", s.diagnostic or "boot failed")
        return _ProcResult(0, f"{contract.tool_id} 1.0.0", "")


@dataclass
class FakeFileSystem:
    """Scripted in-memory FileSystemPort.

    Models the codex false-PASS distinction: ``present_globs`` is the set of
    REAL artifact globs that exist. A bare directory existing does NOT count —
    only a glob in ``present_globs`` is "present". ``missing_artifacts``
    returns the required globs absent from that set.
    """

    present_globs: set[str] = field(default_factory=set)
    calls: list[str] = field(default_factory=list)

    def missing_artifacts(
        self, contract: ToolContract, target: Path
    ) -> tuple[str, ...]:
        assert contract is not None, "ToolContract required to assert artifacts"
        assert target is not None, "artifact assert requires an explicit --target"
        _reject_home_target(target)
        self.calls.append(str(target))
        return tuple(
            g for g in contract.required_artifact_globs if g not in self.present_globs
        )
