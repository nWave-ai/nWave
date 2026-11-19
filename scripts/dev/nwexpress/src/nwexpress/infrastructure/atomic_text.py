"""Writes a text file so that a reader sees the old file or the new one, never a part of the new one.

The text is written to a temporary file beside the target and then renamed over it. A crash before the rename
leaves the target as it was and a temporary file that the next write replaces.
"""

from __future__ import annotations

from pathlib import Path


def write_text(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
