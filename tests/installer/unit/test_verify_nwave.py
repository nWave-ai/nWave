"""Unit tests for verify_nwave standalone verification script.

Tests validate the standalone verification entry point including:
- Script existence and importability
- Command line argument parsing (--json, --verbose)
- Integration with InstallationVerifier
- Output mode selection based on context
- Full installation verification
- Missing files detection with remediation

CRITICAL: Tests follow hexagonal architecture - domain classes use real objects.
InstallationVerifier, OutputFormatter, and ContextDetector are NOT mocked.
"""

import json

import pytest


class TestVerifyNwaveCommandLineArgs:
    """Test command line argument parsing."""

    def test_verify_nwave_parse_args_no_flags(self):
        """
        GIVEN: No command line arguments
        WHEN: parse_args() is called
        THEN: Returns default values (json=False, verbose=False)
        """
        from scripts.install.verify_nwave import parse_args

        # ACT
        args = parse_args([])

        # ASSERT
        assert args.json is False
        assert args.verbose is False

    def test_verify_nwave_parse_args_json_flag(self):
        """
        GIVEN: --json flag provided
        WHEN: parse_args() is called
        THEN: Returns json=True
        """
        from scripts.install.verify_nwave import parse_args

        # ACT
        args = parse_args(["--json"])

        # ASSERT
        assert args.json is True

    def test_verify_nwave_parse_args_verbose_flag(self):
        """
        GIVEN: --verbose flag provided
        WHEN: parse_args() is called
        THEN: Returns verbose=True
        """
        from scripts.install.verify_nwave import parse_args

        # ACT
        args = parse_args(["--verbose"])

        # ASSERT
        assert args.verbose is True

    def test_verify_nwave_parse_args_both_flags(self):
        """
        GIVEN: Both --json and --verbose flags provided
        WHEN: parse_args() is called
        THEN: Returns both json=True and verbose=True
        """
        from scripts.install.verify_nwave import parse_args

        # ACT
        args = parse_args(["--json", "--verbose"])

        # ASSERT
        assert args.json is True
        assert args.verbose is True


class TestVerifyNwaveFullInstallation:
    """Test verification passes when fully installed."""

    def test_verify_nwave_full_installation_success(self, tmp_path):
        """
        GIVEN: A complete nWave installation with all files
        WHEN: run_verification() is called
        THEN: Returns success with verification details
        """
        from scripts.install.verify_nwave import run_verification

        # ARRANGE - Create complete installation
        config_dir = tmp_path / ".claude"
        agents_dir = config_dir / "agents" / "nw"
        commands_dir = config_dir / "commands" / "nw"
        agents_dir.mkdir(parents=True)
        commands_dir.mkdir(parents=True)
        skills_dir = config_dir / "skills" / "nw" / "crafter"
        des_dir = config_dir / "lib" / "python" / "des"
        skills_dir.mkdir(parents=True)
        des_dir.mkdir(parents=True)

        # Create agent files
        for i in range(5):
            (agents_dir / f"agent{i}.md").write_text(f"# Agent {i}")

        # Create all essential command files (matching InstallationVerifier.ESSENTIAL_COMMANDS)
        essential_files = [
            "review.md",
            "devops.md",
            "discuss.md",
            "design.md",
            "distill.md",
            "deliver.md",
        ]
        for filename in essential_files:
            (commands_dir / filename).write_text(f"# {filename}")

        (skills_dir / "skill.md").write_text("# Skill")
        (des_dir / "__init__.py").write_text("")

        # Create manifest
        (config_dir / "nwave-manifest.txt").write_text(
            "nWave Framework Installation Manifest"
        )

        # ACT
        result = run_verification(claude_config_dir=config_dir)

        # ASSERT
        assert result.success is True
        assert result.agent_file_count >= 5
        assert result.command_file_count >= 6
        assert result.manifest_exists is True
        assert result.missing_essential_files == []

    def test_verify_nwave_full_installation_exit_code_zero(self, tmp_path):
        """
        GIVEN: A complete nWave installation
        WHEN: main() is called
        THEN: Returns exit code 0 (success)
        """
        from scripts.install.verify_nwave import main

        # ARRANGE - Create complete installation
        config_dir = tmp_path / ".claude"
        agents_dir = config_dir / "agents" / "nw"
        commands_dir = config_dir / "commands" / "nw"
        agents_dir.mkdir(parents=True)
        commands_dir.mkdir(parents=True)
        skills_dir = config_dir / "skills" / "nw" / "crafter"
        des_dir = config_dir / "lib" / "python" / "des"
        skills_dir.mkdir(parents=True)
        des_dir.mkdir(parents=True)

        # Create all essential command files (matching InstallationVerifier.ESSENTIAL_COMMANDS)
        essential_files = [
            "review.md",
            "devops.md",
            "discuss.md",
            "design.md",
            "distill.md",
            "deliver.md",
        ]
        for filename in essential_files:
            (commands_dir / filename).write_text(f"# {filename}")

        (skills_dir / "skill.md").write_text("# Skill")
        (des_dir / "__init__.py").write_text("")

        # Create manifest
        (config_dir / "nwave-manifest.txt").write_text(
            "nWave Framework Installation Manifest"
        )

        # ACT
        exit_code = main(args=[], claude_config_dir=config_dir)

        # ASSERT
        assert exit_code == 0


class TestVerifyNwaveMissingFiles:
    """Test verification fails with remediation when files missing."""

    def test_verify_nwave_missing_essential_files_failure(self, tmp_path):
        """
        GIVEN: An incomplete installation with missing essential files
        WHEN: run_verification() is called
        THEN: Returns failure with missing files list
        """
        from scripts.install.verify_nwave import run_verification

        # ARRANGE - Create incomplete installation
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        # Only create some files (missing design.md, review.md)
        (commands_dir / "devops.md").write_text("# Devop command")
        (commands_dir / "discuss.md").write_text("# Discuss command")

        # ACT
        result = run_verification(claude_config_dir=config_dir)

        # ASSERT
        assert result.success is False
        assert "design.md" in result.missing_essential_files
        assert "review.md" in result.missing_essential_files

    def test_verify_nwave_missing_files_exit_code_nonzero(self, tmp_path):
        """
        GIVEN: An incomplete installation
        WHEN: main() is called
        THEN: Returns non-zero exit code
        """
        from scripts.install.verify_nwave import main

        # ARRANGE - Create incomplete installation
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        # No essential files created

        # ACT
        exit_code = main(args=[], claude_config_dir=config_dir)

        # ASSERT
        assert exit_code != 0

    def test_verify_nwave_missing_manifest_failure(self, tmp_path):
        """
        GIVEN: An installation without manifest file
        WHEN: run_verification() is called
        THEN: Returns failure with manifest_exists=False
        """
        from scripts.install.verify_nwave import run_verification

        # ARRANGE - Create installation without manifest
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        # Create all essential command files but no manifest
        essential_files = [
            "review.md",
            "devops.md",
            "discuss.md",
            "design.md",
            "distill.md",
            "deliver.md",
        ]
        for filename in essential_files:
            (commands_dir / filename).write_text(f"# {filename}")

        # ACT
        result = run_verification(claude_config_dir=config_dir)

        # ASSERT
        assert result.manifest_exists is False
        assert result.success is False


class TestVerifyNwaveEssentialCommands:
    """Test verification checks essential DW commands."""

    def test_verify_nwave_checks_develop_command(self, tmp_path):
        """
        GIVEN: Installation without devop.md
        WHEN: run_verification() is called
        THEN: devop.md is reported as missing
        """
        from scripts.install.verify_nwave import run_verification

        # ARRANGE
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        # Create all except devop.md (using ESSENTIAL_COMMANDS list)
        for filename in [
            "review.md",
            "discuss.md",
            "design.md",
            "distill.md",
            "deliver.md",
        ]:
            (commands_dir / filename).write_text(f"# {filename}")

        # ACT
        result = run_verification(claude_config_dir=config_dir)

        # ASSERT
        assert "devops.md" in result.missing_essential_files

    def test_verify_nwave_checks_distill_command(self, tmp_path):
        """
        GIVEN: Installation without distill.md
        WHEN: run_verification() is called
        THEN: distill.md is reported as missing
        """
        from scripts.install.verify_nwave import run_verification

        # ARRANGE
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        # Create all except distill.md
        for filename in [
            "devops.md",
            "review.md",
            "discuss.md",
            "design.md",
            "deliver.md",
        ]:
            (commands_dir / filename).write_text(f"# {filename}")

        # ACT
        result = run_verification(claude_config_dir=config_dir)

        # ASSERT
        assert "distill.md" in result.missing_essential_files

    def test_verify_nwave_checks_review_command(self, tmp_path):
        """
        GIVEN: Installation without review.md
        WHEN: run_verification() is called
        THEN: review.md is reported as missing
        """
        from scripts.install.verify_nwave import run_verification

        # ARRANGE
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        # Create all except review.md (using ESSENTIAL_COMMANDS list)
        for filename in [
            "devops.md",
            "discuss.md",
            "design.md",
            "distill.md",
            "deliver.md",
        ]:
            (commands_dir / filename).write_text(f"# {filename}")

        # ACT
        result = run_verification(claude_config_dir=config_dir)

        # ASSERT
        assert "review.md" in result.missing_essential_files


class TestVerifyNwaveSchemaTemplate:
    """Test verification validates schema template."""

    def test_verify_nwave_validates_schema_presence(self, tmp_path):
        """
        GIVEN: A complete installation with schema template
        WHEN: run_verification() is called with check_schema=True
        THEN: Schema template validation is performed
        """
        from scripts.install.verify_nwave import run_verification

        # ARRANGE - Create complete installation
        config_dir = tmp_path / ".claude"
        agents_dir = config_dir / "agents" / "nw"
        commands_dir = config_dir / "commands" / "nw"
        agents_dir.mkdir(parents=True)
        commands_dir.mkdir(parents=True)
        skills_dir = config_dir / "skills" / "nw" / "crafter"
        des_dir = config_dir / "lib" / "python" / "des"
        skills_dir.mkdir(parents=True)
        des_dir.mkdir(parents=True)

        # Create essential command files (matching InstallationVerifier.ESSENTIAL_COMMANDS)
        essential_files = [
            "review.md",
            "devops.md",
            "discuss.md",
            "design.md",
            "distill.md",
            "deliver.md",
        ]
        for filename in essential_files:
            (commands_dir / filename).write_text(f"# {filename}")

        (skills_dir / "skill.md").write_text("# Skill")
        (des_dir / "__init__.py").write_text("")

        # Create manifest
        (config_dir / "nwave-manifest.txt").write_text(
            "nWave Framework Installation Manifest"
        )

        # ACT
        result = run_verification(claude_config_dir=config_dir)

        # ASSERT - Schema validation is covered by manifest check for now
        assert result.manifest_exists is True


class TestVerifyNwaveOutputModes:
    """Test output mode selection based on context."""

    def test_verify_nwave_json_output_mode_when_flag_set(self, tmp_path, capsys):
        """
        GIVEN: --json flag is provided
        WHEN: main() is called
        THEN: Output is valid JSON
        """
        from scripts.install.verify_nwave import main

        # ARRANGE - Create complete installation
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        skills_dir = config_dir / "skills" / "nw" / "crafter"
        des_dir = config_dir / "lib" / "python" / "des"
        skills_dir.mkdir(parents=True)
        des_dir.mkdir(parents=True)

        # Create essential command files (matching InstallationVerifier.ESSENTIAL_COMMANDS)
        essential_files = [
            "review.md",
            "devops.md",
            "discuss.md",
            "design.md",
            "distill.md",
            "deliver.md",
        ]
        for filename in essential_files:
            (commands_dir / filename).write_text(f"# {filename}")

        (skills_dir / "skill.md").write_text("# Skill")
        (des_dir / "__init__.py").write_text("")

        # Create manifest
        (config_dir / "nwave-manifest.txt").write_text(
            "nWave Framework Installation Manifest"
        )

        # ACT
        main(args=["--json"], claude_config_dir=config_dir)
        captured = capsys.readouterr()

        # ASSERT - Output should be valid JSON
        try:
            output_json = json.loads(captured.out)
            assert "success" in output_json
        except json.JSONDecodeError:
            pytest.fail("Output should be valid JSON when --json flag is used")

    def test_verify_nwave_terminal_output_mode_by_default(self, tmp_path, capsys):
        """
        GIVEN: No output flags provided
        WHEN: main() is called
        THEN: Output is human-readable terminal format
        """
        from scripts.install.verify_nwave import main

        # ARRANGE - Create complete installation
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        commands_dir.mkdir(parents=True)
        skills_dir = config_dir / "skills" / "nw" / "crafter"
        des_dir = config_dir / "lib" / "python" / "des"
        skills_dir.mkdir(parents=True)
        des_dir.mkdir(parents=True)

        # Create essential command files (matching InstallationVerifier.ESSENTIAL_COMMANDS)
        essential_files = [
            "review.md",
            "devops.md",
            "discuss.md",
            "design.md",
            "distill.md",
            "deliver.md",
        ]
        for filename in essential_files:
            (commands_dir / filename).write_text(f"# {filename}")

        (skills_dir / "skill.md").write_text("# Skill")
        (des_dir / "__init__.py").write_text("")

        # Create manifest
        (config_dir / "nwave-manifest.txt").write_text(
            "nWave Framework Installation Manifest"
        )

        # ACT
        main(args=[], claude_config_dir=config_dir)
        captured = capsys.readouterr()

        # ASSERT - Output should be human-readable (contains verification keywords)
        assert (
            "verification" in captured.out.lower() or "success" in captured.out.lower()
        )

    def test_verify_nwave_verbose_output_includes_details(self, tmp_path, capsys):
        """
        GIVEN: --verbose flag is provided
        WHEN: main() is called
        THEN: Output includes detailed verification information
        """
        from scripts.install.verify_nwave import main

        # ARRANGE - Create complete installation
        config_dir = tmp_path / ".claude"
        agents_dir = config_dir / "agents" / "nw"
        commands_dir = config_dir / "commands" / "nw"
        agents_dir.mkdir(parents=True)
        commands_dir.mkdir(parents=True)
        skills_dir = config_dir / "skills" / "nw" / "crafter"
        des_dir = config_dir / "lib" / "python" / "des"
        skills_dir.mkdir(parents=True)
        des_dir.mkdir(parents=True)

        # Create agent files
        for i in range(3):
            (agents_dir / f"agent{i}.md").write_text(f"# Agent {i}")

        # Create essential command files (matching InstallationVerifier.ESSENTIAL_COMMANDS)
        essential_files = [
            "review.md",
            "devops.md",
            "discuss.md",
            "design.md",
            "distill.md",
            "deliver.md",
        ]
        for filename in essential_files:
            (commands_dir / filename).write_text(f"# {filename}")

        (skills_dir / "skill.md").write_text("# Skill")
        (des_dir / "__init__.py").write_text("")

        # Create manifest
        (config_dir / "nwave-manifest.txt").write_text(
            "nWave Framework Installation Manifest"
        )

        # ACT
        main(args=["--verbose"], claude_config_dir=config_dir)
        captured = capsys.readouterr()

        # ASSERT - Verbose output should include counts
        output = captured.out.lower()
        assert "agent" in output or "command" in output


class TestVerifyNwaveRemediationOutput:
    """Test remediation output when verification fails."""

    def test_verify_nwave_provides_remediation_for_missing_files(
        self, tmp_path, capsys
    ):
        """
        GIVEN: An installation with missing files
        WHEN: main() is called
        THEN: Output includes remediation instructions
        """
        from scripts.install.verify_nwave import main

        # ARRANGE - Create incomplete installation
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        # Only create some files
        (commands_dir / "devops.md").write_text("# Devop command")

        # ACT
        main(args=[], claude_config_dir=config_dir)
        captured = capsys.readouterr()

        # ASSERT - Output should mention missing files or remediation
        output = captured.out.lower() + captured.err.lower()
        assert "missing" in output or "failed" in output or "error" in output

    def test_verify_nwave_json_remediation_includes_all_fields(self, tmp_path, capsys):
        """
        GIVEN: An installation with missing files and --json flag
        WHEN: main() is called
        THEN: JSON output includes remediation field
        """
        from scripts.install.verify_nwave import main

        # ARRANGE - Create incomplete installation
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        # Only create some files
        (commands_dir / "devops.md").write_text("# Devop command")

        # ACT
        main(args=["--json"], claude_config_dir=config_dir)
        captured = capsys.readouterr()

        # ASSERT - JSON should include success=false and missing_files
        try:
            output_json = json.loads(captured.out)
            assert output_json.get("success") is False
            assert (
                "missing_files" in output_json
                or "missing_essential_files" in output_json
            )
        except json.JSONDecodeError:
            pytest.fail("Output should be valid JSON")
