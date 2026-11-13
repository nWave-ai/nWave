"""The lines the review adds to what the tool prints: the stale line, the status lines, the reviewer's packet and
the review section of the summary. Pure: every line is derived from the log, the journal and the values given.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwstep.domain import review


if TYPE_CHECKING:
    from nwstep.domain.journal import Journal
    from nwstep.domain.review import Finding, Packet, ReviewLog

UPSTREAM_CAUSE = "an earlier step was recorded again after them; record them again or say why they still hold"
VERDICT_STEP_NOTE = "a verdict holds only for the candidate it judged: record it again for this candidate"


def stale_line(stale: tuple[str, ...], waiting: tuple[Finding, ...]) -> str | None:
    """The one line that names the stale steps, with the cause the reader can act on."""
    if not stale:
        return None
    cause = UPSTREAM_CAUSE
    if waiting:
        names = ", ".join(finding.identifier for finding in waiting)
        cause = (
            f"finding {names} is open: when its case passes, replay records them again"
        )
    return f"stale ({cause}): {', '.join(stale)}"


def finding_state(finding: Finding, journal: Journal, green_step: str | None) -> str:
    position = review.closing_position(finding, journal, green_step)
    if position is None:
        return "open"
    closing = journal.records[position]
    return f"closed by {closing.step} revision {closing.revision}"


def verdict_line(log: ReviewLog, journal: Journal, green_step: str | None) -> str:
    """The latest verdict, with what has happened to the candidate since: nothing is said to hold beyond its identity."""
    verdict = log.latest_verdict
    if verdict is None:
        return "verdict: none recorded"
    line = f"verdict: {verdict.describe()}"
    frozen = log.latest_packet
    if frozen is not None and frozen.candidate != verdict.candidate:
        return f"{line}; {frozen.candidate} was frozen after it and has no verdict"
    if review.spent_verdict(log, journal, green_step) is not None:
        return f"{line}; a delta closed after it changed the candidate, which needs a new packet and a new verdict"
    return line


def status_lines(
    log: ReviewLog, journal: Journal, green_step: str | None
) -> tuple[str, ...]:
    """Nothing for a workspace without review records, so its status reads as it always did."""
    if not log.events:
        return ()
    lines: list[str] = []
    frozen = log.latest_packet
    if frozen is not None:
        lines.append(f"candidate: {frozen.candidate} frozen for review")
    if log.verdicts:
        lines.append(verdict_line(log, journal, green_step))
    lines += [
        f"finding {finding.identifier} by {finding.author}: {finding_state(finding, journal, green_step)}"
        for finding in log.findings
    ]
    return tuple(lines)


def packet_lines(  # noqa: PLR0913 - one line per fact the reviewer needs; each fact is an argument
    packet: Packet,
    log: ReviewLog,
    *,
    root: str,
    workspace: str,
    base: str,
    stale: tuple[str, ...],
    verdict_command: str,
) -> tuple[str, ...]:
    holding = review.verdict_for(log, packet.candidate)
    earlier = [
        verdict for verdict in log.verdicts if verdict.candidate != packet.candidate
    ]
    lines = [
        "REVIEW PACKET",
        f"candidate: {packet.candidate}",
        f"root: {root}",
        f"workspace: {workspace}",
        f"base: {base}",
    ]
    if stale:
        lines.append(f"stale steps: {', '.join(stale)}")
    lines.append(
        "verdict: none recorded for this candidate"
        if holding is None
        else f"verdict: {holding.outcome} by {holding.reviewer} (recorded {holding.recorded_at})"
    )
    if earlier:
        lines.append(
            f"earlier verdict: {earlier[-1].describe()}; it does not hold for this candidate"
        )
    lines += [
        "A verdict holds only for this candidate identity. If the candidate changes, run packet again and review the new candidate.",
        f"record the verdict with: {verdict_command}",
    ]
    return tuple(lines)


def summary_lines(
    log: ReviewLog, journal: Journal, green_step: str | None
) -> list[str]:
    """The review section of the summary brief; empty when the workspace holds no review record."""
    if not log.events:
        return []
    lines = ["## Review", ""]
    lines += [
        f"- candidate frozen: {packet.candidate} (recorded {packet.recorded_at})"
        for packet in log.packets
    ]
    lines += [
        f"- verdict: {verdict.describe()} (recorded {verdict.recorded_at}); it holds for that identity only"
        for verdict in log.verdicts
    ]
    for finding in log.findings:
        lines += [
            f"- finding {finding.identifier} by {finding.author}: {finding.text}",
            f"  - case seen failing by the tool: `{finding.command}` exited {finding.red.get('exit_code')}",
            f"  - state: {finding_state(finding, journal, green_step)}",
        ]
    return [*lines, ""]
