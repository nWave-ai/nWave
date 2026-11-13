"""Reads one consent tier file: the raw jev value it declares, or nothing.

A missing file and a file without a jev key declare nothing. A file that exists but cannot
be read, or whose content is not a JSON object, is refused: silently skipping it would
change the consent the executor sees.
"""

from __future__ import annotations

import json
from pathlib import Path

from nwstep.domain.refusal import Refusal


def read_declared(path: Path) -> tuple[object, ...]:
    """(value,) when the file declares jev, () otherwise."""
    if not path.is_file():
        return ()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Refusal(
            what=f"{path} cannot be read as JSON: {error}",
            why="a consent file that cannot be read would silently change the Jev consent the executor sees",
            how=f"fix {path} so that it holds one JSON object, or remove it",
        ) from None
    if not isinstance(document, dict):
        raise Refusal(
            what=f"{path} is not a JSON object",
            why="the consent file is read as a JSON object with a jev key",
            how=f'make {path} a JSON object such as {{"jev": "authorized"}}, or remove it',
        )
    return (document["jev"],) if "jev" in document else ()
