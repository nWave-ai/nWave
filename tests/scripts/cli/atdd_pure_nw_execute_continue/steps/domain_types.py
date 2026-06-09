"""Domain types for the nw-execute / nw-continue mode-coherence slice.

slice-08 of the atdd-pure-roadmap-free-rollout (ADR-028 D6; feature-delta
``### slice-08`` design note, L685-725).

Mandate-12 criterion 1: every domain noun used in the Gherkin is expressed once
here as a typed enum / dataclass / NewType. Step bodies and the composition
service consume these typed parameters -- no raw ``str`` where a domain enum
exists.

WHY a coherence-test domain model and not a CLI domain model
------------------------------------------------------------
slice-08's four deliverables are all ``.md`` -- two skill ``SKILL.md`` files
(``nw-execute``, ``nw-continue``) plus two command ``task`` docs
(``nw/execute.md``, ``nw/continue.md``). None ships a ``main()``, an exit code,
or a callable surface; master vs post-slice differ ONLY in markdown text. The
executable mechanics the prose describes (per-slice A->G dispatch, the
AT-completion ledger, the carpaccio gate) are shipped by the Class-C slices
01-03/14, NOT here. Per the refined H3 rule (feature-delta ``[REF] Slice
classes``, L224-262) a slice whose ENTIRE deliverable is ``.md`` prose is
Class P, gated by the executable coherence test -- NOT by ``@slice-NN``
behavioural ATs, because none can exist for prose (there is nothing to invoke).
The feature-delta already types slice-08 as Class P (slice plan row L38, H3
re-audit row L277).

This module types the contract clauses the coherence test asserts. It mirrors
the slice-04/slice-05 precedents
(``tests/scripts/cli/atdd_pure_nw_deliver_spine/``,
``tests/scripts/cli/atdd_pure_nw_bugfix_mode/``) and extends them with a fourth
clause kind -- MODE_SCOPED -- because slice-08's design-note gate has a
*per-line semantic-role* predicate the bare NEW/ABSENCE/PRESERVATION token model
cannot express: every line mentioning ``roadmap.json`` / ``execution-log`` must
co-occur with a ``classic`` / ``workflow.mode`` qualifier (the slice-10
semantic-role-predicate pattern -- feature-delta L777-783).

FOUR clause kinds, one ``__post_init__`` invariant
--------------------------------------------------
- NEW          -- prose genuinely added by slice-08. Carries a
                  ``master_absent_substring`` VERIFIED absent on master; the
                  coherence AT FAILS on master, PASSES once slice-08 lands.
- ABSENCE      -- a stale phrase slice-08 REMOVES. Carries a
                  ``master_present_substring`` VERIFIED present on master; the
                  coherence AT FAILS on master and PASSES once it is gone.
                  (slice-08 declares no ABSENCE clause -- the kind is carried
                  for model parity with slice-05 and ``__post_init__`` coverage;
                  see the SLICE_08_CONTRACTS comment.)
- PRESERVATION -- prose already shipped, guarded against deletion. Carries
                  NEITHER master token; GREEN on master by design.
- MODE_SCOPED  -- a token that is LEGITIMATE under ``classic`` but on master
                  appears UNQUALIFIED (no ``classic`` / ``workflow.mode``
                  co-occurrence on its line) -- the stale "roadmap/log is
                  unconditional" framing. Carries a ``master_present_substring``
                  (the audited token, VERIFIED present-and-unscoped on master).
                  The contract is NOT "remove the token" (a bare ``absent``
                  regex would wrongly forbid the legitimate classic-mode
                  reference -- feature-delta L778-781) but "every line carrying
                  the token also carries a qualifier from
                  ``MODE_QUALIFIER_TOKENS``". FAILS on master (lines unscoped),
                  PASSES once slice-08 mode-scopes every line.

A NEW clause MUST declare ``master_absent_substring`` and MUST NOT declare
``master_present_substring``; an ABSENCE clause is the mirror; a MODE_SCOPED
clause declares ``master_present_substring`` (like ABSENCE) but, unlike ABSENCE,
the token is NOT removed -- it is qualified; a PRESERVATION clause declares
neither. ``SliceClauseContract.__post_init__`` enforces this so a false
"absent on master" / "present on master" claim cannot silently re-enter (the
slice-04 review Blocking-1 false-RED defect).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType


# A repo-root-relative path to a skill / command-doc file under coherence audit.
RepoRelPath = NewType("RepoRelPath", str)


class WorkflowMode(str, Enum):
    """The project's DELIVER execution mode (``.nwave/config.yaml:workflow.mode``).

    CLASSIC    -- the ADR-025 roadmap-based DELIVER spine (default).
    ATDD_PURE  -- the ADR-028 roadmap-free, execution-log-free sibling spine.
    """

    CLASSIC = "classic"
    ATDD_PURE = "atdd_pure"


class OrchestrationDoc(str, Enum):
    """The four slice-08 deliverable files, typed.

    Two skill ``SKILL.md`` files and two command ``task`` docs. The coherence
    test's composition service maps each to its repo-root-relative path.

    NW_EXECUTE_SKILL   -- ``nWave/skills/nw-execute/SKILL.md``
    NW_CONTINUE_SKILL  -- ``nWave/skills/nw-continue/SKILL.md``
    NW_EXECUTE_TASK    -- ``nWave/tasks/nw/execute.md``
    NW_CONTINUE_TASK   -- ``nWave/tasks/nw/continue.md``
    """

    NW_EXECUTE_SKILL = "nw_execute_skill"
    NW_CONTINUE_SKILL = "nw_continue_skill"
    NW_EXECUTE_TASK = "nw_execute_task"
    NW_CONTINUE_TASK = "nw_continue_task"


class ClauseKind(str, Enum):
    """Whether a slice-08 clause is new, removed, mode-scoped, or merely guarded.

    NEW
        The clause's prose is genuinely added by slice-08. The contract carries
        a ``master_absent_substring`` VERIFIED absent on master; the coherence
        AT FAILS on master and PASSES once slice-08 lands (regression-AT
        contract -- the positive half).
    ABSENCE
        A stale phrase slice-08 must DELETE. The contract carries a
        ``master_present_substring`` VERIFIED present on master; the AT FAILS
        on master and PASSES once the phrase is gone. The negative half --
        the mirror of NEW. slice-08 declares no ABSENCE clause (its stale
        framing is addressed by qualification, not deletion -- see MODE_SCOPED);
        the kind is kept for model parity with the slice-05 precedent.
    PRESERVATION
        The clause's prose was already shipped and slice-08 must not delete it.
        The contract carries NEITHER master token; the AT is a regression GUARD
        -- green on master by design.
    MODE_SCOPED
        A token LEGITIMATE under ``classic`` that on master appears UNQUALIFIED.
        The contract carries ``master_present_substring`` (the audited token,
        VERIFIED present-and-unscoped on master). The post-slice contract is:
        every line carrying the token also carries a qualifier from
        ``MODE_QUALIFIER_TOKENS``. FAILS on master (lines unscoped), PASSES
        once slice-08 mode-scopes every line. NOT a removal -- the classic
        reference stays, it is merely qualified.
    """

    NEW = "new"
    ABSENCE = "absence"
    PRESERVATION = "preservation"
    MODE_SCOPED = "mode_scoped"


# The qualifier tokens that, present on the SAME line as an audited MODE_SCOPED
# token, mark that line as mode-scoped (not the stale unconditional framing).
# Per the slice-08 design note (feature-delta L721-722): "every roadmap /
# execution-log mention co-occurs with a classic / workflow.mode qualifier".
MODE_QUALIFIER_TOKENS: tuple[str, ...] = ("classic", "workflow.mode")


class ExecuteClause(str, Enum):
    """The mode-conditional contract clauses for the slice-08 ``nw-execute`` pair.

    Per the slice-08 design note (feature-delta L685-725) the change is:
    ``/nw-execute`` is redefined as the ADR-028 D6 **per-slice lean cycle** --
    under ``atdd_pure`` it executes ONE carpaccio slice (carpaccio entry gate +
    ``A_GREEN_ATS`` + ``B_COVERAGE_CLEANUP`` + light slice review + terminating
    contract-gate run + ``G_COMMIT`` + ``G_COMMIT`` exit gate). It no longer
    extracts roadmap steps under ``atdd_pure``. ``E_BATCH_REFACTOR`` and the
    deep review are explicitly NOT in ``/nw-execute``.

    On master ``nw-execute/SKILL.md`` and ``nw/execute.md`` are mode-UNAWARE:
    both "Dispatch a single roadmap step", require ``roadmap.json`` +
    ``execution-log.json`` as context files, and mention ``roadmap.json`` /
    ``execution-log`` on many lines WITHOUT any ``classic`` / ``workflow.mode``
    qualifier (verified 0 qualifier occurrences on master 2026-05-20). There is
    no ``workflow.mode`` branch, no ``atdd_pure`` path, no ``carpaccio``
    vocabulary, no ``per-slice lean cycle``, no ``A_GREEN_ATS``.

    The design-note gate for the execute pair (feature-delta L719-721):
      PRESENT  -- ``nw-execute`` / ``execute.md`` name the per-slice lean cycle
                  (tokens ``atdd_pure`` + ``per-slice lean cycle`` +
                  ``A_GREEN_ATS``).
      MODE-SCOPED -- every ``roadmap`` / ``execution-log`` mention co-occurs
                  with a ``classic`` / ``workflow.mode`` qualifier.

    Clauses:

    READS_WORKFLOW_MODE (NEW)
        ``/nw-execute`` reads ``workflow.mode`` and branches on it. master is
        mode-unaware. master-absent token: ``workflow.mode``.
    ATDD_PURE_PER_SLICE_LEAN_CYCLE (NEW)
        Under ``atdd_pure`` ``/nw-execute`` IS the per-slice lean cycle -- the
        ``atdd_pure`` token plus the ``per-slice lean cycle`` framing.
        master-absent token: ``per-slice lean cycle``.
    ATDD_PURE_RUNS_A_GREEN_ATS (NEW)
        Under ``atdd_pure`` the slice cycle runs the carpaccio entry gate and
        ``A_GREEN_ATS`` -- NOT roadmap-step extraction. The ``A_GREEN_ATS`` +
        ``carpaccio`` tokens are asserted explicitly so a doc that adds an
        ``atdd_pure`` branch but still routes it through roadmap-step extraction
        is still caught. master-absent token: ``A_GREEN_ATS``.
    ROADMAP_REFERENCES_MODE_SCOPED (MODE_SCOPED)
        Every line mentioning ``roadmap.json`` co-occurs with a ``classic`` /
        ``workflow.mode`` qualifier. On master roadmap.json lines are
        unqualified -- the stale "roadmap is unconditional" framing.
        master-present (unscoped) token: ``roadmap.json``.
    EXECUTION_LOG_REFERENCES_MODE_SCOPED (MODE_SCOPED)
        Every line mentioning ``execution-log`` co-occurs with a ``classic`` /
        ``workflow.mode`` qualifier. On master execution-log lines are
        unqualified. master-present (unscoped) token: ``execution-log``.
    """

    READS_WORKFLOW_MODE = "reads_workflow_mode"
    ATDD_PURE_PER_SLICE_LEAN_CYCLE = "atdd_pure_per_slice_lean_cycle"
    ATDD_PURE_RUNS_A_GREEN_ATS = "atdd_pure_runs_a_green_ats"
    ROADMAP_REFERENCES_MODE_SCOPED = "roadmap_references_mode_scoped"
    EXECUTION_LOG_REFERENCES_MODE_SCOPED = "execution_log_references_mode_scoped"


class ContinueClause(str, Enum):
    """The mode-conditional contract clauses for the slice-08 ``nw-continue`` pair.

    Per the slice-08 design note (feature-delta L707-723) the change is:
    ``/nw-continue`` under ``atdd_pure`` resumes a ``/nw-deliver`` run with the
    **two-case cue** (ADR-028 D6): (i) slices still ``pending`` -> restart the
    ``/nw-execute`` loop at the first un-``shipped`` slice; (ii) all slices
    ``shipped`` but the feature-end cycle did not finish -> read the latest
    ``FeatureEndCheckpoint`` ledger record and resume the feature-end cycle at
    the recorded step.

    On master ``nw-continue/SKILL.md`` and ``nw/continue.md`` are mode-UNAWARE:
    Step 5 "DELIVER Progress Detail" reads ``execution-log.json`` to count
    COMMIT/PASS steps -- it does NOT read ``workflow.mode``, name an
    ``atdd_pure`` path, mention the slice plan, an un-``shipped`` slice, or a
    ``FeatureEndCheckpoint``. Verified 0 occurrences on master 2026-05-20 for
    every NEW token; ``execution-log`` appears unqualified (no ``classic`` /
    ``workflow.mode`` co-occurrence).

    The design-note gate for the continue pair (feature-delta L720-722):
      PRESENT  -- ``nw-continue`` / ``continue.md`` name BOTH resume cases
                  (tokens ``atdd_pure`` + ``un-shipped slice`` +
                  ``FeatureEndCheckpoint``).
      MODE-SCOPED -- every ``roadmap`` / ``execution-log`` mention co-occurs
                  with a ``classic`` / ``workflow.mode`` qualifier.

    Clauses:

    READS_WORKFLOW_MODE (NEW)
        ``/nw-continue`` reads ``workflow.mode`` and branches on it. master is
        mode-unaware. master-absent token: ``workflow.mode``.
    ATDD_PURE_RESUMES_UN_SHIPPED_SLICE (NEW)
        Resume case (i): under ``atdd_pure`` with slices still ``pending``,
        ``/nw-continue`` restarts the ``/nw-execute`` loop at the first
        un-``shipped`` slice -- the ``atdd_pure`` token plus the
        ``un-shipped slice`` framing. master-absent token: ``un-shipped slice``.
    ATDD_PURE_RESUMES_FEATURE_END_CHECKPOINT (NEW)
        Resume case (ii): when all slices are ``shipped`` the Status column
        gives no signal, so ``/nw-continue`` reads the latest
        ``FeatureEndCheckpoint`` ledger record and resumes the feature-end
        cycle. master-absent token: ``FeatureEndCheckpoint``.
    EXECUTION_LOG_REFERENCES_MODE_SCOPED (MODE_SCOPED)
        Every line mentioning ``execution-log`` co-occurs with a ``classic`` /
        ``workflow.mode`` qualifier. On master the Step 5 / error-table
        ``execution-log.json`` lines are unqualified. master-present (unscoped)
        token: ``execution-log``.
    """

    READS_WORKFLOW_MODE = "reads_workflow_mode"
    ATDD_PURE_RESUMES_UN_SHIPPED_SLICE = "atdd_pure_resumes_un_shipped_slice"
    ATDD_PURE_RESUMES_FEATURE_END_CHECKPOINT = (
        "atdd_pure_resumes_feature_end_checkpoint"
    )
    EXECUTION_LOG_REFERENCES_MODE_SCOPED = "execution_log_references_mode_scoped"


@dataclass(frozen=True)
class SliceClauseContract:
    """A single coherence assertion over one slice-08 orchestration-doc's content.

    ``clause`` is the slice-08 contract-clause id (an ``ExecuteClause`` or a
    ``ContinueClause`` value, kept as the raw enum-value string so one record
    type serves both docs). ``doc`` names the file the clause is evaluated
    against. ``kind`` is NEW, ABSENCE, PRESERVATION or MODE_SCOPED.

    ``present_substrings`` are domain tokens that MUST all appear in the file
    once slice-08 lands. For a NEW or PRESERVATION clause they are the positive
    contract. For an ABSENCE or MODE_SCOPED clause this tuple is empty -- an
    ABSENCE clause asserts a removal and a MODE_SCOPED clause asserts a per-line
    qualification, neither asserts a bare presence.

    ``master_absent_substring`` is one token VERIFIED absent on master, proving
    a NEW clause is genuinely new -- the AT FAILS on master, PASSES once
    slice-08 adds the prose. REQUIRED for ``kind == NEW``, MUST be ``None``
    otherwise.

    ``master_present_substring`` is one token VERIFIED present on master.
      - For ABSENCE: the stale phrase slice-08 must DELETE (the post-slice file
        must NOT contain it).
      - For MODE_SCOPED: the audited token, VERIFIED present-AND-unqualified on
        at least one master line; the post-slice contract is that EVERY line
        carrying it also carries a ``MODE_QUALIFIER_TOKENS`` qualifier.
    REQUIRED for ``kind in {ABSENCE, MODE_SCOPED}``, MUST be ``None`` otherwise.

    ``__post_init__`` enforces the kind/token invariant so a false-RED claim
    (slice-04 review Blocking 1) cannot silently re-enter.

    A SliceClauseContract carries no business logic; it is a typed record the
    composition service evaluates against the file content (Mandate-12).
    """

    clause: str
    doc: OrchestrationDoc
    kind: ClauseKind
    present_substrings: tuple[str, ...]
    master_absent_substring: str | None
    master_present_substring: str | None

    def __post_init__(self) -> None:
        if self.kind is ClauseKind.NEW:
            if self.master_absent_substring is None:
                raise ValueError(
                    f"{self.clause}: a NEW clause must declare a "
                    f"master_absent_substring (its regression-AT signal)"
                )
            if self.master_present_substring is not None:
                raise ValueError(
                    f"{self.clause}: a NEW clause must NOT declare a "
                    f"master_present_substring (that is the ABSENCE/MODE_SCOPED "
                    f"signal)"
                )
            if not self.present_substrings:
                raise ValueError(
                    f"{self.clause}: a NEW clause must declare at least one "
                    f"present_substring (its positive contract)"
                )
        elif self.kind is ClauseKind.ABSENCE:
            if self.master_present_substring is None:
                raise ValueError(
                    f"{self.clause}: an ABSENCE clause must declare a "
                    f"master_present_substring (the stale phrase it removes)"
                )
            if self.master_absent_substring is not None:
                raise ValueError(
                    f"{self.clause}: an ABSENCE clause must NOT declare a "
                    f"master_absent_substring (that is the NEW signal)"
                )
            if self.present_substrings:
                raise ValueError(
                    f"{self.clause}: an ABSENCE clause asserts a removal and "
                    f"must NOT declare present_substrings"
                )
        elif self.kind is ClauseKind.MODE_SCOPED:
            if self.master_present_substring is None:
                raise ValueError(
                    f"{self.clause}: a MODE_SCOPED clause must declare a "
                    f"master_present_substring (the unscoped token it audits)"
                )
            if self.master_absent_substring is not None:
                raise ValueError(
                    f"{self.clause}: a MODE_SCOPED clause must NOT declare a "
                    f"master_absent_substring (the token is legitimate under "
                    f"classic -- it is qualified, not absent)"
                )
            if self.present_substrings:
                raise ValueError(
                    f"{self.clause}: a MODE_SCOPED clause asserts a per-line "
                    f"qualification and must NOT declare present_substrings"
                )
        else:  # PRESERVATION
            if self.master_absent_substring is not None:
                raise ValueError(
                    f"{self.clause}: a PRESERVATION clause must NOT declare a "
                    f"master_absent_substring (no new-vs-master delta)"
                )
            if self.master_present_substring is not None:
                raise ValueError(
                    f"{self.clause}: a PRESERVATION clause must NOT declare a "
                    f"master_present_substring (it removes nothing)"
                )
            if not self.present_substrings:
                raise ValueError(
                    f"{self.clause}: a PRESERVATION clause must declare the "
                    f"present_substrings it guards against deletion"
                )


# Repo-root-relative paths for the four slice-08 deliverables.
DOC_PATHS: dict[OrchestrationDoc, RepoRelPath] = {
    OrchestrationDoc.NW_EXECUTE_SKILL: RepoRelPath("nWave/skills/nw-execute/SKILL.md"),
    OrchestrationDoc.NW_CONTINUE_SKILL: RepoRelPath(
        "nWave/skills/nw-continue/SKILL.md"
    ),
    OrchestrationDoc.NW_EXECUTE_TASK: RepoRelPath("nWave/tasks/nw/execute.md"),
    OrchestrationDoc.NW_CONTINUE_TASK: RepoRelPath("nWave/tasks/nw/continue.md"),
}


# -----------------------------------------------------------------------------
# The slice-08 contracts. The composition service
# (ExecuteContinueCoherenceComposition) evaluates each against its doc.
#
# Every master token below was verified on master 2026-05-20 against the four
# real production files. The grep evidence is reproduced in the WAVE: DISTILL
# acceptance brief and re-checked by the test module's docstring:
#
#   nw-execute/SKILL.md (201 lines):
#     NEW master_absent : workflow.mode 0 | per-slice lean cycle 0 |
#                         A_GREEN_ATS 0 | carpaccio 0
#     MODE_SCOPED master_present (unscoped): roadmap.json 5 | execution-log 8
#                         classic / workflow.mode qualifier occurrences: 0
#   nw-continue/SKILL.md (126 lines):
#     NEW master_absent : workflow.mode 0 | un-shipped slice 0 |
#                         FeatureEndCheckpoint 0
#     MODE_SCOPED master_present (unscoped): execution-log 2
#                         classic / workflow.mode qualifier occurrences: 0
#                         (roadmap.json 0 on master -- no roadmap MODE_SCOPED
#                          clause for the continue pair, see note below)
#   nw/execute.md (203 lines):
#     NEW master_absent : workflow.mode 0 | per-slice lean cycle 0 |
#                         A_GREEN_ATS 0 | carpaccio 0
#     MODE_SCOPED master_present (unscoped): roadmap.json 4 | execution-log 8
#                         classic / workflow.mode qualifier occurrences: 0
#   nw/continue.md (129 lines):
#     NEW master_absent : workflow.mode 0 | un-shipped slice 0 |
#                         FeatureEndCheckpoint 0
#     MODE_SCOPED master_present (unscoped): execution-log 2
#                         classic / workflow.mode qualifier occurrences: 0
#                         (roadmap.json 0 on master)
#
# DESIGN-NOTE DISCREPANCY (reported in the acceptance brief). The design note
# (feature-delta L721-722) says "every roadmap / execution-log mention
# co-occurs with a ... qualifier" for ALL four files. But master nw-continue
# (both the SKILL and the task doc) has ZERO roadmap.json occurrences -- a
# roadmap MODE_SCOPED clause for the continue pair would have an empty audited
# line set and so would be VACUOUSLY satisfied on master (no line to qualify),
# i.e. it could never FAIL -- a non-falsifiable, non-regression assertion. Per
# the slice-04 review Blocking-1 discipline (no false / vacuous regression
# claims) the continue pair carries an execution-log MODE_SCOPED clause ONLY.
# The execute pair carries BOTH (roadmap.json + execution-log) because both
# tokens are genuinely present-and-unscoped on master there. This is honest
# coverage: every MODE_SCOPED clause below has a non-empty audited line set on
# master and therefore genuinely FAILS on master.
# -----------------------------------------------------------------------------

SLICE_08_EXECUTE_CONTRACTS: dict[ExecuteClause, SliceClauseContract] = {
    # NEW -- verified master-absent: "workflow.mode" (0 occurrences) on
    # nw-execute/SKILL.md.
    ExecuteClause.READS_WORKFLOW_MODE: SliceClauseContract(
        clause=ExecuteClause.READS_WORKFLOW_MODE.value,
        doc=OrchestrationDoc.NW_EXECUTE_SKILL,
        kind=ClauseKind.NEW,
        present_substrings=("workflow.mode",),
        master_absent_substring="workflow.mode",
        master_present_substring=None,
    ),
    # NEW -- verified master-absent: "per-slice lean cycle" (0). The "atdd_pure"
    # token is in present_substrings (also 0 on master) so a doc that names the
    # per-slice cycle but never scopes it to atdd_pure is still caught.
    ExecuteClause.ATDD_PURE_PER_SLICE_LEAN_CYCLE: SliceClauseContract(
        clause=ExecuteClause.ATDD_PURE_PER_SLICE_LEAN_CYCLE.value,
        doc=OrchestrationDoc.NW_EXECUTE_SKILL,
        kind=ClauseKind.NEW,
        present_substrings=("atdd_pure", "per-slice lean cycle"),
        master_absent_substring="per-slice lean cycle",
        master_present_substring=None,
    ),
    # NEW -- verified master-absent: "A_GREEN_ATS" (0). "carpaccio" is in
    # present_substrings (also 0 on master) so a doc that adds an atdd_pure
    # branch but still routes it through roadmap-step extraction (no carpaccio
    # entry gate) is still caught.
    ExecuteClause.ATDD_PURE_RUNS_A_GREEN_ATS: SliceClauseContract(
        clause=ExecuteClause.ATDD_PURE_RUNS_A_GREEN_ATS.value,
        doc=OrchestrationDoc.NW_EXECUTE_SKILL,
        kind=ClauseKind.NEW,
        present_substrings=("A_GREEN_ATS", "carpaccio"),
        master_absent_substring="A_GREEN_ATS",
        master_present_substring=None,
    ),
    # MODE_SCOPED -- verified master-PRESENT-and-unscoped: "roadmap.json"
    # (5 occurrences on nw-execute/SKILL.md, 0 of them on a line also carrying
    # a classic / workflow.mode qualifier). FAILS on master (unscoped lines),
    # PASSES once slice-08 qualifies every roadmap.json line.
    ExecuteClause.ROADMAP_REFERENCES_MODE_SCOPED: SliceClauseContract(
        clause=ExecuteClause.ROADMAP_REFERENCES_MODE_SCOPED.value,
        doc=OrchestrationDoc.NW_EXECUTE_SKILL,
        kind=ClauseKind.MODE_SCOPED,
        present_substrings=(),
        master_absent_substring=None,
        master_present_substring="roadmap.json",
    ),
    # MODE_SCOPED -- verified master-PRESENT-and-unscoped: "execution-log"
    # (8 occurrences on nw-execute/SKILL.md, 0 mode-qualified).
    ExecuteClause.EXECUTION_LOG_REFERENCES_MODE_SCOPED: SliceClauseContract(
        clause=ExecuteClause.EXECUTION_LOG_REFERENCES_MODE_SCOPED.value,
        doc=OrchestrationDoc.NW_EXECUTE_SKILL,
        kind=ClauseKind.MODE_SCOPED,
        present_substrings=(),
        master_absent_substring=None,
        master_present_substring="execution-log",
    ),
}


# The execute TASK doc (nw/execute.md) carries the SAME five clauses as the
# execute SKILL -- the slice-08 design note (feature-delta L693) names both as
# the execute pair and the master grep evidence is identical in kind (every NEW
# token 0, roadmap.json + execution-log present-and-unscoped). The dict below
# is the task-doc-targeted mirror; the composition service evaluates it against
# nw/execute.md.
SLICE_08_EXECUTE_TASK_CONTRACTS: dict[ExecuteClause, SliceClauseContract] = {
    ExecuteClause.READS_WORKFLOW_MODE: SliceClauseContract(
        clause=ExecuteClause.READS_WORKFLOW_MODE.value,
        doc=OrchestrationDoc.NW_EXECUTE_TASK,
        kind=ClauseKind.NEW,
        present_substrings=("workflow.mode",),
        master_absent_substring="workflow.mode",
        master_present_substring=None,
    ),
    ExecuteClause.ATDD_PURE_PER_SLICE_LEAN_CYCLE: SliceClauseContract(
        clause=ExecuteClause.ATDD_PURE_PER_SLICE_LEAN_CYCLE.value,
        doc=OrchestrationDoc.NW_EXECUTE_TASK,
        kind=ClauseKind.NEW,
        present_substrings=("atdd_pure", "per-slice lean cycle"),
        master_absent_substring="per-slice lean cycle",
        master_present_substring=None,
    ),
    ExecuteClause.ATDD_PURE_RUNS_A_GREEN_ATS: SliceClauseContract(
        clause=ExecuteClause.ATDD_PURE_RUNS_A_GREEN_ATS.value,
        doc=OrchestrationDoc.NW_EXECUTE_TASK,
        kind=ClauseKind.NEW,
        present_substrings=("A_GREEN_ATS", "carpaccio"),
        master_absent_substring="A_GREEN_ATS",
        master_present_substring=None,
    ),
    ExecuteClause.ROADMAP_REFERENCES_MODE_SCOPED: SliceClauseContract(
        clause=ExecuteClause.ROADMAP_REFERENCES_MODE_SCOPED.value,
        doc=OrchestrationDoc.NW_EXECUTE_TASK,
        kind=ClauseKind.MODE_SCOPED,
        present_substrings=(),
        master_absent_substring=None,
        master_present_substring="roadmap.json",
    ),
    ExecuteClause.EXECUTION_LOG_REFERENCES_MODE_SCOPED: SliceClauseContract(
        clause=ExecuteClause.EXECUTION_LOG_REFERENCES_MODE_SCOPED.value,
        doc=OrchestrationDoc.NW_EXECUTE_TASK,
        kind=ClauseKind.MODE_SCOPED,
        present_substrings=(),
        master_absent_substring=None,
        master_present_substring="execution-log",
    ),
}


SLICE_08_CONTINUE_CONTRACTS: dict[ContinueClause, SliceClauseContract] = {
    # NEW -- verified master-absent: "workflow.mode" (0) on nw-continue/SKILL.md.
    ContinueClause.READS_WORKFLOW_MODE: SliceClauseContract(
        clause=ContinueClause.READS_WORKFLOW_MODE.value,
        doc=OrchestrationDoc.NW_CONTINUE_SKILL,
        kind=ClauseKind.NEW,
        present_substrings=("workflow.mode",),
        master_absent_substring="workflow.mode",
        master_present_substring=None,
    ),
    # NEW -- verified master-absent: "un-shipped slice" (0). "atdd_pure" is in
    # present_substrings (also 0 on master) so a doc that names un-shipped-slice
    # resume but never scopes it to atdd_pure is still caught.
    ContinueClause.ATDD_PURE_RESUMES_UN_SHIPPED_SLICE: SliceClauseContract(
        clause=ContinueClause.ATDD_PURE_RESUMES_UN_SHIPPED_SLICE.value,
        doc=OrchestrationDoc.NW_CONTINUE_SKILL,
        kind=ClauseKind.NEW,
        present_substrings=("atdd_pure", "un-shipped slice"),
        master_absent_substring="un-shipped slice",
        master_present_substring=None,
    ),
    # NEW -- verified master-absent: "FeatureEndCheckpoint" (0). This is the
    # resume-case-(ii) cue -- without it a continue doc that adds an atdd_pure
    # branch covering only the un-shipped-slice case is still caught.
    ContinueClause.ATDD_PURE_RESUMES_FEATURE_END_CHECKPOINT: SliceClauseContract(
        clause=ContinueClause.ATDD_PURE_RESUMES_FEATURE_END_CHECKPOINT.value,
        doc=OrchestrationDoc.NW_CONTINUE_SKILL,
        kind=ClauseKind.NEW,
        present_substrings=("FeatureEndCheckpoint", "feature-end cycle"),
        master_absent_substring="FeatureEndCheckpoint",
        master_present_substring=None,
    ),
    # MODE_SCOPED -- verified master-PRESENT-and-unscoped: "execution-log"
    # (2 occurrences on nw-continue/SKILL.md, 0 mode-qualified). No roadmap.json
    # MODE_SCOPED clause for the continue pair -- roadmap.json is 0 on master
    # (a roadmap clause would be vacuously satisfied, non-falsifiable -- see
    # the SLICE_08_CONTRACTS block comment).
    ContinueClause.EXECUTION_LOG_REFERENCES_MODE_SCOPED: SliceClauseContract(
        clause=ContinueClause.EXECUTION_LOG_REFERENCES_MODE_SCOPED.value,
        doc=OrchestrationDoc.NW_CONTINUE_SKILL,
        kind=ClauseKind.MODE_SCOPED,
        present_substrings=(),
        master_absent_substring=None,
        master_present_substring="execution-log",
    ),
}


# The continue TASK doc (nw/continue.md) mirror -- same four clauses, evaluated
# against nw/continue.md. master grep evidence identical in kind.
SLICE_08_CONTINUE_TASK_CONTRACTS: dict[ContinueClause, SliceClauseContract] = {
    ContinueClause.READS_WORKFLOW_MODE: SliceClauseContract(
        clause=ContinueClause.READS_WORKFLOW_MODE.value,
        doc=OrchestrationDoc.NW_CONTINUE_TASK,
        kind=ClauseKind.NEW,
        present_substrings=("workflow.mode",),
        master_absent_substring="workflow.mode",
        master_present_substring=None,
    ),
    ContinueClause.ATDD_PURE_RESUMES_UN_SHIPPED_SLICE: SliceClauseContract(
        clause=ContinueClause.ATDD_PURE_RESUMES_UN_SHIPPED_SLICE.value,
        doc=OrchestrationDoc.NW_CONTINUE_TASK,
        kind=ClauseKind.NEW,
        present_substrings=("atdd_pure", "un-shipped slice"),
        master_absent_substring="un-shipped slice",
        master_present_substring=None,
    ),
    ContinueClause.ATDD_PURE_RESUMES_FEATURE_END_CHECKPOINT: SliceClauseContract(
        clause=ContinueClause.ATDD_PURE_RESUMES_FEATURE_END_CHECKPOINT.value,
        doc=OrchestrationDoc.NW_CONTINUE_TASK,
        kind=ClauseKind.NEW,
        present_substrings=("FeatureEndCheckpoint", "feature-end cycle"),
        master_absent_substring="FeatureEndCheckpoint",
        master_present_substring=None,
    ),
    ContinueClause.EXECUTION_LOG_REFERENCES_MODE_SCOPED: SliceClauseContract(
        clause=ContinueClause.EXECUTION_LOG_REFERENCES_MODE_SCOPED.value,
        doc=OrchestrationDoc.NW_CONTINUE_TASK,
        kind=ClauseKind.MODE_SCOPED,
        present_substrings=(),
        master_absent_substring=None,
        master_present_substring="execution-log",
    ),
}


# -----------------------------------------------------------------------------
# Gherkin-phrase -> typed-value lookups. Module-level dicts keep each step body
# a single typed lookup + a single composition call (Mandate-12 criterion 3:
# no control flow in step bodies). Every phrase used in the .feature file is a
# key here -- a missing key would KeyError at runtime (the slice-04
# step-resolution defect), so the collect-only + real-run gate verifies
# coverage.
# -----------------------------------------------------------------------------

# The doc under audit, keyed by the Gherkin Examples-column phrase.
DOC_BY_PHRASE: dict[str, OrchestrationDoc] = {
    "the nw-execute skill": OrchestrationDoc.NW_EXECUTE_SKILL,
    "the nw-execute command doc": OrchestrationDoc.NW_EXECUTE_TASK,
    "the nw-continue skill": OrchestrationDoc.NW_CONTINUE_SKILL,
    "the nw-continue command doc": OrchestrationDoc.NW_CONTINUE_TASK,
}

# The execute-pair NEW clause, keyed by the Gherkin Examples-column phrase.
EXECUTE_NEW_CLAUSE_BY_PHRASE: dict[str, ExecuteClause] = {
    "reads the workflow mode": ExecuteClause.READS_WORKFLOW_MODE,
    "runs the per-slice lean cycle under atdd_pure": (
        ExecuteClause.ATDD_PURE_PER_SLICE_LEAN_CYCLE
    ),
    "runs A_GREEN_ATS through the carpaccio gate under atdd_pure": (
        ExecuteClause.ATDD_PURE_RUNS_A_GREEN_ATS
    ),
}

# The continue-pair NEW clause, keyed by the Gherkin Examples-column phrase.
CONTINUE_NEW_CLAUSE_BY_PHRASE: dict[str, ContinueClause] = {
    "reads the workflow mode": ContinueClause.READS_WORKFLOW_MODE,
    "resumes at the first un-shipped slice under atdd_pure": (
        ContinueClause.ATDD_PURE_RESUMES_UN_SHIPPED_SLICE
    ),
    "resumes the feature-end cycle from the checkpoint under atdd_pure": (
        ContinueClause.ATDD_PURE_RESUMES_FEATURE_END_CHECKPOINT
    ),
}

# The audited MODE_SCOPED token, keyed by the Gherkin phrase.
MODE_SCOPED_TOKEN_BY_PHRASE: dict[str, str] = {
    "the roadmap file": "roadmap.json",
    "the execution log": "execution-log",
}
