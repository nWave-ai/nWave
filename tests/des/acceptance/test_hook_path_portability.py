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
def install_context(
    tmp_path, project_root, test_logger, monkeypatch
) -> InstallContext:
    """Create InstallContext simulating a fresh DEFAULT-HOME installation.

    The portability assertions in this file (e.g. "PYTHONPATH uses $HOME")
    only apply when the install target is the user's default `~/.claude/`.
    Non-default targets (`nwave-ai install --target ~/.claude-nwave`) emit
    absolute paths by design — see ADR-002 of the per-project-install
    feature.

    To exercise the default-home code path under tmp_path, we redirect
    `Path.home()` to tmp_path so `Path.home() / ".claude" == claude_dir`.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
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

    def test_python_interpreter_is_not_project_venv(self, install_context):
        """
        GIVEN DES hooks are installed
        WHEN examining the Python interpreter in hook commands
        THEN it does NOT use a project-specific .venv/bin/ path

        The interpreter should be one of:
        - $HOME-based path (pipx venv, portable across machines)
        - Absolute system path like /usr/bin/python3 (system install)
        - bare 'python3' (PATH lookup)

        Any of these is acceptable because they reference the Python that
        has nWave's dependencies installed. What is NOT acceptable is a
        project-local .venv path which would break on other machines.
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
            for part in parts:
                if part.startswith("PYTHONPATH="):
                    continue
                python_part = part
                break

            if python_part:
                assert ".venv/bin/" not in python_part, (
                    f"Python interpreter uses project-local venv: {python_part}\n"
                    f"Full command: {cmd}"
                )
                assert ".venv\\bin\\" not in python_part, (
                    f"Python interpreter uses project-local venv (Windows): {python_part}\n"
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
        AND all 3 PreToolUse hooks present (Agent, Write, Edit)
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
        assert matchers.count("Agent") == 1, f"Duplicate Agent hooks: {matchers}"
        assert matchers.count("Write") == 1, f"Duplicate Write hooks: {matchers}"
        assert matchers.count("Edit") == 1, f"Duplicate Edit hooks: {matchers}"

        # Exactly 2 SubagentStop (subagent-stop + deliver-progress) and 1 PostToolUse
        assert len(config["hooks"]["SubagentStop"]) == 2
        assert len(config["hooks"]["PostToolUse"]) == 1


# =============================================================================
# RUNTIME GUARD: Hook module is actually executable (Category A -> runtime layer)
#
# The mock-based tests above verify the generated command STRINGS have the
# correct shape. This class answers the orthogonal question:
#   "Does the DES hook module that those strings reference actually execute?"
#
# Deletion test: if des.adapters.drivers.hooks.claude_code_hook_adapter were
# removed or renamed, ALL the string-pattern tests above would still PASS
# (they test the template text, not the module), but the tests below FAIL
# immediately -- catching the regression before users hit "Task Hook Error".
# =============================================================================


class TestHookModuleExecutable:
    """Runtime guard: the DES hook module referenced in commands is importable."""

    def test_hook_module_importable_via_installed_pythonpath(self, install_context):
        """
        GIVEN DES hooks are installed and PYTHONPATH=$HOME/.claude/lib/python is set
        WHEN the hook module is invoked as python3 -m des.adapters.drivers.hooks...
        THEN the module launches without ImportError or ModuleNotFoundError

        Runtime counterpart to test_pythonpath_uses_home_variable.
        Answers: does the adapter module actually exist at that path?

        Container-level coverage (real PATH resolution with $HOME expansion) is
        owned by tests/e2e/test_fresh_install.py. This test uses the real
        installed lib path from the developer/CI environment.
        """
        import os
        import subprocess
        import sys

        home = str(Path.home())
        lib_path = home + "/.claude/lib/python"

        if not Path(lib_path).exists():
            pytest.skip(
                f"DES not installed at {lib_path} -- "
                "container-level coverage owned by tests/e2e/test_fresh_install.py"
            )

        env = {**os.environ, "PYTHONPATH": lib_path}
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "des.adapters.drivers.hooks.claude_code_hook_adapter",
                "pre-tool-use",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            input="{}",
        )

        assert "ModuleNotFoundError" not in result.stderr, (
            f"Hook module import failed -- DES adapter unreachable at "
            f"PYTHONPATH={lib_path}\nstderr: {result.stderr}"
        )
        assert "ImportError" not in result.stderr, (
            f"Hook module has broken imports at {lib_path}\nstderr: {result.stderr}"
        )

    def test_hook_command_module_path_matches_installed_module(self, install_context):
        """
        GIVEN DES hooks are installed
        WHEN the hook command is extracted and the module path parsed
        THEN the module path references a file that exists in the installed lib

        Bridges mock tests (verify command strings) and runtime tests (verify
        module exists): confirms string in settings.json and file on disk
        refer to the same module.
        """
        home = str(Path.home())
        lib_path = home + "/.claude/lib/python"

        if not Path(lib_path).exists():
            pytest.skip(
                f"DES not installed at {lib_path} -- "
                "container-level coverage owned by tests/e2e/test_fresh_install.py"
            )

        config = _install_hooks(install_context)
        commands = _extract_all_hook_commands(config)

        module_names = set()
        for cmd in commands:
            m = re.search(r"-m\s+([\w.]+)", cmd)
            if m:
                module_names.add(m.group(1))

        assert module_names, "No '-m <module>' found in any hook command"

        for module_name in module_names:
            module_rel = module_name.replace(".", "/") + ".py"
            module_path = Path(lib_path) / module_rel
            assert module_path.exists(), (
                f"Hook command references module '{module_name}' "
                f"but file not found at {module_path}.\n"
                f"settings.json and installed DES are out of sync."
            )
