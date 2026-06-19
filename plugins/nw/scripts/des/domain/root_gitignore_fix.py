"""Pure root-``.gitignore`` content transform (ADR-AG-004).

Match any whole-dir ``.nwave`` exclude line and rewrite it to ``.nwave/*`` +
``!.nwave/local-config.json`` (preserving a leading slash if the original line had
one); if no such line exists, append the re-include under an nWave banner. Git
cannot re-include a child while its parent dir is excluded with a whole-dir
pattern, so the whole-dir exclude must become ``.nwave/*`` + a negation.

Pure: string content in, string content out, no filesystem. Idempotent by
construction -- re-applying to already-fixed content is a no-op.
"""

from __future__ import annotations


_BANNER = "# nWave activation marker (keep .nwave/local-config.json trackable)"

# Whole-dir ``.nwave`` exclude shapes, mapped to whether they carry a leading
# slash. The transform rewrites any of these to ``<prefix>.nwave/*`` plus the
# matching ``!<prefix>.nwave/local-config.json`` negation.
_WHOLE_DIR_EXCLUDES: dict[str, str] = {
    ".nwave": "",
    ".nwave/": "",
    "/.nwave": "/",
    "/.nwave/": "/",
}


def fix_root_gitignore(content: str) -> str:
    """Return the root ``.gitignore`` content with the marker re-included.

    Args:
        content: current root ``.gitignore`` text.

    Returns:
        transformed text (idempotent: re-applying is a no-op).
    """
    if _already_fixed(content):
        return content

    lines = content.splitlines()
    for index, line in enumerate(lines):
        prefix = _WHOLE_DIR_EXCLUDES.get(line.strip())
        if prefix is None:
            continue
        lines[index] = f"{prefix}.nwave/*"
        lines.insert(index + 1, f"!{prefix}.nwave/local-config.json")
        return _join(lines)

    return _append_reinclude(content)


def _already_fixed(content: str) -> bool:
    """Whether a marker re-include negation is already present."""
    stripped = {line.strip() for line in content.splitlines()}
    return any(
        line in {"!.nwave/local-config.json", "!/.nwave/local-config.json"}
        for line in stripped
    )


def _append_reinclude(content: str) -> str:
    """Append the banner + re-include block to customized content."""
    base = content if content.endswith("\n") or content == "" else content + "\n"
    return f"{base}{_BANNER}\n.nwave/*\n!.nwave/local-config.json\n"


def _join(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"
