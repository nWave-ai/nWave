"""Regression tests for uv tool user environment detection in preflight checker.

These tests capture bugs F-01 (uv tool users blocked by VirtualEnvironmentCheck)
and F-08 (remediation message missing uv-specific instructions) from the
install-uv-primary feature design.

Tests 1-3 capture F-01 (is_virtual_environment detection), fixed in step 01-02.
Test 4 captures F-08 (remediation message), fixed in step 01-03.
Tests 5-6 harden D-02 (tool-aware remediation for pipx-only and no-tool cases).

Refs: install-uv-primary feature plan, architects convergence
Step-Id: 01-01, 01-03
"""

import sys

import pytest

from scripts.install.preflight_checker import (
    VirtualEnvironmentCheck,
    is_virtual_environment,
)


def test_is_virtual_env_true_when_uv_tool_env_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UV_TOOL_ENV set and VIRTUAL_ENV absent: must be detected as virtual environment.

    uv tool installs set UV_TOOL_ENV in the subprocess environment.
    VIRTUAL_ENV is NOT set because uv does not use the venv protocol.
    sys.prefix equals sys.base_prefix in this scenario.
    """
    monkeypatch.setenv("UV_TOOL_ENV", "1")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr(sys, "prefix", sys.base_prefix)

    assert is_virtual_environment() is True


def test_is_virtual_env_true_when_sys_executable_under_uv_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sys.executable under ~/.local/share/uv/tools must be detected as virtual environment.

    When uv tool installs nwave-ai, the Python interpreter lives under
    ~/.local/share/uv/tools/<package>/bin/python.
    Neither VIRTUAL_ENV nor UV_TOOL_ENV may be set; only the executable path
    indicates the managed environment.
    """
    monkeypatch.setattr(
        sys,
        "executable",
        "/home/test/.local/share/uv/tools/nwave-ai/bin/python",
    )
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("UV_TOOL_ENV", raising=False)
    monkeypatch.setattr(sys, "prefix", sys.base_prefix)

    assert is_virtual_environment() is True


def test_is_virtual_env_true_when_sys_executable_under_pipx_venvs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sys.executable under ~/.local/share/pipx/venvs must be detected as virtual environment.

    Hardens path-based detection: mirrors the uv/tools pattern for pipx-installed tools.
    pipx creates isolated venvs under ~/.local/share/pipx/venvs/<package>/bin/python.
    VIRTUAL_ENV is not always set when entering via a subprocess call.
    """
    monkeypatch.setattr(
        sys,
        "executable",
        "/home/test/.local/share/pipx/venvs/nwave-ai/bin/python",
    )
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("UV_TOOL_ENV", raising=False)
    monkeypatch.setattr(sys, "prefix", sys.base_prefix)

    assert is_virtual_environment() is True


def test_remediation_mentions_uv_when_uv_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When uv is on PATH, remediation must guide the user to use uv tool install.

    Forces all detection paths to return False (no virtual environment found):
    - sys.prefix == sys.base_prefix
    - VIRTUAL_ENV not set
    - UV_TOOL_ENV not set
    - sys.executable does NOT contain uv/tools or pipx/venvs

    Then verifies that VirtualEnvironmentCheck.run() returns a failing CheckResult
    whose remediation mentions 'uv tool install nwave-ai' because uv is on PATH,
    and does NOT present 'pip install nwave-ai' as the primary standalone command.

    Fixes F-08. Step-Id: 01-03.
    """
    monkeypatch.setattr(sys, "prefix", sys.base_prefix)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("UV_TOOL_ENV", raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")

    monkeypatch.setattr(
        "scripts.install.preflight_checker.shutil.which",
        lambda cmd: "/usr/bin/uv" if cmd == "uv" else None,
    )

    result = VirtualEnvironmentCheck().run()

    assert result.passed is False
    assert result.remediation is not None
    assert "uv tool install nwave-ai" in result.remediation
    assert "pip install nwave-ai" not in result.remediation


def test_remediation_mentions_pipx_when_only_pipx_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When only pipx is on PATH (no uv), remediation must guide user to use pipx install.

    Forces all detection paths to return False (no virtual environment found).
    shutil.which returns None for uv but a path for pipx.
    Verifies remediation mentions 'pipx install nwave-ai' and not 'uv tool install'.

    Hardens D-02 tool-aware remediation for pipx-only case. Step-Id: 01-03.
    """
    monkeypatch.setattr(sys, "prefix", sys.base_prefix)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("UV_TOOL_ENV", raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")

    monkeypatch.setattr(
        "scripts.install.preflight_checker.shutil.which",
        lambda cmd: "/usr/local/bin/pipx" if cmd == "pipx" else None,
    )

    result = VirtualEnvironmentCheck().run()

    assert result.passed is False
    assert result.remediation is not None
    assert "pipx install nwave-ai" in result.remediation
    assert "uv tool install nwave-ai" not in result.remediation
    assert "pip install nwave-ai" not in result.remediation


def test_remediation_suggests_installing_uv_when_no_tool_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When neither uv nor pipx is on PATH, remediation must suggest installing uv first.

    Forces all detection paths to return False (no virtual environment found).
    shutil.which returns None for both uv and pipx.
    Verifies remediation includes the curl install command for uv and 'uv tool install nwave-ai'.

    Hardens D-02 tool-aware remediation for no-tool case. Step-Id: 01-03.
    """
    monkeypatch.setattr(sys, "prefix", sys.base_prefix)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("UV_TOOL_ENV", raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")

    monkeypatch.setattr(
        "scripts.install.preflight_checker.shutil.which",
        lambda cmd: None,
    )

    result = VirtualEnvironmentCheck().run()

    assert result.passed is False
    assert result.remediation is not None
    assert "astral.sh/uv" in result.remediation
    assert "uv tool install nwave-ai" in result.remediation
    assert "pip install nwave-ai" not in result.remediation
