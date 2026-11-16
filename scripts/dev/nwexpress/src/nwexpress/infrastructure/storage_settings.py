"""The effects of the storage decisions: the mount table of the operating system, the free space of a volume, and the
storage keys of the global and repository configuration files.

Only the storage keys are read here, as raw JSON; the other keys of those files belong to other owners and are left
alone. A file that cannot be read or parsed is a refusal that names the file, never an empty policy.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from nwexpress.domain.refusal import Refusal
from nwexpress.domain.storage import (
    MIN_FREE_VARIABLE,
    Mount,
    StoragePolicy,
    judged_mount,
    parse_mount_table,
    resolve_policy,
)


if TYPE_CHECKING:
    from collections.abc import Mapping


MOUNT_TABLE = Path("/proc/self/mountinfo")
CONFIG_RELATIVE = Path(".nwave", "config.json")


def read_storage_policy(
    root: Path | None, home: Path, environ: Mapping[str, str]
) -> StoragePolicy:
    """The policy for a command run in root: the environment, then the repository tier, then the global tier."""
    project = read_tier(root / CONFIG_RELATIVE) if root is not None else {}
    global_ = read_tier(home / ".nwave" / "config.json")
    try:
        return resolve_policy(environ.get(MIN_FREE_VARIABLE), project, global_)
    except ValueError as error:
        raise Refusal(
            what=f"the storage settings cannot be decided: {error}",
            why="the threshold and the forbidden types decide whether a command may start, so a value that is not usable cannot be applied",
            how=f"set {MIN_FREE_VARIABLE} to a whole number of GiB, or set nwexpress storage min_free_gib in the repository or global configuration to one, then run the command again",
        ) from None


def read_mount_table() -> str | None:
    """The kernel's mount table as text, or None where the operating system has none to read."""
    try:
        return MOUNT_TABLE.read_text(encoding="utf-8")
    except OSError:
        return None


def mount_holding(path: Path) -> Mount | None:
    """The mount whose file system decides path: the mount holding it, or for an overlay the mount of its upper directory.

    None when no table is readable, or when the mount that decides cannot be named; the verdict reports that as unverified.
    """
    text = read_mount_table()
    if text is None:
        return None
    return judged_mount(str(path.resolve()), parse_mount_table(text))


def free_bytes(path: Path) -> int:
    """The free bytes of the volume that holds path, or of the nearest existing folder above it."""
    return shutil.disk_usage(nearest_existing(path)).free


def nearest_existing(path: Path) -> Path:
    current = path.resolve()
    while not current.exists() and current != current.parent:
        current = current.parent
    return current


def read_tier(path: Path) -> dict[str, object]:
    """The JSON object of one configuration tier, or {} when the file does not exist; a file that cannot be read is a refusal."""
    if not path.is_file():
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise Refusal(
            what=f"the configuration file {path} cannot be read as JSON: {error}",
            why="its storage keys decide whether a command may start, so a file that cannot be read cannot be ignored",
            how=f"make {path} a readable JSON object, or remove it, then run the command again",
        ) from None
    if not isinstance(document, dict):
        raise Refusal(
            what=f"the configuration file {path} is not a JSON object",
            why="its storage keys decide whether a command may start, so a file of another shape cannot be read",
            how=f"make {path} a JSON object with an nwexpress storage section, or remove it, then run the command again",
        )
    return document
