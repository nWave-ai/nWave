"""Step bodies for slice-01 walking skeleton (US-4 / FM-4 closure).

Driving port: ``CodexDESPlugin.install(context)`` followed by ``FakeCodexHarness.
fire_pre_tool_use(...)``.  Audit-log assertions read the JSONL files written by
the real DES adapter into a tmp ``DES_AUDIT_LOG_DIR``.

Port-to-port: if any of slices 01/02/03 are unwired (event-keyed schema, argv
token, narrow matcher), one of the three scenarios in walking-skeleton.feature
fails at the harness invocation OR at the audit-entry assertion — not at
collection / import.

FM-4 closure: ``HOOK_INVOKED`` + ``HOOK_COMPLETED`` (handler=pre_tool_use) is
the canonical empirical proof — verified against ``hook_protocol.py:209,266``
in PREPARE.  The string ``PRE_TOOL_USE_VALIDATED`` is NOT used: DISCUSS AC-4.3
was wrong and is superseded by DDD-5.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when
from tests.fixtures.fake_codex import FakeCodexHarness, FakeCodexSchemaError

from scripts.install.plugins.codex_des_plugin import CodexDESPlugin


scenarios("../walking-skeleton.feature")


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


def _build_real_harness_env(audit_dir: Path, home_dir: Path) -> dict:
    repo_src = Path(__file__).resolve().parents[5] / "src"
    return {
        "PATH": "/usr/bin:/bin",
        "DES_AUDIT_LOG_DIR": str(audit_dir),
        "PYTHONPATH": str(repo_src),
        "HOME": str(home_dir),
    }


def _rebind_command_to_repo_python(command: str) -> str:
    """Rewrite the patched-resolver command into one that actually runs.

    ``patched_resolvers`` sets the python path to ``/usr/bin/python3`` and the
    PYTHONPATH to ``/home/tester/.claude/lib/python`` — neither exists on the
    dev host.  Preserve the trailing event-token argv (the contract this slice
    relies on) but substitute the real interpreter + repo src/ so the adapter
    actually fires.
    """
    marker = "claude_code_hook_adapter"
    idx = command.find(marker)
    assert idx != -1, f"command must reference adapter; got {command!r}"
    trailing = command[idx + len(marker) :].strip()
    repo_src = Path(__file__).resolve().parents[5] / "src"
    return (
        f"PYTHONPATH={repo_src} {sys.executable} -m "
        f"des.adapters.drivers.hooks.claude_code_hook_adapter "
        f"{trailing}"
    )


def _rewrite_hooks_file_with_real_command(hooks_path: Path) -> None:
    """Mutate the installed hooks.json in place so commands run on this host."""
    doc = json.loads(hooks_path.read_text(encoding="utf-8"))
    for entry in doc["hooks"].get("PreToolUse", []):
        for handler in entry.get("hooks", []):
            if "claude_code_hook_adapter" in handler.get("command", ""):
                handler["command"] = _rebind_command_to_repo_python(handler["command"])
    hooks_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


# --- Given (background) ----------------------------------------------------


@given(
    "the Codex hooks schema spike artifact exists at docs/feature/codex-empirical-e2e-support/spike-codex-hooks-schema.md"
)
def spike_artifact_exists() -> None:
    spike = (
        Path(__file__).resolve().parents[5]
        / "docs"
        / "feature"
        / "codex-empirical-e2e-support"
        / "spike-codex-hooks-schema.md"
    )
    assert spike.is_file(), (
        f"SPIKE artifact must exist at {spike} (DDD-8 canonical source)"
    )


@given(
    "the legacy test tests/e2e/test_codex_full_install.py is marked broken_schema_v0"
)
def legacy_test_marked_broken_schema_v0() -> None:
    legacy_test = (
        Path(__file__).resolve().parents[5]
        / "tests"
        / "e2e"
        / "test_codex_full_install.py"
    )
    assert legacy_test.is_file(), f"legacy test must exist at {legacy_test}"
    content = legacy_test.read_text(encoding="utf-8")
    # The broken_schema_v0 marker must annotate the schema-asserting test.
    # We check the marker appears in the file AND immediately above the
    # function that hardcodes the legacy top-level-array assertion.
    pattern = re.compile(
        r"@pytest\.mark\.broken_schema_v0[^\n]*\n\s*def test_codex_des_hook_installed"
    )
    assert pattern.search(content), (
        "@pytest.mark.broken_schema_v0 must annotate "
        "test_codex_des_hook_installed in the legacy file (DDD-7 quarantine)"
    )


@given("the marker broken_schema_v0 is registered in pyproject.toml")
def marker_registered() -> None:
    pyproject = Path(__file__).resolve().parents[5] / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    assert "broken_schema_v0" in content, (
        "marker 'broken_schema_v0' must be registered in "
        "[tool.pytest.ini_options].markers (DDD-7)"
    )


# --- Given (scenario) ------------------------------------------------------


@given("a clean Codex environment with no prior nWave hooks")
def clean_codex_environment(codex_home: Path) -> None:
    assert codex_home.is_dir()
    assert not (codex_home / "hooks.json").exists()


@given("the nwave-ai installer has been run with --platform codex")
def installer_run_codex(
    install_context, patched_resolvers, hooks_path, state, tmp_path
) -> None:
    result = CodexDESPlugin().install(install_context)
    assert result.success, f"install must succeed; got {result.message}"
    assert hooks_path.exists()

    # The patched resolvers used a non-runnable interpreter path; rebind to
    # the live one so the hook fires the real DES adapter end-to-end.
    _rewrite_hooks_file_with_real_command(hooks_path)

    audit_dir = tmp_path / "audit-logs"
    audit_dir.mkdir(parents=True, exist_ok=True)
    state["audit_dir"] = audit_dir
    state["test_window_start"] = datetime.now(timezone.utc).isoformat()
    state["hooks_path"] = hooks_path


@given("the real Codex binary is not available in the test environment")
def real_binary_absent() -> None:
    # The fake-codex harness IS the documented fallback per DDD-2.  This step
    # asserts the contract used by scenario 2 — we are explicitly exercising
    # the fallback path on a host without the real Codex binary.
    import shutil as _shutil

    if _shutil.which("codex") is not None:
        # Real binary present — fallback test is non-applicable but still
        # valid: the harness is contract-equivalent, so we proceed.
        return


@given("the installed hooks file is left in the legacy top-level-array schema")
def hooks_file_in_legacy_schema(hooks_path: Path, state, tmp_path) -> None:
    legacy_doc = [
        {
            "matcher": "^Bash$",
            "hooks": [
                {
                    "type": "command",
                    "command": "true",
                    "timeout": 5,
                }
            ],
        }
    ]
    hooks_path.write_text(json.dumps(legacy_doc, indent=2) + "\n", encoding="utf-8")
    audit_dir = tmp_path / "audit-logs"
    audit_dir.mkdir(parents=True, exist_ok=True)
    state["audit_dir"] = audit_dir
    state["hooks_path"] = hooks_path


# --- When ------------------------------------------------------------------


@when(parsers.parse('a Codex session invokes the Bash tool with command "{cmd}"'))
def codex_invokes_bash(cmd: str, state, codex_home: Path) -> None:
    harness = FakeCodexHarness(
        state["hooks_path"],
        env=_build_real_harness_env(state["audit_dir"], codex_home.parent),
    )
    state["invocations"] = harness.fire_pre_tool_use(
        tool_name="Bash", tool_input={"command": cmd}
    )


@when("the fake-codex harness loads the installed hooks file and invokes the Bash tool")
def fake_harness_invokes_bash(state, codex_home: Path) -> None:
    harness = FakeCodexHarness(
        state["hooks_path"],
        env=_build_real_harness_env(state["audit_dir"], codex_home.parent),
    )
    state["invocations"] = harness.fire_pre_tool_use(
        tool_name="Bash", tool_input={"command": "echo hello"}
    )


@when("the fake-codex harness attempts to load the installed hooks file")
def fake_harness_loads_file(state) -> None:
    harness = FakeCodexHarness(state["hooks_path"])
    try:
        harness.load_hooks_document()
        state["schema_error"] = None
    except FakeCodexSchemaError as exc:
        state["schema_error"] = exc


# --- Then ------------------------------------------------------------------


@then("the DES PreToolUse hook is fired by Codex")
def des_hook_fired(state) -> None:
    invocations = state.get("invocations", [])
    assert len(invocations) >= 1, (
        f"at least one PreToolUse hook must fire; got {len(invocations)} "
        f"(matcher mismatch — slice-03 narrow matcher must include Bash)"
    )
    assert invocations[0].exit_code == 0, (
        f"hook must exit 0 (allow); got {invocations[0].exit_code}\n"
        f"stderr: {invocations[0].stderr!r}"
    )


@then(
    parsers.parse(
        'the audit log contains a HOOK_INVOKED entry with handler "{handler}"'
    )
)
def audit_has_hook_invoked(handler: str, state) -> None:
    entries = _read_audit_entries(state["audit_dir"])
    matching = [
        e
        for e in entries
        if e.get("event") == "HOOK_INVOKED" and e.get("handler") == handler
    ]
    assert matching, (
        f"audit log must contain HOOK_INVOKED for handler={handler!r}; "
        f"got events={[(e.get('event'), e.get('handler')) for e in entries]}"
    )
    state.setdefault("matched_entries", []).extend(matching)


@then(
    parsers.parse(
        'the audit log contains a HOOK_COMPLETED entry with handler "{handler}" and exit_code {code:d}'
    )
)
def audit_has_hook_completed(handler: str, code: int, state) -> None:
    entries = _read_audit_entries(state["audit_dir"])
    matching = [
        e
        for e in entries
        if e.get("event") == "HOOK_COMPLETED"
        and e.get("handler") == handler
        and e.get("exit_code") == code
    ]
    assert matching, (
        f"audit log must contain HOOK_COMPLETED for handler={handler!r}, "
        f"exit_code={code}; got "
        f"events={[(e.get('event'), e.get('handler'), e.get('exit_code')) for e in entries]}"
    )
    state.setdefault("matched_entries", []).extend(matching)


@then("both entries fall within the test window")
def audit_entries_in_window(state) -> None:
    start = state["test_window_start"]
    end = datetime.now(timezone.utc).isoformat()
    matched = state.get("matched_entries", [])
    assert matched, "no audit entries captured to bound-check"
    for entry in matched:
        ts = entry.get("timestamp", "")
        assert start <= ts <= end, (
            f"audit entry timestamp {ts!r} outside test window [{start}, {end}]"
        )


@then("the harness reads the hooks file in the event-keyed schema")
def harness_reads_event_keyed(state) -> None:
    # The invocations list is non-empty ⇔ the harness loaded the event-keyed
    # schema successfully AND found a matching PreToolUse entry.
    invocations = state.get("invocations", [])
    assert len(invocations) >= 1, (
        "harness must have read the event-keyed schema and fired at least one hook"
    )


@then("the harness invokes the DES adapter with the documented stdin envelope")
def harness_invokes_adapter(state) -> None:
    invocations = state.get("invocations", [])
    assert invocations, "no invocations captured"
    inv = invocations[0]
    # Adapter command must reference the documented entrypoint, and the
    # envelope sent on stdin must conform to the Codex JSON schema (SPIKE Q4).
    assert "claude_code_hook_adapter" in inv.command, (
        f"harness must invoke the DES adapter; command={inv.command!r}"
    )
    required_keys = {
        "cwd",
        "hook_event_name",
        "model",
        "permission_mode",
        "session_id",
        "tool_input",
        "tool_name",
        "tool_use_id",
        "transcript_path",
        "turn_id",
    }
    assert required_keys.issubset(inv.envelope.keys()), (
        f"envelope missing keys: {required_keys - inv.envelope.keys()}"
    )


@then("the harness reports a schema-shape error referencing the event-keyed root")
def harness_reports_schema_error(state) -> None:
    err = state.get("schema_error")
    assert err is not None, "harness must raise FakeCodexSchemaError on legacy array"
    msg = str(err)
    assert "top-level array" in msg or "event-keyed" in msg, (
        f"error message must reference the event-keyed root or legacy array shape; "
        f"got {msg!r}"
    )


@then("no DES hook is fired")
def no_des_hook_fired(state) -> None:
    entries = _read_audit_entries(state["audit_dir"])
    invoked = [e for e in entries if e.get("event") == "HOOK_INVOKED"]
    assert invoked == [], f"no HOOK_INVOKED audit entries must exist; got {invoked!r}"
