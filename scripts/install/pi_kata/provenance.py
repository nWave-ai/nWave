"""Post-hoc commit-trailer provenance backstop (ADR-PKT-001 D-PKT-4, R3).

WHY-NEW-FILE: scripts/install/pi_kata/provenance.py
  CLOSEST-EXISTING: scripts/install/pi_kata/transcript_context.py
  EXTENSION-COST: transcript_context.py is a pure marker-string assembler for the
    LIVE pre-commit gate (it invents no verdict); folding a post-hoc,
    verdict-producing git-verification reader into it would mix a decision-making
    checker into a deliberately decision-free assembler.
  PARALLEL-RATIONALE: different lifecycle and dependency set -- transcript_context
    runs at the pre-commit ``tool_call`` where no commit exists yet and only
    produces engine *input*; provenance runs post-hoc / in CI where commits exist
    and produces a pass/fail *verdict* by invoking the subprocess-backed
    GitCommitVerifier, a dependency the assembler never touches.

The LIVE gate (step 01-01) verifies phase-completeness at the pre-commit
``tool_call``. It logically CANNOT verify a not-yet-existing commit. So a model
could record its COMMIT phase, pass the live gate, then NOT ``git commit`` (or
commit with wrong trailers) -- the "recorded-but-not-committed" gap (R3).

This module is the backstop: AFTER the kata, every step that recorded a COMMIT
phase in ``execution-log.json`` MUST map to a real commit carrying BOTH
``Step-Id: {step}`` AND ``Task-Id: {kata_id}`` trailers (AND-semantics, the
SPIKE constraint). It REUSES the UNCHANGED engine ``GitCommitVerifier``
(``src/des/adapters/driven/git/``) -- the same component the *old* live gate
misused pre-commit, but now CORRECTLY, post-commit, where commits exist.

REUSES UNCHANGED: ``GitCommitVerifier`` (K2 -- zero ``src/des/**`` change). This
module only orchestrates the reused verifier over the kata's recorded-COMMIT
steps; it reimplements no git verification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from des.adapters.driven.git.git_commit_verifier import GitCommitVerifier
from scripts.install.pi_kata.bootstrap import read_kata_manifest


COMMIT_PHASE = "COMMIT"
EXECUTION_LOG_FILENAME = "execution-log.json"


@dataclass(frozen=True)
class ProvenanceResult:
    """Structured outcome of the post-hoc provenance check.

    Attributes:
        verified: True only when every recorded-COMMIT step maps to a matching
            ``Step-Id``+``Task-Id`` commit (AND-semantics).
        verified_steps: recorded-COMMIT step-ids that have a matching commit,
            in recorded order.
        unverified_steps: recorded-COMMIT step-ids with NO matching commit (the
            recorded-but-not-committed gap) or wrong/missing trailers.
        reasons: per-unverified-step human-readable reason (from the reused
            ``GitCommitVerifier``), keyed by step-id.
    """

    verified: bool
    verified_steps: list[str] = field(default_factory=list)
    unverified_steps: list[str] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)


def check_kata_provenance(*, project_root: str, kata_id: str) -> ProvenanceResult:
    """Verify every recorded-COMMIT step of a completed kata was truly committed.

    Reads the kata's ``execution-log.json`` for step-ids that recorded a COMMIT
    phase, reads the kata manifest for the project/Task-Id, and asserts each
    recorded-COMMIT step against ``git log`` by REUSING the UNCHANGED
    ``GitCommitVerifier`` with AND-semantics (``Step-Id`` AND ``Task-Id``).

    Returns a :class:`ProvenanceResult` naming any unverified steps -- the
    structured pass/fail a CI / ``des``-adjacent caller acts on.
    """
    root = Path(project_root)
    task_id = read_kata_manifest(project_root=project_root, kata_id=kata_id)[
        "project_id"
    ]
    recorded_commit_steps = _recorded_commit_steps(root, kata_id)

    verifier = GitCommitVerifier()
    verified_steps: list[str] = []
    unverified_steps: list[str] = []
    reasons: dict[str, str] = {}

    for step_id in recorded_commit_steps:
        outcome = verifier.verify_commit(
            step_id=step_id,
            cwd=str(root),
            feature_id_filter=task_id,
        )
        if outcome.verified:
            verified_steps.append(step_id)
            continue
        unverified_steps.append(step_id)
        reasons[step_id] = outcome.error_reason or "no matching commit found"

    return ProvenanceResult(
        verified=not unverified_steps,
        verified_steps=verified_steps,
        unverified_steps=unverified_steps,
        reasons=reasons,
    )


def _recorded_commit_steps(root: Path, kata_id: str) -> list[str]:
    """Step-ids that recorded a COMMIT phase, in first-recorded order (deduped)."""
    log_path = _deliver_dir(root, kata_id) / EXECUTION_LOG_FILENAME
    events = json.loads(log_path.read_text(encoding="utf-8")).get("events", [])

    ordered_steps: list[str] = []
    for event in events:
        if event.get("p") != COMMIT_PHASE:
            continue
        step_id = event["sid"]
        if step_id not in ordered_steps:
            ordered_steps.append(step_id)
    return ordered_steps


def _deliver_dir(root: Path, kata_id: str) -> Path:
    return root / "docs" / "feature" / kata_id / "deliver"
