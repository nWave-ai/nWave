"""Typed domain concepts for the pi-kata-tdd-flow acceptance suite (Mandate-12).

Every domain noun used in the Gherkin lives here once as a typed value. Step
methods consume these types; business logic lives in the composition-root
services (``scripts/install/pi_kata/*``) and the reused DES adapter -- never
inline in step bodies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TddPhase(str, Enum):
    """A recorded TDD phase in the 3-phase canon (ADR-025)."""

    RED = "RED"
    GREEN = "GREEN"
    COMMIT = "COMMIT"


class PhaseStatus(str, Enum):
    """``des-log-phase`` status field."""

    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"


class CommitVerdict(str, Enum):
    """The observable verdict the commit-boundary gate returns."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"


class CycleCompleteness(str, Enum):
    """Whether a step recorded a full RED->GREEN->COMMIT cycle."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class Kata:
    """A kata under self-driven TDD. ``kata_id`` doubles as the DES project-id."""

    kata_id: str


@dataclass(frozen=True)
class StepId:
    """A ``NN-NN`` step identifier (KD2 convention)."""

    value: str


# Ordered RED->GREEN->COMMIT canon for a single completed step.
COMPLETE_CYCLE: tuple[TddPhase, ...] = (TddPhase.RED, TddPhase.GREEN, TddPhase.COMMIT)

# The four DES markers the synthesized transcript must carry (SPIKE constraint 2).
REQUIRED_DES_MARKERS: tuple[str, ...] = (
    "DES-VALIDATION",
    "DES-PROJECT-ID",
    "DES-STEP-ID",
    "DES-PROJECT-ROOT",
)
