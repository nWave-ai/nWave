"""Answers which step is next, which steps remain, the status of every due step, and whether the person is awaited,
from the schema, the declared size, the journal, the person's answers and the run mode."""

from __future__ import annotations

from collections.abc import Sequence

from nwstep.application.step_status import StepStatus
from nwstep.domain.journal import Journal
from nwstep.domain.person_answer import Pause, PersonAnswer
from nwstep.domain.schema import Schema
from nwstep.domain.size import Size
from nwstep.domain.step import Step


class Progress:
    def __init__(self, schema: Schema, size: Size | None = None) -> None:
        self._schema = schema
        self._size = size

    @property
    def size(self) -> Size | None:
        return self._size

    def next_ready(self, journal: Journal) -> Step | None:
        step_id = self._schema.next_due(self.recorded(journal), self._size)
        return None if step_id is None else self._schema.find(step_id)

    def remaining(self, journal: Journal) -> tuple[str, ...]:
        return tuple(
            step_id
            for step_id in self._schema.due_ids(self._size)
            if not journal.recorded(step_id)
        )

    def not_due(self) -> tuple[str, ...]:
        """The steps the declared size skips, in schema order."""
        due = set(self._schema.due_ids(self._size))
        return tuple(step_id for step_id in self._schema.ids if step_id not in due)

    def statuses(self, journal: Journal) -> tuple[StepStatus, ...]:
        return tuple(
            StepStatus(
                step_id, journal.revisions(step_id), self.unmet(step_id, journal)
            )
            for step_id in self._schema.due_ids(self._size)
        )

    def pending_pause(
        self,
        journal: Journal,
        answers: Sequence[PersonAnswer],
        interactive: bool,
    ) -> Pause | None:
        """The question the person must answer now: in interactive mode, when the last record is a pause step of the
        declared size and no answer has been given to that record yet."""
        if not interactive or not journal.records:
            return None
        last = journal.records[-1]
        if not self._schema.pauses_after(last.step, self._size):
            return None
        if any(answer.after_seq == last.seq for answer in answers):
            return None
        return Pause.after(last.seq, last.step, self._next_step_id(journal))

    def _next_step_id(self, journal: Journal) -> str | None:
        return self._schema.next_due(self.recorded(journal), self._size)

    def recorded(self, journal: Journal) -> frozenset[str]:
        return frozenset(
            step_id for step_id in self._schema.ids if journal.recorded(step_id)
        )

    def unmet(self, step_id: str, journal: Journal) -> tuple[str, ...]:
        return tuple(
            need
            for need in self._schema.effective_needs(step_id, self._size)
            if not journal.recorded(need)
        )

    def stale(
        self, journal: Journal, reopened: frozenset[str] = frozenset()
    ) -> tuple[str, ...]:
        """Recorded steps that no longer describe the work: an earlier step they rely on was recorded again after
        them, or an open finding reopened them or a step they rely on."""
        return tuple(
            step.id
            for step in self._schema.steps
            if journal.recorded(step.id)
            and (
                self._upstream_is_newer(step, journal)
                or bool(reopened & ({step.id} | self._needed_by(step)))
            )
        )

    def replayable(
        self, journal: Journal, reopened: frozenset[str] = frozenset()
    ) -> tuple[str, ...]:
        """The stale steps a replay may record again from their kept submissions: never a verdict step, which holds
        for the candidate it judged, and never a step that relies on a stale verdict step."""
        stale = self.stale(journal, reopened)
        held = {step_id for step_id in stale if self._is_verdict(step_id)}
        return tuple(
            step_id
            for step_id in stale
            if step_id not in held
            and not held & self._needed_by(self._schema.find(step_id))
        )

    def _is_verdict(self, step_id: str) -> bool:
        step = self._schema.find(step_id)
        return step is not None and step.verdict

    def _needed_by(self, step: Step | None) -> set[str]:
        """Every step the given step relies on, directly or through another step."""
        pending = [] if step is None else list(step.needs)
        seen: set[str] = set()
        while pending:
            need = pending.pop()
            if need in seen:
                continue
            seen.add(need)
            upstream = self._schema.find(need)
            if upstream is not None:
                pending.extend(upstream.needs)
        return seen

    def _upstream_is_newer(self, step: Step, journal: Journal) -> bool:
        own = journal.last_position(step.id)
        return any(journal.last_position(need) > own for need in self._needed_by(step))
