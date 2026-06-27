"""Regression: legacy-hook migration must never orphan the attribution shim.

Root cause B (RCA fix-attribution-install-coupling, strand B):
    ``migrate_legacy_hook`` deletes the runtime script
    ``~/.nwave/hooks/nwave_attribution_hook.py`` UNCONDITIONALLY, but scans for
    the ``prepare-commit-msg`` shim in only a bounded set of hooks dirs
    (recorded config value + ``_resolve_hooks_dir()``). When git's effective
    hooks dir differs from that set -- a worktree, a local ``core.hooksPath``,
    a stale recorded value, or a shim installed via the historical
    ``--show-toplevel`` resolution -- the shim is NOT found. It survives while
    its target script is deleted. Every subsequent ``git commit`` then runs the
    orphaned shim, whose interpreter target is gone, and the commit is blocked.

Trap construction (deterministic, version-independent):
    A real tmp git repo whose effective hooks dir is diverted away from the
    real ``.git/hooks`` via a LOCAL ``core.hooksPath`` pointing at an empty
    decoy. The real shim is planted in ``<toplevel>/.git/hooks`` -- the
    historical ``--show-toplevel`` target, which the bounded scan never visits
    (``_resolve_hooks_dir`` returns the decoy because ``core.hooksPath`` wins,
    and ``--git-path hooks`` also follows ``core.hooksPath``). The recorded
    config value points at a second decoy. The runtime script is planted at
    ``<config_dir>/hooks/nwave_attribution_hook.py``.

    On the pre-fix code: runtime deleted + shim survives -> orphan -> RED.
    On the fixed code: the migration also probes ``--show-toplevel/.git/hooks``,
    finds the shim by content, removes it -> no orphan -> GREEN.

Bypass (Gate 12 delta-first): the load-bearing claim is a single relational
invariant across two slots -- "not (shim survives AND runtime deleted)" -- so a
direct assertion is clearer than a state-delta universe here.
"""

import subprocess
from pathlib import Path

import pytest

from scripts.install.attribution_utils import migrate_legacy_hook


# Serialize tests touching .git/hooks/ to avoid xdist races on shared state.
pytestmark = pytest.mark.xdist_group("git_hooks")


# A minimal prepare-commit-msg shim whose body carries the content marker the
# migration matches on (``nwave_attribution_hook``). Anything containing that
# token must be recognized as an nWave shim and removed.
_NWAVE_SHIM_BODY = (
    "#!/bin/sh\n"
    "# nWave attribution hook\n"
    '"$HOME/.nwave/hooks/nwave_attribution_hook.py" "$@"\n'
)

# A user-authored prepare-commit-msg with NO nWave marker -- must be preserved.
_USER_HOOK_BODY = "#!/bin/sh\n# my own prepare-commit-msg\necho hi >&2\n"


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "t@t.t"], check=True
    )
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)


def test_migrate_removes_orphaned_shim_in_unscanned_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shim planted outside the bounded scan set is removed, never orphaned."""
    repo = tmp_path / "repo"
    _init_repo(repo)

    # Divert the bounded scan: local core.hooksPath -> empty decoy. This makes
    # both _resolve_hooks_dir() and --git-path hooks resolve to the decoy.
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    subprocess.run(
        ["git", "-C", str(repo), "config", "core.hooksPath", str(decoy)], check=True
    )

    # The REAL shim sits in <toplevel>/.git/hooks -- the historical target,
    # reachable only by the new --show-toplevel probe.
    real_hooks_dir = repo / ".git" / "hooks"
    real_hooks_dir.mkdir(parents=True, exist_ok=True)
    shim = real_hooks_dir / "prepare-commit-msg"
    shim.write_text(_NWAVE_SHIM_BODY, encoding="utf-8")

    # Recorded config points at a second decoy (stale value).
    recorded_decoy = tmp_path / "recorded-decoy"
    recorded_decoy.mkdir()
    config_dir = tmp_path / ".nwave"
    (config_dir / "hooks").mkdir(parents=True)
    (config_dir / "global-config.json").write_text(
        f'{{"attribution": {{"hooks_dir": "{recorded_decoy}"}}}}\n',
        encoding="utf-8",
    )

    # The runtime script the shim targets -- deleted unconditionally by migrate.
    runtime = config_dir / "hooks" / "nwave_attribution_hook.py"
    runtime.write_text("# runtime\n", encoding="utf-8")

    # Probes are cwd-relative; run the migration from inside the trap repo.
    monkeypatch.chdir(repo)
    migrate_legacy_hook(config_dir=config_dir)

    # The defect: shim survives while its target is gone -> every commit blocks.
    assert not (shim.exists() and not runtime.exists()), (
        "orphaned shim: prepare-commit-msg survived in an unscanned hooks dir "
        "while its runtime target was deleted -- every git commit will block"
    )
    # The fix removes the shim outright (its .nwave-original, absent here).
    assert not shim.exists()


def test_migrate_preserves_user_authored_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A user's own prepare-commit-msg (no nWave marker) is never deleted."""
    repo = tmp_path / "repo"
    _init_repo(repo)

    real_hooks_dir = repo / ".git" / "hooks"
    real_hooks_dir.mkdir(parents=True, exist_ok=True)
    user_hook = real_hooks_dir / "prepare-commit-msg"
    user_hook.write_text(_USER_HOOK_BODY, encoding="utf-8")

    config_dir = tmp_path / ".nwave"
    config_dir.mkdir(parents=True)

    monkeypatch.chdir(repo)
    migrate_legacy_hook(config_dir=config_dir)

    assert user_hook.exists()
    assert user_hook.read_text(encoding="utf-8") == _USER_HOOK_BODY
