"""Composition-root support for the pi-kata-tdd-flow acceptance suite.

Single source of truth for the real I/O the step methods drive: the reused DES
CLIs (``des.cli.init_log`` / ``des.cli.log_phase``), the UNCHANGED
``subagent-stop`` adapter round-trip, a real tmp git repo, and the NEW kata
bootstrap + transcript-context helpers. Step bodies delegate here -- they hold no
business logic (Mandate-12 criterion 3).

Layer 3: real subprocess + real filesystem, example-only (Mandate 11). Engine
reused UNCHANGED (K2): zero ``src/des/**`` change. All test state stays under
``tmp_path`` -- no ``.nwave/des/des-task-active*`` leaks into the main repo.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# NEW surface under test (RED scaffolds until DELIVER implements them).
from scripts.install.pi_kata import bootstrap, transcript_context
from tests.des.acceptance.pi_kata_tdd_flow.steps.domain_types import (
    COMPLETE_CYCLE,
    PhaseStatus,
    TddPhase,
)


_REPO_ROOT = Path(__file__).resolve().parents[5]
_SRC = _REPO_ROOT / "src"


# --------------------------------------------------------------------------- #
# Reused DES CLIs (UNCHANGED) + adapter round-trip
# --------------------------------------------------------------------------- #


def _run_des_cli(
    module: str, args: list[str], cwd: Path
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        env={"PYTHONPATH": str(_SRC), "PATH": os.environ.get("PATH", "")},
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )


def subagent_stop_roundtrip(payload: dict, cwd: Path) -> tuple[int, str]:
    """Drive the UNCHANGED subagent-stop adapter, return (exit, stdout)."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "des.adapters.drivers.hooks.claude_code_hook_adapter",
            "subagent-stop",
        ],
        input=json.dumps(payload),
        env={
            "PYTHONPATH": str(_SRC),
            "PATH": os.environ.get("PATH", ""),
            "DES_AUDIT_LOG_DIR": str(cwd / ".nwave" / "des" / "logs"),
        },
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode, (proc.stdout or "")


# --------------------------------------------------------------------------- #
# Real tmp project + git repo (test fixtures, NOT the feature's expected output)
# --------------------------------------------------------------------------- #


def make_activated_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / ".nwave" / "des" / "logs").mkdir(parents=True)
    (project / ".nwave" / "local-config.json").write_text(
        '{"enabled_for_repo": true}', encoding="utf-8"
    )
    (project / "src").mkdir()
    (project / "tests").mkdir()
    _git(project, "init")
    _git(project, "config", "user.email", "crafter@pi.test")
    _git(project, "config", "user.name", "pi crafter")
    return project


def make_unactivated_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / "src").mkdir(parents=True)
    return project


def _git(project: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=str(project), capture_output=True, text=True, check=True
    )


def deliver_dir(project: Path, kata_id: str) -> Path:
    return project / "docs" / "feature" / kata_id / "deliver"


def filesystem_snapshot(root: Path) -> dict[str, str]:
    """Port-exposed observable: relative path -> sha-ish content, for delta guard."""
    snap: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            snap[str(path.relative_to(root))] = path.read_text(
                encoding="utf-8", errors="replace"
            )
    return snap


# --------------------------------------------------------------------------- #
# NEW surface delegations (composition-root services)
# --------------------------------------------------------------------------- #


def bootstrap_session(project: Path, kata_id: str) -> dict:
    return bootstrap.bootstrap_kata_session(project_root=str(project), kata_id=kata_id)


def read_manifest(project: Path, kata_id: str) -> dict:
    return bootstrap.read_kata_manifest(project_root=str(project), kata_id=kata_id)


def record_phase(
    project: Path, kata_id: str, step_id: str, phase: TddPhase
) -> subprocess.CompletedProcess:
    return _run_des_cli(
        "des.cli.log_phase",
        [
            "--project-dir",
            str(deliver_dir(project, kata_id)),
            "--step-id",
            step_id,
            "--phase",
            phase.value,
            "--status",
            PhaseStatus.EXECUTED.value,
            "--data",
            "PASS",
        ],
        cwd=project,
    )


def record_complete_cycle(project: Path, kata_id: str, step_id: str) -> None:
    for phase in COMPLETE_CYCLE:
        record_phase(project, kata_id, step_id, phase)


def commit_with_trailers(project: Path, step_id: str, kata_id: str) -> None:
    _git(project, "add", "-A")
    _git(
        project,
        "commit",
        "-m",
        f"feat: kata step {step_id}\n\nStep-Id: {step_id}\nTask-Id: {kata_id}",
    )


def validate_at_commit_boundary(
    project: Path, kata_id: str, step_id: str, *, malformed: bool = False
) -> tuple[int, str]:
    transcript = project / ".nwave" / "des" / "kata-transcript.jsonl"
    transcript_context.write_synthesized_transcript(
        transcript_path=str(transcript),
        kata_id="" if malformed else kata_id,
        step_id=step_id,
        project_root=str(project),
    )
    payload = transcript_context.build_subagent_stop_payload(
        transcript_path=str(transcript), project_root=str(project)
    )
    return subagent_stop_roundtrip(payload, cwd=project)
