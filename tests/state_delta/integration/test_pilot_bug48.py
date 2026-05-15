"""Integration tests: D-12 Part A + D-12 DoD #8 branch-coverage PBT.

Part A: matcher catches bug #48 via pre-fix simulator.
DoD #8: one PBT test per production branch of update_path_in_settings_faithful.

Legacy-heal note (strategy gap)
--------------------------------
``path_strategy(include_legacy_fallback=True)`` generates the literal sentinel
``"DES_BIN:SYSTEM_PATH_FALLBACK"`` (a placeholder string), NOT the real legacy
fabricated value ``f"{DES_BIN}:{SYSTEM_PATH_FALLBACK}"``.  The simulator's
legacy-heal branch detects the interpolated form only — so ``path_strategy``
does not exercise it.  ``test_pbt_legacy_heal_branch`` therefore uses
``st.just(LEGACY_FORM)`` directly to target the real legacy form.  This is
documented here so future maintainers know why the legacy test deviates from
the common ``path_strategy(...)`` pattern.

D-12 Part B note (hard gate)
-----------------------------
``test_pilot_bug48_post_fix_validated`` is the pilot ship gate.  It drives 500
Hypothesis-generated examples through the post-fix simulator with inline
branch-dispatch predicate selection.  Legacy-heal is excluded from the
combined 500-example run because ``path_strategy`` cannot generate the real
legacy form (strategy gap, see above) — it is covered by the dedicated
``test_pbt_legacy_heal_branch``.  The hard gate therefore requires ≥ 3 of the
4 remaining production branches to be exercised plus the default-prepend
catch-all.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from nwave_ai.state_delta import (
    assert_state_delta,
    idempotent_after,
    legacy_healed,
    prepended_with,
    set_to,
)
from nwave_ai.state_delta.strategies import (
    path_strategy,
    update_path_in_settings_faithful,
)
from nwave_ai.state_delta.strategies.simulators import SYSTEM_PATH_FALLBACK

from tests.state_delta.fixtures.simulators_pre_fix import (
    update_path_in_settings_pre_fix,
)


# ── Shared constants ──────────────────────────────────────────────────────────
DES_BIN = "/des/bin"
HOME = "/home/u"
LIVE_ENV_PATH = "/usr/local/bin:/usr/bin"
# The real legacy fabricated value written by the pre-fix installer:
#   des_bin + ":" + SYSTEM_PATH_FALLBACK
LEGACY_FORM = f"{DES_BIN}:{SYSTEM_PATH_FALLBACK}"
# Fallback used when live_env_path is empty (matches simulator constant)
FALLBACK = SYSTEM_PATH_FALLBACK


def test_pilot_bug48_pre_fix_dropped_user_dirs_detected() -> None:
    """D-12 Part A: matcher catches bug #48 on pre-fix simulator output.

    The pre-fix logic ignored existing_path entirely and wrote a hardcoded
    SYSTEM_PATH_FALLBACK, silently stripping user dirs like /home/u/.local/bin.

    The matcher must detect this: prepended_with("/des/bin") expects
    new == "/des/bin:/home/u/.local/bin:/usr/bin", but the pre-fix output
    is "/des/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" — the
    fabricated fallback, not a genuine prepend. AssertionError MUST be raised.
    """
    before = {"PATH": "/home/u/.local/bin:/usr/bin"}
    after = {"PATH": update_path_in_settings_pre_fix(before["PATH"], "/des/bin")}
    with pytest.raises(AssertionError, match="predicate_failed|undeclared_change"):
        assert_state_delta(
            before=before,
            after=after,
            universe={"PATH"},
            expected={"PATH": prepended_with("/des/bin")},
        )


# ── DoD #8: branch-coverage PBT (5 tests, one per production branch) ─────────


@given(user_path=path_strategy(include_home_literal=True))
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_pbt_normalization_branch(user_path: str) -> None:
    """Branch 1 — $HOME normalization.

    When existing_path contains a $HOME literal, the simulator expands it to
    the absolute home directory before any other branch runs.  The resulting
    PATH is free of $HOME tokens.

    After normalization the path still falls through to either idempotency
    (des_bin already present) or default-prepend (not yet present).  Both
    sub-cases share the postcondition: new has no $HOME tokens.
    """
    assume("$HOME" in user_path)
    after = update_path_in_settings_faithful(user_path, DES_BIN, HOME, LIVE_ENV_PATH)
    assert_state_delta(
        before={"PATH": user_path},
        after={"PATH": after},
        universe={"PATH"},
        expected={"PATH": lambda old, new: "$HOME" not in new},
    )


@given(user_path=path_strategy())
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_pbt_idempotency_branch(user_path: str) -> None:
    """Branch 3 — idempotency (des_bin already first segment).

    When des_bin is already a colon-segment of existing_path, the simulator
    returns the path unchanged (modulo earlier $HOME normalisation).  The
    first segment of the result must equal des_bin.
    """
    assume(DES_BIN in user_path.split(":"))
    after = update_path_in_settings_faithful(user_path, DES_BIN, HOME, LIVE_ENV_PATH)
    assert_state_delta(
        before={"PATH": user_path},
        after={"PATH": after},
        universe={"PATH"},
        expected={"PATH": idempotent_after(DES_BIN)},
    )


@given(user_path=st.just(LEGACY_FORM))
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_pbt_legacy_heal_branch(user_path: str) -> None:
    """Branch 2 — legacy-heal.

    When existing_path equals the exact fabricated value written by the
    pre-fix installer (des_bin + ":" + SYSTEM_PATH_FALLBACK), the simulator
    replaces it with des_bin + ":" + live_env_path (the real live PATH).

    Strategy note: path_strategy(include_legacy_fallback=True) generates the
    literal sentinel "DES_BIN:SYSTEM_PATH_FALLBACK", not the real interpolated
    form.  This test uses st.just(LEGACY_FORM) directly so Hypothesis targets
    the actual legacy-heal detection logic in the simulator.
    """
    is_legacy = lambda s: s == LEGACY_FORM  # noqa: E731
    is_healed = lambda s: s == f"{DES_BIN}:{LIVE_ENV_PATH}"  # noqa: E731
    after = update_path_in_settings_faithful(user_path, DES_BIN, HOME, LIVE_ENV_PATH)
    assert_state_delta(
        before={"PATH": user_path},
        after={"PATH": after},
        universe={"PATH"},
        expected={"PATH": legacy_healed(is_legacy, is_healed)},
    )


@given(user_path=path_strategy(include_empty=True))
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_pbt_empty_seed_branch(user_path: str) -> None:
    """Branch 5 — empty-seed.

    When existing_path is empty the simulator seeds PATH from live_env_path
    (or SYSTEM_PATH_FALLBACK when live_env_path is also empty).  With
    LIVE_ENV_PATH = "/usr/local/bin:/usr/bin" the result is always
    des_bin + ":" + LIVE_ENV_PATH.
    """
    assume(user_path == "")
    after = update_path_in_settings_faithful(user_path, DES_BIN, HOME, LIVE_ENV_PATH)
    assert_state_delta(
        before={"PATH": user_path},
        after={"PATH": after},
        universe={"PATH"},
        expected={"PATH": set_to(f"{DES_BIN}:{LIVE_ENV_PATH}")},
    )


@given(user_path=path_strategy())
@settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_pbt_default_prepend_branch(user_path: str) -> None:
    """Branch 4 — default prepend.

    For any realistic non-empty PATH that is not the legacy fabricated value
    and does not already contain des_bin, the simulator prepends des_bin.
    Result must equal des_bin + ":" + existing_path.
    """
    assume(user_path != "")
    assume(user_path != LEGACY_FORM)
    assume(DES_BIN not in user_path.split(":"))
    assume("$HOME" not in user_path)
    after = update_path_in_settings_faithful(user_path, DES_BIN, HOME, LIVE_ENV_PATH)
    assert_state_delta(
        before={"PATH": user_path},
        after={"PATH": after},
        universe={"PATH"},
        expected={"PATH": prepended_with(DES_BIN)},
    )


# ── D-12 Part B: hard gate — 500-example combined PBT ─────────────────────────


def _select_predicate_for(user_path: str, branch_hits: dict[str, int]) -> object:
    """Select the appropriate predicate for a given user_path, recording the branch hit.

    Branch selection mirrors the production branch execution order in
    ``update_path_in_settings_faithful``:

    1. $HOME normalization — detected before any other check
    2. Empty-seed          — empty string input
    3. Idempotency         — des_bin already a colon-segment
    4. Default-prepend     — everything else (non-empty, non-idempotent, no $HOME)

    Legacy-heal is intentionally excluded: ``path_strategy`` cannot generate the
    real interpolated legacy form (see module docstring strategy-gap note).  That
    branch is validated exclusively by ``test_pbt_legacy_heal_branch``.
    """
    if user_path == "":
        branch_hits["empty_seed"] += 1
        return set_to(f"{DES_BIN}:{LIVE_ENV_PATH}")
    if "$HOME" in user_path:
        branch_hits["normalization"] += 1
        # After normalization, $HOME tokens must be absent from the new value.
        return lambda old, new: "$HOME" not in new  # type: ignore[return-value]
    if DES_BIN in user_path.split(":"):
        branch_hits["idempotency"] += 1
        return idempotent_after(DES_BIN)
    branch_hits["default_prepend"] += 1
    return prepended_with(DES_BIN)


def test_pilot_bug48_post_fix_validated() -> None:
    """D-12 Part B HARD GATE — 500 generated examples, post-fix simulator, all branches GREEN.

    Drives 500 Hypothesis-generated PATH strings through ``update_path_in_settings_faithful``
    (the post-fix simulator) and verifies the matcher contract holds for every example using
    inline branch-dispatch predicate selection.

    DoD #8 branch coverage:

    | Branch          | Trigger                        | Predicate                       |
    |-----------------|--------------------------------|---------------------------------|
    | normalization   | ``"$HOME" in user_path``       | ``lambda old, new: "$HOME" not in new`` |
    | idempotency     | ``DES_BIN in user_path.split(":")`` | ``idempotent_after(DES_BIN)`` |
    | empty_seed      | ``user_path == ""``            | ``set_to(DES_BIN:LIVE_ENV_PATH)`` |
    | default_prepend | (all other non-empty paths)    | ``prepended_with(DES_BIN)``     |
    | legacy_heal     | ``user_path == LEGACY_FORM``   | covered by test_pbt_legacy_heal_branch (strategy gap) |

    Criterion 2 assertion: at least 3 of 4 addressable production branches must be exercised
    across the 500 examples, plus the default-prepend catch-all must have ≥ 1 hit.
    """
    from hypothesis import HealthCheck, given, settings

    branch_hits: dict[str, int] = {
        "normalization": 0,
        "idempotency": 0,
        "empty_seed": 0,
        "default_prepend": 0,
    }

    @given(user_path=path_strategy(include_home_literal=True, include_empty=True))
    @settings(
        max_examples=500,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
        deadline=None,
    )
    def _run_500_examples(user_path: str) -> None:
        after = update_path_in_settings_faithful(
            user_path, DES_BIN, HOME, LIVE_ENV_PATH
        )
        predicate = _select_predicate_for(user_path, branch_hits)
        assert_state_delta(
            before={"PATH": user_path},
            after={"PATH": after},
            universe={"PATH"},
            expected={"PATH": predicate},
        )

    _run_500_examples()

    # Criterion 2: ≥ 3 of 4 addressable production branches exercised
    addressable_branches = {
        k: v for k, v in branch_hits.items() if k != "default_prepend"
    }
    branches_exercised = sum(1 for v in addressable_branches.values() if v > 0)
    assert branches_exercised >= 3, (
        f"Only {branches_exercised}/3 non-default branches exercised. "
        f"Branch hits: {branch_hits}"
    )
    assert branch_hits["default_prepend"] >= 1, (
        f"Default-prepend branch never exercised. Branch hits: {branch_hits}"
    )
