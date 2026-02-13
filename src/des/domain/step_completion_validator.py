"""Step completion validator domain logic.

Pure business rules for validating TDD phase completion of a step.
No I/O dependencies - operates on in-memory PhaseEvent lists and TDDSchema.

Replaces inline validation in:
- SubagentStopHook._validate_from_execution_log() (lines 199-324)
- claude_code_hook_adapter._verify_step_from_append_only_log()

Validation rules (from TDDSchema):
1. All 7 TDD phases must have an event (missing = abandoned)
2. EXECUTED phases must have outcome PASS or FAIL
3. Terminal phases (COMMIT) must have outcome PASS
4. SKIPPED phases must have a valid skip prefix
5. SKIPPED phases with blocking prefixes (DEFERRED) are invalid
6. Zero events = SILENT_COMPLETION error
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from des.domain.phase_event import PhaseEvent
    from des.domain.tdd_schema import TDDSchema


@dataclass(frozen=True)
class CompletionResult:
    """Result of step completion validation.

    Attributes:
        is_valid: True if all phases pass validation
        missing_phases: Phases with no event at all (abandoned)
        incomplete_phases: EXECUTED phases with invalid outcome
        invalid_skips: SKIPPED phases with invalid or blocking reason
        error_messages: Human-readable error descriptions
        recovery_suggestions: Actionable steps to fix failures
        error_type: Classification of the primary error
    """

    is_valid: bool
    missing_phases: list[str] = field(default_factory=list)
    incomplete_phases: list[str] = field(default_factory=list)
    invalid_skips: list[str] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)
    recovery_suggestions: list[str] = field(default_factory=list)
    error_type: str | None = None


class StepCompletionValidator:
    """Validates TDD phase completion for a step.

    THE SINGLE implementation of TDD phase completion validation.
    This is a stateless validator with no I/O dependencies.

    Constructor:
        StepCompletionValidator(schema: TDDSchema)

    Usage:
        validator = StepCompletionValidator(schema)
        result = validator.validate(events)
        if not result.is_valid:
            print(result.error_messages)
    """

    def __init__(self, schema: TDDSchema) -> None:
        self._schema = schema

    def validate(self, events: list[PhaseEvent]) -> CompletionResult:
        """Validate TDD phase completion from a list of phase events.

        Args:
            events: List of PhaseEvent objects for one step (already filtered
                    by step_id before calling this method).

        Returns:
            CompletionResult with validation details
        """
        # Rule 6: Zero events = SILENT_COMPLETION
        if not events:
            all_phases = ", ".join(self._schema.tdd_phases)
            return CompletionResult(
                is_valid=False,
                missing_phases=list(self._schema.tdd_phases),
                error_type="SILENT_COMPLETION",
                error_messages=[
                    "Agent completed without updating step file",
                    f"Missing phases: {all_phases}",
                ],
                recovery_suggestions=[
                    "Check agent transcript for errors that prevented execution",
                    "Verify agent received correct step context and instructions",
                    f"Resume execution to complete missing phases: {all_phases}",
                ],
            )

        # Build phase lookup: last event per phase wins
        phase_map: dict[str, PhaseEvent] = {}
        for event in events:
            phase_map[event.phase_name] = event

        missing_phases: list[str] = []
        incomplete_phases: list[str] = []
        invalid_skips: list[str] = []
        error_messages: list[str] = []
        recovery_suggestions: list[str] = []

        for phase in self._schema.tdd_phases:
            # Rule 1: All phases must have an event
            if phase not in phase_map:
                missing_phases.append(phase)
                continue

            event = phase_map[phase]
            self._validate_phase_event(
                phase,
                event,
                missing_phases,
                incomplete_phases,
                invalid_skips,
                error_messages,
            )

        # Add missing phases to error_messages for clear reporting
        if missing_phases:
            error_messages.append(f"Missing phases: {', '.join(missing_phases)}")

        # Build recovery suggestions based on what failed
        if missing_phases:
            recovery_suggestions.extend(
                [
                    f"Resume execution to complete missing phases: {', '.join(missing_phases)}",
                    "Format: step_id|phase|status|data|timestamp",
                ]
            )

        if incomplete_phases or invalid_skips or error_messages:
            recovery_suggestions.extend(
                [
                    "Fix invalid phase entries in execution-log.yaml",
                    "Ensure EXECUTED phases have PASS/FAIL outcome",
                    "Ensure SKIPPED phases have valid reason prefix",
                ]
            )

        # Determine overall result
        validation_failed = bool(
            missing_phases or incomplete_phases or invalid_skips or error_messages
        )

        if not validation_failed:
            return CompletionResult(is_valid=True)

        # Classify the primary error type
        error_type = self._classify_error_type(
            missing_phases,
            incomplete_phases,
            invalid_skips,
        )

        return CompletionResult(
            is_valid=False,
            missing_phases=missing_phases,
            incomplete_phases=incomplete_phases,
            invalid_skips=invalid_skips,
            error_messages=error_messages,
            recovery_suggestions=recovery_suggestions,
            error_type=error_type,
        )

    def _validate_phase_event(
        self,
        phase: str,
        event: PhaseEvent,
        missing_phases: list[str],
        incomplete_phases: list[str],
        invalid_skips: list[str],
        error_messages: list[str],
    ) -> None:
        """Validate a single phase event against TDD schema rules.

        Mutates the provided lists in-place for efficiency.
        """
        status = event.status
        outcome = event.outcome

        # Rule 2 & 3: Validate EXECUTED phases
        if status == "EXECUTED":
            self._validate_executed_phase(
                phase,
                outcome,
                incomplete_phases,
                error_messages,
            )

        # Rule 4 & 5: Validate SKIPPED phases
        elif status == "SKIPPED":
            self._validate_skipped_phase(
                phase,
                outcome,
                invalid_skips,
                error_messages,
            )

        # Invalid status
        elif status not in self._schema.valid_statuses:
            error_messages.append(
                f"{phase}: Invalid status '{status}' "
                f"(must be: {', '.join(self._schema.valid_statuses)})"
            )

    def _validate_executed_phase(
        self,
        phase: str,
        outcome: str,
        incomplete_phases: list[str],
        error_messages: list[str],
    ) -> None:
        """Validate an EXECUTED phase's outcome."""
        # Rule 2: Outcome must be PASS or FAIL
        if outcome not in ("PASS", "FAIL"):
            incomplete_phases.append(phase)
            error_messages.append(
                f"{phase}: Invalid outcome '{outcome}' (must be PASS or FAIL)"
            )
        # Rule 3: Terminal phases must PASS
        elif phase in self._schema.terminal_phases and outcome != "PASS":
            incomplete_phases.append(phase)
            error_messages.append(
                f"{phase}: Terminal phase must have outcome PASS (not FAIL)"
            )

    def _validate_skipped_phase(
        self,
        phase: str,
        outcome: str,
        invalid_skips: list[str],
        error_messages: list[str],
    ) -> None:
        """Validate a SKIPPED phase's reason prefix."""
        # Rule 4: Must have valid skip prefix
        valid_prefix_found = any(
            outcome.startswith(prefix) for prefix in self._schema.valid_skip_prefixes
        )
        if not valid_prefix_found:
            invalid_skips.append(phase)
            error_messages.append(
                f"{phase}: Invalid skip reason '{outcome}' "
                f"(must start with: {', '.join(self._schema.valid_skip_prefixes)})"
            )

        # Rule 5: Blocking prefixes not allowed
        blocking_prefix_found = any(
            outcome.startswith(prefix) for prefix in self._schema.blocking_skip_prefixes
        )
        if blocking_prefix_found:
            invalid_skips.append(phase)
            error_messages.append(
                f"{phase}: Skip reason '{outcome}' blocks commit (DEFERRED not allowed)"
            )

    @staticmethod
    def _classify_error_type(
        missing_phases: list[str],
        incomplete_phases: list[str],
        invalid_skips: list[str],
    ) -> str:
        """Classify the primary error type for reporting."""
        phases_are_missing = bool(missing_phases)
        phases_are_incomplete = bool(incomplete_phases)
        skips_are_invalid = bool(invalid_skips)

        if phases_are_missing and not phases_are_incomplete and not skips_are_invalid:
            return "ABANDONED_PHASE"
        if phases_are_incomplete and not phases_are_missing and not skips_are_invalid:
            return "INCOMPLETE_PHASE"
        if skips_are_invalid and not phases_are_missing and not phases_are_incomplete:
            return "INVALID_SKIP"
        return "MULTIPLE_ERRORS"
