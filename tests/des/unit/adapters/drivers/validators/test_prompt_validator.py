"""
Unit Tests: PromptValidator

Validates that DES-validated prompts contain all mandatory sections including TIMEOUT_INSTRUCTION.

Test Coverage:
- TIMEOUT_INSTRUCTION present in MANDATORY_SECTIONS constant
- Validation returns invalid when TIMEOUT_INSTRUCTION missing
- Error message includes 'TIMEOUT_INSTRUCTION' and 'MISSING'
- Validation passes when all mandatory sections present
"""


class TestPromptValidatorTimeoutInstruction:
    """Unit tests for PromptValidator TIMEOUT_INSTRUCTION validation."""

    def test_validator_checks_timeout_instruction_in_mandatory_sections(self):
        """
        GIVEN PromptValidator is initialized
        WHEN checking MANDATORY_SECTIONS constant
        THEN 'TIMEOUT_INSTRUCTION' is present in the list

        Business Value: Ensures validator configuration includes TIMEOUT_INSTRUCTION requirement.
        """
        from des.application.prompt_validator import PromptValidator

        validator = PromptValidator()

        # Verify TIMEOUT_INSTRUCTION is in MANDATORY_SECTIONS
        assert hasattr(validator, "MANDATORY_SECTIONS"), (
            "Validator should have MANDATORY_SECTIONS attribute"
        )
        assert "TIMEOUT_INSTRUCTION" in validator.MANDATORY_SECTIONS, (
            "TIMEOUT_INSTRUCTION should be in MANDATORY_SECTIONS list"
        )

    def test_validator_returns_invalid_when_timeout_missing(self):
        """
        GIVEN prompt missing TIMEOUT_INSTRUCTION section
        WHEN PromptValidator.validate() is called
        THEN is_valid is False

        Business Value: Prevents agent invocation without turn discipline.
        """
        from des.application.prompt_validator import PromptValidator

        # Prompt with all sections EXCEPT TIMEOUT_INSTRUCTION
        incomplete_prompt = """
        <!-- DES-VALIDATION: required -->
        <!-- DES-STEP-FILE: steps/01-01.json -->

        ## DES_METADATA
        step_id: 01-01

        ## AGENT_IDENTITY
        You are software-crafter

        ## TASK_CONTEXT
        Implement feature X

        ## TDD_PHASES
        PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN_UNIT, CHECK_ACCEPTANCE,
        GREEN_ACCEPTANCE, REVIEW, REFACTOR_L1, REFACTOR_L2, REFACTOR_L3,
        REFACTOR_L4, POST_REFACTOR_REVIEW, FINAL_VALIDATE, COMMIT

        ## QUALITY_GATES
        G1-G6 definitions here

        ## OUTCOME_RECORDING
        Record outcomes in step file

        ## BOUNDARY_RULES
        ALLOWED: step file modifications
        FORBIDDEN: other file modifications

        <!-- NOTE: TIMEOUT_INSTRUCTION intentionally omitted -->
        """

        validator = PromptValidator()
        result = validator.validate(incomplete_prompt)

        assert not result.is_valid, (
            "Validation should FAIL when TIMEOUT_INSTRUCTION is missing"
        )

    def test_validator_error_message_includes_timeout_instruction(self):
        """
        GIVEN prompt missing TIMEOUT_INSTRUCTION section
        WHEN PromptValidator.validate() is called
        THEN error message includes 'TIMEOUT_INSTRUCTION'

        Business Value: Clear error messages help developers fix validation issues quickly.
        """
        from des.application.prompt_validator import PromptValidator

        incomplete_prompt = """
        <!-- DES-VALIDATION: required -->

        ## DES_METADATA
        step_id: test

        ## AGENT_IDENTITY
        You are test-agent

        ## TASK_CONTEXT
        Test task

        ## TDD_PHASES
        Phases here

        ## QUALITY_GATES
        Gates here

        ## OUTCOME_RECORDING
        Record here

        ## BOUNDARY_RULES
        Rules here
        """

        validator = PromptValidator()
        result = validator.validate(incomplete_prompt)

        assert any("TIMEOUT_INSTRUCTION" in error for error in result.errors), (
            f"Error message should identify TIMEOUT_INSTRUCTION as missing. Errors: {result.errors}"
        )

    def test_validator_error_message_includes_missing(self):
        """
        GIVEN prompt missing TIMEOUT_INSTRUCTION section
        WHEN PromptValidator.validate() is called
        THEN error message includes 'MISSING'

        Business Value: Distinguishes between missing sections and incomplete sections.
        """
        from des.application.prompt_validator import PromptValidator

        incomplete_prompt = """
        <!-- DES-VALIDATION: required -->

        ## DES_METADATA
        step_id: test
        """

        validator = PromptValidator()
        result = validator.validate(incomplete_prompt)

        assert any("MISSING" in error.upper() for error in result.errors), (
            f"Error should indicate section is MISSING. Errors: {result.errors}"
        )

    def test_validator_passes_when_timeout_instruction_present(self, valid_prompt_v3):
        """
        GIVEN prompt with TIMEOUT_INSTRUCTION section
        WHEN PromptValidator.validate() is called
        THEN is_valid is True

        Business Value: Valid prompts with turn discipline are allowed.
        """
        from des.application.prompt_validator import PromptValidator

        complete_prompt = valid_prompt_v3()

        validator = PromptValidator()
        result = validator.validate(complete_prompt)

        assert result.is_valid, (
            f"Validation should PASS with TIMEOUT_INSTRUCTION present. Errors: {result.errors}"
        )
        assert len(result.errors) == 0, (
            f"Should have no errors. Errors: {result.errors}"
        )
