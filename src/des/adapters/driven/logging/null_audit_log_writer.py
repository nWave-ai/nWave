"""NullAuditLogWriter - NullObject pattern for AuditLogWriter port.

Used when audit logging is disabled. Accepts all log_event calls
without performing any I/O.
"""

from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter


class NullAuditLogWriter(AuditLogWriter):
    """No-op implementation of AuditLogWriter for disabled audit logging."""

    def log_event(self, event: AuditEvent) -> None:
        """Accept event without writing. No-op."""
