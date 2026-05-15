"""
Validator dual-canon dispatch tests (ADR-025, 2026-05-07).

Verifies the JSON schema retains the legacy 5-phase active list (so existing
validators / audit-log replay paths work unchanged) AND exposes the new v5
canonical 3-phase list under ``valid_tdd_phases_v5`` for callers that opt in.

The current ExecutionLogValidator and TDDPhaseValidator consume the legacy
``tdd_phases`` accessor — that contract MUST remain stable to preserve
backward compatibility with pre-2026-05-07 audit logs. These tests pin the
contract.
"""

import json
from pathlib import Path

import pytest

from des.domain.tdd_schema import (
    CANONICAL_PHASES,
    LEGACY_PHASES,
    TDDSchemaLoader,
)


SCHEMA_PATH = (
    Path(__file__).resolve().parents[4]
    / "nWave"
    / "templates"
    / "step-tdd-cycle-schema.json"
)


@pytest.fixture(scope="module")
def raw_schema() -> dict:
    """Raw schema JSON parsed once per test module."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestSchemaJSONExposesBothCanons:
    """The on-disk schema JSON carries both v4 and v5 phase lists."""

    def test_legacy_list_is_five_phase_plus_meta(self, raw_schema):
        """valid_tdd_phases (active) is v4 5-phase + NOT_STARTED/COMPLETED."""
        legacy = raw_schema["valid_tdd_phases"]
        assert "PREPARE" in legacy
        assert "RED_ACCEPTANCE" in legacy
        assert "RED_UNIT" in legacy
        assert "GREEN" in legacy
        assert "COMMIT" in legacy

    def test_v5_list_is_three_phase_plus_meta(self, raw_schema):
        """valid_tdd_phases_v5 is canonical 3-phase + NOT_STARTED/COMPLETED."""
        v5 = raw_schema["valid_tdd_phases_v5"]
        assert "RED" in v5
        assert "GREEN" in v5
        assert "COMMIT" in v5
        assert "PREPARE" not in v5
        assert "RED_ACCEPTANCE" not in v5
        assert "RED_UNIT" not in v5

    def test_canon_migration_block_documents_adr_025(self, raw_schema):
        """The canon_migration metadata block points at ADR-025."""
        meta = raw_schema["canon_migration"]
        assert meta["adr"] == "ADR-025"
        assert meta["cutover_date"] == "2026-05-07"

    def test_v5_transitions_table_present(self, raw_schema):
        """valid_transitions_v5 supports the canonical RED→GREEN→COMMIT cycle."""
        transitions = raw_schema["valid_transitions_v5"]
        assert "RED" in transitions["NOT_STARTED"]
        assert "GREEN" in transitions["RED"]
        assert "COMMIT" in transitions["GREEN"]
        assert "COMPLETED" in transitions["COMMIT"]


class TestLoaderRespectsLegacyDefault:
    """TDDSchemaLoader still resolves the active list as legacy v4."""

    def test_loaded_tdd_phases_remain_five_phase(self):
        """tdd_phases (the active accessor) must stay v4 for backward-compat."""
        schema = TDDSchemaLoader().load()
        assert schema.tdd_phases == LEGACY_PHASES

    def test_loaded_total_phases_remain_five(self):
        """total_phases stays 5 — JSON schema's active list is still v4."""
        schema = TDDSchemaLoader().load()
        assert schema.total_phases == 5

    def test_canonical_phases_available_after_load(self):
        """canonical_phases field is populated even when JSON drives v4 default."""
        schema = TDDSchemaLoader().load()
        assert schema.canonical_phases == CANONICAL_PHASES


class TestPhasesForDispatch:
    """phases_for(schema_version) returns the right list per canon."""

    def test_v5_dispatch_returns_canonical(self):
        """Opting in via schema_version='5.0' yields canonical 3-phase."""
        schema = TDDSchemaLoader().load()
        assert schema.phases_for("5.0") == CANONICAL_PHASES

    def test_v4_dispatch_returns_legacy(self):
        """schema_version='4.0' yields legacy 5-phase (audit-log replay)."""
        schema = TDDSchemaLoader().load()
        assert schema.phases_for("4.0") == LEGACY_PHASES

    @pytest.mark.parametrize("version", ["3.0", "2.0", "1.0", "unknown"])
    def test_pre_v5_versions_fall_back_to_legacy(self, version):
        """Any pre-v5 or unknown version falls back to legacy 5-phase."""
        schema = TDDSchemaLoader().load()
        assert schema.phases_for(version) == LEGACY_PHASES


class TestExecutionLogValidatorBackwardCompat:
    """ExecutionLogValidator continues to validate v4 phase logs unchanged."""

    def test_v4_phase_log_still_validates_clean(self):
        """A complete v4 5-phase log validates without errors via the
        existing validator path."""
        from des.application.validator import ExecutionLogValidator

        v4_log = [
            {
                "phase_name": phase,
                "status": "EXECUTED",
                "outcome": "PASS",
            }
            for phase in LEGACY_PHASES
        ]
        validator = ExecutionLogValidator()
        errors = validator.validate(v4_log)
        assert errors == [], f"Expected no errors, got {errors}"

    def test_empty_log_yields_no_errors(self):
        """Empty phase logs are skipped (no execution yet) — preserved behaviour."""
        from des.application.validator import ExecutionLogValidator

        validator = ExecutionLogValidator()
        errors = validator.validate([])
        assert errors == []
