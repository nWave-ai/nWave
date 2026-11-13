"""Every request sentence is mapped to promises that exist, or declared not testable with a reason."""

from __future__ import annotations

from nwstep.domain.fault import Fault
from nwstep.domain.field import Field
from nwstep.domain.prefixed_item import PrefixedItem
from nwstep.domain.request_sentences import RequestSentences


class SentenceCoverage:
    PROMISES = "promises"
    NOT_TESTABLE = "not-testable:"
    MIN_REASON = 15

    def __init__(
        self,
        field: Field,
        sentences: RequestSentences,
        promise_ids: tuple[str, ...],
    ) -> None:
        self._field = field
        self._sentences = sentences
        self._promise_ids = promise_ids

    def check(self, items: list[str]) -> None:
        problems: list[str] = []
        rejected: list[str] = []
        covered: set[str] = set()
        for item in items:
            identifier = PrefixedItem(item).identifier
            head, separator, body = item.partition("=>")
            if (
                identifier is None
                or head.strip() != identifier
                or self._sentences.find(identifier) is None
            ):
                problems.append(
                    f"'{item}' does not open with a sentence id of the request"
                )
                rejected.append(item)
                continue
            problem = (
                self._problem(body)
                if separator
                else "write 'S1 => P1,P2' or 'S1 => not-testable: reason'"
            )
            if problem is not None:
                problems.append(f"{identifier}: {problem}")
                rejected.append(item)
                continue
            covered.add(identifier)
        uncovered = [
            sentence
            for sentence in self._sentences.sentences
            if sentence.identifier not in covered
        ]
        if not problems and not uncovered:
            return
        parts: list[str] = []
        if problems:
            parts.append(f"the sentence map is invalid: {'; '.join(problems)}")
        if uncovered:
            listing = "; ".join(f"{s.identifier} '{s.text}'" for s in uncovered)
            parts.append(f"request sentences lack a mapping: {listing}")
        raise self._field.refuse(
            " | ".join(parts),
            rejected=tuple(rejected),
            missing=tuple(sentence.identifier for sentence in uncovered),
            fault=Fault.COVERAGE,
        )

    def _problem(self, body: str) -> str | None:
        text = body.strip()
        if text.startswith(self.NOT_TESTABLE):
            reason = text[len(self.NOT_TESTABLE) :].strip()
            if len(reason) < self.MIN_REASON:
                return (
                    f"a not-testable reason needs at least {self.MIN_REASON} characters"
                )
            return None
        names = [name.strip() for name in text.split(",")]
        if not all(names):
            return "promise ids are comma separated and none may be empty"
        unknown = [name for name in names if name not in self._promise_ids]
        if unknown:
            return f"unknown promise id(s) {', '.join(unknown)}"
        return None
