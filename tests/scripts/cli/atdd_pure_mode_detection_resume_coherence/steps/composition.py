"""Composition root for the mode-detection / resume / AT-set-audit coherence slice.

slice-13 of the atdd-pure-roadmap-free-rollout (ADR-028 / ADR-029). Mandate-12
+ Pillar 3: business logic lives here as the single source of truth; step
bodies delegate to ``ModeDetectionResumeComposition`` methods and never inline
logic.

WHY this is a coherence composition and not a CLI composition
-------------------------------------------------------------
slice-13 ships only the atdd_pure *prose* added to three skill files
(``nw-fast-forward``, ``nw-buddy-project-reading``, ``nw-at-completeness-check``)
-- prose, no executable entry point. There is no driving-port CLI to invoke.
The driving surface is the SKILL.md *content*: the coherence test reads each
file and asserts the slice-13 contract clauses hold (the Class-P
executable-coherence-test mechanism the rollout's own ``[REF] Slice classes``
section mandates, slice-09 / slice-04 / slice-10 / slice-15 precedent).

Regression contract: every NEW-clause assertion FAILS on master and PASSES once
slice-13 lands. On master none of the three files mention ``atdd_pure``; none
name the ``AT-completion ledger`` / ``workflow.mode`` / ``per-slice`` mechanism
-- they describe only the classic roadmap / execution-log / all-ATs path. Each
NEW contract's ``master_absent_substring`` is verified absent on master, so the
coherence assertions are genuine missing-functionality RED, not test bugs.

The ONE MODE_SCOPED assertion (nw-buddy-project-reading / ``roadmap.json``)
fails on master because master L92 carries an unscoped ``roadmap.json`` mention.
The other two design-note mode-scope / absence clauses are VACUOUS on master
and are deliberately NOT shipped (see ``domain_types`` VACUITY AUDIT and the
acceptance brief discrepancy flags).

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
# tests/scripts/cli/atdd_pure_mode_detection_resume_coherence/steps/composition.py
# -> five parents up is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[5]


@dataclass(frozen=True)
class UnscopedLine:
    """One scope-token line that carries no classic / workflow.mode qualifier.

    ``line_number`` is 1-based; ``text`` is the offending source line stripped.
    A non-empty list of these is the MODE_SCOPED failure evidence.
    """

    line_number: int
    text: str


@dataclass(frozen=True)
class ClauseVerdict:
    """Observable outcome of evaluating one slice-13 coherence contract clause.

    ``skill``   -- which slice-13 file the clause governs.
    ``kind``    -- NEW or MODE_SCOPED (mirrors the contract's kind so the step
                   layer can decide which assertion applies).
    ``present`` -- for a NEW clause: every mandated substring appears in the
                   file. For a MODE_SCOPED clause: always True (presence is
                   not the mode-scoped contract).
    ``is_new``  -- for a NEW clause: the master-absent token is in the file
                   (slice-13 has added it). For a MODE_SCOPED clause: always
                   False (a mode-scoped clause asserts per-line scoping, not
                   newness).
    ``unscoped_lines``
                -- for a MODE_SCOPED clause: the scope-token lines that lack a
                   ``classic`` / ``workflow.mode`` qualifier. Empty tuple ==
                   the mode-scope contract holds. For a NEW clause: always
                   empty.
    """

    skill: SkillFile
    kind: ClauseKind
    present: bool
    is_new: bool
    unscoped_lines: tuple[UnscopedLine, ...]


@dataclass
class ModeDetectionResumeComposition:
    """Production-wired composition root for the slice-13 coherence slice.

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
        """Read one production slice-13 SKILL.md into the composition."""
        self._skill = skill
        self._skill_text = (self.repo_root / skill.value).read_text(encoding="utf-8")

    @property
    def skill(self) -> SkillFile:
        """The loaded skill identity (raises if load was skipped)."""
        if self._skill is None:  # defensive: a Given must run first
            raise AssertionError("slice-13 skill not loaded")
        return self._skill

    @property
    def skill_text(self) -> str:
        """The loaded SKILL.md content (raises if load was skipped)."""
        if self._skill_text is None:  # defensive: a Given must run first
            raise AssertionError("slice-13 skill not loaded")
        return self._skill_text

    # --- service: evaluate a NEW-prose contract clause -----------------------

    def evaluate_new_clause(self) -> ClauseVerdict:
        """Evaluate the loaded file's NEW (atdd_pure-prose) contract clause.

        Business-logic SSOT (Mandate-12): the present / is-new computation
        lives here, never in a step body. ``present`` is True iff every
        mandated atdd_pure token is in the file; ``is_new`` is True once the
        master-absent token has been added by slice-13.
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
        lives here, never in a step body. Returns every scope-token line that
        lacks a ``classic`` / ``workflow.mode`` qualifier. An empty
        ``unscoped_lines`` tuple == the mode-scope contract holds (the
        slice-13-aligned state); a non-empty tuple is the failure evidence
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
