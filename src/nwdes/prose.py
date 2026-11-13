"""Prose assets: the public prose the examiner reads and the prose-only classifier decides from.

A pure leaf: it imports nothing from nwdes, so the handoff, the packets and the shell probe all
decide public prose from the same patterns and cannot diverge.

A pattern is a path or a glob relative to the candidate root. '*' stays within one path segment,
'**' crosses segments, and '/**/' admits zero or more directories. The examiner's public set is the
default patterns plus the patterns a project declares; the prose-only classifier keeps the defaults.
"""

import posixpath
import re
from dataclasses import dataclass
from functools import cache


@dataclass(frozen=True)
class PublicPattern:
    """One declared public path or glob. Built only from a validated declaration or the defaults."""

    text: str

    def matches(self, path: str) -> bool:
        return _compiled(self.text).fullmatch(path) is not None


@cache
def _compiled(text: str) -> re.Pattern[str]:
    return re.compile(_glob_regex(text))


def _glob_regex(text: str) -> str:
    parts = []
    index = 0
    while index < len(text):
        if text.startswith("/**/", index):
            parts.append("/(?:.*/)?")
            index += 4
        elif text.startswith("**", index):
            parts.append(".*")
            index += 2
        else:
            parts.append(_glob_character(text[index]))
            index += 1
    return "".join(parts)


def _glob_character(character: str) -> str:
    if character == "*":
        return "[^/]*"
    if character == "?":
        return "[^/]"
    return re.escape(character)


# The default public prose: the guides, skills, templates and agents, as Markdown and template files.
DEFAULT_PATTERNS = tuple(
    PublicPattern(f"{root}/**{suffix}")
    for root in ("docs/guides", "nWave/skills", "nWave/templates", "nWave/agents")
    for suffix in (".md", ".tmpl")
)


def examined_patterns(declared) -> tuple[PublicPattern, ...]:
    """The default patterns followed by the declared ones, each pattern once."""
    return tuple(dict.fromkeys((*DEFAULT_PATTERNS, *declared)))


def _normal(path):
    if not isinstance(path, str) or not path or path.startswith("/"):
        return None
    return posixpath.normpath(path)


def is_public_path(path, patterns) -> bool:
    """True when the lexically normalised path stays a relative path that a pattern matches.

    Absolute paths, paths that escape their root and other casings of a suffix are not public.
    """
    normal = _normal(path)
    return normal is not None and any(pattern.matches(normal) for pattern in patterns)


def is_prose_path(path) -> bool:
    return is_public_path(path, DEFAULT_PATTERNS)


def prose_only(paths) -> bool:
    """True when there is at least one path and every path is a prose asset."""
    paths = tuple(paths)
    return bool(paths) and all(is_prose_path(path) for path in paths)
