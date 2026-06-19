"""pytest-bdd configuration for the parked private-skill-leak acceptance track.

The installer-fix Track 2 is deferred — its acceptance scenarios are
RED-by-design because the fix is not yet implemented. They are tagged
``@xfail`` in the ``.feature`` files so they remain tracked and visible
without failing the whole-tree suite.

This hook translates the bare ``xfail`` Gherkin tag into a proper
``pytest.mark.xfail`` carrying the deferral reason and ``strict=False``
(so the scenarios report ``xpass`` rather than error once the fix lands).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import pytest


_XFAIL_REASON = (
    "installer-fix Track 2 parked — fix not yet implemented; "
    "see docs/analysis/rca-installer-private-skill-leak-2026-05-20.md"
)

_T = TypeVar("_T")


def pytest_bdd_apply_tag(
    tag: str, function: Callable[..., _T]
) -> Callable[..., _T] | None:
    """Rewrite the ``xfail`` scenario tag into a reasoned, non-strict xfail mark.

    Returning ``None`` for any other tag lets pytest-bdd fall back to its
    default behaviour (``getattr(pytest.mark, tag)``).
    """
    if tag == "xfail":
        return pytest.mark.xfail(reason=_XFAIL_REASON, strict=False)(function)
    return None
