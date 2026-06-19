"""Integration test: run_contract_gate default mode actually runs the suite.

slice-14 of the atdd-pure-roadmap-free-rollout. Reviewer condition on the
slice-14 AT review (APPROVED with one condition): the acceptance tests cover
only `run_contract_gate`'s digest-verify half (`--collect-only`,
`--verify-gate-scope`). The **suite-running half** -- role (a), the default
mode that actually invokes `pytest -m "unit or integration or acceptance"`
over the whole tree -- has NO acceptance coverage.

slice-14 exists precisely to abolish "verifier subset of contract"; shipping
`run_contract_gate` with a half-covered surface would reproduce that defect.
This dedicated integration test is the coverage owner for the suite-run path:
it exercises a REAL `run_contract_gate` default-mode run against a real
throwaway pytest project and asserts the pass/fail verdict reflects the actual
test outcome.

Real I/O: a real tmp_path project with real `.py` test files, a real
subprocess `pytest` invocation. Integration layer (Mandate 6 -- subprocess
adapter, real exit codes).
"""

from __future__ import annotations

import json
from pathlib import Path

from des.cli.run_contract_gate import main as run_contract_gate_main


def _capture(capsys, argv: list[str]) -> tuple[int, str]:
    """Invoke run_contract_gate.main and return (exit_code, stdout)."""
    exit_code = run_contract_gate_main(argv)
    captured = capsys.readouterr()
    return exit_code, captured.out


def _last_json_event(stdout: str) -> dict:
    """Parse the final single-line JSON object emitted on stdout."""
    json_lines = [line for line in stdout.splitlines() if line.strip().startswith("{")]
    return json.loads(json_lines[-1])


def _write_project(root: Path, *, all_pass: bool) -> None:
    """Materialise a minimal pytest project under ``root``.

    The project carries one test file under a directory that auto-receives the
    `unit` marker, so it falls inside the contract marker expression
    `"unit or integration or acceptance"`.
    """
    tests_dir = root / "tests" / "unit"
    tests_dir.mkdir(parents=True)
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (root / "conftest.py").write_text(
        # Auto-apply the `unit` marker by directory so the contract marker
        # expression collects these tests.
        "import pytest\n\n\n"
        "def pytest_collection_modifyitems(items):\n"
        "    for item in items:\n"
        "        item.add_marker(pytest.mark.unit)\n",
        encoding="utf-8",
    )
    (root / "pytest.ini").write_text(
        "[pytest]\nmarkers =\n"
        "    unit: unit tests\n"
        "    integration: integration tests\n"
        "    acceptance: acceptance tests\n",
        encoding="utf-8",
    )
    body = (
        "def test_contract_behaviour():\n    assert 1 + 1 == 2\n"
        if all_pass
        else "def test_contract_behaviour():\n    assert 1 + 1 == 3\n"
    )
    (tests_dir / "test_contract.py").write_text(body, encoding="utf-8")


def test_run_contract_gate_passes_when_real_suite_passes(
    tmp_path: Path, capsys
) -> None:
    """Default mode runs the real suite; an all-green project -> exit 0, passed."""
    project = tmp_path / "green_project"
    _write_project(project, all_pass=True)

    exit_code, stdout = _capture(capsys, ["--repo", str(project)])

    result = _last_json_event(stdout)
    assert result["event"] == "ContractGateResult"
    assert result["passed"] is True
    assert result["pytest_exit_code"] == 0
    assert exit_code == 0
    # The suite-run mode also emits a gate-scope digest (64-hex SHA-256).
    assert len(result["gate_scope_digest"]) == 64


def test_run_contract_gate_fails_when_real_suite_fails(tmp_path: Path, capsys) -> None:
    """Default mode runs the real suite; a failing project -> exit 1, not passed.

    This is the load-bearing assertion: the gate verdict is derived from the
    ACTUAL pytest run, not a hard-coded pass -- a regression in the contract
    suite is caught by the gate, closing RCA Branch B.
    """
    project = tmp_path / "red_project"
    _write_project(project, all_pass=False)

    exit_code, stdout = _capture(capsys, ["--repo", str(project)])

    result = _last_json_event(stdout)
    assert result["event"] == "ContractGateResult"
    assert result["passed"] is False
    assert result["pytest_exit_code"] != 0
    assert exit_code == 1
