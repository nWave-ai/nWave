"""The verdict on one citation from what was observed at its path. Pure: no reads, no clock."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from nwdes.citation.observation import Absent, FolderAt, NotText, OutsideRoot, TextFile
from nwdes.citation.verdict import CouldNotVerify, Resolved, Unresolved


if TYPE_CHECKING:
    from nwdes.citation.citation import Citation
    from nwdes.citation.observation import Observation
    from nwdes.citation.verdict import Verdict


def judge(citation: Citation, observation: Observation) -> Verdict:
    match observation:
        case OutsideRoot():
            return CouldNotVerify(
                citation, "the cited path lies outside the repository root"
            )
        case FolderAt():
            return CouldNotVerify(citation, "the cited path is a folder, not a file")
        case NotText():
            return CouldNotVerify(citation, "the cited file is not UTF-8 text")
        case Absent():
            return Unresolved(citation, "the cited file does not exist")
        case TextFile(content=content):
            return _by_name(citation, content)


def _by_name(citation: Citation, content: str) -> Verdict:
    if citation.test is None:
        return Unresolved(citation, "no test name is cited for the file")
    if _occurs_by_name(citation.test, content) is None:
        return Unresolved(
            citation,
            f"the name {citation.test} does not occur in the cited file as a whole word",
        )
    return Resolved(citation)


def _occurs_by_name(name: str, content: str) -> re.Match | None:
    """The name as literal text in the content. A boundary is required only on a side where the name
    starts or ends with a word character (letter, digit or underscore). On a side where the name's own
    edge is punctuation, a longer name is not told apart: "order!" is confirmed inside "order!now_extra".
    Text search cannot tell a name inside a comment or a string from a name in code; both count as present."""
    lead = r"(?<!\w)" if re.match(r"\w", name) else ""
    trail = r"(?!\w)" if re.search(r"\w\Z", name) else ""
    return re.search(lead + re.escape(name) + trail, content)
