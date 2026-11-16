"""The prompt templates of a checkout: the ones in use by shipped schema version, the default, and the retired ones.

Pure: the infrastructure reads templates/versions.toml into this value.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateManifest:
    default: str
    versions: Mapping[str, tuple[str, ...]]
    retired: frozenset[str]

    def in_use(self, shipped_versions: frozenset[str]) -> tuple[str, ...]:
        """The default and the templates of every shipped schema version, sorted."""
        names = {self.default}
        for version, templates in self.versions.items():
            if version in shipped_versions:
                names.update(templates)
        return tuple(sorted(names))

    def is_retired(self, name: str) -> bool:
        return name in self.retired
