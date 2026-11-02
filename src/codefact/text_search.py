"""Language-independent UTF-8 lexical floor; its confidence is always noisy."""

from __future__ import annotations

import re

from codefact import scope
from codefact.model import (
    REFERENCE_SHAPES,
    STABLE_CORE_CAPABILITY_IDS,
    Answers,
    Passes,
    Provider,
    Reply,
    observation_count,
)


ATOM_DEFINITION = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:def|class|func|fn|function)\s+([A-Za-z_]\w*)",
    re.MULTILINE,
)


def cover(capability, request, snapshot):
    return (
        Answers("noisy", REFERENCE_SHAPES)
        if capability.id in STABLE_CORE_CAPABILITY_IDS
        else Passes()
    )


def _without_declarations(content: str, target: str) -> str:
    # Deleted, not blanked, so line numbers shift as legacy's do.
    return ATOM_DEFINITION.sub(
        lambda match: "" if match.group(1) == target else match.group(),
        content,
    )


def sites(snapshot, sources, target, calls):
    if not target:
        return []
    pattern = re.compile(
        rf"(?<!\w){re.escape(target)}\s*\("
        if calls
        else rf"(?<!\w){re.escape(target)}\b(?!\s*\()"
    )
    return [
        f"{snapshot.location(path)}:{content.count(chr(10), 0, match.start()) + 1}"
        for path, raw in sources
        if raw is not None
        for content in (_without_declarations(raw, target),)
        for match in pattern.finditer(content)
    ]


def answer(capability, request, snapshot):
    sources = tuple(
        (path, scope.text(snapshot, path)) for path in scope.files(snapshot)
    )
    faults = tuple(
        snapshot.location(path) for path, content in sources if content is None
    )
    symbol = scope.subject(request)
    target = symbol.rsplit(".", 1)[-1]
    if capability.id == "query.atoms-in-file":
        payload = {
            "atoms": sorted(
                {
                    atom
                    for _, content in sources
                    if content is not None
                    for atom in ATOM_DEFINITION.findall(content)
                }
            )
        }
    elif capability.id == "query.adr-section":
        payload = {
            "anchor": symbol,
            "files": [
                path.rsplit("/", 1)[-1]
                for path, content in sources
                if symbol and content and symbol in content
            ],
        }
    elif capability.id == "query.never-wired":
        calls = sites(snapshot, sources, target, True)
        payload = {"symbol": symbol, "never_wired": not calls, "call_sites": calls}
    else:
        payload = {
            "symbol": symbol,
            "sites": sites(
                snapshot, sources, target, capability.id == "query.callers-of"
            ),
        }
    return Reply(
        payload, observation_count(payload), len(faults), faults, scope.health(snapshot)
    )


PROVIDER = Provider("textsearch", cover, answer)
