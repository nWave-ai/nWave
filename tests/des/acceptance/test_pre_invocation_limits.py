"""
E2E Acceptance Test: US-004 Pre-Invocation Turn/Timeout Limits Validation

PERSONA: Marcus (Senior Developer)
STORY: As a senior developer, I want orchestrator to validate turn/timeout configuration
       before invoking sub-agent, so that execution blocks early with clear error guidance
       if limits are missing or invalid.

BUSINESS VALUE:
- Prevents execution with unconfigured limits (fail fast)
- Clear error messages guide developers to configure limits properly
- Reduces time wasted on executions that will timeout/exceed limits
- Enforces TDD discipline by requiring explicit limit configuration

SCOPE: Covers step 07-02 acceptance criteria
WAVE: DISTILL (Acceptance Test Creation)
STATUS: RED (Outside-In TDD - awaiting DELIVER wave implementation)
"""


class TestPreInvocationLimitsValidation:
    """E2E acceptance tests for pre-invocation turn/timeout limits validation."""

    # =========================================================================
    # AC-07-02.1: Orchestrator validates max_turns and duration_minutes are set
    # Scenario 018: Missing limits block invocation with error
    # =========================================================================

    def test_scenario_018_missing_limits_block_invocation(
        self,
        tmp_project_root,
        minimal_step_file,
        des_orchestrator,
        in_memory_filesystem,
    ):
        """
        GIVEN step file without max_turns or duration_minutes configured
        WHEN orchestrator validates pre-invocation requirements
        THEN validation fails with clear error about missing limits
        AND error message guides user to configure limits in step file
        AND sub-agent invocation is blocked

        Business Context:
        Marcus runs /nw:execute but forgot to configure max_turns in step file.
        The orchestrator should catch this before invoking software-crafter,
        providing clear guidance on what to add and where.

        This enables:
        1. Fail-fast validation (before wasting agent turns)
        2. Clear error messages guide correct configuration
        3. Prevents unbounded execution without limits
        """
        # GIVEN: Step file without max_turns or duration_minutes

        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # Create initial step file without limits
        step_data = {
            "task_id": "07-02",
            "project_id": "test-project",
            "state": {
                "status": "IN_PROGRESS",
                "started_at": "2026-01-26T10:00:00Z",
                "completed_at": None,
            },
            "tdd_cycle": {
                # Intentionally missing max_turns and duration_minutes
                "total_extensions_minutes": 0,
                "phase_execution_log": [],
            },
        }

        # Write to in-memory filesystem
        in_memory_filesystem.write_json(minimal_step_file, step_data)

        # WHEN: Orchestrator validates before execute_step
        # Use des_orchestrator which is already configured with in_memory_filesystem
        validation_result = des_orchestrator.validate_invocation_limits(
            step_file=step_file_path, project_root=tmp_project_root
        )

        # THEN: Validation fails with specific error about missing limits
        assert validation_result.is_valid is False, (
            "Validation should fail when max_turns and duration_minutes are missing"
        )

        assert validation_result.errors is not None
        assert len(validation_result.errors) > 0

        # Verify error mentions missing configuration
        errors_text = " ".join(validation_result.errors).lower()
        assert any(
            keyword in errors_text
            for keyword in ["max_turns", "duration_minutes", "limits", "missing"]
        ), "Error should mention missing max_turns or duration_minutes"

        # THEN: Error message guides user to configure limits
        assert validation_result.guidance is not None
        guidance_text = " ".join(validation_result.guidance).lower()

        assert any(
            keyword in guidance_text
            for keyword in ["configure", "add", "set", "tdd_cycle"]
        ), "Guidance should mention how to configure limits in step file"

        assert "max_turns" in guidance_text or "duration_minutes" in guidance_text, (
            "Guidance should explicitly mention which fields to configure"
        )

    # =========================================================================
    # AC-07-02.2: Pre-invocation check fails if limits invalid
    # Scenario 019: Invalid limits block invocation with error
    # =========================================================================

    def test_scenario_019_invalid_limits_block_invocation(
        self,
        tmp_project_root,
        minimal_step_file,
        des_orchestrator,
        in_memory_filesystem,
    ):
        """
        GIVEN step file with invalid limits (negative or zero values)
        WHEN orchestrator validates pre-invocation requirements
        THEN validation fails with error about invalid limit values
        AND error message guides user to use positive integer values

        Business Context:
        Marcus configured max_turns=-1 by mistake in step file.
        The orchestrator should catch this invalid value before invocation.
        """
        # GIVEN: Step file with invalid limits
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # Create step data with invalid limits
        step_data = {
            "task_id": "07-02",
            "project_id": "test-project",
            "state": {
                "status": "IN_PROGRESS",
                "started_at": "2026-01-26T10:00:00Z",
                "completed_at": None,
            },
            "tdd_cycle": {
                "max_turns": -1,
                "duration_minutes": 0,
                "phase_execution_log": [],
            },
        }

        in_memory_filesystem.write_json(minimal_step_file, step_data)

        # WHEN: Orchestrator validates limits
        validation_result = des_orchestrator.validate_invocation_limits(
            step_file=step_file_path, project_root=tmp_project_root
        )

        # THEN: Validation fails with invalid value error
        assert validation_result.is_valid is False

        errors_text = " ".join(validation_result.errors).lower()
        assert any(
            keyword in errors_text
            for keyword in ["invalid", "negative", "zero", "positive"]
        ), "Error should mention invalid limit values"

        # THEN: Guidance suggests positive integer values
        guidance_text = " ".join(validation_result.guidance).lower()
        assert any(
            keyword in guidance_text
            for keyword in ["positive", "greater than", "integer"]
        ), "Guidance should suggest using positive integer values"

    # =========================================================================
    # AC-07-02.3: Valid limits allow invocation to proceed
    # Scenario 020: Valid limits pass validation
    # =========================================================================

    def test_scenario_020_valid_limits_pass_validation(
        self,
        tmp_project_root,
        minimal_step_file,
        des_orchestrator,
        in_memory_filesystem,
    ):
        """
        GIVEN step file with valid max_turns and duration_minutes
        WHEN orchestrator validates pre-invocation requirements
        THEN validation passes with no errors
        AND execution can proceed to sub-agent invocation

        Business Context:
        Marcus configured max_turns=50 and duration_minutes=30 in step file.
        The orchestrator should validate these limits and allow execution.
        """
        # GIVEN: Step file with valid limits
        step_file_path = str(minimal_step_file.relative_to(tmp_project_root))

        # Create step data with valid limits
        step_data = {
            "task_id": "07-02",
            "project_id": "test-project",
            "state": {
                "status": "IN_PROGRESS",
                "started_at": "2026-01-26T10:00:00Z",
                "completed_at": None,
            },
            "tdd_cycle": {
                "max_turns": 50,
                "duration_minutes": 30,
                "phase_execution_log": [],
            },
        }

        in_memory_filesystem.write_json(minimal_step_file, step_data)

        # WHEN: Orchestrator validates limits
        validation_result = des_orchestrator.validate_invocation_limits(
            step_file=step_file_path, project_root=tmp_project_root
        )

        # THEN: Validation passes
        assert validation_result.is_valid is True, (
            "Validation should pass when max_turns and duration_minutes are valid"
        )

        assert validation_result.errors is None or len(validation_result.errors) == 0
        assert (
            validation_result.guidance is None or len(validation_result.guidance) == 0
        )
