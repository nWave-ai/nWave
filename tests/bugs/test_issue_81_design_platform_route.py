"""Acceptance oracle for public issue #81's Decision 0 routing contract."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SURFACES = {
    "task": ROOT / "nWave/tasks/nw/design.md",
    "skill": ROOT / "nWave/skills/nw-design/SKILL.md",
}
EXPECTED_ROUTES = {
    "system": ("@nw-system-designer",),
    "domain": ("@nw-ddd-architect",),
    "application": ("@nw-solution-architect",),
    "full-stack": (
        "@nw-system-designer",
        "@nw-ddd-architect",
        "@nw-solution-architect",
    ),
    "platform-delivery": ("@nw-platform-architect",),
}
LEGACY_OPTION_LINES = {
    "task": (
        "1. **System / infrastructure** — distributed architecture, scalability, caching, load balancing, message queues → invokes @nw-system-designer",
        "2. **Domain / bounded contexts** — DDD, aggregates, Event Modeling, event sourcing, context mapping → invokes @nw-ddd-architect",
        "3. **Application / components** — component boundaries, hexagonal architecture, tech stack, ADRs → invokes @nw-solution-architect",
        "4. **Full stack** — all three in sequence: system -> domain -> application → invokes all three agents sequentially",
    ),
    "skill": (
        "1. **System / infrastructure** → invokes @nw-system-designer",
        "2. **Domain / bounded contexts** → invokes @nw-ddd-architect",
        "3. **Application / components** → invokes @nw-solution-architect",
        "4. **Full stack** → invokes all three agents sequentially",
    ),
}
LEGACY_TABLE_ROWS = (
    "| System / infrastructure | @nw-system-designer | Distributed architecture, scalability, caching, load balancing, message queues |",
    "| Domain / bounded contexts | @nw-ddd-architect | DDD, aggregates, Event Modeling, event sourcing, context mapping |",
    "| Application / components | @nw-solution-architect | Component boundaries, hexagonal architecture, tech stack, ADRs |",
    "| Full stack | @nw-system-designer then @nw-ddd-architect then @nw-solution-architect | All three in sequence |",
)
LEGACY_DISPATCH_LINES = (
    "**System scope** → @nw-system-designer",
    "**Domain scope** → @nw-ddd-architect",
    "**Application scope** → @nw-solution-architect",
    "**Full stack** → @nw-system-designer then @nw-ddd-architect then @nw-solution-architect",
)


def _section(text: str, start: str, end: str) -> str:
    assert text.count(start) == 1, f"expected one {start!r} section"
    tail = text.split(start, 1)[1]
    assert end in tail, f"missing end marker {end!r} after {start!r}"
    return tail.split(end, 1)[0]


def _scope_key(label: str) -> str:
    normalized = " ".join(label.lower().replace("—", " ").split())
    if normalized.startswith("system"):
        return "system"
    if normalized.startswith("domain"):
        return "domain"
    if normalized.startswith("application"):
        return "application"
    if normalized.startswith("full stack"):
        return "full-stack"
    if "platform" in normalized and (
        "delivery" in normalized or "infrastructure" in normalized
    ):
        return "platform-delivery"
    raise AssertionError(f"unsupported Decision 0 scope: {label!r}")


def _agent_sequence(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"@nw-[a-z0-9-]+", text))


def _option_routes(text: str) -> dict[str, tuple[str, ...]]:
    block = _section(text, "### Decision 0: Design Scope", "### Decision 1:")
    rows = re.findall(r"^\d+\. \*\*(.+?)\*\*(.+)$", block, re.MULTILINE)
    routes: dict[str, tuple[str, ...]] = {}
    for label, prose in rows:
        key = _scope_key(label)
        assert key not in routes, f"duplicate Decision 0 option for {key}"
        agents = _agent_sequence(prose)
        if key == "full-stack":
            assert "invokes all three agents sequentially" in prose
            routes[key] = EXPECTED_ROUTES[key]
        else:
            assert agents == EXPECTED_ROUTES[key], (
                f"Decision 0 option {label!r} routes to {agents}, "
                f"expected {EXPECTED_ROUTES[key]}"
            )
            routes[key] = agents
    return routes


def _table_routes(text: str) -> dict[str, tuple[str, ...]]:
    block = _section(text, "### Architect Routing (based on Decision 0)", "Pass Decision 1")
    routes: dict[str, tuple[str, ...]] = {}
    for line in block.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] in {"Decision 0", "-------------"}:
            continue
        if set(cells[0]) == {"-"}:
            continue
        key = _scope_key(cells[0])
        assert key not in routes, f"duplicate Architect Routing row for {key}"
        routes[key] = _agent_sequence(cells[1])
    return routes


def _dispatch_routes(text: str) -> dict[str, tuple[str, ...]]:
    block = _section(text, "### Agent Dispatch (after Decision 0", "Execute \\*design-architecture")
    routes: dict[str, tuple[str, ...]] = {}
    for label, target in re.findall(r"^\*\*(.+?)\*\*\s*→\s*(.+)$", block, re.MULTILINE):
        key = _scope_key(label.removesuffix(" scope"))
        assert key not in routes, f"duplicate Agent Dispatch branch for {key}"
        routes[key] = _agent_sequence(target)
    return routes


def test_design_decision_zero_routes_every_declared_scope() -> None:
    observed: dict[str, dict[str, tuple[str, ...]]] = {}

    for name, path in SURFACES.items():
        text = path.read_text(encoding="utf-8")
        for legacy in (*LEGACY_OPTION_LINES[name], *LEGACY_TABLE_ROWS, *LEGACY_DISPATCH_LINES):
            assert text.count(legacy) == 1, f"{name} changed or duplicated legacy route: {legacy}"

        option_routes = _option_routes(text)
        table_routes = _table_routes(text)
        dispatch_routes = _dispatch_routes(text)
        assert option_routes == EXPECTED_ROUTES
        assert table_routes == EXPECTED_ROUTES
        assert dispatch_routes == EXPECTED_ROUTES
        observed[name] = option_routes

    assert observed["task"] == observed["skill"]

    task = SURFACES["task"].read_text(encoding="utf-8")
    roster = _section(task, "**Wave**: DESIGN", "## Overview").splitlines()[0]
    for agent in {agent for route in EXPECTED_ROUTES.values() for agent in route}:
        assert roster.count(agent.removeprefix("@")) == 1, (
            f"task DESIGN roster must name directly routable {agent} exactly once"
        )
