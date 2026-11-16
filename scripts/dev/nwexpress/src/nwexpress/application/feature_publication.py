"""The publish decision: the folder and the four texts are decided here, before anything is written.

Every refusal a publish can raise comes from resolving the folder or from rendering the texts, and both run in
plan(); the publisher is called only with a complete plan, so a refused publish leaves the repository as it was.
"""

from __future__ import annotations

from dataclasses import dataclass

from nwexpress.application.briefer import Briefer
from nwexpress.application.feature_documents import feature_document_texts
from nwexpress.domain.feature_directory import resolve
from nwexpress.domain.feature_id import FeatureId
from nwexpress.domain.journal import Journal


@dataclass(frozen=True)
class FeaturePlan:
    """The repository-relative folder and the (file name, text) pairs to write into it."""

    folder: str
    documents: tuple[tuple[str, str], ...]


class FeaturePublication:
    """Decides what a publish writes; it performs no effect."""

    @staticmethod
    def plan(
        feature: FeatureId,
        tiers: tuple[object, ...],
        briefer: Briefer,
        journal: Journal,
    ) -> FeaturePlan:
        destination = resolve(tiers, feature.text)
        return FeaturePlan(
            folder=destination.folder,
            documents=feature_document_texts(briefer, journal),
        )
