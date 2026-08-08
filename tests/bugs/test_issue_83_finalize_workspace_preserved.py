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
    re.compile(r"rm\s+-rf\s+docs/feature", re.IGNORECASE),
    re.compile(r"workspace\s+(removal|removed)", re.IGNORECASE),
    re.compile(r"removes?\s+(the\s+)?workspace", re.IGNORECASE),
    re.compile(r"cleaned\s+workspace", re.IGNORECASE),
    re.compile(r"Removed:\s*docs/feature", re.IGNORECASE),
    re.compile(r"Workspace\s+directory\s+removed", re.IGNORECASE),
)


@pytest.mark.parametrize("asset", FINALIZE_ASSETS, ids=lambda p: str(p))
def test_finalize_asset_never_asserts_workspace_removal(asset: Path) -> None:
    path = REPO_ROOT / asset
    assert path.is_file(), f"missing finalize asset: {asset}"

    offenders = [
        f"{asset}:{lineno}: {line.strip()}"
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        for pattern in REMOVAL_PATTERNS
        if pattern.search(line)
    ]

    assert not offenders, "workspace-removal assertions found:\n" + "\n".join(offenders)


@pytest.mark.parametrize("asset", FINALIZE_ASSETS, ids=lambda p: str(p))
def test_finalize_asset_states_workspace_is_preserved(asset: Path) -> None:
    text = (REPO_ROOT / asset).read_text(encoding="utf-8")
    assert "wave matrix derives status" in text.lower() or (
        "wave-status matrix" in text.lower()
    ), f"{asset} does not state why the workspace is preserved"
