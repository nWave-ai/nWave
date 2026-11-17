"""The default update notice: one line read from a local cache, never from the network.

The cache ``<nWave home>/.nwave/latest-release.json`` holds the newest public release the user's own
``nwave-ai update`` command saw: ``{"version": "4.7.1", "checked": "2026-11-16"}``, a version string and a date and
nothing else. Only that command writes it (``record_latest_release``). Reading it here opens no socket and starts
no process. A user who never runs ``nwave-ai update`` never gets a notice: that is what this design cannot do.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from packaging.version import InvalidVersion, Version


CACHE_NAME = "latest-release.json"
#: A cache older than this says nothing: an old answer would be a wrong one.
STALE_AFTER_DAYS = 30


@dataclass(frozen=True)
class Missing:
    """No release was ever recorded here."""


@dataclass(frozen=True)
class Stale:
    """The record is older than STALE_AFTER_DAYS."""

    checked: date


@dataclass(frozen=True)
class Fresh:
    """The newest public release known, and the day it was seen."""

    version: Version
    checked: date


@dataclass(frozen=True)
class Corrupt:
    """The file exists and is not a record of this module."""

    reason: str


CacheState = Missing | Stale | Fresh | Corrupt


def cache_path(nwave_home: Path) -> Path:
    return nwave_home / CACHE_NAME


def record_latest_release(nwave_home: Path, version: Version, today: date) -> None:
    """Write the cache: called only by a command that already reached the public package index."""
    nwave_home.mkdir(parents=True, exist_ok=True)
    record = json.dumps({"version": str(version), "checked": today.isoformat()}) + "\n"
    handle, name = tempfile.mkstemp(dir=nwave_home, prefix=".latest-release-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(record)
        Path(name).replace(cache_path(nwave_home))
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def read_cache(nwave_home: Path, today: date) -> CacheState:
    """The state of the cache; reads one small file and nothing else."""
    path = cache_path(nwave_home)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Missing()
    except (OSError, UnicodeDecodeError) as error:
        return Corrupt(f"{path} cannot be read: {error}")
    try:
        record = json.loads(text)
        if not isinstance(record, dict) or set(record) != {"version", "checked"}:
            raise ValueError(
                'it must be an object with exactly "version" and "checked"'
            )
        version = Version(record["version"])
        checked = date.fromisoformat(record["checked"])
    except (ValueError, TypeError, InvalidVersion) as error:
        return Corrupt(f"{path} is not a release record: {error}")
    if (today - checked).days > STALE_AFTER_DAYS:
        return Stale(checked)
    return Fresh(version, checked)


def notice_line(installed: str, state: CacheState) -> str:
    """One line when the installed release is older than the one the cache holds; otherwise nothing."""
    if not isinstance(state, Fresh):
        return ""
    try:
        current = Version(installed)
    except InvalidVersion:
        return ""
    if current.is_prerelease or current.is_devrelease or current.local:
        return ""
    if state.version <= current:
        return ""
    return (
        f"nWave {state.version} is available (installed {current}, last checked {state.checked}). "
        "Run `nwave-ai update --check` for the upgrade command. "
        "Turn this notice off with updates.notice false in the global config."
    )


def corrupt_report(state: Corrupt) -> str:
    """WHAT, WHY and HOW for a cache the notice ignores quietly and the doctor reports."""
    return (
        f"WHAT: the update-notice cache is unusable: {state.reason}. WHY: the notice reads only a record that "
        "nwave-ai update wrote, so it shows nothing until the file is replaced. HOW: delete the file or run "
        "`nwave-ai update --check` to write it again."
    )
