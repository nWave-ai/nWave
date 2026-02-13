"""
TDD Schema Loader - Single Source of Truth for TDD Rules.

Loads TDD phase definitions, validation rules, and skip prefixes from
nWave/templates/step-tdd-cycle-schema.json. Provides cached access to avoid
repeated file I/O.

Design Principles:
- Single Responsibility: Only loads and parses TDD schema
- Dependency Injection: Schema path can be overridden for testing
- Immutability: Schema data is frozen after load
- Caching: Schema loaded once per process lifetime
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class TDDSchemaProtocol(Protocol):
    """Protocol defining the TDD schema interface.

    Used for type hints and to enable testing with mock implementations.
    """

    @property
    def tdd_phases(self) -> tuple[str, ...]:
        """Ordered tuple of TDD phase names (e.g., PREPARE, RED_ACCEPTANCE, ...)."""
        ...

    @property
    def valid_statuses(self) -> tuple[str, ...]:
        """Valid phase execution statuses (e.g., EXECUTED, SKIPPED, ...)."""
        ...

    @property
    def valid_skip_prefixes(self) -> tuple[str, ...]:
        """Skip reason prefixes that allow commit."""
        ...

    @property
    def blocking_skip_prefixes(self) -> tuple[str, ...]:
        """Skip reason prefixes that block commit."""
        ...

    @property
    def terminal_phases(self) -> tuple[str, ...]:
        """Phases that must complete with PASS outcome (cannot FAIL)."""
        ...


@dataclass(frozen=True)
class TDDSchema:
    """Immutable container for TDD schema data.

    All properties are frozen tuples to prevent mutation after construction.
    """

    tdd_phases: tuple[str, ...] = field(default_factory=tuple)
    valid_statuses: tuple[str, ...] = field(default_factory=tuple)
    valid_skip_prefixes: tuple[str, ...] = field(default_factory=tuple)
    blocking_skip_prefixes: tuple[str, ...] = field(default_factory=tuple)
    terminal_phases: tuple[str, ...] = field(default_factory=tuple)
    schema_version: str = "4.0"
    total_phases: int = 5


class TDDSchemaLoader:
    """Loads TDD schema from step-tdd-cycle-schema.json.

    Responsible for:
    - Locating the schema file relative to project root
    - Parsing JSON structure
    - Extracting phase names, statuses, and skip prefixes
    - Caching parsed schema for efficiency

    Usage:
        loader = TDDSchemaLoader()
        schema = loader.load()
        print(schema.tdd_phases)  # ('PREPARE', 'RED_ACCEPTANCE', ...)
    """

    @staticmethod
    def _resolve_default_schema_path() -> Path:
        """Resolve schema path for current environment.

        Handles both:
        - Source: src/des/domain/tdd_schema.py → project_root/nWave/templates/
        - Installed: ~/.claude/lib/python/des/domain/tdd_schema.py → ~/.claude/templates/
        """
        module_file = Path(__file__)
        # Normalize to forward slashes for cross-platform matching
        module_str = str(module_file).replace("\\", "/")
        module_resolved_str = str(module_file.resolve()).replace("\\", "/")

        is_installed = (
            ".claude" in module_str or ".claude" in module_resolved_str
        ) and (
            "lib/python/des" in module_str or "lib/python/des" in module_resolved_str
        )

        if is_installed:
            for search_path in [module_file, module_file.resolve()]:
                for parent in search_path.parents:
                    if parent.name == ".claude":
                        candidate = parent / "templates" / "step-tdd-cycle-schema.json"
                        if candidate.exists():
                            return candidate

        return (
            module_file.resolve().parent.parent.parent.parent
            / "nWave"
            / "templates"
            / "step-tdd-cycle-schema.json"
        )

    def __init__(self, schema_path: Path | None = None):
        """Initialize loader with optional custom schema path.

        Args:
            schema_path: Path to schema JSON file. Defaults to project's
                         nWave/templates/step-tdd-cycle-schema.json
        """
        self._schema_path = schema_path or self._resolve_default_schema_path()
        self._cached_schema: TDDSchema | None = None

    @property
    def schema_path(self) -> Path:
        """Path to the schema JSON file."""
        return self._schema_path

    def load(self) -> TDDSchema:
        """Load and parse the TDD schema.

        Returns cached schema if already loaded.

        Returns:
            TDDSchema: Immutable schema data container

        Raises:
            FileNotFoundError: If schema file doesn't exist
            json.JSONDecodeError: If schema file is not valid JSON
            KeyError: If required schema fields are missing
        """
        if self._cached_schema is not None:
            return self._cached_schema

        raw_data = self._read_schema_file()
        self._cached_schema = self._parse_schema(raw_data)
        return self._cached_schema

    def _read_schema_file(self) -> dict:
        """Read raw JSON from schema file."""
        with open(self._schema_path, encoding="utf-8") as f:
            return json.load(f)

    def _parse_schema(self, raw_data: dict) -> TDDSchema:
        """Parse raw JSON into TDDSchema dataclass.

        Extracts:
        - tdd_phases from tdd_cycle.phase_execution_log[].phase_name
        - valid_statuses from phase_validation_rules.valid_statuses
        - valid_skip_prefixes from phase_validation_rules.skip_validation.valid_prefixes
          where allows_commit=True
        - blocking_skip_prefixes from same where allows_commit=False
        - terminal_phases from phase_validation_rules.terminal_phases.phases
        """
        tdd_phases = self._extract_tdd_phases(raw_data)
        valid_statuses = self._extract_valid_statuses(raw_data)
        valid_skip_prefixes, blocking_skip_prefixes = self._extract_skip_prefixes(
            raw_data
        )
        terminal_phases = self._extract_terminal_phases(raw_data)
        schema_version = raw_data.get("schema_version", "3.0")
        total_phases = raw_data.get("phase_validation_rules", {}).get("total_phases", 7)

        return TDDSchema(
            tdd_phases=tdd_phases,
            valid_statuses=valid_statuses,
            valid_skip_prefixes=valid_skip_prefixes,
            blocking_skip_prefixes=blocking_skip_prefixes,
            terminal_phases=terminal_phases,
            schema_version=schema_version,
            total_phases=total_phases,
        )

    def _extract_tdd_phases(self, raw_data: dict) -> tuple[str, ...]:
        """Extract ordered TDD phase names from schema."""
        phase_log = raw_data.get("tdd_cycle", {}).get("phase_execution_log", [])
        return tuple(
            phase["phase_name"] for phase in phase_log if "phase_name" in phase
        )

    def _extract_valid_statuses(self, raw_data: dict) -> tuple[str, ...]:
        """Extract valid phase statuses from schema."""
        statuses = raw_data.get("phase_validation_rules", {}).get("valid_statuses", [])
        return tuple(statuses)

    def _extract_skip_prefixes(
        self, raw_data: dict
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Extract skip prefixes, separating those that allow vs block commit.

        Returns:
            Tuple of (valid_prefixes, blocking_prefixes)
        """
        skip_rules = (
            raw_data.get("phase_validation_rules", {})
            .get("skip_validation", {})
            .get("valid_prefixes", {})
        )

        valid_prefixes = []
        blocking_prefixes = []

        for prefix, config in skip_rules.items():
            if config.get("allows_commit", False):
                valid_prefixes.append(prefix)
            else:
                blocking_prefixes.append(prefix)

        return tuple(valid_prefixes), tuple(blocking_prefixes)

    def _extract_terminal_phases(self, raw_data: dict) -> tuple[str, ...]:
        """Extract terminal phases that must complete with PASS outcome.

        Terminal phases represent successful completion and cannot have FAIL outcome.
        Example: COMMIT phase must always PASS, as FAIL indicates incomplete work.
        """
        terminal_config = raw_data.get("phase_validation_rules", {}).get(
            "terminal_phases", {}
        )
        phases = terminal_config.get("phases", [])
        return tuple(phases)

    def clear_cache(self) -> None:
        """Clear the cached schema, forcing reload on next access."""
        self._cached_schema = None


# Module-level singleton for convenience
_global_loader: TDDSchemaLoader | None = None


def get_tdd_schema() -> TDDSchema:
    """Get the TDD schema using the global loader singleton.

    Convenience function for accessing schema without managing loader instances.
    Uses module-level caching for efficiency.

    Returns:
        TDDSchema: The loaded TDD schema

    Example:
        >>> schema = get_tdd_schema()
        >>> print(schema.tdd_phases)
        ('PREPARE', 'RED_ACCEPTANCE', 'RED_UNIT', 'GREEN', 'COMMIT')
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = TDDSchemaLoader()
    return _global_loader.load()


def get_tdd_schema_loader() -> TDDSchemaLoader:
    """Get the global TDDSchemaLoader instance.

    Useful when you need access to the loader itself (e.g., for cache control).

    Returns:
        TDDSchemaLoader: The global loader instance
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = TDDSchemaLoader()
    return _global_loader


def reset_global_schema_loader() -> None:
    """Reset the global schema loader.

    Useful in tests to ensure clean state between test cases.
    """
    global _global_loader
    _global_loader = None
