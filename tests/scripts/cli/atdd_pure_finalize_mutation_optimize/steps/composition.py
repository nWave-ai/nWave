"""Composition root for the finalize/mutation/optimize coherence slice.

slice-09 of the atdd-pure-roadmap-free-rollout (ADR-028 D4.3 + D3). Mandate-12
+ Pillar 3: business logic lives here as the single source of truth; step
bodies delegate to ``FinalizeMutationOptimizeComposition`` methods and never
inline logic.

WHY this is a coherence composition and not a CLI composition
-------------------------------------------------------------
slice-09 ships only the atdd_pure *prose* added to three finalize-adjacent
skill files (``nw-finalize``, ``nw-mutation-test``, ``nw-optimize-tests``) --
prose, no executable entry point. There is no driving-port CLI to invoke. The
driving surface is the SKILL.md *content*: the coherence test reads each file
and asserts the slice-09 contract clauses hold (the Class-P
executable-coherence-test mechanism the rollout's own ``[REF] Slice classes``
section mandates -- feature-delta L160-163, slice-04 / slice-10 / slice-15
precedent).

Regression contract: every NEW-clause assertion FAILS on master and PASSES
once slice-09 lands. On master none of the three files mention ``atdd_pure``
or the ``AT-completion ledger`` -- they describe only the classic roadmap /
execution-log finalize path. Each NEW contract's ``master_absent_substring``
is verified absent on master, so the coherence assertions are genuine
missing-functionality RED, not test bugs. The MODE_SCOPED assertion fails on
master because master carries unscoped ``roadmap.json`` / ``execution-log``
lines (verified: nw-finalize 8, nw-mutation-test 7, nw-optimize-tests 1).

The SUT is the real shipped file at its real repo path -- the production
artifact, read as-is (Pillar 3: app as in production, no hand-built fixture
copy of the skill).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .domain_types import (
    COHERENCE_CONTRACTS,
    ClauseKind,
    CoherenceContract,
    SkillFile,
)


# Repo root: this file is
# tests/scripts/cli/atdd_pure_finalize_mutation_optimize/steps/composition.py
# -> five parents up is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[5]


@dataclass(frozen=True)
class UnscopedLine:
    """One roadmap / execution-log line that carries no classic qualifier.

    ``line_number`` is 1-based; ``text`` is the offending source line stripped.
    A non-empty list of these is the MODE_SCOPED failure evidence.
    """

    line_number: int
    text: str


@dataclass(frozen=True)
class ClauseVerdict:
    """Observable outcome of evaluating one slice-09 coherence contract clause.

    ``skill``   -- which slice-09 file the clause governs.
    ``kind``    -- NEW or MODE_SCOPED (mirrors the contract's kind so the step
                   layer can decide which assertion applies).
    ``present`` -- for a NEW clause: every mandated substring appears in the
                   file. For a MODE_SCOPED clause: always True (presence is
                   not the mode-scoped contract).
    ``is_new``  -- for a NEW clause: the master-absent token is in the file
                   (slice-09 has added it). For a MODE_SCOPED clause: always
                   False (a mode-scoped clause asserts per-line scoping, not
                   newness).
    ``unscoped_lines``
                -- for a MODE_SCOPED clause: the roadmap / execution-log lines
                   that lack a ``classic`` / ``workflow.mode`` qualifier. Empty
                   tuple == the mode-scope contract holds. For a NEW clause:
                   always empty.
    """

    skill: SkillFile
    kind: ClauseKind
    present: bool
    is_new: bool
    unscoped_lines: tuple[UnscopedLine, ...]


@dataclass
class FinalizeMutationOptimizeComposition:
    """Production-wired composition root for the slice-09 coherence slice.

    The SUT is the three real ``SKILL.md`` files at their repo paths.
    ``load_skill`` reads one into the composition; ``evaluate_new_clause`` and
    ``evaluate_mode_scoped_clause`` are the single source of truth for every
    coherence predicate -- step bodies only call them.
    """

    repo_root: Path = field(default=_REPO_ROOT)
    _skill: SkillFile | None = field(default=None, repr=False)
    _skill_text: str | None = field(default=None, repr=False)

    # --- Given: load the SUT -------------------------------------------------

    def load_skill(self, skill: SkillFile) -> None:
        """Read one production slice-09 SKILL.md into the composition."""
        self._skill = skill
        self._skill_text = (self.repo_root / skill.value).read_text(encoding="utf-8")

    @property
    def skill(self) -> SkillFile:
        """The loaded skill identity (raises if load was skipped)."""
        if self._skill is None:  # defensive: a Given must run first
            raise AssertionError("slice-09 skill not loaded")
        return self._skill

    @property
    def skill_text(self) -> str:
        """The loaded SKILL.md content (raises if load was skipped)."""
        if self._skill_text is None:  # defensive: a Given must run first
            raise AssertionError("slice-09 skill not loaded")
        return self._skill_text

    # --- service: evaluate a NEW-prose contract clause -----------------------

    def evaluate_new_clause(self) -> ClauseVerdict:
        """Evaluate the loaded file's NEW (atdd_pure-prose) contract clause.

        Business-logic SSOT (Mandate-12): the present / is-new computation
        lives here, never in a step body. ``present`` is True iff every
        mandated atdd_pure token is in the file; ``is_new`` is True once the
        master-absent token has been added by slice-09.
        """
        contract = COHERENCE_CONTRACTS[self.skill][ClauseKind.NEW]
        text = self.skill_text
        present = all(token in text for token in contract.present_substrings)
        is_new = (
            contract.master_absent_substring is not None
            and contract.master_absent_substring in text
        )
        return ClauseVerdict(
            skill=self.skill,
            kind=ClauseKind.NEW,
            present=present,
            is_new=is_new,
            unscoped_lines=(),
        )

    # --- service: evaluate the MODE_SCOPED contract clause -------------------

    def evaluate_mode_scoped_clause(self) -> ClauseVerdict:
        """Evaluate the loaded file's MODE_SCOPED contract clause.

        Business-logic SSOT (Mandate-12): the per-line mode-scope computation
        lives here, never in a step body. Returns every roadmap / execution-log
        line that lacks a ``classic`` / ``workflow.mode`` qualifier. An empty
        ``unscoped_lines`` tuple == the mode-scope contract holds (the
        slice-09-aligned state); a non-empty tuple is the failure evidence
        (the master state).
        """
        contract = COHERENCE_CONTRACTS[self.skill][ClauseKind.MODE_SCOPED]
        unscoped = self._collect_unscoped_lines(contract)
        return ClauseVerdict(
            skill=self.skill,
            kind=ClauseKind.MODE_SCOPED,
            present=True,
            is_new=False,
            unscoped_lines=unscoped,
        )

    def _collect_unscoped_lines(
        self, contract: CoherenceContract
    ) -> tuple[UnscopedLine, ...]:
        """Lines mentioning a scope token but carrying no qualifier token.

        Helper for ``evaluate_mode_scoped_clause`` -- kept a private method so
        the public service stays a single declarative call and the step layer
        sees one composition method (Mandate-12 criterion 3).
        """
        return tuple(
            UnscopedLine(line_number=i, text=line.strip())
            for i, line in enumerate(self.skill_text.splitlines(), start=1)
            if any(tok in line for tok in contract.scope_tokens)
            and not any(q in line for q in contract.qualifier_tokens)
        )
