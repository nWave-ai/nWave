"""Observes the RED command on the pre-feature tree and names the failing tests the tool saw.

The tool, not the executor, runs the oracle's tests against the code that existed before the change: the
pre-feature tree exported at init, with every test file the working tree changes copied over it. A RED with no
failing test id (an import error, a collection error or a setup error only) proves no behaviour and is refused,
and the refusal names the probable cause and the repair. So is a RED in which a test the oracle maps to a promise
passes before the change: that test is vacuous, whatever its assertion.
"""

from __future__ import annotations

import re
from pathlib import Path

from nwstep.application.how_line import HowLine
from nwstep.application.red_tree import RedTree, changed_tests
from nwstep.domain.baseline import Baseline
from nwstep.domain.fault import Fault
from nwstep.domain.field import Field
from nwstep.domain.refusal import Refusal
from nwstep.infrastructure.command_runner import CommandRunner
from nwstep.infrastructure.git_diff import GitDiff, GitDiffError
from nwstep.infrastructure.workspace import Workspace


NOTHING_PRINTED = "the command printed nothing"


def probable_cause(output: str) -> str:
    """The message of the first ERROR line, else the last printed line, else that nothing was printed.

    Pytest reports setup and collection errors as 'ERROR <test id> - <message>'; that message is the cause the
    refusal states. A line without the separator is stated whole, so the cause is never empty.
    """
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("ERROR "):
            message = line.partition(" - ")[2].strip()
            return message or line
    return lines[-1] if lines else NOTHING_PRINTED


def setup_repair(
    tree: Path, cause: str, has_repository: bool, init_command: str
) -> str:
    """The runnable repair for a RED that failed at setup; a baseline is fixed at init, so the repair is a new workspace."""
    if not has_repository:
        return f"init a new workspace with git on the PATH: {init_command}"
    return (
        f"make '{cause}' true of the pre-feature tree {tree}: commit what the setup reads to the repository, "
        f"or let the test create it under tmp_path; then init a new workspace: {init_command}"
    )


class RedRun:
    _FAILED = re.compile(r"^FAILED (\S+)", re.MULTILINE)
    _ERROR = re.compile(r"^ERROR (\S+)", re.MULTILINE)

    def __init__(
        self, runner: CommandRunner, workspace: Workspace, baseline: Baseline
    ) -> None:
        self._runner = runner
        self._workspace = workspace
        self._baseline = baseline

    def observe(
        self, field: Field, argv: list[str], root: Path, expected: list[str]
    ) -> dict[str, object]:
        reason = self._baseline.unverifiable_for(root)
        if reason is not None:
            raise field.refuse(
                f"'{field.name}' cannot run on the pre-feature tree: {reason}",
                fault=Fault.COMMAND,
            )
        outcome = self._runner.run(argv, self._overlay(field, root))
        field.check_outcome(outcome)
        failing = self._unique(self._FAILED, outcome.output)
        if not failing:
            raise self._setup_refusal(field, outcome.output)
        functions = {re.sub(r"\[.*$", "", node.split("::")[-1]) for node in failing}
        passing = [name for name in expected if name not in functions]
        if passing:
            raise field.refuse(
                f"test(s) {', '.join(passing)} did not fail on the pre-feature tree: a test that passes there, "
                "or does not exist, proves no change of behaviour",
                fault=Fault.COVERAGE,
            )
        value: dict[str, object] = dict(outcome.as_value())
        value["failing"] = failing
        value["errors"] = self._unique(self._ERROR, outcome.output)
        value["pre_feature_sha"] = self._baseline.sha
        return value

    def _setup_refusal(self, field: Field, output: str) -> Refusal:
        errors = self._unique(self._ERROR, output)
        tree = self._baseline.tree()
        has_repository = (tree / ".git").exists()
        cause = probable_cause(output)
        if not has_repository:
            cause = f"the pre-feature tree {tree} has no .git: {cause}"
        init_command = HowLine().command(
            "init",
            "--schema",
            str(self._workspace.schema_path),
            "--workspace",
            f"{self._workspace.directory}-next",
        )
        return Refusal(
            what=(
                f"'{field.name}' names no failing test on the pre-feature tree "
                f"({len(errors)} error(s) only): probable cause: {cause}"
            ),
            why="a RED that fails at import, collection or setup proves no behaviour; only a test that fails on its own assertion shows the change",
            how=setup_repair(tree, cause, has_repository, init_command),
            field=field.name,
            fault=Fault.COMMAND,
        )

    def _overlay(self, field: Field, root: Path) -> Path:
        return RedTree(self._baseline, self._workspace.directory).build(
            root, self._changed_tests(field)
        )

    def _changed_tests(self, field: Field) -> list[str]:
        try:
            names = GitDiff(
                str(self._baseline.top), str(self._baseline.sha), working=True
            ).names()
        except GitDiffError as error:
            raise field.refuse(
                f"'{field.name}' cannot read the change from BASE: {error}",
                fault=Fault.COMMAND,
            ) from None
        return changed_tests(names)

    @staticmethod
    def _unique(pattern: re.Pattern[str], text: str) -> list[str]:
        return list(dict.fromkeys(pattern.findall(text)))
