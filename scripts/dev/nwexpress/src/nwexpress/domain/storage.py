"""Storage decisions over values: which mount holds a path, whether that mount is RAM-backed or forbidden by the
policy, and whether a volume has the minimum free space.

Values only. The mount table, the free space and the configuration documents are read by the infrastructure module
nwexpress.infrastructure.storage_settings and passed in here. The defaults below are the one declaration of the
policy's built-in values; every one of them is overridden by a key of the same name in the configuration.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum


GIB = 1 << 30
MIN_FREE_VARIABLE = "NWEXPRESS_MIN_FREE_GIB"
DEFAULT_MIN_FREE_GIB = 10
DEFAULT_FORBIDDEN_FILESYSTEMS = ("tmpfs", "ramfs")
DEFAULT_FORBIDDEN_SOURCES = ("/dev/zram",)


@dataclass(frozen=True)
class Mount:
    point: str
    fstype: str
    source: str
    options: str = ""

    @property
    def upperdir(self) -> str | None:
        """The upper directory of an overlay mount: where its writes land, read from the super options."""
        for option in self.options.split(","):
            key, _, value = option.partition("=")
            if key == "upperdir" and value:
                return _unescape(value)
        return None


class FileSystemVerdict(Enum):
    ALLOWED = "allowed"
    RAM_BACKED = "ram-backed"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class StoragePolicy:
    min_free_gib: int
    forbidden_filesystems: frozenset[str]
    forbidden_sources: tuple[str, ...]


def parse_mount_table(text: str) -> tuple[Mount, ...]:
    """The mounts of a mountinfo table; a line that does not have the kernel's layout is skipped, never guessed."""
    mounts: list[Mount] = []
    for line in text.splitlines():
        left, separator, right = line.partition(" - ")
        fields = left.split(" ")
        tail = right.split(" ")
        if not separator or len(fields) < 5 or len(tail) < 2:
            continue
        mounts.append(
            Mount(
                point=_unescape(fields[4]),
                fstype=tail[0],
                source=tail[1],
                options=tail[2] if len(tail) > 2 else "",
            )
        )
    return tuple(mounts)


def mount_of(path: str, mounts: tuple[Mount, ...]) -> Mount | None:
    """The mount that holds path: the one whose point is the longest path prefix of it, or None when none holds it."""
    holders = [mount for mount in mounts if _holds(mount.point, path)]
    if not holders:
        return None
    return max(holders, key=lambda mount: len(mount.point))


def judged_mount(path: str, mounts: tuple[Mount, ...]) -> Mount | None:
    """The mount whose file system decides the path: the holder itself, or for an overlay the mount of its upper directory.

    An overlay writes into its upper directory, so that directory's file system is the memory the policy protects; its
    lower directories are read-only and are not judged. An overlay with no upper directory, or whose upper directory no
    mount holds, has no judged mount, which the verdict reports as unverified.
    """
    holder = mount_of(path, mounts)
    if holder is None or holder.fstype != "overlay":
        return holder
    upper = holder.upperdir
    if upper is None:
        return None
    return mount_of(upper, mounts)


def filesystem_verdict(mount: Mount | None, policy: StoragePolicy) -> FileSystemVerdict:
    """RAM_BACKED when the mount's type or source is forbidden by the policy; UNVERIFIED when no mount is known."""
    if mount is None:
        return FileSystemVerdict.UNVERIFIED
    if mount.fstype in policy.forbidden_filesystems or any(
        mount.source.startswith(prefix) for prefix in policy.forbidden_sources
    ):
        return FileSystemVerdict.RAM_BACKED
    return FileSystemVerdict.ALLOWED


def below_minimum_free(free_bytes: int, policy: StoragePolicy) -> bool:
    """True when the free bytes are strictly below the policy's minimum, counted in whole GiB."""
    return free_bytes < policy.min_free_gib * GIB


def resolve_policy(
    environment_value: str | None,
    project: Mapping[str, object],
    global_: Mapping[str, object],
) -> StoragePolicy:
    """The policy one command uses: the environment variable for the threshold, then the repository tier, then the
    global tier, then the built-in defaults. A key a tier sets replaces the same key of the tier below it."""
    project_storage = _storage_of(project)
    global_storage = _storage_of(global_)
    return StoragePolicy(
        min_free_gib=_threshold(environment_value, project_storage, global_storage),
        forbidden_filesystems=frozenset(
            _strings(
                _first(
                    "forbidden_filesystems",
                    project_storage,
                    global_storage,
                    default=DEFAULT_FORBIDDEN_FILESYSTEMS,
                ),
                "forbidden_filesystems",
            )
        ),
        forbidden_sources=tuple(
            _strings(
                _first(
                    "forbidden_sources",
                    project_storage,
                    global_storage,
                    default=DEFAULT_FORBIDDEN_SOURCES,
                ),
                "forbidden_sources",
            )
        ),
    )


def _holds(point: str, path: str) -> bool:
    if point == "/":
        return path.startswith("/")
    return path == point or path.startswith(point.rstrip("/") + "/")


def _unescape(text: str) -> str:
    return (
        text.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def _storage_of(document: Mapping[str, object]) -> Mapping[str, object]:
    nwexpress = document.get("nwexpress")
    if not isinstance(nwexpress, Mapping):
        return {}
    storage = nwexpress.get("storage")
    return storage if isinstance(storage, Mapping) else {}


def _first(
    key: str,
    project: Mapping[str, object],
    global_: Mapping[str, object],
    *,
    default: object,
) -> object:
    if key in project:
        return project[key]
    if key in global_:
        return global_[key]
    return default


def _threshold(
    environment_value: str | None,
    project: Mapping[str, object],
    global_: Mapping[str, object],
) -> int:
    if environment_value is not None:
        try:
            value = int(environment_value)
        except ValueError:
            raise ValueError(
                f"{MIN_FREE_VARIABLE}={environment_value!r} is not a whole number of GiB"
            ) from None
        return _whole(value, MIN_FREE_VARIABLE)
    value = _first("min_free_gib", project, global_, default=DEFAULT_MIN_FREE_GIB)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"min_free_gib {value!r} is not a whole number of GiB")
    return _whole(value, "min_free_gib")


def _whole(value: int, name: str) -> int:
    if value < 0:
        raise ValueError(
            f"{name} {value} is negative; it must be a whole number of GiB"
        )
    return value


def _strings(value: object, name: str) -> list[str]:
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(f"{name} must be a list of strings")
    return list(value)
