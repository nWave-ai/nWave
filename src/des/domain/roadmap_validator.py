"""Roadmap Validator - Structural and semantic validation for roadmap.json.

Pure domain logic. No I/O — takes parsed dict, returns result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from des.domain.roadmap_schema import RoadmapSchema


@dataclass(frozen=True)
class ValidationViolation:
    """Single validation violation."""

    path: str  # e.g. "phases[0].steps[1].id"
    rule: str  # e.g. "INVALID_STEP_ID"
    message: str
    severity: str  # "error" | "warning"


@dataclass(frozen=True)
class ValidationResult:
    """Result of roadmap validation."""

    is_valid: bool
    violations: tuple[ValidationViolation, ...] = field(default_factory=tuple)
    steps_found: int = 0
    phases_found: int = 0


class RoadmapValidator:
    """Validates roadmap dict against schema rules."""

    def __init__(self, schema: RoadmapSchema):
        self._schema = schema

    def validate(self, roadmap_data: dict) -> ValidationResult:
        violations: list[ValidationViolation] = []

        roadmap_meta = roadmap_data.get("roadmap", {})
        phases_list = roadmap_data.get("phases", [])

        violations.extend(self._validate_roadmap_meta(roadmap_meta, phases_list))

        all_step_ids: list[str] = []
        step_id_locations: dict[str, str] = {}
        phases_found = len(phases_list)
        steps_found = 0

        phase_id_re = re.compile(self._schema.phase_id_pattern)
        step_id_re = re.compile(self._schema.step_id_pattern)

        for pi, phase in enumerate(phases_list):
            phase_path = f"phases[{pi}]"
            phase_id = phase.get("id", "")

            violations.extend(
                self._validate_phase_fields(phase, phase_path, phase_id, phase_id_re)
            )

            steps = phase.get("steps", [])
            for si, step in enumerate(steps):
                step_path = f"{phase_path}.steps[{si}]"
                steps_found += 1
                violations.extend(
                    self._validate_step(
                        step,
                        step_path,
                        phase_id,
                        step_id_re,
                        all_step_ids,
                        step_id_locations,
                    )
                )

        violations.extend(self._validate_dep_references(phases_list, set(all_step_ids)))
        violations.extend(
            self._validate_count_metadata(roadmap_meta, phases_found, steps_found)
        )
        violations.extend(self._validate_implementation_scope(roadmap_data))

        has_errors = any(v.severity == "error" for v in violations)
        return ValidationResult(
            is_valid=not has_errors,
            violations=tuple(violations),
            steps_found=steps_found,
            phases_found=phases_found,
        )

    def _validate_roadmap_meta(
        self,
        roadmap_meta: dict,
        phases_list: list,
    ) -> list[ValidationViolation]:
        violations: list[ValidationViolation] = []
        for f in self._schema.required_roadmap_fields:
            if f == "phases":
                if not phases_list:
                    violations.append(
                        ValidationViolation(
                            path="phases",
                            rule="MISSING_REQUIRED_FIELD",
                            message="Required field 'phases' is missing or empty",
                            severity="error",
                        )
                    )
            elif f not in roadmap_meta:
                violations.append(
                    ValidationViolation(
                        path=f"roadmap.{f}",
                        rule="MISSING_REQUIRED_FIELD",
                        message=f"Required field 'roadmap.{f}' is missing",
                        severity="error",
                    )
                )
        return violations

    def _validate_phase_fields(
        self,
        phase: dict,
        phase_path: str,
        phase_id: str,
        phase_id_re: re.Pattern,
    ) -> list[ValidationViolation]:
        violations: list[ValidationViolation] = []

        for f in self._schema.required_phase_fields:
            if f not in phase:
                violations.append(
                    ValidationViolation(
                        path=f"{phase_path}.{f}",
                        rule="MISSING_REQUIRED_FIELD",
                        message=f"Required field '{f}' missing in {phase_path}",
                        severity="error",
                    )
                )

        if phase_id and not phase_id_re.match(str(phase_id)):
            violations.append(
                ValidationViolation(
                    path=f"{phase_path}.id",
                    rule="INVALID_PHASE_ID",
                    message=f"Phase ID '{phase_id}' does not match pattern {self._schema.phase_id_pattern}",
                    severity="error",
                )
            )

        description = phase.get("description", "")
        if description and not str(description).startswith("TODO"):
            word_count = len(str(description).split())
            if word_count > self._schema.max_description_words:
                violations.append(
                    ValidationViolation(
                        path=f"{phase_path}.description",
                        rule="DESCRIPTION_TOO_LONG",
                        message=f"Description has {word_count} words (max {self._schema.max_description_words})",
                        severity="warning",
                    )
                )

        return violations

    def _validate_step(
        self,
        step: dict,
        step_path: str,
        phase_id: str,
        step_id_re: re.Pattern,
        all_step_ids: list[str],
        step_id_locations: dict[str, str],
    ) -> list[ValidationViolation]:
        violations: list[ValidationViolation] = []

        for f in self._schema.required_step_fields:
            if f not in step:
                violations.append(
                    ValidationViolation(
                        path=f"{step_path}.{f}",
                        rule="MISSING_REQUIRED_FIELD",
                        message=f"Required field '{f}' missing in {step_path}",
                        severity="error",
                    )
                )

        step_id = step.get("id", "")

        if step_id and not step_id_re.match(str(step_id)):
            violations.append(
                ValidationViolation(
                    path=f"{step_path}.id",
                    rule="INVALID_STEP_ID",
                    message=f"Step ID '{step_id}' does not match pattern {self._schema.step_id_pattern}",
                    severity="error",
                )
            )

        if step_id and phase_id and step_id_re.match(str(step_id)):
            prefix = str(step_id).split("-")[0]
            if prefix != str(phase_id):
                violations.append(
                    ValidationViolation(
                        path=f"{step_path}.id",
                        rule="STEP_PHASE_MISMATCH",
                        message=f"Step ID '{step_id}' prefix '{prefix}' does not match phase ID '{phase_id}'",
                        severity="error",
                    )
                )

        if step_id:
            if step_id in step_id_locations:
                violations.append(
                    ValidationViolation(
                        path=f"{step_path}.id",
                        rule="DUPLICATE_STEP_ID",
                        message=f"Step ID '{step_id}' already defined at {step_id_locations[step_id]}",
                        severity="error",
                    )
                )
            else:
                step_id_locations[step_id] = step_path
            all_step_ids.append(step_id)

        step_name = step.get("name", "")
        if step_name and not str(step_name).startswith("TODO"):
            name_words = len(str(step_name).split())
            if name_words > self._schema.max_step_name_words:
                violations.append(
                    ValidationViolation(
                        path=f"{step_path}.name",
                        rule="STEP_NAME_TOO_LONG",
                        message=f"Step name has {name_words} words (max {self._schema.max_step_name_words})",
                        severity="warning",
                    )
                )

        violations.extend(self._validate_step_criteria(step, step_path))

        agent = step.get("agent")
        if (
            agent
            and self._schema.valid_agents
            and agent not in self._schema.valid_agents
        ):
            violations.append(
                ValidationViolation(
                    path=f"{step_path}.agent",
                    rule="UNKNOWN_AGENT",
                    message=f"Agent '{agent}' not in valid agents list",
                    severity="warning",
                )
            )

        return violations

    def _validate_step_criteria(
        self,
        step: dict,
        step_path: str,
    ) -> list[ValidationViolation]:
        violations: list[ValidationViolation] = []
        criteria_raw = step.get("criteria")

        # Empty / unset / placeholder — nothing to validate.
        if criteria_raw is None or criteria_raw in ("", []):
            return violations
        if isinstance(criteria_raw, str) and criteria_raw.startswith("TODO"):
            return violations

        # Schema contract (F-1): criteria is list[str]. Legacy string form is
        # accepted with a single warning + migration hint — never errors.
        if isinstance(criteria_raw, list):
            criteria_list = [str(c).strip() for c in criteria_raw if str(c).strip()]
        elif isinstance(criteria_raw, str):
            violations.append(
                ValidationViolation(
                    path=f"{step_path}.criteria",
                    rule="LEGACY_CRITERIA_STRING",
                    message=(
                        "Step.criteria is a string; the schema now expects "
                        "list[str]. Convert to list: [criterion1, criterion2]"
                    ),
                    severity="warning",
                )
            )
            # Skip word/count checks on legacy form — migration hint is enough.
            return violations
        else:
            # Unknown type — single warning, do not error.
            violations.append(
                ValidationViolation(
                    path=f"{step_path}.criteria",
                    rule="LEGACY_CRITERIA_STRING",
                    message=(
                        f"Step.criteria has unsupported type "
                        f"{type(criteria_raw).__name__}; expected list[str]. "
                        "Convert to list: [criterion1, criterion2]"
                    ),
                    severity="warning",
                )
            )
            return violations

        if len(criteria_list) > self._schema.max_criteria_per_step:
            violations.append(
                ValidationViolation(
                    path=f"{step_path}.criteria",
                    rule="TOO_MANY_CRITERIA",
                    message=f"Step has {len(criteria_list)} criteria (max {self._schema.max_criteria_per_step})",
                    severity="warning",
                )
            )

        for ci, criterion in enumerate(criteria_list):
            word_count = len(criterion.split())
            if word_count > self._schema.max_criteria_words:
                violations.append(
                    ValidationViolation(
                        path=f"{step_path}.criteria[{ci}]",
                        rule="CRITERIA_TOO_LONG",
                        message=f"Criterion has {word_count} words (max {self._schema.max_criteria_words})",
                        severity="warning",
                    )
                )

        return violations

    def _validate_dep_references(
        self,
        phases_list: list,
        all_ids_set: set[str],
    ) -> list[ValidationViolation]:
        violations: list[ValidationViolation] = []
        for pi, phase in enumerate(phases_list):
            for si, step in enumerate(phase.get("steps", [])):
                deps = step.get("deps", [])
                if isinstance(deps, list):
                    for dep in deps:
                        if dep and dep not in all_ids_set:
                            violations.append(
                                ValidationViolation(
                                    path=f"phases[{pi}].steps[{si}].deps",
                                    rule="INVALID_DEP_REFERENCE",
                                    message=f"Dependency '{dep}' does not reference an existing step ID",
                                    severity="error",
                                )
                            )
        return violations

    def _validate_count_metadata(
        self,
        roadmap_meta: dict,
        phases_found: int,
        steps_found: int,
    ) -> list[ValidationViolation]:
        violations: list[ValidationViolation] = []

        declared_total = roadmap_meta.get("total_steps")
        if declared_total is not None and int(declared_total) != steps_found:
            violations.append(
                ValidationViolation(
                    path="roadmap.total_steps",
                    rule="TOTAL_STEPS_MISMATCH",
                    message=f"Declared total_steps={declared_total} but found {steps_found} steps",
                    severity="error",
                )
            )

        declared_phases = roadmap_meta.get("phases")
        if declared_phases is not None and int(declared_phases) != phases_found:
            violations.append(
                ValidationViolation(
                    path="roadmap.phases",
                    rule="PHASES_COUNT_MISMATCH",
                    message=f"Declared phases={declared_phases} but found {phases_found} phases",
                    severity="error",
                )
            )

        return violations

    def _validate_implementation_scope(
        self,
        roadmap_data: dict,
    ) -> list[ValidationViolation]:
        violations: list[ValidationViolation] = []

        if "implementation_scope" not in roadmap_data:
            violations.append(
                ValidationViolation(
                    path="implementation_scope",
                    rule="MISSING_IMPLEMENTATION_SCOPE",
                    message="Missing 'implementation_scope' section with source_directories",
                    severity="warning",
                )
            )
        elif "source_directories" not in roadmap_data.get("implementation_scope", {}):
            violations.append(
                ValidationViolation(
                    path="implementation_scope.source_directories",
                    rule="MISSING_SOURCE_DIRECTORIES",
                    message="Missing 'source_directories' in implementation_scope",
                    severity="warning",
                )
            )

        return violations
