"""Discover other ``execution-log.json`` files within a git worktree (issue #79).

"Other" means anywhere under the git worktree root at ANY depth — not only the
directories adjacent to the target. The single path excluded is the log inside
the target directory itself, which the caller already knows about.

``--project-dir`` is resolved implicitly against the *process* CWD by every DES
log CLI. When an agent ``cd``s into a monorepo subdirectory mid-DELIVER, the same
relative string denotes a different absolute directory, and the log silently
forks into two divergent files.

This module supplies the evidence for a LOUD failure rather than a silent fork:
it locates the git worktree root of a target directory and enumerates the
``execution-log.json`` files already present under it. Re-anchoring relative
paths to the worktree root is deliberately NOT done here — that would change
behaviour for callers who legitimately pass a subdirectory-relative path.

Every function here returns a ``Result``. A scan that could not run is a
``Failure`` carrying the reason, never an empty ``Success``: this module exists
because a silent failure hid a real problem, so "found nothing" and "could not
look" must not be the same value. Callers are expected to surface the reason.

Worktree resolution uses ``git rev-parse --show-toplevel``, which in a linked
worktree returns that worktree's own root (not the main checkout), matching the
containment boundary DELIVER runs in.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from des.domain.result import Failure, Result, Success


LOG_FILENAME = "execution-log.json"

#: Upper bound on REPORTED logs — the diagnostic needs a name, not a census. The
#: scan itself is unbounded: every candidate is enumerated and matched, and only
#: the sorted result list is truncated to this many entries.
MAX_REPORTED_LOGS = 10

_GIT_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class WorktreeLog:
    """One ``execution-log.json`` found under the worktree root.

    ``feature_id`` is the id recorded inside the file. ``unreadable_reason`` is
    set when the file exists but could not be parsed — such a log is REPORTED,
    never filtered away, because a corrupt audit trail is a louder problem than
    a missing one, not a quieter one.
    """

    path: Path
    feature_id: str | None
    unreadable_reason: str | None = None

    @property
    def is_readable(self) -> bool:
        return self.unreadable_reason is None


def _run_git(args: list[str], cwd: Path) -> Result[str, str]:
    """Run a git command, returning its stdout or a reason the run failed.

    The three distinguishable failures — git missing, git erroring, git hanging
    — produce three different reasons, because "git is not installed" and "this
    is not a repository" call for different actions from the operator.
    """
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return Failure("git executable not found on PATH")
    except subprocess.TimeoutExpired:
        return Failure(
            f"git {args[0]} timed out after {_GIT_TIMEOUT_SECONDS}s in {cwd}"
        )
    except OSError as exc:
        return Failure(f"could not run git in {cwd}: {exc}")

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip() or "no output"
        return Failure(f"git {args[0]} exited {completed.returncode}: {detail}")

    return Success(completed.stdout)


def _nearest_existing_dir(start: Path) -> Path | None:
    """Return *start* or its closest existing ancestor directory."""
    candidate = start if start.is_dir() else start.parent
    for path in [candidate, *candidate.parents]:
        if path.is_dir():
            return path
    return None


def worktree_root(start: Path) -> Result[Path, str]:
    """Return the git worktree root containing *start*, or why it is unknown."""
    probe = _nearest_existing_dir(start.absolute())
    if probe is None:
        return Failure(f"no existing directory on the path to {start}")

    result = _run_git(["rev-parse", "--show-toplevel"], cwd=probe)
    if isinstance(result, Failure):
        return result

    raw = result.value.strip()
    if not raw:
        return Failure(f"git rev-parse returned no toplevel for {probe}")
    return Success(Path(raw).resolve())


def _read_feature_id(log_path: Path) -> tuple[str | None, str | None]:
    """Return ``(feature_id, unreadable_reason)`` for *log_path*.

    A file that cannot be read or parsed yields a reason rather than being
    silently treated as a log for some other feature.
    """
    try:
        raw = log_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"unreadable: {exc}"
    except UnicodeDecodeError as exc:
        return None, f"not valid UTF-8: {exc}"

    try:
        data = json.loads(raw)
    except ValueError as exc:
        return None, f"not valid JSON: {exc}"

    if not isinstance(data, dict):
        return None, f"top level is {type(data).__name__}, expected object"

    feature_id = data.get("feature_id")
    if feature_id is None:
        return None, None
    if not isinstance(feature_id, str):
        return None, f"feature_id is {type(feature_id).__name__}, expected string"
    return feature_id, None


def _list_candidate_logs(root: Path) -> Result[list[Path], str]:
    """Return every ``execution-log.json`` git accounts for under *root*.

    Enumeration is delegated to ``git ls-files`` rather than walking the tree
    against a hard-coded set of directory names to skip. That list would be a
    second, worse copy of the repository's own ``.gitignore``: it would miss
    whatever a given project ignores (``.direnv``, ``.turbo``, a vendored SDK)
    and would need editing every time a new build tool appeared.

    The pathspec uses ``:(glob)`` magic so ``**/`` matches whole path segments.
    A plain ``*execution-log.json`` would be a suffix match and would also
    select ``my-execution-log.json``.

    ``--cached --others --exclude-standard`` covers tracked files plus untracked
    ones git would not ignore. A log inside an ignored directory is deliberately
    not reported: it is not part of the audit trail this diagnostic protects.
    """
    result = _run_git(
        [
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            f":(glob)**/{LOG_FILENAME}",
            f":(glob){LOG_FILENAME}",
        ],
        cwd=root,
    )
    if isinstance(result, Failure):
        return result

    return Success(
        [
            (root / relative).resolve()
            for relative in result.value.split("\0")
            if relative
        ]
    )


def find_other_logs_in_worktree(
    target_dir: Path,
    feature_id: str | None = None,
    limit: int = MAX_REPORTED_LOGS,
) -> Result[list[WorktreeLog], str]:
    """Return ``execution-log.json`` files under *target_dir*'s worktree root.

    The log directly inside *target_dir* is excluded — the caller already knows
    about that one; what matters is a log living somewhere ELSE in the same
    worktree.

    Args:
        target_dir: The ``--project-dir`` the caller resolved.
        feature_id: When given, logs recording a DIFFERENT feature id are
            filtered out. Logs that could not be read are always kept, since a
            corrupt log cannot be ruled out as the fork.
        limit: Maximum number of entries returned, applied AFTER sorting so the
            result is the deterministic first *limit* paths rather than an
            arbitrary slice of git's enumeration order.

    Returns:
        ``Success`` with the matching logs (possibly empty — genuinely none
        found), or ``Failure`` with the reason the scan could not be performed.
    """
    root_result = worktree_root(target_dir)
    if isinstance(root_result, Failure):
        return Failure(f"cannot determine the worktree root: {root_result.error}")

    candidates_result = _list_candidate_logs(root_result.value)
    if isinstance(candidates_result, Failure):
        return Failure(f"cannot enumerate logs: {candidates_result.error}")

    excluded = target_dir.absolute().resolve()
    matches: list[WorktreeLog] = []

    for log_path in sorted(candidates_result.value):
        if log_path.parent == excluded:
            continue
        found_id, unreadable = _read_feature_id(log_path)
        if unreadable is None and feature_id is not None and found_id != feature_id:
            continue
        matches.append(
            WorktreeLog(
                path=log_path, feature_id=found_id, unreadable_reason=unreadable
            )
        )

    return Success(matches[:limit])


def describe_other_logs(result: Result[list[WorktreeLog], str]) -> list[str]:
    """Render *result* as operator-facing diagnostic lines.

    A failed scan produces a line saying the scan failed and why — never
    silence, which would read as "no other logs exist".
    """
    if isinstance(result, Failure):
        return [f"  (could not scan for other execution logs: {result.error})"]

    if not result.value:
        return []

    lines = []
    for entry in result.value:
        if entry.is_readable:
            suffix = f" (feature_id: {entry.feature_id})" if entry.feature_id else ""
        else:
            suffix = f" (WARNING — {entry.unreadable_reason})"
        lines.append(f"  {entry.path}{suffix}")
    return lines
