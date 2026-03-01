#!/usr/bin/env python3
"""Build a Claude Code plugin directory from the nWave source tree.

Assembles agents, commands, skills, DES module, hooks, and metadata into
a plugin layout:
  nWave/agents/nw-*.md  -> plugin/agents/nw-*.md
  nWave/tasks/nw/*.md   -> plugin/commands/*.md       (tasks -> commands, flat)
  nWave/skills/*/       -> plugin/skills/*/           (preserving structure)
  src/des/              -> plugin/scripts/des/         (imports rewritten)
  nWave/templates/*.json-> plugin/scripts/templates/   (DES runtime templates)
  pyproject.toml        -> plugin/.claude-plugin/plugin.json (version extraction)
  (generated)           -> plugin/hooks/hooks.json     (5 DES hook events)
  (generated)           -> plugin/scripts/des-hook     (thin shell wrapper)

Design: Pure function pipeline with frozen dataclasses and Result types.
No side effects in domain logic; IO confined to pipeline boundaries.

Usage:
    python scripts/build_plugin.py
    python scripts/build_plugin.py --project-root /path/to/project
    python scripts/build_plugin.py --output-dir /path/to/output
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# DES Import Rewriting Patterns (shared with build_dist.py)
# ---------------------------------------------------------------------------

_FROM_PATTERN = re.compile(r"\bfrom\s+src\.des\b")
_IMPORT_PATTERN = re.compile(r"\bimport\s+src\.des\b")
_GENERAL_PATTERN = re.compile(r"\bsrc\.des\.")


# ---------------------------------------------------------------------------
# Domain Types (frozen, immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BuildConfig:
    """Immutable configuration for the plugin build pipeline."""

    source_root: Path
    nwave_dir: Path
    des_dir: Path
    pyproject_path: Path
    output_dir: Path
    plugin_name: str = "nw"

    hook_template_override: dict | None = None

    @staticmethod
    def from_dict(config: dict) -> BuildConfig:
        """Create BuildConfig from a dictionary (test fixture compatibility)."""
        return BuildConfig(
            source_root=Path(config["source_root"]),
            nwave_dir=Path(config["nwave_dir"]),
            des_dir=Path(config["des_dir"]),
            pyproject_path=Path(config["pyproject_path"]),
            output_dir=Path(config["output_dir"]),
            plugin_name=config.get("plugin_name", "nw"),
            hook_template_override=config.get("hook_template_override"),
        )

    @staticmethod
    def from_project_root(project_root: Path, output_dir: Path) -> BuildConfig:
        """Create BuildConfig from a project root directory."""
        return BuildConfig(
            source_root=project_root,
            nwave_dir=project_root / "nWave",
            des_dir=project_root / "src" / "des",
            pyproject_path=project_root / "pyproject.toml",
            output_dir=output_dir,
        )


@dataclass(frozen=True)
class StepResult:
    """Result of a single pipeline step."""

    step_name: str
    count: int
    success: bool
    error: str | None = None

    @staticmethod
    def ok(step_name: str, count: int) -> StepResult:
        return StepResult(step_name=step_name, count=count, success=True)

    @staticmethod
    def fail(step_name: str, error: str) -> StepResult:
        return StepResult(step_name=step_name, count=0, success=False, error=error)


@dataclass(frozen=True)
class BuildResult:
    """Immutable result of the complete build pipeline."""

    output_dir: Path
    success: bool
    error: str | None = None
    metadata: dict = field(default_factory=dict)
    steps: tuple[StepResult, ...] = ()

    def is_success(self) -> bool:
        return self.success


@dataclass(frozen=True)
class ValidationResult:
    """Immutable result of plugin validation.

    Pure function output: no side effects, reports ALL errors at once.
    """

    success: bool
    errors: tuple[str, ...]
    sections: dict[str, bool]
    counts: dict[str, int]


# ---------------------------------------------------------------------------
# Pure Functions: Source Validation
# ---------------------------------------------------------------------------


def validate_source_tree(config: BuildConfig) -> str | None:
    """Validate that required source directories exist.

    Returns None on success, error message on failure.
    """
    agents_dir = config.nwave_dir / "agents"
    if not agents_dir.exists():
        return "Source tree is missing the agents directory"

    skills_dir = config.nwave_dir / "skills"
    if not skills_dir.exists():
        return "Source tree is missing the skills directory"

    commands_dir = config.nwave_dir / "tasks" / "nw"
    if not commands_dir.exists():
        return "Source tree is missing the commands directory (tasks/nw)"

    if not config.des_dir.exists():
        return "Source tree is missing the DES source directory"

    return None


# ---------------------------------------------------------------------------
# Pure Functions: Version Extraction
# ---------------------------------------------------------------------------


def read_version(pyproject_path: Path) -> tuple[str | None, str | None]:
    """Read version from pyproject.toml.

    Returns (version, None) on success, (None, error) on failure.
    """
    if not pyproject_path.exists():
        return None, "Cannot read version: pyproject.toml not found"

    try:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore[no-redef]

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        version = data.get("project", {}).get("version")
        if version is None:
            return None, "Cannot read version: no project.version in pyproject.toml"
        return version, None

    except ModuleNotFoundError:
        # Fallback: regex parse
        content = pyproject_path.read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if match:
            return match.group(1), None
        return None, "Cannot read version: could not parse pyproject.toml"

    except Exception as exc:
        return None, f"Cannot read version: {exc}"


# ---------------------------------------------------------------------------
# Pure Functions: Metadata Generation
# ---------------------------------------------------------------------------


def generate_plugin_metadata(plugin_name: str) -> dict:
    """Generate plugin.json metadata content.

    Only includes fields used by official Anthropic plugins (name, description,
    author). Extra fields (version, homepage, keywords, etc.) cause Claude Code
    to silently fail plugin command discovery.
    """
    return {
        "name": plugin_name,
        "description": (
            "nWave: AI-powered workflow framework — 23 agents, 98+ skills, "
            "TDD enforcement, and wave-based development methodology for Claude Code"
        ),
        "author": {
            "name": "nWave AI",
            "email": "hello@nwave.ai",
        },
    }


def generate_marketplace_catalog(plugin_name: str, version: str) -> dict:
    """Generate marketplace.json catalog for self-hosted distribution."""
    return {
        "name": MARKETPLACE_NAME,
        "owner": {
            "name": "nWave AI",
            "email": "hello@nwave.ai",
        },
        "metadata": {
            "description": (
                "nWave plugin marketplace — structured AI development "
                "with TDD enforcement for Claude Code"
            ),
            "version": version,
        },
        "plugins": [
            {
                "name": plugin_name,
                "source": PLUGIN_SOURCE_TEMPLATE.format(name=plugin_name),
                "description": (
                    "nWave: AI-powered workflow framework — 23 agents, 98+ skills, "
                    "TDD enforcement, and wave-based development methodology"
                ),
                "version": version,
                "category": PLUGIN_CATEGORY,
                "tags": [
                    "tdd",
                    "workflow",
                    "agents",
                    "software-craft",
                    "bdd",
                    "code-quality",
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Pipeline Steps: IO at Boundaries
# ---------------------------------------------------------------------------


def copy_agents(config: BuildConfig, plugin_dir: Path) -> StepResult:
    """Copy agent definitions from source to plugin directory."""
    source_dir = config.nwave_dir / "agents"
    dest_dir = plugin_dir / "agents"
    dest_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for md_file in sorted(source_dir.glob("nw-*.md")):
        shutil.copy2(md_file, dest_dir / md_file.name)
        count += 1

    if count == 0:
        return StepResult.fail("agents", "No agent files found in source")

    return StepResult.ok("agents", count)


def rewrite_agent_skill_refs(plugin_dir: Path, skills_dir: Path) -> StepResult:
    """Rewrite agent frontmatter to reference skill bundles instead of individual skills.

    Transforms:
      skills:
        - tdd-methodology
        - progressive-refactoring
    Into:
      skills:
        - software-crafter

    The bundle name matches the agent's skill directory (nw-<name> -> <name>).
    Only rewrites if a matching skill directory exists in the plugin.
    """
    agents_dir = plugin_dir / "agents"
    if not agents_dir.exists():
        return StepResult.ok("skill_refs", 0)

    available_bundles = (
        {d.name for d in skills_dir.iterdir() if d.is_dir()}
        if skills_dir.exists()
        else set()
    )

    rewritten = 0
    for agent_file in sorted(agents_dir.glob("nw-*.md")):
        agent_name = agent_file.stem.removeprefix("nw-")
        if agent_name not in available_bundles:
            continue

        content = agent_file.read_text(encoding="utf-8")
        if not content.startswith("---"):
            continue

        parts = content.split("---", 2)
        if len(parts) < 3:
            continue

        frontmatter = parts[1].strip()
        body = parts[2]

        # Replace the skills list with the single bundle reference
        new_fm_lines = []
        in_skills_block = False
        for line in frontmatter.splitlines():
            if line.startswith("skills:"):
                new_fm_lines.append("skills:")
                new_fm_lines.append(f"  - {agent_name}")
                in_skills_block = True
            elif in_skills_block and line.startswith("  - "):
                continue  # Skip old individual skill entries
            else:
                in_skills_block = False
                new_fm_lines.append(line)

        new_frontmatter = "\n".join(new_fm_lines)
        agent_file.write_text(
            f"---\n{new_frontmatter}\n---{body}",
            encoding="utf-8",
        )
        rewritten += 1

    return StepResult.ok("skill_refs", rewritten)


def copy_commands(config: BuildConfig, plugin_dir: Path) -> StepResult:
    """Copy command definitions from tasks/nw/ to commands/.

    Commands go directly into commands/ (not commands/nw/) because the
    plugin name in plugin.json already provides the 'nw:' namespace prefix.
    """
    source_dir = config.nwave_dir / "tasks" / "nw"
    dest_dir = plugin_dir / "commands"
    dest_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for md_file in sorted(source_dir.glob("*.md")):
        shutil.copy2(md_file, dest_dir / md_file.name)
        count += 1

    if count == 0:
        return StepResult.fail("commands", "No command files found in source")

    return StepResult.ok("commands", count)


def copy_skills(config: BuildConfig, plugin_dir: Path) -> StepResult:
    """Copy skill files preserving directory structure."""
    source_dir = config.nwave_dir / "skills"
    dest_dir = plugin_dir / "skills"
    dest_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for skill_group in sorted(source_dir.iterdir()):
        if skill_group.is_dir():
            shutil.copytree(
                skill_group, dest_dir / skill_group.name, dirs_exist_ok=True
            )
            count += len(list(skill_group.rglob("*.md")))

    if count == 0:
        return StepResult.fail("skills", "No skill files found in source")

    # Generate SKILL.md entry points for Claude Code discovery
    for skill_dir in sorted(dest_dir.iterdir()):
        if skill_dir.is_dir():
            _generate_skill_entry_point(skill_dir)

    return StepResult.ok("skills", count)


def _parse_skill_frontmatter(md_path: Path) -> dict[str, str]:
    """Extract name and description from a skill file's YAML frontmatter."""
    content = md_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {"name": md_path.stem, "description": ""}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {"name": md_path.stem, "description": ""}

    result: dict[str, str] = {"name": md_path.stem, "description": ""}
    for line in parts[1].strip().splitlines():
        if line.startswith("name:"):
            result["name"] = line.split(":", 1)[1].strip().strip("\"'")
        elif line.startswith("description:"):
            result["description"] = line.split(":", 1)[1].strip().strip("\"'")
    return result


def _generate_skill_entry_point(skill_dir: Path) -> None:
    """Generate a SKILL.md entry point in a skill directory.

    Creates a lightweight index that Claude Code discovers automatically.
    Lists all individual skill files with descriptions so the agent knows
    what's available and can load files on demand.
    """
    skill_files = sorted(f for f in skill_dir.glob("*.md") if f.name != "SKILL.md")
    if not skill_files:
        return

    dir_name = skill_dir.name
    skills_info = [_parse_skill_frontmatter(f) for f in skill_files]

    lines = [
        "---",
        f"name: {dir_name}",
        f"description: Skill bundle for nw-{dir_name} agent — "
        f"{len(skill_files)} skill files",
        "---",
        "",
        f"# {dir_name.replace('-', ' ').title()} Skills",
        "",
        "Load skill files on-demand by phase. "
        "Read the files from this directory as needed.",
        "",
        "| Skill | File | Description |",
        "|-------|------|-------------|",
    ]

    for info, path in zip(skills_info, skill_files, strict=True):
        desc = (
            info["description"][:80] + "..."
            if len(info["description"]) > 80
            else info["description"]
        )
        lines.append(f"| {info['name']} | {path.name} | {desc} |")

    lines.append("")

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Pure Functions: DES Import Rewriting
# ---------------------------------------------------------------------------


def rewrite_des_imports(content: str) -> str:
    """Rewrite src.des imports to standalone des imports.

    Transforms:
      from src.des -> from des
      import src.des -> import des
      src.des. -> des.
    """
    result = _FROM_PATTERN.sub("from des", content)
    result = _IMPORT_PATTERN.sub("import des", result)
    result = _GENERAL_PATTERN.sub("des.", result)
    return result


def validate_python_syntax(content: str, filename: str) -> str | None:
    """Validate that content is syntactically valid Python.

    Returns None on success, error message on failure.
    """
    try:
        ast.parse(content, filename=filename)
        return None
    except SyntaxError as exc:
        return f"Import rewrite produced invalid syntax in {filename}: {exc}"


# ---------------------------------------------------------------------------
# Pure Functions: Hook Configuration Generation
# ---------------------------------------------------------------------------

_HOOK_COMMAND_TEMPLATE = (
    "PYTHONPATH=${{CLAUDE_PLUGIN_ROOT}}/scripts python3"
    " -m des.adapters.drivers.hooks.claude_code_hook_adapter {action}"
)

_HOOK_EVENTS: tuple[tuple[str, str | None, str], ...] = (
    ("PreToolUse", "Task", "pre-task"),
    ("PostToolUse", "Task", "post-tool-use"),
    ("SubagentStop", None, "subagent-stop"),
    ("SessionStart", "startup", "session-start"),
    ("SubagentStart", None, "subagent-start"),
)


def generate_hook_config(
    command_template: str = _HOOK_COMMAND_TEMPLATE,
) -> dict[str, list[dict]]:
    """Generate hooks config in Claude Code settings.json format.

    Output matches the hooks schema documented at
    https://code.claude.com/docs/en/plugins-reference#hooks
    """
    config: dict[str, list[dict]] = {}
    for event, matcher, action in _HOOK_EVENTS:
        command = command_template.format(action=action)
        entry: dict = {"hooks": [{"type": "command", "command": command}]}
        if matcher is not None:
            entry["matcher"] = matcher
        config.setdefault(event, []).append(entry)
    return config


def validate_hook_config(config: dict[str, list[dict]]) -> str | None:
    """Validate that all hook entries have non-empty commands.

    Returns None on success, error message on failure.
    """
    for event, entries in config.items():
        for idx, entry in enumerate(entries):
            for hook in entry.get("hooks", []):
                command = hook.get("command", "")
                if not command.strip():
                    return (
                        f"Hook configuration error: empty command for "
                        f"event '{event}' entry {idx}"
                    )
    return None


# ---------------------------------------------------------------------------
# Pure Functions: Shell Wrapper Generation
# ---------------------------------------------------------------------------

_HOOK_WRAPPER_CONTENT = """\
#!/usr/bin/env python3
\"\"\"DES hook wrapper for Claude Code plugin.

Arguments originate from Claude Code runtime only — not from user input.
\"\"\"
import os
import sys

# Ensure the scripts/ directory is on PYTHONPATH so `import des` works
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from des.adapters.drivers.hooks.claude_code_hook_adapter import main

if __name__ == "__main__":
    main()
"""


# ---------------------------------------------------------------------------
# Pipeline Steps: DES Module, Templates, Hooks
# ---------------------------------------------------------------------------


def copy_des_module(config: BuildConfig, plugin_dir: Path) -> StepResult:
    """Copy src/des/ to plugin/scripts/des/, rewrite imports, clear __pycache__."""
    dest_dir = plugin_dir / "scripts" / "des"
    shutil.copytree(config.des_dir, dest_dir, dirs_exist_ok=True)

    # __pycache__ contains absolute paths from the build machine — ship source only
    for cache_dir in dest_dir.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)

    # src.des imports must become standalone des imports so the plugin
    # works without the nWave source tree on PYTHONPATH
    files_rewritten = 0
    for py_file in sorted(dest_dir.rglob("*.py")):
        original_content = py_file.read_text(encoding="utf-8")
        rewritten_content = rewrite_des_imports(original_content)

        if rewritten_content != original_content:
            syntax_error = validate_python_syntax(rewritten_content, py_file.name)
            if syntax_error is not None:
                return StepResult.fail("des_module", syntax_error)
            py_file.write_text(rewritten_content, encoding="utf-8")
            files_rewritten += 1

    return StepResult.ok("des_module", files_rewritten)


def copy_templates(config: BuildConfig, plugin_dir: Path) -> StepResult:
    """Copy DES runtime templates to plugin/scripts/templates/."""
    templates_dir = config.nwave_dir / "templates"
    dest_dir = plugin_dir / "scripts" / "templates"
    dest_dir.mkdir(parents=True, exist_ok=True)

    template_files = (
        "step-tdd-cycle-schema.json",
        "roadmap-schema.json",
    )

    count = 0
    for template_name in template_files:
        source_file = templates_dir / template_name
        if source_file.exists():
            shutil.copy2(source_file, dest_dir / template_name)
            count += 1

    return StepResult.ok("templates", count)


def generate_hooks_json(
    plugin_dir: Path, hook_template_override: dict | None = None
) -> StepResult:
    """Generate hooks/hooks.json with all 5 DES enforcement events.

    Output format matches the Claude Code settings.json hooks schema:
    {"hooks": {"EventName": [{"matcher": "...", "hooks": [...]}]}}

    If hook_template_override is provided, its config is validated and used
    instead of the default config. This enables error-path testing.
    """
    if hook_template_override is not None:
        config = hook_template_override.get("hooks", {})
        validation_error = validate_hook_config(config)
        if validation_error is not None:
            return StepResult.fail("hooks", validation_error)
    else:
        config = generate_hook_config()
        validation_error = validate_hook_config(config)
        if validation_error is not None:
            return StepResult.fail("hooks", validation_error)

    hooks_dir = plugin_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hooks_data = {"hooks": config}
    hooks_path = hooks_dir / "hooks.json"
    hooks_path.write_text(json.dumps(hooks_data, indent=2) + "\n", encoding="utf-8")

    # Count total hook entries across all events
    total_entries = sum(len(entries) for entries in config.values())
    return StepResult.ok("hooks", total_entries)


def generate_hook_wrapper(plugin_dir: Path) -> StepResult:
    """Generate scripts/des-hook shell wrapper (< 10 lines)."""
    scripts_dir = plugin_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    wrapper_path = scripts_dir / "des-hook"
    wrapper_path.write_text(_HOOK_WRAPPER_CONTENT, encoding="utf-8")
    # Make executable
    wrapper_path.chmod(
        wrapper_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH
    )

    return StepResult.ok("hook_wrapper", 1)


def write_metadata(plugin_dir: Path, metadata: dict) -> StepResult:
    """Write plugin.json metadata to the .claude-plugin directory."""
    metadata_dir = plugin_dir / ".claude-plugin"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = metadata_dir / "plugin.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    return StepResult.ok("metadata", 1)


def write_marketplace_json(
    marketplace_dir: Path,
    plugin_name: str,
    version: str,
) -> StepResult:
    """Write marketplace.json for self-hosted distribution.

    Creates the marketplace catalog at a SEPARATE directory from the plugin.
    The marketplace references plugins via relative paths:
      marketplace_dir/
        .claude-plugin/marketplace.json   <- catalog
        plugins/<plugin_name>/            <- plugin artifacts (symlinked or copied)
    """
    catalog = generate_marketplace_catalog(plugin_name, version)

    mp_meta_dir = marketplace_dir / ".claude-plugin"
    mp_meta_dir.mkdir(parents=True, exist_ok=True)

    mp_path = mp_meta_dir / "marketplace.json"
    mp_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    return StepResult.ok("marketplace", 1)


# ---------------------------------------------------------------------------
# Pipeline Composition
# ---------------------------------------------------------------------------


def _cleanup_on_failure(plugin_dir: Path, *, created_by_build: bool) -> None:
    """Remove partial output on build failure.

    Only removes the directory if it was created by this build run,
    preventing accidental destruction of pre-existing content.
    """
    if created_by_build and plugin_dir.exists():
        shutil.rmtree(plugin_dir)


def build(config: BuildConfig, *, version_override: str | None = None) -> BuildResult:
    """Execute the plugin assembly pipeline.

    Pipeline: validate -> read_version -> copy_agents -> copy_commands
              -> copy_skills -> copy_des_module -> copy_templates
              -> generate_hooks_json -> generate_hook_wrapper
              -> generate_metadata -> write_metadata

    Args:
        config: Build configuration.
        version_override: If provided, use this version instead of reading
            from pyproject.toml. Used by CI to inject the release version
            (e.g. RC or stable) so the plugin.json version matches the
            GitHub release tag exactly.
    """
    # Step 1: Validate source tree
    source_error = validate_source_tree(config)
    if source_error is not None:
        return BuildResult(
            output_dir=config.output_dir,
            success=False,
            error=source_error,
        )

    # Step 2: Read and validate version
    if version_override:
        version = version_override
    else:
        version, read_error = read_version(config.pyproject_path)
        if read_error is not None:
            return BuildResult(
                output_dir=config.output_dir,
                success=False,
                error=read_error,
            )

    # Step 3: Prepare plugin directory
    plugin_dir = config.output_dir
    created_by_build = not plugin_dir.exists()
    plugin_dir.mkdir(parents=True, exist_ok=True)

    def _fail(error: str, steps_so_far: tuple[StepResult, ...]) -> BuildResult:
        _cleanup_on_failure(plugin_dir, created_by_build=created_by_build)
        return BuildResult(
            output_dir=config.output_dir,
            success=False,
            error=error,
            steps=steps_so_far,
        )

    # Step 4: Execute copy pipeline (agents, commands, skills)
    steps: list[StepResult] = []

    copy_functions = [copy_agents, copy_commands, copy_skills]
    for copy_fn in copy_functions:
        result = copy_fn(config, plugin_dir)
        steps.append(result)
        if not result.success:
            return _fail(result.error, tuple(steps))

    # Step 5: Rewrite agent skill references to use bundles
    skill_refs_result = rewrite_agent_skill_refs(plugin_dir, plugin_dir / "skills")
    steps.append(skill_refs_result)

    # Step 6: DES module bundling
    des_result = copy_des_module(config, plugin_dir)
    steps.append(des_result)
    if not des_result.success:
        return _fail(des_result.error, tuple(steps))

    # Step 6: DES runtime templates
    templates_result = copy_templates(config, plugin_dir)
    steps.append(templates_result)

    # Step 7: Hook configuration
    hooks_result = generate_hooks_json(plugin_dir, config.hook_template_override)
    steps.append(hooks_result)
    if not hooks_result.success:
        return _fail(hooks_result.error, tuple(steps))

    # Step 8: Hook shell wrapper
    wrapper_result = generate_hook_wrapper(plugin_dir)
    steps.append(wrapper_result)

    # Step 9: Generate and write metadata
    metadata = generate_plugin_metadata(config.plugin_name)
    metadata_result = write_metadata(plugin_dir, metadata)
    steps.append(metadata_result)

    return BuildResult(
        output_dir=plugin_dir,
        success=True,
        metadata={**metadata, "version": version},
        steps=tuple(steps),
    )


# ---------------------------------------------------------------------------
# Driving Port: Plugin Validation
# ---------------------------------------------------------------------------


def _validate_metadata(plugin_dir: Path) -> tuple[bool, list[str]]:
    """Validate .claude-plugin/plugin.json exists and is well-formed."""
    errors: list[str] = []
    metadata_path = plugin_dir / ".claude-plugin" / "plugin.json"

    if not metadata_path.exists():
        errors.append("Missing metadata: .claude-plugin/plugin.json not found")
        return False, errors

    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"Invalid metadata: plugin.json is not valid JSON ({exc})")
        return False, errors

    for required_field in ("name",):
        if required_field not in data:
            errors.append(
                f"Invalid metadata: plugin.json missing required field '{required_field}'"
            )

    return len(errors) == 0, errors


def _validate_directory_with_md_files(
    plugin_dir: Path, section: str
) -> tuple[bool, list[str], int]:
    """Validate a directory exists and contains at least one .md file."""
    errors: list[str] = []
    target_dir = plugin_dir / section

    if not target_dir.exists():
        errors.append(f"Missing {section}: {section}/ directory not found")
        return False, errors, 0

    md_files = list(target_dir.rglob("*.md"))
    count = len(md_files)

    if count == 0:
        errors.append(f"Empty {section}: {section}/ contains no .md files")
        return False, errors, 0

    return True, errors, count


def _validate_hooks(plugin_dir: Path) -> tuple[bool, list[str]]:
    """Validate hooks/hooks.json exists, is valid JSON, and has proper schema.

    Expected format (Claude Code settings.json schema):
    {"hooks": {"EventName": [{"matcher": "...", "hooks": [{"type": "command", "command": "..."}]}]}}
    """
    errors: list[str] = []
    hooks_path = plugin_dir / "hooks" / "hooks.json"

    if not hooks_path.exists():
        errors.append("Missing hooks: hooks/hooks.json not found")
        return False, errors

    try:
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"Invalid hooks: hooks.json is not valid JSON ({exc})")
        return False, errors

    if "hooks" not in data:
        errors.append("Invalid hooks: hooks.json missing required 'hooks' key")
        return False, errors

    if not isinstance(data["hooks"], dict):
        errors.append(
            "Invalid hooks: 'hooks' must be an object mapping event names to arrays"
        )
        return False, errors

    for event, entries in data["hooks"].items():
        if not isinstance(entries, list):
            errors.append(f"Invalid hooks: event '{event}' must map to an array")
            continue
        for idx, entry in enumerate(entries):
            hooks_list = entry.get("hooks", [])
            if not isinstance(hooks_list, list) or len(hooks_list) == 0:
                errors.append(
                    f"Invalid hooks: event '{event}' entry {idx} missing or empty 'hooks' array"
                )
            for hook in hooks_list:
                command = hook.get("command", "")
                if not command or not isinstance(command, str):
                    errors.append(
                        f"Invalid hooks: event '{event}' entry {idx} has empty 'command'"
                    )

    return len(errors) == 0, errors


def _validate_des_module(plugin_dir: Path) -> tuple[bool, list[str]]:
    """Validate scripts/des/__init__.py exists."""
    errors: list[str] = []
    init_path = plugin_dir / "scripts" / "des" / "__init__.py"

    if not init_path.exists():
        errors.append("Missing DES module: scripts/des/__init__.py not found")
        return False, errors

    return True, errors


def generate_marketplace_manifest(
    plugin_dir: Path,
    download_url: str = "",
) -> StepResult:
    """Generate marketplace-manifest.json for self-hosted distribution."""
    metadata_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if not metadata_path.exists():
        return StepResult.fail(
            "manifest", "Cannot generate manifest: plugin.json not found"
        )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    manifest = {
        "name": metadata.get("name", ""),
        "version": metadata.get("version", ""),
        "description": metadata.get("description", ""),
        "download": download_url,
        "homepage": "https://nwave.ai",
    }

    manifest_path = plugin_dir / "marketplace-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return StepResult.ok("manifest", 1)


def validate(plugin_dir: Path) -> ValidationResult:
    """Validate plugin structure is complete and well-formed.

    Pure function: reads plugin_dir, returns ValidationResult.
    Reports ALL errors, does not stop at first.
    """
    all_errors: list[str] = []
    sections: dict[str, bool] = {}
    counts: dict[str, int] = {}

    # Metadata validation
    metadata_ok, metadata_errors = _validate_metadata(plugin_dir)
    sections["metadata"] = metadata_ok
    all_errors.extend(metadata_errors)

    # Agents validation
    agents_ok, agents_errors, agents_count = _validate_directory_with_md_files(
        plugin_dir, "agents"
    )
    sections["agents"] = agents_ok
    counts["agents"] = agents_count
    all_errors.extend(agents_errors)

    # Skills validation
    skills_ok, skills_errors, skills_count = _validate_directory_with_md_files(
        plugin_dir, "skills"
    )
    sections["skills"] = skills_ok
    counts["skills"] = skills_count
    all_errors.extend(skills_errors)

    # Commands validation
    commands_ok, commands_errors, commands_count = _validate_directory_with_md_files(
        plugin_dir, "commands"
    )
    sections["commands"] = commands_ok
    counts["commands"] = commands_count
    all_errors.extend(commands_errors)

    # Hooks validation
    hooks_ok, hooks_errors = _validate_hooks(plugin_dir)
    sections["hooks"] = hooks_ok
    all_errors.extend(hooks_errors)

    # DES module validation
    des_ok, des_errors = _validate_des_module(plugin_dir)
    sections["des_module"] = des_ok
    all_errors.extend(des_errors)

    return ValidationResult(
        success=len(all_errors) == 0,
        errors=tuple(all_errors),
        sections=sections,
        counts=counts,
    )


# ---------------------------------------------------------------------------
# Pure Functions: Coexistence Verification
# ---------------------------------------------------------------------------

# Plugin installation paths (relative to ~/.claude/)
PLUGIN_INSTALL_PREFIX = "plugins/cache/nwave"

# Marketplace configuration
MARKETPLACE_NAME = "nwave-marketplace"
PLUGIN_SOURCE_TEMPLATE = "./plugins/{name}"
PLUGIN_CATEGORY = "development-workflows"


def get_plugin_paths() -> set[str]:
    """Return the relative paths owned by the plugin installation."""
    return {
        f"{PLUGIN_INSTALL_PREFIX}/agents",
        f"{PLUGIN_INSTALL_PREFIX}/commands",
        f"{PLUGIN_INSTALL_PREFIX}/skills",
        f"{PLUGIN_INSTALL_PREFIX}/hooks",
        f"{PLUGIN_INSTALL_PREFIX}/scripts",
        f"{PLUGIN_INSTALL_PREFIX}/.claude-plugin",
    }


def get_installer_paths() -> set[str]:
    """Return the relative paths owned by the custom installer."""
    return {
        "agents/nw",
        "commands/nw",
        "skills/nw",
        "lib/python/des",
        "scripts/des",
        "templates",
    }


def check_version_consistency(
    plugin_version: str, installer_version: str
) -> str | None:
    """Check if plugin and installer versions match.

    Returns None if versions match, warning message if they differ.
    """
    if plugin_version != installer_version:
        return (
            f"Version mismatch: plugin is {plugin_version}, "
            f"custom installer is {installer_version}. "
            f"Consider upgrading the older installation."
        )
    return None


def verify_path_disjointness() -> tuple[bool, list[str]]:
    """Verify plugin and installer paths never overlap.

    Returns (is_disjoint, overlapping_paths).
    """
    plugin_paths = get_plugin_paths()
    installer_paths = get_installer_paths()

    overlaps = []
    for pp in plugin_paths:
        for ip in installer_paths:
            if pp.startswith(ip) or ip.startswith(pp):
                overlaps.append(f"{pp} overlaps with {ip}")

    return len(overlaps) == 0, overlaps


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Claude Code plugin from nWave source"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (default: auto-detect)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for plugin (default: plugin/)",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="",
        help="Override version (default: read from pyproject.toml)",
    )
    parser.add_argument(
        "--download-url",
        type=str,
        default="",
        help="Download URL for marketplace manifest",
    )
    args = parser.parse_args()

    project_root = args.project_root or Path(__file__).parent.parent
    output_dir = args.output_dir or project_root / "plugin"

    config = BuildConfig.from_project_root(project_root, output_dir)

    print(f"[INFO] Building plugin from {config.nwave_dir}")
    print(f"[INFO] Output: {config.output_dir}")

    result = build(config, version_override=args.version or None)

    for step in result.steps:
        status = "OK" if step.success else "FAIL"
        print(f"[{status}] {step.step_name}: {step.count} items")

    if result.success:
        print(
            f"[INFO] Plugin built successfully (version {result.metadata['version']})"
        )

        # Generate marketplace manifest after successful build
        manifest_result = generate_marketplace_manifest(
            result.output_dir, args.download_url
        )
        if manifest_result.success:
            print("[OK] manifest: 1 items")
        else:
            print(f"[WARN] Manifest generation failed: {manifest_result.error}")
    else:
        print(f"[ERROR] Build failed: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
