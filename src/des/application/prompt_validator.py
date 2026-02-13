"""
PromptValidator - Facade for Template Validation

This module provides a simplified interface for prompt validation,
exposing the PromptValidator class that validates DES prompts contain
all mandatory sections including TIMEOUT_INSTRUCTION.

This is a facade over the full TemplateValidator implementation in
src.des.application.validator, providing a cleaner API for tests
and external consumers.
"""

from dataclasses import dataclass

from des.application.validator import (
    MandatorySectionChecker,
    TemplateValidator,
)


@dataclass
class ValidationResult:
    """Simplified validation result for PromptValidator."""

    is_valid: bool
    errors: list[str]


class PromptValidator:
    """
    Validates DES prompts contain all mandatory sections.

    This is a facade over TemplateValidator providing a simpler API
    focused on prompt section validation.

    MANDATORY_SECTIONS:
    1. DES_METADATA
    2. AGENT_IDENTITY
    3. TASK_CONTEXT
    4. TDD_PHASES
    5. QUALITY_GATES
    6. OUTCOME_RECORDING
    7. RECORDING_INTEGRITY
    8. BOUNDARY_RULES
    9. TIMEOUT_INSTRUCTION
    """

    def __init__(self):
        """Initialize validator with section checker."""
        self._template_validator = TemplateValidator()
        self._section_checker = MandatorySectionChecker()

    @property
    def MANDATORY_SECTIONS(self) -> list[str]:
        """
        Get list of mandatory sections that must be present in prompts.

        Returns:
            List of section names including TIMEOUT_INSTRUCTION
        """
        return self._section_checker.MANDATORY_SECTIONS

    def validate(self, prompt: str) -> ValidationResult:
        """
        Validate prompt contains all mandatory sections.

        Args:
            prompt: The full prompt text to validate

        Returns:
            ValidationResult with is_valid and errors list
        """
        # Use full template validator
        result = self._template_validator.validate_prompt(prompt)

        # Convert to simplified result
        return ValidationResult(
            is_valid=result.task_invocation_allowed, errors=result.errors
        )
