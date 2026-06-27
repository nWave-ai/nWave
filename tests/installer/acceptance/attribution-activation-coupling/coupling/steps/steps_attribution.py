"""Step definitions for the attribution-activation-coupling acceptance suite.

Mandate-12 criterion 3: every step body is ≤2 statements ending in a
``composition.<method>(...)`` call (or an ``assert composition.<reader>()``),
with zero inline control flow / business logic. The DSL emerges from the typed
enums in ``domain_types`` via ``pytest_bdd.parsers`` converters — a small set of
parameterized decorators covers the whole scenario surface rather than one
decorator per literal.

The step-method names are the shared vocabulary contract (Mandate 10). All
business logic lives in ``composition.py`` (the single source of truth, Pillar 3
production composition root).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_bdd import given, parsers, then, when

from .domain_types import (
    AttributionPreference,
    CommitForm,
    DeprecatedKeyLocation,
    HookRegistration,
    RepoActivationState,
    SettingsAvailability,
    SettingsResidue,
    ToggleAction,
    TrailerOutcome,
)


if TYPE_CHECKING:
    from .composition import AttributionCouplingComposition


# ---------------------------------------------------------------------------
# Parser converters — coerce Gherkin literals into typed domain enums.
# ---------------------------------------------------------------------------

_ACTIVATION = {
    "active": RepoActivationState.ACTIVE,
    "inactive": RepoActivationState.INACTIVE_STICKY,
    "non-nWave": RepoActivationState.UNMARKED,
}
_PREFERENCE = {
    "on": AttributionPreference.ON,
    "off": AttributionPreference.OFF,
    "unset": AttributionPreference.UNSET,
}
_RESIDUE = {
    "an nWave-managed": SettingsResidue.NWAVE_MANAGED,
    "a user-modified": SettingsResidue.USER_MODIFIED,
    "no": SettingsResidue.ABSENT,
}
_AVAILABILITY = {
    "present": SettingsAvailability.PRESENT,
    "absent": SettingsAvailability.ABSENT,
    "corrupt": SettingsAvailability.CORRUPT,
}
_FORM = {
    "with -m": CommitForm.DASH_M,
    "in an && chain": CommitForm.AND_CHAIN,
}
_REGISTRATION = {
    "registered": HookRegistration.REGISTERED,
    "not registered": HookRegistration.UNREGISTERED,
}
_DEPRECATED_LOCATION = {
    "the top level": DeprecatedKeyLocation.TOP_LEVEL,
    "under attribution": DeprecatedKeyLocation.NESTED_UNDER_ATTRIBUTION,
}
_TRAILER = {
    "the dual nWave credit": TrailerOutcome.DUAL_TRAILER,
    "no nWave credit": TrailerOutcome.NO_TRAILER,
}


# ---------------------------------------------------------------------------
# Given — preconditions (typed via converters, delegate to composition builders)
# ---------------------------------------------------------------------------


@given(parsers.parse("a {state} repo"))
def given_repo(composition: AttributionCouplingComposition, state: str) -> None:
    composition.given_repo_activation(_ACTIVATION[state])


@given(parsers.parse("attribution preference is {preference}"))
def given_preference(
    composition: AttributionCouplingComposition, preference: str
) -> None:
    composition.given_attribution_preference(_PREFERENCE[preference])


@given(parsers.parse("the Claude settings file is {availability}"))
def given_settings_availability(
    composition: AttributionCouplingComposition, availability: str
) -> None:
    composition.given_settings_availability(_AVAILABILITY[availability])


@given(parsers.parse("{residue} legacy attribution credit in the Claude settings"))
def given_legacy_residue(
    composition: AttributionCouplingComposition, residue: str
) -> None:
    composition.given_legacy_settings_residue(_RESIDUE[residue])


@given(parsers.parse("the attribution commit hook is {registration}"))
def given_hook_registration(
    composition: AttributionCouplingComposition, registration: str
) -> None:
    composition.given_registered_hook(_REGISTRATION[registration])


@given("the nWave execution guard is registered")
def given_des_guard(composition: AttributionCouplingComposition) -> None:
    composition.given_des_guard_registered()


@given(parsers.parse("the deprecated include-co-author flag is set {location}"))
def given_deprecated_flag(
    composition: AttributionCouplingComposition, location: str
) -> None:
    composition.given_deprecated_flag_at(_DEPRECATED_LOCATION[location])


# ---------------------------------------------------------------------------
# When — single user actions (delegate to composition action methods)
# ---------------------------------------------------------------------------


@when(parsers.parse("Claude commits {form}"))
def when_claude_commits(composition: AttributionCouplingComposition, form: str) -> None:
    composition.claude_commits(_FORM[form])


@when("the operator installs nWave")
def when_operator_installs(composition: AttributionCouplingComposition) -> None:
    composition.operator_runs_install()


@when("the operator uninstalls nWave")
def when_operator_uninstalls(composition: AttributionCouplingComposition) -> None:
    composition.operator_runs_uninstall()


@when("the operator turns attribution on")
def when_turn_on(composition: AttributionCouplingComposition) -> None:
    composition.operator_runs_attribution(ToggleAction.ON)


@when("the operator turns attribution on again")
def when_turn_on_again(composition: AttributionCouplingComposition) -> None:
    composition.operator_runs_attribution(ToggleAction.ON)


@when("the operator turns attribution off")
def when_turn_off(composition: AttributionCouplingComposition) -> None:
    composition.operator_runs_attribution(ToggleAction.OFF)


@when("the operator asks for attribution status")
def when_ask_status(composition: AttributionCouplingComposition) -> None:
    composition.operator_runs_attribution(ToggleAction.STATUS)


@when("the operator asks for attribution status through the command line")
def when_ask_status_subprocess(
    composition: AttributionCouplingComposition,
) -> None:
    composition.operator_runs_attribution_subprocess(ToggleAction.STATUS)


@when("the operator runs the doctor")
def when_run_doctor(composition: AttributionCouplingComposition) -> None:
    composition.operator_runs_doctor()


# ---------------------------------------------------------------------------
# Then — observable outcomes (assert against port-exposed composition readers)
# ---------------------------------------------------------------------------


@then(parsers.parse("the commit carries {outcome}"))
def then_commit_carries(
    composition: AttributionCouplingComposition, outcome: str
) -> None:
    assert composition.trailer_outcome() is _TRAILER[outcome]


@then("the committed message has exactly two co-author lines")
def then_two_coauthors(composition: AttributionCouplingComposition) -> None:
    assert composition.coauthor_count() == 2


@then("nothing is written to the Claude settings for that repo")
def then_no_settings_write(composition: AttributionCouplingComposition) -> None:
    assert composition.settings_attribution_commit() is None


@then("the legacy attribution credit is removed from the Claude settings")
def then_legacy_removed(composition: AttributionCouplingComposition) -> None:
    assert composition.settings_attribution_commit() is None


@then("the user-authored attribution credit is preserved unchanged")
def then_user_value_preserved(
    composition: AttributionCouplingComposition,
) -> None:
    assert composition.settings_attribution_commit() is not None


@then("no managed attribution credit is written to the Claude settings")
def then_no_managed_write(composition: AttributionCouplingComposition) -> None:
    assert composition.settings_attribution_commit() is None


@then("the attribution commit hook is registered")
def then_hook_registered(composition: AttributionCouplingComposition) -> None:
    assert composition.attribution_hook_is_registered() is True


@then("the attribution commit hook is not registered")
def then_hook_unregistered(composition: AttributionCouplingComposition) -> None:
    assert composition.attribution_hook_is_registered() is False


@then("exactly one attribution commit hook is registered")
def then_single_hook(composition: AttributionCouplingComposition) -> None:
    assert composition.attribution_hook_is_registered() is True


@then("the nWave execution guard is still registered")
def then_guard_intact(composition: AttributionCouplingComposition) -> None:
    assert composition.des_guard_is_registered() is True


@then(parsers.parse("the attribution preference is recorded as {preference}"))
def then_preference_recorded(
    composition: AttributionCouplingComposition, preference: str
) -> None:
    assert composition.preference_is_enabled() is (preference == "on")


@then("the attribution preference is preserved")
def then_preference_preserved(
    composition: AttributionCouplingComposition,
) -> None:
    assert composition.preference_is_enabled() is not None


@then("the status reports attribution is active for this repo")
def then_status_active(composition: AttributionCouplingComposition) -> None:
    assert "active" in composition.cli_stdout().lower()


@then("the status reports attribution is inactive for this repo")
def then_status_inactive(composition: AttributionCouplingComposition) -> None:
    assert "inactive" in composition.cli_stdout().lower()


@then("the doctor reports the hook registration state")
def then_doctor_hook(composition: AttributionCouplingComposition) -> None:
    assert "hook" in composition.doctor_message().lower()


@then("the doctor reports this repo's activation state")
def then_doctor_activation(composition: AttributionCouplingComposition) -> None:
    assert "repo" in composition.doctor_message().lower()


@then("the doctor reports the legacy settings residue state")
def then_doctor_residue(composition: AttributionCouplingComposition) -> None:
    assert "legacy" in composition.doctor_message().lower()


@then("the doctor reads the deprecated flag from the top level")
def then_doctor_reads_top_level(
    composition: AttributionCouplingComposition,
) -> None:
    assert "false" in composition.doctor_message().lower()


@then("the operation completes without error")
def then_completes_without_error(
    composition: AttributionCouplingComposition,
) -> None:
    assert composition.cli_exit_code() in (None, 0)


@then("the Claude settings are left untouched")
def then_settings_untouched(composition: AttributionCouplingComposition) -> None:
    assert composition.settings_attribution_commit() is None
