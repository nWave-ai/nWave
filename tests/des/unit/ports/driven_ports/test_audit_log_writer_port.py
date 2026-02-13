"""Unit tests for AuditEvent dataclass in audit_log_writer port.

Tests verify:
- AC1: AuditEvent has feature_name and step_id fields (str | None)
- AC2: data dict field remains for additional event-specific fields
- AC3: Fields can be serialized (tested via dataclass asdict)
- AC4: None values are properly handled (not excluded here, that's serialization layer)
"""

from dataclasses import asdict

from des.ports.driven_ports.audit_log_writer import AuditEvent


def test_audit_event_has_feature_name_and_step_id_fields():
    """AC1: Port AuditEvent has feature_name and step_id fields (str | None)."""
    event = AuditEvent(
        event_type="TEST_EVENT",
        timestamp="2026-02-06T17:00:00Z",
        feature_name="test-feature",
        step_id="01-01",
    )

    assert event.feature_name == "test-feature"
    assert event.step_id == "01-01"


def test_audit_event_feature_name_and_step_id_default_to_none():
    """AC1: feature_name and step_id should default to None when not provided."""
    event = AuditEvent(event_type="TEST_EVENT", timestamp="2026-02-06T17:00:00Z")

    assert event.feature_name is None
    assert event.step_id is None


def test_audit_event_data_dict_remains_for_additional_fields():
    """AC2: data dict remains for additional event-specific fields."""
    event = AuditEvent(
        event_type="TEST_EVENT",
        timestamp="2026-02-06T17:00:00Z",
        feature_name="test-feature",
        step_id="01-01",
        data={"error": "test error", "count": 5},
    )

    assert event.data == {"error": "test error", "count": 5}


def test_audit_event_can_be_converted_to_dict():
    """AC3: AuditEvent can be serialized to dictionary with feature_name and step_id as top-level fields."""
    event = AuditEvent(
        event_type="TEST_EVENT",
        timestamp="2026-02-06T17:00:00Z",
        feature_name="test-feature",
        step_id="01-01",
        data={"extra": "value"},
    )

    event_dict = asdict(event)

    assert event_dict["feature_name"] == "test-feature"
    assert event_dict["step_id"] == "01-01"
    assert event_dict["data"] == {"extra": "value"}
    assert event_dict["event_type"] == "TEST_EVENT"
    assert event_dict["timestamp"] == "2026-02-06T17:00:00Z"


def test_audit_event_with_none_values_in_dict():
    """AC4: Serialization should include None-valued feature_name and step_id.

    Note: The actual exclusion of None values happens in the serialization layer
    (JsonlAuditLogWriter in step 01-02), not in the dataclass itself.
    This test verifies the dataclass allows None values.
    """
    event = AuditEvent(
        event_type="TEST_EVENT",
        timestamp="2026-02-06T17:00:00Z",
        feature_name=None,
        step_id=None,
    )

    event_dict = asdict(event)

    # At dataclass level, None values are present
    assert "feature_name" in event_dict
    assert event_dict["feature_name"] is None
    assert "step_id" in event_dict
    assert event_dict["step_id"] is None
