"""Plugin for wiring nWave DES hooks into Codex CLI.

Codex CLI hooks are configured via ~/.codex/hooks.json (user-level) or the
[hooks] section of ~/.codex/config.toml. This plugin writes a hooks.json
entry that registers the existing Python DES adapter as a PreToolUse hook.

Walking-skeleton scope:
- Writes a single PreToolUse hook entry to ~/.codex/hooks.json
- The hook points to the same Python DES adapter used by Claude Code
- The hook logs to stderr to confirm it fires (no TDD enforcement yet)
- No PostToolUse / Stop hooks in this slice (deferred)

Hook protocol is identical to Claude Code: JSON on stdin, decision on stdout.
This means the existing claude_code_hook_adapter.py is theoretically reusable
without modification -- empirical validation is out of scope for this slice.

A manifest (.nwave-des-manifest.json) tracks the installed hook config for
clean uninstallation.
"""

import json
import os
import shutil as _shutil
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.install_paths import (
    resolve_des_lib_path_for_spawn,
    resolve_python_command_for_spawn,
)


_HOOKS_FILENAME = "hooks.json"
_MANIFEST_FILENAME = ".nwave-des-manifest.json"

# Event key used by Codex (verified against developers.openai.com/codex/hooks
# and codex-rs/hooks/schema/generated/pre-tool-use.command.*.schema.json).
_PRE_TOOL_USE_EVENT = "PreToolUse"


def _codex_config_dir() -> Path:
    """Return the Codex CLI configuration directory.

    Returns:
        Path to ~/.codex/ (or $CODEX_HOME if set)
    """
    override = os.environ.get("CODEX_HOME")
    return Path(override) if override else Path.home() / ".codex"


def _build_hook_entry(python_path: str, pythonpath: str) -> dict:
    """Build the Codex PreToolUse hook entry for the DES adapter.

    The hook entry follows the Codex hooks.json format:
    - matcher: regex that matches tool names to intercept
    - hooks: list of command entries with type, command, timeout

    Matcher is narrowed to ``^Bash$|^apply_patch$`` — the two tools
    Codex actually emits in PreToolUse per
    developers.openai.com/codex/hooks (DDD-6, verified by DDD-8 spike Q6):
    - Bash: shell command execution
    - apply_patch: file edits performed by Codex

    The pre-FM-3 matcher (``^Task$|^Bash$``) referenced ``Task`` — a
    Claude-Code-internal tool name Codex never emits — by analogy with the
    Claude Code plugin. FM-3 root cause: mirrored a peer without reading
    the Codex docs. ``Edit|Write`` aliases for apply_patch and ``mcp__*``
    matchers are deferred to a later slice per DESIGN.

    Read / Grep / Glob and other read-only tools are excluded to avoid
    unnecessary overhead on every file access. Using ``.*`` (all tools)
    was the walking-skeleton default; this matcher is the
    production-grade narrow form.

    Args:
        python_path: Absolute path to the Python executable
        pythonpath: Path to add to PYTHONPATH for DES imports

    Returns:
        Dict representing a single hooks.json entry
    """
    # DDD-4 (FM-2 closure): the shared DES adapter (hook_router.py) requires
    # an argv positional event token (one of pre-tool-use / subagent-stop /
    # post-tool-use / ...). Codex does NOT inject the event name as argv —
    # only `cwd` is set; the configured `command` runs as-is. The token must
    # therefore be baked into the command string at install time. Without it,
    # the adapter exits 1 with "Missing command argument" on every fire.
    hook_command = (
        f"PYTHONPATH={pythonpath} {python_path} -m "
        "des.adapters.drivers.hooks.claude_code_hook_adapter "
        "pre-tool-use"
    )
    return {
        "matcher": "^Bash$|^apply_patch$",
        "hooks": [
            {
                "type": "command",
                "command": hook_command,
                "timeout": 30,
                "statusMessage": "nWave DES validation...",
            }
        ],
    }


def _empty_doc() -> dict:
    """Return a fresh, empty event-keyed hooks document."""
    return {"hooks": {}}


def _read_hooks(hooks_path: Path) -> dict:
    """Read existing hooks.json content or return an empty event-keyed doc.

    Codex expects an event-keyed object root per
    developers.openai.com/codex/hooks (DDD-1, verified by SPIKE 2026-05-13):

        {"hooks": {"PreToolUse": [<matcher-group>, ...], ...}}

    Legacy top-level arrays produced by pre-FM-1 installs are auto-migrated
    into ``hooks.PreToolUse`` so re-install is idempotent without leaving the
    file in a Codex-incompatible shape.

    Args:
        hooks_path: Path to ~/.codex/hooks.json

    Returns:
        Event-keyed hooks document (always a dict with a 'hooks' dict).
    """
    if not hooks_path.exists():
        return _empty_doc()
    try:
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        # Malformed JSON: rebuild from scratch rather than silently keep bytes.
        return _empty_doc()

    # Legacy top-level array → migrate into PreToolUse.
    if isinstance(data, list):
        return {"hooks": {_PRE_TOOL_USE_EVENT: list(data)}}

    if isinstance(data, dict):
        hooks_obj = data.get("hooks")
        if not isinstance(hooks_obj, dict):
            # Unexpected shape (e.g. {"hooks": [...]}); normalise.
            data = _empty_doc()
        return data

    # Any other top-level type (number, string, null): rebuild.
    return _empty_doc()


def _is_nwave_matcher_group(entry: dict) -> bool:
    """True if the matcher group contains a nWave DES handler."""
    if not isinstance(entry, dict):
        return False
    return any(
        "claude_code_hook_adapter" in h.get("command", "")
        for h in entry.get("hooks", [])
        if isinstance(h, dict)
    )


def _remove_nwave_hooks(doc: dict) -> dict:
    """Strip any previously installed nWave DES matcher groups from the doc.

    Operates on the event-keyed document shape. Identifies nWave entries by
    the presence of ``claude_code_hook_adapter`` in any handler's command
    string. Non-nWave matcher groups (user-authored) are preserved as-is, on
    every event key.

    Args:
        doc: Event-keyed hooks document (``{"hooks": {<event>: [...], ...}}``)

    Returns:
        New document with nWave matcher groups filtered out of every event
        list. Empty event lists are kept (callers may re-append).
    """
    if not isinstance(doc, dict) or not isinstance(doc.get("hooks"), dict):
        return _empty_doc()
    cleaned_events: dict = {}
    for event_name, entries in doc["hooks"].items():
        if not isinstance(entries, list):
            cleaned_events[event_name] = entries
            continue
        cleaned_events[event_name] = [
            entry for entry in entries if not _is_nwave_matcher_group(entry)
        ]
    return {"hooks": cleaned_events}


class CodexDESPlugin(InstallationPlugin):
    """Plugin for wiring nWave DES hooks into Codex CLI."""

    def __init__(self) -> None:
        """Initialize Codex DES plugin with name, priority, and dependencies."""
        super().__init__(name="codex-des", priority=55)
        self.dependencies = ["des", "codex-skills"]

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        """Validate Codex CLI and DES prerequisites.

        Checks:
        1. ~/.codex/ directory exists OR `codex` binary in PATH (skip if neither)
        2. DES Python module is installed at ~/.claude/lib/python/des/

        Args:
            context: InstallContext with claude_dir

        Returns:
            PluginResult with success=True to skip/proceed, success=False on errors
        """
        codex_dir = _codex_config_dir()
        codex_binary = _shutil.which("codex") is not None

        if not codex_dir.exists() and not codex_binary:
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Codex CLI not detected, skipping DES hook installation",
            )

        des_module = context.claude_dir / "lib" / "python" / "des"
        if not des_module.exists():
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=(
                    f"DES Python module not found at {des_module}. Install DES first."
                ),
                errors=["DES module must be installed before Codex DES hooks"],
            )

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="Codex DES prerequisites validated",
        )

    def install(self, context: InstallContext) -> PluginResult:
        """Install DES PreToolUse hook entry into ~/.codex/hooks.json.

        Steps:
        1. Validate prerequisites (skip if Codex not detected)
        2. Resolve Python path and PYTHONPATH for the hook command
        3. Load existing hooks.json (or start with empty list)
        4. Remove any prior nWave DES entries (idempotent reinstall)
        5. Append new hook entry
        6. Write hooks.json and manifest

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            prereq = self.validate_prerequisites(context)
            if not prereq.success:
                return prereq
            if "skip" in prereq.message.lower():
                return prereq

            codex_dir = _codex_config_dir()
            codex_dir.mkdir(parents=True, exist_ok=True)

            python_path = resolve_python_command_for_spawn()
            pythonpath = resolve_des_lib_path_for_spawn()

            hooks_path = codex_dir / _HOOKS_FILENAME
            doc = _remove_nwave_hooks(_read_hooks(hooks_path))
            doc.setdefault("hooks", {})
            pretool_list = doc["hooks"].setdefault(_PRE_TOOL_USE_EVENT, [])
            new_entry = _build_hook_entry(python_path, pythonpath)
            pretool_list.append(new_entry)

            hooks_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

            manifest = {
                "hooks_file": str(hooks_path),
                "python_path": python_path,
                "pythonpath": pythonpath,
            }
            manifest_path = codex_dir / _MANIFEST_FILENAME
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )

            context.logger.info(f"  Codex DES hook installed in {hooks_path}")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Codex DES hook installed successfully",
                installed_files=[hooks_path],
            )

        except Exception as e:
            context.logger.error(f"  Failed to install Codex DES hook: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex DES hook installation failed: {e!s}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Remove nWave DES hook entries from ~/.codex/hooks.json.

        Reads hooks.json, strips only nWave DES entries (identified by
        'claude_code_hook_adapter' in the command), and rewrites the file.
        User-created hook entries are preserved. The manifest is also removed.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            codex_dir = _codex_config_dir()

            hooks_path = codex_dir / _HOOKS_FILENAME
            if hooks_path.exists():
                existing = _read_hooks(hooks_path)
                cleaned = _remove_nwave_hooks(existing)
                events = cleaned.get("hooks", {}) if isinstance(cleaned, dict) else {}
                any_user_entries = any(
                    isinstance(v, list) and len(v) > 0 for v in events.values()
                )
                if any_user_entries:
                    hooks_path.write_text(
                        json.dumps(cleaned, indent=2) + "\n", encoding="utf-8"
                    )
                else:
                    hooks_path.unlink()
                context.logger.info(f"  Removed nWave DES hook from {hooks_path}")

            manifest_path = codex_dir / _MANIFEST_FILENAME
            if manifest_path.exists():
                manifest_path.unlink()
                context.logger.info(f"  Removed Codex DES manifest: {manifest_path}")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Codex DES hook uninstalled",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex DES hook uninstall failed: {e}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify the DES hook is present in ~/.codex/hooks.json.

        Checks:
        1. hooks.json exists and contains a nWave DES entry
        2. Manifest exists

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            codex_dir = _codex_config_dir()

            codex_binary = _shutil.which("codex") is not None
            if not codex_dir.exists() and not codex_binary:
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="Codex CLI not detected, verification skipped",
                )

            errors: list[str] = []

            hooks_path = codex_dir / _HOOKS_FILENAME
            if not hooks_path.exists():
                errors.append(f"hooks.json not found: {hooks_path}")
            else:
                doc = _read_hooks(hooks_path)
                pretool = (
                    doc.get("hooks", {}).get(_PRE_TOOL_USE_EVENT, [])
                    if isinstance(doc, dict)
                    else []
                )
                nwave_entries = [e for e in pretool if _is_nwave_matcher_group(e)]
                if not nwave_entries:
                    errors.append("No nWave DES hook entry found in hooks.json")

            manifest_path = codex_dir / _MANIFEST_FILENAME
            if not manifest_path.exists():
                errors.append(f"DES manifest not found: {manifest_path}")

            if errors:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Codex DES hook verification failed",
                    errors=errors,
                )

            context.logger.info("  Codex DES hook verified")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Codex DES hook verification passed",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex DES hook verification failed: {e}",
                errors=[str(e)],
            )
