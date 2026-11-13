"""A promise whose sentence has an open CONFLICT is not recorded until a decision for that sentence is given."""

from __future__ import annotations

from nwstep.domain.conflict_line import ConflictLine
from nwstep.domain.fault import Fault
from nwstep.domain.field import Field
from nwstep.domain.prefixed_item import PrefixedItem
from nwstep.domain.sentence_coverage import SentenceCoverage


class ConflictDecisions:
    MIN_CHARS = ConflictLine.MIN_CHARS

    def __init__(
        self,
        field: Field,
        conflict_lines: list[str],
        sentence_map: list[str],
        decisions: list[str],
    ) -> None:
        self._field = field
        self._conflict_lines = conflict_lines
        self._sentence_map = sentence_map
        self._decisions = decisions

    def check(self) -> None:
        open_ids = self._open_ids()
        decided = self._decided_ids()
        missing = [identifier for identifier in open_ids if identifier not in decided]
        if not missing:
            return
        raise self._field.refuse(
            f"the oracle would record promises whose sentence has an open CONFLICT: {', '.join(missing)}; "
            f"give each a decisions item that opens with its sentence id and is at least {self.MIN_CHARS} characters",
            missing=tuple(missing),
            fault=Fault.COVERAGE,
        )

    def _open_ids(self) -> list[str]:
        promises = {
            identifier: item.partition("=>")[2].strip()
            for item in self._sentence_map
            if (identifier := PrefixedItem(item).identifier) is not None
        }
        open_ids: list[str] = []
        for text in self._conflict_lines:
            line = ConflictLine.parse(text)
            if line.is_conflict and self._names_promise(promises.get(line.identifier)):
                open_ids.append(line.identifier)
        return open_ids

    @staticmethod
    def _names_promise(body: str | None) -> bool:
        return bool(body) and not body.startswith(SentenceCoverage.NOT_TESTABLE)

    def _decided_ids(self) -> set[str]:
        decided: set[str] = set()
        for item in self._decisions:
            identifier = PrefixedItem(item).identifier
            if identifier is not None and len(item.strip()) >= self.MIN_CHARS:
                decided.add(identifier)
        return decided
