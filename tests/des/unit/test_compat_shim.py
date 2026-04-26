"""Regression tests for the typing-compat shim and ruff target-version pin.

Issue #43 — HARDENING layer per RCA. Two complementary defenses against
typing-version regressions:

1. ``src/des/_compat.py`` — designated location for typing-3.11+ symbols
   backported via ``typing_extensions`` for Python 3.10 support.
2. ``[tool.ruff] target-version = "py310"`` — makes ruff statically flag
   3.11+-only typing imports as ``UP`` errors at lint time, before merge.

These tests are the regression net: they fail the moment either defense
is removed or weakened.
"""

from __future__ import annotations

import sys
from pathlib import Path


try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]  # Python 3.10 fallback


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_compat_shim_exports_self() -> None:
    """The ``_compat`` shim must export ``Self`` on every supported Python."""
    from des._compat import Self

    assert Self is not None, "Self must be importable from des._compat"

    if sys.version_info >= (3, 11):
        import typing

        assert Self is typing.Self, (
            "On Python 3.11+, des._compat.Self must be the stdlib typing.Self"
        )
    else:
        import typing_extensions

        assert Self is typing_extensions.Self, (
            "On Python 3.10, des._compat.Self must fall back to typing_extensions.Self"
        )


def test_compat_shim_advertises_self_in_dunder_all() -> None:
    """``__all__`` must list ``Self`` so star-imports stay explicit."""
    import des._compat as compat

    assert hasattr(compat, "__all__"), "des._compat must define __all__"
    assert "Self" in compat.__all__, "Self must be advertised in __all__"


def test_ruff_target_version_is_py310() -> None:
    """``[tool.ruff] target-version`` must be pinned to ``py310``.

    This pin makes ruff fail-fast on bare ``from typing import Self`` (and
    other 3.11+-only symbols) before they reach CI on Python 3.10 runners.
    """
    pyproject = REPO_ROOT / "pyproject.toml"
    assert pyproject.is_file(), f"pyproject.toml not found at {pyproject}"

    with pyproject.open("rb") as handle:
        config = tomllib.load(handle)

    ruff_section = config.get("tool", {}).get("ruff", {})
    target_version = ruff_section.get("target-version")

    assert target_version == "py310", (
        f"[tool.ruff] target-version must be 'py310' to catch 3.11+ "
        f"typing imports at lint time; got {target_version!r}"
    )
