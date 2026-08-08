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
from typing import Any, Literal


DensityMode = Literal["lean", "full"]
ExpansionPromptMode = Literal[
    "ask", "always-skip", "always-expand", "smart", "ask-intelligent"
]

# Accepted `documentation.expansion_prompt` values, in documentation order.
# Kept in sync with `ExpansionPromptMode` and with
# `docs/reference/global-config.md` / `docs/guides/configuring-doc-density.md`.
_ACCEPTED_EXPANSION_PROMPTS: tuple[str, ...] = (
    "ask",
    "always-skip",
    "always-expand",
    "smart",
    "ask-intelligent",
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


def _validate_expansion_prompt(value: Any) -> None:
    """Reject a `documentation.expansion_prompt` outside the accepted set.

    A missing key is valid — the cascade supplies a default. Any present value
    that is not one of `_ACCEPTED_EXPANSION_PROMPTS` raises ValueError naming
    the accepted set, so a typo surfaces as a fixable error instead of a
    silent no-op.
    """
    if value is None:
        return
    if value not in _ACCEPTED_EXPANSION_PROMPTS:
        raise ValueError(
            f"Unknown documentation.expansion_prompt {value!r}; "
            f"expected one of {list(_ACCEPTED_EXPANSION_PROMPTS)}."
        )


def resolve_density(global_config: dict[str, Any]) -> Density:
    """Return the active documentation density via the D12 cascade.

    Pure function. No I/O, no logging, no environment lookups. Caller is
    responsible for parsing `~/.nwave/global-config.json` and passing the
    resulting dict in.

    Cascade order (per DDD-5 + D12 + Decision 4):
        1. Explicit `documentation.density` override wins.
        2. Else `rigor.profile` D12 mapping.
        3. Else fallback to ("lean", "ask-intelligent") — fresh-install
           hard default per Decision 4.

    Args:
        global_config: Parsed contents of `~/.nwave/global-config.json`.
            May be empty (fresh install) or arbitrary user-shaped dict.

    Returns:
        Density value object capturing the resolved mode, expansion prompt,
        and provenance.

    Raises:
        ValueError: rigor.profile is set to an unknown value, or
            documentation.expansion_prompt is outside the accepted set.
    """
    # Step 0: reject an unrecognised expansion_prompt outright. Without this
    # the value is silently carried (or silently ignored), leaving the user no
    # signal that their setting does nothing.
    documentation = global_config.get("documentation", {})
    _validate_expansion_prompt(documentation.get("expansion_prompt"))

    # Step 1: explicit override wins — both density and expansion_prompt.
    explicit_mode = documentation.get("density")
    if explicit_mode is not None:
        return Density(
            mode=explicit_mode,
            expansion_prompt=documentation.get("expansion_prompt", "ask-intelligent"),
            provenance="explicit_override",
        )

    # Step 2: rigor.profile inheritance per D12.
    rigor_profile = global_config.get("rigor", {}).get("profile")
    if rigor_profile is not None:
        return _from_rigor_profile(rigor_profile)

    # Step 3: hard default — fresh install, no documentation, no rigor.
    # Per Decision 4 (2026-04-28), the fresh-install default is
    # ("lean", "ask-intelligent"): emit minimal Tier-1 baseline, then
    # show a scoped expansion menu only when triggers fire (the wave
    # skill prose owns trigger detection).
    return Density(
        mode="lean", expansion_prompt="ask-intelligent", provenance="default"
    )
