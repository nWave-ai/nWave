"""ATDD-pure falsifier-gate auto-revert mechanism (plan v3 §4.5).

Reads N latest pilot JSONL feature records from a telemetry directory.
On ANY threshold breach (§4.5.3):
    1. patches workflow.mode -> classic in config YAML
    2. emits FalsifierGateTripped event to audit log
    3. exits with code 42 (CI fails the pilot job)
Otherwise emits FalsifierGateHealthy and exits 0. Insufficient data (<N
records) is advisory: exit 0 with action="advisory_insufficient_data".

CONTRACT_SHAPE: bounded-change (declared mutations: config.yaml workflow.mode
+ audit log append). Dry-run is unbounded-preservation (snapshot invariant).

Invocation: /nw-deliver Phase G post-commit hook OR CI release-prod.yml
falsifier-check job (post-DELIVER per pilot feature).

References:
- plan v3 §4.5: docs/proposals/atdd-pure-workflow-restructure-v3-2026-05-19.md
- ADR-027 §Metrics: docs/architecture/adrs/adr-027-atdd-pure-7-phase-extension.md
- Event shape: src/des/domain/atdd_pure_phases.py::FalsifierGateTripped
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Sequence


logger = logging.getLogger(__name__)

# Thresholds (plan v3 §4.5.3) — breach if metric > threshold (>= for cycles)
THRESHOLD_WALLCLOCK_FACTOR = 1.3
THRESHOLD_REVIEWER_FINDINGS = 12
THRESHOLD_DEFECT_RATE_FACTOR = 2.0
THRESHOLD_PHASE_D_CYCLES = 2.0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="atdd_pure_falsifier_gate",
        description="ATDD-pure falsifier-gate auto-revert (plan v3 §4.5).",
    )
    p.add_argument(
        "--telemetry-dir",
        type=Path,
        default=Path("nWave/telemetry/wave-time-token-telemetry/pilot/"),
    )
    p.add_argument("--config-path", type=Path, default=Path(".nwave/config.yaml"))
    p.add_argument("--n-features", type=int, default=3)
    p.add_argument(
        "--baseline-path",
        type=Path,
        default=Path("docs/analysis/classic-baseline-M-2026-05-19.json"),
    )
    p.add_argument(
        "--audit-log", type=Path, default=Path(".nwave/des/logs/audit-events.jsonl")
    )
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def _load_records(telemetry_dir: Path, n: int) -> list[dict[str, Any]]:
    """Return per-feature aggregated dicts for the N latest files (by mtime)."""
    if not telemetry_dir.exists():
        return []
    files = sorted(
        telemetry_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
    )[:n]
    return [r for r in (_aggregate_feature(f) for f in files) if r is not None]


def _aggregate_feature(path: Path) -> dict[str, Any] | None:
    """Reduce one feature JSONL into a flat metrics dict; tolerate bad lines."""
    wall_clock = 0.0
    findings: list[int] = []
    cycles: list[int] = []
    target_p50: float | None = None
    defect_rate: float | None = None
    feature_id: str | None = None
    saw_any = False
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("skipping malformed JSONL line in %s", path)
            continue
        saw_any = True
        feature_id = event.get("feature", feature_id) or path.stem
        if isinstance(event.get("wall_clock_s"), int | float):
            wall_clock += float(event["wall_clock_s"])
        if isinstance(event.get("reviewer_findings"), int):
            findings.append(event["reviewer_findings"])
        if isinstance(event.get("cycle_n"), int):
            cycles.append(event["cycle_n"])
        if isinstance(event.get("target_p50_s"), int | float):
            target_p50 = float(event["target_p50_s"])
        if isinstance(event.get("post_deploy_defect_rate"), int | float):
            defect_rate = float(event["post_deploy_defect_rate"])
    if not saw_any:
        return None
    return {
        "feature_id": feature_id or path.stem,
        "wall_clock_s": wall_clock,
        "reviewer_findings": max(findings) if findings else 0,
        "phase_d_cycles": max(cycles) if cycles else 0,
        "target_p50_s": target_p50,
        "defect_rate": defect_rate,
    }


def _load_baseline(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        logger.warning("baseline %s malformed; treating as absent", path)
        return None
    return data if isinstance(data, dict) else None


def _evaluate(
    records: list[dict[str, Any]], baseline: dict[str, Any] | None
) -> tuple[dict[str, float | None], list[str]]:
    """Compute medians + breach list. Returns (metrics, breaches)."""
    factors = [
        r["wall_clock_s"] / r["target_p50_s"]
        for r in records
        if r.get("target_p50_s") and r["target_p50_s"] > 0
    ]
    median_wallclock = statistics.median(factors) if factors else 0.0
    median_findings = statistics.median(r["reviewer_findings"] for r in records)
    median_cycles = statistics.median(r["phase_d_cycles"] for r in records)
    observed = [r["defect_rate"] for r in records if r["defect_rate"] is not None]
    defect_factor: float | None = None
    if observed and baseline and baseline.get("defect_rate"):
        rate = float(baseline["defect_rate"])
        if rate > 0:
            defect_factor = statistics.median(observed) / rate

    breaches: list[str] = []
    if median_wallclock > THRESHOLD_WALLCLOCK_FACTOR:
        breaches.append("median_wallclock_factor")
    if median_findings > THRESHOLD_REVIEWER_FINDINGS:
        breaches.append("median_reviewer_findings")
    if defect_factor is not None and defect_factor > THRESHOLD_DEFECT_RATE_FACTOR:
        breaches.append("defect_rate_factor")
    if median_cycles >= THRESHOLD_PHASE_D_CYCLES:
        breaches.append("median_phase_d_cycles")

    return (
        {
            "median_wallclock_factor": round(median_wallclock, 4),
            "median_reviewer_findings": median_findings,
            "defect_rate_factor": defect_factor,
            "median_phase_d_cycles": median_cycles,
        },
        breaches,
    )


def _patch_config(config_path: Path) -> str:
    """Set workflow.mode=classic, idempotent. Returns one-line diff summary."""
    import yaml  # type: ignore[import-untyped]

    cfg: dict[str, Any] = (
        yaml.safe_load(config_path.read_text()) or {} if config_path.exists() else {}
    )
    cfg.setdefault("workflow", {})["mode"] = "classic"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=True))
    return f"workflow.mode -> classic (path={config_path})"


def _emit_event(audit_log: Path, event_type: str, payload: dict[str, Any]) -> None:
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "falsifier_gate",
        "schema_version": "1.0",
        **payload,
    }
    with audit_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def _emit(result: dict[str, Any], exit_code: int) -> int:
    print(json.dumps(result))
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    records = _load_records(args.telemetry_dir, args.n_features)

    if len(records) < args.n_features:
        return _emit(
            {
                "decision": "INSUFFICIENT_DATA",
                "metrics": {},
                "breaches": [],
                "action": "advisory_insufficient_data",
                "config_diff": None,
                "records_found": len(records),
                "n_features_required": args.n_features,
            },
            0,
        )

    metrics, breaches = _evaluate(records, _load_baseline(args.baseline_path))

    if args.dry_run:
        return _emit(
            {
                "decision": "TRIPPED" if breaches else "HEALTHY",
                "metrics": metrics,
                "breaches": breaches,
                "action": "dry_run_only",
                "config_diff": None,
            },
            0,
        )

    if breaches:
        diff = _patch_config(args.config_path)
        _emit_event(
            args.audit_log,
            "FalsifierGateTripped",
            {"breach": metrics, "flipped_to_mode": "classic", "breaches": breaches},
        )
        return _emit(
            {
                "decision": "TRIPPED",
                "metrics": metrics,
                "breaches": breaches,
                "action": "config_patched",
                "config_diff": diff,
            },
            42,
        )

    _emit_event(args.audit_log, "FalsifierGateHealthy", {"metrics": metrics})
    return _emit(
        {
            "decision": "HEALTHY",
            "metrics": metrics,
            "breaches": [],
            "action": "no_action",
            "config_diff": None,
        },
        0,
    )


if __name__ == "__main__":
    sys.exit(main())
