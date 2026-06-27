"""Composition root for the PreToolUse commit-attribution feature.

Two production-wired driving surfaces (Mandate 13 — driving-port-only):

  * `RewriteComposition` drives `CommitAttributionService.plan_rewrite`
    (Layer 3 composition root, return-only). ATs assert on the returned
    `CommitRewritePlan` with ZERO I/O. This is the @in-memory surface: the
    rewrite is a pure transformation with no driven adapters, so OR-reduction
    (Mandate 9 v2) tags these scenarios `@in-memory`.

  * `HookAdapterComposition` drives the real `pre-tool-use` hook adapter via
    subprocess — the same `python -m des.adapters.drivers.hooks.claude_code_hook_adapter
    pre-tool-use` entry point Claude Code dispatches in production (precedent:
    `tests/des/acceptance/test_hook_protocol_conformance.py`). The walking
    skeleton + the adapter mutation-branch scenario use this surface; it touches
    a real subprocess, so OR-reduction tags it `@real-io`.

Business logic lives here as the single source of truth; step bodies delegate to
composition methods and never inline logic (Mandate-12 criterion 3).

Mandate 15 / S3 (dormant-seam reconciliation): the DESIGN driving-surface
declares two net-new seams this feature ships —
`CommitAttributionService.plan_rewrite` (the pure-core entry) and the
`pre_tool_use_handler` mutation branch (`emit_commit_attribution_mutation`,
reached from the real `handle_pre_tool_use` entry point). Both are named here as
the ports the ATs drive, driven through their real entry points, and asserted on
an observable effect (the returned Plan / the emitted `updatedInput`).
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from des.application.commit_attribution_service import (
    CommitAttributionService,
    CommitRewritePlan,
)

from .domain_types import (
    DUAL_TRAILER_BLOCK,
    NWAVE_COAUTHOR,
    BashCommand,
    Decision,
    HookOutcome,
)


# ---------------------------------------------------------------------------
# Surface 1 — pure rewrite core (Layer 3 composition, @in-memory)
# ---------------------------------------------------------------------------


@dataclass
class RewriteResult:
    """Observable outcome of one `plan_rewrite` invocation.

    `plan` is the returned `CommitRewritePlan`. `decision` projects its `action`
    onto the user-observable `Decision`; `rewritten_command` is the rewritten
    Bash command on mutate (None on passthrough).
    """

    plan: CommitRewritePlan

    @property
    def decision(self) -> Decision:
        """The user-observable decision: MUTATE iff the Plan mutates."""
        return Decision.MUTATE if self.plan.action == "mutate" else Decision.PASSTHROUGH

    @property
    def rewritten_command(self) -> str | None:
        """The rewritten command on mutate; None on passthrough."""
        return self.plan.rewritten_command


@dataclass
class RewriteComposition:
    """Production-wired composition root over `CommitAttributionService`.

    The service is the real production object (Pillar 3); the rewrite has no
    driven ports, so nothing is faked. Each scenario plans a rewrite for one
    command and asserts on the returned Plan.
    """

    service: CommitAttributionService

    @classmethod
    def build(cls) -> RewriteComposition:
        """Build the composition with the production service."""
        return cls(service=CommitAttributionService())

    def plan_rewrite(self, command: BashCommand) -> RewriteResult:
        """Drive the return-only port and capture the Plan (the observable)."""
        return RewriteResult(plan=self.service.plan_rewrite(str(command)))

    @staticmethod
    def trailer_count(rewritten_command: str) -> int:
        """Count the nWave co-author trailers in a rewritten command.

        The dual-trailer-lands + idempotency contracts assert exactly ONE nWave
        sentinel is present after a mutate — never zero (trailer dropped) and
        never two (doubled). Counting the sentinel is the observable proxy for
        "the message parses as one Claude + one nWave trailer".
        """
        return rewritten_command.count(NWAVE_COAUTHOR)

    @staticmethod
    def original_is_byte_prefix(original: str, rewritten: str) -> bool:
        """Semantic invariant layer 2, part (1) — byte-prefix preservation.

        The original command string is a byte-prefix of the rewritten command up
        to the appended ` -m <trailer>` argument: nothing in the original — the
        heredoc body included — was mangled. The append is a pure suffix on the
        whole command (standalone) or on the delimited commit segment, with the
        chain re-joined; either way the original text survives verbatim before the
        injected `-m`. (ADR-CA-008 DDD-4 / §8 Layer 2.)
        """
        appended = " -m " + shlex.quote(DUAL_TRAILER_BLOCK)
        return rewritten == original + appended

    @staticmethod
    def last_argv_token(rewritten: str) -> str | None:
        """Semantic invariant layer 2, part (2) — trailing-token identity input.

        Returns the LAST token of ``shlex.split(rewritten)``. The placement
        invariant asserts this equals ``DUAL_TRAILER_BLOCK`` verbatim — proving the
        trailer landed as a real top-level ``-m`` argument on the commit, not
        absorbed into the heredoc body or a mis-delimited later segment. ``None``
        when the rewritten command is not shlex-parseable (which would itself be a
        corruption signal). (ADR-CA-008 §8 Layer 2 / Mitigation.)
        """
        try:
            tokens = shlex.split(rewritten)
        except ValueError:
            return None
        return tokens[-1] if tokens else None

    @staticmethod
    def is_syntactically_valid(command: str) -> bool:
        """Two-layer probe layer 1 — ``bash -n`` syntax check (ADR-CA-008 §8/Probe).

        ``bash -n`` parses without executing: a True verdict means the rewritten
        command is syntactically well-formed bash. It is NECESSARY but NOT
        SUFFICIENT (layer 1 only) — a body-`)` mis-split can be syntactically valid
        yet semantically wrong; layer 2 (byte-prefix + trailing-token) catches that
        class. ``bash`` is a test-only dependency, never shipped.
        """
        bash = shutil.which("bash")
        if bash is None:  # pragma: no cover - CI always has bash
            raise RuntimeError("bash not found — required for the two-layer probe")
        completed = subprocess.run(
            [bash, "-n", "-c", command],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return completed.returncode == 0


# ---------------------------------------------------------------------------
# Surface 2 — real PreToolUse hook adapter (Layer 4 wiring_e2e, @real-io)
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[5]
_SRC_PATH = str(_PROJECT_ROOT / "src")


@dataclass
class HookResult:
    """Observable outcome of one real `pre-tool-use` subprocess invocation.

    `exit_code` and `stdout` are the protocol surface Claude Code consumes.
    `outcome` projects them onto the user-observable `HookOutcome`:
    REWRITES_COMMAND iff stdout carries an `updatedInput`, else RUNS_UNCHANGED.
    """

    exit_code: int
    stdout: str

    @property
    def outcome(self) -> HookOutcome:
        """The agent-observable outcome: did the hook rewrite the command?"""
        if not self.stdout.strip():
            return HookOutcome.RUNS_UNCHANGED
        payload = json.loads(self.stdout)
        updated = (
            payload.get("hookSpecificOutput", {}).get("updatedInput")
            if isinstance(payload, dict)
            else None
        )
        return (
            HookOutcome.REWRITES_COMMAND
            if updated is not None
            else HookOutcome.RUNS_UNCHANGED
        )

    @property
    def rewritten_command(self) -> str | None:
        """The rewritten command from `updatedInput`, or None if unchanged."""
        if self.outcome is HookOutcome.RUNS_UNCHANGED:
            return None
        payload = json.loads(self.stdout)
        return payload["hookSpecificOutput"]["updatedInput"]["command"]

    @property
    def permission_decision(self) -> str | None:
        """The `permissionDecision` echoed on a mutation (must be "allow")."""
        if not self.stdout.strip():
            return None
        payload = json.loads(self.stdout)
        return payload.get("hookSpecificOutput", {}).get("permissionDecision")

    @property
    def echoed_tool_input_keys(self) -> set[str]:
        """The keys of the echoed `updatedInput` (full-object replacement)."""
        if self.outcome is HookOutcome.RUNS_UNCHANGED:
            return set()
        payload = json.loads(self.stdout)
        return set(payload["hookSpecificOutput"]["updatedInput"].keys())


@dataclass
class HookAdapterComposition:
    """Drives the real `pre-tool-use` hook adapter through subprocess.

    Mirrors how Claude Code dispatches the hook: a JSON PreToolUse payload on
    stdin, `python -m …claude_code_hook_adapter pre-tool-use`. The mutation
    branch (`emit_commit_attribution_mutation`) is reached from the real
    `handle_pre_tool_use` entry point — the Mandate-15 witnessing path.
    """

    extra_tool_input: dict[str, object]

    @classmethod
    def build(cls) -> HookAdapterComposition:
        """Build with a representative multi-field `tool_input`.

        The extra fields (`description`) prove the full-object `updatedInput`
        replacement echoes every original field, not just `command`.
        """
        return cls(extra_tool_input={"description": "commit the work"})

    def invoke_pre_tool_use(self, command: BashCommand) -> HookResult:
        """Feed a Bash PreToolUse payload through the real hook subprocess."""
        tool_input = {"command": str(command), **self.extra_tool_input}
        payload = json.dumps({"tool_name": "Bash", "tool_input": tool_input})
        env = os.environ.copy()
        env["PYTHONPATH"] = _SRC_PATH + os.pathsep + env.get("PYTHONPATH", "")
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "des.adapters.drivers.hooks.claude_code_hook_adapter",
                "pre-tool-use",
            ],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        return HookResult(exit_code=completed.returncode, stdout=completed.stdout)
