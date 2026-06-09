"""Composition root for the nw-deliver feature-end-cycle coherence slice.

slice-15 of the atdd-pure-roadmap-free-rollout (ADR-028 D6). Mandate-12 +
Pillar 3: business logic lives here as the single source of truth; step bodies
delegate to ``FeatureEndCoherenceComposition`` methods and never inline logic.

WHY this is a coherence composition and not a CLI composition
-------------------------------------------------------------
slice-15 ships only the D6 feature-end-cycle *prose* added to
``nWave/skills/nw-deliver/SKILL.md`` -- prose, no executable entry point. There
is no driving-port CLI to invoke. The driving surface is the SKILL.md
*content*: the coherence test reads the file and asserts the feature-end-cycle
contract clauses are present (the Class-P executable-coherence-test mechanism
the rollout's own ``[REF] Slice classes`` section mandates -- feature-delta
L160-163, slice-04/slice-10 precedent).

Regression contract: every NEW-clause assertion FAILS on master and PASSES
once slice-15 lands. On master ``nw-deliver/SKILL.md`` describes the atdd_pure
path only as a per-slice 7-phase ``A->G`` sequence -- ``E_BATCH_REFACTOR``,
``C_REVIEWER_AUDIT``, ``F_FINAL_REVIEW`` are PER-SLICE phases in the A->G
table. There is NO once-per-feature feature-end cycle, NO collapsed deep
review with final integrity verification, NO ``FeatureEndCheckpoint`` resume
record. Each NEW contract's ``master_absent_substring`` is verified absent on
master, so the coherence assertions are genuine missing-functionality RED, not
test bugs.

The SUT is the real shipped file at its real repo path -- the production
artifact, read as-is (Pillar 3: app as in production, no hand-built fixture
copy of the skill).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .domain_types import (
    FEATURE_END_CONTRACTS,
    ClauseKind,
    FeatureEndClause,
    RepoRelPath,
)


# Repo root: this file is
# tests/scripts/cli/atdd_pure_feature_end_cycle/steps/composition.py
# -> five parents up is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[5]

# The single slice-15 deliverable under coherence audit.
_NW_DELIVER_SKILL = RepoRelPath("nWave/skills/nw-deliver/SKILL.md")


@dataclass(frozen=True)
class ClauseVerdict:
    """Observable outcome of evaluating one feature-end-cycle contract clause.

    ``kind``    -- NEW or PRESERVATION (mirrors the contract's kind so the step
                   layer can decide whether the ``is_new`` assertion applies).
    ``present`` -- every mandated substring for the clause appears in the file.
    ``is_new``  -- the clause's master-absent token is currently in the file
                   (it has been added by slice-15). Meaningful only for a NEW
                   clause; always False for a PRESERVATION clause (which has no
                   master-absent token and asserts presence, never newness).
    """

    clause: FeatureEndClause
    kind: ClauseKind
    present: bool
    is_new: bool


@dataclass
class FeatureEndCoherenceComposition:
    """Production-wired composition root for the feature-end-cycle slice.

    The SUT is the real ``nWave/skills/nw-deliver/SKILL.md`` at its repo path.
    ``load`` reads it once; the ``evaluate_clause`` method is the single source
    of truth for every coherence predicate -- step bodies only call it.
    """

    repo_root: Path = field(default=_REPO_ROOT)
    _skill_text: str | None = field(default=None, repr=False)

    # --- Given: load the SUT -------------------------------------------------

    def load_nw_deliver_skill(self) -> None:
        """Read the production nw-deliver SKILL.md into the composition."""
        self._skill_text = (self.repo_root / _NW_DELIVER_SKILL).read_text(
            encoding="utf-8"
        )

    @property
    def skill_text(self) -> str:
        """The loaded SKILL.md content (raises if load was skipped)."""
        if self._skill_text is None:  # defensive: a Given must run first
            raise AssertionError("nw-deliver SKILL.md not loaded")
        return self._skill_text

    # --- service: evaluate a feature-end-cycle contract clause ---------------

    def evaluate_clause(self, clause: FeatureEndClause) -> ClauseVerdict:
        """Evaluate one slice-15 feature-end-cycle contract clause.

        Business-logic SSOT (Mandate-12): the present / is-new computation
        lives here, never in a step body.

        ``is_new`` is meaningful only for a NEW-kind clause: it is True once
        the master-absent token has been added by slice-15. For a
        PRESERVATION clause the contract carries no master-absent token, so
        ``is_new`` is reported False -- a preservation clause asserts presence,
        never newness. The step layer reads ``contract.kind`` and only asserts
        ``is_new`` for NEW clauses.
        """
        contract = FEATURE_END_CONTRACTS[clause]
        text = self.skill_text
        present = all(token in text for token in contract.present_substrings)
        is_new = (
            contract.master_absent_substring is not None
            and contract.master_absent_substring in text
        )
        return ClauseVerdict(
            clause=clause,
            kind=contract.kind,
            present=present,
            is_new=is_new,
        )
