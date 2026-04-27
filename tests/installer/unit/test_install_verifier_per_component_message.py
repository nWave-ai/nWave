"""Tests for install_nwave verifier — per-component sync mismatch message.

v3.12.1 install regression — Bug #3 of 4. install_nwave._verify_deployment
emitted the literal string "agent/command sync mismatch" regardless of which
of the four components (agents / commands / templates / scripts) actually
failed verification. Result: when scripts mismatched (Bug #2 cascade), the
user saw an apparent contradiction:

    ✓ Commands verified (6/6)
    ✗ Validation failed (1 issues: agent/command sync mismatch)

The message named agents/commands but agents and commands were green; only
scripts were red. Diagnostic value: zero. Worse: misleading.

Correct semantics: the failure message must enumerate ONLY the components
that failed, with their matched/expected counts. A pure helper
`_format_sync_mismatch(components) -> str` produces the message from a
list of (name, matched, expected, ok) tuples. The helper is the driving
port for the formatter; calling it directly is port-to-port at domain
scope. Tests assert the message is specific, not the misleading legacy
literal.
"""

from scripts.install.install_nwave import (
    ComponentResult,
    _format_sync_mismatch,
)


class TestFormatSyncMismatchMessage:
    """The failure-aggregator must name exactly the failing components.

    Contract: given a list of ComponentResult, the formatter emits a string
    that mentions every component with ok=False (and only those), each
    annotated with its matched/expected counts.
    """

    def test_only_scripts_fail_message_names_scripts(self) -> None:
        """When only scripts mismatch, the message must say 'scripts' and
        carry the count breakdown '0/2'. This is the v3.12.1 user-facing
        bug: scripts failed, message blamed agents/commands.
        """
        components = [
            ComponentResult("agents", matched=23, expected=23, ok=True),
            ComponentResult("commands", matched=6, expected=6, ok=True),
            ComponentResult("templates", matched=8, expected=8, ok=True),
            ComponentResult("scripts", matched=0, expected=2, ok=False),
        ]

        message = _format_sync_mismatch(components)

        assert "scripts" in message
        assert "0/2" in message

    def test_only_agents_fail_message_names_agents(self) -> None:
        """Symmetric to the scripts case: when only agents mismatch, the
        message names 'agents' with its counts. Locks the formatter into
        per-component specificity rather than a static literal.
        """
        components = [
            ComponentResult("agents", matched=20, expected=23, ok=False),
            ComponentResult("commands", matched=6, expected=6, ok=True),
            ComponentResult("templates", matched=8, expected=8, ok=True),
            ComponentResult("scripts", matched=2, expected=2, ok=True),
        ]

        message = _format_sync_mismatch(components)

        assert "agents" in message
        assert "20/23" in message

    def test_multiple_components_fail_lists_all(self) -> None:
        """When two components fail, both must appear in the message.
        Order-tolerant: the formatter may list them in any order, but
        every failing component name must be present.
        """
        components = [
            ComponentResult("agents", matched=23, expected=23, ok=True),
            ComponentResult("commands", matched=6, expected=6, ok=True),
            ComponentResult("templates", matched=5, expected=8, ok=False),
            ComponentResult("scripts", matched=0, expected=2, ok=False),
        ]

        message = _format_sync_mismatch(components)

        assert "templates" in message
        assert "5/8" in message
        assert "scripts" in message
        assert "0/2" in message

    def test_no_misleading_agent_command_literal_when_only_scripts_fail(
        self,
    ) -> None:
        """The legacy literal 'agent/command sync mismatch' must never
        appear when only scripts failed. This is the regression guard
        against the v3.12.1 user-facing bug returning.
        """
        components = [
            ComponentResult("agents", matched=23, expected=23, ok=True),
            ComponentResult("commands", matched=6, expected=6, ok=True),
            ComponentResult("templates", matched=8, expected=8, ok=True),
            ComponentResult("scripts", matched=0, expected=2, ok=False),
        ]

        message = _format_sync_mismatch(components)

        assert "agent/command sync mismatch" not in message

    def test_passing_components_omitted_from_message(self) -> None:
        """Property: components with ok=True must NOT appear in the
        failure message. Only the failures are user-relevant; mentioning
        successes would re-introduce the original confusion.
        """
        components = [
            ComponentResult("agents", matched=23, expected=23, ok=True),
            ComponentResult("commands", matched=6, expected=6, ok=True),
            ComponentResult("templates", matched=8, expected=8, ok=True),
            ComponentResult("scripts", matched=0, expected=2, ok=False),
        ]

        message = _format_sync_mismatch(components)

        # The three passing components must not be named in the failure
        # message (they were green; mentioning them is misleading).
        assert "agents" not in message
        assert "commands" not in message
        assert "templates" not in message
