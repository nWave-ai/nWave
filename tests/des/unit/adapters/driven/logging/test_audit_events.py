"""
Acceptance tests for AuditEvent dataclass refactoring.

Tests verify that AuditEvent correctly uses feature_name and step_id
instead of the deprecated step_path field.
"""

from des.adapters.driven.logging.audit_events import AuditEvent


class TestAuditEventRefactoring:
    """Acceptance tests for AuditEvent field refactoring."""

    def test_ac1_audit_event_has_feature_name_field(self):
        """AC1: AuditEvent dataclass has feature_name field (str | None)."""
        event = AuditEvent(
            timestamp="2025-01-01T00:00:00.000Z",
            event="PHASE_STARTED",
            feature_name="user-authentication",
        )
        assert hasattr(event, "feature_name")
        assert event.feature_name == "user-authentication"
        assert isinstance(event.feature_name, str)

    def test_ac2_audit_event_has_step_id_field(self):
        """AC2: AuditEvent dataclass has step_id field (str | None)."""
        event = AuditEvent(
            timestamp="2025-01-01T00:00:00.000Z",
            event="PHASE_STARTED",
            step_id="01-02",
        )
        assert hasattr(event, "step_id")
        assert event.step_id == "01-02"
        assert isinstance(event.step_id, str)

    def test_ac3_step_path_field_removed(self):
        """AC3: step_path field is removed from AuditEvent dataclass."""
        event = AuditEvent(
            timestamp="2025-01-01T00:00:00.000Z",
            event="PHASE_STARTED",
        )
        assert not hasattr(event, "step_path")

    def test_ac4_serialization_contains_feature_name_and_step_id(self):
        """AC4: AuditEvent serializes to dictionary containing feature_name and step_id keys."""
        event = AuditEvent(
            timestamp="2025-01-01T00:00:00.000Z",
            event="PHASE_STARTED",
            feature_name="user-authentication",
            step_id="01-02",
        )
        serialized = event.to_dict()

        assert "feature_name" in serialized
        assert serialized["feature_name"] == "user-authentication"
        assert "step_id" in serialized
        assert serialized["step_id"] == "01-02"

    def test_ac5_deserialization_from_dictionary(self):
        """AC5: AuditEvent deserializes from dictionary containing feature_name and step_id keys."""
        data = {
            "timestamp": "2025-01-01T00:00:00.000Z",
            "event": "PHASE_STARTED",
            "feature_name": "user-authentication",
            "step_id": "01-02",
        }
        event = AuditEvent.from_dict(data)

        assert event.feature_name == "user-authentication"
        assert event.step_id == "01-02"

    def test_ac6_serialization_excludes_none_values(self):
        """AC6: AuditEvent serialization excludes None-valued feature_name and step_id fields."""
        event = AuditEvent(
            timestamp="2025-01-01T00:00:00.000Z",
            event="PHASE_STARTED",
            feature_name=None,
            step_id=None,
        )
        serialized = event.to_dict()

        # None values should be excluded from serialization
        assert "feature_name" not in serialized
        assert "step_id" not in serialized
        # But required fields should be present
        assert "timestamp" in serialized
        assert "event" in serialized
