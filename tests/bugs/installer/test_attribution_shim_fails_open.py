"""Regression tests: the attribution shim must NEVER hard-block a git commit.

Root cause A (RCA attribution-install-coupling, 2026-06):
    The "never block commits" guarantee lives in the Python layer
    (scripts/hooks/nwave_attribution_hook.py:103 -- "Exit 0 on ALL error
    paths") but NOT in the shell shim that actually gates git. The rendered
    prepare-commit-msg shim runs

        "{{PYTHON_CMD}}" "{{HOOK_SCRIPT_PATH}}" "$@"

    with NO guard that the script exists. When a colleague's
    ~/.nwave/hooks/nwave_attribution_hook.py goes missing (worktree /
    core.hooksPath drift -- root cause B), `python3 /missing.py` aborts with
    a non-zero exit and every `git commit` fails (FM-1).

    A second failure mode (FM-2a): the chain guard on the chained original was
    `[ -f ]`, so a *non-executable* prepare-commit-msg.nwave-original was
    invoked by path -- turning git's would-be "skip a non-exec hook" into a
    hard "Permission denied" error that blocks the commit.

Fix (FIX-1):
    - Guard the script invocation: `[ -f "{{HOOK_SCRIPT_PATH}}" ] || exit 0`.
    - Change the chain guard from `[ -f ]` to `[ -x ]` so a non-executable
      original is skipped, not invoked.
    - A genuine user hook (an *executable* original returning non-zero) MUST
      still propagate its failure -- that is a real block, not plumbing.

Each test renders the shim from the REAL template via the production
`_read_shim_template()` and drives a real `git commit` subprocess, exercising
the exact surface the user hit.
"""

import subprocess
from pathlib import Path

import pytest

from scripts.install.attribution_utils import _read_shim_template


# Serialize tests touching .git/hooks/ to avoid xdist races on shared state.
pytestmark = pytest.mark.xdist_group("git_hooks")


def _init_git_repo(repo: Path) -> Path:
    """Create an isolated git repo and return its hooks directory."""
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    hooks_dir = repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    # Deterministic, fully local identity + no signing/templating interference.
    for key, value in (
        ("user.name", "Regression Bot"),
        ("user.email", "regression@nwave.test"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", str(hooks_dir)),
    ):
        subprocess.run(["git", "config", key, value], cwd=repo, check=True)
    return hooks_dir


def _render_shim(hook_script_path: Path) -> str:
    """Render the real shim template with python3 and the given script path."""
    template = _read_shim_template()
    return template.replace("{{PYTHON_CMD}}", "python3").replace(
        "{{HOOK_SCRIPT_PATH}}", str(hook_script_path)
    )


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _stage_a_file(repo: Path) -> None:
    (repo / "tracked.txt").write_text("content\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)


def _commit(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "commit", "-m", "regression commit"],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def _commit_count(repo: Path) -> int:
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip()) if result.returncode == 0 else 0


def test_orphaned_shim_with_deleted_script_does_not_block_commit(
    tmp_path: Path,
) -> None:
    """FM-1: a shim pointing at a deleted script must fail open (exit 0).

    The user installed attribution, then the runtime script was removed
    (worktree / core.hooksPath drift). The orphaned shim must not abort the
    commit.
    """
    repo = tmp_path / "repo"
    hooks_dir = _init_git_repo(repo)

    # Install a real script, then delete it -- exactly the orphaned state.
    missing_script = repo / ".nwave" / "hooks" / "nwave_attribution_hook.py"
    missing_script.parent.mkdir(parents=True, exist_ok=True)
    missing_script.write_text("import sys; sys.exit(0)\n", encoding="utf-8")
    missing_script.unlink()
    assert not missing_script.exists()

    _write_executable(hooks_dir / "prepare-commit-msg", _render_shim(missing_script))
    _stage_a_file(repo)

    result = _commit(repo)

    assert result.returncode == 0, (
        "orphaned shim (deleted script) blocked the commit -- "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert _commit_count(repo) == 1


def test_non_executable_original_is_skipped_not_invoked(tmp_path: Path) -> None:
    """FM-2a: a non-executable chained original must be skipped, not invoked.

    With the old `[ -f ]` guard, the shim executed the non-exec original by
    path -> "Permission denied" -> non-zero -> commit blocked. The `[ -x ]`
    guard skips it (as git itself would), and the (also-missing) script guard
    lets the commit complete.
    """
    repo = tmp_path / "repo"
    hooks_dir = _init_git_repo(repo)

    # Non-executable original: present but no +x bit -> git would skip it.
    original = hooks_dir / "prepare-commit-msg.nwave-original"
    original.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    original.chmod(0o644)

    missing_script = repo / ".nwave" / "hooks" / "nwave_attribution_hook.py"
    _write_executable(hooks_dir / "prepare-commit-msg", _render_shim(missing_script))
    _stage_a_file(repo)

    result = _commit(repo)

    assert result.returncode == 0, (
        "non-executable original was invoked instead of skipped -- "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert _commit_count(repo) == 1


def test_executable_original_returning_nonzero_still_blocks_commit(
    tmp_path: Path,
) -> None:
    """Criterion 5: a genuine user hook failure MUST still propagate.

    An *executable* chained original returning non-zero is a real block, not
    plumbing -- the fail-open guarantee must not swallow it.
    """
    repo = tmp_path / "repo"
    hooks_dir = _init_git_repo(repo)

    original = hooks_dir / "prepare-commit-msg.nwave-original"
    _write_executable(original, "#!/bin/sh\nexit 1\n")

    script = repo / ".nwave" / "hooks" / "nwave_attribution_hook.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    _write_executable(hooks_dir / "prepare-commit-msg", _render_shim(script))
    _stage_a_file(repo)

    result = _commit(repo)

    assert result.returncode != 0, (
        "an executable user hook returning non-zero must still block the commit"
    )
    assert _commit_count(repo) == 0
