"""Owned update and advisory-hook deadlines, including bounded child cleanup.

The hook allowance covers admission followed by a startup check/update; it is
not a claim that a native host honors that allowance or blocks session work.
Controlled host launchers own admission before starting the host process.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass


UPDATE_STAGES = (
    "replace-package",
    "verify-executable",
    "preflight-framework",
    "synchronize-framework",
    "migrate-artifacts",
)


@dataclass(frozen=True)
class UpdateTiming:
    """Finite budgets with outer deadlines derived from all inner work."""

    stage_seconds: float = 25.0
    pipe_drain_seconds: float = 2.0
    reap_seconds: float = 1.0
    command_overhead_seconds: float = 25.0
    margin_seconds: float = 5.0
    repository_probe_seconds: float = 5.0
    notice_overhead_seconds: float = 10.0

    def __post_init__(self) -> None:
        for value in (
            self.stage_seconds,
            self.pipe_drain_seconds,
            self.reap_seconds,
            self.command_overhead_seconds,
            self.margin_seconds,
            self.repository_probe_seconds,
            self.notice_overhead_seconds,
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("update timing budgets must be finite and positive")
        # Guard arithmetic overflow as well as invalid primitive budgets.
        if not math.isfinite(self.session_start_seconds):
            raise ValueError("derived session-start deadline must be finite")

    @property
    def stage_cleanup_seconds(self) -> float:
        return self.pipe_drain_seconds + self.reap_seconds

    @property
    def update_seconds(self) -> float:
        return (
            len(UPDATE_STAGES) * (self.stage_seconds + self.stage_cleanup_seconds)
            + self.command_overhead_seconds
        )

    @property
    def admission_seconds(self) -> float:
        return self.update_seconds + self.margin_seconds

    @property
    def session_start_seconds(self) -> float:
        return self.admission_seconds + self.notice_overhead_seconds

    @property
    def session_end_seconds(self) -> float:
        return 2 * self.margin_seconds


UPDATE_TIMING = UpdateTiming()

STAGE_SECONDS_VARIABLE = "NWAVE_UPDATE_STAGE_SECONDS"


def resolve_stage_seconds(environment: Mapping[str, str]) -> float:
    """Return the stage wait for one launch, refusing unusable overrides by name.

    Unset or empty selects ``UPDATE_TIMING.stage_seconds``. A supplied value must
    parse as a finite number in ``(0, UPDATE_TIMING.stage_seconds]``.
    """
    supplied = environment.get(STAGE_SECONDS_VARIABLE, "")
    if supplied == "":
        return UPDATE_TIMING.stage_seconds
    try:
        value = float(supplied)
    except ValueError:
        value = math.nan
    if not (math.isfinite(value) and 0 < value <= UPDATE_TIMING.stage_seconds):
        raise ValueError(
            f'{STAGE_SECONDS_VARIABLE}="{supplied}" is refused; the accepted '
            f"stage deadline range is (0, {UPDATE_TIMING.stage_seconds}] seconds"
        )
    return value
