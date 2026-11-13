"""The kit a run will carry, decided from values before any workspace file is written: the record and the skill files to copy, or the refusal that stops init."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from nwstep.domain.kit import (
    KitRecord,
    kit_fingerprint,
    part_fingerprint,
    unshipped_skills,
)
from nwstep.domain.refusal import Refusal


if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


SCHEMA_FILE_NAME = "schema.toml"


def is_source_file(name: str) -> bool:
    return name.endswith(".py") and "__pycache__" not in name.split("/")


@dataclass(frozen=True)
class KitInputs:
    """The files and names one kit is made from, read by the caller before the snapshot is taken."""

    skill_files: Mapping[str, bytes]
    schema_bytes: bytes
    schema_skill_names: Iterable[str]
    template_files: Mapping[str, bytes]
    source_files: Mapping[str, bytes]
    commit: str | None


@dataclass(frozen=True)
class KitSnapshot:
    record: KitRecord
    skill_files: Mapping[str, bytes]

    @classmethod
    def take(cls, inputs: KitInputs) -> KitSnapshot:
        missing = unshipped_skills(inputs.schema_skill_names, inputs.skill_files)
        if missing:
            raise Refusal(
                what=f"the schema names skill(s) the skills source does not hold: {', '.join(missing)}",
                why="a run would point at a SKILL.md that the kit does not contain, so the skill it reads would be silently absent",
            )
        parts = {
            "skills": part_fingerprint(inputs.skill_files),
            "schema": part_fingerprint({SCHEMA_FILE_NAME: inputs.schema_bytes}),
            "templates": part_fingerprint(inputs.template_files),
            "source": part_fingerprint(inputs.source_files),
        }
        record = KitRecord(
            fingerprint=kit_fingerprint(parts), parts=parts, commit=inputs.commit
        )
        return cls(record=record, skill_files=dict(inputs.skill_files))
