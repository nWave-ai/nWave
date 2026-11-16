"""The default schema: the shipped schema file that the shipped set declares current.

Pure: a declared file name and the names of the shipped schema files in, a file name out. Nothing is chosen by sort order
or by the shape of a file name; a declaration that names no shipped file is refused.
"""

from __future__ import annotations

from nwexpress.domain.refusal import Refusal


def resolve_current(declared: str, shipped: frozenset[str]) -> str:
    """The declared schema file name, when a shipped schema file has exactly that name; otherwise a refusal that names the shipped set."""
    if declared in shipped:
        return declared
    names = ", ".join(sorted(shipped)) or "none"
    raise Refusal(
        what=f"the declared current schema {declared} is not among the shipped schemas",
        why="a run starts from the declared current schema, so a declaration that names no shipped file would start a run from nothing",
        how=f"declare as current one of the shipped schemas ({names}) by setting current_schema in templates/versions.toml",
    )
