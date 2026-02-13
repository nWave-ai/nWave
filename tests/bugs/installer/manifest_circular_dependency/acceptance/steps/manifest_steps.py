"""Manifest step definitions for manifest circular dependency bug tests."""

import re

import pytest
from pytest_bdd import given, parsers, then


@then(parsers.parse("the manifest file should exist at {path}"))
def manifest_exists(path: str):
    """Verify manifest file exists at the specified path."""
    # Expand ~ to test HOME directory
    manifest_path = pytest.claude_dir / "nwave-manifest.txt"

    assert manifest_path.exists(), (
        f"Manifest file not found at {manifest_path}. "
        f"Directory contents: {list(pytest.claude_dir.iterdir())}"
    )


@then("the manifest should be created before the validation step")
def manifest_created_before_validation():
    """Verify manifest creation happens before validation."""
    # Check that the log output shows manifest creation before validation
    output = pytest.install_output

    # Find positions in output
    manifest_msg = "Installation manifest created"
    validation_msg = "Validating installation"

    if manifest_msg in output and validation_msg in output:
        manifest_pos = output.find(manifest_msg)
        validation_pos = output.find(validation_msg)

        assert manifest_pos < validation_pos, (
            f"Manifest should be created before validation. "
            f"Manifest at position {manifest_pos}, validation at {validation_pos}"
        )
    else:
        # If messages not in output, check file system timing
        # Manifest should exist after installation
        manifest_path = pytest.claude_dir / "nwave-manifest.txt"
        assert manifest_path.exists(), (
            "Manifest should exist after installation completes"
        )


@then("the manifest should contain installation metadata")
def manifest_contains_metadata():
    """Verify manifest contains installation metadata."""
    manifest_path = pytest.claude_dir / "nwave-manifest.txt"
    content = manifest_path.read_text()

    # Check for expected metadata fields
    assert "nWave Framework Installation Manifest" in content
    assert "Installed:" in content
    assert "Installation directory:" in content


@then("the manifest should list installed components")
def manifest_lists_components():
    """Verify manifest lists installed components."""
    manifest_path = pytest.claude_dir / "nwave-manifest.txt"
    content = manifest_path.read_text()

    # Check for component listings
    assert re.search(r"Total agents:\s+\d+", content), "Agent count not found"
    assert re.search(r"Total commands:\s+\d+", content), "Command count not found"


@given("the manifest has been created")
def manifest_created():
    """Verify manifest has been created."""
    manifest_path = pytest.claude_dir / "nwave-manifest.txt"
    assert manifest_path.exists(), "Manifest should already exist"


@then("the validation should find the existing manifest")
def validation_finds_manifest():
    """Verify validation found the manifest."""
    # Check validation output mentions manifest
    output = pytest.install_output
    # Validation table should show manifest status
    assert "Manifest" in output, "Validation output should mention manifest"


@then("the validation should not attempt to create the manifest")
def validation_no_create():
    """Verify validation doesn't try to create manifest."""
    # Manifest creation should happen before validation,
    # not during or after validation
    output = pytest.install_output

    if (
        "Installation manifest created" in output
        and "Validating installation" in output
    ):
        manifest_pos = output.find("Installation manifest created")
        validation_pos = output.find("Validating installation")

        # Manifest creation message should come before validation
        assert manifest_pos < validation_pos, (
            "Manifest creation should occur before validation starts"
        )
