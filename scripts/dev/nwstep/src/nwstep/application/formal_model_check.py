"""The formal-model decision, checked before craft.

modeled needs a model file that is part of the change, a check command recorded with its exit code, and one witness
per model invariant whose name occurs in the model text. A step that declares the mutant fields also needs a mutant
file the change contains and a mutant command the checker must reject (exit non-zero, enforced by the command's
expect=fail). The mutant must differ from the model: a rejection is evidence only for a change the checker was shown.
A check command that is 'quint run' is a bounded random simulation, and the record says so as a warning.
not_needed needs its reason. The reason's trigger naming and the witness symbols are verified after craft by selfreview.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nwstep.application.diff_contracts import DiffContracts
from nwstep.domain.fault import Fault
from nwstep.domain.field import Field
from nwstep.domain.model_witness_item import ModelWitnessItem
from nwstep.domain.step import Step


class FormalModelCheck:
    DECLARED_FIELDS = (
        "formal_model",
        "no_state_reason",
        "model_file",
        "check_command",
        "invariant_witnesses",
    )
    MODELED_FIELDS = ("model_file", "check_command", "invariant_witnesses")
    MUTANT_FIELDS = ("mutant_file", "mutant_command")
    SIMULATION = (
        "'quint run' is a bounded random simulation: a pass means no violation within the bound, not a proof; "
        "an exhaustive check is 'quint verify', which needs the Apalache backend (apalache-mc) on PATH"
    )

    def __init__(self, contracts: DiffContracts) -> None:
        self._contracts = contracts

    def check(self, step: Step, values: dict[str, Any], root: Path) -> list[str]:
        """Only a step that declares the model fields is checked; older schemas keep their own formal_model field unchanged."""
        if any(step.field(name) is None for name in self.DECLARED_FIELDS):
            return []
        decision = values.get("formal_model")
        if decision is None:
            return []
        if decision == "not_needed":
            if "no_state_reason" not in values:
                raise self._field(step, "no_state_reason").refuse(
                    "formal_model is not_needed but no_state_reason is missing",
                    fault=Fault.MISSING,
                )
            return []
        required = self.MODELED_FIELDS
        if step.field("mutant_file") is not None:
            required = required + self.MUTANT_FIELDS
        missing = [name for name in required if name not in values]
        if missing:
            raise self._field(step, missing[0]).refuse(
                f"formal_model is modeled but {', '.join(missing)} is missing",
                fault=Fault.MISSING,
            )
        outcome = self._contracts.model_file(values["model_file"], root)
        if outcome.problems:
            raise self._field(step, "model_file").refuse(
                "; ".join(outcome.problems), fault=Fault.AS_WRITTEN
            )
        self._names_occur(step, values, root)
        warnings = list(outcome.warnings)
        if "mutant_file" in values:
            warnings += self._mutant(step, values, root)
        warnings += self._simulation_warning(values["check_command"]["argv"])
        return warnings

    @classmethod
    def _simulation_warning(cls, argv: list[str]) -> list[str]:
        """A check that is a bounded simulation is recorded as one, never silently taken as an exhaustive check."""
        bounded = any(
            argv[index] == "quint" and argv[index + 1] == "run"
            for index in range(len(argv) - 1)
        )
        return [f"check_command is {cls.SIMULATION}"] if bounded else []

    def _mutant(self, step: Step, values: dict[str, Any], root: Path) -> list[str]:
        """The mutant file: a model file of the change, different from the model. Its command's rejection is checked when the command runs."""
        mutant = str(values["mutant_file"])
        outcome = self._contracts.model_file(mutant, root)
        if outcome.problems:
            raise self._field(step, "mutant_file").refuse(
                "; ".join(outcome.problems), fault=Fault.AS_WRITTEN
            )
        model = self._read(step, "model_file", str(values["model_file"]), root)
        mutated = self._read(step, "mutant_file", mutant, root)
        if mutated == model:
            raise self._field(step, "mutant_file").refuse(
                f"mutant_file '{mutant}' is identical to model_file: the checker is shown no change to reject",
                fault=Fault.AS_WRITTEN,
            )
        return list(outcome.warnings)

    def _read(self, step: Step, name: str, path: str, root: Path) -> str:
        try:
            return (root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise self._field(step, name).refuse(
                f"model file '{path}' cannot be read: {error}", fault=Fault.AS_WRITTEN
            ) from None

    def _names_occur(self, step: Step, values: dict[str, Any], root: Path) -> None:
        path = str(values["model_file"])
        text = self._read(step, "model_file", path, root)
        for item in values["invariant_witnesses"]:
            try:
                witness = ModelWitnessItem.parse(item)
            except ValueError:
                continue
            if witness.name not in text:
                raise self._field(step, "invariant_witnesses").refuse(
                    f"{witness.identifier}: model invariant '{witness.name}' does not occur in '{path}'",
                    fault=Fault.AS_WRITTEN,
                )

    @staticmethod
    def _field(step: Step, name: str) -> Field:
        field = step.field(name)
        if field is None:
            raise ValueError(f"step '{step.id}' declares no field '{name}'")
        return field
