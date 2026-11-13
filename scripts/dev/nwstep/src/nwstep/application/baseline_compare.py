"""Runs a command field on the candidate and on the pre-feature tree, and reports the findings that are new.

A linter or type checker is judged against what already fails before the change, not against a raw count: the
verdict says whether the candidate adds findings. Digits are compared as '#', so a moved line number or a changed
count does not count as a new finding. Without a readable pre-feature tree, the verdict says it could not compare.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from nwstep.domain.baseline import Baseline
from nwstep.domain.field import Field
from nwstep.infrastructure.command_runner import CommandRunner


# Linters exit 2 when they fail themselves (usage or configuration), not when they report findings.
TOOL_ERROR_EXIT = 2


class BaselineCompare:
    _DIGITS = re.compile(r"\d+")

    def __init__(self, runner: CommandRunner, baseline: Baseline) -> None:
        self._runner = runner
        self._baseline = baseline

    def observe(self, field: Field, argv: list[str], root: Path) -> dict[str, Any]:
        candidate = self._runner.run(argv, root)
        field.check_outcome(candidate)
        value: dict[str, Any] = dict(candidate.as_value())
        reason = self._baseline.unverifiable_for(root)
        if reason is not None:
            value["verdict"] = f"could not compare with the pre-feature tree: {reason}"
            return value
        before = self._runner.run(argv, self._baseline.tree())
        before_lines = {self._normal(line) for line in self._lines(before.output)}
        candidate_lines = self._lines(candidate.output)
        new = list(
            dict.fromkeys(
                line
                for line in candidate_lines
                if self._normal(line) not in before_lines
            )
        )
        value["baseline_exit_code"] = before.exit_code
        value["new_findings"] = new
        value["verdict"] = self._verdict(candidate.exit_code, before.exit_code, new)
        return value

    @staticmethod
    def _verdict(
        exit_code: int | None, baseline_exit: int | None, new: list[str]
    ) -> str:
        if exit_code == 0:
            return "clean"
        if exit_code == TOOL_ERROR_EXIT and baseline_exit == TOOL_ERROR_EXIT:
            return (
                "unverified: the check exits 2 on this clone and on the pre-feature tree, a tool error rather than "
                "a finding, so nothing was compared; fix the command so that it runs and exits 0 or 1"
            )
        if new:
            return f"{len(new)} new finding(s) against the pre-feature tree"
        return f"no new finding; the pre-feature tree exits {baseline_exit} too"

    @classmethod
    def _lines(cls, output: str) -> list[str]:
        return [line.strip() for line in output.splitlines() if line.strip()]

    @classmethod
    def _normal(cls, line: str) -> str:
        return cls._DIGITS.sub("#", line)
