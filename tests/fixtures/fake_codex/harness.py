"""Fake-codex harness — contract-equivalent fake of Codex hook invocation.

Implements the documented Codex hooks contract per the SPIKE artifact:
``docs/feature/codex-empirical-e2e-support/spike-codex-hooks-schema.md``.

The harness:
  1. Reads the installed ``hooks.json`` as an event-keyed object root (Q1).
     Rejects legacy top-level array shape with a ``FakeCodexSchemaError``.
  2. For a given tool event (Q2: ``PreToolUse``, ``PostToolUse``, ...), walks
     every matcher group whose regex matches the tool name (Q6).
  3. Invokes each matcher group's configured ``command`` string as a shell
     command (Q3 — no argv injection; cwd-only is what Codex documents),
     piping the documented stdin envelope (Q4) on stdin.
  4. Returns a ``HookInvocation`` per fired hook with the captured exit code
     (Q5), stdout, stderr, and the invoked command string.

The harness does NOT interpret hook output (allow/block decisions) — the
acceptance tests assert on the observable side-effects (audit log entries
written by the real DES adapter, which is what the configured command runs).
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class FakeCodexSchemaError(Exception):
    """Raised when ``hooks.json`` does not conform to the event-keyed schema.

    Mirrors the failure mode the real Codex binary would surface when the
    hooks file shape is incompatible — used by acceptance scenario 3 of
    walking-skeleton.feature ("fails for the right reason when hooks file
    has the legacy broken schema").
    """


@dataclass(frozen=True)
class HookInvocation:
    """Captures the outcome of a single fired hook command.

    Attributes:
        command: The literal command string from hooks.json (Q3 — invoked as-is).
        exit_code: Process exit code (Q5 semantics: 0=allow, 2=block).
        stdout: Captured stdout text.
        stderr: Captured stderr text (relevant for Q5 exit-2 blocking reasons).
        envelope: The stdin JSON envelope sent to the hook command (Q4).
    """

    command: str
    exit_code: int
    stdout: str
    stderr: str
    envelope: dict = field(default_factory=dict)


# Minimum required envelope keys per the Codex PreToolUse input JSON schema.
# Reference: docs/feature/codex-empirical-e2e-support/spike-codex-hooks-schema.md Q4
_REQUIRED_PRETOOLUSE_KEYS = (
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
)


class FakeCodexHarness:
    """Contract-equivalent fake of Codex hook invocation behavior.

    Args:
        hooks_path: Absolute path to the installed ``hooks.json``.
        env: Optional dict of environment variables passed to every invoked
             command. Tests use this to pipe ``DES_AUDIT_LOG_DIR`` and
             ``PYTHONPATH`` through to the real DES adapter.
        timeout_seconds: Per-command subprocess timeout (default 30s, matches
             the ``timeout`` field of the hooks.json command entries).
    """

    def __init__(
        self,
        hooks_path: Path,
        env: dict | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self._hooks_path = Path(hooks_path)
        self._env = dict(env) if env else {}
        self._timeout_seconds = timeout_seconds

    # -- Public API --------------------------------------------------------

    def load_hooks_document(self) -> dict:
        """Read and validate the hooks.json document.

        Returns:
            The event-keyed hooks document.

        Raises:
            FakeCodexSchemaError: If hooks.json is missing, malformed JSON, or
                has a non-object root (notably the legacy top-level-array shape
                used by pre-FM-1 installs).
        """
        if not self._hooks_path.exists():
            raise FakeCodexSchemaError(f"hooks.json not found at {self._hooks_path}")
        try:
            data = json.loads(self._hooks_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise FakeCodexSchemaError(f"hooks.json is not valid JSON: {exc}") from exc
        if isinstance(data, list):
            raise FakeCodexSchemaError(
                "hooks.json root must be an event-keyed object "
                '(e.g. {"hooks": {"PreToolUse": [...]}}); '
                "got top-level array (legacy pre-FM-1 schema)"
            )
        if not isinstance(data, dict):
            raise FakeCodexSchemaError(
                f"hooks.json root must be an object; got {type(data).__name__}"
            )
        hooks_obj = data.get("hooks")
        if not isinstance(hooks_obj, dict):
            raise FakeCodexSchemaError(
                "hooks.json must contain a 'hooks' object property; "
                f"got hooks={type(hooks_obj).__name__}"
            )
        return data

    def fire_pre_tool_use(
        self,
        tool_name: str,
        tool_input: dict | None = None,
        session_id: str = "fake-codex-session",
    ) -> list[HookInvocation]:
        """Simulate a PreToolUse event for a given tool.

        Loads hooks.json, walks every PreToolUse matcher group whose regex
        matches ``tool_name`` (Q6), builds the documented stdin envelope (Q4),
        and invokes each configured ``command`` string as a shell command (Q3).

        Args:
            tool_name: The Codex tool name (e.g. "Bash", "apply_patch").
            tool_input: Tool-specific payload (defaults to ``{}``).
            session_id: Synthetic session id for the envelope.

        Returns:
            One ``HookInvocation`` per fired hook command. Empty list if no
            matcher group matches ``tool_name``.

        Raises:
            FakeCodexSchemaError: Propagated from ``load_hooks_document``.
        """
        document = self.load_hooks_document()
        pretool_entries = document["hooks"].get("PreToolUse", [])
        if not isinstance(pretool_entries, list):
            return []

        envelope = self._build_pretool_envelope(
            tool_name=tool_name,
            tool_input=tool_input or {},
            session_id=session_id,
        )
        stdin_payload = json.dumps(envelope)

        invocations: list[HookInvocation] = []
        for matcher_group in pretool_entries:
            if not isinstance(matcher_group, dict):
                continue
            if not self._matcher_matches(matcher_group.get("matcher", ""), tool_name):
                continue
            for handler in matcher_group.get("hooks", []) or []:
                if not isinstance(handler, dict):
                    continue
                command = handler.get("command", "")
                if not isinstance(command, str) or not command:
                    continue
                invocations.append(
                    self._invoke_command(
                        command=command,
                        stdin_payload=stdin_payload,
                        envelope=envelope,
                    )
                )
        return invocations

    # -- Internals ---------------------------------------------------------

    @staticmethod
    def _matcher_matches(matcher: str, tool_name: str) -> bool:
        """Apply Codex matcher semantics (Q6).

        - ``"*"`` or empty string or missing: match everything.
        - Otherwise: treat as a Python regex and use ``re.search`` against
          the tool name (Codex docs say "regex string"; ``re.search`` covers
          both anchored (``^Bash$``) and unanchored (``Bash``) patterns).
        """
        if matcher in ("", "*"):
            return True
        try:
            return bool(re.search(matcher, tool_name))
        except re.error:
            return False

    @staticmethod
    def _build_pretool_envelope(
        tool_name: str, tool_input: dict, session_id: str
    ) -> dict:
        """Build a documented PreToolUse stdin envelope (Q4).

        All keys in ``_REQUIRED_PRETOOLUSE_KEYS`` are populated with
        schema-conformant values. ``transcript_path`` is nullable per the
        published JSON schema.
        """
        return {
            "cwd": "/tmp/fake-codex-cwd",
            "hook_event_name": "PreToolUse",
            "model": "gpt-5",
            "permission_mode": "default",
            "session_id": session_id,
            "tool_input": tool_input,
            "tool_name": tool_name,
            "tool_use_id": f"fake-tool-use-{session_id}",
            "transcript_path": None,
            "turn_id": f"fake-turn-{session_id}",
        }

    def _invoke_command(
        self, command: str, stdin_payload: str, envelope: dict
    ) -> HookInvocation:
        """Invoke a single hook ``command`` as a shell command (Q3).

        Mirrors what Codex documents: the literal ``command`` string runs in
        the session ``cwd`` working directory, with the JSON envelope on stdin
        and no positional argv injected by Codex.
        """
        try:
            proc = subprocess.run(
                command,
                shell=True,
                input=stdin_payload,
                capture_output=True,
                text=True,
                env=self._env or None,
                timeout=self._timeout_seconds,
            )
            return HookInvocation(
                command=command,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                envelope=envelope,
            )
        except subprocess.TimeoutExpired as exc:
            return HookInvocation(
                command=command,
                exit_code=124,  # conventional timeout exit code
                stdout=exc.stdout.decode("utf-8", errors="replace")
                if exc.stdout
                else "",
                stderr=(
                    exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
                )
                + f"\n[fake-codex] timeout after {self._timeout_seconds}s",
                envelope=envelope,
            )
