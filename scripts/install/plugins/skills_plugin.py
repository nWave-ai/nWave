"""
Plugin for installing Skills into ~/.claude/skills/.

Supports two source layouts:
- NEW_FLAT: nw-*/SKILL.md directories (each skill is a flat nw-prefixed dir)
- OLD_HIERARCHICAL: {agent}/*.md directories (legacy agent-grouped layout)

Layout detection: if any nw-* directory containing SKILL.md exists in the
source, use NEW_FLAT. Otherwise fall back to OLD_HIERARCHICAL.

During install, the old ~/.claude/skills/nw/ namespace directory is removed
to clean up from previous hierarchical installs. User custom skills (dirs
without nw- prefix) are never touched.

Delegates enumerate/filter/copy logic to scripts.shared.skill_distribution.
"""

import shutil
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.agent_catalog import (
    build_ownership_map,
    detect_command_skills,
    load_public_agents,
)
from scripts.shared.install_paths import (
    PYTHON_CMD_SUBSTITUTION,
    resolve_python_command,
)
from scripts.shared.skill_distribution import (
    SourceLayout,
    cleanup_legacy_namespace,
    copy_skills_to_target,
    detect_layout,
    enumerate_skills,
    filter_public_skills_with_reasons,
)


_SKILL_GROUP_EMOJIS: dict[str, str] = {
    "acceptance-designer": "\u2705",
    "agent-builder": "\U0001f916",
    "data-engineer": "\U0001f4be",
    "devop": "\U0001f527",
    "documentarist": "\U0001f4dd",
    "leanux-designer": "\U0001f3a8",
    "platform-architect": "\u2601\ufe0f",
    "product-discoverer": "\U0001f9ed",
    "product-owner": "\U0001f4cb",
    "researcher": "\U0001f52c",
    "software-crafter": "\U0001f4bb",
    "solution-architect": "\U0001f3d7\ufe0f",
    "troubleshooter": "\U0001f6e0\ufe0f",
}


def _skill_group_emoji(group_name: str) -> str:
    """Return the emoji for a skill group, stripping '-reviewer' suffix if present.

    Args:
        group_name: Skill group directory name (e.g. 'software-crafter-reviewer')

    Returns:
        Mapped emoji or fallback package emoji for unknown groups
    """
    base = group_name.removesuffix("-reviewer")
    return _SKILL_GROUP_EMOJIS.get(base, "\U0001f4e6")


def _substitute_python_in_installed_files(
    skills_target: Path,
    entries: list,
    python_cmd: str,
) -> None:
    """Replace $(command -v ...) pattern with resolved Python command in installed files.

    Only modifies .md files that contain the substitution pattern.
    Source files are never modified -- only the installed copies.

    Args:
        skills_target: Target directory where skills were installed
        entries: List of SkillEntry items that were installed
        python_cmd: Resolved Python command (e.g. 'python3')
    """
    for entry in entries:
        target_dir = skills_target / entry.name
        for md_file in target_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            if PYTHON_CMD_SUBSTITUTION in content:
                content = content.replace(PYTHON_CMD_SUBSTITUTION, python_cmd)
                md_file.write_text(content, encoding="utf-8")


class SkillsPlugin(InstallationPlugin):
    """Plugin for installing Skills into the Claude Code skills directory."""

    def __init__(self):
        """Initialize skills plugin with name and priority."""
        super().__init__(name="skills", priority=35)

    def install(self, context: InstallContext) -> PluginResult:
        """Install skills from source to ~/.claude/skills/.

        Detects source layout (NEW_FLAT or OLD_HIERARCHICAL) and copies
        accordingly. Cleans up old nw/ namespace directory during upgrade.
        Never touches user custom skills (dirs without nw- prefix).

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            context.logger.info("  \U0001f4e6 Installing skills...")

            skills_source, layout = self._resolve_source(context)

            if skills_source is None:
                context.logger.info(
                    "  \u23ed\ufe0f No skills directory found, skipping"
                )
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No skills to install (source directory not found)",
                )

            # Clean up old nw/ namespace from previous hierarchical installs
            skills_target = context.claude_dir / "skills"
            if cleanup_legacy_namespace(skills_target):
                context.logger.info(
                    "  \U0001f5d1\ufe0f Removed legacy skills/nw/ namespace directory"
                )

            if layout == SourceLayout.NEW_FLAT:
                return self._install_new_flat(context, skills_source)
            return self._install_old_hierarchical(context, skills_source)

        except Exception as e:
            context.logger.error(f"  \u274c Failed to install skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Skills installation failed: {e!s}",
                errors=[str(e)],
            )

    def _resolve_source(
        self, context: InstallContext
    ) -> tuple[Path | None, SourceLayout | None]:
        """Find skills source directory and detect its layout.

        Resolution order:
        1. dist/ layout: framework_source/skills/nw/ (build_dist.py adds nw/)
        2. NEW_FLAT: framework_source/skills/ with nw-*/SKILL.md dirs
        3. OLD_HIERARCHICAL: project_root/nWave/skills/ (legacy)

        Returns:
            (source_path, layout) or (None, None) if no source found
        """
        # dist/ layout: skills/nw/ (build_dist.py adds nw/ namespace)
        dist_skills = context.framework_source / "skills" / "nw"
        if dist_skills.exists():
            return dist_skills, SourceLayout.OLD_HIERARCHICAL

        # Check framework_source/skills/ for new flat layout
        flat_source = context.framework_source / "skills"
        if flat_source.exists() and detect_layout(flat_source) == SourceLayout.NEW_FLAT:
            return flat_source, SourceLayout.NEW_FLAT

        # Fall back to old hierarchical: project_root/nWave/skills/
        old_source = context.project_root / "nWave" / "skills"
        if old_source.exists():
            return old_source, detect_layout(old_source)

        return None, None

    def _install_new_flat(
        self, context: InstallContext, skills_source: Path
    ) -> PluginResult:
        """Install from NEW_FLAT layout: copy nw-* dirs to ~/.claude/skills/.

        Each nw-*/SKILL.md directory is copied directly under the skills
        target. Existing nw-* dirs in target are replaced; non-nw-* dirs
        (user custom skills) are left untouched. Private skills are filtered
        out via the shared skill_distribution pipeline.

        Command-skills (user-invocable slash commands) are always included
        regardless of agent ownership.
        """
        skills_target = context.claude_dir / "skills"
        skills_target.mkdir(parents=True, exist_ok=True)

        # Clean up legacy commands/nw/ directory (commands migrated to skills)
        old_commands = context.claude_dir / "commands" / "nw"
        if old_commands.exists():
            shutil.rmtree(old_commands)
            context.logger.info(
                "  \U0001f5d1\ufe0f Removed legacy commands/nw/ (migrated to skills)"
            )

        # Shared pipeline: enumerate -> filter -> copy
        public_agents = (
            set()
            if context.dev_mode
            else load_public_agents(context.project_root / "nWave")
        )
        ownership_map = build_ownership_map(context.project_root / "nWave" / "agents")
        command_skills = detect_command_skills(skills_source)

        entries = enumerate_skills(skills_source)
        entries, excluded = filter_public_skills_with_reasons(
            entries, public_agents, ownership_map, command_skills
        )
        for skipped_name, reason in excluded:
            context.logger.info(f"  ⏭️ Skipped {skipped_name}: {reason}")
        copy_skills_to_target(entries, skills_target, clean_existing=True)

        # Resolve Python command substitution in installed files
        python_cmd = resolve_python_command()
        _substitute_python_in_installed_files(skills_target, entries, python_cmd)

        # Collect installed files for reporting
        installed_files: list[Path] = []
        for entry in entries:
            target_dir = skills_target / entry.name
            installed_files.extend(target_dir.rglob("*.md"))

        count = len(installed_files)
        context.logger.info(f"  \u2705 Skills installed ({count} files)")

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"Skills installed successfully ({count} files)",
            installed_files=installed_files,
        )

    def _install_old_hierarchical(
        self, context: InstallContext, skills_source: Path
    ) -> PluginResult:
        """Install from OLD_HIERARCHICAL layout: copy to ~/.claude/skills/nw/.

        Preserves existing behavior: each agent-grouped subdirectory is
        copied under ~/.claude/skills/nw/{agent}/. Private skills are
        filtered out via the shared skill_distribution pipeline.
        """
        skills_target = context.claude_dir / "skills" / "nw"

        # Shared pipeline: enumerate -> filter -> copy
        public_agents = (
            set()
            if context.dev_mode
            else load_public_agents(context.project_root / "nWave")
        )
        ownership_map = build_ownership_map(context.project_root / "nWave" / "agents")

        entries = enumerate_skills(skills_source)
        entries, excluded = filter_public_skills_with_reasons(
            entries, public_agents, ownership_map
        )
        for skipped_name, reason in excluded:
            context.logger.info(f"  ⏭️ Skipped {skipped_name}: {reason}")

        # Only create target dir if there are skills to install
        if entries:
            if skills_target.exists():
                shutil.rmtree(skills_target)
            skills_target.mkdir(parents=True, exist_ok=True)
            copy_skills_to_target(entries, skills_target)

        # Collect installed files for reporting
        installed_files: list[Path] = []
        for entry in entries:
            target_dir = skills_target / entry.name
            installed_files.extend(target_dir.rglob("*.md"))

        count = len(installed_files)
        context.logger.info(f"  \u2705 Skills installed ({count} files)")

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"Skills installed successfully ({count} files)",
            installed_files=installed_files,
        )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall skills by removing ~/.claude/skills/nw/.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            context.logger.info("  🗑️ Uninstalling skills...")

            skills_nw_dir = context.claude_dir / "skills" / "nw"

            if not skills_nw_dir.exists():
                context.logger.info("  ⏭️ No skills directory found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No skills to uninstall (directory not found)",
                )

            shutil.rmtree(skills_nw_dir)
            context.logger.info("  🗑️ Removed skills/nw directory")

            # Remove parent skills directory if empty
            skills_dir = context.claude_dir / "skills"
            if skills_dir.exists():
                try:
                    if not any(skills_dir.iterdir()):
                        skills_dir.rmdir()
                        context.logger.info("  🗑️ Removed empty skills directory")
                except OSError:
                    pass

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Skills uninstalled successfully",
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to uninstall skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Skills uninstallation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify skills were installed correctly.

        Checks both new flat layout (nw-* dirs under skills/) and old
        hierarchical layout (skills/nw/{agent}/ dirs).

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            context.logger.info("  \U0001f50e Verifying skills...")

            skills_dir = context.claude_dir / "skills"
            old_target = skills_dir / "nw"

            # Collect skill files from both layouts
            skill_files: list[Path] = []
            skill_groups: list[str] = []

            # New flat layout: nw-* dirs directly under skills/
            if skills_dir.exists():
                for d in skills_dir.iterdir():
                    if d.is_dir() and d.name.startswith("nw-"):
                        skill_groups.append(d.name)
                        skill_files.extend(d.rglob("*.md"))

            # Old hierarchical layout: skills/nw/{agent}/
            if old_target.exists():
                for d in old_target.iterdir():
                    if d.is_dir():
                        skill_groups.append(d.name)
                        skill_files.extend(d.rglob("*.md"))

            if not skill_files:
                # Check if source even exists
                source, _ = self._resolve_source(context)
                if source is None:
                    context.logger.info(
                        "  \u23ed\ufe0f No skills to verify (none configured)"
                    )
                    return PluginResult(
                        success=True,
                        plugin_name=self.name,
                        message="No skills configured, verification skipped",
                    )

                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Skills verification failed: no skill files found",
                    errors=["No .md files in skills target directory"],
                )

            context.logger.info(
                f"  \u2705 Verified {len(skill_files)} skill files "
                f"in {len(skill_groups)} groups:"
            )
            for group in sorted(skill_groups):
                emoji = _skill_group_emoji(group)
                context.logger.info(f"    {emoji} {group}")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Skills verification passed ({len(skill_files)} files in {len(skill_groups)} groups)",
            )
        except Exception as e:
            context.logger.error(f"  \u274c Failed to verify skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Skills verification failed: {e!s}",
                errors=[str(e)],
            )
