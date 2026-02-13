"""
Wrapper plugin for utilities installation.

Encapsulates the _install_utility_scripts() method from NWaveInstaller,
maintaining backward compatibility while enabling plugin-based orchestration.
"""

import shutil

from scripts.install.install_utils import PathUtils, VersionUtils
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)


class UtilitiesPlugin(InstallationPlugin):
    """Plugin for installing utilities into the nWave framework."""

    def __init__(self):
        """Initialize utilities plugin with name and priority."""
        super().__init__(name="utilities", priority=40)

    def install(self, context: InstallContext) -> PluginResult:
        """Install utilities into the framework.

        Copies utility scripts from project's scripts directory to the target
        Claude config directory, using version checking to upgrade only when
        source version is newer.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure of installation
        """
        try:
            context.logger.info("  📦 Installing utilities...")

            # dist/ layout: scripts/ (utility scripts collected by build_dist.py)
            # source layout: project root scripts/
            dist_scripts = context.framework_source / "scripts"
            if (
                dist_scripts.exists()
                and (dist_scripts / "install_nwave_target_hooks.py").exists()
            ):
                scripts_source = dist_scripts
            else:
                scripts_source = context.project_root / "scripts"
            scripts_target = context.claude_dir / "scripts"
            scripts_target.mkdir(parents=True, exist_ok=True)

            # List of utility scripts to install with version checking
            utility_scripts = ["install_nwave_target_hooks.py", "validate_step_file.py"]

            installed_files = []
            installed_count = 0

            for script_name in utility_scripts:
                source_script = scripts_source / script_name
                target_script = scripts_target / script_name

                if not source_script.exists():
                    continue

                source_ver = VersionUtils.extract_version_from_file(source_script)
                target_ver = (
                    VersionUtils.extract_version_from_file(target_script)
                    if target_script.exists()
                    else "0.0.0"
                )

                if VersionUtils.compare_versions(source_ver, target_ver) > 0:
                    shutil.copy2(source_script, target_script)
                    context.logger.info(
                        f"  📁 {script_name} upgraded ({target_ver} \u2192 {source_ver})"
                    )
                    installed_files.append(str(target_script))
                    installed_count += 1
                elif not target_script.exists():
                    shutil.copy2(source_script, target_script)
                    context.logger.info(f"  📁 {script_name} installed (v{source_ver})")
                    installed_files.append(str(target_script))
                    installed_count += 1
                else:
                    context.logger.info(
                        f"  📁 {script_name} up-to-date (v{target_ver})"
                    )

            total_scripts = PathUtils.count_files(scripts_target, "*.py")
            context.logger.info(f"  ✅ Utilities installed ({installed_count} scripts)")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Utilities installed successfully ({total_scripts} scripts)",
                installed_files=installed_files,
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to install utilities: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Utilities installation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify utilities were installed correctly.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            context.logger.info("  🔎 Verifying utilities...")

            target_scripts_dir = context.claude_dir / "scripts"

            # Check target directory exists
            if not target_scripts_dir.exists():
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Utilities verification failed: target directory does not exist",
                    errors=["Target directory not found"],
                )

            # Check for utility scripts (primary: .py files)
            utility_scripts = list(target_scripts_dir.glob("*.py"))

            if not utility_scripts:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Utilities verification failed: no utility scripts found",
                    errors=["No .py files in target directory"],
                )

            context.logger.info(f"  ✅ Verified {len(utility_scripts)} utility scripts")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Utilities verification passed ({len(utility_scripts)} scripts)",
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to verify utilities: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Utilities verification failed: {e!s}",
                errors=[str(e)],
            )
