"""Every promise a request sentence maps to has at least one scenario; the refusal names each one without."""

from __future__ import annotations

from nwstep.domain.fault import Fault
from nwstep.domain.field import Field
from nwstep.domain.prefixed_item import PrefixedItem
from nwstep.domain.scenario import Scenario
from nwstep.domain.sentence_coverage import SentenceCoverage


class ScenarioCoverage:
    def __init__(
        self, field: Field, scenarios: list[str], sentence_map: list[str]
    ) -> None:
        self._field = field
        self._scenarios = scenarios
        self._sentence_map = sentence_map

    def check(self) -> None:
        covered = {Scenario.parse(text).promise for text in self._scenarios}
        gaps: list[tuple[str, str]] = []
        for item in self._sentence_map:
            sentence = PrefixedItem(item).identifier
            body = item.partition("=>")[2].strip()
            if sentence is None or body.startswith(SentenceCoverage.NOT_TESTABLE):
                continue
            for promise in (name.strip() for name in body.split(",")):
                if promise not in covered and (sentence, promise) not in gaps:
                    gaps.append((sentence, promise))
        if not gaps:
            return
        listing = "; ".join(
            f"{promise} (from {sentence})" for sentence, promise in gaps
        )
        raise self._field.refuse(
            f"promises mapped from request sentences have no scenario: {listing}",
            missing=tuple(dict.fromkeys(promise for _, promise in gaps)),
            fault=Fault.COVERAGE,
        )
