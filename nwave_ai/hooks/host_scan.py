"""nWave subagent host-scan lockdown (K4 architecture gap), re-homed (F215).

A dispatched nw-* subagent's own Bash ``find``/``bfs`` call is restricted to a
repo-scoped traversal root -- ``find /`` (or an option-prefixed equivalent)
walks the whole host instead of the active project. Root/user Bash and
non-nWave agents are untouched (see :func:`_is_nwave_subagent`).

Identity is resolved through the ONE shared resolver in
``nwave_ai.hooks.lifecycle`` (live envelope field, or the subagent transcript's
``.meta.json`` sidecar) -- never duplicated here.
"""

from __future__ import annotations

from nwave_ai.hooks.lifecycle import resolve_subagent_agent_type
from nwave_ai.hooks.stash import _split_subcommands


_HOST_SCAN_COMMAND_NAMES = frozenset({"find", "bfs"})


def _is_nwave_subagent(hook_input: dict[str, object]) -> bool:
    """True iff this dispatch is a running nWave subagent -- resolved via
    ``lifecycle.resolve_subagent_agent_type`` (the ONE shared resolver: live
    envelope field, or its transcript meta-sidecar) -- never root/user
    (neither source resolves) and never a non-nWave agent (some other prefix
    on both sources)."""
    return resolve_subagent_agent_type(hook_input) is not None


def _host_scan_traversal_roots(argv: list[str]) -> list[str]:
    """The traversal-root path arguments of a ``find``/``bfs`` argv.

    Options may precede the roots (``find -H /``); once at least one root has
    been collected, the next ``-``-prefixed token starts the predicate/
    expression list and ends the scan -- ``find /repo -name find`` must not
    see a later bare ``find`` token in a predicate as a second root.
    """
    roots: list[str] = []
    for token in argv[1:]:
        if token.startswith("-"):
            if roots:
                break
            continue
        roots.append(token)
    return roots


def _is_host_wide_traversal_root(root: str) -> bool:
    """True iff ``root`` is the filesystem root itself (``/``, ``//``, ...) --
    never a scoped path like ``/repo``, ``/tmp/project``, ``.``, or
    ``AUTO-ARCHITECTURE-ROOT``."""
    return root.rstrip("/") == ""


def _nwave_host_scan_block(command: str) -> dict[str, str]:
    return {
        "decision": "block",
        "reason": (
            f"WHAT: an nWave subagent Bash call ({command!r}) traverses the "
            "filesystem root instead of the active project. "
            "WHY: a host-wide find/bfs scan can spend minutes walking the "
            "entire machine instead of the project tree -- discovery must "
            "stay repo-scoped so a consult's critical path is not spent "
            "scanning the host. "
            "HOW: use repo-scoped Glob/Grep/find rooted at the project "
            "directory or the absolute AUTO-ARCHITECTURE-ROOT, or inspect "
            "the exact module path directly (e.g. `python -c "
            '"import inspect, <module>; print(inspect.getsourcefile(<module>))"` '
            "and read the returned path)."
        ),
    }


def _evaluate_nwave_subagent_host_scan(command: object) -> dict[str, str] | None:
    """Pure nWave-subagent ``find``/``bfs`` host-scan decision.

    Returns ``None`` (allow) for anything that is not, in some ``&&``/``||``/``;``/
    ``|``/``&``-separated sub-command, an actual ``find``/``bfs`` invocation whose
    traversal root is the filesystem root -- including quoted mentions
    (shlex tokenizes those into one non-command argument, never ``argv[0]``)
    and repo-/cwd-/AUTO-root-scoped invocations. Fails open (``None``) on an
    unparsable command, which fails open so the safety hook stays local to
    commands it can classify.
    """
    if not isinstance(command, str) or not command.strip():
        return None
    sub_commands = _split_subcommands(command)
    if sub_commands is None:
        return None
    for argv in sub_commands:
        if not argv or argv[0] not in _HOST_SCAN_COMMAND_NAMES:
            continue
        roots = _host_scan_traversal_roots(argv)
        if any(_is_host_wide_traversal_root(root) for root in roots):
            return _nwave_host_scan_block(command)
    return None


__all__ = [
    "_evaluate_nwave_subagent_host_scan",
    "_host_scan_traversal_roots",
    "_is_host_wide_traversal_root",
    "_is_nwave_subagent",
    "_nwave_host_scan_block",
]
