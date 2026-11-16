"""Runs each case on the candidate build and on the pre-feature tree, and states what a preserve case can show.

The pre-feature run uses the same argv, cwd and environment with the candidate root rewritten to the overlay directory:
the pre-feature tree with the change's declared test files copied over it, as a RED run uses. The overlay exists for
the whole judging pass and is removed when it ends. A preserve case protects a file of the change; no language-neutral
trace shows that a run executed that file, so its protection is reported could-not-verify with the reason, never
executed. Whether a result is accepted belongs to CaseResult.
"""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from nwexpress.application.red_tree import RedTree
from nwexpress.domain.baseline import Baseline
from nwexpress.domain.baseline_check import BaselineCheck
from nwexpress.domain.case_expectation import CaseExpectation
from nwexpress.domain.case_result import CaseResult
from nwexpress.domain.case_spec import CaseSpec
from nwexpress.domain.protection_check import ProtectionCheck
from nwexpress.domain.root_rewrite import RootRewrite
from nwexpress.infrastructure.command_runner import CommandRunner
from nwexpress.infrastructure.git_diff import GitDiff, GitDiffError


NO_TRACE = (
    "the tool observes no execution in any language, so this run cannot be shown to have executed the protected file; "
    "the protection is stated as could-not-verify and the case's own expectations are the evidence"
)


class CaseDifferential:
    def __init__(
        self, runner: CommandRunner, baseline: Baseline, workspace_directory: Path
    ) -> None:
        self._runner = runner
        self._baseline = baseline
        self._workspace_directory = workspace_directory

    def judge(
        self, specs: list[CaseSpec], root: Path, declared: list[str]
    ) -> list[CaseResult]:
        reason = self._probe_reason(root)
        if reason is not None:
            return [self._judge(spec, root, None, reason) for spec in specs]
        with RedTree(self._baseline, self._workspace_directory).built(
            root, declared
        ) as tree:
            return [self._judge(spec, root, tree, None) for spec in specs]

    def _judge(
        self,
        spec: CaseSpec,
        root: Path,
        tree: Path | None,
        reason: str | None,
    ) -> CaseResult:
        candidate = self._runner.run(list(spec.argv), root)
        if spec.expectation.kind == CaseExpectation.PRESERVE:
            protection = self._protection(spec.expectation.protects or "", root)
        else:
            protection = ProtectionCheck.not_applicable()
        baseline = self._baseline_check(spec, root, tree, reason)
        return spec.judge(candidate, baseline, protection)

    def _probe_reason(self, root: Path) -> str | None:
        """Why the overlay cannot be judged for this root, or None when it can."""
        reason = self._baseline.unverifiable_for(root)
        if reason is not None:
            return reason
        try:
            GitDiff(
                str(self._baseline.top), str(self._baseline.sha), working=True
            ).names()
        except GitDiffError as error:
            return str(error)
        return None

    def _baseline_check(
        self,
        spec: CaseSpec,
        root: Path,
        tree: Path | None,
        reason: str | None,
    ) -> BaselineCheck:
        if tree is None:
            return BaselineCheck.could_not_verify(reason or "the probe tree is absent")
        rewrite = RootRewrite(root, tree)
        outcome = self._runner.run(
            rewrite.argv(spec.argv),
            tree,
            rewrite.environment(os.environ),
        )
        return BaselineCheck.of(spec.expectation, outcome)

    def _protection(self, protects: str, root: Path) -> ProtectionCheck:
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
        return ProtectionCheck.could_not_verify(protects, NO_TRACE)
