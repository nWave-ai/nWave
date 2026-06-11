"""Shared skill distribution logic for all nWave consumers.

Single source of truth for the enumerate -> filter -> copy pipeline used by:
1. Claude Code CLI installer (skills_plugin.py)
2. OpenCode CLI installer (opencode_skills_plugin.py)
3. Plugin/marketplace builder (build_plugin.py)
4. Dist tarball builder (build_dist.py)

Data Types:
    SkillEntry: NamedTuple(name, source_path) -- a discovered skill.
    SourceLayout: Enum with NEW_FLAT and OLD_HIERARCHICAL variants.

Pipeline:
    entries = enumerate_skills(source_dir)         # detect layout internally
    entries = filter_public_skills(entries, ...)    # remove private skills
    count = copy_skills_to_target(entries, target, clean_existing=True)  # copytree
"""

from __future__ import annotations

import enum
import json
import shutil
from typing import TYPE_CHECKING, NamedTuple


if TYPE_CHECKING:
    from pathlib import Path

from scripts.shared.agent_catalog import is_public_skill


class SkillEntry(NamedTuple):
    """A discovered skill with its name and source path."""

    name: str
    source_path: Path


class SourceLayout(enum.Enum):
    """Detected source directory layout for skills."""

    NEW_FLAT = "new_flat"  # nw-*/SKILL.md directories
    OLD_HIERARCHICAL = "old_hierarchical"  # {agent}/*.md directories


#: The shared record file — ONE manifest format for every asset family.
MANIFEST_FILENAME = ".nwave-manifest.json"
_MANIFEST_FILENAME = MANIFEST_FILENAME

#: Asset-family keys inside the shared manifest document. Families sharing a
#: target directory each own one key; sibling keys are never clobbered.
SCRIPTS_FAMILY_KEY = "installed_scripts"
UTILITIES_FAMILY_KEY = "installed_utilities"
TEMPLATES_FAMILY_KEY = "installed_templates"
SKILLS_FAMILY_KEY = "installed_skills"


class FamilyRecord(NamedTuple):
    """Resolved manifest record for one asset family in a shared directory.

    ``tracked is None`` means pre-record (adoption run): the family must
    preserve everything and may only warn. ``superseded_keys`` are legacy
    v1.0-era keys this family adopted — the next write retires them.
    ``accounted`` unions every name ANY record in the document tracks.
    """

    tracked: frozenset[str] | None
    superseded_keys: frozenset[str]
    accounted: frozenset[str]


def detect_layout(source_dir: Path) -> SourceLayout:
    """Detect whether source uses NEW_FLAT or OLD_HIERARCHICAL layout.

    NEW_FLAT: at least one nw-*/SKILL.md directory exists.
    OLD_HIERARCHICAL: fallback when no nw-*/SKILL.md found.
    """
    for child in source_dir.iterdir():
        if child.is_dir() and child.name.startswith("nw-"):
            if (child / "SKILL.md").is_file():
                return SourceLayout.NEW_FLAT
    return SourceLayout.OLD_HIERARCHICAL


def enumerate_skills(source_dir: Path) -> list[SkillEntry]:
    """Find all skills in source directory, returning sorted SkillEntry list.

    Calls detect_layout() internally. Callers do not need to detect layout.

    NEW_FLAT: iterates nw-*/SKILL.md, returns SkillEntry(name=dir.name, path=dir).
    OLD_HIERARCHICAL: iterates {agent}/*.md, returns SkillEntry(name=stem, path=file).
    """
    layout = detect_layout(source_dir)

    if layout == SourceLayout.NEW_FLAT:
        return _enumerate_flat(source_dir)
    return _enumerate_hierarchical(source_dir)


def _enumerate_flat(source_dir: Path) -> list[SkillEntry]:
    """Enumerate skills from NEW_FLAT layout: nw-*/SKILL.md."""
    entries: list[SkillEntry] = []
    for child in sorted(source_dir.iterdir()):
        if not child.is_dir() or not child.name.startswith("nw-"):
            continue
        if (child / "SKILL.md").is_file():
            entries.append(SkillEntry(name=child.name, source_path=child))
    return entries


def _enumerate_hierarchical(source_dir: Path) -> list[SkillEntry]:
    """Enumerate skills from OLD_HIERARCHICAL layout: {agent}/*.md."""
    entries: list[SkillEntry] = []
    for agent_dir in sorted(source_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        for skill_file in sorted(agent_dir.glob("*.md")):
            entries.append(SkillEntry(name=skill_file.stem, source_path=skill_file))
    return entries


def filter_public_skills(
    entries: list[SkillEntry],
    public_agents: set[str],
    ownership_map: dict[str, set[str]],
    command_skills: set[str] | None = None,
) -> list[SkillEntry]:
    """Filter entries to only public skills using ownership_map.

    Delegates to is_public_skill() from agent_catalog.py.
    Command-skills (user-invocable slash commands) are always included.
    When public_agents is empty, returns all entries (backward compatibility).
    """
    kept, _ = filter_public_skills_with_reasons(
        entries, public_agents, ownership_map, command_skills
    )
    return kept


def filter_public_skills_with_reasons(
    entries: list[SkillEntry],
    public_agents: set[str],
    ownership_map: dict[str, set[str]],
    command_skills: set[str] | None = None,
) -> tuple[list[SkillEntry], list[tuple[str, str]]]:
    """Filter entries + return parallel list of (excluded_name, reason).

    Reason vocabulary:
        - "uncatalogued"                          — no owning agent in ownership_map
        - "private-owned by {comma-separated}"    — all owning agents are private

    When ``public_agents`` is empty (catalog not loaded / dev_mode), no entry
    is excluded and the reasons list is empty. This preserves backward
    compatibility with ``filter_public_skills`` callers.

    Bug #fix-installer-silent-template-skip: pre-fix this filter silently
    dropped skills with zero diagnostic. The reasons list lets the caller
    emit a "Skipped {name}: {reason}" line per dropped skill so authors of
    new skills see why their skill never reached ``~/.claude/``.
    """
    if not public_agents:
        return list(entries), []

    kept: list[SkillEntry] = []
    excluded: list[tuple[str, str]] = []
    for entry in entries:
        if is_public_skill(entry.name, public_agents, ownership_map, command_skills):
            kept.append(entry)
            continue
        excluded.append((entry.name, _exclusion_reason(entry.name, ownership_map)))
    return kept, excluded


def _exclusion_reason(skill_name: str, ownership_map: dict[str, set[str]]) -> str:
    """Derive a human-readable reason explaining why a skill was filtered out."""
    lookup_key = skill_name if skill_name.startswith("nw-") else f"nw-{skill_name}"
    owners = ownership_map.get(lookup_key)
    if not owners:
        return "uncatalogued"
    return f"private-owned by {', '.join(sorted(owners))}"


def copy_skills_to_target(
    entries: list[SkillEntry],
    target_dir: Path,
    *,
    clean_existing: bool = False,
) -> int:
    """Copy skill directories to target via shutil.copytree.

    When *clean_existing* is True, removes all existing nw-* directories
    from target_dir before copying. Non-nw-* directories (user custom
    skills) are preserved.

    For NEW_FLAT entries (source_path is a directory), copies the full directory.
    For OLD_HIERARCHICAL entries (source_path is a file), copies the file into
    a directory named after the skill.

    Returns count of skills copied.
    """
    if clean_existing:
        # Manifest-based selective cleanup: only remove skills previously
        # installed by the framework, preserving user-created nw-* skills.
        manifest = read_manifest(target_dir)
        framework_skills = set(manifest[SKILLS_FAMILY_KEY]) if manifest else None

        for existing in target_dir.iterdir():
            if existing.is_dir() and existing.name.startswith("nw-"):
                if framework_skills is None:
                    # No manifest (first install after this change): fall back
                    # to removing all nw-* dirs (backward compat)
                    shutil.rmtree(existing)
                elif existing.name in framework_skills:
                    # Known framework skill: safe to remove (will be reinstalled)
                    shutil.rmtree(existing)
                # else: user-created skill, preserve it

    count = 0
    new_skill_names = []
    for entry in entries:
        destination = target_dir / entry.name
        if entry.source_path.is_dir():
            shutil.copytree(entry.source_path, destination, dirs_exist_ok=True)
        else:
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry.source_path, destination / entry.source_path.name)
        new_skill_names.append(entry.name)
        count += 1

    # Write manifest for next install's selective cleanup
    if new_skill_names:
        write_manifest(target_dir, new_skill_names)

    return count


def cleanup_legacy_namespace(target_dir: Path) -> bool:
    """Remove old skills/nw/ directory from previous hierarchical installs.

    Returns True if the directory was removed, False if it did not exist.
    """
    nw_dir = target_dir / "nw"
    if nw_dir.exists():
        shutil.rmtree(nw_dir)
        return True
    return False


def write_manifest(
    target_dir: Path,
    installed_names: list[str],
    *,
    key: str = SKILLS_FAMILY_KEY,
) -> None:
    """Write .nwave-manifest.json listing installed names under *key*.

    Whole-document replace — the original v1.0 single-family shape
    (``{key: sorted-names, "version": "1.0"}``) used by the skills family.
    Families SHARING a target directory use :func:`write_family_record`
    (merge semantics) instead.
    """
    _write_document(target_dir, {key: sorted(installed_names), "version": "1.0"})


def read_manifest(target_dir: Path) -> dict | None:
    """Read .nwave-manifest.json if it exists.

    Returns parsed manifest dict, or None if not found.
    """
    manifest_path = target_dir / _MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text())


def read_family_record(
    target_dir: Path,
    *,
    key: str,
    sibling_keys: frozenset[str] = frozenset(),
    adopt_legacy: bool = False,
) -> FamilyRecord:
    """Resolve one family's record from the shared manifest document.

    The family's tracked names come from its own *key*. When *adopt_legacy*
    is set (the family is the directory's v1.0-era lineage owner), list
    values under keys claimed by NO sibling family are adopted as the
    family's prior-version record and reported in ``superseded_keys`` so the
    next :func:`write_family_record` retires them — backward-compatible read
    of the v1.0 single-family shape.
    """
    list_values = _list_values(read_manifest(target_dir) or {})
    accounted = frozenset(name for value in list_values.values() for name in value)
    legacy_keys = (
        frozenset(
            name for name in list_values if name != key and name not in sibling_keys
        )
        if adopt_legacy
        else frozenset()
    )
    if key not in list_values and not legacy_keys:
        return FamilyRecord(
            tracked=None, superseded_keys=frozenset(), accounted=accounted
        )
    tracked = set(list_values.get(key, []))
    for legacy_key in legacy_keys:
        tracked.update(list_values[legacy_key])
    return FamilyRecord(
        tracked=frozenset(tracked), superseded_keys=legacy_keys, accounted=accounted
    )


def write_family_record(
    target_dir: Path,
    installed_names: list[str],
    *,
    key: str,
    superseded_keys: frozenset[str] = frozenset(),
) -> None:
    """Merge one family's record into the shared manifest document.

    Sibling families' keys are preserved verbatim; *superseded_keys* (legacy
    keys this family adopted via :func:`read_family_record`) are dropped.
    ONE manifest format per directory — never a second mechanism.
    """
    manifest = read_manifest(target_dir) or {}
    for superseded_key in superseded_keys:
        manifest.pop(superseded_key, None)
    manifest[key] = sorted(installed_names)
    manifest["version"] = "1.0"
    _write_document(target_dir, manifest)


def sweep_retired_assets(
    target_dir: Path, retired_names: frozenset[str]
) -> tuple[list[str], list[str]]:
    """Delete the named retired assets (files or folders) from *target_dir*.

    Only positively-identified names are ever passed here (manifest-driven
    sweep); names absent from disk are skipped. Returns
    ``(removed, blocked)`` where *blocked* lists read-only assets that
    could not be removed (caller warns, never crashes).
    """
    removed: list[str] = []
    blocked: list[str] = []
    for name in sorted(retired_names):
        path = target_dir / name
        if not path.exists():
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed.append(name)
        except PermissionError:
            blocked.append(name)
    return removed, blocked


def unaccounted_names(
    target_dir: Path,
    *,
    accounted: frozenset[str],
    expected: frozenset[str],
    scope_glob: str = "*",
) -> list[str]:
    """Names on disk that no record tracks and the current version won't ship.

    The preserve-by-default warn scope for a family's adoption (pre-record)
    run: anything here is preserved and the user is told about it.
    """
    return sorted(
        path.name
        for path in target_dir.glob(scope_glob)
        if path.name != _MANIFEST_FILENAME
        and path.name not in accounted
        and path.name not in expected
    )


def preserve_warning_message(
    target_dir: Path,
    unrecorded: list[str],
    *,
    family_label: str,
    item_label: str,
) -> str:
    """The preserve-by-default adoption warning, one shape for every family."""
    return (
        f"  ⚠️ No {family_label} found in {target_dir}: preserving "
        f"{len(unrecorded)} unrecorded {item_label}(s) ({', '.join(unrecorded)}); "
        f"a manifest will track this and future installs"
    )


def _list_values(manifest: dict) -> dict[str, frozenset[str]]:
    """The manifest's family records: every list-of-strings value, by key."""
    return {
        name: frozenset(item for item in value if isinstance(item, str))
        for name, value in manifest.items()
        if isinstance(value, list)
    }


def _write_document(target_dir: Path, manifest: dict) -> None:
    manifest_path = target_dir / _MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
