"""Plugin for installing nWave's public skills for Amp (ampcode.com).

Amp reads a user skill from ``~/.config/amp/skills/<name>/SKILL.md`` and loads a skill by the frontmatter ``name`` and
``description`` it lists for the model; the SKILL.md format is Claude Code's. The public skills are the same selection
the Devin and Copilot installs make, copied with their host paths rewritten.

Amp uses the first skill it finds for a name, and two user roots come before this one: ``~/.config/agents/skills/`` and
``~/.agents/skills/`` (where the Codex install writes). When Codex is installed too, Amp loads Codex's copy of each
skill; the bodies are the same apart from their host paths.

The folder policy (manifest ownership, foreign-collision refusal, staging and swap, uninstall, verify) is shared with
the Devin and Copilot plugins in public_skill_folders; this plugin owns only Amp's folder.
"""

from __future__ import annotations

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.public_skill_folders import (
    install_public_skill_folders,
    uninstall_public_skill_folders,
    verify_public_skill_folders,
)
from scripts.shared.install_paths import amp_skills_dir


class AmpSkillsPlugin(InstallationPlugin):
    """Plugin for installing nWave skills into Amp's user skills folder."""

    def __init__(self) -> None:
        super().__init__(name="amp-skills", priority=37)

    def install(self, context: InstallContext) -> PluginResult:
        """Install public skills into ~/.config/amp/skills/."""
        return install_public_skill_folders(
            context,
            amp_skills_dir(),
            plugin_name=self.name,
            host="amp",
            label="Amp",
        )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only manifest-owned Amp skills; everything else stays."""
        return uninstall_public_skill_folders(
            context, amp_skills_dir(), plugin_name=self.name, label="Amp"
        )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify manifest-listed Amp skill trees exist and are not symlinks."""
        return verify_public_skill_folders(
            context, amp_skills_dir(), plugin_name=self.name, label="Amp"
        )
