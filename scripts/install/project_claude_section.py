"""Managed marker-delimited section in a target project's managed guidance file.

The beta channel teaches the project's LLM how to drive the nWave spine and how
to collect friction/time/cost feedback locally (no transmission). That guidance
ships as a SECTION injected into the project's *existing* guidance file — never a
new file that competes with the user's own (Ale 2026-06-30: "aggiunge una sezione
e rimuoverla alla disinstallazione, non deve crearne uno nuovo"). Two hosts are
supported today: Claude Code's ``CLAUDE.md`` and Codex's ``AGENTS.md`` — same
marker/atomic-write engine, one template per host (``HOSTS`` below), so the
Claude-specific slash-command/Skill-tool prose never lands in the Codex file.

The section is bounded by HTML-comment markers (invisible in rendered markdown),
so injection is idempotent (re-inject replaces the block between the markers) and
removal is surgical (only the managed block is touched; the user's content is
preserved). Writes are atomic (temp file + ``os.replace``).

These are pure functions over a path + content string; the CLI wires them to
``nwave-ai project enable`` (inject, with user consent) and ``project disable``
(remove). They depend ONLY on the stdlib and the filesystem — no git, no network.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import NamedTuple


# HTML-comment markers — invisible in rendered markdown, stable across edits.
# Shared across hosts: each host writes to its own file, so the marker never
# collides even though the text is identical.
BEGIN_MARKER = "<!-- BEGIN nWave-beta-section (managed by nwave-ai; do not edit) -->"
END_MARKER = "<!-- END nWave-beta-section -->"

# Managed fragments are authored once and spliced into every host template.
# Placeholder names are how templates ask for them; the splice here ensures
# composed bytes are identical across hosts.
_FRAGMENTS = (
    (
        "{{DELIVERY_ROUTE_FRAGMENT}}",
        ("nWave", "templates", "delivery-route-fragment.md"),
    ),
    ("{{TOOL_BATCHING_FRAGMENT}}", ("nWave", "templates", "tool-batching-fragment.md")),
    (
        "{{QUESTION_FORMAT_FRAGMENT}}",
        ("nWave", "templates", "question-format-fragment.md"),
    ),
)


class HostGuidance(NamedTuple):
    """One managed-guidance host: its target filename and template source."""

    filename: str
    template_relpath: tuple[str, ...]


# Registry of supported hosts. Add a host by adding one entry + one template —
# never a parallel copy of this module's marker/atomic-write engine.
HOSTS: dict[str, HostGuidance] = {
    "claude": HostGuidance(
        "CLAUDE.md", ("nWave", "templates", "beta-project-claude-section.md")
    ),
    "codex": HostGuidance(
        "AGENTS.md", ("nWave", "templates", "beta-project-agents-section.md")
    ),
}


def resolve_section_template(
    project_root: Path | None = None, *, host: str = "claude"
) -> Path:
    """Locate the beta guidance-section template for ``host``.

    ``project_root`` is the nWave source/package root (where ``nWave/`` lives),
    NOT the target project. When omitted, derive it from this file's location
    (``scripts/install/`` → repo root), which holds in both the dev tree and the
    installed layout where ``nWave/`` ships beside the scripts.
    """
    root = project_root or Path(__file__).resolve().parents[2]
    return root.joinpath(*HOSTS[host].template_relpath)


def load_section_content(
    project_root: Path | None = None, *, host: str = "claude"
) -> str:
    """Read the managed-section body for ``host`` (inner content, no markers).

    Splices managed fragments into the template's placeholders, ensuring
    fragment bytes are identical across every host by construction. Any
    GENERATED region the template carries (e.g. ``communication-rules``) is
    then re-rendered for ``project_root`` via the single-asset projection
    ``des`` owns (``project_asset``, ADR-CFG-001 Slice 2) -- REUSE_CANDIDATE:
    this is the ONE call site, never a second, independent
    DESConfig/merge_config read.

    That engine is imported from ``des`` and NOT from ``scripts.docgen``:
    this module ships in the public wheel while docgen deliberately does not,
    so the previous ``from scripts.docgen import _project_asset`` made every
    consumer install die with ``ModuleNotFoundError: No module named
    'scripts.docgen'``. ``des`` is force-included into every wheel by
    construction, so that mismatch cannot recur here.
    """
    from nwave_ai.platform.regions import project_asset

    root = project_root or Path(__file__).resolve().parents[2]
    template_path = resolve_section_template(root, host=host)
    template = template_path.read_text(encoding="utf-8")
    content = template
    for placeholder, relpath in _FRAGMENTS:
        fragment = root.joinpath(*relpath).read_text(encoding="utf-8").strip()
        content = content.replace(placeholder, fragment)
    content = project_asset(template_path, content, root).projected_text
    return content.strip()


def _build_block(content: str) -> str:
    """Wrap the content body between the BEGIN/END markers."""
    return f"{BEGIN_MARKER}\n\n{content.strip()}\n\n{END_MARKER}\n"


def _atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically (temp file in the same dir + replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=".claude-md-", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        Path(tmp_name).replace(path)
    except BaseException:
        try:
            Path(tmp_name).unlink()
        except OSError:
            pass
        raise


def _strip_existing_block(text: str) -> str:
    """Return ``text`` with the managed block (markers + body) removed.

    Tolerant of surrounding blank lines so repeated inject/remove cycles do not
    accrete whitespace. If no block is present, ``text`` is returned unchanged.
    """
    begin = text.find(BEGIN_MARKER)
    if begin == -1:
        return text
    end = text.find(END_MARKER, begin)
    if end == -1:
        # Malformed (BEGIN without END) — leave the file untouched rather than
        # guess where the block ends.
        return text
    end += len(END_MARKER)
    before = text[:begin].rstrip("\n")
    after = text[end:].lstrip("\n")
    if before and after:
        return f"{before}\n\n{after}"
    return before or after


def inject_managed_section(claude_md_path: Path, content: str) -> str:
    """Inject (or refresh) the managed section in ``claude_md_path``.

    Idempotent:
    - file absent            → create it containing only the managed block
    - file present, no block → append the block, preserving existing content
    - file present, has block→ replace the block in place (no duplication)

    Returns one of ``"created"`` / ``"appended"`` / ``"updated"``.
    """
    block = _build_block(content)
    if not claude_md_path.exists():
        _atomic_write(claude_md_path, block)
        return "created"

    existing = claude_md_path.read_text(encoding="utf-8")
    if BEGIN_MARKER in existing:
        stripped = _strip_existing_block(existing).rstrip("\n")
        new_text = f"{stripped}\n\n{block}" if stripped else block
        _atomic_write(claude_md_path, new_text)
        return "updated"

    base = existing.rstrip("\n")
    new_text = f"{base}\n\n{block}" if base else block
    _atomic_write(claude_md_path, new_text)
    return "appended"


def remove_managed_section(claude_md_path: Path) -> str:
    """Remove the managed section from ``claude_md_path``.

    Preserves all user content outside the markers. If, after removal, the file
    holds only whitespace (i.e. nwave-ai had created it), the file is deleted.

    Returns one of ``"absent"`` / ``"removed-section"`` / ``"removed-file"``.
    """
    if not claude_md_path.exists():
        return "absent"
    existing = claude_md_path.read_text(encoding="utf-8")
    if BEGIN_MARKER not in existing:
        return "absent"

    remainder = _strip_existing_block(existing).strip()
    if not remainder:
        claude_md_path.unlink()
        return "removed-file"
    _atomic_write(claude_md_path, remainder + "\n")
    return "removed-section"
