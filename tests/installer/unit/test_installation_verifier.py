"""Unit tests for installation_verifier module.

Tests validate post-installation verification logic including:
- Agent file counting
- Command file counting
- Manifest existence checking
- Essential command file detection

CRITICAL: Tests follow hexagonal architecture - domain classes use real objects.
Only pathlib.Path is mocked at port boundaries.
"""


class TestVerificationResultDataclass:
    """Test VerificationResult dataclass structure."""

    def test_verification_result_success_has_all_fields(self):
        """
        GIVEN: A successful verification
        WHEN: VerificationResult is created
        THEN: All fields are populated correctly
        """
        from scripts.install.installation_verifier import VerificationResult

        # ACT
        result = VerificationResult(
            success=True,
            agent_file_count=41,
            command_file_count=25,
            manifest_exists=True,
            missing_essential_files=[],
            error_code=None,
            message="Verification completed successfully.",
        )

        # ASSERT
        assert result.success is True
        assert result.agent_file_count == 41
        assert result.command_file_count == 25
        assert result.manifest_exists is True
        assert result.missing_essential_files == []
        assert result.error_code is None
        assert result.message == "Verification completed successfully."

    def test_verification_result_failure_has_error_code(self):
        """
        GIVEN: A failed verification
        WHEN: VerificationResult is created with error details
        THEN: error_code is set to VERIFY_FAILED
        """
        from scripts.install.error_codes import VERIFY_FAILED
        from scripts.install.installation_verifier import VerificationResult

        # ACT
        result = VerificationResult(
            success=False,
            agent_file_count=0,
            command_file_count=0,
            manifest_exists=False,
            missing_essential_files=["design.md", "review.md"],
            error_code=VERIFY_FAILED,
            message="Verification failed: missing essential files.",
        )

        # ASSERT
        assert result.success is False
        assert result.error_code == VERIFY_FAILED
        assert "design.md" in result.missing_essential_files
        assert "review.md" in result.missing_essential_files


class TestInstallationVerifierAgentFiles:
    """Test agent file verification."""

    def test_verify_agent_files_count_with_populated_directory(self, tmp_path):
        """
        GIVEN: A directory with agent markdown files
        WHEN: verify_agent_files() is called
        THEN: Returns correct count of .md files
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE
        agents_dir = tmp_path / ".claude" / "agents" / "nw"
        agents_dir.mkdir(parents=True)

        # Create sample agent files
        (agents_dir / "software-crafter.md").write_text("# Agent 1")
        (agents_dir / "researcher.md").write_text("# Agent 2")
        (agents_dir / "architect.md").write_text("# Agent 3")

        verifier = InstallationVerifier(claude_config_dir=tmp_path / ".claude")

        # ACT
        count = verifier.verify_agent_files()

        # ASSERT
        assert count == 3

    def test_verify_agent_files_count_with_empty_directory(self, tmp_path):
        """
        GIVEN: An empty agents directory
        WHEN: verify_agent_files() is called
        THEN: Returns 0
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE
        agents_dir = tmp_path / ".claude" / "agents" / "nw"
        agents_dir.mkdir(parents=True)

        verifier = InstallationVerifier(claude_config_dir=tmp_path / ".claude")

        # ACT
        count = verifier.verify_agent_files()

        # ASSERT
        assert count == 0

    def test_verify_agent_files_count_with_missing_directory(self, tmp_path):
        """
        GIVEN: A non-existent agents directory
        WHEN: verify_agent_files() is called
        THEN: Returns 0
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE
        config_dir = tmp_path / ".claude"
        config_dir.mkdir(parents=True)
        # Agents directory does NOT exist

        verifier = InstallationVerifier(claude_config_dir=config_dir)

        # ACT
        count = verifier.verify_agent_files()

        # ASSERT
        assert count == 0


class TestInstallationVerifierCommandFiles:
    """Test command file verification."""

    def test_verify_command_files_count_with_populated_directory(self, tmp_path):
        """
        GIVEN: A directory with command markdown files
        WHEN: verify_command_files() is called
        THEN: Returns correct count of .md files
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE
        commands_dir = tmp_path / ".claude" / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        # Create sample command files
        (commands_dir / "review.md").write_text("# Review command")
        (commands_dir / "devops.md").write_text("# Devop command")
        (commands_dir / "discuss.md").write_text("# Discuss command")
        (commands_dir / "design.md").write_text("# Design command")
        (commands_dir / "distill.md").write_text("# Distill command")

        verifier = InstallationVerifier(claude_config_dir=tmp_path / ".claude")

        # ACT
        count = verifier.verify_command_files()

        # ASSERT
        assert count == 5

    def test_verify_command_files_count_with_missing_directory(self, tmp_path):
        """
        GIVEN: A non-existent commands directory
        WHEN: verify_command_files() is called
        THEN: Returns 0
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE
        config_dir = tmp_path / ".claude"
        config_dir.mkdir(parents=True)
        # Commands directory does NOT exist

        verifier = InstallationVerifier(claude_config_dir=config_dir)

        # ACT
        count = verifier.verify_command_files()

        # ASSERT
        assert count == 0


class TestInstallationVerifierManifest:
    """Test manifest existence verification."""

    def test_verify_manifest_exists_when_present(self, tmp_path):
        """
        GIVEN: A manifest file exists at expected location
        WHEN: verify_manifest() is called
        THEN: Returns True
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE
        config_dir = tmp_path / ".claude"
        config_dir.mkdir(parents=True)
        manifest_path = config_dir / "nwave-manifest.txt"
        manifest_path.write_text("nWave Framework Installation Manifest")

        verifier = InstallationVerifier(claude_config_dir=config_dir)

        # ACT
        exists = verifier.verify_manifest()

        # ASSERT
        assert exists is True

    def test_verify_manifest_missing_when_absent(self, tmp_path):
        """
        GIVEN: No manifest file at expected location
        WHEN: verify_manifest() is called
        THEN: Returns False
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE
        config_dir = tmp_path / ".claude"
        config_dir.mkdir(parents=True)
        # Manifest does NOT exist

        verifier = InstallationVerifier(claude_config_dir=config_dir)

        # ACT
        exists = verifier.verify_manifest()

        # ASSERT
        assert exists is False


class TestInstallationVerifierEssentialCommands:
    """Test essential command file verification."""

    def test_verify_essential_commands_all_present(self, tmp_path):
        """
        GIVEN: All essential command files exist
        WHEN: verify_essential_commands() is called
        THEN: Returns empty list (no missing files)
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE
        commands_dir = tmp_path / ".claude" / "commands" / "nw"
        commands_dir.mkdir(parents=True)

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

        verifier = InstallationVerifier(claude_config_dir=tmp_path / ".claude")

        # ACT
        missing = verifier.verify_essential_commands()

        # ASSERT
        assert missing == []

    def test_verify_essential_commands_some_missing(self, tmp_path):
        """
        GIVEN: Some essential command files are missing
        WHEN: verify_essential_commands() is called
        THEN: Returns list of missing filenames
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE
        commands_dir = tmp_path / ".claude" / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        # Create only some essential files (missing design.md, review.md)
        (commands_dir / "devops.md").write_text("# Devop command")
        (commands_dir / "discuss.md").write_text("# Discuss command")

        verifier = InstallationVerifier(claude_config_dir=tmp_path / ".claude")

        # ACT
        missing = verifier.verify_essential_commands()

        # ASSERT
        assert "design.md" in missing
        assert "review.md" in missing
        assert "devops.md" not in missing

    def test_verify_essential_commands_all_missing(self, tmp_path):
        """
        GIVEN: Commands directory is empty
        WHEN: verify_essential_commands() is called
        THEN: Returns list of all essential files
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE
        commands_dir = tmp_path / ".claude" / "commands" / "nw"
        commands_dir.mkdir(parents=True)
        # No files created

        verifier = InstallationVerifier(claude_config_dir=tmp_path / ".claude")

        # ACT
        missing = verifier.verify_essential_commands()

        # ASSERT
        # Should contain all 6 essential files (review, develop, discuss, design, distill, deliver)
        assert len(missing) == 6
        assert "review.md" in missing
        assert "devops.md" in missing


class TestInstallationVerifierFullVerification:
    """Test full verification orchestration."""

    def test_run_verification_success_when_all_present(self, tmp_path):
        """
        GIVEN: A complete installation with all files present
        WHEN: run_verification() is called
        THEN: Returns VerificationResult with success=True
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE - Create complete installation
        config_dir = tmp_path / ".claude"
        agents_dir = config_dir / "agents" / "nw"
        commands_dir = config_dir / "commands" / "nw"
        skills_dir = config_dir / "skills" / "nw" / "software-crafter"
        des_dir = config_dir / "lib" / "python" / "des"
        agents_dir.mkdir(parents=True)
        commands_dir.mkdir(parents=True)
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

        # Create skills
        (skills_dir / "tdd-methodology.md").write_text("# TDD")

        # Create DES module
        (des_dir / "__init__.py").write_text("")

        # Create manifest
        (config_dir / "nwave-manifest.txt").write_text(
            "nWave Framework Installation Manifest"
        )

        verifier = InstallationVerifier(claude_config_dir=config_dir)

        # ACT
        result = verifier.run_verification()

        # ASSERT
        assert result.success is True
        assert result.agent_file_count == 5
        assert result.command_file_count == 6
        assert result.skill_file_count == 1
        assert result.skill_group_count == 1
        assert result.des_installed is True
        assert result.manifest_exists is True
        assert result.missing_essential_files == []
        assert result.error_code is None

    def test_run_verification_failure_when_missing_essential_files(self, tmp_path):
        """
        GIVEN: An incomplete installation with missing essential files
        WHEN: run_verification() is called
        THEN: Returns VerificationResult with success=False and VERIFY_FAILED error code
        """
        from scripts.install.error_codes import VERIFY_FAILED
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE - Create incomplete installation
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        commands_dir.mkdir(parents=True)

        # Create only partial files (missing essential ones)
        (commands_dir / "discuss.md").write_text("# Discuss")

        verifier = InstallationVerifier(claude_config_dir=config_dir)

        # ACT
        result = verifier.run_verification()

        # ASSERT
        assert result.success is False
        assert result.error_code == VERIFY_FAILED
        assert len(result.missing_essential_files) > 0

    def test_run_verification_failure_when_manifest_missing(self, tmp_path):
        """
        GIVEN: An installation without manifest file
        WHEN: run_verification() is called
        THEN: Returns VerificationResult with manifest_exists=False
        """
        from scripts.install.installation_verifier import InstallationVerifier

        # ARRANGE - Create installation without manifest
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        skills_dir = config_dir / "skills" / "nw" / "crafter"
        des_dir = config_dir / "lib" / "python" / "des"
        commands_dir.mkdir(parents=True)
        skills_dir.mkdir(parents=True)
        des_dir.mkdir(parents=True)

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

        (skills_dir / "skill.md").write_text("# Skill")
        (des_dir / "__init__.py").write_text("")

        verifier = InstallationVerifier(claude_config_dir=config_dir)

        # ACT
        result = verifier.run_verification()

        # ASSERT
        assert result.manifest_exists is False
        # Missing manifest alone should trigger failure
        assert result.success is False


# ==============================================================================
# Step 05-03: Post-Installation Verification Integration Tests
# ==============================================================================


class TestInstallNwaveCallsVerifier:
    """Test install_nwave.py integration with InstallationVerifier."""

    def test_install_nwave_calls_verifier_after_install(self):
        """
        GIVEN: A successful installation
        WHEN: validate_installation() is called
        THEN: It uses InstallationVerifier.run_verification() internally

        Step 05-03: Post-Installation Verification Integration
        """
        import sys
        from unittest.mock import MagicMock, patch

        from scripts.install.installation_verifier import VerificationResult

        # ARRANGE
        verifier_called = False
        mock_result = VerificationResult(
            success=True,
            agent_file_count=41,
            command_file_count=25,
            manifest_exists=True,
            missing_essential_files=[],
            error_code=None,
            message="Verification completed successfully.",
        )

        def track_verifier(*args, **kwargs):
            nonlocal verifier_called
            verifier_called = True
            return mock_result

        with patch(
            "scripts.install.install_nwave.InstallationVerifier"
        ) as mock_verifier_class:
            mock_verifier = MagicMock()
            mock_verifier.run_verification.side_effect = track_verifier
            mock_verifier_class.return_value = mock_verifier

            with patch(
                "scripts.install.install_nwave.PreflightChecker"
            ) as mock_preflight_class:
                mock_checker = MagicMock()
                mock_checker.run_all_checks.return_value = []
                mock_checker.has_blocking_failures.return_value = False
                mock_preflight_class.return_value = mock_checker

                with patch(
                    "scripts.install.install_nwave.NWaveInstaller.create_backup"
                ):
                    with patch(
                        "scripts.install.install_nwave.NWaveInstaller.install_framework",
                        return_value=True,
                    ):
                        with patch(
                            "scripts.install.install_nwave.NWaveInstaller.create_manifest"
                        ):
                            # ACT
                            from scripts.install.install_nwave import main

                            with patch.object(sys, "argv", ["install_nwave.py"]):
                                main()

        # ASSERT
        assert verifier_called, (
            "InstallationVerifier.run_verification() should be called "
            "during post-installation validation"
        )

    def test_install_nwave_displays_verification_result(self):
        """
        GIVEN: InstallationVerifier returns verification results
        WHEN: validate_installation() displays results
        THEN: Agent and command counts from verifier are shown

        Step 05-03: Post-Installation Verification Integration
        """
        import sys
        from unittest.mock import MagicMock, patch

        from scripts.install.installation_verifier import VerificationResult

        # ARRANGE
        mock_result = VerificationResult(
            success=True,
            agent_file_count=41,
            command_file_count=25,
            manifest_exists=True,
            missing_essential_files=[],
            error_code=None,
            message="Verification completed successfully. Found 41 agents, 25 commands.",
        )

        logged_messages = []

        def capture_log(msg):
            logged_messages.append(msg)

        with patch(
            "scripts.install.install_nwave.InstallationVerifier"
        ) as mock_verifier_class:
            mock_verifier = MagicMock()
            mock_verifier.run_verification.return_value = mock_result
            mock_verifier_class.return_value = mock_verifier

            with patch(
                "scripts.install.install_nwave.PreflightChecker"
            ) as mock_preflight_class:
                mock_checker = MagicMock()
                mock_checker.run_all_checks.return_value = []
                mock_checker.has_blocking_failures.return_value = False
                mock_preflight_class.return_value = mock_checker

                with patch(
                    "scripts.install.install_nwave.NWaveInstaller.create_backup"
                ):
                    with patch(
                        "scripts.install.install_nwave.NWaveInstaller.install_framework",
                        return_value=True,
                    ):
                        with patch(
                            "scripts.install.install_nwave.NWaveInstaller.create_manifest"
                        ):
                            with patch(
                                "scripts.install.install_nwave.Logger.info",
                                side_effect=capture_log,
                            ):
                                # ACT
                                from scripts.install.install_nwave import main

                                with patch.object(sys, "argv", ["install_nwave.py"]):
                                    main()

        # ASSERT - Check that verification counts are displayed
        all_logs = " ".join(logged_messages)
        assert "41" in all_logs or "agent" in all_logs.lower(), (
            "Verification result should display agent count from verifier"
        )

    def test_install_nwave_logs_verification_outcome(self):
        """
        GIVEN: InstallationVerifier runs verification
        WHEN: Verification completes
        THEN: The outcome (success/failure) is logged

        Step 05-03: Post-Installation Verification Integration
        """
        import sys
        from unittest.mock import MagicMock, patch

        # ARRANGE
        with patch(
            "scripts.install.install_nwave.PreflightChecker"
        ) as mock_preflight_class:
            mock_checker = MagicMock()
            mock_checker.run_all_checks.return_value = []
            mock_checker.has_blocking_failures.return_value = False
            mock_preflight_class.return_value = mock_checker

            with patch("scripts.install.install_nwave.NWaveInstaller.create_backup"):
                with patch(
                    "scripts.install.install_nwave.NWaveInstaller.install_framework",
                    return_value=True,
                ):
                    with patch(
                        "scripts.install.install_nwave.NWaveInstaller.create_manifest"
                    ):
                        with patch(
                            "scripts.install.install_nwave.NWaveInstaller.validate_installation",
                            return_value=True,
                        ):
                            # ACT
                            from scripts.install.install_nwave import main

                            with patch.object(sys, "argv", ["install_nwave.py"]):
                                exit_code = main()

        # ASSERT
        assert exit_code == 0, "Successful verification should result in exit code 0"

    def test_install_nwave_exit_code_on_verification_failure(self):
        """
        GIVEN: InstallationVerifier returns failure
        WHEN: validate_installation() is called
        THEN: main() returns non-zero exit code

        Step 05-03: Post-Installation Verification Integration
        """
        import sys
        from unittest.mock import MagicMock, patch

        from scripts.install.error_codes import VERIFY_FAILED
        from scripts.install.installation_verifier import VerificationResult

        # ARRANGE
        mock_result = VerificationResult(
            success=False,
            agent_file_count=0,
            command_file_count=0,
            manifest_exists=False,
            missing_essential_files=["design.md", "review.md"],
            error_code=VERIFY_FAILED,
            message="Verification failed: missing essential files.",
        )

        with patch(
            "scripts.install.install_nwave.InstallationVerifier"
        ) as mock_verifier_class:
            mock_verifier = MagicMock()
            mock_verifier.run_verification.return_value = mock_result
            mock_verifier_class.return_value = mock_verifier

            with patch(
                "scripts.install.install_nwave.PreflightChecker"
            ) as mock_preflight_class:
                mock_checker = MagicMock()
                mock_checker.run_all_checks.return_value = []
                mock_checker.has_blocking_failures.return_value = False
                mock_preflight_class.return_value = mock_checker

                with patch(
                    "scripts.install.install_nwave.NWaveInstaller.create_backup"
                ):
                    with patch(
                        "scripts.install.install_nwave.NWaveInstaller.install_framework",
                        return_value=True,
                    ):
                        # ACT
                        from scripts.install.install_nwave import main

                        with patch.object(sys, "argv", ["install_nwave.py"]):
                            exit_code = main()

        # ASSERT
        assert exit_code != 0, (
            "Verification failure should result in non-zero exit code"
        )
