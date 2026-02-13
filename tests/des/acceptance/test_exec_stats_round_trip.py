"""Acceptance test: execution statistics round-trip through CLI and reader.

Validates that turns_used and tokens_used flow correctly from CLI entry
through YAML persistence to reader parsing, and that backward compatibility
with the 5-field format is preserved.
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
            "REVIEW",
            "REFACTOR_CONTINUOUS",
            "COMMIT",
        ),
        valid_skip_prefixes=("NOT_APPLICABLE:",),
        blocking_skip_prefixes=("APPROVED_SKIP:",),
    )
    with patch("des.cli.log_phase.get_tdd_schema", return_value=schema):
        yield schema


def _create_execution_log(tmp_path, events=None):
    """Helper to create a minimal execution-log.yaml."""
    data = {
        "schema_version": "2.0",
        "project_id": "test-exec-stats",
        "events": events or [],
    }
    log_path = tmp_path / "execution-log.yaml"
    log_path.write_text(yaml.dump(data, default_flow_style=False))
    return log_path


class TestExecStatsRoundTrip:
    """Round-trip: CLI writes entry with stats, reader parses them back."""

    def test_cli_writes_stats_and_reader_parses_them(self, tmp_path, mock_schema):
        """Entry with --turns-used and --tokens-used is written and read correctly."""
        from des.cli.log_phase import main

        _create_execution_log(tmp_path)

        result = main(
            [
                "--project-dir",
                str(tmp_path),
                "--step-id",
                "07-01",
                "--phase",
                "COMMIT",
                "--status",
                "EXECUTED",
                "--data",
                "PASS",
                "--turns-used",
                "12",
                "--tokens-used",
                "45000",
            ]
        )
        assert result == 0

        reader = YamlExecutionLogReader()
        events = reader.read_step_events(str(tmp_path / "execution-log.yaml"), "07-01")

        assert len(events) == 1
        event = events[0]
        assert event.step_id == "07-01"
        assert event.phase_name == "COMMIT"
        assert event.turns_used == 12
        assert event.tokens_used == 45000

    def test_cli_without_stats_preserves_backward_compatibility(
        self, tmp_path, mock_schema
    ):
        """Entry without stats args produces 5-field format, reader returns None for stats."""
        from des.cli.log_phase import main

        _create_execution_log(tmp_path)

        result = main(
            [
                "--project-dir",
                str(tmp_path),
                "--step-id",
                "07-01",
                "--phase",
                "PREPARE",
                "--status",
                "EXECUTED",
                "--data",
                "PASS",
            ]
        )
        assert result == 0

        reader = YamlExecutionLogReader()
        events = reader.read_step_events(str(tmp_path / "execution-log.yaml"), "07-01")

        assert len(events) == 1
        event = events[0]
        assert event.step_id == "07-01"
        assert event.phase_name == "PREPARE"
        assert event.turns_used is None
        assert event.tokens_used is None

    def test_reader_handles_mixed_old_and_new_format_events(self, tmp_path):
        """Reader correctly parses a log with both 5-field and 7-field entries."""
        log_path = _create_execution_log(
            tmp_path,
            events=[
                "07-01|PREPARE|EXECUTED|PASS|2026-02-11T00:00:00Z",
                "07-01|COMMIT|EXECUTED|PASS|2026-02-11T00:30:00Z|15|50000",
            ],
        )

        reader = YamlExecutionLogReader()
        events = reader.read_step_events(str(log_path), "07-01")

        assert len(events) == 2

        old_event = events[0]
        assert old_event.phase_name == "PREPARE"
        assert old_event.turns_used is None
        assert old_event.tokens_used is None

        new_event = events[1]
        assert new_event.phase_name == "COMMIT"
        assert new_event.turns_used == 15
        assert new_event.tokens_used == 50000
