"""
Hook Installation Step Definitions for Bug 1: Duplicate Hooks.

This module contains step definitions for testing:
- Hook idempotency (multiple installs should not create duplicates)
- Hook uninstall (should remove ALL DES hooks including duplicates)
- Hook format detection (old vs new command formats)
- Non-DES hook preservation

Domain: Hook Management
Bug: Running installer multiple times creates duplicate hook entries
"""

import json
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, then, when

from .helpers import count_des_hooks, is_des_hook, is_des_hook_entry


# -----------------------------------------------------------------------------
# Given Steps: Hook Preconditions
# -----------------------------------------------------------------------------


@given("a clean settings.local.json with no hooks")
def clean_settings_no_hooks(clean_settings_file: Path, test_context: dict):
    """
    Start with a clean settings.local.json containing no hooks.

    This is the baseline state before any DES installation.
    """
    test_context["settings_file"] = clean_settings_file

    # Verify no hooks exist
    with open(clean_settings_file) as f:
        config = json.load(f)

    assert "hooks" not in config or not config.get("hooks"), (
        "Clean settings file should not contain hooks"
    )


@given(
    parsers.parse(
        "settings.local.json contains {count:d} duplicate DES PreToolUse hooks"
    )
)
def settings_with_n_pretooluse_hooks(
    settings_with_duplicates: Path, count: int, test_context: dict
):
    """
    Create settings.local.json with specified number of duplicate PreToolUse hooks.

    This simulates the bug state after multiple install runs.
    """
    test_context["settings_file"] = settings_with_duplicates

    # Verify the duplicates are present
    actual_count = count_des_hooks(settings_with_duplicates, "PreToolUse")
    assert actual_count == count, (
        f"Expected {count} DES PreToolUse hooks but found {actual_count}"
    )


@given(
    parsers.parse(
        "settings.local.json contains {count:d} duplicate DES SubagentStop hooks"
    )
)
def settings_with_n_subagent_hooks(
    settings_with_duplicates: Path, count: int, test_context: dict
):
    """
    Verify settings.local.json has specified number of SubagentStop hooks.
    """
    # settings_with_duplicates fixture already set up duplicates
    actual_count = count_des_hooks(settings_with_duplicates, "SubagentStop")
    assert actual_count == count, (
        f"Expected {count} DES SubagentStop hooks but found {actual_count}"
    )


@given("settings.local.json contains a custom non-DES PreToolUse hook")
def settings_with_custom_hook(settings_with_mixed_hooks: Path, test_context: dict):
    """
    Start with settings containing both DES and non-DES hooks.

    Used for testing that non-DES hooks are preserved.
    """
    test_context["settings_file"] = settings_with_mixed_hooks

    # Verify the custom hook exists
    with open(settings_with_mixed_hooks) as f:
        config = json.load(f)

    pre_hooks = config.get("hooks", {}).get("PreToolUse", [])
    non_des_hooks = [h for h in pre_hooks if not is_des_hook_entry(h)]
    assert len(non_des_hooks) > 0, "Expected at least one non-DES hook"


@given("settings.local.json contains DES hooks")
def settings_with_des_hooks(settings_with_mixed_hooks: Path, test_context: dict):
    """Verify settings contains DES hooks."""
    des_count = count_des_hooks(settings_with_mixed_hooks, "PreToolUse")
    assert des_count > 0, "Expected at least one DES hook"


@given("settings.local.json contains a DES hook with old format command")
def settings_with_old_format(settings_with_old_format_hook: Path, test_context: dict):
    """
    Start with settings containing old-format DES hook command.

    Old format: python3 src/des/.../claude_code_hook_adapter.py
    """
    test_context["settings_file"] = settings_with_old_format_hook


@given("DES hooks were previously installed and uninstalled")
def hooks_installed_then_uninstalled(
    temp_claude_dir: Path, install_context, des_plugin, test_context: dict
):
    """
    Simulate install -> uninstall cycle.

    Creates clean state as if DES was previously used but then removed.
    """
    # Create settings file (plugin reads/writes settings.json)
    settings_file = temp_claude_dir / "settings.json"
    settings_file.write_text(json.dumps({"permissions": {"allow": []}}, indent=2))
    test_context["settings_file"] = settings_file

    # Install hooks
    des_plugin._install_des_hooks(install_context)

    # Verify hooks were installed
    des_count = count_des_hooks(settings_file, "PreToolUse")
    assert des_count > 0, "Hooks should be installed before uninstall test"

    # Uninstall hooks
    des_plugin._uninstall_des_hooks(install_context)

    # Verify hooks were removed
    des_count_after = count_des_hooks(settings_file, "PreToolUse")
    assert des_count_after == 0, "Hooks should be removed after uninstall"


# -----------------------------------------------------------------------------
# When Steps: Hook Actions
# -----------------------------------------------------------------------------


@when("I install DES hooks")
def install_des_hooks(
    temp_claude_dir: Path, install_context, des_plugin, test_context: dict
):
    """
    Install DES hooks using the production DESPlugin.

    Uses the real DESPlugin._install_des_hooks() method.
    """
    # Ensure settings file exists (plugin reads/writes settings.json)
    settings_file = test_context.get("settings_file")
    if not settings_file:
        settings_file = temp_claude_dir / "settings.json"
        if not settings_file.exists():
            settings_file.write_text(
                json.dumps({"permissions": {"allow": []}}, indent=2)
            )
        test_context["settings_file"] = settings_file

    # Update install_context to use our test settings location
    install_context.claude_dir = temp_claude_dir

    # Install hooks using production code
    result = des_plugin._install_des_hooks(install_context)
    test_context["install_result"] = result


@when("I install DES hooks again")
def install_des_hooks_again(install_context, des_plugin, test_context: dict):
    """
    Install DES hooks a second time.

    This should NOT create duplicates if idempotency is working correctly.
    """
    result = des_plugin._install_des_hooks(install_context)
    test_context["second_install_result"] = result


@when("I uninstall DES hooks")
def uninstall_des_hooks(install_context, des_plugin, test_context: dict):
    """
    Uninstall DES hooks using the production DESPlugin.
    """
    result = des_plugin._uninstall_des_hooks(install_context)
    test_context["uninstall_result"] = result


@when("I check if DES hooks are already installed")
def check_hooks_already_installed(des_plugin, test_context: dict):
    """
    Check if DES hook detection works.
    """
    settings_file = test_context.get("settings_file")
    with open(settings_file) as f:
        config = json.load(f)

    test_context["hooks_detected"] = des_plugin._hooks_already_installed(config)


@when("I install DES hooks using new format")
def install_hooks_new_format(install_context, des_plugin, test_context: dict):
    """
    Install hooks with new format command.

    This tests whether old-format hooks are detected and replaced.
    """
    result = des_plugin._install_des_hooks(install_context)
    test_context["install_result"] = result


# -----------------------------------------------------------------------------
# Then Steps: Hook Assertions
# -----------------------------------------------------------------------------


@then(
    parsers.parse(
        "settings.local.json should contain exactly {count:d} PreToolUse hook"
    )
)
def verify_pretooluse_hook_count(count: int, test_context: dict):
    """
    Verify the exact number of PreToolUse hooks.

    BUG DETECTION: If this fails with count > expected, the duplicate bug exists.
    """
    settings_file = test_context.get("settings_file")
    actual_count = count_des_hooks(settings_file, "PreToolUse")

    assert actual_count == count, (
        f"BUG DETECTED: Expected exactly {count} DES PreToolUse hook(s), "
        f"but found {actual_count}. "
        f"This indicates the duplicate hook bug is present."
    )


@then(
    parsers.parse(
        "settings.local.json should contain exactly {count:d} SubagentStop hook"
    )
)
def verify_subagent_hook_count(count: int, test_context: dict):
    """
    Verify the exact number of SubagentStop hooks.

    BUG DETECTION: If this fails with count > expected, the duplicate bug exists.
    """
    settings_file = test_context.get("settings_file")
    actual_count = count_des_hooks(settings_file, "SubagentStop")

    assert actual_count == count, (
        f"BUG DETECTED: Expected exactly {count} DES SubagentStop hook(s), "
        f"but found {actual_count}. "
        f"This indicates the duplicate hook bug is present."
    )


@then(
    parsers.parse(
        "settings.local.json should contain exactly {count:d} DES PreToolUse hook"
    )
)
def verify_des_pretooluse_hook_count_singular(count: int, test_context: dict):
    """
    Verify the exact number of DES PreToolUse hooks (singular form for grammar).

    This is the same as verify_des_pretooluse_count but uses singular 'hook'.
    """
    verify_des_pretooluse_count(count, test_context)


@then(
    parsers.parse("settings.local.json should contain {count:d} DES PreToolUse hooks")
)
def verify_des_pretooluse_count(count: int, test_context: dict):
    """Verify DES PreToolUse hook count (used for uninstall tests)."""
    settings_file = test_context.get("settings_file")
    actual_count = count_des_hooks(settings_file, "PreToolUse")

    assert actual_count == count, (
        f"Expected {count} DES PreToolUse hooks but found {actual_count}"
    )


@then(
    parsers.parse("settings.local.json should contain {count:d} DES SubagentStop hooks")
)
def verify_des_subagent_count(count: int, test_context: dict):
    """Verify DES SubagentStop hook count."""
    settings_file = test_context.get("settings_file")
    actual_count = count_des_hooks(settings_file, "SubagentStop")

    assert actual_count == count, (
        f"Expected {count} DES SubagentStop hooks but found {actual_count}"
    )


@then(parsers.parse("settings.local.json should contain {count:d} DES hooks"))
def verify_total_des_hook_count(count: int, test_context: dict):
    """Verify total DES hook count across all types."""
    settings_file = test_context.get("settings_file")
    pretooluse_count = count_des_hooks(settings_file, "PreToolUse")
    subagent_count = count_des_hooks(settings_file, "SubagentStop")
    total = pretooluse_count + subagent_count

    assert total == count, (
        f"Expected {count} total DES hooks but found {total} "
        f"(PreToolUse: {pretooluse_count}, SubagentStop: {subagent_count})"
    )


@then("no duplicate hook entries should exist")
def verify_no_duplicates(test_context: dict):
    """
    Verify no duplicate hook entries exist.

    Checks that each hook command appears only once.
    Supports both flat and nested hook formats.
    """
    settings_file = test_context.get("settings_file")
    with open(settings_file) as f:
        config = json.load(f)

    for hook_type in ["PreToolUse", "SubagentStop"]:
        hooks = config.get("hooks", {}).get(hook_type, [])
        des_commands = []
        for h in hooks:
            # Flat format
            cmd = h.get("command", "")
            if is_des_hook(cmd):
                des_commands.append(cmd)
            # Nested format
            for inner in h.get("hooks", []):
                cmd = inner.get("command", "")
                if is_des_hook(cmd):
                    des_commands.append(cmd)

        # Check for duplicates
        unique_commands = set(des_commands)
        if len(des_commands) != len(unique_commands):
            pytest.fail(
                f"BUG DETECTED: Duplicate DES hooks found in {hook_type}. "
                f"Found {len(des_commands)} hooks but only {len(unique_commands)} unique. "
                f"Commands: {des_commands}"
            )


@then("non-DES hooks should be preserved")
def verify_non_des_hooks_preserved(test_context: dict):
    """
    Verify that non-DES hooks are not affected by DES operations.
    """
    settings_file = test_context.get("settings_file")
    with open(settings_file) as f:
        config = json.load(f)

    pre_hooks = config.get("hooks", {}).get("PreToolUse", [])
    non_des_hooks = [h for h in pre_hooks if not is_des_hook_entry(h)]

    assert len(non_des_hooks) > 0, (
        "BUG: Non-DES hooks were removed during DES operation. "
        "Expected at least one non-DES hook to be preserved."
    )


@then("the custom non-DES hook should still exist")
def verify_custom_hook_exists(test_context: dict):
    """Verify the specific custom hook still exists."""
    settings_file = test_context.get("settings_file")
    with open(settings_file) as f:
        config = json.load(f)

    pre_hooks = config.get("hooks", {}).get("PreToolUse", [])
    custom_hooks = [
        h for h in pre_hooks if "custom-write-validator" in h.get("command", "")
    ]

    assert len(custom_hooks) == 1, (
        "Custom non-DES hook was not preserved during DES operation"
    )


@then("settings.local.json should contain the custom non-DES hook")
def verify_contains_custom_hook(test_context: dict):
    """Verify settings contains the custom hook."""
    verify_custom_hook_exists(test_context)


@then("the hook detection should return True")
def verify_hook_detection_true(test_context: dict):
    """Verify that hook detection correctly identifies DES hooks."""
    assert test_context.get("hooks_detected") is True, (
        "BUG: Hook detection failed to recognize existing DES hooks. "
        "This can cause duplicate hooks on reinstall."
    )


@then("installing hooks again should not add duplicates")
def verify_no_new_duplicates(install_context, des_plugin, test_context: dict):
    """Verify that a second install doesn't add duplicates."""
    settings_file = test_context.get("settings_file")

    # Count hooks before
    before_count = count_des_hooks(settings_file, "PreToolUse")

    # Install again
    des_plugin._install_des_hooks(install_context)

    # Count hooks after
    after_count = count_des_hooks(settings_file, "PreToolUse")

    assert after_count == before_count, (
        f"BUG DETECTED: Installing hooks again added duplicates. "
        f"Before: {before_count}, After: {after_count}"
    )


@then("the hook should use the new command format")
def verify_new_command_format(test_context: dict):
    """Verify hooks use the new nested command format (python3 -m ...)."""
    settings_file = test_context.get("settings_file")
    with open(settings_file) as f:
        config = json.load(f)

    pre_hooks = config.get("hooks", {}).get("PreToolUse", [])

    # Collect DES hook commands from both flat and nested formats
    des_commands = []
    for h in pre_hooks:
        # Flat format
        if is_des_hook(h.get("command", "")):
            des_commands.append(h.get("command", ""))
        # Nested format
        for inner in h.get("hooks", []):
            if is_des_hook(inner.get("command", "")):
                des_commands.append(inner.get("command", ""))

    assert len(des_commands) > 0, "No DES hooks found"

    for command in des_commands:
        assert "python3 -m des." in command, (
            f"Hook command should use new format 'python3 -m des...', "
            f"but found: {command}"
        )
        assert "src/des" not in command, (
            f"Hook command should not contain old 'src/des' path, but found: {command}"
        )
