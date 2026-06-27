"""Production composition root for the attribution-activation-coupling suite.

Pillar 3 — "app as in production": the SUT is built from the real production
entry points:

  * the real ``AttributionPlugin.{install,uninstall}`` (installer driving port),
  * the real ``nwave_ai.cli._handle_attribution`` (CLI driving port),
  * the real ``AttributionCheck.run`` over a real ``DoctorContext`` (doctor
    driving port),
  * the real ``CommitAttributionService.plan_rewrite`` (the CA-006 rewrite
    driving-port seam — asserts the trailer OUTCOME for AB-1, never re-tests the
    rewriter internals),
  * the real activation gate ``run_gate`` (AB-2/AB-3 — reused from the
    activation-gating harness; this composition does NOT re-derive marker /
    global-config fixtures, it delegates to ``ActivationGatingComposition``).

Only the filesystem roots (``~/.claude`` / ``~/.nwave`` / the project marker) are
redirected to a ``tmp_path`` sandbox — the one "environment" substitution the
Architecture of Reference prescribes for driven-internal FS ports at the
subprocess/FS-acceptance layer (layer 3, example-based, Mandate 9/11).

Mandate-12 criteria:
- (2) every method consumes the typed enums from ``domain_types`` — no raw
  ``str`` where a domain enum exists.
- (3) all business logic (seeding state, reading settings, classifying outcomes)
  lives HERE as the single source of truth; step bodies in
  ``steps_attribution.py`` are ≤2 statements ending in a
  ``composition.<method>(...)`` call.

Production symbols are imported LAZILY inside methods so this module imports
cleanly today (tests collect, never BROKEN). The genuinely-new
``migrate_legacy_settings_attribution`` helper is a Mandate-7 RED scaffold that
raises ``AssertionError`` (RED) when reached — the fail-for-right-reason gate.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from tests.des.acceptance.activation_gating.steps.composition import (
    ActivationGatingComposition,
)
from tests.des.acceptance.activation_gating.steps.domain_types import (
    GlobalMode,
    HookCommand,
    HookEnvelope,
    MarkerState,
)

from .domain_types import (
    NWAVE_MANAGED_COMMIT,
    USER_AUTHORED_COMMIT,
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


# ---------------------------------------------------------------------------
# Mapping helpers — typed domain noun -> activation-gating fixture inputs.
# These translate THIS feature's RepoActivationState into the (marker, mode)
# pair the reused activation harness already knows how to lay down. SSOT: the
# activation truth table lives in the activation_gating suite, not duplicated.
# ---------------------------------------------------------------------------

_ACTIVATION_TO_MARKER_MODE: dict[
    RepoActivationState, tuple[MarkerState, GlobalMode]
] = {
    RepoActivationState.ACTIVE: (MarkerState.ENABLED, GlobalMode.OPT_IN),
    RepoActivationState.INACTIVE_STICKY: (MarkerState.DISABLED, GlobalMode.OPT_IN),
    RepoActivationState.UNMARKED: (MarkerState.ABSENT, GlobalMode.OPT_IN),
}

_RESIDUE_VALUE: dict[SettingsResidue, str | None] = {
    SettingsResidue.NWAVE_MANAGED: NWAVE_MANAGED_COMMIT,
    SettingsResidue.USER_MODIFIED: USER_AUTHORED_COMMIT,
    SettingsResidue.ABSENT: None,
}


@dataclass
class AttributionCouplingComposition:
    """Production composition root over a sandbox ``~/.claude`` + ``~/.nwave`` +
    a ``tmp_path`` project marker.

    ``capture_universe`` returns the port-exposed observable snapshot consumed by
    ``assert_state_delta`` (Mandate 8). Keys are port-exposed names ONLY (commit
    message trailer count, settings.json attribution/\u200bhooks content, global-config
    preference, doctor report lines, CLI exit code) — never internal struct
    fields.
    """

    home_dir: Path
    project_root: Path

    # The activation harness handle — reused for AB-2/AB-3 gate behaviour.
    activation: ActivationGatingComposition = field(init=False)

    # Observable results captured by the most recent action (port-exposed).
    last_trailer_outcome: TrailerOutcome | None = None
    last_committed_message: str | None = None
    last_cli_exit_code: int | None = None
    last_cli_stdout: str = ""
    last_install_message: str = ""
    last_doctor_message: str = ""

    def __post_init__(self) -> None:
        self.activation = ActivationGatingComposition(
            project_root=self.project_root, home_dir=self.home_dir
        )

    # ---- path helpers (port-exposed file locations) ----

    @property
    def claude_dir(self) -> Path:
        return self.home_dir / ".claude"

    @property
    def config_dir(self) -> Path:
        return self.home_dir / ".nwave"

    @property
    def settings_path(self) -> Path:
        return self.claude_dir / "settings.json"

    # ---- PRECONDITION builders (typed in, on-disk state out) ----

    def given_repo_activation(self, state: RepoActivationState) -> None:
        """Lay down the (marker x mode) on-disk state for a repo activation posture.

        Reuses the activation-gating fixture builders — no re-derivation of the
        marker / global-config shape (Mandate-12 step-reuse).
        """
        marker, mode = _ACTIVATION_TO_MARKER_MODE[state]
        self.activation.given_global_mode(mode)
        self.activation.given_marker(marker)

    def given_attribution_preference(self, preference: AttributionPreference) -> None:
        """Record (or omit) the SSOT ``attribution.enabled`` preference."""
        if preference is AttributionPreference.UNSET:
            return
        from scripts.install.attribution_utils import write_attribution_preference

        write_attribution_preference(
            self.config_dir, enabled=preference is AttributionPreference.ON
        )

    def given_settings_availability(self, availability: SettingsAvailability) -> None:
        """Seed ``~/.claude/settings.json`` readability (AB-11 fail-open matrix)."""
        if availability is SettingsAvailability.ABSENT:
            return
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        if availability is SettingsAvailability.CORRUPT:
            self.settings_path.write_text("{ not json", encoding="utf-8")
            return
        self.settings_path.write_text(json.dumps({}), encoding="utf-8")

    def given_legacy_settings_residue(self, residue: SettingsResidue) -> None:
        """Seed a pre-existing ``settings.json attribution.commit`` block (AB-4/AB-5).

        For an nWave-managed residue, also records the ``last_written_value``
        baseline in global-config so the classifier recognises it as managed.
        """
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        value = _RESIDUE_VALUE[residue]
        settings: dict = {}
        if value is not None:
            settings["attribution"] = {"commit": value}
        self.settings_path.write_text(json.dumps(settings), encoding="utf-8")
        if residue is SettingsResidue.NWAVE_MANAGED:
            from scripts.install.attribution_utils import (
                read_global_config,
                write_global_config,
            )

            config = read_global_config(self.config_dir)
            config.setdefault("attribution", {})["last_written_value"] = value
            write_global_config(self.config_dir, config)

    def given_registered_hook(self, registration: HookRegistration) -> None:
        """Seed the ``pre-commit-attribution`` PreToolUse entry registered or not."""
        from scripts.install.attribution_utils import register_attribution_hook

        register_attribution_hook(
            enabled=registration is HookRegistration.REGISTERED,
            claude_dir=self.claude_dir,
        )

    def given_des_guard_registered(self) -> None:
        """Seed the existing DES ``pre-bash`` guard entry (coexistence base)."""
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        settings = self._read_settings_or_empty()
        settings.setdefault("hooks", {}).setdefault("PreToolUse", []).append(
            {
                "matcher": "Bash",
                "hooks": [
                    {"type": "command", "command": "# des-hook:pre-bash\nexit 0"}
                ],
            }
        )
        self.settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    def given_deprecated_flag_at(self, location: DeprecatedKeyLocation) -> None:
        """Seed ``includeCoAuthoredBy: false`` at top-level or nested (AB-9 / DDD-7)."""
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        settings = self._read_settings_or_empty()
        if location is DeprecatedKeyLocation.TOP_LEVEL:
            settings["includeCoAuthoredBy"] = False
        else:
            settings.setdefault("attribution", {})["includeCoAuthoredBy"] = False
        self.settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    # ---- ACTIONS (drive real production code; capture observable result) ----

    def operator_runs_install(self) -> None:
        """Drive the real ``AttributionPlugin.install`` (installer driving port)."""
        self.last_install_message = (
            self._plugin().install(self._install_context()).message
        )

    def operator_runs_uninstall(self) -> None:
        """Drive the real ``AttributionPlugin.uninstall``."""
        self.last_install_message = (
            self._plugin().uninstall(self._install_context()).message
        )

    def operator_runs_attribution(self, action: ToggleAction) -> None:
        """Drive the real ``nwave-ai attribution on|off|status`` CLI handler."""
        import contextlib
        import io
        import os

        from nwave_ai.cli import _handle_attribution

        out = io.StringIO()
        previous_cwd = os.getcwd()
        os.chdir(self.project_root)
        try:
            with contextlib.redirect_stdout(out):
                self.last_cli_exit_code = _handle_attribution([action.value])
        finally:
            os.chdir(previous_cwd)
        self.last_cli_stdout = out.getvalue()

    def operator_runs_attribution_subprocess(self, action: ToggleAction) -> None:
        """Drive the real ``nwave-ai`` CLI as a SUBPROCESS (walking-skeleton adapter).

        Spawns the actual user-facing entry point (``python -m nwave_ai.cli``)
        with HOME redirected to the sandbox, verifying the real arg-parse +
        wiring + exit code path — not just the in-process handler function.
        """
        import os
        import subprocess
        import sys

        project_root = Path(__file__).resolve().parents[6]
        env = {
            **os.environ,
            "HOME": str(self.home_dir),
            "PYTHONPATH": str(project_root),
        }
        proc = subprocess.run(
            [sys.executable, "-m", "nwave_ai.cli", "attribution", action.value],
            cwd=str(self.project_root),
            env=env,
            capture_output=True,
            text=True,
        )
        self.last_cli_exit_code = proc.returncode
        self.last_cli_stdout = proc.stdout

    def operator_runs_doctor(self) -> None:
        """Drive the real ``AttributionCheck.run`` over a real ``DoctorContext``."""
        from nwave_ai.doctor.checks.attribution import AttributionCheck
        from nwave_ai.doctor.context import DoctorContext

        result = AttributionCheck().run(
            DoctorContext(home_dir=self.home_dir, project_root=self.project_root)
        )
        self.last_doctor_message = result.message

    def claude_commits(self, form: CommitForm) -> None:
        """Drive the activation-gated commit path; capture the trailer OUTCOME (AB-1..3).

        Runs the real activation gate over a ``pre-tool-use`` hook envelope; only
        when the gate DISPATCHES (active repo) does the real
        ``CommitAttributionService.plan_rewrite`` run to produce the rewritten
        command carrying the dual trailer. An inactive repo exits the gate at 0
        with the command unchanged (no trailer) — proving the per-repo coupling.
        """
        from des.application.commit_attribution_service import CommitAttributionService

        command = self._commit_command(form)
        envelope = HookEnvelope(
            command=HookCommand.PRE_TOOL_USE, cwd=str(self.project_root), raw=command
        )
        gate = self.activation.dispatch_hook  # noqa: F841 — keep the real seam visible
        run = self._run_gate(envelope)
        if run.gate_outcome.name == "ALLOWED_EXIT_0":
            self.last_committed_message = command
            self.last_trailer_outcome = TrailerOutcome.NO_TRAILER
            return
        plan = CommitAttributionService().plan_rewrite(command)
        rewritten = plan.rewritten_command if plan.action == "mutate" else command
        self.last_committed_message = rewritten
        self.last_trailer_outcome = self._classify_trailer(rewritten)

    # ---- universe capture (Mandate 8 — port-exposed observable names only) ----

    def capture_universe(self) -> dict[str, object]:
        """Snapshot the port-exposed observable surface."""
        return {
            "settings.attribution.commit": self._settings_attribution_commit(),
            "settings.hooks.attribution_registered": self._attribution_hook_registered(),
            "settings.hooks.des_guard_registered": self._des_guard_registered(),
            "settings.raw_present": self.settings_path.exists(),
            "global_config.attribution.enabled": self._preference_enabled(),
            "commit.trailer_outcome": self.last_trailer_outcome,
            "commit.coauthor_count": self._coauthor_count(self.last_committed_message),
            "cli.exit_code": self.last_cli_exit_code,
        }

    # ---- read helpers (port-exposed projections) ----

    def settings_attribution_commit(self) -> str | None:
        return self._settings_attribution_commit()

    def attribution_hook_is_registered(self) -> bool:
        return self._attribution_hook_registered()

    def des_guard_is_registered(self) -> bool:
        return self._des_guard_registered()

    def preference_is_enabled(self) -> bool | None:
        return self._preference_enabled()

    def trailer_outcome(self) -> TrailerOutcome | None:
        return self.last_trailer_outcome

    def coauthor_count(self) -> int:
        return self._coauthor_count(self.last_committed_message)

    def cli_exit_code(self) -> int | None:
        return self.last_cli_exit_code

    def cli_stdout(self) -> str:
        return self.last_cli_stdout

    def doctor_message(self) -> str:
        return self.last_doctor_message

    def install_message(self) -> str:
        return self.last_install_message

    # ---- internals ----

    def _run_gate(self, envelope: HookEnvelope):
        from des.adapters.drivers.hooks import activation_gate

        return activation_gate.run_gate(
            envelope=envelope,
            project_root=self.project_root,
            global_config_path=self.activation.global_config_path,
        )

    def _plugin(self):
        from scripts.install.plugins.attribution_plugin import AttributionPlugin

        return AttributionPlugin(config_dir=self.config_dir)

    def _install_context(self):
        from scripts.install.plugins.base import InstallContext

        project_root = Path(__file__).resolve().parents[6]
        return InstallContext(
            claude_dir=self.claude_dir,
            scripts_dir=project_root / "scripts" / "install",
            templates_dir=project_root / "nWave" / "templates",
            logger=logging.getLogger("test.attribution-coupling.install"),
            project_root=project_root,
            framework_source=project_root / "nWave",
            dry_run=False,
        )

    @staticmethod
    def _commit_command(form: CommitForm) -> str:
        if form is CommitForm.AND_CHAIN:
            return 'git add -A && git commit -m "feat: thing"'
        return 'git commit -m "feat: thing"'

    @staticmethod
    def _classify_trailer(message: str) -> TrailerOutcome:
        count = AttributionCouplingComposition._coauthor_count(message)
        return TrailerOutcome.DUAL_TRAILER if count == 2 else TrailerOutcome.NO_TRAILER

    @staticmethod
    def _coauthor_count(message: str | None) -> int:
        if not message:
            return 0
        return message.count("Co-Authored-By:")

    def _read_settings_or_empty(self) -> dict:
        if not self.settings_path.exists():
            return {}
        try:
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _settings_attribution_commit(self) -> str | None:
        settings = self._read_settings_or_empty()
        return (settings.get("attribution") or {}).get("commit")

    def _preference_enabled(self) -> bool | None:
        from scripts.install.attribution_utils import read_attribution_preference

        return read_attribution_preference(self.config_dir)

    def _attribution_hook_registered(self) -> bool:
        settings = self._read_settings_or_empty()
        entries = settings.get("hooks", {}).get("PreToolUse", [])
        return any(
            "pre-commit-attribution" in hook.get("command", "")
            for entry in entries
            if isinstance(entry, dict)
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        )

    def _des_guard_registered(self) -> bool:
        settings = self._read_settings_or_empty()
        entries = settings.get("hooks", {}).get("PreToolUse", [])
        return any(
            "des-hook:pre-bash" in hook.get("command", "")
            for entry in entries
            if isinstance(entry, dict)
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        )
