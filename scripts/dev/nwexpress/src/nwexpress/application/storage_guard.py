"""Admits the directory a command creates, before anything is written there.

A RAM-backed or forbidden mount, or a volume below the minimum free space, is a refusal that names the configured
alternative. A mount table the operating system does not give is a warning that says the type could not be verified;
it is never a silent pass.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwexpress.domain.refusal import Refusal
from nwexpress.domain.storage import (
    GIB,
    MIN_FREE_VARIABLE,
    FileSystemVerdict,
    StoragePolicy,
    below_minimum_free,
    filesystem_verdict,
)
from nwexpress.infrastructure.storage_settings import (
    free_bytes,
    mount_holding,
    nearest_existing,
)


if TYPE_CHECKING:
    from pathlib import Path


def admit_directory(
    target: Path, *, policy: StoragePolicy, command: str, configuration: Path
) -> tuple[str, ...]:
    """Raises the refusal when target may not be created here; returns the warnings the caller must print."""
    probe = nearest_existing(target)
    mount = mount_holding(probe)
    verdict = filesystem_verdict(mount, policy)
    if verdict is FileSystemVerdict.RAM_BACKED and mount is not None:
        raise Refusal(
            what=f"{command} cannot create {target}: it is on {mount.fstype} ({mount.source}), a file system the storage policy forbids",
            why="a RAM-backed folder takes memory from every process on the machine, and the machine has little of it",
            how=f"remove {mount.fstype} from forbidden_filesystems under nwexpress storage in {configuration} (or in the global configuration), or give a target on a disk file system such as ~/.cache/nwave, then run {command} again",
        )
    warnings: tuple[str, ...] = ()
    if verdict is FileSystemVerdict.UNVERIFIED:
        warnings = (
            f"WARNING: the file system of {target} could not be verified: no readable mount table holds it; the forbidden-type check did not run",
        )
    free = free_bytes(target)
    if below_minimum_free(free, policy):
        raise Refusal(
            what=f"only {free / GIB:.1f} GiB is free on {probe}; {command} needs {policy.min_free_gib} GiB",
            why="a full disk stops every other agent and test that shares this volume, so a delivery must not start on one that is nearly full",
            how=f"free space on that volume, or lower min_free_gib under nwexpress storage in {configuration} or {MIN_FREE_VARIABLE} for this command, then run {command} again",
        )
    return warnings
