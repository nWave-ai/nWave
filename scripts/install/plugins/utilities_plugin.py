"""
Wrapper plugin for utilities installation.

Encapsulates the _install_utility_scripts() method from NWaveInstaller,
maintaining backward compatibility while enabling plugin-based orchestration.

Upgrade hygiene is manifest-driven (shared ``.nwave-manifest.json``
mechanism): install records the shipped script names under the utilities
family key; upgrade sweeps only names that key tracks and the current
version no longer ships. The DES family shares the same directory and
document — its key is a sibling, never clobbered, never swept by this
plugin. User scripts and anything else no record positively identifies are
preserved (hard contract); a pre-record target is adopted with a warning.
"""

import shutil
from pathlib import Path

from scripts.install.install_utils import PathUtils, VersionUtils
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.skill_distribution import (
    SCRIPTS_FAMILY_KEY,
    UTILITIES_FAMILY_KEY,
    FamilyRecord,
    preserve_warning_message,
    read_family_record,
    sweep_retired_assets,
    unaccounted_names,
    write_family_record,
)


class UtilitiesPlugin(InstallationPlugin):
    """Plugin for installing utilities into the nWave framework."""

    # Utility scripts installed (with version checking) to ~/.claude/scripts/
    UTILITY_SCRIPTS = ["install_nwave_target_hooks.py", "validate_step_file.py"]

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

            record = read_family_record(
                scripts_target,
                key=UTILITIES_FAMILY_KEY,
                sibling_keys=frozenset({SCRIPTS_FAMILY_KEY}),
            )

            if context.dry_run:
                total_scripts = PathUtils.count_files(scripts_target, "*.py")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message=f"Utilities installed successfully ({total_scripts} scripts)",
                )

            self._reconcile_target(scripts_target, record, context)

            installed_files: list[str] = []
            installed_count = 0
            recorded: list[str] = []

            for script_name in self.UTILITY_SCRIPTS:
                source_script = scripts_source / script_name
                target_script = scripts_target / script_name

                if not source_script.exists():
                    continue
                recorded.append(script_name)

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

            write_family_record(
                scripts_target,
                recorded,
                key=UTILITIES_FAMILY_KEY,
                superseded_keys=record.superseded_keys,
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

    def _reconcile_target(
        self,
        scripts_target: Path,
        record: FamilyRecord,
        context: InstallContext,
    ) -> None:
        """Sweep this family's retired scripts; adopt a pre-record target."""
        if record.tracked is None:
            self._warn_unrecorded_scripts(scripts_target, record.accounted, context)
            return
        removed, blocked = sweep_retired_assets(
            scripts_target, record.tracked - set(self.UTILITY_SCRIPTS)
        )
        for name in removed:
            context.logger.info(f"  🗑️ Removed retired utility script: {name}")
        for name in blocked:
            context.logger.warning(
                f"  ⚠️ Cannot remove read-only retired script: {name}"
            )

    def _warn_unrecorded_scripts(
        self,
        scripts_target: Path,
        accounted: frozenset[str],
        context: InstallContext,
    ) -> None:
        """Preserve-by-default: warn about scripts no record accounts for."""
        unrecorded = unaccounted_names(
            scripts_target,
            accounted=accounted,
            expected=frozenset(self.UTILITY_SCRIPTS),
            scope_glob="*.py",
        )
        if not unrecorded:
            return
        context.logger.warning(
            preserve_warning_message(
                scripts_target,
                unrecorded,
                family_label="utilities record",
                item_label="script",
            )
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
