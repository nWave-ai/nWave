"""Fixtures + parser converters for the attribution-activation-coupling suite.

The single ``composition`` fixture builds the production composition root over a
``tmp_path`` project + sandbox HOME. HOME is redirected so the real
``AttributionPlugin``, the real ``attribution on|off|status`` CLI, the real
``AttributionCheck`` doctor check, and the reused ``DESConfig`` all resolve the
sandbox ``~/.claude`` + ``~/.nwave`` — NEVER the operator's real home.

Parser converters coerce Gherkin literals into the typed ``domain_types`` enums
so step bodies stay logic-free (Mandate-12 criterion 3).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .composition import AttributionCouplingComposition


def pytest_bdd_apply_tag(tag: str, function):
    """Translate Gherkin tags without tripping ``--strict-markers``.

    ``@skip`` marks a scenario pending (one-at-a-time unskip in DELIVER). Every
    other tag (`@ab-N`, `@driving_port`, `@error`, `@real-io`,
    `@contract-shape:*`, `@walking_skeleton`, feature-level descriptors) is
    documentation/classification only — absorbed here so pytest-bdd does not
    register it as an unknown strict marker. Returning True signals "handled".
    """
    if tag == "skip":
        marker = pytest.mark.skip(reason="DISTILL scaffold — unskip in DELIVER")
        marker(function)
        return True
    # All other tags are descriptive: absorb them (no strict-marker registration).
    return True


@pytest.fixture
def composition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AttributionCouplingComposition:
    """Production composition root over an isolated project + sandbox HOME."""
    project_root = tmp_path / "project"
    home_dir = tmp_path / "home"
    project_root.mkdir(parents=True, exist_ok=True)
    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))
    return AttributionCouplingComposition(home_dir=home_dir, project_root=project_root)
