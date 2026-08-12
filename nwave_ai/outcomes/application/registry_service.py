"""RegistryService — orchestrates registry reads/writes with id uniqueness
and JSON Schema validation.

Driving port: register / load. Drives the RegistryReader and
RegistryWriter driven ports. Validates every outcome against the
packaged nwave_ai/outcomes/schema.json before persistence (fail-fast on
malformed entries — protects the registry contract).
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files

from jsonschema import Draft7Validator
from jsonschema import ValidationError as JsonSchemaValidationError

from nwave_ai.outcomes.domain.outcome import Outcome  # noqa: TC001  # used at runtime
from nwave_ai.outcomes.domain.serialization import outcome_to_dict
from nwave_ai.outcomes.ports.registry_io import (  # noqa: TC001  # runtime DI
    RegistryReader,
    RegistryWriter,
)


_SCHEMA_RESOURCE = files("nwave_ai.outcomes").joinpath("schema.json")


class DuplicateOutcomeIdError(Exception):
    """Raised when register is called with an id already present.

    Message format: ``duplicate outcome id: <id>`` — stable contract for
    CLI stderr matching (AC-1.b: /duplicate.*OUT-1/).
    """


class InvalidOutcomeError(Exception):
    """Raised when an outcome fails JSON Schema validation."""


class UnknownOutcomeIdError(Exception):
    """Raised when a collision check is requested for an id not in registry."""


@lru_cache(maxsize=1)
def _load_validator() -> Draft7Validator:
    schema = json.loads(_SCHEMA_RESOURCE.read_text(encoding="utf-8"))
    return Draft7Validator(schema)


class RegistryService:
    """Application service — register a new outcome, load all outcomes."""

    def __init__(
        self,
        reader: RegistryReader,
        writer: RegistryWriter,
    ) -> None:
        self._reader = reader
        self._writer = writer

    def register(self, outcome: Outcome) -> None:
        """Append `outcome` after JSON Schema validation and id-uniqueness check.

        Raises:
            InvalidOutcomeError: when the outcome fails schema validation.
            DuplicateOutcomeIdError: when the id is already present.
        """
        self._validate_against_schema(outcome)
        self._guard_unique_id(outcome)
        self._writer.append_outcome(outcome)

    def load(self) -> tuple[Outcome, ...]:
        """Return an immutable snapshot of all registered outcomes."""
        return self._reader.read_outcomes()

    def collision_check_for_id(self, outcome_id: str) -> CollisionReport:
        """Run a collision check for `outcome_id` excluding itself from the
        snapshot, so an outcome cannot collide with its own registry entry.

        Drives US-3 aggregate scan over feature-delta.md.

        Raises:
            UnknownOutcomeIdError: when `outcome_id` is not in the registry.
        """
        # Local import keeps the module-level dependency graph minimal and
        # avoids a circular import risk if collision_detector ever imports
        # back from registry_service.
        from nwave_ai.outcomes.application.collision_detector import (
            CollisionDetector,
            TargetShape,
        )

        snapshot = self._reader.read_outcomes()
        target = self._find_outcome(snapshot, outcome_id)
        others = tuple(o for o in snapshot if o.id != outcome_id)
        detector = CollisionDetector()
        return detector.check(
            target=TargetShape(
                input_shape=target.inputs[0].shape if target.inputs else "",
                output_shape=target.output.shape,
                keywords=target.keywords,
            ),
            snapshot=others,
        )

    def _validate_against_schema(self, outcome: Outcome) -> None:
        try:
            _load_validator().validate(outcome_to_dict(outcome))
        except JsonSchemaValidationError as err:
            raise InvalidOutcomeError(
                f"outcome {outcome.id} fails schema: {err.message}"
            ) from err

    def _guard_unique_id(self, outcome: Outcome) -> None:
        existing_ids = tuple(o.id for o in self._reader.read_outcomes())
        if outcome.id in existing_ids:
            raise DuplicateOutcomeIdError(f"duplicate outcome id: {outcome.id}")

    def _find_outcome(self, snapshot: tuple[Outcome, ...], outcome_id: str) -> Outcome:
        for outcome in snapshot:
            if outcome.id == outcome_id:
                return outcome
        raise UnknownOutcomeIdError(f"unknown outcome id: {outcome_id}")
