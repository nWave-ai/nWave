"""Pure scope selection shared by every source provider."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from codefact.model import Snapshot


def text(snapshot: Snapshot, relative: str) -> str | None:
    source = snapshot.entries.get(relative)
    if source is None or source.content is None:
        return None
    try:
        return source.content.decode("utf-8")
    except UnicodeDecodeError:
        return None


@dataclass(frozen=True)
class _IgnoreRules:
    names: frozenset[str]
    excluded: tuple[str, ...]
    included: tuple[str, ...]


def root_ignore_text(snapshot: Snapshot) -> str:
    """The root .gitignore as text. Undecodable bytes raise, as legacy's read does."""
    source = snapshot.entries.get(".gitignore")
    if source is None or source.content is None:
        return ""
    return source.content.decode("utf-8")


def _rules(snapshot: Snapshot) -> _IgnoreRules:
    lines = root_ignore_text(snapshot).splitlines()
    rules = tuple(
        rule
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
        for rule in (_rule(line.strip()),)
        if "*" not in rule[1]
    )
    names = frozenset(
        entry
        for negate, entry, wildcard in rules
        if not negate and "/" not in entry and not wildcard
    ) - frozenset(
        entry
        for negate, entry, wildcard in rules
        if negate and "/" not in entry and not wildcard
    )
    excluded = tuple(
        entry
        for negate, entry, wildcard in rules
        if not negate and ("/" in entry or wildcard)
    )
    included = tuple(
        entry
        for negate, entry, wildcard in rules
        if negate and ("/" in entry or wildcard)
    )
    return _IgnoreRules(names, excluded, included)


def _rule(line: str):
    negate = line.startswith("!")
    entry = line.lstrip("!").strip().rstrip("/")
    wildcard = entry.endswith("/*") and entry.count("*") == 1
    entry = entry[:-2] if wildcard else entry
    return negate, entry.strip("/"), wildcard


def _excluded(rules: _IgnoreRules, relative: str) -> bool:
    parents = relative.split("/")[:-1]
    if ".git" in parents:
        return True
    if rules.names.intersection(parents):
        return True
    directory = "/".join(parents)
    return any(
        directory == entry or directory.startswith(entry + "/")
        for entry in rules.excluded
    ) and not any(
        directory == entry or directory.startswith(entry + "/")
        for entry in rules.included
    )


def files(snapshot: Snapshot, pattern: str = "*") -> tuple[str, ...]:
    rules = _rules(snapshot)
    return tuple(
        sorted(
            path
            for path, source in snapshot.entries.items()
            if fnmatch(path.rsplit("/", 1)[-1], pattern)
            and not _excluded(rules, path)
            and (source.content is None or b"\0" not in source.content[:8000])
        )
    )


def health(snapshot: Snapshot) -> str:
    rules = _rules(snapshot)
    dropped = snapshot.pruned or any(
        _excluded(rules, path)
        or (source.content is not None and b"\0" in source.content[:8000])
        for path, source in snapshot.entries.items()
    )
    return (
        "filtered"
        if dropped
        else "complete"
        if ".gitignore" in snapshot.entries
        else "unfiltered"
    )


def subject(request) -> str:
    return next(
        (
            value
            for key in ("symbol", "anchor", "name")
            if isinstance(value := request.get(key), str) and value
        ),
        "",
    )
