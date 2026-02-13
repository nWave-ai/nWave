"""Unit tests for turn limit configuration module.

Business Value: Validates task type-based turn limits for fine-grained control.
"""

import pytest

from des.domain.turn_config import ConfigLoader, TurnLimitConfig


class TestTurnLimitConfig:
    """Tests for TurnLimitConfig value object."""

    def test_turn_limit_config_stores_limits_by_task_type(self):
        """TurnLimitConfig provides task type-specific turn limits."""
        config = TurnLimitConfig(quick=20, standard=50, complex=100)

        assert config.quick == 20
        assert config.standard == 50
        assert config.complex == 100

    def test_turn_limit_config_has_default_fallback(self):
        """TurnLimitConfig defaults to standard limit when type unknown."""
        config = TurnLimitConfig(quick=20, standard=50, complex=100)

        assert config.get_limit_for_type("standard") == 50
        assert config.get_limit_for_type("unknown_type") == 50  # Falls back to standard


class TestConfigLoader:
    """Tests for ConfigLoader reading turn limit configuration."""

    def test_config_loader_reads_turn_limits_from_dict(self):
        """ConfigLoader parses turn limits from configuration dict."""
        config_data = {"turn_limits": {"quick": 20, "standard": 50, "complex": 100}}

        loader = ConfigLoader()
        config = loader.load_from_dict(config_data)

        assert config.quick == 20
        assert config.standard == 50
        assert config.complex == 100

    def test_config_loader_validates_positive_turn_limits(self):
        """ConfigLoader rejects negative or zero turn limits."""
        invalid_config = {"turn_limits": {"quick": -10, "standard": 50, "complex": 0}}

        loader = ConfigLoader()

        with pytest.raises(ValueError, match="Turn limits must be positive"):
            loader.load_from_dict(invalid_config)

    def test_config_loader_requires_all_task_types(self):
        """ConfigLoader ensures all required task types present."""
        incomplete_config = {
            "turn_limits": {
                "quick": 20,
                "standard": 50,
                # Missing 'complex'
            }
        }

        loader = ConfigLoader()

        with pytest.raises(ValueError, match="Missing required task type"):
            loader.load_from_dict(incomplete_config)

    def test_config_loader_handles_missing_turn_limits_section(self):
        """ConfigLoader raises error when turn_limits section absent."""
        empty_config = {}

        loader = ConfigLoader()

        with pytest.raises(ValueError, match="turn_limits section required"):
            loader.load_from_dict(empty_config)

    def test_config_loader_provides_default_configuration(self):
        """ConfigLoader offers default turn limits when no config provided."""
        loader = ConfigLoader()
        default_config = loader.get_default_config()

        assert default_config.quick == 20
        assert default_config.standard == 50
        assert default_config.complex == 100
