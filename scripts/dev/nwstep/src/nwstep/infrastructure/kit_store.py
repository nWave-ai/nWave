"""Reads and writes a workspace's kit: the skill copy under kit/skills and the record kit.json that names it.

The record is written after the copy is complete, and each file goes in through a temporary name and a rename, so a
record never names a copy that is only partly in place.
"""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

from nwstep.domain.kit import KitRecord, KitState, UnknownKit
from nwstep.domain.refusal import Refusal
from nwstep.infrastructure.skills_root import SkillsRoot


if TYPE_CHECKING:
    from pathlib import Path

    from nwstep.application.kit_snapshot import KitSnapshot
    from nwstep.infrastructure.workspace import Workspace


class KitStore:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    def state(self) -> KitState:
        """The recorded kit, or UnknownKit for a workspace created before the kit existed; a record that cannot be read is a refusal."""
        path = self._workspace.kit_record_path
        if not path.is_file():
            return UnknownKit()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as error:
            raise Refusal(
                what=f"the kit record {path} is not readable JSON: {error}",
                why="the skill paths and the fingerprint of this run come from that record; without it they cannot be trusted",
            ) from None
        return KitRecord.from_mapping(data)

    def skills_root(self) -> Path:
        """The folder a run reads its skills from: the kit copy when a record exists, else the legacy resolution."""
        if isinstance(self.state(), UnknownKit):
            return SkillsRoot.DIRECTORY
        if not self._workspace.kit_skills_directory.is_dir():
            raise Refusal(
                what=f"the kit copy {self._workspace.kit_skills_directory} is missing",
                why="the record names a copy of the skills that is no longer in the workspace, so the paths would point at nothing",
            )
        return self._workspace.kit_skills_directory

    def write(self, snapshot: KitSnapshot) -> None:
        partial = self._workspace.directory / "kit.partial"
        if partial.exists():
            shutil.rmtree(partial)
        (partial / "skills").mkdir(parents=True)
        for name, data in snapshot.skill_files.items():
            target = partial / "skills" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        partial.replace(self._workspace.kit_directory)
        record_partial = self._workspace.directory / "kit.json.partial"
        record_partial.write_text(
            json.dumps(snapshot.record.to_mapping(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        record_partial.replace(self._workspace.kit_record_path)
