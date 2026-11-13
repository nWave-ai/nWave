"""The HOW line of a refused record.

A refusal whose fault has a mechanical repair (wrong flag form, duplicate scalar, unknown
field, absent path with another path still given) yields a command that runs verbatim.
Content the tool cannot know (a missing text, a bad choice, a failing command, an uncovered
id) is marked with <placeholders>; inventing it would be a fabricated value.
"""

from __future__ import annotations

from pathlib import Path

from nwstep.application.how_line import HowLine
from nwstep.domain.command_line import CommandLine
from nwstep.domain.fault import Fault
from nwstep.domain.field import Field
from nwstep.domain.refusal import Refusal
from nwstep.domain.step import Step
from nwstep.domain.submission import Submission


class RecordHow:
    def __init__(self, how: HowLine, workspace: Path, root: Path) -> None:
        self._how = how
        self._workspace = workspace
        self._root = root

    def for_refusal(self, step: Step, submission: Submission, refusal: Refusal) -> str:
        args = [
            "record",
            step.id,
            "--workspace",
            str(self._workspace),
            "--root",
            str(self._root),
        ]
        for field in step.fields:
            if field.kind.is_multi:
                args += self._item_args(field, submission, refusal)
            else:
                args += self._scalar_args(field, submission, refusal)
        return self._how.command(*args)

    def _scalar_args(
        self, field: Field, submission: Submission, refusal: Refusal
    ) -> list[str]:
        raw = submission.scalar(field.name)
        if field.name == refusal.field:
            if refusal.fault is Fault.WRONG_FORM:
                raw = submission.items_of(field.name)[0]
            elif refusal.fault is Fault.SHELL_OPERATOR and raw is not None:
                raw = CommandLine.first_invocation(raw)
            elif refusal.fault not in (Fault.DUPLICATE, Fault.AS_WRITTEN):
                return [f"--{field.name}", field.placeholder()]
        if raw is None:
            return [f"--{field.name}", field.placeholder()] if field.required else []
        return [f"--{field.name}", raw]

    def _item_args(
        self, field: Field, submission: Submission, refusal: Refusal
    ) -> list[str]:
        failing = field.name == refusal.field
        if failing and refusal.fault is Fault.WRONG_FORM:
            values = submission.scalars_of(field.name)
        else:
            values = submission.items_of(field.name)
        if failing:
            values = [value for value in values if value not in refusal.rejected]
            values += [field.template_for(identifier) for identifier in refusal.missing]
        minimum = field.min_items if field.required else 0
        values += [field.placeholder()] * max(0, minimum - len(values))
        args: list[str] = []
        for value in values:
            args += ["--item", f"{field.name}={value}"]
        return args
