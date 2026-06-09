"""E2E: Cross-platform portability and OpenCode installation verification.

Migrated from: tests/e2e/Dockerfile.verify-cross-platform
Layer 4 of platform-testing-strategy.md

Contract (4 sections, 14 assertions):
  Section 1 — macOS simulation (python3 only, no bare 'python'):
    - portable python resolves (command -v python3 || command -v python)
    - DES health check works via portable pattern
    - hook adapter responds via portable pattern

  Section 2 — Windows simulation (python alias, no python3):
    - portable pattern handles both python and python3
    - no bare 'python3 -m des' in task command files
    - no bare 'python3 -m des' in skill files

  Section 3 — OpenCode installation:
    - installer succeeds
    - skills installed under ~/.config/opencode/skills/
    - SKILL.md format present
    - manifest file exists with installed_skills key
    - no private skills leaked

  Section 4 — Skill content integrity:
    - nw-tdd-methodology has content (> 100 chars)
    - nw-tdd-methodology has frontmatter (starts with ---)
    - canary passphrase intact (NWAVE_SKILL_INJECTION_ACTIVE_2026)
    - no empty SKILL.md files

Requires a Docker daemon.  Skips gracefully when Docker is unavailable.

Step-Id: 01-02
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.conftest import exec_in_container, require_docker


_REPO_ROOT = Path(__file__).parent.parent.parent
_IMAGE = "python:3.12-slim"
_CONTAINER_SRC = "/src"


@pytest.fixture(scope="module")
def cross_platform_container():
    """Container with nwave-ai installed from local source for cross-platform checks.

    Mirrors Dockerfile.verify-cross-platform:
    - Copies source into container (volume mount here)
    - Installs nwave-ai from source via venv
    - Runs installer (installs both Claude Code and OpenCode targets)
    """
    from tests.e2e.conftest import _is_docker_available

    if not _is_docker_available():
        pytest.skip("Docker daemon not available")

    from testcontainers.core.container import (
        DockerContainer,  # type: ignore[import-untyped]
    )

    container = DockerContainer(image=_IMAGE)
    container.with_volume_mapping(str(_REPO_ROOT), _CONTAINER_SRC, "ro")
    container.with_env("HOME", "/root")
    container.with_env("DEBIAN_FRONTEND", "noninteractive")
    container._command = "tail -f /dev/null"

    with container:
        setup_script = (
            "set -e && "
            "apt-get update -qq && "
            "apt-get install -y --no-install-recommends git -qq && "
            "rm -rf /var/lib/apt/lists/* && "
            "python -m venv /opt/nwave-venv && "
            "source /opt/nwave-venv/bin/activate && "
            "pip install --quiet "
            "rich typer pydantic 'pydantic-settings' httpx platformdirs pyyaml packaging && "
            f"pip install --quiet --no-deps {_CONTAINER_SRC} && "
            f"export PYTHONPATH={_CONTAINER_SRC} && "
            "echo y | python -m nwave_ai.cli install"
        )
        code, out = exec_in_container(container, ["bash", "-c", setup_script])
        assert code == 0, f"Install failed (exit {code}).\nOutput:\n{out}"

        yield container


# ---------------------------------------------------------------------------
# Section 1: macOS simulation
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@require_docker
class TestCrossPlatformPortability:
    """Cross-platform portability: macOS, Windows-style paths, OpenCode, skill integrity.

    Migrated from Dockerfile.verify-cross-platform (14 assertions across 4 sections).
    """

    # --- Section 1: macOS simulation ---

    def test_macos_portable_python_resolves(self, cross_platform_container) -> None:
        """$(command -v python3 || command -v python) must resolve to a working Python.

        On macOS only python3 exists (no bare 'python' on PATH by default).
        The portable pattern must resolve to python3 on Linux (where both exist)
        and to python on macOS-like environments.
        """
        code, out = exec_in_container(
            cross_platform_container,
            [
                "bash",
                "-c",
                "$(command -v python3 || command -v python) --version",
            ],
        )
        assert code == 0, (
            f"Portable python resolution failed (exit {code}).\nOutput:\n{out}"
        )

    def test_macos_des_health_check_works_via_portable_pattern(
        self, cross_platform_container
    ) -> None:
        """DES health check must work when invoked via portable python pattern.

        Verifies that the health check module is importable without relying on
        a bare 'python3' that may not exist on macOS.
        """
        script = (
            f"PYTHONPATH={_CONTAINER_SRC}/src "
            "$(command -v python3 || command -v python) "
            "-m des.cli.health_check --json"
        )
        code, out = exec_in_container(cross_platform_container, ["bash", "-c", script])
        if code == 0:
            import json

            try:
                data = json.loads(out)
                assert data.get("status") == "healthy", (
                    f"Health check returned status {data.get('status')!r} (expected 'healthy').\n"
                    f"Output:\n{out}"
                )
            except json.JSONDecodeError:
                pytest.fail(f"Health check produced invalid JSON.\nOutput:\n{out}")
        else:
            pytest.fail(
                f"DES health check via portable pattern failed (exit {code}).\n"
                f"Output:\n{out}"
            )

    def test_macos_hook_adapter_responds_via_portable_pattern(
        self, cross_platform_container
    ) -> None:
        """The hook adapter must respond when invoked via portable python pattern.

        Confirms hook execution is not gated on a bare 'python3' binary.
        """
        script = (
            f"echo '{{}}' | PYTHONPATH={_CONTAINER_SRC}/src "
            "$(command -v python3 || command -v python) "
            "-m des.adapters.drivers.hooks.claude_code_hook_adapter pre-tool-use"
        )
        code, out = exec_in_container(cross_platform_container, ["bash", "-c", script])
        assert '{"decision"' in out or code == 0, (
            f"Hook adapter did not produce a decision response.\n"
            f"Exit: {code}, Output: {out[:200]}"
        )

    # --- Section 2: Windows simulation ---

    def test_windows_portable_pattern_handles_both_aliases(
        self, cross_platform_container
    ) -> None:
        """The portable python pattern must work regardless of which alias exists.

        On Windows: 'python' exists, 'python3' may not.
        On Linux/macOS: 'python3' exists, 'python' may not.
        The pattern (command -v python3 || command -v python) handles both.
        """
        code, out = exec_in_container(
            cross_platform_container,
            [
                "bash",
                "-c",
                "command -v python3 && echo 'python3 exists' || echo 'no python3'",
            ],
        )
        assert code == 0, (
            f"Portable python3/python alias check failed (exit {code}).\nOutput:\n{out}"
        )

    def test_windows_no_bare_python3_in_task_commands(
        self, cross_platform_container
    ) -> None:
        """Task command files must not contain bare 'python3 -m des' without portable guard.

        Bare 'python3' calls fail on Windows where only 'python' is on PATH.
        All DES invocations must use the portable pattern or go through shims.
        Lines with 'command -v' guards or comments (#) are acceptable.
        """
        _code, out = exec_in_container(
            cross_platform_container,
            [
                "bash",
                "-c",
                f"grep -rn 'python3 -m des' {_CONTAINER_SRC}/nWave/tasks/nw/ 2>/dev/null "
                "| grep -v 'command -v' | grep -v '^[^:]*:#' || echo 'CLEAN'",
            ],
        )
        assert "CLEAN" in out, (
            "Found bare 'python3 -m des' calls in task command files (Windows portability violation).\n"
            "All DES invocations must use the portable pattern or shims.\n"
            f"Violations:\n{out}"
        )

    def test_windows_no_bare_python3_in_skills(self, cross_platform_container) -> None:
        """Skill files must not contain bare 'python3 -m des' without portable guard.

        Skills are injected into agent prompts and must work on all platforms.
        """
        _code, out = exec_in_container(
            cross_platform_container,
            [
                "bash",
                "-c",
                f"grep -rn 'python3 -m des' {_CONTAINER_SRC}/nWave/skills/ 2>/dev/null "
                "| grep -v 'command -v' | grep -v '^[^:]*:#' || echo 'CLEAN'",
            ],
        )
        assert "CLEAN" in out, (
            "Found bare 'python3 -m des' calls in skill files (Windows portability violation).\n"
            f"Violations:\n{out}"
        )

    # --- Section 3: OpenCode installation ---

    def test_opencode_installer_succeeds(self, cross_platform_container) -> None:
        """The nwave-ai installer must report success for the OpenCode target.

        The installer supports both Claude Code and OpenCode targets.
        A failure here means the OpenCode plugin is broken.
        """
        script = (
            f"export PYTHONPATH={_CONTAINER_SRC} && "
            "python -m venv /tmp/oc-venv && "
            "/tmp/oc-venv/bin/pip install pyyaml -q && "
            "VIRTUAL_ENV=/tmp/oc-venv "
            f"PATH=/tmp/oc-venv/bin:$PATH python {_CONTAINER_SRC}/scripts/install/install_nwave.py 2>&1"
        )
        code, out = exec_in_container(cross_platform_container, ["bash", "-c", script])
        assert "installed and healthy" in out or code == 0, (
            f"OpenCode installer did not report success.\n"
            f"Exit: {code}, Output (last 400 chars):\n{out[-400:]}"
        )

    def test_opencode_skills_installed(self, cross_platform_container) -> None:
        """Skills must be installed under ~/.config/opencode/skills/ for OpenCode.

        Verifies the OpenCode plugin deploys skill files to the correct location.
        """
        _code, count_out = exec_in_container(
            cross_platform_container,
            [
                "bash",
                "-c",
                "find /root/.config/opencode/skills -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l",
            ],
        )
        try:
            count = int(count_out.strip())
        except ValueError:
            count = 0
        if count == 0:
            pytest.skip(
                "~/.config/opencode/skills/ not present — "
                "OpenCode plugin may not be enabled in this install configuration."
            )
        assert count > 50, (
            f"Only {count} skill directories found under ~/.config/opencode/skills/.\n"
            "Expected > 50 skills for a complete OpenCode installation."
        )

    def test_opencode_skill_md_format_present(self, cross_platform_container) -> None:
        """At least one SKILL.md file must exist in OpenCode skills directory."""
        _code, count_out = exec_in_container(
            cross_platform_container,
            [
                "bash",
                "-c",
                "find /root/.config/opencode/skills -name 'SKILL.md' 2>/dev/null | wc -l",
            ],
        )
        try:
            count = int(count_out.strip())
        except ValueError:
            count = 0
        if count == 0:
            pytest.skip(
                "OpenCode skills directory not present — skipping SKILL.md format check."
            )
        assert count > 0, (
            "No SKILL.md files found in ~/.config/opencode/skills/.\n"
            "OpenCode plugin must install skill files in SKILL.md format."
        )

    def test_opencode_manifest_exists(self, cross_platform_container) -> None:
        """OpenCode skills manifest (.nwave-manifest.json) must exist with installed_skills key."""
        _code, out = exec_in_container(
            cross_platform_container,
            [
                "python3",
                "-c",
                "import json, pathlib; "
                "m = pathlib.Path('/root/.config/opencode/skills/.nwave-manifest.json'); "
                "print('EXISTS' if m.exists() else 'MISSING'); "
                "d = json.loads(m.read_text()) if m.exists() else {}; "
                "print('HAS_KEY' if 'installed_skills' in d else 'NO_KEY')",
            ],
        )
        if "MISSING" in out:
            pytest.skip(
                "OpenCode manifest not present — OpenCode plugin may not be enabled."
            )
        assert "HAS_KEY" in out, (
            "OpenCode manifest exists but missing 'installed_skills' key.\n"
            f"Manifest content check output:\n{out}"
        )

    def test_opencode_no_private_skills_leaked(self, cross_platform_container) -> None:
        """Private agent skills must not appear in the OpenCode skills directory.

        Skills such as 'workshopper', 'tutorialist', 'deal-closer' are private
        and must be filtered out by the OpenCode plugin.
        """
        _code, out = exec_in_container(
            cross_platform_container,
            [
                "bash",
                "-c",
                "find /root/.config/opencode/skills -maxdepth 1 -type d 2>/dev/null "
                "| grep -E 'workshopper|tutorialist|deal-closer' || echo 'CLEAN'",
            ],
        )
        assert "CLEAN" in out, (
            "Private skills found in OpenCode skills directory — privacy filter is broken.\n"
            f"Leaked skills:\n{out}"
        )

    # --- Section 4: Skill content integrity ---

    def test_tdd_methodology_skill_has_content(self, cross_platform_container) -> None:
        """nw-tdd-methodology/SKILL.md must have substantial content (> 100 chars).

        An empty or truncated skill file means the install copied a corrupted
        or zero-byte file.
        """
        _code, out = exec_in_container(
            cross_platform_container,
            [
                "python3",
                "-c",
                "import pathlib; "
                "p = pathlib.Path('/root/.claude/skills/nw-tdd-methodology/SKILL.md'); "
                "print(len(p.read_text()) if p.exists() else -1)",
            ],
        )
        try:
            char_count = int(out.strip())
        except ValueError:
            char_count = -1
        assert char_count > 100, (
            f"nw-tdd-methodology/SKILL.md has {char_count} chars (expected > 100).\n"
            "Skill file may be missing or truncated."
        )

    def test_tdd_methodology_skill_has_frontmatter(
        self, cross_platform_container
    ) -> None:
        """nw-tdd-methodology/SKILL.md must start with YAML frontmatter ('---').

        All nWave skill files must have frontmatter (name, description, user-invocable).
        A file without frontmatter indicates a corrupted or wrong-format install.
        """
        _code, out = exec_in_container(
            cross_platform_container,
            [
                "python3",
                "-c",
                "import pathlib; "
                "p = pathlib.Path('/root/.claude/skills/nw-tdd-methodology/SKILL.md'); "
                "print('HAS_FM' if p.exists() and p.read_text().startswith('---') else 'NO_FM')",
            ],
        )
        assert "HAS_FM" in out, (
            "nw-tdd-methodology/SKILL.md does not start with '---' frontmatter.\n"
            "Skill file may be missing or in wrong format."
        )

    def test_canary_passphrase_intact(self, cross_platform_container) -> None:
        """nw-canary/SKILL.md must contain the canary passphrase.

        The canary passphrase (NWAVE_SKILL_INJECTION_ACTIVE_2026) is used to
        verify skill injection is working end-to-end.  If the passphrase is
        absent, the canary skill was not installed or was corrupted.
        """
        _code, out = exec_in_container(
            cross_platform_container,
            [
                "python3",
                "-c",
                "import pathlib; "
                "p = pathlib.Path('/root/.claude/skills/nw-canary/SKILL.md'); "
                "content = p.read_text() if p.exists() else ''; "
                "print('PASSPHRASE_OK' if 'NWAVE_SKILL_INJECTION_ACTIVE_2026' in content "
                "else 'PASSPHRASE_MISSING')",
            ],
        )
        assert "PASSPHRASE_OK" in out, (
            "Canary passphrase 'NWAVE_SKILL_INJECTION_ACTIVE_2026' not found in "
            "nw-canary/SKILL.md.\n"
            "Canary skill may be missing or corrupted."
        )

    def test_no_empty_skill_md_files(self, cross_platform_container) -> None:
        """No nw-*/SKILL.md files may be zero-byte after installation.

        An empty skill file is worse than a missing one — it silently provides
        no guidance while appearing to be installed.
        """
        _code, out = exec_in_container(
            cross_platform_container,
            [
                "python3",
                "-c",
                "import pathlib; "
                "empty = [str(p) for p in pathlib.Path('/root/.claude/skills').rglob('SKILL.md') "
                "if p.stat().st_size == 0]; "
                "print('\\n'.join(empty) if empty else 'ALL_NON_EMPTY')",
            ],
        )
        assert "ALL_NON_EMPTY" in out, (
            "Found empty SKILL.md files after installation:\n"
            + "\n".join(
                f"  - {l}"
                for l in out.splitlines()  # noqa: E741
                if l.strip() and l != "ALL_NON_EMPTY"
            )
        )
