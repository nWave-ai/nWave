"""Creates a workspace: validates the schema, takes the kit snapshot, copies the schema in, opens an empty journal, exports the pre-feature baseline and writes the kit.

Every refusal happens before the workspace directory is created: the kit is decided from values first.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil
from typing import TYPE_CHECKING

from nwstep.application.kit_snapshot import KitInputs, KitSnapshot, is_source_file
from nwstep.domain.refusal import Refusal
from nwstep.infrastructure.baseline_export import BaselineExport
from nwstep.infrastructure.baseline_store import BaselineStore
from nwstep.infrastructure.kit_store import KitStore
from nwstep.infrastructure.package_paths import PackagePaths
from nwstep.infrastructure.skill_tree_reader import SkillTreeReader
from nwstep.infrastructure.toml_schema_reader import TomlSchemaReader
from nwstep.infrastructure.workspace_mode import WorkspaceMode


if TYPE_CHECKING:
    from pathlib import Path

    from nwstep.application.how_line import HowLine
    from nwstep.domain.schema import Schema
    from nwstep.infrastructure.workspace import Workspace


@dataclass(frozen=True)
class PreparedInit:
    """A checked schema and its kit, ready to write."""

    schema: Schema
    snapshot: KitSnapshot


class Initializer:
    def __init__(self, how: HowLine) -> None:
        self._how = how

    def prepare(
        self,
        schema_source: Path,
        workspace: Workspace,
        *,
        skills_source: Path,
        commit: str | None,
    ) -> PreparedInit:
        """Every refusal of init: checks the workspace, reads and kits the schema. Writes nothing."""
        init_how = self._how.command(
            "init",
            "--schema",
            str(schema_source),
            "--workspace",
            str(workspace.directory),
        )
        if workspace.journal_path.exists():
            raise Refusal(
                what=f"workspace {workspace.directory} is already initialized",
                why="init opens the journal once; creating it again would discard the recorded work",
                how=self._how.command(
                    "status", "--workspace", str(workspace.directory)
                ),
            )
        try:
            schema = TomlSchemaReader().read(schema_source)
        except Refusal as refusal:
            raise refusal.with_how(init_how) from None
        try:
            snapshot = KitSnapshot.take(
                KitInputs(
                    skill_files=SkillTreeReader().read(skills_source),
                    schema_bytes=schema_source.read_bytes(),
                    schema_skill_names=[
                        str(skill) for step in schema.steps for skill in step.skills
                    ],
                    template_files=SkillTreeReader().read(
                        PackagePaths.TEMPLATES, keep=lambda name: name.endswith(".tmpl")
                    ),
                    source_files=SkillTreeReader().read(
                        PackagePaths.SOURCE, keep=is_source_file
                    ),
                    commit=commit,
                )
            )
        except Refusal as refusal:
            raise refusal.with_how(init_how) from None
        return PreparedInit(schema=schema, snapshot=snapshot)

    def write(  # noqa: PLR0913
        self,
        prepared: PreparedInit,
        schema_source: Path,
        workspace: Workspace,
        root: Path,
        rev: str,
        *,
        mode: str | None,
    ) -> Schema:
        workspace.directory.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(schema_source, workspace.schema_path)
        workspace.journal_path.touch()
        workspace.lock_path.touch()
        baseline = BaselineExport().create(root, rev, workspace)
        BaselineStore(workspace).write(baseline)
        KitStore(workspace).write(prepared.snapshot)
        if mode is not None:
            WorkspaceMode(workspace).write(mode)
        return prepared.schema
