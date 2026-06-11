"""Per-tool boot + provisioning contracts as DATA (DESIGN D-2).

Adding a tool is adding a row, not a code branch. The registry holds the three
known tools (claude-code / codex / opencode). Copilot is deliberately ABSENT —
its absence is pinned by ``test_copilot_absent.py`` (DESIGN D-5, US-4).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolContract:
    """Everything the harness needs to smoke one tool, expressed as data.

    tool_id           — the ``--platform`` value, e.g. "claude-code".
    install_package   — npm package installed to acquire the CLI.
    boot_argv         — argv whose exit 0 proves the tool boots (version flag).
    isolation_env_var — env var that redirects the tool's config off the real
                        user tree (e.g. CLAUDE_CONFIG_DIR / CODEX_HOME /
                        OPENCODE_CONFIG_DIR). DESIGN D-6 / OQ-D4.
    required_artifact_globs — globs of REAL nWave files (not bare dirs) that
                        must exist under the isolated target after provisioning
                        (kills the codex false-PASS; SPIKE finding).
    """

    tool_id: str
    install_package: str
    boot_argv: tuple[str, ...]
    isolation_env_var: str
    required_artifact_globs: tuple[str, ...]


# The three supported tools, as DATA. Adding a fourth tool is adding a row here
# (DESIGN D-2). The keys are the ``--platform`` contract the matrix agrees on.
_REGISTRY: dict[str, ToolContract] = {
    "claude-code": ToolContract(
        tool_id="claude-code",
        install_package="@anthropic-ai/claude-code",
        boot_argv=("claude", "--version"),
        isolation_env_var="CLAUDE_CONFIG_DIR",
        required_artifact_globs=("agents/nw/*.md", "settings.json"),
    ),
    "codex": ToolContract(
        tool_id="codex",
        install_package="@openai/codex",
        boot_argv=("codex", "--version"),
        isolation_env_var="CODEX_HOME",
        # Verified against a real install (selftest run 27152144240): the codex
        # platform writes TOML agents + a hooks.json under CODEX_HOME.
        required_artifact_globs=("agents/nw-*.toml", "hooks.json"),
    ),
    "opencode": ToolContract(
        tool_id="opencode",
        install_package="opencode-ai",
        boot_argv=("opencode", "--version"),
        isolation_env_var="OPENCODE_CONFIG_DIR",
        # Verified against a real install (selftest run 27152144240): the
        # opencode platform writes a DES plugin + nWave skills under
        # OPENCODE_CONFIG_DIR.
        required_artifact_globs=("plugins/nwave-des.ts", "skills/nw-*/SKILL.md"),
    ),
}


# The supported tool ids, derived from the registry (single source of truth).
KNOWN_TOOLS: tuple[str, ...] = tuple(_REGISTRY)


class UnsupportedToolError(ValueError):
    """Raised when a lane is requested for a tool with no contract row."""


def tool_contract(tool_id: str) -> ToolContract:
    """Look up the contract for a supported tool.

    Raises ``UnsupportedToolError`` for an unknown tool (e.g. "copilot"), so a
    typo in the matrix — or a tool with no install path — fails loudly rather
    than silently smoke-passing.
    """
    try:
        return _REGISTRY[tool_id]
    except KeyError:
        raise UnsupportedToolError(
            f"unsupported tool {tool_id!r}: no contract row "
            f"(supported tools: {', '.join(KNOWN_TOOLS)})"
        ) from None
