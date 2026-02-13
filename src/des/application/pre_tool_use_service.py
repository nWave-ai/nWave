"""PreToolUseService - application service for Task tool invocation validation.

Orchestrates domain logic (MaxTurnsPolicy, DesMarkerParser) and driven ports
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
    from des.domain.max_turns_policy import MaxTurnsPolicy
    from des.ports.driven_ports.time_provider_port import TimeProvider
    from des.ports.driver_ports.validator_port import ValidatorPort


class PreToolUseService(PreToolUsePort):
    """Validates Task tool invocations before execution.

    Flow:
      1. Validate max_turns via MaxTurnsPolicy
         - If invalid: log HOOK_PRE_TOOL_USE_BLOCKED, return block
      1.5. Block step-id tasks without DES markers via DesEnforcementPolicy
         - If enforced: log HOOK_PRE_TOOL_USE_BLOCKED, return block
      2. Parse DES markers via DesMarkerParser
         - If not DES task: log HOOK_PRE_TOOL_USE_ALLOWED, return allow
      2.5. Validate marker completeness via MarkerCompletenessPolicy
         - If invalid: log HOOK_PRE_TOOL_USE_BLOCKED, return block
         - If orchestrator mode: log HOOK_PRE_TOOL_USE_ALLOWED, return allow
      3. Validate prompt structure via ValidatorPort
         - If invalid: log HOOK_PRE_TOOL_USE_BLOCKED, return block
         - If valid: log HOOK_PRE_TOOL_USE_ALLOWED, return allow
    """

    def __init__(
        self,
        max_turns_policy: MaxTurnsPolicy,
        marker_parser: DesMarkerParser,
        prompt_validator: ValidatorPort,
        audit_writer: AuditLogWriter,
        time_provider: TimeProvider,
        enforcement_policy: DesEnforcementPolicy | None = None,
        completeness_policy: MarkerCompletenessPolicy | None = None,
    ) -> None:
        self._max_turns_policy = max_turns_policy
        self._marker_parser = marker_parser
        self._prompt_validator = prompt_validator
        self._audit_writer = audit_writer
        self._time_provider = time_provider
        self._enforcement_policy = enforcement_policy
        self._completeness_policy = completeness_policy

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
        # Step 1: Validate max_turns
        policy_result = self._max_turns_policy.validate(input_data.max_turns)
        if not policy_result.is_valid:
            self._log_blocked(
                policy_result.reason or "MISSING_MAX_TURNS", hook_id=hook_id
            )
            return HookDecision.block(
                reason=policy_result.reason or "MISSING_MAX_TURNS"
            )

        # Step 1.5: Block step-id tasks without DES markers
        if self._enforcement_policy:
            enforcement = self._enforcement_policy.check(input_data.prompt)
            if enforcement.is_enforced:
                self._log_blocked(
                    enforcement.reason or "DES_MARKERS_MISSING", hook_id=hook_id
                )
                return HookDecision.block(
                    reason=enforcement.reason or "DES_MARKERS_MISSING",
                    recovery_suggestions=enforcement.recovery_suggestions,
                )

        # Step 2: Parse DES markers
        markers = self._marker_parser.parse(input_data.prompt)

        if not markers.is_des_task:
            # Ad-hoc task: max_turns validated, no prompt validation needed
            self._log_allowed(context="non_des_task", hook_id=hook_id)
            return HookDecision.allow()

        # Step 2.5: Validate marker completeness
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

        # Step 3: Validate DES prompt structure
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
