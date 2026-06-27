"""Regression: ``nwave-ai attribution off`` must de-trap a broken machine.

Root cause C (RCA fix-attribution-install-coupling, strand C):
    ``nwave-ai attribution off`` (``nwave_ai/cli.py`` off branch) only edited
    ``settings.json`` -- it cleared the preference, scrubbed the legacy settings
    credit, and unregistered the PreToolUse hook -- but it NEVER removed the
    legacy ``prepare-commit-msg`` git shim. So a user whose machine is already
    broken by an orphaned shim (the runtime target deleted, the shim left
    behind) cannot recover with the one obvious remediation command: ``off`` is
    a no-op against the actual blocker. The fix wires ``off`` to the hardened
    ``migrate_legacy_hook`` so turning attribution off removes the shim too.

Trap construction (deterministic, version-independent):
    Mirrors ``test_attribution_migrate_no_orphan_shim``. A real tmp git repo
    whose effective hooks dir is diverted away from the real ``.git/hooks`` via
    a LOCAL ``core.hooksPath`` pointing at an empty decoy. The real shim is
    planted in ``<toplevel>/.git/hooks`` -- the historical ``--show-toplevel``
    target reached only by the hardened (01-02) migration probe. The CLI ``off``
    path is driven for real; only the unrelated ~/.claude side effects
    (settings migration, hook unregister) are stubbed so the test never touches
    the real home dir.

    On the pre-fix code: ``off`` never calls migrate -> shim survives -> RED.
    On the fixed code: ``off`` calls migrate_legacy_hook -> shim removed -> GREEN.

Bypass (Gate 12 delta-first): the load-bearing claim is a single relational
invariant -- "the orphaned shim is gone after off" -- so a direct assertion is
clearer than a state-delta universe here (mirrors the sibling 01-02 test).
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from nwave_ai.cli import main


# Serialize tests touching .git/hooks/ to avoid xdist races on shared state.
pytestmark = pytest.mark.xdist_group("git_hooks")


# A minimal prepare-commit-msg shim whose body carries the content marker the
# migration matches on (``nwave_attribution_hook``).
_NWAVE_SHIM_BODY = (
    "#!/bin/sh\n"
    "# nWave attribution hook\n"
    '"$HOME/.nwave/hooks/nwave_attribution_hook.py" "$@"\n'
)


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "t@t.t"], check=True
    )
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)


def _isolate_off(config_dir: Path):
    """Patch the CLI off path's config dir + the unrelated ~/.claude seams.

    ``migrate_legacy_hook`` itself is deliberately NOT patched -- that is the
    wiring under test. Only the settings-credit migration and the PreToolUse
    hook unregister (both of which would otherwise reach the real ~/.claude)
    are stubbed.
    """
    return (
        patch("sys.argv", ["nwave-ai", "attribution", "off"]),
        patch("nwave_ai.cli._get_config_dir", return_value=config_dir),
        patch("nwave_ai.cli.migrate_legacy_settings_attribution"),
        patch("nwave_ai.cli.unregister_attribution_hook"),
    )


def test_off_removes_orphaned_shim_in_unscanned_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`attribution off` removes a planted orphaned shim (root cause C)."""
    repo = tmp_path / "repo"
    _init_repo(repo)

    # Divert the bounded scan: local core.hooksPath -> empty decoy.
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    subprocess.run(
        ["git", "-C", str(repo), "config", "core.hooksPath", str(decoy)], check=True
    )

    # The REAL shim sits in <toplevel>/.git/hooks -- reachable only by the
    # hardened --show-toplevel probe, never the bounded scan.
    real_hooks_dir = repo / ".git" / "hooks"
    real_hooks_dir.mkdir(parents=True, exist_ok=True)
    shim = real_hooks_dir / "prepare-commit-msg"
    shim.write_text(_NWAVE_SHIM_BODY, encoding="utf-8")

    config_dir = tmp_path / ".nwave"
    (config_dir / "hooks").mkdir(parents=True)

    # Probes are cwd-relative; drive the CLI from inside the trap repo.
    monkeypatch.chdir(repo)
    patch_a, patch_b, patch_c, patch_d = _isolate_off(config_dir)
    with patch_a, patch_b, patch_c, patch_d:
        result = main()

    # off must stay fail-open (never raise / never error the toggle).
    assert result == 0
    # The defect: off leaves the orphaned shim in place -> machine stays broken.
    assert not shim.exists(), (
        "attribution off left the orphaned prepare-commit-msg shim in place -- "
        "an already-broken machine cannot recover with the obvious command"
    )


def test_off_is_fail_open_when_no_shim_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`attribution off` never raises when there is no shim to remove."""
    repo = tmp_path / "repo"
    _init_repo(repo)

    config_dir = tmp_path / ".nwave"
    config_dir.mkdir(parents=True)

    monkeypatch.chdir(repo)
    patch_a, patch_b, patch_c, patch_d = _isolate_off(config_dir)
    with patch_a, patch_b, patch_c, patch_d:
        result = main()

    assert result == 0
