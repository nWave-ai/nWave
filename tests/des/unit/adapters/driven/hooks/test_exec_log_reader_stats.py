"""Unit tests for YamlExecutionLogReader parsing of execution statistics fields.

Validates that the reader correctly passes through turns_used and tokens_used
from pipe-delimited event strings via PhaseEventParser.

Test Budget: 2 behaviors x 2 = 4 max tests. Using 2.
"""

from __future__ import annotations

import yaml

from des.adapters.driven.hooks.yaml_execution_log_reader import YamlExecutionLogReader


def _write_log(tmp_path, events):
    """Write an execution-log.yaml with given events."""
    log_path = tmp_path / "execution-log.yaml"
    data = {"project_id": "test", "events": events}
    log_path.write_text(yaml.dump(data, default_flow_style=False))
    return str(log_path)


class TestYamlExecutionLogReaderExecStats:
    """YamlExecutionLogReader passes through execution statistics from events."""

    def test_read_step_events_returns_stats_from_7_field_entries(self, tmp_path):
        """Reader returns turns_used and tokens_used for 7-field format entries."""
        log_path = _write_log(
            tmp_path,
            [
                "07-01|COMMIT|EXECUTED|PASS|2026-02-11T00:30:00Z|15|50000",
            ],
        )

        reader = YamlExecutionLogReader()
        events = reader.read_step_events(log_path, "07-01")

        assert len(events) == 1
        assert events[0].turns_used == 15
        assert events[0].tokens_used == 50000

    def test_read_all_events_handles_mixed_formats(self, tmp_path):
        """Reader returns correct stats for mixed 5-field and 7-field events."""
        log_path = _write_log(
            tmp_path,
            [
                "07-01|PREPARE|EXECUTED|PASS|2026-02-11T00:00:00Z",
                "07-01|COMMIT|EXECUTED|PASS|2026-02-11T00:30:00Z|10|30000",
            ],
        )

        reader = YamlExecutionLogReader()
        events = reader.read_all_events(log_path)

        assert len(events) == 2
        assert events[0].turns_used is None
        assert events[0].tokens_used is None
        assert events[1].turns_used == 10
        assert events[1].tokens_used == 30000
