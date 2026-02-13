"""
E2E Acceptance Test: US-002 Pre-Invocation Template Validation

PERSONA: Priya (Tech Lead)
STORY: As a tech lead, I want DES to block Task invocation if mandatory sections
       are missing from the prompt, so that sub-agents always receive complete
       instructions and cannot claim ignorance.

BUSINESS VALUE:
- Prevents blame-shifting ("the agent didn't know about X")
- Ensures methodology compliance before execution starts
- Provides specific, actionable error messages
- Validates completeness in < 500ms (non-blocking)

SCOPE: Covers US-002 Acceptance Criteria (AC-002.1 through AC-002.5)
WAVE: DISTILL (Acceptance Test Creation)
STATUS: RED (Outside-In TDD - awaiting DEVELOP wave implementation)
"""


class TestPreInvocationTemplateValidation:
    """E2E acceptance tests for US-002: Pre-invocation template validation."""

    # =========================================================================
    # AC-002.1: All 8 mandatory sections must be present for validation to pass
    # Scenario 4: Complete prompt passes validation
    # =========================================================================

    def test_complete_prompt_passes_all_validation_checks(self, valid_prompt_v3):
        """
        GIVEN orchestrator generates prompt for step with all 9 mandatory sections
        WHEN pre-invocation validation runs
        THEN validation status is PASSED and Task invocation proceeds

        Business Value: Priya verifies that correctly formed prompts are not
                       blocked, ensuring smooth workflow for compliant templates.

        Mandatory Sections Verified:
        1. DES_METADATA
        2. AGENT_IDENTITY
        3. TASK_CONTEXT
        4. TDD_PHASES (5 phases from schema v4.0)
        5. QUALITY_GATES
        6. OUTCOME_RECORDING
        7. RECORDING_INTEGRITY
        8. BOUNDARY_RULES
        9. TIMEOUT_INSTRUCTION
        """
        import time

        from des.application.validator import TemplateValidator

        # Arrange: Create prompt with all 9 mandatory sections from template
        prompt_with_all_sections = valid_prompt_v3()

        # Act: Run pre-invocation validation
        start_time = time.perf_counter()
        validator = TemplateValidator()
        validation_result = validator.validate_prompt(prompt_with_all_sections)
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Assert: Validation passes, Task invocation proceeds
        assert validation_result.status == "PASSED"
        assert validation_result.errors == []
        assert validation_result.task_invocation_allowed is True
        assert duration_ms < 500  # AC-002.5

    # =========================================================================
    # AC-002.2: All 7 TDD phases (v3.0) must be explicitly mentioned
    # Scenario 5: Missing TDD phase blocks Task invocation
    # =========================================================================

    def test_missing_tdd_phase_blocks_task_invocation(self, prompt_missing_phase_v3):
        """
        GIVEN orchestrator generates prompt missing GREEN phase
        WHEN pre-invocation validation runs
        THEN validation FAILS with specific error naming missing phase

        Business Value: Priya ensures all 5 TDD phases (v4.0) are communicated to
                       sub-agents, preventing "I didn't know about X"
                       excuses during PR review.

        Missing Phase: GREEN (one of 5 mandatory phases from schema v4.0)
        """
        # Arrange: Create prompt missing GREEN phase from template
        prompt_missing_phase = prompt_missing_phase_v3(missing_phase="GREEN")

        # Act: Run pre-invocation validation
        from des.application.validator import TemplateValidator

        validator = TemplateValidator()
        validation_result = validator.validate_prompt(prompt_missing_phase)

        # Assert: Validation fails with specific error
        assert validation_result.status == "FAILED"
        assert "INCOMPLETE: TDD phase 'GREEN' not mentioned" in validation_result.errors
        assert validation_result.task_invocation_allowed is False

    # =========================================================================
    # AC-002.3: Validation errors are specific and actionable
    # Scenario 6: Missing mandatory section blocks Task invocation
    # =========================================================================

    def test_missing_mandatory_section_provides_actionable_error(self):
        """
        GIVEN orchestrator generates prompt without TIMEOUT_INSTRUCTION section
        WHEN pre-invocation validation runs
        THEN validation FAILS with error naming missing section AND recovery guidance

        Business Value: Priya receives specific, actionable errors that enable
                       quick template fixes without guesswork.

        Missing Section: TIMEOUT_INSTRUCTION (1 of 9 mandatory)
        Expected Error: "MISSING: Mandatory section 'TIMEOUT_INSTRUCTION' not found"
        Expected Guidance: "Add TIMEOUT_INSTRUCTION section with turn budget guidance"
        """
        # Arrange: Create prompt missing TIMEOUT_INSTRUCTION
        prompt_missing_section = """
        <!-- DES-VALIDATION: required -->

        # DES_METADATA
        Step: 01-03.json

        # AGENT_IDENTITY
        Agent: software-crafter

        # TASK_CONTEXT
        Implement PaymentService

        # TDD_PHASES
        All 14 phases listed (PREPARE through COMMIT)

        # QUALITY_GATES
        G1-G6 defined

        # OUTCOME_RECORDING
        Update step file

        # RECORDING_INTEGRITY
        Valid skip prefixes and anti-fraud rules defined

        # BOUNDARY_RULES
        Scope defined

        # MISSING: TIMEOUT_INSTRUCTION
        """

        # Act: Run pre-invocation validation
        from des.application.validator import TemplateValidator

        validator = TemplateValidator()
        validation_result = validator.validate_prompt(prompt_missing_section)

        # Assert: Validation fails with specific, actionable error
        assert validation_result.status == "FAILED"
        assert (
            "MISSING: Mandatory section 'TIMEOUT_INSTRUCTION' not found"
            in validation_result.errors
        )
        assert validation_result.task_invocation_allowed is False
        assert any(
            "Add TIMEOUT_INSTRUCTION section with turn budget guidance" in guidance
            for guidance in validation_result.recovery_guidance
        )

    # =========================================================================
    # AC-002.4: Task tool is NOT invoked if validation fails
    # Scenario 7: Multiple validation errors reported together
    # =========================================================================

    def test_multiple_validation_errors_reported_together(self, tdd_phases):
        """
        GIVEN orchestrator generates prompt with 2 issues (missing section + missing phase)
        WHEN pre-invocation validation runs
        THEN validation FAILS with all errors listed AND Task NOT invoked

        Business Value: Priya sees ALL validation failures in one pass, enabling
                       complete fix without multiple trial-and-error cycles.

        Issues (v4.0):
        1. Missing BOUNDARY_RULES section
        2. Missing GREEN phase

        Expected: All errors returned together, Task invocation blocked
        """
        # Arrange: Create prompt with multiple issues (missing section + missing phase)
        # Build phase list excluding GREEN
        phases_missing_green = [p for p in tdd_phases if p != "GREEN"]
        phases_text = ", ".join(phases_missing_green)

        _prompt_with_multiple_errors = f"""<!-- DES-VALIDATION: required -->

## DES_METADATA
step_id: test-01-04
project_id: test-project
step_file: steps/test-01-04.json

## AGENT_IDENTITY
You are @software-crafter executing this step.

## TASK_CONTEXT
Implement InventoryService with validation.

## TDD_PHASES
Execute all {len(tdd_phases)} phases from schema:
{phases_text}

## QUALITY_GATES
G1: All tests pass
G2: No code smells
G3: Coverage >= 80%

## OUTCOME_RECORDING
Record phase outcomes in step file

## RECORDING_INTEGRITY
Valid skip prefixes and anti-fraud rules defined

## TIMEOUT_INSTRUCTION
Turn budget: approximately 50 turns"""

        # Act: Run pre-invocation validation
        from des.application.validator import TemplateValidator

        validator = TemplateValidator()
        validation_result = validator.validate_prompt(_prompt_with_multiple_errors)

        # Assert: All errors reported together, Task NOT invoked
        assert validation_result.status == "FAILED"
        assert len(validation_result.errors) == 2
        assert (
            "MISSING: Mandatory section 'BOUNDARY_RULES' not found"
            in validation_result.errors
        )
        assert "INCOMPLETE: TDD phase 'GREEN' not mentioned" in validation_result.errors
        assert validation_result.task_invocation_allowed is False

    # =========================================================================
    # AC-002.5: Validation completes in < 500ms
    # Scenario 4 (Performance Aspect): Fast validation for smooth workflow
    # =========================================================================

    def test_validation_completes_within_performance_budget(self, valid_prompt_v3):
        """
        GIVEN complete prompt with all 9 sections and 7 phases (v3.0)
        WHEN pre-invocation validation runs
        THEN validation completes in less than 500 milliseconds

        Business Value: Priya ensures validation does not create noticeable
                       workflow delays, maintaining developer productivity.

        Performance Requirement: < 500ms validation time (AC-002.5)
        """
        # Arrange: Create complete, valid prompt from template
        _complete_prompt = valid_prompt_v3()

        # Act: Measure validation performance
        import time

        from des.application.validator import TemplateValidator

        validator = TemplateValidator()
        start_time = time.perf_counter()
        validation_result = validator.validate_prompt(_complete_prompt)
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Assert: Validation passes AND completes quickly
        assert validation_result.status == "PASSED"
        assert duration_ms < 500, (
            f"Validation took {duration_ms}ms, exceeds 500ms budget"
        )
        assert validation_result.task_invocation_allowed is True

    # =========================================================================
    # Additional Edge Case: Malformed DES marker validation
    # Ensures robust validation even with corrupted metadata
    # =========================================================================

    def test_malformed_des_marker_detected_and_rejected(self):
        """
        GIVEN prompt contains malformed DES marker (invalid format)
        WHEN pre-invocation validation runs
        THEN validation FAILS with INVALID_MARKER error

        Business Value: Priya ensures even corrupted prompts are caught before
                       execution, preventing mysterious agent failures.

        Malformed Marker: <!-- DES-VALIDATION: unknown --> (invalid value)
        Expected: Validation rejection with clear error
        """
        # Arrange: Create prompt with malformed DES marker
        prompt_malformed_marker = """
        <!-- DES-VALIDATION: unknown -->
        <!-- DES-STEP-FILE: steps/01-06.json -->

        # DES_METADATA
        Step: 01-06.json

        # AGENT_IDENTITY
        Agent: software-crafter

        # TASK_CONTEXT
        Test malformed marker handling

        # TDD_PHASES
        PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN_UNIT, CHECK_ACCEPTANCE, GREEN_ACCEPTANCE,
        REVIEW, REFACTOR_L1, REFACTOR_L2, REFACTOR_L3, REFACTOR_L4, POST_REFACTOR_REVIEW, FINAL_VALIDATE, COMMIT

        # QUALITY_GATES
        G1-G6

        # OUTCOME_RECORDING
        Update step file

        # RECORDING_INTEGRITY
        Valid skip prefixes and anti-fraud rules

        # BOUNDARY_RULES
        Minimal scope

        # TIMEOUT_INSTRUCTION
        50 turns
        """

        # Act: Run pre-invocation validation
        from des.application.validator import TemplateValidator

        validator = TemplateValidator()
        validation_result = validator.validate_prompt(prompt_malformed_marker)

        # Assert: Validation fails with invalid marker error
        assert validation_result.status == "FAILED"
        assert any("INVALID_MARKER" in error for error in validation_result.errors)
        assert validation_result.task_invocation_allowed is False


# =============================================================================
# WIRING TESTS: Validation through DESOrchestrator Entry Point (CM-A/CM-D)
# =============================================================================
# These tests invoke validation through the system entry point (DESOrchestrator)
# instead of directly instantiating TemplateValidator. This ensures the
# integration is wired correctly and prevents "Testing Theatre" where tests
# pass but the feature is not actually connected to the system.
# =============================================================================


class TestOrchestratorIntegration:
    """
    Integration tests that verify TemplateValidator is wired into DESOrchestrator.

    These tests exercise the ENTRY POINT (DESOrchestrator) rather than the
    internal component (TemplateValidator) directly. This is the 10% E2E test
    that proves the wiring works (per CM-D 90/10 rule).
    """

    def test_orchestrator_validates_prompt_via_entry_point(
        self, in_memory_filesystem, mocked_hook, mocked_time_provider, valid_prompt_v3
    ):
        """
        GIVEN a complete prompt with all mandatory sections
        WHEN validation is invoked through DESOrchestrator entry point
        THEN validation passes and task_invocation_allowed is True

        WIRING TEST: Proves TemplateValidator is integrated into orchestrator.
        This test would FAIL if the import or delegation is missing.
        """
        # Arrange: Create orchestrator with REAL validator for integration testing
        from des.application.orchestrator import DESOrchestrator
        from des.application.validator import TemplateValidator

        orchestrator = DESOrchestrator(
            hook=mocked_hook,
            validator=TemplateValidator(),  # Real validator for integration test
            filesystem=in_memory_filesystem,
            time_provider=mocked_time_provider,
        )

        complete_prompt = valid_prompt_v3()

        # Act: Invoke validation through ENTRY POINT
        result = orchestrator.validate_prompt(complete_prompt)

        # Assert: Validation passes through wired validator
        assert result.status == "PASSED"
        assert result.task_invocation_allowed is True
        assert result.errors == []

    def test_orchestrator_blocks_invalid_prompt_via_entry_point(
        self, in_memory_filesystem, mocked_hook, mocked_time_provider
    ):
        """
        GIVEN a prompt missing mandatory sections
        WHEN validation is invoked through DESOrchestrator entry point
        THEN validation fails and task_invocation_allowed is False

        WIRING TEST: Proves validation logic is actually being executed
        through the orchestrator, not just returning success by default.
        """
        # Arrange: Create orchestrator with REAL validator for integration testing
        from des.application.orchestrator import DESOrchestrator
        from des.application.validator import TemplateValidator

        orchestrator = DESOrchestrator(
            hook=mocked_hook,
            validator=TemplateValidator(),  # Real validator for integration test
            filesystem=in_memory_filesystem,
            time_provider=mocked_time_provider,
        )

        # Prompt missing most mandatory sections
        incomplete_prompt = """
        <!-- DES-VALIDATION: required -->
        Some incomplete prompt without mandatory sections.
        """

        # Act: Invoke validation through ENTRY POINT
        result = orchestrator.validate_prompt(incomplete_prompt)

        # Assert: Validation fails (proves validator is actually called)
        assert result.status == "FAILED"
        assert result.task_invocation_allowed is False
        assert len(result.errors) > 0
        assert any("MISSING" in error for error in result.errors)


# =============================================================================
# NOTE: Execution log validation tests have been moved to US-003
# =============================================================================
# Phase execution log validation belongs in SubagentStopHook (post-execution),
# not in TemplateValidator (pre-invocation). See:
# - tests/acceptance/test_post_execution_validation.py (acceptance tests)
# - tests/des/unit/application/test_hooks.py (unit tests)
#
# TemplateValidator validates PROMPTS (templates with mandatory sections).
# SubagentStopHook validates EXECUTION LOGS (step files after agent completion).
# =============================================================================


class TestOrchestratorSubagentStopHook:
    """
    Integration test verifying that orchestrator invokes subagent stop hook
    on validation completion, preventing resource leaks.
    """

    def test_orchestrator_invokes_subagent_stop_hook_on_completion(
        self, in_memory_filesystem, mocked_hook, mocked_validator, mocked_time_provider
    ):
        """
        GIVEN a validation flow completes successfully
        WHEN DESOrchestrator.validate_prompt() returns
        THEN orchestrator must invoke subagent.stop() hook for cleanup

        Business Value: Ensures proper resource cleanup preventing memory leaks
        and zombie processes from incomplete subagent lifecycle management.
        """
        from des.application.orchestrator import DESOrchestrator

        orchestrator = DESOrchestrator(
            hook=mocked_hook,
            validator=mocked_validator,
            filesystem=in_memory_filesystem,
            time_provider=mocked_time_provider,
        )

        complete_prompt = """
        <!-- DES-VALIDATION: required -->

        # DES_METADATA
        Step: 01-08.json

        # AGENT_IDENTITY
        Agent: software-crafter

        # TASK_CONTEXT
        Integration test for subagent lifecycle

        # TDD_PHASES
        All 14 phases listed

        # QUALITY_GATES
        G1-G6

        # OUTCOME_RECORDING
        Update step file

        # BOUNDARY_RULES
        Scope

        # TIMEOUT_INSTRUCTION
        50 turns
        """

        # Act: Validate prompt through orchestrator
        result = orchestrator.validate_prompt(complete_prompt)

        # Assert: Validation completes and lifecycle hook called
        assert result.status == "PASSED"
        assert result.task_invocation_allowed is True
        # Verify stop hook was invoked (check orchestrator internal state or mock)
        assert hasattr(orchestrator, "_subagent_lifecycle_completed")
        assert orchestrator._subagent_lifecycle_completed is True
