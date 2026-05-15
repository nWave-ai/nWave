"""Shared fixtures for E2E testcontainers tests.

Provides:
- ``require_docker``: pytest mark that skips when Docker is unavailable
- ``_exec``: helper to run a command in a DockerContainer and return (exit_code, output)
- ``_exec_ok``: run a command and assert exit 0
- ``pypi_shape_wheel``: session-scoped local-built PyPI-shape wheel (shared by
  test_pypi_shape_install_chain.py + test_wheel_privacy_contract.py)

All E2E test modules import from here to avoid duplicating the docker-availability
guard and the exec helper in every file.

Note: test_fresh_install.py predates this module and defines its own local versions
of ``_is_docker_available``, ``requires_docker``, ``_exec``, and ``_exec_ok``.
Those local definitions remain unchanged for backwards-compatibility.  New E2E
test modules should import the shared fixtures from this file.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Docker availability — evaluated once per session
# ---------------------------------------------------------------------------


def _is_docker_available() -> bool:
    """Return True if the Docker daemon is reachable."""
    try:
        import docker  # type: ignore[import-untyped]

        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


_DOCKER_AVAILABLE: bool = _is_docker_available()


#: Pytest mark: skip if Docker daemon is not reachable.
require_docker = pytest.mark.skipif(
    not _DOCKER_AVAILABLE,
    reason="Docker daemon not available — skipping E2E container test",
)


# ---------------------------------------------------------------------------
# Container exec helpers
# ---------------------------------------------------------------------------


def exec_in_container(
    container,
    command: str | list[str],
    environment: dict[str, str] | None = None,
) -> tuple[int, str]:
    """Run *command* inside *container* and return ``(exit_code, output)``.

    When *environment* is provided the call falls through to the docker-py
    ``exec_run`` API (the testcontainers ``exec()`` shim does not accept an
    environment dict).  Otherwise the lighter ``container.exec()`` wrapper is
    used.

    Args:
        container: A running ``testcontainers.core.container.DockerContainer``.
        command: Command string or list of strings to execute.
        environment: Optional mapping of environment variables for the command.

    Returns:
        ``(exit_code, decoded_output)`` tuple.
    """
    if environment:
        raw = container.get_wrapped_container().exec_run(
            cmd=command,
            environment=environment,
        )
        exit_code: int = raw.exit_code
        output_bytes = raw.output
    else:
        result = container.exec(command)
        exit_code = result.exit_code
        output_bytes = result.output

    output: str = output_bytes.decode("utf-8", errors="replace") if output_bytes else ""
    return exit_code, output


def exec_ok(container, command: str | list[str]) -> str:
    """Run *command* and assert exit 0; return decoded output.

    Fails the test immediately if the command exits non-zero.
    """
    exit_code, output = exec_in_container(container, command)
    assert exit_code == 0, f"Command {command!r} exited {exit_code}.\nOutput:\n{output}"
    return output


# ---------------------------------------------------------------------------
# OpenCode container fixture — shared between opencode-full-install and
# opencode-subagent-hooks tests (session scope to amortize npm/opencode setup)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def opencode_container():
    """Session-scoped container with OpenCode CLI + nWave installed.

    Mirrors Dockerfile.env-opencode build sequence:
      1. Install nodejs 22 + opencode-ai npm package
      2. Configure OpenCode (~/.config/opencode/opencode.json)
      3. Run scripts/install/install_nwave.py from volume-mounted source

    The container is reused across all tests that only need the
    installer side-effects (skills, agents, commands, manifests).
    Tests that also need OPENAI_API_KEY runtime probing build their
    own image via subprocess since that path requires a different
    pipx + overlay layout.
    """

    from tests.e2e.conftest import _is_docker_available

    if not _is_docker_available():
        pytest.skip("Docker daemon not available")

    from testcontainers.core.container import (
        DockerContainer,  # type: ignore[import-untyped]
    )

    repo_root = Path(__file__).parent.parent.parent
    container = DockerContainer(image="python:3.12-slim")
    container.with_volume_mapping(str(repo_root), "/src", "ro")
    container.with_env("HOME", "/home/tester")
    container.with_env("DEBIAN_FRONTEND", "noninteractive")
    container._command = "tail -f /dev/null"

    with container:
        setup_script = (
            "set -e && "
            "apt-get update -qq && "
            "apt-get install -y --no-install-recommends git curl -qq && "
            "curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1 && "
            "apt-get install -y --no-install-recommends nodejs -qq && "
            "rm -rf /var/lib/apt/lists/* && "
            "npm install -g opencode-ai --silent 2>&1 | tail -5 && "
            "useradd -m tester && "
            "mkdir -p /home/tester/.config/opencode && "
            'echo \'{"model": "openai/gpt-4o-mini"}\' > /home/tester/.config/opencode/opencode.json && '
            "chown -R tester:tester /home/tester"
        )
        code, out = exec_in_container(container, ["bash", "-c", setup_script])
        assert code == 0, (
            f"OpenCode container setup failed (exit {code}).\n{out[-800:]}"
        )

        # Copy repo to writable tester location (install needs to write relative-to-source)
        copy_script = (
            "set -e && "
            "cp -r /src /home/tester/nwave-dev && "
            "chown -R tester:tester /home/tester/nwave-dev"
        )
        code, out = exec_in_container(container, ["bash", "-c", copy_script])
        assert code == 0, f"Repo copy failed (exit {code}).\n{out[-500:]}"

        # Install into a venv owned by tester, then run installer as tester
        install_script = (
            "set -e && "
            "python -m venv /tmp/venv && "
            "/tmp/venv/bin/pip install --quiet pyyaml rich typer pydantic pydantic-settings httpx platformdirs packaging && "
            "chown -R tester:tester /tmp/venv && "
            "su tester -c 'cd /home/tester/nwave-dev && "
            "VIRTUAL_ENV=/tmp/venv PATH=/tmp/venv/bin:$PATH "
            "python scripts/install/install_nwave.py' 2>&1"
        )
        code, out = exec_in_container(container, ["bash", "-c", install_script])
        # Install may exit non-zero if optional plugins fail; outcome is asserted
        # per-test against core markers (mirrors Dockerfile `|| true` pattern).
        container._install_stdout = out  # type: ignore[attr-defined]

        yield container


# ---------------------------------------------------------------------------
# Codex CLI container fixture — exercises the auto-detect path triggered by
# the presence of ~/.codex/ alone (no codex binary required per
# scripts/install/context_detector.py:_detect_codex).
#
# Lighter than opencode_container: skips the npm + nodejs + binary install
# step because the installer's Codex detection accepts the directory-only
# signal.  Tests verify the same contract surface (skills land at
# ~/.agents/skills/, agents at ~/.codex/agents/ as TOML, hooks.json wired,
# manifests present, Claude install parity preserved).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def codex_container():
    """Session-scoped container with ~/.codex/ directory + nWave installed.

    Mirrors codex auto-detect behaviour: Codex CLI is presumed available
    whenever ~/.codex/ exists, so the fixture just creates the directory
    and runs the installer.

    Reused across all tests that only need the installer side-effects
    (skills, agents, hooks, manifests).  No actual codex runtime is
    started — that would belong to a Codex subagent-hooks suite (deferred).
    """
    if not _is_docker_available():
        pytest.skip("Docker daemon not available")

    from testcontainers.core.container import (
        DockerContainer,  # type: ignore[import-untyped]
    )

    repo_root = Path(__file__).parent.parent.parent
    container = DockerContainer(image="python:3.12-slim")
    container.with_volume_mapping(str(repo_root), "/src", "ro")
    container.with_env("HOME", "/home/tester")
    container.with_env("DEBIAN_FRONTEND", "noninteractive")
    container._command = "tail -f /dev/null"

    with container:
        setup_script = (
            "set -e && "
            "apt-get update -qq && "
            "apt-get install -y --no-install-recommends git -qq && "
            "rm -rf /var/lib/apt/lists/* && "
            "useradd -m tester && "
            "mkdir -p /home/tester/.codex && "
            "chown -R tester:tester /home/tester"
        )
        code, out = exec_in_container(container, ["bash", "-c", setup_script])
        assert code == 0, f"Codex container setup failed (exit {code}).\n{out[-800:]}"

        # Copy repo to writable tester location (install needs to write relative-to-source)
        copy_script = (
            "set -e && "
            "cp -r /src /home/tester/nwave-dev && "
            "chown -R tester:tester /home/tester/nwave-dev"
        )
        code, out = exec_in_container(container, ["bash", "-c", copy_script])
        assert code == 0, f"Repo copy failed (exit {code}).\n{out[-500:]}"

        install_script = (
            "set -e && "
            "python -m venv /tmp/venv && "
            "/tmp/venv/bin/pip install --quiet pyyaml rich typer pydantic "
            "pydantic-settings httpx platformdirs packaging && "
            "chown -R tester:tester /tmp/venv && "
            "su tester -c 'cd /home/tester/nwave-dev && "
            "VIRTUAL_ENV=/tmp/venv PATH=/tmp/venv/bin:$PATH "
            "python scripts/install/install_nwave.py' 2>&1"
        )
        code, out = exec_in_container(container, ["bash", "-c", install_script])
        # Install may exit non-zero if optional plugins fail; outcome asserted
        # per-test against core markers (mirrors the Dockerfile `|| true` pattern).
        container._install_stdout = out  # type: ignore[attr-defined]

        yield container


# ---------------------------------------------------------------------------
# PyPI-shape wheel build — shared by test_pypi_shape_install_chain.py and
# test_wheel_privacy_contract.py
#
# Moved here from test_pypi_shape_install_chain.py to break the
# wheel_privacy_container catch-22: previously that fixture installed nwave-ai
# from live PyPI via `pipx install --pip-args="--pre"`, which meant a leaked
# wheel on PyPI could not be fixed (pre-push e2e installed the leaked wheel
# and failed on it).  Both consumer tests now share this local-built wheel.
# ---------------------------------------------------------------------------

import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402


_REPO_ROOT_FOR_WHEEL: Path = Path(__file__).resolve().parent.parent.parent

# Dirs/files copied into the per-session sandbox. Anything not in this list
# is excluded from the build root: keeps the build deterministic and avoids
# pulling in dev artefacts (tests/, docs/, .git/, .venv/).
_SANDBOX_INCLUDES: tuple[str, ...] = (
    "nWave",
    "scripts",
    "src",
    "nwave_ai",
    "schemas",
    "pyproject.toml",
    "README.md",
    "LICENSE",
)


def _wheel_build_run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 300,
) -> tuple[int, str]:
    """Run a subprocess and return (exit_code, combined_stdout_stderr)."""
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace")


def _copy_repo_subset(src_root: Path, dst_root: Path) -> None:
    """Copy the strict subset of repo dirs needed for build into dst_root."""
    dst_root.mkdir(parents=True, exist_ok=True)
    for name in _SANDBOX_INCLUDES:
        src = src_root / name
        if not src.exists():
            continue
        dst = dst_root / name
        if src.is_dir():
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)


def _build_pypi_shape_wheel(sandbox: Path) -> Path:
    """Build a PyPI-shape wheel inside *sandbox* and return its path.

    Mirrors the .github/workflows/release-prod.yml publish-to-pypi job:
      1. python scripts/build_dist.py        (produces dist/lib/python/des)
      2. cp -r dist/lib ./lib                (so force-include can resolve)
      3. python scripts/release/patch_pyproject.py   (PyPI wheel shape)
      4. python -m build --wheel             (opaque distributable)
    """
    # 1. Build the DES module into sandbox/dist/lib
    code, out = _wheel_build_run(
        [sys.executable, "scripts/build_dist.py"],
        cwd=sandbox,
    )
    assert code == 0, f"build_dist.py failed (exit {code}):\n{out}"

    # 2. Move dist/lib -> lib (force-include needs lib/python/des at root)
    dist_lib = sandbox / "dist" / "lib"
    assert dist_lib.is_dir(), f"build_dist.py did not produce dist/lib/. Output:\n{out}"
    shutil.copytree(dist_lib, sandbox / "lib")
    # Clean dist so python -m build does not see stale artefacts
    shutil.rmtree(sandbox / "dist", ignore_errors=True)

    # 3. Patch pyproject.toml in place (in the sandbox copy ONLY).
    patched_path = sandbox / "pyproject.toml"
    code, out = _wheel_build_run(
        [
            sys.executable,
            "scripts/release/patch_pyproject.py",
            "--input",
            str(patched_path),
            "--output",
            str(patched_path),
            "--target-name",
            "nwave-ai",
            "--target-version",
            "0.0.0.dev0",
        ],
        cwd=sandbox,
    )
    assert code == 0, f"patch_pyproject.py failed (exit {code}):\n{out}"

    # 4. Build the wheel
    out_dir = sandbox / "wheelhouse"
    code, out = _wheel_build_run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out_dir)],
        cwd=sandbox,
        timeout=600,
    )
    assert code == 0, f"python -m build --wheel failed (exit {code}):\n{out}"

    wheels = list(out_dir.glob("nwave_ai-*.whl"))
    assert len(wheels) == 1, (
        f"Expected exactly one nwave_ai wheel in {out_dir}, found: {wheels}\n"
        f"Build output:\n{out}"
    )
    return wheels[0]


@pytest.fixture(scope="session")
def pypi_shape_wheel(tmp_path_factory) -> Path:
    """Build a PyPI-shape wheel once per session and yield its path.

    Session-scoped: the build is ~60s, must amortize across all consumer tests
    (test_pypi_shape_install_chain.py + test_wheel_privacy_contract.py).
    """
    sandbox = tmp_path_factory.mktemp("nwave_pypi_sandbox")
    _copy_repo_subset(_REPO_ROOT_FOR_WHEEL, sandbox)
    wheel = _build_pypi_shape_wheel(sandbox)
    return wheel
