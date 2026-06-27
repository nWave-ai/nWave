"""Application service orchestrating the commit-attribution rewrite.

The DISTILL test entry seam (Reuse row R3, ADR-CA-006 D3). A thin orchestrator:
it takes the Bash command, delegates to the pure domain rewriter, and returns the
:class:`CommitRewritePlan`. It has NO protocol/JSON knowledge — that lives in the
adapter — and NO effects (Principle 12 — pure-function over the injected core).

Imports the domain rewriter only (intra-`des`), keeping attribution decoupled
from the TDD-enforcement validation path.
"""

from __future__ import annotations

from des.domain.commit_attribution.trailer_rewriter import (
    CommitRewritePlan,
    rewrite,
)


# Re-exported so acceptance tests reference the driving port's public return
# type through the application (driving-port) layer, never by importing the
# domain module directly (S2 — driving-port-only boundary).
__all__ = ["CommitAttributionService", "CommitRewritePlan"]


class CommitAttributionService:
    """Driving-port seam for the commit-attribution rewrite.

    Acceptance tests instantiate this service and call :meth:`plan_rewrite`,
    asserting on the returned :class:`CommitRewritePlan` with zero I/O. The
    adapter (`pre_tool_use_handler`) calls the same method, then translates the
    Plan into the hook protocol JSON.
    """

    def plan_rewrite(self, command: str) -> CommitRewritePlan:
        """Return the :class:`CommitRewritePlan` for a Bash ``command``.

        Delegates to the pure domain rewriter; performs no I/O and emits no
        protocol output.

        Args:
            command: the raw Bash command string from ``tool_input.command``.

        Returns:
            The :class:`CommitRewritePlan` produced by the domain rewriter.
        """
        return rewrite(command)
