"""The one list of area names an install run writes, shared by the dry run and the real run.

A dry run and a real run print the same ``areas:`` line for the same inputs. This module
owns the area names; nothing else spells them. Inputs are read once, before any write, so
the dry run and the real run decide from the same facts.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


class InstallArea(Enum):
    """A part of the machine an install run may write. The value is the name users read."""

    AGENTS = "agents"
    SKILLS = "skills"
    TEMPLATES = "templates"
    SCRIPTS = "scripts"
    SETTINGS = "settings.json"
    HOOKS = "hooks"
    ATTRIBUTION = "attribution"
    GUIDANCE = "guidance"
    PROJECT_CONFIG = "project-config"
    BACKUP = "backup"


_PLATFORM_AREAS: dict[str, frozenset[InstallArea]] = {
    "claude_code": frozenset(
        {
            InstallArea.AGENTS,
            InstallArea.SKILLS,
            InstallArea.TEMPLATES,
            InstallArea.SCRIPTS,
            InstallArea.SETTINGS,
        }
    ),
    "codex": frozenset({InstallArea.AGENTS, InstallArea.SKILLS, InstallArea.HOOKS}),
    "cursor": frozenset({InstallArea.HOOKS}),
    "copilot": frozenset({InstallArea.HOOKS}),
    "opencode": frozenset({InstallArea.AGENTS, InstallArea.SKILLS}),
    "omp": frozenset({InstallArea.AGENTS, InstallArea.SKILLS, InstallArea.HOOKS}),
    "devin": frozenset({InstallArea.SKILLS}),
    "pi": frozenset({InstallArea.HOOKS}),
}


def planned_areas(
    *,
    target_platforms: Iterable[str],
    is_nwave_project: bool,
    jev_pending: bool,
    backup_needed: bool,
) -> tuple[InstallArea, ...]:
    """Pure: the areas a run writes, in the order the enum declares them.

    Every installed run writes attribution. Guidance is written only into an nWave
    project; the project's Jev declaration is written while it is pending; a backup is
    made only when a Claude installation already exists.
    """
    chosen: set[InstallArea] = {InstallArea.ATTRIBUTION}
    for platform in target_platforms:
        chosen |= _PLATFORM_AREAS.get(platform, frozenset())
    if is_nwave_project:
        chosen.add(InstallArea.GUIDANCE)
    if jev_pending:
        chosen.add(InstallArea.PROJECT_CONFIG)
    if backup_needed:
        chosen.add(InstallArea.BACKUP)
    return tuple(area for area in InstallArea if area in chosen)


def areas_line(areas: Iterable[InstallArea]) -> str:
    """Pure: the names of the areas, comma separated, in the order given."""
    return ", ".join(area.value for area in areas)


def project_facts(project_root: Path, home_dir: Path) -> tuple[bool, bool]:
    """Read only: (the folder is an nWave project, its Jev declaration is still pending).

    An nWave project is a folder whose activation declaration is enabled, the same
    declaration ``nwave-ai project enable`` writes and doctor reads.
    """
    from nwave_ai.platform.activation import resolve_activation
    from nwave_ai.platform.config import NWaveConfig
    from nwave_ai.platform.config_writer import ConfigWriter

    config = NWaveConfig(cwd=project_root)
    is_project = resolve_activation(config.enabled_for_repo, config.activation_mode)
    try:
        declared = ConfigWriter(
            home_dir=home_dir, repo_root=project_root
        ).repo_declares_jev()
    except Exception:
        declared = True
    return is_project, not declared
