---
description: "Architecture design with visual representation"
argument-hint: "[component-name] - Optional: --architecture=[hexagonal|layered|microservices] --diagram-format=[mermaid|plantuml]"
---

# NW-DESIGN: Architecture Design

**Wave**: DESIGN (wave 3 of 6)
**Agents**: Morgan (nw-solution-architect)
**Command**: `*design-architecture`

## Overview

Execute DESIGN wave through software architecture design, technology selection, and C4 visual representation. Morgan handles component boundaries, tech stack, and integration points.

Morgan analyzes the existing codebase and evaluates open-source alternatives before designing new components. Integration-first mindset is part of the agent's methodology.

## Context Files Required

- docs/feature/{feature-name}/discuss/requirements.md - From DISCUSS wave
- docs/feature/{feature-name}/discuss/user-stories.md - From DISCUSS wave
- docs/feature/{feature-name}/discuss/domain-model.md - From DISCUSS wave
- docs/feature/{feature-name}/discuss/ux-journey.md - From DISCUSS wave
- docs/feature/{feature-name}/design/constraints.md - Technical and business constraints

## Interactive Decision Points

Before proceeding, the orchestrator asks the user:

### Decision 1: Architecture Style
**Question**: What architecture style should Morgan use for micro-design?
**Options**:
1. Hexagonal (recommended) -- ports and adapters, strong domain isolation
2. Layered -- traditional presentation/business/data layers
3. Clean Architecture -- concentric dependency rings
4. Ports-and-Adapters -- explicit primary/secondary ports

### Decision 2: System Design
**Question**: What system design approach?
**Options**:
1. Monolithic -- single deployable unit
2. Microservices -- independently deployable services
3. Modular Monolith -- logical modules within a single deployment
4. Serverless -- function-as-a-service composition

### Decision 3: Communication Pattern
**Question**: How should components communicate?
**Options**:
1. Synchronous -- REST/gRPC direct calls
2. Asynchronous -- message-driven/event-sourced
3. Hybrid -- synchronous for queries, asynchronous for commands

### Decision 4: Data Architecture
**Question**: What data architecture approach?
**Options**:
1. Single Database -- shared database for all components
2. Database-per-Service -- isolated data stores per bounded context
3. Event Store -- append-only event log as source of truth
4. CQRS -- separate read and write models

## Agent Invocation

@nw-solution-architect

Execute \*design-architecture for {feature-name}.

Context files: see Context Files Required above.

**Configuration:**

- interactive: moderate
- output_format: markdown
- diagram_format: c4
- architecture_style: {from Decision 1, default: hexagonal}
- system_design: {from Decision 2}
- communication_pattern: {from Decision 3}
- data_architecture: {from Decision 4}

## Success Criteria

- [ ] Existing system analyzed before design (codebase search performed)
- [ ] Integration points with existing components documented
- [ ] Reuse vs. new component decisions justified
- [ ] Architecture supports all business requirements
- [ ] Technology stack selected with clear rationale
- [ ] Component boundaries defined (hexagonal architecture)
- [ ] C4 diagrams complete and accessible
- [ ] Handoff accepted by nw-platform-architect (DEVOP wave)

## Next Wave

**Handoff To**: nw-platform-architect (DEVOP wave)
**Deliverables**: See Morgan's handoff package specification in agent file

## Expected Outputs

```
docs/feature/{feature-name}/design/
  architecture-design.md
  technology-stack.md
  component-boundaries.md
  data-models.md
  diagrams/*.svg
```
