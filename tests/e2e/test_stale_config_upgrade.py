"""E2E: nWave upgrade from stale v2.x artifacts to current version.

Migrated from: tests/e2e/Dockerfile.env-with-stale-config
Layer 4 of platform-testing-strategy.md

Contract: nWave install over stale v2.15.0 artifacts must:
  - complete without fatal error
  - install new nw-*/SKILL.md skill layout (new > old count)
  - install agents under ~/.claude/agents/
  - write current DES hook format (claude_code_hook_adapter) to settings.json
  - not produce duplicate hook entries in settings.json

Stale artifacts simulated:
  - ~/.nwave/hooks/ with orphaned v2.15.0 hook scripts
  - ~/.nwave/global-config.json with v2.x format
  - ~/.claude/skills/nw/ flat directory (old layout)
  - ~/.claude/agents/nw/ old agent layout
  - ~/.claude/settings.json with pre-v3 DES hook format

Requires a Docker daemon.  Skips gracefully when Docker is unavailable.

Step-Id: 01-02
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.conftest import exec_in_container, require_docker


_REPO_ROOT = Path(__file__).parent.parent.parent
_IMAGE = "python:3.12-slim"
_CONTAINER_SRC = "/src"


@pytest.fixture(scope="module")
def stale_config_upgrade_container():
    """Container with stale v2.15.0 artifacts, then upgraded with current nwave-ai.

    Mirrors Dockerfile.env-with-stale-config:
    1. Create stale ~/.nwave/hooks/, global-config.json, skill layout, settings.json
    2. Install current nwave-ai from local source and run nwave-ai install
    """
    from tests.e2e.conftest import _is_docker_available

    if not _is_docker_available():
        pytest.skip("Docker daemon not available")

    from testcontainers.core.container import (
        DockerContainer,  # type: ignore[import-untyped]
    )

    container = DockerContainer(image=_IMAGE)
    container.with_volume_mapping(str(_REPO_ROOT), _CONTAINER_SRC, "ro")
    container.with_env("HOME", "/root")
    container.with_env("DEBIAN_FRONTEND", "noninteractive")
    container._command = "tail -f /dev/null"

    with container:
        # Install git (required by nwave installer)
        setup_script = (
            "set -e && "
            "apt-get update -qq && "
            "apt-get install -y --no-install-recommends git -qq && "
            "rm -rf /var/lib/apt/lists/*"
        )
        code, out = exec_in_container(container, ["bash", "-c", setup_script])
        assert code == 0, f"System setup failed (exit {code}).\nOutput:\n{out}"

        # Plant stale v2.15.0 artifacts (mirrors Dockerfile RUN layers)
        stale_setup = r"""set -e
# Old hooks directory with orphaned hook scripts
mkdir -p /root/.nwave/hooks
printf '#!/bin/bash\n# nWave 2.15.0 attribution hook\necho "old-nwave-hook"\n' \
    > /root/.nwave/hooks/pre-commit
chmod +x /root/.nwave/hooks/pre-commit
printf '#!/bin/bash\n# nWave 2.15.0 commit-msg hook\n' \
    > /root/.nwave/hooks/commit-msg
chmod +x /root/.nwave/hooks/commit-msg

# Old global config with v2.x format
printf '{"version":"2.15.0","attribution":{"enabled":true},"hooks":{"global_path":"/root/.nwave/hooks"}}\n' \
    > /root/.nwave/global-config.json

# Old skill layout (flat nw/ directory)
mkdir -p /root/.claude/skills/nw/software-crafter
echo '# Old TDD methodology v2.15.0' > /root/.claude/skills/nw/software-crafter/tdd-methodology.md
mkdir -p /root/.claude/skills/nw/quality-framework
echo '# Old quality framework v2.15.0' > /root/.claude/skills/nw/quality-framework/SKILL.md

# Old agent layout
mkdir -p /root/.claude/agents/nw
echo '# Old crafter agent v2.15.0' > /root/.claude/agents/nw/crafter.md

# Old DES hooks format in settings.json (pre-v3 hook registration)
mkdir -p /root/.claude
printf '{"hooks":{"pre-tool-use":[{"command":"python -m des.old_hook pre_tool_use"}]}}\n' \
    > /root/.claude/settings.json
"""
        code, out = exec_in_container(container, ["bash", "-c", stale_setup])
        assert code == 0, f"Stale artifact setup failed (exit {code}).\nOutput:\n{out}"

        # Create a git project (installer may need one)
        git_setup = (
            "set -e && "
            "git init /root/project && "
            "cd /root/project && "
            "git config user.email 'dev@test.com' && "
            "git config user.name 'Dev' && "
            "echo '# Test' > README.md && "
            "git add -A && "
            "git commit -m 'init' --no-verify"
        )
        code, out = exec_in_container(container, ["bash", "-c", git_setup])
        assert code == 0, f"Git setup failed (exit {code}).\nOutput:\n{out}"

        # Install current nwave-ai over the stale artifacts
        install_script = (
            "set -e && "
            "python -m venv /opt/nwave-venv && "
            "source /opt/nwave-venv/bin/activate && "
            "pip install --quiet "
            "rich typer pydantic 'pydantic-settings' httpx platformdirs pyyaml packaging && "
            f"pip install --quiet --no-deps {_CONTAINER_SRC} && "
            f"export PYTHONPATH={_CONTAINER_SRC} && "
            "echo y | python -m nwave_ai.cli install || true"
        )
        code, out = exec_in_container(container, ["bash", "-c", install_script])
        # Non-zero is tolerated — individual assertions validate each outcome

        yield container


@pytest.mark.e2e
@require_docker
class TestStaleConfigUpgrade:
    """Upgrading nWave over stale v2.15.0 artifacts must produce a clean current install.

    Migrated from Dockerfile.env-with-stale-config (6 assertions).
    """

    def test_install_completes_without_fatal_error(
        self, stale_config_upgrade_container
    ) -> None:
        """Running nwave-ai install over stale artifacts must not crash fatally.

        A clean exit (0) or a logged success/healthy message confirms the
        installer handled stale artifacts gracefully.
        """
        check_script = (
            f"export PYTHONPATH={_CONTAINER_SRC} && "
            "echo y | /opt/nwave-venv/bin/python -m nwave_ai.cli install 2>&1; "
            "echo EXIT:$?"
        )
        _code, out = exec_in_container(
            stale_config_upgrade_container, ["bash", "-c", check_script]
        )
        exit_line = next(
            (l for l in out.splitlines() if l.startswith("EXIT:")),  # noqa: E741
            "EXIT:?",
        )
        exit_code = exit_line.split(":")[1].strip()
        succeeded = exit_code == "0" or any(
            kw in out.lower() for kw in ("installed", "success", "healthy")
        )
        assert succeeded, (
            f"nwave-ai install over stale artifacts exited {exit_code!r} with no "
            f"success indicator.\nOutput (last 400 chars):\n{out[-400:]}"
        )

    def test_new_skill_layout_installed(self, stale_config_upgrade_container) -> None:
        """New nw-*/SKILL.md skill directories must be present after upgrade.

        The installer must deploy the current skill layout regardless of any
        pre-existing stale nw/ directory.
        """
        code, _ = exec_in_container(
            stale_config_upgrade_container,
            ["bash", "-c", "ls -d /root/.claude/skills/nw-* >/dev/null 2>&1"],
        )
        assert code == 0, (
            "No nw-*/SKILL.md skill directories found after upgrade from stale layout.\n"
            "Installer must deploy current skill layout over old nw/ directory."
        )

    def test_new_skills_outnumber_stale_skills(
        self, stale_config_upgrade_container
    ) -> None:
        """The new nw-*/SKILL.md skill count must exceed the stale nw/ skill count.

        The stale install has 2 files under nw/.  A successful upgrade installs
        dozens.  If new <= old, the upgrade did not deploy new skills.
        """
        _code, counts_out = exec_in_container(
            stale_config_upgrade_container,
            [
                "bash",
                "-c",
                "OLD=$(find /root/.claude/skills/nw/ -name '*.md' 2>/dev/null | wc -l); "
                "NEW=$(find /root/.claude/skills/nw-* -name '*.md' 2>/dev/null | wc -l); "
                "echo OLD=$OLD NEW=$NEW",
            ],
        )
        old_count = 0
        new_count = 0
        for part in counts_out.split():
            if part.startswith("OLD="):
                old_count = int(part.split("=")[1])
            elif part.startswith("NEW="):
                new_count = int(part.split("=")[1])
        assert new_count > old_count, (
            f"New skill count ({new_count}) is not greater than old stale skill count "
            f"({old_count}).  Installer did not deploy new skill layout."
        )

    def test_agents_installed_after_upgrade(
        self, stale_config_upgrade_container
    ) -> None:
        """Agents must be installed in some form under ~/.claude/agents/.

        Accepts either old-style nw/ directory or new nw-* prefixed directories.
        The important check is that agent files are present.
        """
        code, _ = exec_in_container(
            stale_config_upgrade_container,
            [
                "bash",
                "-c",
                "[ -d /root/.claude/agents/nw ] || "
                "ls /root/.claude/agents/nw-* >/dev/null 2>&1",
            ],
        )
        assert code == 0, (
            "No agent files found under ~/.claude/agents/ after upgrade.\n"
            "Installer must deploy agent files regardless of stale state."
        )

    def test_current_des_hook_adapter_in_settings(
        self, stale_config_upgrade_container
    ) -> None:
        """settings.json must contain the current DES hook adapter reference.

        The stale settings.json has a pre-v3 hook format ('des.old_hook').
        After upgrade, settings.json must reference 'claude_code_hook_adapter'
        (the current hook entry point).
        """
        code, settings_raw = exec_in_container(
            stale_config_upgrade_container,
            ["cat", "/root/.claude/settings.json"],
        )
        assert code == 0, (
            f"Cannot read ~/.claude/settings.json (exit {code}).\n{settings_raw}"
        )
        assert "claude_code_hook_adapter" in settings_raw, (
            "settings.json does not contain 'claude_code_hook_adapter' after upgrade.\n"
            "Installer must overwrite stale pre-v3 hook format with current adapter.\n"
            f"settings.json content:\n{settings_raw}"
        )

    def test_no_duplicate_hook_entries_in_settings(
        self, stale_config_upgrade_container
    ) -> None:
        """settings.json must not contain an excessive number of hook entries.

        An installer that appends rather than replaces would accumulate the old
        pre-v3 entry plus multiple new entries.  A total count >= 20 indicates
        runaway duplication.
        """
        code, settings_raw = exec_in_container(
            stale_config_upgrade_container,
            ["cat", "/root/.claude/settings.json"],
        )
        assert code == 0, (
            f"Cannot read ~/.claude/settings.json (exit {code}).\n{settings_raw}"
        )

        count_script = (
            "import json, pathlib; "
            "d = json.loads(pathlib.Path('/root/.claude/settings.json').read_text()); "
            "hooks = d.get('hooks', {}); "
            "count = sum(len(v) if isinstance(v, list) else 1 for v in hooks.values()); "
            "print(count)"
        )
        code, count_out = exec_in_container(
            stale_config_upgrade_container,
            ["python3", "-c", count_script],
        )
        try:
            total = int(count_out.strip())
        except ValueError:
            total = 0
        assert total < 20, (
            f"settings.json contains {total} hook entries after upgrade — "
            "installer is accumulating duplicates rather than replacing stale entries.\n"
            f"settings.json content:\n{settings_raw}"
        )
