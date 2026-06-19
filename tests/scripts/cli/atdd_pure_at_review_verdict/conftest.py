"""pytest-bdd configuration for the slice-07 author-ahead acceptance set.

ATDD-pure author-ahead lifecycle: this AT set is authored and reviewed
ahead of its slice's implementation, so its scenarios are RED-by-design.
They are tagged ``@xfail`` in the ``.feature`` file from the author-ahead
commit until the slice-07 crafter removes the marker at the GREEN phase.
This is a transient lifecycle state, not a deferral/park.

This hook translates the bare ``xfail`` Gherkin tag into a proper
``pytest.mark.xfail`` carrying the lifecycle reason and ``strict=False``
(so the scenarios report ``xpass`` rather than error once the slice lands).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import pytest


_XFAIL_REASON = (
    "ATDD-pure author-ahead: slice-07 ATs authored + reviewed, "
    "implementation pending; the slice-07 crafter removes this xfail "
    "at the GREEN phase"
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
