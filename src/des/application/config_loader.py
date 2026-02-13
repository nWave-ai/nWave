"""
Configuration loader for DES system.

Loads and validates configuration including turn limits by task type.
"""

import json
from pathlib import Path


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


class ConfigLoader:
    """
    Loads configuration from JSON file with validation.

    Provides turn limits by task type (see src/des/config/des_defaults.yaml):
    - quick=15
    - background=25
    - standard=30 (default)
    - research=35
    - complex=50

    Defaults to standard (30) if type not specified.
    """

    # Defaults aligned with src/des/config/des_defaults.yaml
    DEFAULT_TURN_LIMITS = {
        "quick": 15,
        "background": 25,
        "standard": 30,
        "research": 35,
        "complex": 50,
    }

    def __init__(self, config_path: str):
        """
        Initialize ConfigLoader.

        Args:
            config_path: Path to JSON configuration file

        Raises:
            ConfigValidationError: If configuration is invalid
        """
        self.config_path = Path(config_path)
        self.turn_limits = self._load_turn_limits()

    def _load_turn_limits(self) -> dict[str, int]:
        """
        Load turn limits from config file with validation.

        Returns:
            Dictionary mapping task type to turn limit

        Raises:
            ConfigValidationError: If turn limits are invalid
        """
        if not self.config_path.exists():
            # Use built-in defaults if config file doesn't exist
            return self.DEFAULT_TURN_LIMITS.copy()

        try:
            with open(self.config_path) as f:
                config = json.load(f)
        except (OSError, json.JSONDecodeError):
            # Gracefully handle malformed or unreadable files
            return self.DEFAULT_TURN_LIMITS.copy()

        turn_limits = config.get("turn_limits", {})

        # Validate all turn limits are positive integers
        for task_type, limit in turn_limits.items():
            if not isinstance(limit, int) or limit <= 0:
                raise ConfigValidationError(
                    f"Turn limit for '{task_type}' must be positive integer, got {limit}"
                )

        return turn_limits

    def get_turn_limit(self, task_type: str | None) -> int:
        """
        Get turn limit for task type.

        Args:
            task_type: Task type (quick/standard/complex) or None

        Returns:
            Turn limit for task type, or standard default (30) if not found
        """
        if task_type is None or task_type not in self.turn_limits:
            # Default fallback to standard
            return self.turn_limits.get(
                "standard", self.DEFAULT_TURN_LIMITS["standard"]
            )

        return self.turn_limits[task_type]
