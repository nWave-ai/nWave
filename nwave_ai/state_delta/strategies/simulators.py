"""Faithful simulators for _update_path_in_settings (des_plugin.py).

This module provides hand-mirrored simulators of the installer's PATH-update
logic at specific git revisions. They are used by property-based tests and
canned-fixture tests to verify installer state transitions without running the
real installer.

A9 contract (ADR-002): importing this module does NOT load hypothesis.
Hypothesis is imported only inside functions that need it (lazy import).

Simulators
----------
- update_path_in_settings_pre_fix   — mirrors bug #48 logic (step 01-08)
- update_path_in_settings_faithful  — mirrors post-fix logic (step 02-03,
                                       post-832b4060, des_plugin.py:881-958)

PR-review note (02-03): update_path_in_settings_faithful is asserted
byte-equivalent to scripts/install/plugins/des_plugin.py:881-958 at the
time of this PR. Runtime equivalence check intentionally omitted per
MEDIUM-1 closure (we validate the contract, not production bytes).
"""

# ──────────────────────────────────────────────────────────────────────────────
# Constants (mirrors DESPlugin class-level constants)
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PATH_FALLBACK = "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


# ──────────────────────────────────────────────────────────────────────────────
# Pre-fix simulator (from step 01-08, preserved here for cross-step imports)
# ──────────────────────────────────────────────────────────────────────────────


def update_path_in_settings_pre_fix(
    existing_path: str,
    des_bin: str,
) -> str:
    """Faithful mirror of _update_path_in_settings BEFORE fix #48.

    Hand-mirrored from des_plugin.py at commit pre-832b4060.
    Asserted byte-equivalent at PR review time; no runtime check.

    Branches (in production order):
    1. des_bin already in segments → return unchanged (idempotent)
    2. existing_path non-empty → prepend des_bin
    3. empty existing_path → seed with des_bin + SYSTEM_PATH_FALLBACK
    """
    segments = existing_path.split(":") if existing_path else []
    if des_bin in segments:
        return existing_path
    if existing_path:
        return f"{des_bin}:{existing_path}"
    return f"{des_bin}:{SYSTEM_PATH_FALLBACK}"


# ──────────────────────────────────────────────────────────────────────────────
# Post-fix simulator (step 02-03)
# ──────────────────────────────────────────────────────────────────────────────


def update_path_in_settings_faithful(
    existing_path: str,
    des_bin: str,
    home: str,
    live_env_path: str,
) -> str:
    """Faithful mirror of post-fix _update_path_in_settings (post-832b4060).

    Hand-mirrored from scripts/install/plugins/des_plugin.py:881-958.

    PR-review note: asserted byte-equivalent to des_plugin.py:881-958 at
    the time of this PR. Runtime equivalence check intentionally omitted
    per MEDIUM-1 closure (we validate the contract, not production bytes).

    Parameters
    ----------
    existing_path:
        Current value of env.PATH in settings.json (empty string if absent).
    des_bin:
        Absolute path to the DES bin directory (injected at install time).
    home:
        Absolute path of the user's home directory (str(Path.home())).
    live_env_path:
        Value of os.environ.get("PATH", "") at install time. May be empty.

    Returns
    -------
    str
        The new PATH value that should be written to settings.json["env"]["PATH"].

    Production branches (in execution order)
    -----------------------------------------
    1. $HOME normalization  — expand any $HOME literals to absolute paths
                              (pre-processing step; may fall through to others)
    2. Legacy-heal          — existing_path == des_bin:SYSTEM_PATH_FALLBACK
                              → replace with des_bin:live_env_path (or fallback)
    3. Idempotency          — des_bin already a colon-segment → return as-is
                              (writes back normalized form if $HOME was expanded)
    4. Default prepend      — non-empty, non-special → prepend des_bin
    5. Empty-seed           — empty → seed with des_bin:live_env_path (or fallback)
    """
    # ── Branch 1: $HOME normalization (pre-processing) ────────────────────────
    # Mirrors lines 922-925 of des_plugin.py.
    # Runs before all other checks; updates existing_path in-place.
    if existing_path and "$HOME" in existing_path:
        segments = [s.replace("$HOME", home) for s in existing_path.split(":")]
        existing_path = ":".join(segments)

    # ── Branch 2: legacy-heal ─────────────────────────────────────────────────
    # Mirrors lines 933-939. Detects the exact fabricated value written by the
    # pre-fix installer: des_bin + ":" + SYSTEM_PATH_FALLBACK.
    legacy_fabricated_path = f"{des_bin}:{SYSTEM_PATH_FALLBACK}"
    if existing_path == legacy_fabricated_path:
        live_path = live_env_path if live_env_path else SYSTEM_PATH_FALLBACK
        return f"{des_bin}:{live_path}"

    # ── Branch 3: idempotency ─────────────────────────────────────────────────
    # Mirrors lines 941-946. If des_bin is already a segment, return as-is
    # (but preserve the normalized form if $HOME was expanded above).
    if des_bin in existing_path.split(":"):
        return existing_path

    # ── Branch 4: non-empty prepend / Branch 5: empty-seed ───────────────────
    # Mirrors lines 948-955.
    if existing_path:
        return f"{des_bin}:{existing_path}"

    # Empty-seed: seed from live install-time PATH or fallback.
    live_path = live_env_path if live_env_path else SYSTEM_PATH_FALLBACK
    return f"{des_bin}:{live_path}"
