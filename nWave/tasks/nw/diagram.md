---
description: "Generates C4 architecture diagrams (context, container, component) in Mermaid or PlantUML. Use when creating or updating architecture visualizations."
argument-hint: "[diagram-type] - Optional: --format=[mermaid|plantuml|c4] --level=[context|container|component]"
---

# NW-DIAGRAM: Architecture Diagram Generation

**Wave**: CROSS_WAVE | **Agent**: Morgan (nw-solution-architect), semantic content only | **Command**: `/nw-diagram`

## Overview

Generate standalone architecture diagram content from design documents, without authoring architecture authority. Supports C4 model levels (context|container|component) in Mermaid|PlantUML|C4 format. Audience-appropriate: high-level context for stakeholders|component details for developers|deployment topology for operations.

## Context Files Required

- docs/product/architecture/brief.md (SSOT — component boundaries, technology stack, design decisions)

## Agent Invocation

@nw-solution-architect

Return semantic diagram content in the configured format for {architecture-component}; do not write final architecture-document bytes or diagram files. The caller validates the content with the selected renderer and writes any requested diagram files.

**Context Files:** docs/product/architecture/brief.md

**Configuration:**
- diagram_type: component (component|deployment|sequence|data|context)
- format: mermaid (mermaid|plantuml|c4)
- level: container (context|container|component)
- output_directory (caller-owned, if files requested): docs/product/architecture/


## Success Criteria

- [ ] Diagrams accurately represent current architecture
- [ ] Audience-appropriate detail level applied
- [ ] Diagrams render without syntax errors
- [ ] Requested output files, if any, rendered and written by the caller in the configured directory

## Next Wave

**Handoff To**: {invoking-agent-returns-to-workflow}
**Deliverables**: Diagram content in configured format, and caller-written diagram files if requested

## Examples

### Example 1: Generate C4 container diagram
```
/nw-diagram payment-service --diagram_type=component --format=mermaid --level=container
```
Morgan reads architecture docs and returns Mermaid container diagram content showing service boundaries, data stores, and external integrations; the caller renders it and writes a diagram file if requested.

## Example File Output (when requested)

```
docs/product/architecture/
  payment-service-container.mmd
```
