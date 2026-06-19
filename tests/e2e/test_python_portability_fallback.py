"""E2E: DES CLI portable-Python resolution works across environments.

Migrated from: tests/e2e/Dockerfile.verify-python-portability
Layer 4 of platform-testing-strategy.md

Validates the portable invocation pattern used in nWave templates:

    $(command -v python3 || command -v python) -m des.cli.<module>

Simulates three operating-system setups inside a single Linux container
(the only controllable environment) and a fourth static-content scan:

  1. macOS-like      — only ``python3`` on PATH
  2. Windows-like    — only ``python`` on PATH
  3. Linux-standard  — both available
  4. Template scan   — no bare ``python/python3 -m des.cli`` in nWave/tasks/nw/

Assertions count: 4 (one per scenario).  In-container manipulation of
/usr/local/bin symlinks + the portable fallback chain is checked for
each scenario against a stub ``des.cli.log_phase`` module.

Requires a Docker daemon.  Skips gracefully when Docker is unavailable.

Step-Id: 01-03
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.conftest import exec_in_container, require_docker


_REPO_ROOT = Path(__file__).parent.parent.parent
_IMAGE = "python:3.12-slim"
_DES_CLI_STUB = "/workspace/lib"


@pytest.fixture(scope="module")
def portability_container():
    """Container with a stub des.cli module and the 3 nWave templates."""
    from tests.e2e.conftest import _is_docker_available

    if not _is_docker_available():
        pytest.skip("Docker daemon not available")

    from testcontainers.core.container import (
        DockerContainer,  # type: ignore[import-untyped]
    )

    container = DockerContainer(image=_IMAGE)
    container.with_volume_mapping(str(_REPO_ROOT), "/src", "ro")
    container.with_env("DEBIAN_FRONTEND", "noninteractive")
    container._command = "tail -f /dev/null"

    with container:
        setup = (
            "set -e && "
            "pip install --no-cache-dir pyyaml --quiet && "
            "mkdir -p /workspace/templates && "
            "cp /src/nWave/tasks/nw/execute.md /workspace/templates/execute.md && "
            "cp /src/nWave/tasks/nw/deliver.md /workspace/templates/deliver.md && "
            "cp /src/nWave/tasks/nw/roadmap.md /workspace/templates/roadmap.md && "
            "mkdir -p /workspace/lib/des/cli && "
            'echo \'"""DES package stub."""\' > /workspace/lib/des/__init__.py && '
            'echo \'"""DES cli stub."""\' > /workspace/lib/des/cli/__init__.py && '
            "echo 'import sys; print(f\"log_phase OK ({sys.version.split()[0]})\")' > /workspace/lib/des/cli/log_phase.py"
        )
        code, out = exec_in_container(container, ["bash", "-c", setup])
        assert code == 0, f"Stub setup failed (exit {code}).\n{out[-500:]}"
        yield container


def _resolve_and_invoke_script(scenario_setup: str, scenario_teardown: str) -> str:
    """Build a one-shot bash snippet that sets up $PATH, resolves, invokes, and cleans up.

    Emits ``RESOLVED=<path>`` and ``INVOKE_EXIT=<code>`` for assertion.
    """
    return (
        "set +e && "
        f"{scenario_setup} && "
        "hash -r && "
        "resolved=$(command -v python3 || command -v python || echo NONE) && "
        'echo "RESOLVED=$resolved" && '
        'if [ "$resolved" = "NONE" ]; then echo "INVOKE_EXIT=127"; else '
        f'  PYTHONPATH={_DES_CLI_STUB} "$resolved" -m des.cli.log_phase; '
        '  echo "INVOKE_EXIT=$?"; '
        "fi && "
        f"{scenario_teardown}"
    )


@pytest.mark.e2e
@require_docker
class TestPythonPortabilityFallback:
    """Portable Python resolution: macOS/Windows-like/Linux + template scan.

    Migrated from Dockerfile.verify-python-portability (4 scenarios).
    """

    def test_macos_homebrew_python3_only(self, portability_container) -> None:
        """macOS Homebrew: only ``python3`` exists; ``command -v python3`` wins."""
        script = _resolve_and_invoke_script(
            # Setup: remove any python symlink (python3 alone remains)
            scenario_setup=(
                "[ -e /usr/local/bin/python ] && rm -f /usr/local/bin/python; "
                "[ -e /usr/bin/python ] && rm -f /usr/bin/python; true"
            ),
            # Teardown: none (no-op)
            scenario_teardown="true",
        )
        _code, out = exec_in_container(portability_container, ["bash", "-c", script])
        assert "RESOLVED=" in out, f"Resolver did not run.\n{out}"
        resolved = [
            line.split("=", 1)[1]
            for line in out.splitlines()
            if line.startswith("RESOLVED=")
        ][-1]
        invoke_exit = [
            line.split("=", 1)[1]
            for line in out.splitlines()
            if line.startswith("INVOKE_EXIT=")
        ][-1]
        assert resolved.endswith("python3") or "python3" in resolved, (
            f"Expected python3 resolution on macOS-like env, got: {resolved}"
        )
        assert invoke_exit == "0", (
            f"des.cli.log_phase invocation failed (exit {invoke_exit}).\n{out[-300:]}"
        )

    def test_windows_like_python_only(self, portability_container) -> None:
        """Windows-like: only ``python`` exists; ``command -v python`` is the fallback."""
        # Setup copies python3 -> python, then hides python3 so only 'python' resolves.
        script = (
            "set +e && "
            "P3=$(command -v python3 2>/dev/null) && "
            'if [ -n "$P3" ] && [ -f "$P3" ]; then '
            '  cp "$P3" /usr/local/bin/python && '
            '  mv "$P3" "${P3}.hidden"; '
            "fi && "
            "hash -r && "
            "resolved=$(command -v python3 || command -v python || echo NONE) && "
            'echo "RESOLVED=$resolved" && '
            f'PYTHONPATH={_DES_CLI_STUB} "$resolved" -m des.cli.log_phase; '
            'echo "INVOKE_EXIT=$?" && '
            # Teardown: restore python3
            'if [ -n "$P3" ] && [ -f "${P3}.hidden" ]; then '
            '  mv "${P3}.hidden" "$P3"; '
            "fi; "
            "hash -r; true"
        )
        _code, out = exec_in_container(portability_container, ["bash", "-c", script])
        assert "RESOLVED=" in out, f"Resolver did not run.\n{out}"
        resolved = [
            line.split("=", 1)[1]
            for line in out.splitlines()
            if line.startswith("RESOLVED=")
        ][-1]
        invoke_exit = [
            line.split("=", 1)[1]
            for line in out.splitlines()
            if line.startswith("INVOKE_EXIT=")
        ][-1]
        # On Windows-like env, python3 hidden -> resolver falls back to 'python'.
        assert resolved.endswith("/python") or resolved == "/usr/local/bin/python", (
            f"Expected python resolution on Windows-like env, got: {resolved}"
        )
        assert invoke_exit == "0", (
            f"des.cli.log_phase invocation failed (exit {invoke_exit}).\n{out[-300:]}"
        )

    def test_linux_standard_both_available(self, portability_container) -> None:
        """Linux: python3 AND python available; command -v python3 wins first."""
        # Ensure both exist: python is a symlink to python3.
        script = (
            "set +e && "
            "P3=$(command -v python3 2>/dev/null) && "
            'ln -sf "$P3" /usr/local/bin/python && '
            "hash -r && "
            "resolved=$(command -v python3 || command -v python || echo NONE) && "
            'echo "RESOLVED=$resolved" && '
            f'PYTHONPATH={_DES_CLI_STUB} "$resolved" -m des.cli.log_phase; '
            'echo "INVOKE_EXIT=$?"'
        )
        _code, out = exec_in_container(portability_container, ["bash", "-c", script])
        assert "RESOLVED=" in out, f"Resolver did not run.\n{out}"
        resolved = [
            line.split("=", 1)[1]
            for line in out.splitlines()
            if line.startswith("RESOLVED=")
        ][-1]
        invoke_exit = [
            line.split("=", 1)[1]
            for line in out.splitlines()
            if line.startswith("INVOKE_EXIT=")
        ][-1]
        assert "python3" in resolved, (
            f"Expected python3 to win precedence when both available, got: {resolved}"
        )
        assert invoke_exit == "0", (
            f"des.cli.log_phase invocation failed (exit {invoke_exit}).\n{out[-300:]}"
        )

    def test_templates_use_portable_pattern(self, portability_container) -> None:
        """No template issues bare ``python/python3 -m des.cli`` invocation.

        The regex matches a python/python3 -m des.cli reference that is NOT
        preceded by ``$(command -v `` or ``|| command -v `` — i.e. not inside
        the portable fallback wrapper.
        """
        _code, out = exec_in_container(
            portability_container,
            [
                "bash",
                "-c",
                (
                    "violations=0 && "
                    "for tmpl in /workspace/templates/*.md; do "
                    "  if grep -P '(?<!\\$\\(command -v )(?<!\\|\\| command -v )"
                    '\\bpython[3]?\\s+-m\\s+des\\.cli\\b\' "$tmpl" >/dev/null 2>&1; then '
                    '    echo "BAD=$tmpl"; '
                    "    violations=$((violations+1)); "
                    "  fi; "
                    "done; "
                    'echo "VIOLATIONS=$violations"'
                ),
            ],
        )
        m = [
            line.split("=", 1)[1]
            for line in out.splitlines()
            if line.startswith("VIOLATIONS=")
        ]
        assert m and m[-1] == "0", (
            f"Templates contain bare python/python3 des.cli references.\n{out}"
        )
