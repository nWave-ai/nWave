from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of template validation."""

    status: str
    errors: list[str]
    task_invocation_allowed: bool
    duration_ms: float
    recovery_guidance: list[str] | None = None


class ValidatorPort(ABC):
    """Port for template validation."""

    @abstractmethod
    def validate_prompt(self, prompt: str) -> ValidationResult:
        """Validate prompt for mandatory sections and TDD phases.

        Args:
            prompt: Full prompt text to validate

        Returns:
            ValidationResult with status, errors, and task invocation flag
        """
        pass
