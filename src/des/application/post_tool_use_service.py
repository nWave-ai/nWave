"""PostToolUseService - checks audit log and injects DES continuation context.

Concrete service (no abstract port) per ADR-2: only one consumer,
only one implementation. Extracting an interface is trivial if needed later.

Called by: ClaudeCodeHookAdapter when PostToolUse hook fires after Task returns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from des.ports.driven_ports.audit_log_reader import AuditLogReader

DES_MARKER_REMINDER = """
MANDATORY: Include these DES markers in the Task prompt:
<!-- DES-VALIDATION : required -->
<!-- DES-PROJECT-ID : {project-id} -->
<!-- DES-STEP-ID : {step-id} -->

Without these markers, DES validation is bypassed and the step won't be verified.
Read nWave/tasks/nw/execute.md for the full DES Prompt Template with all 9 mandatory sections."""


class PostToolUseService:
    """Checks DES completion status and injects orchestrator continuation context.

    For DES tasks:
    - On PASSED: injects continuation context reminding orchestrator to dispatch
      the next step with DES markers.
    - On FAILED (allowed_despite_failure): injects failure notification with
      DES marker reminder for re-dispatch.

    For non-DES tasks: returns None (clean passthrough).
    """

    def __init__(self, audit_reader: AuditLogReader) -> None:
        self._audit_reader = audit_reader

    def check_completion_status(self, *, is_des_task: bool = False) -> str | None:
        """Check the last sub-agent's DES completion status.

        Args:
            is_des_task: True if the just-completed Task had DES markers in its prompt.

        Returns:
            additionalContext string for the orchestrator, or None for passthrough.
        """
        passed_entry = self._audit_reader.read_last_entry(
            event_type="HOOK_SUBAGENT_STOP_PASSED",
        )
        failed_entry = self._audit_reader.read_last_entry(
            event_type="HOOK_SUBAGENT_STOP_FAILED",
        )

        passed_ts = (passed_entry or {}).get("timestamp", "")
        failed_ts = (failed_entry or {}).get("timestamp", "")

        # Most recent event is PASSED
        if passed_entry and passed_ts >= failed_ts:
            if is_des_task:
                return self._build_continuation_context(passed_entry)
            return None

        # Most recent event is FAILED
        if failed_entry and failed_entry.get("allowed_despite_failure"):
            return self._build_failure_context(failed_entry, is_des_task=is_des_task)

        return None

    def _build_continuation_context(self, passed_entry: dict) -> str:
        """Build success continuation context for the orchestrator."""
        feature_name = passed_entry.get("feature_name", "unknown")
        step_id = passed_entry.get("step_id", "unknown")

        return (
            f"DES STEP COMPLETED [{feature_name}/{step_id}]\n"
            f"Status: PASSED\n"
            f"\n"
            f"Continue the DELIVER workflow. Dispatch the next step.\n"
            + DES_MARKER_REMINDER
        )

    def _build_failure_context(self, failed_entry: dict, *, is_des_task: bool) -> str:
        """Build failure notification context for the orchestrator."""
        feature_name = failed_entry.get("feature_name", "unknown")
        step_id = failed_entry.get("step_id", "unknown")
        errors = failed_entry.get("validation_errors", [])
        error_text = "; ".join(errors) if errors else "Unknown validation failure"

        base = (
            f"DES STEP INCOMPLETE [{feature_name}/{step_id}]\n"
            f"Status: FAILED\n"
            f"Errors: {error_text}\n"
            f"\n"
            f"The sub-agent failed to complete all required TDD phases.\n"
            f"You MUST RE-DISPATCH the agent to fix the missing work."
        )

        if is_des_task:
            return base + "\n" + DES_MARKER_REMINDER

        return base
