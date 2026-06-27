"""Regression: commit-identity validators must run in a CLEAN (non-editable) env.

Adversarial-review finding C1 (``docs/feature/commit-author-identity-validation/
plan.md``). Both cross-importing hook scripts —

  * ``scripts/hooks/ci_author_check.py``      (the authoritative CI gate)
  * ``scripts/hooks/validate_push_identity.py`` (the pre-push gate)

— do ``from scripts.hooks.validate_author_identity import is_valid_author_email``
at module import. That import only resolves when ``scripts`` happens to be an
importable top-level package on ``sys.path`` — which it is in THIS machine's
editable ``uv`` install (a ``.pth`` entry adds the repo root) but is NOT in a
clean CI checkout that never ran ``uv sync`` / set ``PYTHONPATH``. There, both
scripts crash with::

    ModuleNotFoundError: No module named 'scripts'

before validating anything — the gate silently never runs. The earlier PR #42
"proof" was masked precisely by this machine's editable ``.pth``.

These tests reproduce the clean environment with ``python3 -S`` (no ``site``, so
no ``.pth`` files are processed) and an explicitly emptied ``PYTHONPATH``, then
drive each script as a subprocess over a tiny throwaway git repo. The contract:
each script must self-locate its sibling module and run to a real verdict — a
``ModuleNotFoundError`` (or any import-time crash) is the bug.

Layer 3 (subprocess, real git), example-based — Mandate 9 + 11: no PBT here.

EXPECTED-RED until the crafter adds a self-locating ``sys.path`` bootstrap to
both cross-importing scripts (plan.md C1 fix). Leave production untouched here.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS = _REPO_ROOT / "scripts" / "hooks"
_CI_SCRIPT = _HOOKS / "ci_author_check.py"
_PUSH_SCRIPT = _HOOKS / "validate_push_identity.py"


def _clean_env(repo: Path) -> dict[str, str]:
    """A non-editable-install environment: no inherited PYTHONPATH, git sandboxed.

    ``PYTHONPATH`` is emptied so the only way ``scripts.hooks.validate_author_identity``
    resolves is if the script bootstraps its own location — mirroring a fresh CI
    checkout. ``HOME`` / ``GIT_CONFIG_*`` / ``GIT_CEILING_DIRECTORIES`` keep git
    pinned to the throwaway repo (pairs with the root conftest pollution guard).
    """
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["HOME"] = str(repo)
    env["GIT_CONFIG_GLOBAL"] = str(repo / ".gitconfig-global")
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    env["GIT_CEILING_DIRECTORIES"] = str(repo.parent)
    return env


def _git(repo: Path, env: dict[str, str], *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def tiny_repo(tmp_path: Path) -> Path:
    """A throwaway git repo with a clean baseline + one clean follow-on commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = _clean_env(repo)
    _git(repo, env, "init", "-q", "-b", "main")
    _git(repo, env, "config", "commit.gpgsign", "false")
    commit_env = dict(env)
    commit_env.update(
        GIT_AUTHOR_NAME="Real",
        GIT_AUTHOR_EMAIL="real@users.noreply.github.com",
        GIT_COMMITTER_NAME="Real",
        GIT_COMMITTER_EMAIL="real@users.noreply.github.com",
    )
    (repo / "f.txt").write_text("base\n")
    subprocess.run(
        ["git", "add", "-A"],
        cwd=str(repo),
        env=commit_env,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "baseline"],
        cwd=str(repo),
        env=commit_env,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "follow-on"],
        cwd=str(repo),
        env=commit_env,
        check=True,
        capture_output=True,
        text=True,
    )
    return repo


def _run_isolated(
    script: Path, args: list[str], repo: Path
) -> subprocess.CompletedProcess[str]:
    """Run ``python3 -S <script> <args>`` in a clean env over ``repo``.

    ``-S`` disables ``site`` so no ``.pth`` file (e.g. an editable-install entry
    that injects the repo root) is processed — exactly the clean CI shape.
    """
    env = _clean_env(repo)
    return subprocess.run(
        [sys.executable, "-S", str(script), *args],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_ci_author_check_imports_in_clean_env(tiny_repo: Path) -> None:
    """``ci_author_check.py`` must not crash with ModuleNotFoundError under ``-S``."""
    base = _git(tiny_repo, _clean_env(tiny_repo), "rev-list", "--max-parents=0", "HEAD")
    head = _git(tiny_repo, _clean_env(tiny_repo), "rev-parse", "HEAD")
    result = _run_isolated(_CI_SCRIPT, ["--base", base, "--head", head], tiny_repo)
    assert "ModuleNotFoundError" not in result.stderr, result.stderr
    # A clean range over clean commits must reach a real verdict (exit 0), not an
    # import crash. (Import crash would exit non-zero with the traceback above.)
    assert result.returncode == 0, result.stderr


def test_validate_push_identity_imports_in_clean_env(tiny_repo: Path) -> None:
    """``validate_push_identity.py`` must not crash with ModuleNotFoundError under ``-S``."""
    env = _clean_env(tiny_repo)
    head = _git(tiny_repo, env, "rev-parse", "HEAD")
    base = _git(tiny_repo, env, "rev-list", "--max-parents=0", "HEAD")
    ref_line = f"refs/heads/main {head} refs/heads/main {base}\n"
    result = subprocess.run(
        [sys.executable, "-S", str(_PUSH_SCRIPT)],
        cwd=str(tiny_repo),
        env=env,
        input=ref_line,
        capture_output=True,
        text=True,
        check=False,
    )
    assert "ModuleNotFoundError" not in result.stderr, result.stderr
    # A clean range over clean commits must reach a real verdict (exit 0).
    assert result.returncode == 0, result.stderr
