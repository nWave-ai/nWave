"""Reads the examine level one configuration file declares, or nothing.

A missing file, a file without an examine object and an examine object without a level declare
nothing. A file that cannot be read, is not a JSON object, or names a level outside the table is
refused: a silent default would change the examination the run states.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

from nwstep.domain import examine_level
from nwstep.domain.refusal import Refusal


def read_declared(path: Path) -> str | None:
    """The level name the file declares, or None when it declares none."""
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Refusal(
            what=f"{path} cannot be read as JSON: {error}",
            why="a configuration file that cannot be read would silently change the examine level",
            how=f"fix {path} so that it holds one JSON object, or remove it",
        ) from None
    if not isinstance(document, dict):
        raise Refusal(
            what=f"{path} is not a JSON object",
            why="the configuration is read as a JSON object with an examine.level key",
            how=f'make {path} a JSON object such as {{"examine": {{"level": "standard"}}}}',
        )
    examine = document.get("examine")
    if examine is None:
        return None
    if not isinstance(examine, dict):
        raise Refusal(
            what=f"`examine` in {path} is not an object",
            why="the examine level is declared inside an examine object",
            how=f'make `examine` in {path} an object such as {{"level": "standard"}}',
        )
    if "level" not in examine:
        return None
    level = examine["level"]
    if not isinstance(level, str) or level not in examine_level.NAMES:
        raise examine_level.refused(str(path), level)
    return level
