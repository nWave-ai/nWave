"""Observes the RED command on the pre-feature tree and accepts it only through the report the command writes.

The tool, not the executor, runs the oracle's declared tests against the code that existed before the change: the
pre-feature tree exported at init, with the declared test files copied over it. The report is removed before the run
and read after it. A RED is accepted when every mapped test is reported failed; each other reading is refused with
what, why and how: no report (a compile error, a missing tool or a setup stop), an unreadable report, a mapped test
absent from the report, a mapped name that selects more than one case, a mapped test that errored, or a mapped test
that did not fail.
"""

from __future__ import annotations

from pathlib import Path

from nwexpress.application.red_tree import RedTree
from nwexpress.domain.baseline import Baseline
from nwexpress.domain.fault import Fault
from nwexpress.domain.field import Field
from nwexpress.domain.red_kind import RedKind
from nwexpress.domain.red_verdict import Refused, judge
from nwexpress.domain.refusal import Refusal
from nwexpress.domain.report_outcome import ReadReport
from nwexpress.domain.report_status import ReportStatus
from nwexpress.domain.test_name import TestName
from nwexpress.domain.test_run import TestRun
from nwexpress.infrastructure.command_runner import CommandRunner
from nwexpress.infrastructure.git_diff import GitDiff, GitDiffError
from nwexpress.infrastructure.report_file import ReportFile
from nwexpress.infrastructure.workspace import Workspace


class RedRun:
    def __init__(
        self, runner: CommandRunner, workspace: Workspace, baseline: Baseline
    ) -> None:
        self._runner = runner
        self._workspace = workspace
        self._baseline = baseline

    def observe(
        self,
        field: Field,
        argv: list[str],
        root: Path,
        expected: list[str],
        report: str,
        declared: list[str],
        timeout_s: int,
    ) -> dict[str, object]:
        reason = self._baseline.unverifiable_for(root)
        if reason is not None:
            raise field.refuse(
                f"'{field.name}' cannot run on the pre-feature tree: {reason}",
                fault=Fault.COMMAND,
            )
        changed = self._changed(field)
        unchanged = [path for path in declared if path not in changed]
        if unchanged:
            raise field.refuse(
                f"'{field.name}' declares test file(s) that are not part of the change from BASE: {', '.join(unchanged)}",
                rejected=tuple(unchanged),
                fault=Fault.COMMAND,
            )
        with RedTree(self._baseline, self._workspace.directory).built(
            root, declared
        ) as tree:
            return self._run_in(field, argv, tree, report, expected, timeout_s)

    def _run_in(  # noqa: PLR0913, PLR0917
        self,
        field: Field,
        argv: list[str],
        tree: Path,
        report: str,
        expected: list[str],
        timeout_s: int,
    ) -> dict[str, object]:
        ReportFile.remove(tree, report)
        outcome = self._runner.run(argv, tree, timeout_s=timeout_s)
        field.check_outcome(outcome)
        written = ReportFile.read(tree, report)
        verdict = judge(
            written,
            tuple(TestName.of(item) for item in expected),
            command_failed=outcome.exit_code not in (0, None),
        )
        if isinstance(verdict, Refused):
            raise self._refusal(field, report, verdict, outcome.exit_code, tree)
        cases = written.cases if isinstance(written, ReadReport) else ()
        value: dict[str, object] = dict(outcome.as_value())
        value["tests"] = TestRun.of(cases).as_value()
        value["failing"] = list(verdict.failing)
        value["evidence"] = [
            {
                "test": item.name,
                "case": item.case,
                "status": item.status,
                "kind": item.kind,
                "message": item.message,
            }
            for item in verdict.evidence
        ]
        value["errors"] = [
            case.name for case in cases if case.status == ReportStatus.ERRORED
        ]
        value["pre_feature_sha"] = self._baseline.sha
        return value

    def _changed(self, field: Field) -> frozenset[str]:
        try:
            return frozenset(
                GitDiff(
                    str(self._baseline.top), str(self._baseline.sha), working=True
                ).names()
            )
        except GitDiffError as error:
            raise field.refuse(
                f"'{field.name}' cannot read the change from BASE: {error}",
                fault=Fault.COMMAND,
            ) from None

    def _refusal(
        self,
        field: Field,
        report: str,
        verdict: Refused,
        exit_code: int | None,
        where: Path,
    ) -> Refusal:
        names = ", ".join(verdict.names)
        if verdict.kind == RedKind.NO_REPORT:
            return field.no_report(report, where, exit_code, copied=True)
        if verdict.kind == RedKind.UNREADABLE:
            return Refusal(
                what=f"'{field.name}' wrote '{report}', which is not a readable report: {verdict.cause}",
                why="only a report of the test run can show which tests failed, so an unreadable one proves nothing",
                how=f"make the command write a well-formed JUnit XML report at '{report}'",
                field=field.name,
                fault=Fault.COMMAND,
            )
        if verdict.kind == RedKind.MISMATCH:
            return Refusal(
                what=f"mapped test(s) {names} name a qualifier that no case of that test in the report carries: {verdict.cause}",
                why="a case of another qualifier is another test, so a RED on it proves nothing about the test the mapping names",
                how="map the test to the qualified name its case has in the report (the module, class or suite, two colons, then the name), or correct the mapping to the test it means; then record the oracle again",
                field=field.name,
                fault=Fault.COMMAND,
            )
        if verdict.kind == RedKind.AMBIGUOUS:
            return Refusal(
                what=f"mapped test(s) {names} each select more than one case of the report: {verdict.cause}",
                why="when the selected cases differ in outcome, the verdict would rest on whichever one the name reached, so no verdict is given",
                how="map each test to the full name of its case as the report writes it (the module, class or suite, two colons, then the name, and any parameters), then record the oracle again",
                field=field.name,
                fault=Fault.COMMAND,
            )
        if verdict.kind == RedKind.ABSENT:
            return Refusal(
                what=f"test(s) {names} absent from the report '{report}': they did not run",
                why="a test the report does not name did not run, so it shows no change of behaviour",
                how="make the test run and appear in the report, or correct the mapping to the name the test has",
                field=field.name,
                fault=Fault.COMMAND,
            )
        if verdict.kind == RedKind.ERRORED:
            return Refusal(
                what=f"test(s) {names} errored in setup, before their assertion ran: {verdict.cause}",
                why="a setup error proves no behaviour; only a test that fails on its own assertion shows the change",
                how="fix the setup the message names so that the test reaches its assertion",
                field=field.name,
                fault=Fault.COMMAND,
            )
        if verdict.kind == RedKind.UNVERIFIED:
            return Refusal(
                what=f"could not verify test(s) {names}: the command failed, yet the report gives neither a failure nor an error element for them",
                why="a failed command whose report says nothing about a test cannot show that the test failed, so the RED is not stated as checked",
                how="make the command report each mapped test with its failure element, or correct the mapping; then record the oracle again",
                field=field.name,
                fault=Fault.COMMAND,
            )
        return Refusal(
            what=f"test(s) {names} did not fail on the pre-feature tree",
            why="a test that passes there, or that is absent, proves no change of behaviour",
            how="make the test assert the promised outcome so that it fails on the pre-feature tree",
            field=field.name,
            fault=Fault.COMMAND,
        )
