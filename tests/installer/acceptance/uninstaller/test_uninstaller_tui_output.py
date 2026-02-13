"""Walking skeleton acceptance test for uninstall_nwave.py TUI output.

Validates the happy-path uninstall journey through the complete TUI output,
anchored to Luna design principles: emoji streams, no Rich borders,
continuous top-to-bottom flow.

The uninstaller is executed ONCE (module-scoped fixture) against a freshly
installed config dir. All tests assert against the same captured stdout.
"""

from scripts.install.install_nwave import __version__ as install_version
from scripts.install.uninstall_nwave import __version__ as uninstall_version


# ─── Design constraints ─────────────────────────────────────────────


class TestDesignConstraints:
    """Luna TUI design rules: no Rich borders, no Forge prefix."""

    def test_no_rich_table_or_panel_borders(self, output: str):
        """TUI output must not contain Rich/box-drawing border characters."""
        forbidden = set("╭╮╰╯┏┓┗┛━─┃│┡┩╇╈┼┤├")
        found = forbidden.intersection(output)
        assert not found, f"Rich border characters found in output: {found}"

    def test_no_forge_prefix(self, output: str):
        """Output must not contain legacy [Forge] prefix."""
        assert "[Forge]" not in output


# ─── Step-by-step journey ────────────────────────────────────────────


class TestWalkingSkeleton:
    """Happy-path walking skeleton: steps a user sees on screen during uninstall."""

    # Step 1: Logo + uninstaller banner
    def test_step_01_logo_with_version(self, output: str):
        """ASCII art logo is printed with the installer version number."""
        assert f"v{install_version}" in output
        assert "nWave" in output or "\u2588" in output

    def test_step_01_uninstaller_banner(self, output: str):
        """Uninstaller banner shows its own version."""
        assert "Uninstaller" in output
        assert uninstall_version in output

    # Step 2: Check installation
    def test_step_02_check_installation(self, output: str):
        """Uninstaller scans for existing nWave components."""
        assert "\U0001f50d" in output  # 🔍
        assert "Checking for nWave installation" in output

    def test_step_02_found_agents(self, output: str):
        """Existing agents directory is detected."""
        assert "Found nWave agents" in output

    def test_step_02_found_commands(self, output: str):
        """Existing commands directory is detected."""
        assert "Found nWave commands" in output

    def test_step_02_found_manifest(self, output: str):
        """Existing manifest file is detected."""
        assert "Found nWave manifest" in output

    # Step 3: Backup (--backup flag)
    def test_step_03_backup_created(self, output: str):
        """Backup is created before removal when --backup is used."""
        assert "Backup" in output or "\U0001f4be" in output  # 💾

    # Step 4: Remove agents
    def test_step_04_agents_removed(self, output: str):
        """Agents removal is reported."""
        assert "Removed" in output and "agents" in output.lower()

    # Step 5: Remove commands
    def test_step_05_commands_removed(self, output: str):
        """Commands removal is reported."""
        assert "Removed" in output and "commands" in output.lower()

    # Step 6: Remove config files
    def test_step_06_config_files_removed(self, output: str):
        """Configuration files are removed."""
        assert "nwave-manifest.txt" in output or "configuration" in output.lower()

    # Step 7: Validate removal
    def test_step_07_validation_passed(self, output: str):
        """Post-removal validation confirms everything is gone."""
        assert "Validating complete removal" in output
        assert "Agents removed" in output
        assert "Commands removed" in output
        assert "Manifest removed" in output
        assert "Uninstallation validation passed" in output

    # Step 8: Uninstall report
    def test_step_08_report_created(self, output: str):
        """Uninstall report is generated."""
        assert "Uninstall report created" in output

    # Step 9: Summary
    def test_step_09_summary(self, output: str):
        """Final summary confirms successful removal with champagne."""
        assert "\U0001f37e" in output  # 🍾
        assert "Framework removed successfully" in output

    def test_step_09_summary_details(self, output: str):
        """Summary lists what was removed."""
        assert "All nWave agents removed" in output
        assert "All nWave commands removed" in output
        assert "Configuration files removed" in output

    def test_step_09_backup_location(self, output: str):
        """Summary shows backup location (since --backup was used)."""
        # With --backup the summary shows the backup path, not "No backup created"
        assert "No backup created" not in output
        # The backup line must end cleanly with the path, no trailing garbage
        backup_lines = [
            line
            for line in output.splitlines()
            if "Backup:" in line and "\U0001f4e6" in line
        ]
        assert backup_lines, "No backup location line found in summary"
        for line in backup_lines:
            # After the path there should only be whitespace
            after_backup = line.split("Backup:")[1]
            assert after_backup.strip().isprintable(), (
                "Backup line contains non-printable chars"
            )
            # Path should not contain emoji (emoji = mangled)
            path_part = after_backup.strip()
            import unicodedata

            emoji_chars = [
                c for c in path_part if unicodedata.category(c).startswith("So")
            ]
            assert not emoji_chars, f"Backup path is mangled with emoji: {path_part!r}"


# ─── Source integrity ────────────────────────────────────────────────


class TestSourceIntegrity:
    """Verify key TUI strings in source haven't been mangled."""

    @staticmethod
    def _get_summary_source() -> str:
        import inspect

        from scripts.install.uninstall_nwave import show_uninstall_summary

        return inspect.getsource(show_uninstall_summary)

    def test_no_backup_message_is_clean(self):
        """The no-backup summary line must be exactly 'No backup created'."""
        source = self._get_summary_source()
        assert "No backup created" in source
        for line in source.splitlines():
            if "No backup created" in line:
                after = line.split("No backup created")[1]
                stripped = after.strip().rstrip("\"').}")
                assert stripped == "", (
                    f"Trailing garbage after 'No backup created': {after!r}"
                )

    def test_backup_line_has_no_trailing_garbage(self):
        """The backup-path f-string must end cleanly with {backup_dir}."""
        source = self._get_summary_source()
        for line in source.splitlines():
            if "Backup:" in line and "backup_dir}" in line:
                # Everything after the closing brace should be just quote + paren
                after_brace = line.split("backup_dir}")[1]
                stripped = after_brace.strip().rstrip("\"').}")
                assert stripped == "", (
                    f"Trailing garbage after backup_dir: {after_brace!r}"
                )


# ─── Ordering ────────────────────────────────────────────────────────


class TestOutputOrdering:
    """The TUI reads as a continuous top-to-bottom stream."""

    def test_output_reads_as_continuous_stream(self, output: str):
        """Key markers appear in chronological journey order."""
        ordered_markers = [
            "Uninstaller",
            "Checking for nWave installation",
            "Found nWave agents",
            "Removed",
            "Validating complete removal",
            "Uninstallation validation passed",
            "Uninstall report created",
            "Framework removed successfully",
        ]
        positions = []
        for marker in ordered_markers:
            pos = output.find(marker)
            assert pos != -1, f"Marker not found in output: {marker!r}"
            positions.append(pos)

        assert positions == sorted(positions), (
            f"Markers appear out of order.\n"
            f"Expected ascending positions, got: "
            f"{list(zip(ordered_markers, positions, strict=True))}"
        )


# ─── Exit code ───────────────────────────────────────────────────────


class TestExitCode:
    """Process exit code validation."""

    def test_exit_code_zero_on_success(self, exit_code: int):
        """Successful uninstallation returns exit code 0."""
        assert exit_code == 0
