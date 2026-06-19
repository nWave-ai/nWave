"""des-verify-slice-commit-completeness -- slice-commit completeness exit gate.

slice-14 of the atdd-pure-roadmap-free-rollout. The slice-commit completeness
exit gate (RCA Gate 1, closes Branch A): given a commit carrying a `Slice-Id:`
trailer, assert every scenario tagged `@slice-NN` for that slice lives in a
git-tracked `.feature` file that is EITHER present in this commit OR already
tracked and unmodified by this slice.

Pure-function: reads `git show --name-only` + `.feature` files, returns a
verdict (exit code + JSON payload), performs NO filesystem mutation.

MUST be stdlib-only (no `import yaml`) per the DES-bundle contract -- the very
contract the slice-01 regression violated. Every import below is stdlib.

A commit MAY carry MULTIPLE `Slice-Id:` trailer lines -- the whole-tree-stashing
pre-commit hook forces interleaved multi-slice work to batch into ONE commit,
which then lists every slice it covers as a separate `Slice-Id:` trailer (see
friction F-07, docs/analysis/atdd-pure-dogfooding-friction-2026-05-20.md). The
gate verifies slice-commit completeness for EVERY listed slice and certifies
the commit only when every listed slice is complete; a single-`Slice-Id:`
commit is the one-element case of the same logic.

Exit codes:
    0 = complete -- for every listed slice, every `@slice-NN` `.feature` file
        is in the commit or already tracked-and-unmodified by this commit.
    1 = incomplete -- one or more listed slices are missing `@slice-NN`
        `.feature` files from the commit; the JSON payload names them.
    2 = malformed input -- no `Slice-Id:` trailer, or repo / commit unreadable.

Reference: docs/feature/atdd-pure-roadmap-free-rollout/feature-delta.md
           # slice-14 design note (E1).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


_SLICE_ID_TRAILER_RE = re.compile(r"^(?:Slice-Id|Step-Id):\s*(slice-\d+)\s*$")
_SLICE_TAG_RE = re.compile(r"@(slice-\d+)\b")


def _git(repo: Path, *args: str) -> str:
    """Run a git command in ``repo`` and return stdout (raises on non-zero)."""
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def extract_slice_id(commit_message: str) -> str | None:
    """Return the FIRST `slice-NN` carried by a `Slice-Id:`/`Step-Id:` trailer.

    Retained for backward compatibility; prefer ``extract_slice_ids`` which
    returns every listed slice (the F-07 multi-trailer shape).
    """
    slice_ids = extract_slice_ids(commit_message)
    return slice_ids[0] if slice_ids else None


def extract_slice_ids(commit_message: str) -> list[str]:
    """Return every `slice-NN` carried by a `Slice-Id:`/`Step-Id:` trailer.

    A batched commit lists each slice it covers as a separate trailer line.
    Order of first appearance is preserved; duplicates are collapsed so a
    repeated trailer does not double-verify the same slice.
    """
    ordered: list[str] = []
    for line in commit_message.splitlines():
        match = _SLICE_ID_TRAILER_RE.match(line.strip())
        if match:
            slice_id = match.group(1)
            if slice_id not in ordered:
                ordered.append(slice_id)
    return ordered


def feature_files_for_slice(repo: Path, slice_id: str) -> list[str]:
    """Return repo-relative paths of `.feature` files tagging the slice.

    A `.feature` file belongs to the slice when any of its scenarios carry the
    `@slice-NN` tag matching ``slice_id``. The working tree is walked, NOT just
    `git ls-files` -- an authored-but-never-committed AT file is untracked yet
    is exactly the RCA Branch-A defect this gate must catch. A file the slice
    authored on disk but kept out of every commit MUST be reported missing.
    """
    matched: list[str] = []
    for path in sorted(repo.rglob("*.feature")):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if slice_id in _SLICE_TAG_RE.findall(text):
            matched.append(str(path.relative_to(repo)))
    return sorted(matched)


def files_in_commit(repo: Path, commit: str) -> set[str]:
    """Return the set of repo-relative paths touched by ``commit``."""
    output = _git(repo, "show", "--name-only", "--pretty=format:", commit)
    return {line for line in output.splitlines() if line}


def missing_at_files(repo: Path, commit: str, slice_id: str) -> list[str]:
    """Return `.feature` AT files for the slice that the commit fails to carry.

    A file is complete when it is present in this commit. A file already
    tracked before this commit AND unmodified by it is also complete -- the
    commit need not re-touch ATs delivered by an earlier slice commit. The
    incomplete case is the RCA Branch-A defect: an AT file the slice authored
    but never persisted into any commit.
    """
    at_files = feature_files_for_slice(repo, slice_id)
    in_commit = files_in_commit(repo, commit)
    missing: list[str] = []
    for rel_path in at_files:
        if rel_path in in_commit:
            continue
        if _tracked_before_commit(repo, commit, rel_path):
            continue
        missing.append(rel_path)
    return sorted(missing)


def _tracked_before_commit(repo: Path, commit: str, rel_path: str) -> bool:
    """True iff ``rel_path`` existed as a tracked file in ``commit``'s parent."""
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}~1:{rel_path}"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="des-verify-slice-commit-completeness",
        description="Verify a slice commit carries the slice's .feature AT files.",
    )
    parser.add_argument(
        "--repo", required=True, help="Path to the git repository to inspect."
    )
    parser.add_argument(
        "--commit",
        required=True,
        help="The commit-ish to inspect (e.g. HEAD).",
    )
    return parser


def _emit(payload: dict[str, object]) -> None:
    """Print exactly one single-line JSON object."""
    print(json.dumps(payload))


def main(argv: list[str] | None = None) -> int:
    """Verify a slice commit contains the slice's `.feature` AT files."""
    args = _build_parser().parse_args(argv)
    repo = Path(args.repo)

    try:
        commit_message = _git(repo, "log", "-1", "--format=%B", args.commit)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        _emit(
            {
                "event": "MalformedInput",
                "error": f"cannot read commit {args.commit!r}: {exc}",
            }
        )
        return 2

    slice_ids = extract_slice_ids(commit_message)
    if not slice_ids:
        _emit(
            {
                "event": "MalformedInput",
                "error": "commit carries no Slice-Id:/Step-Id: trailer",
            }
        )
        return 2

    try:
        missing_by_slice = {
            slice_id: missing_at_files(repo, args.commit, slice_id)
            for slice_id in slice_ids
        }
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        _emit(
            {
                "event": "MalformedInput",
                "error": f"cannot inspect repository: {exc}",
            }
        )
        return 2

    deficient = {
        slice_id: missing for slice_id, missing in missing_by_slice.items() if missing
    }
    if deficient:
        _emit(
            {
                "event": "SliceCommitIncomplete",
                "slice_ids": slice_ids,
                "commit": args.commit,
                "missing_feature_files_by_slice": deficient,
                "error": "; ".join(
                    f"slice {slice_id} commit is missing "
                    f"{len(missing)} .feature AT file(s): " + ", ".join(missing)
                    for slice_id, missing in deficient.items()
                ),
            }
        )
        return 1

    _emit(
        {
            "event": "SliceCommitComplete",
            "slice_ids": slice_ids,
            "commit": args.commit,
        }
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
