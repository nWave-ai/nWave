"""Common step definitions for manifest circular dependency bug tests."""

import pytest
from pytest_bdd import given, parsers, then


@given("I have a clean test environment")
def clean_test_environment(tmp_path_factory):
    """Set up a clean temporary test environment."""
    test_dir = tmp_path_factory.mktemp("manifest_bug_test")
    pytest.test_dir = test_dir
    pytest.claude_dir = test_dir / ".claude"
    pytest.claude_dir.mkdir(parents=True, exist_ok=True)


@given("no nWave installation exists")
def no_existing_installation():
    """Verify no nWave installation exists in test environment."""
    assert not (pytest.claude_dir / "agents").exists()
    assert not (pytest.claude_dir / "commands").exists()
    assert not (pytest.claude_dir / "nwave-manifest.txt").exists()


@then(parsers.parse("the installer should exit with code {code:d}"))
def check_exit_code(code: int):
    """Verify the installer exit code."""
    assert pytest.install_result.returncode == code, (
        f"Expected exit code {code}, got {pytest.install_result.returncode}. "
        f"Output: {pytest.install_result.stdout}\\nError: {pytest.install_result.stderr}"
    )
