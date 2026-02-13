"""
Unit tests for _log_audit_event helper function (Step 03-01).

Tests that _log_audit_event correctly extracts feature_name and step_id from kwargs
and passes them as direct PortAuditEvent fields rather than stuffing them into
the data dict.
"""

from unittest.mock import Mock, patch


def _make_patches():
    """Patch JsonlAuditLogWriter and SystemTimeProvider used inside _log_audit_event."""
    mock_writer_cls = Mock()
    mock_writer = Mock()
    mock_writer_cls.return_value = mock_writer

    mock_time_cls = Mock()
    mock_time_provider = Mock()
    mock_time_provider.now_utc.return_value.isoformat.return_value = (
        "2026-02-06T12:00:00Z"
    )
    mock_time_cls.return_value = mock_time_provider

    writer_patch = patch(
        "des.application.orchestrator.JsonlAuditLogWriter",
        mock_writer_cls,
    )
    time_patch = patch(
        "des.adapters.driven.time.system_time.SystemTimeProvider",
        mock_time_cls,
    )
    return writer_patch, time_patch, mock_writer


class TestLogAuditEventDirectFields:
    """AC1-4: _log_audit_event extracts feature_name/step_id as direct PortAuditEvent fields."""

    def test_feature_name_and_step_id_as_direct_fields(self):
        """AC1: When called with feature_name and step_id kwargs,
        PortAuditEvent has them as direct fields, NOT in data dict."""
        from des.application.orchestrator import _log_audit_event

        writer_patch, time_patch, mock_writer = _make_patches()

        with writer_patch, time_patch:
            _log_audit_event(
                "TEST_EVENT",
                feature_name="my-feature",
                step_id="01-01",
            )

            mock_writer.log_event.assert_called_once()
            event = mock_writer.log_event.call_args[0][0]

            # Direct fields populated
            assert event.feature_name == "my-feature"
            assert event.step_id == "01-01"

            # NOT in data dict
            assert "feature_name" not in event.data
            assert "step_id" not in event.data

    def test_direct_fields_with_extra_kwargs_in_data(self):
        """AC2: When called with feature_name, step_id, AND other kwargs,
        feature_name/step_id are direct fields; command/agent in data dict."""
        from des.application.orchestrator import _log_audit_event

        writer_patch, time_patch, mock_writer = _make_patches()

        with writer_patch, time_patch:
            _log_audit_event(
                "TASK_INVOCATION_STARTED",
                feature_name="audit-log-refactor",
                step_id="03-01",
                command="/nw:execute",
                agent="@software-crafter",
            )

            event = mock_writer.log_event.call_args[0][0]

            # Direct fields
            assert event.feature_name == "audit-log-refactor"
            assert event.step_id == "03-01"

            # Extra kwargs in data dict
            assert event.data["command"] == "/nw:execute"
            assert event.data["agent"] == "@software-crafter"

            # NOT in data dict
            assert "feature_name" not in event.data
            assert "step_id" not in event.data

    def test_without_feature_name_or_step_id(self):
        """AC3: When called WITHOUT feature_name or step_id,
        PortAuditEvent has feature_name=None, step_id=None, all kwargs in data dict."""
        from des.application.orchestrator import _log_audit_event

        writer_patch, time_patch, mock_writer = _make_patches()

        with writer_patch, time_patch:
            _log_audit_event(
                "TASK_INVOCATION_STARTED",
                command="/nw:execute",
                agent="@software-crafter",
            )

            event = mock_writer.log_event.call_args[0][0]

            # Direct fields are None
            assert event.feature_name is None
            assert event.step_id is None

            # All kwargs in data dict
            assert event.data["command"] == "/nw:execute"
            assert event.data["agent"] == "@software-crafter"

    def test_none_valued_feature_name_excluded_from_data(self):
        """AC4: When called with None-valued feature_name,
        it's excluded from data dict (existing None-filtering), feature_name=None on event."""
        from des.application.orchestrator import _log_audit_event

        writer_patch, time_patch, mock_writer = _make_patches()

        with writer_patch, time_patch:
            _log_audit_event(
                "TASK_INVOCATION_STARTED",
                feature_name=None,
                step_id=None,
                command="/nw:execute",
            )

            event = mock_writer.log_event.call_args[0][0]

            # Direct fields are None
            assert event.feature_name is None
            assert event.step_id is None

            # None values NOT in data dict (existing filtering behavior)
            assert "feature_name" not in event.data
            assert "step_id" not in event.data

            # Non-None kwargs present in data
            assert event.data["command"] == "/nw:execute"
