"""`nwave-ai outcomes` subcommand entry — register / check / check-delta.

Driving adapter: argparse-based CLI. Translates argv into application
service calls (RegistryService.register, CollisionDetector.check,
RegistryService.collision_check_for_id) and maps results to exit codes
per feature-delta DESIGN:

    register:    0 success, 2 duplicate id or invalid outcome,
                 3 packaged schema resource unavailable
    check:       0 no collisions, 1 collision detected
    check-delta: 0 zero collisions across delta, 1 if any collision

    all:         4 the registry path is unusable (read-only filesystem,
                 permission denied, or the path is not a regular file)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import get_args

from nwave_ai.outcomes.adapters.yaml_registry import YamlRegistryAdapter
from nwave_ai.outcomes.application.collision_detector import (
    CollisionDetector,
    TargetShape,
)
from nwave_ai.outcomes.application.registry_service import (
    DuplicateOutcomeIdError,
    InvalidOutcomeError,
    RegistryService,
    SchemaResourceUnavailableError,
    UnknownOutcomeIdError,
)
from nwave_ai.outcomes.domain.outcome import (
    InputShape,
    Outcome,
    OutcomeKind,
    OutputShape,
)


_OUT_ID_PATTERN = re.compile(r"\bOUT-[A-Z0-9-]+\b")

# Derived, not restated: `OutcomeKind` in the domain is the single definition of
# the kind vocabulary. The JSON Schema enum cannot be derived at runtime (it is
# static data shipped in the wheel), so it is pinned to this same tuple by
# tests/outcomes/unit/test_schema_validation.py instead.
_KIND_CHOICES = get_args(OutcomeKind)


class RegistryPathUnusableError(Exception):
    """Raised when the registry path cannot be read or created.

    Signals an environment problem (read-only filesystem, permission denied,
    a path occupied by a directory), never a malformed outcome.
    """


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
        choices=_KIND_CHOICES,
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

    chd = sub.add_parser(
        "check-delta",
        help="Aggregate scan: parse OUT-ids from a feature-delta.md and check each",
    )
    chd.add_argument("delta_path", type=Path)

    args = parser.parse_args(argv)
    try:
        registry_path = _ensure_registry(args.registry)
    except RegistryPathUnusableError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 4

    if args.cmd == "register":
        return _run_register(args, registry_path)
    if args.cmd == "check":
        return _run_check(args, registry_path)
    if args.cmd == "check-delta":
        return _run_check_delta(args, registry_path)
    return 2


def _ensure_registry(registry_path: Path) -> Path:
    """Create an empty registry skeleton if missing, then return the path.

    Raises:
        RegistryPathUnusableError: when the path exists but is not a regular
            file, or when the directory or skeleton file cannot be created
            (read-only filesystem, permission denied, a parent that is a file).
    """
    if registry_path.exists():
        if not registry_path.is_file():
            raise RegistryPathUnusableError(
                f"registry path {registry_path} exists but is not a regular file"
            )
        return registry_path
    try:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            'schema_version: "0.1"\noutcomes: []\n',
            encoding="utf-8",
        )
    except OSError as err:
        raise RegistryPathUnusableError(
            f"cannot create registry at {registry_path}: {err}"
        ) from err
    return registry_path


def _run_register(args: argparse.Namespace, registry_path: Path) -> int:
    adapter = YamlRegistryAdapter(registry_path)
    service = RegistryService(reader=adapter, writer=adapter)
    outcome = _build_outcome_from_args(args)
    try:
        service.register(outcome)
    except SchemaResourceUnavailableError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        print(
            "Reinstall nwave-ai (e.g. `uv tool install --force nwave-ai`) "
            "to restore the packaged outcomes schema.",
            file=sys.stderr,
        )
        return 3
    except (DuplicateOutcomeIdError, InvalidOutcomeError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    print(f"REGISTERED: {outcome.id}")
    return 0


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
    for line in _render_collision_lines(report):
        print(line)
    return 1


def _run_check_delta(args: argparse.Namespace, registry_path: Path) -> int:
    """Aggregate scan: extract OUT-ids from a feature-delta.md, run a
    self-excluding collision check on each, emit aggregate report.

    Stdout: ``N outcomes checked, M collisions found across K outcomes``
    Exit:   0 when zero collisions, 1 otherwise.
    """
    delta_path: Path = args.delta_path
    if not delta_path.exists():
        print(f"ERROR: feature-delta not found: {delta_path}", file=sys.stderr)
        return 2

    out_ids = _extract_out_ids(delta_path.read_text(encoding="utf-8"))
    adapter = YamlRegistryAdapter(registry_path)
    service = RegistryService(reader=adapter, writer=adapter)

    collision_count = 0
    colliding_ids: list[str] = []
    for out_id in out_ids:
        try:
            report = service.collision_check_for_id(out_id)
        except UnknownOutcomeIdError:
            print(f"WARNING: {out_id} referenced in delta but not in registry")
            continue
        if report.verdict == "collision":
            collision_count += 1
            colliding_ids.append(out_id)

    n_checked = len(out_ids)
    k_with_collision = len(colliding_ids)
    print(
        f"{n_checked} outcomes checked, {collision_count} "
        f"collision{'s' if collision_count != 1 else ''} found "
        f"across {k_with_collision} outcome{'s' if k_with_collision != 1 else ''}"
    )
    for out_id in colliding_ids:
        print(f"  COLLISION: {out_id}")
    return 0 if collision_count == 0 else 1


def _extract_out_ids(text: str) -> list[str]:
    """Return ordered-unique OUT-ids found in text via regex scan."""
    return _ordered_unique(_OUT_ID_PATTERN.findall(text))


def _render_collision_lines(report) -> list[str]:
    """One stdout line per matched OUT-id with verdict + tier annotation."""
    tier2_by_id = dict(report.tier2_matches)
    label = report.verdict.upper()
    matched_ids = _ordered_unique(
        list(report.tier1_matches) + [out_id for out_id, _ in report.tier2_matches]
    )
    lines: list[str] = []
    for out_id in matched_ids:
        in_tier1 = out_id in report.tier1_matches
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


def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _split_keywords(raw: str) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())
