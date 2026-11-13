"""Where the nwstep checkout keeps its source and templates, found from this module and never from the working directory."""

from __future__ import annotations

import re
from pathlib import Path


class PackagePaths:
    _THIS_FILE = Path(__file__).resolve()
    SOURCE = _THIS_FILE.parents[2]
    CHECKOUT = _THIS_FILE.parents[3]
    REPOSITORY = _THIS_FILE.parents[6]
    TEMPLATES = CHECKOUT / "templates"
    SCHEMAS = CHECKOUT / "schemas"
    MANIFEST = TEMPLATES / "versions.toml"

    @classmethod
    def jev_skill(cls) -> Path:
        """The Jev skill of the nWave checkout that ships this nwstep, found from this module."""
        return cls.CHECKOUT.parents[2] / "nWave" / "skills" / "nw-typesafe-system-one"

    @classmethod
    def shipped_schemas(cls) -> list[str]:
        return sorted(item.name for item in cls.SCHEMAS.glob("*.toml"))

    @classmethod
    def shipped_schema_versions(cls) -> frozenset[str]:
        """The vN of each shipped dynamic-vN.toml: the schema versions whose templates are in use."""
        return frozenset(
            match.group(1)
            for name in cls.shipped_schemas()
            if (match := re.fullmatch(r"dynamic-(v\d+)\.toml", name))
        )
