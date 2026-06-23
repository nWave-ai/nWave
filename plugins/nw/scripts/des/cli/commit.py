"""CLI: Commit a step's owned files under an exclusive lock (issue #51, ADR-027).

In parallel multi-agent DELIVER, several sub-agents share one git working tree
and index. Two concurrent ``git commit`` calls race: the second sweeps up files
another agent staged but did not yet commit (cross-staging), and pre-commit
hooks that auto-stage formatter fixes widen the window. The result is
misattributed commits and a corrupted ``Step-Id:`` audit chain.

``des-commit`` makes the commit critical section safe:

1. Holds an exclusive ``fcntl.flock(LOCK_EX)`` (same idiom as
   ``des.cli.log_phase``; degrades to no-lock on Windows) so concurrent callers
   serialize and never collide on ``.git/index.lock``.
2. Builds the commit from a **temporary index** seeded with HEAD plus ONLY the
   owned paths (``git read-tree HEAD`` then ``git add -A -- <owned>`` against a
   private ``GIT_INDEX_FILE``). The commit is therefore scoped to the owned
   paths *by construction* — a foreign file, a concurrently-staged file, or a
   pre-commit hook's auto-staged file cannot enter this index. ``--no-verify``
   keeps hooks from mutating the commit (the crafter already validated during
   GREEN); ``-A`` records deletions and renames, not just additions.
3. The real index and working tree are left alone except that owned paths are
   resynced to the new HEAD, so any other agent's staged work is preserved.

Usage:
    des-commit \\
      --repo-dir . \\
      --owned-paths src/foo.py tests/test_foo.py \\
      --step-id 02-03 \\
      --message "feat: add foo"

Exit codes:
    0 = Success, commit created containing only the owned paths
    1 = Git/commit error (nothing to commit, bad repo, git failure)
    2 = Usage error (argparse default for missing/invalid arguments)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:  # pragma: no cover - Windows has no fcntl
    _HAS_FCNTL = False


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the commit CLI."""
    parser = argparse.ArgumentParser(
        prog="des.cli.commit",
        description=(
            "Commit a step's owned files under an exclusive lock, scoped so a "
            "parallel agent's staged work is never swept into this commit."
        ),
    )
    parser.add_argument(
        "--repo-dir",
        default=".",
        help="Path to the git repository (default: current directory)",
    )
    parser.add_argument(
        "--owned-paths",
        required=True,
        nargs="+",
        help="The files this step owns; only these are committed",
    )
    parser.add_argument(
        "--step-id",
        required=True,
        help="Step identifier (e.g., 02-03); recorded as a Step-Id trailer",
    )
    parser.add_argument(
        "--message",
        required=True,
        help="Commit message subject/body (Step-Id trailer appended if absent)",
    )
    return parser


def _git(
    repo: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a git command in *repo*, capturing output (never raises on failure)."""
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _with_step_id_trailer(message: str, step_id: str) -> str:
    """Append a ``Step-Id:`` trailer unless the message already carries one."""
    if "Step-Id:" in message:
        return message
    return f"{message}\n\nStep-Id: {step_id}"


def _commit_owned_locked(
    repo: Path, owned_paths: list[str], message: str
) -> tuple[int, str]:
    """Commit only *owned_paths* via a temporary scoped index, under a lock.

    Returns ``(exit_code, error_message)``. The lock (``.nwave/des/commit.lock``)
    serializes concurrent callers. The commit is built from a private index
    (``GIT_INDEX_FILE``) seeded with HEAD plus the owned paths only, so foreign
    or hook-staged files cannot land. The shared index/working tree are
    untouched apart from resyncing the owned paths to the new HEAD.
    """
    lock_path = repo / ".nwave" / "des" / "commit.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with open(lock_path, "w", encoding="utf-8") as lock_handle:
        if _HAS_FCNTL:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            return _commit_via_scoped_index(repo, owned_paths, message)
        finally:
            if _HAS_FCNTL:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _commit_via_scoped_index(
    repo: Path, owned_paths: list[str], message: str
) -> tuple[int, str]:
    """Commit owned paths through a private temporary index (lock already held)."""
    # A private index file, seeded from HEAD, that only the owned paths are
    # staged into — keeps foreign/hook-staged files out of the commit by
    # construction. mkstemp creates it; unlink so git read-tree writes it fresh.
    fd, tmp_index = tempfile.mkstemp(prefix="des-commit-", suffix=".index")
    os.close(fd)
    Path(tmp_index).unlink()
    env = {**os.environ, "GIT_INDEX_FILE": tmp_index}
    try:
        seed = _git(repo, "read-tree", "HEAD", env=env)
        if seed.returncode != 0:
            return 1, f"git read-tree failed: {seed.stderr.strip()}"

        # -A stages additions, modifications AND deletions for the owned paths.
        add = _git(repo, "add", "-A", "--", *owned_paths, env=env)
        if add.returncode != 0:
            return 1, f"git add failed: {add.stderr.strip()}"

        # Nothing changed in the owned paths relative to HEAD → nothing to commit.
        if _git(repo, "diff", "--cached", "--quiet", env=env).returncode == 0:
            return 1, "no changes in owned paths to commit"

        commit = _git(repo, "commit", "--no-verify", "-m", message, env=env)
        if commit.returncode != 0:
            detail = (commit.stderr or commit.stdout).strip()
            return 1, f"git commit failed: {detail}"
    finally:
        Path(tmp_index).unlink(missing_ok=True)

    # Resync the shared index for owned paths to the new HEAD so they show clean;
    # any foreign staged work in the shared index is left untouched.
    _git(repo, "reset", "-q", "--", *owned_paths)
    return 0, ""


def main(argv: list[str] | None = None) -> int:
    """Entry point for the des-commit CLI tool.

    Args:
        argv: Command-line arguments. Uses sys.argv[1:] if None.

    Returns:
        Exit code: 0=success, 1=git error, 2=usage error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    repo = Path(args.repo_dir)
    if not (repo / ".git").exists():
        print(f"Error: not a git repository: {repo}")
        return 1

    owned_paths: list[str] = list(args.owned_paths)
    message = _with_step_id_trailer(args.message, args.step_id)

    exit_code, error = _commit_owned_locked(repo, owned_paths, message)
    if exit_code != 0:
        print(f"Error: {error}")
        return exit_code

    print(f"Committed owned file(s) for step {args.step_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
