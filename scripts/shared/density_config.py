"""Density resolver — shared utility per DDD-5 (lean-wave-documentation feature).

Pure-function domain helper. No I/O — caller passes an already-parsed dict.
Hexagonal: this module is a Tier-1 driving port at domain scope; filesystem
reads of `~/.nwave/global-config.json` live in caller adapters (CLI install,
wave-skill harness, doctor).

Per DDD-5 + D12 + Decision 4 (2026-04-28),
`resolve_density(global_config)` cascades:
    1. Explicit `documentation.density` override wins.
    2. Else `rigor.profile` mapping per D12 (lean -> lean+always-skip,
       standard/custom -> lean+ask-intelligent,
       thorough/exhaustive -> full+always-expand).
    3. Else hard default "lean" + "ask-intelligent" (fresh-install per
       Decision 4).

Provenance is reported on the returned Density value so consumers (telemetry,
doctor, audit) can explain *why* a given density is in effect without
re-running the cascade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast


DensityMode = Literal["lean", "full"]
ExpansionPromptMode = Literal[
    "ask", "always-skip", "always-expand", "smart", "ask-intelligent"
]

EXPANSION_PROMPT_MODES: tuple[ExpansionPromptMode, ...] = (
    "ask",
    "ask-intelligent",
    "always-skip",
    "always-expand",
    "smart",
)


@dataclass(frozen=True)
class Density:
    """Resolved documentation-density decision.

    Immutable value object: density mode, expansion-prompt mode, and the
    provenance string that explains which cascade branch produced this result.

    Attributes:
        mode: "lean" or "full" (per DDD-5).
        expansion_prompt: "ask" | "always-skip" | "always-expand" |
            "smart" | "ask-intelligent" (the last one added per
            Decision 4 2026-04-28; scoped trigger-based menu).
        provenance: human-readable origin tag, e.g. "default",
            "explicit_override", "rigor.profile=thorough".
    """

    mode: DensityMode
    expansion_prompt: ExpansionPromptMode
    provenance: str


# D12 + Decision 4 mapping: rigor.profile -> Density (without provenance —
# set by caller). Returns (mode, expansion_prompt) tuple; provenance is
# composed at call site so the rigor profile name is preserved verbatim in
# the audit trail.
#
# Per Decision 4 (2026-04-28), `standard` and `custom` profiles use
# `ask-intelligent` (scoped trigger-based menu) instead of the broad `ask`
# menu. Trigger detection lives in the wave skill prose, not in this
# resolver.
_RIGOR_PROFILE_MAP: dict[str, tuple[DensityMode, ExpansionPromptMode]] = {
    "lean": ("lean", "always-skip"),
    "standard": ("lean", "ask-intelligent"),
    "thorough": ("full", "always-expand"),
    "exhaustive": ("full", "always-expand"),
    "custom": ("lean", "ask-intelligent"),
}


def _from_rigor_profile(profile: str) -> Density:
    """Map a rigor.profile name to its D12-defined Density.

    Raises ValueError on unknown profile names: density resolver does not
    silently default for invalid rigor configuration. Profile validation
    is owned by the rigor system upstream.
    """
    mapping = _RIGOR_PROFILE_MAP.get(profile)
    if mapping is None:
        raise ValueError(
            f"Unknown rigor.profile {profile!r}; "
            f"expected one of {sorted(_RIGOR_PROFILE_MAP)}."
        )
    mode, expansion_prompt = mapping
    return Density(
        mode=mode,
        expansion_prompt=expansion_prompt,
        provenance=f"rigor.profile={profile}",
    )


def _validate_expansion_prompt(value: Any) -> ExpansionPromptMode:
    """Return a configured prompt mode or reject it without a silent fallback."""
    if value not in EXPANSION_PROMPT_MODES:
        expected = ", ".join(repr(mode) for mode in EXPANSION_PROMPT_MODES)
        raise ValueError(
            f"Unknown documentation.expansion_prompt {value!r}; "
            f"expected one of: {expected}."
        )
    return cast("ExpansionPromptMode", value)


def resolve_density(global_config: dict[str, Any]) -> Density:
    """Return the active documentation density via the D12 cascade.

    Pure function. No I/O, no logging, no environment lookups. Caller is
    responsible for parsing `~/.nwave/global-config.json` and passing the
    resulting dict in.

    Cascade order (per DDD-5 + D12 + Decision 4), independently per key:
        1. Resolve the `rigor.profile` D12 mapping, or the fresh-install
           fallback ("lean", "ask-intelligent") when no profile exists.
        2. Apply an explicit `documentation.density` override when present.
        3. Apply and validate an explicit `documentation.expansion_prompt`
           override when present.

    Args:
        global_config: Parsed contents of `~/.nwave/global-config.json`.
            May be empty (fresh install) or arbitrary user-shaped dict.

    Returns:
        Density value object capturing the resolved mode, expansion prompt,
        and provenance.

    Raises:
        ValueError: rigor.profile or documentation.expansion_prompt is unknown.
    """
    # Resolve the inherited pair first. Explicit documentation keys then
    # override their own dimension independently.
    documentation = global_config.get("documentation", {})
    rigor_profile = global_config.get("rigor", {}).get("profile")
    if rigor_profile is not None:
        inherited = _from_rigor_profile(rigor_profile)
    else:
        inherited = Density(
            mode="lean", expansion_prompt="ask-intelligent", provenance="default"
        )

    explicit_mode = documentation.get("density")
    explicit_prompt = documentation.get("expansion_prompt")
    return Density(
        mode=explicit_mode if explicit_mode is not None else inherited.mode,
        expansion_prompt=(
            _validate_expansion_prompt(explicit_prompt)
            if explicit_prompt is not None
            else inherited.expansion_prompt
        ),
        provenance=(
            "explicit_override" if explicit_mode is not None else inherited.provenance
        ),
    )
