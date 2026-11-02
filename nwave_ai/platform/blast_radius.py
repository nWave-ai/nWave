"""Blast-radius tier value types + the pure classification rule.

Feature-delta: docs/feature/blast-radius-measured-tier/feature-delta.md
  ([REF] Architecture & Contract Tests -- Tier classification table).

Pure, side-effect-free value types + a pure classifier function -- zero
coupling to `scripts.*` (Effect Isolation, principle 12). slice-02 completes the
full closed S/M/L decision table (DISTILL D6, 2026-07-18 -- `>=` is
authoritative for `large_min_consumers`):

    L iff ANY of: boundary_files non-empty; any consumer_counts value is
        None (indeterminate); any consumer_counts value >= large_min_consumers
    S iff ALL of: files <= small_max_files; lines_changed is not None AND
        <= small_max_lines; boundary_files empty; every consumer_counts
        value <= small_max_consumers
    M otherwise (the measured band between S and L)
"""

from __future__ import annotations

from dataclasses import dataclass


class BlastRadiusConfigRejected(Exception):
    """A present, well-typed `blast_radius` threshold is outside its sane range.

    GDP-3/GDP-6 hard fail (D4, feature-delta "Floor/ceiling validation"): raised
    by `DESConfig` when a threshold is PRESENT and WELL-TYPED but outside its
    documented floor/ceiling -- never a silent clamp, never a silent fallback
    (that degrade is reserved for an ABSENT or WRONG-TYPE key). The message
    names the offending key, its value, its valid range, and points at
    `.nwave/config.json` (GDP-3 what/why/how) -- mirrors
    `BlastRadiusInputRejected`'s shape.
    """


@dataclass(frozen=True)
class BlastRadiusThresholds:
    """The numeric/glob thresholds the closed S/M/L decision table reads.

    Canonical defaults (feature-delta "Canonical default thresholds" table).
    `DESConfig._blast_radius()` wires these through the project -> global ->
    hardcoded-default cascade; this dataclass IS the hardcoded-default rung
    (byte-identical to the canonical `.nwave/config.json` shape).
    """

    small_max_files: int = 2
    small_max_lines: int = 10
    small_max_consumers: int = 3
    large_min_consumers: int = 10
    boundary_globs: tuple[str, ...] = (
        "**/ports/**",
        "**/adapters/**",
        "**/schemas/**",
        "**/*.schema.json",
        "**/*.proto",
    )
