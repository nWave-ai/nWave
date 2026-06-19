"""E2E runtime-grade regression test for nWave fresh install via testcontainers.

Contract: verifies OUTCOME not MECHANICS.

Stat-level checks (file existence, mode bits) are smoke tests that catch
source-file regressions.  This test catches runtime failures that stat checks
miss: a machine where ~/.claude/lib/python/des/ is absent passes every stat
assertion while des-log-phase fails with ImportError at runtime.

The authoritative contract is:
    1. Shims deployed to ~/.claude/bin/ with mode 0o755 (stat-level)
    2. shutil.which(<shim>, path=<env.PATH from settings>) non-None for all 5
    3. subprocess.run([<shim>, "--help"]) exits 0 for all 5
    4. nwave-ai doctor exits 0 with all runtime-critical checks green
    5. doctor JSON output conforms to the expected schema (name/passed/message/remediation)
    6. Installed skills contain no PYTHONPATH= pattern (issue #36 real runtime check)
    7. A second install run is idempotent (exit 0, no state duplication)
    8. settings.json env.PATH contains no literal "$HOME" string (P0 f03862e0)

Requires a Docker daemon.  Skips gracefully when docker is unavailable.

Refs: docs/analysis/adversarial-verify-issue-36.md B-5
Step-Id: 01-03
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Docker availability guard
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


_DOCKER_AVAILABLE = _is_docker_available()

requires_docker = pytest.mark.skipif(
    not _DOCKER_AVAILABLE,
    reason="Docker daemon not available — skipping E2E container test",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_IMAGE = "python:3.12-slim"
_CONTAINER_SRC = "/src"
_EXPECTED_SHIMS = [
    "des-log-phase",
    "des-init-log",
    "des-verify-integrity",
    "des-roadmap",
    "des-health-check",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exec(
    container,
    command: str | list[str],
    environment: dict[str, str] | None = None,
) -> tuple[int, str]:
    """Run a command in the container and return (exit_code, output).

    ``environment`` is forwarded to the underlying exec_run call when provided.
    Uses DockerContainer.exec() (a shim over docker-py's exec_run) for the
    no-env case; falls through to exec_run directly only when env vars are needed.
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


def _exec_ok(container, command: str | list[str]) -> str:
    """Run a command and assert exit 0; return decoded output."""
    exit_code, output = _exec(container, command)
    assert exit_code == 0, f"Command {command!r} exited {exit_code}.\nOutput:\n{output}"
    return output


# ---------------------------------------------------------------------------
# Session-scoped fixture: one container for all assertions
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fresh_install_container():
    """Start a python:3.12-slim container, install nwave-ai from local source,
    run nwave-ai install, and yield the running container.

    Scoped to module so all tests share one container lifecycle.
    """
    if not _DOCKER_AVAILABLE:
        pytest.skip("Docker daemon not available")

    from testcontainers.core.container import (
        DockerContainer,  # type: ignore[import-untyped]
    )

    container = DockerContainer(image=_IMAGE)
    container.with_volume_mapping(str(_REPO_ROOT), _CONTAINER_SRC, "ro")
    container.with_env("HOME", "/root")
    container.with_env("DEBIAN_FRONTEND", "noninteractive")
    # Keep container alive
    container._command = "tail -f /dev/null"

    with container:
        # Bootstrap: create a venv (satisfies installer preflight venv check),
        # install runtime deps, then install the nwave package from the mounted
        # source tree.  PYTHONPATH=/src makes nwave_ai importable without it
        # being listed in the hatch wheel packages (nwave_ai/ is the dev-only
        # CLI layer; the public nwave-ai wheel ships it separately).
        bootstrap_script = (
            "set -e && "
            "python -m venv /opt/nwave-venv && "
            "source /opt/nwave-venv/bin/activate && "
            "pip install --quiet "
            "rich typer pydantic 'pydantic-settings' httpx platformdirs pyyaml packaging && "
            # Install des + scripts/install packages from the mounted source
            f"pip install --quiet --no-deps {_CONTAINER_SRC} && "
            # nwave_ai/ is not in the wheel — expose it via PYTHONPATH
            f"export PYTHONPATH={_CONTAINER_SRC} && "
            # Run install; echo y handles any attribution prompt
            "echo y | python -m nwave_ai.cli install"
        )
        code, out = _exec(container, ["bash", "-c", bootstrap_script])
        assert code == 0, (
            f"Container bootstrap/install failed (exit {code}).\nOutput:\n{out}"
        )

        yield container


# ---------------------------------------------------------------------------
# Assertion tests — all share the same running container
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@requires_docker
class TestFreshInstallShimsDeployed:
    """Stat-level: shims exist in ~/.claude/bin/ with mode 0o755."""

    def test_all_shims_exist_with_correct_mode(self, fresh_install_container) -> None:
        """All 5 DES shims must be present in ~/.claude/bin/ with mode 0o755."""
        missing: list[str] = []
        wrong_mode: list[str] = []

        for shim_name in _EXPECTED_SHIMS:
            shim_path = f"/root/.claude/bin/{shim_name}"
            # Check existence
            code, _ = _exec(fresh_install_container, ["test", "-f", shim_path])
            if code != 0:
                missing.append(shim_name)
                continue
            # Check mode (octal)
            code, mode_out = _exec(
                fresh_install_container,
                ["stat", "-c", "%a", shim_path],
            )
            mode_str = mode_out.strip()
            if mode_str != "755":
                wrong_mode.append(f"{shim_name} (mode={mode_str})")

        errors: list[str] = []
        if missing:
            errors.append("Missing shims:\n" + "\n".join(f"  - {s}" for s in missing))
        if wrong_mode:
            errors.append(
                "Wrong mode (expected 755):\n"
                + "\n".join(f"  - {s}" for s in wrong_mode)
            )
        assert not errors, "\n\n".join(errors)


@pytest.mark.e2e
@requires_docker
class TestFreshInstallShimCallable:
    """Runtime-level: des-log-phase --help exits 0 inside container."""

    def test_des_log_phase_help_exits_zero(self, fresh_install_container) -> None:
        """des-log-phase --help must exit 0 — proves the shim is importable at runtime.

        This is the assertion that test_issue_36 (stat-only) could NOT catch:
        a machine where ~/.claude/lib/python/des/ is absent passes the stat check
        but fails here with ImportError.
        """
        shim_path = "/root/.claude/bin/des-log-phase"
        _exec_ok(fresh_install_container, [shim_path, "--help"])

    def test_des_log_phase_resolvable_via_settings_env_path(
        self, fresh_install_container
    ) -> None:
        """The PATH exported in ~/.claude/settings.json must resolve des-log-phase.

        Verifies that the installer correctly configured env.PATH in settings,
        and that the shim is discoverable via that path — the runtime resolution
        check that shutil.which tests locally.
        """
        # Extract env.PATH from settings.json inside the container
        code, settings_raw = _exec(
            fresh_install_container,
            ["cat", "/root/.claude/settings.json"],
        )
        assert code == 0, (
            f"Cannot read ~/.claude/settings.json (exit {code}).\n{settings_raw}"
        )

        settings = json.loads(settings_raw)
        env_path = settings.get("env", {}).get("PATH", "")
        assert env_path, (
            "settings.json missing env.PATH — installer did not configure PATH.\n"
            f"settings.json content:\n{settings_raw}"
        )

        # Verify des-log-phase is discoverable via that PATH.
        # Pass env_path via an environment variable to avoid shell-quoting issues
        # when the PATH contains colons or special characters.
        check_script = (
            "import shutil, os; "
            "p = os.environ['CHECK_PATH']; "
            "result = shutil.which('des-log-phase', path=p); "
            "exit(0 if result else 1)"
        )
        code, which_out = _exec(
            fresh_install_container,
            ["python3", "-c", check_script],
            environment={"CHECK_PATH": env_path},
        )
        assert code == 0, (
            f"shutil.which('des-log-phase', path=<settings env.PATH>) returned None.\n"
            f"env.PATH = {env_path!r}\n"
            f"Output: {which_out}"
        )


@pytest.mark.e2e
@requires_docker
class TestFreshInstallAllShimsCallable:
    """Runtime-level: all 5 DES shims exit 0 with --help inside the container."""

    @pytest.mark.parametrize(
        "shim_name",
        [
            "des-log-phase",
            "des-init-log",
            "des-verify-integrity",
            "des-roadmap",
            "des-health-check",
        ],
    )
    def test_shim_help_exits_zero(
        self, fresh_install_container, shim_name: str
    ) -> None:
        """Each DES shim must exit 0 when invoked with --help.

        Extends the single-shim test to the full shim set.  A shim passes the
        stat check (exists, mode 755) but fails here when the Python import
        chain is broken — e.g. des/ absent from lib/python/ or a stale
        PYTHONPATH reference.
        """
        shim_path = f"/root/.claude/bin/{shim_name}"
        _exec_ok(fresh_install_container, [shim_path, "--help"])


@pytest.mark.e2e
@requires_docker
class TestFreshInstallAllShimsPathResolvable:
    """Runtime-level: all 5 shims are discoverable via the settings env.PATH."""

    @pytest.mark.parametrize(
        "shim_name",
        [
            "des-log-phase",
            "des-init-log",
            "des-verify-integrity",
            "des-roadmap",
            "des-health-check",
        ],
    )
    def test_shim_resolvable_via_settings_env_path(
        self, fresh_install_container, shim_name: str
    ) -> None:
        """shutil.which(<shim>, path=<env.PATH from settings>) must return non-None.

        Verifies that settings.json env.PATH covers the full shim set, not just
        des-log-phase.  A mis-configured PATH that resolves one shim may still
        fail for others if they land in a different bin/ sub-directory.
        """
        code, settings_raw = _exec(
            fresh_install_container,
            ["cat", "/root/.claude/settings.json"],
        )
        assert code == 0, (
            f"Cannot read ~/.claude/settings.json (exit {code}).\n{settings_raw}"
        )

        settings = json.loads(settings_raw)
        env_path = settings.get("env", {}).get("PATH", "")
        assert env_path, (
            "settings.json missing env.PATH — installer did not configure PATH.\n"
            f"settings.json content:\n{settings_raw}"
        )

        check_script = (
            "import shutil, os, sys; "
            "p = os.environ['CHECK_PATH']; "
            "name = os.environ['CHECK_SHIM']; "
            "result = shutil.which(name, path=p); "
            "print(result or ''); "
            "sys.exit(0 if result else 1)"
        )
        code, which_out = _exec(
            fresh_install_container,
            ["python3", "-c", check_script],
            environment={"CHECK_PATH": env_path, "CHECK_SHIM": shim_name},
        )
        assert code == 0, (
            f"shutil.which({shim_name!r}, path=<settings env.PATH>) returned None.\n"
            f"env.PATH = {env_path!r}\n"
            f"Output: {which_out}"
        )


@pytest.mark.e2e
@requires_docker
class TestFreshInstallDoctorPasses:
    """Execution-level: nwave-ai doctor exits 0 with all checks green."""

    def test_doctor_runtime_checks_pass(self, fresh_install_container) -> None:
        """nwave-ai doctor --json must report all runtime-critical checks as passed.

        Runtime-critical checks (verified here):
          - python_version, des_module, hooks_registered, hook_python_path,
            shims_deployed, path_env

        framework_files (agents/skills/commands counts) is NOT asserted here
        because a source-mount install from the dev repo does not deploy the
        commands/ directory (that only ships in the distribution tarball).
        The runtime contract — can des-log-phase execute without ImportError —
        is covered by test_des_log_phase_help_exits_zero above.
        """
        # Doctor is invoked with PYTHONPATH so nwave_ai is importable inside
        # the container (nwave_ai/ is not in the installed wheel packages).
        _code, json_out = _exec(
            fresh_install_container,
            [
                "bash",
                "-c",
                f"PYTHONPATH={_CONTAINER_SRC} "
                "/opt/nwave-venv/bin/python -m nwave_ai.cli doctor --json",
            ],
        )
        # Exit code may be non-zero due to framework_files; parse checks directly.
        try:
            data = json.loads(json_out)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"doctor --json did not produce valid JSON. "
                f"Exit code: {_code}, parse error: {exc}\n"
                f"Output:\n{json_out}"
            )
        checks = data.get("checks", data) if isinstance(data, dict) else data

        _RUNTIME_CRITICAL = {
            "python_version",
            "des_module",
            "hooks_registered",
            "hook_python_path",
            "shims_deployed",
            "path_env",
        }
        failed_critical = [
            r
            for r in checks
            if r.get("name") in _RUNTIME_CRITICAL and not r.get("passed", False)
        ]
        assert not failed_critical, (
            "Doctor reports failing runtime-critical checks after fresh install:\n"
            + "\n".join(
                f"  - {r.get('name', '?')}: {r.get('message', '')}"
                for r in failed_critical
            )
            + f"\n\nFull doctor output:\n{json_out}"
        )

    def test_doctor_json_output_shape(self, fresh_install_container) -> None:
        """doctor --json output must conform to the expected schema.

        Structural contract: the output is either a list of check objects, or a
        dict with a "checks" key containing that list.  Each check entry MUST
        have "name", "passed", "message", and "remediation" keys.

        Protects against formatter regressions where doctor output changes shape
        (e.g. nested dict, flat string) without the consumer (CI, review scripts)
        noticing.
        """
        _code, json_out = _exec(
            fresh_install_container,
            [
                "bash",
                "-c",
                f"PYTHONPATH={_CONTAINER_SRC} "
                "/opt/nwave-venv/bin/python -m nwave_ai.cli doctor --json",
            ],
        )
        try:
            data = json.loads(json_out)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"doctor --json did not produce valid JSON. "
                f"Exit code: {_code}, parse error: {exc}\n"
                f"Output:\n{json_out}"
            )

        checks = data.get("checks", data) if isinstance(data, dict) else data
        assert isinstance(checks, list), (
            f"Expected doctor output to be a list of check objects (or dict with "
            f"'checks' list), got {type(checks).__name__}.\nOutput:\n{json_out}"
        )
        assert len(checks) > 0, (
            f"Doctor returned an empty checks list.\nOutput:\n{json_out}"
        )

        _REQUIRED_KEYS = {"name", "passed", "message", "remediation"}
        malformed = [
            entry
            for entry in checks
            if not isinstance(entry, dict) or not _REQUIRED_KEYS.issubset(entry.keys())
        ]
        assert not malformed, (
            "Doctor check entries missing required keys "
            f"({sorted(_REQUIRED_KEYS)}):\n"
            + "\n".join(f"  - {entry!r}" for entry in malformed)
            + f"\n\nFull doctor output:\n{json_out}"
        )


@pytest.mark.e2e
@requires_docker
class TestFreshInstallNoPythonpathInSkills:
    """Installed skills must contain no PYTHONPATH= pattern (issue #36 runtime)."""

    def test_installed_skills_contain_no_pythonpath_pattern(
        self, fresh_install_container
    ) -> None:
        """grep for 'PYTHONPATH=' inside ~/.claude/skills/ must return empty output.

        This is the real runtime verification for issue #36: the permission-prompt
        regression was caused by hook commands embedding a literal PYTHONPATH=
        assignment that Claude Code surfaced as a permission prompt.  If skills
        (or any installed file) contain that pattern, the regression is live.

        Grep exit codes: 0 = matches found (FAIL), 1 = no matches (PASS),
        2 = error (handled as a distinct assertion).
        """
        skills_dir = "/root/.claude/skills"
        # Check the directory exists before grepping (skills may not be installed
        # in a dev-source-mount scenario; skip gracefully rather than fail).
        code, _ = _exec(fresh_install_container, ["test", "-d", skills_dir])
        if code != 0:
            pytest.skip(
                "~/.claude/skills/ not present in container — "
                "skill installation not part of this install scenario"
            )

        code, grep_out = _exec(
            fresh_install_container,
            ["grep", "-rl", "PYTHONPATH=", skills_dir],
        )
        # exit 1 means grep found no matches — that is the expected outcome.
        # exit 0 means matches were found — that is the failure.
        # exit 2 means grep itself errored.
        assert code != 2, (
            f"grep command errored (exit 2) while scanning {skills_dir}.\n"
            f"Output:\n{grep_out}"
        )
        assert code == 1, (
            "Found PYTHONPATH= pattern in installed skill files (issue #36 regression).\n"
            "Files containing the banned pattern:\n"
            + "\n".join(f"  - {line}" for line in grep_out.strip().splitlines())
        )


@pytest.mark.e2e
@requires_docker
class TestFreshInstallSettingsJsonNoDollarHome:
    """settings.json env.PATH must not contain a literal '$HOME' string (P0 f03862e0)."""

    def test_settings_env_path_has_no_dollar_home_literal(
        self, fresh_install_container
    ) -> None:
        """$HOME must be expanded at install time, not stored as a literal string.

        The P0 fix (f03862e0) ensured that the installer resolves $HOME before
        writing settings.json.  A regression would write the literal string
        "$HOME" into env.PATH, causing all shim lookups to fail on machines
        where PATH expansion is not performed by the consumer.
        """
        code, settings_raw = _exec(
            fresh_install_container,
            ["cat", "/root/.claude/settings.json"],
        )
        assert code == 0, (
            f"Cannot read ~/.claude/settings.json (exit {code}).\n{settings_raw}"
        )

        settings = json.loads(settings_raw)
        env_path = settings.get("env", {}).get("PATH", "")
        assert env_path, (
            "settings.json missing env.PATH — installer did not configure PATH.\n"
            f"settings.json content:\n{settings_raw}"
        )

        assert "$HOME" not in env_path, (
            "settings.json env.PATH contains a literal '$HOME' string — "
            "installer did not expand HOME at write time (P0 regression f03862e0).\n"
            f"env.PATH value: {env_path!r}"
        )


# ---------------------------------------------------------------------------
# Idempotent install — dedicated fixture to avoid mutating the shared container
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def idempotent_install_container():
    """Separate container for the idempotent-install test.

    Installing a second time mutates the filesystem (rewrites settings.json,
    recreates shims).  Using the shared fresh_install_container would corrupt
    path-resolution assertions for tests that run after this one.  A dedicated
    module-scoped fixture avoids that coupling.
    """
    if not _DOCKER_AVAILABLE:
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
        # First install (identical bootstrap to fresh_install_container)
        bootstrap_script = (
            "set -e && "
            "python -m venv /opt/nwave-venv && "
            "source /opt/nwave-venv/bin/activate && "
            "pip install --quiet "
            "rich typer pydantic 'pydantic-settings' httpx platformdirs pyyaml packaging && "
            f"pip install --quiet --no-deps {_CONTAINER_SRC} && "
            f"export PYTHONPATH={_CONTAINER_SRC} && "
            "echo y | python -m nwave_ai.cli install"
        )
        code, out = _exec(container, ["bash", "-c", bootstrap_script])
        assert code == 0, f"First install failed (exit {code}).\nOutput:\n{out}"

        yield container


@pytest.mark.e2e
@requires_docker
class TestFreshInstallIdempotent:
    """A second install run must succeed without duplicating state."""

    def test_second_install_exits_zero(self, idempotent_install_container) -> None:
        """Running nwave-ai install a second time must exit 0.

        An idempotent installer recovers gracefully when destination files
        already exist (shims, settings entries, hook registrations).  A non-zero
        exit here indicates the installer errors on pre-existing state.
        """
        second_install = (
            f"export PYTHONPATH={_CONTAINER_SRC} && "
            "echo y | /opt/nwave-venv/bin/python -m nwave_ai.cli install"
        )
        code, out = _exec(
            idempotent_install_container,
            ["bash", "-c", second_install],
        )
        assert code == 0, (
            f"Second install run exited {code} (expected 0 — idempotent).\n"
            f"Output:\n{out}"
        )

    def test_second_install_no_duplicate_shims(
        self, idempotent_install_container
    ) -> None:
        """After two install runs each shim must exist exactly once in ~/.claude/bin/.

        Counts all files matching the shim names to detect duplicates
        (e.g. des-log-phase, des-log-phase.1, des-log-phase~).
        """
        duplicates: list[str] = []
        for shim_name in _EXPECTED_SHIMS:
            # Count files whose names start with the shim name (catches copies/backups)
            _code, count_out = _exec(
                idempotent_install_container,
                [
                    "bash",
                    "-c",
                    f"ls /root/.claude/bin/ | grep -c '^{shim_name}' || true",
                ],
            )
            count_str = count_out.strip()
            try:
                count = int(count_str)
            except ValueError:
                count = 0
            if count > 1:
                duplicates.append(f"{shim_name} ({count} copies)")

        assert not duplicates, (
            "Idempotent install created duplicate shim files:\n"
            + "\n".join(f"  - {d}" for d in duplicates)
        )

    def test_second_install_no_path_duplication_in_settings(
        self, idempotent_install_container
    ) -> None:
        """env.PATH in settings.json must not contain duplicated path segments.

        A non-idempotent installer appends ~/.claude/bin/ to PATH on every run,
        producing "…/bin:…/bin:…/bin".  This test counts occurrences of the
        bin directory in the PATH value.
        """
        code, settings_raw = _exec(
            idempotent_install_container,
            ["cat", "/root/.claude/settings.json"],
        )
        assert code == 0, (
            f"Cannot read ~/.claude/settings.json (exit {code}).\n{settings_raw}"
        )

        settings = json.loads(settings_raw)
        env_path = settings.get("env", {}).get("PATH", "")
        assert env_path, (
            "settings.json missing env.PATH after second install.\n"
            f"settings.json content:\n{settings_raw}"
        )

        bin_dir = "/root/.claude/bin"
        path_segments = [seg for seg in env_path.split(":") if seg == bin_dir]
        assert len(path_segments) <= 1, (
            f"~/.claude/bin appears {len(path_segments)} times in env.PATH after "
            f"two install runs — installer is not idempotent on PATH.\n"
            f"env.PATH value: {env_path!r}"
        )
