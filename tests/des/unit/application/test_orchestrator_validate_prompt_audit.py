"""
Unit tests for DESOrchestrator.validate_prompt audit logging (Steps 01-02 + 03-02).

Tests that validate_prompt logs HOOK_PRE_TASK_PASSED and HOOK_PRE_TASK_BLOCKED
audit events with proper structure, timestamps from TimeProvider, and relevant context.

Updated for hex-arch redesign: orchestrator now uses JsonlAuditLogWriter + DESConfig
directly instead of legacy get_audit_logger() singleton.

Step 03-02: Updated to verify feature_name and step_id as direct PortAuditEvent
fields rather than data dict entries.
"""

from unittest.mock import Mock, patch

from des.adapters.driven.logging.audit_events import EventType


def _patch_audit_writer_and_config():
    """Create patches for JsonlAuditLogWriter and DESConfig in orchestrator module.

    The orchestrator creates these locally in validate_prompt():
        from des.adapters.driven.config.des_config import DESConfig
        config = DESConfig()
        if config.audit_logging_enabled:
            writer = JsonlAuditLogWriter()
            writer.log_event(PortAuditEvent(...))

    We patch:
    - JsonlAuditLogWriter where it's imported (module-level in orchestrator.py)
    - DESConfig where it's imported (locally in validate_prompt)
    """
    mock_writer_cls = Mock()
    mock_writer = Mock()
    mock_writer_cls.return_value = mock_writer

    mock_config_cls = Mock()
    mock_config = Mock()
    mock_config.audit_logging_enabled = True
    mock_config_cls.return_value = mock_config

    writer_patch = patch(
        "des.application.orchestrator.JsonlAuditLogWriter",
        mock_writer_cls,
    )
    config_patch = patch(
        "des.adapters.driven.config.des_config.DESConfig",
        mock_config_cls,
    )

    return writer_patch, config_patch, mock_writer


class TestValidatePromptAuditLogging:
    """Unit tests for validate_prompt audit logging functionality."""

    def test_validate_prompt_logs_hook_pre_task_passed_when_validation_succeeds(
        self, des_orchestrator
    ):
        """
        GIVEN DESOrchestrator with valid prompt
        WHEN validate_prompt is called and returns task_invocation_allowed True
        THEN HOOK_PRE_TASK_PASSED audit event is logged with timestamp from TimeProvider
        """
        # Arrange
        valid_prompt = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/01-01.json -->
        Task: Implement feature
        """

        writer_patch, config_patch, mock_writer = _patch_audit_writer_and_config()

        with writer_patch, config_patch:
            # Act
            result = des_orchestrator.validate_prompt(valid_prompt)

            # Assert
            assert result.task_invocation_allowed is True
            mock_writer.log_event.assert_called_once()

            # Verify event details via PortAuditEvent
            call_args = mock_writer.log_event.call_args
            port_event = call_args[0][0]  # First positional argument (PortAuditEvent)

            assert port_event.event_type == EventType.HOOK_PRE_TASK_PASSED.value
            assert port_event.timestamp is not None
            # Step 03-02: step_id is a direct PortAuditEvent field, not in data dict
            assert port_event.step_id == "01-01"

    def test_validate_prompt_logs_hook_pre_task_blocked_when_validation_fails(
        self, in_memory_filesystem, mocked_hook, mocked_time_provider
    ):
        """
        GIVEN DESOrchestrator with invalid prompt
        WHEN validate_prompt is called and returns task_invocation_allowed False
        THEN HOOK_PRE_TASK_BLOCKED audit event is logged with rejection reason
        """
        # Arrange
        from des.adapters.drivers.validators.mocked_validator import (
            MockedTemplateValidator,
        )
        from des.application.orchestrator import DESOrchestrator
        from des.ports.driver_ports.validator_port import ValidationResult

        # Create validator that returns failure
        failing_validator = MockedTemplateValidator(
            predefined_result=ValidationResult(
                status="FAILED",
                errors=["Missing DES-VALIDATION marker"],
                task_invocation_allowed=False,
                duration_ms=0.0,
                recovery_guidance=None,
            )
        )

        des_orchestrator = DESOrchestrator(
            hook=mocked_hook,
            validator=failing_validator,
            filesystem=in_memory_filesystem,
            time_provider=mocked_time_provider,
        )

        invalid_prompt = """
        Task: Implement feature without DES markers
        """

        writer_patch, config_patch, mock_writer = _patch_audit_writer_and_config()

        with writer_patch, config_patch:
            # Act
            result = des_orchestrator.validate_prompt(invalid_prompt)

            # Assert
            assert result.task_invocation_allowed is False
            mock_writer.log_event.assert_called_once()

            # Verify event details via PortAuditEvent
            call_args = mock_writer.log_event.call_args
            port_event = call_args[0][0]

            assert port_event.event_type == EventType.HOOK_PRE_TASK_BLOCKED.value
            assert port_event.timestamp is not None
            assert port_event.data.get("rejection_reason") is not None

    def test_validate_prompt_uses_time_provider_for_timestamp(
        self, des_orchestrator, mocked_time_provider
    ):
        """
        GIVEN DESOrchestrator with TimeProvider configured
        WHEN validate_prompt logs audit event
        THEN timestamp comes from TimeProvider.now_utc(), not datetime.now()
        """
        # Arrange
        valid_prompt = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/01-01.json -->
        Task: Implement feature
        """

        expected_timestamp = mocked_time_provider.now_utc()

        writer_patch, config_patch, mock_writer = _patch_audit_writer_and_config()

        with writer_patch, config_patch:
            # Act
            des_orchestrator.validate_prompt(valid_prompt)

            # Assert
            mock_writer.log_event.assert_called_once()

            # Verify timestamp matches TimeProvider
            call_args = mock_writer.log_event.call_args
            port_event = call_args[0][0]

            # Convert to comparable format
            assert port_event.timestamp == expected_timestamp.isoformat()

    def test_validate_prompt_extracts_step_id_from_prompt(self, des_orchestrator):
        """
        GIVEN prompt containing DES-STEP-FILE marker
        WHEN validate_prompt logs audit event
        THEN step_id is extracted from marker (filename without extension)
        """
        # Arrange
        prompt_with_step = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/02-03.json -->
        Task: Refactor module
        """

        writer_patch, config_patch, mock_writer = _patch_audit_writer_and_config()

        with writer_patch, config_patch:
            # Act
            des_orchestrator.validate_prompt(prompt_with_step)

            # Assert
            call_args = mock_writer.log_event.call_args
            port_event = call_args[0][0]

            # Step 03-02: step_id is a direct PortAuditEvent field, not in data dict
            assert port_event.step_id == "02-03"

    def test_validate_prompt_includes_agent_name_in_audit_event(self, des_orchestrator):
        """
        GIVEN prompt with agent information
        WHEN validate_prompt logs audit event
        THEN audit entry includes agent name
        """
        # Arrange
        prompt_with_agent = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/01-01.json -->
        You are the @software-crafter agent.
        Task: Implement feature
        """

        writer_patch, config_patch, mock_writer = _patch_audit_writer_and_config()

        with writer_patch, config_patch:
            # Act
            des_orchestrator.validate_prompt(prompt_with_agent)

            # Assert
            call_args = mock_writer.log_event.call_args
            port_event = call_args[0][0]

            # Agent name should be in data.extra_context
            extra_context = port_event.data.get("extra_context")
            assert extra_context is not None
            assert "agent" in extra_context or "agent_name" in extra_context

    def test_validate_prompt_blocked_includes_rejection_details(
        self, in_memory_filesystem, mocked_hook, mocked_time_provider
    ):
        """
        GIVEN invalid prompt causing validation rejection
        WHEN validate_prompt logs HOOK_PRE_TASK_BLOCKED event
        THEN rejection_reason field contains detailed error information
        """
        # Arrange
        from des.adapters.drivers.validators.mocked_validator import (
            MockedTemplateValidator,
        )
        from des.application.orchestrator import DESOrchestrator
        from des.ports.driver_ports.validator_port import ValidationResult

        # Create validator that returns failure
        failing_validator = MockedTemplateValidator(
            predefined_result=ValidationResult(
                status="FAILED",
                errors=["Missing DES-VALIDATION marker"],
                task_invocation_allowed=False,
                duration_ms=0.0,
                recovery_guidance=None,
            )
        )

        des_orchestrator = DESOrchestrator(
            hook=mocked_hook,
            validator=failing_validator,
            filesystem=in_memory_filesystem,
            time_provider=mocked_time_provider,
        )

        invalid_prompt = "Task without any DES markers"

        writer_patch, config_patch, mock_writer = _patch_audit_writer_and_config()

        with writer_patch, config_patch:
            # Act
            result = des_orchestrator.validate_prompt(invalid_prompt)

            # Assert
            assert result.task_invocation_allowed is False

            call_args = mock_writer.log_event.call_args
            port_event = call_args[0][0]

            assert port_event.event_type == EventType.HOOK_PRE_TASK_BLOCKED.value
            assert port_event.data.get("rejection_reason") is not None
            assert len(port_event.data["rejection_reason"]) > 0

    def test_validate_prompt_does_not_log_if_audit_disabled(
        self, in_memory_filesystem, mocked_hook, mocked_validator, mocked_time_provider
    ):
        """
        GIVEN DES configuration with audit_logging_enabled = false
        WHEN validate_prompt is called
        THEN no audit event is logged
        """
        # Arrange
        from des.application.orchestrator import DESOrchestrator

        des_orchestrator = DESOrchestrator(
            hook=mocked_hook,
            validator=mocked_validator,
            filesystem=in_memory_filesystem,
            time_provider=mocked_time_provider,
        )

        valid_prompt = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/01-01.json -->
        Task: Implement feature
        """

        mock_writer_cls = Mock()
        mock_writer = Mock()
        mock_writer_cls.return_value = mock_writer

        mock_config_cls = Mock()
        mock_config = Mock()
        mock_config.audit_logging_enabled = False  # Audit disabled
        mock_config_cls.return_value = mock_config

        with (
            patch(
                "des.application.orchestrator.JsonlAuditLogWriter",
                mock_writer_cls,
            ),
            patch(
                "des.adapters.driven.config.des_config.DESConfig",
                mock_config_cls,
            ),
        ):
            # Act
            des_orchestrator.validate_prompt(valid_prompt)

            # Assert - writer should never be instantiated when audit is disabled
            mock_writer_cls.assert_not_called()
            mock_writer.log_event.assert_not_called()

    def test_validate_prompt_audit_event_persisted_to_log_file(self, des_orchestrator):
        """
        GIVEN DESOrchestrator with audit logging enabled
        WHEN validate_prompt logs audit event
        THEN event is persisted via JsonlAuditLogWriter.log_event()
        """
        # Arrange
        valid_prompt = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/01-01.json -->
        Task: Implement feature
        """

        writer_patch, config_patch, mock_writer = _patch_audit_writer_and_config()

        with writer_patch, config_patch:
            # Act
            des_orchestrator.validate_prompt(valid_prompt)

            # Assert - verify log_event was called (which handles file persistence)
            assert mock_writer.log_event.called

    def test_validate_prompt_audit_event_has_structured_format(self, des_orchestrator):
        """
        GIVEN validate_prompt creating audit event
        WHEN event is logged
        THEN event follows PortAuditEvent structure with event_type, timestamp, data
        """
        # Arrange
        valid_prompt = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/01-01.json -->
        Task: Implement feature
        """

        writer_patch, config_patch, mock_writer = _patch_audit_writer_and_config()

        with writer_patch, config_patch:
            # Act
            des_orchestrator.validate_prompt(valid_prompt)

            # Assert
            call_args = mock_writer.log_event.call_args
            port_event = call_args[0][0]

            # Verify PortAuditEvent required fields
            assert port_event.timestamp is not None
            assert port_event.event_type is not None
            # Step 03-02: step_id is a direct PortAuditEvent field, not in data dict
            assert port_event.step_id is not None
            # rejection_reason is optional (only for BLOCKED events)

    def test_validate_prompt_uses_direct_feature_name_field(self, des_orchestrator):
        """
        AC3 (Step 03-02): validate_prompt PortAuditEvent uses direct feature_name
        field, not data dict, when DES-PROJECT-ID marker is present.
        """
        # Arrange
        prompt_with_project = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-PROJECT-ID: audit-log-refactor -->
        <!-- DES-STEP-FILE: steps/03-02.json -->
        Task: Update render_prompt audit logging
        """

        writer_patch, config_patch, mock_writer = _patch_audit_writer_and_config()

        with writer_patch, config_patch:
            # Act
            des_orchestrator.validate_prompt(prompt_with_project)

            # Assert
            call_args = mock_writer.log_event.call_args
            port_event = call_args[0][0]

            # feature_name and step_id as DIRECT fields
            assert port_event.feature_name == "audit-log-refactor"
            assert port_event.step_id == "03-02"

            # NOT in data dict
            assert "feature_name" not in port_event.data
            assert "step_id" not in port_event.data

    def test_validate_prompt_step_id_not_in_data_dict(self, des_orchestrator):
        """
        AC3 (Step 03-02): step_id must NOT appear in data dict when used as direct field.
        """
        # Arrange
        prompt = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/01-01.json -->
        Task: Implement feature
        """

        writer_patch, config_patch, mock_writer = _patch_audit_writer_and_config()

        with writer_patch, config_patch:
            # Act
            des_orchestrator.validate_prompt(prompt)

            # Assert
            call_args = mock_writer.log_event.call_args
            port_event = call_args[0][0]

            # step_id as direct field, NOT in data dict
            assert port_event.step_id == "01-01"
            assert "step_id" not in port_event.data
