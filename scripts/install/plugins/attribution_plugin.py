"""Attribution plugin for install-time commit-credit setup.

Couples commit attribution to per-repo nWave activation (ADR-CA-007): the
un-gateable ``~/.claude/settings.json`` ``attribution.{commit,pr}`` write surface
is RETIRED. The activation-gated PreToolUse hook (universal pre-tool-use adapter)
is the sole enforcement, gated by ``attribution.enabled`` at invocation time.
Runs LAST (priority 200) -- never blocks core installation.
"""

import sys
from pathlib import Path

from scripts.install.attribution_utils import (
    ATTRIBUTION_USER_MANAGED,
    UnreadableAttributionPreference,
    classify_attribution_value,
    cleanup_legacy_attribution_hook,
    migrate_legacy_hook,
    migrate_legacy_settings_attribution,
    read_attribution_preference,
    read_global_config,
    write_attribution_preference,
    write_global_config,
)
from scripts.install.host_attribution import (
    AttributionPreference,
    HostAttributionPolicy,
)

from .base import InstallationPlugin, InstallContext, PluginResult


_MSG_FIRST_TIME_ENABLED = (
    "nWave attribution enabled. New Claude commits will carry the nWave credit "
    "via the universal handler (observes the preference at commit time). "
    "Run `nwave-ai attribution off` to disable."
)
_MSG_USER_MODIFIED = (
    "  Attribution credit was user-modified; left it untouched and "
    "remembered the previous value for later restoration."
)


class AttributionPlugin(InstallationPlugin):
    """Install-time attribution setup: legacy retirement, preference, host mechanisms.

    Priority 200: runs after all core plugins (agents=10, commands=20,
    skills=30, des=50, templates=60, utilities=70).

    The policy supplies the targeted hosts' mechanisms; the plugin installs
    them and reports their observed availability.
    """

    def __init__(
        self,
        config_dir: Path | None = None,
        policy: HostAttributionPolicy | None = None,
    ):
        super().__init__(name="attribution", priority=200)
        self._config_dir = config_dir
        self._policy = policy or HostAttributionPolicy.for_platforms(())

    def _config_dir_for(self, context: InstallContext) -> Path:
        if self._config_dir is not None:
            return self._config_dir
        if context.locations is not None:
            return context.locations.agents_home / ".nwave"
        return Path.home() / ".nwave"

    def install(self, context: InstallContext) -> PluginResult:
        """Register the activation-gated commit-attribution hook + record opt-in.

        Never raises -- all errors caught and returned as success with a
        warning message (attribution must not block install).
        """
        try:
            return self._do_install(context)
        except Exception as e:
            context.logger.warn(
                f"  Attribution setup encountered an error: {e}. "
                "Enable manually: nwave-ai attribution on"
            )
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Attribution skipped due to error: {e}",
            )

    def _do_install(self, context: InstallContext) -> PluginResult:
        """Core install logic, may raise.

        A new install defaults to opt-in (enabled=True) without prompting.
        Any legacy ``prepare-commit-msg`` hook is dismantled first. The retired
        ``settings.json attribution.{commit,pr}`` write is NOT performed
        (ADR-CA-007 DDD-1/DDD-2): the activation-gated PreToolUse hook is the
        sole enforcement via universal handler observing attribution.enabled.
        """
        config_dir = self._config_dir_for(context)
        # The CLI runs the installer from its package root, not the user's repo.
        repository = (
            context.user_project_root
            if context.user_project_root is not None
            else Path.cwd()
        )
        preference = AttributionPreference.read(config_dir)
        self._retire_legacy(context, config_dir, repository)
        if isinstance(preference, UnreadableAttributionPreference):
            warning = preference.warning()
            context.logger.warn(f"  {warning}")
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=warning,
            )

        resulting = preference.after_install()
        if resulting is not preference:
            write_attribution_preference(config_dir, enabled=resulting.is_enabled)
        self._install_host_mechanisms(context, resulting, config_dir, repository)

        if not resulting.is_enabled:
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Attribution preference preserved (disabled)",
            )

        if not self._policy.has_hosts or self._policy.claude_expected:
            context.logger.info(f"  {_MSG_FIRST_TIME_ENABLED}")
        return PluginResult(
            success=True,
            plugin_name="attribution",
            message=_MSG_FIRST_TIME_ENABLED,
        )

    def _retire_legacy(
        self, context: InstallContext, config_dir: Path, repository: Path
    ) -> None:
        migrate_legacy_hook(config_dir, repository=repository)
        migrate_legacy_settings_attribution(config_dir, claude_dir=context.claude_dir)
        try:
            cleanup_legacy_attribution_hook(claude_dir=context.claude_dir)
        except Exception:
            pass

    def _install_host_mechanisms(
        self,
        context: InstallContext,
        preference: AttributionPreference,
        config_dir: Path,
        repository: Path,
    ) -> None:
        """Install each targeted host's mechanism; report it while enabled.

        The mechanism is installed even while the preference is disabled (it
        checks the saved preference when a commit is made, so enabling later
        starts marking). Nothing is reported for a disabled preference, and an
        unavailable mechanism is a warning, never an installation failure.
        """
        for mechanism in self._policy.mechanisms_in(repository):
            in_force = mechanism.install(config_dir)
            if not preference.is_enabled:
                continue
            message = f"  {in_force.report()}"
            if in_force.works:
                context.logger.info(message)
                continue
            context.logger.warn(message)
            print(message, file=sys.stderr)

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify attribution preference is readable (config is optional)."""
        try:
            preference = read_attribution_preference(self._config_dir_for(context))
            if isinstance(preference, UnreadableAttributionPreference):
                warning = preference.warning()
                context.logger.warn(f"  {warning}")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message=warning,
                )
            if preference is not None:
                state = "enabled" if preference else "disabled"
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message=f"Attribution is {state}",
                )
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Attribution not yet configured (optional)",
            )
        except Exception as e:
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Attribution verify skipped: {e}",
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Remove only the nWave-managed credit; preserve user-edited values."""
        try:
            config_dir = self._config_dir_for(context)
            classification = classify_attribution_value(
                config_dir, claude_dir=context.claude_dir
            )
            # ADR-CA-007 DDD-3: clean a legacy nWave-managed settings credit on
            # uninstall, preserving any user-modified value -- same one-shot
            # cleanup used on install, routed through the claude_dir seam.
            migrate_legacy_settings_attribution(
                config_dir, claude_dir=context.claude_dir
            )
            # DDD-3: remove the stale independent attribution PreToolUse entry.
            # Contained so it never blocks uninstall.
            try:
                cleanup_legacy_attribution_hook(claude_dir=context.claude_dir)
            except Exception:
                pass

            config = read_global_config(config_dir)
            config.pop("attribution", None)
            write_global_config(config_dir, config)

            if classification == ATTRIBUTION_USER_MANAGED:
                context.logger.info(_MSG_USER_MODIFIED)
                message = "Attribution credit user-modified; left untouched"
            else:
                message = "Attribution credit removed"
            return PluginResult(
                success=True,
                plugin_name="attribution",
                message=message,
            )
        except Exception as e:
            return PluginResult(
                success=True,
                plugin_name="attribution",
                message=f"Attribution uninstall skipped: {e}",
            )
