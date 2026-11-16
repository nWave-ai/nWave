"""Keeps the feature a workspace declares: its id and the repository root its folder lies in, in feature.json.

It sits beside size.json as the other declared fact of a workspace, written once by the feature command. The id is
read back through FeatureId.of, so a hand-edited file meets the same rule as a declaration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from nwexpress.domain.feature_id import FeatureId
from nwexpress.domain.refusal import Refusal
from nwexpress.infrastructure.atomic_json import write_json
from nwexpress.infrastructure.workspace import Workspace


@dataclass(frozen=True)
class DeclaredFeature:
    feature: FeatureId
    root: Path


class FeatureStore:
    def __init__(self, workspace: Workspace) -> None:
        self._path = workspace.feature_path

    def current(self) -> DeclaredFeature | None:
        """The declared feature and its root, or None when the workspace declares none."""
        if not self._path.is_file():
            return None
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
            feature = document["feature"]
            root = document["root"]
            if not isinstance(root, str):
                raise TypeError("the root is not a text")
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise Refusal(
                what=f"{self._path} does not declare a feature",
                why=f"the declared feature fact cannot be read: {error}",
                how=f"Remove {self._path} and declare the feature again with nwexpress feature --workspace <workspace directory> --id <feature-id>.",
            ) from None
        return DeclaredFeature(FeatureId.of(feature), Path(root))

    def declare(self, declared: DeclaredFeature) -> None:
        write_json(
            self._path,
            {"feature": declared.feature.text, "root": str(declared.root)},
        )
