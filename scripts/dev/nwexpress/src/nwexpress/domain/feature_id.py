"""The feature id: the name of the feature folder every feature document of a run is written into.

The rule is nwdes's scope-id rule (src/nwdes/handoff.py _SCOPE_ID), loaded when a feature id is checked rather than
copied. A value that does not match is refused at construction, so no folder name is built from an unchecked text.
"""

from __future__ import annotations

from dataclasses import dataclass

from nwexpress.domain.nwdes_source import nwdes_module
from nwexpress.domain.refusal import Refusal


@dataclass(frozen=True)
class FeatureId:
    text: str

    @classmethod
    def of(cls, text: object) -> FeatureId:
        scope_id = nwdes_module("nwdes.handoff")._SCOPE_ID
        if not isinstance(text, str) or scope_id.fullmatch(text) is None:
            raise Refusal(
                what=f"the feature id {text!r} breaks the feature id rule",
                why="the id names the feature folder under the feature directory, so it may hold only lower-case letters, digits and hyphens, and must start with a letter or digit",
            )
        return cls(text)

    def __str__(self) -> str:
        return self.text
