"""Domain types for the des-verify-integrity mode-aware acceptance slice.

ADR-028 D4.2 / slice-02 of the atdd-pure-roadmap-free-rollout (Mandate-12
criterion 1). Every domain noun used in the Gherkin is expressed once here as
a typed enum or NewType. Step bodies and the composition service consume these
typed parameters -- no raw `str` where a domain enum exists.
"""

from __future__ import annotations

from enum import Enum
from typing import NewType


class WorkflowMode(str, Enum):
    """The project workflow mode resolved from .nwave/config.yaml:workflow.mode.

    ATDD_PURE  -- roadmap-free, execution-log-free spine (ADR-028). des-verify-integrity
                  validates the AT-completion ledger + slice plan instead of
                  roadmap.json / execution-log.json.
    CLASSIC    -- roadmap-based DELIVER; the existing 0/1/2 exit-code contract
                  (roadmap.json + execution-log.json cross-reference) is preserved.
    UNSET      -- no `workflow.mode` key (or no config file). Treated as CLASSIC
                  by des-verify-integrity: the default, no-regression path.
    """

    ATDD_PURE = "atdd_pure"
    CLASSIC = "classic"
    UNSET = "unset"


class LedgerState(str, Enum):
    """Presence/shape of the AT-completion ledger for an atdd_pure feature.

    PRESENT_ALL_SHIPPED -- ledger exists and every slice-plan row is `shipped`.
    ABSENT              -- no AT-completion ledger file. Under atdd_pure this is
                           a verification FAILURE with a structured diagnostic
                           (exit 1), never a crash (ADR-028 D3).
    """

    PRESENT_ALL_SHIPPED = "present_all_shipped"
    ABSENT = "absent"


class IntegrityVerdict(str, Enum):
    """The user-observable verdict of one des-verify-integrity invocation.

    Maps onto the CLI exit-code contract (ADR-028 Reuse Analysis: atdd_pure
    reuses exit codes 0/1; the classic 0/1/2 contract is preserved unchanged).
    """

    VERIFIED = "verified"  # exit 0
    VIOLATION = "violation"  # exit 1
    USAGE_ERROR = "usage_error"  # exit 2


class ClassicProjectShape(str, Enum):
    """The classic-mode (roadmap-based) deliver-project shape under verification.

    These shapes exercise the existing 0/1/2 exit-code contract that slice-02
    MUST preserve byte-for-byte under classic / unset mode (ADR-028 D4.2 limb 4,
    the no-regression limb).

    COMPLETE_TRACES   -- roadmap.json + execution-log.json with every TDD phase
                         recorded for every step -> verified (exit 0).
    INCOMPLETE_TRACES -- roadmap.json + execution-log.json missing a TDD phase
                         for a step -> integrity violation (exit 1).
    """

    COMPLETE_TRACES = "complete_traces"
    INCOMPLETE_TRACES = "incomplete_traces"


class VerifyInvocation(str, Enum):
    """How the operator invokes des-verify-integrity.

    FULL          -- the default invocation: roadmap.json + execution-log.json
                     cross-reference.
    ROADMAP_ONLY  -- the `--roadmap-only` flag. Classic mode validates roadmap.json
                     alone (exit 2 if absent); under atdd_pure the flag is a no-op
                     and resolves to the same ledger-based verdict as FULL
                     (ADR-028 D4.2).
    """

    FULL = "full"
    ROADMAP_ONLY = "roadmap_only"


class LeftoverRoadmap(str, Enum):
    """Whether a leftover roadmap.json sits in an atdd_pure deliver project.

    ABSENT  -- the expected atdd_pure state: no roadmap.json at all.
    PRESENT -- a stale, schema-valid roadmap.json left over from a classic run.
               Under atdd_pure this is a WARNING, never an error (ADR-028 D4.2).
    """

    ABSENT = "absent"
    PRESENT = "present"


# Gherkin-phrase -> typed-value lookups. Keeping these as module-level dicts
# lets each step body stay a single typed lookup + a single composition call
# (Mandate-12 criterion 3: no control flow in step bodies).

CLASSIC_SHAPE_BY_PHRASE: dict[str, ClassicProjectShape] = {
    "complete traces": ClassicProjectShape.COMPLETE_TRACES,
    "incomplete traces": ClassicProjectShape.INCOMPLETE_TRACES,
}

VERDICT_BY_PHRASE: dict[str, IntegrityVerdict] = {
    "the feature verified": IntegrityVerdict.VERIFIED,
    "an integrity violation": IntegrityVerdict.VIOLATION,
}


# A kebab-case feature identifier (e.g. "atdd-pure-demo").
FeatureId = NewType("FeatureId", str)
