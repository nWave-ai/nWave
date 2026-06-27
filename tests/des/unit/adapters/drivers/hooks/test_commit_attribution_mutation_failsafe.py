"""D1 — the attribution mutation branch is fail-safe at the adapter.

Contract (ADR-CA-006): "any error → original command runs unchanged." An
exception in the rewrite plan / JSON serialization must NEVER propagate to the
outer ``handle_pre_tool_use`` ``except Exception`` (which fail-closes to
``exit_code=1`` and BLOCKS the commit). Attribution is best-effort: a missed
trailer is recoverable; a blocked commit is not.

``emit_commit_attribution_mutation`` is the driving seam: feed it a ``tool_input``
whose service raises, and assert it returns ``None`` (passthrough — falls through
to the existing validation path), never raising.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from des.adapters.drivers.hooks import pre_tool_use_handler


if TYPE_CHECKING:
    import pytest


class _RaisingService:
    """A service whose ``plan_rewrite`` always raises (simulated failure)."""

    def plan_rewrite(self, command: str) -> object:
        raise RuntimeError("boom: rewrite core blew up")


def test_d1_service_exception_returns_passthrough_not_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A raising service yields ``None`` (passthrough), never an exception."""
    monkeypatch.setattr(
        pre_tool_use_handler, "_commit_attribution_service", _RaisingService()
    )
    result = pre_tool_use_handler.emit_commit_attribution_mutation(
        {"command": 'git commit -m "x"', "description": "commit the work"}
    )
    assert result is None


def test_d1_service_exception_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The mutation branch swallows the failure (no propagation to the caller)."""
    monkeypatch.setattr(
        pre_tool_use_handler, "_commit_attribution_service", _RaisingService()
    )
    # The bare call must not raise; if it did, the outer handler would block.
    pre_tool_use_handler.emit_commit_attribution_mutation(
        {"command": 'git commit -m "x"'}
    )


def test_d1_non_string_command_still_passes_through() -> None:
    """A non-string command is a no-op passthrough (existing guard preserved)."""
    result = pre_tool_use_handler.emit_commit_attribution_mutation({"command": None})
    assert result is None
