"""Configuration tiers and fixed document destinations, without filesystem effects."""

import json
from dataclasses import dataclass
from enum import Enum

from nwdes.contracts import (
    LINE_BOUNDARIES,
    Built,
    Defect,
    Refused,
    checked,
    local_path,
    strict_object,
)


class DocumentKind(str, Enum):
    Product = "Product"
    Architecture = "Architecture"
    Acceptance = "Acceptance"


@dataclass(frozen=True)
class ConfigurationTier:
    kind: str
    source: str
    entries: tuple[tuple[str, str | tuple[str, ...] | None], ...] = ()
    unknown: bool = False

    def get(self, key: str, default=None):
        return next((value for name, value in self.entries if name == key), default)


@dataclass(frozen=True)
class ConfigurationRefused(Refused):
    """Retain readable sibling keys without treating an invalid key as absent."""

    tier: ConfigurationTier


def _tier_result(tier, defects):
    result = checked(tier, defects)
    return (
        ConfigurationRefused(result.refusal, tier)
        if isinstance(result, Refused)
        else result
    )


@dataclass(frozen=True)
class Destinations:
    briefs: tuple[tuple[DocumentKind, str], ...]
    handoff: str
    adr_directory: str


@dataclass(frozen=True)
class CommitLocations:
    """Private paths derived from the git port's `--git-path nwdes` answer."""

    directory: str

    @property
    def lock(self):
        return self.directory + "/commit.lock"

    @property
    def closes(self):
        return self.directory + "/closes"

    @property
    def workspaces(self):
        return self.directory + "/workspaces"

    def receipt(self, role):
        return self.closes + "/" + role + ".json"


def _malformed(name, key, why):
    return Defect(
        f"ConfigurationMalformed: {name}: {key}",
        why,
        f"Supply {key} with the declared configuration shape in {name}.",
    )


def _read_setting(name, key, value):
    if not isinstance(value, str):
        return ((key, None),), (_malformed(name, key, "Expected a directory string."),)
    if not local_path(value):
        return ((key, None),), (
            Defect(
                f"DestinationInvalid: {name}: {key}",
                "Directory must be repository-relative, without traversal, line boundaries or edge whitespace.",
                f"Set {key} to a repository-relative directory with no '..' segment.",
            ),
        )
    return ((key, value),), ()


def _nwdes(name, value, scoped):
    if not isinstance(value, dict):
        keys = (
            ("nwdes.directory",)
            if scoped
            else tuple(
                f"nwdes.{kind}.directory" for kind in ("feature", "epic", "project")
            )
        )
        return tuple((key, None) for key in keys), (
            _malformed(name, "nwdes", "Expected an object."),
        )
    results = tuple(
        _read_setting(name, "nwdes.directory", value["directory"])
        for _ in (0,)
        if scoped and "directory" in value
    ) + tuple(
        _scope_directory(name, kind, value[kind])
        for kind in ("feature", "epic", "project")
        if not scoped and kind in value
    )
    return (
        tuple(entry for entries, _ in results for entry in entries),
        tuple(defect for _, defects in results for defect in defects),
    )


def _scope_directory(name, kind, value):
    key = f"nwdes.{kind}"
    if not isinstance(value, dict):
        return ((key + ".directory", None),), (
            _malformed(name, key, "Expected an object."),
        )
    return (
        _read_setting(name, key + ".directory", value["directory"])
        if "directory" in value
        else ((), ())
    )


def _jev(name, value):
    """Persistent Jev consent is a user-owned string: authorized or unauthorized."""
    if value in ("authorized", "unauthorized"):
        return (("jev", value),), ()
    return (("jev", None),), (
        _malformed(name, "jev", "Expected 'authorized' or 'unauthorized'."),
    )


def _jev_key(name, value, scoped):
    """Jev is repository-wide: a scoped tier that declares it is refused, never ignored."""
    if scoped:
        return (), (
            _malformed(name, "jev", "This key is repository-wide, not scoped."),
        )
    return _jev(name, value)


def parse_tier(kind: str, name: str, data: bytes):
    """Parse only owned keys; unrelated producers' configuration is opaque."""
    try:
        raw = json.loads(data.decode("utf-8"), object_pairs_hook=strict_object)
    except (UnicodeError, ValueError) as error:
        return _tier_result(
            ConfigurationTier(kind, name, unknown=True),
            (_malformed(name, "JSON", str(error)),),
        )
    if not isinstance(raw, dict):
        return _tier_result(
            ConfigurationTier(kind, name, unknown=True),
            (_malformed(name, "JSON", "Expected an object."),),
        )
    scoped = kind in ("feature", "epic")
    results = (
        ((_nwdes(name, raw["nwdes"], scoped),) if "nwdes" in raw else ())
        + (
            (
                (
                    (),
                    (
                        _malformed(
                            name,
                            "adr.directory",
                            "This key is repository-wide, not scoped.",
                        ),
                    ),
                )
                if scoped
                else _adr(name, raw["adr"]),
            )
            if "adr" in raw
            else ()
        )
        + ((_lanes(name, raw["lanes"], scoped),) if "lanes" in raw else ())
        + ((_jev_key(name, raw["jev"], scoped),) if "jev" in raw else ())
    )
    return _tier_result(
        ConfigurationTier(
            kind, name, tuple(entry for entries, _ in results for entry in entries)
        ),
        (defect for _, defects in results for defect in defects),
    )


def _adr(name, value):
    if not isinstance(value, dict):
        return (("adr.directory", None),), (
            _malformed(
                name, "adr.directory", "Expected an object containing directory."
            ),
        )
    return (
        _read_setting(name, "adr.directory", value["directory"])
        if "directory" in value
        else ((), ())
    )


def _lanes(name, value, scoped):
    keys = ("lanes.trunk", "lanes.disposable")
    if not isinstance(value, dict):
        return tuple((key, None) for key in keys), tuple(
            _malformed(name, key, "Expected a lanes object.") for key in keys
        )
    results = tuple(
        (key, parse_lane_setting(name, key, value[key.removeprefix("lanes.")], scoped))
        for key in keys
        if key.removeprefix("lanes.") in value
    )
    return (
        tuple(
            (key, result.value if isinstance(result, Built) else None)
            for key, result in results
        ),
        tuple(
            defect
            for _, result in results
            if isinstance(result, Refused)
            for defect in result.defects
        ),
    )


def parse_lane_setting(name, key, value, scoped=False):
    if scoped:
        return checked(
            None, (_malformed(name, key, "This key is repository-wide, not scoped."),)
        )
    valid = (
        isinstance(value, str)
        and bool(value)
        and not any(character in value for character in LINE_BOUNDARIES)
        if key == "lanes.trunk"
        else isinstance(value, (list, tuple))
        and all(isinstance(pattern, str) and bool(pattern) for pattern in value)
    )
    if not valid:
        return checked(
            None,
            (
                _malformed(
                    name,
                    key,
                    "Expected a non-empty single-line branch string."
                    if key == "lanes.trunk"
                    else "Expected a list of non-empty pattern strings.",
                ),
            ),
        )
    return Built(tuple(value) if isinstance(value, (list, tuple)) else value)


def readable_setting(tiers, key, default):
    for result in reversed(tiers):
        tier = (
            result.value
            if isinstance(result, Built)
            else result.tier
            if isinstance(result, ConfigurationRefused)
            else result
            if isinstance(result, ConfigurationTier)
            else None
        )
        if tier is None or tier.unknown:
            return None
        if any(name == key for name, _ in tier.entries):
            return tier.get(key)
    return default


def readable_directory(tiers, scope):
    kind = scope.kind.lower()
    directory = readable_setting(
        tiers,
        f"nwdes.{kind}.directory",
        f"docs/{'product' if kind == 'project' else kind}",
    )
    return (
        directory
        if kind == "project"
        else readable_setting(
            tiers,
            "nwdes.directory",
            directory + "/" + scope.id if directory is not None else None,
        )
    )


def _brief_paths(directory):
    return tuple(
        (kind, directory + "/" + filename)
        for kind, filename in (
            (DocumentKind.Product, "brief.md"),
            (DocumentKind.Architecture, "architecture.md"),
            (DocumentKind.Acceptance, "acceptance.md"),
        )
    )


def readable_paths(tiers, scope):
    directory = readable_directory(tiers, scope) if scope is not None else None
    if directory is None:
        return ()
    briefs = _brief_paths(directory)
    return (
        directory + "/handoff.json",
        *(path for _, path in briefs),
        *(path[:-3] + ".html" for _, path in briefs),
    )


def resolve(tiers: tuple[ConfigurationTier, ...], scope):
    """Resolve ascending-precedence tiers, then derive every fixed filename."""
    problems = tuple(
        defect for tier in tiers if isinstance(tier, Refused) for defect in tier.defects
    )
    if problems:
        return checked(None, problems)
    directory = readable_directory(tiers, scope)
    briefs = _brief_paths(directory)
    return Built(
        Destinations(
            briefs,
            directory + "/handoff.json",
            readable_setting(tiers, "adr.directory", "docs/product/architecture"),
        )
    )
