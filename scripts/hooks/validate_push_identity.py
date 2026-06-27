"""pre-push hook: validate author/committer email on all commits being pushed.

Reads ref update lines on stdin
(``<local-ref> <local-sha> <remote-ref> <remote-sha>``), resolves the commit
range (handling the zero-SHA new-branch case by validating against the push
target's default branch via ``_resolve_default_base()``, with a fail-closed
fallback to every commit reachable from the pushed tip), and
validates every commit's author + committer NAME *and* email through the shared
validator core. Returns non-zero if any commit in the range carries a placeholder
identity — catching ``--no-verify`` commits and commits made before the
pre-commit hook was installed (research §2.5, §2.7).

The push gate backstops the same threats as the authoritative CI gate, so it
validates the NAME field too, not emails alone (R3-F1): a placeholder name
(``Test`` / ``User``) with a valid email is still refused. The ``git log`` format
is NUL/control separated (records on NUL via ``-z``; the five fields on the 0x1F
unit separator, which cannot appear inside a git ident) so a TAB or newline in a
name can never misalign the column split and hide a placeholder behind a
clean-looking fragment.

Reuses the validator core from ``validate_author_identity.py`` (DRY: one
denylist, one name rule). Design source:
``docs/analysis/commit-author-validation-research.md`` §2.5.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys


# C1: self-locate the repo root so the sibling-module import resolves regardless
# of cwd or install shape. In a clean CI checkout (no `uv sync` / PYTHONPATH) the
# `scripts` package is not on sys.path, so this bootstrap is what lets the gate
# run at all — without it the script crashes ModuleNotFoundError before
# validating anything. parents[2] of scripts/hooks/x.py is the repo root.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from scripts.hooks.validate_author_identity import (
    is_valid_author_email,
    validate_name_field,
)


ZERO_SHA = "0" * 40

# R3-F1 robust range format: records separated by NUL (``-z``); the five fields
# separated by the 0x1F ASCII unit separator, which cannot appear inside a git
# ident — so a TAB or newline in a name can never misalign the column split.
_UNIT_SEP = "\x1f"
_RECORD_SEP = "\x00"
_RANGE_FORMAT = "%H%x1f%an%x1f%ae%x1f%cn%x1f%ce"

# Each parsed record: (sha, author_name, author_email, committer_name,
# committer_email).
Record = tuple[str, str, str, str, str]

# M1: candidate refs for the push target's default branch, tried in order. The
# new-branch range is validated relative to the default branch — NOT subtracted
# against `--remotes` (which would exclude a placeholder commit merely because it
# is reachable from SOME other remote ref, letting it be introduced into this
# branch's history unchecked). If none of these resolve, the range falls back to
# every commit reachable from the pushed tip — fail-closed: validate more, never
# skip.
_DEFAULT_BRANCH_CANDIDATES = (
    "refs/remotes/origin/HEAD",
    "refs/remotes/origin/master",
    "refs/remotes/origin/main",
)


def _resolve_default_base() -> str | None:
    """Return a resolvable default-branch ref for the push target, or ``None``.

    Tries the remote's symbolic ``origin/HEAD`` first, then the conventional
    ``origin/master`` / ``origin/main``. Returns the first that resolves to a
    commit; ``None`` if none do (caller then validates the whole reachable set —
    fail-closed).
    """
    for ref in _DEFAULT_BRANCH_CANDIDATES:
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode == 0 and probe.stdout.strip():
            return ref
    return None


def commits_in_range(local_sha: str, remote_sha: str) -> list[Record]:
    """Return ``(sha, author_name, author_email, committer_name, committer_email)``.

    One NUL-separated record per commit in the range. For an existing upstream the
    range is ``remote_sha..local_sha``. For a new branch (remote object name is
    the zero SHA) the range is validated relative to the push target's default
    branch (``<default>..local_sha``) — and if the default branch cannot be
    resolved, every commit reachable from ``local_sha`` is validated (fail-closed).
    This avoids the ``--not --remotes`` over-exclusion bug where a placeholder
    commit already on another remote ref escaped the gate (adversarial review M1,
    research §2.5).

    R3-F1: author + committer NAMES are read (``%an``/``%cn``) and validated
    alongside the emails. The NUL/unit-separated format keeps every field
    correctly placed even when a name carries a TAB or newline — superseding the
    earlier ``%H\\t%ae\\t%ce`` format that dropped the name to dodge tab
    misalignment (M2); the control-separated record is tab-proof, so the name can
    be validated without re-introducing that bug.
    """
    if remote_sha == ZERO_SHA:
        default_base = _resolve_default_base()
        if default_base is not None:
            range_args = [f"{default_base}..{local_sha}"]
        else:
            range_args = [local_sha]
    else:
        range_args = [f"{remote_sha}..{local_sha}"]

    result = subprocess.run(
        ["git", "log", "-z", *range_args, f"--format={_RANGE_FORMAT}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return _parse_records(result.stdout)


def _parse_records(stdout: str) -> list[Record]:
    """Split NUL-separated records into clean 5-field tuples, dropping malformed.

    Defensive: a record that does not split into exactly five unit-separated
    fields is dropped rather than mis-unpacked downstream.
    """
    records: list[Record] = []
    for chunk in stdout.split(_RECORD_SEP):
        if not chunk:
            continue
        fields = chunk.split(_UNIT_SEP)
        if len(fields) == 5:
            records.append((fields[0], fields[1], fields[2], fields[3], fields[4]))
    return records


def main() -> int:
    """pre-push entry: validate every commit in the pushed range."""
    errors = []
    for line in sys.stdin:
        parts = line.strip().split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = parts
        if local_sha == ZERO_SHA:
            continue  # deletion push — nothing to validate

        for (
            sha,
            author_name,
            author_email,
            committer_name,
            committer_email,
        ) in commits_in_range(local_sha, remote_sha):
            for role, name in [
                ("author", author_name),
                ("committer", committer_name),
            ]:
                ok, reason = validate_name_field(name)
                if not ok:
                    errors.append(
                        f"{sha[:8]} {role} name rejected: {reason} ({name!r})"
                    )
            for role, email in [
                ("author", author_email),
                ("committer", committer_email),
            ]:
                ok, reason = is_valid_author_email(email)
                if not ok:
                    errors.append(
                        f"{sha[:8]} {role} email rejected: {reason} ({email!r})"
                    )

    if errors:
        print("PUSH REJECTED — commits with invalid identity:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
