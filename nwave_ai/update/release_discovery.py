"""Discover the latest stable public ``nwave-ai`` release from PyPI."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from packaging.version import InvalidVersion, Version


_PYPI_PROJECT_URL = "https://pypi.org/pypi/nwave-ai/json"
_TIMEOUT_SECONDS = 5.0


class ReleaseDiscoveryRefusal(Exception):
    """A typed WHAT/WHY/HOW refusal to invent a public release."""

    def __init__(self, why: str) -> None:
        super().__init__(
            "WHAT: the latest stable public nwave-ai release could not be discovered. "
            f"WHY: {why}. "
            "HOW: verify network access to PyPI and retry."
        )


def _has_non_yanked_file(files: object) -> bool:
    """Whether PyPI release-file metadata establishes one public file."""
    if not isinstance(files, list):
        return False
    return any(
        isinstance(file_metadata, dict) and file_metadata.get("yanked", False) is False
        for file_metadata in files
    )


def _eligible_versions(releases: dict[str, Any]) -> list[Version]:
    """Return parseable stable, non-local versions backed by a public file."""
    eligible: list[Version] = []
    for raw_version, files in releases.items():
        try:
            version = Version(raw_version)
        except (InvalidVersion, TypeError):
            continue
        if (
            version.local is not None
            or version.is_prerelease
            or version.is_devrelease
            or not _has_non_yanked_file(files)
        ):
            continue
        eligible.append(version)
    return eligible


def discover_latest_stable_release() -> Version:
    """Return PyPI's greatest eligible public release, or refuse explicitly."""
    try:
        with urllib.request.urlopen(
            _PYPI_PROJECT_URL, timeout=_TIMEOUT_SECONDS
        ) as response:
            document = json.loads(response.read().decode("utf-8"))
    except (
        OSError,
        TypeError,
        AttributeError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ReleaseDiscoveryRefusal(str(exc)) from exc

    if not isinstance(document, dict):
        raise ReleaseDiscoveryRefusal("PyPI returned metadata that is not an object")
    releases = document.get("releases")
    if not isinstance(releases, dict):
        raise ReleaseDiscoveryRefusal("PyPI release metadata is missing or malformed")

    eligible = _eligible_versions(releases)
    if not eligible:
        raise ReleaseDiscoveryRefusal(
            "PyPI metadata contains no eligible stable public release"
        )
    return max(eligible)
