"""Fixtures + parser converters for the activation-gating acceptance suite.

The single ``composition`` fixture builds the production composition root over a
``tmp_path`` project + sandbox HOME. Parser converters coerce Gherkin literals
into the typed ``domain_types`` enums so step bodies stay logic-free
(Mandate-12 criterion 3).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.des.acceptance.activation_gating.steps.composition import (
    ActivationGatingComposition,
)


@pytest.fixture
def composition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Production composition root over an isolated project + sandbox HOME.

    HOME is redirected so the real ``DESConfig`` / CLI ``_get_config_dir`` read
    the sandbox ``~/.nwave/global-config.json`` rather than the developer's. The
    project root is a fresh ``tmp_path/project``.
    """
    project_root = tmp_path / "project"
    home_dir = tmp_path / "home"
    project_root.mkdir(parents=True, exist_ok=True)
    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))
    return ActivationGatingComposition(project_root=project_root, home_dir=home_dir)
