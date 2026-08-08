"""Unit tests for density resolver — pure function, port-to-port at domain scope.

Driving port: `resolve_density(global_config: dict) -> Density`.
The function signature IS the public interface; calling it directly is correct
port-to-port testing per nw-tdd-methodology + nw-fp-principles.

Per Decision 4 (2026-04-28), the fresh-install hard default is now
`ask-intelligent` (scoped trigger-based menu) instead of the broader `ask`
menu. The wave skill prose owns trigger detection.

Coverage (per task spec):
  1. Empty dict -> lean default + provenance="default" + ask-intelligent
  2. Explicit documentation.density="full" -> full + provenance="explicit_override"
  3. rigor.profile="thorough" only -> full + provenance="rigor.profile=thorough"
  4. Explicit + rigor both -> explicit wins (override beats inheritance)
  5. Unknown rigor profile -> ValueError (strict; profile validation is upstream)
  6. rigor.profile="standard" -> lean+ask-intelligent (Decision 4)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import get_args

import pytest

from scripts.shared.density_config import (
    Density,
    ExpansionPromptMode,
    resolve_density,
)


def test_empty_config_returns_lean_default() -> None:
    """Fresh-install path: no documentation, no rigor -> hard default.

    Per Decision 4 (2026-04-28), hard default is lean + ask-intelligent.
    """
    result = resolve_density({})
    assert result == Density(
        mode="lean", expansion_prompt="ask-intelligent", provenance="default"
    )


def test_explicit_documentation_density_full_wins() -> None:
    """Step-1 cascade: explicit override wins over everything else.

    Per Decision 4, the fallback expansion_prompt for an explicit-density
    override that does not set its own expansion_prompt is now
    "ask-intelligent" (was "ask").
    """
    config = {"documentation": {"density": "full"}}
    result = resolve_density(config)
    assert result == Density(
        mode="full",
        expansion_prompt="ask-intelligent",  # default per Decision 4
        provenance="explicit_override",
    )


def test_rigor_profile_standard_yields_lean_ask_intelligent() -> None:
    """Decision 4: standard profile maps to lean + ask-intelligent."""
    config = {"rigor": {"profile": "standard"}}
    result = resolve_density(config)
    assert result == Density(
        mode="lean",
        expansion_prompt="ask-intelligent",
        provenance="rigor.profile=standard",
    )


def test_rigor_profile_thorough_yields_full_density() -> None:
    """Step-2 cascade: rigor.profile inheritance (D12 mapping)."""
    config = {"rigor": {"profile": "thorough"}}
    result = resolve_density(config)
    assert result == Density(
        mode="full",
        expansion_prompt="always-expand",
        provenance="rigor.profile=thorough",
    )


def test_explicit_override_beats_rigor_profile() -> None:
    """Cascade priority: explicit override beats rigor.profile inheritance."""
    config = {
        "documentation": {"density": "lean", "expansion_prompt": "always-skip"},
        "rigor": {"profile": "thorough"},  # would yield "full" if used
    }
    result = resolve_density(config)
    assert result == Density(
        mode="lean",
        expansion_prompt="always-skip",
        provenance="explicit_override",
    )


def test_unknown_rigor_profile_raises_value_error() -> None:
    """Strict: unknown rigor profile signals upstream config invariant violation."""
    config = {"rigor": {"profile": "ludicrous"}}
    with pytest.raises(ValueError, match="ludicrous"):
        resolve_density(config)


def test_unknown_expansion_prompt_raises_value_error() -> None:
    """Strict: an unrecognised expansion_prompt is rejected, not silently kept."""
    config = {"documentation": {"density": "lean", "expansion_prompt": "sometimes"}}
    with pytest.raises(ValueError, match="sometimes"):
        resolve_density(config)


def test_unknown_expansion_prompt_error_names_accepted_values() -> None:
    """The rejection message enumerates the accepted expansion_prompt set."""
    config = {"documentation": {"expansion_prompt": "sometimes"}}
    with pytest.raises(ValueError) as excinfo:
        resolve_density(config)
    message = str(excinfo.value)
    for accepted in (
        "ask",
        "always-skip",
        "always-expand",
        "smart",
        "ask-intelligent",
    ):
        assert accepted in message


def test_known_expansion_prompt_without_density_is_accepted_and_applied() -> None:
    """A recognised expansion_prompt alone is accepted AND takes effect.

    Asserting only the provenance would let this pass while the user's value was
    silently discarded, which is the defect issue #84 records.
    """
    config = {"documentation": {"expansion_prompt": "smart"}}
    density = resolve_density(config)

    assert density.expansion_prompt == "smart"
    assert density.mode == "lean"


def test_explicit_expansion_prompt_survives_rigor_profile_inheritance():
    """WHEN expansion_prompt is set without density, the value SHALL take effect.

    Validating a value and then discarding it is the silent no-op issue #84
    records, dressed up as strictness.
    """
    density = resolve_density(
        {"documentation": {"expansion_prompt": "always-skip"}, "rigor": {"profile": "thorough"}}
    )

    assert density.expansion_prompt == "always-skip"
    assert "explicit_expansion_prompt" in density.provenance


def test_explicit_expansion_prompt_survives_the_hard_default():
    """The same holds with neither density nor rigor.profile present."""
    density = resolve_density({"documentation": {"expansion_prompt": "always-expand"}})

    assert density.expansion_prompt == "always-expand"
    assert density.mode == "lean", "only the prompt is overridden, not the density"


def test_explicit_null_expansion_prompt_is_rejected():
    """An explicit JSON null is a mistake, not a request for the default.

    `.get(key, default)` returns the stored None when the key is present, so
    treating null as absent lets None reach the resolved Density.
    """
    with pytest.raises(ValueError, match="expansion_prompt"):
        resolve_density({"documentation": {"expansion_prompt": None}})


def test_non_object_documentation_section_names_the_offender():
    """A malformed section raises ValueError, not AttributeError."""
    with pytest.raises(ValueError, match="documentation"):
        resolve_density({"documentation": "lean"})


# --- documented vocabulary ------------------------------------------------
#
# `_ACCEPTED_EXPANSION_PROMPTS` now derives from `ExpansionPromptMode` via
# `get_args`, so code cannot drift from itself. Prose cannot derive — the three
# documents below restate the vocabulary for human readers, and that
# restatement drifting from the type IS the defect issue #84 records:
# `ask-intelligent` was accepted by the resolver while no document listed it.
# These tests are the gate that would have caught it.

_REPO_ROOT = Path(__file__).resolve().parents[4]

# Each doc is addressed by a markdown section plus the enumerating phrase inside
# it, never a line number, so the tests survive reflow, reordering, and edits
# elsewhere in the page. Both documents enumerate other vocabularies too
# (`rigor.profile`, `update_check`), hence the section scoping. A moved anchor
# fails loudly with an instruction rather than silently passing.
_ENUMERATION_ANCHORS = (
    (
        "docs/reference/global-config.md",
        "#### `documentation.expansion_prompt`",
        "Valid values:",
    ),
    (
        "docs/guides/configuring-doc-density.md",
        "### Use case 4",
        "**Accepted values**:",
    ),
)


def _section_lines(text: str, heading_prefix: str) -> list[str]:
    """Return the lines of the markdown section opened by `heading_prefix`."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(heading_prefix)]
    if not starts:
        return []
    start = starts[0]
    for offset, line in enumerate(lines[start + 1 :], start=start + 1):
        if line.startswith("#"):
            return lines[start:offset]
    return lines[start:]


def _backticked_values_after(line: str, anchor: str) -> set[str]:
    """Return the bare backticked value tokens following `anchor` on `line`.

    Filtered to lowercase/hyphen tokens so incidental backticked prose in the
    same sentence (`documentation.expansion_prompt`, `--expand`) is not mistaken
    for a listed value.
    """
    tail = line.split(anchor, 1)[1]
    return {
        token
        for token in re.findall(r"`([^`]+)`", tail)
        if re.fullmatch(r"[a-z][a-z-]*", token)
    }


@pytest.mark.parametrize(("relative_path", "heading", "anchor"), _ENUMERATION_ANCHORS)
def test_documented_expansion_prompt_enumeration_matches_the_type(
    relative_path: str, heading: str, anchor: str
) -> None:
    """Each doc's enumerating sentence lists exactly the accepted values."""
    text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
    section = _section_lines(text, heading)
    assert section, (
        f"section {heading!r} not found in {relative_path}; it was renamed or "
        "removed — update this test's heading anchor."
    )

    matching = [line for line in section if anchor in line]
    assert matching, (
        f"phrase {anchor!r} not found under {heading!r} in {relative_path}; the "
        "enumerating sentence moved or was reworded — update this test's anchor."
    )

    documented: set[str] = set()
    for line in matching:
        documented |= _backticked_values_after(line, anchor)

    assert documented == set(get_args(ExpansionPromptMode))


def test_resolution_contract_skill_mentions_every_accepted_value() -> None:
    """The contract skill has no single enumerating sentence to anchor on.

    It threads the values through per-value bullets and a cascade paragraph, so
    the gate here is presence rather than set equality: every accepted value is
    described somewhere. That catches the #84 direction (a value the contract
    never mentions); the converse — prose naming a value the type dropped — is
    left to the two enumeration tests above, which do check equality.
    """
    text = (
        _REPO_ROOT / "nWave/skills/nw-density-resolution-contract/SKILL.md"
    ).read_text(encoding="utf-8")

    missing = [
        value for value in get_args(ExpansionPromptMode) if f'`"{value}"`' not in text
    ]
    assert not missing, f"undocumented in the resolution contract: {missing}"
