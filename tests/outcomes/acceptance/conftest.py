"""
Shared fixtures for outcomes acceptance tests.

Strategy C — Real local: real subprocess invocations of `nwave-ai outcomes`,
real YAML filesystem under tmp_path. NO mocks at the acceptance boundary.

Mirrors tests/feature_delta/acceptance/conftest.py. The driving-adapter
mandate (Mandate 5) requires the walking-skeleton scenario to invoke the
user-facing entry point via subprocess.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_bdd import given


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
    """Resolve the nwave-ai entry point as an argv prefix."""
    return [sys.executable, "-m", "nwave_ai.cli"]


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """Sandbox directory for a single scenario."""
    sb = tmp_path / "sandbox"
    (sb / "home").mkdir(parents=True)
    (sb / "repo").mkdir(parents=True)
    return sb / "repo"


def registry_path(sandbox: Path) -> Path:
    """Canonical registry path under the per-scenario sandbox."""
    return sandbox / "docs" / "product" / "outcomes" / "registry.yaml"


@pytest.fixture
def state() -> dict:
    """Per-scenario mutable state holder shared across step files."""
    return {}


@given("a clean docs/product/outcomes/registry.yaml under tmp_path")
def _clean_registry(sandbox: Path) -> None:
    """Initialise an empty registry skeleton in the sandbox."""
    path = registry_path(sandbox)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        'schema_version: "0.1"\noutcomes: []\n',
        encoding="utf-8",
    )


def _isolated_env(sandbox: Path) -> dict[str, str]:
    """Minimal environment for vendor-neutrality."""
    project_root = Path(__file__).parents[3]
    env = {
        "HOME": str(sandbox.parent / "home"),
        "PATH": str(Path(sys.executable).parent),
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CEILING_DIRECTORIES": str(project_root.parent),
    }
    if os.environ.get("COVERAGE_PROCESS_START"):
        env["COVERAGE_PROCESS_START"] = os.environ["COVERAGE_PROCESS_START"]
        env["PYTHONPATH"] = os.environ.get("PYTHONPATH", os.getcwd())
        if os.environ.get("COVERAGE_FILE"):
            env["COVERAGE_FILE"] = os.environ["COVERAGE_FILE"]
    no_color = os.environ.get("NO_COLOR")
    if no_color is not None:
        env["NO_COLOR"] = no_color
    return env


@pytest.fixture
def run_cli(nwave_ai_binary: list[str], sandbox: Path):
    """Subprocess runner for nwave-ai outcomes invocations."""

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
