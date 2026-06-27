"""Unit tests for des.cli.init_log CLI module.

Tests the init_log CLI tool that initializes execution-log.json with the
ADR-025 v5.0 (3-phase canon) schema. All tests use tmp_path fixture.

Test Budget: 4 distinct behaviors x 1 = 4 tests.

Behaviors:
1. Success: creates file with correct schema
2. Fails if file already exists (exit 1)
3. Fails if project directory doesn't exist (exit 1)
4. Created file has correct JSON structure
"""

from __future__ import annotations

import json

from des.cli.init_log import main


def test_creates_execution_log_successfully(tmp_path):
    """init_log creates execution-log.json with correct schema when dir exists and file absent."""
    exit_code = main(["--project-dir", str(tmp_path), "--feature-id", "my-feature"])

    assert exit_code == 0

    log_path = tmp_path / "execution-log.json"
    assert log_path.exists()

    data = json.loads(log_path.read_text())
    assert data["schema_version"] == "5.0"
    assert data["feature_id"] == "my-feature"
    assert data["events"] == []


def test_fails_if_file_already_exists(tmp_path, capsys):
    """init_log returns exit 1 when execution-log.json already exists."""
    existing = tmp_path / "execution-log.json"
    existing.write_text("{}")

    exit_code = main(["--project-dir", str(tmp_path), "--feature-id", "my-feature"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "already exists" in captured.out


def test_fails_if_project_dir_missing(tmp_path, capsys):
    """init_log returns exit 1 when project directory does not exist."""
    nonexistent = tmp_path / "nonexistent"

    exit_code = main(["--project-dir", str(nonexistent), "--feature-id", "my-feature"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "does not exist" in captured.out


def test_json_structure_is_valid(tmp_path):
    """Created execution-log.json is valid JSON with exactly 3 keys."""
    main(["--project-dir", str(tmp_path), "--feature-id", "test-feat"])

    data = json.loads((tmp_path / "execution-log.json").read_text())
    assert set(data.keys()) == {"schema_version", "feature_id", "events"}
