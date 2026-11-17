"""Plugin for installing nWave's public skills for GitHub Copilot CLI (card t-0467).

Copilot reads a personal skill from ``<COPILOT_HOME or ~/.copilot>/skills/<name>/SKILL.md``. The public skills are the
same selection the Claude install and the Devin install make, copied verbatim with their host paths rewritten; Copilot
parses each one as strict YAML, and every public skill of this repository parses (observed on Copilot CLI 1.0.103).

The folder policy (manifest ownership, foreign-collision refusal, staging and swap, uninstall, verify) is shared with
the Devin plugin in public_skill_folders; this plugin owns only Copilot's folder.
"""

from __future__ import annotations

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.copilot_common import (
    NOT_CHECKED,
    copilot_skills_dir,
)
from scripts.install.plugins.public_skill_folders import (
    install_public_skill_folders,
    uninstall_public_skill_folders,
    verify_public_skill_folders,
)


class CopilotSkillsPlugin(InstallationPlugin):
    """Plugin for installing nWave skills into the Copilot CLI skills folder."""

    def __init__(self) -> None:
        super().__init__(name="copilot-skills", priority=36)

    def install(self, context: InstallContext) -> PluginResult:
        """Install public skills into the Copilot skills folder; the summary says what was written and not checked."""
        result = install_public_skill_folders(
            context,
            copilot_skills_dir(),
            plugin_name=self.name,
            host="copilot",
            label="Copilot",
        )
        if result.success:
            context.logger.summary(f"  ✅ {result.message}; {NOT_CHECKED}")
        return result

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only manifest-owned Copilot skills; everything else stays."""
        return uninstall_public_skill_folders(
            context, copilot_skills_dir(), plugin_name=self.name, label="Copilot"
        )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify manifest-listed Copilot skill trees exist and are not symlinks."""
        return verify_public_skill_folders(
            context, copilot_skills_dir(), plugin_name=self.name, label="Copilot"
        )
