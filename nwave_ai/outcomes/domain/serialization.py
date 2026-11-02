"""Outcome ↔ canonical-mapping serialization (pure functions).

The wire-format shape is identical for YAML persistence and JSON Schema
validation, so a single helper owns the canonical key order and field
projection. Lives in the domain layer because it is a pure transformation
of an immutable value object — no I/O, no application orchestration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nwave_ai.outcomes.domain.outcome import Outcome


def outcome_to_dict(outcome: Outcome) -> dict:
    """Convert an Outcome to a JSON/YAML-friendly mapping in canonical key order.

    Used by:
      - YamlRegistryAdapter to persist entries with stable key ordering.
      - RegistryService to validate entries against the JSON Schema.
    """
    return {
        "id": outcome.id,
        "kind": outcome.kind,
        "summary": outcome.summary,
        "feature": outcome.feature,
        "inputs": [{"shape": i.shape} for i in outcome.inputs],
        "output": {"shape": outcome.output.shape},
        "keywords": list(outcome.keywords),
        "artifact": outcome.artifact,
        "related": list(outcome.related),
        "superseded_by": outcome.superseded_by,
    }
