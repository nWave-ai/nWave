"""CLI integration tests for `nwave-ai plugin` subcommand.

Tests cover dispatch, registry lookup, and error paths. They mock the
subprocess call so no real PyPI install fires.
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from nwave_ai.cli import KNOWN_PLUGINS, main


def _invoke(args: list[str]) -> tuple[int, str, str]:
    """Invoke CLI main() with given args. Returns (exit_code, stdout, stderr)."""
    out, err = StringIO(), StringIO()
    with (
        patch("sys.argv", ["nwave-ai", *args]),
        patch("sys.stdout", out),
        patch("sys.stderr", err),
    ):
        code = main()
    return code, out.getvalue(), err.getvalue()


def test_plugin_help_lists_known_plugins() -> None:
    code, stdout, _ = _invoke(["plugin", "--help"])
    assert code == 0
    assert "dedup" in stdout
    assert "nwave-dedup" in stdout


def test_plugin_list_machine_format() -> None:
    code, stdout, _ = _invoke(["plugin", "list"])
    assert code == 0
    # Tab-separated `<name>\t<package>` per line — script-friendly.
    assert "dedup\tnwave-dedup" in stdout


def test_plugin_install_unknown_name_fails() -> None:
    code, _, stderr = _invoke(["plugin", "install", "nope"])
    assert code == 1
    assert "Unknown plugin" in stderr


def test_plugin_install_missing_name_fails() -> None:
    code, _, stderr = _invoke(["plugin", "install"])
    assert code == 1
    assert "Missing plugin name" in stderr


def test_plugin_unknown_subcommand_fails() -> None:
    code, _, stderr = _invoke(["plugin", "weird"])
    assert code == 1
    assert "Unknown plugin subcommand" in stderr


def test_plugin_install_dispatches_to_subprocess() -> None:
    """Verify install path actually invokes pipx/pip with correct args."""
    fake_result = type("R", (), {"returncode": 0})()
    with (
        patch("nwave_ai.cli._resolve_installer", return_value=(["pipx"], "pipx")),
        patch("subprocess.run", return_value=fake_result) as mock_run,
        patch("shutil.which", return_value="/usr/bin/nwave-dedup"),
    ):
        code, _, _ = _invoke(["plugin", "install", "dedup"])
    assert code == 0
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd == ["pipx", "install", "nwave-dedup"]


def test_plugin_install_dispatches_to_uv_tool() -> None:
    """uv-first migration: plugin install via uv must shell out to `uv tool install`."""
    fake_result = type("R", (), {"returncode": 0})()
    with (
        patch("nwave_ai.cli._resolve_installer", return_value=(["uv", "tool"], "uv")),
        patch("subprocess.run", return_value=fake_result) as mock_run,
        patch("shutil.which", return_value="/usr/bin/nwave-dedup"),
    ):
        code, _, _ = _invoke(["plugin", "install", "dedup"])
    assert code == 0
    cmd = mock_run.call_args[0][0]
    assert cmd == ["uv", "tool", "install", "nwave-dedup"]


def test_plugin_uninstall_dispatches_to_uv_tool() -> None:
    """uv uninstall path must use `uv tool uninstall` (not `uv uninstall`)."""
    fake_result = type("R", (), {"returncode": 0})()
    with (
        patch("nwave_ai.cli._resolve_installer", return_value=(["uv", "tool"], "uv")),
        patch("subprocess.run", return_value=fake_result) as mock_run,
    ):
        code, _, _ = _invoke(["plugin", "uninstall", "dedup"])
    assert code == 0
    cmd = mock_run.call_args[0][0]
    assert cmd == ["uv", "tool", "uninstall", "nwave-dedup"]


def test_plugin_uninstall_pip_passes_yes_flag() -> None:
    """pip uninstall must be non-interactive (-y) or it hangs on non-TTY stdin."""
    fake_result = type("R", (), {"returncode": 0})()
    with (
        patch("nwave_ai.cli._resolve_installer", return_value=(["pip"], "pip")),
        patch("subprocess.run", return_value=fake_result) as mock_run,
    ):
        code, _, _ = _invoke(["plugin", "uninstall", "dedup"])
    assert code == 0
    cmd = mock_run.call_args[0][0]
    assert cmd == ["pip", "uninstall", "-y", "nwave-dedup"]


def test_plugin_install_pip_has_no_yes_flag() -> None:
    """The -y guard applies only to uninstall, not install."""
    fake_result = type("R", (), {"returncode": 0})()
    with (
        patch("nwave_ai.cli._resolve_installer", return_value=(["pip"], "pip")),
        patch("subprocess.run", return_value=fake_result) as mock_run,
        patch("shutil.which", return_value="/usr/bin/nwave-dedup"),
    ):
        code, _, _ = _invoke(["plugin", "install", "dedup"])
    assert code == 0
    cmd = mock_run.call_args[0][0]
    assert cmd == ["pip", "install", "nwave-dedup"]


def test_plugin_install_no_installer_available() -> None:
    with patch("nwave_ai.cli._resolve_installer", return_value=None):
        code, _, stderr = _invoke(["plugin", "install", "dedup"])
    assert code == 1
    # uv-first error message lists all supported installers.
    assert "uv" in stderr
    assert "pipx" in stderr


def test_known_plugins_registry_is_nonempty() -> None:
    """The registry must include at least the reference plugin."""
    assert "dedup" in KNOWN_PLUGINS
    assert KNOWN_PLUGINS["dedup"] == "nwave-dedup"
