"""Production composition root for the activation-gating acceptance suite.

Pillar 3 — "app as in production": the SUT is built from the real production
entry points (the pure ``resolve_activation`` policy, the real
``AutoMarkingService`` over a ``FileSystemPort``, the real gitignore transforms,
the real ``DESConfig`` reader, the real ``hook_router.main()`` dispatch, and the
real ``nwave_ai.cli.main`` CLI). Only the project filesystem is redirected to a
``tmp_path`` sandbox — that is the one "environment" substitution, exactly as
the Architecture of Reference prescribes for a driven-internal FS port at the
subprocess/FS-acceptance layer (layer 3, example-based).

Mandate-12 criteria:
- (2) every service method consumes the typed enums from ``domain_types`` — no
  raw ``str`` where a domain enum exists.
- (3) step bodies (in ``steps_activation_gating.py``) are ≤2 statements ending
  in ``composition.<service>.<method>(...)`` — all logic lives HERE and in
  production, never inlined in a step.

Production symbols are imported LAZILY inside methods so this module imports
cleanly today (tests collect, never BROKEN). The RED scaffolds at
``src/des/domain/activation_policy.py`` etc. make the lazy imports resolve and
raise ``AssertionError`` (RED) when called — the fail-for-right-reason gate.
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from tests.des.acceptance.activation_gating.steps.domain_types import (
    Activation,
    AdoptionResult,
    AdoptionTrigger,
    CliResult,
    CompletionShell,
    FsMode,
    GateOutcome,
    GitignoreVariant,
    GlobalMode,
    HookEnvelope,
    MarkerState,
    PriorUseEvidence,
)


# ---------------------------------------------------------------------------
# Fixture-shape catalogue (PRECONDITION builders — never the expected output).
# These translate a typed enum into on-disk state. They set up INPUT state only;
# the feature's behaviour is asserted by reading back through production code.
# ---------------------------------------------------------------------------

_GITIGNORE_LINES: dict[GitignoreVariant, str] = {
    GitignoreVariant.SLASH_TRAILING: ".nwave/\n",
    GitignoreVariant.NO_SLASH: ".nwave\n",
    GitignoreVariant.LEADING_SLASH: "/.nwave/\n",
    GitignoreVariant.LEADING_NO_TRAILING: "/.nwave\n",
    GitignoreVariant.NO_NWAVE_LINE: "build/\n*.log\n",
    GitignoreVariant.ALREADY_FIXED: ".nwave/*\n!.nwave/local-config.json\n",
}


@dataclass
class ActivationGatingComposition:
    """Production composition root over a ``tmp_path`` project + global sandbox.

    Shared step-method vocabulary (Tier A) and Tier-B ``@rule`` methods both
    drive this object. ``capture_universe`` returns the port-exposed observable
    snapshot consumed by ``assert_state_delta`` (Mandate 8).
    """

    project_root: Path
    home_dir: Path
    fs_mode: FsMode = FsMode.WRITABLE

    # Observable results captured by the most recent action (port-exposed).
    last_resolution: Activation | None = None
    last_gate_outcome: GateOutcome | None = None
    last_adoption: AdoptionResult | None = None
    last_cli_result: CliResult | None = None
    last_cli_stdout: str = ""
    last_cli_stderr: str = ""
    last_completion_script: str = ""
    captured_handler_stdin: str | None = None
    recorded: dict[str, object] = field(default_factory=dict)

    # ---- path helpers (port-exposed file locations) ----

    @property
    def marker_path(self) -> Path:
        return self.project_root / ".nwave" / "local-config.json"

    @property
    def nested_gitignore_path(self) -> Path:
        return self.project_root / ".nwave" / ".gitignore"

    @property
    def root_gitignore_path(self) -> Path:
        return self.project_root / ".gitignore"

    @property
    def global_config_path(self) -> Path:
        return self.home_dir / ".nwave" / "global-config.json"

    # ---- PRECONDITION builders (typed in, on-disk state out) ----

    def given_global_mode(self, mode: GlobalMode) -> None:
        """Write (or omit/corrupt) the global config's ``activation.mode``."""
        path = self.global_config_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode is GlobalMode.ABSENT:
            if path.exists():
                path.unlink()
            return
        if mode is GlobalMode.CORRUPT:
            path.write_text("{ this is not json", encoding="utf-8")
            return
        path.write_text(
            json.dumps({"activation": {"mode": mode.value}}), encoding="utf-8"
        )

    def given_marker(self, marker: MarkerState) -> None:
        """Write (or omit) the per-project marker ``enabled_for_repo``."""
        path = self.marker_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if marker is MarkerState.ABSENT:
            if path.exists():
                path.unlink()
            return
        enabled = marker is MarkerState.ENABLED
        path.write_text(json.dumps({"enabled_for_repo": enabled}), encoding="utf-8")

    def given_prior_use_evidence(self, evidence: PriorUseEvidence) -> None:
        """Lay down exactly one prior-use signal (or none / the bare-config decoy)."""
        root = self.project_root
        if evidence is PriorUseEvidence.NONE:
            return
        if evidence is PriorUseEvidence.BARE_DES_CONFIG:
            (root / ".nwave").mkdir(parents=True, exist_ok=True)
            (root / ".nwave" / "des-config.json").write_text("{}", encoding="utf-8")
            return
        if evidence is PriorUseEvidence.AUDIT_LOG_NONEMPTY:
            # Real JsonlAuditLogWriter shape (OQ-3): .nwave/des/logs/audit-YYYY-MM-DD.log
            logs = root / ".nwave" / "des" / "logs"
            logs.mkdir(parents=True, exist_ok=True)
            (logs / "audit-2026-06-18.log").write_text(
                '{"event":"phase_entered","timestamp":"2026-06-18T00:00:00Z"}\n',
                encoding="utf-8",
            )
            return
        if evidence is PriorUseEvidence.EXECUTION_LOG:
            d = root / "docs" / "feature" / "some-feature"
            d.mkdir(parents=True, exist_ok=True)
            (d / "execution-log.json").write_text("{}", encoding="utf-8")
            return
        if evidence is PriorUseEvidence.DELIVER_DIR:
            (root / "docs" / "feature" / "some-feature" / "deliver").mkdir(
                parents=True, exist_ok=True
            )
            return
        if evidence is PriorUseEvidence.FEATURE_DELTA:
            d = root / "docs" / "feature" / "some-feature"
            d.mkdir(parents=True, exist_ok=True)
            (d / "feature-delta.md").write_text("# delta\n", encoding="utf-8")
            return

    def given_root_gitignore(self, variant: GitignoreVariant) -> None:
        self.root_gitignore_path.write_text(_GITIGNORE_LINES[variant], encoding="utf-8")

    def given_nested_gitignore_banner(self) -> None:
        """Lay down the shipped nested ``.nwave/.gitignore`` (banner + ``*``)."""
        path = self.nested_gitignore_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Generated by nWave. Do not edit.\n*\n", encoding="utf-8")

    def given_fs_mode(self, mode: FsMode) -> None:
        self.fs_mode = mode

    def given_git_repo(self) -> None:
        """Initialize a real git repo in ``project_root`` so ``git check-ignore`` works.

        ``_marker_tracked`` runs the real ``git check-ignore`` probe; without a
        repository git exits 128 ("not a repository"), which would make every
        trackability scenario BROKEN instead of RED on unskip. A bare ``git init``
        with a minimal identity (no commits needed) is enough for the probe.
        """
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=self.project_root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@nwave.local"],
            cwd=self.project_root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "nWave Test"],
            cwd=self.project_root,
            check=True,
            capture_output=True,
        )

    # ---- ACTIONS (drive the real production code; capture observable result) ----

    def resolve_activation(self) -> None:
        """Resolve active/inactive via the real pure domain policy (ADR-AG-002).

        Reads marker + mode through the real ``DESConfig`` then feeds the real
        ``resolve_activation`` pure function — production wiring, not a re-impl.
        """
        from des.adapters.driven.config.des_config import DESConfig
        from des.domain.activation_policy import resolve_activation

        config = DESConfig(
            cwd=self.project_root, global_config_path=self.global_config_path
        )
        verdict = resolve_activation(config.enabled_for_repo, config.activation_mode)
        self.last_resolution = Activation.ACTIVE if verdict else Activation.INACTIVE

    def dispatch_hook(self, envelope: HookEnvelope) -> None:
        """Drive a hook through the real ``hook_router.main()`` gate (DDD-5/6/9).

        The router buffers stdin, resolves activation, exempts SessionStart,
        adopts-and-proceeds on pre-task, else allow/exit-0 when inactive. The
        composition records the observable gate outcome + the bytes the handler
        actually saw (rewind contract).
        """
        from des.adapters.drivers.hooks import activation_gate

        self.recorded.setdefault("before", self.capture_universe())
        self.recorded["sent_stdin"] = envelope.raw
        outcome = activation_gate.run_gate(
            envelope=envelope,
            project_root=self.project_root,
            global_config_path=self.global_config_path,
        )
        # Adapt the production GateOutcome enum to the test-domain enum at the
        # boundary (production never imports test types; names are the contract).
        self.last_gate_outcome = GateOutcome[outcome.gate_outcome.name]
        self.captured_handler_stdin = outcome.handler_stdin
        self.recorded["exit_code"] = outcome.exit_code

    def adopt(self, trigger: AdoptionTrigger) -> None:
        """Drive the real ``AutoMarkingService.adopt_if_warranted`` (ADR-AG-003)."""
        from des.application.auto_marking_service import (
            AdoptionTrigger as ProdTrigger,
        )
        from des.application.auto_marking_service import (
            AutoMarkingService,
        )

        self.recorded["before"] = self.capture_universe()
        outcome = AutoMarkingService(
            read_only=self.fs_mode is FsMode.READ_ONLY
        ).adopt_if_warranted(
            project_root=self.project_root, trigger=ProdTrigger[trigger.name]
        )
        # Adapt the production outcome enum to the test-domain enum at the
        # boundary (production never imports test types; names are the contract).
        self.last_adoption = AdoptionResult[outcome.name]

    def fix_gitignore(self) -> None:
        """Apply the dual-layer gitignore fix via the real transforms (ADR-AG-004)."""
        from des.application.auto_marking_service import AutoMarkingService

        self.recorded.setdefault("before", self.capture_universe())
        AutoMarkingService(read_only=self.fs_mode is FsMode.READ_ONLY).fix_gitignore(
            project_root=self.project_root
        )
        self.recorded.setdefault(
            "gitignore_after_first", self.capture_universe()["root_gitignore.text"]
        )

    def run_cli(self, argv: list[str]) -> None:
        """Drive the real ``nwave_ai.cli.main`` CLI verb (DDD-12).

        ``_get_config_dir`` is redirected to the sandbox home and side-effecting
        installers patched at the step layer; here we only invoke and capture.
        """
        import os

        from nwave_ai import cli

        self.recorded.setdefault("before", self.capture_universe())
        out, err = io.StringIO(), io.StringIO()
        previous_cwd = os.getcwd()
        os.chdir(self.project_root)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                exit_code = cli.main_with_argv(argv)  # thin testable entry over main()
        finally:
            os.chdir(previous_cwd)
        self.last_cli_stdout = out.getvalue()
        self.last_cli_stderr = err.getvalue()
        self.recorded["cli_exit_code"] = exit_code
        self.last_cli_result = (
            CliResult.SUCCESS if exit_code == 0 else CliResult.USAGE_ERROR
        )

    def generate_completion(self, shell: CompletionShell) -> None:
        """Generate a shell-completion script via the real generator (DDD-14)."""
        from nwave_ai.completion import generate_completion

        self.last_completion_script = generate_completion(shell.value)

    # ---- universe capture (Mandate 8 — port-exposed observable names only) ----

    def capture_universe(self) -> dict[str, object]:
        """Snapshot the port-exposed observable surface.

        Keys are port-exposed names ONLY (file contents, resolved verdict,
        gate outcome, exit codes) — never internal struct fields.
        """
        return {
            "marker.enabled_for_repo": self._marker_value(),
            "marker.file_exists": self.marker_path.exists(),
            "root_gitignore.text": self._read_or_none(self.root_gitignore_path),
            "nested_gitignore.text": self._read_or_none(self.nested_gitignore_path),
            "marker.git_tracked": self._marker_tracked(),
            "resolution": self.last_resolution,
            "gate.outcome": self.last_gate_outcome,
            "adoption.result": self.last_adoption,
            "global_config.text": self._read_or_none(self.global_config_path),
        }

    # ---- read helpers ----

    def _marker_value(self) -> bool | None:
        if not self.marker_path.exists():
            return None
        try:
            data = json.loads(self.marker_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        value = data.get("enabled_for_repo")
        return value if isinstance(value, bool) else None

    def _marker_tracked(self) -> bool:
        """Whether ``git check-ignore`` reports the marker as NOT ignored.

        Delegates to the real ``GitTrackProbe`` (a thin ``git check-ignore``
        wrapper) — the behavioural probe ADR-AG-004 (d) requires.
        """
        from des.adapters.driven.git.git_track_probe import is_tracked

        return is_tracked(self.project_root, self.marker_path)

    @staticmethod
    def _read_or_none(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None
