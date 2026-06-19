"""Composition root for the des-verify-integrity mode-aware acceptance slice.

ADR-028 D4.2 / slice-02 (Mandate-12, Pillar 3). Wires the PRODUCTION
des-verify-integrity CLI entry point (`des.cli.verify_deliver_integrity.main`)
against a tmp_path deliver project. Business logic lives here as the single
source of truth; step bodies delegate to `VerifyIntegrityComposition` methods
and never inline logic.

Layer 3 (subprocess/FS acceptance): the CLI is the driving port; the only
driven port is the real filesystem (tmp_path). No PBT machinery (Mandate 9/11).

Mode resolution: slice-02 reads `workflow.mode` from
`{project_dir}/.nwave/config.yaml`, the SAME path slice-01's des-init-log uses
(`init_log._resolve_workflow_mode`). The composition writes that file so the
ATs exercise the production resolver, not a test re-implementation.

Classic fixtures: the classic (roadmap-based) deliver project is built with the
PRODUCTION `des-roadmap init` CLI (`des.cli.roadmap.main`) so the roadmap.json
is schema-valid by construction -- the no-regression ATs assert the existing
0/1/2 contract against a real classic project, not a hand-rolled JSON shape.
"""

from __future__ import annotations

import contextlib
import io
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from des.cli.roadmap import main as roadmap_main
from des.cli.verify_deliver_integrity import main as verify_integrity_main

from .domain_types import (
    ClassicProjectShape,
    FeatureId,
    IntegrityVerdict,
    LedgerState,
    LeftoverRoadmap,
    VerifyInvocation,
    WorkflowMode,
)


# TDD phases the default rigor profile records per step (RED/GREEN/COMMIT).
# A COMPLETE classic project logs all three for every step; an INCOMPLETE one
# omits the last, which the integrity verifier reports as a violation.
_CLASSIC_TDD_PHASES = ("RED", "GREEN", "COMMIT")


@dataclass
class VerifyIntegrityResult:
    """Observable outcome of one des-verify-integrity invocation."""

    exit_code: int
    output: str

    @property
    def verdict(self) -> IntegrityVerdict:
        """Map the CLI exit code onto the user-observable verdict."""
        return {
            0: IntegrityVerdict.VERIFIED,
            1: IntegrityVerdict.VIOLATION,
            2: IntegrityVerdict.USAGE_ERROR,
        }.get(self.exit_code, IntegrityVerdict.USAGE_ERROR)


@dataclass
class VerifyIntegrityComposition:
    """Production-wired composition root for the des-verify-integrity slice.

    `project_dir` is a real tmp_path directory acting as the deliver project.
    The `.nwave/config.yaml` workflow mode is written via `set_workflow_mode`;
    the AT-completion ledger, a classic roadmap+log pair, and a leftover
    roadmap.json are provisioned via the dedicated methods so each scenario
    builds exactly the project state it needs.
    """

    project_dir: Path
    feature_id: FeatureId = field(default=FeatureId("unset"))

    @property
    def _nwave_dir(self) -> Path:
        return self.project_dir / ".nwave"

    @property
    def roadmap_path(self) -> Path:
        return self.project_dir / "roadmap.json"

    @property
    def execution_log_path(self) -> Path:
        return self.project_dir / "execution-log.json"

    @property
    def ledger_path(self) -> Path:
        """AT-completion ledger for this feature (ADR-028 D3).

        `.nwave/telemetry/atdd-pure/{feature_id}.jsonl` -- the atdd_pure audit
        artifact that replaces per-step execution-log.json.
        """
        return self._nwave_dir / "telemetry" / "atdd-pure" / f"{self.feature_id}.jsonl"

    def create_project(self, feature_id: FeatureId) -> None:
        """Create the deliver project directory for `feature_id`."""
        self.feature_id = feature_id
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self._nwave_dir.mkdir(parents=True, exist_ok=True)

    def set_workflow_mode(self, mode: WorkflowMode) -> None:
        """Record the project workflow mode in .nwave/config.yaml.

        WorkflowMode.UNSET writes no `workflow.mode` key -- the default
        (config-without-mode) state des-verify-integrity must treat as classic.
        """
        if mode is WorkflowMode.UNSET:
            return
        config_path = self._nwave_dir / "config.yaml"
        config_path.write_text(
            yaml.safe_dump({"workflow": {"mode": mode.value}}, sort_keys=True),
            encoding="utf-8",
        )

    def provision_ledger(self, state: LedgerState) -> None:
        """Provision the AT-completion ledger in the requested state.

        PRESENT_ALL_SHIPPED -- write an append-only JSONL ledger whose records
                               mark every slice phase-boundary, with the final
                               slice shipped.
        ABSENT              -- write nothing; the ledger file does not exist.
        """
        if state is LedgerState.ABSENT:
            return
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        records = [
            {"slice_id": "slice-01", "at_ids": ["AT-1"], "phase": "G_COMMIT"},
        ]
        self.ledger_path.write_text(
            "\n".join(json.dumps(r) for r in records) + "\n",
            encoding="utf-8",
        )

    def _write_valid_roadmap(self) -> str:
        """Write a schema-valid roadmap.json via the production des-roadmap CLI.

        Returns the single step id the skeleton roadmap declares.
        """
        roadmap_main(
            [
                "init",
                "--project-id",
                str(self.feature_id),
                "--goal",
                "Slice-02 acceptance fixture",
                "--phases",
                "1",
                "--steps",
                "01:1",
                "--output",
                str(self.roadmap_path),
            ]
        )
        roadmap = json.loads(self.roadmap_path.read_text())
        step = roadmap["phases"][0]["steps"][0]
        return step.get("step_id") or step["id"]

    def provision_classic_project(self, shape: ClassicProjectShape) -> None:
        """Build a classic (roadmap-based) deliver project of the given shape.

        COMPLETE_TRACES   -- roadmap.json + an execution-log.json recording every
                             TDD phase for the step -> the existing 0/1/2
                             contract yields verified (exit 0).
        INCOMPLETE_TRACES -- roadmap.json + an execution-log.json missing the
                             final TDD phase -> integrity violation (exit 1).
        """
        step_id = self._write_valid_roadmap()
        phases = (
            _CLASSIC_TDD_PHASES
            if shape is ClassicProjectShape.COMPLETE_TRACES
            else _CLASSIC_TDD_PHASES[:-1]
        )
        log = {
            "schema_version": "3.0",
            "feature_id": str(self.feature_id),
            "events": [
                {"sid": step_id, "p": phase, "s": "EXECUTED", "d": "PASS"}
                for phase in phases
            ],
        }
        self.execution_log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")

    def provision_leftover_roadmap(self, leftover: LeftoverRoadmap) -> None:
        """Provision (or not) a leftover roadmap.json in an atdd_pure project.

        ABSENT  -- write nothing; the expected atdd_pure state.
        PRESENT -- write a leftover, schema-valid roadmap.json. Under atdd_pure a
                   roadmap.json is the WRONG artifact; its presence is a WARNING,
                   not an error (ADR-028 D4.2). The roadmap is schema-valid so
                   the warning contract is asserted on the artifact's mere
                   presence, not on a malformed-roadmap side effect.
        """
        if leftover is LeftoverRoadmap.ABSENT:
            return
        self._write_valid_roadmap()

    def run_verify_integrity(
        self, invocation: VerifyInvocation = VerifyInvocation.FULL
    ) -> VerifyIntegrityResult:
        """Invoke the production des-verify-integrity CLI via its argv entry point.

        `invocation` selects the default (full) cross-reference or the
        `--roadmap-only` flag path.
        """
        argv = [str(self.project_dir)]
        if invocation is VerifyInvocation.ROADMAP_ONLY:
            argv.append("--roadmap-only")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            exit_code = verify_integrity_main(argv)
        return VerifyIntegrityResult(exit_code=exit_code, output=buffer.getvalue())

    def capture_universe(self) -> dict[str, object]:
        """Port-exposed observable snapshot for assert_state_delta (Mandate 8).

        des-verify-integrity has a pure-read contract: it MUST NOT mutate the
        deliver project. The universe is the set of project files whose
        existence the verifier could be tempted to touch -- the state-delta
        guard proves the verifier reads without writing.
        """
        return {
            "roadmap.json.exists": self.roadmap_path.exists(),
            "execution_log.json.exists": self.execution_log_path.exists(),
            "ledger.exists": self.ledger_path.exists(),
        }
