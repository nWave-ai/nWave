"""Test implementation of template validator adapter."""

from des.ports.driver_ports.validator_port import ValidationResult, ValidatorPort


class MockedTemplateValidator(ValidatorPort):
    """Test implementation of template validator.

    Returns predefined results without actual validation for fast, deterministic testing.
    Tracks call history for verification in tests.
    """

    def __init__(self, predefined_result: ValidationResult = None):
        """Initialize with optional predefined result.

        Args:
            predefined_result: ValidationResult to return from validate_prompt.
                             Defaults to valid/passing result if not provided.
        """
        self._result = predefined_result or ValidationResult(
            status="PASSED",
            errors=[],
            task_invocation_allowed=True,
            duration_ms=0.0,
            recovery_guidance=None,
        )
        self.call_count = 0
        self.last_prompt = None

    def validate_prompt(self, prompt: str) -> ValidationResult:
        """Return predefined result without actual validation.

        Args:
            prompt: Prompt text (recorded but not validated)

        Returns:
            Predefined ValidationResult configured at initialization
        """
        self.call_count += 1
        self.last_prompt = prompt
        return self._result
