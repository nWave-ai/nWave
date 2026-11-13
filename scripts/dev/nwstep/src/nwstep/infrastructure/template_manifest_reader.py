"""Reads templates/versions.toml into the template manifest."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from nwstep.domain.template_manifest import TemplateManifest


if TYPE_CHECKING:
    from pathlib import Path


def read_template_manifest(path: Path) -> TemplateManifest:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return TemplateManifest(
        default=data["default"],
        versions={
            version: tuple(templates) for version, templates in data["versions"].items()
        },
        retired=frozenset(data["retired"]["templates"]),
    )
