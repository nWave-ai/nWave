"""Shared utilities for OMP (oh-my-pi) installer plugins.

OMP is a Markdown-native host: task agents are ``<config-root>/agent/agents/
*.md`` with YAML frontmatter (required ``name``/``description``, body as the
system prompt) and skills are ``<config-root>/agent/skills/<name>/SKILL.md``.

Two projection laws shape everything in this module:

1. **Never widen a capability.** Claude tool names map onto OMP's canonical
   lowercase builtin names one-to-one; a declared entry with no OMP form is
   DROPPED and reported, never approximated. ``StructuredOutput`` is a reply
   channel (``REPLY_CHANNEL_TOOLS``), not an executable tool: it is excluded
   from ``tools`` and expressed as an ``output`` schema projected from the
   canonical model envelope.

2. **Deliver each skill once.** OMP natively injects skills listed in an
   agent's ``autoloadSkills`` frontmatter. Role bodies are therefore NOT
   inlined (unlike the Codex/OpenCode self-contained snapshots); the
   ``skills:`` preload list becomes ``autoloadSkills`` naming only the PUBLIC
   skills actually installed for OMP, and ``Invoke Skill(X)`` directives in
   the body become ``Read skill://X/SKILL.md`` so conditional loads resolve
   through OMP's own skill protocol.

Why the OMP-native skills route and not the shared ``~/.agents/skills`` tree
(the "no second copy" question): that tree is owned by CodexSkillsPlugin under
a strict single-writer manifest that refuses foreign ``nw-*`` directories, so
a second writer there cannot install OR uninstall safely. The shared-consumer
reuse condition fails; each host keeps its own manifest-owned copy.
"""

from __future__ import annotations

import json
import os
import re

from nwave_ai.platform.capability import REPLY_CHANNEL_TOOLS, split_declared_tools
from nwave_ai.platform.role_envelope import COVERED_ROLES, schema_for
from scripts.install.plugins.opencode_common import (
    parse_frontmatter,
    render_frontmatter,
)
from scripts.shared.install_paths import omp_agents_dir, omp_skills_dir
from scripts.shared.platform_contracts import (
    OMP_AGENT_OMITTED_FIELDS,
    nwdes_cli_role_tools,
)


#: Canonical OMP builtin tool names are lowercase (upstream
#: ``tools/builtin-names.ts``). This table maps every Claude tool name nWave
#: roles actually declare onto its true OMP capability. ``WebFetch`` and
#: ``Skill`` are expressed through OMP's ``read`` (the read tool fetches URLs
#: and resolves ``skill://`` URIs); ``Agent`` is OMP's ``task`` dispatch.
_TOOL_NAME_MAP: dict[str, str] = {
    "Read": "read",
    "Write": "write",
    "Edit": "edit",
    "Bash": "bash",
    "Glob": "glob",
    "Grep": "grep",
    "Task": "task",
    "WebSearch": "web_search",
    "WebFetch": "read",
    "Skill": "read",
    "Agent": "task",
}

#: ``Invoke (ONE )?Skill(name)`` directives in role bodies -- ON-TRIGGER
#: suffixes that follow the match are preserved verbatim.
_SKILL_INVOKE_PATTERN = re.compile(
    r"Invoke (?:ONE )?Skill\(([A-Za-z0-9][A-Za-z0-9._-]*)\)"
)

#: Role ids the canonical model envelope covers with a role-specific typed
#: payload. Roles outside this set that declare ``StructuredOutput`` get the
#: envelope's universal outcome floor (every role owes accepted/refused plus a
#: non-empty diagnostic) and an explicit capability-ceiling report -- never an
#: invented typed payload.
_ENVELOPE_COVERED_ROLES = COVERED_ROLES


class OmpProfileNotSupported(ValueError):
    """An OMP named profile is active; the installer only serves the default.

    OMP resolves ``OMP_PROFILE`` (canonical, wins even when empty) over
    ``PI_PROFILE`` (legacy). A named profile relocates the config root in a
    layout this installer does not guess, so the honest move is to refuse
    with an explicit message rather than silently write the default root.
    """


def require_default_profile() -> None:
    """Refuse when an OMP named profile is selected.

    Raises:
        OmpProfileNotSupported: ``OMP_PROFILE`` is defined and non-empty, or
            ``OMP_PROFILE`` is undefined while legacy ``PI_PROFILE`` is
            non-empty (upstream precedence: OMP_PROFILE wins even when empty,
            so an empty OMP_PROFILE explicitly selects the default profile).
    """
    if "OMP_PROFILE" in os.environ:
        if os.environ["OMP_PROFILE"]:
            raise OmpProfileNotSupported(
                f"OMP_PROFILE={os.environ['OMP_PROFILE']!r}: this installer only "
                "supports the OMP default profile; named-profile config roots "
                "are not projected. Unset OMP_PROFILE or install manually."
            )
        return
    legacy = os.environ.get("PI_PROFILE", "")
    if legacy:
        raise OmpProfileNotSupported(
            f"PI_PROFILE={legacy!r}: this installer only supports the OMP "
            "default profile; named-profile config roots are not projected. "
            "Unset PI_PROFILE or install manually."
        )


def map_declared_tools(
    tools_value: str | list | None,
) -> tuple[list[str], list[str], list[str], bool]:
    """Project a role's declared ``tools`` onto OMP's canonical toolset.

    Args:
        tools_value: The raw ``tools`` frontmatter value (CSV string, YAML
            list, or None).

    Returns:
        A 4-tuple ``(mapped, dropped_scoped, dropped_unmapped,
        structured_output)``:

        - ``mapped``: lowercase OMP builtin names, declaration order,
          deduplicated.
        - ``dropped_scoped``: declared entries carrying a scope (e.g.
          scoped ``Bash(...:*)`` grants). OMP tool lists are bare names with no
          grant scope; projecting one as bare ``bash`` would hand the role
          the whole shell it was deliberately not given, so the capability
          is OMITTED and reported instead.
        - ``dropped_unmapped``: declared names with no OMP equivalent.
        - ``structured_output``: whether the reply-channel token
          ``StructuredOutput`` was declared. The token names the SHAPE of
          the role's answer, never a tool; callers project it as an
          ``output`` schema.
    """
    if tools_value is None:
        return [], [], [], False

    if isinstance(tools_value, list):
        entries = [str(tool).strip() for tool in tools_value if str(tool).strip()]
    else:
        entries = list(split_declared_tools(str(tools_value)))

    mapped: list[str] = []
    dropped_scoped: list[str] = []
    dropped_unmapped: list[str] = []
    structured_output = False

    for entry in entries:
        bare = entry.partition("(")[0].strip()
        scoped = entry != bare
        if bare in REPLY_CHANNEL_TOOLS:
            structured_output = True
            continue
        omp_name = _TOOL_NAME_MAP.get(bare)
        if omp_name is None:
            if scoped:
                dropped_scoped.append(entry)
            else:
                dropped_unmapped.append(bare)
            continue
        if scoped:
            dropped_scoped.append(entry)
            continue
        if omp_name not in mapped:
            mapped.append(omp_name)

    return mapped, dropped_scoped, dropped_unmapped, structured_output


def canonical_output_schema(role_id: str) -> tuple[dict | None, bool]:
    """Return the parameter-free canonical envelope schema for *role_id*.

    The envelope's per-call closures (``max_product_values``,
    ``defect_values``, semantic-task variants) are CALL facts; an installed
    agent file can only carry the parameter-free law. Projecting more would
    fake a closure only a call can state.

    Args:
        role_id: The role's published identity (``nw-`` stem).

    Returns:
        ``(schema, covered)``. ``covered`` is True when the envelope holds a
        role-specific typed payload for *role_id*; False means only the
        universal outcome floor applies -- the caller must report that
        capability ceiling rather than present it as a role contract.
    """
    covered = role_id in _ENVELOPE_COVERED_ROLES
    schema = schema_for(role_id)
    return json.loads(schema), covered


def translate_skill_invocations(body: str) -> str:
    """Rewrite ``Invoke Skill(X)`` directives into OMP skill-protocol reads.

    ``skill://<name>/SKILL.md`` is OMP's own resolution path (it works for
    every discovered skill regardless of which provider root installed it),
    so the rewrite never hardcodes an install directory. ON-TRIGGER
    suffixes are preserved; a replacement callable keeps literal backslashes
    in ``body`` out of regex backreference interpretation.
    """
    return _SKILL_INVOKE_PATTERN.sub(
        lambda match: f"Read `skill://{match.group(1)}/SKILL.md`", body
    )


def missing_preload_skills(
    frontmatter: dict, installed_public_skills: frozenset[str]
) -> list[str]:
    """The role's declared mandatory preload names missing from the install.

    Frontmatter ``skills`` are MANDATORY knowledge (builder/source policy):
    a public role whose declared preload the public tree does not ship is
    not a fully usable role. This is a finite closed-set check (declared
    names vs installed public names), never a quality gate.

    Returns:
        Declared preload names, in declaration order, that the OMP install
        does not carry. Empty means the role's knowledge closure is complete.
    """
    preload = frontmatter.get("skills") or []
    if isinstance(preload, str):
        preload = [preload]
    requested = [str(name).strip() for name in preload if str(name).strip()]
    return [name for name in requested if name not in installed_public_skills]


def project_agent_frontmatter(
    frontmatter: dict, *, installed_public_skills: frozenset[str]
) -> tuple[dict, list[str]]:
    """Project one role's Claude frontmatter onto the OMP agent schema.

    Keeps ``name``/``description``; omits ``model`` (every nWave declaration
    is a Claude alias, and an OMP selector would route the role away from
    the user's configured model -- omission inherits the parent's active
    model), ``maxTurns`` (no OMP equivalent; the absent limit is reported,
    never faked), and ``skills`` (replaced by ``autoloadSkills`` naming only
    PUBLIC installed skills, so each skill is delivered once natively).

    Args:
        frontmatter: Parsed Claude frontmatter dict.
        installed_public_skills: Skill names the OMP skills plugin installs
            (public catalog only). ``autoloadSkills`` may only name skills
            OMP will actually discover.

    Returns:
        (projected frontmatter dict, report lines). Report lines are
        explicit third states: dropped scoped/unmapped tools, missing
        maxTurns, preload skills not projected.
    """
    reports: list[str] = []
    agent_name = str(frontmatter.get("name", "<unnamed>"))

    mapped, dropped_scoped, dropped_unmapped, structured_output = map_declared_tools(
        frontmatter.get("tools")
    )
    cli_tools = nwdes_cli_role_tools(agent_name)
    if cli_tools:
        mapped, dropped_scoped, dropped_unmapped, structured_output = (
            map_declared_tools(list(cli_tools))
        )
    for entry in dropped_scoped:
        reports.append(
            f"{agent_name}: scoped tool grant '{entry}' has no OMP form "
            "(OMP tool lists are bare names); capability omitted, not widened"
        )
    for name in dropped_unmapped:
        reports.append(f"{agent_name}: tool '{name}' has no OMP equivalent; omitted")

    projected: dict = {
        key: value
        for key, value in frontmatter.items()
        if key not in OMP_AGENT_OMITTED_FIELDS
        and key not in {"tools", "name", "description"}
    }
    projected["name"] = frontmatter["name"]
    projected["description"] = frontmatter["description"]

    if "maxTurns" in frontmatter:
        reports.append(
            f"{agent_name}: maxTurns={frontmatter['maxTurns']} not projected "
            "(no per-agent turn cap in the OMP agent schema); the declared "
            "limit is absent, not enforced"
        )

    # OMP grants the default FULL toolset when ``tools`` is absent, so an
    # explicit list is always emitted -- including an empty one for a
    # reply-channel-only role (OMP then grants exactly the yield channel).
    projected["tools"] = mapped
    if cli_tools:
        projected.pop("output", None)

    preload = frontmatter.get("skills") or []
    if isinstance(preload, str):
        preload = [preload]
    requested = [str(name).strip() for name in preload if str(name).strip()]
    missing = missing_preload_skills(frontmatter, installed_public_skills)
    autoload = [name for name in requested if name not in missing]
    if missing:
        reports.append(
            f"{agent_name}: preload skills not installed for OMP (private or "
            f"uncatalogued), excluded from autoloadSkills: {', '.join(missing)}"
        )
    if autoload or requested:
        projected["autoloadSkills"] = autoload

    if structured_output:
        schema, covered = canonical_output_schema(agent_name)
        projected["output"] = schema
        if not covered:
            reports.append(
                f"{agent_name}: no role-specific typed envelope exists; "
                "output carries only the universal outcome schema "
                "(accepted/refused + diagnostic) -- capability ceiling, not "
                "a payload contract"
            )

    return projected, reports


def project_agent_content(
    content: str, *, installed_public_skills: frozenset[str]
) -> tuple[str, list[str]]:
    """Full projection pipeline: Claude role markdown -> OMP agent markdown.

    Pipeline: parse frontmatter + body, project frontmatter, translate
    ``Invoke Skill(X)`` directives to ``skill://`` reads. Host path rewrites
    are the caller's concern (they also apply to skill bodies).

    Raises:
        ValueError: The role file has no frontmatter, unparseable
            frontmatter, or lacks the non-empty string ``name``/
            ``description`` OMP's ``parseAgentFields`` requires -- installing
            it would produce a file OMP skips with a discovery warning, so
            the installer refuses loudly instead.
    """
    frontmatter, body = parse_frontmatter(content)
    name = frontmatter.get("name")
    description = frontmatter.get("description")
    if (
        not frontmatter
        or not isinstance(name, str)
        or not name
        or not isinstance(description, str)
        or not description
    ):
        raise ValueError(
            "role file has no parsable frontmatter with non-empty string "
            "name and description; OMP discovery would skip it"
        )
    projected, reports = project_agent_frontmatter(
        frontmatter, installed_public_skills=installed_public_skills
    )
    rendered = render_frontmatter(projected)
    return rendered + translate_skill_invocations(body), reports


__all__ = [
    "OmpProfileNotSupported",
    "canonical_output_schema",
    "map_declared_tools",
    "omp_agents_dir",
    "omp_skills_dir",
    "parse_frontmatter",
    "project_agent_content",
    "project_agent_frontmatter",
    "render_frontmatter",
    "require_default_profile",
    "translate_skill_invocations",
]
