"""The three outcomes of a citation: confirmed, refuted by observation, or not verifiable by the tool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nwdes.citation.citation import Citation


@dataclass(frozen=True)
class Resolved:
    """The cited name occurs as a whole word in the cited text file."""

    citation: Citation


@dataclass(frozen=True)
class Unresolved:
    """The citation is checkable and false: the file is absent or the name is not in it."""

    citation: Citation
    reason: str


@dataclass(frozen=True)
class CouldNotVerify:
    """The tool cannot read the cited location as text, so it cannot confirm or refute the citation."""

    citation: Citation
    reason: str


Verdict = Resolved | Unresolved | CouldNotVerify
