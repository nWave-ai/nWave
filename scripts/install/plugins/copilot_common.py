"""The Copilot CLI host: its folders and the conversion of one nWave role into its agent text (card t-0467).

The folders are the personal ones Copilot reads: ``<COPILOT_HOME>/agents`` for custom agents and
``<COPILOT_HOME>/skills`` for skills, with COPILOT_HOME defaulting to ``~/.copilot``. The conversion takes a Claude Code
role source (YAML frontmatter, then a body) and returns the Copilot agent text: name and description only, the body
with its Claude folders rewritten to the Copilot ones.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from nwave_ai.upgrade_shell import copilot_config_dir
from scripts.install.plugins.copilot_role_card import RoleCard, render_copilot_agent
from scripts.install.plugins.opencode_common import render_frontmatter
from scripts.shared.skill_path_rewrite import rewrite_host_paths


_SOURCE = re.compile(r"\A---\n(?P<head>.*?)\n---\n(?P<body>.*)\Z", re.DOTALL)

# What the summary says the Copilot install did not check: the terminal and VS Code read the files, and only a session
# shows that (card t-0559).
NOT_CHECKED = (
    "not checked by this install: whether Copilot (terminal and VS Code) loads them"
)


def copilot_agents_dir() -> Path:
    """The folder Copilot reads custom agents from: <COPILOT_HOME or ~/.copilot>/agents."""
    return copilot_config_dir(Path.home()) / "agents"


def copilot_skills_dir() -> Path:
    """The folder Copilot reads personal skills from: <COPILOT_HOME or ~/.copilot>/skills."""
    return copilot_config_dir(Path.home()) / "skills"


def convert_agent(content: str) -> str:
    """The Copilot agent text of one Claude Code role source.

    The source is split on its own line-anchored ``---`` delimiters, so a description that contains three dashes
    cannot move the split. The frontmatter must name the role and describe it in text; anything else is refused with
    WHAT, WHY and HOW, because an agent without a name or a description is one Copilot would drop silently.

    Raises:
        ValueError: The source has no frontmatter, or no name or description.
    """
    match = _SOURCE.match(content)
    if match is None:
        raise ValueError(
            "WHAT: a role source has no YAML frontmatter, so no Copilot agent is written. "
            "WHY: the Copilot agent needs the name and the description the frontmatter holds. "
            "HOW: give the role source a frontmatter block between two --- lines."
        )
    frontmatter = yaml.safe_load(match.group("head")) or {}
    name = frontmatter.get("name") if isinstance(frontmatter, dict) else None
    description = (
        frontmatter.get("description") if isinstance(frontmatter, dict) else None
    )
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "WHAT: a role source has no name, so no Copilot agent is written. "
            "WHY: Copilot lists an agent by the name in its frontmatter. "
            "HOW: give the role source a name in its frontmatter."
        )
    if not isinstance(description, str) or description == "":
        raise ValueError(
            "WHAT: a role source has no description, so no Copilot agent is written. "
            "WHY: Copilot drops an agent whose frontmatter it cannot read as name and description. "
            "HOW: give the role source a description in its frontmatter."
        )
    card = RoleCard(
        name=name,
        description=description,
        body=rewrite_host_paths(match.group("body"), "copilot"),
    )
    return render_copilot_agent(card)


def convert_wave(content: str) -> str:
    """The Copilot prompt file text of one wave entry point (card t-0515, part 7).

    The frontmatter keeps the wave's description and, when it declares one, its argument hint; the body is the wave's
    body with its Claude folders rewritten. A wave without a description is refused, because the prompt list would show
    it blank.

    Raises:
        ValueError: The wave has no frontmatter, or no description.
    """
    match = _SOURCE.match(content)
    if match is None:
        raise ValueError(
            "WHAT: a wave entry point has no YAML frontmatter, so no Copilot prompt file is written. "
            "WHY: the prompt file needs the description the frontmatter holds. "
            "HOW: give the wave file a frontmatter block between two --- lines."
        )
    frontmatter = yaml.safe_load(match.group("head")) or {}
    description = (
        frontmatter.get("description") if isinstance(frontmatter, dict) else None
    )
    if not isinstance(description, str) or not description.strip():
        raise ValueError(
            "WHAT: a wave entry point has no description, so no Copilot prompt file is written. "
            "WHY: the prompt list shows the description to the user. "
            "HOW: give the wave file a description in its frontmatter."
        )
    fields = {"description": description}
    hint = frontmatter.get("argument-hint")
    if isinstance(hint, str) and hint.strip():
        fields["argument-hint"] = hint
    body = rewrite_host_paths(match.group("body"), "copilot")
    return f"{render_frontmatter(fields)}\n{body}"
