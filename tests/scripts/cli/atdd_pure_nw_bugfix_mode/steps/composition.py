"""Composition root for the nw-bugfix mode-awareness coherence slice.

slice-05 of the atdd-pure-roadmap-free-rollout (ADR-028 D5; feature-delta
``### slice-05`` design note, L527-546). Mandate-12 + Pillar 3: business logic
lives here as the single source of truth; step bodies delegate to
``BugfixModeCoherenceComposition`` methods and never inline logic.

WHY this is a coherence composition and not a CLI composition
-------------------------------------------------------------
slice-05 ships only ``nWave/skills/nw-bugfix/SKILL.md`` -- prose, no executable
entry point. The file is a slash-command instruction set (``user-invocable:
true`` frontmatter) an LLM interprets, not code with a callable surface. There
is no driving-port CLI to invoke. The driving surface is the SKILL.md
*content*: the coherence test reads the production file and asserts the
slice-05 mode-awareness contract clauses (the Class-P executable-coherence-test
mechanism the rollout's own ``[REF] Slice classes`` section mandates --
feature-delta L199-202, slice-04 precedent).

Regression contract: every NEW / ABSENCE assertion FAILS on master and PASSES
once slice-05 lands. On master ``nw-bugfix/SKILL.md`` is mode-UNAWARE -- Phase 3
always delegates to ``/nw-deliver`` which "creates a minimal roadmap" (L108),
with no ``workflow.mode`` branch, no ``atdd_pure`` path, no ``carpaccio``
vocabulary, no ``/nw-execute`` per-slice cycle. Each NEW contract's
``master_absent_substring`` is verified absent on master and the ABSENCE
contract's ``master_present_substring`` is verified present, so the coherence
assertions are genuine missing-functionality RED, not test bugs.

The SUT is the real shipped file at its real repo path -- the production
artifact, read as-is (Pillar 3: app as in production, no hand-built fixture
copy of the skill).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .domain_types import (
    SLICE_05_CONTRACTS,
    BugfixClause,
    ClauseKind,
    RepoRelPath,
)


# Repo root: this file is tests/scripts/cli/atdd_pure_nw_bugfix_mode/steps/
# composition.py -> five parents up is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[5]

# The single slice-05 deliverable under coherence audit.
_NW_BUGFIX_SKILL = RepoRelPath("nWave/skills/nw-bugfix/SKILL.md")


@dataclass(frozen=True)
class ClauseVerdict:
    """Observable outcome of evaluating one bugfix-mode contract clause.

    ``clause``    -- which slice-05 clause this verdict is for.
    ``kind``      -- NEW, ABSENCE or PRESERVATION (mirrors the contract's kind so
                     the step layer can decide which assertion applies).
    ``satisfied`` -- the clause's post-slice contract holds against the file:
                     for NEW / PRESERVATION, every present_substring appears;
                     for ABSENCE, the stale phrase is gone.
    ``regressed_from_master`` -- the clause's master signal is in the post-slice
                     state expected by slice-05: for a NEW clause the
                     master-absent token is now in the file; for an ABSENCE
                     clause the master-present token is now gone. Meaningful
                     only for NEW / ABSENCE; always False for PRESERVATION
                     (which carries no master signal -- it asserts presence,
                     never a master delta).
    """

    clause: BugfixClause
    kind: ClauseKind
    satisfied: bool
    regressed_from_master: bool


@dataclass
class BugfixModeCoherenceComposition:
    """Production-wired composition root for the nw-bugfix coherence slice.

    The SUT is the real ``nWave/skills/nw-bugfix/SKILL.md`` at its repo path.
    ``load`` reads it once; the ``evaluate_clause`` method is the single source
    of truth for every coherence predicate -- step bodies only call it.
    """

    repo_root: Path = field(default=_REPO_ROOT)
    _skill_text: str | None = field(default=None, repr=False)

    # --- Given: load the SUT -------------------------------------------------

    def load_nw_bugfix_skill(self) -> None:
        """Read the production nw-bugfix SKILL.md into the composition."""
        self._skill_text = (self.repo_root / _NW_BUGFIX_SKILL).read_text(
            encoding="utf-8"
        )

    @property
    def skill_text(self) -> str:
        """The loaded SKILL.md content (raises if load was skipped)."""
        if self._skill_text is None:  # defensive: a Given must run first
            raise AssertionError("nw-bugfix SKILL.md not loaded")
        return self._skill_text

    # --- service: evaluate a bugfix-mode contract clause ---------------------

    def evaluate_clause(self, clause: BugfixClause) -> ClauseVerdict:
        """Evaluate one slice-05 bugfix-mode contract clause against the file.

        Business-logic SSOT (Mandate-12): the satisfied / regressed-from-master
        computation lives here, never in a step body.

        - NEW clause: ``satisfied`` iff every present_substring is in the file;
          ``regressed_from_master`` iff the master-absent token is now present
          (slice-05 added the prose).
        - ABSENCE clause: ``satisfied`` iff the stale master-present token is
          GONE; ``regressed_from_master`` is the same predicate (the removal IS
          the master delta).
        - PRESERVATION clause: ``satisfied`` iff every present_substring is in
          the file; ``regressed_from_master`` is always False -- a preservation
          clause has no master delta to claim.
        """
        contract = SLICE_05_CONTRACTS[clause]
        text = self.skill_text

        if contract.kind is ClauseKind.ABSENCE:
            # master_present_substring is non-None for ABSENCE (domain-types
            # __post_init__ guarantees it). Removal == satisfied == regressed.
            removed = contract.master_present_substring not in text
            return ClauseVerdict(
                clause=clause,
                kind=contract.kind,
                satisfied=removed,
                regressed_from_master=removed,
            )

        satisfied = all(token in text for token in contract.present_substrings)
        regressed = (
            contract.master_absent_substring is not None
            and contract.master_absent_substring in text
        )
        return ClauseVerdict(
            clause=clause,
            kind=contract.kind,
            satisfied=satisfied,
            regressed_from_master=regressed,
        )
