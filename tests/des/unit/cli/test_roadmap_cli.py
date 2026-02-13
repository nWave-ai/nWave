"""Port-to-port tests for roadmap CLI (init + validate)."""

from __future__ import annotations

import yaml

from des.cli.roadmap import main


class TestInit:
    """Tests for the 'init' subcommand."""

    def test_init_with_project_id_and_goal(self, capsys):
        """init with project-id and goal produces valid YAML to stdout."""
        rc = main(["init", "--project-id", "test-feature", "--goal", "Test goal"])
        assert rc == 0
        output = capsys.readouterr().out
        data = yaml.safe_load(output)
        assert data["roadmap"]["project_id"] == "test-feature"
        assert data["phases"]
        assert data["roadmap"]["total_steps"] >= 1

    def test_init_with_output_file(self, capsys, tmp_path):
        """init with --output writes file."""
        out_file = tmp_path / "roadmap.yaml"
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
        data = yaml.safe_load(out_file.read_text())
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
        data = yaml.safe_load(capsys.readouterr().out)
        assert data["roadmap"]["phases"] == 3
        assert data["roadmap"]["total_steps"] == 6
        assert len(data["phases"]) == 3
        assert len(data["phases"][0]["steps"]) == 2
        assert len(data["phases"][1]["steps"]) == 3
        assert len(data["phases"][2]["steps"]) == 1
        # Step IDs match phase
        assert data["phases"][0]["steps"][0]["id"] == "01-01"
        assert data["phases"][1]["steps"][2]["id"] == "02-03"
        assert data["phases"][2]["steps"][0]["id"] == "03-01"

    def test_init_output_passes_validate(self, tmp_path):
        """Round-trip: init output passes validate."""
        out_file = tmp_path / "roadmap.yaml"
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
        data = yaml.safe_load(capsys.readouterr().out)
        assert data["roadmap"]["phases"] == 3
        assert len(data["phases"]) == 3


class TestValidate:
    """Tests for the 'validate' subcommand."""

    def _write_roadmap(self, tmp_path, data):
        """Helper to write a roadmap YAML file."""
        path = tmp_path / "roadmap.yaml"
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        return path

    def _valid_roadmap(self):
        """Return a minimal valid roadmap dict."""
        return {
            "roadmap": {
                "project_id": "test",
                "created_at": "2026-01-01T00:00:00Z",
                "total_steps": 2,
                "phases": 1,
            },
            "phases": [
                {
                    "id": "01",
                    "name": "Phase One",
                    "steps": [
                        {
                            "id": "01-01",
                            "name": "Step one",
                            "criteria": "criterion one",
                        },
                        {
                            "id": "01-02",
                            "name": "Step two",
                            "criteria": "criterion two",
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
        """Declared phases count mismatch returns exit 1."""
        data = self._valid_roadmap()
        data["roadmap"]["phases"] = 5
        path = self._write_roadmap(tmp_path, data)
        assert main(["validate", str(path)]) == 1

    def test_criteria_word_count_warning(self, tmp_path, capsys):
        """Criteria exceeding word count produces warning but exit 0."""
        data = self._valid_roadmap()
        long_criteria = " ".join(["word"] * 35)
        data["phases"][0]["steps"][0]["criteria"] = long_criteria
        path = self._write_roadmap(tmp_path, data)
        rc = main(["validate", str(path)])
        assert rc == 0  # Warnings don't fail validation
        output = capsys.readouterr().out
        assert "WARNING" in output

    def test_missing_file_exit_2(self, tmp_path):
        """Non-existent file returns exit 2."""
        rc = main(["validate", str(tmp_path / "nonexistent.yaml")])
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
        """Too many criteria (>5 semicolons) produces warning."""
        data = self._valid_roadmap()
        data["phases"][0]["steps"][0]["criteria"] = "a; b; c; d; e; f; g"
        path = self._write_roadmap(tmp_path, data)
        rc = main(["validate", str(path)])
        assert rc == 0
        assert "TOO_MANY_CRITERIA" in capsys.readouterr().out
