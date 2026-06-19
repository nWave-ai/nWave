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
        marker_enabled: ``.nwave/local-config.json`` -> ``enabled_for_repo`` (``None``
            when the marker is absent / keyless / corrupt).
        global_mode: ``~/.nwave/global-config.json`` -> ``activation.mode``
            (``None`` when absent / corrupt -> treated as ``"opt-in"``).

    Returns:
        ``True`` if active, ``False`` if inactive (per the ADR-AG-002 table).
    """
    if marker_enabled is not None:
        return marker_enabled
    mode = global_mode if global_mode is not None else _FRESH_INSTALL_DEFAULT_MODE
    return mode == "all"
