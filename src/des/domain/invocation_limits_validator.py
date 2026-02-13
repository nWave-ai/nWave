"""
Invocation Limits Validator

Validates that turn and timeout limits are configured in step files before
invoking sub-agents. This prevents execution with unconfigured limits and
provides clear error guidance.

BUSINESS VALUE:
- Fail fast: Catch missing configuration before wasting agent turns
- Clear guidance: Error messages tell developers exactly how to fix
- Enforce discipline: Require explicit limit configuration per TDD methodology
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InvocationLimitsResult:
    """Result of invocation limits validation.

    Attributes:
        is_valid: True if limits are properly configured
        errors: List of validation error messages
        guidance: List of actionable guidance for fixing errors
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    guidance: list[str] = field(default_factory=list)


class InvocationLimitsValidator:
    """Validates turn and timeout configuration before sub-agent invocation.

    Pre-invocation validation that ensures:
    1. max_turns is configured and positive
    2. duration_minutes is configured and positive

    Example usage:
        validator = InvocationLimitsValidator()
        result = validator.validate_limits(step_file_path)
        if not result.is_valid:
            print("Validation failed:", result.errors)
            print("Guidance:", result.guidance)
    """

    def __init__(self, filesystem=None):
        """Initialize validator with optional filesystem adapter.

        Args:
            filesystem: FileSystemPort adapter for file operations.
                       If None, uses RealFileSystem for production use.
        """
        if filesystem is None:
            from des.adapters.driven.filesystem.real_filesystem import (
                RealFileSystem,
            )

            filesystem = RealFileSystem()
        self._filesystem = filesystem

    def validate_limits(self, step_file_path: Path | str) -> InvocationLimitsResult:
        """Validate turn and timeout limits in step file.

        Args:
            step_file_path: Path to step JSON file

        Returns:
            InvocationLimitsResult with validation status, errors, and guidance
        """
        if isinstance(step_file_path, str):
            step_file_path = Path(step_file_path)

        # Load step file using filesystem adapter
        step_data = self._filesystem.read_json(step_file_path)

        errors = []
        guidance = []

        # Check tdd_cycle section exists
        tdd_cycle = step_data.get("tdd_cycle", {})

        # Validate max_turns
        max_turns = tdd_cycle.get("max_turns")
        if max_turns is None:
            errors.append("MISSING: max_turns not configured in step file")
            guidance.append(
                "Add 'max_turns' field to tdd_cycle section with a positive integer value. "
                'Example: "max_turns": 50'
            )
        elif not isinstance(max_turns, int) or max_turns <= 0:
            errors.append(
                f"INVALID: max_turns must be a positive integer (got: {max_turns})"
            )
            guidance.append(
                "Set 'max_turns' to a positive integer value. "
                "Typical values: 50 for simple tasks, 100 for complex refactoring"
            )

        # Validate duration_minutes
        duration_minutes = tdd_cycle.get("duration_minutes")
        if duration_minutes is None:
            errors.append("MISSING: duration_minutes not configured in step file")
            guidance.append(
                "Add 'duration_minutes' field to tdd_cycle section with a positive integer value. "
                'Example: "duration_minutes": 30'
            )
        elif not isinstance(duration_minutes, int) or duration_minutes <= 0:
            errors.append(
                f"INVALID: duration_minutes must be a positive integer (got: {duration_minutes})"
            )
            guidance.append(
                "Set 'duration_minutes' to a positive integer value. "
                "Typical values: 30 for simple tasks, 60-120 for complex refactoring"
            )

        # Add general guidance if any errors found
        if errors:
            guidance.insert(
                0,
                "Configure turn and timeout limits in step file under tdd_cycle section. "
                "These limits enforce TDD discipline and prevent unbounded execution.",
            )

        is_valid = len(errors) == 0

        return InvocationLimitsResult(
            is_valid=is_valid, errors=errors, guidance=guidance
        )
