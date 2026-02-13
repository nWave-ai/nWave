"""Roadmap Schema Loader - Single Source of Truth for Roadmap Structure.

Loads roadmap validation rules from nWave/templates/roadmap-schema.yaml.
Provides cached access via frozen dataclass.

Mirrors tdd_schema.py pattern: frozen dataclass, lazy path resolution,
singleton loader with WSL-safe path handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RoadmapSchema:
    """Immutable container for roadmap schema data."""

    schema_version: str = "1.0"
    required_roadmap_fields: tuple[str, ...] = field(default_factory=tuple)
    required_phase_fields: tuple[str, ...] = field(default_factory=tuple)
    required_step_fields: tuple[str, ...] = field(default_factory=tuple)
    phase_id_pattern: str = r"^\d{2}$"
    step_id_pattern: str = r"^\d{2}-\d{2}$"
    max_criteria_words: int = 30
    max_criteria_per_step: int = 5
    max_step_name_words: int = 10
    max_description_words: int = 50
    max_decomposition_ratio: float = 2.5
    valid_agents: tuple[str, ...] = field(default_factory=tuple)
    valid_deps_strategies: tuple[str, ...] = field(default_factory=tuple)
    valid_statuses: tuple[str, ...] = field(default_factory=tuple)


class RoadmapSchemaLoader:
    """Loads schema from roadmap-schema.yaml. WSL-safe path resolution."""

    SCHEMA_FILENAME = "roadmap-schema.yaml"

    @staticmethod
    def _resolve_default_schema_path() -> Path:
        """Resolve schema path for current environment.

        Handles both:
        - Source: src/des/domain/roadmap_schema.py -> project_root/nWave/templates/
        - Installed: ~/.claude/lib/python/des/domain/roadmap_schema.py -> ~/.claude/templates/
        """
        module_file = Path(__file__)
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
                        candidate = (
                            parent / "templates" / RoadmapSchemaLoader.SCHEMA_FILENAME
                        )
                        if candidate.exists():
                            return candidate

        return (
            module_file.resolve().parent.parent.parent.parent
            / "nWave"
            / "templates"
            / RoadmapSchemaLoader.SCHEMA_FILENAME
        )

    def __init__(self, schema_path: Path | None = None):
        self._schema_path = schema_path or self._resolve_default_schema_path()
        self._cached_schema: RoadmapSchema | None = None

    @property
    def schema_path(self) -> Path:
        return self._schema_path

    def load(self) -> RoadmapSchema:
        if self._cached_schema is not None:
            return self._cached_schema
        raw_data = self._read_schema_file()
        self._cached_schema = self._parse_schema(raw_data)
        return self._cached_schema

    def _read_schema_file(self) -> dict:
        with open(self._schema_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _parse_schema(self, raw: dict) -> RoadmapSchema:
        required = raw.get("required_fields", {})
        constraints = raw.get("constraints", {})
        id_patterns = raw.get("id_patterns", {})

        return RoadmapSchema(
            schema_version=raw.get("schema_version", "1.0"),
            required_roadmap_fields=tuple(required.get("roadmap", [])),
            required_phase_fields=tuple(required.get("phase", [])),
            required_step_fields=tuple(required.get("step", [])),
            phase_id_pattern=id_patterns.get("phase_id", r"^\d{2}$"),
            step_id_pattern=id_patterns.get("step_id", r"^\d{2}-\d{2}$"),
            max_criteria_words=constraints.get("max_criteria_words", 30),
            max_criteria_per_step=constraints.get("max_criteria_per_step", 5),
            max_step_name_words=constraints.get("max_step_name_words", 10),
            max_description_words=constraints.get("max_description_words", 50),
            max_decomposition_ratio=constraints.get("max_decomposition_ratio", 2.5),
            valid_agents=tuple(raw.get("valid_agents", [])),
            valid_deps_strategies=tuple(raw.get("valid_deps_strategies", [])),
            valid_statuses=tuple(raw.get("valid_validation_statuses", [])),
        )

    def clear_cache(self) -> None:
        self._cached_schema = None


_global_loader: RoadmapSchemaLoader | None = None


def get_roadmap_schema() -> RoadmapSchema:
    """Get roadmap schema via cached singleton."""
    global _global_loader
    if _global_loader is None:
        _global_loader = RoadmapSchemaLoader()
    return _global_loader.load()


def reset_global_schema_loader() -> None:
    """Reset singleton. Used in tests."""
    global _global_loader
    _global_loader = None
