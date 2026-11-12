"""Shared construction outcomes; refusals retain every independent defect."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from itertools import groupby
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class Defect:
    what: str
    why: str
    how: str
    origin: str = field(default="", kw_only=True)

    @property
    def identity(self) -> tuple[str, str]:
        return self.what, self.origin


@dataclass(frozen=True)
class Refusal:
    first: Defect
    rest: tuple[Defect, ...] = ()

    def __post_init__(self):
        if (
            not isinstance(self.first, Defect)
            or not isinstance(self.rest, tuple)
            or any(not isinstance(d, Defect) for d in self.rest)
        ):
            raise TypeError(
                "Refusal requires a first defect and an immutable tuple of defects"
            )
        identities = tuple(defect.identity for defect in self.defects)
        if len(set(identities)) != len(identities):
            raise ValueError(
                "Refusal requires one defect per identity; use checked to combine reasons"
            )

    @property
    def defects(self) -> tuple[Defect, ...]:
        return (self.first, *self.rest)


@dataclass(frozen=True)
class Built(Generic[T]):
    value: T


@dataclass(frozen=True)
class Refused:
    refusal: Refusal

    @property
    def defects(self) -> tuple[Defect, ...]:
        return self.refusal.defects


def refuse(what: str, why: str, how: str) -> Refused:
    return Refused(Refusal(Defect(what, why, how)))


def _merge_identity(defects: tuple[Defect, ...]) -> Defect:
    first = defects[0]
    why = " ".join(dict.fromkeys(defect.why for defect in defects))
    how = " ".join(dict.fromkeys(defect.how for defect in defects))
    return (
        first
        if (why, how) == (first.why, first.how)
        else Defect(first.what, why, how, origin=first.origin)
    )


def _combine_defects(defects: Iterable[Defect]) -> tuple[Defect, ...]:
    problems = tuple(defects)
    identities = tuple(dict.fromkeys(defect.identity for defect in problems))
    if len(identities) == len(problems):
        return problems
    grouped = {
        identity: _merge_identity(tuple(group))
        for identity, group in groupby(
            sorted(problems, key=lambda defect: defect.identity),
            key=lambda defect: defect.identity,
        )
    }
    return tuple(grouped[identity] for identity in identities)


def checked(value: T, defects: Iterable[Defect]) -> Built[T] | Refused:
    problems = _combine_defects(defects)
    return Refused(Refusal(problems[0], problems[1:])) if problems else Built(value)


def collect(
    checks: Iterable[Callable[[], Built[T] | Refused]],
) -> Built[tuple[T, ...]] | Refused:
    results = tuple(check() for check in checks)
    return checked(
        tuple(r.value for r in results if isinstance(r, Built)),
        (d for r in results if isinstance(r, Refused) for d in r.defects),
    )


LINE_BOUNDARIES = "\x00\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"


def local_path(path: str) -> bool:
    return (
        isinstance(path, str)
        and bool(path)
        and path == path.strip()
        and not path.startswith(("/", "\\"))
        and "\\" not in path
        and not any(character in path for character in LINE_BOUNDARIES)
        and all(segment not in ("", ".", "..") for segment in path.split("/"))
    )


class DuplicateKey(ValueError):
    pass


def strict_object(pairs):
    names = tuple(name for name, _ in pairs)
    if len(set(names)) != len(names):
        raise DuplicateKey("Duplicate JSON key")
    return dict(pairs)


@dataclass(frozen=True)
class ExamineLevel:
    """One examine level: its name and the repair rounds it grants, and nothing else.

    A level limits how many examinations a delivery admits, the same way review.max_rounds
    limits review rounds. An examination has no clock.
    """

    name: str
    repair_rounds: int

    @property
    def examinations(self) -> int:
        return 1 + self.repair_rounds


# The examine levels a person chooses. One table in nwdes, read by the config
# parser, the bundle and the shell; nwave_ai/platform/rigor_core.py keeps the
# rigor command's copy, pinned equal by a parity test.
EXAMINE_LEVELS = (
    ExamineLevel("quick", 0),
    ExamineLevel("standard", 1),
    ExamineLevel("extended", 2),
)
DEFAULT_EXAMINE_LEVEL = "standard"
EXAMINE_LEVEL_NAMES = tuple(level.name for level in EXAMINE_LEVELS)


def examine_level_named(name: str) -> ExamineLevel:
    """The level a validated name stands for; any other name is a programming error."""
    for level in EXAMINE_LEVELS:
        if level.name == name:
            return level
    raise ValueError(f"not an examine level: {name!r}")


def describe_examine_level(name: str) -> str:
    """The examinations and repair rounds a level grants: the text every surface prints."""
    level = examine_level_named(name)
    examinations = f"{level.examinations} examination" + (
        "" if level.examinations == 1 else "s"
    )
    if level.repair_rounds == 0:
        repairs = "no repair round"
    else:
        repairs = f"{level.repair_rounds} repair round" + (
            "" if level.repair_rounds == 1 else "s"
        )
    return f"{examinations}, {repairs}"


def examine_level_line(name: str, source: str) -> str:
    """The examine level line: the name, where its value comes from, what it stands for."""
    return f"examine level: {name} ({source}) - {describe_examine_level(name)}"


def resolved_examine_level(
    repository: str | None, global_: str | None
) -> tuple[str, str]:
    """The level in effect with its source: project over global over the built-in default."""
    if repository is not None:
        return repository, "project"
    if global_ is not None:
        return global_, "global"
    return DEFAULT_EXAMINE_LEVEL, "built-in default"
