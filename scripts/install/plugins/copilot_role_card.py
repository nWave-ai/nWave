"""The Copilot agent card: one nWave role as GitHub Copilot CLI reads it (card t-0467).

Copilot parses an agent's frontmatter as strict YAML and drops an agent it cannot parse, without an error (observed on
Copilot CLI 1.0.103: a plain description containing ": " made the agent disappear from the list). The card therefore
holds exactly the two fields Copilot is given, and its text is rendered through the shared YAML renderer, which quotes
every value the YAML grammar needs.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.install.plugins.opencode_common import render_frontmatter


@dataclass(frozen=True, slots=True)
class RoleCard:
    """A role as Copilot reads it: its name, its description and its body after the frontmatter."""

    name: str
    description: str
    body: str


def render_copilot_agent(card: RoleCard) -> str:
    """The Copilot agent text: the frontmatter of name and description, then the body unchanged."""
    frontmatter = render_frontmatter(
        {"name": card.name, "description": card.description}
    )
    return f"{frontmatter}\n{card.body}"
