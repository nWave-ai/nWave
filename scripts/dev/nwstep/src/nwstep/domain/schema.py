"""The schema: the ordered steps, checked for unique ids, known references and acyclic needs; and, for a schema that
declares sizes, which steps each size makes due, where it pauses for the person, and which step closes it."""

from __future__ import annotations

from nwstep.domain.field import Field
from nwstep.domain.field_kind import FieldKind
from nwstep.domain.sentence_coverage import SentenceCoverage
from nwstep.domain.size import Size
from nwstep.domain.step import Step


class Schema:
    def __init__(self, steps: tuple[Step, ...]) -> None:
        if not steps:
            raise ValueError("the schema declares no steps")
        by_id: dict[str, Step] = {}
        for step in steps:
            if step.id in by_id:
                raise ValueError(f"step '{step.id}' is declared twice")
            by_id[step.id] = step
        for step in steps:
            self._check_references(step, by_id)
        settled: set[str] = set()
        for step in steps:
            self._visit(step.id, by_id, [], settled)
        sized = [step.id for step in steps if step.sizes is not None]
        if sized and len(sized) != len(steps):
            unsized = next(step.id for step in steps if step.sizes is None)
            raise ValueError(
                f"step '{unsized}' names no sizes, but other steps do: a sized schema names the sizes of every step"
            )
        self._steps = self._by_dependency(steps)
        self._by_id = by_id

    @property
    def steps(self) -> tuple[Step, ...]:
        return self._steps

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(step.id for step in self._steps)

    @property
    def sized(self) -> bool:
        """Whether the schema declares sizes; a schema without them runs every step, as size L did before sizes."""
        return any(step.sizes is not None for step in self._steps)

    @property
    def has_pauses(self) -> bool:
        """Whether any step of the schema pauses for the person; a schema without pauses keeps the interactive text it had before pauses."""
        return any(step.pauses for step in self._steps)

    def declares(self, kind: FieldKind) -> bool:
        """Whether any step of this schema declares a field of the given kind."""
        return any(field.kind is kind for step in self._steps for field in step.fields)

    def due_ids(self, size: Size | None) -> tuple[str, ...]:
        """The steps the size makes due, in schema order; every step when no size is declared."""
        return tuple(step.id for step in self._steps if step.is_due_for(size))

    def is_due(self, step_id: str, size: Size | None) -> bool:
        step = self._by_id.get(step_id)
        return step is not None and step.is_due_for(size)

    def pauses_after(self, step_id: str, size: Size | None) -> bool:
        """Whether, in interactive mode, the person is asked before the next step once this step is recorded."""
        step = self._by_id.get(step_id)
        return step is not None and step.pauses_for(size)

    def effective_needs(self, step_id: str, size: Size | None) -> tuple[str, ...]:
        """The due steps a step waits for: its needs, and through a need that the size skips, the needs of that need."""
        found: list[str] = []
        for need in self._by_id[step_id].needs:
            if self.is_due(need, size):
                if need not in found:
                    found.append(need)
                continue
            for through in self.effective_needs(need, size):
                if through not in found:
                    found.append(through)
        return tuple(found)

    def next_due(self, recorded: frozenset[str], size: Size | None) -> str | None:
        """The first step, in schema order, that the size makes due, is not recorded yet, and waits for nothing unrecorded."""
        return next(
            (
                step.id
                for step in self._steps
                if step.is_due_for(size)
                and step.id not in recorded
                and all(
                    need in recorded for need in self.effective_needs(step.id, size)
                )
            ),
            None,
        )

    def closing_step(self, size: Size | None) -> str | None:
        """The step that closes a delivery of the size: its last due step, when the schema declares sizes."""
        if not self.sized or size is None:
            return None
        due = self.due_ids(size)
        return due[-1] if due else None

    def missing_due(
        self, recorded: frozenset[str], size: Size | None, *, leaving_out: str
    ) -> tuple[str, ...]:
        """The due steps of the size that are not recorded, other than the one named, in schema order."""
        return tuple(
            step_id
            for step_id in self.due_ids(size)
            if step_id not in recorded and step_id != leaving_out
        )

    def green_step(self) -> Step | None:
        """The first step, in order, whose required command must pass: the record of it is what shows the change green."""
        return next(
            (
                step
                for step in self._steps
                if any(
                    field.kind is FieldKind.COMMAND
                    and field.required
                    and field.expect == "pass"
                    and field.runs_on is None
                    for field in step.fields
                )
            ),
            None,
        )

    @staticmethod
    def _by_dependency(steps: tuple[Step, ...]) -> tuple[Step, ...]:
        """Declared order made consistent with `needs`: a step never precedes what it needs."""
        placed: list[Step] = []
        done: set[str] = set()
        pending = list(steps)
        while pending:
            ready = next(step for step in pending if set(step.needs) <= done)
            pending.remove(ready)
            placed.append(ready)
            done.add(ready.id)
        return tuple(placed)

    def find(self, step_id: str) -> Step | None:
        return self._by_id.get(step_id)

    def field_of(self, step_id: str, field_name: str) -> Field:
        """The field a checked reference names; the schema has already proven it exists."""
        field = self._by_id[step_id].field(field_name)
        if field is None:
            raise ValueError(f"the schema has no field '{step_id}.{field_name}'")
        return field

    @classmethod
    def _check_references(cls, step: Step, by_id: dict[str, Step]) -> None:
        for need in step.needs:
            if need not in by_id:
                raise ValueError(f"step '{step.id}' needs unknown step '{need}'")
        for field in step.fields:
            where = f"field '{step.id}.{field.name}'"
            if field.covers is not None:
                cls._check_list_reference(
                    by_id,
                    where,
                    "covers",
                    field.covers,
                    (FieldKind.LIST, FieldKind.SCENARIOS),
                )
            if field.decides is not None:
                cls._check_list_reference(
                    by_id, where, "decides", field.decides, (FieldKind.CONFLICTS,)
                )
            if field.needs_ids is not None:
                cls._check_list_reference(by_id, where, "needs_ids", field.needs_ids)
            if field.covers_sentences is not None:
                cls._check_sentence_reference(step, field)
            if field.cross_with is not None:
                source = step.field(field.cross_with)
                if source is None or source.kind is not FieldKind.LIST:
                    raise ValueError(
                        f"{where} crosses with '{field.cross_with}', which is not a list field of the same step"
                    )

    @staticmethod
    def _check_list_reference(
        by_id: dict[str, Step],
        where: str,
        option: str,
        reference: tuple[str, str],
        kinds: tuple[FieldKind, ...] = (FieldKind.LIST,),
    ) -> None:
        target_step, target_field = reference
        if target_step not in by_id:
            raise ValueError(f"{where} {option} unknown step '{target_step}'")
        source = by_id[target_step].field(target_field)
        if source is None or source.kind not in kinds:
            names = " or ".join(kind.value for kind in kinds)
            raise ValueError(
                f"{where} {option} '{target_step}.{target_field}', which is not a {names} field"
            )

    @staticmethod
    def _check_sentence_reference(step: Step, field: Field) -> None:
        where = f"field '{step.id}.{field.name}'"
        source = step.field(field.covers_sentences or "")
        if source is None or source.kind is not FieldKind.PATHS:
            raise ValueError(
                f"{where} covers the sentences of '{field.covers_sentences}', which is not a paths field of the same step"
            )
        promises = step.field(SentenceCoverage.PROMISES)
        if promises is None or promises.kind is not FieldKind.LIST:
            raise ValueError(
                f"{where} maps sentences to promises, so step '{step.id}' needs a list field '{SentenceCoverage.PROMISES}'"
            )

    @classmethod
    def _visit(
        cls, step_id: str, by_id: dict[str, Step], trail: list[str], settled: set[str]
    ) -> None:
        if step_id in trail:
            cycle = [*trail[trail.index(step_id) :], step_id]
            raise ValueError(f"steps need each other in a cycle: {' -> '.join(cycle)}")
        if step_id in settled:
            return
        for need in by_id[step_id].needs:
            cls._visit(need, by_id, [*trail, step_id], settled)
        settled.add(step_id)
