"""
Common Step Definitions.

This module contains step definitions that are shared across multiple
feature files and domains.

Domain: Shared/Common Steps
"""

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, then, when


# -----------------------------------------------------------------------------
# Given Steps: Common Preconditions
# -----------------------------------------------------------------------------


@given("the nWave project root is available")
def nwave_project_root(project_root: Path):
    """Verify nWave project root is available."""
    assert project_root.exists(), f"Project root not found: {project_root}"
    # Verify it's actually the nWave project
    assert (project_root / "nWave").exists() or (project_root / "scripts").exists()


@given(parsers.parse('the Claude config directory is "{path}"'))
def claude_config_dir_set(path: str):
    """Set Claude config directory path."""
    pytest.claude_config_dir = path


@given("a clean test installation directory exists")
def clean_test_dir_exists(clean_test_directory: Path):
    """Verify clean test directory exists."""
    assert clean_test_directory.exists()
    # Directory should be empty or minimal (just .claude structure)


@given("a clean installation directory exists")
def clean_install_dir_exists(clean_test_directory: Path):
    """Alias for clean test directory."""
    assert clean_test_directory.exists()


@given(parsers.parse('agent source files are available at "{path}"'))
def agent_source_available(path: str, project_root: Path):
    """Verify agent source files are available."""
    source_path = project_root / path
    if not source_path.exists():
        pytest.skip(f"Agent source not found: {source_path}")


@given(
    parsers.parse("agent source directory contains at least {count:d} agent .md files")
)
def agent_source_has_files(count: int, project_root: Path):
    """Verify agent source has minimum files."""
    agents_dir = project_root / "nWave" / "agents" / "nw"
    if agents_dir.exists():
        agent_files = list(agents_dir.glob("*.md"))
        assert len(agent_files) >= count, (
            f"Expected >= {count} agent files, found {len(agent_files)}"
        )
    else:
        pytest.skip(f"Agent directory not found: {agents_dir}")


@given(parsers.parse("{plugin_name} is registered"))
def plugin_is_registered(plugin_name: str, plugin_registry):
    """Register a plugin with the registry."""
    pass


@given(parsers.parse('agent source files do NOT exist at "{path}"'))
def agent_source_not_exist(path: str, project_root: Path):
    """Verify agent source files do NOT exist (for error testing)."""
    source_path = project_root / path
    if source_path.exists():
        pytest.skip(
            f"Agent source exists - cannot test missing scenario: {source_path}"
        )


# -----------------------------------------------------------------------------
# When Steps: Common Actions
# -----------------------------------------------------------------------------


@when("I create an InstallContext with test directory path")
def create_install_context_with_test_dir(install_context):
    """Create InstallContext with test directory."""
    pytest.install_context = install_context


# -----------------------------------------------------------------------------
# Then Steps: Common Assertions
# -----------------------------------------------------------------------------


@then(parsers.parse("no errors are reported"))
def no_errors_reported():
    """Verify no errors were reported during operation."""
    if hasattr(pytest, "install_error") and pytest.install_error:
        pytest.fail(f"Error was reported: {pytest.install_error}")
    if hasattr(pytest, "install_result") and pytest.install_result:
        if not pytest.install_result.success:
            pytest.fail(f"Operation failed: {pytest.install_result.message}")


# -----------------------------------------------------------------------------
# Scenario Outlines: Parameterized Steps
# -----------------------------------------------------------------------------


@given(parsers.parse('plugin "{plugin_name}" with priority {priority:d}'))
def plugin_with_priority(plugin_name: str, priority: int):
    """Define plugin with specific priority."""
    if not hasattr(pytest, "plugin_priorities"):
        pytest.plugin_priorities = {}
    pytest.plugin_priorities[plugin_name] = priority


@given(parsers.parse('plugin "{plugin_name}" depending on {deps}'))
def plugin_depending_on(plugin_name: str, deps: str):
    """Define plugin with dependencies."""
    dependencies = eval(deps) if deps != "[]" else []
    if not hasattr(pytest, "plugin_dependencies"):
        pytest.plugin_dependencies = {}
    pytest.plugin_dependencies[plugin_name] = dependencies
