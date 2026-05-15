"""Public test API for state-delta assertions (project-local re-export).

This module is the canonical IMPORT POINT for test authors. It is a thin
re-export wrapper around :mod:`nwave_ai.state_delta`; see that module's
docstring for the full API contract.

Usage::

    from tests.common.state_delta import (
        assert_state_delta,
        set_to, unchanged, appended_with, prepended_with,
        containing, normalized_to, idempotent_after, legacy_healed,
    )

    assert_state_delta(
        before,
        after,
        universe={"PATH", "exit_code"},
        expected={"PATH": prepended_with("/des/bin")},
    )

Other-language ports of this surface live at ``tests/common/state_delta.<ext>``
(``.ts``, ``.cs``, ``.java``, ``.kt``, ``.rs``, ``.go``) and are bootstrapped
on first DISTILL invocation by ``nw-acceptance-designer`` per the polyglot
adapter matrix documented in the ``nw-distill`` skill.
"""

from __future__ import annotations

from nwave_ai.state_delta import (
    MatcherResult,
    Perturbation,
    Predicate,
    Violation,
    appended_with,
    assert_state_delta,
    chaos_env_perturbation,
    chaos_filesystem_truncation,
    chaos_ordering_swap,
    containing,
    enumerate_perturbations,
    enumerate_perturbations_strategy,
    idempotent_after,
    legacy_healed,
    normalized_to,
    prepended_with,
    set_to,
    unchanged,
)


__all__ = [
    "MatcherResult",
    "Perturbation",
    "Predicate",
    "Violation",
    "appended_with",
    "assert_state_delta",
    "chaos_env_perturbation",
    "chaos_filesystem_truncation",
    "chaos_ordering_swap",
    "containing",
    "enumerate_perturbations",
    "enumerate_perturbations_strategy",
    "idempotent_after",
    "legacy_healed",
    "normalized_to",
    "prepended_with",
    "set_to",
    "unchanged",
]
