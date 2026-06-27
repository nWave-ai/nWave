"""Production composition root for the plugin/skill deliverable-type acceptance suite.

Pillar 3 -- "app as in production": the SUT is built from real production entry
points:
- the enforcement gate is driven through the REAL ``PreToolUseService.validate``
  driving port, wired by the REAL ``service_factory.create_pre_tool_use_service``
  with the production ``DesEnforcementPolicy`` (no re-impl of the gate logic);
- config resolution reads through the REAL ``DESConfig.deliverable_type`` over a
  ``tmp_path`` project + sandbox HOME;
- root-only detection runs the REAL ``deliverable_type_detector.detect_deliverable_type``.

Only the project filesystem + HOME are redirected to a ``tmp_path`` sandbox --
the one "environment" substitution the Architecture of Reference prescribes for a
driven-internal FS port at the subprocess/FS-acceptance layer (layer 3,
example-based). Audit I/O uses the production ``NullAuditLogWriter`` and a frozen
time provider (driven-external/non-deterministic ports -> fakes).

Mandate-12 criteria:
- (2) every service method consumes the typed enums from ``domain_types`` -- no
  raw ``str`` where a domain enum exists.
- (3) step bodies (in ``steps_plugin_skill.py``) are <=2 statements ending in a
  ``composition.<method>(...)`` call -- all logic lives HERE and in production.

Production symbols that DELIVER has not yet implemented are imported LAZILY
inside methods so this module imports cleanly today (tests COLLECT, never
BROKEN). The RED scaffolds (``DesEnforcementPolicy`` exempt branch,
``DESConfig.deliverable_type``, ``deliverable_type_detector``) make the calls
resolve and raise ``AssertionError`` (RED) -- the fail-for-right-reason gate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from tests.des.acceptance.plugin_skill_deliverable_type.steps.domain_types import (
    ConfigDeclaration,
    DeliverableType,
    DispatchEnvelope,
    ExemptionReason,
    GateOutcome,
    Marker,
    ResolvedType,
    RootMarker,
    StepIdPresence,
    wire_value,
)


# ---------------------------------------------------------------------------
# Prompt builders (PRECONDITION fixtures -- never the expected output). They
# turn a typed enum into the raw prompt text the driving port receives.
# ---------------------------------------------------------------------------

_STEP_ID_FRAGMENT = "step 03-04"  # keyword-anchored, matches STEP_ID_PATTERN
_MARKER_FRAGMENT: dict[Marker, str] = {
    Marker.NONE: "",
    Marker.VALIDATION_REQUIRED: "<!-- DES-VALIDATION : required -->",
    Marker.ENFORCEMENT_EXEMPT: "<!-- DES-ENFORCEMENT : exempt -->",
}


def _build_prompt(step_id: StepIdPresence, marker: Marker) -> str:
    """Assemble the dispatch prompt from the typed step-id + marker fixtures."""
    parts: list[str] = []
    if marker is not Marker.NONE:
        parts.append(_MARKER_FRAGMENT[marker])
    if step_id is StepIdPresence.HAS_STEP_ID:
        parts.append(f"Please run {_STEP_ID_FRAGMENT} of the plan.")
    else:
        parts.append("Please summarise the design notes.")
    return "\n".join(parts)


@dataclass
class PluginSkillComposition:
    """Production composition root over a ``tmp_path`` project + sandbox HOME.

    Shared step-method vocabulary (Tier A) and Tier-B ``@rule`` methods both
    drive this object. ``capture_universe`` returns the port-exposed observable
    snapshot consumed by ``assert_state_delta`` (Mandate 8).
    """

    project_root: Path
    home_dir: Path

    # Observable results captured by the most recent action (port-exposed).
    last_gate_outcome: GateOutcome | None = None
    last_exit_code: int | None = None
    last_exemption_reason: ExemptionReason | None = None
    last_decision_carries_exempt_marker: bool | None = None
    last_resolved_type: ResolvedType | None = None
    last_detected_type: ResolvedType | None = None
    last_config_warning: str | None = None
    last_handler_exit_code: int | None = None
    recorded: dict[str, object] = field(default_factory=dict)
    before_universe: dict[str, object] | None = None

    # ---- path helpers (port-exposed file locations) ----

    @property
    def project_config_path(self) -> Path:
        return self.project_root / ".nwave" / "des-config.json"

    @property
    def global_config_path(self) -> Path:
        return self.home_dir / ".nwave" / "global-config.json"

    # ---- PRECONDITION builders (typed in, on-disk / in-memory state out) ----

    def given_config_declaration(self, declaration: ConfigDeclaration) -> None:
        """Write (or omit) the declared ``deliverable_type`` per the precedence inputs."""
        project = self.project_config_path
        glob = self.global_config_path
        project.parent.mkdir(parents=True, exist_ok=True)
        glob.parent.mkdir(parents=True, exist_ok=True)
        if declaration is ConfigDeclaration.ABSENT:
            return
        if declaration is ConfigDeclaration.GLOBAL_PLUGIN:
            glob.write_text(
                json.dumps({"defaults": {"deliverable_type": "plugin"}}),
                encoding="utf-8",
            )
            return
        if declaration is ConfigDeclaration.PROJECT_TYPO_WITH_ROOT_SKILLS:
            # A typo'd declaration AND a root skills/ dir: the safe default must NOT
            # fall through to detection, else this repo is silently exempted as skill.
            (self.project_root / "skills").mkdir(parents=True, exist_ok=True)
            project.write_text(
                json.dumps({"deliverable_type": "plugn"}), encoding="utf-8"
            )
            return
        value = {
            ConfigDeclaration.PROJECT_PLUGIN: "plugin",
            ConfigDeclaration.PROJECT_SKILL: "skill",
            ConfigDeclaration.PROJECT_APPLICATION: "application",
            ConfigDeclaration.PROJECT_TYPO: "plugn",
        }[declaration]
        project.write_text(json.dumps({"deliverable_type": value}), encoding="utf-8")

    def given_root_marker(self, marker: RootMarker) -> None:
        """Lay down exactly one root (or nested-collision) FS marker for detection."""
        root = self.project_root
        root.mkdir(parents=True, exist_ok=True)
        if marker is RootMarker.NONE:
            return
        if marker is RootMarker.CLAUDE_PLUGIN_DIR:
            (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
            return
        if marker is RootMarker.PLUGIN_JSON:
            (root / "plugin.json").write_text("{}", encoding="utf-8")
            return
        if marker is RootMarker.MARKETPLACE_JSON:
            (root / "marketplace.json").write_text("{}", encoding="utf-8")
            return
        if marker is RootMarker.ROOT_SKILLS_DIR:
            (root / "skills").mkdir(parents=True, exist_ok=True)
            return
        if marker is RootMarker.ROOT_COMMANDS_DIR:
            (root / "commands").mkdir(parents=True, exist_ok=True)
            return
        if marker is RootMarker.ROOT_HOOKS_DIR:
            (root / "hooks").mkdir(parents=True, exist_ok=True)
            return
        if marker is RootMarker.NESTED_NWAVE_SKILLS:
            # The collision guard: a NON-root nWave/skills/ (this very repo's shape).
            (root / "nWave" / "skills").mkdir(parents=True, exist_ok=True)
            return

    # ---- ACTIONS (drive the real production code; capture observable result) ----

    def dispatch(self, envelope: DispatchEnvelope) -> None:
        """Drive the REAL enforcement gate through ``PreToolUseService.validate``.

        Builds the production service via ``service_factory`` with the resolved
        ``deliverable_type`` threaded exactly as the runtime handler will, then
        calls the driving port and records the observable HookDecision shape.
        """
        from des.adapters.driven.logging.null_audit_log_writer import (
            NullAuditLogWriter,
        )
        from des.adapters.drivers.hooks import service_factory
        from des.ports.driver_ports.pre_tool_use_port import PreToolUseInput

        prompt = _build_prompt(envelope.step_id, envelope.marker)
        self.recorded["prompt"] = prompt
        service = service_factory.create_pre_tool_use_service(
            audit_writer_factory=NullAuditLogWriter,
            deliverable_type=wire_value(envelope.deliverable),
        )
        decision = service.validate(PreToolUseInput(prompt=prompt))
        self._record_decision(decision, envelope)

    def dispatch_via_handler(self, envelope: DispatchEnvelope) -> None:
        """Drive the REAL Claude Code hook entry point ``handle_pre_tool_use``.

        This is the DRIVING-ADAPTER seam (one layer ABOVE the service): a hook
        JSON payload on stdin -> ``pre_tool_use_handler.handle_pre_tool_use()``,
        which resolves ``deliverable_type`` itself (via ``_resolve_deliverable_type``)
        and threads it into ``service_factory``. The project's deliverable type is
        declared on disk under the dispatch CWD (``.nwave/des-config.json``), so the
        handler must read it for the exemption to take effect.

        Observable: the handler's process exit code (0 = allowed, 2 = blocked).
        Today the handler's ``_resolve_deliverable_type`` returns ``None`` (seam
        not wired) -> a plugin project's step dispatch is still BLOCKED (exit 2):
        the right-reason RED. DELIVER wires the read and the dispatch is allowed
        (exit 0).
        """
        import io
        import os

        from des.adapters.drivers.hooks import (
            claude_code_hook_adapter as adapter,
        )
        from des.adapters.drivers.hooks import hook_protocol

        prompt = _build_prompt(envelope.step_id, envelope.marker)
        stdin_payload = json.dumps(
            {"tool_name": "Agent", "tool_input": {"prompt": prompt}}
        )
        self.recorded["prompt"] = prompt
        previous_cwd = os.getcwd()
        os.chdir(self.project_root)
        previous_stdin = self._stdin_swap(io.StringIO(stdin_payload))
        previous_print = self._silence_print()
        try:
            self.last_handler_exit_code = adapter.handle_pre_tool_use()
        finally:
            self._restore_stdin(previous_stdin)
            self._restore_print(previous_print)
            os.chdir(previous_cwd)
        self.last_gate_outcome = (
            GateOutcome.EXEMPT
            if self.last_handler_exit_code == 0
            else GateOutcome.BLOCKED
        )
        # NullAuditLogWriter keeps the handler's audit I/O off the developer's FS.
        _ = hook_protocol

    @staticmethod
    def _stdin_swap(buffer):
        import sys

        previous = sys.stdin
        sys.stdin = buffer
        return previous

    @staticmethod
    def _restore_stdin(previous) -> None:
        import sys

        sys.stdin = previous

    @staticmethod
    def _silence_print():
        import builtins

        previous = builtins.print
        builtins.print = lambda *a, **kw: None
        return previous

    @staticmethod
    def _restore_print(previous) -> None:
        import builtins

        builtins.print = previous

    def _record_decision(self, decision, envelope: DispatchEnvelope) -> None:
        """Map the production HookDecision onto the test-domain observables."""
        self.last_exit_code = decision.exit_code
        self.last_gate_outcome = (
            GateOutcome.BLOCKED if decision.action == "block" else GateOutcome.EXEMPT
        )
        # The per-dispatch exempt marker must NOT be what carried a type exemption
        # (the issue's core promise). Observe whether the prompt held the marker.
        prompt = self.recorded.get("prompt", "")
        self.last_decision_carries_exempt_marker = "DES-ENFORCEMENT : exempt" in str(
            prompt
        )
        self.last_exemption_reason = self._classify_exemption(envelope)

    @staticmethod
    def _classify_exemption(envelope: DispatchEnvelope) -> ExemptionReason | None:
        if envelope.step_id is StepIdPresence.NO_STEP_ID:
            return ExemptionReason.NO_STEP_ID
        if envelope.marker is not Marker.NONE:
            return ExemptionReason.EXPLICIT_MARKER
        if envelope.deliverable in (DeliverableType.PLUGIN, DeliverableType.SKILL):
            return ExemptionReason.TYPE_CARRIED
        return None

    def resolve_config_type(self) -> None:
        """Resolve ``deliverable_type`` via the REAL ``DESConfig`` precedence.

        Snapshots the port-exposed universe BEFORE the read so a state-mutating
        ``Then`` can assert the resolution was a PURE read -- the on-disk config
        text and the whole root FS tree must be byte-identical afterwards
        (@contract-shape:unbounded-preservation, D1). A mis-spelled declaration
        must short-circuit to the safe default WITHOUT a root ``skills/`` folder
        rescuing it AND without touching anything on disk.
        """
        from des.adapters.driven.config.des_config import DESConfig

        self.before_universe = self.capture_universe()
        config = DESConfig(
            cwd=self.project_root, global_config_path=self.global_config_path
        )
        resolved = config.deliverable_type
        self.last_resolved_type = self._to_resolved(resolved)

    def detect_root_type(self) -> None:
        """Run the REAL root-only FS detection (ADR-PST-002, DDD-4)."""
        from des.adapters.driven.config.deliverable_type_detector import (
            detect_deliverable_type,
        )

        detected = detect_deliverable_type(self.project_root)
        self.last_detected_type = self._to_resolved(detected)

    @staticmethod
    def _to_resolved(value: str | None) -> ResolvedType:
        if value is None:
            return ResolvedType.NONE
        return {
            "application": ResolvedType.APPLICATION,
            "plugin": ResolvedType.PLUGIN,
            "skill": ResolvedType.SKILL,
        }.get(value, ResolvedType.NONE)

    # ---- universe capture (Mandate 8 -- port-exposed observable names only) ----

    def capture_universe(self) -> dict[str, object]:
        """Snapshot the port-exposed observable surface.

        Keys are port-exposed names ONLY (gate outcome, exit code, exemption
        channel, resolved type, on-disk config text) -- never internal fields.
        """
        return {
            "gate.outcome": self.last_gate_outcome,
            "gate.exit_code": self.last_exit_code,
            "gate.exemption_reason": self.last_exemption_reason,
            "gate.dispatch_carries_exempt_marker": (
                self.last_decision_carries_exempt_marker
            ),
            "config.resolved_type": self.last_resolved_type,
            "config.detected_type": self.last_detected_type,
            "project_config.text": self._read_or_none(self.project_config_path),
            "global_config.text": self._read_or_none(self.global_config_path),
            "root.fs_tree_hash": self._root_fs_tree_hash(),
        }

    @staticmethod
    def _read_or_none(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def _root_fs_tree_hash(self) -> str:
        """A content hash over the WHOLE project root tree (paths + bytes).

        Port-exposed observable: "did resolving the deliverable type leave any
        on-disk side effect?" A pure read must keep this byte-identical -- the
        @contract-shape:unbounded-preservation obligation (D1). Covers the
        typo+root-``skills/`` case: the safe-default short-circuit must NOT
        create, delete, or touch any file (e.g. it must not synthesise a marker).
        """
        import hashlib

        root = self.project_root
        digest = hashlib.sha256()
        for path in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
            relative = path.relative_to(root).as_posix()
            if path.is_dir():
                digest.update(f"D:{relative}\0".encode())
                continue
            digest.update(f"F:{relative}\0".encode())
            try:
                digest.update(path.read_bytes())
            except OSError:
                digest.update(b"<unreadable>")
            digest.update(b"\0")
        return digest.hexdigest()


def build_production_composition(tmp_path: Path, monkeypatch) -> PluginSkillComposition:
    """Build the production composition root over an isolated project + sandbox HOME."""
    project_root = tmp_path / "project"
    home_dir = tmp_path / "home"
    project_root.mkdir(parents=True, exist_ok=True)
    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))
    return PluginSkillComposition(project_root=project_root, home_dir=home_dir)


# Frozen instant for any future time-sensitive observable (kept explicit so the
# driven-external time port stays a fake, never the system clock).
FROZEN_NOW = datetime(2026, 6, 26, 10, 0, 0, tzinfo=timezone.utc)
