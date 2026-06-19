"""
Acceptance tests for stale artifact cleanup during nWave update.

Based on: docs/analysis/rca-stale-nw-colon-commands-windows.md

These tests validate that installer plugins remove stale artifacts from
previous versions so users see only current commands, templates, and scripts.

Driving ports:
  - AgentsPlugin.install()
  - CommandsPlugin.install()
  - SkillsPlugin.install()
  - TemplatesPlugin.install()
  - UtilitiesPlugin.install()

Most scenarios are expected to FAIL (RED) because cleanup logic for stale
templates and utility scripts is not yet implemented.
"""

import logging
import shutil
import stat
from pathlib import Path

import pytest
from pytest_bdd import given, scenario, then, when

from scripts.install.plugins.base import InstallContext, PluginResult
from scripts.shared.skill_distribution import (
    TEMPLATES_FAMILY_KEY,
    UTILITIES_FAMILY_KEY,
    write_manifest,
)


# ---------------------------------------------------------------------------
# Scenario wiring
# ---------------------------------------------------------------------------


@scenario(
    "install-cleanup-stale.feature",
    "User updates and old hierarchical command files are removed",
)
def test_walking_skeleton_legacy_commands_removed():
    """Walking skeleton: legacy commands/nw/ directory cleaned on update."""


@scenario(
    "install-cleanup-stale.feature",
    "Installer removes commands that no longer exist in the current version",
)
def test_stale_command_skills_removed():
    """Stale nw-* skill directories removed when not in current version.

    NOTE: This passes because copy_skills_to_target(clean_existing=True) removes
    ALL nw-* directories before copying, effectively cleaning stale entries.
    """


@scenario(
    "install-cleanup-stale.feature",
    "Installer removes stale template files not in the current version",
)
def test_stale_templates_removed():
    """Stale template files removed when not in current version."""


@scenario(
    "install-cleanup-stale.feature",
    "Installer removes stale agent definitions not in current version",
)
def test_stale_agent_definitions_removed():
    """Stale agent definitions removed when not in current version.

    NOTE: This passes because AgentsPlugin wipes and recreates agents/nw/
    via shutil.rmtree before copying current agents, effectively removing
    any stale agent files.
    """


@scenario(
    "install-cleanup-stale.feature",
    "Installer removes stale utility scripts not in the current set of distributed scripts",
)
def test_stale_utility_scripts_removed():
    """Stale utility scripts removed when not in current distributed set."""


@scenario(
    "install-cleanup-stale.feature",
    "First install succeeds with expected files",
)
def test_first_install_succeeds():
    """First install produces expected files and reports success."""


@scenario(
    "install-cleanup-stale.feature",
    "Second install produces identical result to the first",
)
def test_second_install_identical():
    """Second install produces identical results to the first."""


@scenario(
    "install-cleanup-stale.feature",
    "Installer warns when plugin-format commands coexist with CLI commands",
)
def test_plugin_coexistence_warning():
    """Warning when both CLI and plugin commands coexist."""


@scenario(
    "install-cleanup-stale.feature",
    "Cleanup handles read-only stale files gracefully",
)
def test_readonly_stale_file_cleanup():
    """Read-only stale files handled without crash.

    NOTE: Currently the templates plugin copies files over existing ones
    (including read-only), so this tests that behavior is non-destructive.
    When stale cleanup is added, this must also handle permission errors.
    """


@scenario(
    "install-cleanup-stale.feature",
    "Cleanup handles missing target directory gracefully",
)
def test_fresh_install_no_cleanup_errors():
    """Fresh install with no pre-existing directories succeeds."""


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root() -> Path:
    """Real project root (4 levels up from this file)."""
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.install-cleanup-stale")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
    return logger


@pytest.fixture
def clean_claude_dir(tmp_path: Path) -> Path:
    """Simulate a clean ~/.claude directory for testing."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    return claude_dir


@pytest.fixture
def temp_source_dir(tmp_path: Path) -> Path:
    """Temporary source directory simulating nWave framework source."""
    source = tmp_path / "nWave"
    source.mkdir(parents=True, exist_ok=True)
    return source


@pytest.fixture
def install_context(
    clean_claude_dir: Path,
    temp_source_dir: Path,
    project_root: Path,
    test_logger: logging.Logger,
) -> InstallContext:
    """Create an InstallContext configured for cleanup tests.

    Uses the real InstallContext with test-controlled paths.
    """
    # Create minimal framework-catalog.yaml so shared functions don't fail
    nwave_dir = temp_source_dir
    catalog_path = nwave_dir / "framework-catalog.yaml"
    if not catalog_path.exists():
        catalog_path.write_text("agents: {}\n", encoding="utf-8")

    # Create agents dir for ownership map
    agents_dir = nwave_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    return InstallContext(
        claude_dir=clean_claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=temp_source_dir / "templates",
        logger=test_logger,
        project_root=temp_source_dir.parent,
        framework_source=temp_source_dir,
        dry_run=False,
        dev_mode=True,  # Include all skills, no public/private filtering
    )


@pytest.fixture
def agents_plugin():
    """Create an AgentsPlugin instance -- driving port for agent installation."""
    from scripts.install.plugins.agents_plugin import AgentsPlugin

    return AgentsPlugin()


@pytest.fixture
def commands_plugin():
    """Create a CommandsPlugin instance -- driving port for command cleanup."""
    from scripts.install.plugins.commands_plugin import CommandsPlugin

    return CommandsPlugin()


@pytest.fixture
def skills_plugin():
    """Create a SkillsPlugin instance -- driving port for skill installation."""
    from scripts.install.plugins.skills_plugin import SkillsPlugin

    return SkillsPlugin()


@pytest.fixture
def templates_plugin():
    """Create a TemplatesPlugin instance -- driving port for template installation."""
    from scripts.install.plugins.templates_plugin import TemplatesPlugin

    return TemplatesPlugin()


@pytest.fixture
def utilities_plugin():
    """Create a UtilitiesPlugin instance -- driving port for utility installation."""
    from scripts.install.plugins.utilities_plugin import UtilitiesPlugin

    return UtilitiesPlugin()


# ---------------------------------------------------------------------------
# Shared state fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def scenario_state():
    """Mutable state shared between Given/When/Then steps within a scenario."""
    return {}


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given(
    'the user has legacy commands installed in the "commands/nw/" directory',
    target_fixture="legacy_commands_dir",
)
def given_legacy_commands_dir(clean_claude_dir: Path) -> Path:
    """Pre-populate a legacy commands/nw/ directory."""
    commands_dir = clean_claude_dir / "commands" / "nw"
    commands_dir.mkdir(parents=True, exist_ok=True)
    return commands_dir


@given('the legacy directory contains "deliver.md" and "design.md" command files')
def given_legacy_command_files(legacy_commands_dir: Path):
    """Create old-format command files in the legacy directory."""
    (legacy_commands_dir / "deliver.md").write_text(
        "# Deliver\nLegacy deliver command.\n", encoding="utf-8"
    )
    (legacy_commands_dir / "design.md").write_text(
        "# Design\nLegacy design command.\n", encoding="utf-8"
    )


@given("the current version installs commands as skills")
def given_current_installs_as_skills():
    """Acknowledge that the current version uses skills, not commands/nw/."""


@given(
    'the user has a skills directory with stale command "nw-old-removed-command"',
    target_fixture="stale_skill_dir",
)
def given_stale_skill_in_skills_dir(clean_claude_dir: Path) -> Path:
    """Pre-populate a stale nw-* skill directory that is not in current version."""
    skills_dir = clean_claude_dir / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    stale = skills_dir / "nw-old-removed-command"
    stale.mkdir(parents=True, exist_ok=True)
    (stale / "SKILL.md").write_text(
        "---\nname: old-removed-command\ndescription: Stale\n---\n# Old\n",
        encoding="utf-8",
    )
    return stale


@given('the current version does not include "nw-old-removed-command"')
def given_current_excludes_stale_command(temp_source_dir: Path):
    """Ensure the source tree does not contain the stale command skill."""
    skills_source = temp_source_dir / "skills"
    skills_source.mkdir(parents=True, exist_ok=True)
    # Create a valid current skill so the plugin has something to install
    current = skills_source / "nw-current-command"
    current.mkdir(parents=True, exist_ok=True)
    (current / "SKILL.md").write_text(
        "---\nname: current-command\ndescription: Current\nuser-invocable: true\n---\n# Current\n",
        encoding="utf-8",
    )


@given(
    'the user has a templates directory with "old-workflow-template.yaml" from a previous version',
    target_fixture="stale_template_file",
)
def given_stale_template_file(clean_claude_dir: Path) -> Path:
    """Pre-populate a stale template file in the templates directory.

    "From a previous version" means the previous install RECORDED it in the
    templates family manifest — sweep authority is manifest-driven (slice-02
    of installer-orphan-sweep): unrecorded files are preserved by default.
    """
    templates_dir = clean_claude_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    stale = templates_dir / "old-workflow-template.yaml"
    stale.write_text("# Old workflow template\nstale: true\n", encoding="utf-8")
    write_manifest(templates_dir, [stale.name], key=TEMPLATES_FAMILY_KEY)
    return stale


@given('the current version does not ship "old-workflow-template.yaml"')
def given_current_excludes_stale_template(temp_source_dir: Path):
    """Create a templates source with only current templates."""
    templates_source = temp_source_dir / "templates"
    templates_source.mkdir(parents=True, exist_ok=True)
    (templates_source / "current-template.yaml").write_text(
        "# Current template\ncurrent: true\n", encoding="utf-8"
    )


@given(
    'the user has a scripts directory with "legacy_migration_helper.py" from a previous version',
    target_fixture="stale_script_file",
)
def given_stale_utility_script(clean_claude_dir: Path) -> Path:
    """Pre-populate a stale utility script in the scripts directory.

    "From a previous version" means the previous install RECORDED it in the
    utilities family manifest — sweep authority is manifest-driven (slice-02
    of installer-orphan-sweep): unrecorded ``*.py`` files (user scripts,
    sibling-family scripts) are preserved by default.
    """
    scripts_dir = clean_claude_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    stale = scripts_dir / "legacy_migration_helper.py"
    stale.write_text(
        '"""Legacy migration helper."""\n__version__ = "1.0.0"\n',
        encoding="utf-8",
    )
    write_manifest(scripts_dir, [stale.name], key=UTILITIES_FAMILY_KEY)
    return stale


@given(
    'the current set of distributed scripts does not include "legacy_migration_helper.py"'
)
def given_current_set_excludes_stale(temp_source_dir: Path):
    """Ensure the source scripts directory has only currently distributed scripts."""
    scripts_source = temp_source_dir / "scripts"
    scripts_source.mkdir(parents=True, exist_ok=True)
    # Create a currently distributed script
    (scripts_source / "install_nwave_target_hooks.py").write_text(
        '"""Target hooks installer."""\n__version__ = "2.0.0"\n',
        encoding="utf-8",
    )


@given(
    'the user has an agents directory with "nw-old-retired-agent.md" from a previous version',
    target_fixture="stale_agent_file",
)
def given_stale_agent_file(clean_claude_dir: Path) -> Path:
    """Pre-populate a stale agent file in the agents/nw/ directory."""
    agents_dir = clean_claude_dir / "agents" / "nw"
    agents_dir.mkdir(parents=True, exist_ok=True)
    stale = agents_dir / "nw-old-retired-agent.md"
    stale.write_text(
        "---\nname: old-retired-agent\ndescription: Stale agent from old version\n---\n# Old\n",
        encoding="utf-8",
    )
    return stale


@given('the current version does not include "nw-old-retired-agent.md"')
def given_current_excludes_stale_agent(temp_source_dir: Path):
    """Create an agents source with only current agents (no stale one)."""
    agents_source = temp_source_dir / "agents"
    agents_source.mkdir(parents=True, exist_ok=True)
    # Create a current agent so the plugin has something to install
    (agents_source / "nw-current-active-agent.md").write_text(
        "---\nname: current-active-agent\ndescription: Current agent\n---\n# Current\n",
        encoding="utf-8",
    )


@given("the user has a clean installation directory")
def given_clean_install_dir(clean_claude_dir: Path):
    """The installation directory is clean (already provided by fixture)."""


@given("the current version includes 2 skills and 1 template")
def given_current_version_contents(temp_source_dir: Path):
    """Create source with 2 skills and 1 template for idempotency test."""
    # Skills
    skills_source = temp_source_dir / "skills"
    skills_source.mkdir(parents=True, exist_ok=True)
    for name in ["nw-skill-alpha", "nw-skill-beta"]:
        skill_dir = skills_source / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name.removeprefix('nw-')}\ndescription: Test\n---\n# {name}\n",
            encoding="utf-8",
        )

    # Templates
    templates_source = temp_source_dir / "templates"
    templates_source.mkdir(parents=True, exist_ok=True)
    (templates_source / "main-template.yaml").write_text(
        "# Main template\nversion: 1\n", encoding="utf-8"
    )


@given("a previous install has already completed successfully")
def given_previous_install_completed(
    commands_plugin,
    skills_plugin,
    templates_plugin,
    utilities_plugin,
    install_context: InstallContext,
    scenario_state: dict,
):
    """Run a full install so the second scenario starts from a known state."""
    results = {}
    results["commands"] = commands_plugin.install(install_context)
    results["skills"] = skills_plugin.install(install_context)
    results["templates"] = templates_plugin.install(install_context)
    results["utilities"] = utilities_plugin.install(install_context)
    # Verify the first install succeeded
    for plugin_name, result in results.items():
        assert result.success, f"Pre-install {plugin_name} failed: {result.message}"
    # Capture the file snapshot for comparison in Then steps
    scenario_state["previous_install_results"] = results
    scenario_state["previous_install_snapshot"] = _snapshot_directory(
        install_context.claude_dir
    )


def _snapshot_directory(root: Path) -> dict[str, bytes]:
    """Capture file contents under root as {relative_path: content} dict."""
    snapshot = {}
    for f in sorted(root.rglob("*")):
        if f.is_file():
            snapshot[str(f.relative_to(root))] = f.read_bytes()
    return snapshot


@given(
    'the user has CLI-installed commands in the skills directory as "nw-deliver"',
    target_fixture="cli_command_dir",
)
def given_cli_commands(clean_claude_dir: Path) -> Path:
    """Pre-populate a CLI-installed command skill."""
    skills_dir = clean_claude_dir / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    cli_cmd = skills_dir / "nw-deliver"
    cli_cmd.mkdir(parents=True, exist_ok=True)
    (cli_cmd / "SKILL.md").write_text(
        "---\nname: deliver\ndescription: Deliver command\nuser-invocable: true\n---\n# Deliver\n",
        encoding="utf-8",
    )
    return cli_cmd


@given('the user also has a plugin-installed "nw" plugin active')
def given_plugin_active(clean_claude_dir: Path, scenario_state: dict):
    """Simulate an active nw plugin by creating the plugin marker directory."""
    # The plugin system registers commands via its own namespace.
    # We simulate this by creating a plugins/nw marker directory.
    plugins_dir = clean_claude_dir / "plugins" / "nw"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    (plugins_dir / "plugin.json").write_text(
        '{"name": "nw", "version": "2.0.0"}', encoding="utf-8"
    )
    scenario_state["plugin_dir"] = plugins_dir


@given(
    'the user has a stale template file "old-config.yaml" that is read-only',
    target_fixture="readonly_stale_file",
)
def given_readonly_stale_template(clean_claude_dir: Path) -> Path:
    """Create a read-only stale template file."""
    templates_dir = clean_claude_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    stale = templates_dir / "old-config.yaml"
    stale.write_text("# Old config\nstale: true\n", encoding="utf-8")
    # Recorded by the previous version: keeps the cleanup path exercised
    # under the manifest-driven sweep (unrecorded files are never touched).
    write_manifest(templates_dir, [stale.name], key=TEMPLATES_FAMILY_KEY)
    # Make it read-only
    stale.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return stale


@given('the current version does not ship "old-config.yaml"')
def given_current_excludes_readonly_template(temp_source_dir: Path):
    """Create templates source without the stale config file."""
    templates_source = temp_source_dir / "templates"
    templates_source.mkdir(parents=True, exist_ok=True)
    (templates_source / "current-config.yaml").write_text(
        "# Current config\ncurrent: true\n", encoding="utf-8"
    )


@given("the user has never installed nWave before")
def given_fresh_user():
    """No pre-existing installation -- clean state is already provided by fixtures."""


@given("no commands, templates, or scripts directories exist")
def given_no_directories(clean_claude_dir: Path, temp_source_dir: Path):
    """Ensure none of the target directories exist, but source templates exist."""
    for dirname in ["commands", "templates", "scripts", "skills"]:
        target = clean_claude_dir / dirname
        if target.exists():
            shutil.rmtree(target)
    # The templates plugin needs a source directory to install from.
    # Create a minimal source template so the plugin does not fail
    # due to missing source (which is a different failure mode).
    templates_source = temp_source_dir / "templates"
    templates_source.mkdir(parents=True, exist_ok=True)
    (templates_source / "default-template.yaml").write_text(
        "# Default template\nversion: 1\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when(
    "the user runs the nWave installer",
    target_fixture="install_results",
)
def when_user_runs_installer(
    commands_plugin,
    skills_plugin,
    templates_plugin,
    utilities_plugin,
    install_context: InstallContext,
    scenario_state: dict,
) -> dict[str, PluginResult]:
    """Execute all four plugins in sequence, simulating a full install."""
    results = {}
    results["commands"] = commands_plugin.install(install_context)
    results["skills"] = skills_plugin.install(install_context)
    results["templates"] = templates_plugin.install(install_context)
    results["utilities"] = utilities_plugin.install(install_context)
    scenario_state["install_results"] = results
    return results


@when(
    "the agents plugin installs the current agent set",
    target_fixture="agents_result",
)
def when_agents_plugin_installs(
    agents_plugin,
    install_context: InstallContext,
) -> PluginResult:
    """Execute the agents plugin to install current agent definitions."""
    return agents_plugin.install(install_context)


@when(
    "the skills plugin installs the current command set",
    target_fixture="skills_result",
)
def when_skills_plugin_installs(
    skills_plugin,
    install_context: InstallContext,
) -> PluginResult:
    """Execute the skills plugin to install current command skills."""
    return skills_plugin.install(install_context)


@when(
    "the templates plugin installs the current template set",
    target_fixture="templates_result",
)
def when_templates_plugin_installs(
    templates_plugin,
    install_context: InstallContext,
) -> PluginResult:
    """Execute the templates plugin to install current templates."""
    return templates_plugin.install(install_context)


@when(
    "the utilities plugin installs the current script set",
    target_fixture="utilities_result",
)
def when_utilities_plugin_installs(
    utilities_plugin,
    install_context: InstallContext,
) -> PluginResult:
    """Execute the utilities plugin to install current scripts."""
    return utilities_plugin.install(install_context)


@when(
    "the templates plugin attempts to clean up stale files",
    target_fixture="templates_result",
)
def when_templates_plugin_cleans_up(
    templates_plugin,
    install_context: InstallContext,
) -> PluginResult:
    """Execute the templates plugin, which should attempt stale file cleanup."""
    return templates_plugin.install(install_context)


@when(
    "the user runs the nWave installer for the first time",
    target_fixture="install_results",
)
def when_user_runs_installer_first_time(
    commands_plugin,
    skills_plugin,
    templates_plugin,
    utilities_plugin,
    install_context: InstallContext,
    scenario_state: dict,
) -> dict[str, PluginResult]:
    """Execute all four plugins on a fresh system (no pre-existing dirs)."""
    results = {}
    results["commands"] = commands_plugin.install(install_context)
    results["skills"] = skills_plugin.install(install_context)
    results["templates"] = templates_plugin.install(install_context)
    results["utilities"] = utilities_plugin.install(install_context)
    scenario_state["install_results"] = results
    return results


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then('the legacy "commands/nw/" directory no longer exists')
def then_legacy_commands_gone(clean_claude_dir: Path):
    """Verify the old commands/nw/ directory has been removed."""
    legacy_dir = clean_claude_dir / "commands" / "nw"
    assert not legacy_dir.exists(), (
        f"Legacy commands/nw/ directory still exists at {legacy_dir}"
    )


@then("the installer reports successful cleanup of legacy commands")
def then_installer_reports_cleanup(install_results: dict[str, PluginResult]):
    """Verify the commands plugin reported successful cleanup."""
    result = install_results["commands"]
    assert result.success, f"Commands plugin failed: {result.message}"
    assert "clean" in result.message.lower() or "legacy" in result.message.lower(), (
        f"Commands plugin message does not mention cleanup: {result.message}"
    )


@then('"nw-old-removed-command" is no longer present in the skills directory')
def then_stale_skill_gone(clean_claude_dir: Path):
    """Verify the stale skill directory has been removed."""
    stale = clean_claude_dir / "skills" / "nw-old-removed-command"
    assert not stale.exists(), (
        f"Stale skill 'nw-old-removed-command' still exists at {stale}"
    )


@then("only commands from the current version remain installed")
def then_only_current_commands(clean_claude_dir: Path):
    """Verify only current-version skills are present."""
    skills_dir = clean_claude_dir / "skills"
    if skills_dir.exists():
        nw_dirs = [d.name for d in skills_dir.iterdir() if d.name.startswith("nw-")]
        assert "nw-old-removed-command" not in nw_dirs, (
            f"Stale command still present. Found nw-* dirs: {nw_dirs}"
        )
        assert "nw-current-command" in nw_dirs, (
            f"Current command missing. Found nw-* dirs: {nw_dirs}"
        )


@then('"nw-old-retired-agent.md" is no longer present in the agents directory')
def then_stale_agent_gone(clean_claude_dir: Path):
    """Verify the stale agent file has been removed."""
    stale = clean_claude_dir / "agents" / "nw" / "nw-old-retired-agent.md"
    assert not stale.exists(), (
        f"Stale agent 'nw-old-retired-agent.md' still exists at {stale}"
    )


@then("only agent definitions from the current version remain installed")
def then_only_current_agents(clean_claude_dir: Path):
    """Verify only current-version agent definitions are present."""
    agents_dir = clean_claude_dir / "agents" / "nw"
    assert agents_dir.exists(), "Agents directory does not exist"
    agent_files = [f.name for f in agents_dir.iterdir() if f.name.startswith("nw-")]
    assert "nw-old-retired-agent.md" not in agent_files, (
        f"Stale agent still present. Found nw-* files: {agent_files}"
    )
    assert "nw-current-active-agent.md" in agent_files, (
        f"Current agent missing. Found nw-* files: {agent_files}"
    )


@then('"old-workflow-template.yaml" is no longer present in the templates directory')
def then_stale_template_gone(clean_claude_dir: Path):
    """Verify the stale template file has been removed."""
    stale = clean_claude_dir / "templates" / "old-workflow-template.yaml"
    assert not stale.exists(), (
        f"Stale template 'old-workflow-template.yaml' still exists at {stale}"
    )


@then("only templates from the current version remain installed")
def then_only_current_templates(clean_claude_dir: Path):
    """Verify only current-version templates are present."""
    templates_dir = clean_claude_dir / "templates"
    assert templates_dir.exists(), "Templates directory does not exist"
    files = [f.name for f in templates_dir.iterdir() if f.is_file()]
    assert "old-workflow-template.yaml" not in files, (
        f"Stale template still present. Found: {files}"
    )
    assert "current-template.yaml" in files, f"Current template missing. Found: {files}"


@then('"legacy_migration_helper.py" is no longer present in the scripts directory')
def then_stale_script_gone(clean_claude_dir: Path):
    """Verify the stale utility script has been removed."""
    stale = clean_claude_dir / "scripts" / "legacy_migration_helper.py"
    assert not stale.exists(), (
        f"Stale script 'legacy_migration_helper.py' still exists at {stale}"
    )


@then(
    "only utility scripts from the current set of distributed scripts remain installed"
)
def then_only_current_distributed_scripts(clean_claude_dir: Path):
    """Verify only currently distributed utility scripts are present."""
    scripts_dir = clean_claude_dir / "scripts"
    if scripts_dir.exists():
        py_files = [f.name for f in scripts_dir.glob("*.py")]
        assert "legacy_migration_helper.py" not in py_files, (
            f"Stale script still present. Found: {py_files}"
        )


@then("the installer reports success for all plugins")
def then_all_plugins_succeed(install_results: dict[str, PluginResult]):
    """Verify every plugin reported success on the first install."""
    for plugin_name, result in install_results.items():
        assert result.success, f"Plugin {plugin_name} failed: {result.message}"


@then("the expected skills and templates are installed")
def then_expected_files_installed(clean_claude_dir: Path):
    """Verify the expected skills and templates are present after install."""
    skills_dir = clean_claude_dir / "skills"
    assert skills_dir.exists(), "Skills directory does not exist"
    nw_dirs = [d.name for d in skills_dir.iterdir() if d.name.startswith("nw-")]
    assert len(nw_dirs) == 2, f"Expected 2 skill dirs, found {len(nw_dirs)}: {nw_dirs}"

    templates_dir = clean_claude_dir / "templates"
    assert templates_dir.exists(), "Templates directory does not exist"
    template_files = [f.name for f in templates_dir.iterdir() if f.is_file()]
    assert len(template_files) >= 1, (
        f"Expected at least 1 template, found {len(template_files)}: {template_files}"
    )


@then("the installed files are identical to the previous install")
def then_files_identical_to_previous(
    clean_claude_dir: Path,
    scenario_state: dict,
):
    """Verify file contents match the snapshot from the previous install."""
    previous_snapshot = scenario_state["previous_install_snapshot"]
    current_snapshot = _snapshot_directory(clean_claude_dir)

    assert current_snapshot == previous_snapshot, (
        f"File contents differ. "
        f"Previous keys: {sorted(previous_snapshot.keys())}, "
        f"Current keys: {sorted(current_snapshot.keys())}"
    )


@then("no duplicate files or directories exist")
def then_no_duplicates(clean_claude_dir: Path):
    """Verify no duplicated skill directories or template files."""
    # Check skills: no duplicate nw-* dirs
    skills_dir = clean_claude_dir / "skills"
    if skills_dir.exists():
        nw_dirs = [d.name for d in skills_dir.iterdir() if d.name.startswith("nw-")]
        assert len(nw_dirs) == len(set(nw_dirs)), (
            f"Duplicate skill directories: {nw_dirs}"
        )

    # Check templates: no duplicate files
    templates_dir = clean_claude_dir / "templates"
    if templates_dir.exists():
        files = [f.name for f in templates_dir.iterdir() if f.is_file()]
        assert len(files) == len(set(files)), f"Duplicate template files: {files}"


@then("the installer warns about conflicting command sources")
def then_warns_about_conflict(
    install_results: dict[str, PluginResult],
    scenario_state: dict,
):
    """Verify the installer warns about CLI/plugin command coexistence."""
    # Check any plugin result for a warning about conflicting sources.
    # This could be in the commands plugin result or a preflight check.
    all_messages = " ".join(r.message for r in install_results.values())
    assert "plugin" in all_messages.lower() or "conflict" in all_messages.lower(), (
        f"No warning about conflicting command sources found in: {all_messages}"
    )


@then("the warning recommends removing one installation method")
def then_recommends_removal(
    install_results: dict[str, PluginResult],
):
    """Verify the warning includes actionable remediation advice."""
    all_messages = " ".join(r.message for r in install_results.values())
    assert "remove" in all_messages.lower() or "uninstall" in all_messages.lower(), (
        f"No remediation advice found in: {all_messages}"
    )


@then("the installer reports the cleanup failure with a clear message")
def then_reports_cleanup_failure(templates_result: PluginResult):
    """Verify the plugin reports failure clearly when cleanup fails."""
    # The plugin should either succeed (having handled the error gracefully)
    # or fail with a clear message about the permission issue.
    if not templates_result.success:
        assert templates_result.errors, "Failed but no error details provided"
        error_text = " ".join(templates_result.errors)
        assert (
            "permission" in error_text.lower() or "read-only" in error_text.lower()
        ), f"Error message does not mention permission issue: {error_text}"


@then("the installation continues without crashing")
def then_no_crash(templates_result: PluginResult):
    """Verify the plugin did not raise an unhandled exception."""
    # If we got here, no exception was raised. The result exists.
    assert templates_result is not None, "Plugin result is None -- unexpected crash"


@then("the installer creates the necessary directories")
def then_directories_created(
    clean_claude_dir: Path,
    install_results: dict[str, PluginResult],
):
    """Verify installation creates target directories as needed."""
    # At minimum, the skills directory should be created (or skipped gracefully)
    # The important thing is no error from missing directories
    for plugin_name, result in install_results.items():
        assert result.success, (
            f"Plugin {plugin_name} failed on fresh install: {result.message}"
        )


@then("the installation completes successfully without cleanup errors")
def then_no_cleanup_errors(install_results: dict[str, PluginResult]):
    """Verify all plugins succeeded without cleanup-related errors."""
    for plugin_name, result in install_results.items():
        assert result.success, f"Plugin {plugin_name} failed: {result.message}"
        if result.errors:
            error_text = " ".join(result.errors)
            assert "cleanup" not in error_text.lower(), (
                f"Cleanup error in {plugin_name}: {error_text}"
            )
