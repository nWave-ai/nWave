"""Domain types for the nw-bugfix mode-awareness coherence slice.

slice-05 of the atdd-pure-roadmap-free-rollout (ADR-028 D5; feature-delta
``### slice-05`` design note, L527-546).

Mandate-12 criterion 1: every domain noun used in the Gherkin is expressed once
here as a typed enum / dataclass / NewType. Step bodies and the composition
service consume these typed parameters -- no raw ``str`` where a domain enum
exists.

WHY a coherence-test domain model and not a CLI domain model
------------------------------------------------------------
slice-05's only deliverable is ``nWave/skills/nw-bugfix/SKILL.md`` -- a
skill/command *prose* file (it carries ``user-invocable: true`` frontmatter; it
is a slash-command instruction set an LLM interprets, not code with a callable
surface). It ships NO ``main()``, NO exit code; master vs post-slice differ
ONLY in markdown text. Per the refined H3 rule (feature-delta ``[REF] Slice
classes``, L224-262) a slice whose ENTIRE deliverable is ``.md`` prose is
Class P, gated by the executable coherence test -- NOT by ``@slice-NN``
behavioural ATs, because none can exist for prose (there is nothing to invoke).

This module types the contract clauses that coherence test asserts. It mirrors
the slice-04 precedent (``tests/scripts/cli/atdd_pure_nw_deliver_spine/``) and
extends it with a third clause kind -- ABSENCE -- because slice-05's change
includes REMOVING a stale phrase (``creates a minimal roadmap``), a contract
shape slice-04 did not have.

THREE clause kinds, one ``__post_init__`` invariant
---------------------------------------------------
- NEW          -- prose genuinely added by slice-05. Carries a
                  ``master_absent_substring`` VERIFIED absent on master; the
                  coherence AT FAILS on master, PASSES once slice-05 lands.
- ABSENCE      -- a stale phrase slice-05 REMOVES. Carries a
                  ``master_present_substring`` VERIFIED present on master; the
                  coherence AT FAILS on master (the phrase is still there) and
                  PASSES once slice-05 deletes it. The inverse of NEW.
- PRESERVATION -- prose already shipped, guarded against deletion. Carries
                  NEITHER master token; GREEN on master by design.

A NEW clause MUST declare ``master_absent_substring`` and MUST NOT declare
``master_present_substring``; an ABSENCE clause is the mirror; a PRESERVATION
clause declares neither. ``SliceClauseContract.__post_init__`` enforces this so
a false "absent on master" / "present on master" claim cannot silently
re-enter (the slice-04 review Blocking-1 false-RED defect).
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
    """Whether a bugfix-mode clause is new, removed, or merely guarded.

    NEW
        The clause's prose is genuinely added by slice-05. The contract carries
        a ``master_absent_substring`` VERIFIED absent on master; the coherence
        AT FAILS on master and PASSES once slice-05 lands (regression-AT
        contract -- the positive half).
    ABSENCE
        A stale phrase slice-05 must DELETE. The contract carries a
        ``master_present_substring`` VERIFIED present on master; the coherence
        AT FAILS on master (the stale phrase is still there) and PASSES once
        slice-05 removes it. The negative half -- the mirror of NEW. slice-05's
        design note (L542-544) names exactly one: the unconditional
        ``creates a minimal roadmap`` phrase, which under atdd_pure is wrong
        (an atdd_pure bugfix is one carpaccio slice, no roadmap).
    PRESERVATION
        The clause's prose was already shipped by an earlier change and slice-05
        must not delete it. The contract carries NEITHER master token; the AT is
        a regression GUARD -- green on master by design. It carries no
        new-vs-master signal because there is, honestly, no new-vs-master delta.
    """

    NEW = "new"
    ABSENCE = "absence"
    PRESERVATION = "preservation"


class BugfixClause(str, Enum):
    """The mode-conditional contract clauses for slice-05 ``nw-bugfix``.

    Per the slice-05 design note (feature-delta L527-546) the change is: Phase 3
    of ``nw-bugfix`` reads ``workflow.mode``; under ``atdd_pure`` a bugfix is the
    canonical SINGLE carpaccio slice (regression AT green -> fix -> commit) run
    via the slice-04 spine and the per-slice ``/nw-execute`` lean cycle -- it
    does NOT create a roadmap; under ``classic`` the existing roadmap-based flow
    is unchanged. The stale unconditional ``creates a minimal roadmap`` wording
    is removed.

    On master ``nw-bugfix/SKILL.md`` is mode-UNAWARE: Phase 3 always delegates
    to ``/nw-deliver`` which "creates a minimal roadmap with 2 steps"
    (SKILL.md L108) -- there is no ``workflow.mode`` branch, no ``atdd_pure``
    path, no ``carpaccio`` vocabulary, no ``/nw-execute`` per-slice cycle.

    Clauses split into the three ``ClauseKind`` values:

    PHASE_3_READS_WORKFLOW_MODE (NEW)
        Phase 3 reads ``workflow.mode`` and branches on it -- the classic vs
        atdd_pure dispatch decision. master Phase 3 is mode-unaware.
    ATDD_PURE_SINGLE_CARPACCIO_SLICE (NEW)
        Under ``atdd_pure`` a bugfix IS one canonical carpaccio slice -- the
        ``atdd_pure`` token plus the ``carpaccio slice`` framing. master has
        neither token.
    ATDD_PURE_RUNS_PER_SLICE_CYCLE (NEW)
        Under ``atdd_pure`` the bugfix slice runs via the slice-04 roadmap-free
        spine / the ``/nw-execute`` per-slice lean cycle -- NOT a roadmap
        extraction. The per-slice-cycle token is asserted explicitly so a
        SKILL.md that adds an ``atdd_pure`` branch but still routes it through
        roadmap-step extraction is still caught.
    CLASSIC_ROADMAP_PATH_PRESERVED (PRESERVATION)
        Under ``classic`` the existing roadmap-based bugfix path is preserved --
        the two-step regression-test / fix flow via ``/nw-deliver``. This prose
        is already on master (the whole current Phase 3); slice-05 makes it the
        ``classic`` branch but must not DELETE it. PRESERVATION: green on master
        by design, NO master token (a false "absent on master" claim is
        forbidden -- slice-04 review Blocking 1). NB: the master prose mentions
        a roadmap unconditionally; the post-slice prose mentions it scoped to
        ``classic``. The PRESERVATION present-substrings are chosen to be tokens
        true under BOTH framings (the regression-test / fix two-step shape),
        never the stale unconditional phrase the ABSENCE clause removes.
    STALE_UNCONDITIONAL_ROADMAP_REMOVED (ABSENCE)
        The unconditional ``creates a minimal roadmap`` phrase is REMOVED. On
        master it is present (SKILL.md L108); under atdd_pure it is wrong, so
        slice-05 deletes it (the design note's ``absent_regex`` contract,
        L543-544). The mirror of the NEW clauses: FAILS on master because the
        stale phrase is still there, PASSES once it is gone.
    """

    PHASE_3_READS_WORKFLOW_MODE = "phase_3_reads_workflow_mode"
    ATDD_PURE_SINGLE_CARPACCIO_SLICE = "atdd_pure_single_carpaccio_slice"
    ATDD_PURE_RUNS_PER_SLICE_CYCLE = "atdd_pure_runs_per_slice_cycle"
    CLASSIC_ROADMAP_PATH_PRESERVED = "classic_roadmap_path_preserved"
    STALE_UNCONDITIONAL_ROADMAP_REMOVED = "stale_unconditional_roadmap_removed"


@dataclass(frozen=True)
class SliceClauseContract:
    """A single coherence assertion over the nw-bugfix SKILL.md content.

    ``clause`` names the slice-05 contract clause. ``kind`` is NEW, ABSENCE or
    PRESERVATION.

    ``present_substrings`` are domain tokens that MUST all appear in the file
    once slice-05 lands. For a NEW or PRESERVATION clause they are the positive
    contract. For an ABSENCE clause this tuple is empty -- an ABSENCE clause
    asserts a removal, not a presence.

    ``master_absent_substring`` is one token VERIFIED absent on master, proving
    a NEW clause is genuinely new -- the AT FAILS on master, PASSES once slice-05
    adds the prose. REQUIRED for ``kind == NEW``, MUST be ``None`` otherwise.

    ``master_present_substring`` is one token VERIFIED present on master that
    slice-05 must DELETE, proving an ABSENCE clause is a genuine removal -- the
    AT FAILS on master (the stale phrase is still there), PASSES once it is
    gone. REQUIRED for ``kind == ABSENCE``, MUST be ``None`` otherwise. It is
    also the ``forbidden_substring`` the post-slice file must NOT contain.

    ``__post_init__`` enforces the kind/token invariant so a false-RED claim
    (slice-04 review Blocking 1) cannot silently re-enter.

    A SliceClauseContract carries no business logic; it is a typed record the
    composition service evaluates against the file content (Mandate-12).
    """

    clause: BugfixClause
    kind: ClauseKind
    present_substrings: tuple[str, ...]
    master_absent_substring: str | None
    master_present_substring: str | None

    def __post_init__(self) -> None:
        if self.kind is ClauseKind.NEW:
            if self.master_absent_substring is None:
                raise ValueError(
                    f"{self.clause.value}: a NEW clause must declare a "
                    f"master_absent_substring (its regression-AT signal)"
                )
            if self.master_present_substring is not None:
                raise ValueError(
                    f"{self.clause.value}: a NEW clause must NOT declare a "
                    f"master_present_substring (that is the ABSENCE signal)"
                )
            if not self.present_substrings:
                raise ValueError(
                    f"{self.clause.value}: a NEW clause must declare at least "
                    f"one present_substring (its positive contract)"
                )
        elif self.kind is ClauseKind.ABSENCE:
            if self.master_present_substring is None:
                raise ValueError(
                    f"{self.clause.value}: an ABSENCE clause must declare a "
                    f"master_present_substring (the stale phrase it removes)"
                )
            if self.master_absent_substring is not None:
                raise ValueError(
                    f"{self.clause.value}: an ABSENCE clause must NOT declare a "
                    f"master_absent_substring (that is the NEW signal)"
                )
            if self.present_substrings:
                raise ValueError(
                    f"{self.clause.value}: an ABSENCE clause asserts a removal "
                    f"and must NOT declare present_substrings"
                )
        else:  # PRESERVATION
            if self.master_absent_substring is not None:
                raise ValueError(
                    f"{self.clause.value}: a PRESERVATION clause must NOT "
                    f"declare a master_absent_substring (no new-vs-master delta)"
                )
            if self.master_present_substring is not None:
                raise ValueError(
                    f"{self.clause.value}: a PRESERVATION clause must NOT "
                    f"declare a master_present_substring (it removes nothing)"
                )
            if not self.present_substrings:
                raise ValueError(
                    f"{self.clause.value}: a PRESERVATION clause must declare "
                    f"the present_substrings it guards against deletion"
                )


# The slice-05 bugfix-mode contracts. The composition service
# (BugfixModeCoherenceComposition) evaluates each against nw-bugfix/SKILL.md.
#
# Every master token below was verified on master 2026-05-20 against
# nWave/skills/nw-bugfix/SKILL.md (164 lines):
#   NEW master_absent_substring  -> grep -F -c <token> => 0 occurrences
#     "workflow.mode"      -> 0
#     "atdd_pure"          -> 0
#     "/nw-execute"        -> 0
#   ABSENCE master_present_substring -> grep -F -c <token> => >=1 occurrence
#     "creates a minimal roadmap" -> 1 (SKILL.md L108)
SLICE_05_CONTRACTS: dict[BugfixClause, SliceClauseContract] = {
    # NEW -- verified master-absent: "workflow.mode" (0 occurrences).
    BugfixClause.PHASE_3_READS_WORKFLOW_MODE: SliceClauseContract(
        clause=BugfixClause.PHASE_3_READS_WORKFLOW_MODE,
        kind=ClauseKind.NEW,
        present_substrings=("workflow.mode",),
        master_absent_substring="workflow.mode",
        master_present_substring=None,
    ),
    # NEW -- verified master-absent: "atdd_pure" (0 occurrences). The
    # "carpaccio slice" token is in present_substrings (also 0 on master) so a
    # SKILL.md that adds the atdd_pure token but never names the carpaccio-slice
    # framing is still caught.
    BugfixClause.ATDD_PURE_SINGLE_CARPACCIO_SLICE: SliceClauseContract(
        clause=BugfixClause.ATDD_PURE_SINGLE_CARPACCIO_SLICE,
        kind=ClauseKind.NEW,
        present_substrings=("atdd_pure", "carpaccio slice"),
        master_absent_substring="atdd_pure",
        master_present_substring=None,
    ),
    # NEW -- verified master-absent: "/nw-execute" (0 occurrences). The
    # per-slice-cycle token is the master-absent signal so a SKILL.md that adds
    # an atdd_pure branch but still routes it through roadmap-step extraction
    # (no per-slice /nw-execute cycle) is still caught.
    BugfixClause.ATDD_PURE_RUNS_PER_SLICE_CYCLE: SliceClauseContract(
        clause=BugfixClause.ATDD_PURE_RUNS_PER_SLICE_CYCLE,
        kind=ClauseKind.NEW,
        present_substrings=("/nw-execute", "per-slice"),
        master_absent_substring="/nw-execute",
        master_present_substring=None,
    ),
    # PRESERVATION -- the classic two-step regression-test/fix flow. Both
    # tokens are already on master (the current mode-unaware Phase 3). They are
    # chosen to be true under BOTH the master unconditional framing AND the
    # post-slice classic-scoped framing -- they are NOT the stale phrase the
    # ABSENCE clause removes. No master token: no honest new-vs-master delta.
    BugfixClause.CLASSIC_ROADMAP_PATH_PRESERVED: SliceClauseContract(
        clause=BugfixClause.CLASSIC_ROADMAP_PATH_PRESERVED,
        kind=ClauseKind.PRESERVATION,
        present_substrings=("Regression test (RED)", "Fix implementation (GREEN)"),
        master_absent_substring=None,
        master_present_substring=None,
    ),
    # ABSENCE -- verified master-PRESENT: "creates a minimal roadmap"
    # (1 occurrence, SKILL.md L108). slice-05 removes the unconditional phrase
    # (design note absent_regex, L543-544). FAILS on master (still there),
    # PASSES once slice-05 deletes it.
    BugfixClause.STALE_UNCONDITIONAL_ROADMAP_REMOVED: SliceClauseContract(
        clause=BugfixClause.STALE_UNCONDITIONAL_ROADMAP_REMOVED,
        kind=ClauseKind.ABSENCE,
        present_substrings=(),
        master_absent_substring=None,
        master_present_substring="creates a minimal roadmap",
    ),
}


# Gherkin-phrase -> typed-value lookups. Module-level dicts keep each step body
# a single typed lookup + a single composition call (Mandate-12 criterion 3:
# no control flow in step bodies).

BUGFIX_CLAUSE_BY_PHRASE: dict[str, BugfixClause] = {
    "reads the workflow mode in Phase 3": (BugfixClause.PHASE_3_READS_WORKFLOW_MODE),
    "treats an atdd_pure bugfix as a single carpaccio slice": (
        BugfixClause.ATDD_PURE_SINGLE_CARPACCIO_SLICE
    ),
    "runs the atdd_pure bugfix through the per-slice cycle": (
        BugfixClause.ATDD_PURE_RUNS_PER_SLICE_CYCLE
    ),
    "preserves the classic roadmap-based bugfix path": (
        BugfixClause.CLASSIC_ROADMAP_PATH_PRESERVED
    ),
    "no longer unconditionally creates a roadmap": (
        BugfixClause.STALE_UNCONDITIONAL_ROADMAP_REMOVED
    ),
}

WORKFLOW_MODE_BY_PHRASE: dict[str, WorkflowMode] = {
    "atdd_pure": WorkflowMode.ATDD_PURE,
    "classic": WorkflowMode.CLASSIC,
}
