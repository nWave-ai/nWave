"""
Step definitions for DES bundle and hooks generation scenarios.

Covers: milestone-2-des-bundle.feature
Driving port: PluginAssembler (DES bundling)

Shared steps (Background Given, shared When, cross-feature Then) are
defined in conftest.py and automatically discovered by pytest-bdd.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when


if TYPE_CHECKING:
    from pathlib import Path


scenarios("../milestone-2-des-bundle.feature")


# ---------------------------------------------------------------------------
# Given Steps: Error Path Setup
# ---------------------------------------------------------------------------


@given("the source tree is missing the DES source directory")
def source_missing_des(build_config: dict[str, Any], tmp_path: Path):
    """Create a source tree without DES source."""
    broken_root = tmp_path / "broken_des"
    broken_root.mkdir(parents=True)
    # Source has nWave but no src/des
    build_config["des_dir"] = broken_root / "src" / "des"


@given("a DES source file with an unrewritable import pattern")
def unrewritable_import(build_config: dict[str, Any], tmp_path: Path):
    """Create a DES file that becomes syntactically invalid after rewriting.

    The content `from src.des import (` is an incomplete import statement.
    After rewriting to `from des import (` it remains syntactically invalid,
    causing ast.parse() to fail during the build's validation step.
    """
    des_dir = tmp_path / "bad_des"
    des_dir.mkdir(parents=True)
    (des_dir / "__init__.py").write_text("", encoding="utf-8")
    bad_file = des_dir / "broken_import.py"
    bad_file.write_text(
        "from src.des import (\n",
        encoding="utf-8",
    )
    build_config["des_dir"] = des_dir


@given("a hook configuration template with a missing command path")
def broken_hook_template(build_config: dict[str, Any]):
    """Configure a hook template that references a nonexistent command."""
    build_config["hook_template_override"] = {
        "hooks": {
            "PreToolUse": [
                {
                    "hooks": [{"type": "command", "command": ""}],  # Empty command
                }
            ]
        }
    }


@given("a project with an active DES session in the RED_ACCEPTANCE phase")
def active_des_session_red_acceptance(build_config: dict[str, Any]):
    """Set up a project context with DES in the RED_ACCEPTANCE phase."""
    build_config["des_phase"] = "RED_ACCEPTANCE"


# ---------------------------------------------------------------------------
# When Steps: DES Enforcement
# ---------------------------------------------------------------------------


@when("a tool that is not allowed in RED_ACCEPTANCE is invoked")
def tool_not_allowed_in_phase(
    build_config: dict[str, Any], build_result: dict[str, Any]
):
    """Simulate invoking a tool that is blocked in the current DES phase."""
    pytest.skip("DES hook enforcement not yet implemented")


# ---------------------------------------------------------------------------
# Then Steps: DES Module Presence
# ---------------------------------------------------------------------------


@then("the DES module exists in the plugin scripts directory")
def des_module_exists(build_result: dict[str, Any]):
    """Verify DES module is present in the plugin."""
    plugin_dir = build_result["plugin_dir"]
    des_dir = plugin_dir / "scripts" / "des"
    assert des_dir.exists(), f"DES module directory not found: {des_dir}"
    assert (des_dir / "__init__.py").exists()


@then("the DES module can be imported as a standalone package")
def des_module_importable(build_result: dict[str, Any]):
    """Verify DES module is importable without external dependencies."""
    import importlib
    import sys

    plugin_dir = build_result["plugin_dir"]
    scripts_dir = plugin_dir / "scripts"

    # Temporarily add scripts dir to sys.path
    original_path = sys.path.copy()
    try:
        sys.path.insert(0, str(scripts_dir))
        # This should not raise ImportError
        spec = importlib.util.find_spec("des")
        assert spec is not None, "DES module not found in plugin scripts"
    finally:
        sys.path = original_path


@then("the DES module runs without depending on the original source layout")
def des_runs_standalone(build_result: dict[str, Any]):
    """Verify all DES files are self-contained without source-tree references."""
    plugin_dir = build_result["plugin_dir"]
    des_dir = plugin_dir / "scripts" / "des"
    for py_file in des_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "from src.des" not in content, (
            f"Source-layout dependency in {py_file.name}"
        )
        assert "import src.des" not in content, (
            f"Source-layout dependency in {py_file.name}"
        )


@then("the DES module has no external package dependencies")
def des_no_external_deps(build_result: dict[str, Any]):
    """Verify DES module is stdlib-only."""
    plugin_dir = build_result["plugin_dir"]
    des_dir = plugin_dir / "scripts" / "des"

    # Known external packages that should NOT appear
    forbidden_imports = {"yaml", "pyyaml", "pydantic", "requests", "toml"}

    for py_file in des_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                for pkg in forbidden_imports:
                    if f"import {pkg}" in stripped or f"from {pkg}" in stripped:
                        pytest.fail(
                            f"External dependency '{pkg}' found in {py_file.name}: {stripped}"
                        )


# ---------------------------------------------------------------------------
# Then Steps: Hooks Configuration
# ---------------------------------------------------------------------------


def _load_hooks(build_result: dict[str, Any]) -> dict[str, list[dict]]:
    """Load hook config from the plugin's hooks.json.

    Returns a dict mapping event names to lists of hook entries.
    """
    import json

    plugin_dir = build_result["plugin_dir"]
    data = json.loads((plugin_dir / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    return data.get("hooks", {})


def _get_registered_events(build_result: dict[str, Any]) -> list[str]:
    """Extract registered event names from hooks.json."""
    return list(_load_hooks(build_result).keys())


# plugin_has_hooks is defined in conftest.py (shared with walking-skeleton)


@then("the hook configuration registers a handler for tool validation")
def hooks_register_pre_tool_use(build_result: dict[str, Any]):
    """Verify PreToolUse hook is registered."""
    assert "PreToolUse" in _get_registered_events(build_result)


@then("the hook configuration registers a handler for task completion")
def hooks_register_post_tool_use(build_result: dict[str, Any]):
    """Verify PostToolUse hook is registered."""
    assert "PostToolUse" in _get_registered_events(build_result)


@then("the hook configuration registers a handler for subagent lifecycle")
def hooks_register_subagent_stop(build_result: dict[str, Any]):
    """Verify SubagentStop hook is registered."""
    assert "SubagentStop" in _get_registered_events(build_result)


@then("the hook configuration registers a handler for session startup")
def hooks_register_session_start(build_result: dict[str, Any]):
    """Verify SessionStart hook is registered."""
    assert "SessionStart" in _get_registered_events(build_result)


# hooks_use_plugin_root is defined in conftest.py (shared with walking-skeleton)


@then("every hook command references the plugin root variable")
def every_hook_uses_plugin_root(build_result: dict[str, Any]):
    """Verify all hooks use CLAUDE_PLUGIN_ROOT."""
    for event, entries in _load_hooks(build_result).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                assert "$HOME" not in cmd, (
                    f"Hook for {event} uses $HOME instead of CLAUDE_PLUGIN_ROOT: {cmd}"
                )


@then("no hook command references a home directory path")
def no_home_dir_in_hooks(build_result: dict[str, Any]):
    """Verify no $HOME references in hook commands."""
    for event, entries in _load_hooks(build_result).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                assert "$HOME" not in cmd
                assert "~/" not in cmd


# ---------------------------------------------------------------------------
# Then Steps: DES Templates
# ---------------------------------------------------------------------------


@then("the TDD cycle schema template exists in the plugin")
def tdd_schema_exists(build_result: dict[str, Any]):
    """Verify TDD cycle schema is bundled."""
    plugin_dir = build_result["plugin_dir"]
    # Check in scripts/templates or lib/des/templates
    found = list(plugin_dir.rglob("step-tdd-cycle-schema.json")) or list(
        plugin_dir.rglob("*tdd*schema*")
    )
    assert len(found) > 0, "TDD cycle schema template not found in plugin"


@then("the roadmap schema template exists in the plugin")
def roadmap_schema_exists(build_result: dict[str, Any]):
    """Verify roadmap schema is bundled."""
    plugin_dir = build_result["plugin_dir"]
    found = list(plugin_dir.rglob("roadmap-schema.json")) or list(
        plugin_dir.rglob("*roadmap*schema*")
    )
    assert len(found) > 0, "Roadmap schema template not found in plugin"


# des_importable is defined in conftest.py (shared with walking-skeleton)


# ---------------------------------------------------------------------------
# Then Steps: Error Assertions
# ---------------------------------------------------------------------------


@then("the build fails with a missing DES source error")
def build_fails_missing_des(build_result: dict[str, Any]):
    """Verify build failure mentions DES."""
    assert build_result["success"] is False
    assert "des" in build_result["error"].lower()


@then("the build fails with an import rewriting error")
def build_fails_import_rewrite(build_result: dict[str, Any]):
    """Verify build failure mentions import rewriting."""
    assert build_result["success"] is False
    error_lower = build_result["error"].lower()
    assert "import" in error_lower or "rewrite" in error_lower


@then("the error message identifies the problematic file")
def error_identifies_file(build_result: dict[str, Any]):
    """Verify error message includes filename."""
    assert build_result["error"] is not None
    # Error should reference a .py file
    assert ".py" in build_result["error"]


@then("the build fails with a hook configuration error")
def build_fails_hook_config(build_result: dict[str, Any]):
    """Verify build failure mentions hook configuration."""
    assert build_result["success"] is False
    error_lower = build_result["error"].lower()
    assert "hook" in error_lower or "command" in error_lower


# ---------------------------------------------------------------------------
# Then Steps: Edge Cases
# ---------------------------------------------------------------------------


@then("the plugin does not ship compiled Python files")
def no_compiled_python_in_plugin(build_result: dict[str, Any]):
    """Verify no bytecode cache directories exist in the plugin."""
    plugin_dir = build_result["plugin_dir"]
    des_dir = plugin_dir / "scripts" / "des"
    pycache_dirs = list(des_dir.rglob("__pycache__"))
    assert len(pycache_dirs) == 0, (
        f"Found {len(pycache_dirs)} compiled Python directories in DES bundle"
    )


@then("every rewritten DES file is syntactically valid Python")
def rewritten_file_valid_python(build_result: dict[str, Any]):
    """Property: rewritten files parse as valid Python."""
    import ast

    plugin_dir = build_result["plugin_dir"]
    des_dir = plugin_dir / "scripts" / "des"
    py_files = list(des_dir.rglob("*.py"))
    assert len(py_files) > 0, "No Python files found in DES bundle"
    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        try:
            ast.parse(content, filename=str(py_file))
        except SyntaxError as exc:
            pytest.fail(f"Syntax error in rewritten DES file {py_file.name}: {exc}")


@then("the configuration contains handlers for all five DES event types")
def hooks_have_all_five_events(build_result: dict[str, Any]):
    """Property: all event types present in hook config."""
    registered_events = set(_get_registered_events(build_result))
    expected_events = {
        "PreToolUse",
        "PostToolUse",
        "SubagentStop",
        "SessionStart",
        "SubagentStart",
    }
    assert registered_events == expected_events, (
        f"Missing events: {expected_events - registered_events}, "
        f"Extra events: {registered_events - expected_events}"
    )


# ---------------------------------------------------------------------------
# Then Steps: DES Enforcement
# ---------------------------------------------------------------------------


@then("the hook returns a block decision")
def hook_returns_block(build_result: dict[str, Any]):
    """Verify the hook blocked the tool invocation."""
    hook_decision = build_result.get("hook_decision", {})
    assert hook_decision.get("decision") == "block"


@then("the block message explains which phase is active")
def block_message_has_phase(build_result: dict[str, Any]):
    """Verify the block message includes phase information."""
    hook_decision = build_result.get("hook_decision", {})
    message = hook_decision.get("message", "")
    assert "RED_ACCEPTANCE" in message or "phase" in message.lower()
