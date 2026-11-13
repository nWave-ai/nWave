"""Writes a JSON document so that a reader sees the old file or the new one, never a part of the new one.

The document is written to a temporary file beside the target and then renamed over it. A crash before the rename
leaves the target as it was and a temporary file that the next write replaces.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    """The parsed document, or None when the file does not exist."""
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, document: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
