"""
Unit tests for TDD Schema Loader.

Tests that the schema loader correctly reads from step-tdd-cycle-schema.json
and provides the expected TDD phase names, statuses, and skip prefixes.
"""

import pytest

from des.domain.tdd_schema import (
    TDDSchema,
    TDDSchemaLoader,
    get_tdd_schema,
    get_tdd_schema_loader,
    reset_global_schema_loader,
)


class TestTDDSchemaLoader:
    """Tests for TDDSchemaLoader class."""

    def test_load_returns_tdd_schema_instance(self):
        """Load should return a TDDSchema instance."""
        loader = TDDSchemaLoader()
        schema = loader.load()
        assert isinstance(schema, TDDSchema)

    def test_schema_defines_expected_phase_count(self, tdd_schema):
        """Schema should define exactly 5 TDD phases."""
        assert len(tdd_schema.tdd_phases) == 5

    def test_phases_are_in_correct_order(self, tdd_schema):
        """TDD phases should be in the expected order."""
        expected = (
            "PREPARE",
            "RED_ACCEPTANCE",
            "RED_UNIT",
            "GREEN",
            "COMMIT",
        )
        assert tdd_schema.tdd_phases == expected

    def test_valid_statuses_includes_required_values(self, tdd_schema):
        """Valid statuses should include all execution states."""
        expected = {"NOT_EXECUTED", "IN_PROGRESS", "EXECUTED", "SKIPPED"}
        assert set(tdd_schema.valid_statuses) == expected

    def test_valid_skip_prefixes_allow_commit(self, tdd_schema):
        """Valid skip prefixes should allow commit."""
        expected_valid = {
            "BLOCKED_BY_DEPENDENCY:",
            "NOT_APPLICABLE:",
            "APPROVED_SKIP:",
            "CHECKPOINT_PENDING:",
        }
        assert set(tdd_schema.valid_skip_prefixes) == expected_valid

    def test_blocking_skip_prefixes_block_commit(self, tdd_schema):
        """Blocking skip prefixes should prevent commit."""
        assert "DEFERRED:" in tdd_schema.blocking_skip_prefixes

    def test_schema_version_is_4_0(self, tdd_schema):
        """Schema version should be 4.0."""
        assert tdd_schema.schema_version == "4.0"

    def test_total_phases_is_5(self, tdd_schema):
        """Total phases should be 5."""
        assert tdd_schema.total_phases == 5


class TestTDDSchemaLoaderCaching:
    """Tests for schema caching behavior."""

    def test_loader_caches_schema(self):
        """Loader should return same schema instance on repeated loads."""
        loader = TDDSchemaLoader()
        schema1 = loader.load()
        schema2 = loader.load()
        assert schema1 is schema2

    def test_clear_cache_forces_reload(self):
        """Clear cache should force a fresh load."""
        loader = TDDSchemaLoader()
        schema1 = loader.load()
        loader.clear_cache()
        schema2 = loader.load()
        # Different instances but same content
        assert schema1 is not schema2
        assert schema1.tdd_phases == schema2.tdd_phases


class TestGlobalSchemaAccess:
    """Tests for module-level singleton access."""

    @pytest.fixture(autouse=True)
    def reset_global_state(self):
        """Reset global state before and after each test."""
        reset_global_schema_loader()
        yield
        reset_global_schema_loader()

    def test_get_tdd_schema_returns_schema(self):
        """get_tdd_schema should return a TDDSchema instance."""
        schema = get_tdd_schema()
        assert isinstance(schema, TDDSchema)

    def test_get_tdd_schema_returns_cached_instance(self):
        """get_tdd_schema should return the same instance."""
        schema1 = get_tdd_schema()
        schema2 = get_tdd_schema()
        assert schema1 is schema2

    def test_get_tdd_schema_loader_returns_loader(self):
        """get_tdd_schema_loader should return the global loader."""
        loader = get_tdd_schema_loader()
        assert isinstance(loader, TDDSchemaLoader)

    def test_reset_clears_global_state(self):
        """reset_global_schema_loader should clear cached state."""
        schema1 = get_tdd_schema()
        reset_global_schema_loader()
        schema2 = get_tdd_schema()
        assert schema1 is not schema2
