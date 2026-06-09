"""Domain types for the nw-deliver spine-branch coherence slice.

slice-04 of the atdd-pure-roadmap-free-rollout (ADR-028 D5).

Mandate-12 criterion 1: every domain noun used in the Gherkin is expressed
once here as a typed enum / dataclass / NewType. Step bodies and the
composition service consume these typed parameters -- no raw ``str`` where a
domain enum exists.

WHY a coherence-test domain model and not a CLI domain model
------------------------------------------------------------
slice-04's only deliverable is ``nWave/skills/nw-deliver/SKILL.md`` -- a
skill/prose orchestration file. It ships NO CLI, NO ``main()``, NO exit code.
The slice-04 design note's declared ATs (no roadmap.json/execution-log.json
under atdd_pure; carpaccio gate invoked; classic byte-for-byte unchanged;
Phase 6 ledger verification; Class-P routing) are all outcomes of *an LLM
interpreting the SKILL.md prose at runtime* -- there is no deterministic
runtime that "runs ``/nw-deliver``".

The only mechanically-checkable, master-fails / slice-04-passes surface is
therefore the SKILL.md *content itself*: a permanent executable coherence test
(the Class-P mechanism the rollout's own ``[REF] Slice classes`` section
specifies for files whose contract is a semantic role -- feature-delta L160-163,
slice-10 precedent L621-671). This module types the contract clauses that test
asserts. See the WAVE: DISTILL finding in the acceptance brief: slice-04 is
Class-mislabelled C and is genuinely Class P.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType


# A repo-root-relative path to a skill / doc file under coherence audit.
RepoRelPath = NewType("RepoRelPath", str)


class WorkflowMode(str, Enum):
    """The project's DELIVER execution mode (``.nwave/config.yaml:workflow.mode``).

    CLASSIC    -- the ADR-025 roadmap-based DELIVER spine (default).
    ATDD_PURE  -- the ADR-028 roadmap-free, execution-log-free sibling spine.
    """

    CLASSIC = "classic"
    ATDD_PURE = "atdd_pure"


class ClauseKind(str, Enum):
    """Whether a spine-branch clause is genuinely new in slice-04 or inherited.

    NEW          -- the clause's prose is genuinely added by slice-04. The
                    contract carries a ``master_absent_substring`` that is
                    VERIFIED absent on master; the coherence AT FAILS on master
                    and PASSES once slice-04 lands (regression-AT contract).
    PRESERVATION -- the clause's prose was already shipped by an earlier slice.
                    The contract carries NO ``master_absent_substring``; the AT
                    is a regression GUARD -- green on master by design -- that
                    proves slice-04's spine rewrite does not DELETE the
                    inherited prose. It carries no new-vs-master signal because
                    there is, honestly, no new-vs-master delta to assert.
    """

    NEW = "new"
    PRESERVATION = "preservation"


class SpineClause(str, Enum):
    """The mode-conditional spine-branch contract clauses for slice-04.

    Each clause is one half of the ADR-028 D5 ``nw-deliver`` spine branch. The
    coherence test asserts every clause is present in ``nw-deliver/SKILL.md``
    with the correct mode scoping. On master the SKILL.md describes the
    atdd_pure path only as an inner 7-phase A->G *replacement* of the classic
    per-step cycle (L78: "the classic 3-phase per-step dispatch ... is
    REPLACED") -- it does NOT branch the WHOLE spine, does NOT skip Phase 1
    Roadmap, does NOT provision the telemetry directory in place of
    des-init-log, and Phase 6 still reads "Roadmap integrity verification".

    Clauses split into two kinds (see ``ClauseKind`` / ``SpineContract.kind``):

    SKIP_ROADMAP_AND_LOG (NEW -- AT a)
        Under atdd_pure the spine creates NO roadmap.json and NO
        execution-log.json -- step 1.a (des-init-log) and Phase 1 (Roadmap
        Creation + Review) are SKIPPED, not run-then-discarded.
    CARPACCIO_GATE_REPLACES_PHASE_1 (NEW -- AT b)
        Under atdd_pure the carpaccio slice gate runs as the per-slice
        entry_gate IN PLACE OF Phase 1 roadmap creation, before the first
        A_GREEN_ATS dispatch, AND the spine runs the per-slice
        DISTILL->DELIVER A->G loop -- one A->G pass per slice -- in place of
        the single whole-feature roadmap-step extraction. The per-slice loop
        substring is asserted explicitly so a SKILL.md that swaps the gate but
        keeps the whole-feature step loop is still caught.
    CLASSIC_SPINE_UNCHANGED (NEW -- AT c)
        The classic spine is preserved as a sibling top-level workflow --
        byte-for-byte unchanged, explicitly named so the orchestrator cannot
        fall through from the atdd_pure path into roadmap creation.
    PHASE_6_LEDGER_VERIFICATION (NEW -- D5 / feature-delta L362)
        Under atdd_pure, Phase 6 "Deliver Integrity Verification" verifies the
        AT-completion ledger + slice-plan (all rows shipped) + commit-trailer
        chain -- NOT roadmap/execution-log integrity. A spine rewrite that
        leaves Phase 6 saying only "roadmap integrity verification" is a
        half-implemented branch this clause catches.
    CLASS_P_SKIPS_CARPACCIO_GATE (PRESERVATION -- AT d, reframed)
        A ``Class = P`` slice does NOT invoke the carpaccio entry_gate -- the
        spine reads the slice plan's Class column and runs the coherence check
        instead. This routing prose was ALREADY shipped by slice-03
        (``nw-deliver/SKILL.md`` L92, the carpaccio entry_gate note, which
        forward-references slice-04 spine routing). slice-04 rewrites the
        surrounding spine into sibling workflows; this clause is the
        regression guard that the rewrite PRESERVES the inherited routing. It
        is a PRESERVATION clause: green on master by design, NO master-absent
        token (a false "absent on master" claim is forbidden -- review
        Blocking 1).
    """

    SKIP_ROADMAP_AND_LOG = "skip_roadmap_and_log"
    CARPACCIO_GATE_REPLACES_PHASE_1 = "carpaccio_gate_replaces_phase_1"
    CLASSIC_SPINE_UNCHANGED = "classic_spine_unchanged"
    PHASE_6_LEDGER_VERIFICATION = "phase_6_ledger_verification"
    CLASS_P_SKIPS_CARPACCIO_GATE = "class_p_skips_carpaccio_gate"


class SetupProvision(str, Enum):
    """What the atdd_pure spine's Setup phase provisions in place of a log.

    TELEMETRY_LEDGER_DIR
        ``.nwave/telemetry/atdd-pure/`` -- the AT-completion ledger tree
        (ADR-028 D3), created with ``mkdir -p`` in place of the skipped
        des-init-log step.
    """

    TELEMETRY_LEDGER_DIR = "telemetry_ledger_dir"


@dataclass(frozen=True)
class SpineContract:
    """A single coherence assertion over the nw-deliver SKILL.md content.

    ``clause`` names the slice-04 contract clause. ``kind`` is NEW or
    PRESERVATION. ``present_substrings`` are domain tokens that MUST all appear
    in the file once slice-04 lands (for a PRESERVATION clause, they are
    already present on master).

    ``master_absent_substring`` is one token VERIFIED absent on master, proving
    the clause is genuinely new -- the coherence AT FAILS on master and PASSES
    once slice-04 adds the prose. It is REQUIRED for ``kind == NEW`` and MUST be
    ``None`` for ``kind == PRESERVATION`` (a preservation clause has no honest
    new-vs-master delta to claim). ``__post_init__`` enforces this invariant so
    a future false-absent claim (review Blocking 1) cannot silently re-enter.

    A SpineContract carries no business logic; it is a typed record the
    composition service evaluates against the file content (Mandate-12).
    """

    clause: SpineClause
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


# The slice-04 spine-branch contracts. The composition service
# (SpineCoherenceComposition) evaluates each against nw-deliver/SKILL.md.
# Every NEW-kind master_absent_substring was verified 0 occurrences on master
# 2026-05-20 (`grep -c <token> nWave/skills/nw-deliver/SKILL.md`).
SPINE_CONTRACTS: dict[SpineClause, SpineContract] = {
    # AT a -- verified master-absent: "no roadmap.json" (0 occurrences).
    SpineClause.SKIP_ROADMAP_AND_LOG: SpineContract(
        clause=SpineClause.SKIP_ROADMAP_AND_LOG,
        kind=ClauseKind.NEW,
        present_substrings=(
            "no roadmap.json",
            "no execution-log.json",
        ),
        master_absent_substring="no roadmap.json",
    ),
    # AT b -- verified master-absent: "in place of Phase 1" (0) and "per-slice"
    # (0). The per-slice loop token is in present_substrings so a SKILL.md that
    # swaps the gate but keeps the whole-feature step loop is still caught
    # (review Blocking 3). "in place of Phase 1" is the master-absent signal.
    SpineClause.CARPACCIO_GATE_REPLACES_PHASE_1: SpineContract(
        clause=SpineClause.CARPACCIO_GATE_REPLACES_PHASE_1,
        kind=ClauseKind.NEW,
        present_substrings=(
            "carpaccio",
            "in place of Phase 1",
            "per-slice",
        ),
        master_absent_substring="in place of Phase 1",
    ),
    # AT c -- verified master-absent: "sibling top-level workflow" (0).
    SpineClause.CLASSIC_SPINE_UNCHANGED: SpineContract(
        clause=SpineClause.CLASSIC_SPINE_UNCHANGED,
        kind=ClauseKind.NEW,
        present_substrings=(
            "sibling top-level workflow",
            "byte-for-byte unchanged",
        ),
        master_absent_substring="sibling top-level workflow",
    ),
    # D5 / feature-delta L362 -- verified master-absent: "ledger" (0),
    # "trailer chain" (0). On master Phase 6 reads "roadmap integrity
    # verification" only. "ledger" is the master-absent signal.
    SpineClause.PHASE_6_LEDGER_VERIFICATION: SpineContract(
        clause=SpineClause.PHASE_6_LEDGER_VERIFICATION,
        kind=ClauseKind.NEW,
        present_substrings=(
            "ledger",
            "slice-plan",
            "trailer chain",
        ),
        master_absent_substring="ledger",
    ),
    # AT d, reframed -- PRESERVATION. "Class = P" and "coherence check" are
    # BOTH already on master (nw-deliver/SKILL.md L92, shipped by slice-03).
    # No master_absent_substring: there is no honest new-vs-master delta. This
    # clause guards that slice-04's spine rewrite does not DELETE the routing.
    SpineClause.CLASS_P_SKIPS_CARPACCIO_GATE: SpineContract(
        clause=SpineClause.CLASS_P_SKIPS_CARPACCIO_GATE,
        kind=ClauseKind.PRESERVATION,
        present_substrings=(
            "Class = P",
            "coherence check",
        ),
        master_absent_substring=None,
    ),
}


# Gherkin-phrase -> typed-value lookups. Module-level dicts keep each step body
# a single typed lookup + a single composition call (Mandate-12 criterion 3:
# no control flow in step bodies).

SPINE_CLAUSE_BY_PHRASE: dict[str, SpineClause] = {
    "skips roadmap and execution-log creation": SpineClause.SKIP_ROADMAP_AND_LOG,
    "runs the carpaccio gate in place of roadmap creation": (
        SpineClause.CARPACCIO_GATE_REPLACES_PHASE_1
    ),
    "preserves the classic spine unchanged": SpineClause.CLASSIC_SPINE_UNCHANGED,
    "verifies the ledger and slice-plan and trailers at Phase 6": (
        SpineClause.PHASE_6_LEDGER_VERIFICATION
    ),
    "skips the carpaccio gate for a prose-coherence slice": (
        SpineClause.CLASS_P_SKIPS_CARPACCIO_GATE
    ),
}

WORKFLOW_MODE_BY_PHRASE: dict[str, WorkflowMode] = {
    "atdd_pure": WorkflowMode.ATDD_PURE,
    "classic": WorkflowMode.CLASSIC,
}
