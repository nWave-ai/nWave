"""nwave_ai.state_delta — public test API for state-transition assertions.

This package is the canonical Python port of the polyglot state-delta matcher
documented in the ``nw-distill`` and ``nw-test-design-mandates`` skill files
(see "Polyglot Adapter Matrix"). It is the **public test API** for nWave-built
projects: tests at layers 1-3 (unit, in-memory acceptance, subprocess) that
mutate observable state assert via :func:`assert_state_delta`.

Canonical import point for test authors
---------------------------------------

The recommended import path is the project-local thin re-export wrapper::

    from tests.common.state_delta import (
        assert_state_delta, set_to, unchanged, prepended_with,
    )

Direct imports from ``nwave_ai.state_delta`` continue to work for backwards
compatibility::

    from nwave_ai.state_delta import assert_state_delta, set_to  # also valid

Public surface
--------------

Canonical assertion:

* :func:`assert_state_delta` ``(before, after, universe, expected) -> None``
  — fails closed when any key in ``universe`` not in ``expected`` mutates,
  or when any expected predicate evaluates ``False``.

Predicates (compose :class:`Predicate` callables ``(old, new) -> bool``):

* :func:`set_to` — ``new == value`` (old ignored)
* :func:`unchanged` — ``old == new``
* :func:`appended_with` — ``new == f"{old}{sep}{suffix}"``
* :func:`prepended_with` — ``new == f"{prefix}{sep}{old}"``
* :func:`containing` — ``substring in new``
* :func:`normalized_to` — ``normalizer(old) == normalizer(new)``
* :func:`idempotent_after` — ``prefix`` is already the first segment of ``new``
* :func:`legacy_healed` — D-11 4-case paper-trace (detector + healed_check)

Capture helpers
---------------

The convention for capturing universe state is to build a flat ``dict`` keyed
by port-exposed observable names, populated immediately before the
state-mutating call and again immediately after::

    universe_keys = {"PATH", "exit_code", "events_emitted"}

    def _capture(env: dict[str, str], extra: dict[str, Any]) -> dict[str, Any]:
        return {
            "PATH": env.get("PATH"),
            "exit_code": extra.get("exit_code"),
            "events_emitted": tuple(extra.get("events", ())),
        }

    before = _capture(env, ctx)
    run_under_test(...)
    after = _capture(env, ctx)

    assert_state_delta(before, after, universe_keys, {
        "PATH": prepended_with("/des/bin"),
        # "exit_code" and "events_emitted" are in universe but not in expected
        # => MUST remain unchanged (fail-closed default).
    })

Universe MUST contain port-exposed observable names only — never internal
struct fields. Anything in ``universe`` not in ``expected`` MUST remain
unchanged across the call (fail-closed contract).

Polyglot bindings
-----------------

Other-language ports of this API (TypeScript, Rust, Java, Kotlin, C#, Go)
live at the project-local path ``tests/common/state_delta.<ext>`` and
implement the same eight predicates with identical semantic contracts. See
the ``Polyglot Adapter Matrix`` section of ``nw-distill`` for the full
matrix and the per-language Tier-2 expansion templates.
"""

from __future__ import annotations

from nwave_ai.state_delta.chaos import (
    Perturbation,
    chaos_env_perturbation,
    chaos_filesystem_truncation,
    chaos_ordering_swap,
    enumerate_perturbations,
    enumerate_perturbations_strategy,
)
from nwave_ai.state_delta.matcher import MatcherResult, Violation, assert_state_delta
from nwave_ai.state_delta.predicates import (
    Predicate,
    appended_with,
    containing,
    idempotent_after,
    legacy_healed,
    normalized_to,
    prepended_with,
    set_to,
    unchanged,
)


# Promotion 2026-05-13 (Epic 2A): module is now the public test API for
# nWave-built projects. Marker preserved for tooling that still introspects it
# but flipped to ``False`` to signal external consumers may depend on this
# surface.
__nwave_internal__ = False

__all__ = [
    # matcher
    "MatcherResult",
    "Violation",
    "assert_state_delta",
    # predicates
    "Predicate",
    "appended_with",
    "containing",
    "idempotent_after",
    "legacy_healed",
    "normalized_to",
    "prepended_with",
    "set_to",
    "unchanged",
    # chaos
    "Perturbation",
    "chaos_env_perturbation",
    "chaos_filesystem_truncation",
    "chaos_ordering_swap",
    "enumerate_perturbations",
    "enumerate_perturbations_strategy",
]
