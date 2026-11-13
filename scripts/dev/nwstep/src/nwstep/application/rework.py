"""The rework of a delivery in its own workspace: a reviewer's findings, the packet that freezes the candidate,
and the verdicts. A thin shell: read the journal and the review log under the workspace lock, decide with the pure
rules of domain/review.py, then append. The base recorded at init is never touched and no new workspace is made.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from nwstep.application.progress import Progress
from nwstep.domain import review
from nwstep.domain.candidate import Unreadable
from nwstep.domain.refusal import Refusal
from nwstep.domain.review import (
    CaseRun,
    Observation,
    Refused,
    Remedy,
    Repeated,
    ReviewLog,
)
from nwstep.infrastructure import review_store
from nwstep.infrastructure.candidate_reader import read_candidate
from nwstep.infrastructure.jsonl_journal import JsonlJournal
from nwstep.infrastructure.toml_schema_reader import TomlSchemaReader


if TYPE_CHECKING:
    from pathlib import Path

    from nwstep.application.how_line import HowLine
    from nwstep.domain.candidate import Observed
    from nwstep.domain.journal import Journal
    from nwstep.domain.review import Finding, Packet, Verdict
    from nwstep.domain.schema import Schema
    from nwstep.domain.step import Step
    from nwstep.infrastructure.command_runner import CommandRunner
    from nwstep.infrastructure.workspace import Workspace


@dataclass(frozen=True)
class Desk:
    """Where a rework happens: the workspace, the project root and the writer of repair lines."""

    workspace: Workspace
    root: Path
    how: HowLine

    @property
    def located(self) -> tuple[str, str, str, str]:
        """The options that place a command on this workspace and this project."""
        return ("--workspace", str(self.workspace.directory), "--root", str(self.root))

    def line(self, remedy: Remedy) -> str:
        if remedy is Remedy.STATUS:
            return self.how.command("status", *self.located[:2])
        if remedy is Remedy.FINDING:
            return self.how.command(
                "finding",
                *self.located,
                "--author",
                "<who wrote the finding>",
                "--text",
                "<what the finding says>",
                "--red",
                "<one command that fails on the candidate now>",
            )
        return self.how.command(remedy.value, *self.located)

    def verdict_line(self, candidate: str) -> str:
        return self.how.command(
            "verdict",
            *self.located,
            "--reviewer",
            "<reviewer id>",
            "--candidate",
            candidate,
            "--outcome",
            "<accepted or rejected>",
        )

    def refusal(self, refused: Refused) -> Refusal:
        return Refusal(refused.what, refused.why, self.line(refused.remedy))


@dataclass(frozen=True)
class FindingReport:
    finding: Finding
    repeated: bool
    stale: tuple[str, ...]
    waiting: tuple[Finding, ...]
    closing_step: str | None
    corrects: Finding | None = None


@dataclass(frozen=True)
class PacketReport:
    packet: Packet
    log: ReviewLog
    stale: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class VerdictReport:
    verdict: Verdict
    repeated: bool
    notes: tuple[str, ...]


def green_id(schema: Schema) -> str | None:
    step = schema.green_step()
    return None if step is None else step.id


def stale_steps(schema: Schema, journal: Journal, log: ReviewLog) -> tuple[str, ...]:
    """The stale steps, counting the ones an open finding reopened."""
    return Progress(schema).stale(
        journal, review.reopened(log, journal, green_id(schema))
    )


def replayable_steps(
    schema: Schema, journal: Journal, log: ReviewLog
) -> tuple[str, ...]:
    """The stale steps a replay records again: every stale step except a verdict and what relies on one."""
    return Progress(schema).replayable(
        journal, review.reopened(log, journal, green_id(schema))
    )


def report_finding(
    desk: Desk, runner: CommandRunner, author: str, text: str, red: str
) -> FindingReport:
    """Record a finding with the failing run of its case; every refusal is decided before anything is written."""
    draft = review.finding_draft(author, text, red)
    if isinstance(draft, Refused):
        raise desk.refusal(draft)
    schema = TomlSchemaReader().read(desk.workspace.schema_path)
    green = green_id(schema)
    with JsonlJournal(desk.workspace).exclusive() as session:
        journal = session.snapshot()
        log = review_store.read(desk.workspace)
        gate = review.finding_gate(log, journal, green, draft)
        if isinstance(gate, Refused):
            raise desk.refusal(gate)
        if isinstance(gate, Repeated):
            return _finding_report(gate.event, True, schema, journal, log)
        outcome = runner.run(list(draft.argv), desk.root)
        observed = review.finding_observed(
            log,
            journal,
            gate,
            Observation(outcome.as_value(), outcome.problem),
            _now(),
        )
        if isinstance(observed, Refused):
            raise desk.refusal(observed)
        report = _finding_report(
            observed, False, schema, journal, _kept(desk, log, observed)
        )
        return replace(report, corrects=gate.corrects)


def _kept(desk: Desk, log: ReviewLog, event: Finding | Packet | Verdict) -> ReviewLog:
    """Append the event to the review file and return the log that holds it."""
    review_store.append(desk.workspace, event)
    return ReviewLog((*log.events, event))


def _finding_report(
    finding: Finding, repeated: bool, schema: Schema, journal: Journal, log: ReviewLog
) -> FindingReport:
    green = green_id(schema)
    return FindingReport(
        finding=finding,
        repeated=repeated,
        stale=stale_steps(schema, journal, log),
        waiting=review.open_findings(log, journal, green),
        closing_step=green,
    )


def freeze_candidate(desk: Desk) -> PacketReport:
    """Freeze the identity of the candidate for the reviewer; the same candidate frozen again writes nothing."""
    schema = TomlSchemaReader().read(desk.workspace.schema_path)
    with JsonlJournal(desk.workspace).exclusive() as session:
        journal = session.snapshot()
        log = review_store.read(desk.workspace)
        observed = _candidate(desk)
        decision = review.freeze(
            log, journal, green_id(schema), observed.identity, _now()
        )
        if isinstance(decision, Refused):
            raise desk.refusal(decision)
        if isinstance(decision, Repeated):
            packet, after = decision.event, log
        else:
            packet, after = decision, _kept(desk, log, decision)
        return PacketReport(
            packet, after, stale_steps(schema, journal, after), observed.notes
        )


def record_verdict(
    desk: Desk, reviewer: str, named: str, outcome: str
) -> VerdictReport:
    """Record a verdict for the frozen candidate; a verdict that names another candidate is refused."""
    draft = review.verdict_draft(reviewer, named, outcome)
    if isinstance(draft, Refused):
        raise desk.refusal(draft)
    with JsonlJournal(desk.workspace).exclusive() as session:
        journal = session.snapshot()
        log = review_store.read(desk.workspace)
        observed = _candidate(desk)
        decision = review.judge(log, journal, draft, observed.identity, _now())
        if isinstance(decision, Refused):
            raise desk.refusal(decision)
        if isinstance(decision, Repeated):
            return VerdictReport(decision.event, True, observed.notes)
        review_store.append(desk.workspace, decision)
        return VerdictReport(decision, False, observed.notes)


def close_findings(  # noqa: PLR0913 - called inside the record of a step, with the state that record already holds
    desk: Desk,
    runner: CommandRunner,
    *,
    schema: Schema,
    log: ReviewLog,
    journal: Journal,
    step: Step,
) -> tuple[dict[str, object], ...]:
    """Run the case of every open finding when the step that must pass is recorded.

    Returns the receipts that the record keeps, which is what closes the findings: the closing is part of the same
    journal line as the record. A case that still fails refuses the record, so no finding is closed alone.
    """
    green = green_id(schema)
    if green is None or step.id != green:
        return ()
    runs = tuple(
        _case_run(finding, runner, desk.root)
        for finding in review.open_findings(log, journal, green)
    )
    decision = review.close(runs)
    if isinstance(decision, Refused):
        raise desk.refusal(decision)
    return decision


def _case_run(finding: Finding, runner: CommandRunner, root: Path) -> CaseRun:
    outcome = runner.run(list(finding.argv), root)
    return CaseRun(finding, Observation(outcome.as_value(), outcome.problem))


def _candidate(desk: Desk) -> Observed:
    observed = read_candidate(desk.root, desk.workspace.directory)
    if isinstance(observed, Unreadable):
        raise Refusal(
            what=f"the candidate cannot be read: {observed.reason}",
            why="a packet and a verdict name the candidate by its identity, which is read from the project directory",
            how=desk.how.command("packet", *desk.located[:3], "<project directory>"),
        )
    return observed


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
