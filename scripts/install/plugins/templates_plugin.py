"""
Wrapper plugin for templates installation.

Encapsulates the _install_templates() method from NWaveInstaller,
maintaining backward compatibility while enabling plugin-based orchestration.
"""

import shutil

from scripts.install.install_utils import PathUtils
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)


class TemplatesPlugin(InstallationPlugin):
    """Plugin for installing templates into the nWave framework."""

    def __init__(self):
        """Initialize templates plugin with name and priority."""
        super().__init__(name="templates", priority=30)

    def install(self, context: InstallContext) -> PluginResult:
        """Install templates into the framework.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure of installation
        """
        try:
            context.logger.info("  📦 Installing templates...")

            # Determine source directory (prefer templates_dir from context)
            templates_source = context.templates_dir

            # Fallback to framework_source if templates_dir doesn't exist
            if not templates_source.exists():
                templates_source = context.framework_source / "templates"

            if not templates_source.exists():
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Templates source directory does not exist",
                    errors=[f"Source not found: {templates_source}"],
                )

            # Target directory
            templates_target = context.claude_dir / "templates"
            templates_target.mkdir(parents=True, exist_ok=True)

            # Copy template files (preserving directory structure)
            installed_files = []
            for item in templates_source.iterdir():
                target = templates_target / item.name
                if item.is_dir():
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(item, target)
                    # Collect installed file paths
                    for file in target.rglob("*.yaml"):
                        installed_files.append(str(file))
                    for file in target.rglob("*.md"):
                        installed_files.append(str(file))
                else:
                    shutil.copy2(item, target)
                    installed_files.append(str(target))

            copied_count = PathUtils.count_files(templates_target, "*.yaml")
            context.logger.info(f"  ✅ Templates installed ({copied_count} files)")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Templates installed successfully ({copied_count} files)",
                installed_files=installed_files,
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to install templates: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Templates installation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify templates were installed correctly.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            context.logger.info("  🔎 Verifying templates...")

            target_templates_dir = context.claude_dir / "templates"

            # Check target directory exists
            if not target_templates_dir.exists():
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Templates verification failed: target directory does not exist",
                    errors=["Target directory not found"],
                )

            # Check for template files (primary: .yaml, fallback: .md)
            template_files = list(target_templates_dir.glob("*.yaml"))
            if not template_files:
                # Fallback check for .md files
                template_files = list(target_templates_dir.glob("*.md"))

            if not template_files:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Templates verification failed: no template files found",
                    errors=["No .yaml or .md files in target directory"],
                )

            context.logger.info(f"  ✅ Verified {len(template_files)} template files")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Templates verification passed ({len(template_files)} files)",
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to verify templates: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Templates verification failed: {e!s}",
                errors=[str(e)],
            )
