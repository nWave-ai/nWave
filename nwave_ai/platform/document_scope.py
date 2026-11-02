"""Explicit document ownership; scope cannot be inferred from a missing id."""

from dataclasses import dataclass
from typing import TypeAlias

from nwave_ai.platform.feature_documents import require_feature_id


@dataclass(frozen=True)
class Project:
    pass


@dataclass(frozen=True)
class Epic:
    epic_id: str

    def __post_init__(self):
        require_feature_id(self.epic_id)


@dataclass(frozen=True)
class Feature:
    feature_id: str

    def __post_init__(self):
        require_feature_id(self.feature_id)


@dataclass(frozen=True)
class Slice:
    feature_id: str
    slice_id: str

    def __post_init__(self):
        require_feature_id(self.feature_id)
        require_feature_id(self.slice_id)


DocumentScope: TypeAlias = Project | Epic | Feature | Slice
