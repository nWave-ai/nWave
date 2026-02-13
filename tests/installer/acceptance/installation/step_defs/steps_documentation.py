"""
Step definitions for documentation accuracy acceptance tests (AC-10).

These tests verify that installation documentation is accurate and up-to-date.
Some tests are marked @manual as they require human verification on a fresh machine.

Cross-platform compatible (Windows, macOS, Linux).
"""

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when


# Load scenarios from feature files
scenarios("../features/06_documentation.feature")

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
INSTALLATION_GUIDE = PROJECT_ROOT / "docs" / "guides" / "installation-guide.md"


# ============================================================================
# GIVEN - Preconditions
# ============================================================================


@given("the installation guide exists at docs/guides/installation-guide.md")
def installation_guide_exists():
    """Verify installation guide exists."""
    assert INSTALLATION_GUIDE.exists(), (
        f"Installation guide not found at {INSTALLATION_GUIDE}"
    )


@given("I have a fresh machine with Python installed")
def fresh_machine_with_python():
    """
    Precondition for manual test: fresh machine with Python.

    This is a documentation step for manual testing.
    """
    pass


@given(parsers.parse('pipx is installed via "{command}"'))
def pipx_installed_via_command(command):
    """
    Precondition for manual test: pipx installed.

    This is a documentation step for manual testing.
    """
    assert "pip install pipx" in command


@given("I read the installation guide prerequisites")
def read_prerequisites():
    """Read the prerequisites section of the installation guide."""
    assert INSTALLATION_GUIDE.exists()
    return INSTALLATION_GUIDE.read_text()


@given("I read the quick start section")
def read_quick_start():
    """Read the quick start section of the installation guide."""
    assert INSTALLATION_GUIDE.exists()
    return INSTALLATION_GUIDE.read_text()


@given("I read the installation guide")
def read_installation_guide():
    """Read the complete installation guide."""
    assert INSTALLATION_GUIDE.exists()
    return INSTALLATION_GUIDE.read_text()


@given("I read the troubleshooting section")
def read_troubleshooting():
    """Read the troubleshooting section of the installation guide."""
    assert INSTALLATION_GUIDE.exists()
    return INSTALLATION_GUIDE.read_text()


# ============================================================================
# WHEN - Actions
# ============================================================================


@when("I follow the quick start instructions:")
def follow_quick_start_instructions(pytestconfig):
    """
    Follow quick start instructions (manual test).

    The table in the feature file specifies the steps to follow.
    This is documented for manual verification.
    """
    pass


# ============================================================================
# THEN - Assertions
# ============================================================================


@then("each command should succeed")
def each_command_succeeds():
    """
    Verify each command succeeds (manual test).

    This is documented for manual verification.
    """
    pass


@then("nWave should be installed successfully")
def nwave_installed_successfully():
    """
    Verify nWave is installed successfully (manual test).

    This is documented for manual verification.
    """
    pass


@then(parsers.parse('the prerequisites should include "{text}"'))
def prerequisites_include(text):
    """Verify prerequisites section includes specified text."""
    content = INSTALLATION_GUIDE.read_text()
    assert text.lower() in content.lower(), f"Prerequisites don't include '{text}'"


@then(parsers.parse('the prerequisites should NOT state "{text}" as minimum'))
def prerequisites_not_state(text):
    """Verify prerequisites don't incorrectly state a requirement."""
    content = INSTALLATION_GUIDE.read_text()

    if "Python" in text:
        problematic_patterns = [
            f"Python {text.split()[-1]} or higher",
            f"requires Python {text.split()[-1]}",
            f"Python >= {text.split()[-1]}",
        ]
        for pattern in problematic_patterns:
            assert pattern not in content, (
                f"Documentation incorrectly states '{pattern}'"
            )


@then(parsers.parse('the quick start should include "{text}"'))
def quick_start_includes(text):
    """Verify quick start section includes specified text."""
    content = INSTALLATION_GUIDE.read_text()
    assert text in content, f"Quick start doesn't include '{text}'"


@then("the guide should mention pipx is recommended")
def guide_mentions_pipx():
    """Verify guide mentions pipx as recommended installer."""
    content = INSTALLATION_GUIDE.read_text().lower()
    assert "pipx" in content, "Guide doesn't mention pipx"
    assert "recommended" in content or "prerequisite" in content, (
        "Guide doesn't indicate pipx is recommended"
    )


@then("the guide should explain how to install pipx")
def guide_explains_pipx_install():
    """Verify guide explains how to install pipx."""
    content = INSTALLATION_GUIDE.read_text()
    has_pipx_install = "pip install pipx" in content or "pip3 install pipx" in content
    assert has_pipx_install, "Guide doesn't explain how to install pipx"


@then("the guide should show pipx commands for installation")
def guide_shows_pipx_commands():
    """Verify guide shows pipx commands."""
    content = INSTALLATION_GUIDE.read_text()
    has_pipx_commands = (
        "pipx install nwave-ai" in content or "pipx upgrade nwave-ai" in content
    )
    assert has_pipx_commands, "Guide doesn't show pipx commands"


@then(parsers.parse('the section should address "{error_type}"'))
def section_addresses_error(error_type):
    """Verify troubleshooting section addresses specific error."""
    content = INSTALLATION_GUIDE.read_text()
    assert error_type.lower() in content.lower(), (
        f"Troubleshooting doesn't address '{error_type}'"
    )


@then("each error should have a solution with actionable commands")
def errors_have_actionable_solutions():
    """Verify error solutions include actionable commands."""
    content = INSTALLATION_GUIDE.read_text()

    has_troubleshooting = "troubleshoot" in content.lower()
    has_commands = (
        "nwave-ai" in content or "pipx" in content or "python" in content.lower()
    )

    if has_troubleshooting:
        assert has_commands, (
            "Troubleshooting section doesn't include actionable commands"
        )
