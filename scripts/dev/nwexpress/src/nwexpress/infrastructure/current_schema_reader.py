"""Reads the declared current schema from templates/versions.toml and resolves it against the shipped schema files."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from nwexpress.domain.current_schema import resolve_current
from nwexpress.domain.refusal import Refusal
from nwexpress.infrastructure.package_paths import PackagePaths


if TYPE_CHECKING:
    from pathlib import Path


def declared_current_name(manifest: Path = PackagePaths.MANIFEST) -> str:
    """The file name the manifest declares as current, or a refusal when the manifest declares none."""
    declared = tomllib.loads(manifest.read_text(encoding="utf-8")).get("current_schema")
    if not isinstance(declared, str):
        raise Refusal(
            what=f"{manifest} declares no current schema",
            why="the default schema is the one the shipped set declares current; without the declaration a run has no schema to start from",
            how=f'add a line current_schema = "<one shipped schema file name>" above the first table in {manifest}',
        )
    return declared


def shipped_current_schema() -> Path:
    """The shipped schema file a run starts from when init is given no schema."""
    name = resolve_current(
        declared_current_name(), frozenset(PackagePaths.shipped_schemas())
    )
    return PackagePaths.SCHEMAS / name
