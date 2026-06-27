"""Attribution plugin for install-time commit-credit setup.

Couples commit attribution to per-repo nWave activation (ADR-CA-007): the
un-gateable ``~/.claude/settings.json`` ``attribution.{commit,pr}`` write surface
is RETIRED. Install registers the activation-gated PreToolUse hook (via
``register_attribution_hook``, gated by ``attribution.enabled``) and records the
opt-in preference -- that hook is the sole enforcement. Runs LAST (priority 200)
-- never blocks core installation.
"""

from pathlib import Path

from scripts.install.attribution_utils import (
    ATTRIBUTION_USER_MANAGED,
    classify_attribution_value,
    migrate_legacy_hook,
    migrate_legacy_settings_attribution,
    read_attribution_preference,
    read_global_config,
    register_attribution_hook,
    unregister_attribution_hook,
    write_attribution_preference,
    write_global_config,
)

from .base import InstallationPlugin, InstallContext, PluginResult


_MSG_FIRST_TIME_ENABLED = (
    "nWave attribution enabled. New Claude sessions will carry the nWave credit "
    "via Claude Code settings (restart Claude for it to take effect). "
    "Run `nwave-ai attribution off` to disable."
)
_MSG_USER_MODIFIED = (
    "  Attribution credit was user-modified; left it untouched and "
    "remembered the previous value for later restoration."
)


class AttributionPlugin(InstallationPlugin):
    """Install-time attribution setup via settings.json.

    Priority 200: runs after all core plugins (agents=10, commands=20,
    skills=30, des=50, templates=60, utilities=70).
    """

    def __init__(self, config_dir: Path | None = None):
        super().__init__(name="attribution", priority=200)
        self._config_dir = config_dir or Path.home() / ".nwave"

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
                plugin_name="attribution",
                message=f"Attribution skipped due to error: {e}",
            )

    def _do_install(self, context: InstallContext) -> PluginResult:
        """Core install logic, may raise.

        A new install defaults to opt-in (enabled=True) without prompting.
        Any legacy ``prepare-commit-msg`` hook is dismantled first. The retired
        ``settings.json attribution.{commit,pr}`` write is NOT performed
        (ADR-CA-007 DDD-1/DDD-2): the activation-gated PreToolUse hook is the
        sole enforcement. Install registers that hook (gated by the
        ``attribution.enabled`` preference) and records the opt-in preference.
        """
        migrate_legacy_hook(self._config_dir)
        # ADR-CA-007 DDD-3: machines upgrading off the CA-004 era carry a
        # nWave-written settings.json attribution.{commit,pr} block. Clean it on
        # upgrade (preserving any user-modified value), routing through the
        # claude_dir injection seam so the install target -- not ~/.claude -- is
        # the one touched. Fail-open: this never raises.
        migrate_legacy_settings_attribution(
            self._config_dir, claude_dir=context.claude_dir
        )

        existing = read_attribution_preference(self._config_dir)
        if existing is False:
            return PluginResult(
                success=True,
                plugin_name="attribution",
                message="Attribution preference preserved (disabled)",
            )

        self._ensure_enabled_preference()
        # ADR-CA-006 D7/O-4: the enabled preference gates registration of the
        # PreToolUse commit-attribution hook, coexisting with the DES guards.
        # Belt-and-suspenders: registration must never block install (§Consequences
        # "Both must independently fail-safe"), so its failure is contained here
        # and never corrupts the attribution-credit install message.
        self._register_commit_attribution_hook(context)
        context.logger.info(f"  {_MSG_FIRST_TIME_ENABLED}")
        return PluginResult(
            success=True,
            plugin_name="attribution",
            message=_MSG_FIRST_TIME_ENABLED,
        )

    def _ensure_enabled_preference(self) -> None:
        """Record opt-in preference without clobbering bookkeeping keys."""
        if read_attribution_preference(self._config_dir) is None:
            write_attribution_preference(self._config_dir, enabled=True)

    def _register_commit_attribution_hook(self, context: InstallContext) -> None:
        """Register the PreToolUse commit-attribution hook; never block install.

        The ``attribution.enabled`` preference is load-bearing (ADR-CA-006 O-4):
        it gates registration. A disabled preference makes ``register`` a no-op
        (and removes any stale entry), so the flag honestly drives the hook.
        """
        enabled = read_attribution_preference(self._config_dir) is not False
        try:
            register_attribution_hook(enabled=enabled, claude_dir=context.claude_dir)
        except Exception as e:
            context.logger.warn(f"  Commit-attribution hook registration skipped: {e}")

    def _unregister_commit_attribution_hook(self, context: InstallContext) -> None:
        """Remove the PreToolUse commit-attribution hook; never block uninstall."""
        try:
            unregister_attribution_hook(claude_dir=context.claude_dir)
        except Exception as e:
            context.logger.warn(f"  Commit-attribution hook removal skipped: {e}")

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify attribution preference is readable (config is optional)."""
        try:
            preference = read_attribution_preference(self._config_dir)
            if preference is not None:
                state = "enabled" if preference else "disabled"
                return PluginResult(
                    success=True,
                    plugin_name="attribution",
                    message=f"Attribution is {state}",
                )
            return PluginResult(
                success=True,
                plugin_name="attribution",
                message="Attribution not yet configured (optional)",
            )
        except Exception as e:
            return PluginResult(
                success=True,
                plugin_name="attribution",
                message=f"Attribution verify skipped: {e}",
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Remove only the nWave-managed credit; preserve user-edited values."""
        try:
            classification = classify_attribution_value(
                self._config_dir, claude_dir=context.claude_dir
            )
            # ADR-CA-007 DDD-3: clean a legacy nWave-managed settings credit on
            # uninstall, preserving any user-modified value -- same one-shot
            # cleanup used on install, routed through the claude_dir seam.
            migrate_legacy_settings_attribution(
                self._config_dir, claude_dir=context.claude_dir
            )
            # ADR-CA-006: uninstall removes the commit-attribution hook entry,
            # leaving the DES guards intact. Contained so it never blocks uninstall.
            self._unregister_commit_attribution_hook(context)

            config = read_global_config(self._config_dir)
            config.pop("attribution", None)
            write_global_config(self._config_dir, config)

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
