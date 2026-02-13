"""CLI: Roadmap init and validate tool.

Usage:
    python -m des.cli.roadmap init --project-id ID --goal "Goal" [--phases N] [--steps "01:3,02:2"] [--output FILE]
    python -m des.cli.roadmap validate ROADMAP_PATH

Exit codes:
    0 = Success (init) or valid (validate, warnings OK)
    1 = Validation errors found
    2 = Usage error
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from des.domain.roadmap_schema import RoadmapSchemaLoader
from des.domain.roadmap_validator import RoadmapValidator


def _parse_steps_spec(spec: str) -> dict[str, int]:
    """Parse steps spec like '01:3,02:2' into {phase_id: count}."""
    result: dict[str, int] = {}
    for pair in spec.split(","):
        pair = pair.strip()
        if ":" not in pair:
            raise ValueError(f"Invalid steps spec '{pair}', expected 'PHASE_ID:COUNT'")
        phase_id, count_str = pair.split(":", 1)
        result[phase_id.strip()] = int(count_str.strip())
    return result


def _build_skeleton(
    project_id: str,
    goal: str,
    num_phases: int,
    steps_per_phase: dict[str, int] | None,
) -> dict:
    """Build a roadmap skeleton with TODO placeholders."""
    phases = []
    total_steps = 0

    for pi in range(1, num_phases + 1):
        phase_id = f"{pi:02d}"
        step_count = (steps_per_phase or {}).get(phase_id, 1)
        steps = []
        for si in range(1, step_count + 1):
            step_id = f"{phase_id}-{si:02d}"
            steps.append(
                {
                    "id": step_id,
                    "name": "TODO: step name",
                    "criteria": "TODO: acceptance criteria",
                }
            )
            total_steps += 1
        phase = {
            "id": phase_id,
            "name": "TODO: phase name",
            "steps": steps,
        }
        phases.append(phase)

    roadmap: dict = {
        "roadmap": {
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_steps": total_steps,
            "phases": num_phases,
        },
        "phases": phases,
        "implementation_scope": {
            "source_directories": ["src/TODO/"],
            "test_directories": ["tests/TODO/"],
            "excluded_patterns": ["__init__.py", "__pycache__/**"],
        },
        "validation": {
            "status": "pending",
            "reviewer": "TODO",
            "approved_at": "TODO",
        },
    }

    return roadmap


def _cmd_init(args: list[str]) -> int:
    """Handle 'init' subcommand."""
    project_id = None
    goal = ""
    num_phases = 1
    steps_spec = None
    output_path = None

    i = 0
    while i < len(args):
        if args[i] == "--project-id" and i + 1 < len(args):
            project_id = args[i + 1]
            i += 2
        elif args[i] == "--goal" and i + 1 < len(args):
            goal = args[i + 1]
            i += 2
        elif args[i] == "--phases" and i + 1 < len(args):
            num_phases = int(args[i + 1])
            i += 2
        elif args[i] == "--steps" and i + 1 < len(args):
            steps_spec = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        else:
            print(f"Unknown option: {args[i]}", file=sys.stderr)
            return 2

    if not project_id:
        print("Error: --project-id is required", file=sys.stderr)
        return 2

    steps_per_phase = None
    if steps_spec:
        try:
            steps_per_phase = _parse_steps_spec(steps_spec)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
        # Infer num_phases from steps spec if not explicitly set differently
        if num_phases == 1 and len(steps_per_phase) > 1:
            num_phases = len(steps_per_phase)

    skeleton = _build_skeleton(project_id, goal, num_phases, steps_per_phase)
    yaml_output = yaml.dump(skeleton, default_flow_style=False, sort_keys=False)

    if output_path:
        Path(output_path).write_text(yaml_output, encoding="utf-8")
        print(f"Roadmap skeleton written to {output_path}")
    else:
        print(yaml_output, end="")

    return 0


def _cmd_validate(args: list[str]) -> int:
    """Handle 'validate' subcommand."""
    if not args:
        print("Error: roadmap path required", file=sys.stderr)
        print(
            "Usage: python -m des.cli.roadmap validate ROADMAP_PATH",
            file=sys.stderr,
        )
        return 2

    roadmap_path = Path(args[0])
    if not roadmap_path.exists():
        print(f"Error: file not found: {roadmap_path}", file=sys.stderr)
        return 2

    try:
        roadmap_data = yaml.safe_load(roadmap_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        print(f"Error: invalid YAML: {e}", file=sys.stderr)
        return 2

    if not isinstance(roadmap_data, dict):
        print("Error: roadmap must be a YAML mapping", file=sys.stderr)
        return 2

    loader = RoadmapSchemaLoader()
    schema = loader.load()
    validator = RoadmapValidator(schema)
    result = validator.validate(roadmap_data)

    errors = [v for v in result.violations if v.severity == "error"]
    warnings = [v for v in result.violations if v.severity == "warning"]

    if result.is_valid:
        print(f"VALID: {result.phases_found} phases, {result.steps_found} steps")
        for w in warnings:
            print(f"  WARNING [{w.rule}] {w.path}: {w.message}")
        return 0
    else:
        print(f"INVALID: {len(errors)} error(s), {len(warnings)} warning(s)")
        for e in errors:
            print(f"  ERROR [{e.rule}] {e.path}: {e.message}")
        for w in warnings:
            print(f"  WARNING [{w.rule}] {w.path}: {w.message}")
        return 1


def main(argv: list[str] | None = None) -> int:
    """Main entry point for roadmap CLI."""
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print(
            "Usage: python -m des.cli.roadmap {init|validate} [OPTIONS]",
            file=sys.stderr,
        )
        return 2

    subcommand = argv[0]
    sub_args = argv[1:]

    if subcommand == "init":
        return _cmd_init(sub_args)
    elif subcommand == "validate":
        return _cmd_validate(sub_args)
    else:
        print(f"Unknown subcommand: {subcommand}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
