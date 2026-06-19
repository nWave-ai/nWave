"""Gap-review fixes driven through REAL production entry points.

The central lesson of the gap review: seam-only tests let two requirements ship
unwired. Every test here drives the REAL entry point a user or hook actually
hits — never the ``run_gate`` / ``composition.adopt`` seams.

Real entry points exercised:
- Fix 1: ``session_start_handler.handle_session_start()`` (stdin JSON in).
- Fix 2: ``nwave_ai.cli.main_with_argv(["completion", ...])``.
- Fix 3: ``nwave_ai.cli.main(["--help"])`` / ``main_with_argv([])`` usage text.
- Fix 4: ``DESConfig(...).enabled_for_repo`` over a non-dict marker file +
  ``AutoMarkingService.adopt_if_warranted`` over a non-dict des-config.json.
- Fix 5: ``DESConfig(...).enabled_for_repo`` walk-up + ``$HOME`` stop boundary.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Shared sandbox fixture (mirrors the activation-gating composition fixture):
# redirect HOME so DESConfig / CLI read the sandbox global-config, and give a
# project dir UNDER home (so the $HOME stop boundary is exercisable).
# ---------------------------------------------------------------------------


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home_dir = tmp_path / "home"
    project_root = home_dir / "work" / "project"
    home_dir.mkdir(parents=True, exist_ok=True)
    project_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))
    return home_dir, project_root


def _des_config(project_root: Path):
    from des.adapters.driven.config.des_config import DESConfig

    return DESConfig(
        cwd=project_root,
        global_config_path=Path.home() / ".nwave" / "global-config.json",
    )


def _write_marker(project_root: Path, *, enabled: bool = True) -> None:
    nwave = project_root / ".nwave"
    nwave.mkdir(parents=True, exist_ok=True)
    (nwave / "local-config.json").write_text(
        json.dumps({"enabled_for_repo": enabled}) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Fix 1 — Trigger-1 (prior-use adoption) wired into SessionStart.
# Drives the REAL handle_session_start(...) with a SessionStart hook envelope on
# stdin. Asserts the marker is written for a project with prior-use evidence,
# and NOT written for a project with only a bare des-config.json.
# ---------------------------------------------------------------------------


def _feed_session_start_stdin(
    monkeypatch: pytest.MonkeyPatch, project_root: Path
) -> None:
    payload = json.dumps({"hook_event_name": "SessionStart", "cwd": str(project_root)})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))


def test_session_start_adopts_project_with_prior_use(
    sandbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project with prior-use evidence gets the marker written by SessionStart."""
    _home, project_root = sandbox
    logs = project_root / ".nwave" / "des" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "audit-2026-06-18.log").write_text(
        '{"event":"phase_entered"}\n', encoding="utf-8"
    )
    _feed_session_start_stdin(monkeypatch, project_root)

    from des.adapters.drivers.hooks.session_start_handler import handle_session_start

    exit_code = handle_session_start()

    assert exit_code == 0  # SessionStart never blocks (fail-open)
    marker = project_root / ".nwave" / "local-config.json"
    assert marker.exists(), "prior-use project must be silently adopted at SessionStart"
    assert json.loads(marker.read_text())["enabled_for_repo"] is True


def test_session_start_does_not_adopt_bare_des_config(
    sandbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project with only a bare des-config.json is NOT adopted (gate stays meaningful)."""
    _home, project_root = sandbox
    nwave = project_root / ".nwave"
    nwave.mkdir(parents=True, exist_ok=True)
    (nwave / "des-config.json").write_text("{}", encoding="utf-8")
    _feed_session_start_stdin(monkeypatch, project_root)

    from des.adapters.drivers.hooks.session_start_handler import handle_session_start

    exit_code = handle_session_start()

    assert exit_code == 0
    marker = project_root / ".nwave" / "local-config.json"
    assert not marker.exists(), (
        "a bare des-config.json is mere-install evidence, NOT prior use"
    )


# ---------------------------------------------------------------------------
# Fix 2 — `nwave-ai completion <bash|zsh>` reachable via the real CLI dispatch.
# ---------------------------------------------------------------------------


def _run_argv(argv: list[str]) -> tuple[int, str, str]:
    import contextlib

    from nwave_ai import cli

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main_with_argv(argv)
    return code, out.getvalue(), err.getvalue()


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_completion_subcommand_prints_generated_script(shell: str) -> None:
    """`completion <shell>` exits 0 and prints the generated script via the real CLI."""
    from nwave_ai.completion import generate_completion

    code, out, _err = _run_argv(["completion", shell])

    assert code == 0
    assert out.strip() == generate_completion(shell).strip()
    for token in ("project", "mode", "status", "enable", "disable", "all", "opt-in"):
        assert token in out, f"completion must surface {token!r}"
    assert "hooks" not in out, "completion must not leak internal hook vocabulary"


def test_completion_subcommand_rejects_bad_shell() -> None:
    """An invalid shell -> nonzero exit + usage on stderr."""
    code, _out, err = _run_argv(["completion", "fish"])
    assert code != 0
    assert "completion" in err.lower()


def test_completion_subcommand_requires_a_shell() -> None:
    """A missing shell -> nonzero exit + usage on stderr."""
    code, _out, err = _run_argv(["completion"])
    assert code != 0
    assert "completion" in err.lower()


# ---------------------------------------------------------------------------
# Fix 3 — `--help` lists the new commands (real main / main_with_argv usage).
# ---------------------------------------------------------------------------


def test_help_lists_new_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    """`nwave-ai --help` stdout lists project, mode, status, completion."""
    import contextlib

    from nwave_ai import cli

    monkeypatch.setattr("sys.argv", ["nwave-ai", "--help"])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main()
    text = out.getvalue()

    assert code == 0
    for command in ("project", "mode", "status", "completion"):
        assert command in text, f"--help must list the {command!r} command"


# ---------------------------------------------------------------------------
# Fix 4 — fail-open on non-dict JSON (real DESConfig + AutoMarkingService).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("body", ["null", "[]", "123", '"x"'])
def test_non_dict_marker_resolves_inactive_without_crashing(sandbox, body: str) -> None:
    """A non-dict marker file does not crash enabled_for_repo; resolves to None."""
    _home, project_root = sandbox
    nwave = project_root / ".nwave"
    nwave.mkdir(parents=True, exist_ok=True)
    (nwave / "local-config.json").write_text(body, encoding="utf-8")

    config = _des_config(project_root)
    # No crash; non-dict marker is "no opinion" -> None -> defers to global mode.
    assert config.enabled_for_repo is None


@pytest.mark.parametrize("body", ["null", "[]", "123"])
def test_non_dict_des_config_does_not_crash_adoption(sandbox, body: str) -> None:
    """A non-dict des-config.json does not crash the audit-dir resolution path."""
    _home, project_root = sandbox
    nwave = project_root / ".nwave"
    nwave.mkdir(parents=True, exist_ok=True)
    (nwave / "des-config.json").write_text(body, encoding="utf-8")

    from des.application.auto_marking_service import (
        AdoptionOutcome,
        AdoptionTrigger,
        AutoMarkingService,
    )

    # No prior-use evidence -> NOT_WARRANTED, and crucially: no crash on .get().
    outcome = AutoMarkingService().adopt_if_warranted(
        project_root=project_root, trigger=AdoptionTrigger.PRIOR_USE
    )
    assert outcome is AdoptionOutcome.NOT_WARRANTED


# ---------------------------------------------------------------------------
# Fix 5 — walk-up resolution + $HOME stop boundary (real DESConfig).
# ---------------------------------------------------------------------------


def test_marker_in_parent_activates_subdir(sandbox) -> None:
    """A marker in a parent dir activates a subdirectory cwd (walk-up)."""
    _home, project_root = sandbox
    _write_marker(project_root, enabled=True)
    subdir = project_root / "src" / "deep" / "nested"
    subdir.mkdir(parents=True, exist_ok=True)

    config = _des_config(subdir)
    assert config.enabled_for_repo is True


def test_nearer_marker_shadows_farther(sandbox) -> None:
    """A nearer marker (disabled) shadows a farther one (enabled) — nearer-wins."""
    _home, project_root = sandbox
    _write_marker(project_root, enabled=True)
    subdir = project_root / "src" / "module"
    subdir.mkdir(parents=True, exist_ok=True)
    _write_marker(subdir, enabled=False)

    config = _des_config(subdir)
    assert config.enabled_for_repo is False


def test_home_nwave_is_not_a_project_marker(sandbox) -> None:
    """$HOME/.nwave/local-config.json is NOT treated as a project marker.

    A cwd under $HOME with no marker of its own must NOT pick up the global
    config home's directory as a project activation marker.
    """
    home_dir, _project_root = sandbox
    # Plant a (bogus) marker at $HOME/.nwave — the global config home.
    home_nwave = home_dir / ".nwave"
    home_nwave.mkdir(parents=True, exist_ok=True)
    (home_nwave / "local-config.json").write_text(
        json.dumps({"enabled_for_repo": True}), encoding="utf-8"
    )
    # A cwd under $HOME with NO marker of its own.
    bare = home_dir / "scratch" / "no-marker-here"
    bare.mkdir(parents=True, exist_ok=True)

    config = _des_config(bare)
    assert config.enabled_for_repo is None, (
        "$HOME/.nwave/ must never be inspected as a project marker"
    )
