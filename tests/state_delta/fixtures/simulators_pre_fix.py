"""Faithful in-test simulator of pre-fix _update_path_in_settings (bug #48).

Mirrors des_plugin.py:881-958 BEFORE commit 832b4060 (the pre-fix logic that
ignored existing_path entirely and wrote a hardcoded SYSTEM_PATH_FALLBACK).

Asserted byte-equivalent to the pre-fix git blob in this PR's review; runtime
equivalence check intentionally omitted per MEDIUM-1 closure (the matcher's
contract is what we validate, not the production code's exact bytes).
"""

from __future__ import annotations


SYSTEM_PATH_FALLBACK = "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def update_path_in_settings_pre_fix(existing_path: str, des_bin: str) -> str:
    """Pre-fix bug #48 logic: ignores existing_path, writes hardcoded fallback.

    The bug: existing_path was never read; every install silently replaced the
    user's real PATH dirs with a minimal system fallback.  User dirs in PATH
    (/home/u/.local/bin, ~/.deno/bin, ~/.cargo/bin, etc.) were stripped.
    """
    return f"{des_bin}:{SYSTEM_PATH_FALLBACK}"
