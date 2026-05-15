"""PBT helpers for state_delta matcher (Slice 2). Hypothesis lazy-imported.

A9 contract (ADR-002): importing this subpackage does NOT load hypothesis.
Hypothesis is loaded only when path_strategy() is called.
"""

from nwave_ai.state_delta.strategies.path_strategy import path_strategy
from nwave_ai.state_delta.strategies.simulators import (
    update_path_in_settings_faithful,
)


__all__ = ["path_strategy", "update_path_in_settings_faithful"]
