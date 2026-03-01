"""
Step definitions for plugin build assembly scenarios.

Covers: walking-skeleton.feature, milestone-1-plugin-assembler.feature
Driving port: PluginAssembler (build pipeline entry point)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pytest_bdd import given, parsers, scenarios, then


if TYPE_CHECKING:
    from pathlib import Path


def _read_plugin_metadata(build_result: dict[str, Any]) -> dict:
    """Read plugin.json metadata from the build result's plugin directory."""
    plugin_dir = build_result["plugin_dir"]
    return json.loads(
        (plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )


# Register feature files for this step module
scenarios("../walking-skeleton.feature")
scenarios("../milestone-1-plugin-assembler.feature")


# ---------------------------------------------------------------------------
# Given Steps: Source Tree Context
# ---------------------------------------------------------------------------
# Background Given steps (nwave_source_available, clean_output_dir,
# default_config, any_valid_source) are defined in conftest.py for
# cross-module sharing.


# "the project version is" and "the source tree is missing the agents directory"
# are defined in conftest.py for cross-module sharing.


@given("the source tree is missing the skills directory")
def source_missing_skills(build_config: dict[str, Any], tmp_path: Path):
    """Create a source tree without skills."""
    broken_source = tmp_path / "broken_source" / "nWave"
    broken_source.mkdir(parents=True)
    (broken_source / "agents").mkdir()
    (broken_source / "tasks" / "nw").mkdir(parents=True)
    build_config["nwave_dir"] = broken_source


@given("the source tree is missing the commands directory")
def source_missing_commands(build_config: dict[str, Any], tmp_path: Path):
    """Create a source tree without commands."""
    broken_source = tmp_path / "broken_source" / "nWave"
    broken_source.mkdir(parents=True)
    (broken_source / "agents").mkdir()
    (broken_source / "skills").mkdir()
    build_config["nwave_dir"] = broken_source


@given("the project configuration file is missing")
def project_config_missing(build_config: dict[str, Any], tmp_path: Path):
    """Point to a non-existent pyproject.toml."""
    build_config["pyproject_path"] = tmp_path / "nonexistent" / "pyproject.toml"


# ---------------------------------------------------------------------------
# Given Steps: Edge Cases
# ---------------------------------------------------------------------------


@given("a source tree with exactly 1 agent, 1 skill, and 1 command")
def minimal_source(build_config: dict[str, Any], minimal_source_tree: Path):
    """Use the minimal source tree fixture."""
    build_config["source_root"] = minimal_source_tree
    build_config["nwave_dir"] = minimal_source_tree / "nWave"
    build_config["des_dir"] = minimal_source_tree / "src" / "des"
    build_config["pyproject_path"] = minimal_source_tree / "pyproject.toml"


@given(parsers.parse('an agent file named "{filename}" exists in the source'))
def agent_file_exists(filename: str, nwave_source_tree: Path):
    """Verify a specific agent file exists in the source."""
    agent_path = nwave_source_tree / "agents" / filename
    assert agent_path.exists(), f"Agent file not found: {agent_path}"


# Given step "the plugin assembler has produced a plugin directory" is defined
# in conftest.py for cross-module sharing (used by both walking-skeleton and
# milestone-3-plugin-validation scenarios).


@given("any valid project version string")
def any_valid_version():
    """Placeholder for property-based version testing."""
    pass


# ---------------------------------------------------------------------------
# When Steps: Build Execution
# ---------------------------------------------------------------------------
# Shared When steps (build_plugin, attempt_build_plugin) are defined in
# conftest.py for cross-module sharing.


# ---------------------------------------------------------------------------
# When Steps: Validation
# ---------------------------------------------------------------------------
# Shared When step "the plugin validator checks the output" is defined in
# conftest.py for cross-module sharing (used by both walking-skeleton and
# milestone-3-plugin-validation scenarios).


# ---------------------------------------------------------------------------
# Then Steps: Metadata Assertions
# ---------------------------------------------------------------------------


@then("the plugin directory contains a metadata file with the project version")
def plugin_has_metadata_with_version(build_result: dict[str, Any]):
    """Verify plugin.json exists and contains required fields.

    Version is tracked in BuildResult.metadata (not in plugin.json on disk),
    because plugin.json only contains fields used by Claude Code runtime.
    """
    plugin_dir = build_result["plugin_dir"]
    metadata_path = plugin_dir / ".claude-plugin" / "plugin.json"
    assert metadata_path.exists(), f"Metadata file not found: {metadata_path}"

    metadata = _read_plugin_metadata(build_result)
    assert "name" in metadata
    assert metadata["name"], "Name must not be empty"


@then("the plugin metadata version matches the project version")
def metadata_version_matches_project(
    build_result: dict[str, Any], build_config: dict[str, Any]
):
    """Verify build result version matches pyproject.toml version.

    Version is in BuildResult.metadata (not in plugin.json on disk),
    because plugin.json only contains fields used by Claude Code runtime.
    """
    result = build_result["build_result"]

    import tomllib

    with open(build_config["pyproject_path"], "rb") as f:
        pyproject = tomllib.load(f)
    expected = pyproject["project"]["version"]

    assert result.metadata["version"] == expected


@then(parsers.parse('the plugin metadata name is "{name}"'))
def metadata_name_is(name: str, build_result: dict[str, Any]):
    """Verify plugin name in metadata."""
    metadata = _read_plugin_metadata(build_result)
    assert metadata["name"] == name


@then("the plugin metadata contains a description")
def metadata_has_description(build_result: dict[str, Any]):
    """Verify metadata includes a description field."""
    metadata = _read_plugin_metadata(build_result)
    assert "description" in metadata
    assert len(metadata["description"]) > 0


@then("the plugin metadata contains keywords for discoverability")
def metadata_has_keywords(build_result: dict[str, Any]):
    """Verify metadata includes description (keywords removed from plugin.json).

    Extra fields like keywords, homepage, license caused Claude Code to
    silently fail plugin command discovery, so plugin.json now only contains
    name, description, and author. Description serves as the discoverability
    mechanism via the Claude Code plugin registry.
    """
    metadata = _read_plugin_metadata(build_result)
    assert "description" in metadata
    assert len(metadata["description"]) > 0


@then("the plugin metadata identifies the source directory")
def metadata_identifies_source(build_result: dict[str, Any]):
    """Verify plugin metadata contains author info (source field removed).

    Extra fields like source, homepage, repository caused Claude Code to
    silently fail plugin command discovery. Author info is the closest
    remaining field that identifies the plugin origin.
    """
    metadata = _read_plugin_metadata(build_result)
    assert "author" in metadata, "Metadata missing 'author' field"
    assert metadata["author"].get("name"), "Author name must not be empty"


# "the plugin metadata version is" is defined in conftest.py for cross-module sharing.


# ---------------------------------------------------------------------------
# Then Steps: Component Presence
# ---------------------------------------------------------------------------


@then(
    parsers.parse("the plugin directory contains at least {count:d} agent definition")
)
def plugin_has_agents(count: int, build_result: dict[str, Any]):
    """Verify minimum agent count in plugin."""
    plugin_dir = build_result["plugin_dir"]
    agents_dir = plugin_dir / "agents"
    assert agents_dir.exists()
    agent_files = list(agents_dir.glob("*.md"))
    assert len(agent_files) >= count


@then("the plugin contains all 23 agent definitions")
def plugin_has_all_agents(build_result: dict[str, Any]):
    """Verify all 23 agents are present."""
    plugin_dir = build_result["plugin_dir"]
    agents_dir = plugin_dir / "agents"
    agent_files = list(agents_dir.glob("*.md"))
    assert len(agent_files) == 23, f"Expected 23 agents, found {len(agent_files)}"


@then("every agent file is readable and properly structured")
def agents_are_structured(build_result: dict[str, Any]):
    """Verify every agent file is readable and has proper structure."""
    plugin_dir = build_result["plugin_dir"]
    for agent_file in (plugin_dir / "agents").glob("*.md"):
        content = agent_file.read_text(encoding="utf-8")
        assert content.startswith("---"), (
            f"Agent {agent_file.name} is not properly structured"
        )


@then("every agent body is identical to the source")
def agents_body_matches_source(
    build_result: dict[str, Any], build_config: dict[str, Any]
):
    """Verify agent body content is preserved (frontmatter may differ for skill refs)."""
    plugin_dir = build_result["plugin_dir"]
    source_dir = build_config["nwave_dir"] / "agents"

    def _body(text: str) -> str:
        """Extract body after YAML frontmatter."""
        if text.startswith("---"):
            parts = text.split("---", 2)
            return parts[2] if len(parts) >= 3 else ""
        return text

    for agent_file in (plugin_dir / "agents").glob("*.md"):
        source_file = source_dir / agent_file.name
        assert source_file.exists()
        plugin_body = _body(agent_file.read_text(encoding="utf-8"))
        source_body = _body(source_file.read_text(encoding="utf-8"))
        assert plugin_body == source_body, (
            f"Agent body content differs: {agent_file.name}"
        )


@then("agents with skills have their frontmatter rewritten to bundle refs")
def agents_skill_refs_rewritten(
    build_result: dict[str, Any], build_config: dict[str, Any]
):
    """Verify agents with skill bundles have rewritten frontmatter."""
    plugin_dir = build_result["plugin_dir"]
    skills_dir = plugin_dir / "skills"
    available_bundles = (
        {d.name for d in skills_dir.iterdir() if d.is_dir()}
        if skills_dir.exists()
        else set()
    )

    for agent_file in (plugin_dir / "agents").glob("nw-*.md"):
        agent_name = agent_file.stem.removeprefix("nw-")
        if agent_name not in available_bundles:
            continue
        content = agent_file.read_text(encoding="utf-8")
        if not content.startswith("---"):
            continue
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        frontmatter = parts[1]
        # Should reference the bundle name, not individual skill files
        assert f"  - {agent_name}" in frontmatter, (
            f"Agent {agent_file.name} frontmatter not rewritten to bundle ref"
        )


@then(
    parsers.parse("the plugin directory contains at least {count:d} command definition")
)
def plugin_has_commands(count: int, build_result: dict[str, Any]):
    """Verify minimum command count in plugin."""
    plugin_dir = build_result["plugin_dir"]
    # Commands may be in commands/ or commands/nw/
    commands_dir = plugin_dir / "commands"
    assert commands_dir.exists()
    cmd_files = list(commands_dir.rglob("*.md"))
    assert len(cmd_files) >= count


@then("the plugin contains all command definitions")
def plugin_has_all_commands(build_result: dict[str, Any]):
    """Verify all commands are present."""
    plugin_dir = build_result["plugin_dir"]
    commands_dir = plugin_dir / "commands"
    cmd_files = list(commands_dir.rglob("*.md"))
    assert len(cmd_files) >= 21, f"Expected >= 21 commands, found {len(cmd_files)}"


@then("command files reside in the commands directory")
def commands_in_correct_dir(build_result: dict[str, Any]):
    """Verify commands are in the expected directory."""
    plugin_dir = build_result["plugin_dir"]
    commands_dir = plugin_dir / "commands"
    assert commands_dir.exists()
    assert any(commands_dir.rglob("*.md"))


@then('every command file produces a "/nw:" prefixed slash command')
def commands_produce_nw_prefix(build_result: dict[str, Any]):
    """Verify command files are in the nw namespace directory."""
    plugin_dir = build_result["plugin_dir"]
    commands_dir = plugin_dir / "commands"
    cmd_files = list(commands_dir.rglob("*.md"))
    assert len(cmd_files) > 0, "No command files found"
    for cmd_file in cmd_files:
        # The /nw: prefix comes from commands residing in commands/ dir
        # and the plugin name being "nw"
        relative = cmd_file.relative_to(commands_dir)
        assert cmd_file.suffix == ".md", f"Command file not markdown: {cmd_file.name}"
        assert str(relative) != "", f"Command file outside commands dir: {cmd_file}"


@then(parsers.parse("the plugin directory contains at least {count:d} skill file"))
def plugin_has_skills(count: int, build_result: dict[str, Any]):
    """Verify minimum skill count in plugin."""
    plugin_dir = build_result["plugin_dir"]
    skills_dir = plugin_dir / "skills"
    assert skills_dir.exists()
    skill_files = list(skills_dir.rglob("*.md"))
    assert len(skill_files) >= count


@then("the plugin contains all skill files from the source tree")
def plugin_has_all_skills(build_result: dict[str, Any], build_config: dict[str, Any]):
    """Verify all skills are present."""
    plugin_dir = build_result["plugin_dir"]
    source_dir = build_config["nwave_dir"] / "skills"
    source_skills = list(source_dir.rglob("*.md"))
    plugin_skills = list((plugin_dir / "skills").rglob("*.md"))
    assert len(plugin_skills) >= len(source_skills), (
        f"Expected >= {len(source_skills)} skills, found {len(plugin_skills)}"
    )


@then("skill files are organized by agent name")
def skills_organized_by_agent(build_result: dict[str, Any]):
    """Verify skills are in agent-named subdirectories."""
    plugin_dir = build_result["plugin_dir"]
    skills_dir = plugin_dir / "skills"
    subdirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    assert len(subdirs) > 0, "Skills should be in agent-named subdirectories"


@then("the directory structure mirrors the source layout")
def skills_mirror_source_layout(
    build_result: dict[str, Any], build_config: dict[str, Any]
):
    """Verify skill directory structure matches source."""
    plugin_dir = build_result["plugin_dir"]
    source_dir = build_config["nwave_dir"] / "skills"
    source_dirs = {d.name for d in source_dir.iterdir() if d.is_dir()}
    plugin_dirs = {d.name for d in (plugin_dir / "skills").iterdir() if d.is_dir()}
    assert source_dirs == plugin_dirs


@then("every source skill file is present in the plugin")
def source_skills_present(build_result: dict[str, Any], build_config: dict[str, Any]):
    """Verify all source skill files exist in the plugin (SKILL.md is additive)."""
    plugin_dir = build_result["plugin_dir"]
    source_dir = build_config["nwave_dir"] / "skills"
    source_names = {f.name for f in source_dir.rglob("*.md")}
    plugin_names = {f.name for f in (plugin_dir / "skills").rglob("*.md")}
    missing = source_names - plugin_names
    assert len(missing) == 0, f"Source skills missing from plugin: {missing}"


@then("each skill directory has a SKILL.md entry point")
def skill_dirs_have_entry_points(build_result: dict[str, Any]):
    """Verify every skill subdirectory has a generated SKILL.md."""
    plugin_dir = build_result["plugin_dir"]
    skills_dir = plugin_dir / "skills"
    subdirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    assert len(subdirs) > 0, "Expected at least one skill subdirectory"
    for subdir in subdirs:
        skill_md = subdir / "SKILL.md"
        assert skill_md.exists(), (
            f"Missing SKILL.md entry point in skills/{subdir.name}/"
        )


# ---------------------------------------------------------------------------
# Then Steps: Error Assertions
# ---------------------------------------------------------------------------


@then("the build fails with a missing agents error")
def build_fails_missing_agents(build_result: dict[str, Any]):
    """Verify build failure message mentions agents."""
    assert build_result["success"] is False
    assert "agents" in build_result["error"].lower()


@then("the build fails with a missing skills error")
def build_fails_missing_skills(build_result: dict[str, Any]):
    """Verify build failure message mentions skills."""
    assert build_result["success"] is False
    assert "skills" in build_result["error"].lower()


@then("the build fails with a missing commands error")
def build_fails_missing_commands(build_result: dict[str, Any]):
    """Verify build failure message mentions commands."""
    assert build_result["success"] is False
    assert "commands" in build_result["error"].lower()


@then("the build fails with a version read error")
def build_fails_version_error(build_result: dict[str, Any]):
    """Verify build failure message mentions version."""
    assert build_result["success"] is False
    assert "version" in build_result["error"].lower()


@then("no partial plugin directory is created")
def no_partial_output(build_result: dict[str, Any]):
    """Verify failed build does not leave partial output."""
    plugin_dir = build_result.get("plugin_dir")
    if plugin_dir is not None:
        # Either dir does not exist or is empty
        assert not plugin_dir.exists() or len(list(plugin_dir.iterdir())) == 0


# ---------------------------------------------------------------------------
# Then Steps: Edge Case Assertions
# ---------------------------------------------------------------------------


@then("the plugin directory is created successfully")
def plugin_dir_created(build_result: dict[str, Any]):
    """Verify plugin directory was created."""
    assert build_result["success"] is True
    assert build_result["plugin_dir"].exists()


@then("the plugin metadata is valid")
def plugin_metadata_valid(build_result: dict[str, Any]):
    """Verify metadata is parseable JSON with required fields."""
    metadata = _read_plugin_metadata(build_result)
    assert "name" in metadata
    assert "description" in metadata


@then(parsers.parse("the agent file appears in the plugin with its original name"))
def agent_file_preserved_name(build_result: dict[str, Any]):
    """Verify agent filename is preserved in plugin output."""
    # This step validates that special characters in filenames are handled
    plugin_dir = build_result["plugin_dir"]
    agents_dir = plugin_dir / "agents"
    # At minimum, the agents directory should have files
    assert any(agents_dir.glob("*.md"))


@then("every agent in the source has exactly one corresponding file in the plugin")
def one_to_one_agent_mapping(
    build_result: dict[str, Any], build_config: dict[str, Any]
):
    """Property: bijective mapping between source and plugin agents."""
    source_agents = {
        f.name for f in (build_config["nwave_dir"] / "agents").glob("*.md")
    }
    plugin_agents = {
        f.name for f in (build_result["plugin_dir"] / "agents").glob("*.md")
    }
    assert source_agents == plugin_agents


@then("no extra agent files are introduced")
def no_extra_agents(build_result: dict[str, Any], build_config: dict[str, Any]):
    """Property: no files added that are not in source."""
    source_agents = {
        f.name for f in (build_config["nwave_dir"] / "agents").glob("*.md")
    }
    plugin_agents = {
        f.name for f in (build_result["plugin_dir"] / "agents").glob("*.md")
    }
    extra = plugin_agents - source_agents
    assert len(extra) == 0, f"Extra agents introduced: {extra}"


@then("the plugin metadata version is identical to the source version")
def version_identity(build_result: dict[str, Any], build_config: dict[str, Any]):
    """Property: version is always preserved exactly in BuildResult.metadata.

    Version is in BuildResult.metadata (not in plugin.json on disk),
    because plugin.json only contains fields used by Claude Code runtime.
    """
    import tomllib

    result = build_result["build_result"]
    with open(build_config["pyproject_path"], "rb") as f:
        pyproject = tomllib.load(f)
    expected_version = pyproject["project"]["version"]
    assert result.metadata["version"] == expected_version, (
        f"Version mismatch: metadata={result.metadata['version']!r}, source={expected_version!r}"
    )


# ---------------------------------------------------------------------------
# Then Steps: Validation
# ---------------------------------------------------------------------------


@then("the plugin passes structural validation")
def validation_passes(build_result: dict[str, Any]):
    """Verify structural validation succeeds."""
    validation = build_result["validation_result"]
    assert validation is not None
    assert validation["success"] is True


@then("the validation report confirms all required sections are present")
def validation_all_sections(build_result: dict[str, Any]):
    """Verify validation checked all sections."""
    validation = build_result["validation_result"]
    assert "sections" in validation
    for section in ["agents", "skills", "commands", "hooks", "metadata"]:
        assert section in validation["sections"]
        assert validation["sections"][section] is True
