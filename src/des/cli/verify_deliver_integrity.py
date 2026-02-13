"""CLI: Verify deliver integrity before finalize.

Usage:
    python -m des.cli.verify_deliver_integrity docs/feature/{project-id}/

Reads roadmap.yaml and execution-log.yaml from the project directory,
cross-references step IDs against execution-log entries, and reports
violations (steps without DES traces or with incomplete TDD phases).

Exit codes:
    0 = All steps verified
    1 = Integrity violations found
    2 = Usage error
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from des.domain.deliver_integrity_verifier import DeliverIntegrityVerifier
from des.domain.roadmap_schema import get_roadmap_schema
from des.domain.roadmap_validator import RoadmapValidator
from des.domain.tdd_schema import get_tdd_schema


def _extract_step_ids(roadmap: dict) -> list[str]:
    """Extract step IDs from roadmap, supporting both flat and nested formats.

    Flat format: top-level ``steps`` list with ``id`` or ``step_id`` keys.
    Nested format: ``phases`` list, each containing a ``steps`` list.
    """
    # Flat format: top-level "steps" list
    if "steps" in roadmap:
        return [
            s.get("id") or s.get("step_id")
            for s in roadmap["steps"]
            if s.get("id") or s.get("step_id")
        ]
    # Nested format: steps under phases
    step_ids: list[str] = []
    for phase in roadmap.get("phases", []):
        for step in phase.get("steps", []):
            step_id = step.get("id") or step.get("step_id")
            if step_id:
                step_ids.append(step_id)
    return step_ids


def _parse_execution_log(exec_log: dict) -> dict[str, list[str]]:
    """Parse execution-log.yaml events into step_id -> list[phase_name] mapping.

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


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m des.cli.verify_deliver_integrity <project-dir>")
        return 2

    project_dir = Path(sys.argv[1])

    roadmap_path = project_dir / "roadmap.yaml"
    exec_log_path = project_dir / "execution-log.yaml"

    if not roadmap_path.exists():
        print(f"Error: roadmap.yaml not found at {roadmap_path}")
        return 2

    if not exec_log_path.exists():
        print(f"Error: execution-log.yaml not found at {exec_log_path}")
        return 2

    roadmap = yaml.safe_load(roadmap_path.read_text())
    exec_log = yaml.safe_load(exec_log_path.read_text())

    # Structural pre-check: validate roadmap format before extracting IDs
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

    step_ids = _extract_step_ids(roadmap)
    entries = _parse_execution_log(exec_log)

    schema = get_tdd_schema()
    verifier = DeliverIntegrityVerifier(required_phases=list(schema.tdd_phases))
    result = verifier.verify(step_ids, entries)

    if result.is_valid:
        print(f"All {result.steps_verified} steps have complete DES traces")
        return 0
    else:
        print(f"INTEGRITY VIOLATIONS: {result.reason}")
        for v in result.violations:
            print(
                f"  - {v.step_id}: {v.phase_count}/{len(schema.tdd_phases)} phases, "
                f"missing: {v.missing_phases}"
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
