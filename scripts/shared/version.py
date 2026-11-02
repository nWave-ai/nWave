"""Shared version reader -- single source of truth.

Reads the project version from ``pyproject.toml`` (the canonical
source). Falls back through ``tomllib`` -> ``tomli`` -> regex.

All consumers should import from this module::

    from scripts.shared.version import get_version

``resolve_product_version`` (P2-V1) is the strict, exactly-one-owner
producer: it never falls back to ``"0.0.0"``, instead raising
``VersionResolutionError`` (WHAT/WHY/HOW) on any ambiguous, missing, or
malformed product identity. ``get_version`` above is preserved unchanged
for legacy callers only until P2-V2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import metadata as _importlib_metadata
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


_TOP_LEVEL_MODULE = "nwave_ai"


class VersionResolutionError(Exception):
    """Typed refusal for ambiguous, missing, or malformed product identity.

    Carries WHAT/WHY/HOW so every consumer (CLI, tests) presents the same
    triad without re-deriving it. A caller that already owns one composed
    WHAT/WHY/HOW message (for example a test double standing in for a real
    producer failure) may pass it as the sole positional argument instead of
    the three separate fields; the triad markers are still required in that
    message, so no construction path can weaken the WHAT/WHY/HOW contract.
    """

    def __init__(
        self, what: str, why: str | None = None, how: str | None = None
    ) -> None:
        if why is None and how is None:
            message = what
            if not all(marker in message for marker in ("WHAT:", "WHY:", "HOW:")):
                raise TypeError(
                    "VersionResolutionError single-argument form requires a "
                    "pre-formatted message containing WHAT:, WHY:, and HOW:"
                )
            self.what = what
            self.why = why
            self.how = how
            super().__init__(message)
            return
        self.what = what
        self.why = why
        self.how = how
        super().__init__(f"WHAT: {what} WHY: {why} HOW: {how}")


@dataclass(frozen=True, init=False)
class ProductVersion:
    """A strict version value constructible only through :meth:`from_text`."""

    version: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError("use ProductVersion.from_text(version)")

    @classmethod
    def from_text(cls, version: str) -> ProductVersion:
        if not isinstance(version, str) or not version.strip():
            raise VersionResolutionError(
                what="the selected product version is not a non-empty string",
                why=f"version metadata was {version!r}",
                how="provide a non-empty string version in product metadata",
            )
        if version == "0.0.0":
            raise VersionResolutionError(
                what="the selected product version is the compatibility sentinel",
                why="0.0.0 represents unresolved legacy identity, not a product version",
                how="provide the real product version in source or installed metadata",
            )
        instance = object.__new__(cls)
        object.__setattr__(instance, "version", version)
        return instance


def _owning_distributions(
    module_name: str,
) -> list[_importlib_metadata.Distribution]:
    """Distinct installed distributions that own *module_name*.

    ``packages_distributions`` includes both declared and inferred package
    ownership, so it also recognizes wheels that omit optional
    ``top_level.txt``. Resolve each selected name against the discovered
    distribution objects so version metadata comes from that owner rather
    than a hard-coded product.
    """
    owner_names = sorted(
        set(_importlib_metadata.packages_distributions().get(module_name, ()))
    )
    distributions_by_name: dict[str, _importlib_metadata.Distribution] = {}
    for dist in _importlib_metadata.distributions():
        try:
            name = dist.metadata.get("Name")
        except (KeyError, TypeError):
            continue
        if isinstance(name, str) and name:
            distributions_by_name[name] = dist
    try:
        return [distributions_by_name[name] for name in owner_names]
    except KeyError as exc:
        raise VersionResolutionError(
            what="an installed package owner cannot be resolved to its metadata",
            why=f"the ownership map names {exc.args[0]!r}, but its Name metadata is absent",
            how="reinstall the owning distribution with valid Name and Version metadata",
        ) from exc


def _read_source_version(pyproject_path: Path) -> ProductVersion:
    """Read and validate one complete ``[project]`` identity.

    Tries ``tomllib`` (3.11+), then ``tomli``, then falls back to a regex
    scan (matching ``get_version``'s own fallback shape). Any parse fault
    raises ``VersionResolutionError`` -- a malformed source pyproject must
    never be silently treated as "no version".
    """
    try:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore[no-redef]

        with open(pyproject_path, "rb") as handle:
            data = tomllib.load(handle)
    except ModuleNotFoundError:
        try:
            content = pyproject_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise VersionResolutionError(
                what="the adjacent source pyproject.toml could not be read",
                why=str(exc),
                how=f"make {pyproject_path} readable",
            ) from exc
        project_match = re.search(
            r"^\[project\]\s*$([\s\S]*?)(?=^\[|\Z)", content, re.MULTILINE
        )
        project_text = project_match.group(1) if project_match else ""
        name_match = re.search(r'^name\s*=\s*"([^"]*)"\s*$', project_text, re.MULTILINE)
        version_match = re.search(
            r'^version\s*=\s*"([^"]*)"\s*$', project_text, re.MULTILINE
        )
        name = name_match.group(1) if name_match else None
        version = version_match.group(1) if version_match else None
    except Exception as exc:
        raise VersionResolutionError(
            what="the adjacent source pyproject.toml could not be parsed",
            why=str(exc),
            how=f"repair the [project] table in {pyproject_path}",
        ) from exc
    else:
        project = data.get("project")
        name = project.get("name") if isinstance(project, dict) else None
        version = project.get("version") if isinstance(project, dict) else None

    if not isinstance(name, str) or not name.strip():
        raise VersionResolutionError(
            what="the adjacent source pyproject.toml has no usable project name",
            why=f"[project].name is missing, empty, or non-string in {pyproject_path}",
            how="set a non-empty string [project].name in pyproject.toml",
        )
    return ProductVersion.from_text(version)


def resolve_product_version(project_root: Path) -> ProductVersion:
    """Resolve the single owning product identity for *project_root*.

    Precedence: an installed distribution that declares ownership of
    ``nwave_ai`` wins over the adjacent source ``pyproject.toml``. Multiple
    owners, a selected owner missing version metadata, no owner plus no
    adjacent pyproject, and a malformed/empty source version all raise
    ``VersionResolutionError`` -- this producer never emits ``"0.0.0"``.
    """
    owning = _owning_distributions(_TOP_LEVEL_MODULE)
    if len(owning) > 1:
        names = [dist.metadata["Name"] for dist in owning]
        raise VersionResolutionError(
            what=(
                "multiple installed distributions claim ownership of "
                f"{_TOP_LEVEL_MODULE!r}"
            ),
            why=f"owners: {', '.join(names)}",
            how=(
                "uninstall the extra distribution(s) so exactly one owns "
                f"{_TOP_LEVEL_MODULE!r}"
            ),
        )

    if len(owning) == 1:
        dist = owning[0]
        try:
            owner = dist.metadata["Name"]
            version = dist.version
        except (KeyError, TypeError) as exc:
            raise VersionResolutionError(
                what="the selected installed owner has incomplete metadata",
                why="its Name or Version metadata is absent",
                how="reinstall the owning distribution with valid Name and Version metadata",
            ) from exc
        if not isinstance(owner, str) or not owner.strip():
            raise VersionResolutionError(
                what="the selected installed owner has no usable name metadata",
                why=f"the selected owner's Name field was {owner!r}",
                how="reinstall the owning distribution with valid Name metadata",
            )
        return ProductVersion.from_text(version)

    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        raise VersionResolutionError(
            what="no installed owner and no adjacent pyproject.toml",
            why=(
                f"{_TOP_LEVEL_MODULE!r} is not installed and {pyproject_path} "
                "does not exist"
            ),
            how="install the distribution or run from a checkout with pyproject.toml",
        )

    return _read_source_version(pyproject_path)


def get_version(project_root: Path) -> str:
    """Read version from ``pyproject.toml`` in *project_root*.

    Tries ``tomllib`` (Python 3.11+), then ``tomli``, then regex.
    Raises ``VersionResolutionError`` (WHAT/WHY/HOW) for a missing or
    unparseable source identity -- this legacy compatibility port never
    substitutes the ``"0.0.0"`` sentinel.
    """
    pyproject_path = project_root / "pyproject.toml"
    return _read_source_version(pyproject_path).version
