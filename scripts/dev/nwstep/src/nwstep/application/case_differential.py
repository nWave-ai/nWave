"""Runs each case on the candidate build and on the pre-feature tree, and checks what a preserve case executed.

The pre-feature run uses the same argv, cwd and environment with the candidate root rewritten to
the overlay directory: the pre-feature tree with the change's test files copied over it, as a RED run
uses. A preserve case's candidate run also records which lines ran, through a trace shim that only observes.
Whether a result is accepted belongs to CaseResult.
"""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from nwstep.application.red_tree import RedTree
from nwstep.domain.baseline import Baseline
from nwstep.domain.baseline_check import BaselineCheck
from nwstep.domain.case_expectation import CaseExpectation
from nwstep.domain.case_result import CaseResult
from nwstep.domain.case_spec import CaseSpec
from nwstep.domain.protection_check import ProtectionCheck
from nwstep.domain.root_rewrite import RootRewrite
from nwstep.infrastructure.command_runner import CommandRunner
from nwstep.infrastructure.git_diff import GitDiff, GitDiffError
from nwstep.infrastructure.trace_shim import TraceShim


class CaseDifferential:
    def __init__(
        self, runner: CommandRunner, baseline: Baseline, workspace_directory: Path
    ) -> None:
        self._runner = runner
        self._baseline = baseline
        self._workspace_directory = workspace_directory

    def judge(self, specs: list[CaseSpec], root: Path) -> list[CaseResult]:
        probe = self._probe_tree(root)
        with TraceShim() as shim:
            return [self._judge(spec, root, shim, probe) for spec in specs]

    def _judge(
        self,
        spec: CaseSpec,
        root: Path,
        shim: TraceShim,
        probe: tuple[Path | None, str | None],
    ) -> CaseResult:
        if spec.expectation.kind == CaseExpectation.PRESERVE:
            trace_directory = shim.new_trace_directory()
            candidate = self._runner.run(
                list(spec.argv),
                root,
                shim.environment(os.environ, trace_directory),
            )
            protection = self._protection(
                spec.expectation.protects or "", root, shim, trace_directory
            )
        else:
            candidate = self._runner.run(list(spec.argv), root)
            protection = ProtectionCheck.not_applicable()
        baseline = self._baseline_check(spec, root, probe)
        return spec.judge(candidate, baseline, protection)

    def _probe_tree(self, root: Path) -> tuple[Path | None, str | None]:
        """The overlay tree the cases run on, or the reason it cannot be built."""
        reason = self._baseline.unverifiable_for(root)
        if reason is not None:
            return None, reason
        try:
            names = GitDiff(
                str(self._baseline.top), str(self._baseline.sha), working=True
            ).names()
        except GitDiffError as error:
            return None, str(error)
        tree = RedTree(self._baseline, self._workspace_directory).build(root, names)
        return tree, None

    def _baseline_check(
        self,
        spec: CaseSpec,
        root: Path,
        probe: tuple[Path | None, str | None],
    ) -> BaselineCheck:
        tree, reason = probe
        if tree is None:
            return BaselineCheck.could_not_verify(reason or "the probe tree is absent")
        rewrite = RootRewrite(root, tree)
        outcome = self._runner.run(
            rewrite.argv(spec.argv),
            tree,
            rewrite.environment(os.environ),
        )
        return BaselineCheck.of(spec.expectation, outcome)

    def _protection(
        self, protects: str, root: Path, shim: TraceShim, trace_directory: Path
    ) -> ProtectionCheck:
        reason = self._baseline.unverifiable_for(root)
        if reason is not None:
            return ProtectionCheck.could_not_verify(protects, reason)
        try:
            changed = GitDiff(
                str(self._baseline.top), str(self._baseline.sha), working=False
            ).names()
        except GitDiffError as error:
            return ProtectionCheck.could_not_verify(protects, str(error))
        if PurePosixPath(protects).as_posix() not in changed:
            return ProtectionCheck.not_changed(protects)
        lines = shim.executed_lines(trace_directory, root / protects)
        if lines is None:
            return ProtectionCheck.could_not_verify(
                protects,
                "the candidate run started no Python process that could be traced",
            )
        if lines == 0:
            return ProtectionCheck.not_executed(protects)
        return ProtectionCheck.executed(protects, lines)
