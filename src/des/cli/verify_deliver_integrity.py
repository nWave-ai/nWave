"""CLI: Verify deliver integrity before finalize.

Usage:
    des-verify-integrity docs/feature/{project-id}/

Reads roadmap.json and execution-log.json from the project directory,
cross-references step IDs against execution-log entries, and reports
violations (steps without DES traces or with incomplete TDD phases).

Exit codes:
    0 = All steps verified
    1 = Integrity violations found
    2 = Usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from des.adapters.driven.config.des_config import DESConfig
from des.domain._roadmap_helpers import (
    extract_step_ids as _extract_step_ids,
)
from des.domain.deliver_integrity_verifier import DeliverIntegrityVerifier
from des.domain.roadmap_schema import get_roadmap_schema
from des.domain.roadmap_validator import RoadmapValidator
from des.domain.tdd_schema import TDDSchemaLoader


__all__ = ["_extract_step_ids"]  # re-export for tests/des/unit/cli/


def _parse_execution_log(exec_log: dict) -> dict[str, list[str]]:
    """Parse execution-log.json events into step_id -> list[phase_name] mapping.

    Supports both v2.0 pipe format ("sid|phase|status|data|ts")
    and v3.0 structured format ({sid, p, s, d, t}).
    """
    entries: dict[str, list[str]] = {}
    for event in exec_log.get("events", []):
        if isinstance(event, str):
            parts = event.split("|")
            if len(parts) >= 2:
                step_id = parts[0]
                phase_name = parts[1]
                entries.setdefault(step_id, []).append(phase_name)
        elif isinstance(event, dict):
            step_id = event.get("sid", "")
            phase_name = event.get("p", "")
            if step_id and phase_name:
                entries.setdefault(step_id, []).append(phase_name)
    return entries


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="des-verify-integrity",
        description=(
            "Verify TDD phase completeness for all steps in a feature deliver. "
            "Reads roadmap.json and execution-log.json, cross-references step IDs "
            "against execution-log entries, and reports violations."
        ),
        epilog=(
            "Exit codes: 0 = all steps verified | 1 = integrity violations | "
            "2 = usage / format error."
        ),
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help=(
            "Path to the feature deliver directory containing roadmap.json "
            "and execution-log.json (e.g. docs/feature/<id>/deliver/)"
        ),
    )
    parser.add_argument(
        "--roadmap-only",
        action="store_true",
        help=(
            "Validate roadmap.json only (RoadmapValidator); skip the "
            "execution-log.json cross-reference. Intended for Phase 1 "
            "hard-gate use before crafter dispatch has produced any "
            "execution-log entries."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    # F-2 (RC-B, ADR-025): argparse replaces hand-rolled args[0] loop. The
    # legacy loop silently swallowed `--roadmap-only` (treating it as the
    # positional path) which made the Phase 1 hard gate in
    # `nw-deliver/SKILL.md:153` non-functional. argparse natively raises
    # SystemExit on unknown flags with the usage banner.
    raw_args = sys.argv[1:] if argv is None else list(argv)
    parser = _build_parser()
    args = parser.parse_args(raw_args)

    project_dir: Path = args.project_dir
    roadmap_path = project_dir / "roadmap.json"

    if not roadmap_path.exists():
        print(f"Error: roadmap.json not found at {roadmap_path}")
        return 2

    roadmap = json.loads(roadmap_path.read_text())

    # Structural pre-check: validate roadmap format. In --roadmap-only mode
    # this is the ONLY check; execution-log.json is never opened.
    try:
        roadmap_schema = get_roadmap_schema()
        validator = RoadmapValidator(roadmap_schema)
        validation = validator.validate(roadmap)
        errors = [v for v in validation.violations if v.severity == "error"]
        if errors:
            print(f"ROADMAP FORMAT ERRORS ({len(errors)}):")
            for e in errors:
                print(f"  - [{e.rule}] {e.path}: {e.message}")
            print("Fix roadmap format before verifying deliver integrity.")
            return 1
    except Exception as e:
        print(f"Warning: roadmap format pre-check skipped: {e}")
        if args.roadmap_only:
            # In --roadmap-only mode the validator IS the verdict — surface
            # the failure rather than silently continuing past it.
            return 2

    if args.roadmap_only:
        print(
            f"Roadmap format OK: {roadmap_path} "
            f"(validator: no errors). --roadmap-only: execution-log skipped."
        )
        return 0

    exec_log_path = project_dir / "execution-log.json"
    if not exec_log_path.exists():
        print(f"Error: execution-log.json not found at {exec_log_path}")
        return 2

    exec_log = json.loads(exec_log_path.read_text())

    step_ids = _extract_step_ids(roadmap)
    entries = _parse_execution_log(exec_log)

    schema = TDDSchemaLoader().load()

    # F-3 (RC-C, ADR-025): the integrity verifier honours the rigor-profile
    # phase set declared in `.nwave/des-config.json`, intersected with the
    # canonical TDDSchema phase set. This lets 3-phase ADR-025 projects pass
    # integrity without spurious "missing PREPARE/RED_ACCEPTANCE/RED_UNIT"
    # errors, while legacy 5-phase projects continue to verify unchanged.
    rigor_phases = DESConfig().rigor_tdd_phases
    effective_phases = tuple(p for p in schema.tdd_phases if p in rigor_phases)
    if not effective_phases:
        print(
            f"ERROR: rigor.tdd_phases contains no phases recognised by the "
            f"canonical TDDSchema. Misconfigured rigor phases: "
            f"{list(rigor_phases)!r}; canonical phases: "
            f"{list(schema.tdd_phases)!r}.",
            file=sys.stderr,
        )
        return 2

    required_phases = list(effective_phases)
    verifier = DeliverIntegrityVerifier(required_phases=required_phases)
    result = verifier.verify(step_ids, entries)

    if result.is_valid:
        print(f"All {result.steps_verified} steps have complete DES traces")
        return 0
    else:
        print(f"INTEGRITY VIOLATIONS: {result.reason}")
        for v in result.violations:
            print(
                f"  - {v.step_id}: {v.phase_count}/{len(required_phases)} phases, "
                f"missing: {v.missing_phases}"
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
