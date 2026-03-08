"""Tests for nwave_ai/cli.py

Thin CLI wrapper that dispatches install/uninstall/version commands
to the appropriate scripts under scripts/install/.

BDD scenario mapping:
  - Version resolution: metadata lookup with __version__ fallback
  - Project root: resolves to repo root from cli.py location
  - Run script: subprocess dispatch with missing-script guard
  - Main dispatch: routes commands to correct handlers
  - Usage: prints formatted help text
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from nwave_ai.cli import (
    _get_project_root,
    _get_version,
    _print_usage,
    _run_script,
    main,
)


class TestVersionResolution:
    """_get_version() fallback chain: metadata then __version__."""

    def test_returns_metadata_version_when_installed(self):
        """Given nwave-ai is pip-installed,
        when _get_version() is called,
        then it returns the metadata version string.
        """
        with patch("importlib.metadata.version", return_value="1.2.3"):
            assert _get_version() == "1.2.3"

    def test_falls_back_to_dunder_version(self):
        """Given no package metadata is available,
        when _get_version() is called,
        then it falls back to nwave_ai.__version__.
        """
        from importlib.metadata import PackageNotFoundError

        with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
            result = _get_version()
        assert result == "0.0.0-dev"

    def test_never_falls_back_to_nwave_package(self):
        """Given 'nwave-ai' lookup fails but 'nwave' is installed,
        when _get_version() is called,
        then it must NOT return the 'nwave' version (regression: stale version bug).
        It should fall through to __version__ instead.
        """
        from importlib.metadata import PackageNotFoundError

        def _version_side_effect(name):
            if name == "nwave-ai":
                raise PackageNotFoundError
            if name == "nwave":
                return "1.5.0"  # stale dev version
            raise PackageNotFoundError

        with patch("importlib.metadata.version", side_effect=_version_side_effect):
            result = _get_version()
        assert result != "1.5.0", "Must not fall back to 'nwave' package metadata"


class TestProjectRoot:
    """_get_project_root() returns the repo root."""

    def test_returns_parent_of_nwave_ai_package(self):
        """Given cli.py lives in nwave_ai/,
        when _get_project_root() is called,
        then it returns nwave_ai's parent (the repo root).
        """
        root = _get_project_root()
        assert root == Path(__file__).parent.parent.parent
        assert (root / "nwave_ai" / "cli.py").exists()


class TestRunScript:
    """_run_script() subprocess dispatch."""

    def test_calls_subprocess_with_correct_args(self, tmp_path):
        """Given a valid script path,
        when _run_script() is called,
        then it invokes subprocess.run with the right command.
        """
        mock_result = MagicMock(returncode=0)
        with (
            patch("nwave_ai.cli._get_project_root", return_value=tmp_path),
            patch("nwave_ai.cli.subprocess.run", return_value=mock_result) as mock_run,
        ):
            script_dir = tmp_path / "scripts" / "install"
            script_dir.mkdir(parents=True)
            (script_dir / "install_nwave.py").touch()

            code = _run_script("install_nwave.py", ["--dry-run"])

        assert code == 0
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[1].endswith("install_nwave.py")
        assert "--dry-run" in cmd
        assert call_args[1]["cwd"] == str(tmp_path)

    def test_returns_1_when_script_missing(self, tmp_path, capsys):
        """Given the script file does not exist,
        when _run_script() is called,
        then it prints an error and returns 1.
        """
        with patch("nwave_ai.cli._get_project_root", return_value=tmp_path):
            code = _run_script("missing.py", [])

        assert code == 1
        err = capsys.readouterr().err
        assert "missing.py not found" in err

    def test_propagates_subprocess_return_code(self, tmp_path):
        """Given the subprocess exits with code 42,
        when _run_script() is called,
        then it returns 42.
        """
        mock_result = MagicMock(returncode=42)
        with (
            patch("nwave_ai.cli._get_project_root", return_value=tmp_path),
            patch("nwave_ai.cli.subprocess.run", return_value=mock_result),
        ):
            script_dir = tmp_path / "scripts" / "install"
            script_dir.mkdir(parents=True)
            (script_dir / "install_nwave.py").touch()

            code = _run_script("install_nwave.py", [])

        assert code == 42


class TestMainDispatch:
    """main() routes commands to the correct handlers."""

    def test_install_routes_to_run_script(self):
        """Given argv=['nwave-ai', 'install', '--dry-run'],
        when main() is called,
        then it dispatches to _run_script('install_nwave.py', ['--dry-run']).
        """
        with (
            patch("nwave_ai.cli.sys.argv", ["nwave-ai", "install", "--dry-run"]),
            patch("nwave_ai.cli._run_script", return_value=0) as mock_rs,
        ):
            code = main()

        assert code == 0
        mock_rs.assert_called_once_with("install_nwave.py", ["--dry-run"])

    def test_uninstall_routes_to_run_script(self):
        """Given argv=['nwave-ai', 'uninstall'],
        when main() is called,
        then it dispatches to _run_script('uninstall_nwave.py', []).
        """
        with (
            patch("nwave_ai.cli.sys.argv", ["nwave-ai", "uninstall"]),
            patch("nwave_ai.cli._run_script", return_value=0) as mock_rs,
        ):
            code = main()

        assert code == 0
        mock_rs.assert_called_once_with("uninstall_nwave.py", [])

    def test_version_prints_version(self, capsys):
        """Given argv=['nwave-ai', 'version'],
        when main() is called,
        then it prints the version string and returns 0.
        """
        with (
            patch("nwave_ai.cli.sys.argv", ["nwave-ai", "version"]),
            patch("nwave_ai.cli._get_version", return_value="3.4.5"),
        ):
            code = main()

        assert code == 0
        assert "3.4.5" in capsys.readouterr().out

    def test_help_flag_prints_usage(self, capsys):
        """Given argv=['nwave-ai', '--help'],
        when main() is called,
        then it prints usage and returns 0.
        """
        with (
            patch("nwave_ai.cli.sys.argv", ["nwave-ai", "--help"]),
            patch("nwave_ai.cli._get_version", return_value="1.0.0"),
        ):
            code = main()

        assert code == 0
        out = capsys.readouterr().out
        assert "Usage:" in out

    def test_no_args_prints_usage(self, capsys):
        """Given argv=['nwave-ai'] (no command),
        when main() is called,
        then it prints usage and returns 0.
        """
        with (
            patch("nwave_ai.cli.sys.argv", ["nwave-ai"]),
            patch("nwave_ai.cli._get_version", return_value="1.0.0"),
        ):
            code = main()

        assert code == 0
        assert "Usage:" in capsys.readouterr().out

    def test_unknown_command_returns_1(self, capsys):
        """Given argv=['nwave-ai', 'bogus'],
        when main() is called,
        then it prints an error and returns 1.
        """
        with patch("nwave_ai.cli.sys.argv", ["nwave-ai", "bogus"]):
            code = main()

        assert code == 1
        err = capsys.readouterr().err
        assert "Unknown command: bogus" in err


class TestUsage:
    """_print_usage() output format."""

    def test_includes_version_and_commands(self, capsys):
        """Given a version string,
        when _print_usage() is called,
        then it prints version header, commands, and options.
        """
        with patch("nwave_ai.cli._get_version", return_value="9.8.7"):
            code = _print_usage()

        assert code == 0
        out = capsys.readouterr().out
        assert "nwave-ai 9.8.7" in out
        assert "install" in out
        assert "uninstall" in out
        assert "version" in out
        assert "--dry-run" in out

    def test_returns_zero(self):
        """_print_usage() always returns 0."""
        with patch("nwave_ai.cli._get_version", return_value="0.0.0"):
            assert _print_usage() == 0
