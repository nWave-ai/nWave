"""
Unit tests for DESConfig configuration loader.

Tests DESConfig behavior from driving port perspective (public interface):
- Configuration loading from JSON file at .nwave/des-config.json
- Default value fallback when file missing/invalid (defaults to True)
- audit_logging_enabled setting access
- Environment variable override (DES_AUDIT_LOGGING_ENABLED)

Test Budget: 8 behaviors x 2 = 16 max. Actual: 8 tests (4 parametrized).
"""

import json

import pytest


class TestDESConfigLoadsValidConfiguration:
    """Test DESConfig loads configuration from valid JSON file."""

    @pytest.mark.parametrize(
        "audit_value,expected",
        [
            (True, True),
            (False, False),
        ],
    )
    def test_loads_audit_logging_enabled_from_config(
        self, tmp_path, audit_value, expected
    ):
        """DESConfig loads audit_logging_enabled from valid JSON config file."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps({"audit_logging_enabled": audit_value}), encoding="utf-8"
        )

        from des.adapters.driven.config.des_config import DESConfig

        config = DESConfig(config_path=config_file)

        assert config.audit_logging_enabled is expected


class TestDESConfigDefaultsToTrue:
    """Test DESConfig defaults to audit_logging_enabled=True."""

    def test_defaults_to_true_when_config_file_missing(self, tmp_path):
        """DESConfig defaults to audit_logging_enabled=True when config file missing."""
        config_file = tmp_path / ".nwave" / "des-config.json"

        from des.adapters.driven.config.des_config import DESConfig

        config = DESConfig(config_path=config_file)

        assert config.audit_logging_enabled is True

    @pytest.mark.parametrize(
        "file_content",
        [
            "not valid json {{{",
            json.dumps({"some_other_setting": "value"}),
        ],
        ids=["invalid_json", "key_absent"],
    )
    def test_defaults_to_true_when_config_unusable(self, tmp_path, file_content):
        """DESConfig defaults to audit_logging_enabled=True when JSON invalid or key absent."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(file_content, encoding="utf-8")

        from des.adapters.driven.config.des_config import DESConfig

        config = DESConfig(config_path=config_file)

        assert config.audit_logging_enabled is True


class TestDESConfigUsesNwavePath:
    """Test DESConfig uses .nwave/des-config.json as default path."""

    def test_resolves_config_from_cwd_nwave_directory(self, tmp_path):
        """DESConfig resolves config from cwd/.nwave/des-config.json by default."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps({"audit_logging_enabled": True}), encoding="utf-8"
        )

        from des.adapters.driven.config.des_config import DESConfig

        config = DESConfig(cwd=tmp_path)

        assert config.audit_logging_enabled is True

    def test_does_not_create_config_file_when_missing(self, tmp_path):
        """DESConfig does NOT auto-create config file when missing."""
        config_file = tmp_path / ".nwave" / "des-config.json"

        from des.adapters.driven.config.des_config import DESConfig

        _ = DESConfig(config_path=config_file)

        assert not config_file.exists()


class TestDESConfigEnvVarOverride:
    """Test DES_AUDIT_LOGGING_ENABLED env var overrides config file."""

    @pytest.mark.parametrize(
        "env_value,expected",
        [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("0", False),
            ("no", False),
        ],
        ids=["true", "1", "yes", "false", "0", "no"],
    )
    def test_env_var_overrides_config_file(
        self, tmp_path, monkeypatch, env_value, expected
    ):
        """DES_AUDIT_LOGGING_ENABLED env var takes priority over config file."""
        # Arrange: config file says False, but env var overrides
        config_file = tmp_path / ".nwave" / "des-config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps({"audit_logging_enabled": False}), encoding="utf-8"
        )
        monkeypatch.setenv("DES_AUDIT_LOGGING_ENABLED", env_value)

        from des.adapters.driven.config.des_config import DESConfig

        config = DESConfig(config_path=config_file)

        assert config.audit_logging_enabled is expected

    def test_env_var_absent_falls_through_to_config(self, tmp_path, monkeypatch):
        """When env var is absent, config file value is used."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps({"audit_logging_enabled": True}), encoding="utf-8"
        )
        monkeypatch.delenv("DES_AUDIT_LOGGING_ENABLED", raising=False)

        from des.adapters.driven.config.des_config import DESConfig

        config = DESConfig(config_path=config_file)

        assert config.audit_logging_enabled is True
