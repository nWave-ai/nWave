"""The examine level a dynamic run fixes: its name, where the name came from, and what it stands for.

The level is a count of examinations a delivery admits, one per repair round plus the first. The
table is a copy of the one nwdes reads (src/nwdes/contracts.py EXAMINE_LEVELS); nwstep does not
import nwdes, and tests/test_examine_level_table.py pins the two copies equal. There is no clock.
The level resolves project over global over the built-in default, like the Jev consent it mirrors.
"""

from __future__ import annotations

from dataclasses import dataclass

from nwstep.domain.refusal import Refusal


DEFAULT_NAME = "standard"
PROJECT = "project"
GLOBAL = "global"
BUILT_IN = "built-in default"


@dataclass(frozen=True)
class Level:
    name: str
    repair_rounds: int

    @property
    def examinations(self) -> int:
        return 1 + self.repair_rounds


LEVELS = (
    Level("quick", 0),
    Level("standard", 1),
    Level("extended", 2),
)
NAMES = tuple(level.name for level in LEVELS)


@dataclass(frozen=True)
class Resolved:
    name: str
    source: str

    def line(self) -> str:
        return f"examine level: {self.name} ({self.source}) - {describe(self.name)}"

    def section(self) -> str:
        return (
            "\n## EXAMINE LEVEL\n"
            + self.line()
            + "\nThe examiner runs under this level after the handoff; the level is fixed in the "
            "run workspace (examine-level.json) and does not change during the run.\n"
        )


def describe(name: str) -> str:
    level = _named(name)
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


def _named(name: str) -> Level:
    for level in LEVELS:
        if level.name == name:
            return level
    raise ValueError(f"not an examine level: {name!r}")


def resolve(repository: str | None, global_: str | None) -> Resolved:
    """The level in effect with its source: project over global over the built-in default."""
    if repository is not None:
        return Resolved(repository, PROJECT)
    if global_ is not None:
        return Resolved(global_, GLOBAL)
    return Resolved(DEFAULT_NAME, BUILT_IN)


def refused(path: str, value: object) -> Refusal:
    return Refusal(
        what=f"`examine.level` in {path} vale {value!r}",
        why=f"ammessi solo {', '.join(NAMES)}",
        how="run `nwave-ai rigor --examine-level standard` or correct the file",
    )
