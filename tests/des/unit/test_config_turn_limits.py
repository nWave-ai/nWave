"""
Unit tests for ConfigLoader turn limit configuration.

Tests configuration module that defines turn limits by task type:
- quick=15
- background=25
- standard=30 (default)
- research=35
- complex=50
- Default fallback to standard (30) if type not specified

See src/des/config/des_defaults.yaml for configuration.
"""

import json
import tempfile
from pathlib import Path

import pytest


class TestConfigLoaderTurnLimits:
    """Test ConfigLoader reads and validates turn limit configuration."""

    def test_load_turn_limits_from_config_file(self):
        """ConfigLoader reads turn limits from configuration file."""
        # Given: Config file with turn limits by task type
        config_data = {"turn_limits": {"quick": 20, "standard": 50, "complex": 100}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            # When: ConfigLoader loads the configuration
            from des.application.config_loader import ConfigLoader

            loader = ConfigLoader(config_path)

            # Then: Turn limits are correctly loaded
            assert loader.get_turn_limit("quick") == 20
            assert loader.get_turn_limit("standard") == 50
            assert loader.get_turn_limit("complex") == 100
        finally:
            Path(config_path).unlink()

    def test_default_fallback_to_standard_when_type_not_specified(self):
        """Default fallback to standard (30 turns) if type not specified."""
        # Given: Config file with standard turn limit
        config_data = {"turn_limits": {"standard": 30}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            # When: ConfigLoader requests unknown task type
            from des.application.config_loader import ConfigLoader

            loader = ConfigLoader(config_path)

            # Then: Returns standard fallback value
            assert loader.get_turn_limit("unknown_type") == 30
            assert loader.get_turn_limit(None) == 30
        finally:
            Path(config_path).unlink()

    def test_validates_turn_limits_are_positive_integers(self):
        """Schema validates turn_count as non-negative integer."""
        # Given: Config file with invalid turn limit (negative)
        config_data = {"turn_limits": {"quick": -10, "standard": 50}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            # When/Then: ConfigLoader raises validation error
            from des.application.config_loader import (
                ConfigLoader,
                ConfigValidationError,
            )

            with pytest.raises(ConfigValidationError, match="must be positive"):
                ConfigLoader(config_path)
        finally:
            Path(config_path).unlink()

    def test_handles_missing_config_file_gracefully(self):
        """ConfigLoader handles missing config file with sensible defaults."""
        # Given: Non-existent config file path
        from des.application.config_loader import ConfigLoader

        # When: ConfigLoader initialized with missing file
        loader = ConfigLoader("/nonexistent/path/config.json")

        # Then: Uses built-in defaults (see src/des/config/des_defaults.yaml)
        assert loader.get_turn_limit("quick") == 15
        assert loader.get_turn_limit("background") == 25
        assert loader.get_turn_limit("standard") == 30
        assert loader.get_turn_limit("research") == 35
        assert loader.get_turn_limit("complex") == 50
