"""Step definitions: E7 install-registration + attribution.enabled gate (ADR-CA-006).

Binds the three E7 `.feature` files. Two production-wired driving surfaces, both
Layer 3 composition over a sandboxed `~/.claude` (Mandate 13 — driving-port-only):

  * the real `AttributionPlugin` install/uninstall lifecycle (`@real-io`);
  * the real `nwave-ai attribution on|off` CLI handler (`@real-io`).

Both reach the SAME net-new production seam — the attribution-hook registration
that writes/removes the `Bash`/`pre-commit-attribution` entry in `settings.json`,
gated by `attribution.enabled`. The seam is driven through the real entry points
(install / CLI), never in isolation (Mandate 15 / S3 witnessing).

Example-only, no PBT machinery (Mandate 9/11): this is a config-shaped install
slice (finite gate states + finite home shapes), so every state is enumerated.
Step bodies delegate to the composition roots and never inline business logic
(Mandate-12 criterion 3): each body is a typed lookup plus a composition call.

State-delta (Mandate 8): the coexistence/preservation Then steps assert via
`assert_state_delta` over a port-exposed universe (the `pre-bash` guard and the
operator's own hook), so "what did NOT change" is a fail-closed claim, not an
afterthought. The simpler count assertions (registered / absent / exactly-one)
read the observable directly.

RED contract (Mandate 7): every scenario reaches the net-new registration scaffold
(`register_attribution_hook`/`unregister_attribution_hook` in
`scripts/install/attribution_utils.py`, called from the real install + CLI entry
points), which raises AssertionError until DELIVER implements it — so the
pre-DELIVER gate classifies each as RED (MISSING_FUNCTIONALITY), never BROKEN.

Step-text is unique within this E7 directory (S1): the phrases here
(`the commit-attribution hook is registered …`, `the existing commit guard …`)
are disjoint from the E1-E6 sibling slice's phrases (`the rewrite core …`,
`the attribution hook processes …`), so no pytest-bdd registry collision.
"""

from __future__ import annotations

import pytest
from nwave_ai.state_delta import assert_state_delta, unchanged
from pytest_bdd import given, parsers, scenarios, then, when

from .composition import CliComposition, InstallComposition, SettingsView
from .domain_types import (
    CHOICE_BY_PHRASE,
    CHOICE_BY_STATE,
    HOME_BY_PHRASE,
    HomeShape,
)


scenarios(
    "../walking-skeleton.feature",
    "../registration-gate.feature",
    "../coexistence-and-failsafe.feature",
)


# ---------------------------------------------------------------------------
# Fixtures — one production-wired composition root per driving surface
# ---------------------------------------------------------------------------


@pytest.fixture
def install(sandbox_home) -> InstallComposition:
    """Production-wired composition over the real AttributionPlugin lifecycle."""
    return InstallComposition(home=sandbox_home)


@pytest.fixture
def cli(sandbox_home) -> CliComposition:
    """Production-wired composition over the real `attribution on|off` CLI."""
    return CliComposition(home=sandbox_home)


# ---------------------------------------------------------------------------
# Given — sandbox shape + preference + neighbours
# ---------------------------------------------------------------------------


@given(parsers.parse("a sandboxed nWave home {home_phrase}"))
def given_home_shape(install: InstallComposition, home_phrase: str) -> None:
    _seed_home(install, HOME_BY_PHRASE[home_phrase])


@given("the operator has added their own Bash hook")
def given_operator_hook(install: InstallComposition) -> None:
    install.seed_operator_hook()


@given(parsers.parse("the operator has chosen to {choice_phrase}"))
def given_preference(install: InstallComposition, choice_phrase: str) -> None:
    install.set_preference(CHOICE_BY_PHRASE[choice_phrase])


@given(parsers.parse("nWave is installed with attribution {state}"))
def given_installed_with_state(
    install: InstallComposition, box: dict[str, object], state: str
) -> None:
    install.set_preference(CHOICE_BY_STATE[state])
    install.install()
    box["before"] = install.settings()


# ---------------------------------------------------------------------------
# When — drive the real install lifecycle / CLI
# ---------------------------------------------------------------------------


@when("nWave is installed")
@when("nWave is installed again")
def when_installed(install: InstallComposition, box: dict[str, object]) -> None:
    box.setdefault("before", install.settings())
    box["message"] = install.install()
    box["after"] = install.settings()


@when("nWave is uninstalled")
def when_uninstalled(install: InstallComposition, box: dict[str, object]) -> None:
    box["message"] = install.uninstall()
    box["after"] = install.settings()


@when(parsers.parse("the operator turns attribution {state}"))
@when(parsers.parse("the operator turns attribution {state} again"))
def when_cli_turn(cli: CliComposition, box: dict[str, object], state: str) -> None:
    box["exit_code"] = cli.turn(state)
    box["after"] = cli.settings()


# ---------------------------------------------------------------------------
# Then — observe settings.json hooks.PreToolUse content
# ---------------------------------------------------------------------------


@then("the commit-attribution hook is registered for Bash commands")
def then_attribution_registered(box: dict[str, object]) -> None:
    assert _after(box).attribution_hook_count() >= 1


@then("no commit-attribution hook is registered")
def then_attribution_absent(box: dict[str, object]) -> None:
    assert _after(box).attribution_hook_count() == 0


@then("exactly one commit-attribution hook is registered")
def then_exactly_one_attribution(box: dict[str, object]) -> None:
    assert _after(box).attribution_hook_count() == 1


@then("the existing commit guard is still registered")
def then_guard_coexists(box: dict[str, object]) -> None:
    after = _after(box)
    assert_state_delta(
        before={"guard_registered": _before(box).guard_is_registered()},
        after={"guard_registered": after.guard_is_registered()},
        universe={"guard_registered"},
        expected={"guard_registered": unchanged()},
    )
    assert after.guard_is_registered()


@then("the operator's own Bash hook is still registered")
def then_operator_hook_preserved(box: dict[str, object]) -> None:
    after = _after(box)
    assert_state_delta(
        before={"operator_hook": _before(box).operator_hook_is_registered()},
        after={"operator_hook": after.operator_hook_is_registered()},
        universe={"operator_hook"},
        expected={"operator_hook": unchanged()},
    )
    assert after.operator_hook_is_registered()


@then("the install still succeeds")
def then_install_succeeds(box: dict[str, object]) -> None:
    assert box["message"] is not None


@then("the corrupt settings are left untouched")
def then_corrupt_untouched(box: dict[str, object]) -> None:
    assert _after(box).raw_text == "{ not json"


# ---------------------------------------------------------------------------
# Helpers (kept here so step bodies stay a single expression)
# ---------------------------------------------------------------------------


def _seed_home(install: InstallComposition, shape: HomeShape) -> None:
    if shape is HomeShape.GUARD_PRESENT:
        install.seed_guard()
    elif shape is HomeShape.CORRUPT:
        install.seed_corrupt_settings()
    # HomeShape.NO_CLAUDE — leave ~/.claude absent (no seeding).


def _after(box: dict[str, object]) -> SettingsView:
    return box["after"]  # type: ignore[return-value]


def _before(box: dict[str, object]) -> SettingsView:
    return box["before"]  # type: ignore[return-value]
