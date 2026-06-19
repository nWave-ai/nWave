"""Generic HMAC-SHA256 commit-trailer verifier CLI.

Methodology-agnostic verifier for ``Reviewed-by: <agent>:<hmac-sha256-hex>``
trailers embedded in git commit messages. Reconstructs the canonical verdict
JSON from the trailer, recomputes the HMAC-SHA256 using a signing key (env
first, file fallback), and constant-time-compares against the trailer hex.

Invoked by (not specific to): DEV-side pre-push hooks, DISTILL/DELIVER
command flows, and the SF (nwave-software-factory) sequencer. The CLI knows
nothing about wave names, phase counts, or workflow shape — it verifies
HMAC integrity of opaque verdict payloads only.

Canonical verdict JSON shape (input to HMAC):
    {"findings_summary": [...], "reviewer_agent_id": "...",
     "timestamp": "...", "verdict": "..."}
Serialised with ``json.dumps(..., sort_keys=True,
separators=(",", ":")).encode("utf-8")``.

Trailer shape (one or more per commit):
    ``Reviewed-by: <agent-id>:<64-hex-sha256>``

Exit codes:
    0 = all trailers verify (or no trailers + not --strict)
    4 = hash mismatch (tampering detected)
    5 = missing key (env unset + file absent)
    6 = malformed trailer OR --strict + no trailers
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_KEY_ENV = "NWAVE_REVIEWER_SIGNING_KEY"
DEFAULT_KEY_FILE = ".nwave/secrets/reviewer-signing.key"
TRAILER_RE = re.compile(r"^Reviewed-by:\s*([^:\s]+):([0-9a-fA-F]{64})\s*$")
VERDICT_RE = re.compile(
    r"^Verdict-Payload:\s*(\{.*\})\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Trailer:
    """Parsed ``Reviewed-by:`` trailer."""

    agent_id: str
    hash_hex: str


def extract_trailers(commit_message: str) -> list[Trailer]:
    """Extract ``Reviewed-by:`` trailers from commit message body.

    Returns trailers in source order. Lines matching the prefix
    ``Reviewed-by:`` but failing the canonical shape raise ``ValueError``
    so the caller can surface a malformed-trailer exit (code 6).
    """
    trailers: list[Trailer] = []
    for line in commit_message.splitlines():
        if not line.startswith("Reviewed-by:"):
            continue
        match = TRAILER_RE.match(line)
        if match is None:
            raise ValueError(f"malformed Reviewed-by trailer: {line!r}")
        trailers.append(Trailer(agent_id=match.group(1), hash_hex=match.group(2)))
    return trailers


def canonical_verdict_json(verdict: dict[str, object]) -> bytes:
    """Serialise a verdict dict to canonical JSON bytes.

    Canonical form: sorted keys, no whitespace, UTF-8. Required fields:
    ``verdict``, ``timestamp``, ``reviewer_agent_id``, ``findings_summary``.
    Extra fields are rejected to keep the HMAC input bit-stable across
    callers.
    """
    required = {"verdict", "timestamp", "reviewer_agent_id", "findings_summary"}
    keys = set(verdict.keys())
    if keys != required:
        missing = required - keys
        extra = keys - required
        raise ValueError(
            f"verdict shape mismatch: missing={sorted(missing)} extra={sorted(extra)}"
        )
    return json.dumps(verdict, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_verdict_hash(verdict: dict[str, object], key: bytes) -> str:
    """Compute HMAC-SHA256 over ``canonical_verdict_json(verdict)`` as hex."""
    return hmac.new(key, canonical_verdict_json(verdict), hashlib.sha256).hexdigest()


def verify_trailer(trailer: Trailer, verdict: dict[str, object], key: bytes) -> bool:
    """Constant-time-compare expected HMAC vs trailer hex."""
    expected = compute_verdict_hash(verdict, key)
    return hmac.compare_digest(expected, trailer.hash_hex)


def _load_key(env_var: str, key_file: Path) -> bytes | None:
    """Load HMAC signing key. Env first, file fallback. None if neither."""
    env_value = os.environ.get(env_var)
    if env_value:
        return env_value.encode("utf-8")
    if key_file.exists():
        return key_file.read_bytes().strip()
    return None


def _extract_verdicts(commit_message: str) -> list[dict[str, object]]:
    """Extract one ``Verdict-Payload:`` JSON dict per trailer (source order)."""
    payloads: list[dict[str, object]] = []
    for match in VERDICT_RE.finditer(commit_message):
        try:
            obj = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed Verdict-Payload JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError("Verdict-Payload must be a JSON object")
        payloads.append(obj)
    return payloads


def _get_commit_message(commit_sha: str) -> str:
    """Read commit body via ``git show -s --format=%B``."""
    result = subprocess.run(
        ["git", "show", "-s", "--format=%B", commit_sha],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git show failed: {result.stderr.strip()}")
    return result.stdout


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="des-verify-commit-trailers",
        description=(
            "Generic HMAC-SHA256 commit-trailer verifier. Verifies "
            "Reviewed-by: <agent>:<hmac-hex> trailers against "
            "Verdict-Payload: {...} JSON in the same commit body."
        ),
        epilog=(
            "Exit codes: 0 ok | 4 hash mismatch | 5 missing key | "
            "6 malformed trailer or --strict + no trailers."
        ),
    )
    parser.add_argument("--commit", default="HEAD", help="target commit SHA")
    parser.add_argument(
        "--key-source",
        choices=("env", "file"),
        default="env",
        help="primary key source (the other is always used as fallback)",
    )
    parser.add_argument("--key-env", default=DEFAULT_KEY_ENV)
    parser.add_argument("--key-file", type=Path, default=Path(DEFAULT_KEY_FILE))
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 6 if commit has no trailers (default: exit 0)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))

    try:
        message = _get_commit_message(args.commit)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 6

    try:
        trailers = extract_trailers(message)
        verdicts = _extract_verdicts(message)
    except ValueError as exc:
        print(f"MALFORMED: {exc}", file=sys.stderr)
        return 6

    if not trailers:
        if args.strict:
            print("STRICT: no Reviewed-by trailers found", file=sys.stderr)
            return 6
        print("OK: no Reviewed-by trailers (non-strict mode)")
        return 0

    if len(verdicts) != len(trailers):
        print(
            f"MALFORMED: {len(trailers)} trailer(s) but "
            f"{len(verdicts)} Verdict-Payload(s)",
            file=sys.stderr,
        )
        return 6

    # key_source toggles which source is tried first; both are tried.
    if args.key_source == "env":
        key = _load_key(args.key_env, args.key_file)
    else:
        env_save = os.environ.pop(args.key_env, None)
        try:
            key = _load_key(args.key_env, args.key_file) or (
                env_save.encode("utf-8") if env_save else None
            )
        finally:
            if env_save is not None:
                os.environ[args.key_env] = env_save

    if key is None:
        print(
            f"MISSING KEY: env {args.key_env} unset and {args.key_file} absent",
            file=sys.stderr,
        )
        return 5

    for trailer, verdict in zip(trailers, verdicts, strict=True):
        try:
            ok = verify_trailer(trailer, verdict, key)
        except ValueError as exc:
            print(f"MALFORMED: {exc}", file=sys.stderr)
            return 6
        if not ok:
            print(
                f"MISMATCH: trailer for {trailer.agent_id} failed HMAC verify",
                file=sys.stderr,
            )
            return 4

    print(f"OK: {len(trailers)} trailer(s) verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
