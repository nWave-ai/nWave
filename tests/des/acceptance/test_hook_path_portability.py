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

State-delta migration summary
------------------------------
CONVERTED (8 tests) — assert_state_delta + implicit-unchanged invariant:
  - test_no_hardcoded_python_venv_path: universe declares all hook event
    slots + env + permissions; set_to(after[slot]) for each hook slot while
    implicit-unchanged guards permissions; post-delta assertion scans commands
    for forbidden .venv/bin/ substring.
  - test_no_hardcoded_home_directory: same universe; post-delta assertion
    checks PYTHONPATH segments for hardcoded /home/<user>/ or /Users/<user>/.
  - test_pythonpath_uses_home_variable: same universe; post-delta assertion
    verifies PYTHONPATH uses $HOME variable for shell expansion.
  - test_python_interpreter_is_not_project_venv: same universe; post-delta
    assertion confirms Python interpreter part avoids .venv/bin/ paths.
  - test_write_hook_installed: universe guards all hook slots; containing()
    on hooks.PreToolUse JSON verifies Write matcher is present.
  - test_edit_hook_installed: same universe; containing() on
    hooks.PreToolUse JSON verifies Edit matcher is present.
  - test_write_hook_has_fast_path: same universe; containing() on
    hooks.PreToolUse JSON verifies test -f / exit 0 fast-path for Write.
  - test_edit_hook_has_fast_path: same universe; containing() on
    hooks.PreToolUse JSON verifies test -f / exit 0 fast-path for Edit.

KEPT as-is (3 tests) — no state-delta benefit:
  - test_double_install_no_duplicates: count-based check (matchers.count == 1,
    len == 2); idempotent_after targets PATH prepend semantics, not list
    deduplication; direct assertions are clearer and sufficient.
  - test_hook_module_importable_via_installed_pythonpath: subprocess runtime
    contract; environment-dependent (skipped when DES not installed); no
    state mutation to track.
  - test_hook_command_module_path_matches_installed_module: filesystem check
    against real installed lib; single assertion per module; environment-
    dependent; no installer state mutation involved.

Hidden mutations found: NONE detected across all 8 converted tests.
The implicit-unchanged invariant on "permissions" was clean — _install_des_hooks()
does not silently touch that slot. Explicit confirmation that the permissions block
is excluded from hook installation writes is now part of the test contract.
"""

import json
import logging
import re
from pathlib import Path

import pytest
from nwave_ai.state_delta import (
    assert_state_delta,
    containing,
    set_to,
)

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


# ---------------------------------------------------------------------------
# State-delta helpers
# ---------------------------------------------------------------------------

#: Per-event-type hook slots tracked in the portability universe.
_HOOK_EVENT_SLOTS: frozenset[str] = frozenset(
    [
        "hooks.PreToolUse",
        "hooks.PostToolUse",
        "hooks.SubagentStop",
        "hooks.SessionStart",
        "hooks.SubagentStart",
    ]
)

#: Full universe for hook-portability assertions.
#: Includes env slot written by _install_des_hooks and the permissions block.
HOOKS_SETTINGS_UNIVERSE: frozenset[str] = _HOOK_EVENT_SLOTS | frozenset(
    ["env.SLASH_COMMAND_TOOL_CHAR_BUDGET", "permissions"]
)


def _hooks_settings_state(settings_file: Path) -> dict[str, object]:
    """Return a flat state dict for hooks + env slots in settings.json.

    Slots:
      "hooks.<Event>"                      — JSON-serialized hook entry list
      "env.SLASH_COMMAND_TOOL_CHAR_BUDGET" — string value (empty str if absent)
      "permissions"                        — JSON-serialized permissions block

    Returns an empty-state dict when settings.json does not yet exist.
    """
    if not settings_file.exists():
        return {
            **{slot: json.dumps([]) for slot in _HOOK_EVENT_SLOTS},
            "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": "",
            "permissions": json.dumps({}),
        }
    config = json.loads(settings_file.read_text(encoding="utf-8"))
    hooks_block = config.get("hooks", {})
    env_block = config.get("env", {})
    return {
        "hooks.PreToolUse": json.dumps(
            hooks_block.get("PreToolUse", []), sort_keys=True
        ),
        "hooks.PostToolUse": json.dumps(
            hooks_block.get("PostToolUse", []), sort_keys=True
        ),
        "hooks.SubagentStop": json.dumps(
            hooks_block.get("SubagentStop", []), sort_keys=True
        ),
        "hooks.SessionStart": json.dumps(
            hooks_block.get("SessionStart", []), sort_keys=True
        ),
        "hooks.SubagentStart": json.dumps(
            hooks_block.get("SubagentStart", []), sort_keys=True
        ),
        "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": env_block.get(
            "SLASH_COMMAND_TOOL_CHAR_BUDGET", ""
        ),
        "permissions": json.dumps(config.get("permissions", {}), sort_keys=True),
    }


def _install_hooks_with_delta(
    install_context: InstallContext,
) -> tuple[dict[str, object], dict[str, object], dict]:
    """Install hooks, capture before/after state and parsed config.

    Returns:
        (before_state, after_state, config_dict)
    """
    settings_file = install_context.claude_dir / "settings.json"
    before = _hooks_settings_state(settings_file)
    config = _install_hooks(install_context)
    after = _hooks_settings_state(settings_file)
    return before, after, config


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
             AND no unexpected settings.json slot is mutated (implicit-unchanged
             on permissions enforces _install_des_hooks writes only hook + env slots)

        BUG: Previously used sys.executable which resolved to
             a project-specific .venv/bin/python3 path
        """
        before, after, config = _install_hooks_with_delta(install_context)

        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.PreToolUse": set_to(after["hooks.PreToolUse"]),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
                # implicit-unchanged: "permissions" must not change
            },
        )

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
             AND the full hook universe remains within expected slots
             (implicit-unchanged on permissions)

        BUG: Previously used context.claude_dir which resolved to
             /home/<user>/.claude/lib/python
        """
        before, after, config = _install_hooks_with_delta(install_context)

        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.PreToolUse": set_to(after["hooks.PreToolUse"]),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
                # implicit-unchanged: "permissions" must not change
            },
        )

        # Match /home/<user>/ or /Users/<user>/ patterns
        home_pattern = re.compile(r"/(?:home|Users)/\w+/")
        commands = _extract_all_hook_commands(config)

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
             AND the full hook universe is declared (implicit-unchanged on permissions)

        This ensures the path resolves correctly on every machine.
        """
        before, after, config = _install_hooks_with_delta(install_context)

        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.PreToolUse": set_to(after["hooks.PreToolUse"]),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
                # implicit-unchanged: "permissions" must not change
            },
        )

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
             AND the full hook universe is declared (implicit-unchanged on permissions)

        The interpreter should be one of:
        - $HOME-based path (pipx venv, portable across machines)
        - Absolute system path like /usr/bin/python3 (system install)
        - bare 'python3' (PATH lookup)

        Any of these is acceptable because they reference the Python that
        has nWave's dependencies installed. What is NOT acceptable is a
        project-local .venv path which would break on other machines.
        """
        before, after, config = _install_hooks_with_delta(install_context)

        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.PreToolUse": set_to(after["hooks.PreToolUse"]),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
                # implicit-unchanged: "permissions" must not change
            },
        )

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
        THEN a Write matcher hook exists in settings.json
             AND the full hook universe is declared (implicit-unchanged on permissions)
        """
        before, after, _config = _install_hooks_with_delta(install_context)

        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.PreToolUse": containing('"Write"'),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
                # implicit-unchanged: "permissions" must not change
            },
        )

    def test_edit_hook_installed(self, install_context):
        """
        GIVEN DES hooks are installed
        WHEN examining PreToolUse hooks
        THEN an Edit matcher hook exists in settings.json
             AND the full hook universe is declared (implicit-unchanged on permissions)
        """
        before, after, _config = _install_hooks_with_delta(install_context)

        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.PreToolUse": containing('"Edit"'),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
                # implicit-unchanged: "permissions" must not change
            },
        )

    def test_write_hook_has_fast_path(self, install_context):
        """
        GIVEN Write guard hook is installed
        WHEN examining its command
        THEN it includes shell fast-path (test -f ... || exit 0)
             AND the full hook universe is declared (implicit-unchanged on permissions)
        """
        before, after, _config = _install_hooks_with_delta(install_context)

        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.PreToolUse": containing("test -f"),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
                # implicit-unchanged: "permissions" must not change
            },
        )

        # Domain assertion: specifically the Write hook has exit 0 fast-path
        config = json.loads((install_context.claude_dir / "settings.json").read_text())
        write_hook = next(
            h for h in config["hooks"]["PreToolUse"] if h.get("matcher") == "Write"
        )
        cmd = write_hook["hooks"][0]["command"]
        assert "exit 0" in cmd, f"Write hook missing fast-path exit: {cmd}"

    def test_edit_hook_has_fast_path(self, install_context):
        """
        GIVEN Edit guard hook is installed
        WHEN examining its command
        THEN it includes shell fast-path (test -f ... || exit 0)
             AND the full hook universe is declared (implicit-unchanged on permissions)
        """
        before, after, _config = _install_hooks_with_delta(install_context)

        assert_state_delta(
            before=before,
            after=after,
            universe=set(HOOKS_SETTINGS_UNIVERSE),
            expected={
                "hooks.PreToolUse": containing("test -f"),
                "hooks.PostToolUse": set_to(after["hooks.PostToolUse"]),
                "hooks.SubagentStop": set_to(after["hooks.SubagentStop"]),
                "hooks.SessionStart": set_to(after["hooks.SessionStart"]),
                "hooks.SubagentStart": set_to(after["hooks.SubagentStart"]),
                "env.SLASH_COMMAND_TOOL_CHAR_BUDGET": set_to(
                    after["env.SLASH_COMMAND_TOOL_CHAR_BUDGET"]
                ),
                # implicit-unchanged: "permissions" must not change
            },
        )

        # Domain assertion: specifically the Edit hook has exit 0 fast-path
        config = json.loads((install_context.claude_dir / "settings.json").read_text())
        edit_hook = next(
            h for h in config["hooks"]["PreToolUse"] if h.get("matcher") == "Edit"
        )
        cmd = edit_hook["hooks"][0]["command"]
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

        KEPT as-is: count-based assertion (matchers.count == 1, list len == N).
        idempotent_after targets PATH-prepend semantics; for list-deduplication
        the direct count assertions are clearer and sufficient.
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

        KEPT as-is: subprocess runtime contract; environment-dependent
        (skipped when DES not installed); no installer state mutation to track.
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

        KEPT as-is: filesystem check against real installed lib; single
        assertion per module; environment-dependent (skipped when DES not
        installed); no installer state mutation to track.
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
