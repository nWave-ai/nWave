"""Characterization guard for DESPlugin._hooks_already_installed.

`_hooks_already_installed(config)` is live production code
(scripts/install/plugins/des_plugin.py:1071), called by verify()
(des_plugin.py:1249). Its documented contract:

    "Returns True if ANY hook event type has a DES hook. This handles
     cases where only partial hooks exist (e.g., old format)."

WTBD-165 / PR #89 retired the bug-1 "Hook detection works for both old and
new command formats" acceptance scenario. That scenario's step 2 ("the hook
detection should return True" for an OLD-format hook) was the ONLY test
exercising this method — after the retirement `grep -rn _hooks_already_installed
tests/` returned nothing. The stale strict count-equality step was correctly
dropped, but the *valid* old-format DETECTION assertion went with it. This
module restores that lost coverage directly at the unit level.

These are GREEN-now characterization tests of existing, correct behaviour —
they pin the method's documented contract, they do not drive new code.

Paradigm note (bypass): `_hooks_already_installed` is a pure boolean classifier
over a config dict with a single return value and no side effects. Per the
state-delta / PBT mandate this is an EXEMPT category (pure-function, single
output) — example-based tests expressing each documented branch are the
correct, minimal shape. There is no multi-slot state surface to declare.
"""

from scripts.install.plugins.des_plugin import DESPlugin


# Old-format DES command shape, matching the retired scenario's
# `settings_with_old_format_hook` fixture
# (tests/bugs/plugins/des/installation/acceptance/steps/conftest.py:234).
# Flat entry, path-style invocation (not `-m`), carries the canonical
# "claude_code_hook_adapter" marker.
_OLD_FORMAT_COMMAND = (
    "python3 src/des/adapters/drivers/hooks/claude_code_hook_adapter.py pre-task"
)

# New-format DES command shape: nested `-m` module invocation, the format the
# canonical installer writes today.
_NEW_FORMAT_COMMAND = (
    "PYTHONPATH=/tmp/.claude/lib/python python3 -m "
    "des.adapters.drivers.hooks.claude_code_hook_adapter pre-task"
)


def test_old_format_hook_is_detected_as_installed():
    """An OLD-format (flat, path-style) DES hook returns True.

    This is the exact assertion the retired bug-1 scenario's step 2 covered:
    the partial/legacy installation must be recognised so install can clean up
    and reinstall. Regression guard for WTBD-165.
    """
    config = {
        "permissions": {"allow": []},
        "hooks": {
            "PreToolUse": [{"matcher": "Task", "command": _OLD_FORMAT_COMMAND}],
            "SubagentStop": [],
        },
    }

    assert DESPlugin()._hooks_already_installed(config) is True


def test_new_format_hook_is_detected_as_installed():
    """A NEW-format (nested `-m` module) DES hook returns True."""
    config = {
        "permissions": {"allow": []},
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Task",
                    "hooks": [{"type": "command", "command": _NEW_FORMAT_COMMAND}],
                }
            ],
        },
    }

    assert DESPlugin()._hooks_already_installed(config) is True


def test_non_des_hook_only_is_not_detected_as_installed():
    """A config whose only hook is non-DES returns False."""
    config = {
        "permissions": {"allow": []},
        "hooks": {
            "PreToolUse": [
                {"matcher": "Write", "command": "custom-write-validator.py"}
            ],
        },
    }

    assert DESPlugin()._hooks_already_installed(config) is False


def test_config_without_hooks_key_is_not_detected_as_installed():
    """A config with no "hooks" key returns False (the early-return branch)."""
    config = {"permissions": {"allow": []}}

    assert DESPlugin()._hooks_already_installed(config) is False
