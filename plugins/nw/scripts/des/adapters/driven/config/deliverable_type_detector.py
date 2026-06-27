"""Root-only filesystem deliverable-type detection (ADR-PST-002) -- RED scaffold.

DISTILL scaffold (feature plugin-skill-deliverable-type, issue #66). Pure given a
project-root directory listing: inspects ONLY project-root markers and returns
``"plugin"`` / ``"skill"`` / ``"application"``. It NEVER recursively scans nested
directories -- a bounded (root-only) universe (Principle 12). The collision case
``nWave/skills/`` (nested) MUST NOT trigger ``skill``.

Detection is the FALLBACK only; ``.nwave/des-config.json`` declaration is
authoritative (resolved in ``DESConfig.deliverable_type``). Detection on its own
never DISABLES enforcement -- only a positive ``plugin``/``skill`` root marker does.

Root markers (ADR-PST-002 precedence, first match wins; issue #66 AC signal set):
  1. ``.claude-plugin/`` dir OR ``plugin.json`` OR ``marketplace.json`` -> plugin
  2. top-level ``skills/`` / ``commands/`` / ``hooks/`` (root only, no plugin
     manifest)                                                        -> skill
  3. otherwise                                                        -> application

The issue AC enumerates ``.claude-plugin/``, top-level ``skills/`` / ``commands/`` /
``hooks/``, or ``marketplace.json`` as the signal set; ``commands/`` and ``hooks/``
are skill-class markers (the issue is authoritative). All root-only; a nested
``*/skills/`` / ``*/commands/`` / ``*/hooks/`` never triggers detection.

DELIVER replaces this scaffold with the real implementation (GREEN) and removes
the ``__SCAFFOLD__`` marker.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003  (used at runtime via iterdir on the argument)


# Root markers, by precedence (ADR-PST-002). A plugin manifest wins over skill
# markers: a plugin may bundle skills, so its own manifest is the stronger signal.
_PLUGIN_MARKERS = frozenset({".claude-plugin", "plugin.json", "marketplace.json"})
_SKILL_MARKERS = frozenset({"skills", "commands", "hooks"})


def detect_deliverable_type(project_root: Path) -> str:
    """Detect the deliverable type from root-only filesystem markers.

    Inspects ONLY the entries sitting directly at ``project_root`` -- it never
    recurses, so a nested ``*/skills/`` is not a signal (the collision guard,
    ADR-PST-002). The scan is a pure read over the root directory listing: it
    mutates nothing and is idempotent.

    Precedence (first class wins): a plugin manifest (``.claude-plugin/`` dir,
    ``plugin.json``, or ``marketplace.json``) -> ``"plugin"``; otherwise a skill
    folder (``skills/``, ``commands/``, or ``hooks/``) -> ``"skill"``; otherwise
    ``"application"``. Plugin wins over skill because a plugin may bundle skills.

    Args:
        project_root: the project root directory to inspect (root-only; never
            recursed).

    Returns:
        ``"plugin"`` | ``"skill"`` | ``"application"``.
    """
    root_entries = {entry.name for entry in project_root.iterdir()}
    if root_entries & _PLUGIN_MARKERS:
        return "plugin"
    if root_entries & _SKILL_MARKERS:
        return "skill"
    return "application"
