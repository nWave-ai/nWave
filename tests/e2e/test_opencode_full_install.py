"""E2E: OpenCode CLI install (skills + agents + commands + contract).

Migrated from: tests/e2e/Dockerfile.env-opencode
Layer 4 of platform-testing-strategy.md

Validates that the nWave installer detects OpenCode configuration and
installs skills, agents, and commands to the correct OpenCode paths with
proper format transformations:

  1. Skills at ~/.config/opencode/skills/, each with SKILL.md
  2. Agents at ~/.config/opencode/agents/, mode: subagent, no tools: CSV
  3. Commands at ~/.config/opencode/commands/
  4. No Claude Code-only frontmatter in skills (user-invocable, disable-model-invocation)
  5. No Claude Code-only fields in agents (name, model, skills)
  6. Agent skill-path references rewritten ~/.claude/skills -> ~/.config/opencode/skills
  7. Manifests present and versioned
  8. Parallel Claude Code skill install preserved (parity)

13 assertions total.  Uses the shared ``opencode_container`` fixture
(session scope) so expensive npm + nodejs + opencode-ai setup is
amortized with test_opencode_subagent_hooks.

Requires a Docker daemon.  Skips gracefully when Docker is unavailable.

Step-Id: 01-03
"""

from __future__ import annotations

import json
import re

import pytest

from tests.e2e.conftest import exec_in_container, require_docker


# Core install markers — the installer contract inherited from the
# Dockerfile.  These strings are emitted by the installer plugins
# (skills_plugin, agents_plugin, des_plugin, installation_verifier) and
# represent the four CORE components whose presence confirms a healthy
# install.  A drift in these markers is a contract change and MUST be
# caught by this test.
_CORE_MARKERS = (
    "Skills installed",
    "Agents installed",
    "DES module",
    "Settings updated",
)


@pytest.mark.e2e
@require_docker
class TestOpenCodeFullInstall:
    """OpenCode-aware installer deploys skills, agents, commands with contract.

    Migrated from Dockerfile.env-opencode (13 assertions).
    """

    # --- 1. Install succeeded (core markers) -----------------------------

    def test_install_produced_core_component_markers(self, opencode_container) -> None:
        """>=3 of 4 core install markers must appear in installer stdout.

        Mirrors Dockerfile heuristic: optional plugins (attribution) may
        fail; core components must still install.
        """
        stdout = getattr(opencode_container, "_install_stdout", "")
        found = sum(1 for m in _CORE_MARKERS if m in stdout)
        assert found >= 3, (
            f"Only {found}/{len(_CORE_MARKERS)} core markers found in install output.\n"
            f"Markers expected: {_CORE_MARKERS}\n"
            f"Install output tail:\n{stdout[-800:]}"
        )

    # --- 2. OpenCode skills ----------------------------------------------

    def test_opencode_skills_directory_populated(self, opencode_container) -> None:
        _code, out = exec_in_container(
            opencode_container,
            [
                "bash",
                "-c",
                "find /home/tester/.config/opencode/skills -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l",
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 50, (
            f"Only {count} skill dirs under ~/.config/opencode/skills/ (expected > 50)."
        )

    def test_every_opencode_skill_has_skill_md(self, opencode_container) -> None:
        _code, out = exec_in_container(
            opencode_container,
            [
                "bash",
                "-c",
                (
                    "skills=/home/tester/.config/opencode/skills; "
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
            f"{with_md}/{total} OpenCode skill dirs have SKILL.md."
        )

    def test_opencode_skills_manifest_present_and_versioned(
        self, opencode_container
    ) -> None:
        code, out = exec_in_container(
            opencode_container,
            [
                "cat",
                "/home/tester/.config/opencode/skills/.nwave-manifest.json",
            ],
        )
        assert code == 0, "OpenCode skills manifest missing."
        try:
            data = json.loads(out)
        except json.JSONDecodeError as exc:
            pytest.fail(f"Skills manifest is not valid JSON: {exc}\n{out[:300]}")
        assert "installed_skills" in data, "Manifest missing 'installed_skills' key."
        assert data.get("version") == "1.0", (
            f"Skills manifest version is {data.get('version')!r}, expected '1.0'."
        )

    def test_opencode_skills_strip_claude_only_frontmatter_fields(
        self, opencode_container
    ) -> None:
        """``user-invocable`` and ``disable-model-invocation`` are Claude-only."""
        forbidden = ("user-invocable", "disable-model-invocation")
        _code, out = exec_in_container(
            opencode_container,
            [
                "bash",
                "-c",
                (
                    "cd /home/tester/.config/opencode/skills && "
                    "found=''; for f in $(find . -name SKILL.md | head -20); do "
                    "  head -20 \"$f\" | grep -E '^(user-invocable|disable-model-invocation):' "
                    '  && found="$found $f"; done; '
                    'echo "RESULT=$found"'
                ),
            ],
        )
        assert "RESULT=" in out and out.split("RESULT=", 1)[1].strip() == "", (
            f"Claude-only frontmatter fields {forbidden} found in OpenCode skills.\n{out[-400:]}"
        )

    # --- 3. OpenCode agents ----------------------------------------------

    def test_opencode_agents_installed(self, opencode_container) -> None:
        _code, out = exec_in_container(
            opencode_container,
            [
                "bash",
                "-c",
                "find /home/tester/.config/opencode/agents -name 'nw-*.md' 2>/dev/null | wc -l",
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 10, f"Only {count} OpenCode agents installed (expected > 10)."

    def test_opencode_agents_manifest_present(self, opencode_container) -> None:
        code, out = exec_in_container(
            opencode_container,
            [
                "cat",
                "/home/tester/.config/opencode/agents/.nwave-agents-manifest.json",
            ],
        )
        assert code == 0, "OpenCode agents manifest missing."
        try:
            data = json.loads(out)
        except json.JSONDecodeError as exc:
            pytest.fail(f"Agents manifest invalid JSON: {exc}")
        assert "installed_agents" in data, "Agents manifest missing 'installed_agents'."

    def test_opencode_agents_use_mode_subagent(self, opencode_container) -> None:
        _code, out = exec_in_container(
            opencode_container,
            [
                "bash",
                "-c",
                (
                    "cd /home/tester/.config/opencode/agents && "
                    "count=0; for f in $(ls nw-*.md | head -10); do "
                    "  head -30 \"$f\" | grep -q '^mode: subagent' && count=$((count+1)); done; "
                    'echo "MODE_COUNT=$count"'
                ),
            ],
        )
        m = re.search(r"MODE_COUNT=(\d+)", out)
        assert m and int(m.group(1)) > 0, (
            f"No OpenCode agents declare 'mode: subagent'.\n{out[-300:]}"
        )

    def test_opencode_agents_no_tools_csv(self, opencode_container) -> None:
        _code, out = exec_in_container(
            opencode_container,
            [
                "bash",
                "-c",
                (
                    "cd /home/tester/.config/opencode/agents && "
                    "bad=$(grep -l '^tools: \"' nw-*.md 2>/dev/null | wc -l); "
                    'echo "BAD=$bad"'
                ),
            ],
        )
        m = re.search(r"BAD=(\d+)", out)
        assert m and int(m.group(1)) == 0, (
            f"Some OpenCode agents use tools: CSV format (should be permission block).\n{out[-300:]}"
        )

    def test_opencode_agents_strip_claude_only_fields(self, opencode_container) -> None:
        """name/model/skills are Claude-only agent frontmatter fields."""
        _code, out = exec_in_container(
            opencode_container,
            [
                "bash",
                "-c",
                (
                    "cd /home/tester/.config/opencode/agents && "
                    'bad=""; for f in $(ls nw-*.md | head -10); do '
                    "  head -20 \"$f\" | grep -qE '^(name|model|skills):' "
                    '    && bad="$bad $f"; done; '
                    'echo "BAD=$bad"'
                ),
            ],
        )
        assert out.strip().endswith("BAD="), (
            f"Claude-only fields (name/model/skills) found in OpenCode agents.\n{out[-400:]}"
        )

    def test_opencode_agent_bodies_rewrite_skill_paths(
        self, opencode_container
    ) -> None:
        """Agent markdown bodies must reference OpenCode paths, not Claude paths."""
        _code, out = exec_in_container(
            opencode_container,
            [
                "bash",
                "-c",
                (
                    "cd /home/tester/.config/opencode/agents && "
                    "bad=$(grep -l '~/\\.claude/skills/' nw-*.md 2>/dev/null | wc -l); "
                    'echo "BAD=$bad"'
                ),
            ],
        )
        m = re.search(r"BAD=(\d+)", out)
        assert m and int(m.group(1)) == 0, (
            f"{m.group(1) if m else '?'} OpenCode agent(s) still reference ~/.claude/skills/ — paths not rewritten."
        )

    # --- 4. OpenCode commands --------------------------------------------

    def test_opencode_commands_installed(self, opencode_container) -> None:
        _code, out = exec_in_container(
            opencode_container,
            [
                "bash",
                "-c",
                "find /home/tester/.config/opencode/commands -name '*.md' 2>/dev/null | wc -l",
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 0, "No commands installed at ~/.config/opencode/commands/."

    # --- 5. Claude Code skills parity install ----------------------------

    def test_claude_code_skills_also_installed(self, opencode_container) -> None:
        """Installing with OpenCode detected must NOT skip the Claude install.

        Both targets must receive the skill set so the user can switch CLIs
        without reinstalling.
        """
        _code, out = exec_in_container(
            opencode_container,
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
            "OpenCode install must preserve Claude install parity."
        )
