"""Step bodies for slice-03 (US-2) — DES hook adapter argv contract.

Driving port: ``CodexDESPlugin.install(context)`` followed by direct subprocess
invocation of the produced command string against a tmp ``DES_AUDIT_LOG_DIR``.
Port-to-port: if `_build_hook_entry` does NOT append the ``pre-tool-use`` token,
the first scenario fails on the schema assertion (token-end), the second fails
on exit-code (adapter exits 1 on missing argv), and the audit-log scenario
fails on the absence of HOOK_INVOKED.

Adapter contract source: hook_router.py (verified at DDD-4).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from scripts.install.plugins.codex_des_plugin import CodexDESPlugin


scenarios("../argv-contract.feature")


# --- Helpers ---------------------------------------------------------------


def _read_hooks(hooks_path: Path) -> dict:
    return json.loads(hooks_path.read_text(encoding="utf-8"))


def _pretool_entries(parsed: dict) -> list[dict]:
    assert isinstance(parsed, dict)
    return parsed.get("hooks", {}).get("PreToolUse", [])


def _nwave_command_strings(parsed: dict) -> list[str]:
    """Every command string that targets the DES adapter."""
    cmds: list[str] = []
    for entry in _pretool_entries(parsed):
        for handler in entry.get("hooks", []):
            cmd = handler.get("command", "")
            if "claude_code_hook_adapter" in cmd:
                cmds.append(cmd)
    return cmds


def _synthetic_codex_pretool_stdin() -> str:
    """Synthetic Codex PreToolUse envelope (matches spike Q4 required fields)."""
    return json.dumps(
        {
            "cwd": "/tmp/fake-cwd",
            "hook_event_name": "PreToolUse",
            "model": "gpt-5",
            "permission_mode": "default",
            "session_id": "test-session",
            "tool_input": {"command": "echo hello"},
            "tool_name": "Bash",
            "tool_use_id": "test-tool-use-id",
            "transcript_path": None,
            "turn_id": "test-turn",
        }
    )


def _run_installer(install_context, patched_resolvers, state, hooks_path) -> None:
    """Driving port: run the installer plugin and stash the produced command."""
    plugin = CodexDESPlugin()
    result = plugin.install(install_context)
    state["install_result"] = result
    assert result.success, f"install must succeed; got {result.message}"
    assert hooks_path.exists(), f"hooks.json must be written at {hooks_path}"
    parsed = _read_hooks(hooks_path)
    state["parsed_hooks"] = parsed
    state["commands"] = _nwave_command_strings(parsed)
    assert state["commands"], "installer must produce at least one nWave command"


def _invoke_adapter(
    command: str, stdin: str, audit_dir: Path
) -> subprocess.CompletedProcess:
    """Invoke the installed hook command as a real subprocess.

    The patched_resolvers fixture seeds the command string with
    /usr/bin/python3 and /home/tester/.claude/lib/python — neither suitable
    for actual subprocess execution. We therefore re-bind to the current
    interpreter + repo src/ via env, but preserve the trailing argv tokens
    (the part that step 01-02 is contractually testing).
    """
    # Extract trailing argv: everything after `claude_code_hook_adapter` token.
    marker = "claude_code_hook_adapter"
    idx = command.find(marker)
    assert idx != -1, f"command must reference adapter; got {command!r}"
    trailing = command[idx + len(marker) :].strip().split()

    env = {
        "PATH": "/usr/bin:/bin",
        "DES_AUDIT_LOG_DIR": str(audit_dir),
        "PYTHONPATH": str(Path(__file__).resolve().parents[5] / "src"),
        "HOME": str(audit_dir.parent),
    }
    cmd = [
        sys.executable,
        "-m",
        "des.adapters.drivers.hooks.claude_code_hook_adapter",
        *trailing,
    ]
    return subprocess.run(
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


def _read_audit_entries(audit_dir: Path) -> list[dict]:
    """Read every JSONL line written to the audit directory."""
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


# --- Given -----------------------------------------------------------------


@given("a clean Codex environment with no prior nWave hooks")
def clean_codex_environment(codex_home: Path) -> None:
    assert codex_home.is_dir()
    assert not (codex_home / "hooks.json").exists()


@given("the nwave-ai installer has been run with --platform codex")
def installer_already_run(
    install_context, patched_resolvers, hooks_path, state
) -> None:
    _run_installer(install_context, patched_resolvers, state, hooks_path)


# --- When ------------------------------------------------------------------


@when("the nwave-ai installer is run with --platform codex")
def installer_run_codex(install_context, patched_resolvers, hooks_path, state) -> None:
    _run_installer(install_context, patched_resolvers, state, hooks_path)


@when(
    "the installed PreToolUse hook command is invoked with a synthetic Codex Bash tool-event stdin payload"
)
def invoke_hook_command_synthetic_stdin(state, tmp_path) -> None:
    audit_dir = tmp_path / "audit-logs"
    audit_dir.mkdir(parents=True, exist_ok=True)
    state["audit_dir"] = audit_dir
    command = state["commands"][0]
    state["proc"] = _invoke_adapter(
        command, _synthetic_codex_pretool_stdin(), audit_dir
    )


@when("the DES adapter entrypoint is invoked with no event positional argument")
def invoke_adapter_without_argv(state, tmp_path) -> None:
    audit_dir = tmp_path / "audit-logs"
    audit_dir.mkdir(parents=True, exist_ok=True)
    state["audit_dir"] = audit_dir
    # Bypass the installed command — call the entrypoint with empty argv.
    env = {
        "PATH": "/usr/bin:/bin",
        "DES_AUDIT_LOG_DIR": str(audit_dir),
        "PYTHONPATH": str(Path(__file__).resolve().parents[5] / "src"),
        "HOME": str(audit_dir.parent),
    }
    state["proc"] = subprocess.run(
        [sys.executable, "-m", "des.adapters.drivers.hooks.claude_code_hook_adapter"],
        input="",
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


@when("the installed PreToolUse hook command is invoked with malformed JSON on stdin")
def invoke_hook_command_malformed_stdin(state, tmp_path) -> None:
    audit_dir = tmp_path / "audit-logs"
    audit_dir.mkdir(parents=True, exist_ok=True)
    state["audit_dir"] = audit_dir
    command = state["commands"][0]
    state["proc"] = _invoke_adapter(command, "{not valid json,,,", audit_dir)


# --- Then ------------------------------------------------------------------


@then(
    parsers.parse('every nWave PreToolUse command string ends with the token "{token}"')
)
def command_ends_with_token(token: str, state) -> None:
    commands = state["commands"]
    assert commands, "must have at least one nWave command to inspect"
    for cmd in commands:
        tokens = cmd.strip().split()
        assert tokens[-1] == token, (
            f"command must end with token {token!r}; got tail {tokens[-3:]!r} "
            f"(full: {cmd!r})"
        )


@then("no command string omits the event positional argument")
def no_command_omits_argv(state) -> None:
    valid_events = {
        "pre-tool-use",
        "pre-task",
        "subagent-stop",
        "post-tool-use",
        "pre-write",
        "pre-edit",
        "session-start",
        "subagent-start",
        "deliver-progress",
    }
    for cmd in state["commands"]:
        tokens = cmd.strip().split()
        assert tokens[-1] in valid_events, (
            f"command final token must be a valid event; got {tokens[-1]!r} "
            f"(full: {cmd!r})"
        )


@then(parsers.parse("the adapter exits with status {code:d}"))
def adapter_exit_status(code: int, state) -> None:
    proc = state["proc"]
    assert proc.returncode == code, (
        f"adapter must exit with {code}; got {proc.returncode}\n"
        f"stdout: {proc.stdout!r}\nstderr: {proc.stderr!r}"
    )


@then("the adapter writes at least one observable artifact")
def adapter_writes_artifact(state) -> None:
    audit_dir: Path = state["audit_dir"]
    entries = _read_audit_entries(audit_dir)
    assert entries, (
        f"adapter must write at least one audit entry; "
        f"audit_dir={audit_dir} contents={list(audit_dir.glob('*'))}"
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
        f"got events={[e.get('event') for e in entries]}"
    )


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
        f"audit log must contain HOOK_COMPLETED for handler={handler!r} "
        f"exit_code={code}; got events={[(e.get('event'), e.get('exit_code')) for e in entries]}"
    )


@then(parsers.parse('the error reason mentions "{phrase}"'))
def error_reason_mentions(phrase: str, state) -> None:
    proc = state["proc"]
    haystack = (proc.stdout or "") + (proc.stderr or "")
    assert phrase in haystack, (
        f"error output must mention {phrase!r}; got stdout={proc.stdout!r} "
        f"stderr={proc.stderr!r}"
    )


@then("the adapter does not raise an uncaught exception")
def adapter_does_not_raise_uncaught(state) -> None:
    proc = state["proc"]
    # Uncaught exceptions surface as a Python Traceback on stderr.
    assert "Traceback" not in (proc.stderr or ""), (
        f"adapter must not raise uncaught exception; stderr={proc.stderr!r}"
    )


@then(
    parsers.parse(
        'the adapter emits a HOOK_PROTOCOL_ANOMALY audit entry with anomaly_type "{anomaly}"'
    )
)
def adapter_emits_protocol_anomaly(anomaly: str, state) -> None:
    entries = _read_audit_entries(state["audit_dir"])
    matching = [
        e
        for e in entries
        if e.get("event") == "HOOK_PROTOCOL_ANOMALY"
        and e.get("anomaly_type") == anomaly
    ]
    assert matching, (
        f"audit log must contain HOOK_PROTOCOL_ANOMALY for anomaly_type={anomaly!r}; "
        f"got events={[(e.get('event'), e.get('anomaly_type')) for e in entries]}"
    )
