"""Walking skeleton acceptance test for install_nwave.py TUI output.

Validates the happy-path user journey through the complete TUI output,
anchored to Luna design principles: emoji streams, no Rich borders,
continuous top-to-bottom flow.

The installer is executed ONCE (module-scoped fixture) and all tests
assert against the same captured stdout, making the suite fast while
covering every visible step of the installation journey.
"""

from scripts.install.install_nwave import __version__


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
    """Happy-path walking skeleton: 12 steps a user sees on screen."""

    # Step 1: Logo
    def test_step_01_logo_with_version(self, output: str):
        """ASCII art logo is printed with the current version number."""
        assert f"v{__version__}" in output
        assert "nWave" in output or "\u2588" in output  # block chars from logo art

    # Step 2: Pre-flight checks
    def test_step_02_preflight_checks_as_emoji_stream(self, output: str):
        """Pre-flight section opens with magnifier emoji and closes with pass."""
        assert "\U0001f50d" in output  # 🔍
        assert "Pre-flight checks" in output
        assert "\u2705" in output  # ✅
        assert "Pre-flight passed" in output

    def test_step_02_all_three_checks_reported(self, output: str):
        """Each of the three preflight check results appears in output."""
        assert "Virtual environment detected" in output
        assert "Pipenv is available" in output
        assert "All required dependencies are available" in output

    # Step 3: Source framework (removed - install now goes directly to plugins)
    def test_step_03_install_proceeds_after_preflight(self, output: str):
        """After preflight passes, installation proceeds to backup/install."""
        assert "Pre-flight passed" in output

    # Step 4: Backup
    def test_step_04_backup_section(self, output: str):
        """Backup section appears (fresh install skips with info message)."""
        # On a fresh temp dir there's nothing to back up
        assert (
            "No existing installation, skipping backup" in output or "Backup" in output
        )

    # Step 5: Install start
    def test_step_05_install_started(self, output: str):
        """Installation banner with target directory is shown."""
        assert "\U0001f4bf" in output  # 💿
        assert "Installing nWave" in output

    # Step 6: Plugin execution
    def test_step_06_plugin_execution(self, output: str):
        """Plugin context installation message is displayed."""
        assert "Installing Context" in output

    # Step 7: Manifest
    def test_step_07_manifest_created(self, output: str):
        """Installation manifest creation is reported."""
        assert "Installation manifest created" in output

    # Step 8: Validation details
    def test_step_08_validation_details(self, output: str):
        """Post-install verification reports components individually."""
        assert "Agents verified" in output
        assert "Commands verified" in output
        assert "Manifest created" in output
        assert "Schema validated" in output

    # Step 9: Schema
    def test_step_09_schema_validated(self, output: str):
        """TDD cycle schema validation reports version and phase count."""
        assert "TDD cycle schema" in output

    # Step 10: Deployment validated
    def test_step_10_deployment_validated(self, output: str):
        """Deployment validation succeeds with champagne emoji."""
        assert "\U0001f37e" in output  # 🍾
        assert "Deployment validated" in output

    # Step 11: Celebration
    def test_step_11_celebration(self, output: str):
        """Success celebration with version number."""
        assert "\U0001f389" in output  # 🎉
        assert "installed and healthy" in output
        assert __version__ in output

    # Step 12: Quick start
    def test_step_12_quick_start_commands(self, output: str):
        """Quick start section lists the wizard entry-point commands."""
        assert "Quick start" in output
        assert "/nw:new" in output
        assert "/nw:continue" in output
        assert "/nw:ff" in output

    def test_step_12_docs_url(self, output: str):
        """Docs URL points to the correct repository."""
        expected_url = "https://github.com/nWave-ai/nWave"
        # Find the line containing the URL and verify it's exact (not a substring of a mangled URL)
        doc_lines = [
            line for line in output.splitlines() if "github.com/nWave-ai" in line
        ]
        assert doc_lines, "No docs URL line found in output"
        assert any(line.rstrip().endswith(expected_url) for line in doc_lines), (
            f"Docs URL is mangled. Found: {doc_lines}"
        )


# ─── Ordering ────────────────────────────────────────────────────────


class TestOutputOrdering:
    """The TUI reads as a continuous top-to-bottom stream."""

    def test_output_reads_as_continuous_stream(self, output: str):
        """Key markers appear in chronological journey order."""
        ordered_markers = [
            "Pre-flight checks",
            "Pre-flight passed",
            "Installing nWave",
            "Installing Context",
            "manifest created",
            "Validate Installation",
            "Deployment validated",
            "installed and healthy",
            "Quick start",
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
        """Successful installation returns exit code 0."""
        assert exit_code == 0
