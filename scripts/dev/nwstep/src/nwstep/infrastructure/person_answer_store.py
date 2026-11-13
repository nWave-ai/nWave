"""Keeps the person's answers to the pauses of a workspace, in the order given, each with its text and author."""

from __future__ import annotations

from nwstep.domain.person_answer import PersonAnswer
from nwstep.infrastructure.atomic_json import read_json, write_json
from nwstep.infrastructure.workspace import Workspace


class PersonAnswerStore:
    def __init__(self, workspace: Workspace) -> None:
        self._path = workspace.answers_path

    def read(self) -> tuple[PersonAnswer, ...]:
        document = read_json(self._path)
        if document is None:
            return ()
        return tuple(PersonAnswer.from_dict(item) for item in document["answers"])

    def append(self, answer: PersonAnswer) -> None:
        write_json(
            self._path,
            {"answers": [item.to_dict() for item in [*self.read(), answer]]},
        )
