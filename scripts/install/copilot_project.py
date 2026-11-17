"""The project-level Copilot install: nWave's public roles, skills and prompts in a project's .github folders (card t-0515).

``nwave-ai project copilot enable --yes`` writes the public roles to ``.github/agents``, the public skills to
``.github/skills`` and one prompt file per wave entry point to ``.github/prompts``. ``disable`` removes only what the
three manifests list. The writers are the personal install's own (copilot_agents_plugin and public_skill_folders), so
both installs select and write the same files; the prompt text is copilot_common.convert_wave.

Consent is a value: enable takes a ProjectConsent, which only the command line builds from the --yes flag, so a write
cannot run without the user's choice. Every prompt text is converted and every target folder is checked for foreign
files before any file is written, so a refusal leaves the project as it was.

The install reports what it did not check: whether the Copilot CLI lists or loads these files needs a real session.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.install.install_utils import Logger
from scripts.install.plugins.base import InstallContext, PluginResult
from scripts.install.plugins.copilot_agents_plugin import (
    AGENT_MANIFEST_FILENAME,
    AGENT_SUFFIX,
    agent_collision,
    find_agents_source,
    install_public_agents,
    public_agent_sources,
)
from scripts.install.plugins.copilot_common import NOT_CHECKED, convert_wave
from scripts.install.plugins.opencode_common import (
    read_manifest,
    remove_manifest_owned_assets,
)
from scripts.install.plugins.public_skill_folders import (
    MANIFEST_FILENAME as SKILL_MANIFEST_FILENAME,
)
from scripts.install.plugins.public_skill_folders import (
    install_public_skill_folders,
    preflight_foreign_names,
    read_owned_manifest_strict,
    uninstall_public_skill_folders,
)


if TYPE_CHECKING:
    from pathlib import Path

PLUGIN_NAME = "copilot-project"
PROMPTS_MANIFEST_FILENAME = ".nwave-prompts-manifest.json"
PROMPT_SUFFIX = ".prompt.md"
PROMPTS_KEY = "installed_prompts"
_LABEL = "Copilot"

USAGE = (
    "Usage: nwave-ai project copilot enable --yes\n"
    "       nwave-ai project copilot disable\n"
    "  enable --yes  write nWave's public roles, skills and prompts into this project's .github folders\n"
    "  disable       remove only the files nWave wrote there"
)


@dataclass(frozen=True)
class ProjectConsent:
    """The user's choice to write nWave's files into the project. Only the command line builds it, from --yes."""


def _fail(message: str, logger: Logger) -> PluginResult:
    logger.error(f"  ❌ {message}")
    return PluginResult(
        success=False, plugin_name=PLUGIN_NAME, message=message, errors=[message]
    )


def _consent_refusal() -> str:
    return (
        "WHAT: nWave's Copilot files were not written into this project. "
        "WHY: writing the project's .github folders is a choice, so enable needs the consent flag --yes. "
        "HOW: run nwave-ai project copilot enable --yes in this project."
    )


def _prompt_refusal(target: Path) -> str:
    return (
        f"WHAT: {target} is a file nWave did not write, so the Copilot prompts are not written into this project. "
        "WHY: nWave replaces only the prompts its manifest lists, so a user's file of the same name is never overwritten. "
        f"HOW: rename or move {target}, then run nwave-ai project copilot enable --yes again."
    )


def _context(framework_root: Path, logger: Logger) -> InstallContext:
    return InstallContext(
        claude_dir=framework_root,
        scripts_dir=framework_root / "scripts",
        templates_dir=framework_root / "nWave" / "templates",
        logger=logger,
        project_root=framework_root,
        framework_source=framework_root,
    )


def _wave_sources(framework_root: Path) -> list[Path]:
    """Every wave entry point: nWave/tasks/nw/<wave>.md, one prompt file each."""
    return sorted((framework_root / "nWave" / "tasks" / "nw").glob("*.md"))


def _prompt_name(wave: Path) -> str:
    return f"nw-{wave.stem}{PROMPT_SUFFIX}"


def _previous_prompts(prompts_dir: Path) -> set[str]:
    if not prompts_dir.exists():
        return set()
    previous = read_manifest(prompts_dir, PROMPTS_MANIFEST_FILENAME)
    return set(previous.get(PROMPTS_KEY, [])) if previous else set()


def _prompt_collision(prompts_dir: Path, waves: list[Path]) -> str | None:
    previously_written = _previous_prompts(prompts_dir)
    for wave in waves:
        target = prompts_dir / _prompt_name(wave)
        if (
            target.exists()
            and _prompt_name(wave).removesuffix(PROMPT_SUFFIX) not in previously_written
        ):
            return _prompt_refusal(target)
    return None


def _write_prompts(prompts_dir: Path, texts: dict[str, str]) -> list[Path]:
    """Replace the prompts the manifest lists, write the new ones and record them in the manifest."""
    prompts_dir.mkdir(parents=True, exist_ok=True)
    remove_manifest_owned_assets(
        prompts_dir,
        PROMPTS_MANIFEST_FILENAME,
        PROMPT_SUFFIX,
        manifest_key=PROMPTS_KEY,
    )
    written: list[Path] = []
    for name, text in sorted(texts.items()):
        target = prompts_dir / name
        target.write_text(text, encoding="utf-8")
        written.append(target)
    stems = [name.removesuffix(PROMPT_SUFFIX) for name in texts]
    manifest = {"installed_prompts": sorted(stems), "version": "1.0"}
    (prompts_dir / PROMPTS_MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return written


def enable_project(
    project_root: Path,
    framework_root: Path,
    consent: ProjectConsent | None,
    logger: Logger,
) -> PluginResult:
    """Write the public roles, skills and prompts into project_root/.github, after every check passes."""
    if consent is None:
        return _fail(_consent_refusal(), logger)
    context = _context(framework_root, logger)
    github = project_root / ".github"
    agents_dir = github / "agents"
    skills_dir = github / "skills"
    prompts_dir = github / "prompts"

    agents_source = find_agents_source(context)
    if agents_source is None:
        return _fail(
            "WHAT: no agents source directory was found, so no project agents are written. "
            "WHY: the public roles are read from nWave/agents. "
            "HOW: run the command from a checkout that holds nWave/agents.",
            logger,
        )
    agent_sources = public_agent_sources(context, agents_source)
    waves = _wave_sources(framework_root)
    try:
        texts = {
            _prompt_name(wave): convert_wave(wave.read_text(encoding="utf-8"))
            for wave in waves
        }
    except ValueError as error:
        return _fail(str(error), logger)

    # Every refusal is decided before the first write: agents, skills and prompts.
    refusal = agent_collision(agents_dir, agent_sources) or _prompt_collision(
        prompts_dir, waves
    )
    if refusal is not None:
        return _fail(refusal, logger)
    try:
        preflight_foreign_names(
            skills_dir, read_owned_manifest_strict(skills_dir, _LABEL), _LABEL
        )
    except ValueError as error:
        return _fail(str(error), logger)

    agents = install_public_agents(context, agents_source, agents_dir)
    if not agents.success:
        return _fail(agents.message, logger)
    skills = install_public_skill_folders(
        context, skills_dir, plugin_name=PLUGIN_NAME, host="copilot", label=_LABEL
    )
    if not skills.success:
        return _fail(skills.message, logger)
    prompts = _write_prompts(prompts_dir, texts)

    skill_count = len(read_owned_manifest_strict(skills_dir, _LABEL))
    message = (
        f"Copilot project files written in {github}: {len(agent_sources)} agents, {skill_count} skills, "
        f"{len(prompts)} prompts; {NOT_CHECKED}"
    )
    logger.summary(f"  ✅ {message}")
    return PluginResult(
        success=True,
        plugin_name=PLUGIN_NAME,
        message=message,
        installed_files=[*agents.installed_files, *prompts],
    )


def disable_project(
    project_root: Path, framework_root: Path, logger: Logger
) -> PluginResult:
    """Remove only the agents, skills and prompts the three manifests list; the user's own files stay."""
    context = _context(framework_root, logger)
    github = project_root / ".github"
    agents_dir = github / "agents"
    skills_dir = github / "skills"
    prompts_dir = github / "prompts"
    try:
        if agents_dir.is_dir():
            remove_manifest_owned_assets(
                agents_dir, AGENT_MANIFEST_FILENAME, AGENT_SUFFIX
            )
            (agents_dir / AGENT_MANIFEST_FILENAME).unlink(missing_ok=True)
        if skills_dir.is_dir():
            result = uninstall_public_skill_folders(
                context, skills_dir, plugin_name=PLUGIN_NAME, label=_LABEL
            )
            if not result.success:
                return _fail(result.message, logger)
            (skills_dir / SKILL_MANIFEST_FILENAME).unlink(missing_ok=True)
        if prompts_dir.is_dir():
            remove_manifest_owned_assets(
                prompts_dir,
                PROMPTS_MANIFEST_FILENAME,
                PROMPT_SUFFIX,
                manifest_key=PROMPTS_KEY,
            )
            (prompts_dir / PROMPTS_MANIFEST_FILENAME).unlink(missing_ok=True)
    except (OSError, ValueError) as error:
        return _fail(
            f"WHAT: the Copilot project files were not fully removed from {github}. WHY: {error}. "
            "HOW: remove the named file by hand, then run disable again.",
            logger,
        )
    message = (
        f"Copilot project files removed from {github}; the files you wrote there stay"
    )
    logger.summary(f"  ✅ {message}")
    return PluginResult(success=True, plugin_name=PLUGIN_NAME, message=message)


def command(args: list[str], project_root: Path, framework_root: Path) -> int:
    """The project copilot command: enable [--yes], disable, and --help. Returns the process exit code."""
    if "--help" in args or "-h" in args:
        print(USAGE)
        return 0
    verb = args[0] if args else ""
    rest = args[1:]
    logger = Logger()
    if verb == "enable" and rest in ([], ["--yes"]):
        consent = ProjectConsent() if rest == ["--yes"] else None
        result = enable_project(project_root, framework_root, consent, logger)
    elif verb == "disable" and not rest:
        result = disable_project(project_root, framework_root, logger)
    else:
        print(USAGE, file=sys.stderr)
        return 1
    return 0 if result.success else 1
