"""
TDD Schema Loader - Single Source of Truth for TDD Rules.

Loads TDD phase definitions, validation rules, and skip prefixes from
nWave/templates/step-tdd-cycle-schema.json. Provides cached access to avoid
repeated file I/O.

Dual-canon support (ADR-025, 2026-05-07):
- ``legacy_phases`` (v4, 5-phase: PREPARE/RED_ACCEPTANCE/RED_UNIT/GREEN/COMMIT)
  is the active list returned by ``tdd_phases`` for backward compatibility
  with pre-2026-05-07 audit-log replay and existing validators/tests.
- ``canonical_phases`` (v5, 3-phase: RED/GREEN/COMMIT) is the new canonical
  list per ADR-025. RED absorbs PREPARE+RED_ACCEPTANCE+RED_UNIT.

Callers that need to write or validate v5 logs explicitly read
``canonical_phases``; callers consuming the legacy contract continue to read
``tdd_phases`` unchanged.

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


# Module-level constants exposing both canons explicitly.
# ADR-025 (2026-05-07): canonical TDD cycle is 3-phase. Legacy 5-phase
# preserved for backward-compat audit-log replay.
LEGACY_PHASES: tuple[str, ...] = (
    "PREPARE",
    "RED_ACCEPTANCE",
    "RED_UNIT",
    "GREEN",
    "COMMIT",
)
"""5-phase TDD cycle (v4, ADR-024 era). Kept for audit-log replay of
pre-2026-05-07 commits and for the JSON schema's active ``valid_tdd_phases``
list (which still drives the default loader path)."""

CANONICAL_PHASES: tuple[str, ...] = ("RED", "GREEN", "COMMIT")
"""3-phase TDD cycle (v5, ADR-025, 2026-05-07). RED absorbs
PREPARE+RED_ACCEPTANCE+RED_UNIT via the fail-for-right-reason gate; GREEN +
COMMIT semantics unchanged from v4."""


class TDDSchemaProtocol(Protocol):
    """Protocol defining the TDD schema interface.

    Used for type hints and to enable testing with mock implementations.
    """

    @property
    def tdd_phases(self) -> tuple[str, ...]:
        """Ordered tuple of active TDD phase names.

        Currently aliases ``legacy_phases`` (5-phase v4) for backward
        compatibility. Callers needing the canonical 3-phase contract
        (ADR-025) read ``canonical_phases`` explicitly.
        """
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

    Dual-canon (ADR-025, 2026-05-07):
    - ``tdd_phases`` / ``legacy_phases`` = 5-phase v4 (default active list).
    - ``canonical_phases`` = 3-phase v5 (RED, GREEN, COMMIT) for new logs.

    All tuple fields are frozen to prevent mutation after construction.
    """

    tdd_phases: tuple[str, ...] = field(default_factory=tuple)
    valid_statuses: tuple[str, ...] = field(default_factory=tuple)
    valid_skip_prefixes: tuple[str, ...] = field(default_factory=tuple)
    blocking_skip_prefixes: tuple[str, ...] = field(default_factory=tuple)
    terminal_phases: tuple[str, ...] = field(default_factory=tuple)
    schema_version: str = "4.0"
    total_phases: int = 5
    canonical_phases: tuple[str, ...] = CANONICAL_PHASES
    legacy_phases: tuple[str, ...] = LEGACY_PHASES

    def phases_for(self, schema_version: str) -> tuple[str, ...]:
        """Return phase list for the requested schema version.

        - ``"5.0"`` → canonical 3-phase (RED, GREEN, COMMIT).
        - any other version (default, ``"4.0"``, ``"3.0"``, etc.) → legacy
          5-phase, preserving prior behaviour.
        """
        if schema_version == "5.0":
            return self.canonical_phases
        return self.legacy_phases


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

        Handles three deployment contexts:
        - Source: src/des/domain/tdd_schema.py → project_root/nWave/templates/
        - Installed: ~/.claude/lib/python/des/domain/tdd_schema.py → ~/.claude/templates/
        - Plugin: .../scripts/des/domain/tdd_schema.py → .../scripts/templates/
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

        # Plugin context: scripts/des/domain/tdd_schema.py → scripts/templates/
        for search_path in [module_file, module_file.resolve()]:
            for parent in search_path.parents:
                if parent.name == "scripts":
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


# --- Deprecated global convenience functions ---
# These exist only for backward compatibility with test code.
# Production code should use TDDSchemaLoader().load() directly
# or accept TDDSchema via constructor injection.
_global_loader: TDDSchemaLoader | None = None


def resolve_schema_or_default(schema: TDDSchema | None) -> TDDSchema:
    """Return ``schema`` if non-None, else load the default via TDDSchemaLoader.

    Shared helper for constructor injection patterns where ``schema=None``
    means "use the default loader". Extracted 2026-05-03 (RPP L3) — both
    ``Validator.__init__`` and ``ValidationErrorDetector.__init__`` had
    identical 5-line resolution logic.
    """
    if schema is None:
        return TDDSchemaLoader().load()
    return schema


def get_tdd_schema() -> TDDSchema:
    """Get the TDD schema using the global loader singleton.

    .. deprecated::
        Use ``TDDSchemaLoader().load()`` or accept ``TDDSchema`` via constructor.
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = TDDSchemaLoader()
    return _global_loader.load()


def get_tdd_schema_loader() -> TDDSchemaLoader:
    """Get the global TDDSchemaLoader instance.

    .. deprecated::
        Create your own ``TDDSchemaLoader()`` instance instead.
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = TDDSchemaLoader()
    return _global_loader


def reset_global_schema_loader() -> None:
    """Reset the global schema loader.

    .. deprecated::
        Only needed when using the deprecated global functions.
    """
    global _global_loader
    _global_loader = None
