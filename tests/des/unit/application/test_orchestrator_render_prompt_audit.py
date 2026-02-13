"""
Unit tests for DESOrchestrator.render_prompt audit logging (Step 03-02).

Tests that render_prompt passes feature_name (via project_id parameter) and step_id
as direct PortAuditEvent fields for TASK_INVOCATION_STARTED and TASK_INVOCATION_VALIDATED
events.
"""

from unittest.mock import Mock, patch


def _patch_log_audit_event():
    """Patch _log_audit_event at module level to capture calls."""
    mock_log = Mock()
    log_patch = patch(
        "des.application.orchestrator._log_audit_event",
        mock_log,
    )
    return log_patch, mock_log


class TestRenderPromptAuditFeatureName:
    """AC1-2: render_prompt passes feature_name (project_id) and step_id to _log_audit_event."""

    def test_render_prompt_passes_feature_name_from_project_id(self, des_orchestrator):
        """AC1: render_prompt accepts project_id and passes it as feature_name
        to _log_audit_event for TASK_INVOCATION_STARTED event."""
        log_patch, mock_log = _patch_log_audit_event()

        with log_patch:
            des_orchestrator.render_prompt(
                command="/nw:execute",
                agent="@software-crafter",
                step_file="steps/03-02.json",
                project_id="audit-log-refactor",
            )

            # Find the TASK_INVOCATION_STARTED call
            started_calls = [
                c
                for c in mock_log.call_args_list
                if c[0][0] == "TASK_INVOCATION_STARTED"
            ]
            assert len(started_calls) == 1, (
                f"Expected 1 TASK_INVOCATION_STARTED call, got {len(started_calls)}"
            )

            call_kwargs = started_calls[0][1]
            assert call_kwargs.get("feature_name") == "audit-log-refactor"

    def test_render_prompt_passes_step_id_to_started_event(self, des_orchestrator):
        """AC2: TASK_INVOCATION_STARTED event logs both feature_name and step_id."""
        log_patch, mock_log = _patch_log_audit_event()

        with log_patch:
            des_orchestrator.render_prompt(
                command="/nw:execute",
                agent="@software-crafter",
                step_file="steps/03-02.json",
                project_id="audit-log-refactor",
            )

            started_calls = [
                c
                for c in mock_log.call_args_list
                if c[0][0] == "TASK_INVOCATION_STARTED"
            ]
            call_kwargs = started_calls[0][1]

            assert call_kwargs.get("step_id") == "03-02"
            assert call_kwargs.get("feature_name") == "audit-log-refactor"

    def test_render_prompt_passes_feature_name_to_validated_event(
        self, des_orchestrator
    ):
        """AC2: TASK_INVOCATION_VALIDATED event also logs feature_name and step_id."""
        log_patch, mock_log = _patch_log_audit_event()

        with log_patch:
            des_orchestrator.render_prompt(
                command="/nw:execute",
                agent="@software-crafter",
                step_file="steps/03-02.json",
                project_id="audit-log-refactor",
            )

            validated_calls = [
                c
                for c in mock_log.call_args_list
                if c[0][0] == "TASK_INVOCATION_VALIDATED"
            ]
            assert len(validated_calls) == 1, (
                f"Expected 1 TASK_INVOCATION_VALIDATED call, got {len(validated_calls)}"
            )

            call_kwargs = validated_calls[0][1]
            assert call_kwargs.get("feature_name") == "audit-log-refactor"
            assert call_kwargs.get("step_id") == "03-02"

    def test_render_prompt_without_project_id_passes_none_feature_name(
        self, des_orchestrator
    ):
        """When project_id is not provided, feature_name is not passed (backward compat)."""
        log_patch, mock_log = _patch_log_audit_event()

        with log_patch:
            des_orchestrator.render_prompt(
                command="/nw:execute",
                agent="@software-crafter",
                step_file="steps/03-02.json",
            )

            started_calls = [
                c
                for c in mock_log.call_args_list
                if c[0][0] == "TASK_INVOCATION_STARTED"
            ]
            call_kwargs = started_calls[0][1]

            # feature_name should not be present or be None
            assert call_kwargs.get("feature_name") is None
