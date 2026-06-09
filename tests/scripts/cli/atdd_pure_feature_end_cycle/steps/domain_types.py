"""Domain types for the nw-deliver feature-end-cycle coherence slice.

slice-15 of the atdd-pure-roadmap-free-rollout (ADR-028 D6).

Mandate-12 criterion 1: every domain noun used in the Gherkin is expressed
once here as a typed enum / dataclass / NewType. Step bodies and the
composition service consume these typed parameters -- no raw ``str`` where a
domain enum exists.

WHY a coherence-test domain model and not a CLI domain model
------------------------------------------------------------
slice-15's only deliverable is the D6 feature-end-cycle *prose* added to
``nWave/skills/nw-deliver/SKILL.md`` -- a skill / orchestration prose file. It
ships NO CLI, NO ``main()``, NO exit code; ``master`` vs post-slice-15 differ
ONLY in markdown text. A behavioural / regression AT is structurally
impossible -- there is nothing to invoke. Per the refined H3 rule
(feature-delta ``[REF] Slice classes``) a slice whose entire deliverable is
``.md`` prose is Class P, gated by the executable coherence test.

WHY a SEPARATE test from slice-04's ``atdd_pure_nw_deliver_spine``
------------------------------------------------------------------
slice-04 (commit ``8d78f5c6c``) shipped the per-slice spine prose into the
SAME file and its own coherence test
(``tests/scripts/cli/atdd_pure_nw_deliver_spine/``) gates that per-slice
contract. slice-04's scope was frozen at its commit *before* the D6 refinement
was ratified (2026-05-20). slice-15 ships the feature-end-cycle prose -- a
named, separately-committed Class-P slice (feature-delta L915-952, follow-up
note HIGH-2/HIGH-3). This module therefore types ONLY the feature-end-cycle
clauses; it does NOT duplicate slice-04's per-slice-spine clauses. The one
PRESERVATION clause here is the cross-slice regression guard that slice-15's
edit does not DELETE slice-04's per-slice spine prose (Pillar 2: chained
narrative -- slice-15 builds on slice-04, never overwrites it).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType


# A repo-root-relative path to a skill / doc file under coherence audit.
RepoRelPath = NewType("RepoRelPath", str)


class ClauseKind(str, Enum):
    """Whether a feature-end-cycle clause is genuinely new in slice-15.

    NEW          -- the clause's prose is genuinely added by slice-15. The
                    contract carries a ``master_absent_substring`` VERIFIED
                    absent on master; the coherence AT FAILS on master and
                    PASSES once slice-15 lands (regression-AT contract).
    PRESERVATION -- the clause's prose was shipped by an earlier slice
                    (slice-04). The contract carries NO
                    ``master_absent_substring``; the AT is a regression GUARD
                    -- green on master by design -- that proves slice-15's edit
                    does not DELETE the inherited prose. It carries no
                    new-vs-master signal because there is no new-vs-master
                    delta to assert.
    """

    NEW = "new"
    PRESERVATION = "preservation"


class FeatureEndClause(str, Enum):
    """The D6 feature-end-cycle contract clauses for slice-15.

    Each clause is one half of the ADR-028 D6 ``nw-deliver`` feature-end cycle.
    The coherence test asserts every clause is present in
    ``nw-deliver/SKILL.md``. On master the SKILL.md describes the atdd_pure
    path only as a per-slice 7-phase ``A->G`` sequence (SKILL.md L107-128):
    ``E_BATCH_REFACTOR``, ``C_REVIEWER_AUDIT``, ``F_FINAL_REVIEW`` are listed
    as PER-SLICE phases in the A->G table -- master has NO once-per-feature
    feature-end cycle, NO collapsed deep review, NO ``FeatureEndCheckpoint``
    resume record. slice-15 adds exactly that prose.

    Clauses split into two kinds (see ``ClauseKind`` / ``FeatureEndContract``):

    FEATURE_END_CYCLE_DEFINED (NEW -- design note L930-934)
        Under atdd_pure, after the last slice's ``G_COMMIT``, ``/nw-deliver``
        runs ONE once-per-feature feature-end cycle: ``E_BATCH_REFACTOR``
        (L1-L6 whole-feature, batch-then-verify) run once, not per slice. The
        master-absent token is ``feature-end cycle`` (0 occurrences on master
        -- ``E_BATCH_REFACTOR`` itself IS on master, but only as a per-slice
        A->G phase; the once-per-feature *cycle* framing is genuinely new).
    DEEP_REVIEW_COLLAPSED (NEW -- design note L933-934)
        The feature-end cycle's deep adversarial review COLLAPSES
        ``C_REVIEWER_AUDIT`` + ``F_FINAL_REVIEW`` into one review of the
        coherent finished feature, followed by final integrity verification.
        The master-absent token is ``final integrity`` (0 occurrences on
        master). ``C_REVIEWER_AUDIT`` / ``F_FINAL_REVIEW`` are in
        present_substrings so a SKILL.md that names the cycle but never
        collapses the two reviews is still caught.
    FEATURE_END_CHECKPOINT (NEW -- design note L938-941, ADR-028 D6 L379-389)
        Each feature-end-cycle step boundary appends a
        ``"event": "FeatureEndCheckpoint"`` record to the AT-completion
        ledger; ``/nw-continue`` reads the latest ``FeatureEndCheckpoint`` and
        resumes the feature-end cycle at the recorded step when all slice-plan
        rows are ``shipped``. The master-absent token is
        ``FeatureEndCheckpoint`` (0 occurrences on master).
    PER_SLICE_SPINE_PRESERVED (PRESERVATION -- slice-04 cross-slice guard)
        slice-04 (commit ``8d78f5c6c``) shipped the per-slice spine prose --
        the ``ATDD-Pure Roadmap-Free Spine`` section and the per-slice A->G
        loop -- into the same file. slice-15 ADDS the feature-end-cycle prose
        ALONGSIDE it. This clause is the regression guard that slice-15's edit
        does not DELETE slice-04's per-slice spine. It is a PRESERVATION
        clause: green on master by design, NO master-absent token (a false
        "absent on master" claim is forbidden -- slice-04 review Blocking 1
        precedent).
    """

    FEATURE_END_CYCLE_DEFINED = "feature_end_cycle_defined"
    DEEP_REVIEW_COLLAPSED = "deep_review_collapsed"
    FEATURE_END_CHECKPOINT = "feature_end_checkpoint"
    PER_SLICE_SPINE_PRESERVED = "per_slice_spine_preserved"


@dataclass(frozen=True)
class FeatureEndContract:
    """A single coherence assertion over the nw-deliver SKILL.md content.

    ``clause`` names the slice-15 feature-end-cycle contract clause. ``kind``
    is NEW or PRESERVATION. ``present_substrings`` are domain tokens that MUST
    all appear in the file once slice-15 lands (for a PRESERVATION clause they
    are already present on master).

    ``master_absent_substring`` is one token VERIFIED absent on master,
    proving the clause is genuinely new -- the coherence AT FAILS on master
    and PASSES once slice-15 adds the prose. It is REQUIRED for
    ``kind == NEW`` and MUST be ``None`` for ``kind == PRESERVATION`` (a
    preservation clause has no honest new-vs-master delta to claim).
    ``__post_init__`` enforces this invariant so a false-absent claim cannot
    silently re-enter (slice-04 review Blocking 1 precedent).

    A FeatureEndContract carries no business logic; it is a typed record the
    composition service evaluates against the file content (Mandate-12).
    """

    clause: FeatureEndClause
    kind: ClauseKind
    present_substrings: tuple[str, ...]
    master_absent_substring: str | None

    def __post_init__(self) -> None:
        if self.kind is ClauseKind.NEW and self.master_absent_substring is None:
            raise ValueError(
                f"{self.clause.value}: a NEW clause must declare a "
                f"master_absent_substring (its regression-AT signal)"
            )
        if (
            self.kind is ClauseKind.PRESERVATION
            and self.master_absent_substring is not None
        ):
            raise ValueError(
                f"{self.clause.value}: a PRESERVATION clause must NOT declare a "
                f"master_absent_substring (it has no new-vs-master delta)"
            )
        if self.master_absent_substring is not None and (
            self.master_absent_substring not in self.present_substrings
        ):
            raise ValueError(
                f"{self.clause.value}: the master_absent_substring "
                f"'{self.master_absent_substring}' must also be one of the "
                f"present_substrings (the slice-15 prose adds it)"
            )


# The slice-15 feature-end-cycle contracts. The composition service
# (FeatureEndCoherenceComposition) evaluates each against nw-deliver/SKILL.md.
# Every NEW-kind master_absent_substring was verified 0 occurrences on master
# 2026-05-20 (`grep -cF <token> nWave/skills/nw-deliver/SKILL.md`):
#   "feature-end cycle"            -> 0
#   "final integrity"              -> 0
#   "FeatureEndCheckpoint"         -> 0
# The PRESERVATION clause's present tokens were verified PRESENT on master:
#   "ATDD-Pure Roadmap-Free Spine" -> present (SKILL.md L82 section heading)
#   "per-slice"                    -> 3 occurrences (slice-04 spine prose)
FEATURE_END_CONTRACTS: dict[FeatureEndClause, FeatureEndContract] = {
    # NEW -- verified master-absent: "feature-end cycle" (0 occurrences).
    # "E_BATCH_REFACTOR" IS on master (per-slice A->G table) -- co-located so
    # a SKILL.md naming the cycle without scoping it to E_BATCH_REFACTOR is
    # still caught. "after the last slice" anchors the once-per-feature timing.
    FeatureEndClause.FEATURE_END_CYCLE_DEFINED: FeatureEndContract(
        clause=FeatureEndClause.FEATURE_END_CYCLE_DEFINED,
        kind=ClauseKind.NEW,
        present_substrings=(
            "feature-end cycle",
            "after the last slice",
            "E_BATCH_REFACTOR",
        ),
        master_absent_substring="feature-end cycle",
    ),
    # NEW -- verified master-absent: "final integrity" (0 occurrences).
    # C_REVIEWER_AUDIT / F_FINAL_REVIEW ARE on master (per-slice A->G table) --
    # in present_substrings so a SKILL.md that names a feature-end review but
    # never collapses the two per-slice reviews is still caught.
    FeatureEndClause.DEEP_REVIEW_COLLAPSED: FeatureEndContract(
        clause=FeatureEndClause.DEEP_REVIEW_COLLAPSED,
        kind=ClauseKind.NEW,
        present_substrings=(
            "final integrity",
            "C_REVIEWER_AUDIT",
            "F_FINAL_REVIEW",
        ),
        master_absent_substring="final integrity",
    ),
    # NEW -- verified master-absent: "FeatureEndCheckpoint" (0 occurrences).
    # "feature-end-cycle checkpoint" anchors the /nw-continue resume-cue prose
    # (ADR-028 D6 L379-389); also 0 on master.
    FeatureEndClause.FEATURE_END_CHECKPOINT: FeatureEndContract(
        clause=FeatureEndClause.FEATURE_END_CHECKPOINT,
        kind=ClauseKind.NEW,
        present_substrings=(
            "FeatureEndCheckpoint",
            "feature-end-cycle checkpoint",
        ),
        master_absent_substring="FeatureEndCheckpoint",
    ),
    # PRESERVATION -- both tokens already on master (slice-04, commit
    # 8d78f5c6c). No master_absent_substring: there is no honest new-vs-master
    # delta. This clause guards that slice-15's edit does not DELETE slice-04's
    # per-slice spine prose (Pillar 2 cross-slice regression guard).
    FeatureEndClause.PER_SLICE_SPINE_PRESERVED: FeatureEndContract(
        clause=FeatureEndClause.PER_SLICE_SPINE_PRESERVED,
        kind=ClauseKind.PRESERVATION,
        present_substrings=(
            "ATDD-Pure Roadmap-Free Spine",
            "per-slice",
        ),
        master_absent_substring=None,
    ),
}


# Gherkin-phrase -> typed-value lookups. Module-level dicts keep each step body
# a single typed lookup + a single composition call (Mandate-12 criterion 3:
# no control flow in step bodies).

FEATURE_END_CLAUSE_BY_PHRASE: dict[str, FeatureEndClause] = {
    "defines a once-per-feature feature-end cycle after the last slice": (
        FeatureEndClause.FEATURE_END_CYCLE_DEFINED
    ),
    "collapses the deep review and runs final integrity verification": (
        FeatureEndClause.DEEP_REVIEW_COLLAPSED
    ),
    "records a feature-end-cycle checkpoint for /nw-continue resume": (
        FeatureEndClause.FEATURE_END_CHECKPOINT
    ),
    "preserves the slice-04 per-slice spine prose": (
        FeatureEndClause.PER_SLICE_SPINE_PRESERVED
    ),
}
