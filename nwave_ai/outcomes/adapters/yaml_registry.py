"""YamlRegistryAdapter — real-filesystem YAML adapter.

Implements both RegistryReader and RegistryWriter ports. Reads and writes
the registry YAML file in-place, preserving `schema_version` and field
order (sort_keys=False).
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003  # used at runtime in __init__

import yaml

from nwave_ai.outcomes.domain.outcome import InputShape, Outcome, OutputShape
from nwave_ai.outcomes.domain.serialization import outcome_to_dict


class YamlRegistryAdapter:
    """Filesystem adapter for the outcomes registry YAML file."""

    def __init__(self, registry_path: Path) -> None:
        self._path = registry_path

    def read_outcomes(self) -> tuple[Outcome, ...]:
        """Return an immutable snapshot of all registered outcomes."""
        data = self._load_raw()
        raw_outcomes = data.get("outcomes") or []
        return tuple(_to_outcome(raw) for raw in raw_outcomes)

    def append_outcome(self, outcome: Outcome) -> None:
        """Append the outcome to the registry on disk."""
        data = self._load_raw()
        data.setdefault("schema_version", "0.1")
        outcomes_list = list(data.get("outcomes") or [])
        outcomes_list.append(outcome_to_dict(outcome))
        data["outcomes"] = outcomes_list
        self._path.write_text(
            yaml.safe_dump(data, sort_keys=False),
            encoding="utf-8",
        )

    def _load_raw(self) -> dict:
        if not self._path.exists():
            return {"schema_version": "0.1", "outcomes": []}
        loaded = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(
                f"WHAT: invalid registry file {self._path}.\n"
                "WHY: the YAML document must be a mapping, not a sequence, scalar or null; "
                "it cannot be treated as an empty registry without losing its contents.\n"
                "HOW: restore a valid registry mapping from backup, or use --registry "
                "with a new file path to start an empty registry."
            )
        return loaded


def _to_outcome(raw: dict) -> Outcome:
    """Convert a YAML mapping into an Outcome value object."""
    inputs = tuple(InputShape(shape=i["shape"]) for i in raw.get("inputs") or ())
    output_raw = raw.get("output") or {"shape": ""}
    return Outcome(
        id=raw["id"],
        kind=raw["kind"],
        summary=raw.get("summary", ""),
        feature=raw.get("feature", ""),
        inputs=inputs,
        output=OutputShape(shape=output_raw["shape"]),
        keywords=tuple(raw.get("keywords") or ()),
        artifact=raw.get("artifact", ""),
        related=tuple(raw.get("related") or ()),
        superseded_by=raw.get("superseded_by"),
    )
