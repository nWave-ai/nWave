---
description: "Generates C4 architecture diagrams (context, container, component) in Mermaid or PlantUML. Use when creating or updating architecture visualizations."
argument-hint: "[diagram-type] - Optional: --format=[mermaid|plantuml|c4] --level=[context|container|component]"
---

# NW-DIAGRAM: Architecture Diagram Generation

**Wave**: CROSS_WAVE
**Agent**: Morgan (nw-solution-architect)
**Command**: `*create-diagrams`

## Overview

Generate architecture diagrams from design documents. Supports C4 model levels (context, container, component) in Mermaid, PlantUML, or C4 format. Produces audience-appropriate visualizations: high-level context for stakeholders, component details for developers, deployment topology for operations.

## Context Files Required

- docs/architecture/architecture-design.md - Architecture definition
- docs/architecture/component-boundaries.md - Component structure
- docs/architecture/technology-stack.md - Technology choices

## Agent Invocation

@nw-solution-architect

Execute \*create-diagrams for {architecture-component}.

**Context Files:**

- docs/architecture/architecture-design.md
- docs/architecture/component-boundaries.md
- docs/architecture/technology-stack.md

**Configuration:**

- diagram_type: component # component/deployment/sequence/data/context
- format: mermaid # mermaid/plantuml/c4
- level: container # context/container/component
- output_directory: docs/architecture/diagrams/

## Success Criteria

- [ ] Diagrams accurately represent current architecture
- [ ] Audience-appropriate detail level applied
- [ ] Diagrams render without syntax errors
- [ ] Output files created in configured directory

## Next Wave

**Handoff To**: {invoking-agent-returns-to-workflow}
**Deliverables**: Architecture diagrams in configured format

## Examples

### Example 1: Generate C4 container diagram
```
/nw:diagram payment-service --diagram_type=component --format=mermaid --level=container
```
Morgan reads architecture docs and produces a Mermaid container diagram showing service boundaries, data stores, and external integrations.

## Expected Outputs

```
docs/architecture/diagrams/
  system-context.{ext}
  component-architecture.{ext}
  deployment-architecture.{ext}
```
