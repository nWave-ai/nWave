"""The dependents command a project declares, its time bound, and the format its refusals teach.

Each call of the command is bounded: a call still running at the bound is killed and
gives no answer. The default bound is measured on nWave's own tree (see the design
record); a declaration may set another bound, up to the ceiling. The ceiling keeps a
declaration from switching the bound off.
"""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_TIMEOUT_SECONDS = 120.0
CEILING_TIMEOUT_SECONDS = 600.0

DEPENDENTS_FORMAT = (
    "selection.dependents declares the command that says which files depend on a file, "
    'as {"argv": ["python3", "scripts/dependents.py"], "covers": ["*.py"]}: argv is run '
    "from the project root, without a shell; covers lists the path patterns the command "
    "answers for. Optionally timeout_seconds bounds each call of the command (default "
    f"{DEFAULT_TIMEOUT_SECONDS:g} seconds, at most {CEILING_TIMEOUT_SECONDS:g}); a call "
    "still running at the bound is killed and its files are INDETERMINATE. On standard "
    "input the command gets one JSON object, "
    '{"files": [tree-relative paths], "targets": [paths it answers for]}, and prints one '
    "line per dependency on a target: TARGET, a tab, then DEPENDENT, where DEPENDENT "
    "depends directly on TARGET. Exit status 0 is an answer; any other status is "
    "could-not-verify. Check the declaration with: "
    "nwave-ai tests select --use commit <a changed path>"
)


@dataclass(frozen=True)
class DeclaredDependents:
    """The command that answers which files depend on a file, the paths it covers, its bound."""

    argv: tuple[str, ...]
    covers: tuple[str, ...]
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
