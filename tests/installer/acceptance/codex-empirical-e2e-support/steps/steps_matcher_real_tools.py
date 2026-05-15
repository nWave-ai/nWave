"""Step bodies for slice-04 (US-3) — matcher real-tools whitelist (FM-3 closure).

Driving port: ``CodexDESPlugin.install(context)`` followed by reading the
installed ``~/.codex/hooks.json`` and extracting the PreToolUse matcher regex.
Port-to-port: if the matcher constant in ``_build_hook_entry`` is reverted to
``^Task$|^Bash$`` (or anything containing "Task"), the first scenario fails on
the literal-substring assertion, the Task-rejection scenario fails on the
regex-match assertion, and the whitelist-membership scenario fails on the
alternation property.

Whitelist source: DDD-6 (refined by DDD-8 spike Q6, see
``docs/feature/codex-empirical-e2e-support/spike-codex-hooks-schema.md`` lines
157+ — matcher universe for this slice is the tuple ``("Bash", "apply_patch")``,
``Edit|Write`` aliases deferred per DESIGN out-of-scope, MCP names deferred).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from scripts.install.plugins.codex_des_plugin import CodexDESPlugin


scenarios("../matcher-real-tools.feature")


# --- Helpers ---------------------------------------------------------------


def _read_hooks(hooks_path: Path) -> dict:
    return json.loads(hooks_path.read_text(encoding="utf-8"))


def _pretool_entries(parsed: dict) -> list[dict]:
    assert isinstance(parsed, dict)
    return parsed.get("hooks", {}).get("PreToolUse", [])


def _nwave_matcher_strings(parsed: dict) -> list[str]:
    """Every matcher regex string attached to a nWave handler."""
    matchers: list[str] = []
    for entry in _pretool_entries(parsed):
        for handler in entry.get("hooks", []):
            cmd = handler.get("command", "")
            if "claude_code_hook_adapter" in cmd:
                matchers.append(entry.get("matcher", ""))
                break  # one matcher per group is enough
    return matchers


def _alternations(matcher_regex: str) -> list[str]:
    """Split a `^A$|^B$|^C$` regex into ['A', 'B', 'C']."""
    parts = matcher_regex.split("|")
    out: list[str] = []
    for p in parts:
        p = p.strip()
        # Strip leading ^ and trailing $ anchors if present.
        if p.startswith("^"):
            p = p[1:]
        if p.endswith("$"):
            p = p[:-1]
        out.append(p)
    return out


# --- Given -----------------------------------------------------------------


@given("a clean Codex environment with no prior nWave hooks")
def clean_codex_environment(codex_home: Path) -> None:
    assert codex_home.is_dir()
    assert not (codex_home / "hooks.json").exists()


# --- When ------------------------------------------------------------------


@when("the nwave-ai installer is run with --platform codex")
def installer_run_codex(install_context, patched_resolvers, hooks_path, state) -> None:
    plugin = CodexDESPlugin()
    result = plugin.install(install_context)
    state["install_result"] = result
    assert result.success, f"install must succeed; got {result.message}"
    assert hooks_path.exists(), f"hooks.json must be written at {hooks_path}"
    parsed = _read_hooks(hooks_path)
    state["parsed_hooks"] = parsed
    matchers = _nwave_matcher_strings(parsed)
    assert matchers, "installer must produce at least one nWave matcher"
    state["matchers"] = matchers


# --- Then ------------------------------------------------------------------


@then(
    parsers.parse(
        'the PreToolUse matcher regex contains zero occurrences of the literal "{literal}"'
    )
)
def matcher_no_literal(literal: str, state) -> None:
    for matcher in state["matchers"]:
        assert literal not in matcher, (
            f"matcher must not contain literal {literal!r}; got {matcher!r}"
        )


@then(parsers.parse('the matcher does not match a tool named "{name}"'))
def matcher_does_not_match_tool(name: str, state) -> None:
    for matcher in state["matchers"]:
        assert not re.match(matcher, name), (
            f"matcher {matcher!r} must NOT match tool name {name!r}"
        )


@then(
    "every alternation in the PreToolUse matcher regex is a member of the vetted Codex tool whitelist"
)
def every_alternation_in_whitelist(state, codex_tool_whitelist) -> None:
    whitelist = set(codex_tool_whitelist)
    for matcher in state["matchers"]:
        for alt in _alternations(matcher):
            assert alt in whitelist, (
                f"alternation {alt!r} (from matcher {matcher!r}) is NOT in "
                f"vetted Codex whitelist {sorted(whitelist)}"
            )


@then("the whitelist is sourced from the DESIGN docs citation")
def whitelist_sourced_from_docs(codex_tool_whitelist) -> None:
    # Conftest fixture docstring cites DDD-6 + DDD-8 spike artifact. Confirm
    # the fixture holds the exact tuple sourced from the citation.
    assert codex_tool_whitelist == ("Bash", "apply_patch"), (
        f"whitelist must be the DDD-6/DDD-8-cited tuple; got {codex_tool_whitelist!r}"
    )


@then(parsers.parse('the matcher regex matches the tool name "{name}"'))
def matcher_matches_tool(name: str, state) -> None:
    matched = any(re.match(m, name) for m in state["matchers"])
    assert matched, (
        f"at least one matcher must match tool name {name!r}; "
        f"matchers={state['matchers']!r}"
    )


@then(parsers.parse('the matcher regex does not match a fabricated tool name "{name}"'))
def matcher_does_not_match_fabricated(name: str, state) -> None:
    for matcher in state["matchers"]:
        assert not re.match(matcher, name), (
            f"matcher {matcher!r} must NOT match fabricated name {name!r}"
        )


@then("the matcher regex does not match the empty string")
def matcher_does_not_match_empty(state) -> None:
    for matcher in state["matchers"]:
        assert not re.match(matcher, ""), (
            f"matcher {matcher!r} must NOT match the empty string"
        )


@then(parsers.parse('the matcher regex does not match the tool name "{name}"'))
def matcher_does_not_match_named_tool(name: str, state) -> None:
    for matcher in state["matchers"]:
        assert not re.match(matcher, name), (
            f"matcher {matcher!r} must NOT match tool name {name!r}"
        )
