"""Step definitions + pytest-bdd collector for the silent-verifier regression.

Drives two scenarios from
``tests/bugs/installer/acceptance/test_installer_verifier_content_aware.feature``:

Scenario A — Verifier blind to content drift (Root Cause A in the RCA).
  Driving port: ``NWaveInstaller.validate_installation()``.
  Pre-fix behaviour: target file's content differs from source → existence check
  still succeeds → ``validate_installation()`` returns ``True`` → no drift log.
  Post-fix (M1) behaviour: hash compare detects drift → ``validate_installation()``
  returns ``False`` and the logger captures a drift marker that names the file.

Scenario B — Skills filter is silent (Root Cause B in the RCA).
  Driving port: ``SkillsPlugin.install(context)``.
  Pre-fix behaviour: ``filter_public_skills`` removes orphan/private skills from
  the install set with no log line → an author sees "✅ Skills installed" yet
  their new skill never reached ``~/.claude/``.
  Post-fix (M2) behaviour: every excluded skill emits an info-level
  "Skipped <name>" entry citing the public-agent filter as the reason.

State-delta universes asserted under
``nwave_ai.state_delta.assert_state_delta(..., strict=True)``:
  A: ``{verifier.returned_ok, log.contains_drift_marker, log.names_drifted_file}``
  B: ``{log.contains_skipped_marker, log.names_filtered_skill,
        log.states_reason, target.contains_dropped_skill}``

Both scenarios MUST fail on the current master (the bugs are present).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from nwave_ai.state_delta import assert_state_delta, set_to
from pytest_bdd import given, parsers, scenarios, then, when


# Register every scenario in the sibling feature file. pytest-bdd resolves the
# path relative to this module unless an absolute path is provided.
_FEATURE = (
    Path(__file__).resolve().parents[1]
    / "test_installer_verifier_content_aware.feature"
)
scenarios(str(_FEATURE))


# Track regressions on a single xdist group so concurrent workers do not race
# on shared monkeypatched module-level globals (CLAUDE_CONFIG_DIR + project
# root resolution + plugin registry singletons).
pytestmark = pytest.mark.xdist_group("installer_silent_verifier_regression")


# ---------------------------------------------------------------------------
# Shared scenario context
# ---------------------------------------------------------------------------


class _ScenarioState:
    """Container passed across pytest-bdd Given/When/Then steps.

    pytest-bdd resolves step arguments by fixture name; the conftest fixture
    ``scenario_state`` yields a fresh instance per scenario so state cannot
    leak between the two regression scenarios in the same module.
    """

    def __init__(self) -> None:
        self.universe_before: dict[str, Any] = {}
        self.universe_after: dict[str, Any] = {}
        # Scenario A handles
        self.installer: Any = None
        self.drift_target_name: str | None = None
        self.captured_log_lines: list[str] = []
        # Scenario B handles
        self.install_result: Any = None
        self.skills_target: Path | None = None
        self.dropped_skill_name: str | None = None


@pytest.fixture
def scenario_state() -> _ScenarioState:
    return _ScenarioState()


def _capture_logger() -> tuple[MagicMock, list[str]]:
    """Build a MagicMock logger that records every message at every level.

    The recorded list is the state-delta surface for the log-related slots in
    both scenarios. Using a single list (vs separate per-level lists) keeps
    the universe shape uniform with what a real ``Logger`` consumer sees.
    """
    captured: list[str] = []
    logger = MagicMock()

    def _record(level: str):
        def _emit(message: Any, *_args: Any, **_kwargs: Any) -> None:
            captured.append(f"{level.upper()}: {message}")

        return _emit

    for level in ("info", "warn", "warning", "error", "debug"):
        getattr(logger, level).side_effect = _record(level)

    # Logger.progress_spinner is used inside validate_installation; return a
    # minimal context manager so the spinner call site does not explode.
    spinner = MagicMock()
    spinner.__enter__ = MagicMock(return_value=spinner)
    spinner.__exit__ = MagicMock(return_value=False)
    logger.progress_spinner.return_value = spinner

    return logger, captured


# ---------------------------------------------------------------------------
# Scenario A — Verifier detects content drift on a target template
# ---------------------------------------------------------------------------


_DRIFT_TARGET = "deliver-outside-in-tdd.yaml"
_SOURCE_CONTENT = b"# canonical source content for deliver-outside-in-tdd.yaml\n"
_MUTATED_CONTENT = b"# canonical source content for deliver-outside-in-tdd.yaml!\n"


def _seed_consistent_install(
    tmp_path: Path,
    drift_name: str,
    *,
    drift_target: bool,
) -> tuple[Path, Path, Path]:
    """Lay out a minimal source + target pair the verifier can walk.

    Returns ``(project_root, framework_source, claude_dir)``. Every verifier
    component is satisfied EXCEPT for templates content drift — that is the
    bug under test. The agents loop is skipped (no ``nWave/agents/`` dir
    present, so the verifier skips that component entirely). Scripts loop is
    satisfied by the zero-zero parity case. Essential command-skills are
    seeded so ``commands verified`` returns 6/6.
    """
    project_root = tmp_path / "project"
    framework_source = project_root / "nWave"
    claude_dir = tmp_path / ".claude"

    framework_source.mkdir(parents=True, exist_ok=True)
    (framework_source / "framework-catalog.yaml").write_text(
        "agents: {}\n", encoding="utf-8"
    )

    # Essential command-skills: the verifier expects all 6 SKILL.md to exist
    # under <claude_dir>/skills/<name>/SKILL.md. Seed them so the commands
    # check passes and only the templates content drift can fail the verifier.
    skills_target = claude_dir / "skills"
    skills_target.mkdir(parents=True, exist_ok=True)
    for essential in (
        "nw-deliver",
        "nw-design",
        "nw-discuss",
        "nw-distill",
        "nw-devops",
        "nw-review",
    ):
        skill_dir = skills_target / essential
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {essential}\n---\n", encoding="utf-8"
        )

    templates_source = framework_source / "templates"
    templates_target = claude_dir / "templates"
    templates_source.mkdir(parents=True, exist_ok=True)
    templates_target.mkdir(parents=True, exist_ok=True)

    # Drift candidate: byte-mutated on target when drift_target=True.
    (templates_source / drift_name).write_bytes(_SOURCE_CONTENT)
    (templates_target / drift_name).write_bytes(
        _MUTATED_CONTENT if drift_target else _SOURCE_CONTENT
    )
    # Sibling template: always identical, anchors "21/22 fine, 1 drifted" shape.
    sibling = "AGENT_TEMPLATE.md"
    (templates_source / sibling).write_bytes(b"# sibling template content\n")
    (templates_target / sibling).write_bytes(b"# sibling template content\n")

    return project_root, framework_source, claude_dir


@given(
    parsers.parse(
        'the installer source tree has a template "{name}" with known content'
    )
)
def given_source_template_with_known_content(
    name: str,
    scenario_state: _ScenarioState,
    tmp_path: Path,
):
    project_root, framework_source, claude_dir = _seed_consistent_install(
        tmp_path, name, drift_target=False
    )
    scenario_state.drift_target_name = name
    scenario_state.universe_before["log.contains_drift_marker"] = False
    scenario_state.universe_before["log.names_drifted_file"] = False
    # Stash paths for the next step in this scenario.
    scenario_state._project_root = project_root
    scenario_state._framework_source = framework_source
    scenario_state._claude_dir = claude_dir


@given("the target tree has the same-named template but with one byte mutated")
def given_target_template_mutated(scenario_state: _ScenarioState):
    """Mutate the target file post-seed to model a stale install."""
    target = (
        scenario_state._claude_dir / "templates" / scenario_state.drift_target_name  # type: ignore[arg-type]
    )
    target.write_bytes(_MUTATED_CONTENT)
    # Snapshot the BEFORE state of the verifier-result universe: pre-fix this
    # is what we expect to see post-call (no drift caught, returned ok).
    scenario_state.universe_before["verifier.returned_ok"] = True


@given("every other verifier check is configured to pass")
def given_other_checks_pass(scenario_state: _ScenarioState):
    """Marker step — the actual neutralisation happens inside the When step.

    pytest-bdd evaluates Given→When→Then strictly; the verifier seams must be
    patched in the same ``with`` block as the call itself, so we record an
    intent flag here and apply the patches inside ``when_invoke_validate``.
    """
    scenario_state._neutralize_other_checks = True


@when("the installer's validate_installation driving port is invoked")
def when_invoke_validate(scenario_state: _ScenarioState):
    from scripts.install.install_nwave import NWaveInstaller
    from scripts.install.plugins.base import PluginResult

    logger, captured = _capture_logger()

    # Pre-instantiation patches: PathUtils.get_claude_config_dir +
    # get_project_root drive every path NWaveInstaller resolves at __init__.
    with (
        patch(
            "scripts.install.install_nwave.PathUtils.get_claude_config_dir",
            return_value=scenario_state._claude_dir,
        ),
        patch(
            "scripts.install.install_nwave.PathUtils.get_project_root",
            return_value=scenario_state._project_root,
        ),
    ):
        installer = NWaveInstaller(dry_run=True)

    # Replace the installer logger with our capture so the verifier's drift
    # messages are observable. dry_run=True ensures no real Logger file is
    # opened on disk for the test fixture.
    installer.logger = logger

    mock_registry = MagicMock()
    mock_registry.verify_all.return_value = {
        "templates": PluginResult(success=True, plugin_name="templates", message="ok"),
    }
    mock_verifier_result = MagicMock()
    mock_verifier_result.success = True
    mock_verifier_result.manifest_exists = True
    mock_verifier_result.missing_essential_files = []

    with (
        patch.object(
            installer,
            "_create_plugin_registry",
            return_value=mock_registry,
        ),
        patch.object(
            type(installer),
            "_validate_schema_template",
            return_value=True,
        ),
        patch(
            "scripts.install.install_nwave.InstallationVerifier"
        ) as mock_verifier_cls,
    ):
        mock_verifier_cls.return_value.run_verification.return_value = (
            mock_verifier_result
        )
        returned = installer.validate_installation()

    drift_name = scenario_state.drift_target_name or ""
    log_blob = "\n".join(captured)
    scenario_state.captured_log_lines = captured
    scenario_state.universe_after = {
        "verifier.returned_ok": bool(returned),
        "log.contains_drift_marker": ("drift" in log_blob.lower()),
        "log.names_drifted_file": (drift_name in log_blob),
    }


@then("the verifier reports installation as NOT verified")
def then_not_verified(scenario_state: _ScenarioState):
    # State-delta assertion: the universe MUST transition into "drift caught".
    # Pre-fix the verifier returns True (no drift caught) → this fails.
    assert_state_delta(
        scenario_state.universe_before,
        scenario_state.universe_after,
        universe={
            "verifier.returned_ok",
            "log.contains_drift_marker",
            "log.names_drifted_file",
        },
        expected={
            "verifier.returned_ok": set_to(False),
            "log.contains_drift_marker": set_to(True),
            "log.names_drifted_file": set_to(True),
        },
        strict=True,
    )


@then("the verifier log contains a content drift marker")
def then_drift_marker(scenario_state: _ScenarioState):
    log_blob = "\n".join(scenario_state.captured_log_lines).lower()
    assert "drift" in log_blob, (
        "Expected the verifier to log a content drift marker after detecting "
        "that the target template diverges from the source. Found log lines:\n"
        + "\n".join(scenario_state.captured_log_lines)
    )


@then("the verifier log names the drifted template file")
def then_drift_names_file(scenario_state: _ScenarioState):
    name = scenario_state.drift_target_name or ""
    log_blob = "\n".join(scenario_state.captured_log_lines)
    assert name in log_blob, (
        f"Expected the verifier log to name the drifted file '{name}' so the "
        "operator can fix it. Captured log:\n" + log_blob
    )


# ---------------------------------------------------------------------------
# Scenario B — Skills plugin logs every dropped skill
# ---------------------------------------------------------------------------


_KEEP_AGENT = "stub-public-owner"
_KEEP_SKILL = "nw-keep-me"
_DROP_SKILL = "nw-drop-me"


def _seed_skills_source(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Lay out a minimal source tree exercising the filter pipeline.

    Returns ``(project_root, framework_source, claude_dir)``.
    """
    project_root = tmp_path / "project"
    framework_source = project_root / "nWave"
    claude_dir = tmp_path / ".claude"

    skills_source = framework_source / "skills"
    skills_source.mkdir(parents=True, exist_ok=True)
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Skill kept: wired to a public agent via ownership-map (frontmatter).
    keep_dir = skills_source / _KEEP_SKILL
    keep_dir.mkdir(parents=True, exist_ok=True)
    (keep_dir / "SKILL.md").write_text(
        "---\nname: keep-me\ndescription: kept by filter\n---\n\nbody\n",
        encoding="utf-8",
    )

    # Orphan skill: no owning agent → silently filtered out pre-fix.
    drop_dir = skills_source / _DROP_SKILL
    drop_dir.mkdir(parents=True, exist_ok=True)
    (drop_dir / "SKILL.md").write_text(
        "---\nname: drop-me\ndescription: orphan, no public owner\n---\n\nbody\n",
        encoding="utf-8",
    )

    # Public agent definition naming only the keep-skill in its frontmatter so
    # build_ownership_map wires nw-keep-me → stub-public-owner.
    agents_dir = framework_source / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f"nw-{_KEEP_AGENT}.md").write_text(
        "---\n"
        f"name: {_KEEP_AGENT}\n"
        "description: public stub agent for the regression test\n"
        f"skills: [{_KEEP_SKILL}]\n"
        "---\n\nstub body\n",
        encoding="utf-8",
    )

    # Catalog: stub-public-owner is the sole public agent. Anything not owned
    # by it (orphan or private-owned) must be filtered out.
    (framework_source / "framework-catalog.yaml").write_text(
        "agents:\n"
        f"  {_KEEP_AGENT}:\n"
        "    wave: CROSS_WAVE\n"
        "    role: stub\n"
        "    public: true\n",
        encoding="utf-8",
    )

    return project_root, framework_source, claude_dir


@given(
    parsers.parse(
        'the source tree has a public-owned skill "{keep}" and an orphan skill "{drop}"'
    )
)
def given_source_has_keep_and_drop_skills(
    keep: str,
    drop: str,
    scenario_state: _ScenarioState,
    tmp_path: Path,
):
    assert keep == _KEEP_SKILL, (
        f"Feature/keep-skill mismatch: expected {_KEEP_SKILL}, got {keep}. "
        "Update the seed helper if the feature contract evolves."
    )
    assert drop == _DROP_SKILL, (
        f"Feature/drop-skill mismatch: expected {_DROP_SKILL}, got {drop}. "
        "Update the seed helper if the feature contract evolves."
    )
    project_root, framework_source, claude_dir = _seed_skills_source(tmp_path)
    scenario_state.dropped_skill_name = drop
    scenario_state._project_root = project_root
    scenario_state._framework_source = framework_source
    scenario_state._claude_dir = claude_dir
    scenario_state.universe_before = {
        "log.contains_skipped_marker": False,
        "log.names_filtered_skill": False,
        "log.states_reason": False,
        "target.contains_dropped_skill": False,
    }


@given(parsers.parse('the public-agent catalog excludes "{drop}" from distribution'))
def given_catalog_excludes_drop(drop: str, scenario_state: _ScenarioState):
    """Catalog seeded in the previous step already excludes the orphan skill.

    This step is a discoverability marker — it documents the precondition in
    the feature file and lets the BDD reader trace policy intent without
    having to read the fixture helper.
    """
    assert drop == scenario_state.dropped_skill_name


@when("the skills plugin's install driving port is invoked with the filter active")
def when_skills_plugin_install(scenario_state: _ScenarioState):
    from scripts.install.plugins.base import InstallContext
    from scripts.install.plugins.skills_plugin import SkillsPlugin

    logger, captured = _capture_logger()

    context = InstallContext(
        claude_dir=scenario_state._claude_dir,
        scripts_dir=scenario_state._project_root / "scripts" / "install",
        templates_dir=scenario_state._framework_source / "templates",
        logger=logger,
        project_root=scenario_state._project_root,
        framework_source=scenario_state._framework_source,
        dry_run=False,
        # dev_mode=False ensures the public-agent filter is active. With
        # dev_mode=True the filter is bypassed and the regression would not
        # reproduce — explicit here to document the contract.
        dev_mode=False,
    )

    plugin = SkillsPlugin()
    scenario_state.install_result = plugin.install(context)
    scenario_state.captured_log_lines = captured
    scenario_state.skills_target = scenario_state._claude_dir / "skills"

    log_blob = "\n".join(captured)
    drop = scenario_state.dropped_skill_name or ""
    target_dir = scenario_state.skills_target / drop if drop else None

    scenario_state.universe_after = {
        "log.contains_skipped_marker": ("skipped" in log_blob.lower()),
        "log.names_filtered_skill": (drop in log_blob),
        "log.states_reason": (
            "filter" in log_blob.lower()
            or "public" in log_blob.lower()
            or "catalog" in log_blob.lower()
            or "owner" in log_blob.lower()
        ),
        "target.contains_dropped_skill": bool(target_dir and target_dir.exists()),
    }


@then(parsers.parse('the install log contains a "Skipped" diagnostic for "{drop}"'))
def then_log_contains_skipped(drop: str, scenario_state: _ScenarioState):
    assert_state_delta(
        scenario_state.universe_before,
        scenario_state.universe_after,
        universe={
            "log.contains_skipped_marker",
            "log.names_filtered_skill",
            "log.states_reason",
            "target.contains_dropped_skill",
        },
        expected={
            "log.contains_skipped_marker": set_to(True),
            "log.names_filtered_skill": set_to(True),
            "log.states_reason": set_to(True),
            "target.contains_dropped_skill": set_to(False),
        },
        strict=True,
    )


@then("the install log states the filter as the reason")
def then_log_states_reason(scenario_state: _ScenarioState):
    log_blob = "\n".join(scenario_state.captured_log_lines).lower()
    assert any(
        keyword in log_blob for keyword in ("filter", "public", "catalog", "owner")
    ), (
        "Expected the install log to cite the public-agent filter as the "
        "reason a skill was skipped (one of: 'filter', 'public', 'catalog', "
        "'owner'). Captured log:\n" + "\n".join(scenario_state.captured_log_lines)
    )


@then(parsers.parse('"{drop}" is absent from the installation target'))
def then_drop_skill_absent(drop: str, scenario_state: _ScenarioState):
    target_dir = (scenario_state.skills_target or Path("/nonexistent")) / drop
    assert not target_dir.exists(), (
        f"Filter contract broken: '{drop}' was not supposed to land in the "
        f"target tree, but {target_dir} exists."
    )
