"""Acceptance tests for the curl-able bootstrap installer scripts/install/install.sh.

The script is POSIX sh and dependency-free: the only external commands it runs
are the installer tools (uv / pipx / nwave-ai). That lets these tests run it
fully hermetically — every test builds a throwaway ``bin/`` directory of stub
executables, points ``PATH`` at it *and nothing else*, and asserts on:

  * the process exit code,
  * stdout / stderr text, and
  * a call log the stubs append to (which tool was actually invoked).

Because PATH contains only the fake bin, the host's real uv/pipx never leak in,
so the auto-detection branches are deterministic.

Interactive prompt branches (accept / decline) need a TTY on stdin, so those two
cases drive the script through a pseudo-terminal.
"""

from __future__ import annotations

import os
import pty
import select
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "scripts" / "install" / "install.sh"

# Stub that records "name arg1 arg2 ..." to $NWAVE_TEST_LOG and exits 0.
_STUB_TEMPLATE = '#!/bin/sh\nprintf "{name} %s\\n" "$*" >> "$NWAVE_TEST_LOG"\nexit 0\n'


@pytest.fixture
def env(tmp_path):
    """A hermetic environment: empty fake bin on PATH, isolated call log.

    Returns an object exposing ``stub(name)`` to add a fake executable and
    ``calls()`` to read back the recorded invocations.
    """

    class Env:
        def __init__(self) -> None:
            self.bin = tmp_path / "bin"
            self.bin.mkdir()
            self.log = tmp_path / "calls.log"
            self.log.write_text("")

        def stub(self, name: str) -> None:
            path = self.bin / name
            path.write_text(_STUB_TEMPLATE.format(name=name))
            path.chmod(0o755)

        def stub_failing_doctor(self, exit_code: int = 7) -> None:
            """nwave-ai stub modelling a CLI whose `doctor` finds a real problem.

            `doctor` exists (so the `doctor --help` capability probe exits 0),
            but the actual health run exits non-zero. Lets a test assert the
            script propagates that exit code rather than swallowing it.
            """
            path = self.bin / "nwave-ai"
            path.write_text(
                "#!/bin/sh\n"
                'printf "nwave-ai %s\\n" "$*" >> "$NWAVE_TEST_LOG"\n'
                'if [ "$1" = "doctor" ]; then\n'
                '    case "${2:-}" in\n'
                "        --help|-h) exit 0 ;;\n"
                f"        *) exit {exit_code} ;;\n"
                "    esac\n"
                "fi\n"
                "exit 0\n"
            )
            path.chmod(0o755)

        def stub_old_cli_without_doctor(self) -> None:
            """nwave-ai stub modelling a build that predates `doctor` (#74).

            Every `doctor` invocation — including the `doctor --help` capability
            probe — fails the way the real old CLI does: it prints
            ``Unknown command: doctor`` and exits non-zero. ``install`` succeeds.
            """
            path = self.bin / "nwave-ai"
            path.write_text(
                "#!/bin/sh\n"
                'printf "nwave-ai %s\\n" "$*" >> "$NWAVE_TEST_LOG"\n'
                'if [ "$1" = "doctor" ]; then\n'
                '    echo "Unknown command: doctor" >&2\n'
                "    exit 1\n"
                "fi\n"
                "exit 0\n"
            )
            path.chmod(0o755)

        def env_vars(self, **extra: str) -> dict[str, str]:
            base = {
                "PATH": str(self.bin),
                "NWAVE_TEST_LOG": str(self.log),
                # Force deterministic, color-free output for stdout assertions.
                "NO_COLOR": "1",
            }
            base.update(extra)
            return base

        def calls(self) -> list[str]:
            return [
                line.strip()
                for line in self.log.read_text().splitlines()
                if line.strip()
            ]

    return Env()


def run(env, *args: str, env_vars: dict[str, str] | None = None):
    """Run install.sh non-interactively (stdin closed) and capture output."""
    return subprocess.run(
        ["/bin/sh", str(SCRIPT), *args],
        env=env.env_vars(**(env_vars or {})),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )


def run_pty(env, *args: str, answer: str = "", env_vars: dict[str, str] | None = None):
    """Run install.sh attached to a pseudo-terminal so ``[ -t 0 ]`` is true.

    ``answer`` is written to the terminal to satisfy the script's read prompt.
    Returns ``(returncode, combined_output)``.
    """
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        ["/bin/sh", str(SCRIPT), *args],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=env.env_vars(**(env_vars or {})),
        close_fds=True,
    )
    os.close(slave)
    if answer:
        os.write(master, answer.encode())

    chunks: list[bytes] = []
    while True:
        ready, _, _ = select.select([master], [], [], 10)
        if ready:
            try:
                data = os.read(master, 1024)
            except OSError:  # EIO once the slave side is fully closed
                break
            if not data:
                break
            chunks.append(data)
        elif proc.poll() is not None:
            break
    rc = proc.wait(timeout=10)
    os.close(master)
    return rc, b"".join(chunks).decode(errors="replace")


# --------------------------------------------------------------------------
# Help / argument validation
# --------------------------------------------------------------------------


def test_help_exits_zero_and_documents_tool_flag(env):
    result = run(env, "--help")
    assert result.returncode == 0
    assert "Usage" in result.stdout
    assert "--tool" in result.stdout
    assert "recommended installer" in result.stdout
    assert env.calls() == []  # nothing installed


def test_invalid_tool_value_is_rejected(env):
    result = run(env, "--tool", "conda")
    assert result.returncode == 2
    assert "Invalid --tool" in result.stderr
    assert env.calls() == []


def test_unknown_option_is_rejected(env):
    result = run(env, "--frobnicate")
    assert result.returncode == 2
    assert "Unknown option" in result.stderr
    assert env.calls() == []


def test_tool_flag_without_argument_is_rejected(env):
    result = run(env, "--tool")
    assert result.returncode == 2
    assert "--tool requires an argument" in result.stderr


# --------------------------------------------------------------------------
# auto mode — uv present
# --------------------------------------------------------------------------


def test_auto_uses_uv_when_present(env):
    env.stub("uv")
    env.stub("nwave-ai")
    result = run(env)
    assert result.returncode == 0
    calls = env.calls()
    assert "uv tool install --reinstall nwave-ai" in calls
    assert "nwave-ai install" in calls
    assert not any(c.startswith("pipx") for c in calls)


def test_auto_prefers_uv_when_both_present(env):
    env.stub("uv")
    env.stub("pipx")
    env.stub("nwave-ai")
    result = run(env)
    assert result.returncode == 0
    calls = env.calls()
    assert "uv tool install --reinstall nwave-ai" in calls
    assert not any(c.startswith("pipx") for c in calls)


# --------------------------------------------------------------------------
# auto mode — only pipx present
# --------------------------------------------------------------------------


def test_auto_pipx_only_noninteractive_aborts_with_fixes(env):
    """No uv, no TTY, no --yes: abort and list the three fixes."""
    env.stub("pipx")
    env.stub("nwave-ai")
    result = run(env)
    assert result.returncode == 1
    assert "non-interactive" in result.stderr
    # The three suggested fixes are surfaced.
    assert "astral.sh/uv/install.sh" in result.stdout  # install uv
    assert "--tool pipx" in result.stdout  # force pipx
    assert "--yes" in result.stdout  # accept fallback
    assert env.calls() == []  # nothing installed


def test_auto_pipx_only_with_yes_flag_proceeds(env):
    env.stub("pipx")
    env.stub("nwave-ai")
    result = run(env, "--yes")
    assert result.returncode == 0
    calls = env.calls()
    assert "pipx install --force nwave-ai" in calls
    assert "nwave-ai install" in calls


def test_auto_pipx_only_with_assume_yes_env_proceeds(env):
    env.stub("pipx")
    env.stub("nwave-ai")
    result = run(env, env_vars={"NWAVE_ASSUME_YES": "1"})
    assert result.returncode == 0
    assert "pipx install --force nwave-ai" in env.calls()


# --------------------------------------------------------------------------
# auto mode — neither present
# --------------------------------------------------------------------------


def test_auto_neither_present_errors_with_both_instructions(env):
    env.stub("nwave-ai")  # present but never reached
    result = run(env)
    assert result.returncode == 1
    assert "Neither" in result.stderr
    assert "preferred" in result.stdout  # uv highlighted as preferred
    assert "astral.sh/uv/install.sh" in result.stdout
    assert "pipx" in result.stdout
    assert env.calls() == []


# --------------------------------------------------------------------------
# explicit --tool selection
# --------------------------------------------------------------------------


def test_tool_pipx_explicit_consent_skips_prompt(env):
    """--tool pipx is explicit consent: it must NOT abort even with no TTY."""
    env.stub("pipx")
    env.stub("nwave-ai")
    result = run(env, "--tool", "pipx")  # stdin closed, no --yes
    assert result.returncode == 0
    assert "pipx install --force nwave-ai" in env.calls()


def test_tool_pipx_missing_errors_with_pipx_instructions(env):
    env.stub("uv")  # present but pipx explicitly requested
    result = run(env, "--tool", "pipx")
    assert result.returncode == 1
    assert "pipx" in result.stderr
    assert "pipx.pypa.io" in result.stdout
    assert env.calls() == []


def test_tool_uv_missing_errors_with_uv_instructions(env):
    env.stub("pipx")  # present but uv explicitly requested
    result = run(env, "--tool", "uv")
    assert result.returncode == 1
    assert "uv" in result.stderr
    assert "astral.sh/uv/install.sh" in result.stdout
    assert env.calls() == []


def test_tool_env_var_selects_pipx(env):
    env.stub("pipx")
    env.stub("nwave-ai")
    result = run(env, env_vars={"NWAVE_INSTALLER_TOOL": "pipx"})
    assert result.returncode == 0
    assert "pipx install --force nwave-ai" in env.calls()


# --------------------------------------------------------------------------
# post-install PATH handling
# --------------------------------------------------------------------------


def test_cli_not_on_path_after_install_warns_instead_of_running(env):
    env.stub("uv")  # installs, but no nwave-ai stub => not on PATH
    result = run(env)
    assert result.returncode == 0
    calls = env.calls()
    assert "uv tool install --reinstall nwave-ai" in calls
    assert "nwave-ai install" not in calls
    assert "not on your PATH" in result.stderr
    assert "uv tool update-shell" in result.stdout


# --------------------------------------------------------------------------
# nwave-ai doctor exit-code propagation
# --------------------------------------------------------------------------


def test_healthy_doctor_exits_zero(env):
    env.stub("uv")
    env.stub("nwave-ai")  # default stub exits 0 for every subcommand
    result = run(env)
    assert result.returncode == 0
    assert "nwave-ai doctor" in env.calls()
    assert "complete" in result.stdout


def test_old_cli_without_doctor_completes_without_failing(env):
    """Regression for #74: a stale nwave-ai that predates `doctor` must not
    turn an otherwise successful install into a failure.

    The `doctor --help` capability probe detects the missing subcommand, so the
    script skips the health check, tells the user how to upgrade, and still
    exits 0 — instead of surfacing `Unknown command: doctor` as a hard failure.
    """
    env.stub("uv")
    env.stub_old_cli_without_doctor()
    result = run(env)
    assert result.returncode == 0
    calls = env.calls()
    assert "nwave-ai install" in calls
    # The real health check (`doctor` with no args) is never run on the old CLI.
    assert "nwave-ai doctor" not in calls
    # The user is pointed at the command that installs the version with doctor.
    assert "predates" in result.stderr
    assert "uv tool install --reinstall" in result.stderr


def test_old_cli_upgrade_hint_matches_selected_tool_pipx(env):
    """The pre-`doctor` upgrade hint must name the tool that was actually used.

    When pipx is the selected installer, the hint must read
    `pipx install --force`, not the uv command — a pipx user can't act on a
    `uv tool install` instruction.
    """
    env.stub("pipx")  # pipx-only auto-detection -> SELECTED=pipx
    env.stub_old_cli_without_doctor()
    result = run(env, "--yes")  # pipx needs consent
    assert result.returncode == 0
    assert "predates" in result.stderr
    assert "pipx install --force" in result.stderr
    assert "uv tool install" not in result.stderr


def test_doctor_failure_propagates_its_exit_code(env):
    env.stub("uv")
    env.stub_failing_doctor(exit_code=7)
    result = run(env)
    # The script's exit code mirrors `nwave-ai doctor` — a real problem, not
    # a swallowed warning.
    assert result.returncode == 7
    calls = env.calls()
    assert "uv tool install --reinstall nwave-ai" in calls
    assert "nwave-ai install" in calls
    assert "nwave-ai doctor" in calls
    assert "reported problems" in result.stderr


# --------------------------------------------------------------------------
# interactive prompt (pty-driven)
# --------------------------------------------------------------------------


def test_interactive_accept_proceeds_with_pipx(env):
    env.stub("pipx")
    env.stub("nwave-ai")
    rc, _out = run_pty(env, answer="y\n")
    assert rc == 0
    assert "pipx install --force nwave-ai" in env.calls()


def test_interactive_decline_shows_uv_instructions_and_installs_nothing(env):
    env.stub("pipx")
    env.stub("nwave-ai")
    rc, out = run_pty(env, answer="n\n")
    assert rc == 1  # declining is a non-zero outcome: nothing was installed
    assert "astral.sh/uv/install.sh" in out
    assert env.calls() == []  # declined => nothing installed
