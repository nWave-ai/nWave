"""
Wrapper plugin for templates installation.

Encapsulates the _install_templates() method from NWaveInstaller,
maintaining backward compatibility while enabling plugin-based orchestration.

Upgrade hygiene is manifest-driven (shared ``.nwave-manifest.json``
mechanism): install records the shipped asset names under the templates
family key; upgrade sweeps only manifest-tracked names absent from the
current source. Anything the record does not positively identify — user
templates included — is preserved (hard contract); a pre-record target is
adopted with a warning instead of swept.
"""

import shutil
from pathlib import Path

from scripts.install.install_utils import PathUtils
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.skill_distribution import (
    TEMPLATES_FAMILY_KEY,
    FamilyRecord,
    preserve_warning_message,
    read_family_record,
    sweep_retired_assets,
    unaccounted_names,
    write_family_record,
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

            source_names = frozenset(item.name for item in templates_source.iterdir())
            record = read_family_record(
                templates_target, key=TEMPLATES_FAMILY_KEY, adopt_legacy=True
            )

            installed_files: list[str] = []
            if not context.dry_run:
                self._reconcile_target(templates_target, record, source_names, context)
                installed_files = self._copy_templates(
                    templates_source, templates_target
                )
                write_family_record(
                    templates_target,
                    sorted(source_names),
                    key=TEMPLATES_FAMILY_KEY,
                    superseded_keys=record.superseded_keys,
                )

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

    def _reconcile_target(
        self,
        templates_target: Path,
        record: FamilyRecord,
        source_names: frozenset[str],
        context: InstallContext,
    ) -> None:
        """Sweep manifest-tracked retired assets; adopt a pre-record target."""
        if record.tracked is None:
            self._warn_unrecorded_templates(
                templates_target, record.accounted, source_names, context
            )
            return
        removed, blocked = sweep_retired_assets(
            templates_target, record.tracked - source_names
        )
        for name in removed:
            context.logger.info(f"  🗑️ Removed retired template: {name}")
        for name in blocked:
            context.logger.warning(
                f"  ⚠️ Cannot remove read-only retired template: {name}"
            )

    @staticmethod
    def _warn_unrecorded_templates(
        templates_target: Path,
        accounted: frozenset[str],
        source_names: frozenset[str],
        context: InstallContext,
    ) -> None:
        """Preserve-by-default: warn about items no record accounts for."""
        unrecorded = unaccounted_names(
            templates_target, accounted=accounted, expected=source_names
        )
        if not unrecorded:
            return
        context.logger.warning(
            preserve_warning_message(
                templates_target,
                unrecorded,
                family_label="templates record",
                item_label="item",
            )
        )

    @staticmethod
    def _copy_templates(templates_source: Path, templates_target: Path) -> list[str]:
        """Copy template files, preserving directory structure."""
        installed_files: list[str] = []
        for item in templates_source.iterdir():
            target = templates_target / item.name
            if item.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
                installed_files.extend(str(file) for file in target.rglob("*.yaml"))
                installed_files.extend(str(file) for file in target.rglob("*.md"))
            else:
                shutil.copy2(item, target)
                installed_files.append(str(target))
        return installed_files

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
