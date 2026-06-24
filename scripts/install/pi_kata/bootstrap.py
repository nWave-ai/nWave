"""Kata-session bootstrap + kata-manifest writer -- RED scaffold (created by DISTILL).

NEW surface for pi-kata-tdd-flow (ADR-PKT-001 KD1/KD2). The pi ``registerCommand``
handler (TS, in the extension template) delegates the deterministic bootstrap to
this Python helper: it runs ``des-init-log`` for the kata's deliver dir and writes
the ``kata-manifest.json`` carrying ``(project-id, current step-id, cwd)`` plus a
deliver-session marker. Manifest writes are atomic (temp-then-move) and re-read-
asserted (ADR-PKT-001 H3).

REUSES UNCHANGED: ``des.cli.init_log`` (K2 -- zero ``src/des/**`` change). This
module only orchestrates the reused CLI + owns the manifest file (contract-shape
``bounded-change``).
"""

from __future__ import annotations


__SCAFFOLD__ = True


def bootstrap_kata_session(
    *,
    project_root: str,
    kata_id: str,
) -> dict:
    """Initialize a DES-tracked kata session and write the kata manifest.

    Runs ``des-init-log`` for ``docs/feature/{kata_id}/deliver`` (idempotent --
    a re-bootstrap of an already-initialized session must not clobber the log),
    then writes ``kata-manifest.json`` with project-id = kata_id, first step-id
    ``01-01``, and cwd = project_root, plus a deliver-session marker.

    Returns an observable result dict: ``{"status": "bootstrapped", "manifest":
    {...}}`` on success, or ``{"status": "refused", "reason": "..."}`` when the
    project is not activated for the kata harness (an observable refusal contract,
    never a raised exception).
    """
    raise AssertionError("Not yet implemented -- RED scaffold")


def read_kata_manifest(*, project_root: str, kata_id: str) -> dict:
    """Re-read and return the persisted kata manifest (ADR-PKT-001 H3)."""
    raise AssertionError("Not yet implemented -- RED scaffold")


def advance_step_id(*, project_root: str, kata_id: str) -> str:
    """Increment the manifest's current step-id (``01-NN`` convention, KD2).

    Atomic write + re-read-assert. Returns the new step-id. A fresh per-step id
    is required every cycle (SPIKE constraint 3: never reuse a step-id).
    """
    raise AssertionError("Not yet implemented -- RED scaffold")
