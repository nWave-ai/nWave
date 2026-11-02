"""Project the canonical task command roster onto OMP's native slash-command port."""

import json
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.omp_agents_plugin import (
    _read_owned_manifest_strict,
)
from scripts.install.plugins.omp_common import (
    require_default_profile,
    translate_skill_invocations,
)
from scripts.install.plugins.opencode_commands_plugin import _find_commands_source
from scripts.install.plugins.opencode_common import (
    ManifestPluginConfig,
    parse_frontmatter,
    remove_manifest_owned_assets,
    render_frontmatter,
    uninstall_with_manifest,
    verify_with_manifest,
)
from scripts.shared.agent_catalog import load_public_commands
from scripts.shared.install_paths import (
    PYTHON_CMD_SUBSTITUTION,
    omp_skills_dir,
    resolve_python_command,
)
from scripts.shared.skill_path_rewrite import rewrite_host_paths


_MANIFEST = ".nwave-commands-manifest.json"


def omp_commands_dir() -> Path:
    return omp_skills_dir().parent / "commands"


def command_sources(context: InstallContext) -> list[Path]:
    source = _find_commands_source(context)
    if source is None:
        raise ValueError(
            "Task command roster missing; reinstall from a complete nWave distribution."
        )
    public_commands = (
        set()
        if context.dev_mode
        else load_public_commands(context.project_root / "nWave")
    )
    return [
        path
        for path in sorted(source.glob("*.md"))
        if context.dev_mode or path.stem in public_commands
    ]


class OmpCommandsPlugin(InstallationPlugin):
    def __init__(self):
        super().__init__("omp-commands", priority=38)
        self.dependencies = ["omp-skills"]

    def install(self, context: InstallContext) -> PluginResult:
        try:
            require_default_profile()
            target = omp_commands_dir()
            rendered = {}
            for source in command_sources(context):
                name = f"nw-{source.stem}"
                frontmatter, body = parse_frontmatter(
                    source.read_text(encoding="utf-8")
                )
                metadata = {
                    key: frontmatter[key]
                    for key in ("description", "argument-hint")
                    if key in frontmatter
                }
                body = translate_skill_invocations(rewrite_host_paths(body, "omp"))
                rendered[name] = (render_frontmatter(metadata) + body).replace(
                    PYTHON_CMD_SUBSTITUTION, resolve_python_command()
                )
            if target.is_symlink() or (target.exists() and not target.is_dir()):
                raise ValueError(
                    f"Unsafe OMP command directory: {target}; remove the symlink and rerun install."
                )
            owned = _read_owned_manifest_strict(
                target, manifest_filename=_MANIFEST, installed_key="installed_commands"
            )
            for name in rendered:
                path = target / f"{name}.md"
                if path.is_symlink() or (path.exists() and name not in owned):
                    raise ValueError(
                        f"OMP command collision: {path}; back up the foreign file, remove it and rerun install."
                    )
            installed = [target / f"{name}.md" for name in rendered]
            if not context.dry_run:
                target.mkdir(parents=True, exist_ok=True)
                remove_manifest_owned_assets(
                    target, _MANIFEST, ".md", manifest_key="installed_commands"
                )
                for name, content in rendered.items():
                    (target / f"{name}.md").write_text(content, encoding="utf-8")
                (target / _MANIFEST).write_text(
                    json.dumps(
                        {"installed_commands": sorted(rendered), "version": "1.0"},
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            message = f"{'Would install' if context.dry_run else 'Installed'} {len(rendered)} OMP commands to {target}"
            context.logger.info(message)
            return PluginResult(True, self.name, message, installed_files=installed)
        except (OSError, ValueError, RuntimeError) as error:
            return PluginResult(
                False,
                self.name,
                f"OMP commands installation refused: {error}. "
                "HOW: restore the nWave manifest or back up/remove the conflicting file, then rerun install.",
                errors=[str(error)],
            )

    def _config(self) -> ManifestPluginConfig:
        return ManifestPluginConfig(
            self.name,
            omp_commands_dir(),
            _MANIFEST,
            "commands",
            "installed_commands",
            host_name="OMP",
        )

    def verify(self, context: InstallContext) -> PluginResult:
        return verify_with_manifest(context, self._config(), _find_commands_source)

    def uninstall(self, context: InstallContext) -> PluginResult:
        return uninstall_with_manifest(context, self._config())
