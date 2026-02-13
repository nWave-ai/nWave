"""
PhaseStateValidator: Validates phase state transitions and field requirements.

Detects invalid phase states:
- EXECUTED phases without outcome field
- SKIPPED phases without blocked_by reason

Generates recovery suggestions to guide developers toward correct state.
"""

from typing import Any


class PhaseStateValidator:
    """
    Validates phase state transitions and required fields.

    Ensures:
    - EXECUTED phases have outcome field with description
    - SKIPPED phases have blocked_by field with reason
    - All phase states are valid and complete
    """

    # Valid reason codes for SKIPPED phases
    VALID_SKIP_REASONS = [
        "CHECKPOINT_PENDING",
        "NOT_APPLICABLE",
        "BLOCKED_BY_DEPENDENCY",
        "AWAITING_CLARIFICATION",
    ]

    def validate_phase_state(self, phase: dict[str, Any]) -> list[str]:
        """
        Validate a phase's state and required fields.

        Args:
            phase: Phase dictionary with status, outcome, blocked_by fields

        Returns:
            List of error messages if state is invalid, empty list if valid
        """
        errors = []

        status = phase.get("status")
        phase_name = phase.get("phase_name", "UNKNOWN")

        # Validate EXECUTED state
        if status == "EXECUTED":
            outcome = phase.get("outcome")
            if outcome is None or (isinstance(outcome, str) and not outcome.strip()):
                errors.append(
                    f"Invalid phase state: {phase_name} is EXECUTED but missing outcome field. "
                    f"EXECUTED phases must have an outcome describing what was accomplished."
                )

        # Validate SKIPPED state
        elif status == "SKIPPED":
            blocked_by = phase.get("blocked_by")
            if blocked_by is None or (
                isinstance(blocked_by, str) and not blocked_by.strip()
            ):
                errors.append(
                    f"Invalid phase state: {phase_name} is SKIPPED but missing blocked_by reason. "
                    f"SKIPPED phases must explain why they were skipped (e.g., CHECKPOINT_PENDING, NOT_APPLICABLE)."
                )

        return errors

    def generate_recovery_suggestions(self, phase: dict[str, Any]) -> list[str]:
        """
        Generate recovery suggestions for invalid phase state.

        Args:
            phase: Invalid phase dictionary

        Returns:
            List of actionable recovery suggestions
        """
        suggestions = []
        status = phase.get("status")
        phase_name = phase.get("phase_name", "UNKNOWN")

        if status == "EXECUTED":
            outcome = phase.get("outcome")
            if outcome is None or (isinstance(outcome, str) and not outcome.strip()):
                suggestions = self._generate_executed_state_suggestions(phase_name)

        elif status == "SKIPPED":
            blocked_by = phase.get("blocked_by")
            if blocked_by is None or (
                isinstance(blocked_by, str) and not blocked_by.strip()
            ):
                suggestions = self._generate_skipped_state_suggestions(phase_name)

        return suggestions

    def _generate_executed_state_suggestions(self, phase_name: str) -> list[str]:
        """
        Generate suggestions for EXECUTED phase missing outcome.

        Args:
            phase_name: Name of the phase with invalid state

        Returns:
            List of recovery suggestions
        """
        return [
            (
                f"WHY: The outcome field provides evidence that {phase_name} "
                f"completed and documents what was accomplished. "
                f"Without it, reviewers cannot see what was done.\n\n"
                f"HOW: Add a descriptive outcome describing the results of {phase_name}. "
                f"This should be a brief summary of what was completed.\n\n"
                f"ACTION: Set phase.outcome to a descriptive text like "
                f"'Implementation complete, all tests passing' or 'Code refactored for readability'."
            ),
            (
                f"WHY: Every EXECUTED phase must document its outcome so the "
                f"step file serves as a complete record of work done.\n\n"
                f"HOW: Write a 1-10 word outcome describing the results (e.g., "
                f"'Unit tests passing', 'Domain model refactored', 'All AC verified').\n\n"
                f"ACTION: Update state.tdd_cycle.phase_execution_log entry for {phase_name}: "
                f"set outcome field to a brief description of what was accomplished."
            ),
            (
                f"WHY: The outcome field is required by the step file schema "
                f"to track progress and communicate completion.\n\n"
                f"HOW: Provide context about what {phase_name} achieved. "
                f"This helps your team understand the state of the work.\n\n"
                f"ACTION: Add outcome following the format: "
                f"'[noun] [verb] [result]' such as "
                f"'Tests passing', 'Code refactored', or 'Design validated'."
            ),
        ]

    def _generate_skipped_state_suggestions(self, phase_name: str) -> list[str]:
        """
        Generate suggestions for SKIPPED phase missing blocked_by.

        Args:
            phase_name: Name of the phase with invalid state

        Returns:
            List of recovery suggestions
        """
        valid_codes = ", ".join(self.VALID_SKIP_REASONS)

        return [
            (
                f"WHY: The blocked_by field explains why {phase_name} was skipped, "
                f"providing context for the decision to skip. This is crucial for understanding "
                f"your workflow and helps others learn from the decision.\n\n"
                f"HOW: Choose a reason code from the approved list: {valid_codes}. "
                f"Each code explains a different skip reason.\n\n"
                f"ACTION: Set phase.blocked_by to one of: {valid_codes}. "
                f"For example: 'NOT_APPLICABLE: {phase_name} not needed for this feature' or "
                f"'CHECKPOINT_PENDING: Complex refactoring needs domain review'."
            ),
            (
                f"WHY: SKIPPED phases must declare their reason so the system understands "
                f"why they were not executed. This prevents confusion about incomplete phases.\n\n"
                f"HOW: Use a structured reason code indicating the skip category. "
                f"Valid codes: {valid_codes}.\n\n"
                f"ACTION: Update state.tdd_cycle.phase_execution_log entry for {phase_name}: "
                f"set blocked_by to a valid skip reason code (e.g., 'NOT_APPLICABLE')."
            ),
            (
                f"WHY: The blocked_by field creates a record of why you chose to skip {phase_name}, "
                f"which is important for code reviews and knowledge sharing.\n\n"
                f"HOW: Select the most appropriate reason from the approved list. "
                f"If none fit exactly, use 'CHECKPOINT_PENDING' for phases waiting on decisions.\n\n"
                f"ACTION: Set phase.blocked_by using this format: "
                f"'[REASON_CODE]: [brief explanation]'. "
                f"Example: 'NOT_APPLICABLE: Utility function needs no architectural patterns'."
            ),
        ]
