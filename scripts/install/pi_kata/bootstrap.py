"""Kata-session bootstrap + kata-manifest writer (ADR-PKT-001 KD1/KD2).

The pi ``registerCommand`` handler (TS, in the extension template) delegates the
deterministic bootstrap to this Python helper: it runs ``des-init-log`` for the
kata's deliver dir and writes the ``kata-manifest.json`` carrying ``(project-id,
current step-id, cwd)`` plus a deliver-session marker. Manifest writes are atomic
(temp-then-move) and re-read-asserted (ADR-PKT-001 H3).

REUSES UNCHANGED: ``des.cli.init_log`` (K2 -- zero ``src/des/**`` change). This
module only orchestrates the reused CLI + owns the manifest file (contract-shape
``bounded-change``).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.shared.install_paths import (
    resolve_des_lib_path_for_spawn,
    resolve_python_command_for_spawn,
)


FIRST_STEP_ID = "01-01"
MANIFEST_FILENAME = "kata-manifest.json"
SESSION_MARKER_FILENAME = ".kata-session"
LOCAL_CONFIG_RELPATH = Path(".nwave") / "local-config.json"
INIT_LOG_MODULE = "des.cli.init_log"
LOG_PHASE_MODULE = "des.cli.log_phase"

STATUS_BOOTSTRAPPED = "bootstrapped"
STATUS_REFUSED = "refused"

PHASE_STATUS_EXECUTED = "EXECUTED"


def bootstrap_kata_session(*, project_root: str, kata_id: str) -> dict:
    """Initialize a DES-tracked kata session and write the kata manifest.

    Returns ``{"status": "bootstrapped", "manifest": {...}}`` on success, or
    ``{"status": "refused", "reason": "..."}`` when the project is not activated
    for the kata harness (an observable refusal contract, never a raised
    exception).

    Idempotent: a re-bootstrap of an existing session returns the persisted
    manifest unchanged and performs no filesystem mutation (the reused
    ``des-init-log`` is not re-run, so its log is never clobbered).
    """
    root = Path(project_root)

    if not _is_activated(root):
        return {
            "status": STATUS_REFUSED,
            "reason": "project is not activated for the kata harness",
        }

    deliver = _deliver_dir(root, kata_id)
    manifest_file = deliver / MANIFEST_FILENAME

    if manifest_file.exists():
        return _read_manifest_file(manifest_file)

    deliver.mkdir(parents=True, exist_ok=True)
    _run_init_log(root=root, deliver=deliver, kata_id=kata_id)

    manifest = {
        "status": STATUS_BOOTSTRAPPED,
        "project_id": kata_id,
        "step_id": FIRST_STEP_ID,
        "cwd": str(root),
    }
    _atomic_write_json(manifest_file, manifest)
    _write_session_marker(deliver, kata_id)

    persisted = _read_manifest_file(manifest_file)
    if persisted != manifest:
        raise AssertionError(
            "kata manifest re-read mismatch after write (ADR-PKT-001 H3)"
        )
    return persisted


def read_kata_manifest(*, project_root: str, kata_id: str) -> dict:
    """Re-read and return the persisted kata manifest (ADR-PKT-001 H3)."""
    manifest_file = _deliver_dir(Path(project_root), kata_id) / MANIFEST_FILENAME
    return _read_manifest_file(manifest_file)


def advance_step_id(*, project_root: str, kata_id: str) -> str:
    """Increment the manifest's current step-id (``01-NN`` convention, KD2).

    Atomic write + re-read-assert. Returns the new step-id. A fresh per-step id
    is required every cycle (SPIKE constraint 3: never reuse a step-id) -- this
    is the canonical step-advance the kata harness invokes between cycles so the
    commit gate never re-validates an already-validated step-id and hits the
    engine's anti-infinite-loop second-attempt-allow.
    """
    manifest_file = _deliver_dir(Path(project_root), kata_id) / MANIFEST_FILENAME
    manifest = _read_manifest_file(manifest_file)

    next_step_id = _increment_step_id(manifest["step_id"])
    manifest["step_id"] = next_step_id
    _atomic_write_json(manifest_file, manifest)

    if _read_manifest_file(manifest_file)["step_id"] != next_step_id:
        raise AssertionError(
            "kata manifest re-read mismatch after step-id advance (H3)"
        )
    return next_step_id


def current_step_id(*, project_root: str, kata_id: str) -> str:
    """Return the manifest's current step-id (the id the next cycle records)."""
    manifest_file = _deliver_dir(Path(project_root), kata_id) / MANIFEST_FILENAME
    return _read_manifest_file(manifest_file)["step_id"]


def record_phase(
    *,
    project_root: str,
    kata_id: str,
    step_id: str,
    phase: str,
    status: str = PHASE_STATUS_EXECUTED,
    data: str = "PASS",
) -> None:
    """Append one TDD phase to ``execution-log.json`` via the reused des CLI.

    This is the canonical recording path the crafter skill prescribes: the
    install-resolved ``python -m des.cli.log_phase`` spawn (same interpreter +
    PYTHONPATH resolution as the bootstrap's ``des-init-log``). The kata harness
    drives recording through HERE, not through a test-rigged interpreter, so the
    live-wiring is exercised exactly as the model runs it. An empty
    ``execution-log.json`` after a cycle is the regression this path guards.
    """
    _run_log_phase(
        root=Path(project_root),
        deliver=_deliver_dir(Path(project_root), kata_id),
        step_id=step_id,
        phase=phase,
        status=status,
        data=data,
    )


# --------------------------------------------------------------------------- #
# Activation + path helpers
# --------------------------------------------------------------------------- #


def _is_activated(root: Path) -> bool:
    config_path = root / LOCAL_CONFIG_RELPATH
    if not config_path.is_file():
        return False
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return config.get("enabled_for_repo") is True


def _deliver_dir(root: Path, kata_id: str) -> Path:
    return root / "docs" / "feature" / kata_id / "deliver"


def _increment_step_id(step_id: str) -> str:
    slice_field, _, step_field = step_id.partition("-")
    return f"{slice_field}-{int(step_field) + 1:02d}"


# --------------------------------------------------------------------------- #
# Reused des-init-log spawn (D-PKT-3: resolved interpreter + PYTHONPATH)
# --------------------------------------------------------------------------- #


def _run_init_log(*, root: Path, deliver: Path, kata_id: str) -> None:
    _spawn_des_cli(
        root=root,
        module=INIT_LOG_MODULE,
        args=["--project-dir", str(deliver), "--feature-id", kata_id],
    )


def _run_log_phase(
    *,
    root: Path,
    deliver: Path,
    step_id: str,
    phase: str,
    status: str,
    data: str,
) -> None:
    _spawn_des_cli(
        root=root,
        module=LOG_PHASE_MODULE,
        args=[
            "--project-dir",
            str(deliver),
            "--step-id",
            step_id,
            "--phase",
            phase,
            "--status",
            status,
            "--data",
            data,
        ],
    )


def _spawn_des_cli(*, root: Path, module: str, args: list[str]) -> None:
    """Spawn a reused des CLI with the install-resolved interpreter + PYTHONPATH.

    The single skill-prescribed spawn shape shared by ``des-init-log`` and
    ``des-log-phase`` (D-PKT-3): resolved interpreter, ``des`` on PYTHONPATH,
    real subprocess, fail-loud (``check=True``).
    """
    subprocess.run(
        [_spawn_interpreter(), "-m", module, *args],
        env={
            "PYTHONPATH": _des_lib_pythonpath(),
            "PATH": os.environ.get("PATH", ""),
        },
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )


def _spawn_interpreter() -> str:
    """Install-time-resolved interpreter, falling back to the running one.

    ``resolve_python_command_for_spawn`` returns the bare ``python3`` when the
    process runs from a project-local ``.venv`` (dev/CI), to avoid leaking
    development paths into installed artifacts. In that dev context the current
    interpreter is the one that can import the DES lib, so use it directly.
    """
    resolved = resolve_python_command_for_spawn()
    if resolved == "python3":
        return sys.executable
    return resolved


def _des_lib_pythonpath() -> str:
    """Directory to put on ``PYTHONPATH`` so ``des`` imports in the spawn.

    Resolves the parent of the importable ``des`` package for the running
    interpreter (works in both the dev tree at ``src/`` and an installed lib
    dir), falling back to the install-time resolver.
    """
    spec = importlib.util.find_spec("des")
    if spec is not None and spec.submodule_search_locations:
        return str(Path(spec.submodule_search_locations[0]).parent)
    return resolve_des_lib_path_for_spawn()


# --------------------------------------------------------------------------- #
# Atomic manifest + session marker (ADR-PKT-001 H3: temp-then-move)
# --------------------------------------------------------------------------- #


def _atomic_write_json(target: Path, payload: dict) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=target.name, suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        Path(tmp_name).replace(target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _write_session_marker(deliver: Path, kata_id: str) -> None:
    marker = deliver / SESSION_MARKER_FILENAME
    _atomic_write_json(marker, {"project_id": kata_id, "active": True})


def _read_manifest_file(manifest_file: Path) -> dict:
    return json.loads(manifest_file.read_text(encoding="utf-8"))
