"""Composition root for the des-init-log mode-aware acceptance slice (Mandate-12, Pillar 3).

Wires the PRODUCTION des-init-log CLI entry point (`des.cli.init_log.main`)
against a tmp_path deliver project. Business logic lives here as the single
source of truth; step bodies delegate to `InitLogComposition` methods and
never inline logic.

Layer 3 (subprocess/FS acceptance): the CLI is the driving port; the only
driven port is the real filesystem (tmp_path). No PBT machinery (Mandate 9/11).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from des.cli.init_log import main as init_log_main

from .domain_types import FeatureId, WorkflowMode


@dataclass
class InitLogResult:
    """Observable outcome of one des-init-log invocation."""

    exit_code: int
    output: str


@dataclass
class InitLogComposition:
    """Production-wired composition root for the des-init-log slice.

    `project_dir` is a real tmp_path directory acting as the deliver project.
    The `.nwave/config.yaml` workflow mode is written via `set_workflow_mode`.
    """

    project_dir: Path
    feature_id: FeatureId = field(default=FeatureId("unset"))

    @property
    def _nwave_dir(self) -> Path:
        return self.project_dir / ".nwave"

    @property
    def execution_log_path(self) -> Path:
        return self.project_dir / "execution-log.json"

    def create_project(self, feature_id: FeatureId) -> None:
        """Create the deliver project directory for `feature_id`."""
        self.feature_id = feature_id
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self._nwave_dir.mkdir(parents=True, exist_ok=True)

    def set_workflow_mode(self, mode: WorkflowMode) -> None:
        """Record the project workflow mode in .nwave/config.yaml.

        WorkflowMode.UNSET writes no `workflow.mode` key -- it is the default,
        no-config-file (or config-without-mode) state des-init-log must treat
        as classic.
        """
        if mode is WorkflowMode.UNSET:
            return
        config_path = self._nwave_dir / "config.yaml"
        config_path.write_text(
            yaml.safe_dump({"workflow": {"mode": mode.value}}, sort_keys=True),
            encoding="utf-8",
        )

    def run_init_log(self) -> InitLogResult:
        """Invoke the production des-init-log CLI through its argv entry point."""
        import contextlib
        import io

        argv = [
            "--project-dir",
            str(self.project_dir),
            "--feature-id",
            str(self.feature_id),
        ]
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            exit_code = init_log_main(argv)
        return InitLogResult(exit_code=exit_code, output=buffer.getvalue())

    def capture_universe(self) -> dict[str, object]:
        """Port-exposed observable snapshot for assert_state_delta (Mandate 8).

        Universe entries are observable filesystem facts -- never internal
        struct fields.
        """
        return {
            "execution_log.exists": self.execution_log_path.exists(),
        }
