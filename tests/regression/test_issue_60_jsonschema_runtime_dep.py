"""Regression guard: jsonschema MUST be a base runtime dependency.

Background (Issue #60, nWave-ai/nWave):
`nwave_ai/outcomes/application/registry_service.py:16` does a module-top-level
`from jsonschema import Draft7Validator`, reached unconditionally via the
user-facing `nwave-ai outcomes ...` CLI path
(`nwave_ai/cli.py:main` -> `nwave_ai/outcomes/cli.py`). But `jsonschema` was
declared only under the `dev` / `test` optional-dependency extras, never in
`[project].dependencies`. A clean install (`uv tool install nwave-ai`,
`pip install nwave-ai`) therefore never pulls it, and the first `outcomes`
command crashes with `ModuleNotFoundError: No module named 'jsonschema'`.

The fix promotes `jsonschema>=4.0.0` to `[project].dependencies`. This test
locks that contract so the runtime import can never again rely on an extra.

Refs: https://github.com/nWave-ai/nWave/issues/60
"""

from __future__ import annotations

import re
from pathlib import Path


try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


PYPROJECT_PATH = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"

# Third-party modules imported at module-import time on the `outcomes` CLI path.
RUNTIME_IMPORTED_PACKAGE = "jsonschema"


def _load_pyproject() -> dict:
    with open(PYPROJECT_PATH, "rb") as f:
        return tomllib.load(f)


def _base_dependency_names() -> set[str]:
    """Normalized distribution names declared in [project].dependencies."""
    deps = _load_pyproject()["project"]["dependencies"]
    names: set[str] = set()
    for spec in deps:
        # Strip extras, version specifiers, and environment markers:
        #   "tomli>=2.0.0; python_version < '3.11'" -> "tomli"
        name = re.split(r"[\s<>=!~;\[]", spec, maxsplit=1)[0]
        names.add(name.lower().replace("_", "-"))
    return names


def test_jsonschema_is_a_base_runtime_dependency() -> None:
    """jsonschema is imported unconditionally at runtime, so it must be a base dep."""
    assert RUNTIME_IMPORTED_PACKAGE in _base_dependency_names(), (
        f"{RUNTIME_IMPORTED_PACKAGE!r} is imported at runtime by the outcomes CLI "
        "but is not declared in [project].dependencies — a clean install will "
        "crash with ModuleNotFoundError (Issue #60)."
    )
