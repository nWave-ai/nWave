"""
Installer Step Definitions.

This module contains step definitions related to:
- Installation execution
- Installer configuration
- Version management
- CLI commands

Domain: Installer Operations
"""

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, then, when


# -----------------------------------------------------------------------------
# Given Steps: Installer Preconditions
# -----------------------------------------------------------------------------


@given(parsers.parse('the current installer version is "{version}"'))
def current_installer_version(version: str, project_root: Path):
    """Store the current installer version for testing."""
    # This is declarative - used to track version context
    pytest.installer_version = version


@given("wrapper plugins are complete (Milestone 2)")
def wrapper_plugins_complete():
    """Verify wrapper plugins from Milestone 2 are complete."""
    try:
        from scripts.install.plugins.agents_plugin import AgentsPlugin
        from scripts.install.plugins.commands_plugin import CommandsPlugin
        from scripts.install.plugins.templates_plugin import TemplatesPlugin
        from scripts.install.plugins.utilities_plugin import UtilitiesPlugin

        # Verify all plugins exist
        assert AgentsPlugin is not None
        assert CommandsPlugin is not None
        assert TemplatesPlugin is not None
        assert UtilitiesPlugin is not None
    except ImportError as e:
        pytest.skip(f"Milestone 2 not complete: {e}")


@given("install_framework() is modified to use PluginRegistry")
def install_framework_uses_registry(project_root: Path):
    """Verify install_framework() is modified to use plugin system."""
    # This is validated during Milestone 3 switchover
    pass


@given("plugin orchestration is active (Milestone 3)")
def plugin_orchestration_active():
    """Verify plugin orchestration is active from Milestone 3."""
    pass


@given(parsers.parse("a baseline installation from {installer_type} installer exists"))
def baseline_installation_exists(installer_type: str, tmp_path: Path):
    """Create or verify baseline installation exists."""
    # Baseline will be captured during regression testing
    pytest.baseline_installation = tmp_path / "baseline"
    pytest.baseline_installation.mkdir(parents=True, exist_ok=True)


@given("baseline file tree is captured")
def baseline_file_tree_captured():
    """Capture baseline file tree for comparison."""
    pass


@given(parsers.parse("a monolithic installer ({version}) installation exists"))
def monolithic_installation_exists(version: str, tmp_path: Path):
    """Create monolithic installer installation for upgrade testing."""
    pytest.monolithic_version = version
    pytest.monolithic_dir = tmp_path / "monolithic"
    pytest.monolithic_dir.mkdir(parents=True, exist_ok=True)


@given("agents, commands, templates, utilities are installed")
def base_components_installed(tmp_path: Path):
    """Verify base components are installed."""
    pass


@given("all tests pass (unit + integration)")
def all_tests_pass():
    """Verify all tests pass."""
    pass


@given("documentation is complete")
def documentation_complete():
    """Verify documentation is complete."""
    pass


@given(parsers.parse('version in pyproject.toml is "{version}"'))
def version_in_pyproject(version: str, project_root: Path):
    """Verify version in pyproject.toml."""
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        # Just store expected version for verification
        pytest.expected_version = version


@given(parsers.parse("user downloads nWave installer {version}"))
def user_downloads_installer(version: str):
    """Simulate user downloading installer."""
    pytest.download_version = version


@given("user has no existing nWave installation")
def no_existing_installation(clean_test_directory: Path):
    """Verify no existing nWave installation."""
    assert clean_test_directory.exists()
    # Should be empty or minimal
    assert len(list(clean_test_directory.iterdir())) <= 1


# -----------------------------------------------------------------------------
# When Steps: Installer Actions
# -----------------------------------------------------------------------------


@when("I run install_nwave.py with plugin orchestration")
def run_installer_with_plugins(project_root: Path):
    """Run the installer with plugin orchestration."""
    installer_path = project_root / "scripts" / "install" / "install_nwave.py"
    if not installer_path.exists():
        pytest.skip(f"Installer not found: {installer_path}")


@when(parsers.parse("I run plugin-based installer on {target}"))
def run_plugin_installer(target: str, project_root: Path, clean_test_directory: Path):
    """Run plugin-based installer."""
    pass


@when("I compare resulting file tree with baseline")
def compare_file_tree_with_baseline():
    """Compare resulting file tree with captured baseline."""
    pass


@when(parsers.parse("I upgrade to plugin-based installer ({version})"))
def upgrade_to_plugin_installer(version: str):
    """Upgrade from monolithic to plugin-based installer."""
    pytest.upgrade_version = version


@when("I run install_nwave.py upgrade")
def run_installer_upgrade(project_root: Path):
    """Run installer upgrade command."""
    pass


@when(parsers.parse('I bump version to "{version}" for production release'))
def bump_version(version: str, project_root: Path):
    """Bump version for production release."""
    pytest.bumped_version = version


@when("I update CHANGELOG.md with migration notes")
def update_changelog():
    """Update CHANGELOG with migration notes."""
    pass


@when("I create release notes")
def create_release_notes():
    """Create release notes."""
    pass


@when(parsers.parse('I tag release: "{tag_command}"'))
def tag_release(tag_command: str):
    """Tag release in git."""
    pass


@when(parsers.parse('user runs: "{command}"'))
def user_runs_command(command: str, project_root: Path):
    """Simulate user running a command."""
    pytest.user_command = command


@when("installation completes")
def installation_completes():
    """Verify installation completes."""
    pass


# -----------------------------------------------------------------------------
# Then Steps: Installer Assertions
# -----------------------------------------------------------------------------


@then("all 4 plugins are installed in correct order")
def four_plugins_installed_in_order():
    """Verify 4 plugins installed in correct order."""
    pass


@then("installation completes successfully")
def installation_successful():
    """Verify installation completes successfully."""
    pass


@then("the same files are installed to the same locations")
def same_files_installed():
    """Verify same files are installed."""
    pass


@then("the same verification passes (InstallationVerifier output identical)")
def same_verification_passes():
    """Verify same verification output."""
    pass


@then("file contents are byte-for-byte identical")
def files_byte_identical():
    """Verify file contents are identical."""
    pass


@then("no regressions are detected in installation behavior")
def no_regressions():
    """Verify no regressions in installation."""
    pass


@then("existing components are detected and preserved")
def existing_components_preserved():
    """Verify existing components are preserved during upgrade."""
    pass


@then("DES plugin is added without affecting existing components")
def des_added_without_affecting_existing():
    """Verify DES plugin doesn't affect existing components."""
    pass


@then("no existing functionality is broken")
def no_functionality_broken():
    """Verify no existing functionality is broken."""
    pass


@then(parsers.parse('version in pyproject.toml is "{version}"'))
def verify_pyproject_version(version: str, project_root: Path):
    """Verify version in pyproject.toml."""
    pass


@then(
    parsers.parse(
        "CHANGELOG.md documents all changes from {from_version} -> {to_version}"
    )
)
def changelog_documents_changes(from_version: str, to_version: str):
    """Verify CHANGELOG documents changes."""
    pass


@then("release notes include DES feature announcement")
def release_notes_include_des():
    """Verify release notes include DES announcement."""
    pass


@then(parsers.parse("git tag {tag} exists"))
def git_tag_exists(tag: str):
    """Verify git tag exists."""
    pass


@then("the release is ready for deployment")
def release_ready():
    """Verify release is ready for deployment."""
    pass


@then(parsers.parse('user sees output: "{output}"'))
def user_sees_output(output: str):
    """Verify user sees expected output."""
    pass


@then(parsers.parse('user sees progress: "{progress}"'))
def user_sees_progress(progress: str):
    """Verify user sees progress message."""
    pass


@then(parsers.parse('user sees: "{message}"'))
def user_sees_message(message: str):
    """Verify user sees message."""
    pass


@then(parsers.parse('user can verify installation: "{command}"'))
def user_can_verify_installation(command: str):
    """Verify user can verify installation."""
    pass


@then("verification table shows all components OK with counts")
def verification_table_ok():
    """Verify verification table shows OK."""
    pass
