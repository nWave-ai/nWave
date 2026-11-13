"""Where the tests declaration of a project is read from.

Effects only: a file the caller names, else the ``tests`` block of the project's
``.nwave/config.json`` and, when the project has none, of the account's. The tiers
and the project root across git worktrees are ``NWaveConfig``'s; this module adds no
second reader of those files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nwave_ai.platform.config import NWaveConfig
from nwave_ai.testrun.declaration import Declaration, Malformed, parse_declaration
from nwave_ai.testrun.refusal import Refusal


if TYPE_CHECKING:
    from pathlib import Path


_WHY = "the queue and the selector act only on a declaration they understand in full"
BUILT_IN = "the built-in defaults (no tests block is declared)"


@dataclass(frozen=True)
class Sourced:
    """A parsed declaration and the place it came from, for messages."""

    declaration: Declaration
    source: str


def _parsed(document: object | None, source: str) -> Sourced | Refusal:
    declaration = parse_declaration(document)
    if isinstance(declaration, Malformed):
        return Refusal(
            what=(
                f"the tests declaration in {source} is malformed: "
                f"{'; '.join(declaration.defects)}"
            ),
            why=_WHY,
            how=f"correct these fields in {source}",
        )
    return Sourced(declaration, source)


def load_declaration(root: Path, named: Path | None) -> Sourced | Refusal:
    """Read and parse the declaration that governs ``root``."""
    if named is not None:
        try:
            document = json.loads(named.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            return Refusal(
                what=f"the tests declaration {named} cannot be read: {error}",
                why=_WHY,
                how=(
                    f"make {named} a JSON object with the tests declaration, or "
                    "leave --declaration out to read .nwave/config.json"
                ),
            )
        return _parsed(document, str(named))
    block = NWaveConfig(cwd=root).tests_declaration()
    if block.unreadable:
        unreadable = ", ".join(str(path) for path in block.unreadable)
        return Refusal(
            what=f"the configuration cannot be read as a JSON object: {unreadable}",
            why="an unreadable file may hold a tests declaration; guessing its content "
            "would run or select tests the project never declared",
            how=f"repair the JSON of {unreadable}, or pass --declaration FILE",
        )
    return _parsed(block.value, str(block.source) if block.source else BUILT_IN)
