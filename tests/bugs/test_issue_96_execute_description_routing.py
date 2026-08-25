"""Regression oracle for nWave-ai/nWave issue #96."""

from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "nWave" / "skills" / "nw-execute" / "SKILL.md"
COMMAND = REPO_ROOT / "nWave" / "tasks" / "nw" / "execute.md"
CATALOG = REPO_ROOT / "nWave" / "framework-catalog.yaml"

EXPECTED_DESCRIPTION = (
    "Use when a DELIVER roadmap already exists and you need to dispatch exactly one "
    "identified step through its TDD cycle. Use nw-roadmap to create the plan, "
    "nw-deliver for the whole wave, and nw-continue to resume at the next inferred step."
)


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    _, raw, _ = text.split("---", 2)
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, dict)
    return parsed


def test_execute_description_routes_one_known_step_and_excludes_neighbors() -> None:
    """Intent-to-dispatch law is identical across every shipped projection."""
    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    descriptions = {
        "skill": _frontmatter(SKILL)["description"],
        "command": _frontmatter(COMMAND)["description"],
        "catalog": catalog["commands"]["execute"]["description"],
    }

    assert descriptions == {
        "skill": EXPECTED_DESCRIPTION,
        "command": EXPECTED_DESCRIPTION,
        "catalog": EXPECTED_DESCRIPTION,
    }
