"""PreToolUseService - application service for Agent tool invocation validation.

Orchestrates domain logic (DesMarkerParser, MarkerCompletenessPolicy) and driven ports
(ValidatorPort, AuditLogWriter, TimeProvider) to produce allow/block decisions.

This service implements the PreToolUsePort driver port interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter
from des.ports.driver_ports.pre_tool_use_port import (
    HookDecision,
    PreToolUseInput,
    PreToolUsePort,
)


if TYPE_CHECKING:
    from des.domain.des_enforcement_policy import DesEnforcementPolicy
    from des.domain.des_marker_parser import DesMarkerParser
    from des.domain.marker_completeness_policy import MarkerCompletenessPolicy
    from des.ports.driven_ports.time_provider_port import TimeProvider
    from des.ports.driver_ports.validator_port import ValidatorPort


class PreToolUseService(PreToolUsePort):
    """Validates Agent tool invocations before execution.

    Flow:
      1. Parse DES markers via DesMarkerParser
      2. Block step-id tasks without DES markers via DesEnforcementPolicy
         - If enforced: log HOOK_PRE_TOOL_USE_BLOCKED, return block
      2.5. Whole-project exemption (ADR-PST-001): if deliverable_type is in
         DesEnforcementPolicy.EXEMPT_DELIVERABLE_TYPES (plugin/skill), log
         HOOK_PRE_TOOL_USE_ALLOWED and return allow immediately — a plugin/skill
         project is not policed at all (no completeness/structure validation).
         Unreachable for application/None (not in the exempt set).
      3. If not DES task: log HOOK_PRE_TOOL_USE_ALLOWED, return allow immediately
         (no prompt validation — non-DES tasks pass through)
      4. Validate marker completeness via MarkerCompletenessPolicy
         - If invalid: log HOOK_PRE_TOOL_USE_BLOCKED, return block
         - If orchestrator mode: log HOOK_PRE_TOOL_USE_ALLOWED, return allow
      5. Validate prompt structure via ValidatorPort
         - If invalid: log HOOK_PRE_TOOL_USE_BLOCKED, return block
         - If valid: log HOOK_PRE_TOOL_USE_ALLOWED, return allow
    """

    def __init__(
        self,
        marker_parser: DesMarkerParser,
        prompt_validator: ValidatorPort,
        audit_writer: AuditLogWriter,
        time_provider: TimeProvider,
        enforcement_policy: DesEnforcementPolicy | None = None,
        completeness_policy: MarkerCompletenessPolicy | None = None,
        deliverable_type: str | None = None,
    ) -> None:
        self._marker_parser = marker_parser
        self._prompt_validator = prompt_validator
        self._audit_writer = audit_writer
        self._time_provider = time_provider
        self._enforcement_policy = enforcement_policy
        self._completeness_policy = completeness_policy
        # ADR-PST-001 (feature plugin-skill-deliverable-type): resolved once per
        # dispatch by the DESConfig adapter, threaded pure into policy.check().
        # ``None`` keeps the app-code enforcement path byte-identical.
        self._deliverable_type = deliverable_type

    def validate(
        self,
        input_data: PreToolUseInput,
        hook_id: str | None = None,
    ) -> HookDecision:
        """Validate a Task tool invocation.

        Args:
            input_data: Parsed input from the hook protocol
            hook_id: Optional correlation ID from the adapter hook invocation.
                When provided, included in all emitted audit events for correlation.

        Returns:
            HookDecision indicating allow or block
        """
        # Step 1: Parse DES markers
        markers = self._marker_parser.parse(input_data.prompt)

        # Step 2: Enforce DES markers on step-id references (applies to all tasks)
        if self._enforcement_policy:
            enforcement = self._enforcement_policy.check(
                input_data.prompt, self._deliverable_type
            )
            if enforcement.is_enforced:
                self._log_blocked(
                    enforcement.reason or "DES_MARKERS_MISSING", hook_id=hook_id
                )
                return HookDecision.block(
                    reason=enforcement.reason or "DES_MARKERS_MISSING",
                    recovery_suggestions=enforcement.recovery_suggestions,
                )

            # Whole-project exemption (ADR-PST-001): declaring plugin/skill exempts
            # ALL step dispatches for that project -- the policy has already
            # certified is_enforced=False, so the service honors that verdict at
            # whole-project granularity and allows immediately, without re-imposing
            # discipline via marker-completeness/prompt-structure validation. The
            # service only THREADS this context; the enforcement decision stays in
            # the pure policy. App-code (None/application) is unaffected: it never
            # enters this branch, so its path is byte-identical.
            if (
                self._deliverable_type
                in self._enforcement_policy.EXEMPT_DELIVERABLE_TYPES
            ):
                self._log_allowed(context="deliverable_type_exempt", hook_id=hook_id)
                return HookDecision.allow()

        if not markers.is_des_task:
            # Non-DES task (no step-id enforcement triggered): allow immediately
            # No max_turns check, no prompt validation for non-DES tasks
            self._log_allowed(context="non_des_task", hook_id=hook_id)
            return HookDecision.allow()

        # Step 3: Validate marker completeness
        if self._completeness_policy:
            completeness = self._completeness_policy.validate(markers)
            if not completeness.is_valid:
                self._log_blocked(
                    completeness.reason or "DES_MARKERS_INCOMPLETE", hook_id=hook_id
                )
                return HookDecision.block(
                    reason=completeness.reason or "DES_MARKERS_INCOMPLETE",
                    recovery_suggestions=completeness.recovery_suggestions,
                )

        if markers.is_orchestrator_mode:
            # Orchestrator mode: relaxed validation
            self._log_allowed(context="orchestrator_mode", hook_id=hook_id)
            return HookDecision.allow()

        # Step 5: Validate DES prompt structure
        validation_result = self._prompt_validator.validate_prompt(input_data.prompt)

        if validation_result.task_invocation_allowed:
            self._log_allowed(context="des_validated", hook_id=hook_id)
            return HookDecision.allow()
        else:
            reason = "; ".join(validation_result.errors)
            self._log_blocked(reason, hook_id=hook_id)
            return HookDecision.block(reason=reason)

    def _log_allowed(self, context: str, hook_id: str | None = None) -> None:
        """Log an allowed invocation to the audit trail."""
        self._audit_writer.log_event(
            AuditEvent(
                event_type="HOOK_PRE_TOOL_USE_ALLOWED",
                timestamp=self._time_provider.now_utc().isoformat(),
                hook_id=hook_id,
                data={"context": context},
            )
        )

    def _log_blocked(self, reason: str, hook_id: str | None = None) -> None:
        """Log a blocked invocation to the audit trail."""
        self._audit_writer.log_event(
            AuditEvent(
                event_type="HOOK_PRE_TOOL_USE_BLOCKED",
                timestamp=self._time_provider.now_utc().isoformat(),
                hook_id=hook_id,
                data={"reason": reason},
            )
        )
