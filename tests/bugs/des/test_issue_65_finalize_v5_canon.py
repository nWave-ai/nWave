"""Regression guard (issue #65, downstream — the headline): the
``verify_deliver_integrity`` finalize path accepts a v5 (``schema_version
"5.0"``) 3-phase execution log end-to-end, including when ``rigor.tdd_phases``
is overridden to the legacy 5-phase set.

The PreToolUse *prompt* gate is guarded elsewhere
(``tests/bugs/des/test_issue_65_deliver_3phase_prompt.py``). This guard covers
the FINALIZE stage — the "passes prompt, fails finalize" failure #65 feared.
``des.cli.verify_deliver_integrity.main`` derives the active phase set from the
LOG's own canon, intersects it with ``rigor.tdd_phases``, and a v5 log must pass.

Drives the REAL finalize entry in-process: ``main([deliver_dir])`` builds the
production composition itself (``DESConfig`` -> ``TDDSchema`` -> the per-log
canon dispatch -> ``DeliverIntegrityVerifier``). ``cwd`` is set to the project
root via ``monkeypatch.chdir`` so ``DESConfig()`` resolves the on-disk
``.nwave/des-config.json`` exactly as in production (port-to-port — no DESConfig
mocking). All fixtures are isolated under ``tmp_path``.

Each project config carries an explicit ``"rigor"`` key, which makes the cascade
deterministic: a present ``"rigor"`` block causes the global rigor config to be
ignored entirely (``DESConfig._rigor``), so the test is not perturbed by any
machine-level ``~/.nwave/global-config.json``.

Refs: https://github.com/nWave-ai/nWave/issues/65 ; ADR-025 (2026-05-07).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from des.cli.verify_deliver_integrity import main


if TYPE_CHECKING:
    import pytest


CANONICAL_3_PHASE = ["RED", "GREEN", "COMMIT"]
LEGACY_5_PHASE = ["PREPARE", "RED_ACCEPTANCE", "RED_UNIT", "GREEN", "COMMIT"]


# A contract-conforming roadmap with one step (mirrors the proven fixture shape
# in tests/bugs/installer/acceptance/steps/test_rigor_aware_integrity.py).
_MIN_ROADMAP: dict = {
    "roadmap": {
        "project_id": "issue-65-finalize-fixture",
        "created_at": "2026-06-17T00:00:00Z",
        "total_steps": 1,
    },
    "phases": [
        {
            "id": "01",
            "name": "Single-step phase",
            "steps": [
                {
                    "id": "01-01",
                    "name": "Single fixture step",
                    "criteria": ["criterion one"],
                }
            ],
        }
    ],
    "implementation_scope": {
        "source_directories": ["src/fixture/"],
    },
}


def _write_execution_log(
    deliver_dir: Path, step_id: str, phases: list[str], schema_version: str
) -> None:
    """Write a v3.0-structured execution-log.json stamped with *schema_version*."""
    events = [
        {
            "sid": step_id,
            "p": phase,
            "s": "EXECUTED",
            "d": "PASS",
            "t": f"2026-06-17T00:00:{idx:02d}Z",
        }
        for idx, phase in enumerate(phases)
    ]
    log = {
        "schema_version": schema_version,
        "feature_id": "issue-65-finalize-fixture",
        "events": events,
    }
    (deliver_dir / "execution-log.json").write_text(json.dumps(log), encoding="utf-8")


def _build_fixture(
    tmp_path: Path,
    *,
    rigor: dict,
    log_phases: list[str],
    schema_version: str,
) -> tuple[Path, Path]:
    """Build a project-root + deliver-dir fixture, returning (root, deliver_dir).

    Layout::

        tmp_path/                         <- project root (cwd for finalize)
          .nwave/des-config.json          <- {"rigor": rigor}
          feature/deliver/roadmap.json
          feature/deliver/execution-log.json
    """
    project_root = tmp_path
    deliver_dir = tmp_path / "feature" / "deliver"
    deliver_dir.mkdir(parents=True)

    (deliver_dir / "roadmap.json").write_text(
        json.dumps(_MIN_ROADMAP), encoding="utf-8"
    )

    nwave_dir = project_root / ".nwave"
    nwave_dir.mkdir()
    (nwave_dir / "des-config.json").write_text(
        json.dumps({"rigor": rigor}), encoding="utf-8"
    )

    _write_execution_log(
        deliver_dir, step_id="01-01", phases=log_phases, schema_version=schema_version
    )
    return project_root, deliver_dir


def _run_finalize(
    monkeypatch: pytest.MonkeyPatch, project_root: Path, deliver_dir: Path
) -> int:
    """Invoke the real finalize entry in-process with cwd at the project root."""
    monkeypatch.chdir(project_root)
    return main([str(deliver_dir)])


def _assert_verified(returncode: int, captured: pytest.CaptureResult) -> None:
    assert returncode == 0, (
        f"finalize exit={returncode}; stdout={captured.out!r}; stderr={captured.err!r}"
    )
    assert "complete DES traces" in captured.out, (
        f"finalize did not report verified traces; stdout={captured.out!r}"
    )
    assert "INTEGRITY VIOLATIONS" not in captured.out, (
        f"finalize reported an integrity violation; stdout={captured.out!r}"
    )


def test_v5_log_passes_with_default_rigor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """(a) Default rigor.tdd_phases (canonical 3-phase) accepts a v5 log."""
    # An empty rigor block exercises the documented default (RED/GREEN/COMMIT)
    # while keeping the global-config cascade pinned out.
    project_root, deliver_dir = _build_fixture(
        tmp_path,
        rigor={},
        log_phases=CANONICAL_3_PHASE,
        schema_version="5.0",
    )
    returncode = _run_finalize(monkeypatch, project_root, deliver_dir)
    _assert_verified(returncode, capsys.readouterr())


def test_v5_log_passes_when_rigor_overridden_to_legacy_five_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """(b) issue #65 layer 4: a legacy 5-phase rigor override must NOT defeat a
    v5 3-phase log — the log's own canon governs the active phase set."""
    project_root, deliver_dir = _build_fixture(
        tmp_path,
        rigor={"tdd_phases": LEGACY_5_PHASE},
        log_phases=CANONICAL_3_PHASE,
        schema_version="5.0",
    )
    returncode = _run_finalize(monkeypatch, project_root, deliver_dir)
    _assert_verified(returncode, capsys.readouterr())


def test_v4_legacy_log_still_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Backward-compat: a v4 legacy 5-phase log with legacy rigor still verifies
    (pre-2026-05-07 audit-log replay)."""
    project_root, deliver_dir = _build_fixture(
        tmp_path,
        rigor={"tdd_phases": LEGACY_5_PHASE},
        log_phases=LEGACY_5_PHASE,
        schema_version="4.0",
    )
    returncode = _run_finalize(monkeypatch, project_root, deliver_dir)
    _assert_verified(returncode, capsys.readouterr())
