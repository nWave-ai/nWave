"""The identity of a candidate: what a reviewer's packet names and what a verdict holds for.

An identity is the commit when the project's version control has one for the whole tree, otherwise a digest of
the tree state. Two identities are the same candidate exactly when their texts are equal. Only `parse`,
`commit` and `tree_digest` build one, so a held identity is always well formed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable


class Kind(Enum):
    COMMIT = "commit"
    TREE = "tree"


_HASH = re.compile(r"[0-9a-f]{40,64}")
SHAPE = "commit:HASH or tree:HASH, as the packet prints it"


@dataclass(frozen=True)
class Identity:
    kind: Kind
    value: str

    @property
    def text(self) -> str:
        return f"{self.kind.value}:{self.value}"


@dataclass(frozen=True)
class Observed:
    """A candidate that could be read: its identity, and every weaker answer the reader had to fall back to."""

    identity: Identity
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Unreadable:
    """A candidate that could not be read at all, with the reason."""

    reason: str


def parse(text: str) -> Identity | None:
    """The identity a text names, or None when the text is not one."""
    kind_text, separator, value = text.strip().partition(":")
    kinds = {kind.value: kind for kind in Kind}
    if not separator or kind_text not in kinds or not _HASH.fullmatch(value):
        return None
    return Identity(kinds[kind_text], value)


def commit(revision: str) -> Identity | None:
    """The identity of a committed tree, or None when the text is not a full commit hash."""
    return parse(f"{Kind.COMMIT.value}:{revision.strip()}")


def tree_digest(files: Iterable[tuple[str, bytes | None]]) -> Identity:
    """The identity of a tree state: a digest over every path and its content, in path order.

    A path whose content is None is a file the listing names but the tree no longer holds; it counts, so a deleted
    file is a change. Lengths are part of the digest, so no two different trees share one byte stream.
    """
    digest = hashlib.sha256()
    for path, content in sorted(files, key=lambda entry: entry[0]):
        name = path.encode("utf-8", errors="surrogateescape")
        digest.update(f"{len(name)}:".encode())
        digest.update(name)
        if content is None:
            digest.update(b"absent;")
            continue
        digest.update(f"{len(content)}:".encode())
        digest.update(content)
    return Identity(Kind.TREE, digest.hexdigest())
