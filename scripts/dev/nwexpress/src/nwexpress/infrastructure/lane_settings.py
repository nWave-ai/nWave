"""Reads lanes.trunk, the trunk the project names, from the repository's configuration and then the global one.

The same two files and the same order as the storage keys; the other keys of those files belong to other owners and are
left alone. A file that cannot be read is a refusal that names the file, through the shared tier reader.
"""

from __future__ import annotations

from pathlib import Path

from nwexpress.infrastructure.storage_settings import read_tier


CONFIG_RELATIVE = Path(".nwave", "config.json")


def configured_trunk(main: Path, home: Path) -> str | None:
    """The configured trunk of the main checkout, or None when no tier names one."""
    for document in (
        read_tier(main / CONFIG_RELATIVE),
        read_tier(home / ".nwave" / "config.json"),
    ):
        lanes = document.get("lanes")
        if isinstance(lanes, dict):
            trunk = lanes.get("trunk")
            if isinstance(trunk, str) and trunk:
                return trunk
    return None
