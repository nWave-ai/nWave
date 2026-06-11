"""installer-orphan-sweep slice-03 — verifier orphan report acceptance tests.

Scenario SSOT: ``../verifier-orphan-report.feature``. Active-RED scaffolds per
atdd_pure (ADR-028): the scenarios RUN today and fail with ``AssertionError``
— the verifier counts expected files but has no orphan visibility at all
(``installation_verifier.py`` exposes no unaccounted listing). DELIVER makes
them green; nothing is skipped.

Step bodies delegate to :class:`VerifierReportJourney`
(SSOT-via-Types-Services-DSL mandate, criterion 3: <=2 statements, no logic).
Shared slice-01/02 vocabulary is reused by IMPORT (single registration — the
S1-tolerable pattern), never re-declared.

``capsys`` is consumed in the WHEN step (F-002: capsys is step-scoped in
pytest-bdd, never read in a THEN step).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, scenario, then, when

from .composition_verifier import VerifierReportJourney
from .domain_types import (
    ORPHAN_ASSET_DIR,
    ORPHAN_SCRIPT,
    SECOND_ORPHAN_SCRIPT,
    USER_SKILL,
    AssetFamily,
)

# Shared step vocabulary from slices 01/02 — REUSED, not re-declared (S1):
# the imported function objects are re-bound here by re-applying the
# decorator. ONE function body per step text (single source, propagated);
# the steps resolve this module's `journey` fixture by name (duck-typed
# against VerifierReportJourney).
from .test_des_script_manifest import (
    given_personal_script as _slice01_given_personal_script,
)
from .test_runtime_asset_sweep import (
    given_user_template as _slice02_given_user_template,
)


given_personal_script = given(
    'the user keeps a personal script "my_backup_tool.py" '
    "alongside the installed scripts"
)(_slice01_given_personal_script)
given_user_template = given(
    'the user keeps a personal template "my-team-conventions.md" '
    "alongside the installed runtime assets"
)(_slice02_given_user_template)


_FEATURE = "../verifier-orphan-report.feature"


# ---------------------------------------------------------------------------
# Scenario wiring
# ---------------------------------------------------------------------------


@scenario(_FEATURE, "The verifier reports every file no asset family accounts for")
def test_report_lists_unaccounted_files_per_family():
    """Stray files tracked by no record are listed, per family, report-only."""


@scenario(_FEATURE, "A fully accounted installation verifies clean, run after run")
def test_clean_installation_verifies_quiet_and_idempotent():
    """Positive clean bill, zero noise, identical on re-run, nothing touched."""


@scenario(
    _FEATURE, "The user's own assets are reported as preserved, never as problems"
)
def test_user_created_assets_safelisted():
    """Safelist witness: preserved-not-problem classification, nothing touched."""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def journey(tmp_path: Path) -> VerifierReportJourney:
    """One real-filesystem verifier journey per scenario."""
    return VerifierReportJourney(tmp_path)


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given("the current nWave version is installed with every asset family recorded")
def given_recorded_installation(journey: VerifierReportJourney) -> None:
    journey.given_recorded_installation()


@given(
    'scripts "superseded_tool.py" and "old_migration.py" linger among '
    "the installed scripts without any record"
)
def given_unaccounted_scripts(journey: VerifierReportJourney) -> None:
    journey.given_unaccounted_scripts((ORPHAN_SCRIPT, SECOND_ORPHAN_SCRIPT))


@given(
    'a folder "stale-flavor" lingers among the installed runtime assets '
    "without any record"
)
def given_unaccounted_asset_dir(journey: VerifierReportJourney) -> None:
    journey.given_unaccounted_asset_dir(ORPHAN_ASSET_DIR)


@given('the user keeps a personal skill "nw-custom" among the installed skills')
def given_user_skill(journey: VerifierReportJourney) -> None:
    journey.given_user_skill(USER_SKILL)


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when("the operator runs the installation verifier")
def when_operator_runs_verifier(
    journey: VerifierReportJourney, capsys: pytest.CaptureFixture[str]
) -> None:
    journey.run_verifier(capsys)


@when("the operator runs the installation verifier twice")
def when_operator_runs_verifier_twice(
    journey: VerifierReportJourney, capsys: pytest.CaptureFixture[str]
) -> None:
    journey.run_verifier(capsys, runs=2)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then(
    'the report lists "superseded_tool.py" and "old_migration.py" as '
    "unaccounted in the scripts family"
)
def then_unaccounted_scripts_listed(journey: VerifierReportJourney) -> None:
    journey.assert_unaccounted_listed(
        AssetFamily.SCRIPTS, frozenset({ORPHAN_SCRIPT, SECOND_ORPHAN_SCRIPT})
    )


@then('the report lists "stale-flavor" as unaccounted in the runtime assets family')
def then_unaccounted_asset_dir_listed(journey: VerifierReportJourney) -> None:
    journey.assert_unaccounted_listed(
        AssetFamily.RUNTIME_ASSETS, frozenset({ORPHAN_ASSET_DIR})
    )


@then("the report confirms every installed file is accounted for")
def then_clean_bill(journey: VerifierReportJourney) -> None:
    journey.assert_clean_bill()


@then("both runs report exactly the same")
def then_runs_identical(journey: VerifierReportJourney) -> None:
    journey.assert_runs_identical()


@then(
    "the report notes each of the user's assets as preserved and not managed by nWave"
)
def then_user_assets_noted_preserved(journey: VerifierReportJourney) -> None:
    journey.assert_user_assets_noted_as_preserved()


@then("none of the user's assets is reported as a problem")
def then_user_assets_not_problems(journey: VerifierReportJourney) -> None:
    journey.assert_user_assets_not_problems()


@then("the verification still passes")
def then_verification_passes(journey: VerifierReportJourney) -> None:
    journey.assert_verification_passes()


@then("the verifier has changed nothing on disk and reported nothing else")
def then_read_only_contract_holds(journey: VerifierReportJourney) -> None:
    journey.assert_contract_holds()
