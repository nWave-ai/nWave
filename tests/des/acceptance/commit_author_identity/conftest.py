"""Slice-gating for the commit-author-identity acceptance suite.

DELIVER unskips one slice at a time (RED -> GREEN -> COMMIT). The gherkin tags
in the ``.feature`` files name the enforcement layer each scenario drives
(``@precommit`` / ``@prepush`` / ``@ci`` / ``@regression_anchor``). While a later
slice's production entry is still a RED scaffold, this hook skips that layer's
scenarios so the suite stays green for the slice currently under construction.

The set below shrinks to empty as slices land; once it is empty every scenario
in this feature directory runs. ``pytest_bdd_apply_tag`` is ``firstresult`` and
per-directory conftests fire before the root conftest, so returning ``None`` for
tags this hook does not gate lets the root hook apply registered markers
(``tests/conftest.py``).
"""

from __future__ import annotations

import pytest


#: Enforcement-layer gherkin tags whose production entry is not yet implemented.
#: DELIVER removes a tag from this set as its slice reaches GREEN. All slices
#: (S1 core, S2 pre-commit, S3 pre-push, S4 CI, S5 anchor) have landed, so the
#: set is empty and every scenario in this directory runs.
_PENDING_SLICE_TAGS: set[str] = set()


def pytest_bdd_apply_tag(tag, function):
    """Skip scenarios for layers still under construction; defer otherwise."""
    if tag in _PENDING_SLICE_TAGS:
        marker = pytest.mark.skip(
            reason=f"slice not yet delivered (@{tag}) — DELIVER unskips per slice"
        )
        return marker(function)
    return None
