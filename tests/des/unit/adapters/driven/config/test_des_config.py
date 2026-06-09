"""
Unit tests for DESConfig configuration loader.

Tests DESConfig behavior from driving port perspective (public interface):
- Configuration loading from JSON file at .nwave/des-config.json
- Default value fallback when file missing/invalid (defaults to True)
- audit_logging_enabled setting access
- Environment variable override (DES_AUDIT_LOGGING_ENABLED)
- Rigor configuration properties (profile, models, phases, flags)
- Housekeeping configuration properties (enabled, retention, staleness, size)

Test Budget: 20 behaviors x 2 = 40 max. Actual: 20 tests (4 parametrized).
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


class TestDESConfigRigorDefaults:
    """Test DESConfig rigor properties default to 'standard' profile values."""

    def test_no_rigor_key_defaults_to_standard(self, tmp_path):
        """All rigor properties return standard defaults when no rigor key in config."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps({"audit_logging_enabled": True}), encoding="utf-8"
        )

        from des.adapters.driven.config.des_config import DESConfig

        # Isolate from real ~/.nwave/global-config.json
        nonexistent_global = tmp_path / "no-global-config.json"
        cfg = DESConfig(config_path=config_file, global_config_path=nonexistent_global)

        assert cfg.rigor_profile == "standard"
        assert cfg.rigor_agent_model == "sonnet"
        assert cfg.rigor_reviewer_model == "haiku"
        assert cfg.rigor_review_enabled is True
        assert cfg.rigor_double_review is False
        assert cfg.rigor_mutation_enabled is False
        assert cfg.rigor_refactor_pass is True
        # F6 sweep (2026-05-18): default rigor_tdd_phases follows ADR-025
        # canonical (RED/GREEN/COMMIT). Legacy 5-phase only via explicit
        # rigor.tdd_phases override (see TestDESConfigRigorExplicitProfiles).
        assert cfg.rigor_tdd_phases == ("RED", "GREEN", "COMMIT")

    def test_missing_config_file_defaults_to_standard(self, tmp_path):
        """All rigor properties return standard defaults when config file missing."""
        config_file = tmp_path / ".nwave" / "des-config.json"

        from des.adapters.driven.config.des_config import DESConfig

        # Isolate from real ~/.nwave/global-config.json
        nonexistent_global = tmp_path / "no-global-config.json"
        cfg = DESConfig(config_path=config_file, global_config_path=nonexistent_global)

        assert cfg.rigor_profile == "standard"
        assert cfg.rigor_agent_model == "sonnet"
        # F6 sweep (2026-05-18): default rigor_tdd_phases follows ADR-025
        # canonical (RED/GREEN/COMMIT).
        assert cfg.rigor_tdd_phases == ("RED", "GREEN", "COMMIT")

    def test_partial_rigor_fills_missing_with_standard_defaults(self, tmp_path):
        """Missing rigor sub-keys get standard defaults."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps({"rigor": {"profile": "custom"}}), encoding="utf-8"
        )

        from des.adapters.driven.config.des_config import DESConfig

        cfg = DESConfig(config_path=config_file)

        assert cfg.rigor_profile == "custom"
        assert cfg.rigor_agent_model == "sonnet"
        assert cfg.rigor_reviewer_model == "haiku"
        assert cfg.rigor_review_enabled is True


class TestDESConfigRigorExplicitProfiles:
    """Test DESConfig rigor properties with explicit profile configurations."""

    def test_lean_profile_values(self, tmp_path):
        """Lean profile config returns lean values for all rigor properties."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps(
                {
                    "rigor": {
                        "profile": "lean",
                        "agent_model": "haiku",
                        "reviewer_model": "haiku",
                        "tdd_phases": ["GREEN", "COMMIT"],
                        "review_enabled": False,
                        "double_review": False,
                        "mutation_enabled": False,
                        "refactor_pass": False,
                    }
                }
            ),
            encoding="utf-8",
        )

        from des.adapters.driven.config.des_config import DESConfig

        cfg = DESConfig(config_path=config_file)

        assert cfg.rigor_profile == "lean"
        assert cfg.rigor_agent_model == "haiku"
        assert cfg.rigor_reviewer_model == "haiku"
        assert cfg.rigor_tdd_phases == ("GREEN", "COMMIT")
        assert cfg.rigor_review_enabled is False
        assert cfg.rigor_double_review is False
        assert cfg.rigor_mutation_enabled is False
        assert cfg.rigor_refactor_pass is False

    def test_exhaustive_profile_values(self, tmp_path):
        """Exhaustive profile config returns exhaustive values for all rigor properties."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps(
                {
                    "rigor": {
                        "profile": "exhaustive",
                        "agent_model": "opus",
                        "reviewer_model": "opus",
                        "tdd_phases": [
                            "PREPARE",
                            "RED_ACCEPTANCE",
                            "RED_UNIT",
                            "GREEN",
                            "COMMIT",
                        ],
                        "review_enabled": True,
                        "double_review": True,
                        "mutation_enabled": True,
                        "refactor_pass": True,
                    }
                }
            ),
            encoding="utf-8",
        )

        from des.adapters.driven.config.des_config import DESConfig

        cfg = DESConfig(config_path=config_file)

        assert cfg.rigor_profile == "exhaustive"
        assert cfg.rigor_agent_model == "opus"
        assert cfg.rigor_reviewer_model == "opus"
        assert cfg.rigor_tdd_phases == (
            "PREPARE",
            "RED_ACCEPTANCE",
            "RED_UNIT",
            "GREEN",
            "COMMIT",
        )
        assert cfg.rigor_review_enabled is True
        assert cfg.rigor_double_review is True
        assert cfg.rigor_mutation_enabled is True
        assert cfg.rigor_refactor_pass is True

    def test_rigor_tdd_phases_returns_tuple_not_list(self, tmp_path):
        """rigor_tdd_phases always returns a tuple even when config has a list."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps({"rigor": {"tdd_phases": ["GREEN", "COMMIT"]}}),
            encoding="utf-8",
        )

        from des.adapters.driven.config.des_config import DESConfig

        cfg = DESConfig(config_path=config_file)

        assert isinstance(cfg.rigor_tdd_phases, tuple)
        assert cfg.rigor_tdd_phases == ("GREEN", "COMMIT")


class TestDESConfigHousekeepingDefaults:
    """Test DESConfig housekeeping properties return correct defaults when config absent."""

    def test_housekeeping_enabled_defaults_to_true_when_config_missing(self, tmp_path):
        """housekeeping_enabled returns True when no config file present."""
        config_file = tmp_path / ".nwave" / "des-config.json"

        from des.adapters.driven.config.des_config import DESConfig

        cfg = DESConfig(config_path=config_file)

        assert cfg.housekeeping_enabled is True

    def test_housekeeping_audit_retention_days_defaults_to_7(self, tmp_path):
        """housekeeping_audit_retention_days returns 7 when no housekeeping key in config."""
        config_file = tmp_path / ".nwave" / "des-config.json"

        from des.adapters.driven.config.des_config import DESConfig

        cfg = DESConfig(config_path=config_file)

        assert cfg.housekeeping_audit_retention_days == 7

    def test_housekeeping_signal_staleness_hours_defaults_to_4(self, tmp_path):
        """housekeeping_signal_staleness_hours returns 4 when no housekeeping key in config."""
        config_file = tmp_path / ".nwave" / "des-config.json"

        from des.adapters.driven.config.des_config import DESConfig

        cfg = DESConfig(config_path=config_file)

        assert cfg.housekeeping_signal_staleness_hours == 4

    def test_housekeeping_skill_log_max_bytes_defaults_to_1mb(self, tmp_path):
        """housekeeping_skill_log_max_bytes returns 1_048_576 when no housekeeping key in config."""
        config_file = tmp_path / ".nwave" / "des-config.json"

        from des.adapters.driven.config.des_config import DESConfig

        cfg = DESConfig(config_path=config_file)

        assert cfg.housekeeping_skill_log_max_bytes == 1_048_576


class TestDESConfigHousekeepingReadsCustomValues:
    """Test DESConfig housekeeping properties read from 'housekeeping' key in config."""

    @pytest.mark.parametrize(
        "field,config_value,expected",
        [
            ("enabled", False, False),
            ("audit_retention_days", 14, 14),
            ("signal_staleness_hours", 8, 8),
            ("skill_log_max_bytes", 2097152, 2097152),
        ],
        ids=[
            "enabled",
            "audit_retention_days",
            "signal_staleness_hours",
            "skill_log_max_bytes",
        ],
    )
    def test_reads_custom_housekeeping_values_from_config(
        self, tmp_path, field, config_value, expected
    ):
        """DESConfig reads each housekeeping property from 'housekeeping' config key."""
        config_file = tmp_path / ".nwave" / "des-config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps({"housekeeping": {field: config_value}}), encoding="utf-8"
        )

        from des.adapters.driven.config.des_config import DESConfig

        cfg = DESConfig(config_path=config_file)

        prop_name = f"housekeeping_{field}"
        assert getattr(cfg, prop_name) == expected
