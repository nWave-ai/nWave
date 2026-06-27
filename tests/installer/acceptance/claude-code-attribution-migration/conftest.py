"""SANDBOX fixtures + step registration for claude-code-attribution-migration.

SANDBOX contract (HARD requirement): every scenario runs against an isolated
``$HOME`` rooted in ``tmp_path``. ``~/.claude`` and ``~/.nwave`` are NEVER the
real ones. Isolation is achieved by monkeypatching ``HOME`` (so ``Path.home()``
resolves into the sandbox) and unsetting ``CLAUDE_CONFIG_DIR``. Follows the
backup-retention-policy conftest precedent.

Because the feature directory name is hyphenated, ``steps/steps_attribution.py``
cannot be imported by a dotted name under ``--import-mode=importlib``. It is
loaded by file path here and its public step functions + fixtures are injected
into this conftest's namespace so pytest-bdd discovers them. The thin
``test_*.py`` binder files at the feature root bind each scenario via
``@scenario`` (backup-retention-policy precedent).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Load step definitions by file path and inject their public names here.
# ---------------------------------------------------------------------------

_steps_path = Path(__file__).parent / "steps" / "steps_attribution.py"
_spec = importlib.util.spec_from_file_location(
    "attribution_migration_steps", str(_steps_path)
)
_steps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_steps)

for _name in dir(_steps):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_steps, _name)


# ---------------------------------------------------------------------------
# SANDBOX fixtures — isolated HOME; ~/.claude and ~/.nwave live inside tmp_path.
# ---------------------------------------------------------------------------


@pytest.fixture
def sandbox_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated developer HOME rooted in tmp_path.

    ``~/.claude`` and ``~/.nwave`` are NOT created eagerly — Given steps build
    exactly the world each scenario needs (absence is a valid world).
    """
    home_dir = tmp_path / "dev-home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    return home_dir


@pytest.fixture
def scenario_state() -> dict:
    """Mutable bag threaded across Given/When/Then within one scenario."""
    return {
        "install_log": [],
        "settings_before": None,
    }
