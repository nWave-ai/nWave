"""In-memory composition root for the rc_smoke acceptance suite (DISTILL).

Pillar 3: the SUT (SmokeRunner / __main__) is wired through the SAME ports the
production composition root uses; only the driven ports — install, subprocess
boot, real-tool filesystem — are faked, because those are external /
non-deterministic and can only run for real in the CI gate.

A ToolContract is real data (not faked): the registry is pure domain DATA, so
the suite builds genuine ToolContract rows to exercise per-tool behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.release.rc_smoke.contracts import ToolContract
from scripts.release.rc_smoke.runner import SmokeRunner
from tests.release.rc_smoke.acceptance.steps.domain_types import Tool
from tests.release.rc_smoke.acceptance.steps.fakes import (
    FakeFileSystem,
    FakeInstaller,
    FakeProcess,
)


# Genuine ToolContract rows used by the local suite. These mirror the SHAPE
# DELIVER will register in scripts/release/rc_smoke/contracts.py; the local
# suite owns its own copies so it can exercise per-tool behaviour without
# importing the (RED-scaffold) production registry lookup.
_LOCAL_CONTRACTS: dict[Tool, ToolContract] = {
    Tool.CLAUDE_CODE: ToolContract(
        tool_id="claude-code",
        install_package="@anthropic-ai/claude-code",
        boot_argv=("claude", "--version"),
        isolation_env_var="CLAUDE_CONFIG_DIR",
        required_artifact_globs=("agents/nw/*.md", "settings.json"),
    ),
    Tool.CODEX: ToolContract(
        tool_id="codex",
        install_package="@openai/codex",
        boot_argv=("codex", "--version"),
        isolation_env_var="CODEX_HOME",
        required_artifact_globs=("AGENTS.md", "prompts/nw/*.md"),
    ),
    Tool.OPENCODE: ToolContract(
        tool_id="opencode",
        install_package="opencode-ai",
        boot_argv=("opencode", "--version"),
        isolation_env_var="OPENCODE_CONFIG_DIR",
        required_artifact_globs=("opencode.json", "agent/nw/*.md"),
    ),
}


def contract_for(tool: Tool) -> ToolContract:
    return _LOCAL_CONTRACTS[tool]


@dataclass
class Composition:
    """Holds the fakes and the SUT wired over them."""

    installer: FakeInstaller
    process: FakeProcess
    filesystem: FakeFileSystem
    runner: SmokeRunner


def build_composition(
    installer: FakeInstaller | None = None,
    process: FakeProcess | None = None,
    filesystem: FakeFileSystem | None = None,
) -> Composition:
    """Wire a SmokeRunner over in-memory fakes (defaults = all-pass)."""
    inst = installer or FakeInstaller()
    proc = process or FakeProcess()
    fs = filesystem or FakeFileSystem()
    runner = SmokeRunner(installer=inst, process=proc, filesystem=fs)
    return Composition(installer=inst, process=proc, filesystem=fs, runner=runner)
