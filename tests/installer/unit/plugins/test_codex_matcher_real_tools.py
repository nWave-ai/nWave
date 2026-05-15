"""Unit tests for the Codex DES plugin matcher whitelist (US-3 / FM-3).

Single-behavior unit test that pins the contract: ``_build_hook_entry`` MUST
produce a matcher regex whose alternations are restricted to the documented
Codex tool whitelist ``{"Bash", "apply_patch"}`` — no reference to ``Task``
(which is a Claude-Code-internal tool name Codex never emits in PreToolUse).

Whitelist source: DDD-6 refined by DDD-8 spike Q6
(``docs/feature/codex-empirical-e2e-support/spike-codex-hooks-schema.md`` lines
157+). ``Edit|Write`` aliases are deferred per DESIGN out-of-scope for this
slice; MCP names also deferred.

Budget: 1 behavior (matcher whitelist) x 2 = 2 unit tests. Coverage shape:
1. Alternation-membership property → matcher ⊆ whitelist (catches Task literal
   transitively since Task ∉ whitelist).
2. Match-rejection property → ∀ name ∉ whitelist · matcher rejects name
   (covers Claude-Code-only names + fabricated names + empty string).
The "matches every whitelisted tool" direction is folded into the acceptance
suite (matcher-real-tools.feature: Bash + apply_patch positive scenarios) to
keep the unit budget honest.

WHY-NEW-FILE: tests/installer/unit/plugins/test_codex_matcher_real_tools.py
  CLOSEST-EXISTING: tests/installer/unit/plugins/test_codex_argv_contract.py
  EXTENSION-COST: existing file is the FM-2 argv contract, scoped to a single
    invariant on the command-string tail. Adding a matcher-whitelist class
    there mixes orthogonal FMs (argv vs matcher) and makes regression triage
    harder to locate by FM ID.
  PARALLEL-RATIONALE: the matcher whitelist is a discrete, FM-tracked
    invariant DDD-6 locks against the Codex hooks documentation. Co-locating
    its test in a 1-class file makes the FM-3 regression net trivially
    greppable and keeps the contract surface explicit.
"""

from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from scripts.install.plugins.codex_des_plugin import _build_hook_entry


# Vetted whitelist sourced from DDD-6 / DDD-8 spike Q6.
# Source: docs/feature/codex-empirical-e2e-support/spike-codex-hooks-schema.md
_CODEX_TOOL_WHITELIST: tuple[str, ...] = ("Bash", "apply_patch")

# Fabricated / Claude-Code-only names that MUST NOT match.
_BLACKLIST: tuple[str, ...] = (
    "Task",
    "Read",
    "Edit",
    "Write",
    "Grep",
    "Glob",
    "FictionalTool",
    "",
)


def _alternations(matcher_regex: str) -> list[str]:
    """Split `^A$|^B$` regex into ['A', 'B']."""
    parts = matcher_regex.split("|")
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if p.startswith("^"):
            p = p[1:]
        if p.endswith("$"):
            p = p[:-1]
        out.append(p)
    return out


class TestBuildHookEntryMatcherWhitelist:
    """``_build_hook_entry`` matcher MUST be restricted to Codex-real tools."""

    def test_every_alternation_is_in_whitelist(self) -> None:
        """Property: matcher alternations ⊆ documented Codex tool whitelist.

        Catches FM-3 transitively: ``Task`` is not in the whitelist, so a
        matcher containing ``^Task$`` would fail this assertion. Covers both
        "no Task literal" and "alternations are vetted" in one property check.
        """
        entry = _build_hook_entry("/usr/bin/python3", "/home/tester/.claude/lib/python")
        matcher = entry["matcher"]
        whitelist = set(_CODEX_TOOL_WHITELIST)
        for alt in _alternations(matcher):
            assert alt in whitelist, (
                f"alternation {alt!r} not in whitelist {sorted(whitelist)}; "
                f"matcher={matcher!r}"
            )

    @given(tool_name=st.sampled_from(_BLACKLIST))
    @settings(max_examples=20, deadline=None)
    def test_matcher_rejects_every_non_whitelisted_name(self, tool_name: str) -> None:
        """Property: ∀ name ∉ whitelist · matcher does NOT match name.

        Covers Claude-Code-only names (Task, Read, Edit), aliases deferred to a
        later slice (Write), and fabricated names — including the empty string.
        """
        entry = _build_hook_entry("/usr/bin/python3", "/home/tester/.claude/lib/python")
        matcher = entry["matcher"]
        assert not re.match(matcher, tool_name), (
            f"matcher {matcher!r} must NOT match non-whitelisted name {tool_name!r}"
        )
