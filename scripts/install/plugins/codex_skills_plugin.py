"""Plugin for installing nWave Skills into Codex CLI's SKILL.md format.

Codex CLI expects skills at: $HOME/.agents/skills/{skill-name}/SKILL.md
Each skill lives in its own directory with a single SKILL.md file.

This is distinct from OpenCode (~/.config/opencode/skills/) and Claude Code
(~/.claude/skills/). The Codex skills path is under $HOME/.agents/, not
under ~/.codex/ -- per official Codex CLI documentation.

A manifest file (.nwave-manifest.json) tracks which skills nWave installed,
so uninstall() can remove only nWave skills without touching user-created ones.
"""

import json
import os
import shutil
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.agent_catalog import load_public_agents
from scripts.shared.platform_contracts import CODEX_SKILL_FORBIDDEN_FIELDS
from scripts.shared.skill_distribution import (
    enumerate_skills,
    filter_public_skills,
)


_MANIFEST_FILENAME = ".nwave-manifest.json"


def _codex_skills_dir() -> Path:
    """Return the Codex CLI skills target directory.

    Codex skills live at $HOME/.agents/skills/ -- note this is NOT under
    ~/.codex/; it is a sibling of ~/.codex/ at the $HOME level.
    CODEX_HOME only overrides ~/.codex/ (config dir); it has no effect on
    the skills path.

    For testing isolation the env var NWAVE_AGENTS_HOME overrides the
    resolved $HOME in the returned path.  Production code never sets this
    variable, so production semantics are always $HOME/.agents/skills/.

    Returns:
        Path to $HOME/.agents/skills/ (or $NWAVE_AGENTS_HOME/.agents/skills/)
    """
    agents_home_override = os.environ.get("NWAVE_AGENTS_HOME")
    if agents_home_override:
        return Path(agents_home_override) / ".agents" / "skills"
    return Path.home() / ".agents" / "skills"


def _codex_config_dir() -> Path:
    """Return the Codex CLI configuration directory.

    Returns:
        Path to ~/.codex/ (or $CODEX_HOME if set)
    """
    override = os.environ.get("CODEX_HOME")
    return Path(override) if override else Path.home() / ".codex"


def _find_skills_source(context: InstallContext) -> Path | None:
    """Locate the skills source directory from dist or project layout.

    Args:
        context: InstallContext with framework_source and project_root

    Returns:
        Path to the skills source directory, or None if not found
    """
    dist_skills = context.framework_source / "skills" / "nw"
    if dist_skills.exists():
        return dist_skills

    project_skills = context.project_root / "nWave" / "skills"
    if project_skills.exists():
        return project_skills

    return None


def _strip_forbidden_fields(content: str) -> str:
    """Remove Claude Code-only frontmatter fields from skill content.

    Strips YAML frontmatter fields listed in CODEX_SKILL_FORBIDDEN_FIELDS.
    Only operates within the frontmatter block (between --- delimiters).
    Body content is never modified.

    Args:
        content: Full skill file content with YAML frontmatter

    Returns:
        Content with forbidden fields removed from frontmatter
    """
    if not content.startswith("---"):
        return content

    end_index = content.find("---", 3)
    if end_index == -1:
        return content

    frontmatter = content[4:end_index]
    body = content[end_index:]

    filtered_lines = [
        line
        for line in frontmatter.splitlines(keepends=True)
        if not any(
            line.startswith(f"{field}:") for field in CODEX_SKILL_FORBIDDEN_FIELDS
        )
    ]

    return "---\n" + "".join(filtered_lines) + body


def _write_manifest(target_dir: Path, installed_skill_names: list[str]) -> None:
    """Write the manifest file tracking nWave-installed skills.

    Args:
        target_dir: Codex skills directory
        installed_skill_names: List of installed skill directory names
    """
    manifest = {
        "installed_skills": sorted(installed_skill_names),
        "version": "1.0",
    }
    manifest_path = target_dir / _MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _read_manifest(target_dir: Path) -> dict | None:
    """Read the manifest file if it exists.

    Args:
        target_dir: Codex skills directory

    Returns:
        Parsed manifest dict, or None if not found
    """
    manifest_path = target_dir / _MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


class CodexSkillsPlugin(InstallationPlugin):
    """Plugin for installing nWave Skills into Codex CLI's SKILL.md format."""

    def __init__(self) -> None:
        """Initialize Codex skills plugin with name and priority."""
        super().__init__(name="codex-skills", priority=50)

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        """Check whether Codex CLI is present; skip gracefully if not.

        Detection: ~/.codex/ directory exists OR `codex` binary in PATH.
        If neither is found the plugin returns success with a skip message --
        the absence of Codex is not an error.

        Args:
            context: InstallContext (unused for detection, but required by ABC)

        Returns:
            PluginResult with success=True always (skip or proceed)
        """
        codex_dir = _codex_config_dir()
        codex_binary = shutil.which("codex") is not None
        if not codex_dir.exists() and not codex_binary:
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Codex CLI not detected, skipping skills installation",
            )

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="Codex CLI prerequisites validated",
        )

    def install(self, context: InstallContext) -> PluginResult:
        """Install skills from nWave/skills/ to $HOME/.agents/skills/.

        Copies each source SKILL.md to the Codex skills directory, stripping
        Claude Code-only frontmatter fields. A manifest tracks installed skill
        names for safe uninstallation.

        Walking-skeleton scope: copies ALL public skills with no name transform
        (flat namespace, no collision resolution needed for the skeleton).

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            # Check prerequisites first; skip if Codex not present
            prereq = self.validate_prerequisites(context)
            if "skip" in prereq.message.lower():
                return prereq

            context.logger.info("  Installing Codex skills...")

            skills_source = _find_skills_source(context)
            if skills_source is None:
                context.logger.info("  No skills directory found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No skills to install (source directory not found)",
                )

            target_dir = _codex_skills_dir()
            target_dir.mkdir(parents=True, exist_ok=True)

            public_agents = (
                set()
                if context.dev_mode
                else load_public_agents(context.project_root / "nWave")
            )

            from scripts.shared.agent_catalog import build_ownership_map

            agents_dir = context.project_root / "nWave" / "agents"
            ownership_map = (
                build_ownership_map(agents_dir) if agents_dir.exists() else {}
            )

            entries = enumerate_skills(skills_source)
            entries = filter_public_skills(entries, public_agents, ownership_map)

            installed_names: list[str] = []
            installed_files: list[Path] = []

            for entry in entries:
                skill_target_dir = target_dir / entry.name
                if skill_target_dir.exists():
                    shutil.rmtree(skill_target_dir)
                skill_target_dir.mkdir(parents=True)

                target_file = skill_target_dir / "SKILL.md"
                if entry.source_path.is_dir():
                    source_file = entry.source_path / "SKILL.md"
                else:
                    source_file = entry.source_path

                content = source_file.read_text(encoding="utf-8")
                content = _strip_forbidden_fields(content)
                target_file.write_text(content, encoding="utf-8")

                installed_names.append(entry.name)
                installed_files.append(target_file)

            _write_manifest(target_dir, installed_names)

            context.logger.info(
                f"  Codex skills installed ({len(installed_names)} skills)"
            )

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Codex skills installed successfully ({len(installed_names)} skills)",
                installed_files=installed_files,
            )

        except Exception as e:
            context.logger.error(f"  Failed to install Codex skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex skills installation failed: {e!s}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only nWave-installed Codex skills using manifest.

        Reads the manifest to determine which skills were installed by nWave,
        removes only those, and leaves user-created skills untouched.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            context.logger.info("  Uninstalling Codex skills...")

            target_dir = _codex_skills_dir()
            manifest = _read_manifest(target_dir)

            if manifest is None:
                context.logger.info("  No Codex skills manifest found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No Codex skills to uninstall (no manifest found)",
                )

            installed_skills = manifest.get("installed_skills", [])
            removed_count = 0

            for skill_name in installed_skills:
                skill_dir = target_dir / skill_name
                if skill_dir.exists():
                    shutil.rmtree(skill_dir)
                    removed_count += 1

            manifest_path = target_dir / _MANIFEST_FILENAME
            if manifest_path.exists():
                manifest_path.unlink()

            context.logger.info(f"  Removed {removed_count} Codex skills")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Codex skills uninstalled ({removed_count} removed)",
            )

        except Exception as e:
            context.logger.error(f"  Failed to uninstall Codex skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex skills uninstallation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify Codex skills were installed correctly.

        Checks that each skill listed in the manifest has a valid SKILL.md file.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            context.logger.info("  Verifying Codex skills...")

            target_dir = _codex_skills_dir()
            manifest = _read_manifest(target_dir)

            if manifest is None:
                skills_source = _find_skills_source(context)
                if skills_source is None:
                    context.logger.info("  No Codex skills to verify (none configured)")
                    return PluginResult(
                        success=True,
                        plugin_name=self.name,
                        message="No Codex skills configured, verification skipped",
                    )

                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Codex skills verification failed: manifest not found",
                    errors=["Manifest file .nwave-manifest.json not found"],
                )

            installed_skills = manifest.get("installed_skills", [])
            missing_skills: list[str] = []
            verified_count = 0

            for skill_name in installed_skills:
                skill_md = target_dir / skill_name / "SKILL.md"
                if not skill_md.exists():
                    missing_skills.append(f"{skill_name}/SKILL.md not found")
                else:
                    verified_count += 1

            if missing_skills:
                context.logger.error(
                    f"  Codex skills verification failed: {len(missing_skills)} missing"
                )
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=(
                        f"Codex skills verification failed: "
                        f"{len(missing_skills)} skills missing SKILL.md"
                    ),
                    errors=missing_skills,
                )

            context.logger.info(f"  Verified {verified_count} Codex skills")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Codex skills verification passed ({verified_count} skills)",
            )

        except Exception as e:
            context.logger.error(f"  Failed to verify Codex skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex skills verification failed: {e!s}",
                errors=[str(e)],
            )
