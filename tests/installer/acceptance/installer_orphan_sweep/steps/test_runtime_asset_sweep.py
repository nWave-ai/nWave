"""installer-orphan-sweep slice-02 — runtime-asset family acceptance tests.

Scenario SSOT: ``../runtime-asset-sweep.feature``. Active-RED scaffolds per
atdd_pure (ADR-028): the scenarios RUN today and fail with ``AssertionError``
— the runtime-asset family manifest does not exist, and the indiscriminate
stale sweeps in ``templates_plugin.py`` / ``utilities_plugin.py`` delete
user-created files (preserve-by-default hard-contract violation made
visible). DELIVER makes them green; nothing is skipped.

Step bodies delegate to :class:`FamiliesUpgradeJourney`
(SSOT-via-Types-Services-DSL mandate, criterion 3: <=2 statements, no logic).
Shared slice-01 vocabulary is reused by IMPORT (single registration — the
S1-tolerable pattern), never re-declared.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, scenario, then, when

from .composition_families import FamiliesUpgradeJourney
from .domain_types import RETIRED_ASSET_DIR, USER_TEMPLATE

# Shared step vocabulary from slice-01 — REUSED, not re-declared (S1):
# pytest-bdd registers steps into the defining module's namespace, so the
# imported function objects are re-bound here by re-applying the decorator.
# ONE function body per step text (single source, propagated — the
# S1-tolerable variant); the steps resolve this module's `journey` fixture
# by name (duck-typed against FamiliesUpgradeJourney).
from .test_des_script_manifest import (
    given_manifest_tracked_install as _slice01_given_manifest_tracked_install,
)
from .test_des_script_manifest import (
    given_personal_script as _slice01_given_personal_script,
)
from .test_des_script_manifest import (
    then_personal_script_preserved as _slice01_then_personal_script_preserved,
)
from .test_des_script_manifest import (
    then_preserve_warning_surfaced as _slice01_then_preserve_warning_surfaced,
)
from .test_des_script_manifest import (
    when_user_upgrades as _slice01_when_user_upgrades,
)


given_manifest_tracked_install = given(
    "a previous nWave version installed its DES scripts with a manifest"
)(_slice01_given_manifest_tracked_install)
given_personal_script = given(
    'the user keeps a personal script "my_backup_tool.py" '
    "alongside the installed scripts"
)(_slice01_given_personal_script)
when_user_upgrades = when("the user upgrades nWave")(_slice01_when_user_upgrades)
then_personal_script_preserved = then(
    '"my_backup_tool.py" is still present with its original content'
)(_slice01_then_personal_script_preserved)
then_preserve_warning_surfaced = then(
    "the user is warned that unrecorded scripts were preserved"
)(_slice01_then_preserve_warning_surfaced)


_FEATURE = "../runtime-asset-sweep.feature"


# ---------------------------------------------------------------------------
# Scenario wiring
# ---------------------------------------------------------------------------


@scenario(
    _FEATURE, "Upgrade removes a runtime asset folder the new version no longer ships"
)
def test_upgrade_sweeps_retired_runtime_asset():
    """Tracked asset folder absent from the new source is swept; manifest exact."""


@scenario(_FEATURE, "A template the user created survives an upgrade untouched")
def test_user_template_survives_upgrade():
    """Untracked user template is preserved — not deleted by any stale sweep."""


@scenario(_FEATURE, "No part of an upgrade touches the user's personal script")
def test_personal_script_survives_whole_upgrade():
    """The full pipeline (every sibling plugin) honors preserve-by-default."""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def journey(tmp_path: Path) -> FamiliesUpgradeJourney:
    """One real-filesystem plugin-pipeline journey per scenario."""
    return FamiliesUpgradeJourney(tmp_path)


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given("a previous nWave version installed its runtime assets with a manifest")
def given_runtime_assets_tracked(journey: FamiliesUpgradeJourney) -> None:
    journey.given_runtime_assets_tracked()


@given(
    'the previous version had installed the runtime asset folder "legacy-flavors" '
    "which the new version no longer ships"
)
def given_retired_asset_dir(journey: FamiliesUpgradeJourney) -> None:
    journey.given_retired_asset_dir(RETIRED_ASSET_DIR)


@given(
    'the user keeps a personal template "my-team-conventions.md" '
    "alongside the installed runtime assets"
)
def given_user_template(journey: FamiliesUpgradeJourney) -> None:
    journey.given_user_template(USER_TEMPLATE)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then('the runtime asset folder "legacy-flavors" is no longer installed')
def then_retired_asset_swept(journey: FamiliesUpgradeJourney) -> None:
    journey.assert_retired_asset_swept(RETIRED_ASSET_DIR)


@then("the runtime assets of the current version are installed")
def then_current_assets_installed(journey: FamiliesUpgradeJourney) -> None:
    journey.assert_current_assets_installed()


@then('"my-team-conventions.md" is still present with its original content')
def then_user_template_preserved(journey: FamiliesUpgradeJourney) -> None:
    journey.assert_user_template_preserved()


@then("every asset family's manifest lists exactly what this version ships")
def then_family_manifests_contract_holds(journey: FamiliesUpgradeJourney) -> None:
    journey.assert_contract_holds()
