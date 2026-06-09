"""Composition root for the documentation coherence slice.

slice-12 of the atdd-pure-roadmap-free-rollout (ADR-028 / ADR-029). Mandate-12
+ Pillar 3: business logic lives here as the single source of truth; step
bodies delegate to ``DocumentationCoherenceComposition`` methods and never
inline logic.

WHY this is a coherence composition and not a CLI composition
-------------------------------------------------------------
slice-12 ships only the atdd_pure documentation *prose* added to three
documentation files (``docs/reference/des-markers.md``,
``docs/guides/tutorial-deliver-feature/README.md``,
``docs/analysis/wave-flow-precise-map.md``) -- prose, no executable entry
point. There is no driving-port CLI to invoke. The driving surface is the
file *content*: the coherence test reads each file and asserts the slice-12
``present_regex`` clauses match (the Class-P executable-coherence-test
mechanism the rollout's own ``[REF] Slice classes`` section mandates,
slice-09 / slice-04 / slice-10 / slice-13 precedent).

Regression contract: every clause assertion FAILS on master and PASSES once
slice-12 lands. On master none of the three files match their ``present_regex``
(verified 0 matches 2026-05-20) -- they document only the classic path. Each
contract's ``present_regex`` is verified 0 matches on master, so the coherence
assertions are genuine missing-functionality RED, not test bugs.

The SUT is the real shipped file at its real repo path -- the production
artifact, read as-is (Pillar 3: app as in production, no hand-built fixture
copy of the doc).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .domain_types import COHERENCE_CONTRACTS, ClauseKind, DocFile


# Repo root: this file is
# tests/scripts/cli/atdd_pure_documentation_coherence/steps/composition.py
# -> five parents up is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[5]


@dataclass(frozen=True)
class ClauseVerdict:
    """Observable outcome of evaluating one slice-12 coherence contract clause.

    ``doc_file``    -- which slice-12 file the clause governs.
    ``kind``        -- NEW (every slice-12 clause is NEW).
    ``present``     -- the contract's ``present_regex`` matches >=1 line in
                       the file. True == the slice-12 prose has landed;
                       False == master state (the AT's RED signal).
    ``match_count`` -- how many lines the ``present_regex`` matches (>=1 on
                       the slice-12-aligned file, 0 on master). Surfaced so
                       the assertion message can report the count.
    """

    doc_file: DocFile
    kind: ClauseKind
    present: bool
    match_count: int


@dataclass
class DocumentationCoherenceComposition:
    """Production-wired composition root for the slice-12 coherence slice.

    The SUT is the three real production ``.md`` doc files at their repo
    paths. ``load_doc`` reads one into the composition;
    ``evaluate_present_clause`` is the single source of truth for the
    literal-regex coherence predicate -- step bodies only call it.
    """

    repo_root: Path = field(default=_REPO_ROOT)
    _doc_file: DocFile | None = field(default=None, repr=False)
    _doc_text: str | None = field(default=None, repr=False)

    # --- Given: load the SUT -------------------------------------------------

    def load_doc(self, doc_file: DocFile) -> None:
        """Read one production slice-12 ``.md`` doc file into the composition."""
        self._doc_file = doc_file
        self._doc_text = (self.repo_root / doc_file.value).read_text(encoding="utf-8")

    @property
    def doc_file(self) -> DocFile:
        """The loaded doc identity (raises if load was skipped)."""
        if self._doc_file is None:  # defensive: a Given/When must run first
            raise AssertionError("slice-12 doc file not loaded")
        return self._doc_file

    @property
    def doc_text(self) -> str:
        """The loaded doc content (raises if load was skipped)."""
        if self._doc_text is None:  # defensive: a Given/When must run first
            raise AssertionError("slice-12 doc file not loaded")
        return self._doc_text

    # --- service: evaluate the NEW literal-regex contract clause -------------

    def evaluate_present_clause(self) -> ClauseVerdict:
        """Evaluate the loaded doc's NEW (present_regex) contract clause.

        Business-logic SSOT (Mandate-12): the regex-match computation lives
        here, never in a step body. ``present`` is True iff the contract's
        ``present_regex`` matches >=1 line of the doc; ``match_count`` is the
        number of matching lines.
        """
        contract = COHERENCE_CONTRACTS[self.doc_file]
        pattern = re.compile(contract.present_regex)
        match_count = sum(
            1 for line in self.doc_text.splitlines() if pattern.search(line)
        )
        return ClauseVerdict(
            doc_file=self.doc_file,
            kind=contract.kind,
            present=match_count >= 1,
            match_count=match_count,
        )
