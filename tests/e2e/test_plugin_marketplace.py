"""E2E: Plugin marketplace install simulation.

Migrated from: tests/e2e/Dockerfile.env-plugin-marketplace
Layer 4 of platform-testing-strategy.md

Validates the plugin structure built by ``scripts/build_plugin.py`` matches
what Claude Code expects from a marketplace plugin: ``hooks.json`` with all
event types, agents, skills, and functional DES hooks.  Exercises the
"plugin install" path where pip/pipx are NOT used and ``$HOME`` may be empty
(known Claude Code bug #24529).

15 assertions grouped by concern:
  1. hooks.json structure (6): exists, envelope, 5 event types, 4 matchers,
     nested format, adapter references
  2. Agent files (3): directory exists, > 10 agents, nw-software-crafter.md
  3. Skill files (3): directory exists, > 30 skills, all have SKILL.md
  4. DES module (3): dir exists, __init__.py, hook adapter file
  5. Hook functionality (3): works with CLAUDE_PLUGIN_ROOT, fallback discovery,
     works without $HOME (plugin env bug simulation)

Requires a Docker daemon.  Skips gracefully when Docker is unavailable.

Step-Id: 01-03
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.conftest import exec_in_container, require_docker


_REPO_ROOT = Path(__file__).parent.parent.parent
_IMAGE = "python:3.12-slim"
_PLUGIN_ROOT = "/root/.claude/plugins/cache/nwave-marketplace/nw/latest"


# ---------------------------------------------------------------------------
# Hook discovery script — materialized in the container at fixture setup
# so we can invoke it as ``python3 /tmp/des_discover.py <action>`` and avoid
# triple-layer shell-quoting of the Python code.  Logic matches the
# Dockerfile DISCOVERY snippet verbatim.
# ---------------------------------------------------------------------------

_DISCOVERY_SCRIPT = """\
import os
import sys
from pathlib import Path

action = sys.argv[1]
root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
candidate = root + "/scripts" if root else ""
if not candidate:
    found = next(
        (
            str(s)
            for s in sorted(
                Path.home().joinpath(".claude/plugins/cache").glob("*/nw/*/scripts")
            )
            if (s / "des" / "__init__.py").exists()
        ),
        None,
    )
    candidate = found or str(Path.home() / ".claude/lib/python")

sys.path.insert(0, candidate)
sys.argv = ["des-hook", action]
from des.adapters.drivers.hooks.claude_code_hook_adapter import main

main()
"""


@pytest.fixture(scope="module")
def plugin_marketplace_container():
    """Build plugin via build_plugin.py, copy to Claude-Code cache layout."""
    from tests.e2e.conftest import _is_docker_available

    if not _is_docker_available():
        pytest.skip("Docker daemon not available")

    from testcontainers.core.container import (
        DockerContainer,  # type: ignore[import-untyped]
    )

    container = DockerContainer(image=_IMAGE)
    container.with_volume_mapping(str(_REPO_ROOT), "/src", "ro")
    container.with_env("HOME", "/root")
    container.with_env("DEBIAN_FRONTEND", "noninteractive")
    container._command = "tail -f /dev/null"

    with container:
        setup = (
            "set -e && "
            "pip install --quiet pyyaml && "
            "mkdir -p /build && "
            "cp -r /src/scripts/build_plugin.py /build/ && "
            "cp -r /src/scripts/shared /build/shared && "
            "cp -r /src/src /build/src && "
            "cp -r /src/nWave /build/nWave && "
            "cp /src/pyproject.toml /build/pyproject.toml && "
            "mkdir -p /build/scripts && "
            "mv /build/build_plugin.py /build/scripts/build_plugin.py && "
            "mv /build/shared /build/scripts/shared && "
            "cd /build && "
            "python scripts/build_plugin.py --output-dir /tmp/plugin 2>&1 | tail -20"
        )
        code, out = exec_in_container(container, ["bash", "-c", setup])
        assert code == 0, f"Plugin build failed (exit {code}).\nOutput:\n{out[-800:]}"

        install = (
            f"set -e && mkdir -p {_PLUGIN_ROOT} && cp -r /tmp/plugin/. {_PLUGIN_ROOT}/"
        )
        code, out = exec_in_container(container, ["bash", "-c", install])
        assert code == 0, f"Plugin cache install failed (exit {code}).\n{out[-300:]}"

        # Materialize the DES-discovery script inside the container once.
        # Subsequent hook tests invoke `python3 /tmp/des_discover.py <action>`
        # which avoids shell-quoting hell across bash -> bash -> python3 -c.
        write_discover = (
            "cat > /tmp/des_discover.py << 'DISCOVER_EOF'\n"
            + _DISCOVERY_SCRIPT
            + "DISCOVER_EOF"
        )
        code, out = exec_in_container(container, ["bash", "-c", write_discover])
        assert code == 0, f"Discovery script write failed.\n{out[-300:]}"

        yield container


@pytest.mark.e2e
@require_docker
class TestPluginMarketplace:
    """Plugin marketplace install structure and DES-hook functionality.

    Migrated from Dockerfile.env-plugin-marketplace (15 assertions).
    """

    # --- 1. hooks.json structure -----------------------------------------

    def test_hooks_json_exists(self, plugin_marketplace_container) -> None:
        code, _ = exec_in_container(
            plugin_marketplace_container,
            ["test", "-f", f"{_PLUGIN_ROOT}/hooks/hooks.json"],
        )
        assert code == 0, "hooks.json missing from built plugin."

    def test_hooks_json_has_hooks_envelope(self, plugin_marketplace_container) -> None:
        _code, out = exec_in_container(
            plugin_marketplace_container,
            [
                "python3",
                "-c",
                (
                    "import json,pathlib;"
                    f"d=json.loads(pathlib.Path('{_PLUGIN_ROOT}/hooks/hooks.json').read_text());"
                    "print('YES' if 'hooks' in d else 'NO')"
                ),
            ],
        )
        assert "YES" in out, f"hooks.json missing 'hooks' envelope key.\n{out}"

    def test_hooks_json_has_all_5_event_types(
        self, plugin_marketplace_container
    ) -> None:
        expected = {
            "PreToolUse",
            "PostToolUse",
            "SubagentStop",
            "SessionStart",
            "SubagentStart",
        }
        _code, out = exec_in_container(
            plugin_marketplace_container,
            [
                "python3",
                "-c",
                (
                    "import json,pathlib;"
                    f"d=json.loads(pathlib.Path('{_PLUGIN_ROOT}/hooks/hooks.json').read_text());"
                    "print(','.join(sorted(d.get('hooks',{}).keys())))"
                ),
            ],
        )
        actual = set(out.strip().split(","))
        assert expected.issubset(actual), (
            f"Missing event types: {expected - actual}.  Got: {sorted(actual)}"
        )

    def test_pre_tool_use_has_agent_write_edit_bash_matchers(
        self, plugin_marketplace_container
    ) -> None:
        expected_matchers = {"Agent", "Write", "Edit", "Bash"}
        _code, out = exec_in_container(
            plugin_marketplace_container,
            [
                "python3",
                "-c",
                (
                    "import json,pathlib;"
                    f"d=json.loads(pathlib.Path('{_PLUGIN_ROOT}/hooks/hooks.json').read_text());"
                    "ms={e.get('matcher') for e in d.get('hooks',{}).get('PreToolUse',[])};"
                    "print(','.join(sorted(m for m in ms if m)))"
                ),
            ],
        )
        actual = set(out.strip().split(","))
        assert expected_matchers.issubset(actual), (
            f"PreToolUse missing matchers {expected_matchers - actual}. Got: {sorted(actual)}"
        )

    def test_all_hook_entries_use_nested_format(
        self, plugin_marketplace_container
    ) -> None:
        _code, out = exec_in_container(
            plugin_marketplace_container,
            [
                "python3",
                "-c",
                (
                    "import json,pathlib;"
                    f"d=json.loads(pathlib.Path('{_PLUGIN_ROOT}/hooks/hooks.json').read_text());"
                    "ok=all('hooks' in e for evs in d.get('hooks',{}).values() for e in evs);"
                    "print('YES' if ok else 'NO')"
                ),
            ],
        )
        assert "YES" in out, "Some hook entries missing nested 'hooks' key."

    def test_hook_commands_reference_adapter_or_shell_guard(
        self, plugin_marketplace_container
    ) -> None:
        _code, out = exec_in_container(
            plugin_marketplace_container,
            [
                "python3",
                "-c",
                (
                    "import json,pathlib;"
                    f"d=json.loads(pathlib.Path('{_PLUGIN_ROOT}/hooks/hooks.json').read_text());"
                    "refs=sum(1 for evs in d.get('hooks',{}).values() "
                    "for e in evs for h in e.get('hooks',[]) "
                    "if 'claude_code_hook_adapter' in h.get('command',''));"
                    "print(refs)"
                ),
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 0, (
            "No hook commands reference claude_code_hook_adapter — "
            "plugin hooks cannot invoke DES runtime."
        )

    # --- 2. Agent files --------------------------------------------------

    def test_agents_directory_exists(self, plugin_marketplace_container) -> None:
        code, _ = exec_in_container(
            plugin_marketplace_container, ["test", "-d", f"{_PLUGIN_ROOT}/agents"]
        )
        assert code == 0, "Plugin agents/ directory missing."

    def test_more_than_10_agent_files_present(
        self, plugin_marketplace_container
    ) -> None:
        _code, out = exec_in_container(
            plugin_marketplace_container,
            [
                "bash",
                "-c",
                f"find {_PLUGIN_ROOT}/agents -maxdepth 1 -name 'nw-*.md' | wc -l",
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 10, f"Only {count} agent files found (expected > 10)."

    def test_software_crafter_agent_present(self, plugin_marketplace_container) -> None:
        code, _ = exec_in_container(
            plugin_marketplace_container,
            ["test", "-f", f"{_PLUGIN_ROOT}/agents/nw-software-crafter.md"],
        )
        assert code == 0, "nw-software-crafter.md missing from plugin agents/."

    # --- 3. Skills -------------------------------------------------------

    def test_skills_directory_exists(self, plugin_marketplace_container) -> None:
        code, _ = exec_in_container(
            plugin_marketplace_container, ["test", "-d", f"{_PLUGIN_ROOT}/skills"]
        )
        assert code == 0, "Plugin skills/ directory missing."

    def test_more_than_30_skill_dirs_present(
        self, plugin_marketplace_container
    ) -> None:
        _code, out = exec_in_container(
            plugin_marketplace_container,
            [
                "bash",
                "-c",
                f"find {_PLUGIN_ROOT}/skills -maxdepth 1 -mindepth 1 -type d | wc -l",
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 30, f"Only {count} skill dirs found (expected > 30)."

    def test_every_skill_dir_has_skill_md(self, plugin_marketplace_container) -> None:
        _code, out = exec_in_container(
            plugin_marketplace_container,
            [
                "bash",
                "-c",
                (
                    f"total=$(find {_PLUGIN_ROOT}/skills -maxdepth 1 -mindepth 1 -type d | wc -l); "
                    f"with=$(find {_PLUGIN_ROOT}/skills -maxdepth 2 -name SKILL.md | wc -l); "
                    'echo "$with/$total"'
                ),
            ],
        )
        try:
            with_md, total = (int(x) for x in out.strip().split("/"))
        except ValueError:
            pytest.fail(f"Could not parse count output: {out!r}")
        assert with_md == total, f"Only {with_md}/{total} skill dirs contain SKILL.md."

    # --- 4. DES module ---------------------------------------------------

    def test_des_module_present(self, plugin_marketplace_container) -> None:
        code, _ = exec_in_container(
            plugin_marketplace_container,
            ["test", "-f", f"{_PLUGIN_ROOT}/scripts/des/__init__.py"],
        )
        assert code == 0, "DES __init__.py not shipped in plugin."

        code, _ = exec_in_container(
            plugin_marketplace_container,
            [
                "test",
                "-f",
                f"{_PLUGIN_ROOT}/scripts/des/adapters/drivers/hooks/claude_code_hook_adapter.py",
            ],
        )
        assert code == 0, "DES hook adapter not shipped in plugin."

    # --- 5. Hook functionality (DES runtime in plugin context) -----------

    def test_des_hook_works_with_claude_plugin_root(
        self, plugin_marketplace_container
    ) -> None:
        """Happy path: CLAUDE_PLUGIN_ROOT set → hooks resolve DES runtime."""
        code, out = exec_in_container(
            plugin_marketplace_container,
            [
                "bash",
                "-c",
                (
                    f"export CLAUDE_PLUGIN_ROOT={_PLUGIN_ROOT} && "
                    'echo \'{"tool_input":{"prompt":"test"}}\' | '
                    "python3 /tmp/des_discover.py pre-task"
                ),
            ],
        )
        assert code == 0, (
            f"DES hook failed with CLAUDE_PLUGIN_ROOT (exit {code}).\n{out[-400:]}"
        )

    def test_des_hook_fallback_discovery_without_claude_plugin_root(
        self, plugin_marketplace_container
    ) -> None:
        """Fallback: no CLAUDE_PLUGIN_ROOT → glob ``~/.claude/plugins/cache``."""
        code, out = exec_in_container(
            plugin_marketplace_container,
            [
                "bash",
                "-c",
                (
                    "unset CLAUDE_PLUGIN_ROOT && "
                    'echo \'{"tool_input":{"prompt":"test"}}\' | '
                    "python3 /tmp/des_discover.py pre-task"
                ),
            ],
        )
        assert code == 0, (
            f"DES hook fallback discovery failed (exit {code}).\n{out[-400:]}"
        )

    def test_des_hook_works_without_home_env(
        self, plugin_marketplace_container
    ) -> None:
        """$HOME empty (known plugin env bug) → still works if CLAUDE_PLUGIN_ROOT set.

        Claude Code plugin hooks may run with empty ``$HOME`` (#24529).  As long
        as ``CLAUDE_PLUGIN_ROOT`` is provided, DES must resolve.
        """
        # Use docker-py exec_run with explicit env (bypasses shell HOME inheritance).
        raw = plugin_marketplace_container.get_wrapped_container().exec_run(
            cmd=[
                "bash",
                "-c",
                'echo "{}" | python3 /tmp/des_discover.py session-start',
            ],
            environment={"CLAUDE_PLUGIN_ROOT": _PLUGIN_ROOT, "HOME": ""},
        )
        out = raw.output.decode("utf-8", errors="replace") if raw.output else ""
        assert raw.exit_code == 0, (
            f"DES hook failed without $HOME (exit {raw.exit_code}).\n"
            f"This is the invocation-context fidelity check for #24529.\n{out[-400:]}"
        )
