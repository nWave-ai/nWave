"""Shared public/private agent filtering logic.

Used by installer plugins and build scripts to exclude private agents
and their skills from public distributions. The source of truth is
``nWave/framework-catalog.yaml`` where each agent has a ``public`` field.

Fail-closed semantics (default): when the catalog file is missing,
``load_public_agents`` raises ``CatalogNotFoundError``. When the catalog
cannot be parsed, it raises ``CatalogParseError``. Pass ``strict=False``
for backward compatibility (returns empty set on missing catalog).

**Important**: PyYAML must be installed. If missing, ``load_public_agents``
raises ``RuntimeError`` instead of silently returning an empty set (which
would cause all agents to be treated as public -- a security leak).
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CatalogNotFoundError(FileNotFoundError):
    """Raised when the framework-catalog.yaml file is missing."""


class CatalogParseError(ValueError):
    """Raised when the framework-catalog.yaml file cannot be parsed."""


# ---------------------------------------------------------------------------
# Public shared skills — load-bearing skills with no owning public agent
# ---------------------------------------------------------------------------

# Skill ownership is derived from agent frontmatter ``skills:`` lists. A skill
# that is depended on by a public artifact (a public command-skill body, a
# public agent's Skill Loading Strategy table, or a shared methodology
# reference) but is NOT declared in any public agent's frontmatter would be
# dropped by the ownership-only strip as "uncatalogued" — shipping a public
# package with a dangling skill reference (RCA Q4,
# docs/analysis/rca-installer-private-skill-leak-2026-05-20.md).
#
# This allow-list is the SSOT for those load-bearing public skills: every
# entry here is public methodology that public installs depend on and that
# the privacy strip MUST preserve. The strip removes private work; an
# uncatalogued public-methodology skill is not private work.
PUBLIC_SHARED_SKILLS: frozenset[str] = frozenset(
    {
        # Auto microkernel (2026-08-08): loaded by the installed product's
        # hook spine directly, not via any owning public agent's frontmatter
        # skills list -- same load-bearing pattern as above.
        "nw-auto",
        "nw-role-invocation",
        "nw-jtbd-core",
        "nw-jtbd-interviews",
        "nw-jtbd-opportunity-scoring",
        "nw-jtbd-workflow-selection",
        # Language PBT deep dives are selected exactly one-at-a-time by the
        # acceptance-designer's loading table, not frontmatter-preloaded.
        "nw-pbt-dotnet",
        "nw-pbt-erlang-elixir",
        "nw-pbt-go",
        "nw-pbt-haskell",
        "nw-pbt-jvm",
        "nw-pbt-python",
        "nw-pbt-rust",
        "nw-pbt-typescript",
        # FP language idioms are the SAME load-bearing pattern, one row
        # below: resolved by target language from the table at
        # nw-code-design-fp/SKILL.md, not frontmatter-preloaded by
        # nw-functional-software-crafter despite declaring it as `agent:`
        # in their own frontmatter (2026-08-24, F-FP-LANGUAGE-SKILLS-
        # SHIPPED-UNREACHABLE).
        "nw-fp-clojure",
        "nw-fp-erlang-elixir",
        "nw-fp-fsharp",
        "nw-fp-haskell",
        "nw-fp-kotlin",
        "nw-fp-rust",
        "nw-fp-scala",
        "nw-fp-typescript",
        "nw-persona-jtbd-analysis",
        "nw-spike-methodology",
        "nw-speculative-dispatch",
        "nw-tdd-cross-language",
        # Optional remote System One methodology, available to every installed
        # host but never preloaded into a role. It is used by default when its
        # API key is available and falls back locally when it is not.
        "nw-typesafe-system-one",
        # Decomposed command-design-patterns modules (2026-06-17): the public
        # core nw-command-design-patterns (load-bearing for the public
        # agent-builder via *optimize-command) composes these via its loading
        # table; they are routed via-core, not frontmatter-owned, so the
        # ownership strip would drop them — same load-bearing pattern as above.
        "nw-command-design-patterns-classification",
        "nw-command-design-patterns-reduction",
        "nw-command-design-patterns-authoring",
    }
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_yaml():
    """Import and return the yaml module, or raise RuntimeError."""
    try:
        import yaml

        return yaml
    except ModuleNotFoundError:
        msg = (
            "PyYAML is required for agent filtering but is not installed. "
            "Install it with: pip install pyyaml"
        )
        raise RuntimeError(msg) from None


def _load_catalog(nwave_dir: Path, *, strict: bool = True) -> dict | None:
    """Load and parse framework-catalog.yaml, returning the parsed dict.

    Returns ``None`` when the file is missing and ``strict=False``.
    Raises ``CatalogNotFoundError`` when missing and ``strict=True``.
    Raises ``CatalogParseError`` when the file exists but cannot be parsed
    and ``strict=True``.
    """
    catalog_path = nwave_dir / "framework-catalog.yaml"
    if not catalog_path.exists():
        if strict:
            msg = f"Framework catalog not found: {catalog_path}"
            raise CatalogNotFoundError(msg)
        return None

    yaml = _ensure_yaml()

    try:
        with catalog_path.open(encoding="utf-8") as fh:
            catalog = yaml.safe_load(fh)
    except Exception as exc:
        if strict:
            msg = f"Failed to parse YAML catalog at {catalog_path}: {exc}"
            raise CatalogParseError(msg) from exc
        return None

    if not isinstance(catalog, dict) or "agents" not in catalog:
        if strict:
            msg = (
                f"Catalog at {catalog_path} is missing the 'agents' section "
                f"or is not a valid YAML mapping"
            )
            raise CatalogParseError(msg)
        return None

    return catalog


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_agent_name(raw: str) -> str:
    """Normalize agent filename to bare name: ``'nw-foo-reviewer.md'`` -> ``'foo-reviewer'``.

    Strips the ``nw-`` prefix and ``.md`` suffix. Idempotent on bare names.
    """
    return raw.removeprefix("nw-").removesuffix(".md")


def base_agent_name(name: str) -> str:
    """Extract base agent from reviewer: ``'foo-reviewer'`` -> ``'foo'``.

    Returns the name unchanged if it does not end with ``-reviewer``.
    """
    return name.removesuffix("-reviewer")


def load_public_agents(nwave_dir: Path, *, strict: bool = True) -> set[str]:
    """Read framework-catalog.yaml and return the set of public agent names.

    An agent is public when its ``public`` field is not ``False``.
    Missing ``public`` field defaults to public.

    When ``strict=True`` (default -- fail-closed):
      - Missing catalog raises ``CatalogNotFoundError``
      - Corrupted catalog raises ``CatalogParseError``

    When ``strict=False`` (backward compatibility):
      - Returns an empty set when the catalog file is missing or cannot
        be parsed (callers treat empty set as "include everything").
    """
    catalog = _load_catalog(nwave_dir, strict=strict)
    if catalog is None:
        return set()

    return {
        name
        for name, info in catalog.get("agents", {}).items()
        if info.get("public") is not False
    }


def scrub_removed_skill_references(
    agents_dir: Path,
    target_dir: Path,
    removed_skills: set[str],
    public_agents: set[str],
) -> list[str]:
    """Drop ``skills:`` frontmatter entries naming a skill the strip removed.

    WHY: a surviving public agent whose frontmatter still names a removed
    skill ships a dangling instruction. The public user installs an agent
    that points at a directory the package does not contain, and nothing
    fails loudly -- the reference is inert at load time, so the defect
    surfaces only as missing behaviour.

    The edit is line-scoped on purpose: a YAML round-trip would reformat
    every surviving public agent file, turning a two-line correction into
    an unreviewable diff. Only the matching list-item lines are dropped;
    the rest of the file, frontmatter included, is left byte-identical.

    Returns one report string per scrubbed reference.
    """
    if not removed_skills or not agents_dir.exists():
        return []

    scrubbed: list[str] = []
    for agent_file in sorted(agents_dir.glob("nw-*.md")):
        if not is_public_agent(agent_file.name, public_agents):
            continue
        text = agent_file.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        if end == -1:
            continue

        head, tail = text[:end], text[end:]
        kept_lines: list[str] = []
        in_skills = False
        dropped: list[str] = []
        for line in head.split("\n"):
            stripped = line.strip()
            if not line.startswith((" ", "\t")) and stripped.endswith(":"):
                in_skills = stripped == "skills:"
            elif in_skills and stripped.startswith("- "):
                name = stripped[2:].strip().strip("\"'")
                key = name if name.startswith("nw-") else f"nw-{name}"
                if key in removed_skills:
                    dropped.append(key)
                    continue
            kept_lines.append(line)

        if not dropped:
            continue
        agent_file.write_text("\n".join(kept_lines) + tail, encoding="utf-8")
        rel = agent_file.relative_to(target_dir)
        scrubbed.extend(f"{rel} no longer references {name}" for name in dropped)

    return scrubbed


def is_public_command(metadata: dict, public_agents: set[str]) -> bool:
    """A command is public unless all of its declared agents are non-public."""
    agents = metadata.get("agents") or []
    return not agents or any(
        agent.replace("_", "-") in public_agents for agent in agents
    )


def load_public_commands(nwave_dir: Path) -> set[str]:
    """Return catalog command names using the task roster's hyphen spelling."""
    catalog = _load_catalog(nwave_dir)
    public_agents = {
        name
        for name, metadata in catalog.get("agents", {}).items()
        if metadata.get("public") is not False
    }
    return {
        name.replace("_", "-")
        for name, metadata in catalog.get("commands", {}).items()
        if is_public_command(metadata, public_agents)
    }


def load_private_agents(nwave_dir: Path) -> set[str]:
    """Read framework-catalog.yaml and return agents where ``public`` is ``False``.

    Always uses strict mode -- missing or corrupted catalog raises.
    """
    catalog = _load_catalog(nwave_dir, strict=True)
    if catalog is None:
        return set()

    return {
        name
        for name, info in catalog.get("agents", {}).items()
        if info.get("public") is False
    }


def load_private_skills(nwave_dir: Path, *, strict: bool = True) -> set[str]:
    """Read framework-catalog.yaml and return skills declared ``public: false``.

    Skill visibility is DERIVED by default (a skill is public when at least
    one owning agent is public -- see :func:`is_public_skill`). The optional
    top-level ``skills:`` catalog section is the one place that can OVERRIDE
    that derivation for a single skill, so that knowledge held to be a
    competitive advantage stays out of the public repository and the PyPI
    wheel even while a public agent owns it.

    Keys are skill DIRECTORY names as they appear in ``nWave/skills/``
    (``nw-`` prefixed). Only ``public: false`` is an override; ``public:
    true`` and an absent entry both mean "derive as usual".

    With ``strict=False`` a missing or unparseable catalog yields an empty
    set. That is not a silent pass: every release caller loads the same
    catalog strictly through :func:`load_public_agents` first and aborts
    with ``unverifiable catalog`` before any visibility decision is made.
    """
    catalog = _load_catalog(nwave_dir, strict=strict)
    if catalog is None:
        return set()

    skills_section = catalog.get("skills")
    if not isinstance(skills_section, dict):
        return set()

    return {
        name
        for name, info in skills_section.items()
        if isinstance(info, dict) and info.get("public") is False
    }


def load_all_agents(nwave_dir: Path) -> dict[str, dict]:
    """Read framework-catalog.yaml and return full agent metadata dict.

    Returns a dict keyed by agent name with each value being the agent's
    metadata dict from the catalog. Always uses strict mode.
    """
    catalog = _load_catalog(nwave_dir, strict=True)
    if catalog is None:
        return {}

    return dict(catalog.get("agents", {}))


def is_public_agent(agent_file_name: str, public_agents: set[str]) -> bool:
    """Check whether an agent file belongs to a public agent.

    Strips the ``nw-`` prefix and ``.md`` suffix to derive the agent name.
    The agent MUST be explicitly listed in public_agents to be distributed.
    Agents on disk but not in the catalog are NOT distributed (fail-closed).

    When *public_agents* is empty (catalog not loaded), returns ``True``
    for every file (backward compatibility).
    """
    if not public_agents:
        return True
    agent_name = agent_file_name.removeprefix("nw-").removesuffix(".md")
    return agent_name in public_agents


def build_ownership_map(agents_dir: Path) -> dict[str, set[str]]:
    """Build skill-directory-name -> set-of-agent-names mapping from frontmatter.

    Parses each ``nw-*.md`` agent file's YAML frontmatter and extracts
    the ``skills`` list. Returns a dict mapping each skill **directory name**
    (nw-prefixed, as it appears on disk) to the set of agent names that
    reference it.

    Skill keys are nw-prefixed (matching directory names in nWave/skills/).
    Agent values are bare names without nw- prefix (matching public_agents set).

    Example::

        {
            "nw-tdd-methodology": {"software-crafter", "functional-software-crafter"},
            "nw-five-whys-methodology": {"troubleshooter"},
        }
    """
    if not agents_dir.exists():
        return {}

    try:
        import yaml
    except ModuleNotFoundError:
        return {}

    ownership: dict[str, set[str]] = {}

    for agent_file in sorted(agents_dir.glob("nw-*.md")):
        agent_name = agent_file.stem.removeprefix("nw-")
        frontmatter = _parse_frontmatter(agent_file, yaml)
        if frontmatter is None:
            continue
        skills = frontmatter.get("skills")
        if not isinstance(skills, list):
            continue
        for skill in skills:
            # Ensure skill key is nw-prefixed (matches directory name)
            skill_key = skill if skill.startswith("nw-") else f"nw-{skill}"
            ownership.setdefault(skill_key, set()).add(agent_name)

    _add_role_skill_registry_ownership(agents_dir, ownership, yaml)

    return ownership


def _add_role_skill_registry_ownership(
    agents_dir: Path, ownership: dict[str, set[str]], yaml_module: object
) -> None:
    """Fold the sibling role-skill-loading.yaml registry's direct role fields
    (on_demand/phase keys, paradigm/language_pbt values, catalog_only items)
    into ``ownership``, keyed under the bare role owner name -- these skills
    are conditionally projected by docgen, not frontmatter-listed, so the
    frontmatter-only scan above would otherwise miss them. ``catalog_only``
    entries are build-time ownership only (never rendered by docgen) for
    skills a role owns without eager preload or an ON-TRIGGER row. Also maps
    each ``reviewer_of`` role to every reviewed owner's ``on_demand`` keys,
    since a reviewer's usage ownership of a reviewed role's on-demand skills
    is a distribution concern, not author-phase ownership or eager preload.
    Missing or malformed registry is a no-op: this is a secondary
    distribution seam, not the registry's schema authority.
    """
    registry_path = agents_dir.parent / "data" / "role-skill-loading.yaml"
    if not registry_path.exists():
        return

    try:
        registry = yaml_module.safe_load(registry_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    except Exception:
        return

    if not isinstance(registry, dict):
        return

    roles = registry.get("roles")
    if not isinstance(roles, dict):
        return

    global_on_demand = registry.get("global_on_demand")
    if global_on_demand is None:
        global_on_demand = {}
    if not isinstance(global_on_demand, dict):
        return

    for role_name, entry in roles.items():
        if not isinstance(role_name, str) or not isinstance(entry, dict):
            continue
        owner = role_name.removeprefix("nw-")
        skills: list[str] = []
        for field in ("on_demand", "phase"):
            values = entry.get(field)
            if isinstance(values, dict):
                skills.extend(k for k in values if isinstance(k, str))
        for field in ("paradigm", "language_pbt"):
            values = entry.get(field)
            if isinstance(values, dict):
                skills.extend(v for v in values.values() if isinstance(v, str))
        catalog_only = entry.get("catalog_only")
        if isinstance(catalog_only, list):
            skills.extend(v for v in catalog_only if isinstance(v, str))
        for skill in skills:
            skill_key = skill if skill.startswith("nw-") else f"nw-{skill}"
            ownership.setdefault(skill_key, set()).add(owner)

    # Global on-demand lenses are rendered into every shipped agent, including
    # older roles that have no role-specific registry entry.  Their ownership
    # must use the same complete population or the public strip can preserve a
    # skill while the loaded-but-unowned validator still reports drift.
    for agent_file in sorted(agents_dir.glob("nw-*.md")):
        owner = agent_file.stem.removeprefix("nw-")
        for skill in global_on_demand:
            if not isinstance(skill, str):
                continue
            skill_key = skill if skill.startswith("nw-") else f"nw-{skill}"
            ownership.setdefault(skill_key, set()).add(owner)

    for role_name, entry in roles.items():
        if not isinstance(role_name, str) or not isinstance(entry, dict):
            continue
        reviewer_of = entry.get("reviewer_of")
        if not isinstance(reviewer_of, list):
            continue
        reviewer = role_name.removeprefix("nw-")
        for reviewed in reviewer_of:
            if not isinstance(reviewed, str):
                continue
            owner_entry = roles.get(reviewed)
            if not isinstance(owner_entry, dict):
                continue
            on_demand = owner_entry.get("on_demand")
            if not isinstance(on_demand, dict):
                continue
            for skill in on_demand:
                if not isinstance(skill, str):
                    continue
                skill_key = skill if skill.startswith("nw-") else f"nw-{skill}"
                ownership.setdefault(skill_key, set()).add(reviewer)


def _parse_frontmatter(file_path: Path, yaml_module: object) -> dict | None:
    """Extract YAML frontmatter from a markdown file.

    Returns the parsed dict, or ``None`` if parsing fails or no
    frontmatter is found.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    if not text.startswith("---"):
        return None

    end = text.find("---", 3)
    if end == -1:
        return None

    try:
        return yaml_module.safe_load(text[3:end])  # type: ignore[union-attr]
    except Exception:
        return None


def is_agent_on_disk_catalogued(agents_dir: Path, nwave_dir: Path) -> list[str]:
    """Return filenames of agents on disk that are NOT in the catalog.

    Enumerates ``nw-*.md`` files in *agents_dir*, normalizes each filename,
    and checks whether it (or its base name for reviewers) appears in the
    catalog. Returns the list of uncatalogued filenames.

    Also reports agents whose catalog entry is missing an explicit
    ``public`` field (returns ``"<name> (missing public field)"``).
    """
    catalog = _load_catalog(nwave_dir, strict=True)
    if catalog is None:
        return []

    agents_section: dict = catalog.get("agents", {})
    uncatalogued: list[str] = []

    # Check for missing public field first
    for name, info in agents_section.items():
        if "public" not in info:
            uncatalogued.append(f"{name} (missing public field)")

    # Check disk files against catalog
    if not agents_dir.exists():
        return uncatalogued

    for agent_file in sorted(agents_dir.glob("nw-*.md")):
        normalized = normalize_agent_name(agent_file.name)
        base = base_agent_name(normalized)
        # Agent is catalogued if its normalized name OR its base name is in catalog
        if normalized not in agents_section and base not in agents_section:
            uncatalogued.append(agent_file.name)

    return uncatalogued


def detect_command_skills(skills_dir: Path) -> set[str]:
    """Detect command-skills by scanning SKILL.md for ``user-invocable: true``.

    Command-skills are user-facing slash commands migrated to skill format.
    They have ``user-invocable: true`` (visible in menu) or
    ``user-invocable: false`` (hidden but still a command, not an agent skill).

    Agent-only skills have ``disable-model-invocation: true`` and
    ``user-invocable: false`` — these are NOT command-skills.

    The distinguishing marker: command-skills do NOT have
    ``disable-model-invocation`` in their frontmatter.

    Returns a set of skill directory names (e.g. ``{"nw-deliver", "nw-design"}``).
    """
    command_skills: set[str] = set()
    if not skills_dir.exists():
        return command_skills

    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir() or not child.name.startswith("nw-"):
            continue
        skill_file = child / "SKILL.md"
        if not skill_file.exists():
            continue
        try:
            text = skill_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        frontmatter = text.split("\n---\n")[0]
        # Command-skills have user-invocable but NOT disable-model-invocation
        has_user_invocable = "user-invocable:" in frontmatter
        has_disable_model = "disable-model-invocation:" in frontmatter
        if has_user_invocable and not has_disable_model:
            command_skills.add(child.name)

    return command_skills


def _skill_key(skill_dir_name: str) -> str:
    """Normalize a skill name to its ``nw-``-prefixed directory-name key."""
    return (
        skill_dir_name if skill_dir_name.startswith("nw-") else f"nw-{skill_dir_name}"
    )


def is_public_skill(
    skill_dir_name: str,
    public_agents: set[str],
    ownership_map: dict[str, set[str]] | None = None,
    command_skills: set[str] | None = None,
    private_skills: set[str] | None = None,
) -> bool:
    """Check whether a skill directory belongs to a public agent.

    The ``common`` directory is always considered public.
    Command-skills (user-invocable slash commands) are always public.
    Every agent (including reviewers) must be explicitly listed in the
    catalog to be distributed — no implicit inheritance.

    When *ownership_map* is provided, uses it to look up the owning
    agent(s) for the skill. A skill is public if at least one of its
    owning agents is public.

    When *private_skills* is provided (from :func:`load_private_skills`),
    every skill it names is private no matter who owns it and no matter
    which public override would otherwise apply. Callers deciding real
    distribution MUST pass it; ``tests/build/unit/test_is_public_skill_
    call_sites_pass_private_skills.py`` pins that they do.

    When *command_skills* is provided, skills in this set are always
    treated as public (they are user-facing commands, not agent-only).

    When *ownership_map* is ``None``, falls back to the old heuristic
    (directory name matching).

    When *public_agents* is empty (catalog not loaded), returns ``True``
    for every directory (backward compatibility).
    """
    if not public_agents:
        return True

    # The catalog's private declaration is the FIRST thing consulted: it wins
    # over every public path below -- the shared-skill allow-list, command
    # skill status, and any public owning agent. Fail-closed by ordering.
    if private_skills and _skill_key(skill_dir_name) in private_skills:
        return False

    if skill_dir_name in ("common", "nw-canary"):
        return True
    if skill_dir_name in PUBLIC_SHARED_SKILLS:
        return True
    if command_skills and skill_dir_name in command_skills:
        return True

    if ownership_map is not None:
        # Normalize to nw-prefixed key (matching ownership map convention)
        lookup_key = _skill_key(skill_dir_name)
        if lookup_key in ownership_map:
            owning_agents = ownership_map[lookup_key]
            return any(agent in public_agents for agent in owning_agents)

    # Fallback: skill must match a public agent name explicitly (no inheritance)
    return skill_dir_name in public_agents


def surviving_skill_dirs(nwave_dir: Path, *, strict: bool = True) -> set[str]:
    """Skill directory names that survive the public release strip.

    The one computation of skill survival. ``strip_private_agents.strip``
    removes every skill directory outside this set, and the docs renderer
    emits a skill page (and its Source link) only for a member of it.
    ``strict`` reaches every catalog read: the release fails closed on a
    missing or corrupt catalog, while documentation may read it leniently.
    """
    public_agents = load_public_agents(nwave_dir, strict=strict)
    private_skills = load_private_skills(nwave_dir, strict=strict)
    skills_dir = nwave_dir / "skills"
    if not skills_dir.is_dir():
        return set()
    ownership_map = build_ownership_map(nwave_dir / "agents")
    command_skills = detect_command_skills(skills_dir)
    return {
        child.name
        for child in skills_dir.iterdir()
        if child.is_dir()
        and is_public_skill(
            child.name,
            public_agents,
            ownership_map=ownership_map,
            command_skills=command_skills,
            private_skills=private_skills,
        )
    }
