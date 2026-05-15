"""Port-to-port tests for roadmap CLI (init + validate)."""

from __future__ import annotations

import json
from pathlib import Path

from des.cli.roadmap import main


SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "nWave"
    / "templates"
    / "roadmap-schema.json"
)


class TestRoadmapSchema:
    """Tests for roadmap-schema.json content."""

    def test_schema_optional_step_fields_include_test_file(self):
        """roadmap-schema.json optional_fields.step must include test_file."""
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        optional_step_fields = schema["optional_fields"]["step"]
        assert "test_file" in optional_step_fields

    def test_schema_optional_step_fields_include_scenario_name(self):
        """roadmap-schema.json optional_fields.step must include scenario_name."""
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        optional_step_fields = schema["optional_fields"]["step"]
        assert "scenario_name" in optional_step_fields


class TestInit:
    """Tests for the 'init' subcommand."""

    def test_init_with_project_id_and_goal(self, capsys):
        """init with project-id and goal produces valid YAML to stdout."""
        rc = main(["init", "--project-id", "test-feature", "--goal", "Test goal"])
        assert rc == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["roadmap"]["project_id"] == "test-feature"
        assert data["phases"]
        assert data["roadmap"]["total_steps"] >= 1

    def test_init_with_output_file(self, capsys, tmp_path):
        """init with --output writes file."""
        out_file = tmp_path / "roadmap.json"
        rc = main(
            [
                "init",
                "--project-id",
                "test-proj",
                "--goal",
                "G",
                "--output",
                str(out_file),
            ]
        )
        assert rc == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["roadmap"]["project_id"] == "test-proj"

    def test_init_with_phases_and_steps(self, capsys):
        """init with --phases and --steps creates correct skeleton."""
        rc = main(
            [
                "init",
                "--project-id",
                "multi",
                "--goal",
                "G",
                "--phases",
                "3",
                "--steps",
                "01:2,02:3,03:1",
            ]
        )
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        # F-1: skeleton must NOT emit roadmap.phases int (collides with top-level
        # `phases: array`). The array length below is the canonical phase count.
        assert "phases" not in data["roadmap"]
        assert data["roadmap"]["total_steps"] == 6
        assert len(data["phases"]) == 3
        assert len(data["phases"][0]["steps"]) == 2
        assert len(data["phases"][1]["steps"]) == 3
        assert len(data["phases"][2]["steps"]) == 1
        # Step IDs match phase
        assert data["phases"][0]["steps"][0]["id"] == "01-01"
        assert data["phases"][1]["steps"][2]["id"] == "02-03"
        assert data["phases"][2]["steps"][0]["id"] == "03-01"
        # F-1: step.criteria is a JSON list (empty placeholder), not a TODO string.
        assert data["phases"][0]["steps"][0]["criteria"] == []

    def test_init_output_passes_validate(self, tmp_path):
        """Round-trip: init output passes validate."""
        out_file = tmp_path / "roadmap.json"
        rc_init = main(
            [
                "init",
                "--project-id",
                "roundtrip",
                "--goal",
                "RT",
                "--phases",
                "2",
                "--steps",
                "01:2,02:1",
                "--output",
                str(out_file),
            ]
        )
        assert rc_init == 0
        rc_validate = main(["validate", str(out_file)])
        assert rc_validate == 0

    def test_init_without_project_id_fails(self, capsys):
        """init without --project-id returns exit 2."""
        rc = main(["init", "--goal", "Missing project ID"])
        assert rc == 2
        assert "project-id" in capsys.readouterr().err.lower()

    def test_init_steps_infers_phases(self, capsys):
        """init with --steps but no explicit --phases infers phase count."""
        rc = main(
            [
                "init",
                "--project-id",
                "infer",
                "--goal",
                "G",
                "--steps",
                "01:1,02:1,03:1",
            ]
        )
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        # F-1: legacy roadmap.phases int field removed; array length is canonical.
        assert "phases" not in data["roadmap"]
        assert len(data["phases"]) == 3

    def test_init_scaffold_includes_test_file_and_scenario_name(self, capsys):
        """init scaffold includes test_file and scenario_name as empty strings."""
        rc = main(["init", "--project-id", "handoff", "--goal", "Test handoff"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        step = data["phases"][0]["steps"][0]
        assert "test_file" in step, "Step must include test_file key"
        assert "scenario_name" in step, "Step must include scenario_name key"
        assert step["test_file"] == ""
        assert step["scenario_name"] == ""

    def test_init_scaffold_test_file_and_scenario_name_across_phases(self, capsys):
        """All scaffolded steps across multiple phases include handoff fields."""
        rc = main(
            [
                "init",
                "--project-id",
                "multi-handoff",
                "--goal",
                "G",
                "--phases",
                "2",
                "--steps",
                "01:2,02:1",
            ]
        )
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        for phase in data["phases"]:
            for step in phase["steps"]:
                assert step["test_file"] == "", f"Step {step['id']} missing test_file"
                assert step["scenario_name"] == "", (
                    f"Step {step['id']} missing scenario_name"
                )


class TestValidate:
    """Tests for the 'validate' subcommand."""

    def _write_roadmap(self, tmp_path, data):
        """Helper to write a roadmap YAML file."""
        path = tmp_path / "roadmap.json"
        path.write_text(json.dumps(data, indent=2))
        return path

    def _valid_roadmap(self):
        """Return a minimal valid roadmap dict (F-1 schema: criteria as list)."""
        return {
            "roadmap": {
                "project_id": "test",
                "created_at": "2026-01-01T00:00:00Z",
                "total_steps": 2,
                # F-1: legacy roadmap.phases int omitted; array length below is canonical.
            },
            "phases": [
                {
                    "id": "01",
                    "name": "Phase One",
                    "steps": [
                        {
                            "id": "01-01",
                            "name": "Step one",
                            "criteria": ["criterion one"],
                        },
                        {
                            "id": "01-02",
                            "name": "Step two",
                            "criteria": ["criterion two"],
                        },
                    ],
                }
            ],
            "implementation_scope": {
                "source_directories": ["src/test/"],
            },
        }

    def test_valid_roadmap_exit_0(self, tmp_path):
        """Valid compact roadmap returns exit 0."""
        path = self._write_roadmap(tmp_path, self._valid_roadmap())
        assert main(["validate", str(path)]) == 0

    def test_missing_project_id_exit_1(self, tmp_path):
        """Missing roadmap.project_id returns exit 1."""
        data = self._valid_roadmap()
        del data["roadmap"]["project_id"]
        path = self._write_roadmap(tmp_path, data)
        assert main(["validate", str(path)]) == 1

    def test_invalid_phase_id_exit_1(self, tmp_path):
        """Invalid phase ID 'A1' returns exit 1."""
        data = self._valid_roadmap()
        data["phases"][0]["id"] = "A1"
        path = self._write_roadmap(tmp_path, data)
        assert main(["validate", str(path)]) == 1

    def test_invalid_step_id_exit_1(self, tmp_path):
        """Invalid step ID '1-1' returns exit 1."""
        data = self._valid_roadmap()
        data["phases"][0]["steps"][0]["id"] = "1-1"
        path = self._write_roadmap(tmp_path, data)
        assert main(["validate", str(path)]) == 1

    def test_duplicate_step_ids_exit_1(self, tmp_path):
        """Duplicate step IDs returns exit 1."""
        data = self._valid_roadmap()
        data["phases"][0]["steps"][1]["id"] = "01-01"  # Same as first
        path = self._write_roadmap(tmp_path, data)
        assert main(["validate", str(path)]) == 1

    def test_step_phase_mismatch_exit_1(self, tmp_path):
        """Step ID prefix not matching phase ID returns exit 1."""
        data = self._valid_roadmap()
        data["phases"][0]["steps"][0]["id"] = "02-01"  # Phase is 01
        path = self._write_roadmap(tmp_path, data)
        assert main(["validate", str(path)]) == 1

    def test_total_steps_mismatch_exit_1(self, tmp_path):
        """total_steps mismatch returns exit 1."""
        data = self._valid_roadmap()
        data["roadmap"]["total_steps"] = 99
        path = self._write_roadmap(tmp_path, data)
        assert main(["validate", str(path)]) == 1

    def test_phases_count_mismatch_exit_1(self, tmp_path):
        """Declared roadmap.phases int (legacy) mismatching array length errors."""
        # F-1: skeleton no longer emits this field; validator still detects
        # legacy-authored mismatches when present, preserving regression safety.
        data = self._valid_roadmap()
        data["roadmap"]["phases"] = 5  # array length is 1 → mismatch
        path = self._write_roadmap(tmp_path, data)
        assert main(["validate", str(path)]) == 1

    def test_criteria_word_count_warning(self, tmp_path, capsys):
        """Criteria exceeding word count produces warning but exit 0."""
        data = self._valid_roadmap()
        # F-1: criteria is a list[str]; place the long criterion as one element.
        long_criteria = " ".join(["word"] * 35)
        data["phases"][0]["steps"][0]["criteria"] = [long_criteria]
        path = self._write_roadmap(tmp_path, data)
        rc = main(["validate", str(path)])
        assert rc == 0  # Warnings don't fail validation
        output = capsys.readouterr().out
        assert "WARNING" in output

    def test_missing_file_exit_2(self, tmp_path):
        """Non-existent file returns exit 2."""
        rc = main(["validate", str(tmp_path / "nonexistent.json")])
        assert rc == 2

    def test_invalid_dep_reference_exit_1(self, tmp_path):
        """deps referencing non-existent step returns exit 1."""
        data = self._valid_roadmap()
        data["phases"][0]["steps"][0]["deps"] = ["99-99"]
        path = self._write_roadmap(tmp_path, data)
        assert main(["validate", str(path)]) == 1

    def test_unknown_agent_warning(self, tmp_path, capsys):
        """Unknown agent name produces warning but exit 0."""
        data = self._valid_roadmap()
        data["phases"][0]["steps"][0]["agent"] = "unknown-agent"
        path = self._write_roadmap(tmp_path, data)
        rc = main(["validate", str(path)])
        assert rc == 0
        assert "WARNING" in capsys.readouterr().out

    def test_missing_implementation_scope_warning(self, tmp_path, capsys):
        """Missing implementation_scope produces warning but exit 0."""
        data = self._valid_roadmap()
        del data["implementation_scope"]
        path = self._write_roadmap(tmp_path, data)
        rc = main(["validate", str(path)])
        assert rc == 0
        assert "WARNING" in capsys.readouterr().out

    def test_valid_deps_pass(self, tmp_path):
        """Valid deps referencing existing steps pass validation."""
        data = self._valid_roadmap()
        data["phases"][0]["steps"][1]["deps"] = ["01-01"]
        path = self._write_roadmap(tmp_path, data)
        assert main(["validate", str(path)]) == 0

    def test_no_subcommand_exit_2(self, capsys):
        """No subcommand returns exit 2."""
        rc = main([])
        assert rc == 2

    def test_unknown_subcommand_exit_2(self, capsys):
        """Unknown subcommand returns exit 2."""
        rc = main(["unknown"])
        assert rc == 2

    def test_validate_no_path_exit_2(self, capsys):
        """validate with no path returns exit 2."""
        rc = main(["validate"])
        assert rc == 2

    def test_too_many_criteria_warning(self, tmp_path, capsys):
        """Too many criteria (>5) produces warning."""
        data = self._valid_roadmap()
        # F-1: criteria is list[str]; element count is counted against max.
        data["phases"][0]["steps"][0]["criteria"] = ["a", "b", "c", "d", "e", "f", "g"]
        path = self._write_roadmap(tmp_path, data)
        rc = main(["validate", str(path)])
        assert rc == 0
        assert "TOO_MANY_CRITERIA" in capsys.readouterr().out

    def test_validate_step_with_test_file_and_scenario_name(self, tmp_path):
        """Steps with test_file and scenario_name optional fields pass validation."""
        data = self._valid_roadmap()
        data["phases"][0]["steps"][0]["test_file"] = "tests/acceptance/test_feature.py"
        data["phases"][0]["steps"][0]["scenario_name"] = "test_order_placed"
        path = self._write_roadmap(tmp_path, data)
        assert main(["validate", str(path)]) == 0
