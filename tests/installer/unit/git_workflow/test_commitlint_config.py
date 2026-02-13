"""
Unit tests for commitlint configuration validation.

These tests verify that:
1. Commitlint configuration file exists in project root
2. Configuration is valid JSON/JS format
3. Configuration includes required conventional commit types
"""

import json
from pathlib import Path

import pytest


class TestCommitlintConfiguration:
    """Test commitlint configuration exists and is valid."""

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        # Navigate from tests/unit/git_workflow to project root
        current_file = Path(__file__)
        return current_file.parent.parent.parent.parent.parent

    def test_commitlint_config_exists(self, project_root):
        """Verify commitlint configuration file exists."""
        # Check for common commitlint config file names
        config_files = [
            project_root / ".commitlintrc.json",
            project_root / ".commitlintrc.js",
            project_root / "commitlint.config.js",
        ]

        config_exists = any(f.exists() for f in config_files)
        assert config_exists, (
            "No commitlint configuration found. Expected one of: "
            ".commitlintrc.json, .commitlintrc.js, commitlint.config.js"
        )

    def test_commitlint_config_is_valid_json(self, project_root):
        """Verify JSON configuration is parseable."""
        config_file = project_root / ".commitlintrc.json"

        if not config_file.exists():
            pytest.skip("JSON config not used (using JS config)")

        with open(config_file) as f:
            config = json.load(f)

        assert isinstance(config, dict), "Commitlint config must be a dictionary"

    def test_commitlint_config_extends_conventional(self, project_root):
        """Verify configuration extends conventional commits standard."""
        config_file = project_root / ".commitlintrc.json"

        if not config_file.exists():
            pytest.skip("JSON config not used (using JS config)")

        with open(config_file) as f:
            config = json.load(f)

        # Check for conventional commits extension
        assert "extends" in config, "Config must extend conventional commits"
        extends = config["extends"]
        if isinstance(extends, list):
            assert "@commitlint/config-conventional" in extends
        else:
            assert extends == "@commitlint/config-conventional"
