"""PATH string Hypothesis strategy — lazy-imports hypothesis to keep wheel install clean.

A9 contract (ADR-002): hypothesis is imported ONLY inside function bodies,
never at module level. This ensures `import nwave_ai.state_delta.strategies`
does not load hypothesis into sys.modules.

Covers 4 production branches (Spike 2 taxonomy):

  Branch           | Trigger shape
  -----------------+---------------------------------------------------
  Empty-seed       | existing_path == ""
  $HOME-literal    | "$HOME" in existing_path
  Legacy-heal      | existing_path == "DES_BIN:SYSTEM_PATH_FALLBACK"
  Idempotent       | des_bin already first segment in existing_path
  Default-prepend  | any realistic multi-dir PATH (implicit 5th branch)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from hypothesis.strategies import SearchStrategy

# ---------------------------------------------------------------------------
# Constants — kept at module level so they can be imported without hypothesis
# ---------------------------------------------------------------------------

_LEGACY_SENTINEL = "DES_BIN:SYSTEM_PATH_FALLBACK"
_DES_BIN = "/des/bin"
_USER_DIRS = [
    "/home/u/.local/bin",
    "/home/u/.deno/bin",
    "/home/u/bin",
]
_SYSTEM_DIRS = [
    "/usr/bin",
    "/usr/local/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
]
_HOME_LITERAL_DIRS = [
    "$HOME/.local/bin",
    "$HOME/bin",
]
_WINDOWS_DES_BIN = "C:\\des\\bin"
_WINDOWS_USER_DIRS = [
    "C:\\Users\\u\\.local\\bin",
    "C:\\Users\\u\\AppData\\Local\\Programs\\Python\\Python312",
    "C:\\Users\\u\\bin",
]
_WINDOWS_SYSTEM_DIRS = [
    "C:\\Windows\\system32",
    "C:\\Windows",
    "C:\\Program Files\\Git\\cmd",
]
_WINDOWS_HOME_LITERAL_DIRS = [
    "$HOME\\.local\\bin",
    "$HOME\\bin",
]


def path_strategy(
    *,
    include_home_literal: bool = True,
    include_empty: bool = True,
    include_legacy_fallback: bool = True,
    sep: str | None = None,
) -> SearchStrategy[str]:
    """Composable Hypothesis strategy generating realistic PATH shapes.

    Lazy-imports hypothesis inside the function body to keep the
    nwave-ai wheel install hypothesis-free at module load time.

    Covers all 4 production branches from the Spike 2 taxonomy:
    - Empty-seed: ``""`` (when ``include_empty=True``)
    - $HOME-literal: strings containing ``$HOME`` (when ``include_home_literal=True``)
    - Legacy-heal: the exact string ``"DES_BIN:SYSTEM_PATH_FALLBACK"``
      (when ``include_legacy_fallback=True``)
    - Idempotent: paths whose first segment is already the DES bin
      (``/des/bin``, or ``C:\\des\\bin`` when ``sep`` is ``";"``)
    - Default-prepend: realistic multi-dir PATH strings (always included)

    Args:
        include_home_literal: When True, generated strings may contain
            ``$HOME``-style dir references (e.g. ``$HOME/.local/bin``).
        include_empty: When True, the empty string ``""`` may be generated.
        include_legacy_fallback: When True, the legacy sentinel string
            ``"DES_BIN:SYSTEM_PATH_FALLBACK"`` may be generated.
        sep: PATH separator, default ``os.pathsep`` (resolved at call time).
            With ``";"`` the entries are Windows-shaped drive-letter paths.

    Returns:
        A Hypothesis ``SearchStrategy[str]`` producing PATH-shaped strings.
    """
    # Lazy import — hypothesis is loaded only when this function is CALLED.
    from hypothesis import strategies as st

    separator = os.pathsep if sep is None else sep
    windows = separator == ";"
    des_bin = _WINDOWS_DES_BIN if windows else _DES_BIN

    # Build segment pool — always includes user dirs and system dirs
    if windows:
        segment_pool = list(_WINDOWS_USER_DIRS) + list(_WINDOWS_SYSTEM_DIRS)
        home_literal_dirs = _WINDOWS_HOME_LITERAL_DIRS
    else:
        segment_pool = list(_USER_DIRS) + list(_SYSTEM_DIRS)
        home_literal_dirs = _HOME_LITERAL_DIRS
    if include_home_literal:
        segment_pool += list(home_literal_dirs)

    # Branch 1: realistic separator-joined PATH from 1-5 segments (default-prepend)
    realistic_path = st.lists(
        st.sampled_from(segment_pool),
        min_size=1,
        max_size=5,
    ).map(separator.join)

    # Branch 2: idempotent shape — des_bin already occupies first segment
    idempotent_path = realistic_path.map(lambda s: f"{des_bin}{separator}{s}")

    # Assemble branches — start with the always-present ones
    branches: list[SearchStrategy[str]] = [realistic_path, idempotent_path]

    if include_empty:
        branches.append(st.just(""))

    if include_legacy_fallback:
        branches.append(st.just(_LEGACY_SENTINEL))

    return st.one_of(*branches)
