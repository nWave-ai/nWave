"""Domain types for the rc-cross-os-multitool-validation acceptance suite.

Mandate-12 (criterion 1): every domain noun used in the Gherkin and the
step methods is expressed once here as a typed enum / dataclass. Step methods
and the in-memory composition consume these types — never raw ``str`` where a
domain enum exists.

Vocabulary shared across the suite (all under
``tests/release/rc_smoke/acceptance/steps/``):
  * test_smoke_orchestration.py   (SmokeRunner orchestration + exit-code contract)
  * test_tool_contract_registry.py (per-tool ToolContract behaviour)
  * test_platform_passthrough.py  (US-5 --platform contract)
  * test_copilot_absent.py        (US-4 Copilot xfail-strict)

This is a config-/orchestration-shaped feature (one smoke lane, finite tool
set), so Tier B (state-machine PBT) is NOT warranted (Mandate 10 skip rule).
The real cross-OS install runs ONLY in the ``validate-rc-multitool`` CI gate;
this suite drives the harness through in-memory fakes (see ``fakes.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Tool(Enum):
    """A supported agentic CLI the harness can smoke.

    The three KNOWN tools have a ToolContract row. COPILOT is deliberately
    absent from the contract registry — its absence is the US-4 assertion.
    """

    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    OPENCODE = "opencode"


# Tools that are NOT supported and must have NO install path (US-4 / D-5).
class UnsupportedTool(Enum):
    COPILOT = "copilot"


class SmokeStepKind(Enum):
    """The ordered steps a single lane runs (mirrors result.SmokeStep)."""

    INSTALL_PUBLISHED = "install_published"
    PROVISION = "provision"
    BOOT = "boot"
    ASSERT_ARTIFACTS = "assert_artifacts"


class LaneOutcome(Enum):
    """The observable verdict of a lane, as seen at the harness exit code."""

    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class ScriptedStep:
    """A scripted per-step outcome for the in-memory fakes.

    ``kind`` is the step to script; ``succeeds`` is whether that step's fake
    reports success; ``diagnostic`` is the readable message a failure carries.
    """

    kind: SmokeStepKind
    succeeds: bool
    diagnostic: str = ""


# The canonical exit-code contract (DESIGN L1), expressed as data so the
# step bodies assert against it rather than hard-coding magic numbers.
EXIT_PASS = 0
EXIT_FAIL_NONZERO = 1
