"""
Pytest-BDD Configuration for Plugin Build Acceptance Tests.

Provides fixtures and shared BDD step definitions for the plugin build
pipeline acceptance tests. All fixtures use real filesystem operations
for the build pipeline and produce temporary directories for plugin output.

Shared step definitions (Background steps, common When steps, cross-feature
Then steps) live here so they are automatically discovered by pytest-bdd
across all test modules in this directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when


# ---------------------------------------------------------------------------
# Fixtures: Source Tree
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    current = Path(__file__).resolve()
    # Navigate from tests/build/acceptance/plugin/conftest.py to project root
    return current.parents[4]


@pytest.fixture
def nwave_source_tree(project_root: Path) -> Path:
    """Return the nWave framework source directory."""
    source = project_root / "nWave"
    assert source.exists(), f"nWave source tree not found: {source}"
    return source


@pytest.fixture
def des_source_tree(project_root: Path) -> Path:
    """Return the DES source directory."""
    source = project_root / "src" / "des"
    assert source.exists(), f"DES source tree not found: {source}"
    return source


@pytest.fixture
def pyproject_path(project_root: Path) -> Path:
    """Return the path to pyproject.toml."""
    path = project_root / "pyproject.toml"
    assert path.exists(), f"pyproject.toml not found: {path}"
    return path


# ---------------------------------------------------------------------------
# Fixtures: Build Output
# ---------------------------------------------------------------------------


@pytest.fixture
def plugin_output_dir(tmp_path: Path) -> Path:
    """Provide a clean temporary directory for plugin build output."""
    output = tmp_path / "plugin"
    output.mkdir(parents=True, exist_ok=True)
    return output


# ---------------------------------------------------------------------------
# Fixtures: Build Configuration (will be replaced by real BuildConfig)
# ---------------------------------------------------------------------------


@pytest.fixture
def build_config(
    nwave_source_tree: Path,
    des_source_tree: Path,
    pyproject_path: Path,
    plugin_output_dir: Path,
) -> dict[str, Any]:
    """
    Provide a default build configuration for the plugin assembler.

    This is a placeholder that will be replaced by the real BuildConfig
    dataclass once implemented by the software crafter.
    """
    return {
        "source_root": nwave_source_tree.parent,
        "nwave_dir": nwave_source_tree,
        "des_dir": des_source_tree,
        "pyproject_path": pyproject_path,
        "output_dir": plugin_output_dir,
        "plugin_name": "nw",
    }


# ---------------------------------------------------------------------------
# Fixtures: Build Results (populated by When steps)
# ---------------------------------------------------------------------------


@pytest.fixture
def build_result() -> dict[str, Any]:
    """
    Mutable container for build pipeline results.

    When steps populate this dict; Then steps read from it.
    Avoids storing state on pytest module.
    """
    return {
        "plugin_dir": None,
        "success": None,
        "error": None,
        "validation_result": None,
    }


# ---------------------------------------------------------------------------
# Fixtures: Minimal Source Trees (for edge case testing)
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_source_tree(tmp_path: Path) -> Path:
    """
    Create a minimal source tree with exactly 1 agent, 1 skill, 1 command.

    Used for minimum viable build tests.
    """
    root = tmp_path / "minimal_source"
    root.mkdir()

    # Minimal pyproject.toml
    pyproject = root / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "nwave"\nversion = "0.0.1"\n',
        encoding="utf-8",
    )

    # 1 agent
    agents_dir = root / "nWave" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "nw-test-agent.md").write_text(
        "---\nname: nw-test-agent\n---\n# Test Agent\n",
        encoding="utf-8",
    )

    # 1 skill
    skills_dir = root / "nWave" / "skills" / "test-agent"
    skills_dir.mkdir(parents=True)
    (skills_dir / "test-skill.md").write_text(
        "---\nname: test-skill\n---\n# Test Skill\n",
        encoding="utf-8",
    )

    # 1 command
    commands_dir = root / "nWave" / "tasks" / "nw"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test-command.md").write_text(
        "---\nname: test-command\n---\n# Test Command\n",
        encoding="utf-8",
    )

    # Minimal DES source
    des_dir = root / "src" / "des"
    des_dir.mkdir(parents=True)
    (des_dir / "__init__.py").write_text("", encoding="utf-8")

    return root


# ---------------------------------------------------------------------------
# Shared BDD Step Definitions: Background Steps
# ---------------------------------------------------------------------------
# These steps are used by Background blocks in multiple feature files
# (walking-skeleton, milestone-1, milestone-2). Defining them in conftest
# makes them available to all test modules automatically.


@given("the nWave source tree is available")
def nwave_source_available(nwave_source_tree: Path):
    """Verify the nWave source tree exists and contains expected content."""
    assert nwave_source_tree.exists()
    assert (nwave_source_tree / "agents").exists()


@given("a clean output directory for the plugin build")
def clean_output_dir(plugin_output_dir: Path):
    """Verify the output directory is clean and writable."""
    assert plugin_output_dir.exists()
    assert len(list(plugin_output_dir.iterdir())) == 0


@given("default build configuration for the nWave source tree")
def default_config(build_config: dict[str, Any]):
    """Verify default build configuration is available."""
    assert build_config["plugin_name"] == "nw"
    assert build_config["nwave_dir"].exists()


@given(parsers.parse('the project version is "{version}"'))
def project_version_set(build_config: dict[str, Any], tmp_path: Path, version: str):
    """Override the project version for testing."""
    # Create a temporary pyproject.toml with the specified version
    pyproject = tmp_path / "pyproject_override.toml"
    pyproject.write_text(
        f'[project]\nname = "nwave"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    build_config["pyproject_path"] = pyproject
    build_config["expected_version"] = version


@given("the source tree is missing the agents directory")
def source_missing_agents(build_config: dict[str, Any], tmp_path: Path):
    """Create a source tree without agents."""
    broken_source = tmp_path / "broken_source" / "nWave"
    broken_source.mkdir(parents=True)
    # Create skills and commands but NOT agents
    (broken_source / "skills").mkdir()
    (broken_source / "tasks" / "nw").mkdir(parents=True)
    build_config["nwave_dir"] = broken_source


@given("any valid nWave source tree")
def any_valid_source(nwave_source_tree: Path):
    """Use the real nWave source tree for property-based checks."""
    assert nwave_source_tree.exists()


@given("the plugin assembler has produced a plugin directory")
def plugin_already_built(build_config: dict[str, Any], build_result: dict[str, Any]):
    """
    Pre-condition: a plugin directory has been built.

    This step invokes the PluginAssembler driving port, providing
    a pre-built plugin for validation scenarios.
    """
    from scripts.build_plugin import BuildConfig, build

    config = BuildConfig.from_dict(build_config)
    result = build(config)
    build_result["plugin_dir"] = result.output_dir
    build_result["success"] = result.is_success()
    build_result["build_result"] = result


# ---------------------------------------------------------------------------
# Shared BDD Step Definitions: When Steps (Build Execution)
# ---------------------------------------------------------------------------


@when("the plugin assembler builds the plugin")
def build_plugin(build_config: dict[str, Any], build_result: dict[str, Any]):
    """Execute the plugin build pipeline."""
    from scripts.build_plugin import BuildConfig, build

    config = BuildConfig.from_dict(build_config)
    result = build(config)
    build_result["plugin_dir"] = result.output_dir
    build_result["success"] = result.is_success()
    build_result["build_result"] = result


@when("the plugin validator checks the output")
def validate_plugin(build_result: dict[str, Any]):
    """
    Run the plugin validator on the build output.

    Driving port: PluginValidator (validate function)
    """
    from scripts.build_plugin import validate

    plugin_dir = build_result["plugin_dir"]
    result = validate(plugin_dir)
    build_result["validation_result"] = {
        "success": result.success,
        "errors": list(result.errors),
        "sections": result.sections,
        "counts": result.counts,
    }


@when("the plugin assembler attempts to build the plugin")
def attempt_build_plugin(build_config: dict[str, Any], build_result: dict[str, Any]):
    """Execute the plugin build pipeline expecting failure."""
    from scripts.build_plugin import BuildConfig, build

    try:
        config = BuildConfig.from_dict(build_config)
        result = build(config)
        build_result["plugin_dir"] = result.output_dir
        build_result["success"] = result.is_success()
        build_result["error"] = result.error if not result.is_success() else None
        build_result["build_result"] = result
    except Exception as exc:
        build_result["success"] = False
        build_result["error"] = str(exc)


# ---------------------------------------------------------------------------
# Shared BDD Step Definitions: Cross-Feature Then Steps
# ---------------------------------------------------------------------------
# These Then steps are referenced by scenarios in multiple feature files
# (walking-skeleton WS-3 and milestone-2-des-bundle).


@then("the plugin directory contains hook registrations")
def plugin_has_hooks(build_result: dict[str, Any]):
    """Verify hooks.json exists."""
    plugin_dir = build_result["plugin_dir"]
    hooks_path = plugin_dir / "hooks" / "hooks.json"
    assert hooks_path.exists(), f"hooks.json not found: {hooks_path}"


@then("hook commands reference the plugin root for execution")
def hooks_use_plugin_root(build_result: dict[str, Any]):
    """Verify hook commands use CLAUDE_PLUGIN_ROOT, not HOME."""
    plugin_dir = build_result["plugin_dir"]
    hooks = json.loads(
        (plugin_dir / "hooks" / "hooks.json").read_text(encoding="utf-8")
    )
    for event, entries in hooks.get("hooks", {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                assert "${CLAUDE_PLUGIN_ROOT}" in cmd or "CLAUDE_PLUGIN_ROOT" in cmd, (
                    f"Hook command for {event} does not reference plugin root: {cmd}"
                )


@then(parsers.parse('the plugin metadata version is "{version}"'))
def metadata_version_is(version: str, build_result: dict[str, Any]):
    """Verify specific version in build result metadata.

    Version is in BuildResult.metadata (not in plugin.json on disk),
    because plugin.json only contains fields used by Claude Code runtime.
    """
    result = build_result["build_result"]
    assert result.metadata["version"] == version


@then("the DES module is importable from the plugin directory")
def des_importable(build_result: dict[str, Any]):
    """Verify DES can be imported (alias for walking skeleton)."""
    plugin_dir = build_result["plugin_dir"]
    des_dir = plugin_dir / "scripts" / "des"
    assert des_dir.exists()
    assert (des_dir / "__init__.py").exists()
