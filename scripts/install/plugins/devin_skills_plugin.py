"""Plugin for installing nWave skills into Devin CLI's native SKILL.md format.

Devin CLI discovers global skills at ~/.config/devin/skills/<name>/SKILL.md
(``devin skills paths`` reports this as the first user-level search root on
Linux/macOS). The SKILL.md format is compatible with Claude Code's: ``name``
and ``description`` frontmatter are natively recognised; unknown keys such as
``metadata`` are preserved as opaque metadata.

The target directory is ``~/.config/devin/skills/`` by default; the
``DEVIN_CONFIG_DIR`` env var relocates it for test isolation (same pattern as
the OMP ``PI_CONFIG_DIR`` override).

The folder policy (manifest ownership, foreign-collision refusal, staging and
swap, uninstall, verify) is shared with the other folder-skill hosts and lives
in public_skill_folders; this plugin owns only Devin's directory and its
prerequisite check.
"""

import shutil  # noqa: F401 - the Devin staging test patches shutil.copytree through this module's attribute
from shutil import which as _which

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.public_skill_folders import (  # noqa: F401 - the Devin tests import the source finder from here
    find_skills_source as _find_skills_source,
)
from scripts.install.plugins.public_skill_folders import (
    install_public_skill_folders,
    uninstall_public_skill_folders,
    verify_public_skill_folders,
)
from scripts.shared.install_paths import devin_config_dir, devin_skills_dir


class DevinSkillsPlugin(InstallationPlugin):
    """Plugin for installing nWave skills into the Devin CLI native format."""

    def __init__(self) -> None:
        super().__init__(name="devin-skills", priority=37)

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        """Check whether Devin CLI is present; skip gracefully if not.

        Detection: ~/.config/devin/ directory exists OR ``devin`` binary in PATH.
        If neither is found, the plugin returns success with a skip message —
        the absence of Devin is not an error.
        """
        devin_dir = devin_config_dir()
        devin_binary = _which("devin") is not None
        if (
            "devin" not in context.target_platforms
            and not devin_dir.exists()
            and not devin_binary
        ):
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Devin not detected, skipping skills installation",
            )

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="Devin prerequisites validated",
        )

    def install(self, context: InstallContext) -> PluginResult:
        """Install public skills from nWave/skills/ into Devin's global tree."""
        prereq = self.validate_prerequisites(context)
        if "skip" in prereq.message.lower():
            return prereq
        return install_public_skill_folders(
            context,
            devin_skills_dir(),
            plugin_name=self.name,
            host="devin",
            label="Devin",
        )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only manifest-owned Devin skills; everything else stays."""
        return uninstall_public_skill_folders(
            context, devin_skills_dir(), plugin_name=self.name, label="Devin"
        )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify manifest-listed Devin skill trees exist and are not symlinks."""
        return verify_public_skill_folders(
            context, devin_skills_dir(), plugin_name=self.name, label="Devin"
        )
