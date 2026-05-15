"""Shared fixtures for codex-empirical-e2e-support acceptance tests.

DELIVER fills the live bodies. DISTILL left NotImplementedError markers so the
suite was RED for the right reason (implementation missing).

Placed at the feature root (sibling of .feature files), NOT under steps/, to
avoid a pytest plugin-name collision with sibling features that also contain a
steps/conftest.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from scripts.install.plugins.base import InstallContext


@pytest.fixture
def codex_home(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    """Provide a tmp_path-scoped CODEX_HOME for the installer to write into.

    Sets the CODEX_HOME env var so the plugin's _codex_config_dir() resolves
    to a clean tmp path. Auto-reverted by monkeypatch on teardown.
    """
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CODEX_HOME", str(codex_dir))
    return codex_dir


@pytest.fixture
def des_audit_log_path(tmp_path):  # type: ignore[no-untyped-def]
    """Provide a tmp_path-scoped DES audit log JSONL file path.

    Reserved for step 01-02 (argv contract scenarios that actually fire the
    adapter). For 01-01 the file is not read, but the fixture is wired here
    so steps importing it don't error during collection.
    """
    return tmp_path / "des-audit.jsonl"


@pytest.fixture
def codex_tool_whitelist():  # type: ignore[no-untyped-def]
    """Vetted whitelist of Codex tool names sourced from DDD-8 spike artifact.

    DDD-6 (refined by DDD-8 spike): matcher universe = {Bash, apply_patch}.
    MCP names deferred per spike Q6 + open question 3. Used by step 01-03.
    """
    return ("Bash", "apply_patch")


@pytest.fixture
def fake_codex_harness():  # type: ignore[no-untyped-def]
    """Fake-codex harness placeholder for step 02-01.

    Step 01-01 does not boot the harness — fixture exists so step modules
    importing it don't error during collection.
    """
    return None


@pytest.fixture
def install_context(tmp_path, codex_home):  # type: ignore[no-untyped-def]
    """Build a real InstallContext pointing at tmp_path-scoped dirs.

    The DES module directory is created so validate_prerequisites() proceeds
    past the dependency check. This is the canonical driving-port fixture for
    every acceptance scenario in this feature.
    """
    project_root = tmp_path / "project"
    framework_source = project_root / "nWave"
    framework_source.mkdir(parents=True, exist_ok=True)

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    des_dir = claude_dir / "lib" / "python" / "des"
    des_dir.mkdir(parents=True, exist_ok=True)
    (des_dir / "__init__.py").write_text("", encoding="utf-8")

    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts",
        templates_dir=framework_source / "templates",
        logger=MagicMock(),
        project_root=project_root,
        framework_source=framework_source,
    )


@pytest.fixture
def patched_resolvers(monkeypatch):  # type: ignore[no-untyped-def]
    """Force deterministic Python and PYTHONPATH resolution in the plugin."""
    monkeypatch.setattr(
        "scripts.install.plugins.codex_des_plugin.resolve_python_command_for_spawn",
        lambda: "/usr/bin/python3",
    )
    monkeypatch.setattr(
        "scripts.install.plugins.codex_des_plugin.resolve_des_lib_path_for_spawn",
        lambda: "/home/tester/.claude/lib/python",
    )


@pytest.fixture
def hooks_path(codex_home):  # type: ignore[no-untyped-def]
    """Absolute path to the installed Codex hooks.json under tmp."""
    return codex_home / "hooks.json"


@pytest.fixture
def state():  # type: ignore[no-untyped-def]
    """Per-scenario shared dict so Given/When steps can hand context to Then.

    pytest-bdd does not auto-thread context between step functions; tests use
    this fixture as the explicit context bag.
    """
    return {}
