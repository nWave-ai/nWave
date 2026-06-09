"""Composition root for the nw-execute / nw-continue mode-coherence slice.

slice-08 of the atdd-pure-roadmap-free-rollout (ADR-028 D6; feature-delta
``### slice-08`` design note, L685-725). Mandate-12 + Pillar 3: business logic
lives here as the single source of truth; step bodies delegate to
``ExecuteContinueCoherenceComposition`` methods and never inline logic.

WHY this is a coherence composition and not a CLI composition
-------------------------------------------------------------
slice-08 ships four ``.md`` files -- two skill ``SKILL.md`` files and two
command ``task`` docs -- all prose, no executable entry point. The skill files
are slash-command instruction sets an LLM interprets; the task docs are command
definitions. None is code with a callable surface; there is no driving-port CLI
to invoke. The driving surface is the doc *content*: the coherence test reads
each production file and asserts the slice-08 mode-coherence contract clauses
(the Class-P executable-coherence-test mechanism the rollout's own
``[REF] Slice classes`` section mandates -- feature-delta L199-202, slice-04 /
slice-05 precedents).

Regression contract: every NEW and MODE_SCOPED assertion FAILS on master and
PASSES once slice-08 lands. On master all four files are mode-UNAWARE -- no
``workflow.mode`` branch, no ``atdd_pure`` path, no ``carpaccio`` /
``per-slice lean cycle`` / ``A_GREEN_ATS`` vocabulary, no ``un-shipped slice``
or ``FeatureEndCheckpoint`` resume cue -- and they mention ``roadmap.json`` /
``execution-log`` on lines with NO ``classic`` / ``workflow.mode`` qualifier.
Each NEW contract's ``master_absent_substring`` is verified absent on master and
each MODE_SCOPED contract's ``master_present_substring`` is verified
present-and-unscoped, so the coherence assertions are genuine
missing-functionality RED, not test bugs.

The SUT is the real shipped file at its real repo path -- the production
artifact, read as-is (Pillar 3: app as in production, no hand-built fixture
copy of the skill / command doc).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .domain_types import (
    DOC_PATHS,
    MODE_QUALIFIER_TOKENS,
    SLICE_08_CONTINUE_CONTRACTS,
    SLICE_08_CONTINUE_TASK_CONTRACTS,
    SLICE_08_EXECUTE_CONTRACTS,
    SLICE_08_EXECUTE_TASK_CONTRACTS,
    ClauseKind,
    ContinueClause,
    ExecuteClause,
    OrchestrationDoc,
    SliceClauseContract,
)


# Repo root: this file is
# tests/scripts/cli/atdd_pure_nw_execute_continue/steps/composition.py
# -> five parents up is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[5]


# The two execute-pair contract dicts, keyed by the doc they target. The
# composition selects the right dict from the OrchestrationDoc so one
# evaluate_* method serves both the SKILL and the task doc (SSOT -- the clause
# logic is written once).
_EXECUTE_CONTRACTS_BY_DOC: dict[
    OrchestrationDoc, dict[ExecuteClause, SliceClauseContract]
] = {
    OrchestrationDoc.NW_EXECUTE_SKILL: SLICE_08_EXECUTE_CONTRACTS,
    OrchestrationDoc.NW_EXECUTE_TASK: SLICE_08_EXECUTE_TASK_CONTRACTS,
}

_CONTINUE_CONTRACTS_BY_DOC: dict[
    OrchestrationDoc, dict[ContinueClause, SliceClauseContract]
] = {
    OrchestrationDoc.NW_CONTINUE_SKILL: SLICE_08_CONTINUE_CONTRACTS,
    OrchestrationDoc.NW_CONTINUE_TASK: SLICE_08_CONTINUE_TASK_CONTRACTS,
}


@dataclass(frozen=True)
class ClauseVerdict:
    """Observable outcome of evaluating one slice-08 contract clause.

    ``clause`` -- the contract-clause id (raw enum-value string).
    ``doc``    -- the orchestration doc the clause was evaluated against.
    ``kind``   -- NEW, ABSENCE, PRESERVATION or MODE_SCOPED (mirrors the
                  contract's kind so the step layer can decide which assertion
                  applies).
    ``satisfied`` -- the clause's post-slice contract holds against the file:
                  for NEW / PRESERVATION, every present_substring appears;
                  for ABSENCE, the stale phrase is gone; for MODE_SCOPED, every
                  line carrying the audited token also carries a mode qualifier.
    ``regressed_from_master`` -- the clause's master signal is in the
                  post-slice state expected by slice-08:
                    * NEW         -- the master-absent token is now in the file;
                    * ABSENCE     -- the master-present token is now gone;
                    * MODE_SCOPED -- every audited line is now mode-qualified
                                     (on master at least one line is unscoped,
                                     so this is False on master -- a genuine
                                     regression signal);
                    * PRESERVATION -- always False (no master delta to claim).
    ``unscoped_lines`` -- for a MODE_SCOPED clause, the 1-based line numbers
                  carrying the audited token WITHOUT a mode qualifier (empty
                  once slice-08 scopes them all); empty for every other kind.
                  Surfaced so the test failure message can name the offending
                  lines -- the same diagnostic precision the slice-03 carpaccio
                  gate emits.
    """

    clause: str
    doc: OrchestrationDoc
    kind: ClauseKind
    satisfied: bool
    regressed_from_master: bool
    unscoped_lines: tuple[int, ...]


@dataclass
class ExecuteContinueCoherenceComposition:
    """Production-wired composition root for the slice-08 coherence slice.

    The SUT is the set of four real production files at their repo paths. Each
    is read once on demand; ``evaluate_clause`` is the single source of truth
    for every coherence predicate -- step bodies only call it.
    """

    repo_root: Path = field(default=_REPO_ROOT)
    _doc_text: dict[OrchestrationDoc, str] = field(default_factory=dict, repr=False)

    # --- Given: load a SUT doc ----------------------------------------------

    def load_doc(self, doc: OrchestrationDoc) -> None:
        """Read one production orchestration doc into the composition."""
        self._doc_text[doc] = (self.repo_root / DOC_PATHS[doc]).read_text(
            encoding="utf-8"
        )

    def doc_text(self, doc: OrchestrationDoc) -> str:
        """The loaded doc content (raises if its Given was skipped)."""
        if doc not in self._doc_text:  # defensive: a Given must run first
            raise AssertionError(f"orchestration doc {doc.value} not loaded")
        return self._doc_text[doc]

    def sole_loaded_doc(self) -> OrchestrationDoc:
        """The single doc loaded by this scenario row's Given.

        Each Scenario-Outline row loads exactly one orchestration doc; the
        Then step evaluates a clause against it. Asserting the dict holds
        exactly one entry makes the one-doc-per-row contract explicit (rather
        than relying on an opaque ``next(iter(...))``), and turns a future
        multi-Given mistake into a clear failure instead of a silent
        wrong-doc evaluation.
        """
        if len(self._doc_text) != 1:  # defensive: exactly one Given per row
            raise AssertionError(
                f"expected exactly one loaded orchestration doc, got "
                f"{[d.value for d in self._doc_text]}"
            )
        return next(iter(self._doc_text))

    # --- service: evaluate a slice-08 contract clause -----------------------

    def _contract_for(self, doc: OrchestrationDoc, clause: str) -> SliceClauseContract:
        """Resolve the typed contract record for (doc, clause)."""
        if doc in _EXECUTE_CONTRACTS_BY_DOC:
            execute_clause = ExecuteClause(clause)
            return _EXECUTE_CONTRACTS_BY_DOC[doc][execute_clause]
        continue_clause = ContinueClause(clause)
        return _CONTINUE_CONTRACTS_BY_DOC[doc][continue_clause]

    def _unscoped_lines(self, text: str, token: str) -> tuple[int, ...]:
        """1-based line numbers carrying ``token`` without a mode qualifier.

        A line is mode-scoped iff it ALSO contains a token from
        ``MODE_QUALIFIER_TOKENS`` (``classic`` / ``workflow.mode``). The
        per-line co-occurrence rule is the slice-08 design note's MODE-SCOPED
        contract (feature-delta L721-722) and the slice-10 semantic-role
        predicate pattern.
        """
        return tuple(
            lineno
            for lineno, line in enumerate(text.splitlines(), start=1)
            if token in line and not any(q in line for q in MODE_QUALIFIER_TOKENS)
        )

    def evaluate_clause(self, doc: OrchestrationDoc, clause: str) -> ClauseVerdict:
        """Evaluate one slice-08 contract clause against its doc.

        Business-logic SSOT (Mandate-12): the satisfied / regressed-from-master
        computation lives here, never in a step body.

        - NEW clause: ``satisfied`` iff every present_substring is in the file;
          ``regressed_from_master`` iff the master-absent token is now present.
        - MODE_SCOPED clause: ``satisfied`` iff NO line carries the audited
          token unscoped; ``regressed_from_master`` is the same predicate (a
          fully-scoped file IS the post-master state). ``unscoped_lines`` names
          the offending lines.
        - ABSENCE clause: ``satisfied`` iff the stale token is GONE;
          ``regressed_from_master`` is the same predicate.
        - PRESERVATION clause: ``satisfied`` iff every present_substring is in
          the file; ``regressed_from_master`` always False.
        """
        contract = self._contract_for(doc, clause)
        text = self.doc_text(doc)

        if contract.kind is ClauseKind.MODE_SCOPED:
            # master_present_substring is non-None for MODE_SCOPED
            # (domain-types __post_init__ guarantees it).
            token = contract.master_present_substring
            assert token is not None  # __post_init__ invariant
            unscoped = self._unscoped_lines(text, token)
            fully_scoped = len(unscoped) == 0
            return ClauseVerdict(
                clause=clause,
                doc=doc,
                kind=contract.kind,
                satisfied=fully_scoped,
                regressed_from_master=fully_scoped,
                unscoped_lines=unscoped,
            )

        if contract.kind is ClauseKind.ABSENCE:
            removed = contract.master_present_substring not in text
            return ClauseVerdict(
                clause=clause,
                doc=doc,
                kind=contract.kind,
                satisfied=removed,
                regressed_from_master=removed,
                unscoped_lines=(),
            )

        satisfied = all(token in text for token in contract.present_substrings)
        regressed = (
            contract.master_absent_substring is not None
            and contract.master_absent_substring in text
        )
        return ClauseVerdict(
            clause=clause,
            doc=doc,
            kind=contract.kind,
            satisfied=satisfied,
            regressed_from_master=regressed,
            unscoped_lines=(),
        )
