"""Fitness function: skill-vs-command reviewer dispatch parity.

CONTRACT_SHAPE: pure-function
Outcome anchor: After running the test suite, developers see every mandatory
reviewer declared in a wave skill is dispatched by its command — drift fails CI
immediately, not in user reports.

Asserts that every reviewer agent named in a wave skill's MANDATORY review
sections (e.g. "Final Wave Review Gate (Mandatory ...)") also appears as an
Agent-tool dispatch (`subagent_type="nw-X-reviewer"`) in the corresponding
wave command file. Pure file parsing — no subprocess, no network.

Empirical anchor (nWave-ai/nWave issue #52): nw-distill/SKILL.md mandates the
acceptance-designer-reviewer (Sentinel) in its Final Wave Review Gate, but
tasks/nw/distill.md only dispatches product-owner / solution-architect /
platform-architect reviewers via `subagent_type=...` in its Triple Review
Gate. The Sentinel mention at the fast-path line is markdown prose, not an
Agent dispatch, so the orchestrator never invokes it. This fitness function
is the missing mechanical contract called out in the RCA (root cause A,
why-5A): no CI gate forces skill↔command consistency.

RCA reference: docs/feature/fix-distill-reviewer-gate-gap/discuss/wave-decisions.md
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "nWave" / "skills"
COMMANDS_DIR = REPO_ROOT / "nWave" / "tasks" / "nw"

WAVES = ["discuss", "design", "devops", "distill"]

# Heading is "mandatory" when the line is a markdown heading (#, ##, ###, ...)
# AND contains the case-insensitive substring "mandator" (matches "Mandatory",
# "mandatory" — but not the optional-with-mandatory-suffix phrasing in
# DEVOPS/DISCUSS "OPTIONAL — per-wave; mandatory at end of DISTILL" because
# that line's heading text leads with OPTIONAL, see below).
MANDATORY_HEADING_RE = re.compile(r"^#{1,6}\s+(?P<heading>.+)$")
REVIEWER_NAME_RE = re.compile(r"@?(nw-[a-z][a-z0-9-]*-reviewer)")
SUBAGENT_DISPATCH_RE = re.compile(
    r'subagent_type\s*=\s*"(nw-[a-z][a-z0-9-]*-reviewer)"'
)


def _is_mandatory_heading(heading_text: str) -> bool:
    """Return True if heading declares a MANDATORY review/dispatch gate.

    Heuristic: contains "mandator" (case-insensitive) AND does NOT lead with
    "OPTIONAL" / "optional". This excludes per-wave optional gates whose
    headings read "Peer Review Gate (OPTIONAL — per-wave; mandatory at end of
    DISTILL)" — these are pointers to the DISTILL gate, not local mandates.
    """
    lowered = heading_text.lower().strip()
    if "mandator" not in lowered:
        return False
    return not (lowered.startswith("optional") or "(optional" in lowered)


def _extract_mandatory_reviewers(skill_text: str) -> set[str]:
    """Return reviewer agent names declared in MANDATORY review sections.

    Walks the markdown line-by-line tracking the current "mandatory" section
    scope. A section starts at a heading flagged mandatory and ends at the
    next heading of equal-or-shallower depth. Inside the section, collect
    every `@nw-...-reviewer` or `nw-...-reviewer` token.
    """
    reviewers: set[str] = set()
    in_mandatory_section = False
    section_depth = 0

    for line in skill_text.splitlines():
        heading_match = MANDATORY_HEADING_RE.match(line)
        if heading_match:
            depth = len(line) - len(line.lstrip("#"))
            heading_text = heading_match.group("heading")
            if _is_mandatory_heading(heading_text):
                in_mandatory_section = True
                section_depth = depth
                continue
            # New heading at same or shallower depth closes the mandatory section
            if in_mandatory_section and depth <= section_depth:
                in_mandatory_section = False
                section_depth = 0
            continue

        if in_mandatory_section:
            for match in REVIEWER_NAME_RE.finditer(line):
                reviewers.add(match.group(1))

    return reviewers


def _extract_dispatched_reviewers(command_text: str) -> set[str]:
    """Return reviewer agent names dispatched via Agent tool in command file.

    Looks for `subagent_type="nw-X-reviewer"` patterns only — these are the
    actual orchestration dispatches the runtime executes. Markdown prose
    mentions of reviewer agents elsewhere in the file are NOT counted because
    the orchestrator does not auto-dispatch from prose (RCA evidence C).
    """
    return set(SUBAGENT_DISPATCH_RE.findall(command_text))


@pytest.mark.parametrize("wave", WAVES)
def test_every_mandatory_wave_reviewer_in_skill_appears_in_command_dispatch(
    wave: str,
) -> None:
    """For each wave, mandatory skill reviewers must be dispatched by command.

    The skill file declares the contract (which reviewers are mandatory). The
    command file is what the orchestrator actually executes. When skill says
    "dispatch reviewer X" but command file does not include `subagent_type="X"`
    in any Agent dispatch block, the runtime silently runs a different gate
    than the documented one — production drift.
    """
    skill_path = SKILLS_DIR / f"nw-{wave}" / "SKILL.md"
    command_path = COMMANDS_DIR / f"{wave}.md"

    assert skill_path.is_file(), f"Missing skill file: {skill_path}"
    assert command_path.is_file(), f"Missing command file: {command_path}"

    skill_text = skill_path.read_text(encoding="utf-8")
    command_text = command_path.read_text(encoding="utf-8")

    skill_mandatory = _extract_mandatory_reviewers(skill_text)
    command_dispatched = _extract_dispatched_reviewers(command_text)

    missing = skill_mandatory - command_dispatched
    assert not missing, (
        f"Wave '{wave}': skill mandates reviewers not dispatched by command. "
        f"Missing from {command_path.name}: {sorted(missing)}. "
        f"Skill mandatory set: {sorted(skill_mandatory)}. "
        f"Command dispatched set: {sorted(command_dispatched)}. "
        f'Fix: add `subagent_type="<reviewer>"` Agent dispatch block(s) to '
        f"{command_path.relative_to(REPO_ROOT)}, OR remove the reviewer from "
        f"the skill's mandatory section if no longer required."
    )
