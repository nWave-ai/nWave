"""
Unit tests for TDDSchema v5 dual-canon support (ADR-025, 2026-05-07).

Verifies:
- Module-level constants LEGACY_PHASES (5-tuple) and CANONICAL_PHASES (3-tuple)
  expose the two canons explicitly.
- TDDSchema dataclass exposes canonical_phases + legacy_phases fields.
- TDDSchema.phases_for() dispatches on schema_version:
    "5.0" -> canonical 3-phase, anything else -> legacy 5-phase.
- Backward-compat: tdd_phases (active field) continues to return the legacy
  5-phase list so existing validators / audit-log replay paths are
  unaffected.
"""

import pytest

from des.domain.tdd_schema import (
    CANONICAL_PHASES,
    LEGACY_PHASES,
    TDDSchema,
    TDDSchemaLoader,
)


class TestDualCanonConstants:
    """Module-level constants expose both TDD canons."""

    def test_legacy_phases_is_five_phase_v4(self):
        """LEGACY_PHASES is the 5-phase v4 contract (ADR-024 era)."""
        assert LEGACY_PHASES == (
            "PREPARE",
            "RED_ACCEPTANCE",
            "RED_UNIT",
            "GREEN",
            "COMMIT",
        )

    def test_canonical_phases_is_three_phase_v5(self):
        """CANONICAL_PHASES is the 3-phase v5 contract (ADR-025)."""
        assert CANONICAL_PHASES == ("RED", "GREEN", "COMMIT")

    def test_canon_lists_are_tuples_for_immutability(self):
        """Both lists are tuples — mutating them must be impossible."""
        assert isinstance(LEGACY_PHASES, tuple)
        assert isinstance(CANONICAL_PHASES, tuple)


class TestTDDSchemaCanonFields:
    """TDDSchema exposes both canons as fields."""

    def test_default_schema_exposes_canonical_phases(self):
        """Default-constructed TDDSchema carries CANONICAL_PHASES."""
        schema = TDDSchema()
        assert schema.canonical_phases == CANONICAL_PHASES

    def test_default_schema_exposes_legacy_phases(self):
        """Default-constructed TDDSchema carries LEGACY_PHASES."""
        schema = TDDSchema()
        assert schema.legacy_phases == LEGACY_PHASES

    def test_loaded_schema_exposes_both_canons(self):
        """Loaded schema from JSON also carries both canon fields."""
        schema = TDDSchemaLoader().load()
        assert schema.canonical_phases == CANONICAL_PHASES
        assert schema.legacy_phases == LEGACY_PHASES


class TestPhasesForDispatch:
    """phases_for() returns the right canon based on schema_version."""

    @pytest.fixture
    def schema(self):
        return TDDSchemaLoader().load()

    def test_v5_returns_canonical_three_phase(self, schema):
        """schema_version '5.0' -> canonical 3-phase tuple."""
        result = schema.phases_for("5.0")
        assert result == CANONICAL_PHASES
        assert len(result) == 3

    def test_v4_returns_legacy_five_phase(self, schema):
        """schema_version '4.0' -> legacy 5-phase tuple."""
        result = schema.phases_for("4.0")
        assert result == LEGACY_PHASES
        assert len(result) == 5

    def test_v3_returns_legacy_for_backward_compat(self, schema):
        """schema_version '3.0' -> legacy fallback (no v3 canon defined here)."""
        result = schema.phases_for("3.0")
        assert result == LEGACY_PHASES

    def test_unknown_version_returns_legacy(self, schema):
        """Unknown schema_version -> legacy fallback (safe default)."""
        result = schema.phases_for("99.99")
        assert result == LEGACY_PHASES


class TestBackwardCompatibility:
    """tdd_phases (active field) preserves the legacy contract."""

    def test_tdd_phases_active_field_returns_five_phase(self):
        """tdd_phases stays 5-phase so existing validators / audit-log
        replay paths are unaffected by the dual-canon migration.
        """
        schema = TDDSchemaLoader().load()
        assert schema.tdd_phases == LEGACY_PHASES
        assert len(schema.tdd_phases) == 5

    def test_total_phases_field_remains_five(self):
        """total_phases stays 5 — JSON schema's active list is still v4."""
        schema = TDDSchemaLoader().load()
        assert schema.total_phases == 5
