"""Verify a built wheel (or wheel tree) contains no private artifact.

The wheel-privacy gate (RCA Fix 1 hardening) — the release-pipeline check
that would have caught the nwave_ai-3.15.1 IP leak. It inspects a wheel
tree, loads the catalog allow-list (the privacy SSOT), and reports every
``public: false`` agent file and every privately-owned skill directory
that survived into the package.

This is the verification counterpart of ``strip_private_agents.strip``:
the strip removes private work, this gate detects-if-present. It reuses
the catalog-reading logic in ``scripts.shared.agent_catalog`` rather than
re-deriving the public/private partition.

Usage::

    python scripts/release/verify_wheel_privacy.py <wheel-or-tree>

``verify`` returns a list of privacy-violation strings (empty == clean).
"""

from __future__ import annotations

import sys
from pathlib import Path


# Ensure project root is in sys.path for standalone CLI invocation
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.shared.agent_catalog import (  # noqa: E402
    CatalogNotFoundError,
    CatalogParseError,
    build_ownership_map,
    detect_command_skills,
    is_public_agent,
    is_public_skill,
    load_public_agents,
)


def verify(wheel_or_tree: Path) -> list[str]:
    """Return the list of private artifacts found in the wheel.

    Empty list == the wheel is clean. A non-empty list fails the gate.

    Args:
        wheel_or_tree: path to a directory tree containing an ``nWave/``
            subdirectory.

    Returns:
        list of violation strings (one per leaked private artifact).
    """
    nwave_dir = Path(wheel_or_tree) / "nWave"

    # Fail-closed: a missing or corrupt catalog raises CatalogNotFoundError /
    # CatalogParseError — the gate cannot prove the wheel is clean, so it
    # must report the unverifiable catalog as a violation and refuse the
    # wheel, never silently pass (and never crash with a traceback).
    try:
        public_agents = load_public_agents(nwave_dir, strict=True)
    except (CatalogNotFoundError, CatalogParseError) as exc:
        return [f"unverifiable catalog: {exc}"]

    violations: list[str] = []

    agents_dir = nwave_dir / "agents"
    skills_dir = nwave_dir / "skills"

    if agents_dir.exists():
        for agent_file in sorted(agents_dir.glob("nw-*.md")):
            if not is_public_agent(agent_file.name, public_agents):
                violations.append(f"private agent: nWave/agents/{agent_file.name}")

    if skills_dir.exists():
        ownership_map = build_ownership_map(agents_dir)
        command_skills = detect_command_skills(skills_dir)
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir() or not skill_dir.name.startswith("nw-"):
                continue
            if not is_public_skill(
                skill_dir.name,
                public_agents,
                ownership_map=ownership_map,
                command_skills=command_skills,
            ):
                violations.append(f"private skill: nWave/skills/{skill_dir.name}")

    return violations


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <wheel-or-tree>", file=sys.stderr)
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.is_dir():
        print(f"ERROR: not a directory: {target}", file=sys.stderr)
        sys.exit(1)

    violations = verify(target)
    if violations:
        print(f"FAIL: {len(violations)} private artifact(s) in the wheel:")
        for v in violations:
            print(f"  {v}")
        sys.exit(1)

    print("PASS: wheel carries no private artifact")


if __name__ == "__main__":
    main()
