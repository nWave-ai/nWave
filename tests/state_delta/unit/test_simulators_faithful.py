"""Unit tests for update_path_in_settings_faithful (post-fix simulator).

Canned-fixture tests verifying the 5 production branches of the post-fix
_update_path_in_settings (post-832b4060, des_plugin.py:881-958).

Step-Id: 02-03 | Slice 2 | DoD #6 simulator unit tests
"""

from nwave_ai.state_delta.strategies import update_path_in_settings_faithful


DES_BIN = "/home/u/.local/share/nwave/bin"
HOME = "/home/u"
SYSTEM_PATH_FALLBACK = "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def test_faithful_empty_seed() -> None:
    """Branch 5 (empty-seed): empty existing_path seeds from live env or fallback.

    When settings.json has no PATH, the post-fix code seeds from the user's
    live install-time PATH or SYSTEM_PATH_FALLBACK. With no live env in
    the simulator, the output is des_bin + ":" + SYSTEM_PATH_FALLBACK.
    """
    result = update_path_in_settings_faithful(
        existing_path="",
        des_bin=DES_BIN,
        home=HOME,
        live_env_path="",
    )
    assert result == f"{DES_BIN}:{SYSTEM_PATH_FALLBACK}"


def test_faithful_legacy_heal_with_live_env() -> None:
    """Branch 2 (legacy-heal): legacy fabricated form healed with live env path.

    When existing_path == des_bin:SYSTEM_PATH_FALLBACK (the old installer's
    fabricated value), the post-fix code replaces it with des_bin + live PATH.
    """
    legacy_form = f"{DES_BIN}:{SYSTEM_PATH_FALLBACK}"
    live_env_path = "/usr/local/bin:/usr/bin"
    result = update_path_in_settings_faithful(
        existing_path=legacy_form,
        des_bin=DES_BIN,
        home=HOME,
        live_env_path=live_env_path,
    )
    assert result == f"{DES_BIN}:{live_env_path}"


def test_faithful_legacy_heal_no_live_env() -> None:
    """Branch 2 (legacy-heal): legacy fabricated form healed with fallback when no live env.

    When live_env_path is empty, falls back to SYSTEM_PATH_FALLBACK.
    """
    legacy_form = f"{DES_BIN}:{SYSTEM_PATH_FALLBACK}"
    result = update_path_in_settings_faithful(
        existing_path=legacy_form,
        des_bin=DES_BIN,
        home=HOME,
        live_env_path="",
    )
    assert result == f"{DES_BIN}:{SYSTEM_PATH_FALLBACK}"


def test_faithful_home_normalization() -> None:
    """Branch 1 (normalization): $HOME literals expanded to absolute paths.

    Post-fix code normalizes $HOME in existing_path before checking idempotency
    or prepending. Output must not contain literal '$HOME'.
    """
    result = update_path_in_settings_faithful(
        existing_path="$HOME/.local/bin:/usr/bin",
        des_bin=DES_BIN,
        home=HOME,
        live_env_path="/home/u/.local/bin:/usr/bin",
    )
    assert result.startswith(DES_BIN), "des_bin must be first segment"
    assert "/home/u/.local/bin" in result, "normalized path must contain absolute home"
    assert "$HOME" not in result, "$HOME literal must not remain"


def test_faithful_idempotency() -> None:
    """Branch 3 (idempotency): no double-prepend when des_bin already present.

    When des_bin is already a colon-delimited segment, output is unchanged.
    """
    existing_path = f"{DES_BIN}:/usr/bin"
    result = update_path_in_settings_faithful(
        existing_path=existing_path,
        des_bin=DES_BIN,
        home=HOME,
        live_env_path="/usr/bin",
    )
    assert result == existing_path


def test_faithful_default_prepend() -> None:
    """Branch 4 (default-prepend): non-special non-empty path gets des_bin prepended.

    When existing_path is non-empty, not legacy form, has no $HOME, and does
    not already contain des_bin, the post-fix code prepends des_bin.
    """
    existing_path = f"{HOME}/.local/bin:/usr/bin"
    result = update_path_in_settings_faithful(
        existing_path=existing_path,
        des_bin=DES_BIN,
        home=HOME,
        live_env_path=existing_path,
    )
    assert result == f"{DES_BIN}:{existing_path}"
