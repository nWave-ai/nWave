"""E2E: Codex CLI install (skills + agents + DES hooks + contract).

Layer 4 of platform-testing-strategy.md (parallel to test_opencode_full_install.py).

Validates that the nWave installer detects Codex (via ~/.codex/ directory or
codex binary in PATH) and installs the three Codex-shaped components with
proper format transformations:

  1. Skills at ~/.agents/skills/, each with SKILL.md (NOT under ~/.codex/)
  2. Agents at ~/.codex/agents/ as `.toml` files (Codex frontmatter shape)
  3. DES hook wired into ~/.codex/hooks.json with narrow ^Task$|^Bash$ matcher
  4. Three manifests:
       - ~/.agents/skills/.nwave-manifest.json
       - ~/.codex/agents/.nwave-agents-manifest.json
       - ~/.codex/.nwave-des-manifest.json
  5. Claude Code skill install parity preserved (concurrent target)

Closes the E2E gap that allowed prior Codex install regressions to ship
without acceptance-level coverage.

Uses the shared ``codex_container`` fixture (session scope) so the install
is amortized across all tests in this file.

Requires a Docker daemon.  Skips gracefully when Docker is unavailable.
"""

from __future__ import annotations

import json
import re

import pytest

from tests.e2e.conftest import exec_in_container, require_docker


# Core install markers — same contract as OpenCode (the installer plugins
# emit identical phase markers regardless of detected target).  The Codex
# install does NOT register a commands plugin (Codex has no slash-command
# surface), so we check the same four core markers as OpenCode.
_CORE_MARKERS = (
    "Skills installed",
    "Agents installed",
    "DES module",
    "Settings updated",
)


@pytest.mark.e2e
@require_docker
class TestCodexFullInstall:
    """Codex-aware installer deploys skills, agents, DES hooks with contract."""

    # --- 1. Install succeeded (core markers) -----------------------------

    def test_install_produced_core_component_markers(self, codex_container) -> None:
        """>=3 of 4 core install markers must appear in installer stdout.

        Mirrors the OpenCode heuristic: optional plugins may fail without
        invalidating the core install contract.
        """
        stdout = getattr(codex_container, "_install_stdout", "")
        found = sum(1 for m in _CORE_MARKERS if m in stdout)
        assert found >= 3, (
            f"Only {found}/{len(_CORE_MARKERS)} core markers found in install output.\n"
            f"Markers expected: {_CORE_MARKERS}\n"
            f"Install output tail:\n{stdout[-800:]}"
        )

    # --- 2. Codex skills (under ~/.agents/skills/, NOT ~/.codex/) -------

    def test_codex_skills_directory_populated(self, codex_container) -> None:
        """Codex skills land at ~/.agents/skills/ (sibling of ~/.codex/)."""
        _code, out = exec_in_container(
            codex_container,
            [
                "bash",
                "-c",
                (
                    "find /home/tester/.agents/skills -maxdepth 1 -mindepth 1 "
                    "-type d 2>/dev/null | wc -l"
                ),
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 50, (
            f"Only {count} skill dirs under ~/.agents/skills/ (expected > 50)."
        )

    def test_every_codex_skill_has_skill_md(self, codex_container) -> None:
        """Every installed skill directory must contain SKILL.md."""
        _code, out = exec_in_container(
            codex_container,
            [
                "bash",
                "-c",
                (
                    "skills=/home/tester/.agents/skills; "
                    "total=$(find $skills -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l); "
                    "with=$(find $skills -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l); "
                    'echo "$with/$total"'
                ),
            ],
        )
        try:
            with_md, total = (int(x) for x in out.strip().split("/"))
        except ValueError:
            pytest.fail(f"Could not parse: {out!r}")
        assert with_md == total and total > 0, (
            f"{with_md}/{total} Codex skill dirs have SKILL.md."
        )

    def test_codex_skills_manifest_present_and_versioned(self, codex_container) -> None:
        """Skills manifest tracks installation for clean uninstall."""
        code, out = exec_in_container(
            codex_container,
            ["cat", "/home/tester/.agents/skills/.nwave-manifest.json"],
        )
        assert code == 0, "Codex skills manifest missing."
        try:
            data = json.loads(out)
        except json.JSONDecodeError as exc:
            pytest.fail(f"Skills manifest is not valid JSON: {exc}\n{out[:300]}")
        assert "installed_skills" in data, "Manifest missing 'installed_skills' key."
        assert data.get("version") == "1.0", (
            f"Skills manifest version is {data.get('version')!r}, expected '1.0'."
        )

    def test_codex_skills_strip_claude_only_frontmatter_fields(
        self, codex_container
    ) -> None:
        """``user-invocable`` and ``disable-model-invocation`` are Claude-only."""
        forbidden = ("user-invocable", "disable-model-invocation")
        _code, out = exec_in_container(
            codex_container,
            [
                "bash",
                "-c",
                (
                    "cd /home/tester/.agents/skills && "
                    "found=''; for f in $(find . -name SKILL.md | head -20); do "
                    "  head -20 \"$f\" | grep -E '^(user-invocable|disable-model-invocation):' "
                    '  && found="$found $f"; done; '
                    'echo "RESULT=$found"'
                ),
            ],
        )
        assert "RESULT=" in out and out.split("RESULT=", 1)[1].strip() == "", (
            f"Claude-only frontmatter fields {forbidden} found in Codex skills.\n{out[-400:]}"
        )

    # --- 3. Codex agents (TOML format under ~/.codex/agents/) -----------

    def test_codex_agents_installed_as_toml(self, codex_container) -> None:
        """Codex agents are TOML files (NOT markdown like Claude/OpenCode)."""
        _code, out = exec_in_container(
            codex_container,
            [
                "bash",
                "-c",
                "find /home/tester/.codex/agents -name 'nw-*.toml' 2>/dev/null | wc -l",
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 10, f"Only {count} Codex agents installed (expected > 10)."

    def test_codex_agents_manifest_present(self, codex_container) -> None:
        """Agents manifest tracks installation for clean uninstall."""
        code, out = exec_in_container(
            codex_container,
            ["cat", "/home/tester/.codex/agents/.nwave-agents-manifest.json"],
        )
        assert code == 0, "Codex agents manifest missing."
        try:
            data = json.loads(out)
        except json.JSONDecodeError as exc:
            pytest.fail(f"Agents manifest invalid JSON: {exc}")
        assert "installed_agents" in data, "Agents manifest missing 'installed_agents'."

    def test_codex_agents_have_required_toml_fields(self, codex_container) -> None:
        """Each Codex agent TOML must declare name + developer_instructions."""
        _code, out = exec_in_container(
            codex_container,
            [
                "bash",
                "-c",
                (
                    "cd /home/tester/.codex/agents && "
                    "missing=0; for f in $(ls nw-*.toml | head -10); do "
                    '  grep -q "^name = " "$f" || missing=$((missing+1)); '
                    '  grep -q "^developer_instructions = " "$f" || missing=$((missing+1)); '
                    "done; "
                    'echo "MISSING=$missing"'
                ),
            ],
        )
        m = re.search(r"MISSING=(\d+)", out)
        assert m and int(m.group(1)) == 0, (
            f"Codex agents missing required TOML fields.\n{out[-400:]}"
        )

    def test_codex_agents_strip_claude_only_fields(self, codex_container) -> None:
        """tools/skills (block-form) are Claude-only and must NOT appear in TOML.

        ``model = "inherit"`` is allowed (it is the Codex-native default).
        """
        _code, out = exec_in_container(
            codex_container,
            [
                "bash",
                "-c",
                (
                    "cd /home/tester/.codex/agents && "
                    'bad=""; for f in $(ls nw-*.toml | head -10); do '
                    "  head -30 \"$f\" | grep -qE '^(tools|skills) = ' "
                    '    && bad="$bad $f"; done; '
                    'echo "BAD=$bad"'
                ),
            ],
        )
        assert out.strip().endswith("BAD="), (
            f"Claude-only fields (tools/skills block-form) found in Codex agents.\n{out[-400:]}"
        )

    # --- 4. Codex DES hook (~/.codex/hooks.json + manifest) -------------

    @pytest.mark.broken_schema_v0
    def test_codex_des_hook_installed(self, codex_container) -> None:
        """hooks.json must exist and contain the nWave PreToolUse entry.

        QUARANTINED (DDD-7 / FM-4): this test asserts the pre-FM-1 internal
        schema (top-level array root), which is incompatible with the Codex-
        documented event-keyed object root.  Superseded by
        ``tests/e2e/test_codex_real_boot.py`` which proves the install fires
        the DES adapter end-to-end on the correct schema.

        Excluded from default CI selection via ``-m "not broken_schema_v0"``.
        Kept on disk so the audit trail of the FM-4 closure remains visible.
        """
        code, out = exec_in_container(
            codex_container,
            ["cat", "/home/tester/.codex/hooks.json"],
        )
        assert code == 0, "Codex hooks.json missing."
        try:
            hooks = json.loads(out)
        except json.JSONDecodeError as exc:
            pytest.fail(f"hooks.json is not valid JSON: {exc}\n{out[:300]}")
        assert isinstance(hooks, list) and len(hooks) > 0, (
            f"hooks.json must be a non-empty list, got: {hooks!r}"
        )

    @pytest.mark.broken_schema_v0
    def test_codex_des_hook_uses_narrow_matcher(self, codex_container) -> None:
        """Matcher must be ^Task$|^Bash$ (NOT .* — wildcard was the WS default).

        QUARANTINED (FM-3 closure 2026-05-13 c13d7397e): assertion is the
        pre-FM-3 matcher; production now uses ^Bash$|^apply_patch$ (documented
        Codex tools). Superseded by tests/e2e/test_codex_real_boot.py.
        """
        _code, out = exec_in_container(
            codex_container,
            ["cat", "/home/tester/.codex/hooks.json"],
        )
        hooks = json.loads(out)
        nwave_entries = [
            entry
            for entry in hooks
            if any(
                "claude_code_hook_adapter" in h.get("command", "")
                for h in entry.get("hooks", [])
            )
        ]
        assert len(nwave_entries) == 1, (
            f"Expected exactly one nWave hook entry, found {len(nwave_entries)}."
        )
        matcher = nwave_entries[0].get("matcher", "")
        assert matcher == "^Task$|^Bash$", (
            f"DES hook matcher is {matcher!r}, expected '^Task$|^Bash$' "
            f"(narrow production matcher; .* was a walking-skeleton default)."
        )

    def test_codex_des_manifest_present(self, codex_container) -> None:
        """DES manifest tracks the hook installation for clean uninstall."""
        code, out = exec_in_container(
            codex_container,
            ["cat", "/home/tester/.codex/.nwave-des-manifest.json"],
        )
        assert code == 0, "Codex DES manifest missing."
        try:
            data = json.loads(out)
        except json.JSONDecodeError as exc:
            pytest.fail(f"DES manifest invalid JSON: {exc}")
        assert "hooks_file" in data, "DES manifest missing 'hooks_file' key."

    # --- 5. Claude Code skills parity install ----------------------------

    def test_claude_code_skills_also_installed(self, codex_container) -> None:
        """Installing with Codex detected must NOT skip the Claude install.

        Both targets must receive the skill set so the user can switch CLIs
        without reinstalling.
        """
        _code, out = exec_in_container(
            codex_container,
            [
                "bash",
                "-c",
                (
                    "find /home/tester/.claude/skills -maxdepth 1 -mindepth 1 "
                    "-type d -name 'nw-*' 2>/dev/null | wc -l"
                ),
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 50, (
            f"Only {count} Claude Code skills installed (expected > 50).  "
            "Codex install must preserve Claude install parity."
        )
