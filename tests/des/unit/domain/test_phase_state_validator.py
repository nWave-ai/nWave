"""
Unit Tests: PhaseStateValidator - Step 02-05

Tests for detecting invalid phase state transitions in step files:
- Invalid EXECUTED state: Phase marked EXECUTED without outcome field
- Invalid SKIPPED state: Phase marked SKIPPED without blocked_by reason
- Recovery suggestions generation for invalid states
- Expected field format guidance in suggestions

These tests drive the implementation of PhaseStateValidator domain service.
AC-005.1: Detect invalid phase state combinations
AC-005.2: Generate specific recovery suggestions
"""


class TestPhaseStateValidator:
    """Unit tests for PhaseStateValidator domain service."""

    def test_detect_executed_phase_without_outcome(self):
        """
        GIVEN a phase marked EXECUTED but missing outcome field
        WHEN phase state validator analyzes the phase
        THEN it should detect the invalid state

        Acceptance Criteria (AC-005.1):
        - Detects EXECUTED phases without outcome field
        - Error message specifies the phase name and missing field
        - Error includes recovery guidance

        Example Invalid Phase:
        {
            "phase_name": "GREEN",
            "status": "EXECUTED",
            "outcome": null  # INVALID: EXECUTED requires outcome
        }
        """
        from des.domain.phase_state_validator import PhaseStateValidator

        validator = PhaseStateValidator()

        # Invalid phase: EXECUTED without outcome
        invalid_phase = {
            "phase_name": "GREEN",
            "status": "EXECUTED",
            "outcome": None,  # INVALID
        }

        errors = validator.validate_phase_state(invalid_phase)

        assert errors is not None, "Should detect invalid state"
        assert isinstance(errors, list), "Errors should be a list"
        assert len(errors) > 0, "Should have at least one error"
        assert any("outcome" in err.lower() and "EXECUTED" in err for err in errors), (
            "Should mention EXECUTED and missing outcome"
        )

    def test_detect_skipped_phase_without_blocked_by(self):
        """
        GIVEN a phase marked SKIPPED but missing blocked_by field
        WHEN phase state validator analyzes the phase
        THEN it should detect the invalid state

        Acceptance Criteria (AC-005.1):
        - Detects SKIPPED phases without blocked_by reason
        - Error message specifies the phase name and missing blocked_by
        - Error includes recovery guidance

        Example Invalid Phase:
        {
            "phase_name": "REFACTOR_L4",
            "status": "SKIPPED",
            "blocked_by": null  # INVALID: SKIPPED requires blocked_by
        }
        """
        from des.domain.phase_state_validator import PhaseStateValidator

        validator = PhaseStateValidator()

        # Invalid phase: SKIPPED without blocked_by
        invalid_phase = {
            "phase_name": "REFACTOR_L4",
            "status": "SKIPPED",
            "blocked_by": None,  # INVALID
        }

        errors = validator.validate_phase_state(invalid_phase)

        assert errors is not None, "Should detect invalid state"
        assert isinstance(errors, list), "Errors should be a list"
        assert len(errors) > 0, "Should have at least one error"
        assert any(
            "blocked_by" in err.lower() and "SKIPPED" in err for err in errors
        ), "Should mention SKIPPED and missing blocked_by"

    def test_generate_recovery_suggestions_for_invalid_executed_state(self):
        """
        GIVEN a phase marked EXECUTED without outcome
        WHEN recovery suggestions are generated
        THEN suggestions explain WHY the field is needed and HOW to fix

        Acceptance Criteria (AC-005.2 + AC-005.5):
        - Generates 2+ recovery suggestions for invalid EXECUTED state
        - Suggestions explain WHY outcome field is required
        - Suggestions explain HOW to add outcome field
        - Suggestions include expected field format

        Expected Suggestions:
        1. WHY: Outcome provides evidence that phase completed and what was accomplished
        2. HOW: Add a descriptive outcome (e.g., "Implementation complete, all tests passing")
        3. ACTIONABLE: Update phase.outcome with brief description of what was done
        """
        from des.domain.phase_state_validator import PhaseStateValidator

        validator = PhaseStateValidator()

        invalid_phase = {
            "phase_name": "GREEN",
            "status": "EXECUTED",
            "outcome": None,
        }

        suggestions = validator.generate_recovery_suggestions(invalid_phase)

        assert suggestions is not None, "Should generate recovery suggestions"
        assert isinstance(suggestions, list), "Suggestions should be a list"
        assert len(suggestions) >= 2, "Should have 2+ suggestions for invalid state"

        # Check for WHY explanation
        assert any(
            keyword in " ".join(suggestions).lower()
            for keyword in [
                "outcome",
                "evidence",
                "describes",
                "accomplished",
                "required",
            ]
        ), "Suggestions should explain why outcome is required"

        # Check for HOW explanation
        assert any(
            keyword in " ".join(suggestions).lower()
            for keyword in ["add", "descriptive", "provide", "include", "update"]
        ), "Suggestions should explain how to add outcome"

    def test_generate_recovery_suggestions_for_invalid_skip_state(self):
        """
        GIVEN a phase marked SKIPPED without blocked_by reason
        WHEN recovery suggestions are generated
        THEN suggestions explain WHY blocked_by is needed and HOW to fix

        Acceptance Criteria (AC-005.2 + AC-005.5):
        - Generates 2+ recovery suggestions for invalid SKIPPED state
        - Suggestions explain WHY blocked_by field is required
        - Suggestions explain HOW to add blocked_by reason
        - Suggestions include expected field format

        Expected Suggestions:
        1. WHY: blocked_by provides context for why phase was skipped (dependency, N/A, etc.)
        2. HOW: Add a reason code (e.g., "CHECKPOINT_PENDING", "NOT_APPLICABLE")
        3. ACTIONABLE: Update phase.blocked_by with skip reason from approved list
        """
        from des.domain.phase_state_validator import PhaseStateValidator

        validator = PhaseStateValidator()

        invalid_phase = {
            "phase_name": "REFACTOR_L4",
            "status": "SKIPPED",
            "blocked_by": None,
        }

        suggestions = validator.generate_recovery_suggestions(invalid_phase)

        assert suggestions is not None, "Should generate recovery suggestions"
        assert isinstance(suggestions, list), "Suggestions should be a list"
        assert len(suggestions) >= 2, "Should have 2+ suggestions for invalid state"

        # Check for WHY explanation
        assert any(
            keyword in " ".join(suggestions).lower()
            for keyword in [
                "blocked_by",
                "reason",
                "context",
                "why",
                "explains",
                "indicates",
            ]
        ), "Suggestions should explain why blocked_by is required"

        # Check for HOW explanation
        assert any(
            keyword in " ".join(suggestions).lower()
            for keyword in ["add", "reason", "code", "provide", "update", "set"]
        ), "Suggestions should explain how to add blocked_by"

    def test_invalid_state_suggestions_include_expected_field_format(self):
        """
        GIVEN invalid phase state(s)
        WHEN recovery suggestions are generated
        THEN suggestions include expected field format and valid values

        Acceptance Criteria (AC-005.3):
        - Suggestions include format examples (e.g., outcome text length)
        - Suggestions reference valid values (e.g., CHECKPOINT_PENDING, NOT_APPLICABLE)
        - Suggestions provide copy-paste examples developers can use

        Expected Format Guidance:
        - outcome: 1-10 word descriptive text (e.g., "Implementation complete")
        - blocked_by: One of: CHECKPOINT_PENDING, NOT_APPLICABLE, {reason}
        - Example: "Set blocked_by to 'NOT_APPLICABLE: Utility detector needs no patterns'"
        """
        from des.domain.phase_state_validator import PhaseStateValidator

        validator = PhaseStateValidator()

        # Test both invalid states
        test_cases = [
            {
                "phase": {
                    "phase_name": "GREEN",
                    "status": "EXECUTED",
                    "outcome": None,
                },
                "field": "outcome",
            },
            {
                "phase": {
                    "phase_name": "REFACTOR_L4",
                    "status": "SKIPPED",
                    "blocked_by": None,
                },
                "field": "blocked_by",
            },
        ]

        for test_case in test_cases:
            suggestions = validator.generate_recovery_suggestions(test_case["phase"])

            # Check suggestions include format guidance
            suggestions_text = " ".join(suggestions).lower()

            # Should mention examples or expected format
            assert any(
                keyword in suggestions_text
                for keyword in [
                    "example",
                    "format",
                    "like",
                    "such as",
                    "e.g",
                    "valid",
                    "code",
                ]
            ), f"Suggestions for {test_case['field']} should include format examples"

            # For blocked_by, should mention valid reason codes
            if test_case["field"] == "blocked_by":
                suggestions_text = " ".join(suggestions)
                assert any(
                    keyword in suggestions_text
                    for keyword in [
                        "CHECKPOINT_PENDING",
                        "NOT_APPLICABLE",
                        "reason code",
                    ]
                ), "blocked_by suggestions should mention valid reason codes"

            # For outcome, should mention descriptive text guidance
            if test_case["field"] == "outcome":
                suggestions_text = " ".join(suggestions)
                assert any(
                    keyword in suggestions_text.lower()
                    for keyword in [
                        "descriptive",
                        "brief",
                        "describe",
                        "what",
                        "accomplished",
                    ]
                ), "outcome suggestions should mention descriptive text requirement"
