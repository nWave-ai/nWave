"""
DES Configuration Adapter - Driven Port Implementation.

Loads configuration from .nwave/des-config.json and provides access to settings.
Falls back to safe defaults (audit logging ON) when file is missing or invalid.

Hexagonal Architecture:
- DRIVEN ADAPTER: Implements configuration port (driven by business logic)
- ON BY DEFAULT: Audit logging enabled unless explicitly disabled in config
"""

import json
import os
from pathlib import Path
from typing import Any


class DESConfig:
    """
    Configuration loader for DES settings.

    Loads configuration from .nwave/des-config.json with on-by-default audit logging.
    Does NOT auto-create config files.
    """

    def __init__(
        self,
        config_path: Path | None = None,
        cwd: Path | None = None,
    ):
        """
        Initialize DESConfig.

        Args:
            config_path: Optional explicit path to config file
            cwd: Optional working directory (defaults to Path.cwd());
                 used to resolve .nwave/des-config.json when config_path is None
        """
        if config_path is None:
            effective_cwd = cwd or Path.cwd()
            config_path = effective_cwd / ".nwave" / "des-config.json"

        self._config_path = config_path
        self._config_data = self._load_configuration()

    def _load_configuration(self) -> dict[str, Any]:
        """
        Load configuration from JSON file.

        Returns:
            Configuration dictionary, empty dict if loading fails
        """
        if not self._config_path.exists():
            return {}

        try:
            return json.loads(self._config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    @property
    def audit_logging_enabled(self) -> bool:
        """
        Check if audit logging is enabled.

        Priority: DES_AUDIT_LOGGING_ENABLED env var > config file > default (True).

        Returns:
            True if audit logging enabled, False otherwise (defaults to True)
        """
        env_override = os.environ.get("DES_AUDIT_LOGGING_ENABLED")
        if env_override is not None:
            return env_override.lower() in ("true", "1", "yes")
        return self._config_data.get("audit_logging_enabled", True)
