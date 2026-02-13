"""
Unit tests for NullAuditLogWriter (NullObject pattern).

Tests that NullAuditLogWriter implements AuditLogWriter port
with no-op behavior.

Test Budget: 1 behavior x 2 = 2 max. Actual: 2 tests.
"""

from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter


class TestNullAuditLogWriterImplementsPort:
    """Test NullAuditLogWriter conforms to AuditLogWriter port."""

    def test_implements_audit_log_writer_interface(self):
        """NullAuditLogWriter is an instance of AuditLogWriter."""
        from des.adapters.driven.logging.null_audit_log_writer import (
            NullAuditLogWriter,
        )

        writer = NullAuditLogWriter()

        assert isinstance(writer, AuditLogWriter)

    def test_log_event_accepts_event_without_side_effects(self):
        """NullAuditLogWriter.log_event accepts an AuditEvent and returns None."""
        from des.adapters.driven.logging.null_audit_log_writer import (
            NullAuditLogWriter,
        )

        writer = NullAuditLogWriter()
        event = AuditEvent(
            event_type="TEST_EVENT",
            timestamp="2026-01-01T00:00:00Z",
            data={"key": "value"},
        )

        result = writer.log_event(event)

        assert result is None
