"""Plugin for installing nWave agents into OMP's native task-agent format.

OMP discovers task agents at <config-root>/agent/agents/*.md: YAML
frontmatter (required non-empty ``name``/``description``, body as the
system prompt) plus optional ``tools`` (lowercase builtin names),
``autoloadSkills``, and ``output`` (opaque structured-reply schema). Raw
Claude/Codex agent directories are intentionally NOT read by OMP, so this
plugin is the only way nWave roles become OMP task agents.

Projection (see omp_common for the laws):
- ``model`` is OMITTED: every nWave declaration is a Claude alias, which OMP
  would treat as a literal selector and route away from the user's
  configured model. Omission inherits the parent session's active model.
- ``tools`` map to OMP's canonical lowercase builtins; scoped grants and
  unmapped names are OMITTED and reported, never widened.
- ``StructuredOutput`` is a reply channel: excluded from ``tools``, carried
  as an ``output`` schema projected from the canonical model envelope.
- Examiner and product-owner roles record through the nwdes CLI with Bash,
  not through a structured reply schema.
- ``skills`` become ``autoloadSkills`` naming only PUBLIC installed skills,
  so each skill is delivered once through OMP's native autoload; bodies are
  NOT inlined.
- ``maxTurns`` is omitted (no OMP equivalent) and reported.
- ``Invoke Skill(X)`` directives become ``Read skill://X/SKILL.md``.

This plugin owns agents only; OmpDESPlugin owns the separate host extension.
Ownership is manifest-driven (``.nwave-agents-manifest.json``); foreign
``nw-*`` files and symlinks in owned paths are refused, never adopted.
Non-``nw-`` entries are outside this plugin's glob and untouched.
"""

import json
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.omp_common import (
    missing_preload_skills,
    project_agent_content,
    require_default_profile,
)
from scripts.install.plugins.opencode_common import parse_frontmatter
from scripts.shared.agent_catalog import is_public_agent, load_public_agents
from scripts.shared.install_paths import omp_agents_dir
from scripts.shared.skill_distribution import (
    enumerate_skills,
    filter_public_skills,
)
from scripts.shared.skill_path_rewrite import rewrite_host_paths


_MANIFEST_FILENAME = ".nwave-agents-manifest.json"
_FOREIGN_COLLISION = "foreign or untracked OMP agent collision"


def _find_agents_source(context: InstallContext) -> Path | None:
    """Locate the agents source directory from dist or project layout."""
    dist_agents = context.framework_source / "agents"
    if dist_agents.exists():
        return dist_agents

    project_agents = context.project_root / "nWave" / "agents"
    if project_agents.exists():
        return project_agents

    return None


def _installed_public_skills(context: InstallContext) -> frozenset[str]:
    """The skill names the OMP skills plugin installs (public catalog only).

    ``autoloadSkills`` may only name skills OMP will actually discover; the
    desired set of the skills plugin is exactly that population. When no
    skills source resolves, no preload name can be verified as discovered,
    so every preload name is excluded (and reported) rather than guessed.
    """
    from scripts.install.plugins.omp_skills_plugin import _find_skills_source

    public_agents = (
        set()
        if context.dev_mode
        else load_public_agents(context.project_root / "nWave")
    )
    skills_source = _find_skills_source(context)
    if skills_source is None:
        return frozenset()
    from scripts.shared.agent_catalog import (
        build_ownership_map,
        detect_command_skills,
        load_private_skills,
    )

    agents_dir = context.project_root / "nWave" / "agents"
    ownership_map = build_ownership_map(agents_dir) if agents_dir.exists() else {}
    entries = enumerate_skills(skills_source)
    command_skills = set() if context.dev_mode else detect_command_skills(skills_source)
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
    return frozenset(entry.name for entry in entries)


def _read_manifest(target_dir: Path) -> dict | None:
    """Read the ownership manifest, or None when absent.

    Lenient compatibility reader for uninstall/verify: a missing or
    malformed manifest means "nothing provably owned", never a crash.
    """
    manifest_path = target_dir / _MANIFEST_FILENAME
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
    return None


def _read_owned_manifest_strict(
    target_dir: Path,
    *,
    manifest_filename: str = _MANIFEST_FILENAME,
    installed_key: str = "installed_agents",
) -> set[str]:
    """Strictly read the ownership manifest before any mutation.

    Same trust bar as the skills plugin: the manifest file must be a regular
    non-symlink file, carry exactly {installed_key, version: "1.0"}, and
    list unique safe basenames. A name is an ownership claim only after its
    own shape is trusted.

    Raises:
        ValueError: The manifest exists but cannot be trusted.
    """
    manifest_path = target_dir / manifest_filename
    noun = installed_key.removeprefix("installed_")
    if not (manifest_path.exists() or manifest_path.is_symlink()):
        return set()
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError(f"unsafe OMP {noun} manifest: {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable OMP {noun} manifest: {manifest_path}") from exc
    names = document.get(installed_key) if isinstance(document, dict) else None
    trusted = (
        isinstance(document, dict)
        and set(document) == {installed_key, "version"}
        and document.get("version") == "1.0"
        and isinstance(names, list)
        and all(
            isinstance(name, str) and bool(name) and Path(name).name == name
            for name in names
        )
        and len(names) == len(set(names))
    )
    if not trusted:
        raise ValueError(f"untrusted OMP {noun} manifest: {manifest_path}")
    return set(names)


def _write_manifest(target_dir: Path, installed_agent_names: list[str]) -> None:
    """Write the ownership manifest listing this run's installed agents."""
    manifest = {
        "installed_agents": sorted(installed_agent_names),
        "version": "1.0",
    }
    manifest_path = target_dir / _MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


class OmpAgentsPlugin(InstallationPlugin):
    """Plugin for installing nWave agents into OMP native format."""

    def __init__(self) -> None:
        super().__init__(name="omp-agents", priority=37)

    def install(self, context: InstallContext) -> PluginResult:
        """Install public agents from nWave/agents/ as OMP task agents.

        Transforms each source role (frontmatter projection + body skill
        invocation rewrite), writes manifest-owned files clean-then-write,
        refuses foreign ``nw-*`` collisions and symlinks, and reports every
        capability that could not be projected (scoped tools, unmapped
        tools, absent maxTurns, excluded preload skills, envelope ceiling).
        """
        try:
            require_default_profile()
        except ValueError as e:
            context.logger.error(f"  ❌ OMP agents install refused: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OMP agents installation refused: {e}",
                errors=[str(e)],
            )

        try:
            context.logger.info("  📦 Installing OMP agents...")

            agents_source = _find_agents_source(context)
            if agents_source is None:
                context.logger.info("  ⏭️ No agents directory found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No agents to install (source directory not found)",
                )

            installed_public_skills = _installed_public_skills(context)
            target_dir = omp_agents_dir()
            previous_owned: set[str] = set()
            if target_dir.exists() or target_dir.is_symlink():
                if target_dir.is_symlink() or not target_dir.is_dir():
                    raise ValueError(f"unsafe OMP agents directory: {target_dir}")
                previous_owned = _read_owned_manifest_strict(target_dir)
                for existing in sorted(target_dir.glob("nw-*.md")):
                    # Manifest names are file stems (nw-*.md without .md),
                    # matching what install() records below.
                    if existing.name.removesuffix(".md") in previous_owned:
                        continue
                    if existing.is_symlink():
                        raise ValueError(f"{_FOREIGN_COLLISION} (symlink): {existing}")
                    raise ValueError(f"{_FOREIGN_COLLISION}: {existing}")

            public_agents = (
                set()
                if context.dev_mode
                else load_public_agents(context.project_root / "nWave")
            )
            agent_files = sorted(agents_source.glob("nw-*.md"))
            desired = [f for f in agent_files if is_public_agent(f.name, public_agents)]

            # Render EVERYTHING before touching the target: a transform
            # failure must leave the previous install fully intact, not a
            # half-written roster whose unmanifested files would read as
            # foreign collisions on the next run.
            rendered: list[tuple[str, str, list[str]]] = []
            all_reports: list[str] = []
            missing_by_role: dict[str, list[str]] = {}
            for source_file in desired:
                agent_name = source_file.stem
                content = source_file.read_text(encoding="utf-8")
                frontmatter, _raw_body = parse_frontmatter(content)
                role_missing = missing_preload_skills(
                    frontmatter, installed_public_skills
                )
                if role_missing:
                    # Mandatory frontmatter skills are REQUIRED knowledge
                    # (builder/source policy). A public role whose declared
                    # preload the public tree does not carry is refused for
                    # the WHOLE run -- never installed partially-successful
                    # with a warning. Aggregated across all roles so one
                    # refusal names every deficiency.
                    missing_by_role[agent_name] = role_missing
                    continue
                transformed, reports = project_agent_content(
                    content, installed_public_skills=installed_public_skills
                )
                # Host path rewrites apply to the whole projected file: the
                # frontmatter is projection-native, the body carries the
                # canonical ~/.claude tokens.
                frontmatter_end = transformed.find("\n---", 3)
                if transformed.startswith("---") and frontmatter_end != -1:
                    body = transformed[frontmatter_end + 4 :]
                    body = rewrite_host_paths(body, "omp")
                    transformed = transformed[: frontmatter_end + 4] + body
                rendered.append((agent_name, transformed, reports))
                all_reports.extend(reports)

            if missing_by_role:
                detail = "; ".join(
                    f"{role} missing {', '.join(skills)}"
                    for role, skills in sorted(missing_by_role.items())
                )
                raise ValueError(
                    "OMP role projection refused: mandatory frontmatter "
                    f"skills are required knowledge and the public install "
                    f"does not carry them ({detail}). Nothing was written; "
                    "private knowledge is never copied to close the gap."
                )

            target_dir.mkdir(parents=True, exist_ok=True)

            installed_names: list[str] = []
            installed_files: list[Path] = []
            for agent_name, transformed, _reports in rendered:
                target_file = target_dir / f"{agent_name}.md"
                if target_file.exists() or target_file.is_symlink():
                    if agent_name not in previous_owned:
                        raise ValueError(f"{_FOREIGN_COLLISION}: {target_file}")
                    if target_file.is_symlink():
                        raise ValueError(
                            f"refusing to replace symlinked OMP agent: {target_file}"
                        )
                    target_file.unlink()
                target_file.write_text(transformed, encoding="utf-8")

                installed_names.append(agent_name)
                installed_files.append(target_file)

            # Prune stale manifest-owned agents after every desired file
            # rendered successfully.
            desired_names = {f.stem for f in desired}
            for stale in sorted(previous_owned - desired_names):
                stale_file = target_dir / f"{stale}.md"
                if stale_file.is_symlink() or not stale_file.is_file():
                    raise ValueError(f"unsafe stale OMP agent file: {stale_file}")
                stale_file.unlink()

            _write_manifest(target_dir, installed_names)

            for report in all_reports:
                context.logger.info(f"  ⚠️ {report}")

            context.logger.info(
                f"  ✅ OMP agents installed ({len(installed_names)} agents)"
            )
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(
                    f"OMP agents installed successfully ({len(installed_names)} agents)"
                ),
                installed_files=installed_files,
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to install OMP agents: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OMP agents installation failed: {e!s}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only manifest-owned OMP agents; user files stay."""
        try:
            require_default_profile()
        except ValueError as e:
            context.logger.error(f"  ❌ OMP agents uninstall refused: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OMP agents uninstallation refused: {e}",
                errors=[str(e)],
            )

        try:
            context.logger.info("  🗑️ Uninstalling OMP agents...")
            target_dir = omp_agents_dir()
            manifest = _read_manifest(target_dir)
            if manifest is None:
                context.logger.info("  ⏭️ No OMP agents manifest found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No OMP agents to uninstall (no manifest found)",
                )

            names = manifest.get("installed_agents", [])
            removed = 0
            for name in names:
                if not (isinstance(name, str) and Path(name).name == name):
                    continue
                agent_file = target_dir / f"{name}.md"
                if agent_file.is_symlink() or not agent_file.is_file():
                    continue
                agent_file.unlink()
                removed += 1

            manifest_path = target_dir / _MANIFEST_FILENAME
            if manifest_path.exists():
                manifest_path.unlink()

            context.logger.info(f"  🗑️ Removed {removed} OMP agents")
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"OMP agents uninstalled ({removed} removed)",
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to uninstall OMP agents: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OMP agents uninstallation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify manifest-listed OMP agent files exist and are not symlinks."""
        try:
            context.logger.info("  🔍 Verifying OMP agents...")
            target_dir = omp_agents_dir()
            manifest = _read_manifest(target_dir)
            source = _find_agents_source(context)
            if manifest is None and source is None:
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No OMP agents configured (nothing to verify)",
                )
            if manifest is None:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="OMP agents manifest missing after install",
                    errors=[f"No {_MANIFEST_FILENAME} under {target_dir}"],
                )
            missing = []
            for name in manifest.get("installed_agents", []):
                agent_file = target_dir / f"{name}.md"
                if agent_file.is_symlink():
                    missing.append(f"{name} (symlink)")
                elif not agent_file.is_file():
                    missing.append(name)
            if missing:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=f"OMP agents verification failed ({len(missing)} missing)",
                    errors=[f"missing or invalid: {', '.join(missing)}"],
                )
            count = len(manifest.get("installed_agents", []))
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"OMP agents verified ({count} present)",
            )
        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OMP agents verification failed: {e!s}",
                errors=[str(e)],
            )
