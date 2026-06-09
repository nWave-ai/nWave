"""ATDD-Pure 7-phase scaffolding — declarative domain types.

Phase 1 scaffolding for the ATDD-pure workflow (ADR-027). Defines the
7-phase enum, legal transition matrix, gap/verdict/event dataclasses,
and routing-exit sentinels.

NO business logic, NO TDD cycle implementation: this module is pure
data + enum. Orchestrator state-machine implementation lands in Phase 2
(`src/des/application/atdd_pure_runner.py`).

References:
- ADR-027: docs/architecture/adrs/adr-027-atdd-pure-7-phase-extension.md
- Design: docs/feature/atdd-pure-7-phase-scaffolding/design/wave-decisions.md
- Plan v3: docs/proposals/atdd-pure-workflow-restructure-v3-2026-05-19.md
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal

from des.domain.value_objects import AgentName, FeatureName, StepId


if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


# ---------------------------------------------------------------------------
# Type aliases (per architect Reuse Analysis Table §6)
# ---------------------------------------------------------------------------

# Plan v3 vocabulary uses `feature_id`; existing DES uses FeatureName.
# Alias preserves call-site terminology without renaming 30+ existing uses.
FeatureId = FeatureName

# ADR-027 §Decision: workflow_mode opt-in dispatch selector.
WorkflowMode = Literal["classic", "atdd_pure"]

# Plan v3 §4.1: cohort pre-assignment drives SLO calibration.
Cohort = Literal["S", "M", "L", "XL"]


# ---------------------------------------------------------------------------
# Phase enum + routing-exit sentinel
# ---------------------------------------------------------------------------


class ATDDPurePhase(str, Enum):
    """The 7 canonical ATDD-pure phases (ADR-027 §Decision).

    Execution order: A → B → C → D → (A | E | exit) → E → F → G.
    Phase D is the only non-linear node; routing exits via PhaseExit.
    """

    A_GREEN_ATS = "A_GREEN_ATS"
    B_COVERAGE_CLEANUP = "B_COVERAGE_CLEANUP"
    C_REVIEWER_AUDIT = "C_REVIEWER_AUDIT"
    D_GAP_ROUTING = "D_GAP_ROUTING"
    E_BATCH_REFACTOR = "E_BATCH_REFACTOR"
    F_FINAL_REVIEW = "F_FINAL_REVIEW"
    G_COMMIT = "G_COMMIT"


class PhaseExit(str, Enum):
    """Non-phase routing outcomes from Phase D (architect choice 3).

    Sentinel enum keeps `ATDDPurePhase` clean of non-phase routing
    targets. Phase D returns one of these when the next step is NOT a
    forward phase transition.
    """

    RELOOP_A = "RELOOP_A"  # AT-gap-in-scope → re-enter Phase A with refined ATs
    REROUTE_DISCUSS = "REROUTE_DISCUSS"  # specification ambiguity upstream
    REROUTE_DESIGN = "REROUTE_DESIGN"  # architecture-scope-miss upstream
    REROUTE_DEVOPS = "REROUTE_DEVOPS"  # platform/infra ambiguity upstream
    HUMAN_ESCALATION = "HUMAN_ESCALATION"  # halt + human review
    CHECKPOINT_TIMEOUT = "CHECKPOINT_TIMEOUT"  # wall-clock budget exceeded
    TERMINAL = "TERMINAL"  # G_COMMIT reached — end of cycle


# ---------------------------------------------------------------------------
# Legal transition matrix (architect §1.3)
# ---------------------------------------------------------------------------

LEGAL_TRANSITIONS: dict[ATDDPurePhase, frozenset[ATDDPurePhase | PhaseExit]] = {
    ATDDPurePhase.A_GREEN_ATS: frozenset({ATDDPurePhase.B_COVERAGE_CLEANUP}),
    ATDDPurePhase.B_COVERAGE_CLEANUP: frozenset({ATDDPurePhase.C_REVIEWER_AUDIT}),
    ATDDPurePhase.C_REVIEWER_AUDIT: frozenset({ATDDPurePhase.D_GAP_ROUTING}),
    ATDDPurePhase.D_GAP_ROUTING: frozenset(
        {
            ATDDPurePhase.E_BATCH_REFACTOR,
            PhaseExit.RELOOP_A,
            PhaseExit.REROUTE_DISCUSS,
            PhaseExit.REROUTE_DESIGN,
            PhaseExit.REROUTE_DEVOPS,
            PhaseExit.HUMAN_ESCALATION,
            PhaseExit.CHECKPOINT_TIMEOUT,
        }
    ),
    ATDDPurePhase.E_BATCH_REFACTOR: frozenset({ATDDPurePhase.F_FINAL_REVIEW}),
    ATDDPurePhase.F_FINAL_REVIEW: frozenset(
        {ATDDPurePhase.G_COMMIT, PhaseExit.HUMAN_ESCALATION}
    ),
    ATDDPurePhase.G_COMMIT: frozenset({PhaseExit.TERMINAL}),
}


class IllegalPhaseTransition(Exception):
    """Raised when orchestrator attempts a transition not in LEGAL_TRANSITIONS.

    Narrow exception (architect §7 justified divergence): orchestrator needs
    to discriminate this failure mode from generic value errors at the
    routing call site.
    """


# ---------------------------------------------------------------------------
# Gap classification enums
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """ATGap severity per plan v3 §7.2 routing predicate."""

    BLOCKER = "BLOCKER"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ATGapKind(str, Enum):
    """Reviewer-authored gap kinds (plan v3 §7.1 + ADR-027 glossary).

    ARCHITECTURE_SCOPE_MISS is router-derived (Phase D second-order rule),
    not reviewer-authored — hence absent from this enum.
    """

    AT_GAP_IN_DELIVERY_SCOPE = "at_gap_in_delivery_scope"
    SPECIFICATION_AMBIGUITY = "specification_ambiguity"


# ---------------------------------------------------------------------------
# ATGap dataclass (architect §2.1 + choice 1: source_at_path included)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ATGap:
    """A single reviewer-identified gap in acceptance-test coverage.

    Per architect choice 1 (Ale ratified): `source_at_path` is INCLUDED
    as a `Path` field. Reviewer optionally populates with the offending
    AT file path; orchestrator ignores; audit-report renderer uses.
    """

    scenario_class: str
    current_at_count: int
    reason: str
    kind: ATGapKind
    severity: Severity
    source_at_path: Path | None = None

    def __post_init__(self) -> None:
        if not self.scenario_class:
            raise ValueError("scenario_class must be non-empty")
        if self.current_at_count < 0:
            raise ValueError(f"current_at_count must be >= 0: {self.current_at_count}")
        if not self.reason:
            raise ValueError("reason must be non-empty")
        if len(self.reason) > 500:
            raise ValueError(
                f"reason exceeds 500-char telemetry bound: {len(self.reason)}"
            )
        if self.source_at_path is not None:
            if self.source_at_path.is_absolute():
                raise ValueError(
                    f"source_at_path must be repo-relative, not absolute: "
                    f"{self.source_at_path}"
                )
            if ".." in self.source_at_path.parts:
                raise ValueError(
                    f"source_at_path must not contain '..' segments: "
                    f"{self.source_at_path}"
                )


# ---------------------------------------------------------------------------
# Reviewer verdict shapes (architect choice 2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhaseCReviewerVerdict:
    """Phase C audit verdict — verdict_hash OPTIONAL (architect choice 2).

    Phase C may halt before producing a verdict (e.g. reviewer LLM crash);
    in that path the halt event is the record of truth, not this verdict.
    """

    step_id: StepId
    feature_id: FeatureId
    findings: list[ATGap]
    approved: bool
    verdict_hash: str | None = None

    def __post_init__(self) -> None:
        # Invariant: approved=True ⇔ no BLOCKER findings.
        if self.approved and any(f.severity == Severity.BLOCKER for f in self.findings):
            raise ValueError(
                "PhaseCReviewerVerdict cannot be approved with BLOCKER findings"
            )
        if self.verdict_hash is not None and not _is_hex64(self.verdict_hash):
            raise ValueError(
                f"verdict_hash must be 64-char hex (HMAC-SHA256): {self.verdict_hash!r}"
            )


@dataclass(frozen=True)
class PhaseFReviewerVerdict:
    """Phase F terminal verdict — verdict_hash MANDATORY (architect choice 2).

    The G_COMMIT phase emits a `Reviewed-by:` trailer carrying this
    verdict_hash. Earned Trust APPROVAL gate requires it always present.
    """

    step_id: StepId
    feature_id: FeatureId
    approved: bool
    verdict_hash: str

    def __post_init__(self) -> None:
        if not _is_hex64(self.verdict_hash):
            raise ValueError(
                f"verdict_hash must be 64-char hex (HMAC-SHA256): {self.verdict_hash!r}"
            )


def _is_hex64(s: str) -> bool:
    """Validate string is 64-character lowercase hex (HMAC-SHA256 output)."""
    if len(s) != 64:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Domain events (architect §3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeliverBlocker:
    """Emitted by Phase D when a BLOCKER gap halts the cycle (plan v3 §7.2)."""

    feature_id: FeatureId
    step_id: StepId
    gaps: tuple[ATGap, ...]
    timestamp: datetime

    def __post_init__(self) -> None:
        _require_tz_aware(self.timestamp, "DeliverBlocker.timestamp")


@dataclass(frozen=True)
class AcceptanceTestGapIdentified:
    """Emitted by Phase D on AT-gap-in-delivery-scope (plan v3 §7.2 case 5)."""

    feature_id: FeatureId
    step_id: StepId
    gaps: tuple[ATGap, ...]
    cycle_n: int
    timestamp: datetime

    def __post_init__(self) -> None:
        _require_tz_aware(self.timestamp, "AcceptanceTestGapIdentified.timestamp")
        if self.cycle_n < 0:
            raise ValueError(f"cycle_n must be >= 0: {self.cycle_n}")


@dataclass(frozen=True)
class SpecificationAmbiguityDetected:
    """Emitted by Phase D on upstream ambiguity reroute (plan v3 §6.7)."""

    feature_id: FeatureId
    step_id: StepId
    gaps: tuple[ATGap, ...]
    upstream_wave: Literal["DISCUSS", "DESIGN", "DEVOPS"]
    timestamp: datetime

    def __post_init__(self) -> None:
        _require_tz_aware(self.timestamp, "SpecificationAmbiguityDetected.timestamp")


@dataclass(frozen=True)
class ArchitectureScopeMissDetected:
    """Emitted by Phase D on second-order architecture-scope-miss (plan v3 §7.1)."""

    feature_id: FeatureId
    step_id: StepId
    scenario_classes: tuple[str, ...]
    missing_components: tuple[str, ...]
    timestamp: datetime

    def __post_init__(self) -> None:
        _require_tz_aware(self.timestamp, "ArchitectureScopeMissDetected.timestamp")


@dataclass(frozen=True)
class DeliverTimeoutExceeded:
    """Emitted by Phase D on wall-clock budget breach (plan v3 §7.2 case 3)."""

    feature_id: FeatureId
    step_id: StepId
    wall_clock_s: float
    current_phase: ATDDPurePhase
    timestamp: datetime

    def __post_init__(self) -> None:
        _require_tz_aware(self.timestamp, "DeliverTimeoutExceeded.timestamp")
        if self.wall_clock_s < 0:
            raise ValueError(f"wall_clock_s must be >= 0: {self.wall_clock_s}")


@dataclass(frozen=True)
class FalsifierGateTripped:
    """Emitted by falsifier-gate script on metric breach (plan v3 §4.5.2).

    Shape lives here (not in scripts/automation/) so script + DES sequencer
    + telemetry aggregator share one SSOT definition.
    """

    feature_id: FeatureId
    breach: dict[str, float]
    flipped_to_mode: Literal["classic"]
    timestamp: datetime

    def __post_init__(self) -> None:
        _require_tz_aware(self.timestamp, "FalsifierGateTripped.timestamp")


def _require_tz_aware(ts: datetime, field_name: str) -> None:
    """Enforce tz-aware UTC timestamp invariant on event dataclasses."""
    if ts.tzinfo is None:
        raise ValueError(f"{field_name} must be tz-aware (UTC required)")


# ---------------------------------------------------------------------------
# Public exports (explicit for mypy strict + import hygiene)
# ---------------------------------------------------------------------------

__all__ = [
    "LEGAL_TRANSITIONS",
    "ATDDPurePhase",
    "ATGap",
    "ATGapKind",
    "AcceptanceTestGapIdentified",
    "AgentName",
    "ArchitectureScopeMissDetected",
    "Cohort",
    "DeliverBlocker",
    "DeliverTimeoutExceeded",
    "FalsifierGateTripped",
    "FeatureId",
    "IllegalPhaseTransition",
    "PhaseCReviewerVerdict",
    "PhaseExit",
    "PhaseFReviewerVerdict",
    "Severity",
    "SpecificationAmbiguityDetected",
    "StepId",
    "WorkflowMode",
]
