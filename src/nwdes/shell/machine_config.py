"""The machine-wide nWave config file, located in one place for every reader that consults it.

Pure: the caller passes the home directory it resolved (Path.home() at the edge), so this module
reads no environment and performs no I/O.
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


def machine_config_path(home: Path) -> Path:
    """The machine-wide config file under ``home``."""
    return home / ".nwave" / "config.json"
