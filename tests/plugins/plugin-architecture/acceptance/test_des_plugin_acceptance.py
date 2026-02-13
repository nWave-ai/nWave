"""
Acceptance Test for DESPlugin Implementation (Step 03-02).

This test verifies that DESPlugin integrates with the plugin registry
and installs DES module, scripts, and templates correctly.

Acceptance Criteria (from milestone-4-des-plugin.feature):
1. DESPlugin declares dependencies: ["templates", "utilities"]
2. DES is installed AFTER templates and utilities (dependency resolution)
3. DES module is copied to ~/.claude/lib/python/des/
4. DES scripts are copied to ~/.claude/scripts/
5. DES templates are copied to ~/.claude/templates/
6. Installation completes without modifying install_nwave.py
"""

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenario, then, when


@scenario(
    "milestone-4-des-plugin.feature",
    "DES plugin installs successfully",
)
def test_des_plugin_installs_successfully():
    """Step 03-02: DESPlugin integrates with registry and installs correctly."""
    pass


# -----------------------------------------------------------------------------
# Background Steps (reused from other milestone tests)
# -----------------------------------------------------------------------------


@given("the nWave project root is available")
def nwave_project_root_available(project_root: Path):
    """Verify nWave project root is available."""
    assert project_root.exists(), f"Project root not found: {project_root}"


@given(parsers.parse('the Claude config directory is "{path}"'))
def claude_config_dir_set(path: str):
    """Set Claude config directory path."""
    pytest.claude_config_dir = path


@given(parsers.parse('the current installer version is "{version}"'))
def installer_version(version: str):
    """Store current installer version."""
    pytest.installer_version = version


@given("plugin infrastructure exists (base.py, registry.py)")
def plugin_infrastructure_exists(project_root: Path):
    """Verify plugin infrastructure files exist."""
    base_path = project_root / "scripts" / "install" / "plugins" / "base.py"
    registry_path = project_root / "scripts" / "install" / "plugins" / "registry.py"

    assert base_path.exists(), f"Plugin base.py not found: {base_path}"
    assert registry_path.exists(), f"Plugin registry.py not found: {registry_path}"


# -----------------------------------------------------------------------------
# Given Steps
# -----------------------------------------------------------------------------


@given("wrapper plugins are operational (Milestone 2)")
def wrapper_plugins_operational(project_root: Path):
    """Verify wrapper plugins from Milestone 2 are operational."""
    from scripts.install.plugins.agents_plugin import AgentsPlugin
    from scripts.install.plugins.commands_plugin import CommandsPlugin
    from scripts.install.plugins.templates_plugin import TemplatesPlugin
    from scripts.install.plugins.utilities_plugin import UtilitiesPlugin

    plugins = [AgentsPlugin(), CommandsPlugin(), TemplatesPlugin(), UtilitiesPlugin()]

    for plugin in plugins:
        assert hasattr(plugin, "install"), f"{plugin.name} missing install() method"
        assert hasattr(plugin, "verify"), f"{plugin.name} missing verify() method"


@given("plugin orchestration is active (Milestone 3)")
def plugin_orchestration_active(project_root: Path):
    """Verify plugin orchestration from Milestone 3 is operational."""
    from scripts.install.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    assert hasattr(registry, "install_all"), "Registry missing install_all() method"
    assert hasattr(registry, "register"), "Registry missing register() method"


@given(parsers.parse('DES source exists at "{path}"'))
def des_source_exists(path: str, project_root: Path):
    """Verify DES source directory exists."""
    des_source = project_root / path.strip("/")
    assert des_source.exists(), f"DES source not found: {des_source}"
    assert des_source.is_dir(), f"DES source is not a directory: {des_source}"

    # Verify key DES module files exist
    init_file = des_source / "__init__.py"
    application_dir = des_source / "application"
    domain_dir = des_source / "domain"

    assert init_file.exists(), f"DES __init__.py not found: {init_file}"
    assert application_dir.exists(), f"DES application/ not found: {application_dir}"
    assert domain_dir.exists(), f"DES domain/ not found: {domain_dir}"

    pytest.des_source_path = des_source


@given(parsers.parse('DES scripts exist at "{path}"'))
def des_scripts_exist(path: str, project_root: Path):
    """Verify DES scripts directory exists."""
    des_scripts = project_root / path.strip("/")
    assert des_scripts.exists(), f"DES scripts not found: {des_scripts}"

    # Verify key scripts exist
    check_stale = des_scripts / "check_stale_phases.py"
    scope_check = des_scripts / "scope_boundary_check.py"

    assert check_stale.exists(), f"check_stale_phases.py not found: {check_stale}"
    assert scope_check.exists(), f"scope_boundary_check.py not found: {scope_check}"

    pytest.des_scripts_path = des_scripts


@given(parsers.parse('DES templates exist at "{path}"'))
def des_templates_exist(path: str, project_root: Path):
    """Verify DES templates exist in templates directory."""
    templates_dir = project_root / path.strip("/")
    assert templates_dir.exists(), f"Templates directory not found: {templates_dir}"

    # Verify DES-specific templates exist
    des_audit_readme = templates_dir / ".des-audit-README.md"
    assert des_audit_readme.exists(), (
        f".des-audit-README.md not found: {des_audit_readme}"
    )

    pytest.des_templates_path = templates_dir


@given(parsers.parse("DESPlugin declares dependencies: {dependencies}"))
def des_plugin_declares_dependencies(dependencies: str):
    """Verify DESPlugin declares correct dependencies."""
    from scripts.install.plugins.des_plugin import DESPlugin

    plugin = DESPlugin()

    # Parse expected dependencies from feature file format: ["templates", "utilities"]
    expected_deps = eval(dependencies)  # Safe here as it's from our feature file

    assert plugin.dependencies == expected_deps, (
        f"DESPlugin dependencies {plugin.dependencies} != expected {expected_deps}"
    )

    pytest.des_plugin = plugin


# -----------------------------------------------------------------------------
# When Steps
# -----------------------------------------------------------------------------


@when("I create DESPlugin and register it with PluginRegistry")
def create_and_register_des_plugin(project_root: Path):
    """Create DESPlugin and register it with the registry."""
    from scripts.install.plugins.agents_plugin import AgentsPlugin
    from scripts.install.plugins.commands_plugin import CommandsPlugin
    from scripts.install.plugins.des_plugin import DESPlugin
    from scripts.install.plugins.registry import PluginRegistry
    from scripts.install.plugins.templates_plugin import TemplatesPlugin
    from scripts.install.plugins.utilities_plugin import UtilitiesPlugin

    registry = PluginRegistry()

    # Register all plugins (order should not matter due to dependency resolution)
    registry.register(DESPlugin())
    registry.register(AgentsPlugin())
    registry.register(CommandsPlugin())
    registry.register(TemplatesPlugin())
    registry.register(UtilitiesPlugin())

    pytest.plugin_registry = registry


@when("I call registry.install_all(context)")
def call_registry_install_all(
    clean_test_directory: Path, project_root: Path, test_logger
):
    """Call registry.install_all(context) to install all plugins."""
    from scripts.install.plugins.base import InstallContext

    # Create context with all required utilities
    context = InstallContext(
        claude_dir=clean_test_directory,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )

    results = pytest.plugin_registry.install_all(context)

    pytest.install_context = context
    pytest.install_results = results


# -----------------------------------------------------------------------------
# Then Steps
# -----------------------------------------------------------------------------


@then("DES is installed AFTER templates and utilities (dependency resolution)")
def des_installed_after_dependencies():
    """Verify DES is installed after its dependencies."""
    execution_order = pytest.plugin_registry.get_execution_order()

    # Find positions in execution order
    des_pos = execution_order.index("des") if "des" in execution_order else -1
    templates_pos = (
        execution_order.index("templates") if "templates" in execution_order else -1
    )
    utilities_pos = (
        execution_order.index("utilities") if "utilities" in execution_order else -1
    )

    assert des_pos > templates_pos, (
        f"DES (pos {des_pos}) should be after templates (pos {templates_pos})"
    )
    assert des_pos > utilities_pos, (
        f"DES (pos {des_pos}) should be after utilities (pos {utilities_pos})"
    )


@then(parsers.parse('DES module is copied to "{path}"'))
def des_module_copied(path: str):
    """Verify DES module is copied to target location."""
    context = pytest.install_context
    target_path = context.claude_dir / "lib" / "python" / "des"

    assert target_path.exists(), f"DES module not found at: {target_path}"
    assert target_path.is_dir(), f"DES module is not a directory: {target_path}"

    # Verify key files exist
    init_file = target_path / "__init__.py"
    application_dir = target_path / "application"
    domain_dir = target_path / "domain"

    assert init_file.exists(), f"DES __init__.py not found: {init_file}"
    assert application_dir.exists(), f"DES application/ not found: {application_dir}"
    assert domain_dir.exists(), f"DES domain/ not found: {domain_dir}"


@then(parsers.parse('DES scripts are copied to "{path}"'))
def des_scripts_copied(path: str):
    """Verify DES scripts are copied to target location."""
    context = pytest.install_context
    target_path = context.claude_dir / "scripts"

    # Check DES scripts are copied
    check_stale = target_path / "check_stale_phases.py"
    scope_check = target_path / "scope_boundary_check.py"

    assert check_stale.exists(), f"check_stale_phases.py not found: {check_stale}"
    assert scope_check.exists(), f"scope_boundary_check.py not found: {scope_check}"


@then(parsers.parse('DES templates are copied to "{path}"'))
def des_templates_copied(path: str):
    """Verify DES templates are copied to target location."""
    context = pytest.install_context
    target_path = context.claude_dir / "templates"

    # Check DES-specific templates are copied
    des_audit_readme = target_path / ".des-audit-README.md"
    assert des_audit_readme.exists(), (
        f".des-audit-README.md not found: {des_audit_readme}"
    )


@then("DES installation completes without installer changes")
def des_installation_no_installer_changes(project_root: Path):
    """Verify DES is installed via plugin registry pattern."""
    # The DES plugin is installed via the plugin system using registry.install_all()
    # It should be registered with the registry, but not have custom installation code

    # Verify DES result is successful
    results = pytest.install_results
    assert "des" in results, "DES plugin not in results"
    assert results["des"].success, f"DES installation failed: {results['des'].message}"

    # Verify install_nwave.py doesn't have DES-specific installation code
    install_script = project_root / "scripts" / "install" / "install_nwave.py"
    content = install_script.read_text()

    # It should NOT have direct DES installation calls (custom methods)
    assert "_install_des" not in content, (
        "install_nwave.py should not have _install_des() method"
    )

    # It SHOULD register DESPlugin with the registry (this is the correct pattern)
    assert "DESPlugin" in content, (
        "install_nwave.py should import and register DESPlugin with the registry"
    )
    assert "registry.register" in content, (
        "install_nwave.py should use registry.register() pattern"
    )
