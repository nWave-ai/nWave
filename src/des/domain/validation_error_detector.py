"""
ValidationErrorDetector: Domain service for detecting validation errors in step files.

Detects validation failures for missing mandatory sections and TDD phases,
generating specific recovery guidance explaining WHY and HOW to fix each error.

Uses canonical TDD cycle from step-tdd-cycle-schema.json v4.0 (single source of truth).

Implements AC-005.1 and AC-005.4:
- AC-005.1: Identifies missing required step file fields and invalid phase sequences
- AC-005.4: Provides specific guidance on what to fix for each validation error

Failure modes detected:
- Missing mandatory sections (acceptance_criteria, phase_execution_log)
- Invalid phase execution sequences
- Incomplete acceptance criteria details
- Partially-valid step files with mixed valid/invalid state
"""

from typing import Any


class ValidationErrorDetector:
    """
    Domain service for detecting validation errors in step file structure.

    Identifies:
    1. Missing required fields (step_id, acceptance_criteria, etc.)
    2. Invalid phase sequences (out-of-order execution)
    3. Missing acceptance criteria details
    4. Incomplete phase documentation

    Uses canonical TDD cycle from schema (single source of truth).
    """

    # Required fields that every step file must have
    REQUIRED_STEP_FIELDS = [
        "step_id",
        "step_name",
        "project_id",
        "acceptance_criteria",
        "required_acceptance_test",
        "tdd_cycle",
    ]

    def __init__(self):
        """Initialize detector with schema loader."""
        from des.domain.tdd_schema import get_tdd_schema

        self._schema = get_tdd_schema()
        self.VALID_PHASE_SEQUENCE = self._schema.tdd_phases

    def detect_errors(self, step: dict[str, Any]) -> list[str]:
        """
        Detect validation errors in a step file.

        Args:
            step: Step file data dictionary

        Returns:
            List of error messages (empty if no errors)
        """
        errors = []

        # Check required fields
        for field in self.REQUIRED_STEP_FIELDS:
            if field not in step:
                errors.append(f"Missing required field: {field}")
            elif field == "acceptance_criteria" and not step.get(field):
                errors.append(f"Missing required field: {field} (empty or null)")

        return errors

    def detect_phase_sequence_errors(self, tdd_cycle: dict[str, Any]) -> list[str]:
        """
        Detect invalid phase execution sequences.

        Args:
            tdd_cycle: TDD cycle data with phase_execution_log

        Returns:
            List of sequence error messages
        """
        # Validate log structure exists
        structure_errors = self._validate_phase_log_structure(tdd_cycle)
        if structure_errors:
            return structure_errors

        phases = tdd_cycle.get("phase_execution_log", [])
        phase_names = [p.get("phase_name") for p in phases if "phase_name" in p]

        # Detect schema version and validate sequence
        valid_sequence = self._get_valid_phase_sequence(phase_names)
        return self._check_phase_ordering(phase_names, valid_sequence)

    def _validate_phase_log_structure(self, tdd_cycle: dict[str, Any]) -> list[str]:
        """Validate that phase_execution_log exists and is not empty."""
        if "phase_execution_log" not in tdd_cycle:
            return ["Missing phase_execution_log in tdd_cycle"]

        phases = tdd_cycle.get("phase_execution_log", [])
        if not phases:
            return ["Empty phase_execution_log"]

        return []

    def _get_valid_phase_sequence(self, phase_names: list[str]) -> tuple[str, ...]:
        """Return canonical TDD cycle from schema."""
        return self.VALID_PHASE_SEQUENCE

    def _check_phase_ordering(
        self, phase_names: list[str], valid_sequence: list[str]
    ) -> list[str]:
        """Validate that phases appear in correct order."""
        errors = []
        expected_index = 0

        for phase_name in phase_names:
            if phase_name in valid_sequence:
                phase_expected_index = valid_sequence.index(phase_name)
                if phase_expected_index < expected_index:
                    errors.append(
                        f"Invalid phase sequence: {phase_name} appears after "
                        f"{valid_sequence[expected_index - 1]} (invalid order)"
                    )
                else:
                    expected_index = phase_expected_index + 1

        return errors

    def detect_acceptance_criteria_errors(self, step: dict[str, Any]) -> list[str]:
        """
        Detect missing or incomplete acceptance criteria.

        Args:
            step: Step file data

        Returns:
            List of acceptance criteria error messages
        """
        errors = []

        acceptance_criteria = step.get("acceptance_criteria", "")

        # Check if acceptance_criteria field exists and is not empty
        if (
            not acceptance_criteria
            or not isinstance(acceptance_criteria, str)
            or len(acceptance_criteria.strip()) == 0
        ):
            errors.append(
                "Missing or empty acceptance_criteria: must contain concrete, testable acceptance criteria"
            )
            return errors

        # Check if acceptance_criteria has sufficient detail (< 20 chars is likely too brief)
        if len(acceptance_criteria) < 20:
            errors.append(
                f"Acceptance criteria too brief ({len(acceptance_criteria)} chars): should have multiple testable criteria"
            )

        return errors

    def get_fix_guidance(self, error: str) -> str:
        """
        Generate specific, actionable fix guidance for a validation error.

        Args:
            error: The validation error message

        Returns:
            Specific fix guidance string
        """
        # Try specific error patterns first
        guidance = self._get_specific_guidance(error)
        if guidance:
            return guidance

        # Fall back to generic guidance
        return self._get_generic_guidance()

    def _get_specific_guidance(self, error: str) -> str:
        """Extract specific fix guidance for known error patterns."""
        error_lower = error.lower()

        if "acceptance_criteria" in error_lower:
            return self._get_acceptance_criteria_guidance()

        if "phase_execution_log" in error_lower:
            return self._get_phase_log_guidance()

        if "phase sequence" in error_lower or "invalid phase" in error_lower:
            return self._get_phase_sequence_guidance()

        if "required_acceptance_test" in error_lower:
            return self._get_acceptance_test_guidance()

        return None

    def _get_acceptance_criteria_guidance(self) -> str:
        """Guidance for missing acceptance_criteria field."""
        return (
            "Add 'acceptance_criteria' field to step file with comma-separated or "
            "bullet-point acceptance criteria. "
            "Example: 'Detects missing fields, Identifies phase sequence errors, "
            "Provides actionable fix guidance'"
        )

    def _get_phase_log_guidance(self) -> str:
        """Guidance for missing phase_execution_log."""
        return (
            "Ensure 'tdd_cycle.phase_execution_log' contains array of all phases "
            "with status and outcome fields. "
            "Each phase should have: phase_name, status (EXECUTED/NOT_EXECUTED/IN_PROGRESS), "
            "outcome (brief description)"
        )

    def _get_phase_sequence_guidance(self) -> str:
        """Guidance for invalid phase sequence."""
        return (
            "Reorder phases in phase_execution_log to follow valid TDD sequence. "
            "For 5-phase (v4.0): PREPARE → RED_ACCEPTANCE → RED_UNIT → GREEN → COMMIT. "
            "For 7-phase (v3.0): PREPARE → RED_ACCEPTANCE → RED_UNIT → GREEN → REVIEW → "
            "REFACTOR_CONTINUOUS → COMMIT. "
            "For 14-phase (v1.0): PREPARE → RED_ACCEPTANCE → RED_UNIT → GREEN_UNIT → "
            "CHECK_ACCEPTANCE → GREEN_ACCEPTANCE → REVIEW → REFACTOR_L1-L4 → "
            "POST_REFACTOR_REVIEW → FINAL_VALIDATE → COMMIT"
        )

    def _get_acceptance_test_guidance(self) -> str:
        """Guidance for missing required_acceptance_test field."""
        return (
            "Add 'required_acceptance_test' field naming the acceptance test scenario "
            "that validates this step. "
            "Example: 'test_scenario_003_validation_failure_provides_recovery_suggestions'"
        )

    def _get_generic_guidance(self) -> str:
        """Generic guidance when specific error pattern not found."""
        return (
            "Review step file schema against specification in docs/feature/des-us005/roadmap.yaml. "
            "Ensure all required fields are present and have valid values."
        )

    def validate_partial_state(self, step: dict[str, Any]) -> dict[str, list[str]]:
        """
        Analyze partially valid step file, distinguishing valid from invalid portions.

        Args:
            step: Step file with partial execution

        Returns:
            Dictionary with:
            - valid_phases: List of completed phases
            - invalid_phases: List of phases with errors
            - incomplete_phases: List of IN_PROGRESS phases
        """
        result = {
            "valid_phases": [],
            "invalid_phases": [],
            "incomplete_phases": [],
            "missing_phases": [],
        }

        if "tdd_cycle" not in step or "phase_execution_log" not in step["tdd_cycle"]:
            return result

        phases = step["tdd_cycle"]["phase_execution_log"]

        for i, phase in enumerate(phases):
            phase_name = phase.get("phase_name", "UNKNOWN")
            status = phase.get("status", "NOT_EXECUTED")

            if status == "EXECUTED":
                # Valid if in correct sequence (don't require outcome for this test)
                # Check if any previous phases are NOT_EXECUTED
                earlier_phases_incomplete = any(
                    phase_entry.get("status") != "EXECUTED"
                    for phase_entry in phases[:i]
                )
                if not earlier_phases_incomplete:
                    result["valid_phases"].append(phase_name)
                else:
                    result["invalid_phases"].append(
                        f"{phase_name}: EXECUTED but earlier phases not completed"
                    )
            elif status == "IN_PROGRESS":
                result["incomplete_phases"].append(phase_name)
            elif status == "NOT_EXECUTED":
                # Check if it's out of order
                if i < len(phases) - 1 and phases[i + 1].get("status") in [
                    "EXECUTED",
                    "IN_PROGRESS",
                ]:
                    # A NOT_EXECUTED phase appears before executed phases
                    result["missing_phases"].append(phase_name)

        return result
