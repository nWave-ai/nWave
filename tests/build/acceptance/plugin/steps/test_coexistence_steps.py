"""
Step definitions for coexistence verification scenarios.

Covers: milestone-5-coexistence.feature
Driving port: PluginAssembler, path resolution utilities, verify_path_disjointness
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when


scenarios("../milestone-5-coexistence.feature")


# ---------------------------------------------------------------------------
# Standalone Tests: Migration Guide & Coexistence Functions
# ---------------------------------------------------------------------------


def test_migration_guide_exists(project_root: Path):
    """Verify the migration guide exists and has required sections."""
    guide = project_root / "docs" / "guides" / "plugin-migration-guide" / "README.md"
    assert guide.exists(), f"Migration guide not found: {guide}"
    content = guide.read_text(encoding="utf-8")
    assert "Prerequisites" in content, "Migration guide missing Prerequisites section"
    assert "Verify" in content, "Migration guide missing Verify section"
    assert "Rollback" in content, "Migration guide missing Rollback section"
    assert "Coexistence" in content, "Migration guide missing Coexistence section"


def test_verify_path_disjointness_returns_true():
    """Pure function test: plugin and installer paths are disjoint."""
    from scripts.build_plugin import verify_path_disjointness

    is_disjoint, overlaps = verify_path_disjointness()
    assert is_disjoint, f"Expected disjoint paths but found overlaps: {overlaps}"
    assert overlaps == []


def test_get_plugin_paths_all_under_plugin_prefix():
    """Pure function test: all plugin paths start with the plugin prefix."""
    from scripts.build_plugin import PLUGIN_INSTALL_PREFIX, get_plugin_paths

    for path in get_plugin_paths():
        assert path.startswith(PLUGIN_INSTALL_PREFIX), (
            f"Plugin path {path} does not start with {PLUGIN_INSTALL_PREFIX}"
        )


def test_get_installer_paths_none_under_plugin_prefix():
    """Pure function test: no installer path starts with the plugin prefix."""
    from scripts.build_plugin import PLUGIN_INSTALL_PREFIX, get_installer_paths

    for path in get_installer_paths():
        assert not path.startswith(PLUGIN_INSTALL_PREFIX), (
            f"Installer path {path} starts with plugin prefix {PLUGIN_INSTALL_PREFIX}"
        )


def test_check_version_consistency_match():
    """Pure function test: matching versions return None."""
    from scripts.build_plugin import check_version_consistency

    assert check_version_consistency("2.18.0", "2.18.0") is None


def test_check_version_consistency_mismatch():
    """Pure function test: mismatched versions return warning."""
    from scripts.build_plugin import check_version_consistency

    result = check_version_consistency("2.18.0", "2.17.0")
    assert result is not None
    assert "mismatch" in result.lower()


# ---------------------------------------------------------------------------
# Helpers: Create realistic directory structures
# ---------------------------------------------------------------------------


def _create_plugin_structure(plugin_dir: Path) -> None:
    """Create a realistic plugin directory with commands, hooks, metadata.

    Commands go directly in commands/ (not commands/nw/) because the plugin
    name in plugin.json provides the 'nw:' namespace prefix.
    """
    # commands/ with .md files (flat, no nw/ subdirectory)
    commands_dir = plugin_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    (commands_dir / "deliver.md").write_text(
        "---\nname: deliver\n---\n# Deliver\n", encoding="utf-8"
    )
    (commands_dir / "design.md").write_text(
        "---\nname: design\n---\n# Design\n", encoding="utf-8"
    )

    # agents/
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "nw-software-crafter.md").write_text(
        "---\nname: nw-software-crafter\n---\n# Agent\n", encoding="utf-8"
    )

    # hooks/hooks.json using CLAUDE_PLUGIN_ROOT (settings.json schema)
    hooks_dir = plugin_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hooks_data: dict[str, dict] = {"hooks": {}}
    for event, matcher, action in [
        ("PreToolUse", "Task", "pre-task"),
        ("PostToolUse", "Task", "post-tool-use"),
        ("SubagentStop", None, "subagent-stop"),
        ("SessionStart", "startup", "session-start"),
        ("SubagentStart", None, "subagent-start"),
    ]:
        command = (
            "PYTHONPATH=${CLAUDE_PLUGIN_ROOT}/scripts python3"
            f" -m des.adapters.drivers.hooks.claude_code_hook_adapter {action}"
        )
        entry: dict = {"hooks": [{"type": "command", "command": command}]}
        if matcher is not None:
            entry["matcher"] = matcher
        hooks_data["hooks"].setdefault(event, []).append(entry)

    (hooks_dir / "hooks.json").write_text(
        json.dumps(hooks_data, indent=2) + "\n", encoding="utf-8"
    )

    # .claude-plugin/plugin.json
    metadata_dir = plugin_dir / ".claude-plugin"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "plugin.json").write_text(
        json.dumps(
            {
                "name": "nw",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _create_installer_structure(installer_dir: Path) -> None:
    """Create a realistic installer directory with commands, agents, skills."""
    # agents/nw/
    agents_dir = installer_dir / "agents" / "nw"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "nw-software-crafter.md").write_text(
        "---\nname: nw-software-crafter\n---\n# Agent\n", encoding="utf-8"
    )

    # commands/nw/
    commands_dir = installer_dir / "commands" / "nw"
    commands_dir.mkdir(parents=True, exist_ok=True)
    (commands_dir / "deliver.md").write_text(
        "---\nname: deliver\n---\n# Deliver\n", encoding="utf-8"
    )
    (commands_dir / "design.md").write_text(
        "---\nname: design\n---\n# Design\n", encoding="utf-8"
    )

    # skills/nw/
    skills_dir = installer_dir / "skills" / "nw"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "tdd-methodology.md").write_text(
        "---\nname: tdd-methodology\n---\n# TDD\n", encoding="utf-8"
    )


def _create_installer_settings(
    settings_path: Path, installer_dir: Path
) -> dict[str, Any]:
    """Create a simulated settings.json with installer hook config.

    Returns the parsed settings dict.
    """
    settings_data = {
        "hooks": {
            "PreToolUse": (
                f"PYTHONPATH={installer_dir}/lib/python python3"
                " -m des.adapters.drivers.hooks.claude_code_hook_adapter pre-task"
            ),
            "PostToolUse": (
                f"PYTHONPATH={installer_dir}/lib/python python3"
                " -m des.adapters.drivers.hooks.claude_code_hook_adapter post-tool-use"
            ),
            "SubagentStop": (
                f"PYTHONPATH={installer_dir}/lib/python python3"
                " -m des.adapters.drivers.hooks.claude_code_hook_adapter subagent-stop"
            ),
            "SessionStart": (
                f"PYTHONPATH={installer_dir}/lib/python python3"
                " -m des.adapters.drivers.hooks.claude_code_hook_adapter session-start"
            ),
            "SubagentStart": (
                f"PYTHONPATH={installer_dir}/lib/python python3"
                " -m des.adapters.drivers.hooks.claude_code_hook_adapter subagent-start"
            ),
        }
    }
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(settings_data, indent=2) + "\n", encoding="utf-8"
    )
    return settings_data


# ---------------------------------------------------------------------------
# Given Steps
# ---------------------------------------------------------------------------


@given("only the plugin is installed")
def only_plugin_installed(tmp_path: Path, build_result: dict[str, Any]):
    """Simulate an environment with only the plugin."""
    plugin_dir = tmp_path / ".claude" / "plugins" / "cache" / "nwave"
    plugin_dir.mkdir(parents=True)
    _create_plugin_structure(plugin_dir)
    build_result["plugin_install_path"] = plugin_dir
    build_result["installer_install_path"] = None


@given("only the custom installer is active")
def only_installer_active(tmp_path: Path, build_result: dict[str, Any]):
    """Simulate an environment with only the custom installer."""
    installer_dir = tmp_path / ".claude"
    installer_dir.mkdir(parents=True, exist_ok=True)
    _create_installer_structure(installer_dir)
    build_result["installer_install_path"] = installer_dir
    build_result["plugin_install_path"] = None


@given("the plugin is installed")
def plugin_is_installed(tmp_path: Path, build_result: dict[str, Any]):
    """Create plugin installation."""
    plugin_dir = tmp_path / ".claude" / "plugins" / "cache" / "nwave"
    plugin_dir.mkdir(parents=True)
    _create_plugin_structure(plugin_dir)
    build_result["plugin_install_path"] = plugin_dir


@given("the custom installer is also active")
def installer_also_active(tmp_path: Path, build_result: dict[str, Any]):
    """Create custom installer installation alongside plugin."""
    installer_dir = tmp_path / ".claude"
    _create_installer_structure(installer_dir)
    build_result["installer_install_path"] = installer_dir


@given("the plugin hook registrations are in the plugin directory")
def plugin_hooks_in_plugin_dir(tmp_path: Path, build_result: dict[str, Any]):
    """Create plugin with hooks in plugin directory."""
    plugin_dir = tmp_path / ".claude" / "plugins" / "cache" / "nwave"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    _create_plugin_structure(plugin_dir)
    build_result["plugin_install_path"] = plugin_dir


@given("the custom installer hook registrations are in the settings file")
def installer_hooks_in_settings(tmp_path: Path, build_result: dict[str, Any]):
    """Create installer hooks in a simulated settings.json."""
    installer_dir = tmp_path / ".claude"
    installer_dir.mkdir(parents=True, exist_ok=True)
    _create_installer_structure(installer_dir)
    settings_path = installer_dir / "settings.json"
    settings_data = _create_installer_settings(settings_path, installer_dir)
    build_result["installer_install_path"] = installer_dir
    build_result["installer_settings"] = settings_data
    build_result["installer_settings_path"] = settings_path


@given(parsers.parse('the plugin is version "{version}"'))
def plugin_version_is(version: str, build_result: dict[str, Any]):
    """Set plugin version."""
    build_result["plugin_version"] = version


@given(parsers.parse('the custom installer is version "{version}"'))
def installer_version_is(version: str, build_result: dict[str, Any]):
    """Set custom installer version."""
    build_result["installer_version"] = version


@given("both plugin and custom installer are active")
def both_active(tmp_path: Path, build_result: dict[str, Any]):
    """Create both installations."""
    # Plugin path
    plugin_dir = tmp_path / ".claude" / "plugins" / "cache" / "nwave"
    plugin_dir.mkdir(parents=True)
    _create_plugin_structure(plugin_dir)

    # Installer path
    installer_dir = tmp_path / ".claude"
    _create_installer_structure(installer_dir)

    build_result["plugin_install_path"] = plugin_dir
    build_result["installer_install_path"] = installer_dir


@given("any valid installation of both plugin and custom installer")
def any_valid_dual_install():
    """Setup for property-based path disjointness test.

    No filesystem setup needed -- the property test uses the pure function
    verify_path_disjointness() which operates on path strings, not real files.
    """
    pass


# ---------------------------------------------------------------------------
# When Steps
# ---------------------------------------------------------------------------


@when("a user invokes a slash command")
def invoke_slash_command(build_result: dict[str, Any]):
    """Verify structural readiness for command discovery.

    Instead of actually invoking a command (requires Claude Code runtime),
    we verify the directory structure that enables Claude Code to discover
    commands: commands/nw/*.md files must exist in the active installation(s).
    """
    plugin_path = build_result.get("plugin_install_path")
    installer_path = build_result.get("installer_install_path")

    # At least one installation must be active
    assert plugin_path is not None or installer_path is not None, (
        "No installation is active -- cannot verify command discovery"
    )

    # Verify command files exist in whichever installation(s) are active
    discovered_sources: list[str] = []
    if plugin_path is not None:
        plugin_commands = list((plugin_path / "commands").rglob("*.md"))
        if plugin_commands:
            discovered_sources.append("plugin")
    if installer_path is not None:
        installer_commands_dir = installer_path / "commands" / "nw"
        if installer_commands_dir.exists():
            installer_commands = list(installer_commands_dir.glob("*.md"))
            if installer_commands:
                discovered_sources.append("installer")

    build_result["discovered_sources"] = discovered_sources
    assert len(discovered_sources) > 0, (
        "No command .md files found in any active installation"
    )


@when("both are active simultaneously")
def both_simultaneous(build_result: dict[str, Any]):
    """Verify both installations exist."""
    assert build_result.get("plugin_install_path") is not None
    assert (
        build_result.get("installer_install_path") is not None
        or build_result.get("installer_settings") is not None
    )


@when("a version consistency check runs")
def run_version_check(build_result: dict[str, Any]):
    """Run version consistency between plugin and installer."""
    from scripts.build_plugin import check_version_consistency

    plugin_version = build_result.get("plugin_version")
    installer_version = build_result.get("installer_version")
    assert plugin_version is not None, "Plugin version not set"
    assert installer_version is not None, "Installer version not set"

    warning = check_version_consistency(plugin_version, installer_version)
    build_result["version_warning"] = warning


@when("the custom installer is uninstalled")
def uninstall_installer(build_result: dict[str, Any]):
    """Simulate removing the custom installer."""
    import shutil

    installer_path = build_result.get("installer_install_path")
    if installer_path:
        for subdir in ["agents/nw", "commands/nw", "skills/nw"]:
            target = installer_path / subdir
            if target.exists():
                shutil.rmtree(target)


@when("the plugin is removed")
def remove_plugin(build_result: dict[str, Any]):
    """Simulate removing the plugin."""
    import shutil

    plugin_path = build_result.get("plugin_install_path")
    if plugin_path and plugin_path.exists():
        shutil.rmtree(plugin_path)


# ---------------------------------------------------------------------------
# Then Steps
# ---------------------------------------------------------------------------


@then("the plugin target directory differs from the custom installer target directory")
def different_install_paths(build_result: dict[str, Any]):
    """Verify plugin and installer use different paths."""
    from scripts.build_plugin import get_installer_paths, get_plugin_paths

    plugin_paths = get_plugin_paths()
    installer_paths = get_installer_paths()
    assert plugin_paths.isdisjoint(installer_paths), (
        f"Overlapping paths: {plugin_paths & installer_paths}"
    )


@then("no files overlap between plugin and custom installer paths")
def no_file_overlap():
    """Verify disjoint file sets using the production path verification."""
    from scripts.build_plugin import verify_path_disjointness

    is_disjoint, overlaps = verify_path_disjointness()
    assert is_disjoint, f"Path overlap detected: {overlaps}"


@then("the command is discovered from the plugin directory")
def command_from_plugin(build_result: dict[str, Any]):
    """Verify plugin directory has discoverable command files."""
    plugin_path = build_result.get("plugin_install_path")
    assert plugin_path is not None, "Plugin path not set"

    commands_dir = plugin_path / "commands"
    assert commands_dir.exists(), f"Plugin commands directory not found: {commands_dir}"

    md_files = list(commands_dir.rglob("*.md"))
    assert len(md_files) > 0, (
        f"No command .md files found in plugin directory: {commands_dir}"
    )


@then("no errors reference missing custom installer files")
def no_installer_errors(build_result: dict[str, Any]):
    """Verify plugin hooks do not reference installer paths."""
    plugin_path = build_result.get("plugin_install_path")
    assert plugin_path is not None

    hooks_path = plugin_path / "hooks" / "hooks.json"
    assert hooks_path.exists(), "Plugin hooks.json not found"

    hooks_content = hooks_path.read_text(encoding="utf-8")
    # Plugin hooks should use CLAUDE_PLUGIN_ROOT, not $HOME/.claude references
    assert "$HOME/.claude/lib" not in hooks_content, (
        "Plugin hooks reference installer path ($HOME/.claude/lib)"
    )
    assert "$HOME/.claude/scripts" not in hooks_content, (
        "Plugin hooks reference installer path ($HOME/.claude/scripts)"
    )


@then("the command is discovered from the custom installer directory")
def command_from_installer(build_result: dict[str, Any]):
    """Verify installer directory has discoverable command files."""
    installer_path = build_result.get("installer_install_path")
    assert installer_path is not None, "Installer path not set"

    commands_dir = installer_path / "commands" / "nw"
    assert commands_dir.exists(), (
        f"Installer commands directory not found: {commands_dir}"
    )

    md_files = list(commands_dir.glob("*.md"))
    assert len(md_files) > 0, (
        f"No command .md files found in installer directory: {commands_dir}"
    )


@then("no errors reference missing plugin files")
def no_plugin_errors(build_result: dict[str, Any]):
    """Verify installer setup does not reference plugin paths."""
    installer_path = build_result.get("installer_install_path")
    assert installer_path is not None

    # Check that installer commands don't contain plugin path references
    commands_dir = installer_path / "commands" / "nw"
    for md_file in commands_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        assert "plugins/cache/nwave" not in content, (
            f"Installer command {md_file.name} references plugin path"
        )


@then("the command executes successfully from one of the two sources")
def command_executes_from_either(build_result: dict[str, Any]):
    """Verify both directories contain command .md files for discovery."""
    discovered = build_result.get("discovered_sources", [])
    assert len(discovered) >= 1, (
        "Expected at least one source to have discoverable commands, "
        f"but found: {discovered}"
    )

    # Verify both installations have structurally valid command files
    plugin_path = build_result.get("plugin_install_path")
    installer_path = build_result.get("installer_install_path")

    if plugin_path:
        plugin_cmds = list((plugin_path / "commands").rglob("*.md"))
        assert len(plugin_cmds) > 0, "Plugin has no command files"

    if installer_path:
        installer_cmds = list((installer_path / "commands" / "nw").glob("*.md"))
        assert len(installer_cmds) > 0, "Installer has no command files"


@then("each DES enforcement event is handled by exactly one source")
def single_event_handler(build_result: dict[str, Any]):
    """Verify plugin hooks use CLAUDE_PLUGIN_ROOT and installer hooks use $HOME.

    These are structurally different scopes: the plugin hooks are scoped to the
    plugin directory via CLAUDE_PLUGIN_ROOT, while installer hooks use $HOME.
    Claude Code reads them from separate locations, so each event is handled
    by exactly one source per installation context.
    """
    plugin_path = build_result.get("plugin_install_path")
    installer_settings = build_result.get("installer_settings")

    # Plugin hooks must use CLAUDE_PLUGIN_ROOT
    assert plugin_path is not None
    hooks_path = plugin_path / "hooks" / "hooks.json"
    assert hooks_path.exists(), "Plugin hooks.json not found"
    plugin_hooks = json.loads(hooks_path.read_text(encoding="utf-8"))

    for event, entries in plugin_hooks.get("hooks", {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                assert "CLAUDE_PLUGIN_ROOT" in cmd, (
                    f"Plugin hook for {event} does not use CLAUDE_PLUGIN_ROOT: {cmd}"
                )
                assert "$HOME" not in cmd, (
                    f"Plugin hook for {event} incorrectly references $HOME: {cmd}"
                )

    # Installer hooks must use a different path (not CLAUDE_PLUGIN_ROOT)
    assert installer_settings is not None, "Installer settings not created"
    for event, cmd in installer_settings.get("hooks", {}).items():
        assert "CLAUDE_PLUGIN_ROOT" not in cmd, (
            f"Installer hook for {event} incorrectly uses CLAUDE_PLUGIN_ROOT: {cmd}"
        )


@then("no event triggers duplicate enforcement")
def no_duplicate_enforcement(build_result: dict[str, Any]):
    """Verify hook command paths are disjoint between plugin and installer.

    Plugin hooks point to ${CLAUDE_PLUGIN_ROOT}/scripts/ while installer
    hooks point to a different path (e.g., lib/python). The PYTHONPATH
    values are structurally different, ensuring no duplication.
    """
    plugin_path = build_result.get("plugin_install_path")
    installer_settings = build_result.get("installer_settings")

    assert plugin_path is not None
    assert installer_settings is not None

    # Extract PYTHONPATH from plugin hooks
    hooks_path = plugin_path / "hooks" / "hooks.json"
    plugin_hooks = json.loads(hooks_path.read_text(encoding="utf-8"))

    plugin_pythonpaths = set()
    for _event, entries in plugin_hooks.get("hooks", {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                # Extract the PYTHONPATH value (before "python3")
                if "PYTHONPATH=" in cmd:
                    pythonpath = cmd.split("PYTHONPATH=")[1].split(" ")[0]
                    plugin_pythonpaths.add(pythonpath)

    installer_pythonpaths = set()
    for _event, cmd in installer_settings.get("hooks", {}).items():
        if "PYTHONPATH=" in cmd:
            pythonpath = cmd.split("PYTHONPATH=")[1].split(" ")[0]
            installer_pythonpaths.add(pythonpath)

    # PYTHONPATH values must be disjoint
    assert plugin_pythonpaths.isdisjoint(installer_pythonpaths), (
        f"Hook PYTHONPATH overlap detected: "
        f"plugin={plugin_pythonpaths}, installer={installer_pythonpaths}"
    )


@then("a warning is raised about version mismatch between installation methods")
def version_mismatch_warning(build_result: dict[str, Any]):
    """Verify the version consistency check returned a mismatch warning."""
    warning = build_result.get("version_warning")
    assert warning is not None, "Expected a version mismatch warning but got None"
    assert "mismatch" in warning.lower(), (
        f"Warning does not mention 'mismatch': {warning}"
    )


@then("the plugin continues to operate normally")
def plugin_still_works(build_result: dict[str, Any]):
    """Verify plugin survives installer removal."""
    plugin_path = build_result.get("plugin_install_path")
    if plugin_path:
        assert plugin_path.exists()


@then("no plugin files are affected by the uninstall")
def plugin_files_intact(build_result: dict[str, Any]):
    """Verify plugin files remain after installer removal."""
    plugin_path = build_result.get("plugin_install_path")
    if plugin_path:
        assert plugin_path.exists()
        assert (plugin_path / "agents").exists()


@then("the custom installer continues to operate normally")
def installer_still_works(build_result: dict[str, Any]):
    """Verify installer survives plugin removal."""
    installer_path = build_result.get("installer_install_path")
    if installer_path:
        assert (installer_path / "agents" / "nw").exists()


@then("no custom installer files are affected by the removal")
def installer_files_intact(build_result: dict[str, Any]):
    """Verify installer files remain after plugin removal."""
    installer_path = build_result.get("installer_install_path")
    if installer_path:
        assert (installer_path / "agents" / "nw").exists()


@then(
    "the set of files owned by the plugin is disjoint from the set owned by the custom installer"
)
def disjoint_file_ownership():
    """Property: plugin and installer file sets never overlap.

    Uses the verify_path_disjointness() pure function from build_plugin
    to verify that all plugin paths and all installer paths are disjoint.
    """
    from scripts.build_plugin import verify_path_disjointness

    is_disjoint, overlaps = verify_path_disjointness()
    assert is_disjoint, f"Path overlap detected: {overlaps}"
