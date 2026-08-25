"""Regression oracle for nWave-ai/nWave issue #83.

Finalization has two independently observable effects: delivery history remains
available to the wave matrix, while session-only resume state disappears.  The
Claude skill and command projection must state that same law and must not offer
a destructive alternative.
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
FINALIZE_SURFACES = (
    REPO_ROOT / "nWave" / "skills" / "nw-finalize" / "SKILL.md",
    REPO_ROOT / "nWave" / "tasks" / "nw" / "finalize.md",
)

PRESERVE_HISTORY = "Preserve delivery history"
REMOVE_SESSION_ONLY = "Remove session artifacts only"
DESTRUCTIVE_ALTERNATIVES = (
    "rm -rf docs/feature/{feature-id}/",
    "Workspace directory removed: docs/feature/{feature-id}/",
    "Removed: docs/feature/{feature-id}/",
    "workspace removal",
)


@pytest.mark.parametrize("surface", FINALIZE_SURFACES, ids=lambda path: path.name)
def test_finalize_preserves_history_and_removes_session_state_only(
    surface: Path,
) -> None:
    """Every executable projection states one non-destructive final state."""
    text = surface.read_text(encoding="utf-8")

    assert PRESERVE_HISTORY in text, (
        f"{surface.relative_to(REPO_ROOT)} must make delivery-history preservation "
        "an explicit finalize observation"
    )
    assert REMOVE_SESSION_ONLY in text, (
        f"{surface.relative_to(REPO_ROOT)} must limit cleanup to session artifacts"
    )

    contradictions = [phrase for phrase in DESTRUCTIVE_ALTERNATIVES if phrase in text]
    assert not contradictions, (
        f"{surface.relative_to(REPO_ROOT)} still permits destructive finalize state: "
        f"{contradictions}"
    )
