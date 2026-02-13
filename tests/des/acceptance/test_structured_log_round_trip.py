"""Acceptance test: structured YAML log format (schema v3.0) round-trip.

Validates that:
1. log_phase CLI writes structured YAML objects with short keys (sid, p, s, d, t)
2. log_phase CLI bumps schema_version to '3.0'
3. YamlExecutionLogReader reads v3.0 structured format correctly
4. YamlExecutionLogReader reads v2.0 pipe format correctly (backward compat)
5. Auto-detection works: v2.0 events are strings, v3.0 events are dicts
6. Structured events with tu/tk keys are parsed correctly
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import yaml

from des.adapters.driven.hooks.yaml_execution_log_reader import YamlExecutionLogReader
from des.domain.tdd_schema import TDDSchema


@pytest.fixture()
def mock_schema():
    """Patch get_tdd_schema in the log_phase module to return a test schema."""
    schema = TDDSchema(
        tdd_phases=(
            "PREPARE",
            "RED_ACCEPTANCE",
            "RED_UNIT",
            "GREEN",
            "COMMIT",
        ),
        valid_skip_prefixes=("NOT_APPLICABLE:",),
        blocking_skip_prefixes=("APPROVED_SKIP:",),
    )
    with patch("des.cli.log_phase.get_tdd_schema", return_value=schema):
        yield schema


def _create_execution_log(tmp_path, schema_version="2.0", events=None):
    """Helper to create a minimal execution-log.yaml."""
    data = {
        "schema_version": schema_version,
        "project_id": "test-structured",
        "events": events or [],
    }
    log_path = tmp_path / "execution-log.yaml"
    log_path.write_text(yaml.dump(data, default_flow_style=False))
    return log_path


class TestStructuredLogRoundTrip:
    """Round-trip: CLI writes structured v3.0 entry, reader parses it back."""

    def test_cli_writes_structured_format_and_reader_parses_it(
        self, tmp_path, mock_schema
    ):
        """CLI writes structured YAML dict, reader returns correct PhaseEvent."""
        from des.cli.log_phase import main

        _create_execution_log(tmp_path)

        result = main(
            [
                "--project-dir",
                str(tmp_path),
                "--step-id",
                "08-01",
                "--phase",
                "GREEN",
                "--status",
                "EXECUTED",
                "--data",
                "PASS",
            ]
        )
        assert result == 0

        # Verify the YAML file contains structured dict, not a pipe-delimited string
        log_data = yaml.safe_load((tmp_path / "execution-log.yaml").read_text())
        assert log_data["schema_version"] == "3.0"
        entry = log_data["events"][0]
        assert isinstance(entry, dict), f"Expected dict, got {type(entry).__name__}"
        assert entry["sid"] == "08-01"
        assert entry["p"] == "GREEN"
        assert entry["s"] == "EXECUTED"
        assert entry["d"] == "PASS"
        assert "t" in entry

        # Reader parses it correctly
        reader = YamlExecutionLogReader()
        events = reader.read_step_events(str(tmp_path / "execution-log.yaml"), "08-01")
        assert len(events) == 1
        event = events[0]
        assert event.step_id == "08-01"
        assert event.phase_name == "GREEN"
        assert event.status == "EXECUTED"
        assert event.outcome == "PASS"
        assert event.turns_used is None
        assert event.tokens_used is None

    def test_cli_writes_structured_format_with_stats(self, tmp_path, mock_schema):
        """CLI writes structured dict with tu/tk keys for execution stats."""
        from des.cli.log_phase import main

        _create_execution_log(tmp_path)

        result = main(
            [
                "--project-dir",
                str(tmp_path),
                "--step-id",
                "08-01",
                "--phase",
                "COMMIT",
                "--status",
                "EXECUTED",
                "--data",
                "PASS",
                "--turns-used",
                "25",
                "--tokens-used",
                "80000",
            ]
        )
        assert result == 0

        log_data = yaml.safe_load((tmp_path / "execution-log.yaml").read_text())
        entry = log_data["events"][0]
        assert isinstance(entry, dict)
        assert entry["tu"] == 25
        assert entry["tk"] == 80000

        reader = YamlExecutionLogReader()
        events = reader.read_step_events(str(tmp_path / "execution-log.yaml"), "08-01")
        assert len(events) == 1
        assert events[0].turns_used == 25
        assert events[0].tokens_used == 80000

    def test_reader_handles_v2_pipe_format_backward_compat(self, tmp_path):
        """Reader parses v2.0 pipe-delimited strings in log with schema_version '2.0'."""
        _create_execution_log(
            tmp_path,
            schema_version="2.0",
            events=[
                "08-01|PREPARE|EXECUTED|PASS|2026-02-11T10:00:00Z",
                "08-01|GREEN|EXECUTED|PASS|2026-02-11T10:05:00Z",
            ],
        )

        reader = YamlExecutionLogReader()
        events = reader.read_step_events(str(tmp_path / "execution-log.yaml"), "08-01")
        assert len(events) == 2
        assert events[0].phase_name == "PREPARE"
        assert events[1].phase_name == "GREEN"
