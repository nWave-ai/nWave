"""Composition root for the roadmap classic-only flagging coherence slice.

slice-11 of the atdd-pure-roadmap-free-rollout (ADR-028 / ADR-029). Mandate-12
+ Pillar 3: business logic lives here as the single source of truth; step
bodies delegate to ``RoadmapClassicOnlyComposition`` methods and never inline
logic.

WHY this is a coherence composition and not a CLI composition
-------------------------------------------------------------
slice-11 ships only the classic-only / atdd_pure-context *prose* added to
three production files (``nw-roadmap/SKILL.md``, ``nw/roadmap.md``,
``nw-root-why/SKILL.md``) -- prose, no executable entry point. There is no
driving-port CLI to invoke. The driving surface is the file *content*: the
coherence test reads each file and asserts the slice-11 ``present_regex``
clauses match (the Class-P executable-coherence-test mechanism the rollout's
own ``[REF] Slice classes`` section mandates, slice-09 / slice-04 / slice-10 /
slice-13 precedent).

Regression contract: every clause assertion FAILS on master and PASSES once
slice-11 lands. On master none of the three files match their ``present_regex``
(verified 0 matches 2026-05-20) -- they describe only the classic roadmap
path without the classic-only flag / atdd_pure-context paragraph. Each
contract's ``present_regex`` is verified 0 matches on master, so the coherence
assertions are genuine missing-functionality RED, not test bugs.

The SUT is the real shipped file at its real repo path -- the production
artifact, read as-is (Pillar 3: app as in production, no hand-built fixture
copy of the skill / command).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .domain_types import COHERENCE_CONTRACTS, ClauseKind, RoadmapFile


# Repo root: this file is
# tests/scripts/cli/atdd_pure_roadmap_classic_only_coherence/steps/composition.py
# -> five parents up is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[5]


@dataclass(frozen=True)
class ClauseVerdict:
    """Observable outcome of evaluating one slice-11 coherence contract clause.

    ``roadmap_file`` -- which slice-11 file the clause governs.
    ``kind``         -- NEW (every slice-11 clause is NEW).
    ``present``      -- the contract's ``present_regex`` matches >=1 line in
                        the file. True == the slice-11 prose has landed;
                        False == master state (the AT's RED signal).
    ``match_count``  -- how many lines the ``present_regex`` matches (>=1 on
                        the slice-11-aligned file, 0 on master). Surfaced so
                        the assertion message can report the count.
    """

    roadmap_file: RoadmapFile
    kind: ClauseKind
    present: bool
    match_count: int


@dataclass
class RoadmapClassicOnlyComposition:
    """Production-wired composition root for the slice-11 coherence slice.

    The SUT is the three real production ``.md`` files at their repo paths.
    ``load_file`` reads one into the composition; ``evaluate_present_clause``
    is the single source of truth for the literal-regex coherence predicate --
    step bodies only call it.
    """

    repo_root: Path = field(default=_REPO_ROOT)
    _roadmap_file: RoadmapFile | None = field(default=None, repr=False)
    _file_text: str | None = field(default=None, repr=False)

    # --- Given: load the SUT -------------------------------------------------

    def load_file(self, roadmap_file: RoadmapFile) -> None:
        """Read one production slice-11 ``.md`` file into the composition."""
        self._roadmap_file = roadmap_file
        self._file_text = (self.repo_root / roadmap_file.value).read_text(
            encoding="utf-8"
        )

    @property
    def roadmap_file(self) -> RoadmapFile:
        """The loaded file identity (raises if load was skipped)."""
        if self._roadmap_file is None:  # defensive: a Given/When must run first
            raise AssertionError("slice-11 roadmap file not loaded")
        return self._roadmap_file

    @property
    def file_text(self) -> str:
        """The loaded file content (raises if load was skipped)."""
        if self._file_text is None:  # defensive: a Given/When must run first
            raise AssertionError("slice-11 roadmap file not loaded")
        return self._file_text

    # --- service: evaluate the NEW literal-regex contract clause -------------

    def evaluate_present_clause(self) -> ClauseVerdict:
        """Evaluate the loaded file's NEW (present_regex) contract clause.

        Business-logic SSOT (Mandate-12): the regex-match computation lives
        here, never in a step body. ``present`` is True iff the contract's
        ``present_regex`` matches >=1 line of the file; ``match_count`` is the
        number of matching lines.
        """
        contract = COHERENCE_CONTRACTS[self.roadmap_file]
        pattern = re.compile(contract.present_regex)
        match_count = sum(
            1 for line in self.file_text.splitlines() if pattern.search(line)
        )
        return ClauseVerdict(
            roadmap_file=self.roadmap_file,
            kind=contract.kind,
            present=match_count >= 1,
            match_count=match_count,
        )
