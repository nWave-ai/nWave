"""E2E: Codex+DES end-to-end empirical proof (US-4 / FM-4 closure).

Walking-skeleton-grade e2e that proves the three infrastructure fixes
(slices 01/02/03 → event-keyed schema, argv token, narrow matcher) compose
all the way through to a DES audit-log entry.

Strategy B variant per DDD-2: the real ``codex`` binary is not assumed
available on every CI runner. The test uses the documented fake-codex
harness (``tests/fixtures/fake_codex/harness.py``) which is contract-
equivalent to the real binary per the SPIKE artifact:

  docs/feature/codex-empirical-e2e-support/spike-codex-hooks-schema.md

A future ticket can wrap the harness in testcontainers; the contract this
test asserts is stable regardless of which side (real or fake) fires the
hook command.

Port-to-port litmus: if ``CodexDESPlugin._build_hook_entry`` is unwired
(e.g. drops the event-token, drops the matcher, or writes a top-level
array), this test fails — either on schema-shape, exit-code, or absence
of the HOOK_INVOKED / HOOK_COMPLETED audit entry.

Closes FM-4: ``tests/e2e/test_codex_full_install.py::test_codex_des_hook_installed``
asserted the INTERNAL schema shape (top-level array), which precluded any
empirical test of the install. This file replaces that with a genuine
end-to-end fire of the DES adapter from a Codex-shaped invocation.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.codex_des_plugin import CodexDESPlugin
from tests.fixtures.fake_codex import FakeCodexHarness


# --- Fixtures --------------------------------------------------------------


@pytest.fixture
def codex_home(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    """tmp-scoped Codex configuration directory."""
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CODEX_HOME", str(codex_dir))
    return codex_dir


@pytest.fixture
def audit_log_dir(tmp_path):  # type: ignore[no-untyped-def]
    """tmp-scoped directory where the DES adapter writes audit JSONL files."""
    audit_dir = tmp_path / "audit-logs"
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


@pytest.fixture
def install_context(tmp_path, codex_home):  # type: ignore[no-untyped-def]
    """InstallContext pointing at tmp-scoped dirs with DES module present."""
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
    """Bind the installed command to the current interpreter + repo src/.

    The plugin normally resolves the python interpreter and PYTHONPATH for
    the user's environment; here we redirect them to the live test
    interpreter so the produced command actually runs the real DES adapter
    in this process tree.
    """
    repo_src = Path(__file__).resolve().parents[2] / "src"
    monkeypatch.setattr(
        "scripts.install.plugins.codex_des_plugin.resolve_python_command_for_spawn",
        lambda: sys.executable,
    )
    monkeypatch.setattr(
        "scripts.install.plugins.codex_des_plugin.resolve_des_lib_path_for_spawn",
        lambda: str(repo_src),
    )


# --- Helpers ---------------------------------------------------------------


def _read_audit_entries(audit_dir: Path) -> list[dict]:
    entries: list[dict] = []
    if not audit_dir.exists():
        return entries
    for log_file in sorted(audit_dir.glob("audit-*.log")):
        for line in log_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


# --- Tests -----------------------------------------------------------------


@pytest.mark.e2e
class TestCodexRealBoot:
    """End-to-end proof that an installed Codex hook fires the real DES adapter."""

    def test_bash_invocation_fires_des_hook_invoked_and_completed(
        self,
        install_context: InstallContext,
        patched_resolvers,
        codex_home: Path,
        audit_log_dir: Path,
    ) -> None:
        """A Bash tool event must trigger HOOK_INVOKED + HOOK_COMPLETED entries.

        Steps:
          1. Run the Codex DES installer plugin against a tmp ~/.codex/.
          2. Load the installed hooks.json with the fake-codex harness.
          3. Fire a synthetic Bash PreToolUse event.
          4. Read the DES audit-log JSONL and assert both diagnostic events
             are present, with ``handler=pre_tool_use`` and exit_code=0.
        """
        test_window_start = datetime.now(timezone.utc).isoformat()

        # 1. Install
        result = CodexDESPlugin().install(install_context)
        assert result.success, f"install must succeed; got {result.message}"

        hooks_path = codex_home / "hooks.json"
        assert hooks_path.exists()

        # 2. Boot fake-codex harness pointed at the installed hooks file.
        repo_src = Path(__file__).resolve().parents[2] / "src"
        harness = FakeCodexHarness(
            hooks_path,
            env={
                "PATH": "/usr/bin:/bin",
                "DES_AUDIT_LOG_DIR": str(audit_log_dir),
                "PYTHONPATH": str(repo_src),
                "HOME": str(install_context.claude_dir.parent),
            },
        )

        # 3. Fire the Bash event — the installed hook command runs the real
        #    DES adapter, which writes HOOK_INVOKED + HOOK_COMPLETED audit
        #    entries to DES_AUDIT_LOG_DIR.
        invocations = harness.fire_pre_tool_use(
            tool_name="Bash", tool_input={"command": "echo hello"}
        )
        assert len(invocations) == 1, (
            f"expected exactly one PreToolUse hook to fire; got {len(invocations)}"
        )
        invocation = invocations[0]
        assert invocation.exit_code == 0, (
            f"hook must exit 0 (allow); got {invocation.exit_code}\n"
            f"stderr: {invocation.stderr!r}"
        )

        # 4. Assert audit-log diagnostic entries.
        entries = _read_audit_entries(audit_log_dir)
        invoked = [
            e
            for e in entries
            if e.get("event") == "HOOK_INVOKED" and e.get("handler") == "pre_tool_use"
        ]
        completed = [
            e
            for e in entries
            if e.get("event") == "HOOK_COMPLETED"
            and e.get("handler") == "pre_tool_use"
            and e.get("exit_code") == 0
        ]
        assert invoked, (
            f"audit log must contain HOOK_INVOKED with handler=pre_tool_use; "
            f"got events={[e.get('event') for e in entries]}"
        )
        assert completed, (
            f"audit log must contain HOOK_COMPLETED with handler=pre_tool_use, exit_code=0; "
            f"got events={[(e.get('event'), e.get('handler'), e.get('exit_code')) for e in entries]}"
        )

        # Test window — both diagnostic entries fall within bounds.
        test_window_end = datetime.now(timezone.utc).isoformat()
        for entry in invoked + completed:
            ts = entry.get("timestamp", "")
            assert test_window_start <= ts <= test_window_end, (
                f"audit entry timestamp {ts!r} outside test window "
                f"[{test_window_start}, {test_window_end}]"
            )

    def test_legacy_top_level_array_schema_blocks_harness_load(
        self, codex_home: Path
    ) -> None:
        """If hooks.json was left in the legacy top-level array shape, the
        harness must surface a schema-shape error and fire no hook.

        This is the failure mode the SPIKE Q1 + DDD-1 / FM-1 fix prevents.
        """
        from tests.fixtures.fake_codex import FakeCodexSchemaError

        legacy_doc = [
            {
                "matcher": "^Bash$",
                "hooks": [{"type": "command", "command": "true", "timeout": 5}],
            }
        ]
        hooks_path = codex_home / "hooks.json"
        hooks_path.write_text(json.dumps(legacy_doc, indent=2) + "\n", encoding="utf-8")

        harness = FakeCodexHarness(hooks_path)
        with pytest.raises(FakeCodexSchemaError, match="top-level array"):
            harness.fire_pre_tool_use(tool_name="Bash")
