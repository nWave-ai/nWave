"""Plugin for installing nWave agents into Codex CLI's TOML agent format.

Codex CLI expects agents at: ~/.codex/agents/{agent-name}.toml
Each agent file is TOML with:
  name = "agent-name"
  description = "..."
  developer_instructions = '''
  ...full agent body...
  '''
  model = "..."   (optional)

This is distinct from OpenCode (~/.config/opencode/agents/*.md), which uses
YAML-frontmatter Markdown. The transform pipeline:

  Claude Code source (.md, YAML frontmatter + Markdown body)
    -> parse frontmatter + body
    -> extract scalar fields (name, description, model)
    -> translate tools block into a capability-mapping preamble (the Codex
       TOML schema has no tools field, so declared capabilities are granted
       against the native surface and undeclared ones explicitly denied)
    -> render TOML with body as developer_instructions

A manifest (.nwave-agents-manifest.json) tracks which agents nWave installed,
enabling safe uninstallation without touching user-created agents.
"""

import importlib
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path

from nwave_ai.platform.capability import REPLY_CHANNEL_TOOLS, split_declared_tools
from nwave_ai.platform.role_render import render_installed_role
from nwave_ai.upgrade_shell import _codex_legacy_direct_des_command
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.opencode_common import (
    parse_frontmatter,
    remove_manifest_owned_assets,
)
from scripts.shared.agent_catalog import is_public_agent, load_public_agents
from scripts.shared.codex_model_wording import rewrite_claude_model_names
from scripts.shared.platform_contracts import (
    CODEX_AGENT_FORBIDDEN_FIELDS,
    nwdes_cli_role_tools,
    project_nwdes_role_text,
)
from scripts.shared.skill_path_rewrite import rewrite_host_paths


_MANIFEST_FILENAME = ".nwave-agents-manifest.json"
# Metadata key the installer sets from the cleanup's Codex witness (F510). When the
# key is absent (dry-run, direct plugin use) the disk witness decides (F516).
_CODEX_LEGACY_WITNESS_KEY = "codex_legacy_witness"
_LEGACY_AGENT_SOURCES = {
    "nw-architect": "nw-solution-architect",
    "nw-crafter": "nw-software-crafter",
}
_logger = logging.getLogger(__name__)
_toml_reader = importlib.import_module(
    "tomllib" if sys.version_info >= (3, 11) else "tomli"
)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _codex_agents_dir() -> Path:
    """Return the Codex CLI agents target directory.

    Codex agents live at ~/.codex/agents/. CODEX_HOME overrides ~/.codex/.

    Returns:
        Path to ~/.codex/agents/ (or $CODEX_HOME/agents/)
    """
    override = os.environ.get("CODEX_HOME")
    base = Path(override) if override else Path.home() / ".codex"
    return base / "agents"


def _codex_config_dir() -> Path:
    """Return the Codex CLI configuration directory.

    Returns:
        Path to ~/.codex/ (or $CODEX_HOME if set)
    """
    override = os.environ.get("CODEX_HOME")
    return Path(override) if override else Path.home() / ".codex"


def _find_agents_source(context: InstallContext) -> Path | None:
    """Locate the agents source directory from dist or project layout.

    Args:
        context: InstallContext with framework_source and project_root

    Returns:
        Path to the agents source directory, or None if not found
    """
    dist_agents = context.framework_source / "agents"
    # Distribution builds retain the host grouping (agents/nw), whereas a
    # project checkout has nWave/agents directly.  Return the actual role
    # directory in either layout so the shared loader can derive its owned
    # skills root without guessing.
    if (dist_agents / "nw").exists():
        return dist_agents / "nw"
    if dist_agents.exists():
        return dist_agents

    project_agents = context.project_root / "nWave" / "agents"
    if project_agents.exists():
        return project_agents

    return None


# ---------------------------------------------------------------------------
# Transform pipeline (pure functions)
# ---------------------------------------------------------------------------


def _extract_scalar_fields(frontmatter: dict) -> dict[str, str]:
    """Extract string-valued TOML fields from the agent frontmatter.

    Keeps only scalar (string) fields that have TOML equivalents.
    Drops all fields in CODEX_AGENT_FORBIDDEN_FIELDS and any non-string
    complex values (lists, dicts).

    Args:
        frontmatter: Parsed YAML frontmatter dict from a Claude Code agent

    Returns:
        Dict of TOML-compatible scalar fields
    """
    return {
        key: str(value)
        for key, value in frontmatter.items()
        if key not in CODEX_AGENT_FORBIDDEN_FIELDS and isinstance(value, str)
    }


#: What an operator is told when a role's declared model cannot cross to Codex.
#: The mapping from a Claude selector to a Codex model belongs to the unified
#: config SSOT work, not here, so this states the gap rather than guessing at a
#: correspondence: the repository declares exactly one Codex model anywhere
#: (the host `~/.codex/config.toml`), and no tier vocabulary to map onto.
#: It never names the dropped Claude selector: an installed Codex agent must not
#: mention a Claude model. The selector stays in the install log
#: (see `_transform_agent`), where the operator reads what was discarded.
UNPROJECTED_MODEL_NOTICE = (
    "declared model not projected for codex: host mapping pending F-CONFIG-SSOT-UNIFIED"
)

#: Scalar fields that are identity or a Codex model policy, never prose: they
#: reach Codex exactly as declared. A surviving ``model`` is a Codex model (the
#: Claude selectors were dropped by ``_omit_unsupported_model``).
_VERBATIM_SCALAR_FIELDS = frozenset({"name", "model"})


def _rewrite_scalar_fields(scalar_fields: dict[str, str]) -> dict[str, str]:
    """Neutralise Claude model names in every prose field.

    The agent's ``name`` is identity and a kept ``model`` is a Codex model; both
    are left as written, so a tier in a name is reported by the install scan
    rather than silently renamed.
    """
    return {
        key: value
        if key in _VERBATIM_SCALAR_FIELDS
        else rewrite_claude_model_names(value)
        for key, value in scalar_fields.items()
    }


def _omit_unsupported_model(scalar_fields: dict[str, str]) -> str | None:
    """Drop a Claude-only model selector, and RETURN what was dropped.

    Returning it is the whole point. Dropping silently made the loss invisible
    twice over: the projected role carries no model, so Codex answers on its
    own configured default, and nothing in the artifact or the install output
    says a declared model was discarded. Measured 2026-09-06: every reviewing
    role declares `sonnet` per Ale's decision of that day, and not one of those
    declarations reaches Codex.

    Returns:
        The dropped selector, or ``None`` when the field was absent or already
        a Codex model that projects unchanged.
    """
    model = scalar_fields.get("model", "")
    normalized = model.casefold()
    if normalized in {"inherit", "haiku", "sonnet", "opus"} or normalized.startswith(
        "claude-"
    ):
        scalar_fields.pop("model", None)
        return model
    return None


def _log_tools_translated(agent_name: str, frontmatter: dict) -> None:
    """Log that a tools block is translated into a capability preamble.

    Codex CLI has no per-agent tool-permission block equivalent; the declared
    tools are translated into a capability-mapping preamble prepended to
    developer_instructions instead of being silently dropped.

    Args:
        agent_name: Agent identifier (for log context)
        frontmatter: Parsed frontmatter dict, potentially containing tools
    """
    if "tools" in frontmatter:
        _logger.info(
            "codex_agents_plugin: translating 'tools' block for agent '%s' "
            "into a capability-mapping preamble (the Codex agent TOML schema "
            "has no tools field)",
            agent_name,
        )


def _parse_declared_tools(frontmatter: dict) -> list[str]:
    """Normalize the frontmatter tools block to a list of tool names.

    Claude Code agents declare tools either as a comma-separated string
    ("Read, Write, Bash") or as a YAML list ([Read, Glob, Grep]).

    Args:
        frontmatter: Parsed YAML frontmatter dict

    Returns:
        Declared tool names in declaration order; empty when absent/empty.
    """
    declared = frontmatter.get("tools")
    if isinstance(declared, str):
        return list(split_declared_tools(declared))
    if isinstance(declared, list):
        items = [str(item) for item in declared]
    else:
        return []
    return [name for name in (item.strip() for item in items) if name]


#: Grant lines, emitted only for capability categories with a declared member.
_CAPABILITY_GRANTS: tuple[tuple[frozenset[str], str], ...] = (
    (
        frozenset({"Read"}),
        "- Read -> read-only file access via your native toolset; shell "
        "read-only commands such as cat, ls and sed -n ARE the sanctioned "
        "Read on this platform.",
    ),
    (
        frozenset({"Write", "Edit"}),
        "- Write/Edit -> create and modify files via your native surface "
        "(apply_patch or shell).",
    ),
    (
        frozenset({"Bash"}),
        "- Bash -> command execution via your native shell.",
    ),
    (
        frozenset({"Glob", "Grep"}),
        "- Glob/Grep -> file and content search via your native toolset "
        "(read-only find/grep-style commands).",
    ),
)

#: Denial lines, emitted for categories with no declared member and no
#: Bash-implied equivalent (Bash subsumes reading and searching; for writing
#: it implies only the disposable probe files of _BASH_PROBE_FILES_DENIAL).
_CAPABILITY_DENIALS: tuple[tuple[frozenset[str], str], ...] = (
    (
        frozenset({"Read", "Bash"}),
        "- Reading file contents is NOT granted: do not read files by any "
        "means, including shell reads such as cat or ls. This role is "
        "source-blind by design; the only exception is an asset the body "
        "explicitly instructs you to load (for example a skill file under "
        "~/.agents/skills/).",
    ),
    (
        frozenset({"Write", "Edit"}),
        "- Creating or modifying files is NOT granted.",
    ),
    (
        frozenset({"Bash"}),
        "- Command execution is NOT granted: the shell may serve only as the "
        "vehicle for a capability granted above, never for arbitrary "
        "commands.",
    ),
    (
        frozenset({"Glob", "Grep", "Bash"}),
        "- File and content search is NOT granted.",
    ),
)

#: Write denial for a role declaring bare Bash without Write/Edit. On Claude
#: Code its Bash tool can create the disposable probe files a role body may
#: authorize (for example a formal model handed to a checker); repository
#: files stay denied, and a body that authorizes no probe gains nothing.
_BASH_PROBE_FILES_DENIAL = (
    "- Creating or modifying repository files is NOT granted. Only where your "
    "role body authorizes disposable probes may the shell create probe files, "
    "and only in a fresh invocation-local directory outside the repository or "
    "in output your caller declared as not owned by you; remove your own probe "
    "files before you finish."
)


def _capability_preamble(frontmatter: dict) -> str:
    """Derive the Codex capability-mapping preamble from declared tools.

    One template parameterized on the declared tools -- no per-agent maps.
    Declared capabilities are granted against the native Codex surface;
    core capabilities with no declared (or Bash-implied) member are denied
    explicitly, so a source-blind role stays source-blind.

    Args:
        frontmatter: Parsed YAML frontmatter dict

    Returns:
        Preamble text, or an empty string when no tools are declared.
    """
    declared = _parse_declared_tools(frontmatter)
    if not declared:
        return ""
    # A reply-channel token (StructuredOutput) names the shape of the role's
    # ANSWER, never an executable Codex capability: Codex enforces the typed
    # reply through --output-schema regardless of declared tools. It must
    # therefore never appear on the "Declared tools:" line and never drive a
    # grant/denial -- but its presence alone still emits this preamble (the
    # role declared a ``tools:`` key), so a reply-channel-only role keeps its
    # explicit source-blind denial block instead of falling back to none.
    declared = [name for name in declared if name not in REPLY_CHANNEL_TOOLS]
    if not declared:
        declared_set: set[str] = set()
        scoped_shell: list[str] = []
    else:
        declared_set = set(declared)
        # A declared entry may be a permission SPECIFIER ("Bash(tool
        # explain:*)") rather than a bare tool name. It grants exactly what it
        # names and implies nothing else, so it is matched verbatim -- the Read
        # and search denials below stay as strict as they were -- and carries
        # its own grant line instead of widening the role to the whole shell.
        scoped_shell = [name for name in declared if name.startswith("Bash(")]

    grants = [line for members, line in _CAPABILITY_GRANTS if members & declared_set]
    if scoped_shell and "Bash" not in declared_set:
        grants.append(
            "- "
            + ", ".join(scoped_shell)
            + " -> run EXACTLY these commands via your native shell, and no "
            "others; the scope in each grant is part of the grant."
        )
    denials = [
        _BASH_PROBE_FILES_DENIAL
        if members == frozenset({"Write", "Edit"}) and "Bash" in declared_set
        else line
        for members, line in _CAPABILITY_DENIALS
        if not members & declared_set
        and not (members == frozenset({"Bash"}) and scoped_shell)
    ]

    sections = [
        "## Codex Capability Mapping (derived from this role's declared tools)",
        "",
        "This role body was authored for a platform with semantic tools; the "
        "Codex agent schema has none. Your native surface (shell, apply_patch) "
        "is the sanctioned vehicle for EXACTLY the capabilities granted below. "
        'Literal tool-name prohibitions in the body (for example "never use '
        'Bash to read") forbid using the shell to CIRCUMVENT a capability '
        "not granted here; they do not forbid the native surface for a "
        "granted capability.",
        "",
        f"Declared tools: {', '.join(declared)}",
    ]
    if grants:
        sections += ["", "Granted:", *grants]
    if denials:
        sections += ["", "Denied (not declared by this role):", *denials]
    if "SendMessage" in declared_set:
        sections += [
            "",
            "Peer messaging: SendMessage is declared for this role but is not projected by this capability mapping; native exposure remains host and configuration dependent.",
        ]
    return "\n".join(sections)


def _render_toml_agent(
    scalar_fields: dict[str, str], body: str, model_unprojected: bool = False
) -> str:
    """Render a Codex agent TOML file from scalar fields and the agent body.

    The Codex agent TOML schema requires:
      name = "..."            (required)
      description = "..."     (required)
      developer_instructions = "..."  (multi-line string, equivalent to body)

    Optional fields (model, etc.) are included when present in scalar_fields.
    The body is assigned to developer_instructions using a TOML basic
    multi-line string (triple-quoted).

    Args:
        scalar_fields: TOML-compatible scalar fields (name, description, model…)
        body: Agent body text (Markdown section after the YAML frontmatter)
        model_unprojected: A declared model that could not cross to Codex. A
            leading TOML comment says so, without naming it, so the loss is
            legible in the artifact an operator opens, not only in install
            output that scrolls past.

    Returns:
        Complete TOML file content as a string
    """
    lines: list[str] = []
    if model_unprojected:
        lines.append(f"# {UNPROJECTED_MODEL_NOTICE}")

    # Emit canonical fields first in a stable order
    for key in ("name", "description", "model"):
        if key in scalar_fields:
            lines.append(f"{key} = {_toml_string(scalar_fields[key])}")

    # Emit remaining scalar fields (alphabetical for stability)
    for key in sorted(scalar_fields):
        if key not in ("name", "description", "model"):
            lines.append(f"{key} = {_toml_string(scalar_fields[key])}")

    # JSON string escaping is compatible with TOML basic strings and safely
    # handles quotes, backslashes, and control characters in arbitrary bodies.
    lines.append(f"developer_instructions = {_toml_multiline_string(body)}")

    if nwdes_cli_role_tools(scalar_fields.get("name", "")):
        lines.extend(
            (
                "",
                "[features]",
                "shell_tool = true",
            )
        )
    return "\n".join(lines) + "\n"


def _toml_string(value: str) -> str:
    """Render a TOML basic string using JSON's compatible string grammar.

    Args:
        value: Raw Python string value

    Returns:
        TOML-quoted string (e.g. '"hello \\"world\\""')
    """
    # Keep non-ASCII scalar values literal: JSON's UTF-16 surrogate-pair escapes
    # for astral characters are not valid TOML Unicode escapes. JSON already
    # escapes C0 controls; TOML additionally forbids a literal DEL character.
    return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007F")


def _toml_multiline_string(value: str) -> str:
    """Render arbitrary text as a TOML-compatible multi-line basic string.

    The body is escaped first with the stdlib JSON serializer, whose string
    escape grammar is compatible with TOML basic strings. Only the JSON
    delimiters are replaced by TOML's multi-line delimiters.

    Args:
        value: Multi-line string content (agent body)

    Returns:
        TOML multi-line basic string literal
    """
    escaped_body = _toml_string(value)[1:-1]
    return f'"""\n{escaped_body}"""'


#: Codex has no native Skill tool. Native agent bodies carry
#: `Invoke Skill(NAME)` / `Invoke ONE Skill(NAME)` directives (docgen/dispatch
#: output); Codex must instead be told to read the skill file directly.
_SKILL_INVOKE_PATTERN = re.compile(r"Invoke( ONE)? Skill\(([a-z0-9-]+)\)")


def _translate_skill_invocations(body: str) -> str:
    """Rewrite native Skill-invocation directives into explicit read
    instructions. ON-TRIGGER suffixes that follow the matched directive are
    untouched. Uses a replacement callable (not a replacement string) so
    literal backslashes in ``body`` are never interpreted as regex
    backreferences."""

    def _replace(match: re.Match[str]) -> str:
        path = f"~/.agents/skills/{match.group(2)}/SKILL.md"
        prefix = "Read ONE" if match.group(1) else "Read"
        return f"{prefix} `{path}`"

    return _SKILL_INVOKE_PATTERN.sub(_replace, body)


def _transform_agent(
    source_content: str, agent_name: str, *, source_path: Path | None = None
) -> str:
    """Full transform pipeline: Claude Code agent MD -> Codex TOML.

    Pipeline:
      1. Parse YAML frontmatter + Markdown body
      2. Log that a declared tools block is translated (not silently dropped)
      3. Extract scalar TOML fields (drop forbidden + non-scalar)
      4. Replace every Claude model name in the fields and body with neutral
         wording (Codex runs on its own configured model)
      5. Prepend the capability-mapping preamble derived from declared tools
      6. Render TOML with body as developer_instructions

    Args:
        source_content: Full source agent file content (Claude Code format).
            Retained for pure callers that do not have an owned source path.
        agent_name: Agent stem name (used for log context only)
        source_path: Owned role source path during installation.  When given,
            explicit frontmatter skills are materialized through the shared
            runtime loader before their paths are projected to Codex.

    Returns:
        Transformed agent TOML content
    """
    if source_path is not None:
        source_content = render_installed_role(source_path, "~/.agents/skills")

    source_content = project_nwdes_role_text(source_content)
    frontmatter, body = parse_frontmatter(source_content)
    _log_tools_translated(agent_name, frontmatter)
    scalar_fields = _extract_scalar_fields(frontmatter)
    unprojected_model = _omit_unsupported_model(scalar_fields)
    if unprojected_model:
        _logger.warning(
            "codex_agents_plugin: agent '%s': %s (declared model: %s)",
            agent_name,
            UNPROJECTED_MODEL_NOTICE,
            unprojected_model,
        )
    scalar_fields = _rewrite_scalar_fields(scalar_fields)
    body = rewrite_host_paths(body, "codex")
    body = _translate_skill_invocations(body)
    body = rewrite_claude_model_names(body)
    preamble = _capability_preamble(frontmatter)
    if preamble:
        body = f"\n{preamble}\n{body}"
    return _render_toml_agent(scalar_fields, body, bool(unprojected_model))


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------


def _write_manifest(target_dir: Path, installed_agent_names: list[str]) -> None:
    """Write the manifest tracking nWave-installed Codex agents.

    Args:
        target_dir: Codex agents directory
        installed_agent_names: List of installed agent stems (without .toml)
    """
    manifest = {
        "installed_agents": sorted(installed_agent_names),
        "version": "1.0",
    }
    manifest_path = target_dir / _MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _read_manifest(target_dir: Path) -> dict | None:
    """Read the manifest file if it exists.

    Args:
        target_dir: Codex agents directory

    Returns:
        Parsed manifest dict, or None if not found
    """
    manifest_path = target_dir / _MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _legacy_agent_names(codex_dir: Path, target_dir: Path) -> set[str]:
    """Return legacy aliases only when the DES ownership witness is exact."""
    if (target_dir / _MANIFEST_FILENAME).exists():
        return set()
    hooks_path = codex_dir / "hooks.json"
    manifest_path = codex_dir / ".nwave-des-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        hooks_document = json.loads(hooks_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return set()
    if _codex_legacy_direct_des_command(manifest, hooks_path, hooks_document) is None:
        return set()
    return _legacy_alias_files(target_dir)


def _legacy_alias_files(target_dir: Path) -> set[str]:
    """Return the legacy alias names present on disk as <name>.toml."""
    return {
        name
        for name in _LEGACY_AGENT_SOURCES
        if (target_dir / f"{name}.toml").is_file()
    }


def _adopted_legacy_agent_names(
    context: InstallContext, codex_dir: Path, target_dir: Path
) -> set[str]:
    """Return the legacy aliases this install adopts.

    The cleanup retires the DES witness before this install runs, so the disk witness
    is gone on the normal path. The installer passes its Codex witness in the context
    metadata instead (F510); the disk witness decides only when that key is absent
    (dry-run, direct plugin use; F516).
    """
    if _CODEX_LEGACY_WITNESS_KEY not in context.metadata:
        return _legacy_agent_names(codex_dir, target_dir)
    if not context.metadata[_CODEX_LEGACY_WITNESS_KEY]:
        return set()
    if (target_dir / _MANIFEST_FILENAME).exists():
        return set()
    return _legacy_alias_files(target_dir)


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------


class CodexAgentsPlugin(InstallationPlugin):
    """Plugin for installing nWave agents into Codex CLI TOML format."""

    def __init__(self) -> None:
        """Initialize Codex agents plugin with name and priority."""
        super().__init__(name="codex-agents", priority=45)
        self.dependencies = ["codex-skills"]

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        """Check whether Codex CLI is present; skip gracefully if not.

        Detection: ~/.codex/ directory exists OR `codex` binary in PATH.

        Args:
            context: InstallContext (unused for detection, but required by ABC)

        Returns:
            PluginResult with success=True always (skip or proceed)
        """

        codex_dir = _codex_config_dir()
        codex_binary = shutil.which("codex") is not None
        if (
            "codex" not in context.target_platforms
            and not codex_dir.exists()
            and not codex_binary
        ):
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Codex CLI not detected, skipping agents installation",
            )

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="Codex agents prerequisites validated",
        )

    def install(self, context: InstallContext) -> PluginResult:
        """Install agents from nWave/agents/ as Codex TOML files.

        Transform pipeline per agent:
          1. Parse YAML frontmatter + Markdown body
          2. Translate tools block into a capability-mapping preamble
          3. Emit scalar fields (name, description, model) as TOML
          4. Emit Markdown body as developer_instructions multi-line string
          5. Write to ~/.codex/agents/{agent-name}.toml

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            prereq = self.validate_prerequisites(context)
            if "skip" in prereq.message.lower():
                return prereq

            context.logger.info("  Installing Codex agents...")

            agents_source = _find_agents_source(context)
            if agents_source is None:
                context.logger.info("  No agents directory found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No agents to install (source directory not found)",
                )

            target_dir = _codex_agents_dir()
            target_dir.mkdir(parents=True, exist_ok=True)

            public_agents = (
                set()
                if context.dev_mode
                else load_public_agents(context.project_root / "nWave")
            )

            agent_files = sorted(agents_source.glob("nw-*.md"))
            if not agent_files:
                context.logger.info("  No agent files found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No agent files found in source directory",
                )

            # Render everything first: a failure keeps the previous install.
            rendered: list[tuple[str, str]] = []
            try:
                for source_file in agent_files:
                    if not is_public_agent(source_file.name, public_agents):
                        continue
                    content = source_file.read_text(encoding="utf-8")
                    rendered.append(
                        (
                            source_file.stem,
                            _transform_agent(
                                content, source_file.stem, source_path=source_file
                            ),
                        )
                    )
                # Known legacy aliases from the pre-manifest bootstrap.
                codex_dir = _codex_config_dir()
                for legacy_name in sorted(
                    _adopted_legacy_agent_names(context, codex_dir, target_dir)
                ):
                    source_file = (
                        agents_source / f"{_LEGACY_AGENT_SOURCES[legacy_name]}.md"
                    )
                    if not source_file.is_file():
                        continue
                    content = source_file.read_text(encoding="utf-8")
                    rendered.append(
                        (
                            legacy_name,
                            _transform_agent(
                                content, legacy_name, source_path=source_file
                            ),
                        )
                    )
            except (OSError, ValueError) as error:
                message = (
                    f"Cannot render Codex role: {error}. "
                    "Restore the SKILL.md or fix the role's skills declaration."
                )
                context.logger.error(f"  ❌ {message}")
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=message,
                    errors=[message],
                )

            stale = remove_manifest_owned_assets(
                target_dir, _MANIFEST_FILENAME, ".toml"
            )
            if stale:
                context.logger.info(
                    f"  Removed {len(stale)} previously installed Codex agents"
                )

            installed_names: list[str] = []
            installed_files: list[Path] = []
            for name, transformed in rendered:
                target_file = target_dir / f"{name}.toml"
                target_file.write_text(transformed, encoding="utf-8")
                installed_names.append(name)
                installed_files.append(target_file)

            _write_manifest(target_dir, installed_names)

            context.logger.info(
                f"  Codex agents installed ({len(installed_names)} agents)"
            )

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(
                    f"Codex agents installed successfully ({len(installed_names)} agents)"
                ),
                installed_files=installed_files,
            )

        except Exception as e:
            context.logger.error(f"  Failed to install Codex agents: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex agents installation failed: {e!s}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only nWave-installed Codex agents using manifest.

        Reads the manifest to determine which agents were installed by nWave,
        removes only those (.toml files), and leaves user-created agents
        untouched. The manifest is also removed.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            context.logger.info("  Uninstalling Codex agents...")

            target_dir = _codex_agents_dir()
            manifest = _read_manifest(target_dir)

            if manifest is None:
                context.logger.info("  No Codex agents manifest found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No Codex agents to uninstall (no manifest found)",
                )

            installed_agents = manifest.get("installed_agents", [])
            removed_count = 0

            for agent_name in installed_agents:
                agent_file = target_dir / f"{agent_name}.toml"
                if agent_file.exists():
                    agent_file.unlink()
                    removed_count += 1

            manifest_path = target_dir / _MANIFEST_FILENAME
            if manifest_path.exists():
                manifest_path.unlink()

            context.logger.info(f"  Removed {removed_count} Codex agents")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Codex agents uninstalled ({removed_count} removed)",
            )

        except Exception as e:
            context.logger.error(f"  Failed to uninstall Codex agents: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex agents uninstallation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify Codex agents were installed correctly.

        Checks that each agent listed in the manifest has a valid .toml file.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            context.logger.info("  Verifying Codex agents...")

            target_dir = _codex_agents_dir()
            manifest = _read_manifest(target_dir)

            if manifest is None:
                agents_source = _find_agents_source(context)
                if agents_source is None:
                    context.logger.info("  No Codex agents to verify (none configured)")
                    return PluginResult(
                        success=True,
                        plugin_name=self.name,
                        message="No Codex agents configured, verification skipped",
                    )

                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Codex agents verification failed: manifest not found",
                    errors=["Manifest file .nwave-agents-manifest.json not found"],
                )

            installed_agents = manifest.get("installed_agents", [])
            if not isinstance(installed_agents, list) or not installed_agents:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Codex agents verification failed: empty population",
                    errors=["Manifest contains no installed Codex agents"],
                )

            agents_source = _find_agents_source(context)
            if agents_source is None:
                expected_agents: set[str] = set()
            else:
                public_agents = (
                    set()
                    if context.dev_mode
                    else load_public_agents(context.project_root / "nWave")
                )
                expected_agents = {
                    source_file.stem
                    for source_file in agents_source.glob("nw-*.md")
                    if is_public_agent(source_file.name, public_agents)
                }
            installed_set = set(installed_agents)
            permitted_agents = expected_agents | set(_LEGACY_AGENT_SOURCES)
            if not expected_agents.issubset(
                installed_set
            ) or not installed_set.issubset(permitted_agents):
                missing = sorted(expected_agents - installed_set)
                unexpected = sorted(installed_set - permitted_agents)
                errors = []
                if missing:
                    errors.append(
                        f"Manifest missing expected agents: {', '.join(missing)}"
                    )
                if unexpected:
                    errors.append(
                        f"Manifest contains unexpected agents: {', '.join(unexpected)}"
                    )
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Codex agents verification failed: population mismatch",
                    errors=errors,
                )

            missing_agents: list[str] = []
            verified_count = 0

            for agent_name in installed_agents:
                agent_toml = target_dir / f"{agent_name}.toml"
                if not agent_toml.exists():
                    missing_agents.append(f"{agent_name}.toml not found")
                else:
                    try:
                        document = _toml_reader.loads(
                            agent_toml.read_text(encoding="utf-8")
                        )
                    except (OSError, _toml_reader.TOMLDecodeError) as error:
                        missing_agents.append(
                            f"{agent_name}.toml is not loadable TOML: {error}"
                        )
                        continue
                    required = ("name", "description", "developer_instructions")
                    absent = [
                        field
                        for field in required
                        if not isinstance(document.get(field), str)
                        or not document[field].strip()
                    ]
                    if absent:
                        missing_agents.append(
                            f"{agent_name}.toml missing required fields: "
                            f"{', '.join(absent)}"
                        )
                        continue
                    verified_count += 1

            if missing_agents:
                context.logger.error(
                    f"  Codex agents verification failed: {len(missing_agents)} missing"
                )
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=(
                        f"Codex agents verification failed: "
                        f"{len(missing_agents)} agents missing .toml"
                    ),
                    errors=missing_agents,
                )

            context.logger.info(f"  Verified {verified_count} Codex agents")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Codex agents verification passed ({verified_count} agents)",
            )

        except Exception as e:
            context.logger.error(f"  Failed to verify Codex agents: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex agents verification failed: {e!s}",
                errors=[str(e)],
            )
