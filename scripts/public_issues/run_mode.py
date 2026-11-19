"""Whether a pass may write. Dry by default: only the exact text true, and no forced dry run, is live."""

from __future__ import annotations

from dataclasses import dataclass


LIVE_VALUE = "true"
FORCED_DRY_VALUE = "true"


@dataclass(frozen=True)
class RunMode:
    live: bool
    reason: str

    @classmethod
    def from_settings(
        cls, live_variable: str | None, dry_run_input: str | None
    ) -> RunMode:
        if live_variable != LIVE_VALUE:
            return cls(
                live=False,
                reason=(
                    "dry run: ISSUE_CLOSE_LIVE is not exactly 'true' "
                    "(a missing variable counts as dry)"
                ),
            )
        if dry_run_input == FORCED_DRY_VALUE:
            return cls(
                live=False, reason="dry run: the dispatch input dry_run forced it"
            )
        return cls(
            live=True,
            reason="live: ISSUE_CLOSE_LIVE is 'true' and no dry run was forced",
        )
