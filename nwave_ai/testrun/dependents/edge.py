"""One edge of the dependency relation: ``dependent`` depends directly on ``target``."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyEdge:
    """Loading or starting ``dependent`` reaches ``target``, with no file in between."""

    target: str
    dependent: str
