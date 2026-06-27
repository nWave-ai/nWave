"""Domain types for the plugin/skill deliverable-type acceptance suite (Mandate-12 criterion 1).

Every domain noun used in the Gherkin scenarios is expressed here ONCE as a typed
enum / dataclass / NewType. Composition-service signatures (in ``composition.py``)
consume these types -- never raw ``str`` where an enum exists. Step bodies coerce
Gherkin literals into these types via ``pytest_bdd.parsers`` converters, so the DSL
emerges from the type system rather than from a decorator-per-literal explosion.

Feature contract source of truth:
- ``docs/feature/plugin-skill-deliverable-type/feature-delta.md`` (DESIGN, DDD-1..7)
- ``docs/feature/plugin-skill-deliverable-type/design/wave-decisions.md`` (5 locked decisions)
- ``docs/feature/plugin-skill-deliverable-type/spike/findings.md`` (8/8 behaviour matrix)
- ``docs/product/architecture/ADR-PST-00{1,2,3}-*.md``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import NewType

from des.domain.des_enforcement_policy import DesEnforcementPolicy


class DeliverableType(Enum):
    """Whole-project deliverable classification (DDD-1, ADR-PST-002).

    ``APPLICATION`` is the default and keeps the pytest/TDD + DES-enforcement
    path 100% unchanged. ``PLUGIN`` / ``SKILL`` carry the DES exemption (DDD-2)
    and route verification to structural+behavioral (ADR-PST-003).

    The two "no positive resolution" shapes are modelled separately because the
    fail-safe (ADR-PST-001) hinges on them staying OUTSIDE the exempt set:
      ``UNSET``   -- nothing declared/detected (the policy receives ``None``);
      ``TYPO``    -- an unknown/misspelled declared value (e.g. ``"plugn"``);
      ``MIXEDCASE`` -- a case-mismatch (``"Plugin"``) -- case-sensitivity is
                    intentional and asserted (ADR-PST-001 obligation 1).
    """

    APPLICATION = "application"
    PLUGIN = "plugin"
    SKILL = "skill"
    UNSET = "unset"  # resolves to None at the policy boundary
    TYPO = "typo"  # an unknown declared value -> falls through to enforcement
    MIXEDCASE = "mixedcase"  # "Plugin" -> NOT exempt (case-sensitive)


# The raw string a TYPO / MIXEDCASE deliverable type carries on the wire.
_DELIVERABLE_WIRE_VALUE: dict[DeliverableType, str | None] = {
    DeliverableType.APPLICATION: "application",
    DeliverableType.PLUGIN: "plugin",
    DeliverableType.SKILL: "skill",
    DeliverableType.UNSET: None,
    DeliverableType.TYPO: "plugn",
    DeliverableType.MIXEDCASE: "Plugin",
}


def wire_value(dt: DeliverableType) -> str | None:
    """The literal value that reaches the policy for a given typed deliverable.

    ``None`` for ``UNSET``; the misspelled/case-mismatched literal otherwise.
    Used by the composition to feed ``check(prompt, <wire>)`` exactly as the
    runtime would after config resolution.
    """
    return _DELIVERABLE_WIRE_VALUE[dt]


# The closed exempt set, DERIVED from the production policy (ADR-PST-001) so the
# test vocabulary can never drift from the runtime: a type is exempt here iff its
# wire value is in ``DesEnforcementPolicy.EXEMPT_DELIVERABLE_TYPES``. The suite
# still asserts closedness/disjointness, which now also guards against a positive
# type (e.g. "application") wrongly entering the production set.
EXEMPT_DELIVERABLE_TYPES: frozenset[DeliverableType] = frozenset(
    dt
    for dt in DeliverableType
    if wire_value(dt) in DesEnforcementPolicy.EXEMPT_DELIVERABLE_TYPES
)


class StepIdPresence(Enum):
    """Whether the dispatched Task prompt carries a step-id pattern."""

    HAS_STEP_ID = "has-step-id"  # e.g. "step 03-04" -> enforcement candidate
    NO_STEP_ID = "no-step-id"  # ordinary prompt -> never blocked


class Marker(Enum):
    """An explicit per-dispatch DES marker embedded in the prompt (DDD overrides).

    These short-circuit FIRST regardless of deliverable type (D6 / SPIKE rows 5-6).
    ``NONE`` is the no-marker fixture.
    """

    NONE = "none"
    VALIDATION_REQUIRED = "validation-required"  # "DES-VALIDATION : required"
    ENFORCEMENT_EXEMPT = "enforcement-exempt"  # "DES-ENFORCEMENT : exempt"


class GateOutcome(Enum):
    """What the enforcement gate decided for a dispatch (observable at the port)."""

    BLOCKED = "blocked"  # is_enforced=True -> HookDecision.block, exit 2
    EXEMPT = "exempt"  # is_enforced=False -> HookDecision.allow, exit 0


class ExemptionReason(Enum):
    """WHY a dispatch was exempt -- distinguishes the exemption channel (HIGH-1).

    A type-carried exemption must leave NO per-dispatch ``DES-ENFORCEMENT :
    exempt`` marker in play; the issue's core promise is exactly that the
    practitioner stops hand-stamping that marker.
    """

    TYPE_CARRIED = "type-carried"  # exempt because deliverable_type in {plugin, skill}
    EXPLICIT_MARKER = "explicit-marker"  # exempt because the prompt carried a marker
    NO_STEP_ID = "no-step-id"  # exempt because there was nothing to enforce


class RootMarker(Enum):
    """A project-root filesystem marker for FS-fallback detection (ADR-PST-002, DDD-4).

    ``NESTED_NWAVE_SKILLS`` is the named collision guard: a NON-root
    ``nWave/skills/`` directory that MUST NOT trigger ``skill`` detection (the
    nwave-dev self-classification bug, SPIKE edge case 1). ``NONE`` is the empty
    fixture -> ``application``.
    """

    CLAUDE_PLUGIN_DIR = "claude-plugin-dir"  # root ".claude-plugin/" -> plugin
    PLUGIN_JSON = "plugin-json"  # root "plugin.json" -> plugin
    MARKETPLACE_JSON = "marketplace-json"  # root "marketplace.json" -> plugin
    ROOT_SKILLS_DIR = "root-skills-dir"  # root "skills/" -> skill
    ROOT_COMMANDS_DIR = "root-commands-dir"  # root "commands/" -> skill (issue AC)
    ROOT_HOOKS_DIR = "root-hooks-dir"  # root "hooks/" -> skill (issue AC)
    NESTED_NWAVE_SKILLS = (
        "nested-nwave-skills"  # "nWave/skills/" -> application (guard)
    )
    NONE = "none"  # no markers -> application


class ConfigDeclaration(Enum):
    """What ``.nwave/des-config.json`` / global config declares for ``deliverable_type``."""

    PROJECT_PLUGIN = "project-plugin"  # project file declares "plugin"
    PROJECT_SKILL = "project-skill"  # project file declares "skill"
    PROJECT_APPLICATION = "project-application"  # project file declares "application"
    GLOBAL_PLUGIN = "global-plugin"  # only global defaults.deliverable_type = "plugin"
    PROJECT_TYPO = "project-typo"  # project declares "plugn" -> safe default + warning
    # typo'd declaration AND a root skills/ dir present: the safe default must NOT
    # fall through to detection (else the typo'd repo is silently exempted as skill).
    PROJECT_TYPO_WITH_ROOT_SKILLS = "project-typo-with-root-skills"
    ABSENT = "absent"  # nothing declared -> fall through to detection


class ResolvedType(Enum):
    """The value ``DESConfig.deliverable_type`` returns after precedence resolution.

    ``NONE`` is the explicit unresolved sentinel (HIGH-1: never ``application``).
    """

    APPLICATION = "application"
    PLUGIN = "plugin"
    SKILL = "skill"
    NONE = "none"  # nothing resolved -> property returns Python None


# ---------------------------------------------------------------------------
# Typed scalars + records
# ---------------------------------------------------------------------------

Prompt = NewType("Prompt", str)


@dataclass(frozen=True)
class EnforcementCase:
    """One row of the deliverable-type enforcement matrix (ADR-PST-001).

    Mirrors the SPIKE 8/8 behaviour matrix + the fail-safe obligations. The full
    Cartesian over ``(step_id x marker x deliverable_type)`` is exercised
    exhaustively in the parametrized specification; these records are the data.
    """

    step_id: StepIdPresence
    marker: Marker
    deliverable: DeliverableType
    expected: GateOutcome
    note: str = ""


@dataclass(frozen=True)
class DetectionCase:
    """One row of the root-only FS detection table (ADR-PST-002, DDD-4)."""

    root_marker: RootMarker
    expected: ResolvedType
    note: str = ""


# The canonical enforcement matrix, expressed once as data. Seeds from the SPIKE
# 8/8 matrix and adds the fail-safe obligation rows (typo, case-mismatch). The
# input domain is finite + enumerable -> parametrize, NOT PBT (falsifier-gate).
ENFORCEMENT_MATRIX: tuple[EnforcementCase, ...] = (
    # -- core behaviour: prompt HAS step-id, NO markers (SPIKE rows 1-4) --
    EnforcementCase(
        StepIdPresence.HAS_STEP_ID,
        Marker.NONE,
        DeliverableType.APPLICATION,
        GateOutcome.BLOCKED,
        "app code stays enforced (existing behaviour preserved)",
    ),
    EnforcementCase(
        StepIdPresence.HAS_STEP_ID,
        Marker.NONE,
        DeliverableType.UNSET,
        GateOutcome.BLOCKED,
        "unset fails safe -> enforced",
    ),
    EnforcementCase(
        StepIdPresence.HAS_STEP_ID,
        Marker.NONE,
        DeliverableType.PLUGIN,
        GateOutcome.EXEMPT,
        "plugin exempt by type, NO per-dispatch marker",
    ),
    EnforcementCase(
        StepIdPresence.HAS_STEP_ID,
        Marker.NONE,
        DeliverableType.SKILL,
        GateOutcome.EXEMPT,
        "skill exempt by type, NO per-dispatch marker",
    ),
    # -- fail-safe obligations (ADR-PST-001 obligation 1): non-exempt values --
    EnforcementCase(
        StepIdPresence.HAS_STEP_ID,
        Marker.NONE,
        DeliverableType.TYPO,
        GateOutcome.BLOCKED,
        "typo'd type silently RE-ENABLES enforcement (never silently exempts)",
    ),
    EnforcementCase(
        StepIdPresence.HAS_STEP_ID,
        Marker.NONE,
        DeliverableType.MIXEDCASE,
        GateOutcome.BLOCKED,
        "case mismatch 'Plugin' is NOT exempt -- case-sensitivity asserted",
    ),
    # -- explicit markers short-circuit regardless of type (SPIKE rows 5-6) --
    EnforcementCase(
        StepIdPresence.HAS_STEP_ID,
        Marker.ENFORCEMENT_EXEMPT,
        DeliverableType.APPLICATION,
        GateOutcome.EXEMPT,
        "explicit exempt marker still works on app code",
    ),
    EnforcementCase(
        StepIdPresence.HAS_STEP_ID,
        Marker.VALIDATION_REQUIRED,
        DeliverableType.PLUGIN,
        GateOutcome.EXEMPT,
        "whole-project exemption (HIGH-2): plugin + DES-VALIDATION:required + "
        "step-id -> NOT enforced. No ordering conflict: both the type exemption "
        "and DES-VALIDATION:required short-circuit to allow (is_enforced=False). "
        "DES-VALIDATION:required means 'allow, monitored' (NOT a force-block); there "
        "is intentionally no per-step force-enforce mechanism (ADR-PST-001).",
    ),
    # -- no step-id is never blocked for any type (SPIKE rows 7-8) --
    EnforcementCase(
        StepIdPresence.NO_STEP_ID,
        Marker.NONE,
        DeliverableType.APPLICATION,
        GateOutcome.EXEMPT,
        "no step-id, app code -> nothing to enforce",
    ),
    EnforcementCase(
        StepIdPresence.NO_STEP_ID,
        Marker.NONE,
        DeliverableType.PLUGIN,
        GateOutcome.EXEMPT,
        "no step-id, plugin -> nothing to enforce",
    ),
)


# The canonical root-only detection table (ADR-PST-002, DDD-4). Finite +
# enumerable -> parametrize. The NESTED_NWAVE_SKILLS row is the collision guard.
DETECTION_TABLE: tuple[DetectionCase, ...] = (
    DetectionCase(
        RootMarker.CLAUDE_PLUGIN_DIR, ResolvedType.PLUGIN, "root .claude-plugin/"
    ),
    DetectionCase(RootMarker.PLUGIN_JSON, ResolvedType.PLUGIN, "root plugin.json"),
    DetectionCase(
        RootMarker.MARKETPLACE_JSON, ResolvedType.PLUGIN, "root marketplace.json"
    ),
    DetectionCase(RootMarker.ROOT_SKILLS_DIR, ResolvedType.SKILL, "root skills/ dir"),
    DetectionCase(
        RootMarker.ROOT_COMMANDS_DIR,
        ResolvedType.SKILL,
        "root commands/ dir (issue AC)",
    ),
    DetectionCase(
        RootMarker.ROOT_HOOKS_DIR, ResolvedType.SKILL, "root hooks/ dir (issue AC)"
    ),
    DetectionCase(
        RootMarker.NESTED_NWAVE_SKILLS,
        ResolvedType.APPLICATION,
        "nested nWave/skills/ MUST NOT trigger skill (the collision guard)",
    ),
    DetectionCase(
        RootMarker.NONE, ResolvedType.APPLICATION, "no markers -> application"
    ),
)


@dataclass
class DispatchEnvelope:
    """The inputs a single enforcement dispatch carries through the driving port.

    ``raw`` lets a scenario assert against the exact prompt text built. The
    deliverable type is resolved upstream and threaded as ``wire_value`` -- the
    same scalar the production handler would pass after ``DESConfig`` resolution.
    """

    step_id: StepIdPresence
    marker: Marker
    deliverable: DeliverableType
    raw: str | None = None
    extra: dict[str, object] = field(default_factory=dict)
