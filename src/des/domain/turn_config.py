"""Turn limit configuration by task type.

Business Value: Enables fine-grained control over execution duration per task complexity.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TurnLimitConfig:
    """Configuration for task type-specific turn limits.

    Provides turn limits tailored to task complexity:
    - quick: Short-running tasks (e.g., schema validation)
    - standard: Normal development tasks (e.g., feature implementation)
    - complex: Long-running tasks (e.g., architectural refactoring)
    """

    quick: int
    standard: int
    complex: int

    def get_limit_for_type(self, task_type: str) -> int:
        """Retrieve turn limit for specified task type.

        Args:
            task_type: Task complexity classification (quick, standard, complex)

        Returns:
            Turn limit for task type. Defaults to standard if type unknown.
        """
        limit_map = {
            "quick": self.quick,
            "standard": self.standard,
            "complex": self.complex,
        }
        return limit_map.get(task_type, self.standard)


class ConfigLoader:
    """Loads and validates turn limit configuration.

    Ensures configuration integrity through validation:
    - All required task types present
    - Turn limits positive and reasonable
    - Provides safe defaults when config unavailable
    """

    REQUIRED_TASK_TYPES = {"quick", "standard", "complex"}

    def load_from_dict(self, config_data: dict[str, Any]) -> TurnLimitConfig:
        """Parse turn limits from configuration dictionary.

        Args:
            config_data: Configuration dict with turn_limits section

        Returns:
            Validated TurnLimitConfig instance

        Raises:
            ValueError: If configuration invalid or incomplete
        """
        if "turn_limits" not in config_data:
            raise ValueError("turn_limits section required in configuration")

        turn_limits = config_data["turn_limits"]

        # Validate all required task types present
        missing_types = self.REQUIRED_TASK_TYPES - set(turn_limits.keys())
        if missing_types:
            raise ValueError(f"Missing required task type: {', '.join(missing_types)}")

        # Extract and validate limits
        quick = turn_limits["quick"]
        standard = turn_limits["standard"]
        complex_limit = turn_limits["complex"]

        if quick <= 0 or standard <= 0 or complex_limit <= 0:
            raise ValueError("Turn limits must be positive integers")

        return TurnLimitConfig(quick=quick, standard=standard, complex=complex_limit)

    def get_default_config(self) -> TurnLimitConfig:
        """Provide default turn limit configuration.

        Returns:
            TurnLimitConfig with sensible defaults for each task type
        """
        return TurnLimitConfig(quick=20, standard=50, complex=100)
