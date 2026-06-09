"""des-run-contract-gate -- the single canonical ATDD-pure contract gate.

slice-14 of the atdd-pure-roadmap-free-rollout (RCA Gate 2, closes Branch B).

`run_contract_gate.py` IS the canonical ATDD-pure commit gate. It has two
roles, so the terminating crafter run, the pre-commit wrapper, and CI all
invoke ONE definition -- verification scope can no longer be a proper subset
of the contract:

  (a) RUN -- the default mode runs
      `pytest -m "unit or integration or acceptance"` over the WHOLE tree
      (the exact pre-push scope, NOT a crafter-picked subset) and emits a
      machine-readable pass/fail plus a `gate_scope_digest`.
  (b) DIGEST / VERIFY -- `--collect-only --print-digest` derives the
      `gate_scope_digest` without running the suite; `--verify-gate-scope`
      reads a commit's `Gate-Scope:` trailer and compares it against a fresh
      `--collect-only` digest, so the `G_COMMIT` exit gate can refuse a commit
      whose verification scope does not match the contract.

The `gate_scope_digest` is the SHA-256 of the sorted, newline-joined set of
collected test node-ids -- a stable fingerprint of "which tests the contract
gate covers".

stdlib + pytest only.

Exit codes:
    0 = the requested role succeeded (suite passed / digest printed /
        gate-scope verified).
    1 = the contract suite FAILED, OR `--verify-gate-scope` found the
        commit's `Gate-Scope:` digest absent or mismatching.
    2 = malformed input (repo / commit unreadable, collection failed).

Reference: docs/feature/atdd-pure-roadmap-free-rollout/feature-delta.md
           # slice-14 design note (E2).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


# The contract gate scope -- the exact pre-push marker expression
# (.pre-commit-config.yaml). NOT a crafter-picked subset.
_CONTRACT_MARKER = "unit or integration or acceptance"

_GATE_SCOPE_TRAILER_RE = re.compile(r"^Gate-Scope:\s*([0-9a-f]{64})\s*$")


def _emit(payload: dict[str, object]) -> None:
    """Print exactly one single-line JSON object."""
    print(json.dumps(payload))


def _collect_node_ids(repo: Path) -> list[str]:
    """Collect the contract suite's test node-ids without running them.

    Runs `pytest --collect-only -q` with the contract marker so the digest
    fingerprints exactly the pre-push contract scope.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            _CONTRACT_MARKER,
            "--collect-only",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in (0, 5):
        # 0 = collected, 5 = no tests collected. Anything else is a
        # collection error -- malformed input.
        raise _CollectionError(completed.stderr or completed.stdout)
    node_ids = [
        line.strip()
        for line in completed.stdout.splitlines()
        if "::" in line and not line.startswith(" ")
    ]
    return sorted(set(node_ids))


class _CollectionError(Exception):
    """pytest collection failed -- the contract scope cannot be derived."""


def compute_gate_scope_digest(node_ids: list[str]) -> str:
    """Return the SHA-256 digest of the sorted set of collected node-ids."""
    joined = "\n".join(sorted(set(node_ids)))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def gate_scope_digest(repo: Path) -> str:
    """Derive a fresh `gate_scope_digest` for ``repo``'s contract suite."""
    return compute_gate_scope_digest(_collect_node_ids(repo))


def extract_gate_scope(commit_message: str) -> str | None:
    """Return the digest carried by a `Gate-Scope:` commit trailer, if any."""
    for line in commit_message.splitlines():
        match = _GATE_SCOPE_TRAILER_RE.match(line.strip())
        if match:
            return match.group(1)
    return None


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


def _run_contract_suite(repo: Path) -> int:
    """Run the whole-tree contract suite; return its pytest exit code."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            _CONTRACT_MARKER,
            "-p",
            "no:cacheprovider",
        ],
        cwd=repo,
    )
    return completed.returncode


def _mode_print_digest(repo: Path) -> int:
    """`--collect-only --print-digest`: emit a fresh digest, run nothing."""
    try:
        digest = gate_scope_digest(repo)
    except _CollectionError as exc:
        _emit({"event": "MalformedInput", "error": f"collection failed: {exc}"})
        return 2
    # Plain stdout so callers can capture the bare digest (composition does
    # `.strip()` on it); the JSON event goes to stderr for machine readers.
    print(digest)
    print(
        json.dumps({"event": "GateScopeDigest", "gate_scope_digest": digest}),
        file=sys.stderr,
    )
    return 0


def _mode_verify_gate_scope(repo: Path, commit: str) -> int:
    """`--verify-gate-scope`: compare the commit's digest to a fresh one."""
    try:
        commit_message = _git(repo, "log", "-1", "--format=%B", commit)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        _emit(
            {
                "event": "MalformedInput",
                "error": f"cannot read commit {commit!r}: {exc}",
            }
        )
        return 2

    declared = extract_gate_scope(commit_message)
    try:
        fresh = gate_scope_digest(repo)
    except _CollectionError as exc:
        _emit({"event": "MalformedInput", "error": f"collection failed: {exc}"})
        return 2

    if declared is None:
        _emit(
            {
                "event": "GateScopeUnverified",
                "commit": commit,
                "reason": "absent",
                "error": (
                    "commit carries no Gate-Scope: trailer -- the contract "
                    "gate scope is unverified"
                ),
            }
        )
        return 1

    if declared != fresh:
        _emit(
            {
                "event": "GateScopeUnverified",
                "commit": commit,
                "reason": "mismatch",
                "declared_digest": declared,
                "fresh_digest": fresh,
                "error": (
                    "commit Gate-Scope: digest does not match a fresh "
                    "run_contract_gate --collect-only digest -- the "
                    "terminating run was narrower than the contract"
                ),
            }
        )
        return 1

    _emit(
        {
            "event": "GateScopeVerified",
            "commit": commit,
            "gate_scope_digest": fresh,
        }
    )
    return 0


def _mode_run_suite(repo: Path) -> int:
    """Default mode: run the whole-tree contract suite + emit a digest."""
    try:
        digest = gate_scope_digest(repo)
    except _CollectionError as exc:
        _emit({"event": "MalformedInput", "error": f"collection failed: {exc}"})
        return 2
    suite_code = _run_contract_suite(repo)
    passed = suite_code == 0
    _emit(
        {
            "event": "ContractGateResult",
            "passed": passed,
            "pytest_exit_code": suite_code,
            "gate_scope_digest": digest,
        }
    )
    return 0 if passed else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="des-run-contract-gate",
        description="The canonical ATDD-pure contract gate (run / digest / verify).",
    )
    parser.add_argument(
        "--repo", required=True, help="Path to the git repository / project root."
    )
    parser.add_argument(
        "--commit",
        help="Commit-ish for --verify-gate-scope (e.g. HEAD).",
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Derive the gate-scope digest without running the suite.",
    )
    parser.add_argument(
        "--print-digest",
        action="store_true",
        help="Print the gate-scope digest to stdout (use with --collect-only).",
    )
    parser.add_argument(
        "--verify-gate-scope",
        action="store_true",
        help="Verify --commit's Gate-Scope: trailer against a fresh digest.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the canonical ATDD-pure contract gate in the requested role."""
    args = _build_parser().parse_args(argv)
    repo = Path(args.repo)

    if args.verify_gate_scope:
        if not args.commit:
            _emit(
                {
                    "event": "MalformedInput",
                    "error": "--verify-gate-scope requires --commit",
                }
            )
            return 2
        return _mode_verify_gate_scope(repo, args.commit)

    if args.collect_only or args.print_digest:
        return _mode_print_digest(repo)

    return _mode_run_suite(repo)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
