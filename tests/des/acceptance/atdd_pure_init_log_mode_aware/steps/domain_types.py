"""Domain types for the des-init-log mode-aware acceptance slice (Mandate-12 criterion 1).

Every domain noun used in the Gherkin is expressed once here as a typed enum
or NewType. Step bodies and the composition service consume these typed
parameters -- no raw `str` where a domain enum exists.
"""

from __future__ import annotations

from enum import Enum
from typing import NewType


class WorkflowMode(str, Enum):
    """The project workflow mode resolved from .nwave/config.yaml:workflow.mode.

    ATDD_PURE  -- roadmap-free, execution-log-free spine (ADR-028).
    CLASSIC    -- roadmap-based DELIVER; execution-log created normally.
    UNSET      -- no `workflow.mode` key (or no config file). Treated as CLASSIC
                  by des-init-log: the default, no-regression path.
    """

    ATDD_PURE = "atdd_pure"
    CLASSIC = "classic"
    UNSET = "unset"


# A kebab-case feature identifier (e.g. "atdd-pure-demo").
FeatureId = NewType("FeatureId", str)
