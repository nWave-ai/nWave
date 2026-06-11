"""installer-orphan-sweep slice-01 — DES scripts manifest acceptance tests.

Scenario SSOT: ``../des-script-manifest.feature``. Active-RED scaffolds per
atdd_pure (ADR-028): the scenarios RUN today and fail with ``AssertionError``
because the scripts-manifest behaviour is not implemented — DELIVER makes
them green, nothing is skipped.

Step bodies delegate to :class:`ScriptsUpgradeJourney`
(SSOT-via-Types-Services-DSL mandate, criterion 3: <=2 statements, no logic).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, scenario, then, when

from .composition import ScriptsUpgradeJourney
from .domain_types import PERSONAL_SCRIPT, RETIRED_SCRIPT, TargetEra


_FEATURE = "../des-script-manifest.feature"


# ---------------------------------------------------------------------------
# Scenario wiring
# ---------------------------------------------------------------------------


@scenario(_FEATURE, "Fresh install records every DES script it installs")
def test_fresh_install_writes_script_manifest():
    """Install writes a manifest tracking exactly the installed DES scripts."""


@scenario(_FEATURE, "Upgrade removes a DES script the new version no longer ships")
def test_upgrade_deletes_manifest_tracked_removed_script():
    """Walking skeleton: manifest-tracked script absent from new source is swept."""


@scenario(
    _FEATURE,
    "Upgrading a manifest-less installation preserves unknown scripts and warns",
)
def test_no_manifest_upgrade_preserves_unknown_files_and_warns():
    """Fail-safe: 3.16.0-shaped target — preserve-by-default plus a warning."""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def journey(tmp_path: Path) -> ScriptsUpgradeJourney:
    """One real-filesystem installer journey per scenario."""
    return ScriptsUpgradeJourney(tmp_path)


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given("a machine where nWave has never been installed")
def given_never_installed(journey: ScriptsUpgradeJourney) -> None:
    journey.given_target(TargetEra.NEVER_INSTALLED)


@given("a previous nWave version installed its DES scripts with a manifest")
def given_manifest_tracked_install(journey: ScriptsUpgradeJourney) -> None:
    journey.given_target(TargetEra.MANIFEST_TRACKED)


@given(
    'the previous version had installed "retired_helper.py" '
    "which the new version no longer ships"
)
def given_retired_script_was_installed(journey: ScriptsUpgradeJourney) -> None:
    journey.given_previously_installed_script(RETIRED_SCRIPT)


@given("a nWave installation from a version that kept no manifest")
def given_pre_manifest_install(journey: ScriptsUpgradeJourney) -> None:
    journey.given_target(TargetEra.PRE_MANIFEST)


@given(
    'the user keeps a personal script "my_backup_tool.py" '
    "alongside the installed scripts"
)
def given_personal_script(journey: ScriptsUpgradeJourney) -> None:
    journey.given_personal_script(PERSONAL_SCRIPT)


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when("the user installs nWave")
def when_user_installs(journey: ScriptsUpgradeJourney) -> None:
    journey.run_installer()


@when("the user upgrades nWave")
def when_user_upgrades(journey: ScriptsUpgradeJourney) -> None:
    journey.run_installer()


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then("the DES scripts of the current version are installed")
def then_current_scripts_installed(journey: ScriptsUpgradeJourney) -> None:
    journey.assert_current_scripts_installed()


@then('"retired_helper.py" is no longer among the installed DES scripts')
def then_retired_script_gone(journey: ScriptsUpgradeJourney) -> None:
    journey.assert_script_absent(RETIRED_SCRIPT)


@then("the installation manifest lists exactly the installed DES scripts")
def then_manifest_contract_holds(journey: ScriptsUpgradeJourney) -> None:
    journey.assert_contract_holds()


@then('"my_backup_tool.py" is still present with its original content')
def then_personal_script_preserved(journey: ScriptsUpgradeJourney) -> None:
    journey.assert_personal_script_preserved()


@then("the user is warned that unrecorded scripts were preserved")
def then_preserve_warning_surfaced(journey: ScriptsUpgradeJourney) -> None:
    journey.assert_preserve_warning_surfaced()
