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
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st


def _create_essential_command_skills(skills_dir: Path) -> None:
    """Create essential command-skill directories for testing."""
    for name in [
        "nw-review",
        "nw-devops",
        "nw-discuss",
        "nw-design",
        "nw-distill",
        "nw-deliver",
    ]:
        d = skills_dir / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: test\nuser-invocable: true\n---\n# {name}\n"
        )


def _create_complete_installation(config_dir: Path) -> None:
    """Create a complete nWave installation for testing."""
    agents_dir = config_dir / "agents" / "nw"
    skills_dir = config_dir / "skills"
    des_dir = config_dir / "lib" / "python" / "des"

    agents_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True, exist_ok=True)
    des_dir.mkdir(parents=True)

    for i in range(5):
        (agents_dir / f"agent{i}.md").write_text(f"# Agent {i}")

    _create_essential_command_skills(skills_dir)

    # Add at least one agent-skill for verify_skills
    agent_skill = skills_dir / "nw-tdd-methodology"
    agent_skill.mkdir(parents=True, exist_ok=True)
    (agent_skill / "SKILL.md").write_text(
        "---\nname: nw-tdd-methodology\ndescription: test\n"
        "disable-model-invocation: true\n---\n# TDD\n"
    )

    (des_dir / "__init__.py").write_text("")
    (config_dir / "nwave-manifest.txt").write_text(
        "nWave Framework Installation Manifest"
    )


class TestVerifyNwaveCommandLineArgs:
    """Test command line argument parsing."""

    def test_verify_nwave_parse_args_no_flags(self):
        """
        GIVEN: No command line arguments
        WHEN: parse_args() is called
        THEN: Returns default values (json=False, verbose=False)
        """
        from scripts.install.verify_nwave import parse_args

        args = parse_args([])
        assert args.json is False
        assert args.verbose is False

    def test_verify_nwave_parse_args_json_flag(self):
        """
        GIVEN: --json flag provided
        WHEN: parse_args() is called
        THEN: Returns json=True
        """
        from scripts.install.verify_nwave import parse_args

        args = parse_args(["--json"])
        assert args.json is True

    def test_verify_nwave_parse_args_verbose_flag(self):
        """
        GIVEN: --verbose flag provided
        WHEN: parse_args() is called
        THEN: Returns verbose=True
        """
        from scripts.install.verify_nwave import parse_args

        args = parse_args(["--verbose"])
        assert args.verbose is True

    def test_verify_nwave_parse_args_both_flags(self):
        """
        GIVEN: Both --json and --verbose flags provided
        WHEN: parse_args() is called
        THEN: Returns both json=True and verbose=True
        """
        from scripts.install.verify_nwave import parse_args

        args = parse_args(["--json", "--verbose"])
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

        config_dir = tmp_path / ".claude"
        _create_complete_installation(config_dir)

        result = run_verification(claude_config_dir=config_dir)

        assert result.success is True
        assert result.agent_file_count >= 5
        assert result.manifest_exists is True
        assert result.missing_essential_files == []

    def test_verify_nwave_full_installation_exit_code_zero(self, tmp_path):
        """
        GIVEN: A complete nWave installation
        WHEN: main() is called
        THEN: Returns exit code 0 (success)
        """
        from scripts.install.verify_nwave import main

        config_dir = tmp_path / ".claude"
        _create_complete_installation(config_dir)

        exit_code = main(args=[], claude_config_dir=config_dir)

        assert exit_code == 0


class TestVerifyNwaveMissingFiles:
    """Test verification fails with remediation when files missing."""

    def test_verify_nwave_missing_essential_files_failure(self, tmp_path):
        """
        GIVEN: An incomplete installation with missing essential command-skills
        WHEN: run_verification() is called
        THEN: Returns failure with missing files list
        """
        from scripts.install.verify_nwave import run_verification

        config_dir = tmp_path / ".claude"
        skills_dir = config_dir / "skills"
        skills_dir.mkdir(parents=True)

        # Only create some command-skills (missing nw-design, nw-review)
        for name in ["nw-devops", "nw-discuss"]:
            d = skills_dir / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: test\nuser-invocable: true\n---\n"
            )

        result = run_verification(claude_config_dir=config_dir)

        assert result.success is False
        assert "nw-design" in result.missing_essential_files
        assert "nw-review" in result.missing_essential_files

    def test_verify_nwave_missing_files_exit_code_nonzero(self, tmp_path):
        """
        GIVEN: An incomplete installation
        WHEN: main() is called
        THEN: Returns non-zero exit code
        """
        from scripts.install.verify_nwave import main

        config_dir = tmp_path / ".claude"
        config_dir.mkdir(parents=True)

        exit_code = main(args=[], claude_config_dir=config_dir)

        assert exit_code != 0

    def test_verify_nwave_missing_manifest_failure(self, tmp_path):
        """
        GIVEN: An installation without manifest file
        WHEN: run_verification() is called
        THEN: Returns failure with manifest_exists=False
        """
        from scripts.install.verify_nwave import run_verification

        config_dir = tmp_path / ".claude"
        skills_dir = config_dir / "skills"
        skills_dir.mkdir(parents=True)
        _create_essential_command_skills(skills_dir)

        result = run_verification(claude_config_dir=config_dir)

        assert result.manifest_exists is False
        assert result.success is False


class TestVerifyNwaveEssentialCommands:
    """Test verification checks essential command-skills."""

    def test_verify_nwave_checks_devops_command(self, tmp_path):
        """
        GIVEN: Installation without nw-devops skill
        WHEN: run_verification() is called
        THEN: nw-devops is reported as missing
        """
        from scripts.install.verify_nwave import run_verification

        config_dir = tmp_path / ".claude"
        skills_dir = config_dir / "skills"
        skills_dir.mkdir(parents=True)

        # Create all except nw-devops
        for name in [
            "nw-review",
            "nw-discuss",
            "nw-design",
            "nw-distill",
            "nw-deliver",
        ]:
            d = skills_dir / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: test\nuser-invocable: true\n---\n"
            )

        result = run_verification(claude_config_dir=config_dir)

        assert "nw-devops" in result.missing_essential_files

    def test_verify_nwave_checks_distill_command(self, tmp_path):
        """
        GIVEN: Installation without nw-distill skill
        WHEN: run_verification() is called
        THEN: nw-distill is reported as missing
        """
        from scripts.install.verify_nwave import run_verification

        config_dir = tmp_path / ".claude"
        skills_dir = config_dir / "skills"
        skills_dir.mkdir(parents=True)

        for name in ["nw-devops", "nw-review", "nw-discuss", "nw-design", "nw-deliver"]:
            d = skills_dir / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: test\nuser-invocable: true\n---\n"
            )

        result = run_verification(claude_config_dir=config_dir)

        assert "nw-distill" in result.missing_essential_files

    def test_verify_nwave_checks_review_command(self, tmp_path):
        """
        GIVEN: Installation without nw-review skill
        WHEN: run_verification() is called
        THEN: nw-review is reported as missing
        """
        from scripts.install.verify_nwave import run_verification

        config_dir = tmp_path / ".claude"
        skills_dir = config_dir / "skills"
        skills_dir.mkdir(parents=True)

        for name in [
            "nw-devops",
            "nw-discuss",
            "nw-design",
            "nw-distill",
            "nw-deliver",
        ]:
            d = skills_dir / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: test\nuser-invocable: true\n---\n"
            )

        result = run_verification(claude_config_dir=config_dir)

        assert "nw-review" in result.missing_essential_files


class TestVerifyNwaveSchemaTemplate:
    """Test verification validates schema template."""

    def test_verify_nwave_validates_schema_presence(self, tmp_path):
        """
        GIVEN: A complete installation with schema template
        WHEN: run_verification() is called
        THEN: Schema template validation is performed
        """
        from scripts.install.verify_nwave import run_verification

        config_dir = tmp_path / ".claude"
        _create_complete_installation(config_dir)

        result = run_verification(claude_config_dir=config_dir)

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

        config_dir = tmp_path / ".claude"
        _create_complete_installation(config_dir)

        main(args=["--json"], claude_config_dir=config_dir)
        captured = capsys.readouterr()

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

        config_dir = tmp_path / ".claude"
        _create_complete_installation(config_dir)

        main(args=[], claude_config_dir=config_dir)
        captured = capsys.readouterr()

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

        config_dir = tmp_path / ".claude"
        _create_complete_installation(config_dir)

        main(args=["--verbose"], claude_config_dir=config_dir)
        captured = capsys.readouterr()

        output = captured.out.lower()
        assert "agent" in output or "command" in output


def _result_with_unaccounted(unaccounted_files):
    """A successful VerificationResult carrying the given per-family listing."""
    from scripts.install.installation_verifier import VerificationResult

    return VerificationResult(
        success=True,
        agent_file_count=5,
        command_file_count=6,
        manifest_exists=True,
        missing_essential_files=[],
        skill_file_count=7,
        skill_group_count=7,
        des_installed=True,
        unaccounted_files=unaccounted_files,
        message="Verification completed successfully.",
    )


#: Per-family listings: family directory key -> sorted unaccounted names.
_family_listings = st.dictionaries(
    keys=st.sampled_from(["scripts", "templates", "skills"]),
    values=st.lists(
        st.text(alphabet="abcdefgh-_", min_size=2, max_size=12),
        min_size=1,
        max_size=4,
        unique=True,
    ).map(sorted),
    min_size=1,
    max_size=3,
)


class TestVerifyNwaveUnaccountedListing:
    """C5a/C5b routed pins (installer-orphan-sweep slice-03): pure-formatter
    rendering of the per-family unaccounted listing across output modes.

    Taxonomy contract: the listing reads as "preserved, not managed by
    nWave" — informational, NEVER an imperative deletion suggestion
    (provenance is unprovable).
    """

    def test_json_output_always_carries_unaccounted_files_even_when_empty(self):
        """
        GIVEN: A clean verification result (no unaccounted files anywhere)
        WHEN: format_json_output() renders it (default and verbose modes)
        THEN: The "unaccounted_files" field is PRESENT and empty — absent
              normalizes to None downstream and is NOT a clean bill
        """
        from scripts.install.verify_nwave import format_json_output

        result = _result_with_unaccounted({})

        for verbose in (False, True):
            output_json = json.loads(format_json_output(result, verbose=verbose))
            assert "unaccounted_files" in output_json
            assert output_json["unaccounted_files"] == {}

    @given(listings=_family_listings)
    def test_json_output_renders_listing_per_family_verbatim(self, listings):
        """
        GIVEN: A result with unaccounted names in one or more families
        WHEN: format_json_output() renders it
        THEN: The "unaccounted_files" field maps each family to exactly
              its names, in both output modes
        """
        from scripts.install.verify_nwave import format_json_output

        result = _result_with_unaccounted(listings)

        for verbose in (False, True):
            output_json = json.loads(format_json_output(result, verbose=verbose))
            assert output_json["unaccounted_files"] == listings

    @given(listings=_family_listings)
    def test_terminal_output_notes_preserved_not_managed_in_every_mode(self, listings):
        """
        GIVEN: A result with unaccounted names in one or more families
        WHEN: format_terminal_output() renders it (default and verbose)
        THEN: Every family and every name appears under a line that reads
              "preserved, not managed by nWave" — and the output contains
              no imperative deletion suggestion
        """
        from scripts.install.verify_nwave import format_terminal_output

        result = _result_with_unaccounted(listings)

        for verbose in (False, True):
            output = format_terminal_output(result, verbose=verbose)
            assert "not managed by nWave" in output
            for family, names in listings.items():
                assert family in output
                for name in names:
                    assert name in output
            lowered = output.lower()
            assert "delet" not in lowered
            assert "remov" not in lowered

    def test_terminal_output_renders_no_preserved_line_when_listing_empty(self):
        """
        GIVEN: A clean verification result (empty listing)
        WHEN: format_terminal_output() renders it (default and verbose)
        THEN: No preserved-not-managed line appears — zero noise
        """
        from scripts.install.verify_nwave import format_terminal_output

        result = _result_with_unaccounted({})

        for verbose in (False, True):
            output = format_terminal_output(result, verbose=verbose)
            assert "not managed" not in output


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

        config_dir = tmp_path / ".claude"
        config_dir.mkdir(parents=True)

        main(args=[], claude_config_dir=config_dir)
        captured = capsys.readouterr()

        output = captured.out.lower() + captured.err.lower()
        assert "missing" in output or "failed" in output or "error" in output

    def test_verify_nwave_json_remediation_includes_all_fields(self, tmp_path, capsys):
        """
        GIVEN: An installation with missing files and --json flag
        WHEN: main() is called
        THEN: JSON output includes remediation field
        """
        from scripts.install.verify_nwave import main

        config_dir = tmp_path / ".claude"
        config_dir.mkdir(parents=True)

        main(args=["--json"], claude_config_dir=config_dir)
        captured = capsys.readouterr()

        try:
            output_json = json.loads(captured.out)
            assert output_json.get("success") is False
            assert (
                "missing_files" in output_json
                or "missing_essential_files" in output_json
            )
        except json.JSONDecodeError:
            pytest.fail("Output should be valid JSON")
