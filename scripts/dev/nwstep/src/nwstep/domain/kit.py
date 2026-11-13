"""The kit of a run: the fingerprints of what it copies, the record that names them, and the comparison of two skill trees.

Pure: no path, clock or process. Files arrive as mappings from a relative name to its bytes; the record is a value.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nwstep.domain.refusal import Refusal
from nwstep.domain.skill_name import SkillName


if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


PART_NAMES = ("skills", "schema", "templates", "source")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def part_fingerprint(files: Mapping[str, bytes]) -> str:
    """The fingerprint of a set of files: each name with the digest of its bytes, in name order, so listing order does not matter."""
    lines = [
        f"{name}\t{hashlib.sha256(files[name]).hexdigest()}" for name in sorted(files)
    ]
    return _sha256("\n".join(lines))


def kit_fingerprint(parts: Mapping[str, str]) -> str:
    """The fingerprint of a kit: each part name with its own fingerprint, in name order."""
    lines = [f"{name}\t{parts[name]}" for name in sorted(parts)]
    return _sha256("\n".join(lines))


def unshipped_skills(
    names: Iterable[str], files: Mapping[str, bytes]
) -> tuple[str, ...]:
    """The named skills whose SKILL.md is not among the files, each once, in name order."""
    return tuple(
        sorted(
            {name for name in names if f"{name}/{SkillName.SKILL_FILE}" not in files}
        )
    )


@dataclass(frozen=True)
class TreeComparison:
    """Two skill trees compared by file name: present in both with other bytes, only in the checkout, only in the installed copy."""

    differs: tuple[str, ...]
    missing: tuple[str, ...]
    extra: tuple[str, ...]

    @property
    def same(self) -> bool:
        return not (self.differs or self.missing or self.extra)


def compare_trees(
    installed: Mapping[str, bytes], checkout: Mapping[str, bytes]
) -> TreeComparison:
    shared = installed.keys() & checkout.keys()
    return TreeComparison(
        differs=tuple(
            sorted(name for name in shared if installed[name] != checkout[name])
        ),
        missing=tuple(sorted(checkout.keys() - installed.keys())),
        extra=tuple(sorted(installed.keys() - checkout.keys())),
    )


@dataclass(frozen=True)
class KitRecord:
    """What a workspace's kit was made of: the overall fingerprint, one fingerprint per part, and the checkout commit or none."""

    fingerprint: str
    parts: Mapping[str, str]
    commit: str | None

    @classmethod
    def from_mapping(cls, data: Any) -> KitRecord:
        if not isinstance(data, dict):
            raise cls._refuse("the record is not a JSON object")
        fingerprint = data.get("fingerprint")
        parts = data.get("parts")
        commit = data.get("commit")
        if not _is_digest(fingerprint):
            raise cls._refuse("its 'fingerprint' is not a sha256 digest")
        if not isinstance(parts, dict) or set(parts) != set(PART_NAMES):
            raise cls._refuse(
                f"its 'parts' do not name exactly {', '.join(PART_NAMES)}"
            )
        if not all(_is_digest(parts[name]) for name in PART_NAMES):
            raise cls._refuse("one of its 'parts' is not a sha256 digest")
        if commit is not None and not isinstance(commit, str):
            raise cls._refuse("its 'commit' is neither a string nor null")
        return cls(fingerprint=fingerprint, parts=dict(parts), commit=commit)

    @staticmethod
    def _refuse(problem: str) -> Refusal:
        return Refusal(
            what=f"the kit record cannot be read: {problem}",
            why="the kit record names the skill copies a run reads and the version its scores belong to; a record that does not hold them cannot be trusted",
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "parts": {name: self.parts[name] for name in PART_NAMES},
            "commit": self.commit,
        }

    def describe(self) -> str:
        return f"kit: {self.fingerprint} commit: {self.commit or 'none'}"


@dataclass(frozen=True)
class UnknownKit:
    """A workspace with no kit record: it was created before the kit existed."""

    def describe(self) -> str:
        return "kit: unknown"


KitState = KitRecord | UnknownKit


def _is_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
