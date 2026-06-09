"""
Step definitions for rigor cascade resolution acceptance tests.

Covers walking-skeleton.feature and milestone-1-cascade-resolution.feature.

Driving port: DESConfig constructor + rigor_* properties.
All tests invoke DESConfig with injectable global_config_path to verify
the cascade: project rigor -> global rigor -> standard defaults.
"""

from __future__ import annotations

import json
import stat
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from des.adapters.driven.config.des_config import DESConfig
from tests.des.acceptance.rigor_global_config.steps.helpers import (
    write_global_config,
    write_project_config,
)


if TYPE_CHECKING:
    from pathlib import Path


# Link feature files
scenarios("../walking-skeleton.feature")
scenarios("../milestone-1-cascade-resolution.feature")


# ---------------------------------------------------------------------------
# Shared test context fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def ctx() -> dict[str, Any]:
    """Mutable context shared across Given/When/Then steps in a scenario."""
    return {}


# ---------------------------------------------------------------------------
# Given steps: project configuration
# ---------------------------------------------------------------------------


@given("a temporary project directory exists")
def given_temp_project(project_dir: Path, ctx: dict[str, Any]) -> None:
    """Store project directory in context."""
    ctx["project_dir"] = project_dir
    ctx["project_config_path"] = project_dir / ".nwave" / "des-config.json"


@given("a temporary global configuration directory exists")
def given_temp_global(
    global_config_dir: Path,
    global_config_path: Path,
    ctx: dict[str, Any],
) -> None:
    """Store global config directory in context."""
    ctx["global_config_dir"] = global_config_dir
    ctx["global_config_path"] = global_config_path


@given(
    parsers.parse(
        'Ale has set his global rigor profile to "{profile}" with agent model "{model}"'
    )
)
def given_ale_global_rigor(
    tmp_path: Path, ctx: dict[str, Any], profile: str, model: str
) -> None:
    """Create global config with the specified rigor profile."""
    global_dir = tmp_path / "home" / ".nwave"
    global_dir.mkdir(parents=True, exist_ok=True)
    global_config = global_dir / "global-config.json"
    write_global_config(
        global_config,
        {"rigor": {"profile": profile, "agent_model": model}},
    )
    ctx["global_config_path"] = global_config


@given(parsers.parse('project "{name}" has no rigor configuration'))
def given_project_no_rigor(tmp_path: Path, ctx: dict[str, Any], name: str) -> None:
    """Create project config without rigor key."""
    project_root = tmp_path / name
    nwave_dir = project_root / ".nwave"
    nwave_dir.mkdir(parents=True, exist_ok=True)
    config = nwave_dir / "des-config.json"
    config.write_text(json.dumps({"audit_logging_enabled": True}), encoding="utf-8")
    ctx["project_config_path"] = config
    ctx["project_dir"] = project_root


@given(
    parsers.parse(
        'project "{name}" has rigor profile "{profile}" with agent model "{model}"'
    )
)
def given_project_rigor(
    tmp_path: Path, ctx: dict[str, Any], name: str, profile: str, model: str
) -> None:
    """Create project config with specific rigor."""
    project_root = tmp_path / name
    nwave_dir = project_root / ".nwave"
    nwave_dir.mkdir(parents=True, exist_ok=True)
    config = nwave_dir / "des-config.json"
    config.write_text(
        json.dumps({"rigor": {"profile": profile, "agent_model": model}}),
        encoding="utf-8",
    )
    ctx["project_config_path"] = config
    ctx["project_dir"] = project_root


@given("Tomasz has never configured rigor anywhere")
def given_tomasz_no_config(tmp_path: Path, ctx: dict[str, Any]) -> None:
    """No global config file exists."""
    global_config = tmp_path / "home" / ".nwave" / "global-config.json"
    # Do NOT create the file
    ctx["global_config_path"] = global_config


@given(
    parsers.re(
        r'the project config has rigor profile "(?P<profile>[^"]+)"'
        r' with agent model "(?P<amodel>[^"]+)"'
        r' and reviewer model "(?P<rmodel>[^"]+)"'
    )
)
def given_project_rigor_full(
    ctx: dict[str, Any], profile: str, amodel: str, rmodel: str
) -> None:
    """Write rigor with reviewer to project config."""
    write_project_config(
        ctx["project_config_path"],
        {
            "rigor": {
                "profile": profile,
                "agent_model": amodel,
                "reviewer_model": rmodel,
            }
        },
    )


@given(
    parsers.re(
        r'the project config has rigor profile "(?P<profile>[^"]+)"'
        r' with agent model "(?P<model>[^"]+)"$'
    )
)
def given_project_rigor_profile(ctx: dict[str, Any], profile: str, model: str) -> None:
    """Write rigor to project config."""
    write_project_config(
        ctx["project_config_path"],
        {"rigor": {"profile": profile, "agent_model": model}},
    )


@given("the project config has no rigor key")
def given_project_no_rigor_key(ctx: dict[str, Any]) -> None:
    """Ensure project config has no rigor key."""
    write_project_config(
        ctx["project_config_path"],
        {"audit_logging_enabled": True},
    )


@given("the project config has an empty rigor block")
def given_project_empty_rigor(ctx: dict[str, Any]) -> None:
    """Project config has rigor key but it is an empty dict."""
    write_project_config(ctx["project_config_path"], {"rigor": {}})


# ---------------------------------------------------------------------------
# Given steps: global configuration
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        'the global config has rigor profile "{profile}" with agent model "{model}"'
    )
)
def given_global_rigor(ctx: dict[str, Any], profile: str, model: str) -> None:
    """Write rigor to global config."""
    write_global_config(
        ctx["global_config_path"],
        {"rigor": {"profile": profile, "agent_model": model}},
    )


@given(
    parsers.parse(
        'the global config has rigor profile "{profile}"'
        ' with agent model "{amodel}"'
        ' and reviewer model "{rmodel}"'
        " and double review enabled"
    )
)
def given_global_rigor_full(
    ctx: dict[str, Any], profile: str, amodel: str, rmodel: str
) -> None:
    """Write full rigor block to global config."""
    write_global_config(
        ctx["global_config_path"],
        {
            "rigor": {
                "profile": profile,
                "agent_model": amodel,
                "reviewer_model": rmodel,
                "double_review": True,
            }
        },
    )


@given("no global config file exists")
def given_no_global_config(ctx: dict[str, Any]) -> None:
    """Ensure global config file does not exist."""
    path = ctx["global_config_path"]
    if path.exists():
        path.unlink()


@given("the global config has no rigor key")
def given_global_no_rigor(ctx: dict[str, Any]) -> None:
    """Global config exists but has no rigor key."""
    write_global_config(
        ctx["global_config_path"],
        {"update_check": {"frequency": "daily"}},
    )


@given("the global config file contains invalid content")
def given_global_invalid(ctx: dict[str, Any]) -> None:
    """Write invalid JSON to global config file."""
    ctx["global_config_path"].parent.mkdir(parents=True, exist_ok=True)
    ctx["global_config_path"].write_text("not valid json {{{", encoding="utf-8")


@given("the global config file has restricted permissions")
def given_global_unreadable(ctx: dict[str, Any]) -> None:
    """Create global config file with no read permissions."""
    path = ctx["global_config_path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"rigor": {"profile": "custom"}}), encoding="utf-8")
    # Remove read permission
    path.chmod(0o000)
    ctx["_restore_permissions"] = path


@given(
    parsers.parse(
        "the global config has rigor with only"
        ' profile "{profile}" and agent model "{model}"'
    )
)
def given_global_partial_rigor(ctx: dict[str, Any], profile: str, model: str) -> None:
    """Global config with partial rigor -- only some fields set."""
    write_global_config(
        ctx["global_config_path"],
        {"rigor": {"profile": profile, "agent_model": model}},
    )


@given("any combination of project config and global config states")
def given_any_config_combination(ctx: dict[str, Any]) -> None:
    """
    Property-shaped: signals the When step to try multiple combinations.

    The @property tag on this scenario tells the DELIVER wave crafter
    to implement this as a property-based test with generators.
    """
    ctx["property_test"] = True


@given(parsers.parse("a custom global config path pointing to a test directory"))
def given_custom_global_path(tmp_path: Path, ctx: dict[str, Any]) -> None:
    """Create a custom global config directory for injection testing."""
    custom_dir = tmp_path / "custom-global" / ".nwave"
    custom_dir.mkdir(parents=True)
    ctx["custom_global_path"] = custom_dir / "global-config.json"


@given(
    parsers.parse(
        'that test directory has rigor profile "{profile}" with agent model "{model}"'
    )
)
def given_custom_global_rigor(ctx: dict[str, Any], profile: str, model: str) -> None:
    """Write rigor to the custom global config path."""
    write_global_config(
        ctx["custom_global_path"],
        {"rigor": {"profile": profile, "agent_model": model}},
    )


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when(parsers.parse('rigor settings are loaded for project "{name}"'))
def when_load_rigor_for_project(ctx: dict[str, Any], name: str) -> None:
    """Load DESConfig with project and global paths."""
    try:
        config = DESConfig(
            config_path=ctx["project_config_path"],
            global_config_path=ctx["global_config_path"],
        )
        ctx["des_config"] = config
        ctx["error"] = None
    except Exception as exc:
        ctx["des_config"] = None
        ctx["error"] = exc


@when("rigor settings are loaded")
def when_load_rigor(ctx: dict[str, Any]) -> None:
    """Load DESConfig with project and global paths from context."""
    try:
        config = DESConfig(
            config_path=ctx["project_config_path"],
            global_config_path=ctx["global_config_path"],
        )
        ctx["des_config"] = config
        ctx["error"] = None
    except Exception as exc:
        ctx["des_config"] = None
        ctx["error"] = exc
    finally:
        # Restore permissions if we restricted them
        restore_path = ctx.get("_restore_permissions")
        if restore_path:
            restore_path.chmod(stat.S_IRUSR | stat.S_IWUSR)


@when("rigor settings are loaded with the custom global path")
def when_load_rigor_custom_path(ctx: dict[str, Any]) -> None:
    """Load DESConfig with an injected custom global config path."""
    config = DESConfig(
        config_path=ctx["project_config_path"],
        global_config_path=ctx["custom_global_path"],
    )
    ctx["des_config"] = config
    ctx["error"] = None


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then(parsers.parse('the active rigor profile is "{expected}"'))
def then_profile_is(ctx: dict[str, Any], expected: str) -> None:
    """Verify the resolved rigor profile."""
    assert ctx["des_config"].rigor_profile == expected


@then(parsers.parse('the active agent model is "{expected}"'))
def then_agent_model_is(ctx: dict[str, Any], expected: str) -> None:
    """Verify the resolved agent model."""
    assert ctx["des_config"].rigor_agent_model == expected


@then(parsers.parse('the active reviewer model is "{expected}"'))
def then_reviewer_model_is(ctx: dict[str, Any], expected: str) -> None:
    """Verify the resolved reviewer model."""
    assert ctx["des_config"].rigor_reviewer_model == expected


@then("the active TDD phases are the canonical 3-phase cycle")
def then_canonical_tdd_phases(ctx: dict[str, Any]) -> None:
    """Verify canonical 3-phase TDD cycle is active (ADR-025 default).

    F6 sweep (2026-05-18): renamed from "full 5-phase cycle" and inverted
    assertion from LEGACY_PHASES to CANONICAL_PHASES. Default rigor profile
    follows ADR-025 canonical (RED/GREEN/COMMIT). Legacy 5-phase only via
    explicit rigor.tdd_phases override.
    """
    expected = ("RED", "GREEN", "COMMIT")
    assert ctx["des_config"].rigor_tdd_phases == expected


@then("double review is disabled")
def then_double_review_disabled(ctx: dict[str, Any]) -> None:
    """Verify double review is off."""
    assert ctx["des_config"].rigor_double_review is False


@then("double review is enabled")
def then_double_review_enabled(ctx: dict[str, Any]) -> None:
    """Verify double review is on."""
    assert ctx["des_config"].rigor_double_review is True


@then("mutation testing is disabled")
def then_mutation_disabled(ctx: dict[str, Any]) -> None:
    """Verify mutation testing is off."""
    assert ctx["des_config"].rigor_mutation_enabled is False


@then("no error is raised")
def then_no_error(ctx: dict[str, Any]) -> None:
    """Verify no exception was raised during config loading."""
    assert ctx["error"] is None
    assert ctx["des_config"] is not None


@then("the result is always a valid set of rigor settings")
def then_valid_rigor_settings(ctx: dict[str, Any]) -> None:
    """
    Property assertion: rigor settings are always valid.

    Validates that every rigor property returns a value of the correct type
    regardless of what config state was provided. These invariants must hold
    for ALL possible config inputs.

    CRAFTER NOTE: The @property-tagged scenario (M1-11) should be
    implemented using hypothesis to generate random config states
    (missing files, empty dicts, partial rigor blocks, corrupt JSON)
    and verify these invariants hold for every generated input.
    Use hypothesis strategies like st.one_of, st.fixed_dictionaries
    to cover all config state combinations.
    """
    config = ctx["des_config"]

    # rigor_profile: always a non-empty string
    assert isinstance(config.rigor_profile, str)
    assert len(config.rigor_profile) > 0

    # rigor_agent_model: always a non-empty string
    assert isinstance(config.rigor_agent_model, str)
    assert len(config.rigor_agent_model) > 0

    # rigor_reviewer_model: always a non-empty string
    assert isinstance(config.rigor_reviewer_model, str)
    assert len(config.rigor_reviewer_model) > 0

    # rigor_tdd_phases: always a tuple of strings
    assert isinstance(config.rigor_tdd_phases, tuple)
    assert len(config.rigor_tdd_phases) > 0
    assert all(isinstance(p, str) for p in config.rigor_tdd_phases)

    # rigor_review_enabled: always a boolean
    assert isinstance(config.rigor_review_enabled, bool)

    # rigor_double_review: always a boolean
    assert isinstance(config.rigor_double_review, bool)

    # rigor_mutation_enabled: always a boolean
    assert isinstance(config.rigor_mutation_enabled, bool)

    # rigor_refactor_pass: always a boolean
    assert isinstance(config.rigor_refactor_pass, bool)


@then("no exception is raised")
def then_no_exception(ctx: dict[str, Any]) -> None:
    """Verify no exception was raised."""
    assert ctx["error"] is None
