"""Writes the feature documents of one run into their folder: each named file replaced whole, nothing removed.

Each file is written to a temporary name beside it and then renamed over the old one, so a file is either the old
text or the new text. A kill between two files can leave some of the four updated and others not; that window is
recorded as an unproven limit, not claimed away.
"""

from __future__ import annotations

from pathlib import Path

from nwexpress.application.feature_publication import FeaturePlan


class FeaturePublisher:
    def __init__(self, root: Path) -> None:
        self._root = root

    def publish(self, plan: FeaturePlan) -> list[str]:
        """Writes every document of the plan; returns the repository-relative paths written."""
        folder = self._root / plan.folder
        folder.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        for name, text in plan.documents:
            path = folder / name
            temporary = path.with_name(f".{name}.tmp")
            temporary.write_text(text, encoding="utf-8")
            temporary.replace(path)
            written.append(f"{plan.folder}/{name}")
        return written
