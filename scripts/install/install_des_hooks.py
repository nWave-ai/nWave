#!/usr/bin/env python3
"""
DES Hook Installer - Manages Claude Code hook lifecycle.

Merges DES hooks into .claude/settings.json, preserving existing hooks.
Uninstalls cleanly without traces or configuration corruption.
"""

import argparse
import json
import sys
from pathlib import Path


class DESHookInstaller:
    """Manages DES hook installation and uninstallation."""

    # Hook configuration templates (Claude Code v2 nested format)
    # Format: {"matcher": "...", "hooks": [{"type": "command", "command": "..."}]}
    # Note: Commands run from project root with PYTHONPATH set for module imports
    DES_PRETOOLUSE_HOOK = {
        "matcher": "Task",
        "hooks": [
            {
                "type": "command",
                "command": "cd {project_root} && PYTHONPATH={project_root} {python_path} -m src.des.adapters.drivers.hooks.claude_code_hook_adapter pre-task",
            }
        ],
    }

    DES_SUBAGENT_STOP_HOOK = {
        "hooks": [
            {
                "type": "command",
                "command": "cd {project_root} && PYTHONPATH={project_root} {python_path} -m src.des.adapters.drivers.hooks.claude_code_hook_adapter subagent-stop",
            }
        ],
    }

    DES_POSTTOOLUSE_HOOK = {
        "matcher": "Task",
        "hooks": [
            {
                "type": "command",
                "command": "cd {project_root} && PYTHONPATH={project_root} {python_path} -m src.des.adapters.drivers.hooks.claude_code_hook_adapter post-tool-use",
            }
        ],
    }

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize installer.

        Args:
            config_dir: Path to .claude directory (default: ~/.claude)
        """
        if config_dir is None:
            config_dir = Path.home() / ".claude"
        self.config_dir = Path(config_dir)
        self.settings_file = self.config_dir / "settings.json"

    def install(self) -> bool:
        """
        Install DES hooks into Claude Code configuration.

        Merges DES hooks into existing settings.json, preserving other hooks.
        Creates settings.json if it doesn't exist.
        Idempotent - always removes existing DES hooks before adding new ones
        to ensure latest format is used and prevent duplicates.

        Returns:
            bool: True if installation succeeded, False otherwise
        """
        try:
            config = self._load_config()
            self._ensure_hooks_structure(config)

            # Always remove existing DES hooks before adding new ones
            # to ensure idempotency and latest format
            if self._is_installed(config):
                print("DES hooks already installed - updating to latest format")
                self._remove_des_hooks(config)

            self._add_des_hooks(config)
            self._save_config(config)

            print("DES hooks installed successfully")
            print("Restart Claude Code session to activate hooks")
            return True

        except Exception as e:
            print(f"Installation failed: {e}", file=sys.stderr)
            return False

    def uninstall(self) -> bool:
        """
        Uninstall DES hooks from Claude Code configuration.

        Removes only DES hook entries, preserving all other hooks.
        Handles missing settings.json gracefully (no error).

        Returns:
            bool: True if uninstallation succeeded, False otherwise
        """
        try:
            if not self.settings_file.exists():
                print("DES hooks not installed (settings.json not found)")
                return True

            config = self._load_config()
            self._remove_des_hooks(config)
            self._save_config(config)

            print("DES hooks uninstalled successfully")
            return True

        except Exception as e:
            print(f"Uninstallation failed: {e}", file=sys.stderr)
            return False

    def status(self) -> bool:
        """
        Check DES hook installation status.

        Returns:
            bool: True if hooks are installed, False otherwise
        """
        try:
            if not self.settings_file.exists():
                print("DES hooks are not installed")
                return True

            config = self._load_config()
            installed = self._is_installed(config)

            if installed:
                print("DES hooks are installed")
            else:
                print("DES hooks are not installed")

            return True

        except Exception as e:
            print(f"Status check failed: {e}", file=sys.stderr)
            return False

    def _load_config(self) -> dict:
        """
        Load configuration from settings.json.

        Returns:
            dict: Configuration dictionary (empty if file doesn't exist)
        """
        if not self.settings_file.exists():
            return {}

        try:
            with open(self.settings_file, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.settings_file}: {e}")

    def _save_config(self, config: dict):
        """
        Save configuration to settings.json.

        Args:
            config: Configuration dictionary to save
        """
        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Write with proper formatting
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            f.write("\n")  # Add trailing newline

    def _is_installed(self, config: dict) -> bool:
        """
        Check if DES hooks are already installed.

        Returns True if EITHER PreToolUse or SubagentStop has a DES hook.
        This handles cases where only partial hooks exist (e.g., old format).
        The install process will clean up and reinstall both properly.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if DES hooks are present
        """
        if "hooks" not in config:
            return False

        # Check for PreToolUse hook
        pre_hooks = config["hooks"].get("PreToolUse", [])
        has_pre = any(self._is_des_hook_entry(h) for h in pre_hooks)

        # Check for SubagentStop hook
        stop_hooks = config["hooks"].get("SubagentStop", [])
        has_stop = any(self._is_des_hook_entry(h) for h in stop_hooks)

        # Check for PostToolUse hook
        post_hooks = config["hooks"].get("PostToolUse", [])
        has_post = any(self._is_des_hook_entry(h) for h in post_hooks)

        return has_pre or has_stop or has_post

    def _is_des_hook_entry(self, hook_entry: dict) -> bool:
        """
        Check if a hook entry is a DES hook.

        Supports both old flat format and new nested format:
        - Old flat: {"matcher": "Task", "command": "...claude_code_hook_adapter..."}
        - New nested: {"matcher": "Task", "hooks": [{"type": "command", "command": "...claude_code_hook_adapter..."}]}

        Args:
            hook_entry: Hook entry dictionary from settings JSON

        Returns:
            bool: True if entry is a DES hook
        """
        # Check old flat format
        if "claude_code_hook_adapter" in hook_entry.get("command", ""):
            return True
        # Check new nested format
        for h in hook_entry.get("hooks", []):
            if "claude_code_hook_adapter" in h.get("command", ""):
                return True
        return False

    def _ensure_hooks_structure(self, config: dict):
        """
        Ensure hooks structure exists in config.

        Args:
            config: Configuration dictionary to update
        """
        if "hooks" not in config:
            config["hooks"] = {}
        if "PreToolUse" not in config["hooks"]:
            config["hooks"]["PreToolUse"] = []
        if "SubagentStop" not in config["hooks"]:
            config["hooks"]["SubagentStop"] = []
        if "PostToolUse" not in config["hooks"]:
            config["hooks"]["PostToolUse"] = []

    def _add_des_hooks(self, config: dict):
        """
        Add DES hooks to configuration.

        Args:
            config: Configuration dictionary to update
        """
        # Get absolute path to project root (parent of scripts/install/)
        project_root = str(Path(__file__).resolve().parent.parent.parent)

        # Substitution map for all placeholders
        substitutions = {
            "{project_root}": project_root,
            "{python_path}": sys.executable,
        }

        # Create hook configs with placeholders substituted
        pre_hook = self._substitute_placeholders(
            self.DES_PRETOOLUSE_HOOK, substitutions
        )
        stop_hook = self._substitute_placeholders(
            self.DES_SUBAGENT_STOP_HOOK, substitutions
        )
        post_hook = self._substitute_placeholders(
            self.DES_POSTTOOLUSE_HOOK, substitutions
        )

        config["hooks"]["PreToolUse"].append(pre_hook)
        config["hooks"]["SubagentStop"].append(stop_hook)
        config["hooks"]["PostToolUse"].append(post_hook)

    def _substitute_placeholders(self, hook_config: dict, substitutions: dict) -> dict:
        """
        Recursively substitute placeholders in hook configuration.

        Args:
            hook_config: Hook configuration dictionary
            substitutions: Map of placeholder → value (e.g. {"{project_root}": "/path"})

        Returns:
            dict: Hook configuration with placeholders substituted
        """
        import copy

        result = copy.deepcopy(hook_config)

        def substitute_in_dict(d):
            for key, value in d.items():
                if isinstance(value, str):
                    for placeholder, replacement in substitutions.items():
                        value = value.replace(placeholder, replacement)
                    d[key] = value
                elif isinstance(value, dict):
                    substitute_in_dict(value)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            substitute_in_dict(item)
                        elif isinstance(item, str):
                            for placeholder, replacement in substitutions.items():
                                item = item.replace(placeholder, replacement)
                            value[i] = item

        substitute_in_dict(result)
        return result

    def _remove_des_hooks(self, config: dict):
        """
        Remove DES hooks from configuration.

        Args:
            config: Configuration dictionary to update
        """
        if "hooks" not in config:
            return

        if "PreToolUse" in config["hooks"]:
            config["hooks"]["PreToolUse"] = [
                h
                for h in config["hooks"]["PreToolUse"]
                if not self._is_des_hook_entry(h)
            ]

        if "SubagentStop" in config["hooks"]:
            config["hooks"]["SubagentStop"] = [
                h
                for h in config["hooks"]["SubagentStop"]
                if not self._is_des_hook_entry(h)
            ]

        if "PostToolUse" in config["hooks"]:
            config["hooks"]["PostToolUse"] = [
                h
                for h in config["hooks"]["PostToolUse"]
                if not self._is_des_hook_entry(h)
            ]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Install or uninstall DES hooks for Claude Code"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install", action="store_true", help="Install DES hooks")
    group.add_argument("--uninstall", action="store_true", help="Uninstall DES hooks")
    group.add_argument(
        "--status", action="store_true", help="Check installation status"
    )
    parser.add_argument(
        "--config-dir", type=Path, help="Path to .claude directory (default: ~/.claude)"
    )

    args = parser.parse_args()

    installer = DESHookInstaller(config_dir=args.config_dir)

    if args.install:
        success = installer.install()
    elif args.uninstall:
        success = installer.uninstall()
    else:  # status
        success = installer.status()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
