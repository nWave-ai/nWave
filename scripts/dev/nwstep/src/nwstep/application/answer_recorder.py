"""Records the person's answer to the pause that the journal awaits. The journal lock is held while the pause is read
and the answer is written, so an answer and a record never interleave on one workspace.

What it proves: an answer is kept only for the pause that is awaited at that moment, with its text and its author.
What it does not prove: that the person who gave the answer is the person named, since the tool keeps the id given.
"""

from __future__ import annotations

from nwstep.application.how_line import HowLine
from nwstep.application.progress import Progress
from nwstep.domain import run_mode
from nwstep.domain.person_answer import PersonAnswer
from nwstep.domain.refusal import Refusal
from nwstep.domain.size import Size
from nwstep.infrastructure.jsonl_journal import JsonlJournal
from nwstep.infrastructure.person_answer_store import PersonAnswerStore
from nwstep.infrastructure.size_store import SizeStore
from nwstep.infrastructure.toml_schema_reader import TomlSchemaReader
from nwstep.infrastructure.workspace import Workspace
from nwstep.infrastructure.workspace_mode import WorkspaceMode


class AnswerRecorder:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace
        self._schema = TomlSchemaReader().read(workspace.schema_path)
        self._journal = JsonlJournal(workspace)
        self._answers = PersonAnswerStore(workspace)
        self._how = HowLine()

    def answer(self, author: str, text: str) -> PersonAnswer:
        with self._journal.exclusive() as session:
            journal = session.snapshot()
            declaration = SizeStore(self._workspace).current()
            size: Size | None = None
            if self._schema.sized and declaration is not None:
                size = declaration.size
            mode = WorkspaceMode(self._workspace).read()
            pause = Progress(self._schema, size).pending_pause(
                journal,
                self._answers.read(),
                interactive=mode == run_mode.INTERACTIVE,
            )
            if pause is None:
                raise Refusal(
                    what="nothing awaits an answer: the last record is not a pause of the declared size, or it is answered",
                    why="an answer answers one pause of interactive mode; in auto mode, and after an answer, nothing is asked",
                    how=self._how.command(
                        "status", "--workspace", str(self._workspace.directory)
                    ),
                )
            recorded = PersonAnswer.for_pause(pause, author, text)
            self._answers.append(recorded)
        return recorded
