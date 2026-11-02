"""`nwave-ai outcomes` subcommand entry — register / check.

Driving adapter: argparse-based CLI. Translates argv into application
service calls (RegistryService.register, CollisionDetector.check) and maps
results to exit codes:

    register:    0 success
                 2 refused — checked and rejected (invalid, or duplicate id)
                 3 refused — could NOT check (schema resource unavailable)
    check:       0 no collisions, 1 collision detected
2 and 3 are kept apart deliberately: "I checked it and said no" and "I never
managed to check it" are different events for whoever is reading the exit code,
and only one of them is fixed by reinstalling. Every other unexpected failure is
reported as `ERROR: <Type>: <message>` on stderr with exit 2 — a raw traceback
is never a user-facing outcome (see `handle_outcomes`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nwave_ai.outcomes.adapters.yaml_registry import YamlRegistryAdapter
from nwave_ai.outcomes.application.collision_detector import (
    CollisionDetector,
    TargetShape,
)
from nwave_ai.outcomes.application.registry_service import (
    DuplicateOutcomeIdError,
    InvalidOutcomeError,
    RegistryService,
    SchemaUnavailableError,
)
from nwave_ai.outcomes.domain.outcome import InputShape, Outcome, OutputShape


# Exit codes. 2 = refused after checking; 3 = refused because checking was
# impossible. Kept distinct so a damaged install cannot look like bad input.
_EXIT_REFUSED = 2
_EXIT_SCHEMA_UNAVAILABLE = 3

_REINSTALL_HINT = (
    "HOW: reinstall nwave-ai (e.g. `pipx reinstall nwave-ai`, or "
    "`uv tool install --force nwave-ai`) - the schema ships inside the package."
)


_DEFAULT_REGISTRY = Path("docs") / "product" / "outcomes" / "registry.yaml"


def handle_outcomes(argv: list[str]) -> int:
    """Dispatch `nwave-ai outcomes <subcommand>`."""
    parser = argparse.ArgumentParser(prog="nwave-ai outcomes")
    parser.add_argument(
        "--registry",
        type=Path,
        default=_DEFAULT_REGISTRY,
        help="Path to registry.yaml (default: docs/product/outcomes/registry.yaml)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    reg = sub.add_parser("register", help="Register a new outcome")
    reg.add_argument("--id", required=True)
    reg.add_argument(
        "--kind",
        required=True,
        choices=["specification", "operation", "invariant"],
    )
    reg.add_argument("--input-shape", required=True)
    reg.add_argument("--output-shape", required=True)
    reg.add_argument("--summary", default="")
    reg.add_argument("--feature", default="unknown")
    reg.add_argument("--keywords", default="")
    reg.add_argument("--artifact", default="")

    chk = sub.add_parser("check", help="Check for collisions")
    chk.add_argument("--input-shape", required=True)
    chk.add_argument("--output-shape", required=True)
    chk.add_argument("--keywords", default="")

    args = parser.parse_args(argv)

    # Everything downstream of argv parsing runs inside the guard, so no failure
    # mode reaches the user as a raw traceback: not the schema resource, and not
    # the several other unguarded throw sites either (registry mkdir/write ->
    # PermissionError, malformed registry YAML -> YAMLError, a row missing `id`
    # -> KeyError). `Exception`, not
    # `BaseException`: argparse's SystemExit must still pass through.
    try:
        registry_path = _ensure_registry(args.registry)
        return _dispatch(args, registry_path)
    except Exception as err:
        print(f"ERROR: {type(err).__name__}: {err}", file=sys.stderr)
        return _EXIT_REFUSED


def _dispatch(args: argparse.Namespace, registry_path: Path) -> int:
    if args.cmd == "register":
        return _run_register(args, registry_path)
    if args.cmd == "check":
        return _run_check(args, registry_path)
    return _EXIT_REFUSED


def _ensure_registry(registry_path: Path) -> Path:
    """Create an empty registry skeleton if missing, then return the path."""
    if not registry_path.exists():
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            'schema_version: "0.1"\noutcomes: []\n',
            encoding="utf-8",
        )
    return registry_path


def _run_register(args: argparse.Namespace, registry_path: Path) -> int:
    adapter = YamlRegistryAdapter(registry_path)
    service = RegistryService(reader=adapter, writer=adapter)
    outcome = _build_outcome_from_args(args)
    try:
        service.register(outcome)
    except SchemaUnavailableError as err:
        return _refuse_unvalidatable(outcome.id, err)
    except (DuplicateOutcomeIdError, InvalidOutcomeError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return _EXIT_REFUSED
    print(f"REGISTERED: {outcome.id}")
    return 0


def _refuse_unvalidatable(outcome_id: str, err: SchemaUnavailableError) -> int:
    """Say WHAT / WHY / HOW, having written nothing, and exit 3.

    The outcome could not be checked, so it was not registered. Saying so out
    loud is the whole point: silently writing an unvalidated row, or dying in a
    traceback, would both leave the user unable to tell a damaged install from
    a bad outcome.
    """
    print(
        f"REFUSED: cannot validate {outcome_id} - the outcome was NOT registered.",
        file=sys.stderr,
    )
    print(f"WHY: {err}", file=sys.stderr)
    print(_REINSTALL_HINT, file=sys.stderr)
    return _EXIT_SCHEMA_UNAVAILABLE


def _build_outcome_from_args(args: argparse.Namespace) -> Outcome:
    """Translate `register` argv into an Outcome value object."""
    return Outcome(
        id=args.id,
        kind=args.kind,
        summary=args.summary,
        feature=args.feature,
        inputs=(InputShape(shape=args.input_shape),),
        output=OutputShape(shape=args.output_shape),
        keywords=_split_keywords(args.keywords),
        artifact=args.artifact,
        related=(),
        superseded_by=None,
    )


def _run_check(args: argparse.Namespace, registry_path: Path) -> int:
    adapter = YamlRegistryAdapter(registry_path)
    snapshot = adapter.read_outcomes()
    detector = CollisionDetector()
    report = detector.check(
        target=TargetShape(
            input_shape=args.input_shape,
            output_shape=args.output_shape,
            keywords=_split_keywords(args.keywords),
        ),
        snapshot=snapshot,
    )
    if report.verdict == "clean":
        print("NO COLLISIONS")
        return 0
    for line in _render_collision_lines(report, snapshot):
        print(line)
    return 1


def _render_collision_lines(report, snapshot: tuple[Outcome, ...]) -> list[str]:
    """One stdout line per matched OUT-id with verdict + tier annotation."""
    tier2_by_id = dict(report.tier2_matches)
    tier1_ids = set(report.tier1_matches)
    label = report.verdict.upper()
    matched_ids = dict.fromkeys(
        outcome.id
        for outcome in snapshot
        if outcome.id in tier1_ids or outcome.id in tier2_by_id
    )
    lines: list[str] = []
    for out_id in matched_ids:
        in_tier1 = out_id in tier1_ids
        tier2_score = tier2_by_id.get(out_id)
        annotation = _annotate(in_tier1, tier2_score)
        lines.append(f"{label}: {out_id} ({annotation})")
    return lines


def _annotate(in_tier1: bool, tier2_score: float | None) -> str:
    if in_tier1 and tier2_score is not None:
        return f"Tier-1 + Tier-2 {tier2_score:.2f}"
    if in_tier1:
        return "Tier-1 only"
    return f"Tier-2 {tier2_score:.2f} only"


def _split_keywords(raw: str) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())
