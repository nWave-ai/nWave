"""Reads and writes the baseline record of a workspace as JSON."""

from __future__ import annotations

import json

from nwstep.domain.baseline import Baseline
from nwstep.infrastructure.workspace import Workspace


class BaselineStore:
    def __init__(self, workspace: Workspace) -> None:
        self._path = workspace.baseline_path

    def write(self, baseline: Baseline) -> None:
        self._path.write_text(
            json.dumps(baseline.to_value(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def read(self) -> Baseline:
        if not self._path.is_file():
            return Baseline.unavailable(
                "the workspace has no baseline record; it was initialized before baselines existed"
            )
        return Baseline.from_value(json.loads(self._path.read_text(encoding="utf-8")))
