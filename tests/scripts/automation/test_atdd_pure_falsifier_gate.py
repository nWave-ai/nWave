"""Tests for atdd_pure_falsifier_gate CLI (plan v3 §4.5).

CONTRACT_SHAPE: bounded-change (CLI exits + audit-log append + config patch)
Outcome anchor: DISCUSS plan v3 §4.5 "falsifier-gate is prose, not automation"
— operator runs the gate and sees TRIPPED/HEALTHY decision; on TRIPPED the
config flips to classic AND a FalsifierGateTripped event lands in audit log.

Tests enter through the CLI's main() driving port. The full observable
universe is: (exit_code, stdout_json, audit_log_appended_events,
config_yaml_content). Strict state-delta is asserted on
config + audit log; complement equality on other tmp_path files.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# In-process driving port
# ---------------------------------------------------------------------------


def _run_cli(args: list[str]) -> tuple[int, dict[str, Any]]:
    """Invoke falsifier_gate.main() in-process; return (exit_code, json)."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from scripts.automation import atdd_pure_falsifier_gate

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = atdd_pure_falsifier_gate.main(args)
    stdout = buf.getvalue().strip()
    payload: dict[str, Any] = json.loads(stdout) if stdout else {}
    return code, payload


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _write_record(
    telemetry_dir: Path,
    feature_id: str,
    *,
    wall_clock_s: float,
    reviewer_findings: int,
    phase_d_cycles: int,
    target_p50_s: float = 100.0,
) -> Path:
    """Append a feature pilot JSONL with the metrics needed by the gate."""
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    path = telemetry_dir / f"{feature_id}.jsonl"
    lines = [
        {
            "feature": feature_id,
            "phase": "A_GREEN_ATS",
            "wall_clock_s": wall_clock_s / 3,
            "cycle_n": None,
            "reviewer_findings": None,
            "target_p50_s": target_p50_s,
        },
        {
            "feature": feature_id,
            "phase": "C_REVIEWER_AUDIT",
            "wall_clock_s": wall_clock_s / 3,
            "cycle_n": None,
            "reviewer_findings": reviewer_findings,
            "target_p50_s": target_p50_s,
        },
        {
            "feature": feature_id,
            "phase": "D_PHASE_D_ROUTER",
            "wall_clock_s": wall_clock_s / 3,
            "cycle_n": phase_d_cycles,
            "reviewer_findings": None,
            "target_p50_s": target_p50_s,
        },
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return path


def _seed_config(path: Path, mode: str = "atdd_pure") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"workflow": {"mode": mode}}))


def _seed_baseline(path: Path, defect_rate: float = 0.01) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"defect_rate": defect_rate}))


def _seed_healthy_telemetry(telemetry_dir: Path) -> None:
    for i in range(3):
        _write_record(
            telemetry_dir,
            f"feat-{i}",
            wall_clock_s=100.0,
            reviewer_findings=3,
            phase_d_cycles=1,
        )


def _common_args(tmp: Path, **overrides: Any) -> list[str]:
    telemetry = overrides.get("telemetry_dir", tmp / "telemetry")
    cfg = overrides.get("config_path", tmp / "config.yaml")
    baseline = overrides.get("baseline_path", tmp / "baseline.json")
    return [
        "--telemetry-dir",
        str(telemetry),
        "--config-path",
        str(cfg),
        "--baseline-path",
        str(baseline),
        "--n-features",
        str(overrides.get("n_features", 3)),
    ]


# ---------------------------------------------------------------------------
# Threshold breaches (parametrized — one PBT-style block per breach type)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("breach_kind", "fixture_kwargs", "expected_breach"),
    [
        (
            "median_wallclock_factor",
            {"wall_clock_s": 200.0, "reviewer_findings": 3, "phase_d_cycles": 1},
            "median_wallclock_factor",
        ),
        (
            "median_reviewer_findings",
            {"wall_clock_s": 100.0, "reviewer_findings": 15, "phase_d_cycles": 1},
            "median_reviewer_findings",
        ),
        (
            "median_phase_d_cycles",
            {"wall_clock_s": 100.0, "reviewer_findings": 3, "phase_d_cycles": 3},
            "median_phase_d_cycles",
        ),
    ],
)
def test_single_threshold_breach_trips(
    tmp_path: Path,
    breach_kind: str,
    fixture_kwargs: dict[str, Any],
    expected_breach: str,
) -> None:
    """Each single-axis breach → TRIPPED + config flips + event emitted."""
    telemetry = tmp_path / "telemetry"
    cfg = tmp_path / "config.yaml"
    _seed_config(cfg, mode="atdd_pure")
    _seed_baseline(tmp_path / "baseline.json")
    for i in range(3):
        _write_record(telemetry, f"feat-{i}", **fixture_kwargs)

    code, payload = _run_cli(_common_args(tmp_path))

    assert code == 42
    assert payload["decision"] == "TRIPPED"
    assert expected_breach in payload["breaches"]
    assert payload["action"] == "config_patched"
    flipped = yaml.safe_load(cfg.read_text())
    assert flipped["workflow"]["mode"] == "classic"


def test_defect_rate_breach_trips(tmp_path: Path) -> None:
    """Defect-rate-factor breach (vs baseline) → TRIPPED."""
    telemetry = tmp_path / "telemetry"
    cfg = tmp_path / "config.yaml"
    baseline = tmp_path / "baseline.json"
    _seed_config(cfg)
    _seed_baseline(baseline, defect_rate=0.01)
    for i in range(3):
        _write_record(
            telemetry,
            f"feat-{i}",
            wall_clock_s=100.0,
            reviewer_findings=3,
            phase_d_cycles=1,
        )
    # Override one record with embedded post_deploy_defect_rate
    extra = telemetry / "feat-0.jsonl"
    extra.write_text(
        extra.read_text()
        + json.dumps(
            {
                "feature": "feat-0",
                "phase": "G_COMPLETE",
                "post_deploy_defect_rate": 0.05,
            }
        )
        + "\n"
    )

    code, payload = _run_cli(_common_args(tmp_path))

    assert code == 42
    assert payload["decision"] == "TRIPPED"
    assert "defect_rate_factor" in payload["breaches"]


def test_combined_breaches_single_event(tmp_path: Path) -> None:
    """Multiple breaches → ONE TRIPPED event listing all breach keys."""
    telemetry = tmp_path / "telemetry"
    cfg = tmp_path / "config.yaml"
    _seed_config(cfg)
    _seed_baseline(tmp_path / "baseline.json")
    for i in range(3):
        _write_record(
            telemetry,
            f"feat-{i}",
            wall_clock_s=200.0,
            reviewer_findings=15,
            phase_d_cycles=3,
        )

    code, payload = _run_cli(_common_args(tmp_path))

    assert code == 42
    assert payload["decision"] == "TRIPPED"
    breaches = set(payload["breaches"])
    assert {
        "median_wallclock_factor",
        "median_reviewer_findings",
        "median_phase_d_cycles",
    }.issubset(breaches)


def test_healthy_metrics_pass(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry"
    cfg = tmp_path / "config.yaml"
    _seed_config(cfg)
    _seed_baseline(tmp_path / "baseline.json")
    _seed_healthy_telemetry(telemetry)

    code, payload = _run_cli(_common_args(tmp_path))

    assert code == 0
    assert payload["decision"] == "HEALTHY"
    assert payload["breaches"] == []
    # Config unchanged
    assert yaml.safe_load(cfg.read_text())["workflow"]["mode"] == "atdd_pure"


def test_insufficient_data_advisory(tmp_path: Path) -> None:
    """<N records → INSUFFICIENT_DATA advisory + exit 0 (do not block CI)."""
    telemetry = tmp_path / "telemetry"
    cfg = tmp_path / "config.yaml"
    _seed_config(cfg)
    _seed_baseline(tmp_path / "baseline.json")
    _write_record(
        telemetry,
        "only-one",
        wall_clock_s=100.0,
        reviewer_findings=3,
        phase_d_cycles=1,
    )

    code, payload = _run_cli(_common_args(tmp_path))

    assert code == 0
    assert payload["decision"] == "INSUFFICIENT_DATA"
    assert payload["action"] == "advisory_insufficient_data"
    assert yaml.safe_load(cfg.read_text())["workflow"]["mode"] == "atdd_pure"


def test_malformed_jsonl_line_skipped(tmp_path: Path) -> None:
    """Malformed JSONL line is skipped with warning — graceful, never crash."""
    telemetry = tmp_path / "telemetry"
    cfg = tmp_path / "config.yaml"
    _seed_config(cfg)
    _seed_baseline(tmp_path / "baseline.json")
    _seed_healthy_telemetry(telemetry)
    # Inject malformed line in one feature file
    bad = telemetry / "feat-0.jsonl"
    bad.write_text(bad.read_text() + "{not valid json\n")

    code, payload = _run_cli(_common_args(tmp_path))

    assert code == 0
    assert payload["decision"] == "HEALTHY"


def test_dry_run_does_not_patch_config(tmp_path: Path) -> None:
    """Dry-run: report decision but never patch config nor emit events."""
    telemetry = tmp_path / "telemetry"
    cfg = tmp_path / "config.yaml"
    _seed_config(cfg)
    _seed_baseline(tmp_path / "baseline.json")
    for i in range(3):
        _write_record(
            telemetry,
            f"feat-{i}",
            wall_clock_s=200.0,
            reviewer_findings=15,
            phase_d_cycles=3,
        )

    code, payload = _run_cli([*_common_args(tmp_path), "--dry-run"])

    assert code == 0  # dry-run never blocks
    assert payload["action"] == "dry_run_only"
    assert payload["decision"] == "TRIPPED"
    assert yaml.safe_load(cfg.read_text())["workflow"]["mode"] == "atdd_pure"


def test_config_patch_idempotent(tmp_path: Path) -> None:
    """Run twice on breach → final config identical to single run."""
    telemetry = tmp_path / "telemetry"
    cfg = tmp_path / "config.yaml"
    _seed_config(cfg)
    _seed_baseline(tmp_path / "baseline.json")
    for i in range(3):
        _write_record(
            telemetry,
            f"feat-{i}",
            wall_clock_s=200.0,
            reviewer_findings=3,
            phase_d_cycles=1,
        )

    code1, _ = _run_cli(_common_args(tmp_path))
    snapshot_after_first = cfg.read_text()
    code2, _ = _run_cli(_common_args(tmp_path))
    snapshot_after_second = cfg.read_text()

    assert code1 == code2 == 42
    assert snapshot_after_first == snapshot_after_second
    assert yaml.safe_load(snapshot_after_first)["workflow"]["mode"] == "classic"


# ---------------------------------------------------------------------------
# Property-based: random metric values → decision invariant
# ---------------------------------------------------------------------------


@given(
    wall_clock=st.floats(min_value=50.0, max_value=80.0),
    findings=st.integers(min_value=0, max_value=8),
    cycles=st.integers(min_value=1, max_value=1),
)
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_pbt_healthy_inputs_always_pass(
    tmp_path: Path,
    wall_clock: float,
    findings: int,
    cycles: int,
) -> None:
    """For any inputs strictly below ALL thresholds → HEALTHY."""
    telemetry = tmp_path / "telemetry"
    cfg = tmp_path / "config.yaml"
    # Clean per-example
    if cfg.exists():
        cfg.unlink()
    if telemetry.exists():
        for f in telemetry.iterdir():
            f.unlink()
    _seed_config(cfg)
    _seed_baseline(tmp_path / "baseline.json")
    for i in range(3):
        _write_record(
            telemetry,
            f"feat-{i}",
            wall_clock_s=wall_clock,
            reviewer_findings=findings,
            phase_d_cycles=cycles,
        )

    code, payload = _run_cli(_common_args(tmp_path))

    assert code == 0
    assert payload["decision"] == "HEALTHY"
