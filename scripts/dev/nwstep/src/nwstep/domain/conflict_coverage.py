"""Every request sentence has one conflict line; a malformed or unknown line is refused with the rest."""

from __future__ import annotations

from nwstep.domain.conflict_line import ConflictLine
from nwstep.domain.fault import Fault
from nwstep.domain.field import Field
from nwstep.domain.request_sentences import RequestSentences


class ConflictCoverage:
    def __init__(
        self, field: Field, sentences: RequestSentences, items: list[str]
    ) -> None:
        self._field = field
        self._sentences = sentences
        self._items = items

    def check(self) -> None:
        problems: list[str] = []
        rejected: list[str] = []
        covered: set[str] = set()
        for item in self._items:
            try:
                line = ConflictLine.parse(item)
            except ValueError as error:
                problems.append(f"'{item}': {error}")
                rejected.append(item)
                continue
            if self._sentences.find(line.identifier) is None:
                problems.append(
                    f"'{item}' does not open with a sentence id of the request"
                )
                rejected.append(item)
                continue
            covered.add(line.identifier)
        uncovered = [
            sentence
            for sentence in self._sentences.sentences
            if sentence.identifier not in covered
        ]
        if not problems and not uncovered:
            return
        parts: list[str] = []
        if problems:
            parts.append(f"the conflict lines are invalid: {'; '.join(problems)}")
        if uncovered:
            listing = "; ".join(f"{s.identifier} '{s.text}'" for s in uncovered)
            parts.append(f"request sentences lack a conflict line: {listing}")
        raise self._field.refuse(
            " | ".join(parts),
            rejected=tuple(rejected),
            missing=tuple(sentence.identifier for sentence in uncovered),
            fault=Fault.COVERAGE,
        )
