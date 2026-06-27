"""Fixtures for the plugin/skill deliverable-type acceptance suite.

The single ``composition`` fixture builds the production composition root over a
``tmp_path`` project + sandbox HOME. Parser converters in
``steps_plugin_skill.py`` coerce Gherkin literals into the typed ``domain_types``
enums so step bodies stay logic-free (Mandate-12 criterion 3).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.des.acceptance.plugin_skill_deliverable_type.steps.composition import (
    build_production_composition,
)


@pytest.fixture
def composition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Production composition root over an isolated project + sandbox HOME.

    HOME is redirected so the real ``DESConfig`` reads the sandbox
    ``~/.nwave/global-config.json`` rather than the developer's. The project root
    is a fresh ``tmp_path/project``.
    """
    return build_production_composition(tmp_path, monkeypatch)
