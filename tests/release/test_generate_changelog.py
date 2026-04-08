"""Tests for scripts/release/generate_changelog.py

Generates markdown release notes from conventional commits between git tags.
Three modes: dev (snapshot), RC (release candidate), and stable,
with different headers and install commands.

Scenario inventory (16 scenarios):

  Dev changelog:
    1. Dev changelog with features and fixes
    2. Dev changelog finds previous tag of any type
    3. Dev changelog has no install section
    4. Dev changelog empty history shows no notable changes

  RC changelog:
    5. RC changelog with features and fixes
    6. RC changelog shows promoted-from source tag
    7. RC changelog empty history shows no notable changes

  Stable changelog:
    8. Stable changelog with breaking changes
    9. Stable install command has no --pre flag

  Commit parsing (pure function tests):
   10. feat commit categorized as feature
   11. fix commit categorized as fix
   12. chore(release) commits are filtered
   13. bang notation marks breaking change
   14. non-conventional commit goes to other

  Compare link:
   15. Compare link included when previous tag exists

  Output file:
   16. Output file created at specified path
"""

import subprocess
import sys
from pathlib import Path

from scripts.release.generate_changelog import _categorize_commits


SCRIPT = "scripts/release/generate_changelog.py"


# ---------------------------------------------------------------------------
# Git helpers for integration tests (same pattern as test_discover_tag.py)
# ---------------------------------------------------------------------------


def _git(path, *command):
    """Run a git command in the given repo directory."""
    env = {
        **__import__("os").environ,
        "GIT_CEILING_DIRECTORIES": str(Path(path).parent),
    }
    subprocess.run(
        ["git", *command],
        cwd=str(path),
        capture_output=True,
        check=True,
        env=env,
    )


def _init_git_repo(path):
    """Initialize a git repo in the given directory."""
    _git(path, "init")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    _git(path, "config", "core.hooksPath", "/dev/null")


def _create_commit(path, message):
    """Create an empty commit in the given git repo."""
    _git(path, "commit", "--allow-empty", "-m", message)


def _create_tag(path, tag_name):
    """Create a lightweight tag at HEAD in the given git repo."""
    _git(path, "tag", tag_name)


def _project_root():
    """Resolve project root from this test file's location."""
    return str(Path(__file__).resolve().parents[2])


def _run_changelog_in_repo(repo_path, *args):
    """Run generate_changelog.py inside a specific git repo directory."""
    script_path = str(Path(_project_root()) / SCRIPT)
    env = {**__import__("os").environ, "GIT_CEILING_DIRECTORIES": str(repo_path)}
    return subprocess.run(
        [sys.executable, script_path, *args],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        env=env,
    )


def _read_output(path):
    """Read the generated release notes file."""
    return Path(path).read_text()


# ===========================================================================
# Dev Changelog
# ===========================================================================
class TestDevChangelog:
    """Dev snapshot changelog generation from conventional commits."""

    def test_dev_changelog_with_features_and_fixes(self, tmp_path):
        """Given a repo with feat and fix commits after any tag,
        when generating dev changelog,
        then notes contain Features and Bug Fixes sections with Dev snapshot header."""
        _init_git_repo(tmp_path)
        _create_commit(tmp_path, "initial commit")
        _create_tag(tmp_path, "v1.1.22")
        _create_commit(tmp_path, "feat: add streaming support")
        _create_commit(tmp_path, "fix: handle empty payload")

        output_file = str(tmp_path / "notes.md")
        result = _run_changelog_in_repo(
            tmp_path,
            "--stage",
            "dev",
            "--version",
            "1.1.23.dev1",
            "--repo",
            "nWave-ai/nwave-dev",
            "--output",
            output_file,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        notes = _read_output(output_file)
        assert "**Dev snapshot**" in notes
        assert "## Features" in notes
        assert "add streaming support" in notes
        assert "## Bug Fixes" in notes
        assert "handle empty payload" in notes

    def test_dev_changelog_finds_previous_tag_of_any_type(self, tmp_path):
        """Given a stable tag v1.1.22, then an rc tag v1.1.23rc1, then a feat commit,
        when generating dev changelog for 1.1.23.dev1,
        then compare link references v1.1.23rc1 (most recent tag regardless of type)."""
        _init_git_repo(tmp_path)
        _create_commit(tmp_path, "initial commit")
        _create_tag(tmp_path, "v1.1.22")
        _create_commit(tmp_path, "chore(release): v1.1.23rc1 [skip ci]")
        _create_tag(tmp_path, "v1.1.23rc1")
        _create_commit(tmp_path, "feat: new feature for dev")

        output_file = str(tmp_path / "notes.md")
        result = _run_changelog_in_repo(
            tmp_path,
            "--stage",
            "dev",
            "--version",
            "1.1.23.dev1",
            "--repo",
            "nWave-ai/nwave-dev",
            "--output",
            output_file,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        notes = _read_output(output_file)
        assert "v1.1.23rc1" in notes
        assert (
            "https://github.com/nWave-ai/nwave-dev/compare/v1.1.23rc1...v1.1.23.dev1"
        ) in notes

    def test_dev_changelog_has_no_install_section(self, tmp_path):
        """Given dev stage,
        when generating changelog,
        then output does NOT contain Install or pipx install."""
        _init_git_repo(tmp_path)
        _create_commit(tmp_path, "feat: initial")

        output_file = str(tmp_path / "notes.md")
        result = _run_changelog_in_repo(
            tmp_path,
            "--stage",
            "dev",
            "--version",
            "1.1.23.dev1",
            "--output",
            output_file,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        notes = _read_output(output_file)
        assert "Install" not in notes
        assert "pipx install" not in notes

    def test_dev_changelog_empty_history_shows_no_notable_changes(self, tmp_path):
        """Given only chore(release) commits,
        when generating dev changelog,
        then output shows 'No notable changes'."""
        _init_git_repo(tmp_path)
        _create_commit(tmp_path, "chore(release): v1.1.22 [skip ci]")
        _create_tag(tmp_path, "v1.1.22")
        _create_commit(tmp_path, "chore(release): v1.1.23.dev1 [skip ci]")

        output_file = str(tmp_path / "notes.md")
        result = _run_changelog_in_repo(
            tmp_path,
            "--stage",
            "dev",
            "--version",
            "1.1.23.dev1",
            "--output",
            output_file,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        notes = _read_output(output_file)
        assert "No notable changes (internal improvements)" in notes


# ===========================================================================
# RC Changelog
# ===========================================================================
class TestRCChangelog:
    """RC changelog generation from conventional commits."""

    def test_rc_changelog_with_features_and_fixes(self, tmp_path):
        """Given a git repo with feat and fix commits after an RC tag,
        when generating RC changelog,
        then release notes contain Features and Bug Fixes sections."""
        _init_git_repo(tmp_path)
        _create_commit(tmp_path, "initial commit")
        _create_tag(tmp_path, "v1.1.22rc1")
        _create_commit(tmp_path, "feat: add user authentication")
        _create_commit(tmp_path, "fix: resolve login crash")
        _create_tag(tmp_path, "v1.1.22rc2")

        output_file = str(tmp_path / "notes.md")
        result = _run_changelog_in_repo(
            tmp_path,
            "--stage",
            "rc",
            "--version",
            "1.1.22rc2",
            "--output",
            output_file,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        notes = _read_output(output_file)
        assert "## Features" in notes
        assert "add user authentication" in notes
        assert "## Bug Fixes" in notes
        assert "resolve login crash" in notes
        assert "**Release candidate**" in notes

    def test_rc_changelog_shows_promoted_from_source_tag(self, tmp_path):
        """Given --source-tag is provided,
        when generating RC changelog,
        then 'Promoted from' line appears in output."""
        _init_git_repo(tmp_path)
        _create_commit(tmp_path, "feat: initial feature")

        output_file = str(tmp_path / "notes.md")
        result = _run_changelog_in_repo(
            tmp_path,
            "--stage",
            "rc",
            "--version",
            "1.1.23rc1",
            "--source-tag",
            "v1.1.23.dev1",
            "--output",
            output_file,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        notes = _read_output(output_file)
        assert "**Promoted from**: `v1.1.23.dev1`" in notes

    def test_rc_changelog_empty_history_shows_no_notable_changes(self, tmp_path):
        """Given no conventional commits exist,
        when generating RC changelog,
        then output shows 'No notable changes'."""
        _init_git_repo(tmp_path)
        _create_commit(tmp_path, "chore(release): v1.1.22rc1 [skip ci]")
        _create_tag(tmp_path, "v1.1.22rc1")
        _create_commit(tmp_path, "chore(release): v1.1.22rc2 [skip ci]")
        _create_tag(tmp_path, "v1.1.22rc2")

        output_file = str(tmp_path / "notes.md")
        result = _run_changelog_in_repo(
            tmp_path,
            "--stage",
            "rc",
            "--version",
            "1.1.22rc2",
            "--output",
            output_file,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        notes = _read_output(output_file)
        assert "No notable changes (internal improvements)" in notes


# ===========================================================================
# Stable Changelog
# ===========================================================================
class TestStableChangelog:
    """Stable changelog generation from conventional commits."""

    def test_stable_changelog_with_breaking_changes(self, tmp_path):
        """Given a commit with ! bang notation,
        when generating stable changelog,
        then Breaking Changes section appears first."""
        _init_git_repo(tmp_path)
        _create_commit(tmp_path, "initial commit")
        _create_tag(tmp_path, "v1.1.22")
        _create_commit(tmp_path, "feat!: new API replaces old endpoints")
        _create_commit(tmp_path, "feat: add metrics dashboard")

        output_file = str(tmp_path / "notes.md")
        result = _run_changelog_in_repo(
            tmp_path,
            "--stage",
            "stable",
            "--version",
            "1.1.23",
            "--output",
            output_file,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        notes = _read_output(output_file)
        assert "## Breaking Changes" in notes
        assert "new API replaces old endpoints" in notes
        # Breaking Changes appears before Features
        breaking_pos = notes.index("## Breaking Changes")
        features_pos = notes.index("## Features")
        assert breaking_pos < features_pos

    def test_stable_changelog_install_command_has_no_pre_flag(self, tmp_path):
        """Given stable stage,
        when generating changelog,
        then install command is 'pipx install nwave-ai' without --pre."""
        _init_git_repo(tmp_path)
        _create_commit(tmp_path, "feat: initial")

        output_file = str(tmp_path / "notes.md")
        result = _run_changelog_in_repo(
            tmp_path,
            "--stage",
            "stable",
            "--version",
            "1.1.23",
            "--output",
            output_file,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        notes = _read_output(output_file)
        assert "pipx install nwave-ai" in notes
        assert "--pre" not in notes
        assert "# nWave Framework v1.1.23" in notes


# ===========================================================================
# Commit Parsing (pure function tests via _categorize_commits)
# ===========================================================================
class TestCommitParsing:
    """Conventional commit categorization (pure function tests)."""

    def _make_log_entry(
        self, subject: str, body: str = "", sha: str = "abc1234"
    ) -> str:
        """Build a single record in the git log format."""
        return f"{subject}\x00{body}\x00{sha}<<--EOR-->>"

    def test_feat_commit_categorized_as_feature(self):
        """Given 'feat: add login', categorized as feature."""
        raw = self._make_log_entry("feat: add login")
        result = _categorize_commits(raw)
        assert len(result["features"]) == 1
        assert "add login" in result["features"][0]

    def test_fix_commit_categorized_as_fix(self):
        """Given 'fix: resolve crash', categorized as fix."""
        raw = self._make_log_entry("fix: resolve crash")
        result = _categorize_commits(raw)
        assert len(result["fixes"]) == 1
        assert "resolve crash" in result["fixes"][0]

    def test_chore_release_commits_are_filtered(self):
        """Given 'chore(release): v1.0.0 [skip ci]', it is excluded."""
        raw = self._make_log_entry("chore(release): v1.0.0 [skip ci]")
        result = _categorize_commits(raw)
        assert len(result["breaking"]) == 0
        assert len(result["features"]) == 0
        assert len(result["fixes"]) == 0
        assert len(result["other"]) == 0

    def test_bang_notation_marks_breaking_change(self):
        """Given 'feat!: new API', categorized as breaking."""
        raw = self._make_log_entry("feat!: new API")
        result = _categorize_commits(raw)
        assert len(result["breaking"]) == 1
        assert "new API" in result["breaking"][0]

    def test_non_conventional_commit_goes_to_other(self):
        """Given 'updated readme', goes to other category."""
        raw = self._make_log_entry("updated readme")
        result = _categorize_commits(raw)
        assert len(result["other"]) == 1
        assert "updated readme" in result["other"][0]


# ===========================================================================
# Compare Link
# ===========================================================================
class TestCompareLink:
    """Compare link generation for release notes."""

    def test_compare_link_included_when_previous_tag_exists(self, tmp_path):
        """Given a previous tag exists,
        when generating changelog,
        then compare link is present."""
        _init_git_repo(tmp_path)
        _create_commit(tmp_path, "initial commit")
        _create_tag(tmp_path, "v1.1.22rc1")
        _create_commit(tmp_path, "feat: new feature")
        _create_tag(tmp_path, "v1.1.22rc2")

        output_file = str(tmp_path / "notes.md")
        result = _run_changelog_in_repo(
            tmp_path,
            "--stage",
            "rc",
            "--version",
            "1.1.22rc2",
            "--repo",
            "nWave-ai/nwave-dev",
            "--output",
            output_file,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        notes = _read_output(output_file)
        assert "v1.1.22rc1" in notes
        assert "https://github.com/nWave-ai/nwave-dev/compare/" in notes
        assert "**Changes since**" in notes


# ===========================================================================
# Output File
# ===========================================================================
class TestOutputFile:
    """Output file creation."""

    def test_output_file_created_at_specified_path(self, tmp_path):
        """Given --output path,
        when generating changelog,
        then file exists at that path with content."""
        _init_git_repo(tmp_path)
        _create_commit(tmp_path, "feat: something")

        output_file = str(tmp_path / "dist" / "RELEASE_NOTES.md")
        result = _run_changelog_in_repo(
            tmp_path,
            "--stage",
            "rc",
            "--version",
            "1.0.0rc1",
            "--output",
            output_file,
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert Path(output_file).exists()
        content = _read_output(output_file)
        assert len(content) > 0
        assert "**Release candidate**" in content
        # Also verify stdout has the same content
        assert "**Release candidate**" in result.stdout
