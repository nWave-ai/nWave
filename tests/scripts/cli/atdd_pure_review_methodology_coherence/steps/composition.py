"""Composition root for the review-methodology + reviewer-agent coherence slice.

slice-10 of the atdd-pure-roadmap-free-rollout (ADR-028 7-phase A->G sibling
spine + ADR-029 PO/ATD reviewer DoR/DoD re-split). Mandate-12 + Pillar 3:
business logic lives here as the single source of truth; step bodies delegate
to ``ReviewMethodologyCoherenceComposition`` methods and never inline logic.

WHY this is a coherence composition and not a CLI composition
-------------------------------------------------------------
slice-10 ships only the atdd_pure-coherence *prose* edited into six
review-methodology / reviewer-agent files -- prose, no executable entry point.
There is no driving-port CLI to invoke. The driving surface is the file
*content*: the coherence test reads each file and asserts the slice-10
contract clauses hold (the Class-P executable-coherence-test mechanism the
rollout's own ``[REF] Slice classes`` section mandates -- slice-04 / slice-09 /
slice-15 precedent).

Regression contract -- two mechanisms (slice-10 design note H2-final):

* REGEX (4 files): every ``present_regex`` token is verified 0 occurrences on
  master 2026-05-20 -- so the PRESENT predicate FAILS on master and PASSES once
  slice-10 lands. The ``absent_regex`` tokens are ALSO 0 on master (vacuity
  audit, domain_types.py docstring): the absent clause is a non-regression
  GUARD, not the slice-10 RED signal. ``evaluate_regex_clause`` returns both
  results so the step layer asserts the falsifiable PRESENT predicate as RED
  and the non-falsifiable ABSENT predicate only as a documented guard.

* SEMANTIC-ROLE (2 files): the ledger token "AT-completion ledger" is verified
  0 occurrences on master in both files -- predicate 1 FAILS on master. Each
  file carries 3 unscoped ``execution-log.json`` lines on master -- predicate 2
  FAILS on master. Both predicates are genuine missing-functionality RED.

The SUT is the real shipped file at its real repo path -- the production
artifact, read as-is (Pillar 3: app as in production, no hand-built fixture
copy of the skill / agent spec).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .domain_types import (
    REGEX_CONTRACTS,
    SEMANTIC_ROLE_CONTRACTS,
    CoherenceFile,
    Mechanism,
)


# Repo root: this file is
# tests/scripts/cli/atdd_pure_review_methodology_coherence/steps/composition.py
# -> five parents up is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[5]


@dataclass(frozen=True)
class UnscopedLine:
    """One execution-log.json line that carries no classic qualifier.

    ``line_number`` is 1-based; ``text`` is the offending source line stripped.
    A non-empty tuple of these is the SEMANTIC-ROLE predicate-2 failure
    evidence (the master state).
    """

    line_number: int
    text: str


@dataclass(frozen=True)
class RegexVerdict:
    """Observable outcome of evaluating one REGEX-mechanism coherence contract.

    ``coherence_file``   -- which of the four REGEX-gated files this governs.
    ``mechanism``        -- always ``Mechanism.REGEX`` (lets the step layer
                            assert it reached the right evaluator).
    ``present_matched``  -- True iff ``present_regex`` matches >=1 line. This is
                            the falsifiable slice-10 regression signal.
    ``absent_clear``     -- True iff ``absent_regex`` matches zero lines.
    ``absent_is_vacuous``-- True iff the absent clause already matched zero on
                            master (mirrors the contract). When True the step
                            layer treats ``absent_clear`` as a documented
                            non-regression guard, NOT a slice-10 RED signal.
    """

    coherence_file: CoherenceFile
    mechanism: Mechanism
    present_matched: bool
    absent_clear: bool
    absent_is_vacuous: bool


@dataclass(frozen=True)
class SemanticRoleVerdict:
    """Observable outcome of evaluating one SEMANTIC-ROLE coherence contract.

    ``coherence_file``    -- which of the two SEMANTIC-ROLE-gated files.
    ``mechanism``         -- always ``Mechanism.SEMANTIC_ROLE``.
    ``names_ledger``      -- predicate 1: the file NAMES the atdd_pure phase
                             record ("AT-completion ledger"). Falsifiable --
                             master-absent.
    ``unscoped_lines``    -- predicate 2: the ``execution-log.json`` lines that
                             lack a ``classic`` / ``workflow.mode`` qualifier.
                             Empty tuple == predicate 2 holds (the slice-10
                             state); a non-empty tuple is the failure evidence
                             (the master state).
    """

    coherence_file: CoherenceFile
    mechanism: Mechanism
    names_ledger: bool
    unscoped_lines: tuple[UnscopedLine, ...]


@dataclass
class ReviewMethodologyCoherenceComposition:
    """Production-wired composition root for the slice-10 coherence slice.

    The SUT is the six real review-methodology / reviewer-agent files at their
    repo paths. ``load_file`` reads one into the composition;
    ``evaluate_regex_clause`` and ``evaluate_semantic_role_clause`` are the
    single source of truth for every coherence predicate -- step bodies only
    call them.
    """

    repo_root: Path = field(default=_REPO_ROOT)
    _coherence_file: CoherenceFile | None = field(default=None, repr=False)
    _file_text: str | None = field(default=None, repr=False)

    # --- Given: load the SUT -------------------------------------------------

    def load_file(self, coherence_file: CoherenceFile) -> None:
        """Read one production slice-10 file into the composition."""
        self._coherence_file = coherence_file
        self._file_text = (self.repo_root / coherence_file.value).read_text(
            encoding="utf-8"
        )

    @property
    def coherence_file(self) -> CoherenceFile:
        """The loaded file identity (raises if load was skipped)."""
        if self._coherence_file is None:  # defensive: a Given must run first
            raise AssertionError("slice-10 coherence file not loaded")
        return self._coherence_file

    @property
    def file_text(self) -> str:
        """The loaded file content (raises if load was skipped)."""
        if self._file_text is None:  # defensive: a Given must run first
            raise AssertionError("slice-10 coherence file not loaded")
        return self._file_text

    # --- service: evaluate a REGEX-mechanism contract ------------------------

    def evaluate_regex_clause(self) -> RegexVerdict:
        """Evaluate the loaded file's REGEX-mechanism coherence contract.

        Business-logic SSOT (Mandate-12): the present / absent regex match
        computation lives here, never in a step body. ``present_matched`` is
        the falsifiable slice-10 regression signal; ``absent_clear`` is the
        non-regression guard (vacuous on master per the vacuity audit).
        """
        contract = REGEX_CONTRACTS[self.coherence_file]
        text = self.file_text
        present_matched = (
            re.search(contract.present_regex, text, flags=re.MULTILINE) is not None
        )
        absent_clear = (
            re.search(contract.absent_regex, text, flags=re.MULTILINE) is None
        )
        return RegexVerdict(
            coherence_file=self.coherence_file,
            mechanism=Mechanism.REGEX,
            present_matched=present_matched,
            absent_clear=absent_clear,
            absent_is_vacuous=contract.absent_is_vacuous,
        )

    # --- service: evaluate a SEMANTIC-ROLE-mechanism contract ----------------

    def evaluate_semantic_role_clause(self) -> SemanticRoleVerdict:
        """Evaluate the loaded file's SEMANTIC-ROLE-mechanism coherence contract.

        Business-logic SSOT (Mandate-12): the predicate-1 ledger-naming check
        and the predicate-2 per-line mode-scope computation live here, never in
        a step body. ``names_ledger`` False == predicate 1 fails (master
        state); a non-empty ``unscoped_lines`` tuple == predicate 2 fails
        (master state).
        """
        contract = SEMANTIC_ROLE_CONTRACTS[self.coherence_file]
        names_ledger = contract.ledger_token in self.file_text
        unscoped = self._collect_unscoped_lines()
        return SemanticRoleVerdict(
            coherence_file=self.coherence_file,
            mechanism=Mechanism.SEMANTIC_ROLE,
            names_ledger=names_ledger,
            unscoped_lines=unscoped,
        )

    def _collect_unscoped_lines(self) -> tuple[UnscopedLine, ...]:
        """Lines mentioning a phase-record token but carrying no qualifier.

        Helper for ``evaluate_semantic_role_clause`` -- kept a private method
        so the public service stays a single declarative call and the step
        layer sees one composition method (Mandate-12 criterion 3). Mirrors the
        slice-10 design-note predicate-2 regex ``\\bclassic\\b|workflow\\.mode``.
        """
        contract = SEMANTIC_ROLE_CONTRACTS[self.coherence_file]
        qualifier = re.compile(r"\bclassic\b|workflow\.mode")
        return tuple(
            UnscopedLine(line_number=i, text=line.strip())
            for i, line in enumerate(self.file_text.splitlines(), start=1)
            if any(tok in line for tok in contract.phase_record_tokens)
            and qualifier.search(line) is None
        )
