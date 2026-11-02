"""Pure activation-resolution policy (ADR-AG-002).

Pure function: two already-read scalars in, one bool out. No I/O. The 9-row
truth table over (marker_enabled, global_mode) is documented in ADR-AG-002 and
mirrored exhaustively by the parametrized acceptance suite.
"""

from __future__ import annotations


_FRESH_INSTALL_DEFAULT_MODE = "opt-in"


def resolve_activation(marker_enabled: bool | None, global_mode: str | None) -> bool:
    """Resolve whether nWave is active for the current project.

    Args:
        marker_enabled: the DECLARED per-repo enablement opinion
            (``DESConfig.enabled_for_repo``): the unified ``.nwave/config.json``
            repo tier, else the legacy ``.nwave/config.json`` marker's
            ``enabled_for_repo``, else the unified global tier. ``None`` when NO
            tier declares one (absent / keyless / corrupt / wrongly typed) --
            that is the state on which the ``mode`` branch below is reached.
            The short-circuit is intentional and load-bearing (an explicit
            opinion wins over ``mode`` in BOTH directions); it went dead only
            while the reader collapsed ``None`` into a bool (P-SSOT-1 P5-bis).
        global_mode: ``~/.nwave/config.json`` -> ``activation.mode``
            (``None`` when absent / corrupt -> treated as ``"opt-in"``).

    Returns:
        ``True`` if active, ``False`` if inactive (per the ADR-AG-002 table).
    """
    if marker_enabled is not None:
        return marker_enabled
    mode = global_mode if global_mode is not None else _FRESH_INSTALL_DEFAULT_MODE
    return mode == "all"
