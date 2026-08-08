"""CLI: Verify deliver integrity before finalize.

Usage:
    des-verify-integrity docs/feature/{project-id}/

Reads roadmap.json and execution-log.json from the project directory,
cross-references step IDs against execution-log entries, and reports
violations (steps without DES traces or with incomplete TDD phases).

Workflow-mode awareness (ADR-028 D4.2):
    Under `workflow.mode: atdd_pure` (resolved from `.nwave/config.yaml`),
    the DELIVER spine is roadmap-free and execution-log-free. In that mode
    `--roadmap-only` and the execution-log cross-reference are no-ops: a
    missing roadmap.json is the expected state (never exit 2), a leftover
    roadmap.json is a WARNING, and the verifier validates the AT-completion
    ledger instead. An absent ledger is an integrity violation (exit 1),
    never a crash. Any other mode -- `classic`, an absent key, or an absent
    config file -- is treated as classic and behaves exactly as before
    (the 0/1/2 exit-code contract is preserved byte-for-byte).

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
from des.cli.init_log import ATDD_PURE_MODE, _resolve_workflow_mode
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


def _find_at_completion_ledger(project_dir: Path) -> Path | None:
    """Locate the AT-completion ledger for an atdd_pure feature (ADR-028 D3).

    The ledger is a single per-feature append-only JSONL file at
    `{project_dir}/.nwave/telemetry/atdd-pure/{feature_id}.jsonl`. The verifier
    discovers it by glob -- one file per feature -- so it need not be told the
    feature id. Returns the ledger path, or None when no ledger exists.
    """
    ledger_dir = project_dir / ".nwave" / "telemetry" / "atdd-pure"
    if not ledger_dir.is_dir():
        return None
    ledgers = sorted(ledger_dir.glob("*.jsonl"))
    return ledgers[0] if ledgers else None


def _verify_atdd_pure(project_dir: Path, roadmap_path: Path) -> int:
    """Verify deliver integrity for an atdd_pure feature (ADR-028 D4.2).

    The atdd_pure spine is roadmap-free and execution-log-free. `--roadmap-only`
    and the execution-log cross-reference are no-ops here -- this branch never
    inspects either artifact for verdict purposes. The verifier validates the
    AT-completion ledger instead:

    - present ledger -> feature verified (exit 0);
    - absent ledger  -> structured integrity-violation diagnostic (exit 1),
      never a crash;
    - a leftover roadmap.json is the WRONG artifact for this spine, reported as
      a WARNING -- never an error.
    """
    ledger_path = _find_at_completion_ledger(project_dir)

    if ledger_path is None:
        print(
            "INTEGRITY VIOLATION: the AT-completion ledger is missing for this "
            "atdd_pure feature.\n"
            f"  - expected an append-only JSONL ledger under "
            f"{project_dir / '.nwave' / 'telemetry' / 'atdd-pure'}\n"
            "  - the atdd_pure DELIVER spine records audit telemetry in the "
            "AT-completion ledger (ADR-028 D3); without it the feature has no "
            "verifiable integrity trace."
        )
        return 1

    if roadmap_path.exists():
        print(
            f"Warning: a leftover roadmap.json is present at {roadmap_path}. "
            "The atdd_pure spine is roadmap-free (ADR-028 D1); this stale "
            "artifact is ignored and may be removed."
        )

    print(
        f"All slices have a complete AT-completion ledger trace: {ledger_path} "
        "(atdd_pure: roadmap.json and execution-log.json cross-reference skipped)."
    )
    return 0


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

    # ADR-028 D4.2: resolve workflow mode BEFORE any roadmap.json access. Under
    # atdd_pure the spine is roadmap-free -- a missing roadmap is the expected
    # state, not exit 2 -- so the mode branch MUST run above the roadmap check.
    if _resolve_workflow_mode(project_dir) == ATDD_PURE_MODE:
        return _verify_atdd_pure(project_dir, roadmap_path)

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
    #
    # ADR-025 dispatch (per-log auto-detect, 2026-05-18 hotfix): the CLI
    # uses the EXECUTION LOG to decide which canon applies. If ALL three
    # legacy-only phases (PREPARE, RED_ACCEPTANCE, RED_UNIT) appear in
    # ANY step's recorded events, treat the log as v4 legacy and validate
    # against the schema's `legacy_phases` tuple. Otherwise canonical.
    # Mirrors `validator._resolve_active_phases` for consistency with the
    # in-process step-completion validator.
    legacy_only = {"PREPARE", "RED_ACCEPTANCE", "RED_UNIT"}
    log_canon_is_legacy = any(
        legacy_only.issubset(set(phase_names)) for phase_names in entries.values()
    )
    active_phases = schema.legacy_phases if log_canon_is_legacy else schema.tdd_phases
    rigor_phases = DESConfig().rigor_tdd_phases
    # Empty rigor.tdd_phases is a config misconfiguration, not a degenerate
    # zero-overlap case — surface the diagnostic BEFORE the active-phases
    # fallback can mask it. The fallback (line below) is correct ONLY when
    # rigor declares non-empty phases that simply do not overlap with the
    # active canon (e.g. 3-phase rigor against a legacy v4 audit-replay).
    if not rigor_phases:
        print(
            f"ERROR: rigor.tdd_phases is empty in .nwave/des-config.json. "
            f"Configure rigor.tdd_phases with at least one of: "
            f"{list(schema.tdd_phases)!r} (canonical) or "
            f"{list(schema.legacy_phases)!r} (legacy).",
            file=sys.stderr,
        )
        return 2
    effective_phases = (
        tuple(p for p in active_phases if p in rigor_phases) or active_phases
    )
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
