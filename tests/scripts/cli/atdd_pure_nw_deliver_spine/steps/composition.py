"""Composition root for the nw-deliver spine-branch coherence slice.

slice-04 of the atdd-pure-roadmap-free-rollout (ADR-028 D5). Mandate-12 +
Pillar 3: business logic lives here as the single source of truth; step bodies
delegate to ``SpineCoherenceComposition`` methods and never inline logic.

WHY this is a coherence composition and not a CLI composition
-------------------------------------------------------------
slice-04 ships only ``nWave/skills/nw-deliver/SKILL.md`` -- prose, no executable
entry point (verified: no ``nw_deliver``/``deliver`` orchestrator under
``src/`` or ``scripts/``; ``carpaccio_slice_gate.py`` does not parse the slice
``Class`` column). There is no driving-port CLI to invoke. The driving surface
is the SKILL.md *content*: the coherence test reads the file and asserts the
four slice-04 spine-branch contract clauses are present with correct mode
scoping (the Class-P executable-coherence-test mechanism the rollout's own
``[REF] Slice classes`` section mandates -- feature-delta L160-163,
slice-10 precedent L621-671).

Regression contract: every assertion FAILS on master and PASSES once slice-04
lands. On master ``nw-deliver/SKILL.md`` frames atdd_pure as an *inner 7-phase
A->G replacement* of the classic per-step cycle (L78) -- it does NOT branch the
whole spine, skip Phase 1 roadmap, provision the telemetry ledger dir, or route
on the slice Class column. Each contract's ``master_absent_substring`` is
verified absent on master, so the coherence assertions are genuine
missing-functionality RED, not test bugs.

The SUT is the real shipped file at its real repo path -- the production
artifact, read as-is (Pillar 3: app as in production, no hand-built fixture
copy of the skill).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .domain_types import (
    SPINE_CONTRACTS,
    ClauseKind,
    RepoRelPath,
    SetupProvision,
    SpineClause,
    WorkflowMode,
)


# Repo root: this file is tests/scripts/cli/atdd_pure_nw_deliver_spine/steps/
# composition.py -> five parents up is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[5]

# The single slice-04 deliverable under coherence audit.
_NW_DELIVER_SKILL = RepoRelPath("nWave/skills/nw-deliver/SKILL.md")

# Tokens that prove the atdd_pure Setup provisions the AT-completion ledger
# tree in place of the skipped des-init-log step (ADR-028 D3/D5). Verified
# absent on master.
_SETUP_PROVISION_TOKENS: dict[SetupProvision, tuple[str, ...]] = {
    SetupProvision.TELEMETRY_LEDGER_DIR: ("mkdir -p .nwave/telemetry/atdd-pure",),
}

# Token proving the telemetry schema is bumped to 1.1.0 for the atdd_pure
# per-phase-boundary record (ADR-028 D5). On master nw-deliver/SKILL.md L138
# carries telemetry_schema_version "1.0.0" only.
_TELEMETRY_SCHEMA_TOKEN = "1.1.0"

# The stable classic Phase-1 heading phrase (SKILL.md L257 numbered section
# title). Anchoring on the full heading -- not the bare token "Roadmap
# Creation" -- keeps the classic-preservation check robust against unrelated
# prose (review non-blocking item).
_CLASSIC_PHASE_1_HEADING = "Phase 1 — Roadmap Creation + Review"


@dataclass(frozen=True)
class ClauseVerdict:
    """Observable outcome of evaluating one spine-branch contract clause.

    ``kind``    -- NEW or PRESERVATION (mirrors the contract's kind so the step
                   layer can decide whether the ``is_new`` assertion applies).
    ``present`` -- every mandated substring for the clause appears in the file.
    ``is_new``  -- the clause's master-absent token is currently in the file
                   (it has been added by slice-04). Meaningful only for a NEW
                   clause; always False for a PRESERVATION clause (which has no
                   master-absent token and asserts presence, never newness).
    """

    clause: SpineClause
    kind: ClauseKind
    present: bool
    is_new: bool


@dataclass
class SpineCoherenceComposition:
    """Production-wired composition root for the nw-deliver spine coherence slice.

    The SUT is the real ``nWave/skills/nw-deliver/SKILL.md`` at its repo path.
    ``load`` reads it once; the ``assert_*`` methods are the single source of
    truth for every coherence predicate -- step bodies only call them.
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

    # --- service: evaluate a spine-branch contract clause --------------------

    def evaluate_clause(self, clause: SpineClause) -> ClauseVerdict:
        """Evaluate one slice-04 spine-branch contract clause against the file.

        Business-logic SSOT (Mandate-12): the present / is-new computation
        lives here, never in a step body.

        ``is_new`` is meaningful only for a NEW-kind clause: it is True once
        the master-absent token has been added by slice-04. For a PRESERVATION
        clause the contract carries no master-absent token, so ``is_new`` is
        reported False -- a preservation clause asserts presence, never
        newness. The step layer reads ``contract.kind`` and only asserts
        ``is_new`` for NEW clauses.
        """
        contract = SPINE_CONTRACTS[clause]
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

    def setup_provisions(self, provision: SetupProvision) -> bool:
        """True iff the atdd_pure Setup prose provisions the given resource."""
        tokens = _SETUP_PROVISION_TOKENS[provision]
        return all(token in self.skill_text for token in tokens)

    def telemetry_schema_is_bumped(self) -> bool:
        """True iff the SKILL.md declares the 1.1.0 atdd_pure telemetry schema."""
        return _TELEMETRY_SCHEMA_TOKEN in self.skill_text

    def classic_phase_1_still_documented(self) -> bool:
        """True iff the classic roadmap Phase 1 prose is still present.

        slice-04 must preserve the classic spine (AT c) -- it adds the
        atdd_pure sibling workflow ALONGSIDE the classic one, never deleting
        classic roadmap creation. This guards against an over-eager rewrite
        that drops the classic path.

        Anchored to the stable Phase-1 heading phrase
        ``Phase 1 — Roadmap Creation + Review`` (the SKILL.md L257 numbered
        section title), not the bare token ``Roadmap Creation`` -- a bare
        token is fragile against unrelated prose mentioning a roadmap (review
        non-blocking item).
        """
        return _CLASSIC_PHASE_1_HEADING in self.skill_text


# Convenience: phrase -> WorkflowMode is re-exported so step modules import
# one place. (Kept here so the steps file has a single composition import.)
def workflow_mode(value: str) -> WorkflowMode:
    """Coerce a Gherkin mode token to the typed WorkflowMode."""
    return WorkflowMode(value)
