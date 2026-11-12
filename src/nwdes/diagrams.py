"""Mermaid diagrams on the readable page: the author's description and the node limit.

A diagram reaches the readable page only when its block declares exactly one non-empty
description, as a `%% alt:` line, and names at most NODE_LIMIT distinct nodes of a supported
type. The node count is a tokenizer over the common syntax of each supported type, not a
Mermaid parser: exotic syntax can miscount, and the brief states that as a limit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from nwdes.contracts import Built, Defect, Refused, checked


# Provisional limit decided by Ale on 11 Nov 2026. Change it here and nowhere else.
NODE_LIMIT = 25

_DESCRIPTION_LINE = re.compile(r"^[ \t]*%%[ \t]*alt:(.*)$", re.MULTILINE)
_FLOWCHART = frozenset({"flowchart", "graph"})
_C4 = frozenset({"C4Context", "C4Container", "C4Component"})
_SEQUENCE = frozenset({"sequenceDiagram"})
_FLOW_KEYWORDS = (
    "subgraph",
    "classDef",
    "class ",
    "style ",
    "linkStyle",
    "click ",
    "direction ",
    "accTitle",
    "accDescr",
)
_QUOTED = re.compile(r'"[^"]*"')
_BRACKETED = re.compile(r"\[[^\[\]]*\]|\([^()]*\)|\{[^{}]*\}|\|[^|]*\|")
_EDGE_TEXT = re.compile(r"--\s+[^-\n]+?\s+(?:-{2,}|={2,})>?")
_EDGE = re.compile(r"<?(?:-{2,}|={2,}|-\.+-?)(?:[ox](?![A-Za-z0-9_]))?>?")
_IDENTIFIER = re.compile(r"[A-Za-z0-9_]+")
_C4_ELEMENT = re.compile(
    r"\s*((?:Person|System|Container|Component)\w*)\(\s*([A-Za-z0-9_]+)\s*,"
)
_PARTICIPANT = re.compile(r"\s*(?:participant|actor)\s+([A-Za-z0-9_]+)")
_MESSAGE = re.compile(
    r"\s*([A-Za-z0-9_]+)\s*--?(?:>>?|[x)])[+-]?\s*([A-Za-z0-9_]+)\s*:"
)


@dataclass(frozen=True)
class Description:
    """The author's one sentence about a diagram; never empty."""

    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError(
                "a diagram description is never empty: build it from the author's %% alt: line"
            )


@dataclass(frozen=True)
class Diagram:
    """A diagram admitted to the readable page: its description and its Mermaid source."""

    description: Description
    source: str


def describe(source: str, ordinal: int) -> Built[Diagram] | Refused:
    """Admit one Mermaid block, or refuse it with every rule it breaks; `ordinal` numbers it."""
    lines = _DESCRIPTION_LINE.findall(source)
    nodes = count_nodes(source)
    defects = list(_description_defects(lines, ordinal))
    if nodes is None:
        defects.append(_unmeasured_defect(source, ordinal))
    elif nodes > NODE_LIMIT:
        defects.append(_limit_defect(nodes, ordinal))
    if defects:
        return checked(None, defects)
    return Built(Diagram(Description(lines[0].strip()), source))


def count_nodes(source: str) -> int | None:
    """The number of distinct nodes of a supported diagram; None for an unmeasured type."""
    kind, body = _header_and_body(source)
    if kind in _FLOWCHART:
        return len(_flowchart_nodes(body))
    if kind in _C4:
        return len(_c4_nodes(body))
    if kind in _SEQUENCE:
        return len(_sequence_nodes(body))
    return None


def _header_and_body(source: str) -> tuple[str, list[str]]:
    lines = [
        line.strip()
        for line in source.split("\n")
        if line.strip() and not line.strip().startswith("%%")
    ]
    if not lines:
        return "", []
    return lines[0].split()[0], lines[1:]


def _flowchart_nodes(lines: list[str]) -> set[str]:
    names: set[str] = set()
    for line in lines:
        if line == "end" or line.startswith(_FLOW_KEYWORDS):
            continue
        names.update(_IDENTIFIER.findall(_without_edges_and_labels(line)))
    return names


def _without_edges_and_labels(line: str) -> str:
    text = _QUOTED.sub(" ", line)
    while (stripped := _BRACKETED.sub(" ", text)) != text:
        text = stripped
    return _EDGE.sub(" ", _EDGE_TEXT.sub(" ", text))


def _c4_nodes(lines: list[str]) -> set[str]:
    return {
        match[2]
        for line in lines
        if (match := _C4_ELEMENT.match(line)) and "Boundary" not in match[1]
    }


def _sequence_nodes(lines: list[str]) -> set[str]:
    names: set[str] = set()
    for line in lines:
        if participant := _PARTICIPANT.match(line):
            names.add(participant[1])
        if message := _MESSAGE.match(line):
            names.update((message[1], message[2]))
    return names


def _description_defects(lines: list[str], ordinal: int) -> tuple[Defect, ...]:
    how = (
        "Keep exactly one line `%% alt: <one sentence saying what the diagram shows>` "
        "inside its mermaid block, then rerun the same document command."
    )
    if not lines:
        return (
            Defect(
                f"Mermaid diagram {ordinal} has no description",
                "The readable page shows a description as text in place of the diagram; "
                "without one a reader gets only the code.",
                how,
            ),
        )
    if len(lines) > 1:
        return (
            Defect(
                f"Mermaid diagram {ordinal} declares {len(lines)} descriptions",
                "A diagram has one description; a second one would be ambiguous.",
                how,
            ),
        )
    if not lines[0].strip():
        return (
            Defect(
                f"Mermaid diagram {ordinal} has an empty description",
                "An empty description would show an empty paragraph in place of the diagram.",
                how,
            ),
        )
    return ()


def _unmeasured_defect(source: str, ordinal: int) -> Defect:
    kind = _header_and_body(source)[0] or "empty"
    return Defect(
        f"Mermaid diagram {ordinal} is of type {kind}, whose node count is not measured",
        "The 25-node limit cannot be checked for this diagram type.",
        "Express it as a flowchart, a C4Context, C4Container or C4Component diagram, or a "
        f"sequenceDiagram of at most {NODE_LIMIT} distinct nodes, then rerun the same "
        "document command.",
    )


def _limit_defect(nodes: int, ordinal: int) -> Defect:
    return Defect(
        f"Mermaid diagram {ordinal} has {nodes} distinct nodes, above the limit of {NODE_LIMIT}",
        f"A readable diagram must stay small enough to follow as text; the limit is "
        f"{NODE_LIMIT} distinct nodes.",
        f"Split the diagram into diagrams of at most {NODE_LIMIT} distinct nodes, each with "
        "its own `%% alt:` line, then rerun the same document command.",
    )
