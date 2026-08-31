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
# Reused subagent-stop adapter round-trip (UNCHANGED engine)
# --------------------------------------------------------------------------- #


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


def record_phase(project: Path, kata_id: str, step_id: str, phase: TddPhase) -> None:
    """Record one phase through the SKILL-PRESCRIBED install-resolved spawn.

    Delegates to ``bootstrap.record_phase`` -- the canonical
    ``python -m des.cli.log_phase`` invocation the crafter skill instructs the
    model to run (install-resolved interpreter + PYTHONPATH), NOT a test-rigged
    interpreter. This is the live-wiring the empty-log regression slipped past:
    the old tests called the CLI with their own ``sys.executable`` + ``src`` on
    PYTHONPATH, so a broken skill-path spawn would still have gone green.
    """
    bootstrap.record_phase(
        project_root=str(project),
        kata_id=kata_id,
        step_id=step_id,
        phase=phase.value,
        status=PhaseStatus.EXECUTED.value,
        data="PASS",
    )


def record_complete_cycle(project: Path, kata_id: str, step_id: str) -> None:
    for phase in COMPLETE_CYCLE:
        record_phase(project, kata_id, step_id, phase)


def advance_to_next_step(project: Path, kata_id: str) -> str:
    """Advance the kata manifest to a fresh step-id (SPIKE constraint 3)."""
    return bootstrap.advance_step_id(project_root=str(project), kata_id=kata_id)


def current_step(project: Path, kata_id: str) -> str:
    return bootstrap.current_step_id(project_root=str(project), kata_id=kata_id)


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


def validate_at_commit_boundary_pre_commit(
    project: Path, kata_id: str, step_id: str
) -> tuple[int, str]:
    """Validate at the LIVE pre-commit order: the commit does NOT exist yet.

    The live gate fires on the bash ``git commit`` tool_call, BEFORE the commit
    is created. This helper -- unlike ``validate_at_commit_boundary`` -- does NOT
    commit first. It drives the phase-completeness-only mode: the synthesized
    transcript OMITS the ``DES-PROJECT-ROOT`` marker and the payload OMITS ``cwd``,
    so the engine resolves no validated marker and no cwd, skips GitCommitVerifier
    (``if context.cwd ...``), and gates on phase-completeness alone. The relative
    ``docs/feature/<kata>/deliver`` path still resolves against the subprocess cwd.
    """
    transcript = project / ".nwave" / "des" / "kata-transcript.jsonl"
    transcript_context.write_synthesized_transcript(
        transcript_path=str(transcript),
        kata_id=kata_id,
        step_id=step_id,
        project_root=str(project),
        phase_completeness_only=True,
    )
    payload = transcript_context.build_subagent_stop_payload(
        transcript_path=str(transcript),
        project_root=str(project),
        phase_completeness_only=True,
    )
    return subagent_stop_roundtrip(payload, cwd=project)


def record_phase_only(
    project: Path, kata_id: str, step_id: str, phase: TddPhase
) -> None:
    """Record a single phase (for the incomplete-cycle pre-commit regression)."""
    record_phase(project, kata_id, step_id, phase)


def audit_events(project: Path) -> list[dict]:
    """Read today's emitted DES audit events (port-exposed observable surface).

    R1 anchor: the phase-only validation must emit a genuine
    SUBAGENT_STOP_PASSED/FAILED -- NOT degrade to a non-DES passthrough (which
    emits no decision event). Reading the events lets the regression assert both
    the genuine verdict AND the absence of any commit-verification attempt.
    """
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = project / ".nwave" / "des" / "logs" / f"audit-{today}.log"
    if not log_file.exists():
        return []
    events: list[dict] = []
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events
