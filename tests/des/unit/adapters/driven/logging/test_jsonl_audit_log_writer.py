"""Unit tests for JsonlAuditLogWriter serialization of feature_name and step_id.

Step 01-02: Update JsonlAuditLogWriter to serialize new fields correctly.

Tests verify:
- AC1: JsonlAuditLogWriter writes feature_name and step_id at JSON root level
- AC2: data dict contents written separately from feature_name/step_id
- AC3: None-valued feature_name and step_id excluded from JSON output
- AC4: JSONL file format unchanged (one JSON object per line)
"""

import json

from des.adapters.driven.logging.jsonl_audit_log_writer import JsonlAuditLogWriter
from des.ports.driven_ports.audit_log_writer import AuditEvent


def _read_all_entries(writer: JsonlAuditLogWriter) -> list[dict]:
    """Read all JSON entries from the writer's current log file."""
    log_file = writer._get_log_file()
    entries = []
    if log_file.exists():
        with open(log_file) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
    return entries


class TestJsonlAuditLogWriterSerializesNewFields:
    """Tests for feature_name and step_id serialization in JSONL output."""

    def test_ac1_writes_feature_name_and_step_id_at_json_root_level(self, tmp_path):
        """AC1: feature_name and step_id appear as top-level JSON keys."""
        writer = JsonlAuditLogWriter(log_dir=tmp_path / "logs")

        writer.log_event(
            AuditEvent(
                event_type="HOOK_PRE_TOOL_USE_ALLOWED",
                timestamp="2026-02-06T12:00:00.000Z",
                feature_name="audit-log-refactor",
                step_id="01-02",
            )
        )

        entries = _read_all_entries(writer)
        assert len(entries) == 1
        entry = entries[0]
        assert entry["feature_name"] == "audit-log-refactor"
        assert entry["step_id"] == "01-02"

    def test_ac2_data_dict_written_separately_from_feature_name_and_step_id(
        self, tmp_path
    ):
        """AC2: data dict contents are separate top-level keys, not merged with feature_name/step_id."""
        writer = JsonlAuditLogWriter(log_dir=tmp_path / "logs")

        writer.log_event(
            AuditEvent(
                event_type="SCOPE_VIOLATION",
                timestamp="2026-02-06T12:00:00.000Z",
                feature_name="user-auth",
                step_id="02-01",
                data={"severity": "WARNING", "file": "src/main.py"},
            )
        )

        entries = _read_all_entries(writer)
        entry = entries[0]
        # feature_name and step_id at root level
        assert entry["feature_name"] == "user-auth"
        assert entry["step_id"] == "02-01"
        # data dict contents also at root level (existing behavior: **event.data)
        assert entry["severity"] == "WARNING"
        assert entry["file"] == "src/main.py"

    def test_ac3_none_valued_feature_name_excluded_from_json(self, tmp_path):
        """AC3: When feature_name is None, it is not present in JSON output."""
        writer = JsonlAuditLogWriter(log_dir=tmp_path / "logs")

        writer.log_event(
            AuditEvent(
                event_type="HOOK_PRE_TOOL_USE_ALLOWED",
                timestamp="2026-02-06T12:00:00.000Z",
                feature_name=None,
                step_id="01-02",
            )
        )

        entries = _read_all_entries(writer)
        entry = entries[0]
        assert "feature_name" not in entry
        assert entry["step_id"] == "01-02"

    def test_ac3_none_valued_step_id_excluded_from_json(self, tmp_path):
        """AC3: When step_id is None, it is not present in JSON output."""
        writer = JsonlAuditLogWriter(log_dir=tmp_path / "logs")

        writer.log_event(
            AuditEvent(
                event_type="HOOK_PRE_TOOL_USE_ALLOWED",
                timestamp="2026-02-06T12:00:00.000Z",
                feature_name="audit-log-refactor",
                step_id=None,
            )
        )

        entries = _read_all_entries(writer)
        entry = entries[0]
        assert entry["feature_name"] == "audit-log-refactor"
        assert "step_id" not in entry

    def test_ac3_both_none_excluded_from_json(self, tmp_path):
        """AC3: When both feature_name and step_id are None, neither appears in JSON."""
        writer = JsonlAuditLogWriter(log_dir=tmp_path / "logs")

        writer.log_event(
            AuditEvent(
                event_type="HOOK_PRE_TOOL_USE_ALLOWED",
                timestamp="2026-02-06T12:00:00.000Z",
                feature_name=None,
                step_id=None,
            )
        )

        entries = _read_all_entries(writer)
        entry = entries[0]
        assert "feature_name" not in entry
        assert "step_id" not in entry
        # Core fields still present
        assert entry["event"] == "HOOK_PRE_TOOL_USE_ALLOWED"
        assert entry["timestamp"] == "2026-02-06T12:00:00.000Z"

    def test_ac4_jsonl_format_one_json_object_per_line(self, tmp_path):
        """AC4: Each event is one valid JSON object per line, format unchanged."""
        writer = JsonlAuditLogWriter(log_dir=tmp_path / "logs")

        writer.log_event(
            AuditEvent(
                event_type="HOOK_PRE_TOOL_USE_ALLOWED",
                timestamp="2026-02-06T12:00:00.000Z",
                feature_name="feat-a",
                step_id="01-01",
            )
        )
        writer.log_event(
            AuditEvent(
                event_type="SCOPE_VIOLATION",
                timestamp="2026-02-06T12:01:00.000Z",
                feature_name="feat-a",
                step_id="01-02",
                data={"severity": "WARNING"},
            )
        )

        log_file = writer._get_log_file()
        raw_lines = log_file.read_text().strip().split("\n")

        assert len(raw_lines) == 2
        # Each line is valid JSON
        for line in raw_lines:
            parsed = json.loads(line)
            assert isinstance(parsed, dict)
        # No multi-line JSON (compact format)
        assert "\n" not in raw_lines[0]
        assert "\n" not in raw_lines[1]
