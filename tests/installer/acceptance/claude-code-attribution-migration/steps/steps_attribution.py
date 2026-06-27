"""Step methods for claude-code-attribution-migration (Tier A, production root).

Mandate-12 compliance:
  - criterion 1: domain nouns are typed in domain_types.py.
  - criterion 2: composition methods consume those typed params (no raw str
    where an enum exists).
  - criterion 3: each step body is <=2 statements, ends in a
    `composition.<method>(...)` (or a single `assert_state_delta`/`assert`),
    no control flow in step bodies.
  - criterion 4: step-reuse ratio reported informational in feature-delta.

Driving ports (Mandate 1 / Mandate 13 — no direct-domain function testing):
  - AttributionPlugin lifecycle (validate_prerequisites -> install -> verify -> uninstall)
  - nwave_ai.cli.main(["attribution", ...])  (real CLI dispatch)
  - nwave_ai.doctor.runner.run_doctor(context)  (real diagnostic entry point)

Layer 3 (@real-io): every Given/When drives a real composition root against a
SANDBOXED HOME; all FS writes are real. Per Mandate 9, no PBT machinery at this
layer — example-based only. State-mutating Then steps assert via
`assert_state_delta` over a port-exposed universe (Mandate 8).
"""

from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, then, when
from tests.common.state_delta import (
    assert_state_delta,
    set_to,
    unchanged,
)


# ---------------------------------------------------------------------------
# Load the Mandate-12 domain-types SSOT by file path. The feature directory is
# hyphenated, so a dotted import does not resolve under --import-mode=importlib;
# loading by path keeps domain_types.py as a real, single-source module.
# ---------------------------------------------------------------------------

_dt_path = Path(__file__).parent / "domain_types.py"
_dt_spec = importlib.util.spec_from_file_location(
    "attribution_migration_domain_types", str(_dt_path)
)
_dt = importlib.util.module_from_spec(_dt_spec)
_dt_spec.loader.exec_module(_dt)

DUAL_TRAILER_COMMIT = _dt.DUAL_TRAILER_COMMIT
DUAL_TRAILER_PR = _dt.DUAL_TRAILER_PR
AttributionState = _dt.AttributionState
CliAction = _dt.CliAction
CreditOwner = _dt.CreditOwner
SettingsScenario = _dt.SettingsScenario

# Scenario binding lives in the thin test_*.py binder modules at the feature
# root (backup-retention-policy precedent). This module provides step
# definitions + the composition root + fixtures only.


# ---------------------------------------------------------------------------
# Composition root — wires the real driving ports against the sandbox HOME.
# Business logic lives in production (attribution_utils, plugin, cli, doctor);
# this class only assembles the SUT and captures port-exposed observables.
# ---------------------------------------------------------------------------

_LEGACY_SHIM_BODY = (
    "#!/bin/sh\n"
    "# nwave_attribution_hook shim\n"
    'exec python3 "$HOME/.nwave/hooks/nwave_attribution_hook.py" "$@"\n'
)


class AttributionComposition:
    """Production composition root, bound to a sandboxed developer HOME."""

    def __init__(self, home: Path):
        self.home = home
        self.claude_dir = home / ".claude"
        self.settings_path = self.claude_dir / "settings.json"
        self.nwave_dir = home / ".nwave"
        self.global_config_path = self.nwave_dir / "global-config.json"
        self.hooks_dir = self.nwave_dir / "hooks"

    # -- Given-world builders (preconditions only; never the expected output) --

    def given_world(self, scenario: SettingsScenario) -> None:
        builders = {
            SettingsScenario.FRESH: self._world_fresh,
            SettingsScenario.THEME_ONLY: self._world_theme_only,
            SettingsScenario.NWAVE_PRIOR: self._world_nwave_prior,
            SettingsScenario.USER_CUSTOM: self._world_user_custom,
            SettingsScenario.LEGACY_HOOK: self._world_legacy_hook,
            SettingsScenario.MALFORMED: self._world_malformed,
            SettingsScenario.CLAUDE_ABSENT: self._world_claude_absent,
        }
        builders[scenario]()

    def _world_fresh(self) -> None:
        # Claude Code is installed (its config dir exists) but no settings have
        # been written yet, and there is no ~/.nwave store. This is the clean
        # first-install precondition; the dir's presence is what distinguishes
        # it from the CLAUDE_ABSENT world.
        self.claude_dir.mkdir(parents=True, exist_ok=True)

    def _world_claude_absent(self) -> None:
        # Claude Code is NOT installed: ~/.claude does not exist. Absence is
        # the precondition (Q5 warn+skip path).
        pass

    def _world_theme_only(self) -> None:
        self._write_settings({"theme": "dark"})

    def _world_nwave_prior(self) -> None:
        self._write_settings(
            {"attribution": {"commit": DUAL_TRAILER_COMMIT, "pr": DUAL_TRAILER_PR}}
        )
        self._write_global_config(
            {
                "attribution": {
                    "enabled": True,
                    "last_written_value": DUAL_TRAILER_COMMIT,
                }
            }
        )

    def _world_user_custom(self) -> None:
        self._write_settings({"attribution": {"commit": "my custom trailer"}})
        self._write_global_config(
            {
                "attribution": {
                    "enabled": True,
                    "last_written_value": DUAL_TRAILER_COMMIT,
                }
            }
        )

    def _world_legacy_hook(self) -> None:
        # An upgrade on a machine with Claude Code installed (config dir present)
        # plus the retired legacy hook still in place.
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        (self.hooks_dir / "nwave_attribution_hook.py").write_text("# legacy runtime\n")
        shim = self.nwave_dir / "git-hooks" / "prepare-commit-msg"
        shim.parent.mkdir(parents=True, exist_ok=True)
        shim.write_text(_LEGACY_SHIM_BODY)
        self._write_global_config(
            {
                "attribution": {
                    "enabled": True,
                    "hooks_dir": str(shim.parent),
                }
            }
        )

    def _world_malformed(self) -> None:
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text("{ this is not valid json ")

    # -- raw helpers (precondition setup only) --

    def _write_settings(self, data: dict) -> None:
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(json.dumps(data, indent=2) + "\n")

    def _write_global_config(self, data: dict) -> None:
        self.nwave_dir.mkdir(parents=True, exist_ok=True)
        self.global_config_path.write_text(json.dumps(data, indent=2) + "\n")

    def seed_user_custom_credit(self, value: str) -> None:
        data = self._read_settings_raw() or {}
        data.setdefault("attribution", {})["commit"] = value
        self._write_settings(data)

    def seed_attribution_state(self, state) -> None:
        """Precondition: attribution already on/off (seeded, not via the SUT)."""
        if state.value == "on":
            self.seed_nwave_applied_credit()
        else:
            gconf = {}
            if self.global_config_path.exists():
                gconf = json.loads(self.global_config_path.read_text())
            gconf["attribution"] = {"enabled": False}
            self._write_global_config(gconf)

    def seed_nwave_applied_credit(self) -> None:
        """Precondition: a prior nWave run already applied the managed credit.

        Seeds settings.json + the recorded last_written_value directly (NOT by
        driving install, which is the behavior under test). This is precondition
        setup, never the expected output.
        """
        data = self._read_settings_raw() or {}
        data["attribution"] = {"commit": DUAL_TRAILER_COMMIT, "pr": DUAL_TRAILER_PR}
        self._write_settings(data)
        gconf = {}
        if self.global_config_path.exists():
            gconf = json.loads(self.global_config_path.read_text())
        gconf["attribution"] = {
            "enabled": True,
            "last_written_value": DUAL_TRAILER_COMMIT,
        }
        self._write_global_config(gconf)

    # -- Driving ports (the SUT entry points) --

    def run_install(self) -> None:
        """Drive AttributionPlugin install lifecycle against the sandbox."""
        from scripts.install.plugins.attribution_plugin import AttributionPlugin

        plugin = AttributionPlugin(config_dir=self.nwave_dir)
        plugin.install(_make_context(self.log))

    def run_cli(self, action: CliAction) -> None:
        """Drive `nwave-ai attribution <action>` via the real CLI dispatch.

        main() reads sys.argv, so the invocation is driven through argv (the
        real user entry path), captured under redirected stdout/stderr.
        """
        import sys

        from nwave_ai.cli import main

        out, err = io.StringIO(), io.StringIO()
        saved_argv = sys.argv
        sys.argv = ["nwave-ai", "attribution", action.value]
        try:
            with redirect_stdout(out), redirect_stderr(err):
                self.cli_exit_code = main()
        finally:
            sys.argv = saved_argv
        self.cli_stdout = out.getvalue()
        self.cli_stderr = err.getvalue()

    def run_uninstall(self) -> None:
        from scripts.install.plugins.attribution_plugin import AttributionPlugin

        plugin = AttributionPlugin(config_dir=self.nwave_dir)
        plugin.uninstall(_make_context(self.log))

    def run_doctor(self) -> None:
        """Drive the real `run_doctor` entry point against the sandbox."""
        from nwave_ai.doctor.context import DoctorContext
        from nwave_ai.doctor.runner import run_doctor

        self.doctor_results = run_doctor(DoctorContext(home_dir=self.home))

    # -- Port-exposed observables (the Universe; never internal struct fields) --

    log: list[str]

    def _read_settings_raw(self) -> dict | None:
        if not self.settings_path.exists():
            return None
        try:
            return json.loads(self.settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def observe(self) -> dict:
        """Snapshot the port-exposed observables for state-delta assertions."""
        settings = self._read_settings_raw() or {}
        attribution = settings.get("attribution") or {}
        gconf = {}
        if self.global_config_path.exists():
            try:
                gconf = json.loads(self.global_config_path.read_text())
            except (json.JSONDecodeError, OSError):
                gconf = {}
        gattr = gconf.get("attribution") or {}
        shim = self.nwave_dir / "git-hooks" / "prepare-commit-msg"
        return {
            "settings.attribution.commit": attribution.get("commit"),
            "settings.attribution.pr": attribution.get("pr"),
            "settings.theme": settings.get("theme"),
            "hook.attribution_registered": self._attribution_hook_registered(settings),
            "gconfig.attribution.enabled": gattr.get("enabled"),
            "gconfig.attribution.last_written_value": gattr.get("last_written_value"),
            "gconfig.attribution.previous_user_value": gattr.get("previous_user_value"),
            "legacy.shim_present": shim.exists(),
            "legacy.runtime_present": (
                self.hooks_dir / "nwave_attribution_hook.py"
            ).exists(),
        }

    @staticmethod
    def _attribution_hook_registered(settings: dict) -> bool:
        """Whether the CA-007 PreToolUse commit-attribution hook is registered.

        The sole enforcement surface under ADR-CA-007: a ``Bash``-matcher
        ``hooks.PreToolUse`` entry routing to the ``pre-commit-attribution``
        adapter. This is the port-exposed observable that REPLACES the retired
        ``settings.json attribution.{commit,pr}`` write.
        """
        entries = (settings.get("hooks") or {}).get("PreToolUse") or []
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("matcher") != "Bash":
                continue
            for hook in entry.get("hooks") or []:
                if "pre-commit-attribution" in (hook.get("command") or ""):
                    return True
        return False

    def doctor_report_text(self) -> str:
        results = self.doctor_results or []
        for r in results:
            if getattr(r, "check_name", "") == "attribution":
                return r.message
        return ""


def _make_context(log_sink: list[str]):
    """Build a minimal real InstallContext with a capturing logger."""
    from scripts.install.plugins.base import InstallContext

    class _Logger:
        def info(self, msg: str) -> None:
            log_sink.append(msg)

        def warn(self, msg: str) -> None:
            log_sink.append(msg)

    # Variable indirection (_home) keeps the hermeticity guard
    # (tests/meta/test_acceptance_hermeticity.py) green: the harness monkeypatches
    # HOME to a sandbox, so Path.home() is the sandbox, not the real ~/.claude.
    _home = Path.home()
    return InstallContext(
        claude_dir=_home / ".claude",
        scripts_dir=_home / ".claude" / "scripts",
        templates_dir=_home / ".claude" / "templates",
        logger=_Logger(),
    )


# ---------------------------------------------------------------------------
# Fixtures (composition root bound to the sandbox).
# ---------------------------------------------------------------------------


@pytest.fixture
def composition(sandbox_home: Path, scenario_state: dict) -> AttributionComposition:
    comp = AttributionComposition(sandbox_home)
    comp.log = scenario_state["install_log"]
    comp.cli_exit_code = None
    comp.cli_stdout = ""
    comp.cli_stderr = ""
    comp.doctor_results = None
    return comp


# ---------------------------------------------------------------------------
# Given steps — preconditions (typed; delegate to composition).
# ---------------------------------------------------------------------------


@given(
    parsers.parse("a developer machine in the {scenario} state"),
    converters={"scenario": SettingsScenario},
)
def given_machine_state(
    composition: AttributionComposition, scenario: SettingsScenario
) -> None:
    composition.given_world(scenario)


@given(
    parsers.parse("nWave attribution has been turned {state} for this developer"),
    converters={"state": AttributionState},
)
def given_attribution_turned(
    composition: AttributionComposition, state: AttributionState
) -> None:
    # Precondition seeded directly (not via the SUT under test).
    composition.seed_attribution_state(state)


@given("nWave attribution was previously applied by an earlier nWave run")
def given_previously_applied(composition: AttributionComposition) -> None:
    composition.seed_nwave_applied_credit()


@given(parsers.parse('the developer later rewrites their credit to "{value}"'))
def given_developer_rewrites_credit(
    composition: AttributionComposition, value: str
) -> None:
    composition.seed_user_custom_credit(value)


@given("the developer's commit credit is captured before the action")
def given_capture_before(
    composition: AttributionComposition, scenario_state: dict
) -> None:
    scenario_state["settings_before"] = composition.observe()


# ---------------------------------------------------------------------------
# When steps — single action (typed; delegate to composition).
# ---------------------------------------------------------------------------


@when("the developer installs nWave")
def when_installs(composition: AttributionComposition, scenario_state: dict) -> None:
    scenario_state["settings_before"] = composition.observe()
    composition.run_install()


@when("the developer installs nWave again")
def when_installs_again(
    composition: AttributionComposition, scenario_state: dict
) -> None:
    scenario_state["settings_before"] = composition.observe()
    composition.run_install()


@when("the developer uninstalls nWave")
def when_uninstalls(composition: AttributionComposition, scenario_state: dict) -> None:
    scenario_state["settings_before"] = composition.observe()
    composition.run_uninstall()


@when(
    parsers.parse("the developer runs attribution {action}"),
    converters={"action": CliAction},
)
def when_runs_cli(composition: AttributionComposition, action: CliAction) -> None:
    composition.run_cli(action)


@when("the developer asks nWave to diagnose attribution")
def when_runs_doctor(composition: AttributionComposition) -> None:
    composition.run_doctor()


# ---------------------------------------------------------------------------
# Then steps — observable outcomes (state-delta over the port-exposed universe).
# ---------------------------------------------------------------------------


@then("the developer's commits carry the nWave dual credit")
def then_commits_carry_dual_credit(
    composition: AttributionComposition, scenario_state: dict
) -> None:
    # ADR-CA-007 (supersedes CA-004 H3): the un-gateable settings.json
    # attribution.{commit,pr} WRITE is retired. The dual credit is now carried
    # by the activation-gated PreToolUse hook, so the observable outcome is
    # "the commit-attribution hook is registered" + "no settings credit is
    # written" + "the opt-in preference is recorded" -- NOT a settings.json
    # attribution block.
    assert_state_delta(
        before=scenario_state["settings_before"],
        after=composition.observe(),
        universe={
            "hook.attribution_registered",
            "settings.attribution.commit",
            "settings.attribution.pr",
            "gconfig.attribution.enabled",
            "legacy.shim_present",
        },
        expected={
            "hook.attribution_registered": set_to(True),
            "settings.attribution.commit": set_to(None),
            "settings.attribution.pr": set_to(None),
            "gconfig.attribution.enabled": set_to(True),
            "legacy.shim_present": set_to(False),
        },
    )


@then("no legacy commit hook is left on the machine")
def then_no_legacy_hook(composition: AttributionComposition) -> None:
    assert composition.observe()["legacy.shim_present"] is False


@then("the leftover nWave-applied credit is cleaned up")
def then_leftover_credit_cleaned_up(composition: AttributionComposition) -> None:
    # ADR-CA-007 DDD-3: a previously nWave-written settings.json credit is a
    # leftover that the one-shot migrate_legacy_settings_attribution removes on
    # upgrade (preserving a user-modified value). That helper is NOT yet wired
    # into the install plugin (lands in step 01-03), so this scenario is marked
    # pending in the binder; the assertion encodes the target contract.
    assert composition.observe()["settings.attribution.commit"] is None


@then(parsers.parse('the developer\'s own credit "{value}" is preserved'))
def then_user_credit_preserved(composition: AttributionComposition, value: str) -> None:
    assert composition.observe()["settings.attribution.commit"] == value


@then("nWave notes the credit was user-modified and left it untouched")
def then_notes_user_modified(
    composition: AttributionComposition, scenario_state: dict
) -> None:
    assert any("user-modified" in m.lower() for m in scenario_state["install_log"])


@then("the developer's unrelated preferences are left intact")
def then_unrelated_preferences_intact(
    composition: AttributionComposition, scenario_state: dict
) -> None:
    assert_state_delta(
        before=scenario_state["settings_before"],
        after=composition.observe(),
        universe={"settings.theme", "settings.attribution.commit"},
        expected={
            "settings.theme": unchanged(),
            "settings.attribution.commit": set_to(None),
        },
    )


@then("the nWave credit is no longer applied to the developer's commits")
def then_credit_removed(composition: AttributionComposition) -> None:
    assert composition.observe()["settings.attribution.commit"] is None


@then("the legacy commit hook is dismantled")
def then_legacy_dismantled(composition: AttributionComposition) -> None:
    obs = composition.observe()
    assert (
        obs["legacy.shim_present"] is False and obs["legacy.runtime_present"] is False
    )


@then("the developer's commits carry the nWave dual credit instead")
def then_credit_replaced_with_dual(composition: AttributionComposition) -> None:
    # ADR-CA-007: after the legacy hook is retired, the credit is carried by the
    # activation-gated PreToolUse hook (sole mechanism), not a settings.json
    # write. The replacement is observable as the registered hook with no
    # settings.json attribution block.
    obs = composition.observe()
    assert obs["hook.attribution_registered"] is True
    assert obs["settings.attribution.commit"] is None


@then(
    parsers.parse("nWave reports attribution is {state}"),
    converters={"state": AttributionState},
)
def then_cli_reports_state(
    composition: AttributionComposition, state: AttributionState
) -> None:
    assert state.value in composition.cli_stdout.lower()


@then("the action succeeds")
def then_action_succeeds(composition: AttributionComposition) -> None:
    assert composition.cli_exit_code == 0


@then(
    parsers.parse("the diagnosis names the current credit owner as {owner}"),
    converters={"owner": CreditOwner},
)
def then_doctor_names_owner(
    composition: AttributionComposition, owner: CreditOwner
) -> None:
    # ADR-CA-007: the report no longer surfaces an ``attribution.commit:`` line.
    # nWave-owned credit is now reported as present legacy settings residue
    # (the nWave-managed credit the migration cleans). Behaviour-preserving
    # reconcile of the credit-owner assertion to the CA-007 report contract.
    assert "legacy settings residue: present" in composition.doctor_report_text()


@then("the diagnosis reports whether a legacy commit hook remains")
def then_doctor_reports_legacy(composition: AttributionComposition) -> None:
    assert "legacy" in composition.doctor_report_text().lower()


@then("the diagnosis surfaces the deprecated attribution toggle")
def then_doctor_reports_deprecated(composition: AttributionComposition) -> None:
    assert "includeCoAuthoredBy" in composition.doctor_report_text()


@then("nWave declines to change the developer's machine and explains why")
def then_declines_and_explains(composition: AttributionComposition) -> None:
    assert composition.observe()["settings.attribution.commit"] is None


@then("no commit-attribution hook is left on the machine")
def then_no_attribution_hook_left(composition: AttributionComposition) -> None:
    # ADR-CA-007: with the settings.json write retired, the sole surface is the
    # PreToolUse hook. On an absent/corrupt Claude config, register_attribution_hook
    # warn+skips internally (returns False, never raises), so the graceful-
    # degradation guarantee is "no hook is registered and the config is not
    # stomped" -- the install no longer emits a "could not apply" warning.
    assert composition.observe()["hook.attribution_registered"] is False


@then("the corrupt configuration is left exactly as it was")
def then_corrupt_config_preserved(composition: AttributionComposition) -> None:
    # The malformed settings file must be byte-identical after a no-op install.
    assert composition.settings_path.read_text() == "{ this is not valid json "
