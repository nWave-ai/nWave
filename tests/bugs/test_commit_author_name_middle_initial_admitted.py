"""Regression: the range gates must ADMIT a real contributor with a middle initial.

Companion to ``test_name_field_middle_initial_false_positive.py`` at the
enforcement layer. The pre-push (``validate_push_identity.py``) and authoritative
CI (``ci_author_check.py``) runners both call ``validate_name_field`` on the
author/committer NAME of every commit in the range. Because that check tokenizes
on ALL whitespace, a legitimate contributor whose name carries a middle initial
``T`` — or a name part like ``User`` / ``Test`` — is wrongly REFUSED at the
authoritative gate (the one that survives ``--no-verify`` and ``core.hooksPath``
injection). A contributor named ``Bao T Nguyen`` pushing with a valid GitHub
no-reply email must be ADMITTED (exit 0), not blocked.

Faithful composition (no test-weakening): a REAL git commit is created with
``GIT_AUTHOR_NAME="Bao T Nguyen"`` and a clean no-reply email, and the REAL
runner subprocess reads exactly what git stored (``%an`` over a NUL-separated
record). Nothing here helps the gate — the name staged is the name git keeps and
the runner validates.

Layer 3 (subprocess, real git in an isolated tmp repo), example-based —
Mandate 9 + 11: no PBT here.

EXPECTED-RED until the crafter narrows ``validate_name_field`` tokenization to
control characters only. Production is left untouched by this test.
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

#: A legitimate contributor whose middle initial collides with the placeholder
#: denylist token ``t`` — the exact shape PR-style real names take.
_REAL_AUTHOR_NAME = "Bao T Nguyen"
_REAL_AUTHOR_EMAIL = "bao@users.noreply.github.com"


def _isolated_env(repo: Path) -> dict[str, str]:
    """Env pinning git to ``repo`` and letting the runner import its sibling core.

    ``HOME`` / ``GIT_CONFIG_*`` / ``GIT_CEILING_DIRECTORIES`` sandbox git to the
    throwaway repo (pairs with the root conftest pollution guard).
    ``PYTHONPATH`` carries the repo root so ``scripts.hooks.validate_author_identity``
    resolves — this regression is about the NAME verdict, not the import path
    (that is covered by ``test_commit_author_validator_clean_env_import.py``).
    """
    env = os.environ.copy()
    env["HOME"] = str(repo)
    env["GIT_CONFIG_GLOBAL"] = str(repo / ".gitconfig-global")
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    env["GIT_CEILING_DIRECTORIES"] = str(repo.parent)
    env["PYTHONPATH"] = str(_REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
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


def _commit(
    repo: Path, env: dict[str, str], message: str, name: str, email: str
) -> None:
    commit_env = dict(env)
    commit_env.update(
        GIT_AUTHOR_NAME=name,
        GIT_AUTHOR_EMAIL=email,
        GIT_COMMITTER_NAME=name,
        GIT_COMMITTER_EMAIL=email,
    )
    (repo / "f.txt").write_text(message + "\n")
    subprocess.run(
        ["git", "add", "-A"],
        cwd=str(repo),
        env=commit_env,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", message],
        cwd=str(repo),
        env=commit_env,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo_with_middle_initial_author(tmp_path: Path) -> Path:
    """Throwaway repo: clean baseline + an in-range commit by ``Bao T Nguyen``.

    The baseline (root) commit is the range BASE (excluded from ``base..head``);
    the in-range follow-on commit carries the real middle-initial author, so it
    is exactly the commit the runner must admit.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    env = _isolated_env(repo)
    _git(repo, env, "init", "-q", "-b", "main")
    _git(repo, env, "config", "commit.gpgsign", "false")
    _commit(repo, env, "baseline", "Real", "real@users.noreply.github.com")
    _commit(repo, env, "real contributor work", _REAL_AUTHOR_NAME, _REAL_AUTHOR_EMAIL)
    return repo


def test_ci_gate_admits_a_real_middle_initial_contributor(
    repo_with_middle_initial_author: Path,
) -> None:
    """The authoritative CI range gate ADMITS ``Bao T Nguyen`` (exit 0).

    EXPECTED-RED: today ``validate_name_field("Bao T Nguyen")`` rejects on the
    space-separated ``T`` token, so the gate exits non-zero and blocks a real
    contributor. After the tokenization narrowing it exits 0.
    """
    repo = repo_with_middle_initial_author
    env = _isolated_env(repo)
    base = _git(repo, env, "rev-list", "--max-parents=0", "HEAD")
    head = _git(repo, env, "rev-parse", "HEAD")
    result = subprocess.run(
        [sys.executable, str(_CI_SCRIPT), "--base", base, "--head", head],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "CI gate wrongly blocked a real middle-initial contributor:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_push_gate_admits_a_real_middle_initial_contributor(
    repo_with_middle_initial_author: Path,
) -> None:
    """The pre-push range gate ADMITS ``Bao T Nguyen`` (exit 0).

    EXPECTED-RED for the same reason as the CI gate — both runners share the
    ``validate_name_field`` NAME check. The push gate reads the real ``%an`` over
    a NUL-separated record, so it validates exactly the name git stored.
    """
    repo = repo_with_middle_initial_author
    env = _isolated_env(repo)
    head = _git(repo, env, "rev-parse", "HEAD")
    base = _git(repo, env, "rev-list", "--max-parents=0", "HEAD")
    ref_line = f"refs/heads/main {head} refs/heads/main {base}\n"
    result = subprocess.run(
        [sys.executable, str(_PUSH_SCRIPT)],
        cwd=str(repo),
        env=env,
        input=ref_line,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Push gate wrongly blocked a real middle-initial contributor:\n"
        f"{result.stdout}\n{result.stderr}"
    )
