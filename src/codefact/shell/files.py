"""Read filesystem effects once, then hand immutable bytes to the core."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

from codefact.index_layout import LAYOUT
from codefact.model import Snapshot, Source


def _source(path: Path) -> Source:
    try:
        stat = path.stat()
        return Source(path.read_bytes(), stat.st_mtime)
    except OSError:
        return Source(None, 0)


def _linked(directory: Path) -> bool:
    marker = directory / ".git"
    if not marker.is_file():
        return False
    try:
        value = marker.read_text().strip()
        metadata = Path(value.removeprefix("gitdir: "))
        if not metadata.is_absolute():
            metadata = directory / metadata
        return value.startswith("gitdir: ") and (metadata / "commondir").is_file()
    except (OSError, UnicodeError):
        return False


def read_tree(root: Path | str) -> Snapshot:
    display_root = str(Path(root))
    root = Path(root).absolute()
    if root.is_file():
        return _with_index(
            Snapshot(
                str(root),
                MappingProxyType({root.name: _source(root)}),
                True,
                display_root=display_root,
            ),
            root.parent,
        )
    entries = {}
    pruned = False
    for directory, children, names in os.walk(root):
        parent = Path(directory)
        for child in children[:]:
            if child == ".git" or _linked(parent / child):
                children.remove(child)
                pruned = True
        for name in names:
            path = parent / name
            if path.is_file():
                entries[path.relative_to(root).as_posix()] = _source(path)
    return _with_index(
        Snapshot(
            str(root),
            MappingProxyType(entries),
            pruned=pruned,
            display_root=display_root,
        ),
        root,
    )


def _with_index(snapshot: Snapshot, directory: Path) -> Snapshot:
    if LAYOUT is None:
        return snapshot
    paths = LAYOUT.paths

    # The initial tree listing already tells us whether its index files exist.
    # Ancestor probes use string paths: an unindexed query should not allocate
    # Path objects for every nonexistent index member up to the filesystem root.
    parent = str(directory)
    local = not snapshot.file_root
    while True:
        present = (
            all(name in snapshot.entries for name in paths[:2])
            if local
            else all(os.path.isfile(os.path.join(parent, name)) for name in paths[:2])
        )
        if present:
            entries = {
                name: snapshot.entries[name]
                if local and name in snapshot.entries
                else _source(Path(parent) / name)
                for name in paths
            }
            return replace(
                snapshot,
                index_root=parent,
                index_entries=MappingProxyType(entries),
            )
        ancestor = os.path.dirname(parent)  # noqa: PTH120
        if ancestor == parent:
            return snapshot
        parent = ancestor
        local = False
