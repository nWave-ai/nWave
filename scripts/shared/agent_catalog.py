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
        "nw-density-resolution-contract",
        "nw-jtbd-core",
        "nw-jtbd-interviews",
        "nw-jtbd-opportunity-scoring",
        "nw-jtbd-workflow-selection",
        "nw-persona-jtbd-analysis",
        "nw-roadmap-design",
        "nw-spike-methodology",
        "nw-speculative-dispatch",
        "nw-tdd-cross-language",
        "nw-wizard-shared-rules",
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

    return ownership


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


def is_public_skill(
    skill_dir_name: str,
    public_agents: set[str],
    ownership_map: dict[str, set[str]] | None = None,
    command_skills: set[str] | None = None,
) -> bool:
    """Check whether a skill directory belongs to a public agent.

    The ``common`` directory is always considered public.
    Command-skills (user-invocable slash commands) are always public.
    Every agent (including reviewers) must be explicitly listed in the
    catalog to be distributed — no implicit inheritance.

    When *ownership_map* is provided, uses it to look up the owning
    agent(s) for the skill. A skill is public if at least one of its
    owning agents is public.

    When *command_skills* is provided, skills in this set are always
    treated as public (they are user-facing commands, not agent-only).

    When *ownership_map* is ``None``, falls back to the old heuristic
    (directory name matching).

    When *public_agents* is empty (catalog not loaded), returns ``True``
    for every directory (backward compatibility).
    """
    if not public_agents:
        return True
    if skill_dir_name in ("common", "nw-canary"):
        return True
    if skill_dir_name in PUBLIC_SHARED_SKILLS:
        return True
    if command_skills and skill_dir_name in command_skills:
        return True

    if ownership_map is not None:
        # Normalize to nw-prefixed key (matching ownership map convention)
        if skill_dir_name.startswith("nw-"):
            lookup_key = skill_dir_name
        else:
            lookup_key = f"nw-{skill_dir_name}"
        if lookup_key in ownership_map:
            owning_agents = ownership_map[lookup_key]
            return any(agent in public_agents for agent in owning_agents)

    # Fallback: skill must match a public agent name explicitly (no inheritance)
    return skill_dir_name in public_agents
