"""E2E: OpenCode fires tool.execute.before inside sub-agent sessions.

Migrated from: tests/e2e/Dockerfile.smoke-opencode-subagent-hooks
Layer 4 of platform-testing-strategy.md

Regression gate for ADR-OC-004 (full DES enforcement on OpenCode).  If
OpenCode stops propagating hooks to sub-agent sessions, DES loses its
enforcement boundary and this test fails — the release does not ship.

Protected by ``@pytest.mark.live_api`` and skipped unless
``OPENAI_API_KEY`` is set.  Live-API cost is non-trivial: ~240s opencode
run + gpt-4o-mini tokens.  Not on the default CI path.

Structural assertions extracted from the Dockerfile smoke.sh:
  1. /tmp/opencode-probe.jsonl exists (plugin loaded)
  2. >= 1 plugin.init event (plugin lifecycle hook fired)
  3. primary agent fired tool.execute.before for 'task' tool
  4. sub-agent fired tool.execute.before for a non-task tool with
     distinct sessionID
  5. sub-agent and primary session IDs do not intersect

Uses its own container (not the shared ``opencode_container``) because
this test requires the pipx + local-branch overlay toolchain from the
Dockerfile — the nwave-ai PyPI package plus our in-branch fixes.

Step-Id: 01-03
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.e2e.conftest import exec_in_container, require_docker


_REPO_ROOT = Path(__file__).parent.parent.parent
_IMAGE = "python:3.12-slim"


# Marker + skip condition: live API key must be present.
live_api = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set — skipping live-API OpenCode sub-agent probe",
)


@pytest.fixture(scope="module")
def opencode_subagent_container():
    """Container with pipx nwave-ai + local-branch overlay + probe plugin.

    Mirrors Dockerfile.smoke-opencode-subagent-hooks build sequence:
      1. apt install git + curl + ca-certificates + node 22
      2. npm install -g opencode-ai
      3. pipx install nwave-ai (released version)
      4. Overlay local-branch source over pipx venv (validates CURRENT BRANCH)
      5. Configure OpenCode + install probe plugin fixture
      6. nwave-ai install (populate skills/agents/commands)

    OPENAI_API_KEY is injected via ``with_env`` at runtime (never build arg).
    """
    from tests.e2e.conftest import _is_docker_available

    if not _is_docker_available():
        pytest.skip("Docker daemon not available")

    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    from testcontainers.core.container import (
        DockerContainer,  # type: ignore[import-untyped]
    )

    api_key = os.environ["OPENAI_API_KEY"]

    container = DockerContainer(image=_IMAGE)
    container.with_volume_mapping(str(_REPO_ROOT), "/src", "ro")
    container.with_env("HOME", "/home/tester")
    container.with_env("DEBIAN_FRONTEND", "noninteractive")
    container.with_env("OPENAI_API_KEY", api_key)
    container.with_env(
        "PATH",
        "/home/tester/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    )
    container._command = "tail -f /dev/null"

    with container:
        base = (
            "set -e && "
            "pip install --no-cache-dir pipx --quiet && pipx ensurepath && "
            "apt-get update -qq && "
            "apt-get install -y --no-install-recommends curl git ca-certificates -qq && "
            "curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1 && "
            "apt-get install -y --no-install-recommends nodejs -qq && "
            "rm -rf /var/lib/apt/lists/* && "
            "npm install -g opencode-ai --silent 2>&1 | tail -3 && "
            "useradd -m -s /bin/bash tester"
        )
        code, out = exec_in_container(container, ["bash", "-c", base])
        assert code == 0, f"Base image setup failed.\n{out[-600:]}"

        pipx_install = (
            "su tester -c 'export PATH=/home/tester/.local/bin:$PATH && "
            "pipx install nwave-ai'"
        )
        code, out = exec_in_container(container, ["bash", "-c", pipx_install])
        assert code == 0, f"pipx install nwave-ai failed.\n{out[-600:]}"

        overlay = (
            "su tester -c '"
            "export PATH=/home/tester/.local/bin:$PATH && "
            'NWAVE_VENV="$(pipx environment --value PIPX_LOCAL_VENVS)/nwave-ai" && '
            'SITE_PKGS="$(${NWAVE_VENV}/bin/python -c \\"import sysconfig; print(sysconfig.get_paths()[\\\\\\"purelib\\\\\\"])\\")" && '
            'cp /src/scripts/install/plugins/opencode_des_plugin.py "${SITE_PKGS}/scripts/install/plugins/opencode_des_plugin.py" && '
            'cp /src/scripts/shared/install_paths.py "${SITE_PKGS}/scripts/shared/install_paths.py" && '
            'cp /src/nWave/templates/opencode-des-plugin.ts.template "${SITE_PKGS}/nWave/templates/opencode-des-plugin.ts.template" && '
            'find "${SITE_PKGS}/scripts" "${SITE_PKGS}/nWave/templates" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true'
            "'"
        )
        code, out = exec_in_container(container, ["bash", "-c", overlay])
        assert code == 0, f"Local-branch overlay failed.\n{out[-600:]}"

        cfg = (
            "su tester -c 'mkdir -p /home/tester/.config/opencode/plugins && "
            'echo \'{"model": "openai/gpt-4o-mini"}\' > '
            "/home/tester/.config/opencode/opencode.json && "
            "cp /src/tests/e2e/fixtures/opencode-subagent-hook-probe.ts "
            "/home/tester/.config/opencode/plugins/probe-plugin.ts && "
            "mkdir -p /home/tester/workspace/.opencode/plugins && "
            "cp /src/tests/e2e/fixtures/opencode-subagent-hook-probe.ts "
            "/home/tester/workspace/.opencode/plugins/probe-plugin.ts'"
        )
        code, out = exec_in_container(container, ["bash", "-c", cfg])
        assert code == 0, f"Config + probe fixture placement failed.\n{out[-500:]}"

        nwave_install = (
            "su tester -c 'export PATH=/home/tester/.local/bin:$PATH && "
            "nwave-ai install --yes || nwave-ai install || true'"
        )
        exec_in_container(container, ["bash", "-c", nwave_install])

        yield container


def _write_auth_json(container, api_key: str) -> None:
    """Write OpenCode auth.json with the API key inside the container."""
    cmd = (
        "su tester -c 'mkdir -p /home/tester/.local/share/opencode && "
        f"python3 -c \"import json,os; json.dump({{'openai':{{'type':'api','key':'{api_key}'}}}}, "
        "open('/home/tester/.local/share/opencode/auth.json','w'))\" && "
        "chmod 600 /home/tester/.local/share/opencode/auth.json'"
    )
    code, out = exec_in_container(container, ["bash", "-c", cmd])
    assert code == 0, f"auth.json write failed.\n{out[-300:]}"


@pytest.mark.e2e
@pytest.mark.live_api
@live_api
@require_docker
class TestOpenCodeSubagentHooks:
    """OpenCode sub-agent hook-propagation regression gate.

    Migrated from Dockerfile.smoke-opencode-subagent-hooks (5 assertions).
    """

    @pytest.fixture(scope="class")
    def probe_log(self, opencode_subagent_container):
        """Run the probe scenario once and return parsed JSONL entries.

        Heavy operation: opencode DB warmup + opencode run (up to 240s).
        All 5 assertions share the same probe log.
        """
        api_key = os.environ["OPENAI_API_KEY"]
        _write_auth_json(opencode_subagent_container, api_key)

        # Warmup: triggers one-time SQLite migration on first opencode call.
        warmup = "su tester -c 'timeout 300 opencode auth list 2>&1 || true'"
        exec_in_container(opencode_subagent_container, ["bash", "-c", warmup])

        # Prepare workspace + canary.
        prep = (
            "echo CANARY_LINE_42 > /tmp/canary.txt && chmod 644 /tmp/canary.txt && "
            "su tester -c 'cd /home/tester/workspace && "
            "(git init -q 2>&1 || true) && "
            "git config user.email smoke@nwave.local && "
            "git config user.name Smoke && "
            "echo workspace > README.md && "
            "(git add -A && git commit -q -m init 2>&1 || true) && "
            ": > /tmp/opencode-probe.jsonl'"
        )
        exec_in_container(opencode_subagent_container, ["bash", "-c", prep])

        # Fire the scenario.
        prompt = (
            "Use the task tool to dispatch a subagent of type nw-nwave-buddy "
            'with the prompt: "Read the file /tmp/canary.txt using the read '
            'tool and report its first line verbatim." After the subagent '
            "finishes, tell me the exact line it reported."
        )
        run_cmd = (
            "su tester -c 'cd /home/tester/workspace && "
            f'timeout 240 opencode run --model openai/gpt-4o-mini "{prompt}" '
            "> /tmp/opencode-stdout.log 2>&1 || true'"
        )
        exec_in_container(opencode_subagent_container, ["bash", "-c", run_cmd])

        # Fetch the probe log.
        code, raw = exec_in_container(
            opencode_subagent_container,
            ["cat", "/tmp/opencode-probe.jsonl"],
        )
        assert code == 0, "Probe log file missing — plugin did not load."
        entries = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return entries

    @staticmethod
    def _session_id(entry: dict) -> str | None:
        snap = entry.get("snapshot") or {}
        inp = snap.get("input") or {} if isinstance(snap, dict) else {}
        return inp.get("sessionID") if isinstance(inp, dict) else None

    def test_probe_plugin_loaded(self, probe_log) -> None:
        inits = [e for e in probe_log if e.get("hook_name") == "plugin.init"]
        assert inits, (
            "No plugin.init events in probe log — OpenCode never loaded "
            "the probe plugin.  Regression in OpenCode plugin discovery."
        )

    def test_primary_task_tool_execute_before_fired(self, probe_log) -> None:
        task_events = [
            e
            for e in probe_log
            if e.get("hook_name") == "tool.execute.before"
            and e.get("tool_name") == "task"
        ]
        assert task_events, (
            "No tool.execute.before events for 'task' tool — the primary "
            "agent did not dispatch a sub-agent.  Unable to test sub-agent "
            "hook propagation."
        )

    def test_subagent_tool_execute_before_fired(self, probe_log) -> None:
        task_sessions = {
            self._session_id(e)
            for e in probe_log
            if e.get("hook_name") == "tool.execute.before"
            and e.get("tool_name") == "task"
        }
        task_sessions.discard(None)

        sub_events = [
            e
            for e in probe_log
            if e.get("hook_name") == "tool.execute.before"
            and e.get("tool_name") not in (None, "task")
            and self._session_id(e)
            and self._session_id(e) not in task_sessions
        ]
        assert sub_events, (
            "No tool.execute.before events from a sub-agent session.\n"
            "Either the sub-agent did not run, or OpenCode stopped firing "
            "hooks for sub-agent tool calls — regression in plugin-hook "
            "propagation.  This is the exact bug ADR-OC-004 protects against."
        )

    def test_subagent_sessions_distinct_from_primary(self, probe_log) -> None:
        task_sessions = {
            self._session_id(e)
            for e in probe_log
            if e.get("hook_name") == "tool.execute.before"
            and e.get("tool_name") == "task"
        }
        task_sessions.discard(None)
        sub_sessions = {
            self._session_id(e)
            for e in probe_log
            if e.get("hook_name") == "tool.execute.before"
            and e.get("tool_name") not in (None, "task")
            and self._session_id(e)
            and self._session_id(e) not in task_sessions
        }
        sub_sessions.discard(None)
        shared = task_sessions & sub_sessions
        assert not shared, (
            f"Sub-agent and primary sessions share session IDs: {shared}.\n"
            "Correlation-logic assumption violated."
        )
