"""Unit tests for YamlExecutionLogReader v3.0 structured format support.

Tests that the reader auto-detects schema_version and correctly parses
both v2.0 (pipe-delimited) and v3.0 (structured dict) event formats.

Test Budget: 3 behaviors x 2 = 6 max tests. Using 4.
- Reader reads v3.0 structured events (1 test)
- Reader reads v3.0 with stats tu/tk (1 test)
- Reader auto-detects v2.0 vs v3.0 via schema_version (1 test)
- Reader handles mixed format in single log (1 test)
"""

from __future__ import annotations

import yaml

from des.adapters.driven.hooks.yaml_execution_log_reader import YamlExecutionLogReader


def _write_log(tmp_path, events, schema_version="3.0"):
    """Write an execution-log.yaml with given events and schema_version."""
    log_path = tmp_path / "execution-log.yaml"
    data = {"schema_version": schema_version, "project_id": "test", "events": events}
    log_path.write_text(yaml.dump(data, default_flow_style=False))
    return str(log_path)


class TestYamlExecutionLogReaderV3:
    """YamlExecutionLogReader supports v3.0 structured YAML events."""

    def test_read_step_events_parses_v3_structured_dicts(self, tmp_path):
        """Reader parses v3.0 structured dict events into PhaseEvents."""
        log_path = _write_log(
            tmp_path,
            [
                {
                    "sid": "08-01",
                    "p": "PREPARE",
                    "s": "EXECUTED",
                    "d": "PASS",
                    "t": "2026-02-11T10:00:00Z",
                },
                {
                    "sid": "08-01",
                    "p": "GREEN",
                    "s": "EXECUTED",
                    "d": "PASS",
                    "t": "2026-02-11T10:05:00Z",
                },
                {
                    "sid": "09-01",
                    "p": "PREPARE",
                    "s": "EXECUTED",
                    "d": "PASS",
                    "t": "2026-02-11T10:10:00Z",
                },
            ],
        )

        reader = YamlExecutionLogReader()
        events = reader.read_step_events(log_path, "08-01")

        assert len(events) == 2
        assert events[0].step_id == "08-01"
        assert events[0].phase_name == "PREPARE"
        assert events[1].phase_name == "GREEN"

    def test_read_step_events_parses_v3_with_stats(self, tmp_path):
        """Reader extracts turns_used and tokens_used from v3.0 tu/tk keys."""
        log_path = _write_log(
            tmp_path,
            [
                {
                    "sid": "08-01",
                    "p": "COMMIT",
                    "s": "EXECUTED",
                    "d": "PASS",
                    "t": "2026-02-11T10:30:00Z",
                    "tu": 20,
                    "tk": 60000,
                },
            ],
        )

        reader = YamlExecutionLogReader()
        events = reader.read_step_events(log_path, "08-01")

        assert len(events) == 1
        assert events[0].turns_used == 20
        assert events[0].tokens_used == 60000

    def test_read_all_events_auto_detects_v2_pipe_format(self, tmp_path):
        """Reader with schema_version '2.0' parses pipe-delimited strings."""
        log_path = _write_log(
            tmp_path,
            [
                "08-01|PREPARE|EXECUTED|PASS|2026-02-11T10:00:00Z",
                "08-01|GREEN|EXECUTED|PASS|2026-02-11T10:05:00Z",
            ],
            schema_version="2.0",
        )

        reader = YamlExecutionLogReader()
        events = reader.read_all_events(log_path)

        assert len(events) == 2
        assert events[0].phase_name == "PREPARE"
        assert events[1].phase_name == "GREEN"

    def test_read_all_events_handles_mixed_string_and_dict(self, tmp_path):
        """Reader handles logs containing both string and dict events (auto-detect per item)."""
        log_path = _write_log(
            tmp_path,
            [
                "08-01|PREPARE|EXECUTED|PASS|2026-02-11T10:00:00Z",
                {
                    "sid": "08-01",
                    "p": "GREEN",
                    "s": "EXECUTED",
                    "d": "PASS",
                    "t": "2026-02-11T10:05:00Z",
                },
            ],
            schema_version="3.0",
        )

        reader = YamlExecutionLogReader()
        events = reader.read_all_events(log_path)

        assert len(events) == 2
        assert events[0].phase_name == "PREPARE"
        assert events[1].phase_name == "GREEN"
