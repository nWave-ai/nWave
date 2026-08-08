"""Regression guard for issue #83 — nw-finalize contradicted itself.

The nw-finalize prompt assets stated both that the feature workspace
``docs/feature/{feature-id}/`` is preserved (Phase C step 3, which also
names the system-level consequence: the wave-status matrix derives feature
status from that directory) and that it is removed (Overview, Phase D,
Success Criteria, Example, Deliverables, Expected Outputs, plus a literal
``rm -rf`` in the command asset).

WHEN the nw-finalize prompt assets are read, the system SHALL find no
statement asserting that the feature workspace is deleted, removed, or
cleaned.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# plugins/nw/** is the release-pipeline-managed marketplace payload and is on
# the mirror denylist, so it is not edited from an external PR. Only the two
# source assets are guarded here.
FINALIZE_ASSETS = (
    Path("nWave/skills/nw-finalize/SKILL.md"),
    Path("nWave/tasks/nw/finalize.md"),
)

# Patterns that assert destruction of the feature workspace.
REMOVAL_PATTERNS = (
    # Any destructive verb aimed at the feature workspace path, however phrased.
    # The first pattern is the general one; the rest catch phrasings that do not
    # name the path on the same line.
    re.compile(
        r"(rm\s+-rf|delete|deletes|deleted|remove|removes|removed|purge|purged)"
        r"[^\n]{0,40}docs/feature",
        re.IGNORECASE,
    ),
    re.compile(r"docs/feature[^\n]{0,40}(is|are|be)\s+(deleted|removed|purged)", re.IGNORECASE),
    re.compile(r"workspace\s+(removal|removed|deleted|deletion|purged)", re.IGNORECASE),
    re.compile(r"(removes?|deletes?|purges?)\s+(the\s+)?(feature\s+)?workspace", re.IGNORECASE),
    re.compile(r"cleaned\s+workspace", re.IGNORECASE),
    re.compile(r"(Removed|Deleted):\s*docs/feature", re.IGNORECASE),
    re.compile(r"temporary\s+workspace", re.IGNORECASE),
    # "discard" applied to wave artifacts reads as deletion even when the author
    # meant "not copied" — the ambiguity that made this bug survivable.
    re.compile(r"Why\s+discard", re.IGNORECASE),
    re.compile(r"disposable\s+after", re.IGNORECASE),
)


# A line may legitimately mention removal while asserting retention — "removes
# session markers only; docs/feature/{id}/ is retained" is correct and must not
# trip the guard. Proximity alone cannot separate the two, so a line carrying an
# explicit retention marker is exempt. This is the guard's known limit: it
# detects unqualified removal claims, not every conceivable phrasing.
RETENTION_MARKERS = (
    re.compile(r"is\s+retained", re.IGNORECASE),
    re.compile(r"(is|are)\s+NOT\s+(deleted|removed)", re.IGNORECASE),
    re.compile(r"Do\s+NOT\s+(delete|remove)", re.IGNORECASE),
    re.compile(r"preserv", re.IGNORECASE),
    re.compile(r"never\s+means", re.IGNORECASE),
    re.compile(r"not\s+copied", re.IGNORECASE),
    re.compile(r"stays?\s+in", re.IGNORECASE),
    re.compile(r"remain", re.IGNORECASE),
)


def _asserts_removal(line: str) -> bool:
    """True when *line* claims the workspace is destroyed, unqualified."""
    if any(marker.search(line) for marker in RETENTION_MARKERS):
        return False
    return any(pattern.search(line) for pattern in REMOVAL_PATTERNS)


@pytest.mark.parametrize("asset", FINALIZE_ASSETS, ids=lambda p: str(p))
def test_finalize_asset_never_asserts_workspace_removal(asset: Path) -> None:
    path = REPO_ROOT / asset
    assert path.is_file(), f"missing finalize asset: {asset}"

    offenders = [
        f"{asset}:{lineno}: {line.strip()}"
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if _asserts_removal(line)
    ]

    assert not offenders, "workspace-removal assertions found:\n" + "\n".join(offenders)


@pytest.mark.parametrize("asset", FINALIZE_ASSETS, ids=lambda p: str(p))
def test_finalize_asset_states_workspace_is_preserved(asset: Path) -> None:
    text = (REPO_ROOT / asset).read_text(encoding="utf-8")
    assert "wave matrix derives status" in text.lower() or (
        "wave-status matrix" in text.lower()
    ), f"{asset} does not state why the workspace is preserved"
