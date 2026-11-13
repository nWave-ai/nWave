"""The review of a delivery, kept beside its journal: frozen candidates, verdicts and findings.

Pure decisions over values. A packet freezes the identity of a candidate; a verdict holds for the identity frozen
last while the candidate still has it; a finding stays open until the step that must pass is recorded again, and
that one record closes every open finding, so the corrections after a verdict form one delta.

Every decision returns its outcome: the event to append, `Repeated` when the same thing is already recorded, or
`Refused` with what and why and the remedy the shell turns into a command line. Nothing here reads a file, a
clock or a process: the journal, the log, the observed identity and the time are arguments.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from nwstep.domain import candidate
from nwstep.domain.command_line import CommandLine, UnquotedOperator


if TYPE_CHECKING:
    from collections.abc import Mapping

    from nwstep.domain.candidate import Identity
    from nwstep.domain.journal import Journal

CLOSED_KEY = "findings_closed"
OUTCOMES = ("accepted", "rejected")
MIN_NAME_CHARS = 3
MIN_TEXT_CHARS = 20


class Remedy(Enum):
    """The command a refusal points at; the shell writes the line."""

    PACKET = "packet"
    REPLAY = "replay"
    STATUS = "status"
    FINDING = "finding"
    VERDICT = "verdict"


@dataclass(frozen=True)
class Refused:
    what: str
    why: str
    remedy: Remedy


@dataclass(frozen=True)
class Packet:
    seq: int
    recorded_at: str
    candidate: str
    journal_records: int


@dataclass(frozen=True)
class Verdict:
    seq: int
    recorded_at: str
    reviewer: str
    outcome: str
    candidate: str
    journal_records: int

    def describe(self) -> str:
        return f"{self.outcome} by {self.reviewer} for {self.candidate}"


@dataclass(frozen=True)
class Finding:
    seq: int
    recorded_at: str
    identifier: str
    author: str
    text: str
    red: Mapping[str, Any]
    journal_records: int

    @property
    def argv(self) -> tuple[str, ...]:
        return tuple(str(word) for word in self.red["argv"])

    @property
    def command(self) -> str:
        return shlex.join(self.argv)


Event = Packet | Verdict | Finding
KINDS: dict[str, type[Packet] | type[Verdict] | type[Finding]] = {
    "packet": Packet,
    "verdict": Verdict,
    "finding": Finding,
}


Recorded = TypeVar("Recorded", Packet, Verdict, Finding)


@dataclass(frozen=True)
class Repeated(Generic[Recorded]):
    """The same thing is already the latest record of its kind: nothing new is written."""

    event: Recorded


@dataclass(frozen=True)
class ReviewLog:
    events: tuple[Event, ...] = ()

    @property
    def packets(self) -> tuple[Packet, ...]:
        return tuple(event for event in self.events if isinstance(event, Packet))

    @property
    def verdicts(self) -> tuple[Verdict, ...]:
        return tuple(event for event in self.events if isinstance(event, Verdict))

    @property
    def findings(self) -> tuple[Finding, ...]:
        """Each finding as last reported: a later record under the same name corrects the case of the earlier one."""
        latest: dict[str, Finding] = {}
        for event in self.events:
            if isinstance(event, Finding):
                latest[event.identifier] = event
        return tuple(latest.values())

    @property
    def latest_packet(self) -> Packet | None:
        return self.packets[-1] if self.packets else None

    @property
    def latest_verdict(self) -> Verdict | None:
        return self.verdicts[-1] if self.verdicts else None

    @property
    def next_seq(self) -> int:
        return len(self.events) + 1


def to_value(event: Event) -> dict[str, Any]:
    kind = next(name for name, shape in KINDS.items() if isinstance(event, shape))
    return {"kind": kind, **{name: getattr(event, name) for name in _names(event)}}


def from_value(value: Mapping[str, Any]) -> Event | None:
    """The event a stored line holds, or None when the line is not one of the three kinds with all its parts."""
    shape = KINDS.get(str(value.get("kind")))
    if shape is None:
        return None
    names = tuple(shape.__dataclass_fields__)
    if any(name not in value for name in names):
        return None
    return shape(**{name: value[name] for name in names})


def _names(event: Event) -> tuple[str, ...]:
    return tuple(type(event).__dataclass_fields__)


# --- findings ---------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FindingDraft:
    """A finding as its author gave it, already well formed: who, what, and the one invocation that proves it."""

    author: str
    text: str
    argv: tuple[str, ...]

    @property
    def command(self) -> str:
        return shlex.join(self.argv)


def finding_draft(author: str, text: str, red: str) -> FindingDraft | Refused:
    problems = [
        *_short("--author", author, MIN_NAME_CHARS),
        *_short("--text", text, MIN_TEXT_CHARS),
    ]
    argv: tuple[str, ...] = ()
    try:
        argv = CommandLine.parse(red).argv
    except UnquotedOperator as error:
        problems.append(
            f"--red holds the shell operator '{error.operator.text}': the case is run without a shell"
        )
    except ValueError as error:
        problems.append(f"--red is not a command line: {error}")
    else:
        if not argv:
            problems.append("--red is empty: a finding needs the case that proves it")
    if problems:
        return Refused(
            what="; ".join(problems),
            why="a finding says who wrote it, what it says and which one invocation fails because of it",
            remedy=Remedy.FINDING,
        )
    return FindingDraft(author.strip(), text.strip(), argv)


def green_indexes(journal: Journal, green_step: str | None) -> tuple[int, ...]:
    return tuple(
        index
        for index, record in enumerate(journal.records)
        if record.step == green_step
    )


def closing_position(
    finding: Finding, journal: Journal, green_step: str | None
) -> int | None:
    """The journal position of the record that closed the finding: the first record of the green step after it."""
    return next(
        (
            index
            for index in green_indexes(journal, green_step)
            if index >= finding.journal_records
        ),
        None,
    )


def open_findings(
    log: ReviewLog, journal: Journal, green_step: str | None
) -> tuple[Finding, ...]:
    return tuple(
        finding
        for finding in log.findings
        if closing_position(finding, journal, green_step) is None
    )


def reopened(
    log: ReviewLog, journal: Journal, green_step: str | None
) -> frozenset[str]:
    """The steps an open finding reopens: the green step, when it is recorded and a finding waits for it."""
    if green_step is None or not open_findings(log, journal, green_step):
        return frozenset()
    return frozenset({green_step})


def spent_verdict(
    log: ReviewLog, journal: Journal, green_step: str | None
) -> tuple[Verdict, int] | None:
    """The latest verdict when a delta was closed after it, with the journal position of the closing record."""
    verdict = log.latest_verdict
    if verdict is None:
        return None
    closings = [
        position
        for finding in log.findings
        if (position := closing_position(finding, journal, green_step)) is not None
        and position >= verdict.journal_records
    ]
    return (verdict, min(closings)) if closings else None


@dataclass(frozen=True)
class Admitted:
    """A finding the state admits, under the name it is kept by: a new one, or an open one whose case is corrected."""

    draft: FindingDraft
    identifier: str
    corrects: Finding | None


def finding_gate(
    log: ReviewLog, journal: Journal, green_step: str | None, draft: FindingDraft
) -> Refused | Repeated[Finding] | Admitted:
    """Whether the state admits the finding, decided before its case is run.

    An open finding reported again by its author with the same text and another case is that finding with its case
    corrected: the earlier record stays, and only the corrected case has to pass.
    """
    if green_step is None:
        return Refused(
            what="this schema has no step whose required command must pass",
            why="a finding is closed by the record of the step that must pass; without such a step no record could ever close it",
            remedy=Remedy.STATUS,
        )
    spent = spent_verdict(log, journal, green_step)
    if spent is not None:
        verdict, position = spent
        closing = journal.records[position]
        return Refused(
            what=(
                f"the verdict {verdict.describe()} already had its delta, closed by '{closing.step}' "
                f"revision {closing.revision}"
            ),
            why=(
                "the corrections after a verdict form one delta; that delta changed the candidate, "
                "so the verdict no longer applies and a further finding needs a verdict on the new candidate"
            ),
            remedy=Remedy.PACKET,
        )
    same = next(
        (
            finding
            for finding in open_findings(log, journal, green_step)
            if (finding.author, finding.text) == (draft.author, draft.text)
        ),
        None,
    )
    if same is None:
        return Admitted(draft, f"F{len(log.findings) + 1}", None)
    if same.argv == draft.argv:
        return Repeated(same)
    return Admitted(draft, same.identifier, same)


@dataclass(frozen=True)
class Observation:
    """One run of a case as the tool saw it: the recorded run, and the reason when it could not start or finish."""

    run: Mapping[str, Any]
    problem: str | None

    @property
    def passed(self) -> bool:
        return self.problem is None and self.run.get("exit_code") == 0

    def describe(self) -> str:
        return self.problem or f"exited {self.run.get('exit_code')}"


def finding_observed(
    log: ReviewLog,
    journal: Journal,
    admitted: Admitted,
    seen: Observation,
    recorded_at: str,
) -> Finding | Refused:
    """The finding with the run of its case, or the refusal of a case that did not fail on the candidate."""
    if seen.problem is not None:
        return Refused(
            what=f"the case of the finding did not run: {seen.problem}",
            why="a finding is proven by a case the tool itself saw fail; a case that cannot start proves nothing",
            remedy=Remedy.FINDING,
        )
    if seen.passed:
        return Refused(
            what=f"the case of the finding exited 0 on the candidate: `{admitted.draft.command}`",
            why="a case that passes on the candidate proves no finding; the case must fail now and pass after the fix",
            remedy=Remedy.FINDING,
        )
    return Finding(
        seq=log.next_seq,
        recorded_at=recorded_at,
        identifier=admitted.identifier,
        author=admitted.draft.author,
        text=admitted.draft.text,
        red=dict(seen.run),
        journal_records=len(journal.records),
    )


@dataclass(frozen=True)
class CaseRun:
    """The case of one open finding, run again on the candidate."""

    finding: Finding
    seen: Observation

    @property
    def passed(self) -> bool:
        return self.seen.passed

    def describe(self) -> str:
        return f"{self.finding.identifier} (`{self.finding.command}` {self.seen.describe()})"


def close(runs: tuple[CaseRun, ...]) -> tuple[dict[str, Any], ...] | Refused:
    """The receipts that close every open finding in one record, or the refusal naming each case that still fails."""
    failing = [run for run in runs if not run.passed]
    if failing:
        return Refused(
            what="the case of an open finding still fails: "
            + "; ".join(run.describe() for run in failing),
            why=(
                "a finding is closed only when the tool sees its case pass, and the corrections enter one delta: "
                "the record of the step that must pass closes every open finding or none"
            ),
            remedy=Remedy.REPLAY,
        )
    return tuple(
        {"finding": run.finding.identifier, "green": dict(run.seen.run)} for run in runs
    )


# --- candidates and verdicts ------------------------------------------------------------------------------------


def freeze(
    log: ReviewLog,
    journal: Journal,
    green_step: str | None,
    identity: Identity,
    recorded_at: str,
) -> Packet | Repeated[Packet] | Refused:
    waiting = open_findings(log, journal, green_step)
    if waiting:
        return Refused(
            what="a finding is open: "
            + ", ".join(finding.identifier for finding in waiting),
            why=(
                "the corrections after a verdict form one delta; a candidate frozen while a finding is open "
                "would be judged before the delta is complete and need a second one"
            ),
            remedy=Remedy.REPLAY,
        )
    latest = log.latest_packet
    if latest is not None and latest.candidate == identity.text:
        return Repeated(latest)
    return Packet(
        seq=log.next_seq,
        recorded_at=recorded_at,
        candidate=identity.text,
        journal_records=len(journal.records),
    )


def verdict_for(log: ReviewLog, identity: str) -> Verdict | None:
    """The latest verdict that holds for this identity; a verdict for any other identity is not it."""
    return next(
        (
            verdict
            for verdict in reversed(log.verdicts)
            if verdict.candidate == identity
        ),
        None,
    )


@dataclass(frozen=True)
class VerdictDraft:
    """A verdict as its reviewer gave it, already well formed."""

    reviewer: str
    outcome: str
    candidate: Identity


def verdict_draft(reviewer: str, named: str, outcome: str) -> VerdictDraft | Refused:
    identity = candidate.parse(named)
    problems = [*_short("--reviewer", reviewer, MIN_NAME_CHARS)]
    if identity is None:
        problems.append(
            f"--candidate '{named}' is not a candidate identity ({candidate.SHAPE})"
        )
    if outcome not in OUTCOMES:
        problems.append(
            f"--outcome '{outcome}' is not a verdict: use {' or '.join(OUTCOMES)}"
        )
    if problems or identity is None:
        return Refused(
            what="; ".join(problems),
            why="a verdict says who gave it, which candidate identity it judged and what it decided",
            remedy=Remedy.PACKET,
        )
    return VerdictDraft(reviewer.strip(), outcome, identity)


def judge(
    log: ReviewLog,
    journal: Journal,
    draft: VerdictDraft,
    current: Identity,
    recorded_at: str,
) -> Verdict | Repeated[Verdict] | Refused:
    """A verdict is recorded only for the identity frozen last, while the candidate still has it."""
    named = draft.candidate.text
    if all(packet.candidate != named for packet in log.packets):
        return Refused(
            what=f"no packet froze {named}",
            why="a verdict is given on the candidate a packet named for the reviewer; without the packet nothing says which candidate was judged",
            remedy=Remedy.PACKET,
        )
    frozen = log.latest_packet
    if frozen is None or frozen.candidate != named or current.text != named:
        return Refused(
            what=(
                f"the verdict names {named}, but the candidate is now {current.text}"
                + (
                    ""
                    if frozen is None or frozen.candidate in (named, current.text)
                    else f" (frozen last: {frozen.candidate})"
                )
            ),
            why="a verdict holds only for the identity it judged; a changed candidate needs a new verdict, and the old one cannot be applied to it",
            remedy=Remedy.PACKET,
        )
    latest = log.latest_verdict
    if latest is not None and (latest.reviewer, latest.outcome, latest.candidate) == (
        draft.reviewer,
        draft.outcome,
        named,
    ):
        return Repeated(latest)
    return Verdict(
        seq=log.next_seq,
        recorded_at=recorded_at,
        reviewer=draft.reviewer,
        outcome=draft.outcome,
        candidate=named,
        journal_records=len(journal.records),
    )


def _short(option: str, value: str, minimum: int) -> list[str]:
    length = len(value.strip())
    if length >= minimum:
        return []
    return [f"{option} needs at least {minimum} characters, got {length}"]
