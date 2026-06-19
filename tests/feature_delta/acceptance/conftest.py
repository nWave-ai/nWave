"""
Shared fixtures for feature_delta acceptance tests.

Strategy C — Real local: real subprocess invocations of the nwave-ai
binary, real filesystem under tmp_path, real schema/verb-list files
loaded via importlib.resources or repo-relative paths. NO mocks at the
acceptance boundary.

The driving-adapter mandate (Mandate 5) requires every walking-skeleton
scenario to invoke the user-facing entry point via subprocess. These
fixtures provide the sandbox + invocation helpers shared by
validation/, extraction/, migration/, and cross_cutting/ step files.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# CLI invocation contract (Mandate 5 — Driving Adapter Verification)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CliResult:
    """Snapshot of a subprocess invocation of nwave-ai."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


@pytest.fixture
def nwave_ai_binary() -> list[str]:
    """
    Resolve the nwave-ai entry point as an argv prefix.

    During DELIVER, this resolves to the installed `nwave-ai` console
    script. During DISTILL RED-ready scaffolding, this points to the
    Python module so subprocess invocation can fail with the scaffold
    AssertionError surfacing through the CLI dispatcher.
    """
    return [sys.executable, "-m", "nwave_ai.cli"]


@pytest.fixture
def run_cli(nwave_ai_binary: list[str], sandbox: Path):
    """
    Subprocess runner for nwave-ai invocations.

    Runs the CLI in the sandbox directory with isolated HOME and a
    minimal PATH that contains only the python interpreter directory.
    Captures stdout/stderr/exit code and elapsed time.
    """
    import time

    def _run(*argv: str, env: dict[str, str] | None = None) -> CliResult:
        start = time.monotonic()
        completed = subprocess.run(
            [*nwave_ai_binary, *argv],
            cwd=sandbox,
            env=env if env is not None else _isolated_env(sandbox),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        return CliResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=duration_ms,
        )

    return _run


def _isolated_env(sandbox: Path) -> dict[str, str]:
    """Minimal environment for vendor-neutrality (no Git, no pre-commit)."""
    import pathlib

    project_root = pathlib.Path(__file__).parents[3]
    env = {
        "HOME": str(sandbox / "home"),
        "PATH": str(Path(sys.executable).parent),
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        # Prevent subprocess git from walking up to the host repo.
        "GIT_CEILING_DIRECTORIES": str(project_root.parent),
    }
    if os.environ.get("COVERAGE_PROCESS_START"):
        env["COVERAGE_PROCESS_START"] = os.environ["COVERAGE_PROCESS_START"]
        env["PYTHONPATH"] = os.environ.get("PYTHONPATH", os.getcwd())
        if os.environ.get("COVERAGE_FILE"):
            env["COVERAGE_FILE"] = os.environ["COVERAGE_FILE"]
    # Propagate NO_COLOR (https://no-color.org/) when set in the caller's environment.
    no_color = os.environ.get("NO_COLOR")
    if no_color is not None:
        env["NO_COLOR"] = no_color
    return env


# ---------------------------------------------------------------------------
# Sandbox — clean working directory (Mandate 6 — real I/O)
# ---------------------------------------------------------------------------


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """
    Sandbox directory for a single scenario.

    Layout:
      tmp_path/
        sandbox/
          home/                # isolated $HOME
          repo/                # CWD for the invocation
            docs/feature/.../
    """
    sb = tmp_path / "sandbox"
    (sb / "home").mkdir(parents=True)
    (sb / "repo").mkdir(parents=True)
    return sb / "repo"


# ---------------------------------------------------------------------------
# Sandbox snapshot helpers (G4 — DD-A4 zero-side-effects)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SandboxSnapshot:
    """Filesystem snapshot for diff-based G4 assertions."""

    files: dict[str, str]  # relative path -> sha256 of content


@pytest.fixture
def take_snapshot():
    """Snapshot HOME + CWD recursive at depth <= 4."""
    import hashlib

    def _snap(root: Path) -> SandboxSnapshot:
        files: dict[str, str] = {}
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if len(rel.parts) > 6:
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            files[str(rel)] = digest
        return SandboxSnapshot(files=files)

    return _snap


# ---------------------------------------------------------------------------
# Fixture corpus loader
# ---------------------------------------------------------------------------


@pytest.fixture
def fixture_dir() -> Path:
    """Path to the fixtures directory inside this test package."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def write_feature_delta(sandbox: Path):
    """Write a feature-delta.md file under the sandbox repo."""

    def _write(relpath: str, content: str) -> Path:
        path = sandbox / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    return _write


# ---------------------------------------------------------------------------
# Token-billing exemplar (US-05 walking skeleton)
# ---------------------------------------------------------------------------


@pytest.fixture
def token_billing_exemplar(write_feature_delta) -> Path:
    """
    The token-billing failure exemplar applied retroactively to v1.0
    schema. DISCUSS commits to "real WSGI handler"; DESIGN weakens to
    "framework-agnostic dispatcher" with no DDD ratification.
    """
    content = (
        "# token-billing\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | real WSGI handler bound to /api/usage | n/a | "
        "establishes protocol surface |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| DISCUSS#row1 | framework-agnostic dispatcher | "
        "(none) | tradeoffs apply across the stack |\n"
    )
    return write_feature_delta("runs/nwave-attempt/feature-delta.md", content)
