"""Result DTO + smoke-depth enum.

``SmokeDepth.TURN`` is the reserved seam for the deferred
``F-RC-REAL-TURN-SMOKE`` (DESIGN D-8 / L4); kept present but unused so the gate
can be widened by flipping depth, not re-architecting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SmokeDepth(Enum):
    """How deep a lane smoke-tests the installed tool.

    BOOT — install + ``--version`` + real provisioned-artifact asserts (default).
    TURN — reserved seam for the deferred real model-turn smoke. Not wired.
    """

    BOOT = "boot"
    TURN = "turn"


class SmokeStep(Enum):
    """The ordered steps a single lane runs."""

    INSTALL_PUBLISHED = "install_published"
    PROVISION = "provision"
    BOOT = "boot"
    ASSERT_ARTIFACTS = "assert_artifacts"


@dataclass(frozen=True)
class StepOutcome:
    """Pass/fail + diagnostic for one smoke step."""

    step: SmokeStep
    passed: bool
    diagnostic: str = ""


@dataclass(frozen=True)
class SmokeResult:
    """Aggregate result of one lane (one tool on one OS).

    ``passed`` is True iff EVERY step passed. ``diagnostics`` is a readable,
    multi-line explanation of any failure (the defect the feature fixes: a
    failing step must NEVER report pass).
    """

    tool: str
    passed: bool
    steps: tuple[StepOutcome, ...] = field(default_factory=tuple)
    diagnostics: str = ""
