"""
Unit Tests for DESPlugin Graceful Failure (Step 03-04).

Tests for DESPlugin prerequisite validation and graceful failure handling.
Ensures clear error messages and no partial installation on failure.

Acceptance Criteria:
1. When DES scripts missing, returns PluginResult(success=False)
2. Error message contains 'DES scripts not found: nWave/scripts/des/'
3. When DES templates missing, error message explains what's missing
4. No partial DES files installed on failure
5. Error logged with clear remediation steps

Domain: Plugin Infrastructure - DES Plugin Error Handling
"""

import logging
from pathlib import Path

import pytest

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.des_plugin_errors")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    current = Path(__file__).resolve()
    return current.parents[4]


@pytest.fixture
def clean_test_directory(tmp_path: Path) -> Path:
    """Provide a clean test installation directory simulating ~/.claude."""
    test_dir = tmp_path / ".claude"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


@pytest.fixture
def isolated_project_with_des_source_only(tmp_path: Path) -> Path:
    """Create isolated project with DES source but NO scripts/templates."""
    isolated_root = tmp_path / "isolated_project"
    isolated_root.mkdir(parents=True, exist_ok=True)

    # Create src/des with minimal valid structure
    src_des = isolated_root / "src" / "des"
    src_des.mkdir(parents=True, exist_ok=True)
    (src_des / "__init__.py").write_text("# DES module\n")
    (src_des / "application").mkdir(parents=True, exist_ok=True)
    (src_des / "application" / "__init__.py").write_text("# Application layer\n")
    (src_des / "domain").mkdir(parents=True, exist_ok=True)
    (src_des / "domain" / "__init__.py").write_text("# Domain layer\n")

    # DO NOT create nWave/scripts/des/ or nWave/templates/
    return isolated_root


@pytest.fixture
def isolated_project_with_scripts_only(
    tmp_path: Path, project_root: Path, shared_des_source: Path
) -> Path:
    """Create isolated project with DES scripts but NO templates."""
    isolated_root = tmp_path / "isolated_scripts_only"
    isolated_root.mkdir(parents=True, exist_ok=True)

    # Symlink src/des from the session-scoped shared copy
    src_des = isolated_root / "src" / "des"
    src_des.parent.mkdir(parents=True, exist_ok=True)
    src_des.symlink_to(shared_des_source)

    # Create nWave/scripts/des/ with scripts
    scripts_dir = isolated_root / "nWave" / "scripts" / "des"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "check_stale_phases.py").write_text(
        "#!/usr/bin/env python3\n# check stale phases\n"
    )
    (scripts_dir / "scope_boundary_check.py").write_text(
        "#!/usr/bin/env python3\n# scope boundary check\n"
    )

    # DO NOT create nWave/templates/ with DES templates
    return isolated_root


@pytest.fixture
def context_with_missing_prerequisites(
    clean_test_directory: Path,
    isolated_project_with_des_source_only: Path,
    test_logger: logging.Logger,
) -> InstallContext:
    """Create InstallContext with missing scripts and templates."""
    return InstallContext(
        claude_dir=clean_test_directory,
        scripts_dir=isolated_project_with_des_source_only / "scripts" / "install",
        templates_dir=isolated_project_with_des_source_only / "nWave" / "templates",
        logger=test_logger,
        project_root=isolated_project_with_des_source_only,
        framework_source=None,
        dry_run=False,
    )


@pytest.fixture
def context_with_missing_templates(
    clean_test_directory: Path,
    isolated_project_with_scripts_only: Path,
    test_logger: logging.Logger,
) -> InstallContext:
    """Create InstallContext with scripts but missing templates."""
    return InstallContext(
        claude_dir=clean_test_directory,
        scripts_dir=isolated_project_with_scripts_only / "scripts" / "install",
        templates_dir=isolated_project_with_scripts_only / "nWave" / "templates",
        logger=test_logger,
        project_root=isolated_project_with_scripts_only,
        framework_source=None,
        dry_run=False,
    )


# -----------------------------------------------------------------------------
# Test: Prerequisite Validation Method
# -----------------------------------------------------------------------------


class TestDESPluginValidatePrerequisites:
    """Tests for DESPlugin prerequisite validation."""

    def test_validate_prerequisites_returns_false_when_scripts_missing(
        self, context_with_missing_prerequisites: InstallContext
    ):
        """validate_prerequisites() returns failure when scripts missing."""
        plugin = DESPlugin()

        result = plugin.validate_prerequisites(context_with_missing_prerequisites)

        assert not result.success
        assert "scripts" in result.message.lower()

    def test_validate_prerequisites_error_mentions_scripts_path(
        self, context_with_missing_prerequisites: InstallContext
    ):
        """validate_prerequisites() error mentions the missing scripts path."""
        plugin = DESPlugin()

        result = plugin.validate_prerequisites(context_with_missing_prerequisites)

        assert not result.success
        # Should mention the path where scripts should be
        assert (
            "nwave/scripts/des" in result.message.lower()
            or "nwave\\scripts\\des" in result.message.lower()
        )

    def test_validate_prerequisites_returns_false_when_templates_missing(
        self, context_with_missing_templates: InstallContext
    ):
        """validate_prerequisites() returns failure when templates missing."""
        plugin = DESPlugin()

        result = plugin.validate_prerequisites(context_with_missing_templates)

        assert not result.success
        assert "template" in result.message.lower()

    def test_validate_prerequisites_includes_remediation_steps(
        self, context_with_missing_prerequisites: InstallContext
    ):
        """validate_prerequisites() includes remediation guidance."""
        plugin = DESPlugin()

        result = plugin.validate_prerequisites(context_with_missing_prerequisites)

        assert not result.success
        # Should have some remediation keywords
        remediation_keywords = [
            "ensure",
            "verify",
            "create",
            "run",
            "required",
            "prerequisite",
        ]
        all_text = (
            result.message.lower() + " ".join(result.errors).lower()
            if result.errors
            else result.message.lower()
        )
        has_remediation = any(keyword in all_text for keyword in remediation_keywords)
        assert has_remediation, f"No remediation guidance found in: {result.message}"


# -----------------------------------------------------------------------------
# Test: Install Method with Missing Prerequisites
# -----------------------------------------------------------------------------


class TestDESPluginInstallWithMissingPrerequisites:
    """Tests for DESPlugin.install() when prerequisites are missing."""

    def test_install_fails_when_scripts_missing(
        self, context_with_missing_prerequisites: InstallContext
    ):
        """install() returns failure when DES scripts are missing."""
        plugin = DESPlugin()

        result = plugin.install(context_with_missing_prerequisites)

        assert not result.success
        assert result.plugin_name == "des"

    def test_install_error_message_mentions_missing_scripts(
        self, context_with_missing_prerequisites: InstallContext
    ):
        """install() error message mentions missing scripts."""
        plugin = DESPlugin()

        result = plugin.install(context_with_missing_prerequisites)

        assert not result.success
        all_text = result.message.lower()
        assert "script" in all_text or "nwave/scripts/des" in all_text

    def test_install_does_not_create_partial_files_when_scripts_missing(
        self, context_with_missing_prerequisites: InstallContext
    ):
        """install() does not create partial files when scripts missing."""
        plugin = DESPlugin()

        result = plugin.install(context_with_missing_prerequisites)

        assert not result.success

        # Check no partial DES files were created
        des_lib = (
            context_with_missing_prerequisites.claude_dir / "lib" / "python" / "des"
        )
        des_scripts = context_with_missing_prerequisites.claude_dir / "scripts"
        des_templates = context_with_missing_prerequisites.claude_dir / "templates"

        # None of the DES directories should have content
        if des_lib.exists():
            assert not list(des_lib.iterdir()), "Partial DES module created"
        if des_scripts.exists():
            des_script_files = [
                f for f in des_scripts.iterdir() if f.name in DESPlugin.DES_SCRIPTS
            ]
            assert not des_script_files, (
                f"Partial DES scripts created: {des_script_files}"
            )
        if des_templates.exists():
            des_template_files = [
                f for f in des_templates.iterdir() if f.name in DESPlugin.DES_TEMPLATES
            ]
            assert not des_template_files, (
                f"Partial DES templates created: {des_template_files}"
            )

    def test_install_fails_when_templates_missing(
        self, context_with_missing_templates: InstallContext
    ):
        """install() returns failure when DES templates are missing."""
        plugin = DESPlugin()

        result = plugin.install(context_with_missing_templates)

        assert not result.success
        assert "template" in result.message.lower()


# -----------------------------------------------------------------------------
# Test: Error Message Quality
# -----------------------------------------------------------------------------


class TestDESPluginErrorMessageQuality:
    """Tests for quality of error messages in DESPlugin."""

    def test_error_message_is_actionable(
        self, context_with_missing_prerequisites: InstallContext
    ):
        """Error message provides actionable guidance."""
        plugin = DESPlugin()

        result = plugin.install(context_with_missing_prerequisites)

        assert not result.success

        # Should mention specific file or directory
        all_text = result.message + " ".join(result.errors if result.errors else [])
        has_path_info = "/" in all_text or "\\" in all_text or "nWave" in all_text

        assert has_path_info, f"Error lacks specific path info: {all_text}"

    def test_error_identifies_which_prerequisites_missing(
        self, context_with_missing_prerequisites: InstallContext
    ):
        """Error identifies specifically which prerequisites are missing."""
        plugin = DESPlugin()

        result = plugin.install(context_with_missing_prerequisites)

        assert not result.success

        # Should distinguish between scripts and templates
        all_text = result.message.lower()
        has_specific_issue = "script" in all_text or "template" in all_text

        assert has_specific_issue, (
            f"Error doesn't identify specific missing item: {result.message}"
        )


# -----------------------------------------------------------------------------
# Test: Successful Prerequisites Validation
# -----------------------------------------------------------------------------


class TestDESPluginValidatePrerequisitesSuccess:
    """Tests for DESPlugin prerequisite validation when prerequisites exist."""

    def test_validate_prerequisites_succeeds_when_all_present(
        self,
        project_root: Path,
        clean_test_directory: Path,
        test_logger: logging.Logger,
    ):
        """validate_prerequisites() succeeds when all prerequisites exist."""
        # Use real project root where prerequisites exist
        context = InstallContext(
            claude_dir=clean_test_directory,
            scripts_dir=project_root / "scripts" / "install",
            templates_dir=project_root / "nWave" / "templates",
            logger=test_logger,
            project_root=project_root,
            framework_source=None,
            dry_run=False,
        )

        plugin = DESPlugin()

        result = plugin.validate_prerequisites(context)

        assert result.success, f"Expected success but got: {result.message}"
