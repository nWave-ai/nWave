"""Prose assets: the one set of public files the examiner reads and the prose-only classifier decides from.

A pure leaf: it imports nothing from nwdes, so the handoff, the packets and the shell probe
all read the same set and cannot diverge.
"""

import posixpath


# Roots and suffixes of the files the source-blind examiner reads from HEAD.
PUBLIC_PROJECTION = (
    ("docs/guides", "nWave/skills", "nWave/templates", "nWave/agents"),
    (".md", ".tmpl"),
)


def is_prose_path(path) -> bool:
    """True when the lexically normalised path stays under a prose root with a prose suffix.

    Absolute paths, paths that escape their root and other casings of a suffix are not prose.
    """
    if not isinstance(path, str) or not path or path.startswith("/"):
        return False
    normal = posixpath.normpath(path)
    roots, suffixes = PUBLIC_PROJECTION
    return normal.endswith(suffixes) and any(
        normal.startswith(root + "/") for root in roots
    )


def prose_only(paths) -> bool:
    """True when there is at least one path and every path is a prose asset."""
    paths = tuple(paths)
    return bool(paths) and all(is_prose_path(path) for path in paths)
