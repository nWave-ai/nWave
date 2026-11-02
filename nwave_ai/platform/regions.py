"""GENERATED-region projection for the installable nwave-ai surface.

The ONE engine that re-renders the marker-delimited generated regions an installed
asset carries. Marker grammar:
    <!-- GENERATED:<region-id> START ... --> body <!-- GENERATED:<region-id> END -->
Each marker names its source; assets carry projections only, never hand-edits.

Only the ``communication-rules`` region is installable: its inputs are the merged
configuration files, which are present on every consumer machine. Regions whose
inputs exist only in the developer source tree are rendered by ``scripts/docgen.py``
and never ship through this module.

Depends on the platform package alone; it imports nothing from ``des``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from nwave_ai.platform.config import effective_config


GENERATED_REGION_RE = re.compile(
    r"<!--\s*GENERATED:(?P<region_id>[a-z][a-z0-9-]*)\s+START[^>]*-->\n"
    r"(?P<body>.*?)"
    r"<!--\s*GENERATED:(?P=region_id)\s+END\s*-->",
    re.DOTALL,
)

#: A region's marker DECLARES where its body comes from; a marker naming a source
#: that did not produce the body is a false fact shipped inside generated prose,
#: so each region names its own source instead of inheriting a default.
REGION_SOURCE_OF_TRUTH: dict[str, str] = {
    "role-skill-loading": "role-skill-loading.yaml (build-time registry, not shipped)",
    "communication-rules": (
        "nwave_ai.platform.effective_config() "
        "(ADR-CFG-001 Slice 2 -- ~/.nwave/config.json + .nwave/config.json)"
    ),
}


class GeneratedRegionError(Exception):
    """Raised when a GENERATED region cannot be rendered honestly."""


@dataclass(frozen=True)
class AssetProjection:
    """One asset's re-rendered GENERATED-region state vs what is on disk."""

    path: Path
    current_text: str
    projected_text: str

    @property
    def stale(self) -> bool:
        return self.current_text != self.projected_text


#: ``(region_id, asset_path, root) -> body``.
RegionRenderer = Callable[[str, Path, Path], str]


def generated_region(region_id: str, body: str) -> str:
    """The canonical full region text (markers + body) this engine owns."""
    source = REGION_SOURCE_OF_TRUTH.get(region_id)
    if source is None:
        raise GeneratedRegionError(
            f"Unknown GENERATED region id '{region_id}' -- refusing to serve "
            "a region with no declared source"
        )
    return (
        f"<!-- GENERATED:{region_id} START — source of truth: "
        f"{source}; do not hand-edit (docgen renders this region) -->\n"
        f"{body}\n"
        f"<!-- GENERATED:{region_id} END -->"
    )


def communication_rules_body(root: Path) -> str:
    """Render the ``communication-rules`` body from the effective configuration of ``root``."""
    effective = effective_config(root)
    attribution = "enabled" if effective["attribution"] else "disabled"
    return "\n".join(
        (
            f"- Communication verbosity: **{effective['verbosity']}**",
            f"- Commit attribution: **{attribution}**",
        )
    )


#: Regions renderable from an INSTALLED layout. Adding a row is a decision to ship
#: that region's inputs too.
INSTALLABLE_RENDERERS: dict[str, Callable[[Path], str]] = {
    "communication-rules": communication_rules_body,
}


def render_installable_region_body(region_id: str, asset_path: Path, root: Path) -> str:
    """Default renderer: the installable region set only, failing LOUD otherwise."""
    renderer = INSTALLABLE_RENDERERS.get(region_id)
    if renderer is None:
        raise GeneratedRegionError(
            f"WHAT: GENERATED region '{region_id}' in {asset_path} cannot be "
            f"rendered from an installed layout.\n"
            f"WHY: only {sorted(INSTALLABLE_RENDERERS)} have every input present "
            "on a consumer machine.\n"
            "HOW: drop that marker from the shipped asset, or move the region's "
            "inputs into the installed package and register its renderer in "
            "nwave_ai.platform.regions.INSTALLABLE_RENDERERS."
        )
    return renderer(root)


def project_asset(
    path: Path,
    text: str,
    root: Path,
    render_body: RegionRenderer = render_installable_region_body,
) -> AssetProjection:
    """Re-render every GENERATED region in ``text`` for ``root``."""

    def _replace(match: re.Match[str]) -> str:
        region_id = match.group("region_id")
        return generated_region(region_id, render_body(region_id, path, root))

    return AssetProjection(
        path=path,
        current_text=text,
        projected_text=GENERATED_REGION_RE.sub(_replace, text),
    )
