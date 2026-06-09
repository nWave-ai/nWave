"""Domain types for the fix-installer-private-skill-leak acceptance suite.

Mandate-12 (criterion 1): every domain noun used in the Gherkin and the
Python ATs is expressed once here as a typed enum / NewType / dataclass.
Step methods and composition services consume these types — never raw
``str`` where a domain enum exists.

Vocabulary shared across (all under
``tests/installer/acceptance/private_skill_leak/steps/``):
  * test_install_log_hygiene.py        (install-log hygiene, Tier A)
  * test_wheel_privacy.py              (wheel privacy + survival)
  * test_skill_reference_integrity.py  (prevention validator)

The slice-01 walking skeleton lives at
``tests/e2e/test_wheel_private_artifact_contract.py`` — it builds the real
``.whl`` through the release pipeline. The release-pipeline strip-order
contract is guarded by that real-wheel outcome test, not by inspecting the
workflow YAML step layout (which would couple the AT to an implementation
shape the shipped fix deliberately does not have).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType


# --- domain nouns ----------------------------------------------------------

# A skill directory name as it appears on disk, e.g. "nw-cialdini-outreach".
SkillName = NewType("SkillName", str)

# An agent file basename, e.g. "nw-outreach-writer.md".
AgentFileName = NewType("AgentFileName", str)


class InstallMode(Enum):
    """Who is running the installer.

    PUBLIC  — an end user installing the published ``nwave-ai`` package.
              The install log must never enumerate private identifiers.
    DEV     — a framework developer (``--dev`` flag). Per-skill skip
              diagnostics are allowed; nothing is private to a dev install.
    """

    PUBLIC = "public"
    DEV = "dev"


class Visibility(Enum):
    """Whether an artifact is allowed in the public PyPI wheel."""

    PUBLIC = "public"
    PRIVATE = "private"


# --- canonical fixtures of record ------------------------------------------

# Private agent files confirmed leaking in nwave_ai-3.15.1 (RCA Q1).
# A fixed (or simulated-fixed) wheel MUST contain none of these.
PRIVATE_AGENT_FILES: tuple[AgentFileName, ...] = tuple(
    AgentFileName(n)
    for n in (
        "nw-outreach-writer.md",
        "nw-deal-closer.md",
        "nw-business-osint.md",
        "nw-workshopper.md",
        "nw-workshopper-reviewer.md",
        "nw-tutorialist.md",
        "nw-tutorialist-reviewer.md",
        "nw-copywriter.md",
        "nw-copywriter-reviewer.md",
        "nw-business-discoverer.md",
        "nw-business-reviewer.md",
        "nw-ux-designer.md",
        "nw-adoption-strategist.md",
        "nw-adoption-strategist-reviewer.md",
    )
)

# Private skill directories confirmed leaking in nwave_ai-3.15.1 (RCA Q1).
PRIVATE_SKILL_DIRS: tuple[SkillName, ...] = tuple(
    SkillName(n)
    for n in (
        "nw-cialdini-outreach",
        "nw-voss-negotiation",
        "nw-competitive-analysis",
        "nw-tbr-methodology",
        "nw-copywriting-frameworks",
        "nw-cw-halbert-editing",
        "nw-pricing-frameworks",
        "nw-icp-design",
        "nw-adoption-funnel-analysis",
        "nw-curriculum-series-design",
    )
)

# Public skills that are load-bearing for public artifacts and MUST survive
# the privacy strip (RCA Q4). All 11 are referenced by a public artifact
# (command-skill body or public agent) yet are NOT owned by any public
# agent's frontmatter ``skills:`` list — so the ownership-only strip drops
# them as "uncatalogued" orphan work, shipping a public package with a
# dangling reference. This is the EXACT triage of the 11 uncatalogued
# skills from the 2026-05-20 audit; the fix must make every one survive.
LOAD_BEARING_PUBLIC_SKILLS: tuple[SkillName, ...] = tuple(
    SkillName(n)
    for n in (
        "nw-density-resolution-contract",
        "nw-jtbd-core",
        "nw-jtbd-interviews",
        "nw-jtbd-opportunity-scoring",
        "nw-jtbd-workflow-selection",
        "nw-persona-jtbd-analysis",
        "nw-roadmap-design",
        "nw-spike-methodology",
        "nw-speculative-dispatch",
        "nw-tdd-cross-language",
        "nw-wizard-shared-rules",
    )
)

# Public agent files that MUST survive the privacy strip — the exact
# complement of PRIVATE_AGENT_FILES. Derived from framework-catalog.yaml
# (every agent with ``public: true``), expressed as ``nw-<key>.md`` to
# match the on-disk basename. Fixture of record for the C6 closed-set
# survival assertion: the strip must keep EVERY one of these, not merely
# "some agent". (32 public agents as of the 2026-05-20 catalog.)
PUBLIC_AGENT_FILES: tuple[AgentFileName, ...] = tuple(
    AgentFileName(f"nw-{name}.md")
    for name in (
        "acceptance-designer",
        "acceptance-designer-reviewer",
        "agent-builder",
        "agent-builder-reviewer",
        "data-engineer",
        "data-engineer-reviewer",
        "ddd-architect",
        "ddd-architect-reviewer",
        "diverger",
        "diverger-reviewer",
        "documentarist",
        "documentarist-reviewer",
        "functional-software-crafter",
        "nwave-buddy",
        "platform-architect",
        "platform-architect-reviewer",
        "product-discoverer",
        "product-discoverer-reviewer",
        "product-owner",
        "product-owner-reviewer",
        "researcher",
        "researcher-reviewer",
        "software-crafter",
        "software-crafter-reviewer",
        "solution-architect",
        "solution-architect-reviewer",
        "system-designer",
        "system-designer-reviewer",
        "test-optimizer",
        "test-optimizer-reviewer",
        "troubleshooter",
        "troubleshooter-reviewer",
    )
)


@dataclass(frozen=True)
class SkillReference:
    """A reference from a public artifact to a skill directory.

    referrer  — the public agent/skill file that names the skill.
    skill     — the referenced skill directory.
    """

    referrer: str
    skill: SkillName
