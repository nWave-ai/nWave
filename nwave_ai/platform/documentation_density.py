"""Density resolver — the ONE documentation-density cascade (DDD-5).

Pure-function domain helper. No I/O — caller passes an already-parsed dict.
Hexagonal: this module is a Tier-1 driving port at domain scope; filesystem
reads of `~/.nwave/config.json` live in caller adapters (CLI install,
wave-entry step, doctor).

WHY IT LIVES UNDER ``nwave_ai/platform/`` AND NOT UNDER ``scripts/``. The
installed runtime's hooks run with their own bundled libraries and must not
depend on a development checkout: a hook importing ``scripts.shared.*`` raises
``ModuleNotFoundError`` outside a development checkout (the same packaging-tier
defect the wave-entry cascade fixed).
The ``nwave_ai`` CLI, wave-entry step and doctor need this cascade, so the
cascade ships with ``nwave_ai``: one cascade, one set of
legal values, no second resolver.

Per DDD-5 + D12 + Decision 4 (2026-04-28),
`resolve_density(global_config)` cascades:
    1. Explicit `documentation.density` override wins.
    2. Else `rigor.profile` mapping per D12 (lean -> lean+always-skip,
       standard/custom -> lean+ask-intelligent,
       thorough/exhaustive -> full+always-expand).
    3. Else hard default "lean" + "ask-intelligent" (fresh-install per
       Decision 4).

Provenance is reported on the returned Density value so entry and diagnostic
consumers can explain *why* a given density is in effect without re-running
the cascade. Density selects the completed-wave reading surface; expansion
prompt selects optional conversational detail. Neither selects a provider,
model, or mandatory check.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, get_args

from nwave_ai.platform.result import Failure, Result, Success


DensityMode = Literal["lean", "full"]
ExpansionPromptMode = Literal[
    "ask", "always-skip", "always-expand", "smart", "ask-intelligent"
]


@dataclass(frozen=True)
class Density:
    """Resolved documentation-density decision.

    Immutable value object: density mode, expansion-prompt mode, and the
    provenance string that explains which cascade branch produced this result.

    Attributes:
        mode: "lean" or "full" (per DDD-5). The installed wave consumer
            uses full to render a local view of a completed DES authority;
            lean retains the authoritative handoff.
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


def _require_object(value: Any, *, field: str) -> dict[str, Any]:
    """Return ``value`` as a dict, or raise a useful ``ValueError``.

    A malformed JSON type for a config section (e.g. a list where an
    object is expected) must surface as a clear resolver-level ValueError,
    never as an ``AttributeError`` from a stray ``.get()`` deep in the
    cascade (V4-02).
    """
    if not isinstance(value, dict):
        raise ValueError(
            f"Invalid {field!r} config: expected a JSON object, got "
            f"{type(value).__name__}."
        )
    return value


@dataclass(frozen=True)
class IllegalChoice:
    """A configured value outside a CLOSED legal set, carried as DATA.

    The cascade folds three distinct causes into one builtin ``ValueError``
    (illegal closed-set choice, unknown ``rigor.profile``, non-object section).
    Only the first is decidable from facts the software already holds -- the
    field, the supplied value and the complete legal tuple -- so it is exposed
    as a value a caller can classify without parsing an exception's text.

    Attributes:
        field: dotted configuration field, e.g. ``documentation.density``.
        value: the offending configured value, verbatim.
        legal: every accepted member of the closed set.
    """

    field: str
    value: Any
    legal: tuple[str, ...]

    @property
    def message(self) -> str:
        """The byte-identical sentence ``resolve_density`` has always raised."""
        return f"Unknown {self.field} {self.value!r}; expected one of {sorted(self.legal)}."


def _validate_choice(
    value: str | None, *, field: str, legal: tuple[str, ...]
) -> IllegalChoice | None:
    if value is not None and value not in legal:
        return IllegalChoice(field=field, value=value, legal=legal)
    return None


def resolve_density(global_config: dict[str, Any]) -> Density:
    """Return the active documentation density, raising on any illegal input.

    Unchanged signature and unchanged messages: the raising form is kept for
    the install preflight and the doctor check, and it raises FROM the same
    typed outcome ``resolve_density_result`` returns, so exactly one cascade
    and one set of legal values remain.

    Raises:
        ValueError: `rigor.profile` is unknown, `documentation.density` or
            `documentation.expansion_prompt` is not one of their legal
            values, or `documentation`/`rigor` is not a JSON object.
    """
    resolved = resolve_density_result(global_config)
    if isinstance(resolved, Failure):
        raise ValueError(resolved.error.message)
    return resolved.unwrap()


def resolve_density_result(
    global_config: dict[str, Any],
) -> Result[Density, IllegalChoice]:
    """Return the active documentation density via the D12 cascade.

    Pure function. No I/O, no logging, no environment lookups. Caller is
    responsible for parsing `~/.nwave/config.json` and passing the
    resulting dict in.

    Cascade order (per DDD-5 + D12 + Decision 4):
        1. Explicit `documentation.density` override wins for the mode.
        2. Else `rigor.profile` D12 mapping decides the mode.
        3. Else fallback to "lean" — fresh-install hard default per
           Decision 4.
        Independently of which branch decided the mode, an explicit
        `documentation.expansion_prompt` always wins for the prompt
        (V4-02: previously dropped whenever density was omitted and the
        cascade fell through to the rigor-profile or hard-default branch).

    Args:
        global_config: Parsed contents of `~/.nwave/config.json`.
            May be empty (fresh install) or arbitrary user-shaped dict.

    Returns:
        Success(Density) capturing the resolved mode, expansion prompt and
        provenance, or Failure(IllegalChoice) when a configured closed-set
        choice lies outside its legal values.

    Raises:
        ValueError: `rigor.profile` is unknown, or `documentation`/`rigor` is
            not a JSON object. Those causes are NOT decidable from a closed
            legal set the software owns: profile validation belongs to the
            rigor system upstream, and a malformed section was never read.
    """
    documentation = _require_object(
        global_config.get("documentation", {}), field="documentation"
    )
    rigor = _require_object(global_config.get("rigor", {}), field="rigor")

    explicit_mode = documentation.get("density")
    explicit_expansion_prompt = documentation.get("expansion_prompt")
    illegal = _validate_choice(
        explicit_mode, field="documentation.density", legal=get_args(DensityMode)
    ) or _validate_choice(
        explicit_expansion_prompt,
        field="documentation.expansion_prompt",
        legal=get_args(ExpansionPromptMode),
    )
    if illegal is not None:
        return Failure(illegal)

    # Step 1: explicit density override wins for the mode.
    if explicit_mode is not None:
        return Success(
            Density(
                mode=explicit_mode,
                expansion_prompt=explicit_expansion_prompt or "ask-intelligent",
                provenance="explicit_override",
            )
        )

    # Step 2: rigor.profile inheritance per D12 decides the mode.
    rigor_profile = rigor.get("profile")
    if rigor_profile is not None:
        if not isinstance(rigor_profile, str):
            raise ValueError(
                f"Invalid rigor.profile: expected a string, got "
                f"{type(rigor_profile).__name__}."
            )
        base = _from_rigor_profile(rigor_profile)
    else:
        # Step 3: hard default — fresh install, no documentation, no rigor.
        # Per Decision 4 (2026-04-28), the fresh-install default is
        # ("lean", "ask-intelligent"): emit minimal Tier-1 baseline, then
        # show a scoped expansion menu only when triggers fire (the wave
        # skill prose owns trigger detection).
        base = Density(
            mode="lean", expansion_prompt="ask-intelligent", provenance="default"
        )

    # An explicit expansion_prompt is honored regardless of whether the
    # mode came from the rigor cascade or the hard default (V4-02).
    if explicit_expansion_prompt is not None:
        return Success(
            Density(
                mode=base.mode,
                expansion_prompt=explicit_expansion_prompt,
                provenance=base.provenance,
            )
        )
    return Success(base)
