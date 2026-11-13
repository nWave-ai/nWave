"""Binds the examine level of a run workspace: the first prompt records it, later prompts keep it.

The level a run states is fixed once. A later prompt whose configuration resolves another level
is refused, as a later prompt with another run mode is refused; a prompt that is refused writes
nothing. `bound_to` only reads, so it is safe before the mode is bound; `record` writes, and is
called after every other refusal has been ruled out.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

from nwstep.domain import examine_level
from nwstep.domain.refusal import Refusal


FILE_NAME = "examine-level.json"


class ExamineLevelBinding:
    def __init__(self, directory: Path) -> None:
        self._path = directory / FILE_NAME

    def recorded(self) -> examine_level.Resolved | None:
        """The level this workspace was bound to, or None when no prompt has bound one yet."""
        if not self._path.is_file():
            return None
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise Refusal(
                what=f"{self._path} cannot be read as JSON: {error}",
                why="the examine level of the run is read from this file; an unreadable file would let a prompt state another level",
                how=f"restore {self._path} or start a new run in a new workspace with nwstep init",
            ) from None
        fields = document if isinstance(document, dict) else {}
        name = fields.get("level")
        source = fields.get("source")
        if name not in examine_level.NAMES or not isinstance(source, str):
            raise Refusal(
                what=f"{self._path} does not hold a bound examine level",
                why="the examine level of the run is read from this file, as a name and a source",
                how=f"restore {self._path} or start a new run in a new workspace with nwstep init",
            )
        return examine_level.Resolved(name, source)

    def bound_to(self, resolved: examine_level.Resolved) -> examine_level.Resolved:
        """The level the run states: the recorded one when bound, else the one resolved now. Writes nothing."""
        recorded = self.recorded()
        if recorded is None:
            return resolved
        if recorded.name != resolved.name:
            raise Refusal(
                what=(
                    f"this run is bound to examine level {recorded.name} ({recorded.source}), "
                    f"and the configuration now resolves {resolved.name} ({resolved.source})"
                ),
                why="the examine level is fixed once per run; a changed configuration would make one run state two levels",
                how=(
                    f"put back the configuration that resolves {recorded.name}, "
                    "or start a new run in a new workspace with nwstep init"
                ),
            )
        return recorded

    def record(self, bound: examine_level.Resolved) -> None:
        """Writes the bound level once; an already bound workspace keeps its file as it is."""
        if self.recorded() is not None:
            return
        temporary = self._path.with_name(f".{FILE_NAME}.tmp")
        payload = json.dumps({"level": bound.name, "source": bound.source}) + "\n"
        try:
            temporary.write_text(payload, encoding="utf-8")
            temporary.replace(self._path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
