"""Unit tests for ``scripts.shared.git_hooks_paths.resolve_hooks_dir``.

The helper is the shared primitive that both the attribution plugin's
install path and uninstall path use to resolve the worktree-aware
``.git/hooks`` directory. It MUST work in three layouts:

1. Regular checkout (``.git`` is a real directory)
2. Linked worktree (``.git`` is a pointer file)
3. Bare repository (returned path may be relative to ``cwd``)

These tests use real ``git`` subprocess calls against ``tmp_path``-backed
repositories — no mocks. ``--git-common-dir`` behavior is the explicit
contract under test.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from scripts.shared.git_hooks_paths import resolve_hooks_dir


pytestmark = pytest.mark.xdist_group("git_hooks_paths_unit")


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand with predictable env, raising on non-zero."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )


def _init_repo(repo_dir: Path) -> Path:
    """Initialize a fresh git repository with one commit. Returns repo path."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    _git(repo_dir, "init", "-q", "-b", "main")
    _git(repo_dir, "config", "user.email", "test@example.com")
    _git(repo_dir, "config", "user.name", "Test")
    (repo_dir / "README.md").write_text("seed\n")
    _git(repo_dir, "add", "README.md")
    _git(repo_dir, "commit", "-q", "-m", "chore: seed")
    return repo_dir


def _run_in_dir(target: Path) -> Path:
    """Run resolve_hooks_dir() from ``target`` as cwd. Restores cwd on exit."""
    original = Path.cwd()
    try:
        os.chdir(target)
        return resolve_hooks_dir()
    finally:
        os.chdir(original)


class TestResolveHooksDirContract:
    """Behavior contract for ``resolve_hooks_dir``."""

    def test_returns_absolute_path_in_main_checkout(self, tmp_path: Path) -> None:
        """In a regular checkout, the helper returns an ABSOLUTE path
        ending in ``.git/hooks``.

        Absolute paths are required because callers (attribution_utils) join
        and ``mkdir(parents=True)`` against the result; a relative path
        resolved against the wrong cwd is the original 01-01 bug class.
        """
        repo = _init_repo(tmp_path / "main_checkout")

        hooks_dir = _run_in_dir(repo)

        assert hooks_dir.is_absolute(), (
            f"resolve_hooks_dir must return an absolute path; got {hooks_dir!r}"
        )
        assert hooks_dir.name == "hooks"
        assert hooks_dir.parent.resolve() == (repo / ".git").resolve()

    def test_returns_shared_hooks_dir_in_worktree(self, tmp_path: Path) -> None:
        """In a linked worktree, the helper returns the SHARED ``.git/hooks``
        directory of the main checkout, not the per-worktree git dir.

        This is the worktree-aware contract: ``--git-common-dir`` is the
        sibling of ``--show-toplevel`` that resolves to the shared ``.git``
        directory regardless of whether ``.git`` is a directory or a pointer
        file. This test FAILS without ``--git-common-dir``.
        """
        main_repo = _init_repo(tmp_path / "main")
        worktree_path = tmp_path / "wt"
        _git(main_repo, "worktree", "add", "-q", str(worktree_path), "-b", "feature/x")

        hooks_in_worktree = _run_in_dir(worktree_path)
        hooks_in_main = _run_in_dir(main_repo)

        assert hooks_in_worktree.resolve() == hooks_in_main.resolve(), (
            "Worktree must resolve to the SAME shared hooks dir as the main "
            f"checkout; got worktree={hooks_in_worktree!r} main={hooks_in_main!r}"
        )
        # And the resolved hooks dir must actually exist (it lives under
        # the main repo, not the worktree's pointer-file ``.git``).
        assert hooks_in_worktree.parent.is_dir(), (
            f"Resolved git common dir must be a real directory; got "
            f"{hooks_in_worktree.parent!r}"
        )

    def test_uses_git_common_dir_subcommand(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The helper invokes ``git rev-parse --git-common-dir`` (and not
        ``--show-toplevel``).

        We assert this by capturing the argv passed to ``subprocess.run`` —
        intercepting at the subprocess boundary lets us verify the contract
        without breaking the helper's purity properties.
        """
        repo = _init_repo(tmp_path / "intercept")

        captured: list[list[str]] = []
        real_run = subprocess.run

        def spy_run(args, *a, **kw):  # type: ignore[no-untyped-def]
            if isinstance(args, list) and args and args[0] == "git":
                captured.append(list(args))
            return real_run(args, *a, **kw)

        monkeypatch.setattr("scripts.shared.git_hooks_paths.subprocess.run", spy_run)

        _run_in_dir(repo)

        assert captured, "Expected at least one git subprocess invocation"
        assert any("--git-common-dir" in cmd for cmd in captured), (
            f"Expected --git-common-dir in one of the git calls; saw {captured!r}"
        )
        assert not any("--show-toplevel" in cmd for cmd in captured), (
            "--show-toplevel is the broken API from RCA Branch A; helper must "
            f"not use it. Saw: {captured!r}"
        )
