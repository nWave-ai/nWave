"""The manifest-owned skill folder policy: nWave's public skills installed as one folder per skill.

A host that reads skills as ``<skills root>/<name>/SKILL.md`` installs them through this policy. Ownership is
manifest-driven: only names recorded in the plugin's ``.nwave-manifest.json`` are ever replaced or pruned; a foreign
or user-created ``nw-*`` directory is refused as a collision, never adopted; non-``nw-`` entries are outside its glob
and untouched by construction. Symlinks are never traversed or replaced.

Each host plugin supplies its skills root, the host key of its path rewrite, its plugin name and the label its messages
name. The Devin and Copilot skills plugins are the callers. The Devin names and messages are the ones it wrote before
this module existed; the existing Devin tests pin them.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from scripts.install.plugins.base import InstallContext, PluginResult
from scripts.shared.agent_catalog import (
    build_ownership_map,
    detect_command_skills,
    load_private_skills,
    load_public_agents,
)
from scripts.shared.express_command_skill import express_skill_entry
from scripts.shared.skill_distribution import enumerate_skills, filter_public_skills
from scripts.shared.skill_path_rewrite import rewrite_host_paths


MANIFEST_FILENAME = ".nwave-manifest.json"


def find_skills_source(context: InstallContext) -> Path | None:
    """Locate the skills source directory from dist or project layout."""
    dist_skills = context.framework_source / "skills" / "nw"
    if dist_skills.exists():
        return dist_skills

    project_skills = context.project_root / "nWave" / "skills"
    if project_skills.exists():
        return project_skills

    return None


def read_manifest(target_dir: Path) -> dict | None:
    """Read the ownership manifest, or None when absent."""
    manifest_path = target_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def read_owned_manifest_strict(target_dir: Path, label: str) -> set[str]:
    """Strictly read the ownership manifest before any mutation.

    A manifest name is an ownership claim only after its own shape is
    trusted: single known key set, version 1.0, safe basenames, unique.

    Raises:
        ValueError: The manifest exists but cannot be trusted.
    """
    manifest_path = target_dir / MANIFEST_FILENAME
    if not (manifest_path.exists() or manifest_path.is_symlink()):
        return set()
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError(f"unsafe {label} skills manifest: {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"unreadable {label} skills manifest: {manifest_path}"
        ) from exc
    names = document.get("installed_skills") if isinstance(document, dict) else None
    safe = (
        isinstance(document, dict)
        and set(document) == {"installed_skills", "version"}
        and document.get("version") == "1.0"
        and isinstance(names, list)
        and all(is_plain_skill_name(name) for name in names)
        and len(names) == len(set(names))
    )
    if not safe:
        raise ValueError(f"untrusted {label} skills manifest: {manifest_path}")
    return set(names)


def write_manifest(target_dir: Path, installed_skill_names: list[str]) -> None:
    """Write the ownership manifest listing this run's installed skills."""
    manifest = {
        "installed_skills": sorted(installed_skill_names),
        "version": "1.0",
    }
    manifest_path = target_dir / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def is_plain_skill_name(name: object) -> bool:
    """True for one path segment that names a child, never '.' or '..'."""
    return (
        isinstance(name, str)
        and name not in {"", ".", ".."}
        and Path(name).name == name
    )


def safe_owned_skill_dir(target_dir: Path, name: str, label: str) -> Path:
    """Validate a manifest-owned skill directory before replace/remove."""
    if not is_plain_skill_name(name):
        raise ValueError(f"unsafe {label} skill name: {name!r}")
    if target_dir.is_symlink() or not target_dir.is_dir():
        raise ValueError(f"unsafe {label} skills directory: {target_dir}")
    skill_dir = target_dir / name
    if skill_dir.parent != target_dir or skill_dir.is_symlink():
        raise ValueError(f"unsafe {label} skill directory: {skill_dir}")
    return skill_dir


def _collision(label: str, path: Path) -> str:
    """The refusal of a foreign or untracked skill folder: the phrase the Devin tests pin, with what, why and how."""
    return (
        f"WHAT: foreign or untracked {label} skill collision: {path}. "
        "WHY: nWave replaces only the skill folders its manifest lists, so a folder it did not write is never "
        f"overwritten. HOW: rename or move {path}, then run the installer again."
    )


def preflight_foreign_names(
    target_dir: Path, previous_owned: set[str], label: str
) -> None:
    """Refuse every nw-* folder the manifest does not own, before any folder is replaced.

    A folder this install would write is refused too: refusing it at the swap, after earlier folders were replaced,
    would leave a partial install behind a refusal.

    Raises:
        ValueError: A foreign or untracked nw-* folder is in the way.
    """
    for existing in sorted(target_dir.glob("nw-*")):
        if existing.name in previous_owned:
            continue
        raise ValueError(_collision(label, existing))


def install_public_skill_folders(
    context: InstallContext,
    target_dir: Path,
    *,
    plugin_name: str,
    host: str,
    label: str,
) -> PluginResult:
    """Install public skills from nWave/skills/ as one folder per skill under target_dir.

    Copies each public skill directory verbatim (the host keeps unknown frontmatter keys), rewriting the host's paths in
    SKILL.md bodies. A manifest tracks installed names; previous manifest names are replaced clean-then-write, foreign
    ``nw-*`` directories are refused, and symlinks are never traversed or replaced.
    """
    dynamic_staging: Path | None = None
    try:
        context.logger.info(f"  📦 Installing {label} skills...")

        skills_source = find_skills_source(context)
        if skills_source is None:
            context.logger.info("  ⏭️ No skills directory found, skipping")
            return PluginResult(
                success=True,
                plugin_name=plugin_name,
                message="No skills to install (source directory not found)",
            )

        public_agents = (
            set()
            if context.dev_mode
            else load_public_agents(context.project_root / "nWave")
        )
        agents_dir = context.project_root / "nWave" / "agents"
        ownership_map = build_ownership_map(agents_dir) if agents_dir.exists() else {}
        entries = enumerate_skills(skills_source)
        command_skills = (
            set() if context.dev_mode else detect_command_skills(skills_source)
        )
        private_skills = (
            set()
            if context.dev_mode
            else load_private_skills(context.project_root / "nWave")
        )
        entries = filter_public_skills(
            entries,
            public_agents,
            ownership_map,
            command_skills,
            private_skills,
        )
        # The dynamic command skill is rendered from its one source, staged in
        # a temporary directory that the finally removes even on failure.
        dynamic_staging = Path(tempfile.mkdtemp(prefix="nwave-dynamic-skill-"))
        dynamic_entry = express_skill_entry(
            context.project_root / "nWave", dynamic_staging
        )
        if dynamic_entry is not None:
            entries.append(dynamic_entry)

        desired_names = {entry.name for entry in entries}
        previous_owned = (
            read_owned_manifest_strict(target_dir, label)
            if (target_dir.exists() or target_dir.is_symlink())
            else set()
        )

        # Foreign-collision preflight: an nw-* directory this install
        # does not own and will not write is refused, never adopted.
        if target_dir.exists() or target_dir.is_symlink():
            if target_dir.is_symlink() or not target_dir.is_dir():
                raise ValueError(f"unsafe {label} skills directory: {target_dir}")
            preflight_foreign_names(target_dir, previous_owned, label)

        stale_names = previous_owned - desired_names
        target_dir.mkdir(parents=True, exist_ok=True)

        # Stage every replacement outside the discovery root before any
        # target mutation: a copy/rewrite failure leaves the previous
        # install fully intact.
        staging_root = target_dir.parent / ".nwave-skills-staging"
        if staging_root.is_symlink() or (
            staging_root.exists() and not staging_root.is_dir()
        ):
            raise ValueError(f"unsafe {label} staging directory: {staging_root}")
        shutil.rmtree(staging_root, ignore_errors=True)
        staging_root.mkdir(parents=True)
        try:
            for entry in entries:
                staged = staging_root / entry.name
                if entry.source_path.is_dir():
                    shutil.copytree(entry.source_path, staged, symlinks=False)
                    target_file = staged / "SKILL.md"
                else:
                    staged.mkdir(parents=True)
                    target_file = staged / "SKILL.md"
                    shutil.copy2(entry.source_path, target_file)

                content = target_file.read_text(encoding="utf-8")
                rewritten = rewrite_host_paths(content, host)
                if rewritten != content:
                    target_file.write_text(rewritten, encoding="utf-8")

            # Swap phase: replace manifest-owned desired names, then
            # prune stale owned names.
            installed_names: list[str] = []
            installed_files: list[Path] = []
            for entry in entries:
                skill_dir = safe_owned_skill_dir(target_dir, entry.name, label)
                if skill_dir.exists():
                    if entry.name not in previous_owned:
                        raise ValueError(_collision(label, skill_dir))
                    shutil.rmtree(skill_dir)
                staged = staging_root / entry.name
                staged.rename(skill_dir)
                installed_names.append(entry.name)
                installed_files.append(skill_dir / "SKILL.md")

            for name in sorted(stale_names):
                shutil.rmtree(safe_owned_skill_dir(target_dir, name, label))

            write_manifest(target_dir, installed_names)
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

        context.logger.info(
            f"  ✅ {label} skills installed ({len(installed_names)} skills)"
        )
        return PluginResult(
            success=True,
            plugin_name=plugin_name,
            message=(
                f"{label} skills installed successfully ({len(installed_names)} skills)"
            ),
            installed_files=installed_files,
        )
    except Exception as e:
        context.logger.error(f"  ❌ Failed to install {label} skills: {e}")
        return PluginResult(
            success=False,
            plugin_name=plugin_name,
            message=f"{label} skills installation failed: {e!s}",
            errors=[str(e)],
        )
    finally:
        if dynamic_staging is not None:
            shutil.rmtree(dynamic_staging, ignore_errors=True)


def uninstall_public_skill_folders(
    context: InstallContext, target_dir: Path, *, plugin_name: str, label: str
) -> PluginResult:
    """Uninstall only manifest-owned skills; everything else stays."""
    try:
        context.logger.info(f"  🗑️ Uninstalling {label} skills...")
        manifest_path = target_dir / MANIFEST_FILENAME
        if not (manifest_path.exists() or manifest_path.is_symlink()):
            context.logger.info(f"  ⏭️ No {label} skills manifest found, skipping")
            return PluginResult(
                success=True,
                plugin_name=plugin_name,
                message=f"No {label} skills to uninstall (no manifest found)",
            )

        names = read_owned_manifest_strict(target_dir, label)
        removed = 0
        for name in sorted(names):
            skill_dir = safe_owned_skill_dir(target_dir, name, label)
            if not skill_dir.is_dir():
                continue
            shutil.rmtree(skill_dir)
            removed += 1

        if manifest_path.exists():
            manifest_path.unlink()

        context.logger.info(f"  🗑️ Removed {removed} {label} skills")
        return PluginResult(
            success=True,
            plugin_name=plugin_name,
            message=f"{label} skills uninstalled ({removed} removed)",
        )
    except Exception as e:
        context.logger.error(f"  ❌ Failed to uninstall {label} skills: {e}")
        return PluginResult(
            success=False,
            plugin_name=plugin_name,
            message=f"{label} skills uninstallation failed: {e!s}",
            errors=[str(e)],
        )


def verify_public_skill_folders(
    context: InstallContext, target_dir: Path, *, plugin_name: str, label: str
) -> PluginResult:
    """Verify manifest-listed skill trees exist and are not symlinks."""
    try:
        context.logger.info(f"  🔍 Verifying {label} skills...")
        manifest = read_manifest(target_dir)
        source = find_skills_source(context)
        if manifest is None and source is None:
            return PluginResult(
                success=True,
                plugin_name=plugin_name,
                message=f"No {label} skills configured (nothing to verify)",
            )
        if manifest is None:
            return PluginResult(
                success=False,
                plugin_name=plugin_name,
                message=f"{label} skills manifest missing after install",
                errors=[f"No {MANIFEST_FILENAME} under {target_dir}"],
            )
        missing = []
        for name in manifest.get("installed_skills", []):
            skill_dir = target_dir / str(name)
            skill_file = skill_dir / "SKILL.md"
            if skill_dir.is_symlink() or skill_file.is_symlink():
                missing.append(f"{name} (symlink)")
            elif not skill_file.is_file():
                missing.append(name)
        if missing:
            return PluginResult(
                success=False,
                plugin_name=plugin_name,
                message=f"{label} skills verification failed ({len(missing)} missing)",
                errors=[f"missing or invalid: {', '.join(missing)}"],
            )
        count = len(manifest.get("installed_skills", []))
        context.logger.info(f"  ✅ Verified {count} {label} skills")
        return PluginResult(
            success=True,
            plugin_name=plugin_name,
            message=f"{label} skills verified ({count} present)",
        )
    except Exception as e:
        return PluginResult(
            success=False,
            plugin_name=plugin_name,
            message=f"{label} skills verification failed: {e!s}",
            errors=[str(e)],
        )
