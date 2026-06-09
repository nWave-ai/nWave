"""E2E: Cross-platform contract validation (5 anomalies + CI gate).

Migrated from: tests/e2e/Dockerfile.verify-contract-validation
Layer 4 of platform-testing-strategy.md

Validates the platform-contracts SSOT module, its validator functions,
the CI-enforcement script, and that installer plugins/templates consume
the SSOT correctly (D3 fix: no hardcoded field lists in plugins).

7 test groups covering ~21 contract-surface assertions:

  1. Platform-contracts SSOT module exposes required constants
     (path rewrites + exceptions, forbidden fields including D3's argument-hint)
  2. ``validate_des_template`` catches ANOMALY-3 (wrong import) and
     ANOMALY-4 (is_subagent); passes compliant template unchanged
  3. CI validator script (``scripts/validation/validate_platform_contracts.py``)
     exits 0 on a clean repo
  4. opencode_commands_plugin imports from SSOT, has _rewrite_paths, has no
     hardcoded _FIELDS_TO_REMOVE (D3 fix verified)
  5. opencode_skills_plugin imports forbidden-fields list from SSOT
  6. DES .ts template uses @opencode-ai/plugin import, no is_subagent,
     two-parameter handler signature
  7. opencode_agents_plugin uses "permission" key with "allow" string format

Requires a Docker daemon.  Skips gracefully when Docker is unavailable.

Step-Id: 01-03
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.conftest import exec_in_container, require_docker


pytestmark = pytest.mark.e2e_smoke

_REPO_ROOT = Path(__file__).parent.parent.parent
_IMAGE = "python:3.12-slim"
_CONTAINER_SRC = "/home/tester/nwave-dev"


@pytest.fixture(scope="module")
def contract_validation_container():
    """Container with repo copied under /home/tester/nwave-dev (writable)."""
    from tests.e2e.conftest import _is_docker_available

    if not _is_docker_available():
        pytest.skip("Docker daemon not available")

    from testcontainers.core.container import (
        DockerContainer,  # type: ignore[import-untyped]
    )

    container = DockerContainer(image=_IMAGE)
    container.with_volume_mapping(str(_REPO_ROOT), "/src", "ro")
    container.with_env("HOME", "/home/tester")
    container.with_env("DEBIAN_FRONTEND", "noninteractive")
    container._command = "tail -f /dev/null"

    with container:
        setup = (
            "set -e && "
            "apt-get update -qq && "
            "apt-get install -y --no-install-recommends git -qq && "
            "rm -rf /var/lib/apt/lists/* && "
            "useradd -m tester && "
            "cp -r /src /home/tester/nwave-dev && "
            "chown -R tester:tester /home/tester/nwave-dev"
        )
        code, out = exec_in_container(container, ["bash", "-c", setup])
        assert code == 0, f"Container setup failed.\n{out[-500:]}"
        yield container


def _py(container, code: str) -> tuple[int, str]:
    """Run a Python snippet inside /home/tester/nwave-dev.

    Writes the snippet to a unique per-call path and invokes python3
    directly — avoids nested shell-within-shell-within-python quote escaping.
    Runs as root (the container default user); imports from the repo work
    because we ``cd`` into it and prepend ``.`` to ``sys.path``.
    """
    import hashlib

    script_id = hashlib.md5(code.encode()).hexdigest()[:8]
    script_path = f"/tmp/run_{script_id}.py"

    prelude = "import sys\nsys.path.insert(0, '.')\n"
    full = prelude + code + "\n"
    write_cmd = (
        f"cat > {script_path} << 'RUN_PY_EOF'\n"
        + full
        + "RUN_PY_EOF\n"
        + f"chmod 644 {script_path} && "
        + f"cd /home/tester/nwave-dev && python3 {script_path} 2>&1"
    )
    return exec_in_container(container, ["bash", "-c", write_cmd])


@pytest.mark.e2e
@require_docker
class TestCrossPlatformContractValidation:
    """Cross-platform contract validation — 5 anomalies + CI gate + D3 fix.

    Migrated from Dockerfile.verify-contract-validation (7 test groups).
    """

    # --- T1: SSOT module surface -----------------------------------------

    def test_ssot_module_has_path_rewrites(self, contract_validation_container) -> None:
        code, out = _py(
            contract_validation_container,
            "from scripts.shared.platform_contracts import OPENCODE_PATH_REWRITES; "
            "print(len(OPENCODE_PATH_REWRITES))",
        )
        assert code == 0, f"Import failed.\n{out[-300:]}"
        try:
            count = int(out.strip().splitlines()[-1])
        except ValueError:
            pytest.fail(f"Could not parse count: {out!r}")
        assert count >= 4, (
            f"OPENCODE_PATH_REWRITES has {count} entries (expected >= 4)."
        )

    def test_ssot_module_has_required_path_rewrites(
        self, contract_validation_container
    ) -> None:
        """Skills, agents, nWave-framework rewrites all present."""
        code, out = _py(
            contract_validation_container,
            "from scripts.shared.platform_contracts import OPENCODE_PATH_REWRITES; "
            "keys=[s for s,_ in OPENCODE_PATH_REWRITES]; "
            'print("SKILLS_OK" if any(s == "~/.claude/skills/" for s in keys) else "SKILLS_MISS"); '
            'print("AGENTS_OK" if any(s == "~/.claude/agents/" for s in keys) else "AGENTS_MISS"); '
            'print("NWAVE_OK" if any("nWave" in s for s in keys) else "NWAVE_MISS")',
        )
        assert code == 0, f"Inspection failed.\n{out[-300:]}"
        assert "SKILLS_OK" in out, "skills path rewrite entry missing."
        assert "AGENTS_OK" in out, "agents path rewrite entry missing."
        assert "NWAVE_OK" in out, "nWave framework rewrite entry missing."

    def test_ssot_module_has_des_lib_exception(
        self, contract_validation_container
    ) -> None:
        _code, out = _py(
            contract_validation_container,
            "from scripts.shared.platform_contracts import OPENCODE_PATH_REWRITE_EXCEPTIONS; "
            'print("OK" if "~/.claude/lib/python" in OPENCODE_PATH_REWRITE_EXCEPTIONS else "MISS")',
        )
        assert "OK" in out, "DES lib path missing from rewrite exceptions."

    def test_ssot_module_has_forbidden_fields_lists(
        self, contract_validation_container
    ) -> None:
        """Skill-forbidden + command-forbidden (including D3's argument-hint)."""
        _code, out = _py(
            contract_validation_container,
            "from scripts.shared.platform_contracts import ("
            "  OPENCODE_SKILL_FORBIDDEN_FIELDS, OPENCODE_COMMAND_FORBIDDEN_FIELDS); "
            'print("SKILL_OK" if "user-invocable" in OPENCODE_SKILL_FORBIDDEN_FIELDS else "SKILL_MISS"); '
            'print("CMD_OK" if "argument-hint" in OPENCODE_COMMAND_FORBIDDEN_FIELDS else "CMD_MISS")',
        )
        assert "SKILL_OK" in out, "'user-invocable' not in skill-forbidden fields."
        assert "CMD_OK" in out, (
            "'argument-hint' not in command-forbidden fields — D3 fix regressed."
        )

    # --- T2: Validator function behaviour --------------------------------

    def test_validate_des_template_catches_anomalies(
        self, contract_validation_container
    ) -> None:
        # Heredoc delimiter 'RUN_PY_EOF' is single-quoted in _py, so NO shell
        # expansion happens.  Triple-quoted Python string is safe.
        snippet = '''\
from scripts.validation.validate_platform_contracts import validate_des_template

bad = """import { PluginContext } from "opencode";
const is_subagent = true;
"""
findings = validate_des_template(bad)
msgs = " ".join(f.message.lower() for f in findings)
print("IMPORT_CAUGHT" if ("import" in msgs or "opencode" in msgs) else "IMPORT_MISS")
print("SUBAGENT_CAUGHT" if "subagent" in msgs else "SUBAGENT_MISS")
'''
        code, out = _py(contract_validation_container, snippet)
        assert code == 0, f"Validator invocation failed.\n{out[-400:]}"
        assert "IMPORT_CAUGHT" in out, (
            "ANOMALY-3 not caught: wrong import should be flagged."
        )
        assert "SUBAGENT_CAUGHT" in out, (
            "ANOMALY-4 not caught: is_subagent should be flagged."
        )

    def test_validate_des_template_passes_compliant_template(
        self, contract_validation_container
    ) -> None:
        # Run from a file to avoid quoting hell.
        create = (
            "cat > /tmp/good.ts << 'EOF'\nimport type { Plugin } from \"@opencode-ai/plugin\";\n"
            'export default {\n  name: "nwave-des",\n  hooks: {\n'
            '    "tool.execute.before": async (input: { tool: string }, '
            "output: Record<string, unknown>) => {},\n"
            "  }\n};\nEOF"
        )
        exec_in_container(contract_validation_container, ["bash", "-c", create])

        _code, out = _py(
            contract_validation_container,
            "from scripts.validation.validate_platform_contracts import validate_des_template; "
            "content=open('/tmp/good.ts').read(); "
            "findings=validate_des_template(content); "
            'print("CLEAN" if not findings else "DIRTY:" + ";".join(f.message for f in findings))',
        )
        assert "CLEAN" in out, (
            f"Compliant template triggered validator findings.\n{out[-400:]}"
        )

    # --- T3: CI validator script -----------------------------------------

    def test_ci_validation_script_exits_zero(
        self, contract_validation_container
    ) -> None:
        code, out = exec_in_container(
            contract_validation_container,
            [
                "bash",
                "-c",
                (
                    "su tester -c 'cd /home/tester/nwave-dev && "
                    "python3 scripts/validation/validate_platform_contracts.py 2>&1' | tail -30"
                ),
            ],
        )
        assert code == 0, f"CI validation script exited {code}.\nOutput:\n{out[-500:]}"

    # --- T4: Commands plugin SSOT compliance (D3 fix) --------------------

    def test_commands_plugin_imports_from_ssot(
        self, contract_validation_container
    ) -> None:
        _code, out = exec_in_container(
            contract_validation_container,
            [
                "grep",
                "-c",
                "platform_contracts",
                f"{_CONTAINER_SRC}/scripts/install/plugins/opencode_commands_plugin.py",
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 0, (
            "opencode_commands_plugin.py does not import from platform_contracts SSOT."
        )

    def test_commands_plugin_has_rewrite_paths_helper(
        self, contract_validation_container
    ) -> None:
        _code, out = exec_in_container(
            contract_validation_container,
            [
                "grep",
                "-c",
                "_rewrite_paths",
                f"{_CONTAINER_SRC}/scripts/install/plugins/opencode_commands_plugin.py",
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 0, "_rewrite_paths helper missing from commands plugin."

    def test_commands_plugin_has_no_hardcoded_fields_list(
        self, contract_validation_container
    ) -> None:
        """D3 fix: plugin must import forbidden-fields from SSOT, not hardcode."""
        _code, out = exec_in_container(
            contract_validation_container,
            [
                "bash",
                "-c",
                (
                    f"grep -c '_FIELDS_TO_REMOVE' "
                    f"{_CONTAINER_SRC}/scripts/install/plugins/opencode_commands_plugin.py "
                    "2>/dev/null || echo 0"
                ),
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count == 0, (
            f"Commands plugin has {count} hardcoded _FIELDS_TO_REMOVE references — "
            "D3 fix regressed.  Import from SSOT instead."
        )

    # --- T5: Skills plugin SSOT import -----------------------------------

    def test_skills_plugin_imports_forbidden_fields_list(
        self, contract_validation_container
    ) -> None:
        _code, out = exec_in_container(
            contract_validation_container,
            [
                "bash",
                "-c",
                (
                    f"grep -E '(platform_contracts|OPENCODE_SKILL_FORBIDDEN_FIELDS)' "
                    f"{_CONTAINER_SRC}/scripts/install/plugins/opencode_skills_plugin.py "
                    "| wc -l"
                ),
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 0, (
            "opencode_skills_plugin.py does not reference the SSOT "
            "forbidden-fields list — field-stripping may be inconsistent."
        )

    # --- T6: DES template compliance -------------------------------------

    def test_des_template_uses_opencode_ai_import(
        self, contract_validation_container
    ) -> None:
        tpl = f"{_CONTAINER_SRC}/nWave/templates/opencode-des-plugin.ts.template"
        _code, out = exec_in_container(
            contract_validation_container,
            ["bash", "-c", f'grep -c "@opencode-ai/plugin" "{tpl}"'],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 0, (
            "DES template does not import from @opencode-ai/plugin — ANOMALY-3."
        )

    def test_des_template_has_no_is_subagent(
        self, contract_validation_container
    ) -> None:
        tpl = f"{_CONTAINER_SRC}/nWave/templates/opencode-des-plugin.ts.template"
        _code, out = exec_in_container(
            contract_validation_container,
            ["bash", "-c", f'grep -c "is_subagent" "{tpl}" || echo 0'],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count == 0, (
            "DES template contains is_subagent references — ANOMALY-4 regressed."
        )

    def test_des_template_uses_two_param_handler(
        self, contract_validation_container
    ) -> None:
        tpl = f"{_CONTAINER_SRC}/nWave/templates/opencode-des-plugin.ts.template"
        _code, out = exec_in_container(
            contract_validation_container,
            [
                "bash",
                "-c",
                f'grep -cE "async\\s*\\(input[^)]*,\\s*output" "{tpl}" || echo 0',
            ],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 0, (
            "DES template handler does not use two-param (input, output) signature."
        )

    # --- T7: Agent permission format (matthias fix) ----------------------

    def test_agents_plugin_uses_allow_string_format(
        self, contract_validation_container
    ) -> None:
        plugin = f"{_CONTAINER_SRC}/scripts/install/plugins/opencode_agents_plugin.py"
        _code, out = exec_in_container(
            contract_validation_container,
            ["bash", "-c", f'grep -c \'"allow"\' "{plugin}" || echo 0'],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 0, 'Agents plugin does not use "allow" string permission format.'

    def test_agents_plugin_uses_permission_key(
        self, contract_validation_container
    ) -> None:
        plugin = f"{_CONTAINER_SRC}/scripts/install/plugins/opencode_agents_plugin.py"
        _code, out = exec_in_container(
            contract_validation_container,
            ["bash", "-c", f'grep -c "permission" "{plugin}"'],
        )
        try:
            count = int(out.strip())
        except ValueError:
            count = 0
        assert count > 0, "Agents plugin missing 'permission' key references."
