"""What an agent's published spec DECLARES it can do -- and the REGISTER in
which a briefing may therefore speak about that agent's access.

RCA: docs/feature/fix-examiner-blindness-enforced/rca.md (root causes A + D).
``nwdes dispatch`` told every reader of a NON-CODE-FACING envelope that the
dispatched agent had no source / design / acceptance-test access "BY
CONSTRUCTION". Nothing enforced that: the predicate behind the claim was a
frozenset of agent NAMES, never computed from what the agent can actually DO,
while the examiner's own frontmatter granted unrestricted ``Read`` and
``Bash``. "By construction" is precisely the instruction to the orchestrator to
STOP verifying, so the unenforced constraint was also unchecked.

This module supplies the FACT the claim must be derived from, and the
vocabulary the framework was missing (root cause D) -- three mutually
exclusive registers:

``ENFORCED``
    The declared tools grant NOTHING that reaches the tree. An absolute ("by
    construction" / "cannot read") is EARNED here and only here: an ungranted
    tool is genuinely uncallable, so the declaration IS the mechanism.
``INSTRUCTED``
    The role is non-code-facing by INTENT, but its declared tools DO grant a
    source-reaching capability. The honest register: instructed, not
    prevented -- and the reader is owed a concrete place to confirm it.
``UNKNOWN``
    The spec was not found, or carries no parseable frontmatter. Degrade LOUD
    (GDP-6): "I looked and she is blind" and "I never looked" must not produce
    the same sentence. An unreadable capability is an INDETERMINATE, never an
    inferred one -- and NEVER the permissive ``ENFORCED``.

Two deliberate safety properties:

1. **Fail-safe classification.** A tool this module does not recognise is
   treated as SOURCE-REACHING. The only way to reach ``ENFORCED`` is for every
   declared tool to be on the known non-source-reaching list, so an unknown
   tool can never manufacture a false absolute.
2. **First EXISTING candidate wins -- no fall-through on a parse failure.**
   The checkout the caller POINTED AT is consulted before the installed tree
   (a resolver that ignores the checkout it was handed cannot be
   capability-derived in a dev tree). A candidate that exists but will not
   parse yields ``UNKNOWN``; it must NOT silently fall through to a different
   deployment's copy of the spec, which would answer a question about a file
   the caller never named.

The same frontmatter also carries the role's ``model:``, exposed as
``declared_model``. It is read HERE, from the same resolved file, because a
model answered from one copy of a spec and a capability answered from another
would describe two different roles under one name -- and the provider honours
the model on the argv, not the one a distant copy declares. A caller that finds
``None`` must degrade LOUD: supplying a default would put the model back in a
second place, which is exactly what this field removes.

An OMITTED ``tools:`` key is NOT an empty capability -- in Claude Code the
omission INHERITS every tool, i.e. maximally permissive. It resolves to
``INSTRUCTED``, never ``ENFORCED``.

Target-machine agnostic: Python + stdlib only. No git, no external CLI.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from nwave_ai.platform.assets import AssetOrigin, resolve_packaged_asset


class ClaimRegister(Enum):
    """The register a briefing may use when speaking about an agent's access."""

    ENFORCED = "enforced"
    INSTRUCTED = "instructed"
    UNKNOWN = "unknown"


#: The ONE owner of the typed reply-channel token set (brief.md §typed reply
#: channel). A reply-channel token names the SHAPE of a role's answer -- never
#: a tree permission and never a sandbox grant. Every consumer that used to
#: hold its own copy of the literal (the Claude adapter's
#: ``_STRUCTURED_OUTPUT_TOOL``, the Codex adapter's ``_METADATA_CAPABILITIES``,
#: the Codex installer's capability preamble) reads this set instead, so the
#: token can never drift out of step between them.
REPLY_CHANNEL_TOOLS: frozenset[str] = frozenset({"StructuredOutput"})

#: Tools that reach only the running product or the web -- never the tree.
#: Everything NOT named here (or matching a prefix below) is treated as
#: source-reaching, so an unrecognised tool can never yield a false absolute.
#: The reply-channel tokens are declared in native frontmatter so a provider
#: emits ``--json-schema structured_output``: they shape the reply's own
#: schema, never the tree, so declaring one must not move a role's register
#: off ENFORCED.
_NON_SOURCE_REACHING_TOOLS: frozenset[str] = (
    frozenset(
        {
            "WebFetch",
            "WebSearch",
            "AskUserQuestion",
            "TodoWrite",
        }
    )
    | REPLY_CHANNEL_TOOLS
)

#: Tool-name prefixes for the browser-driving MCP servers (the examiner's real
#: instrument): they exercise the running product, they do not read the tree.
_NON_SOURCE_REACHING_PREFIXES: tuple[str, ...] = (
    "mcp__playwright__",
    "mcp__plugin_playwright_",
)

#: Candidate 1 -- the checkout the caller pointed at (dev tree). Precedent:
#: the wave-entry cascade reads ``root / "nWave" / "agents"``.
_CHECKOUT_AGENT_SPEC_PARTS: tuple[str, ...] = ("nWave", "agents")

#: Legacy installed Claude deployment. The provider-neutral packaged copy is
#: considered before this compatibility location.
_INSTALLED_AGENT_SPEC_PARTS: tuple[str, ...] = ("agents", "nw")

_FRONTMATTER_DELIMITER = "---"
_TOOLS_KEY = "tools:"
_MODEL_KEY = "model:"


class UnbalancedToolSpecifier(ValueError):
    """A declared ``tools:`` field whose specifier parentheses do not close.

    Raised rather than guessed at: a half-read specifier registers no tool with
    the provider, so a role would silently lose a capability its spec granted.
    Callers that resolve a capability turn this into ``UNKNOWN`` -- never into
    the permissive ``INSTRUCTED``.
    """

    def __init__(self, raw: str) -> None:
        super().__init__(
            "WHAT: the tools field has unbalanced specifier parentheses: "
            f"{raw!r}. "
            "WHY: a declared entry may carry its own scope "
            "(Bash(code-fact:*)), and a half-read scope registers no tool "
            "at all, so the role would lose the capability in silence. "
            "HOW: close every '(' with a ')' on the tools line of the spec."
        )


def split_declared_tools(raw: str) -> tuple[str, ...]:
    """The declared ``tools:`` field split into entries, scopes kept whole.

    A declared entry may be a permission SPECIFIER whose scope contains commas
    (``Bash(code-fact:*)``), so the split honours
    parenthesis depth instead of every comma. Unbalanced parentheses raise
    ``UnbalancedToolSpecifier``.
    """
    entries: list[str] = []
    current: list[str] = []
    depth = 0
    for char in raw:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise UnbalancedToolSpecifier(raw)
        if char == "," and depth == 0:
            entries.append("".join(current))
            current = []
            continue
        current.append(char)
    if depth != 0:
        raise UnbalancedToolSpecifier(raw)
    entries.append("".join(current))
    return tuple(entry.strip() for entry in entries if entry.strip())


def provider_tool_name(declared: str) -> str:
    """The bare provider tool name inside one declared capability entry.

    ``Bash(code-fact:*)`` names the tool ``Bash``; a bare name is its own
    answer. The two are not interchangeable at the provider boundary: measured
    against Claude Code 2.1.261 under ``--restricted`` (2026-09-05), a specifier
    passed where a tool NAME is expected registers no tool at all, while the
    bare name passed where the SCOPE is expected grants the whole tool.
    """
    return declared.partition("(")[0].strip()


def tool_reaches_source(tool: str) -> bool:
    """True when ``tool`` can reach the repository tree.

    Fail-safe: an unrecognised tool answers True. Only a tool KNOWN to be
    confined to the running product / the web answers False.
    """
    if tool in _NON_SOURCE_REACHING_TOOLS:
        return False
    return not tool.startswith(_NON_SOURCE_REACHING_PREFIXES)


@dataclass(frozen=True)
class DeclaredCapability:
    """An agent's declared capability, plus the register it licenses.

    ``declared_tools`` is ``None`` for BOTH "spec unreadable" and "no ``tools:``
    key" -- ``register`` is what distinguishes them (``UNKNOWN`` vs
    ``INSTRUCTED``), so the two are never conflated by a reader.

    ``declared_model`` is the frontmatter ``model:`` value, or ``None`` when the
    spec declares none. It is read HERE, from the same frontmatter and the same
    resolved file the tools come from, so a role's model and a role's capability
    can never be answered from two different copies of its spec. A caller that
    needs a model and finds ``None`` must degrade LOUD; supplying a default
    would put the model back in a second place, which is the defect this field
    exists to remove.
    """

    register: ClaimRegister
    spec_path: Path | None
    declared_tools: tuple[str, ...] | None
    declared_model: str | None = None

    @classmethod
    def unknown(cls, spec_path: Path | None) -> DeclaredCapability:
        """The capability could not be determined -- degrade LOUD."""
        return cls(
            register=ClaimRegister.UNKNOWN,
            spec_path=spec_path,
            declared_tools=None,
            declared_model=None,
        )

    @classmethod
    def inherits_every_tool(
        cls, spec_path: Path, model: str | None = None
    ) -> DeclaredCapability:
        """A spec with NO ``tools:`` key: maximally permissive, never blind."""
        return cls(
            register=ClaimRegister.INSTRUCTED,
            spec_path=spec_path,
            declared_tools=None,
            declared_model=model,
        )

    @classmethod
    def from_declared_tools(
        cls, spec_path: Path, tools: tuple[str, ...], model: str | None = None
    ) -> DeclaredCapability:
        """Derive the register from the tools the spec actually declares."""
        reaches = any(tool_reaches_source(tool) for tool in tools)
        register = ClaimRegister.INSTRUCTED if reaches else ClaimRegister.ENFORCED
        return cls(
            register=register,
            spec_path=spec_path,
            declared_tools=tools,
            declared_model=model,
        )

    @property
    def source_reaching_tools(self) -> tuple[str, ...]:
        """The declared tools that reach the tree (empty when none/unknown)."""
        if self.declared_tools is None:
            return ()
        return tuple(tool for tool in self.declared_tools if tool_reaches_source(tool))

    def spec_reference(self, agent: str) -> str:
        """A short, falsifiable pointer at the spec the register was read from.

        The last three path components (``nWave/agents/<agent>.md`` in a
        checkout, ``agents/nw/<agent>.md`` when installed) -- enough for the
        reader to open the exact file, without pasting a host-specific absolute
        path into a briefing that travels.
        """
        if self.spec_path is None:
            return f"{'/'.join(_CHECKOUT_AGENT_SPEC_PARTS)}/{agent}.md (not found)"
        return "/".join(self.spec_path.parts[-3:])


def _default_claude_dir() -> Path:
    """The Claude configuration directory (``CLAUDE_CONFIG_DIR`` or ``~/.claude``)."""
    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    if configured:
        return Path(configured)
    return Path.home() / ".claude"


def _frontmatter_lines(text: str) -> tuple[str, ...] | None:
    """The YAML frontmatter block's lines, or ``None`` when there is no block.

    A spec whose first non-empty line is not the ``---`` delimiter, or whose
    block is never closed, has no parseable frontmatter -- the ``UNKNOWN``
    case, stated rather than guessed at.
    """
    lines = text.splitlines()
    opened = False
    collected: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not opened:
            if not stripped:
                continue
            if stripped != _FRONTMATTER_DELIMITER:
                return None
            opened = True
            continue
        if stripped == _FRONTMATTER_DELIMITER:
            return tuple(collected)
        collected.append(line)
    return None


def _declared_tools(frontmatter: tuple[str, ...]) -> tuple[str, ...] | None:
    """The ``tools:`` value as a tuple, or ``None`` when the key is absent."""
    for line in frontmatter:
        if not line.startswith(_TOOLS_KEY):
            continue
        return split_declared_tools(line[len(_TOOLS_KEY) :])
    return None


def _declared_model(frontmatter: tuple[str, ...]) -> str | None:
    """The ``model:`` value, or ``None`` when the key is absent or empty."""
    for line in frontmatter:
        if not line.startswith(_MODEL_KEY):
            continue
        return line[len(_MODEL_KEY) :].strip() or None
    return None


def _capability_from_spec(spec_path: Path) -> DeclaredCapability:
    """Read ONE spec file into a capability. Never falls through on failure."""
    try:
        text = spec_path.read_text(encoding="utf-8")
    except OSError:
        return DeclaredCapability.unknown(spec_path)
    frontmatter = _frontmatter_lines(text)
    if frontmatter is None:
        return DeclaredCapability.unknown(spec_path)
    try:
        tools = _declared_tools(frontmatter)
    except UnbalancedToolSpecifier:
        # A field nobody could read establishes no capability. UNKNOWN, never
        # the permissive INSTRUCTED that an OMITTED key licenses.
        return DeclaredCapability.unknown(spec_path)
    model = _declared_model(frontmatter)
    if tools is None:
        return DeclaredCapability.inherits_every_tool(spec_path, model)
    return DeclaredCapability.from_declared_tools(spec_path, tools, model)


def _entry_is_present(path: Path) -> bool:
    """Whether a candidate was named, including an unreadable dangling link."""
    return path.exists() or path.is_symlink()


def resolve_declared_capability(
    agent: str,
    *,
    repo_root: Path,
    claude_dir: Path | None = None,
    framework_root: Path | None = None,
) -> DeclaredCapability:
    """Resolve ``agent``'s declared capability from its published spec.

    A supplied framework root owns its public roles; otherwise the invocation
    repository is first. The FIRST candidate that EXISTS decides -- including
    deciding ``UNKNOWN`` when it exists but will not parse. Falling through on
    a parse failure would answer with a different deployment's copy of the
    spec, i.e. answer a question the caller never asked.
    """
    # A runtime may qualify a role as ``role#competence`` to select its model.
    # The qualifier is configuration identity, not an agent filename: both
    # provider adapters must load the one published base-role specification.
    # ``qualify_role_id`` rejects ``#`` in either component, so taking the
    # first component here cannot reinterpret a valid role name.
    base_agent = agent.partition("#")[0]

    if framework_root is not None:
        framework = framework_root.joinpath(
            *_CHECKOUT_AGENT_SPEC_PARTS, f"{base_agent}.md"
        )
        if _entry_is_present(framework):
            return _capability_from_spec(framework)

    checkout = repo_root.joinpath(*_CHECKOUT_AGENT_SPEC_PARTS, f"{base_agent}.md")
    if _entry_is_present(checkout):
        return _capability_from_spec(checkout)

    packaged = resolve_packaged_asset(f"nWave/agents/{base_agent}.md", start=repo_root)
    if packaged.origin is AssetOrigin.AMBIGUOUS:
        # The caller named a tree whose public role differs from the packaged
        # runtime. Picking a Claude-profile copy after that refusal would hide
        # the exact source/install disagreement the shared resolver detected.
        return DeclaredCapability.unknown(None)
    if packaged.path is not None and _entry_is_present(packaged.path):
        return _capability_from_spec(packaged.path)

    installed_root = claude_dir if claude_dir is not None else _default_claude_dir()
    legacy = installed_root.joinpath(*_INSTALLED_AGENT_SPEC_PARTS, f"{base_agent}.md")
    if _entry_is_present(legacy):
        return _capability_from_spec(legacy)
    return DeclaredCapability.unknown(None)
