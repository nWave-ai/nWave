"""Plugin for installing nWave skills into OMP's native SKILL.md format.

OMP discovers skills at <config-root>/agent/skills/<name>/SKILL.md (one
level, non-recursive; native provider, highest priority). ``description``
frontmatter is REQUIRED for native discovery -- every nWave skill carries
one. Unknown frontmatter keys are preserved as opaque metadata by OMP's
conventional scanners, so the skill body is copied verbatim except for host
path rewrites; ``disable-model-invocation`` is honored natively.

Why the OMP-native route rather than the shared ``$HOME/.agents/skills``
tree (the "no second copy" question): that tree is owned by
CodexSkillsPlugin under a strict single-writer manifest that REFUSES
foreign ``nw-*`` directories, so a second writer there can neither install
nor uninstall safely. The shared-consumer reuse condition therefore fails,
and each host keeps its own manifest-owned copy.

Ownership is manifest-driven: only names recorded in this plugin's
``.nwave-manifest.json`` are ever replaced or pruned; a foreign or
user-created ``nw-*`` directory is refused as a collision, never adopted,
and non-``nw-`` entries (the user's own skills, including personal symlinks
such as ``personal-agent``) are outside this plugin's glob and untouched by
construction.
"""

import json
import shutil
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.omp_common import require_default_profile
from scripts.shared.agent_catalog import (
    build_ownership_map,
    detect_command_skills,
    load_private_skills,
    load_public_agents,
)
from scripts.shared.install_paths import omp_agent_dir, omp_skills_dir
from scripts.shared.skill_distribution import (
    enumerate_skills,
    filter_public_skills,
)
from scripts.shared.skill_path_rewrite import rewrite_host_paths


_MANIFEST_FILENAME = ".nwave-manifest.json"

#: Raised-shaped marker for ownership/foreign-collision refusals surfaced in
#: install output the same way the Codex plugin reports them.
_FOREIGN_COLLISION = "foreign or untracked OMP skill collision"


def _find_skills_source(context: InstallContext) -> Path | None:
    """Locate the skills source directory from dist or project layout."""
    dist_skills = context.framework_source / "skills" / "nw"
    if dist_skills.exists():
        return dist_skills

    project_skills = context.project_root / "nWave" / "skills"
    if project_skills.exists():
        return project_skills

    return None


def _read_manifest(target_dir: Path) -> dict | None:
    """Read the ownership manifest, or None when absent."""
    manifest_path = target_dir / _MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _read_owned_manifest_strict(target_dir: Path) -> set[str]:
    """Strictly read the ownership manifest before any mutation.

    A manifest name is an ownership claim only after its own shape is
    trusted (the same bar the Codex plugin applies): single known key set,
    version 1.0, safe basenames, unique.

    Raises:
        ValueError: The manifest exists but cannot be trusted.
    """
    manifest_path = target_dir / _MANIFEST_FILENAME
    if not (manifest_path.exists() or manifest_path.is_symlink()):
        return set()
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError(f"unsafe OMP skills manifest: {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable OMP skills manifest: {manifest_path}") from exc
    names = document.get("installed_skills") if isinstance(document, dict) else None
    safe = (
        isinstance(document, dict)
        and set(document) == {"installed_skills", "version"}
        and document.get("version") == "1.0"
        and isinstance(names, list)
        and all(
            isinstance(name, str) and bool(name) and Path(name).name == name
            for name in names
        )
        and len(names) == len(set(names))
    )
    if not safe:
        raise ValueError(f"untrusted OMP skills manifest: {manifest_path}")
    return set(names)


def _write_manifest(target_dir: Path, installed_skill_names: list[str]) -> None:
    """Write the ownership manifest listing this run's installed skills."""
    manifest = {
        "installed_skills": sorted(installed_skill_names),
        "version": "1.0",
    }
    manifest_path = target_dir / _MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _safe_owned_skill_dir(target_dir: Path, name: str) -> Path:
    """Validate a manifest-owned skill directory before replace/remove."""
    if not (name and Path(name).name == name):
        raise ValueError(f"unsafe OMP skill name: {name!r}")
    if target_dir.is_symlink() or not target_dir.is_dir():
        raise ValueError(f"unsafe OMP skills directory: {target_dir}")
    skill_dir = target_dir / name
    if skill_dir.parent != target_dir or skill_dir.is_symlink():
        raise ValueError(f"unsafe OMP skill directory: {skill_dir}")
    return skill_dir


class OmpSkillsPlugin(InstallationPlugin):
    """Plugin for installing nWave skills into OMP native format."""

    def __init__(self) -> None:
        super().__init__(name="omp-skills", priority=36)

    def install(self, context: InstallContext) -> PluginResult:
        """Install public skills from nWave/skills/ into OMP's native tree.

        Copies each public skill directory verbatim (OMP preserves unknown
        frontmatter keys), rewriting host paths in SKILL.md bodies. A
        manifest tracks installed names; a previous manifest's names are
        replaced clean-then-write, foreign ``nw-*`` directories are refused,
        and symlinks are never traversed or replaced.
        """
        try:
            require_default_profile()
        except ValueError as e:
            context.logger.error(f"  ❌ OMP skills install refused: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OMP skills installation refused: {e}",
                errors=[str(e)],
            )

        try:
            context.logger.info("  📦 Installing OMP skills...")

            skills_source = _find_skills_source(context)
            if skills_source is None:
                context.logger.info("  ⏭️ No skills directory found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No skills to install (source directory not found)",
                )

            public_agents = (
                set()
                if context.dev_mode
                else load_public_agents(context.project_root / "nWave")
            )
            agents_dir = context.project_root / "nWave" / "agents"
            ownership_map = (
                build_ownership_map(agents_dir) if agents_dir.exists() else {}
            )
            entries = enumerate_skills(skills_source)
            command_skills = (
                set() if context.dev_mode else detect_command_skills(skills_source)
            )
            # Real distribution MUST pass the catalog's private declaration:
            # a skill a public agent owns but the catalog declares private is
            # excluded no matter who lists it.
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

            desired_names = {entry.name for entry in entries}
            target_dir = omp_skills_dir()

            previous_owned = (
                _read_owned_manifest_strict(target_dir)
                if (target_dir.exists() or target_dir.is_symlink())
                else set()
            )

            # Foreign-collision preflight: an nw-* directory this install
            # does not own and will not write is refused, never adopted.
            if target_dir.exists() or target_dir.is_symlink():
                if target_dir.is_symlink() or not target_dir.is_dir():
                    raise ValueError(f"unsafe OMP skills directory: {target_dir}")
                for existing in sorted(target_dir.glob("nw-*")):
                    if (
                        existing.name in desired_names
                        or existing.name in previous_owned
                    ):
                        continue
                    raise ValueError(f"{_FOREIGN_COLLISION}: {existing}")

            stale_names = previous_owned - desired_names
            target_dir.mkdir(parents=True, exist_ok=True)

            # Stage EVERY replacement outside the discovery root before any
            # target mutation: a copy/rewrite failure leaves the previous
            # install fully intact (and the staging dir is a sibling of the
            # skills root, never a one-level `*/SKILL.md` discovery hit).
            # Only after every skill is staged do the owned trees swap in,
            # so a mid-loop failure can never strand half-written unowned
            # directories that a later run would misread as foreign.
            staging_root = omp_agent_dir() / ".nwave-skills-staging"
            if staging_root.is_symlink() or (
                staging_root.exists() and not staging_root.is_dir()
            ):
                raise ValueError(f"unsafe OMP staging directory: {staging_root}")
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
                    rewritten = rewrite_host_paths(content, "omp")
                    if rewritten != content:
                        target_file.write_text(rewritten, encoding="utf-8")

                # Swap phase: replace manifest-owned desired names, then
                # prune stale owned names.
                installed_names: list[str] = []
                installed_files: list[Path] = []
                for entry in entries:
                    skill_dir = _safe_owned_skill_dir(target_dir, entry.name)
                    if skill_dir.exists():
                        if entry.name not in previous_owned:
                            raise ValueError(f"{_FOREIGN_COLLISION}: {skill_dir}")
                        shutil.rmtree(skill_dir)
                    staged = staging_root / entry.name
                    staged.rename(skill_dir)
                    installed_names.append(entry.name)
                    installed_files.append(skill_dir / "SKILL.md")

                for name in sorted(stale_names):
                    shutil.rmtree(_safe_owned_skill_dir(target_dir, name))

                _write_manifest(target_dir, installed_names)
            finally:
                shutil.rmtree(staging_root, ignore_errors=True)

            context.logger.info(
                f"  ✅ OMP skills installed ({len(installed_names)} skills)"
            )
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(
                    f"OMP skills installed successfully ({len(installed_names)} skills)"
                ),
                installed_files=installed_files,
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to install OMP skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OMP skills installation failed: {e!s}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only manifest-owned OMP skills; everything else stays."""
        try:
            require_default_profile()
        except ValueError as e:
            context.logger.error(f"  ❌ OMP skills uninstall refused: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OMP skills uninstallation refused: {e}",
                errors=[str(e)],
            )

        try:
            context.logger.info("  🗑️ Uninstalling OMP skills...")
            target_dir = omp_skills_dir()
            manifest = _read_manifest(target_dir)
            if manifest is None:
                context.logger.info("  ⏭️ No OMP skills manifest found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No OMP skills to uninstall (no manifest found)",
                )

            names = manifest.get("installed_skills", [])
            removed = 0
            for name in names:
                if not (isinstance(name, str) and Path(name).name == name):
                    continue
                skill_dir = target_dir / name
                if skill_dir.is_symlink() or not skill_dir.is_dir():
                    continue
                shutil.rmtree(skill_dir)
                removed += 1

            manifest_path = target_dir / _MANIFEST_FILENAME
            if manifest_path.exists():
                manifest_path.unlink()

            context.logger.info(f"  🗑️ Removed {removed} OMP skills")
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"OMP skills uninstalled ({removed} removed)",
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to uninstall OMP skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OMP skills uninstallation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify manifest-listed OMP skill trees exist and are not symlinks."""
        try:
            context.logger.info("  🔍 Verifying OMP skills...")
            target_dir = omp_skills_dir()
            manifest = _read_manifest(target_dir)
            source = _find_skills_source(context)
            if manifest is None and source is None:
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No OMP skills configured (nothing to verify)",
                )
            if manifest is None:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="OMP skills manifest missing after install",
                    errors=[f"No {_MANIFEST_FILENAME} under {target_dir}"],
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
                    plugin_name=self.name,
                    message=f"OMP skills verification failed ({len(missing)} missing)",
                    errors=[f"missing or invalid: {', '.join(missing)}"],
                )
            count = len(manifest.get("installed_skills", []))
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"OMP skills verified ({count} present)",
            )
        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OMP skills verification failed: {e!s}",
                errors=[str(e)],
            )
