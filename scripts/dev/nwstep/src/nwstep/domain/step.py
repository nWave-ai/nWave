"""A named step of the schema: what it needs first, whether it repeats, whether recording it replays the steps it made
stale, whether its record is a verdict about one candidate, whether recording it runs the pre-review checks the
candidate declares, the sizes it is due in, the sizes after which the person is asked, and its fields."""

from __future__ import annotations

from collections.abc import Iterable

from nwstep.domain.field import Field
from nwstep.domain.field_kind import FieldKind
from nwstep.domain.size import Size
from nwstep.domain.skill_name import SkillName


class Step:
    def __init__(
        self,
        step_id: str,
        title: str,
        help_text: str,
        *,
        needs: Iterable[str] = (),
        repeat: bool = False,
        replay: bool = False,
        verdict: bool = False,
        prereview: bool = False,
        fields: Iterable[Field] = (),
        skills: Iterable[str] = (),
        sizes: Iterable[Size] | None = None,
        pauses: Iterable[Size] = (),
    ) -> None:
        if (
            not step_id
            or step_id.startswith("-")
            or "=" in step_id
            or any(c.isspace() for c in step_id)
        ):
            raise ValueError(f"step id '{step_id}' must be one bare word")
        if not title.strip() or not help_text.strip():
            raise ValueError(f"step '{step_id}' needs a title and a help sentence")
        needs_tuple = tuple(needs)
        if step_id in needs_tuple:
            raise ValueError(f"step '{step_id}' cannot need itself")
        fields_tuple = tuple(fields)
        names = [field.name for field in fields_tuple]
        for name in names:
            if names.count(name) > 1:
                raise ValueError(f"step '{step_id}' declares field '{name}' twice")
        for field in fields_tuple:
            if field.fallback is None:
                continue
            target = next(
                (other for other in fields_tuple if other.name == field.fallback), None
            )
            if target is None or target.kind is not FieldKind.COMMAND:
                raise ValueError(
                    f"step '{step_id}': field '{field.name}' falls back to '{field.fallback}', "
                    "which must be a command field of the same step"
                )
        skill_names = tuple(SkillName(text) for text in skills)
        if len({name.text for name in skill_names}) != len(skill_names):
            raise ValueError(f"step '{step_id}' names a skill twice")
        due_in = None if sizes is None else frozenset(sizes)
        pause_in = frozenset(pauses)
        if due_in is not None and not pause_in <= due_in:
            raise ValueError(
                f"step '{step_id}' pauses for a size it is not due in: pauses must be a subset of sizes"
            )

        self.id = step_id
        self.title = title.strip()
        self.help = help_text.strip()
        self.needs = needs_tuple
        self.repeat = repeat
        self.replay = replay
        # A verdict holds for the candidate it judged: a replay never records it again from its kept submission.
        self.verdict = verdict
        self.prereview = prereview
        self.fields = fields_tuple
        self.skills = skill_names
        # None: due in every size, as every step of a schema without sizes is.
        self.sizes = due_in
        self.pauses = pause_in

    def field(self, name: str) -> Field | None:
        return next((field for field in self.fields if field.name == name), None)

    def is_due_for(self, size: Size | None) -> bool:
        """Due for every size when the step names none; with no size declared (None) every step is due."""
        return self.sizes is None or size is None or size in self.sizes

    def pauses_for(self, size: Size | None) -> bool:
        return size is not None and size in self.pauses
