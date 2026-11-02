"""Codex model wording: installed Codex text never names a Claude model.

Codex runs on the model its host configures, so installed agent and skill text
that prescribes or mentions Haiku, Sonnet or Opus contradicts the host the user
installed for. Both Codex plugins apply this one rule before they write; it
depends on nothing under ``scripts.install`` so neither plugin needs the other.
"""

from __future__ import annotations

import re


#: What replaces a Claude model name in installed Codex prose: Codex answers on
#: the model its host configures, so that is the only truthful referent.
CODEX_MODEL_NEUTRAL_WORDING = "the configured model"

_CLAUDE_TIER = r"(?:haiku|sonnet|opus)"
_CLAUDE_VERSION = r"[0-9]+(?:[.-][0-9]+)*"

#: A Claude model selector, bounded by non-letters rather than ``\b`` so a name
#: stays matched after an escaped line break. It covers the bare tier, a
#: ``claude-<tier>-<version>`` id, a prose form (``Claude Opus 4.6``) and a
#: trailing ``model`` noun, so the replacement reads as one noun phrase.
_CLAUDE_MODEL_NAME = re.compile(
    rf"(?<![A-Za-z])(?:claude[- ])?{_CLAUDE_TIER}"
    rf"(?:-{_CLAUDE_VERSION}|[ \t]+[0-9]+(?:\.[0-9]+)*)?"
    r"(?:[ \t]+model)?(?![A-Za-z])",
    re.IGNORECASE,
)

#: A frontmatter-style declaration quoted in prose (`` `model: haiku` ``): the
#: whole declaration, not just its value, becomes the neutral phrase.
_CLAUDE_MODEL_DECLARATION = re.compile(
    rf"`model:[ \t]*(?:claude-)?{_CLAUDE_TIER}(?:-{_CLAUDE_VERSION})?`",
    re.IGNORECASE,
)


def rewrite_claude_model_names(text: str) -> str:
    """Replace every Claude model name in *text* with neutral wording.

    Args:
        text: Agent or skill prose, before any TOML escaping.

    Returns:
        *text* with each Claude model name replaced by
        ``CODEX_MODEL_NEUTRAL_WORDING``.
    """
    declared = _CLAUDE_MODEL_DECLARATION.sub(CODEX_MODEL_NEUTRAL_WORDING, text)
    return _CLAUDE_MODEL_NAME.sub(CODEX_MODEL_NEUTRAL_WORDING, declared)
