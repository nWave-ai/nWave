"""Writes a JSON document so that a reader sees the old file or the new one, never a part of the new one.

The document is written by the shared atomic text write, so a crash leaves the target as it was.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nwexpress.infrastructure.atomic_text import write_text


def read_json(path: Path) -> Any:
    """The parsed document, or None when the file does not exist."""
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, document: Any) -> None:
    write_text(path, json.dumps(document, indent=2, sort_keys=True) + "\n")
