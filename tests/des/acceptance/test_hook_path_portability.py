"""
Acceptance Test: Hook Path Portability Across Machines

BUG: DES hooks in settings.json contained hardcoded absolute paths:
  - Python interpreter: /mnt/c/.../project/.venv/bin/python3
  - Lib path: /home/<user>/.claude/lib/python

Since ~/.claude/settings.json is shared across machines (synced directory),
these machine-specific paths caused "Task Hook Error" on every other machine.

FIX: Hook commands must use portable shell constructs:
  - $HOME/.claude/lib/python for PYTHONPATH (shell-expanded per machine)
  - python3 (system PATH) or $HOME-based venv path for interpreter

REGRESSION GUARD: These tests ensure the bug never returns.
"""

import json
import logging
import re
from pathlib import Path

import pytest

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_logger() -> logging.Logger:
    logger = logging.getLogger("test.hook_portability")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def project_root() -> Path:
    current = Path(__file__).resolve()
    return current.parents[3]


@pytest.fixture
def install_context(tmp_path, project_root, test_logger) -> InstallContext:
    """Create InstallContext simulating a fresh installation."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )


def _install_hooks(install_context: InstallContext) -> dict:
    """Run DES hook installation and return the resulting settings."""
    plugin = DESPlugin()
    result = plugin._install_des_hooks(install_context)
    assert result.success, f"Hook installation failed: {result.message}"

    settings_file = install_context.claude_dir / "settings.json"
    return json.loads(settings_file.read_text())


def _extract_all_hook_commands(config: dict) -> list[str]:
    """Extract all command strings from all hook entries."""
    commands = []
    for event_hooks in config.get("hooks", {}).values():
        for entry in event_hooks:
            for h in entry.get("hooks", []):
                if "command" in h:
                    commands.append(h["command"])
    return commands


# =============================================================================
# BUG REGRESSION: No hardcoded absolute paths in hook commands
# =============================================================================


class TestNoHardcodedPaths:
    """Hook commands must not contain machine-specific absolute paths."""

    def test_no_hardcoded_python_venv_path(self, install_context):
        """
        GIVEN DES hooks are installed
        WHEN examining hook command strings
        THEN no command contains a project-specific .venv/bin/python path

        BUG: Previously used sys.executable which resolved to
             a project-specific .venv/bin/python3 path
        """
        config = _install_hooks(install_context)
        commands = _extract_all_hook_commands(config)

        for cmd in commands:
            assert ".venv/bin/" not in cmd, (
                f"Hook command contains hardcoded venv path: {cmd}"
            )
            assert ".venv\\bin\\" not in cmd, (
                f"Hook command contains hardcoded venv path (Windows): {cmd}"
            )

    def test_no_hardcoded_home_directory(self, install_context):
        """
        GIVEN DES hooks are installed
        WHEN examining hook command strings
        THEN no command contains a hardcoded /home/<user> path

        BUG: Previously used context.claude_dir which resolved to
             /home/<user>/.claude/lib/python
        """
        config = _install_hooks(install_context)
        commands = _extract_all_hook_commands(config)

        # Match /home/<user>/ or /Users/<user>/ patterns
        home_pattern = re.compile(r"/(?:home|Users)/\w+/")

        for cmd in commands:
            # The tmp_path-based test dir will have /tmp/ paths;
            # we check the PYTHONPATH part specifically
            pythonpath_match = re.search(r"PYTHONPATH=(\S+)", cmd)
            if pythonpath_match:
                pythonpath = pythonpath_match.group(1)
                assert not home_pattern.match(pythonpath), (
                    f"PYTHONPATH contains hardcoded home directory: {pythonpath}"
                )

    def test_pythonpath_uses_home_variable(self, install_context):
        """
        GIVEN DES hooks are installed
        WHEN examining PYTHONPATH in hook commands
        THEN PYTHONPATH uses $HOME for shell expansion

        This ensures the path resolves correctly on every machine.
        """
        config = _install_hooks(install_context)
        commands = _extract_all_hook_commands(config)

        for cmd in commands:
            pythonpath_match = re.search(r"PYTHONPATH=(\S+)", cmd)
            if pythonpath_match:
                pythonpath = pythonpath_match.group(1)
                assert "$HOME" in pythonpath, (
                    f"PYTHONPATH should use $HOME for portability, got: {pythonpath}"
                )

    def test_python_interpreter_is_portable(self, install_context):
        """
        GIVEN DES hooks are installed
        WHEN examining the Python interpreter in hook commands
        THEN it uses 'python3' or a $HOME-based path (not a project-specific venv)
        """
        config = _install_hooks(install_context)
        commands = _extract_all_hook_commands(config)

        for cmd in commands:
            # Strip shell fast-path prefix for Write/Edit guards
            effective_cmd = cmd.split(";")[-1].strip() if ";" in cmd else cmd
            # Extract the Python interpreter (after PYTHONPATH=... )
            parts = effective_cmd.split()
            # Find the python invocation (after PYTHONPATH=X)
            python_part = None
            for i, part in enumerate(parts):
                if part.startswith("PYTHONPATH="):
                    continue
                # First non-env-var part is the interpreter
                python_part = part
                break

            if python_part:
                is_portable = (
                    python_part == "python3"
                    or python_part.startswith("$HOME")
                    or python_part.startswith("${HOME}")
                )
                assert is_portable, (
                    f"Python interpreter is not portable: {python_part}\n"
                    f"Full command: {cmd}"
                )


# =============================================================================
# Write/Edit guard hooks must be installed
# =============================================================================


class TestWriteEditGuardsInstalled:
    """Write/Edit session guard hooks must be present after installation."""

    def test_write_hook_installed(self, install_context):
        """
        GIVEN DES hooks are installed
        WHEN examining PreToolUse hooks
        THEN a Write matcher hook exists
        """
        config = _install_hooks(install_context)
        matchers = [h.get("matcher") for h in config["hooks"]["PreToolUse"]]
        assert "Write" in matchers, f"Write guard hook not found. Matchers: {matchers}"

    def test_edit_hook_installed(self, install_context):
        """
        GIVEN DES hooks are installed
        WHEN examining PreToolUse hooks
        THEN an Edit matcher hook exists
        """
        config = _install_hooks(install_context)
        matchers = [h.get("matcher") for h in config["hooks"]["PreToolUse"]]
        assert "Edit" in matchers, f"Edit guard hook not found. Matchers: {matchers}"

    def test_write_hook_has_fast_path(self, install_context):
        """
        GIVEN Write guard hook is installed
        WHEN examining its command
        THEN it includes shell fast-path (test -f ... || exit 0)
        """
        config = _install_hooks(install_context)
        write_hook = next(
            h for h in config["hooks"]["PreToolUse"] if h.get("matcher") == "Write"
        )
        cmd = write_hook["hooks"][0]["command"]
        assert "test -f" in cmd, f"Write hook missing fast-path: {cmd}"
        assert "exit 0" in cmd, f"Write hook missing fast-path exit: {cmd}"

    def test_edit_hook_has_fast_path(self, install_context):
        """
        GIVEN Edit guard hook is installed
        WHEN examining its command
        THEN it includes shell fast-path (test -f ... || exit 0)
        """
        config = _install_hooks(install_context)
        edit_hook = next(
            h for h in config["hooks"]["PreToolUse"] if h.get("matcher") == "Edit"
        )
        cmd = edit_hook["hooks"][0]["command"]
        assert "test -f" in cmd, f"Edit hook missing fast-path: {cmd}"
        assert "exit 0" in cmd, f"Edit hook missing fast-path exit: {cmd}"


# =============================================================================
# Idempotency with new hooks
# =============================================================================


class TestHookInstallIdempotency:
    """Installing hooks twice must not create duplicates."""

    def test_double_install_no_duplicates(self, install_context):
        """
        GIVEN DES hooks are installed once
        WHEN hooks are installed a second time
        THEN no duplicate hooks exist
        AND all 3 PreToolUse hooks present (Task, Write, Edit)
        """
        plugin = DESPlugin()

        # Install twice
        plugin._install_des_hooks(install_context)
        plugin._install_des_hooks(install_context)

        settings_file = install_context.claude_dir / "settings.json"
        config = json.loads(settings_file.read_text())

        # Exactly 3 PreToolUse hooks
        pre_hooks = config["hooks"]["PreToolUse"]
        matchers = [h.get("matcher") for h in pre_hooks]
        assert matchers.count("Task") == 1, f"Duplicate Task hooks: {matchers}"
        assert matchers.count("Write") == 1, f"Duplicate Write hooks: {matchers}"
        assert matchers.count("Edit") == 1, f"Duplicate Edit hooks: {matchers}"

        # Exactly 1 SubagentStop and 1 PostToolUse
        assert len(config["hooks"]["SubagentStop"]) == 1
        assert len(config["hooks"]["PostToolUse"]) == 1
