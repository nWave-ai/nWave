"""Unit tests for des.cli.log_phase CLI module.

Tests the log_phase CLI tool that appends structured JSON objects (v3.0 format)
to execution-log.json with real UTC timestamps. All tests use tmp_path fixture
and mock get_tdd_schema.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from des.domain.tdd_schema import TDDSchema


@pytest.fixture()
def mock_schema():
    """Patch TDDSchemaLoader.load in the log_phase module to return a test schema."""
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
    with patch("des.cli.log_phase.TDDSchemaLoader") as mock_loader_cls:
        mock_loader_cls.return_value.load.return_value = schema
        yield schema


def _create_execution_log(
    tmp_path, schema_version="2.0", project_id="test", events=None
):
    """Helper to create a minimal execution-log.json in tmp_path."""
    data = {
        "schema_version": schema_version,
        "project_id": project_id,
        "events": events or [],
    }
    log_path = tmp_path / "execution-log.json"
    log_path.write_text(json.dumps(data, indent=2))
    return log_path


class TestLogPhaseValidExecutedEntry:
    """Test that a valid EXECUTED entry is appended as structured dict with real timestamp."""

    def test_valid_executed_entry_appended_with_real_timestamp(
        self, tmp_path, mock_schema, capsys
    ):
        from des.cli.log_phase import main

        _create_execution_log(tmp_path)
        before = datetime.now(timezone.utc).replace(microsecond=0)

        result = main(
            [
                "--project-dir",
                str(tmp_path),
                "--step-id",
                "01-01",
                "--phase",
                "PREPARE",
                "--status",
                "EXECUTED",
                "--data",
                "PASS",
            ]
        )

        after = datetime.now(timezone.utc).replace(microsecond=0)

        assert result == 0

        log_data = json.loads((tmp_path / "execution-log.json").read_text())
        events = log_data["events"]
        assert len(events) == 1

        entry = events[0]
        assert isinstance(entry, dict)
        assert entry["sid"] == "01-01"
        assert entry["p"] == "PREPARE"
        assert entry["s"] == "EXECUTED"
        assert entry["d"] == "PASS"

        timestamp = datetime.strptime(entry["t"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        assert before <= timestamp <= after

        captured = capsys.readouterr()
        assert "sid=01-01" in captured.out
        assert "p=PREPARE" in captured.out


class TestLogPhaseValidSkippedEntry:
    """Test that a valid SKIPPED entry with a recognized prefix is accepted."""

    def test_valid_skipped_entry_with_prefix(self, tmp_path, mock_schema, capsys):
        from des.cli.log_phase import main

        _create_execution_log(tmp_path)

        result = main(
            [
                "--project-dir",
                str(tmp_path),
                "--step-id",
                "02-01",
                "--phase",
                "REVIEW",
                "--status",
                "SKIPPED",
                "--data",
                "NOT_APPLICABLE: no tests needed",
            ]
        )

        assert result == 0

        log_data = json.loads((tmp_path / "execution-log.json").read_text())
        events = log_data["events"]
        assert len(events) == 1
        entry = events[0]
        assert isinstance(entry, dict)
        assert entry["sid"] == "02-01"
        assert entry["p"] == "REVIEW"
        assert entry["s"] == "SKIPPED"
        assert entry["d"] == "NOT_APPLICABLE: no tests needed"


class TestLogPhaseInvalidPhaseName:
    """Test that an invalid phase name is rejected with exit code 1."""

    def test_invalid_phase_name_rejected(self, tmp_path, mock_schema, capsys):
        from des.cli.log_phase import main

        _create_execution_log(tmp_path)

        result = main(
            [
                "--project-dir",
                str(tmp_path),
                "--step-id",
                "01-01",
                "--phase",
                "BOGUS",
                "--status",
                "EXECUTED",
                "--data",
                "PASS",
            ]
        )

        assert result == 1

        captured = capsys.readouterr()
        assert "BOGUS" in captured.out or "BOGUS" in captured.err


class TestLogPhaseSkippedWithoutValidPrefix:
    """Test that SKIPPED without a valid prefix is rejected with exit code 1."""

    def test_skipped_without_valid_prefix_rejected(self, tmp_path, mock_schema, capsys):
        from des.cli.log_phase import main

        _create_execution_log(tmp_path)

        result = main(
            [
                "--project-dir",
                str(tmp_path),
                "--step-id",
                "01-01",
                "--phase",
                "PREPARE",
                "--status",
                "SKIPPED",
                "--data",
                "just because",
            ]
        )

        assert result == 1


class TestLogPhaseMissingLogFile:
    """Test that a missing execution-log.json is rejected with exit code 1."""

    def test_missing_log_file_rejected(self, tmp_path, mock_schema, capsys):
        from des.cli.log_phase import main

        # Do NOT create execution-log.json in tmp_path

        result = main(
            [
                "--project-dir",
                str(tmp_path),
                "--step-id",
                "01-01",
                "--phase",
                "PREPARE",
                "--status",
                "EXECUTED",
                "--data",
                "PASS",
            ]
        )

        assert result == 1


class TestLogPhaseYamlStructurePreserved:
    """Test that YAML structure is preserved and schema_version bumped to 3.0."""

    def test_yaml_structure_preserved(self, tmp_path, mock_schema):
        from des.cli.log_phase import main

        _create_execution_log(tmp_path, schema_version="2.0", project_id="test")

        main(
            [
                "--project-dir",
                str(tmp_path),
                "--step-id",
                "01-01",
                "--phase",
                "GREEN",
                "--status",
                "EXECUTED",
                "--data",
                "PASS",
            ]
        )

        log_data = json.loads((tmp_path / "execution-log.json").read_text())
        assert log_data["schema_version"] == "3.0"
        assert log_data["project_id"] == "test"
        assert len(log_data["events"]) == 1


class TestLogPhaseMultipleEntriesSequential:
    """Test that multiple structured entries are appended sequentially in order."""

    def test_multiple_entries_appended_sequentially(self, tmp_path, mock_schema):
        from des.cli.log_phase import main

        _create_execution_log(tmp_path)

        phases = ["PREPARE", "RED_ACCEPTANCE", "GREEN"]
        for phase in phases:
            result = main(
                [
                    "--project-dir",
                    str(tmp_path),
                    "--step-id",
                    "01-01",
                    "--phase",
                    phase,
                    "--status",
                    "EXECUTED",
                    "--data",
                    "PASS",
                ]
            )
            assert result == 0

        log_data = json.loads((tmp_path / "execution-log.json").read_text())
        events = log_data["events"]
        assert len(events) == 3

        for i, phase in enumerate(phases):
            assert isinstance(events[i], dict)
            assert events[i]["p"] == phase


class TestLogPhaseConcurrentWritesNoLostUpdates:
    """Regression for #51: concurrent des-log-phase appends must not lose entries.

    The original read-modify-write (read_text -> append -> write_text) had no
    file locking, so interleaved writers overwrote each other (last-writer-wins)
    and DES audit-trail entries silently vanished during parallel DELIVER waves.
    With an exclusive lock held across the whole RMW, every concurrent append
    lands exactly once.
    """

    def test_concurrent_appends_all_land(self, tmp_path, mock_schema):
        import threading

        from des.cli.log_phase import main

        _create_execution_log(tmp_path)

        num_threads = 12
        appends_per_thread = 8
        expected = num_threads * appends_per_thread

        barrier = threading.Barrier(num_threads)
        errors: list[int] = []

        def worker(tid: int) -> None:
            # Release all writers simultaneously to maximise interleaving.
            barrier.wait()
            for i in range(appends_per_thread):
                rc = main(
                    [
                        "--project-dir",
                        str(tmp_path),
                        "--step-id",
                        f"{tid:02d}-{i:02d}",
                        "--phase",
                        "GREEN",
                        "--status",
                        "EXECUTED",
                        "--data",
                        "PASS",
                    ]
                )
                if rc != 0:
                    errors.append(rc)

        threads = [
            threading.Thread(target=worker, args=(t,)) for t in range(num_threads)
        ]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert not errors, f"some appends returned non-zero: {errors}"

        log_data = json.loads((tmp_path / "execution-log.json").read_text())
        events = log_data["events"]
        assert len(events) == expected, (
            f"expected {expected} events, found {len(events)} — "
            "lost updates indicate the concurrent read-modify-write is not "
            "serialized"
        )
        # Each (tid, i) pair carries a unique step-id; no losses, no duplicates.
        unique_sids = {e["sid"] for e in events}
        assert len(unique_sids) == expected


class TestLogPhaseExecStats:
    """Test that --turns-used and --tokens-used produce structured entries with tu/tk."""

    def test_entry_with_stats_has_tu_tk_keys(self, tmp_path, mock_schema, capsys):
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

        log_data = json.loads((tmp_path / "execution-log.json").read_text())
        entry = log_data["events"][0]
        assert isinstance(entry, dict)
        assert entry["tu"] == 12
        assert entry["tk"] == 45000

        captured = capsys.readouterr()
        assert "tu=12" in captured.out
        assert "tk=45000" in captured.out

    def test_entry_without_stats_has_no_tu_tk_keys(self, tmp_path, mock_schema, capsys):
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
            ]
        )

        assert result == 0

        log_data = json.loads((tmp_path / "execution-log.json").read_text())
        entry = log_data["events"][0]
        assert isinstance(entry, dict)
        assert "tu" not in entry
        assert "tk" not in entry
