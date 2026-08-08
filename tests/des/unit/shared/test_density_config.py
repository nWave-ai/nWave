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

import pytest

from scripts.shared.density_config import Density, resolve_density


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


def test_known_expansion_prompt_without_density_is_accepted() -> None:
    """A recognised expansion_prompt alone does not raise."""
    config = {"documentation": {"expansion_prompt": "smart"}}
    assert resolve_density(config).provenance == "default"
